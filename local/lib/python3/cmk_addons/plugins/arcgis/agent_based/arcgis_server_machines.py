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
    ArcGISServerMachineState,
    SectionArcGISServerMachines,
)

DEFAULT_SERVER_MACHINE_PARAMS = {
    "started_not_started_state": "crit",
    "stopped_stopped_state": "warn",
    "stopped_not_stopped_state": "warn",
    "transitional_state": "warn",
    "unknown_state": "unknown",
}
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_SERVER_MACHINE_PARAMS, key)


def _state_for_machine(
    configured_state: str,
    realtime_state: str,
    params: Mapping[str, Any],
) -> tuple[State, str]:
    configured = configured_state.strip().upper()
    realtime = realtime_state.strip().upper()

    if configured == "STARTED" and realtime == "STARTED":
        return State.OK, "Machine is running"

    if configured == "STARTED" and realtime != "STARTED":
        return (
            state_from_param(_param_str(params, "started_not_started_state")),
            f"Configured STARTED but realtime state is {realtime}",
        )

    if configured == "STOPPED" and realtime == "STOPPED":
        return (
            state_from_param(_param_str(params, "stopped_stopped_state")),
            "Machine is stopped",
        )

    if configured == "STOPPED" and realtime != "STOPPED":
        return (
            state_from_param(_param_str(params, "stopped_not_stopped_state")),
            f"Configured STOPPED but realtime state is {realtime}",
        )

    if realtime in {"STARTING", "STOPPING"}:
        return (
            state_from_param(_param_str(params, "transitional_state")),
            f"Machine is {realtime}",
        )

    return (
        state_from_param(_param_str(params, "unknown_state")),
        f"Configured {configured}, realtime {realtime}",
    )


def parse_arcgis_server_machines(
    string_table: StringTable,
) -> SectionArcGISServerMachines:
    machines: list[ArcGISServerMachineState] = []

    for section in parse_json_rows(string_table, SectionArcGISServerMachines):
        machines.extend(section.machines)

    return SectionArcGISServerMachines(machines=machines)


def discover_arcgis_server_machines(
    section: SectionArcGISServerMachines,
) -> DiscoveryResult:
    for machine in section.machines:
        yield Service(item=machine.name)


def check_arcgis_server_machines(
    item: str,
    params: Mapping[str, Any],
    section: SectionArcGISServerMachines,
) -> CheckResult:
    machines_by_name = {
        machine.name: machine
        for machine in section.machines
    }

    if item not in machines_by_name:
        yield Result(
            state=State.UNKNOWN,
            summary="Machine missing from agent output",
        )
        return

    machine = machines_by_name[item]

    state, summary = _state_for_machine(
        machine.configured_state,
        machine.realtime_state,
        params,
    )

    yield Result(
        state=state,
        summary=summary,
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
    check_default_parameters=DEFAULT_SERVER_MACHINE_PARAMS,
    check_ruleset_name="arcgis_server_machines",
)