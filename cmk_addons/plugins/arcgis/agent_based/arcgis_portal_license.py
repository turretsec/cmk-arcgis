from collections.abc import Mapping
from typing import Any
import time

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
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    param_int,
    param_float,
    state_from_param,
    worst_state,
)


DEFAULT_PORTAL_LICENSE_PARAMS = {
    "usage_warn_percent": 85.0,
    "usage_crit_percent": 95.0,
    "expiration_warn_days": 90,
    "expiration_crit_days": 30,
    "maximum_unknown_state": "unknown",
    "expired_state": "crit",
}


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_PORTAL_LICENSE_PARAMS, key)


def _param_float(params: Mapping[str, Any], key: str) -> float:
    return param_float(params, DEFAULT_PORTAL_LICENSE_PARAMS, key)


def _param_int(params: Mapping[str, Any], key: str) -> int:
    return param_int(params, DEFAULT_PORTAL_LICENSE_PARAMS, key)


def _usage_summary(
    current: int,
    maximum: int,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    if maximum <= 0:
        return (
            state_from_param(_param_str(params, "maximum_unknown_state")),
            f"{current} assigned, maximum unknown",
        )

    usage_percent = current / maximum * 100.0
    warn = _param_float(params, "usage_warn_percent")
    crit = _param_float(params, "usage_crit_percent")

    if usage_percent >= crit:
        state = State.CRIT
    elif usage_percent >= warn:
        state = State.WARN
    else:
        state = State.OK

    return state, f"{current}/{maximum} assigned ({usage_percent:.1f}%)"


def _days_until_expiration(expiration_ms: int) -> int | None:
    if expiration_ms <= 0:
        return None

    now_ms = int(time.time() * 1000)
    return int((expiration_ms - now_ms) / 86_400_000)


def _expiration_summary(
    expiration_ms: int,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    days = _days_until_expiration(expiration_ms)

    if days is None:
        return State.OK, "does not expire"

    if days < 0:
        return (
            state_from_param(_param_str(params, "expired_state")),
            f"expired {-days} days ago",
        )

    warn = _param_int(params, "expiration_warn_days")
    crit = _param_int(params, "expiration_crit_days")

    if days <= crit:
        state = State.CRIT
    elif days <= warn:
        state = State.WARN
    else:
        state = State.OK

    return state, f"expires in {days} days"


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


def check_arcgis_portal_license(
    item: str,
    params: Mapping[str, Any],
    section: SectionPortalLicense,
) -> CheckResult:
    if item == "summary":
        current = section.summary.current
        maximum = section.summary.maximum
        version = section.summary.version

        usage_state, usage_text = _usage_summary(
            current,
            maximum,
            params,
        )

        # The summary item is member usage only, no expiration attached.
        if maximum <= 0:
            yield Result(
                state=usage_state,
                summary=f"Portal {version}, {current} registered members, maximum unknown",
            )
            return

        yield Result(
            state=usage_state,
            summary=f"Portal {version}: {usage_text.replace('assigned', 'members used')}",
        )
        return

    items_by_name = {
        f"{license_item.kind} {license_item.id}": license_item
        for license_item in section.items
    }

    license_item = items_by_name.get(item)
    if license_item is None:
        yield Result(
            state=State.UNKNOWN,
            summary="License data missing from agent output",
        )
        return

    usage_state, usage_text = _usage_summary(
        license_item.current,
        license_item.maximum,
        params,
    )

    expiration_state, expiration_text = _expiration_summary(
        license_item.expiration,
        params,
    )

    yield Result(
        state=worst_state(usage_state, expiration_state),
        summary=(
            f"{license_item.kind} {license_item.id}: "
            f"{usage_text}, {expiration_text}"
        ),
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
    check_default_parameters=DEFAULT_PORTAL_LICENSE_PARAMS,
    check_ruleset_name="arcgis_portal_license",
)