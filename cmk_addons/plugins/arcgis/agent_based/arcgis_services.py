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
    ArcGISServiceState,
    SectionArcGISServices,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)


DEFAULT_SERVICE_PARAMS = {
    "started_not_started_state": "crit",
    "stopped_stopped_state": "ok",
    "stopped_not_stopped_state": "warn",
    "transitional_state": "warn",
    "failed_state": "crit",
    "unknown_state": "unknown",
}

def _param_str(
    params: Mapping[str, Any],
    key: str,
) -> str:
    return param_str(params, DEFAULT_SERVICE_PARAMS, key)


def parse_arcgis_services(string_table: StringTable) -> SectionArcGISServices:
    services: list[ArcGISServiceState] = []

    for section in parse_json_rows(string_table, SectionArcGISServices):
        services.extend(section.services)

    return SectionArcGISServices(services=services)


def discover_arcgis_services(section: SectionArcGISServices) -> DiscoveryResult:
    for service in section.services:
        yield Service(item=service.name)


def check_arcgis_services(item: str, params: Mapping[str, Any], section: SectionArcGISServices) -> CheckResult:
    services_by_name = {service.name: service for service in section.services}

    service = services_by_name.get(item)
    if service is None:
        yield Result(state=State.UNKNOWN, summary="Service missing from agent output")
        return

    configured = service.configured_state.strip().upper()
    realtime = service.realtime_state.strip().upper()

    if configured == "STARTED" and realtime == "STARTED":
        yield Result(state=State.OK, summary="Service is running")
        return

    if configured == "STOPPED" and realtime == "STOPPED":
        yield Result(
            state=state_from_param(_param_str(params, "stopped_stopped_state")),
            summary="Service is intentionally stopped",
        )
        return

    if configured == "STARTED" and realtime != "STARTED":
        yield Result(
            state=state_from_param(_param_str(params, "started_not_started_state")),
            summary=f"Configured STARTED but realtime state is {realtime}",
        )
        return

    if configured == "STOPPED" and realtime != "STOPPED":
        yield Result(
            state=state_from_param(_param_str(params, "stopped_not_stopped_state")),
            summary=f"Configured STOPPED but realtime state is {realtime}",
        )
        return

    if realtime in {"STARTING", "STOPPING"}:
        yield Result(
            state=state_from_param(_param_str(params, "transitional_state")),
            summary=f"Service is {realtime}",
        )
        return

    if realtime in {"FAILED", "FAILURE"}:
        yield Result(
            state=state_from_param(_param_str(params, "failed_state")),
            summary=f"Service is {realtime}",
        )
        return

    yield Result(
        state=state_from_param(_param_str(params, "unknown_state")),
        summary=f"Configured {configured}, realtime {realtime}",
    )


agent_section_arcgis_services = AgentSection(
    name="arcgis_services",
    parse_function=parse_arcgis_services,
)

check_plugin_arcgis_services = CheckPlugin(
    name="arcgis_services",
    service_name="ArcGIS Service %s",
    discovery_function=discover_arcgis_services,
    check_function=check_arcgis_services,
    check_default_parameters=DEFAULT_SERVICE_PARAMS,
    check_ruleset_name="arcgis_services",
)