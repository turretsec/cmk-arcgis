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

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    ArcGISServiceState,
    SectionArcGISServices,
)

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import (
    looks_like_json_rows,
    raw_section_rows,
)

def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()

def _state_from_service_status(
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

# Maps realTimeState values to CMK states
_SERVICE_STATES = {
    "STARTED": State.OK,
    "STOPPED": State.CRIT,
    "STARTING": State.WARN,
    "STOPPING": State.WARN,
    "FAILED": State.CRIT,
}

def parse_arcgis_services(
    string_table: StringTable,
) -> SectionArcGISServices:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        services: list[ArcGISServiceState] = []

        for raw in raw_rows:
            section = SectionArcGISServices.model_validate_json(raw)
            services.extend(section.services)

        return SectionArcGISServices(services=services)

    # Old text-row fallback
    services: list[ArcGISServiceState] = []

    for row in string_table:
        if len(row) < 3:
            continue

        services.append(
            ArcGISServiceState(
                name=row[0],
                configured_state=row[1],
                realtime_state=row[2],
            )
        )

    return SectionArcGISServices(services=services)

def discover_arcgis_services(section: SectionArcGISServices):
    for service in section.services:
        yield Service(item=service.name)

def check_arcgis_services(item: str, section: SectionArcGISServices) -> CheckResult:
    services_by_name = {
        service.name: service
        for service in section.services
    }

    service = services_by_name[item]

    state = _state_from_service_status(
        service.configured_state,
        service.realtime_state,
    )

    if service.configured_state == "STARTED" and service.realtime_state == "STARTED":
        yield Result(state=State.OK, summary=f"Running (configured: {service.configured_state})")

    elif service.configured_state == "STOPPED" and service.realtime_state == "STOPPED":
        yield Result(state=State.OK, summary=f"Intentionally stopped (configured: {service.configured_state})")

    elif service.configured_state == "STARTED" and service.realtime_state != "STARTED":
        yield Result(state=State.CRIT, summary=f"Should be running but is {service.realtime_state}")

    elif service.configured_state == "STOPPED" and service.realtime_state != "STOPPED":
        yield Result(state=State.WARN, summary=f"Running but configured as stopped (realtime: {service.realtime_state})")

    else:
        cmk_state = _SERVICE_STATES.get(service.realtime_state, State.UNKNOWN)
        yield Result(state=cmk_state, summary=f"State: {service.realtime_state} (configured: {service.configured_state})")

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