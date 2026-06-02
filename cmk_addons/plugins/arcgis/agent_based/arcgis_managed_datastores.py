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

def _state_from_managed_datastore_classification(
    classification: str,
    message: str,
) -> State:
    normalized = classification.strip().lower()
    lowered_message = message.strip().lower()

    if normalized in {"success", "ok", "passed", "healthy", "true"}:
        return State.OK

    if normalized in {"warning", "warn", "healthywithwarning", "success_with_warnings"}:
        return State.WARN

    if normalized in {"failure", "failed", "unhealthy", "stopped", "false"}:
        return State.CRIT

    if normalized == "unsupported":
        return State.OK

    if normalized == "error":
        # These are not necessarily failed datastores; some are unsupported API paths.
        if (
            "could not find resource or operation 'validate'" in lowered_message
            or "not installed in the current configuration" in lowered_message
        ):
            return State.OK

        return State.UNKNOWN

    return State.UNKNOWN

def parse_arcgis_managed_datastore_validation(
    string_table: StringTable,
) -> Section:
    parsed: Section = {}

    for row in string_table:
        if len(row) < 2:
            continue

        path = row[0]
        classification = row[1]
        message = " ".join(row[2:]).strip() if len(row) > 2 else ""

        parsed[path] = {
            "path": path,
            "classification": classification,
            "message": message,
        }

    return parsed

def discover_arcgis_managed_datastore_validation(
    section: Section,
) -> DiscoveryResult:
    for path in section:
        yield Service(item=path)

def check_arcgis_managed_datastore_validation(
    item: str,
    section: Section,
) -> CheckResult:
    if item not in section:
        yield Result(
            state=State.UNKNOWN,
            summary="Managed datastore missing from agent output",
        )
        return

    datastore = section[item]

    classification = datastore["classification"]
    message = datastore.get("message", "")

    state = _state_from_managed_datastore_classification(classification, message)
    normalized = classification.strip().lower()

    if normalized == "success":
        summary = "Managed datastore validation successful"
    elif normalized == "unsupported":
        summary = "Managed datastore type is not installed or not supported by this validation method"
    elif normalized == "error":
        summary = "Managed datastore validation returned an error"
    elif normalized in {"failure", "failed"}:
        summary = "Managed datastore validation failed"
    elif normalized in {"warning", "warn"}:
        summary = "Managed datastore validation warning"
    else:
        summary = f"Managed datastore validation status: {classification}"

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

agent_section_arcgis_managed_datastore_validation = AgentSection(
    name="arcgis_managed_datastore_validation",
    parse_function=parse_arcgis_managed_datastore_validation,
)

check_plugin_arcgis_managed_datastore_validation = CheckPlugin(
    name="arcgis_managed_datastore_validation",
    service_name="ArcGIS Managed Datastore %s",
    discovery_function=discover_arcgis_managed_datastore_validation,
    check_function=check_arcgis_managed_datastore_validation,
)