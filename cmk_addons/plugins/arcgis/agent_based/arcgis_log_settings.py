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
from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import (
    looks_like_json_rows,
    raw_section_rows,
)

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import raw_section_text
from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionArcGISLogSettings


def _parse_optional_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_arcgis_log_settings(
    string_table: StringTable,
) -> SectionArcGISLogSettings:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        # If multiple appear, last one wins.
        section = SectionArcGISLogSettings()

        for raw in raw_rows:
            section = SectionArcGISLogSettings.model_validate_json(raw)

        return section

    # Old text-row fallback
    values: dict[str, str] = {}

    for row in string_table:
        if len(row) < 2:
            continue

        values[row[0]] = " ".join(row[1:])

    return SectionArcGISLogSettings(
        level=values.get("level", "UNKNOWN"),
        max_log_file_age=_parse_optional_int(values.get("maxLogFileAge")),
        log_dir=values.get("logDir"),
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
    if days <= 0:
        return State.WARN, f"retention {days} days"
    if days < 7:
        return State.WARN, f"retention {days} days"
    if days > 365:
        return State.WARN, f"retention {days} days"

    return State.OK, f"retention {days} days"


def _worst_state(*states: State) -> State:
    order = {
        State.OK: 0,
        State.WARN: 1,
        State.CRIT: 2,
        State.UNKNOWN: 3,
    }
    return max(states, key=lambda state: order[state])


def check_arcgis_log_settings(section: SectionArcGISLogSettings) -> CheckResult:
    level_state, level_summary = _state_for_log_level(section.level)

    states = [level_state]
    summaries = [level_summary]

    if section.max_log_file_age is not None:
        age_state, age_summary = _state_for_max_age(section.max_log_file_age)
        states.append(age_state)
        summaries.append(age_summary)

    if section.log_dir:
        summaries.append(f"log directory {section.log_dir}")

    yield Result(
        state=_worst_state(*states),
        summary=", ".join(summaries),
    )


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
