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

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_json_rows
from cmk_addons.plugins.arcgis.lib.arcgis_sections import SectionArcGISServerLogs
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import worst_state


DEFAULT_SERVER_LOGS_PARAMS: Mapping[str, Any] = {
    # One SEVERE error in the window is worth surfacing immediately.
    # 10 or more is a cascade or a misconfiguration producing noise.
    "severe_warn": 1,
    "severe_crit": 10,
    # WARNING messages are normally present on healthy servers.
    # 0 = threshold disabled - operators who want to alert on warning
    # counts should set these explicitly via check parameters.
    "warning_warn": 0,
    "warning_crit": 0,
}


def _format_timestamp(time_ms: int) -> str:
    """Convert a millisecond epoch timestamp to a readable UTC string."""
    if time_ms <= 0:
        return "unknown time"
    try:
        dt = datetime.datetime.fromtimestamp(time_ms / 1000, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OSError, OverflowError, ValueError):
        return f"t={time_ms}"


def _threshold_state(value: int, warn: int, crit: int) -> State:
    """Evaluate value against thresholds. 0 for either means disabled."""
    if crit > 0 and value >= crit:
        return State.CRIT
    if warn > 0 and value >= warn:
        return State.WARN
    return State.OK


def parse_arcgis_server_logs(string_table: StringTable) -> SectionArcGISServerLogs:
    for section in parse_json_rows(string_table, SectionArcGISServerLogs):
        return section
    return SectionArcGISServerLogs()


def discover_arcgis_server_logs(section: SectionArcGISServerLogs) -> DiscoveryResult:
    yield Service()


def check_arcgis_server_logs(
    params: Mapping[str, Any],
    section: SectionArcGISServerLogs,
) -> CheckResult:
    severe_warn = int(params.get("severe_warn", DEFAULT_SERVER_LOGS_PARAMS["severe_warn"]))
    severe_crit = int(params.get("severe_crit", DEFAULT_SERVER_LOGS_PARAMS["severe_crit"]))
    warning_warn = int(params.get("warning_warn", DEFAULT_SERVER_LOGS_PARAMS["warning_warn"]))
    warning_crit = int(params.get("warning_crit", DEFAULT_SERVER_LOGS_PARAMS["warning_crit"]))

    severe_state = _threshold_state(section.severe_count, severe_warn, severe_crit)
    warning_state = _threshold_state(section.warning_count, warning_warn, warning_crit)
    final_state = worst_state(severe_state, warning_state)

    window = section.window_minutes
    count_prefix = "at least " if section.has_more else ""

    # Metrics - yielded before Result so they're always stored.
    yield Metric(
        "arcgis_server_severe_log_count",
        float(section.severe_count),
        levels=(float(severe_warn), float(severe_crit)) if severe_warn > 0 else None,
    )
    yield Metric(
        "arcgis_server_warning_log_count",
        float(section.warning_count),
        levels=(float(warning_warn), float(warning_crit)) if warning_warn > 0 else None,
    )

    # Summary line
    summary_parts = [
        f"{count_prefix}{section.severe_count} severe",
        f"{count_prefix}{section.warning_count} warnings",
    ]

    if section.ignored_count:
        summary_parts.append(f"{section.ignored_count} ignored")

    summary = f"{', '.join(summary_parts)} (last {section.window_minutes} min)"

    # Details: surface recent SEVERE messages so operators can triage
    # without opening ArcGIS Server Manager.
    details_lines = [summary]

    if section.has_more:
        details_lines.extend(
            [
                "",
                "Log query was truncated before the full time window was read.",
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
            if entry.code:
                source_info += f" (code {entry.code})"
            details_lines.append(f"  {ts}{source_info}: {entry.message}")

    if section.ignored_count:
        details_lines.extend(
            [
                "",
                f"Ignored {section.ignored_count} log entries due to configured filters.",
            ]
        )        

    details = "\n".join(details_lines)

    yield Result(state=final_state, summary=summary, details=details)


agent_section_arcgis_server_logs = AgentSection(
    name="arcgis_server_logs",
    parse_function=parse_arcgis_server_logs,
)

check_plugin_arcgis_server_logs = CheckPlugin(
    name="arcgis_server_logs",
    service_name="ArcGIS Server Logs",
    discovery_function=discover_arcgis_server_logs,
    check_function=check_arcgis_server_logs,
    check_default_parameters=dict(DEFAULT_SERVER_LOGS_PARAMS),
    check_ruleset_name="arcgis_server_logs",
)