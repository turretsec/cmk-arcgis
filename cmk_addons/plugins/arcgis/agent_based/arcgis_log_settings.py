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

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_last_json_row
from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionArcGISLogSettings
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    param_int,
    state_from_param,
    worst_state,
)

DEFAULT_LOG_SETTINGS_PARAMS = {
    "info_state": "warn",
    "off_state": "warn",
    "debug_state": "crit",
    "unknown_state": "unknown",
    "unexpected_state": "warn",
    "retention_unknown_state": "unknown",
    "retention_outside_range_state": "warn",
    "retention_min_days": 7,
    "retention_max_days": 365,
}


def _param_str(
    params: Mapping[str, Any],
    key: str,
) -> str:
    return param_str(params, DEFAULT_LOG_SETTINGS_PARAMS, key)


def _param_int(
    params: Mapping[str, Any],
    key: str,
) -> int:
    return param_int(params, DEFAULT_LOG_SETTINGS_PARAMS, key)


def parse_arcgis_log_settings(string_table: StringTable) -> SectionArcGISLogSettings:
    return parse_last_json_row(
        string_table,
        SectionArcGISLogSettings,
        SectionArcGISLogSettings(),
    )


def discover_arcgis_log_settings(section: SectionArcGISLogSettings) -> DiscoveryResult:
    if section.level:
        yield Service()


def _state_for_log_level(
    level: str,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    normalized = level.strip().upper()

    if normalized in {"WARNING", "WARN", "SEVERE"}:
        return State.OK, f"log level {normalized}"

    if normalized == "OFF":
        return (
            state_from_param(_param_str(params, "off_state")),
            "log level OFF",
        )

    if normalized == "INFO":
        return (
            state_from_param(_param_str(params, "info_state")),
            "log level INFO",
        )

    if normalized in {"FINE", "FINER", "FINEST", "VERBOSE", "DEBUG"}:
        return (
            state_from_param(_param_str(params, "debug_state")),
            f"log level {normalized}",
        )

    if normalized in {"UNKNOWN", ""}:
        return (
            state_from_param(_param_str(params, "unknown_state")),
            "log level unknown",
        )

    return (
        state_from_param(_param_str(params, "unexpected_state")),
        f"log level {normalized}",
    )


def _state_for_max_age(
    days: int | None,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    if days is None:
        return (
            state_from_param(_param_str(params, "retention_unknown_state")),
            "retention unknown",
        )

    min_days = _param_int(params, "retention_min_days")
    max_days = _param_int(params, "retention_max_days")

    if days <= 0 or days < min_days or days > max_days:
        return (
            state_from_param(_param_str(params, "retention_outside_range_state")),
            f"retention {days} days outside expected range {min_days}-{max_days} days",
        )

    return State.OK, f"retention {days} days"


def check_arcgis_log_settings(
    params: Mapping[str, Any],
    section: SectionArcGISLogSettings,
) -> CheckResult:
    level_state, level_text = _state_for_log_level(section.level, params)
    age_state, age_text = _state_for_max_age(section.max_log_file_age, params)
    final_state = worst_state(level_state, age_state)

    parts = [level_text, age_text]
    if section.log_dir:
        parts.append(f"log directory {section.log_dir}")

    yield Result(state=final_state, summary=", ".join(parts))


agent_section_arcgis_portal_log_settings = AgentSection(
    name="arcgis_portal_log_settings",
    parse_function=parse_arcgis_log_settings,
)

check_plugin_arcgis_portal_log_settings = CheckPlugin(
    name="arcgis_portal_log_settings",
    service_name="ArcGIS Portal Log Settings",
    discovery_function=discover_arcgis_log_settings,
    check_function=check_arcgis_log_settings,
    check_default_parameters=DEFAULT_LOG_SETTINGS_PARAMS,
    check_ruleset_name="arcgis_log_settings",
)

agent_section_arcgis_server_log_settings = AgentSection(
    name="arcgis_server_log_settings",
    parse_function=parse_arcgis_log_settings,
)

check_plugin_arcgis_server_log_settings = CheckPlugin(
    name="arcgis_server_log_settings",
    service_name="ArcGIS Server Log Settings",
    discovery_function=discover_arcgis_log_settings,
    check_function=check_arcgis_log_settings,
    check_default_parameters=DEFAULT_LOG_SETTINGS_PARAMS,
    check_ruleset_name="arcgis_log_settings",
)