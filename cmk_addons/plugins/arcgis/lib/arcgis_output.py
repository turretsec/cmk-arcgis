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
    SectionArcGISServices,
    SectionPortalFederation,
    SectionPortalHealth,
    SectionPortalIndexer,
    SectionPortalLicense,
    SectionServerLicense,
    ServerLicenseEntry,
)


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
