from datetime import datetime, timezone

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_json_rows
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    PortalLicenseEntry,
    PortalLicenseSummary,
    SectionPortalLicense,
)


def _expiration_summary(expiration_ms: int) -> tuple[State, str]:
    if expiration_ms <= 0:
        return State.UNKNOWN, "expiration unknown"

    now = datetime.now(timezone.utc)
    expiration = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
    days_left = (expiration - now).days
    expiration_text = expiration.strftime("%Y-%m-%d")

    if days_left < 0:
        return State.CRIT, f"expired on {expiration_text}"
    if days_left <= 7:
        return State.CRIT, f"expires on {expiration_text} ({days_left} days)"
    if days_left <= 30:
        return State.WARN, f"expires on {expiration_text} ({days_left} days)"

    return State.OK, f"expires on {expiration_text} ({days_left} days)"


def _worst_state(*states: State) -> State:
    order = {State.OK: 0, State.WARN: 1, State.CRIT: 2, State.UNKNOWN: 3}
    return max(states, key=lambda state: order[state])


def parse_arcgis_portal_license(string_table: StringTable) -> SectionPortalLicense:
    summary = PortalLicenseSummary()
    items: list[PortalLicenseEntry] = []

    for section in parse_json_rows(string_table, SectionPortalLicense):
        summary = section.summary
        items.extend(section.items)

    return SectionPortalLicense(summary=summary, items=items)


def discover_arcgis_portal_license(section: SectionPortalLicense) -> DiscoveryResult:
    yield Service(item="summary")

    for item in section.items:
        yield Service(item=f"{item.kind} {item.id}")


def check_arcgis_portal_license(item: str, section: SectionPortalLicense) -> CheckResult:
    if item == "summary":
        current = section.summary.current
        maximum = section.summary.maximum
        version = section.summary.version

        if maximum <= 0:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Portal {version}, {current} registered members, maximum unknown",
            )
            return

        usage_percent = current / maximum * 100

        if usage_percent >= 95:
            state = State.CRIT
        elif usage_percent >= 85:
            state = State.WARN
        else:
            state = State.OK

        yield Result(
            state=state,
            summary=f"Portal {version}: {current}/{maximum} members used ({usage_percent:.1f}%)",
        )
        return

    items_by_name = {
        f"{license_item.kind} {license_item.id}": license_item
        for license_item in section.items
    }

    license_item = items_by_name.get(item)
    if license_item is None:
        yield Result(state=State.UNKNOWN, summary="License data missing from agent output")
        return

    expiration_state, expiration_text = _expiration_summary(license_item.expiration)

    if license_item.maximum > 0:
        usage_percent = license_item.current / license_item.maximum * 100
        usage_text = (
            f"{license_item.current}/{license_item.maximum} assigned "
            f"({usage_percent:.1f}%)"
        )

        if usage_percent >= 95:
            usage_state = State.CRIT
        elif usage_percent >= 85:
            usage_state = State.WARN
        else:
            usage_state = State.OK
    else:
        usage_text = f"{license_item.current} assigned, maximum unknown"
        usage_state = State.UNKNOWN

    yield Result(
        state=_worst_state(usage_state, expiration_state),
        summary=f"{license_item.kind} {license_item.id}: {usage_text}, {expiration_text}",
    )


agent_section_arcgis_portal_license = AgentSection(
    name="arcgis_portal_license",
    parse_function=parse_arcgis_portal_license,
)

check_plugin_arcgis_portal_license = CheckPlugin(
    name="arcgis_portal_license",
    service_name="ArcGIS Portal License %s",
    discovery_function=discover_arcgis_portal_license,
    check_function=check_arcgis_portal_license,
)
