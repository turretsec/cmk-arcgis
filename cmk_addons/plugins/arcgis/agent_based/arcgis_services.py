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
    ArcGISServiceState,
    SectionArcGISServices,
)


def _state_from_service_status(
    configured_state: str,
    realtime_state: str,
) -> State:
    configured = configured_state.strip().upper()
    realtime = realtime_state.strip().upper()

    if configured == "STARTED" and realtime == "STARTED":
        return State.OK
    if configured == "STOPPED" and realtime == "STOPPED":
        return State.OK
    if configured == "STARTED" and realtime != "STARTED":
        return State.CRIT
    if configured != realtime:
        return State.WARN

    return State.UNKNOWN


_SERVICE_STATES = {
    "STARTED": State.OK,
    "STOPPED": State.CRIT,
    "STARTING": State.WARN,
    "STOPPING": State.WARN,
    "FAILED": State.CRIT,
}


def parse_arcgis_services(string_table: StringTable) -> SectionArcGISServices:
    services: list[ArcGISServiceState] = []

    for section in parse_json_rows(string_table, SectionArcGISServices):
        services.extend(section.services)

    return SectionArcGISServices(services=services)


def discover_arcgis_services(section: SectionArcGISServices) -> DiscoveryResult:
    for service in section.services:
        yield Service(item=service.name)


def check_arcgis_services(item: str, section: SectionArcGISServices) -> CheckResult:
    services_by_name = {service.name: service for service in section.services}

    service = services_by_name.get(item)
    if service is None:
        yield Result(state=State.UNKNOWN, summary="Service missing from agent output")
        return

    state = _state_from_service_status(
        service.configured_state,
        service.realtime_state,
    )

    if service.configured_state == "STARTED" and service.realtime_state == "STARTED":
        summary = f"Running (configured: {service.configured_state})"
    elif service.configured_state == "STOPPED" and service.realtime_state == "STOPPED":
        summary = f"Intentionally stopped (configured: {service.configured_state})"
    elif service.configured_state == "STARTED" and service.realtime_state != "STARTED":
        summary = f"Should be running but is {service.realtime_state}"
    elif service.configured_state == "STOPPED" and service.realtime_state != "STOPPED":
        summary = f"Running but configured as stopped (realtime: {service.realtime_state})"
    else:
        state = _SERVICE_STATES.get(service.realtime_state, State.UNKNOWN)
        summary = (
            f"State: {service.realtime_state} "
            f"(configured: {service.configured_state})"
        )

    yield Result(state=state, summary=summary)


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
