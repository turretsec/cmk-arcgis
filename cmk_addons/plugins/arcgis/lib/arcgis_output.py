import json
import sys
import time
from typing import Any

from pydantic import BaseModel

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    ArcGISServerMachineState,
    ArcGISServiceState,
    PortalFederatedServerStatus,
    PortalIndexCount,
    PortalLicenseEntry,
    PortalLicenseSummary,
    SectionArcGISLogSettings,
    SectionArcGISServerMachines,
    SectionArcGISServiceStats,
    SectionArcGISServices,
    SectionPortalFederation,
    SectionPortalHealth,
    SectionPortalIndexer,
    SectionPortalLicense,
    SectionServerLicense,
    ServerLicenseEntry,
    ServiceStatsEntry,
)


WINDOW_SECONDS: dict[str, int] = {
    "LAST_HOUR": 3_600,
    "LAST_DAY": 86_400,
    "LAST_WEEK": 604_800,
    "LAST_MONTH": 2_592_000,
}


def _json_payload(payload: Any) -> str:
    if isinstance(payload, BaseModel):
        return payload.model_dump_json()

    return json.dumps(payload, separators=(",", ":"))


def output_json_section(
    section_name: str,
    payload: Any,
    cache_interval: int | None = None,
) -> None:
    if cache_interval is not None:
        sys.stdout.write(
            f"<<<{section_name}:sep(0):cached({int(time.time())},{cache_interval})>>>\n"
        )
    else:
        sys.stdout.write(f"<<<{section_name}:sep(0)>>>\n")

    sys.stdout.write(_json_payload(payload))
    sys.stdout.write("\n")


def output_json_piggyback(
    hostname: str,
    section_name: str,
    payload: Any,
    cache_interval: int | None = None,
) -> None:
    sys.stdout.write(f"<<<<{hostname}>>>>\n")
    output_json_section(section_name, payload, cache_interval)
    sys.stdout.write("<<<<>>>>\n")


def portal_license_section(license_data: dict) -> SectionPortalLicense:
    summary = PortalLicenseSummary(
        current=license_data.get("currentRegisteredMembers", 0),
        maximum=license_data.get("maximumRegisteredMembers", 0),
        version=license_data.get("version", "unknown"),
    )

    items: list[PortalLicenseEntry] = []

    for kind, key in (
        ("userType", "userTypes"),
        ("appBundle", "appBundles"),
        ("app", "apps"),
        ("extension", "extensions"),
    ):
        for item in license_data.get(key, []):
            items.append(
                PortalLicenseEntry(
                    kind=kind,
                    id=item.get("id", "unknown"),
                    current=item.get("currentRegisteredMembers", 0),
                    maximum=item.get("maximumRegisteredMembers", 0),
                    expiration=item.get("expiration", 0),
                )
            )

    return SectionPortalLicense(summary=summary, items=items)


def server_license_section(license_data: dict) -> SectionServerLicense:
    entries: list[ServerLicenseEntry] = []

    edition = license_data.get("edition")
    if edition:
        entries.append(
            ServerLicenseEntry(
                kind="edition",
                name=edition.get("name", "unknown"),
                version=edition.get("version", "unknown"),
                can_expire=bool(edition.get("canExpire", False)),
                expiration=int(edition.get("expiration", 0) or 0),
                extra=edition.get("featureName", ""),
            )
        )

    level = license_data.get("level")
    if level:
        entries.append(
            ServerLicenseEntry(
                kind="level",
                name=level.get("name", "unknown"),
                version=level.get("version", "unknown"),
                can_expire=bool(level.get("canExpire", False)),
                expiration=int(level.get("expiration", 0) or 0),
            )
        )

    datafeature = license_data.get("datafeature")
    if datafeature:
        entries.append(
            ServerLicenseEntry(
                kind="datafeature",
                name=datafeature.get("name", "unknown"),
                version=datafeature.get("version", "unknown"),
                can_expire=bool(datafeature.get("canExpire", False)),
                expiration=int(datafeature.get("expiration", 0) or 0),
                extra=datafeature.get("ecpCode", ""),
            )
        )

    for extension in license_data.get("extensions", []):
        entries.append(
            ServerLicenseEntry(
                kind="extension",
                name=extension.get("name", "unknown"),
                version=extension.get("version", "unknown"),
                can_expire=bool(extension.get("canExpire", False)),
                expiration=int(extension.get("expiration", 0) or 0),
            )
        )

    for feature in license_data.get("features", []):
        entries.append(
            ServerLicenseEntry(
                kind="feature",
                name=feature.get("name", "unknown"),
                display_name=feature.get("displayName"),
                core_count=int(feature.get("coreCount", 0) or 0),
                version=feature.get("version", "unknown"),
                can_expire=bool(feature.get("canExpire", False)),
                expiration=int(feature.get("expiration", 0) or 0),
                is_valid=bool(feature.get("isValid", True)),
            )
        )

    return SectionServerLicense(entries=entries)


def portal_health_section(status: str, role: str) -> SectionPortalHealth:
    return SectionPortalHealth(status=status, role=role or "standalone")


def portal_indexer_section(indexer_data: dict) -> SectionPortalIndexer:
    indexes: list[PortalIndexCount] = []

    # Native ArcGIS shape:
    # {"indexes": [{"name": "users", "databaseCount": 1, "indexCount": 1}], ...}
    for index in indexer_data.get("indexes", []):
        indexes.append(
            PortalIndexCount(
                name=index.get("name", "unknown"),
                database_count=int(index.get("databaseCount", 0) or 0),
                index_count=int(index.get("indexCount", 0) or 0),
            )
        )

    # Defensive fallback for already-normalized dict shapes.
    if not indexes:
        for name in ("users", "groups", "items"):
            value = indexer_data.get(name)

            if isinstance(value, dict):
                database_count = int(
                    value.get("databaseCount")
                    or value.get("database_count")
                    or value.get("dbCount")
                    or 0
                )
                index_count = int(
                    value.get("indexCount")
                    or value.get("index_count")
                    or value.get("idxCount")
                    or 0
                )
            elif isinstance(value, (list, tuple)) and len(value) >= 2:
                database_count = int(value[0])
                index_count = int(value[1])
            else:
                continue

            indexes.append(
                PortalIndexCount(
                    name=name,
                    database_count=database_count,
                    index_count=index_count,
                )
            )

    sync_status_raw = indexer_data.get("syncStatus")
    if isinstance(sync_status_raw, str):
        sync_status = sync_status_raw.strip().lower() == "true"
    elif sync_status_raw is None:
        sync_status = None
    else:
        sync_status = bool(sync_status_raw)

    return SectionPortalIndexer(indexes=indexes, sync_status=sync_status)


def portal_federation_section(validation_data: dict) -> SectionPortalFederation:
    servers = [
        PortalFederatedServerStatus(
            admin_url=server.get("adminUrl", "unknown"),
            status=server.get("status", "unknown"),
        )
        for server in validation_data.get("serversStatus", [])
    ]

    return SectionPortalFederation(
        servers=servers,
        federation_status=(
            validation_data.get("federationStatus")
            or validation_data.get("status")
            or "unknown"
        ),
    )


def arcgis_services_section(
    statuses: dict[str, dict[str, str]],
) -> SectionArcGISServices:
    return SectionArcGISServices(
        services=[
            ArcGISServiceState(
                name=name,
                configured_state=states.get("configuredState", "UNKNOWN"),
                realtime_state=states.get("realTimeState", "UNKNOWN"),
            )
            for name, states in statuses.items()
        ]
    )


def arcgis_server_machines_section(
    machine_statuses: list[dict[str, str]],
) -> SectionArcGISServerMachines:
    return SectionArcGISServerMachines(
        machines=[
            ArcGISServerMachineState(
                name=machine["name"],
                configured_state=machine.get("configured_state", "UNKNOWN"),
                realtime_state=machine.get("realtime_state", "UNKNOWN"),
            )
            for machine in machine_statuses
        ]
    )


def log_settings_section(settings_response: dict) -> SectionArcGISLogSettings:
    settings = settings_response.get("settings", settings_response)

    level = (
        settings.get("logLevel")
        or settings.get("log level")
        or settings.get("level")
        or settings.get("loglevel")
        or "UNKNOWN"
    )
    max_age = (
        settings.get("maxLogFileAge")
        or settings.get("max log file age")
        or settings.get("maxLogAgeDays")
    )
    log_dir = settings.get("logDir") or settings.get("log dir") or settings.get("logDirectory")

    return SectionArcGISLogSettings(
        level=str(level),
        max_log_file_age=int(max_age) if max_age is not None else None,
        log_dir=str(log_dir) if log_dir else None,
    )

# Service statistics aggregation
 
def _normalize_resource_uri(uri: str) -> str:
    """Strip the leading 'services/' prefix so URIs align with arcgis_services items.
 
    Examples:
        services/MyService.MapServer  ->  MyService.MapServer
        services/Folder/Svc.GPServer  ->  Folder/Svc.GPServer
    """
    prefix = "services/"
    if uri.startswith(prefix):
        return uri[len(prefix):]
    return uri
 
 
def _has_any_data(data: list) -> bool:
    """Return True when the metric has at least one non-null time slice."""
    return any(value is not None for value in data)


def _sum_data(data: list) -> int:
    """Sum all non-null values."""
    return sum(int(value) for value in data if value is not None)


def _weighted_mean_data(values: list, weights: list) -> float | None:
    """Return request-count-weighted mean across time slices.

    ArcGIS usage reports return averages per time slice. A plain mean of those
    slices gives tiny quiet slices the same weight as busy slices, so use
    RequestCount as the weight.
    """
    weighted_total = 0.0
    total_weight = 0.0

    for value, weight in zip(values, weights):
        if value is None or weight is None:
            continue

        weight_float = float(weight)
        if weight_float <= 0:
            continue

        weighted_total += float(value) * weight_float
        total_weight += weight_float

    if total_weight <= 0:
        return None

    return weighted_total / total_weight


def _max_data(data: list) -> float | None:
    """Max of non-null values; returns None when every slice is null."""
    values = [float(value) for value in data if value is not None]
    if not values:
        return None
    return max(values)
 
def arcgis_service_stats_section(
    report_data: dict,
    since: str,
) -> SectionArcGISServiceStats:
    """Aggregate a usage-report API response into per-service stats entries.
 
    The usage report returns time-sliced data for each (service, metric) pair.
    We collapse the time slices into single scalar values:
      - Counts (RequestCount, RequestsFailed, RequestsTimedOut) -> sum
      - Averages (AvgResponseTime, AvgWaitTime)                 -> request-count-weighted mean
      - Maxima  (MaxResponseTime, MaxWaitTime)                  -> max of non-null slices
      - ServiceRunningInstancesMax                              -> max of non-null slices
    """
    window_seconds = WINDOW_SECONDS.get(since, WINDOW_SECONDS["LAST_DAY"])
 
    report = report_data.get("report", {})
 
    # report-data is a list of query results; each query result is a list of
    # {resourceURI, metric-type, data} objects.  We use a single query so
    # report-data[0] has everything, but we flatten all queries defensively.
    all_entries: list[dict] = []
    for query_result in report.get("report-data", []):
        if isinstance(query_result, list):
            all_entries.extend(query_result)
 
    # Group metric data by normalized service name.
    by_service: dict[str, dict[str, list]] = {}
    for entry in all_entries:
        uri = entry.get("resourceURI", "")
        metric = entry.get("metric-type", "")
        data = entry.get("data", [])
        service_name = _normalize_resource_uri(uri)
        by_service.setdefault(service_name, {})[metric] = data
 
    services: list[ServiceStatsEntry] = []
    for service_name, metrics in by_service.items():
        request_count_data = metrics.get("RequestCount", [])
        if not _has_any_data(request_count_data):
            # If RequestCount is entirely null/missing, do not invent zero-traffic stats.
            # The check will fall back to state-only output for this service.
            continue

        request_count = _sum_data(request_count_data)
        failed_requests = _sum_data(metrics.get("RequestsFailed", []))
        timed_out_requests = _sum_data(metrics.get("RequestsTimedOut", []))

        avg_response_time_ms = _weighted_mean_data(
            metrics.get("RequestAvgResponseTime", []),
            request_count_data,
        )
        max_response_time_ms = _max_data(metrics.get("RequestMaxResponseTime", []))
        avg_wait_time_ms = _weighted_mean_data(
            metrics.get("RequestAvgWaitTime", []),
            request_count_data,
        )
        max_wait_time_ms = _max_data(metrics.get("RequestMaxWaitTime", []))
 
        max_instances_raw = _max_data(metrics.get("ServiceRunningInstancesMax", []))
        max_running_instances = int(max_instances_raw) if max_instances_raw is not None else None
 
        services.append(
            ServiceStatsEntry(
                service_name=service_name,
                window_seconds=window_seconds,
                request_count=request_count,
                failed_requests=failed_requests,
                timed_out_requests=timed_out_requests,
                avg_response_time_ms=avg_response_time_ms,
                max_response_time_ms=max_response_time_ms,
                avg_wait_time_ms=avg_wait_time_ms,
                max_wait_time_ms=max_wait_time_ms,
                max_running_instances=max_running_instances,
            )
        )
 
    return SectionArcGISServiceStats(services=services)
