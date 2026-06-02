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

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import raw_section_text
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    ArcGISServerMachineState,
    SectionArcGISServerMachines,
)


def _state_from_machine_status(configured_state: str, realtime_state: str) -> State:
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


def parse_arcgis_server_machines(string_table: StringTable) -> SectionArcGISServerMachines:
    raw = raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionArcGISServerMachines.model_validate_json(raw)

    machines: list[ArcGISServerMachineState] = []

    for row in string_table:
        if len(row) < 3:
            continue

        machines.append(
            ArcGISServerMachineState(
                name=row[0],
                configured_state=row[1],
                realtime_state=row[2],
            )
        )

    return SectionArcGISServerMachines(machines=machines)


def discover_arcgis_server_machines(section: SectionArcGISServerMachines) -> DiscoveryResult:
    for machine in section.machines:
        yield Service(item=machine.name)


def check_arcgis_server_machines(
    item: str,
    section: SectionArcGISServerMachines,
) -> CheckResult:
    machines_by_name = {machine.name: machine for machine in section.machines}

    if item not in machines_by_name:
        yield Result(state=State.UNKNOWN, summary="Server machine missing from agent output")
        return

    machine = machines_by_name[item]
    state = _state_from_machine_status(machine.configured_state, machine.realtime_state)

    yield Result(
        state=state,
        summary=f"configured {machine.configured_state}, real-time {machine.realtime_state}",
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
