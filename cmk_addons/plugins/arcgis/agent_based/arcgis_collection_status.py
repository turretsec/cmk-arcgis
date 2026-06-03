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
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    CollectionStatusEntry,
    SectionCollectionStatus,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
    worst_state,
)

def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_COLLECTION_STATUS_PARAMS, key)


DEFAULT_COLLECTION_STATUS_PARAMS = {
    "warning_state": "warn",
    "skipped_state": "warn",
    "error_state": "crit",
    "unknown_state": "unknown",
}


def _state_for_collection_status(
    status: str,
    params: Mapping[str, Any],
) -> State:
    normalized = status.strip().upper()

    if normalized in {"OK", "SUCCESS"}:
        return State.OK

    if normalized in {"WARN", "WARNING"}:
        return state_from_param(_param_str(params, "warning_state"))

    if normalized in {"SKIP", "SKIPPED"}:
        return state_from_param(_param_str(params, "skipped_state"))

    if normalized in {"ERROR", "FAILURE", "FAILED"}:
        return state_from_param(_param_str(params, "error_state"))

    return state_from_param(_param_str(params, "unknown_state"))


def _entry_detail(entry: CollectionStatusEntry) -> str:
    parts = [
        f"{entry.component}:{entry.target}",
        entry.status,
    ]

    if entry.message:
        parts.append(entry.message)

    return " ".join(parts)


def parse_arcgis_collection_status(string_table: StringTable) -> SectionCollectionStatus:
    entries: list[CollectionStatusEntry] = []

    for section in parse_json_rows(string_table, SectionCollectionStatus):
        entries.extend(section.entries)

    return SectionCollectionStatus(entries=entries)


def discover_arcgis_collection_status(section: SectionCollectionStatus) -> DiscoveryResult:
    if section.entries:
        yield Service()


def check_arcgis_collection_status(
    params: Mapping[str, Any],
    section: SectionCollectionStatus,
) -> CheckResult:
    if not section.entries:
        yield Result(
            state=state_from_param(_param_str(params, "unknown_state")),
            summary="No collection status found",
        )
        return

    entry_states = [
        _state_for_collection_status(entry.status, params)
        for entry in section.entries
    ]

    final_state = worst_state(*entry_states)

    problem_entries = [
        entry
        for entry, state in zip(section.entries, entry_states)
        if state != State.OK
    ]

    if not problem_entries:
        yield Result(
            state=State.OK,
            summary=f"{len(section.entries)} collection step(s) OK",
        )
        return

    errors = [
        entry for entry in section.entries
        if entry.status.strip().upper() in {"ERROR", "FAILURE", "FAILED"}
    ]
    warnings = [
        entry for entry in section.entries
        if entry.status.strip().upper() in {"WARN", "WARNING"}
    ]
    skips = [
        entry for entry in section.entries
        if entry.status.strip().upper() in {"SKIP", "SKIPPED"}
    ]
    unknowns = [
        entry for entry in section.entries
        if entry.status.strip().upper()
        not in {"OK", "SUCCESS", "WARN", "WARNING", "SKIP", "SKIPPED", "ERROR", "FAILURE", "FAILED"}
    ]

    summary_parts = []
    if errors:
        summary_parts.append(f"{len(errors)} error(s)")
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s)")
    if skips:
        summary_parts.append(f"{len(skips)} skipped step(s)")
    if unknowns:
        summary_parts.append(f"{len(unknowns)} unknown status step(s)")

    yield Result(
        state=final_state,
        summary="Collection status: " + ", ".join(summary_parts),
        details="; ".join(_entry_detail(entry) for entry in problem_entries),
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
    check_default_parameters=DEFAULT_COLLECTION_STATUS_PARAMS,
    check_ruleset_name="arcgis_collection_status",
)