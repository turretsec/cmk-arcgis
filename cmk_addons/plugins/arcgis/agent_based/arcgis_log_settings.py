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


def parse_arcgis_log_settings(string_table: StringTable) -> SectionArcGISLogSettings:
    return parse_last_json_row(
        string_table,
        SectionArcGISLogSettings,
        SectionArcGISLogSettings(),
    )


def discover_arcgis_log_settings(section: SectionArcGISLogSettings) -> DiscoveryResult:
    if section.level:
        yield Service()


def _state_for_log_level(level: str) -> tuple[State, str]:
    normalized = level.strip().upper()

    if normalized in {"WARNING", "WARN", "SEVERE"}:
        return State.OK, f"log level {normalized}"
    if normalized == "OFF":
        return State.WARN, "log level OFF"
    if normalized == "INFO":
        return State.WARN, "log level INFO"
    if normalized in {"FINE", "VERBOSE", "DEBUG"}:
        return State.CRIT, f"log level {normalized}"
    if normalized in {"UNKNOWN", ""}:
        return State.UNKNOWN, "log level unknown"

    return State.WARN, f"log level {normalized}"


def _state_for_max_age(days: int | None) -> tuple[State, str]:
    if days is None:
        return State.UNKNOWN, "retention unknown"
    if days <= 0 or days < 7 or days > 365:
        return State.WARN, f"retention {days} days"

    return State.OK, f"retention {days} days"


def _worst_state(*states: State) -> State:
    order = {State.OK: 0, State.WARN: 1, State.CRIT: 2, State.UNKNOWN: 3}
    return max(states, key=lambda state: order[state])


def check_arcgis_log_settings(section: SectionArcGISLogSettings) -> CheckResult:
    level_state, level_text = _state_for_log_level(section.level)
    age_state, age_text = _state_for_max_age(section.max_log_file_age)
    final_state = _worst_state(level_state, age_state)

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
)
