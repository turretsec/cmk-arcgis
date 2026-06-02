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



Section = dict[str, str]

def parse_arcgis_log_settings(string_table: StringTable) -> Section:
    parsed: Section = {}

    for row in string_table:
        if len(row) < 2:
            continue

        key = row[0]
        value = " ".join(row[1:])
        parsed[key] = value

    return parsed

def discover_arcgis_log_settings(section: Section) -> DiscoveryResult:
    if section:
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

def _state_for_max_age(value: str) -> tuple[State, str]:
    try:
        days = int(value)
    except ValueError:
        return State.UNKNOWN, f"retention {value}"

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

def check_arcgis_log_settings(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No log settings found")
        return

    level = section.get("level", "UNKNOWN")
    level_state, level_summary = _state_for_log_level(level)

    states = [level_state]
    summaries = [level_summary]

    if "maxLogFileAge" in section:
        age_state, age_summary = _state_for_max_age(section["maxLogFileAge"])
        states.append(age_state)
        summaries.append(age_summary)

    if "logDir" in section:
        summaries.append(f"log directory {section['logDir']}")

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