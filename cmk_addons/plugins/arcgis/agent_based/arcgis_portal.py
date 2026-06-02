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

def parse_arcgis_portal_health(string_table: StringTable) -> dict[str, str]:
    #print(f"DEBUG portal health rows: {string_table}\n")
    parsed = {}
    for row in string_table:
        if len(row) == 2:
            parsed["status"] = row[0]
            parsed["role"] = row[1]
    return parsed

def discover_arcgis_portal(section: dict[str, str]) -> DiscoveryResult:
    if section.get("status"):
        yield Service()

def check_arcgis_portal_health(section: dict[str, str]) -> CheckResult:
    status = section.get("status", "error")
    role = section.get("role", "")

    if status.strip().lower() == "success":
        summary = "Ready" if not role or role == "unknown" else f"Ready ({role})"
        yield Result(state=State.OK, summary=summary)
    else:
        yield Result(state=State.CRIT, summary=f"Machine not ready: {status}")

agent_section_arcgis_portal = AgentSection(
    name = "arcgis_portal_health",
    parse_function=parse_arcgis_portal_health,
)

check_plugin_arcgis_portal = CheckPlugin(
    name="arcgis_portal_health",
    service_name="ArcGIS Portal Health",
    discovery_function=discover_arcgis_portal,
    check_function=check_arcgis_portal_health,
)

### Portal indexer status

def parse_arcgis_portal_indexer(string_table: StringTable) -> dict:
    parsed = {}
    for row in string_table:
        if len(row) == 3:
            name, db_count, idx_count = row
            parsed[name] = (int(db_count), int(idx_count))
        elif len(row) == 2 and row[0] == "syncStatus":
            parsed["syncStatus"] = row[1] == "True"
    return parsed

def discover_arcgis_portal_indexer(section: dict) -> DiscoveryResult:
    for name in section:
        if name != "syncStatus":
            yield Service(item=name)

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

def discover_arcgis_portal_sync(section: dict) -> DiscoveryResult:
    if "syncStatus" in section:
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

def parse_arcgis_portal_federation(string_table: StringTable) -> dict:
    parsed = {}

    for row in string_table:
        if len(row) == 2 and row[0] == "federationStatus":
            parsed["federationStatus"] = row[1]
        elif len(row) == 2:
            parsed[row[0]] = row[1]

    return parsed

agent_section_arcgis_portal_federation = AgentSection(
    name="arcgis_portal_federation",
    parse_function=parse_arcgis_portal_federation,
)

def discover_arcgis_portal_federation_servers(section: dict) -> DiscoveryResult:
    for name in section:
        if name != "federationStatus":
            yield Service(item=name)

def check_arcgis_portal_federation_servers(item: str, section: dict) -> CheckResult:
    status = section.get(item, "error").strip().lower().replace("_", " ")

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

def discover_arcgis_portal_federation_status(section: dict) -> DiscoveryResult:
    if "federationStatus" in section:
        yield Service()

def check_arcgis_portal_federation_status(section: dict) -> CheckResult:
    status = section.get("federationStatus", "error").strip().lower().replace("_", " ")

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