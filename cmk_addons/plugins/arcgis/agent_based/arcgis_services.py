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

# Maps realTimeState values to CMK states
_SERVICE_STATES = {
    "STARTED": State.OK,
    "STOPPED": State.CRIT,
    "STARTING": State.WARN,
    "STOPPING": State.WARN,
    "FAILED": State.CRIT,
}

def parse_arcgis_services(string_table: StringTable) -> dict[str, tuple[str, str]]:
    parsed = {}
    for row in string_table:
        if len(row) == 3:
            service_name, configured_state, realtime_state = row
            parsed[service_name] = (configured_state, realtime_state)
        elif len(row) == 2:
            # backwards compat if needed
            service_name, realtime_state = row
            parsed[service_name] = ("UNKNOWN", realtime_state)
    return parsed

def discover_arcgis_services(section: dict[str, tuple[str, str]]) -> DiscoveryResult:
    for service_name in section:
        yield Service(item=service_name)

def check_arcgis_services(item: str, section: dict[str, tuple[str, str]]) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Service not found in agent output")
        return

    configured, realtime = section[item]

    if configured == "STARTED" and realtime == "STARTED":
        yield Result(state=State.OK, summary=f"Running (configured: {configured})")

    elif configured == "STOPPED" and realtime == "STOPPED":
        yield Result(state=State.OK, summary=f"Intentionally stopped (configured: {configured})")

    elif configured == "STARTED" and realtime != "STARTED":
        yield Result(state=State.CRIT, summary=f"Should be running but is {realtime}")

    elif configured == "STOPPED" and realtime != "STOPPED":
        yield Result(state=State.WARN, summary=f"Running but configured as stopped (realtime: {realtime})")

    else:
        cmk_state = _SERVICE_STATES.get(realtime, State.UNKNOWN)
        yield Result(state=cmk_state, summary=f"State: {realtime} (configured: {configured})")

agent_section_arcgis_services = AgentSection(
    name="arcgis_services",
    parse_function=parse_arcgis_services,
)

check_plugin_arcgis_services = CheckPlugin(
    name="arcgis_services",
    service_name="ArcGIS Service %s",
    discovery_function=discover_arcgis_services,
    check_function=check_arcgis_services,
)