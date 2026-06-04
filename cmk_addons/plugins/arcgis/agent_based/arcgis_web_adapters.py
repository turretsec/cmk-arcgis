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
    SectionArcGISWebAdaptors,
    WebAdaptorEntry,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)


DEFAULT_WEB_ADAPTOR_PARAMS: Mapping[str, Any] = {
    # An adaptor vanishing from the registered list means requests to its URL
    # will no longer reach ArcGIS Server - treat as CRIT by default.
    "missing_state": "crit",
    # isAdminEnabled exposes the Server Admin REST API through the web adaptor.
    # Most security hardening guides recommend keeping this disabled; WARN by
    # default so administrators are alerted without breaking the check.
    "admin_enabled_state": "warn",
}


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_WEB_ADAPTOR_PARAMS, key)


def parse_arcgis_web_adaptors(string_table: StringTable) -> SectionArcGISWebAdaptors:
    web_adaptors = []
    for section in parse_json_rows(string_table, SectionArcGISWebAdaptors):
        web_adaptors.extend(section.web_adaptors)
    return SectionArcGISWebAdaptors(web_adaptors=web_adaptors)


def discover_arcgis_web_adaptors(section: SectionArcGISWebAdaptors) -> DiscoveryResult:
    for adaptor in section.web_adaptors:
        yield Service(item=adaptor.web_adaptor_url)


def check_arcgis_web_adaptors(
    item: str,
    params: Mapping[str, Any],
    section: SectionArcGISWebAdaptors,
) -> CheckResult:
    by_url = {a.web_adaptor_url: a for a in section.web_adaptors}

    adaptor = by_url.get(item)
    if adaptor is None:
        yield Result(
            state=state_from_param(_param_str(params, "missing_state")),
            summary="Web adaptor no longer registered with this site",
            details=(
                "This web adaptor URL was discovered during a previous collection "
                "but is no longer present in /admin/system/webadaptors. "
                "External traffic routed through this URL will fail to reach "
                "ArcGIS Server until the adaptor is re-registered."
            ),
        )
        return

    # Build summary
    summary_parts = [f"Machine: {adaptor.machine_name}"]
    if adaptor.https_port and adaptor.https_port != 443:
        summary_parts.append(f"HTTPS port: {adaptor.https_port}")
    if adaptor.description:
        summary_parts.append(adaptor.description)

    # Admin access check
    if adaptor.is_admin_enabled:
        admin_state = state_from_param(_param_str(params, "admin_enabled_state"))
        yield Result(
            state=admin_state,
            summary=f"Admin access enabled - {', '.join(summary_parts)}",
            details=(
                "isAdminEnabled is true on this web adaptor. The ArcGIS Server "
                "Admin REST API is accessible through this adaptor's URL. "
                "Most security hardening guides recommend disabling this unless "
                "it is explicitly required for your deployment."
            ),
        )
        return

    yield Result(
        state=State.OK,
        summary=", ".join(summary_parts),
    )


agent_section_arcgis_web_adaptors = AgentSection(
    name="arcgis_web_adaptors",
    parse_function=parse_arcgis_web_adaptors,
)

check_plugin_arcgis_web_adaptors = CheckPlugin(
    name="arcgis_web_adaptors",
    service_name="ArcGIS Web Adaptor %s",
    discovery_function=discover_arcgis_web_adaptors,
    check_function=check_arcgis_web_adaptors,
    check_default_parameters=dict(DEFAULT_WEB_ADAPTOR_PARAMS),
    check_ruleset_name="arcgis_web_adaptors",
)