import json

from pydantic import ValidationError

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

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    CollectionStatusEntry,
    SectionCollectionStatus,
)

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import (
    looks_like_json_rows,
    raw_section_rows,
)


def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()


def parse_arcgis_collection_status(
    string_table: StringTable,
) -> SectionCollectionStatus:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        entries: list[CollectionStatusEntry] = []

        for raw in raw_rows:
            section = SectionCollectionStatus.model_validate_json(raw)
            entries.extend(section.entries)

        return SectionCollectionStatus(entries=entries)

    # Old text-row fallback
    entries: list[CollectionStatusEntry] = []

    for row in string_table:
        if len(row) < 3:
            continue

        entries.append(
            CollectionStatusEntry(
                component=row[0],
                target=row[1],
                status=row[2],
                message=" ".join(row[3:]) if len(row) > 3 else "",
            )
        )

    return SectionCollectionStatus(entries=entries)

def discover_arcgis_collection_status(section: SectionCollectionStatus) -> DiscoveryResult:
    if section.entries:
        yield Service()

def check_arcgis_collection_status(section: SectionCollectionStatus) -> CheckResult:
    if not section.entries:
        yield Result(state=State.UNKNOWN, summary="No collection status found")
        return

    errors = [entry for entry in section.entries if entry.status.upper() == "ERROR"]
    warnings = [entry for entry in section.entries if entry.status.upper() == "WARN"]
    skips = [entry for entry in section.entries if entry.status.upper() == "SKIP"]

    if errors:
        details = "; ".join(
            f"{entry.component}:{entry.target} {entry.message}"
            for entry in errors
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
            f"{entry.component}:{entry.target} {entry.status} {entry.message}"
            for entry in problem_rows
        )
        yield Result(
            state=State.WARN,
            summary=f"{len(problem_rows)} collection warning/skipped step(s)",
            details=details,
        )
        return

    yield Result(
        state=State.OK,
        summary=f"{len(section.entries)} collection step(s) OK",
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