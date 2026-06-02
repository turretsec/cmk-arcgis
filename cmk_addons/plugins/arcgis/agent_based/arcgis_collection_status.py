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
    CollectionStatusEntry,
    SectionCollectionStatus,
)


def parse_arcgis_collection_status(string_table: StringTable) -> SectionCollectionStatus:
    entries: list[CollectionStatusEntry] = []

    for section in parse_json_rows(string_table, SectionCollectionStatus):
        entries.extend(section.entries)

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
        yield Result(
            state=State.CRIT,
            summary=f"{len(errors)} collection error(s)",
            details="; ".join(
                f"{entry.component}:{entry.target} {entry.message}" for entry in errors
            ),
        )
        return

    if warnings or skips:
        problem_entries = warnings + skips
        yield Result(
            state=State.WARN,
            summary=f"{len(problem_entries)} collection warning/skipped step(s)",
            details="; ".join(
                f"{entry.component}:{entry.target} {entry.status} {entry.message}"
                for entry in problem_entries
            ),
        )
        return

    yield Result(state=State.OK, summary=f"{len(section.entries)} collection step(s) OK")


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
