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

Section = dict[str, dict[str, str]]

def _state_from_registered_datastore_status(status: str) -> State:
    normalized = status.strip().lower()

    if normalized in {"success", "passed", "ok", "true"}:
        return State.OK

    if normalized in {"warning", "warn", "success with warnings"}:
        return State.WARN

    if normalized in {"failure", "failed", "error", "false"}:
        return State.CRIT

    return State.UNKNOWN

def parse_arcgis_registered_datastore_validation(
    string_table: StringTable,
) -> Section:
    parsed: Section = {}

    for row in string_table:
        if len(row) < 3:
            continue

        path = row[0]
        datastore_type = row[1]
        status = row[2]
        message = " ".join(row[3:]) if len(row) > 3 else ""

        parsed[path] = {
            "path": path,
            "type": datastore_type,
            "status": status,
            "message": message,
        }

    return parsed

def discover_arcgis_registered_datastore_validation(
    section: Section,
) -> DiscoveryResult:
    for path in section:
        yield Service(item=path)

def check_arcgis_registered_datastore_validation(
    item: str,
    section: Section,
) -> CheckResult:
    if item not in section:
        yield Result(
            state=State.UNKNOWN,
            summary="Registered datastore missing from agent output",
        )
        return

    datastore = section[item]

    datastore_type = datastore["type"]
    status = datastore["status"]
    message = datastore.get("message", "")

    state = _state_from_registered_datastore_status(status)

    if state == State.OK:
        summary = f"{datastore_type} validation successful"
    elif state == State.WARN:
        summary = f"{datastore_type} validation warning"
    elif state == State.CRIT:
        summary = f"{datastore_type} validation failed"
    else:
        summary = f"{datastore_type} validation status unknown: {status}"

    if message:
        yield Result(
            state=state,
            summary=summary,
            details=message,
        )
    else:
        yield Result(
            state=state,
            summary=summary,
        )

agent_section_arcgis_registered_datastore_validation = AgentSection(
    name="arcgis_registered_datastore_validation",
    parse_function=parse_arcgis_registered_datastore_validation,
)

check_plugin_arcgis_registered_datastore_validation = CheckPlugin(
    name="arcgis_registered_datastore_validation",
    service_name="ArcGIS Registered Datastore %s",
    discovery_function=discover_arcgis_registered_datastore_validation,
    check_function=check_arcgis_registered_datastore_validation,
)