from collections.abc import Callable, Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_json_rows
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    PortalFederatedServerStatus,
    PortalIndexCount,
    SectionPortalFederation,
    SectionPortalHealth,
    SectionPortalIndexer,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)


# ---------------------------------------------------------------------------
# Portal Health
# ---------------------------------------------------------------------------

def parse_arcgis_portal_health(string_table: StringTable) -> SectionPortalHealth:
    for section in parse_json_rows(string_table, SectionPortalHealth):
        return section
    return SectionPortalHealth(status="UNKNOWN")


def discover_arcgis_portal(section: SectionPortalHealth) -> DiscoveryResult:
    yield Service()


def check_arcgis_portal_health(
    section: SectionPortalHealth,
) -> CheckResult:
    status = section.status.strip().upper()

    if status in {"SUCCESS", "OK", "AVAILABLE"}:
        yield Result(state=State.OK, summary=f"Portal is ready ({section.status})")
        return

    yield Result(state=State.CRIT, summary=f"Portal is not ready: {section.status}")


agent_section_arcgis_portal_health = AgentSection(
    name="arcgis_portal_health",
    parse_function=parse_arcgis_portal_health,
)


check_plugin_arcgis_portal = CheckPlugin(
    name="arcgis_portal_health",
    service_name="ArcGIS Portal Health",
    discovery_function=discover_arcgis_portal,
    check_function=check_arcgis_portal_health,
)


# ---------------------------------------------------------------------------
# Portal Indexer
# ---------------------------------------------------------------------------

DEFAULT_PORTAL_INDEXER_PARAMS = {
    "mismatch_state": "crit",
    "missing_index_state": "unknown",
}

DEFAULT_PORTAL_INDEXER_SYNC_PARAMS = {
    "sync_false_state": "crit",
    "sync_unknown_state": "unknown",
}


def _indexer_param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_PORTAL_INDEXER_PARAMS, key)


def _indexer_sync_param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_PORTAL_INDEXER_SYNC_PARAMS, key)


def parse_arcgis_portal_indexer(string_table: StringTable) -> SectionPortalIndexer:
    indexes: list[PortalIndexCount] = []
    sync_status: bool | None = None

    for section in parse_json_rows(string_table, SectionPortalIndexer):
        indexes.extend(section.indexes)
        if section.sync_status is not None:
            sync_status = section.sync_status

    return SectionPortalIndexer(indexes=indexes, sync_status=sync_status)


def discover_arcgis_portal_indexer(section: SectionPortalIndexer) -> DiscoveryResult:
    for index in section.indexes:
        yield Service(item=index.name)


def check_arcgis_portal_indexer(
    item: str,
    params: Mapping[str, Any],
    section: SectionPortalIndexer,
) -> CheckResult:
    indexes_by_name = {index.name: index for index in section.indexes}

    index = indexes_by_name.get(item)
    if index is None:
        yield Result(
            state=state_from_param(_indexer_param_str(params, "missing_index_state")),
            summary="Index missing from agent output",
        )
        return

    # Metrics yielded regardless of sync state so the trend graph always has
    # data. When counts match the lines overlap; drift makes them diverge.
    yield Metric("arcgis_index_database_count", float(index.database_count))
    yield Metric("arcgis_index_count", float(index.index_count))

    if index.database_count == index.index_count:
        yield Result(
            state=State.OK,
            summary=f"In sync: database {index.database_count}, index {index.index_count}",
        )
        return

    diff = abs(index.database_count - index.index_count)
    yield Result(
        state=state_from_param(_indexer_param_str(params, "mismatch_state")),
        summary=(
            f"Out of sync: database {index.database_count}, "
            f"index {index.index_count} ({diff} apart)"
        ),
    )


agent_section_arcgis_portal_indexer = AgentSection(
    name="arcgis_portal_indexer",
    parse_function=parse_arcgis_portal_indexer,
)


check_plugin_arcgis_portal_indexer = CheckPlugin(
    name="arcgis_portal_indexer",
    service_name="ArcGIS Portal Index %s",
    discovery_function=discover_arcgis_portal_indexer,
    check_function=check_arcgis_portal_indexer,
    check_default_parameters=DEFAULT_PORTAL_INDEXER_PARAMS,
    check_ruleset_name="arcgis_portal_indexer",
)


def discover_arcgis_portal_indexer_sync(
    section: SectionPortalIndexer,
) -> DiscoveryResult:
    if section.sync_status is not None:
        yield Service()


def check_arcgis_portal_indexer_sync(
    params: Mapping[str, Any],
    section: SectionPortalIndexer,
) -> CheckResult:
    if section.sync_status is True:
        yield Result(state=State.OK, summary="Index sync is healthy")
        return

    if section.sync_status is False:
        yield Result(
            state=state_from_param(_indexer_sync_param_str(params, "sync_false_state")),
            summary="Index sync is unhealthy",
        )
        return

    yield Result(
        state=state_from_param(_indexer_sync_param_str(params, "sync_unknown_state")),
        summary="Index sync status unknown",
    )


check_plugin_arcgis_portal_indexer_sync = CheckPlugin(
    name="arcgis_portal_indexer_sync",
    sections=["arcgis_portal_indexer"],
    service_name="ArcGIS Portal Index Sync",
    discovery_function=discover_arcgis_portal_indexer_sync,
    check_function=check_arcgis_portal_indexer_sync,
    check_default_parameters=DEFAULT_PORTAL_INDEXER_SYNC_PARAMS,
    check_ruleset_name="arcgis_portal_indexer_sync",
)


# ---------------------------------------------------------------------------
# Portal Federation
# ---------------------------------------------------------------------------

DEFAULT_PORTAL_FEDERATION_SERVER_PARAMS = {
    "warning_state": "warn",
    "failed_state": "crit",
    "unknown_state": "unknown",
    "missing_server_state": "unknown",
}

DEFAULT_PORTAL_FEDERATION_STATUS_PARAMS = {
    "warning_state": "warn",
    "failed_state": "crit",
    "unknown_state": "unknown",
}


def _federation_server_param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_PORTAL_FEDERATION_SERVER_PARAMS, key)


def _federation_status_param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_PORTAL_FEDERATION_STATUS_PARAMS, key)


def parse_arcgis_portal_federation(
    string_table: StringTable,
) -> SectionPortalFederation:
    servers: list[PortalFederatedServerStatus] = []
    federation_status = "unknown"

    for section in parse_json_rows(string_table, SectionPortalFederation):
        servers.extend(section.servers)
        if section.federation_status != "unknown":
            federation_status = section.federation_status

    return SectionPortalFederation(
        servers=servers,
        federation_status=federation_status,
    )


agent_section_arcgis_portal_federation = AgentSection(
    name="arcgis_portal_federation",
    parse_function=parse_arcgis_portal_federation,
)


def _state_from_federation_status(
    status: str,
    params: Mapping[str, Any],
    param_reader: Callable[[Mapping[str, Any], str], str],
) -> tuple[State, str]:
    normalized = status.strip().lower().replace("_", " ")

    if normalized == "success":
        return State.OK, "healthy"

    if normalized == "success with warnings":
        return (
            state_from_param(param_reader(params, "warning_state")),
            "warning",
        )

    if normalized in {"error", "failure", "failed"}:
        return (
            state_from_param(param_reader(params, "failed_state")),
            "not healthy",
        )

    return (
        state_from_param(param_reader(params, "unknown_state")),
        normalized or "unknown",
    )


def discover_arcgis_portal_federation_servers(
    section: SectionPortalFederation,
) -> DiscoveryResult:
    for server in section.servers:
        yield Service(item=server.admin_url)


def check_arcgis_portal_federation_servers(
    item: str,
    params: Mapping[str, Any],
    section: SectionPortalFederation,
) -> CheckResult:
    servers_by_url = {server.admin_url: server for server in section.servers}

    server = servers_by_url.get(item)
    if server is None:
        yield Result(
            state=state_from_param(
                _federation_server_param_str(params, "missing_server_state")
            ),
            summary="Federated server missing from agent output",
        )
        return

    state, text = _state_from_federation_status(
        server.status,
        params,
        _federation_server_param_str,
    )

    yield Result(state=state, summary=f"Federated server is {text}")


check_plugin_arcgis_portal_federation_servers = CheckPlugin(
    name="arcgis_portal_federation_servers",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Federated Server %s",
    discovery_function=discover_arcgis_portal_federation_servers,
    check_function=check_arcgis_portal_federation_servers,
    check_default_parameters=DEFAULT_PORTAL_FEDERATION_SERVER_PARAMS,
    check_ruleset_name="arcgis_portal_federation_servers",
)


def discover_arcgis_portal_federation_status(
    section: SectionPortalFederation,
) -> DiscoveryResult:
    if section.federation_status:
        yield Service()


def check_arcgis_portal_federation_status(
    params: Mapping[str, Any],
    section: SectionPortalFederation,
) -> CheckResult:
    state, text = _state_from_federation_status(
        section.federation_status,
        params,
        _federation_status_param_str,
    )

    yield Result(state=state, summary=f"Federation is {text}")


check_plugin_arcgis_portal_federation_status = CheckPlugin(
    name="arcgis_portal_federation_status",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Portal Federation Status",
    discovery_function=discover_arcgis_portal_federation_status,
    check_function=check_arcgis_portal_federation_status,
    check_default_parameters=DEFAULT_PORTAL_FEDERATION_STATUS_PARAMS,
    check_ruleset_name="arcgis_portal_federation_status",
)