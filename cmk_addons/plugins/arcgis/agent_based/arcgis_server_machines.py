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

Section = dict[str, dict[str, str]]

def _state_from_machine_status(
    configured_state: str,
    realtime_state: str,
) -> State:
    configured = configured_state.strip().upper()
    realtime = realtime_state.strip().upper()

    if configured == "STARTED" and realtime == "STARTED":
        return State.OK

    if configured == "STOPPED" and realtime == "STOPPED":
        return State.WARN

    if configured == "STARTED" and realtime != "STARTED":
        return State.CRIT

    if configured != realtime:
        return State.WARN

    return State.UNKNOWN

def parse_arcgis_server_machines(string_table: StringTable) -> Section:
    parsed: Section = {}

    for row in string_table:
        if len(row) < 3:
            continue

        machine_name = row[0]
        configured_state = row[1]
        realtime_state = row[2]

        parsed[machine_name] = {
            "configured_state": configured_state,
            "realtime_state": realtime_state,
        }

    return parsed

def discover_arcgis_server_machines(section: Section) -> DiscoveryResult:
    for machine_name in section:
        yield Service(item=machine_name)

def check_arcgis_server_machines(
    item: str,
    section: Section,
) -> CheckResult:
    if item not in section:
        yield Result(
            state=State.UNKNOWN,
            summary="Server machine missing from agent output",
        )
        return

    machine = section[item]
    configured_state = machine["configured_state"]
    realtime_state = machine["realtime_state"]

    state = _state_from_machine_status(configured_state, realtime_state)

    yield Result(
        state=state,
        summary=(
            f"configured {configured_state}, "
            f"real-time {realtime_state}"
        ),
    )

agent_section_arcgis_server_machines = AgentSection(
    name="arcgis_server_machines",
    parse_function=parse_arcgis_server_machines,
)

check_plugin_arcgis_server_machines = CheckPlugin(
    name="arcgis_server_machines",
    service_name="ArcGIS Server Machine %s",
    discovery_function=discover_arcgis_server_machines,
    check_function=check_arcgis_server_machines,
)