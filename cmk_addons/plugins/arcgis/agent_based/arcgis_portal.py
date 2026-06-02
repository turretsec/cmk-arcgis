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

from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionPortalHealth

def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()

def parse_arcgis_portal_health(string_table: StringTable) -> SectionPortalHealth:
    raw = _raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionPortalHealth.model_validate_json(raw)

    # Old fallback: success standalone
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

### Portal indexer status

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    PortalIndexCount,
    SectionPortalIndexer,
)

def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def parse_arcgis_portal_indexer(string_table: StringTable) -> SectionPortalIndexer:
    raw = _raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionPortalIndexer.model_validate_json(raw)

    indexes: list[PortalIndexCount] = []
    sync_status = None

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

    return SectionPortalIndexer(indexes=indexes, sync_status=sync_status)

def discover_arcgis_portal_indexer(section: SectionPortalIndexer) -> DiscoveryResult:
    for index in section.indexes:
        yield Service(item=index.name)

def check_arcgis_portal_indexer(item: str, section: dict[str, tuple[int, int]]) -> CheckResult:
    if item == "syncStatus":
        return
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Index not found in agent output")
        return

    db_count, idx_count = section[item]

    if db_count != idx_count:
        yield Result(
            state=State.WARN,
            summary=f"Index mismatch: database={db_count}, index={idx_count}"
        )
    else:
        yield Result(state=State.OK, summary=f"In sync ({idx_count} items)")

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

### Portal sync status

def discover_arcgis_portal_sync(section: SectionPortalIndexer) -> DiscoveryResult:
    if section.sync_status is not None:
        yield Service()

def check_arcgis_portal_sync(section: dict) -> CheckResult:
    sync = section.get("syncStatus")
    if sync is True:
        yield Result(state=State.OK, summary="Index sync is healthy")
    elif sync is False:
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

### Portal federation status

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    PortalFederatedServerStatus,
    SectionPortalFederation,
)

def parse_arcgis_portal_federation(string_table: StringTable) -> SectionPortalFederation:
    raw = _raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionPortalFederation.model_validate_json(raw)

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

def discover_arcgis_portal_federation_servers(section: SectionPortalFederation) -> DiscoveryResult:
    for server in section.servers:
        yield Service(item=server.admin_url)

def check_arcgis_portal_federation_servers(item: str, section: SectionPortalFederation) -> CheckResult:
    status = section.federation_status

    if status == "success":
        yield Result(state=State.OK, summary="Federated server is healthy")
    elif status == "error":
        yield Result(state=State.CRIT, summary="Federated server is not healthy")
    elif status == "success with warnings":
        yield Result(state=State.WARN, summary="Federated server status is warning")
    else:
        yield Result(state=State.UNKNOWN, summary=f"Federated server status: {status}")

check_plugin_arcgis_portal_federation_servers = CheckPlugin(
    name="arcgis_portal_federation_servers",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Federated Server %s",
    discovery_function=discover_arcgis_portal_federation_servers,
    check_function=check_arcgis_portal_federation_servers,
)

def discover_arcgis_portal_federation_status(section: SectionPortalFederation) -> DiscoveryResult:
    if section.federation_status is not None:
        yield Service()

def check_arcgis_portal_federation_status(section: SectionPortalFederation) -> CheckResult:
    status = section.federation_status.strip().lower().replace("_", " ")

    if status == "success":
        yield Result(state=State.OK, summary="Federation is healthy")
    elif status == "error":
        yield Result(state=State.CRIT, summary="Federation is not healthy")
    elif status == "success with warnings":
        yield Result(state=State.WARN, summary="Federation status is warning")
    else:
        yield Result(state=State.UNKNOWN, summary=f"Federation status: {status}")

check_plugin_arcgis_portal_federation_status = CheckPlugin(
    name="arcgis_portal_federation_status",
    sections=["arcgis_portal_federation"],
    service_name="ArcGIS Portal Federation Status",
    discovery_function=discover_arcgis_portal_federation_status,
    check_function=check_arcgis_portal_federation_status,
)