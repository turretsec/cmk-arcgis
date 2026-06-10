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
from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionArcGISServerMode
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)


DEFAULT_SERVER_MODE_PARAMS: Mapping[str, Any] = {
    # READ_ONLY is a legitimate maintenance state but should not go unnoticed.
    # Default WARN rather than CRIT because operators may set it intentionally
    # during upgrades; they should still be reminded to flip it back.
    "read_only_state": "warn",
    "unknown_state": "unknown",
}


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_SERVER_MODE_PARAMS, key)


def parse_arcgis_server_mode(string_table: StringTable) -> SectionArcGISServerMode:
    for section in parse_json_rows(string_table, SectionArcGISServerMode):
        return section
    return SectionArcGISServerMode()


def discover_arcgis_server_mode(section: SectionArcGISServerMode) -> DiscoveryResult:
    yield Service()


def check_arcgis_server_mode(
    params: Mapping[str, Any],
    section: SectionArcGISServerMode,
) -> CheckResult:
    mode = section.site_mode.strip().upper()

    if mode == "EDITABLE":
        yield Result(state=State.OK, summary="Site mode: EDITABLE")
        return

    if mode == "READ_ONLY":
        yield Result(
            state=state_from_param(_param_str(params, "read_only_state")),
            summary="Site mode: READ_ONLY",
            details=(
                "The ArcGIS Server site is in read-only mode. "
                "Services cannot be started, stopped, or modified. "
                "This is normal during upgrades but should be resolved afterward."
            ),
        )
        return

    yield Result(
        state=state_from_param(_param_str(params, "unknown_state")),
        summary=f"Site mode: {section.site_mode}",
    )


agent_section_arcgis_server_mode = AgentSection(
    name="arcgis_server_mode",
    parse_function=parse_arcgis_server_mode,
)

check_plugin_arcgis_server_mode = CheckPlugin(
    name="arcgis_server_mode",
    service_name="ArcGIS Server Mode",
    discovery_function=discover_arcgis_server_mode,
    check_function=check_arcgis_server_mode,
    check_default_parameters=dict(DEFAULT_SERVER_MODE_PARAMS),
    check_ruleset_name="arcgis_server_mode",
)