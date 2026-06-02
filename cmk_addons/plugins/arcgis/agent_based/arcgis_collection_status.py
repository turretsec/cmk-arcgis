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

Section = list[dict[str, str]]

def parse_arcgis_collection_status(string_table: StringTable) -> Section:
    parsed: Section = []

    for row in string_table:
        if len(row) < 3:
            continue

        component = row[0]
        target = row[1]
        status = row[2].strip().upper()
        message = " ".join(row[3:]).strip() if len(row) > 3 else ""

        parsed.append(
            {
                "component": component,
                "target": target,
                "status": status,
                "message": message,
            }
        )

    return parsed

def discover_arcgis_collection_status(section: Section) -> DiscoveryResult:
    if section:
        yield Service()

def check_arcgis_collection_status(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No collection status found")
        return

    errors = [row for row in section if row["status"] == "ERROR"]
    warnings = [row for row in section if row["status"] == "WARN"]
    skips = [row for row in section if row["status"] == "SKIP"]

    if errors:
        details = "; ".join(
            f"{row['component']}:{row['target']} {row['message']}"
            for row in errors
        )
        yield Result(
            state=State.CRIT,
            summary=f"{len(errors)} collection error(s)",
            details=details,
        )
        return

    if warnings or skips:
        problem_rows = warnings + skips
        details = "; ".join(
            f"{row['component']}:{row['target']} {row['status']} {row['message']}"
            for row in problem_rows
        )
        yield Result(
            state=State.WARN,
            summary=f"{len(problem_rows)} collection warning/skipped step(s)",
            details=details,
        )
        return

    yield Result(
        state=State.OK,
        summary=f"{len(section)} collection step(s) OK",
    )

agent_section_arcgis_collection_status = AgentSection(
    name="arcgis_collection_status",
    parse_function=parse_arcgis_collection_status,
)

check_plugin_arcgis_collection_status = CheckPlugin(
    name="arcgis_collection_status",
    service_name="ArcGIS Collection Status",
    discovery_function=discover_arcgis_collection_status,
    check_function=check_arcgis_collection_status,
)