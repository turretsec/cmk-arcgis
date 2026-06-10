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
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    ArcGISServiceState,
    SectionArcGISServiceStats,
    SectionArcGISServices,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
    worst_state,
)


DEFAULT_SERVICE_PARAMS: Mapping[str, Any] = {
    # --- State handling ---
    "started_not_started_state": "crit",
    "stopped_stopped_state": "ok",
    "stopped_not_stopped_state": "warn",
    "transitional_state": "warn",
    "failed_state": "crit",
    "unknown_state": "unknown",

    # --- Usage statistics thresholds ---
    "failure_rate_warn": 5.0,
    "failure_rate_crit": 20.0,
    "failure_rate_min_requests": 20,
    "timeout_rate_warn": 5.0,
    "timeout_rate_crit": 20.0,
    "timeout_rate_min_requests": 20,
}


def _param_str(params: Mapping[str, Any], key: str) -> str:
    return param_str(params, DEFAULT_SERVICE_PARAMS, key)


def _int_param(params: Mapping[str, Any], key: str) -> int:
    return int(params.get(key, DEFAULT_SERVICE_PARAMS[key]))


def _rate_levels(
    params: Mapping[str, Any],
    warn_key: str,
    crit_key: str,
) -> tuple[float, float]:
    warn = float(params.get(warn_key, DEFAULT_SERVICE_PARAMS.get(warn_key, 5.0)))
    crit = float(params.get(crit_key, DEFAULT_SERVICE_PARAMS.get(crit_key, 20.0)))
    return warn, crit


def _time_levels(
    params: Mapping[str, Any],
    warn_key: str,
    crit_key: str,
) -> tuple[float, float] | None:
    warn = params.get(warn_key)
    crit = params.get(crit_key)
    if warn is not None and crit is not None:
        return float(warn), float(crit)
    return None


def _state_for_value(
    value: float,
    warn: float | None,
    crit: float | None,
) -> State:
    if crit is not None and value >= crit:
        return State.CRIT
    if warn is not None and value >= warn:
        return State.WARN
    return State.OK


# ---------------------------------------------------------------------------
# Parse functions
# ---------------------------------------------------------------------------


def parse_arcgis_services(string_table: StringTable) -> SectionArcGISServices:
    services: list[ArcGISServiceState] = []
    for section in parse_json_rows(string_table, SectionArcGISServices):
        services.extend(section.services)
    return SectionArcGISServices(services=services)


def parse_arcgis_service_stats(string_table: StringTable) -> SectionArcGISServiceStats:
    services = []
    for section in parse_json_rows(string_table, SectionArcGISServiceStats):
        services.extend(section.services)
    return SectionArcGISServiceStats(services=services)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_arcgis_services(
    section_arcgis_services: SectionArcGISServices | None,
    section_arcgis_service_stats: SectionArcGISServiceStats | None,
) -> DiscoveryResult:
    # Discovery is driven by the state section only. Check works with or without the stats section
    if section_arcgis_services is None:
        return
    for service in section_arcgis_services.services:
        yield Service(item=service.name)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _evaluate_state(
    item: str,
    params: Mapping[str, Any],
    section: SectionArcGISServices,
) -> tuple[State, str]:
    """Return (state, summary) for the service configured/realtime state."""
    services_by_name = {svc.name: svc for svc in section.services}

    service = services_by_name.get(item)
    if service is None:
        return State.UNKNOWN, "Service missing from agent output"

    configured = service.configured_state.strip().upper()
    realtime = service.realtime_state.strip().upper()

    if configured == "STARTED" and realtime == "STARTED":
        return State.OK, "Service is running"

    if configured == "STOPPED" and realtime == "STOPPED":
        return (
            state_from_param(_param_str(params, "stopped_stopped_state")),
            "Service is intentionally stopped",
        )

    if configured == "STARTED" and realtime != "STARTED":
        return (
            state_from_param(_param_str(params, "started_not_started_state")),
            f"Configured STARTED but realtime state is {realtime}",
        )

    if configured == "STOPPED" and realtime != "STOPPED":
        return (
            state_from_param(_param_str(params, "stopped_not_stopped_state")),
            f"Configured STOPPED but realtime state is {realtime}",
        )

    if realtime in {"STARTING", "STOPPING"}:
        return (
            state_from_param(_param_str(params, "transitional_state")),
            f"Service is {realtime}",
        )

    if realtime in {"FAILED", "FAILURE"}:
        return (
            state_from_param(_param_str(params, "failed_state")),
            f"Service is {realtime}",
        )

    return (
        state_from_param(_param_str(params, "unknown_state")),
        f"Configured {configured}, realtime {realtime}",
    )


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


def check_arcgis_services(
    item: str,
    params: Mapping[str, Any],
    section_arcgis_services: SectionArcGISServices | None,
    section_arcgis_service_stats: SectionArcGISServiceStats | None,
) -> CheckResult:
    # ---- State ----
    if section_arcgis_services is None:
        yield Result(state=State.UNKNOWN, summary="Service section missing from agent output")
        return

    state_state, state_summary = _evaluate_state(item, params, section_arcgis_services)

    # ---- Stats (optional) ----
    if section_arcgis_service_stats is None:
        yield Result(state=state_state, summary=state_summary)
        return

    by_name = {s.service_name: s for s in section_arcgis_service_stats.services}
    stats = by_name.get(item)

    if stats is None:
        # Stats section is present but this service had no usage data.
        yield Result(state=state_state, summary=state_summary)
        return

    # ---- Derived values ----
    requests_per_sec = (
        stats.request_count / stats.window_seconds
        if stats.window_seconds > 0
        else 0.0
    )
    failure_rate = (
        stats.failed_requests / stats.request_count * 100.0
        if stats.request_count > 0
        else 0.0
    )
    timeout_rate = (
        stats.timed_out_requests / stats.request_count * 100.0
        if stats.request_count > 0
        else 0.0
    )

    # ---- Threshold evaluation ----
    failure_warn, failure_crit = _rate_levels(params, "failure_rate_warn", "failure_rate_crit")
    timeout_warn, timeout_crit = _rate_levels(params, "timeout_rate_warn", "timeout_rate_crit")
    avg_resp_levels = _time_levels(params, "avg_response_time_warn", "avg_response_time_crit")
    max_resp_levels = _time_levels(params, "max_response_time_warn", "max_response_time_crit")

    failure_min_requests = _int_param(params, "failure_rate_min_requests")
    timeout_min_requests = _int_param(params, "timeout_rate_min_requests")

    stats_states: list[State] = []

    if stats.request_count >= failure_min_requests:
        stats_states.append(_state_for_value(failure_rate, failure_warn, failure_crit))

    if stats.request_count >= timeout_min_requests:
        stats_states.append(_state_for_value(timeout_rate, timeout_warn, timeout_crit))

    if stats.avg_response_time_ms is not None and avg_resp_levels is not None:
        stats_states.append(
            _state_for_value(stats.avg_response_time_ms, avg_resp_levels[0], avg_resp_levels[1])
        )
    if stats.max_response_time_ms is not None and max_resp_levels is not None:
        stats_states.append(
            _state_for_value(stats.max_response_time_ms, max_resp_levels[0], max_resp_levels[1])
        )

    final_state = worst_state(state_state, *stats_states)

    # ---- Summary & details ----
    stats_summary_parts = [
        f"{stats.request_count:,} requests ({requests_per_sec:.3f}/s)",
        f"{stats.failed_requests} failed ({failure_rate:.2f}%)",
        f"{stats.timed_out_requests} timed out ({timeout_rate:.2f}%)",
    ]
    if stats.request_count < failure_min_requests:
        stats_summary_parts.append(
            f"failure threshold ignored below {failure_min_requests} requests"
        )

    if stats.request_count < timeout_min_requests:
        stats_summary_parts.append(
            f"timeout threshold ignored below {timeout_min_requests} requests"
        )
    if stats.avg_response_time_ms is not None:
        stats_summary_parts.append(f"avg resp {stats.avg_response_time_ms:.0f} ms")

    details_lines = [
        f"Requests: {stats.request_count:,}",
        f"Requests/sec: {requests_per_sec:.4f}",
        f"Failed requests: {stats.failed_requests} ({failure_rate:.2f}%)",
        f"Timed-out requests: {stats.timed_out_requests} ({timeout_rate:.2f}%)",
    ]
    if stats.avg_response_time_ms is not None:
        details_lines.append(f"Avg response time: {stats.avg_response_time_ms:.1f} ms")
    if stats.max_response_time_ms is not None:
        details_lines.append(f"Max response time: {stats.max_response_time_ms:.1f} ms")
    if stats.avg_wait_time_ms is not None:
        details_lines.append(f"Avg wait time: {stats.avg_wait_time_ms:.1f} ms")
    if stats.max_wait_time_ms is not None:
        details_lines.append(f"Max wait time: {stats.max_wait_time_ms:.1f} ms")
    if stats.max_running_instances is not None:
        details_lines.append(f"Max running instances: {stats.max_running_instances}")

    yield Result(
        state=final_state,
        summary=f"{state_summary}, {', '.join(stats_summary_parts)}",
        details="\n".join(details_lines),
    )

    # ---- Metrics ----
    yield Metric("arcgis_request_count", float(stats.request_count))
    yield Metric("arcgis_requests_per_second", requests_per_sec)
    yield Metric("arcgis_failed_requests", float(stats.failed_requests))
    yield Metric(
        "arcgis_failure_rate",
        failure_rate,
        levels=(failure_warn, failure_crit),
        boundaries=(0.0, 100.0),
    )
    yield Metric("arcgis_timed_out_requests", float(stats.timed_out_requests))
    yield Metric(
        "arcgis_timeout_rate",
        timeout_rate,
        levels=(timeout_warn, timeout_crit),
        boundaries=(0.0, 100.0),
    )
    if stats.avg_response_time_ms is not None:
        yield Metric(
            "arcgis_avg_response_time",
            stats.avg_response_time_ms,
            levels=avg_resp_levels,
        )
    if stats.max_response_time_ms is not None:
        yield Metric(
            "arcgis_max_response_time",
            stats.max_response_time_ms,
            levels=max_resp_levels,
        )
    if stats.avg_wait_time_ms is not None:
        yield Metric("arcgis_avg_wait_time", stats.avg_wait_time_ms)
    if stats.max_wait_time_ms is not None:
        yield Metric("arcgis_max_wait_time", stats.max_wait_time_ms)
    if stats.max_running_instances is not None:
        yield Metric("arcgis_max_running_instances", float(stats.max_running_instances))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

agent_section_arcgis_services = AgentSection(
    name="arcgis_services",
    parse_function=parse_arcgis_services,
)

# The stats section is produced by a separate agent collection pass
agent_section_arcgis_service_stats = AgentSection(
    name="arcgis_service_stats",
    parse_function=parse_arcgis_service_stats,
)

check_plugin_arcgis_services = CheckPlugin(
    name="arcgis_services",
    sections=["arcgis_services", "arcgis_service_stats"],
    service_name="ArcGIS Service %s",
    discovery_function=discover_arcgis_services,
    check_function=check_arcgis_services,
    check_default_parameters=dict(DEFAULT_SERVICE_PARAMS),
    check_ruleset_name="arcgis_services",
)