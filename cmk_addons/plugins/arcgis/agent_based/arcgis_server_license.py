import time
from collections.abc import Mapping
from typing import Any

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
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    param_int,
    state_from_param,
    worst_state,
)


DEFAULT_SERVER_LICENSE_PARAMS = {
    "expiration_warn_days": 90,
    "expiration_crit_days": 30,
    "expired_state": "crit",
    "invalid_feature_state": "crit",
    "unknown_expiration_state": "unknown",
    "missing_license_state": "unknown",
}


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_SERVER_LICENSE_PARAMS, key)


def _param_int(params: Mapping[str, Any], key: str) -> int:
    return param_int(params, DEFAULT_SERVER_LICENSE_PARAMS, key)


def _days_until_expiration(expiration_ms: int) -> int | None:
    if expiration_ms <= 0:
        return None

    now_ms = int(time.time() * 1000)
    return int((expiration_ms - now_ms) / 86_400_000)


def _expiration_summary(
    license_item: ServerLicenseEntry,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    if not license_item.can_expire:
        return State.OK, "does not expire"

    days = _days_until_expiration(license_item.expiration)

    if days is None:
        return (
            state_from_param(_param_str(params, "unknown_expiration_state")),
            "expiration unknown",
        )

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


def _validity_summary(
    license_item: ServerLicenseEntry,
    params: Mapping[str, Any],
) -> tuple[State, str | None]:
    if license_item.kind != "feature":
        return State.OK, None

    if license_item.is_valid:
        return State.OK, "valid"

    return (
        state_from_param(_param_str(params, "invalid_feature_state")),
        "invalid",
    )


def parse_arcgis_server_license(string_table: StringTable) -> SectionServerLicense:
    entries: list[ServerLicenseEntry] = []

    for section in parse_json_rows(string_table, SectionServerLicense):
        entries.extend(section.entries)

    return SectionServerLicense(entries=entries)


def discover_arcgis_server_license(section: SectionServerLicense) -> DiscoveryResult:
    for entry in section.entries:
        yield Service(item=f"{entry.kind} {entry.name}")


def check_arcgis_server_license(
    item: str,
    params: Mapping[str, Any],
    section: SectionServerLicense,
) -> CheckResult:
    entries_by_item = {
        f"{entry.kind} {entry.name}": entry
        for entry in section.entries
    }

    license_item = entries_by_item.get(item)
    if license_item is None:
        yield Result(
            state=state_from_param(_param_str(params, "missing_license_state")),
            summary="License data missing from agent output",
        )
        return

    expiration_state, expiration_text = _expiration_summary(
        license_item,
        params,
    )

    validity_state, validity_text = _validity_summary(
        license_item,
        params,
    )

    final_state = worst_state(expiration_state, validity_state)

    summary_parts = [
        f"{license_item.kind} {license_item.name}",
        expiration_text,
    ]

    if validity_text:
        summary_parts.append(validity_text)

    if license_item.display_name:
        summary_parts.append(license_item.display_name)

    if license_item.version:
        summary_parts.append(f"version {license_item.version}")

    if license_item.core_count:
        summary_parts.append(f"{license_item.core_count} cores")

    if license_item.extra:
        summary_parts.append(license_item.extra)

    yield Result(
        state=final_state,
        summary=", ".join(summary_parts),
    )


agent_section_arcgis_server_license = AgentSection(
    name="arcgis_server_license",
    parse_function=parse_arcgis_server_license,
)


check_plugin_arcgis_server_license = CheckPlugin(
    name="arcgis_server_license",
    service_name="ArcGIS Server License %s",
    discovery_function=discover_arcgis_server_license,
    check_function=check_arcgis_server_license,
    check_default_parameters=DEFAULT_SERVER_LICENSE_PARAMS,
    check_ruleset_name="arcgis_server_license",
)
