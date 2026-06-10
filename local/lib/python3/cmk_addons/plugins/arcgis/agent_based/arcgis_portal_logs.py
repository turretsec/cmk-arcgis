import datetime
from collections.abc import Mapping
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

from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import worst_state
from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_json_rows
from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionArcGISPortalLogs


DEFAULT_PORTAL_LOGS_PARAMS: Mapping[str, Any] = {
    "severe_warn": 1,
    "severe_crit": 10,
    "warning_warn": 0,
    "warning_crit": 0,
}


def _format_timestamp(time_ms: int) -> str:
    if time_ms <= 0:
        return "unknown time"
    try:
        dt = datetime.datetime.fromtimestamp(time_ms / 1000, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, OverflowError, ValueError):
        return f"t={time_ms}"


def _threshold_state(value: int, warn: int, crit: int) -> State:
    if crit > 0 and value >= crit:
        return State.CRIT
    if warn > 0 and value >= warn:
        return State.WARN
    return State.OK


def parse_arcgis_portal_logs(string_table: StringTable) -> SectionArcGISPortalLogs:
    for section in parse_json_rows(string_table, SectionArcGISPortalLogs):
        return section
    return SectionArcGISPortalLogs()


def discover_arcgis_portal_logs(section: SectionArcGISPortalLogs) -> DiscoveryResult:
    yield Service()


def check_arcgis_portal_logs(
    params: Mapping[str, Any],
    section: SectionArcGISPortalLogs,
) -> CheckResult:
    severe_warn = int(params.get("severe_warn", DEFAULT_PORTAL_LOGS_PARAMS["severe_warn"]))
    severe_crit = int(params.get("severe_crit", DEFAULT_PORTAL_LOGS_PARAMS["severe_crit"]))
    warning_warn = int(params.get("warning_warn", DEFAULT_PORTAL_LOGS_PARAMS["warning_warn"]))
    warning_crit = int(params.get("warning_crit", DEFAULT_PORTAL_LOGS_PARAMS["warning_crit"]))

    severe_state = _threshold_state(section.severe_count, severe_warn, severe_crit)
    warning_state = _threshold_state(section.warning_count, warning_warn, warning_crit)
    final_state = worst_state(severe_state, warning_state)

    yield Metric(
        "arcgis_portal_severe_log_count",
        float(section.severe_count),
        levels=(float(severe_warn), float(severe_crit)) if severe_warn > 0 else None,
    )
    yield Metric(
        "arcgis_portal_warning_log_count",
        float(section.warning_count),
        levels=(float(warning_warn), float(warning_crit)) if warning_warn > 0 else None,
    )

    count_prefix = "at least " if section.has_more else ""

    summary_parts = [
        f"{count_prefix}{section.severe_count} severe",
        f"{count_prefix}{section.warning_count} warnings",
    ]

    if section.ignored_count:
        summary_parts.append(f"{section.ignored_count} ignored")

    summary = f"{', '.join(summary_parts)} (last {section.window_minutes} min)"

    details_lines = [summary]

    if section.has_more:
        details_lines.extend(
            [
                "",
                "Portal log query was truncated before the full time window was read.",
                "Counts should be treated as lower bounds.",
            ]
        )

    if section.recent_severe:
        details_lines.extend(["", "Recent SEVERE errors:"])

        for entry in section.recent_severe:
            ts = _format_timestamp(entry.time_ms)
            source_info = ""
            if entry.machine:
                source_info += f" [{entry.machine}]"
            if entry.source:
                source_info += f" {entry.source}"
            if entry.user:
                source_info += f" user={entry.user}"
            if entry.code:
                source_info += f" (code {entry.code})"
            if entry.request_id:
                source_info += f" request={entry.request_id}"

            details_lines.append(f"  {ts}{source_info}: {entry.message}")

    if section.ignored_count:
        details_lines.extend(
            [
                "",
                f"Ignored {section.ignored_count} log entries due to configured filters.",
            ]
        )

    yield Result(
        state=final_state,
        summary=summary,
        details="\n".join(details_lines),
    )


agent_section_arcgis_portal_logs = AgentSection(
    name="arcgis_portal_logs",
    parse_function=parse_arcgis_portal_logs,
)


check_plugin_arcgis_portal_logs = CheckPlugin(
    name="arcgis_portal_logs",
    service_name="ArcGIS Portal Logs",
    discovery_function=discover_arcgis_portal_logs,
    check_function=check_arcgis_portal_logs,
    check_default_parameters=dict(DEFAULT_PORTAL_LOGS_PARAMS),
    check_ruleset_name="arcgis_portal_logs",
)