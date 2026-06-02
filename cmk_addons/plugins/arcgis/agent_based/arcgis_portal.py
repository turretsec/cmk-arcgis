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
    PortalFederatedServerStatus,
    PortalIndexCount,
    SectionPortalFederation,
    SectionPortalHealth,
    SectionPortalIndexer,
)
from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import (
    looks_like_json_rows,
    raw_section_rows,
)

def parse_arcgis_portal_health(
    string_table: StringTable,
) -> SectionPortalHealth:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        # If multiple appear, last one wins.
        section = SectionPortalHealth(status="unknown", role="unknown")

        for raw in raw_rows:
            section = SectionPortalHealth.model_validate_json(raw)

        return section

    # Old text-row fallback
    if string_table and len(string_table[0]) >= 1:
        status = string_table[0][0]
        role = string_table[0][1] if len(string_table[0]) > 1 else "standalone"
        return SectionPortalHealth(status=status, role=role)

    return SectionPortalHealth(status="unknown", role="unknown")


def discover_arcgis_portal(section: SectionPortalHealth) -> DiscoveryResult:
    if section.status:
        yield Service()


def check_arcgis_portal_health(section: SectionPortalHealth) -> CheckResult:
    status = section.status
    role = section.role

    if status.strip().lower() == "success":
        summary = "Ready" if not role or role == "unknown" else f"Ready ({role})"
        yield Result(state=State.OK, summary=summary)
    else:
        yield Result(state=State.CRIT, summary=f"Machine not ready: {status}")


agent_section_arcgis_portal = AgentSection(
    name="arcgis_portal_health",
    parse_function=parse_arcgis_portal_health,
)

check_plugin_arcgis_portal = CheckPlugin(
    name="arcgis_portal_health",
    service_name="ArcGIS Portal Health",
    discovery_function=discover_arcgis_portal,
    check_function=check_arcgis_portal_health,
)


def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_arcgis_portal_indexer(
    string_table: StringTable,
) -> SectionPortalIndexer:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        indexes: list[PortalIndexCount] = []
        sync_status: bool | None = None

        for raw in raw_rows:
            section = SectionPortalIndexer.model_validate_json(raw)
            indexes.extend(section.indexes)

            if section.sync_status is not None:
                sync_status = section.sync_status

        return SectionPortalIndexer(
            indexes=indexes,
            sync_status=sync_status,
        )

    # Old text-row fallback
    indexes: list[PortalIndexCount] = []
    sync_status: bool | None = None

    for row in string_table:
        if not row:
            continue

        if row[0] == "syncStatus" and len(row) >= 2:
            sync_status = row[1].strip().lower() == "true"
            continue

        if len(row) >= 3:
            indexes.append(
                PortalIndexCount(
                    name=row[0],
                    database_count=_parse_int(row[1]),
                    index_count=_parse_int(row[2]),
                )
            )

    return SectionPortalIndexer(
        indexes=indexes,
        sync_status=sync_status,
    )


def discover_arcgis_portal_indexer(section: SectionPortalIndexer) -> DiscoveryResult:
    for index in section.indexes:
        yield Service(item=index.name)


def check_arcgis_portal_indexer(item: str, section: SectionPortalIndexer) -> CheckResult:
    indexes_by_name = {index.name: index for index in section.indexes}

    if item not in indexes_by_name:
        yield Result(state=State.UNKNOWN, summary="Index not found in agent output")
        return

    index = indexes_by_name[item]

    if index.database_count != index.index_count:
        yield Result(
            state=State.WARN,
            summary=(
                f"Index mismatch: database={index.database_count}, "
                f"index={index.index_count}"
            ),
        )
    else:
        yield Result(state=State.OK, summary=f"In sync ({index.index_count} items)")


agent_section_arcgis_portal_indexer = AgentSection(
    name="arcgis_portal_indexer",
    parse_function=parse_arcgis_portal_indexer,
)

check_plugin_arcgis_portal_indexer = CheckPlugin(
    name="arcgis_portal_indexer",
    service_name="ArcGIS Portal Index %s",
    discovery_function=discover_arcgis_portal_indexer,
    check_function=check_arcgis_portal_indexer,
)


def discover_arcgis_portal_sync(section: SectionPortalIndexer) -> DiscoveryResult:
    if section.sync_status is not None:
        yield Service()


def check_arcgis_portal_sync(section: SectionPortalIndexer) -> CheckResult:
    if section.sync_status is True:
        yield Result(state=State.OK, summary="Index sync is healthy")
    elif section.sync_status is False:
        yield Result(state=State.CRIT, summary="Index sync is not healthy")
    else:
        yield Result(state=State.UNKNOWN, summary="Sync status unavailable")


check_plugin_arcgis_portal_sync = CheckPlugin(
    name="arcgis_portal_indexer_sync",
    sections=["arcgis_portal_indexer"],
    service_name="ArcGIS Portal Index Sync",
    discovery_function=discover_arcgis_portal_sync,
    check_function=check_arcgis_portal_sync,
)


def parse_arcgis_portal_federation(
    string_table: StringTable,
) -> SectionPortalFederation:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        servers: list[PortalFederatedServerStatus] = []
        federation_status = "unknown"

        for raw in raw_rows:
            section = SectionPortalFederation.model_validate_json(raw)
            servers.extend(section.servers)

            if section.federation_status != "unknown":
                federation_status = section.federation_status

        return SectionPortalFederation(
            servers=servers,
            federation_status=federation_status,
        )

    # Old text-row fallback
    servers: list[PortalFederatedServerStatus] = []
    federation_status = "unknown"

    for row in string_table:
        if len(row) < 2:
            continue

        if row[0] == "federationStatus":
            federation_status = row[1]
        else:
            servers.append(
                PortalFederatedServerStatus(
                    admin_url=row[0],
                    status=row[1],
                )
            )

    return SectionPortalFederation(
        servers=servers,
        federation_status=federation_status,
    )


agent_section_arcgis_portal_federation = AgentSection(
    name="arcgis_portal_federation",
    parse_function=parse_arcgis_portal_federation,
)


def _state_from_federation_status(status: str) -> tuple[State, str]:
    normalized = status.strip().lower().replace("_", " ")

    if normalized == "success":
        return State.OK, "healthy"
    if normalized == "success with warnings":
        return State.WARN, "warning"
    if normalized in {"error", "failure", "failed"}:
        return State.CRIT, "not healthy"
    return State.UNKNOWN, normalized or "unknown"


def discover_arcgis_portal_federation_servers(section: SectionPortalFederation) -> DiscoveryResult:
    for server in section.servers:
        yield Service(item=server.admin_url)


def check_arcgis_portal_federation_servers(
    item: str,
    section: SectionPortalFederation,
) -> CheckResult:
    servers_by_url = {server.admin_url: server for server in section.servers}

    if item not in servers_by_url:
        yield Result(
            state=State.UNKNOWN,
            summary="Federated server missing from agent output",
        )
        return

    server = servers_by_url[item]
    state, text = _state_from_federation_status(server.status)
    yield Result(state=state, summary=f"Federated server is {text}")


check_plugin_arcgis_portal_federation_servers = CheckPlugin(
    name="arcgis_portal_federation_servers",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Federated Server %s",
    discovery_function=discover_arcgis_portal_federation_servers,
    check_function=check_arcgis_portal_federation_servers,
)


def discover_arcgis_portal_federation_status(section: SectionPortalFederation) -> DiscoveryResult:
    if section.federation_status:
        yield Service()


def check_arcgis_portal_federation_status(section: SectionPortalFederation) -> CheckResult:
    state, text = _state_from_federation_status(section.federation_status)
    yield Result(state=state, summary=f"Federation is {text}")


check_plugin_arcgis_portal_federation_status = CheckPlugin(
    name="arcgis_portal_federation_status",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Portal Federation Status",
    discovery_function=discover_arcgis_portal_federation_status,
    check_function=check_arcgis_portal_federation_status,
)
