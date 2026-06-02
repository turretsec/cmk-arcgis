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
    SectionServerLicense,
    ServerLicenseEntry,
)


def _worst_state(*states: State) -> State:
    order = {State.OK: 0, State.WARN: 1, State.CRIT: 2, State.UNKNOWN: 3}
    return max(states, key=lambda state: order[state])


def _expiration_state(expiration_ms: int, can_expire: bool) -> tuple[State, str]:
    if not can_expire:
        return State.OK, "does not expire"

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


def parse_arcgis_server_license(string_table: StringTable) -> SectionServerLicense:
    entries: list[ServerLicenseEntry] = []

    for section in parse_json_rows(string_table, SectionServerLicense):
        entries.extend(section.entries)

    return SectionServerLicense(entries=entries)


def discover_arcgis_server_license(section: SectionServerLicense) -> DiscoveryResult:
    for entry in section.entries:
        yield Service(item=f"{entry.kind} {entry.name}")


def check_arcgis_server_license(item: str, section: SectionServerLicense) -> CheckResult:
    entries_by_item = {f"{entry.kind} {entry.name}": entry for entry in section.entries}

    license_item = entries_by_item.get(item)
    if license_item is None:
        yield Result(state=State.UNKNOWN, summary="License data missing from agent output")
        return

    expiration_state, expiration_text = _expiration_state(
        license_item.expiration,
        license_item.can_expire,
    )

    if not license_item.is_valid:
        validity_state = State.CRIT
        validity_text = "invalid"
    else:
        validity_state = State.OK
        validity_text = "valid"

    final_state = _worst_state(expiration_state, validity_state)
    display_name = license_item.display_name or license_item.name

    if license_item.kind == "feature":
        if license_item.core_count > 0:
            summary = (
                f"{display_name}: {validity_text}, version {license_item.version}, "
                f"{license_item.core_count} licensed core(s), {expiration_text}"
            )
        else:
            summary = (
                f"{display_name}: {validity_text}, version {license_item.version}, "
                f"{expiration_text}"
            )
    else:
        summary = (
            f"{license_item.kind} {license_item.name}: "
            f"version {license_item.version}, {expiration_text}"
        )

    yield Result(state=final_state, summary=summary)


agent_section_arcgis_server_license = AgentSection(
    name="arcgis_server_license",
    parse_function=parse_arcgis_server_license,
)

check_plugin_arcgis_server_license = CheckPlugin(
    name="arcgis_server_license",
    service_name="ArcGIS Server License %s",
    discovery_function=discover_arcgis_server_license,
    check_function=check_arcgis_server_license,
)
