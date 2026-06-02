import json
import sys
import time
from typing import Any

from pydantic import BaseModel

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    PortalLicenseEntry,
    PortalLicenseSummary,
    SectionPortalLicense,
    SectionServerLicense,
    ServerLicenseEntry,
    SectionPortalHealth,
    SectionPortalIndexer,
    PortalIndexCount,
    SectionPortalFederation,
    PortalFederatedServerStatus,
    SectionArcGISServices,
    ArcGISServiceState,
    SectionArcGISServerMachines,
    ArcGISServerMachineState,
    SectionArcGISLogSettings,
)

### JSON output

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

    for kind, key in [
        ("userType", "userTypes"),
        ("appBundle", "appBundles"),
        ("app", "apps"),
        ("extension", "extensions"),
    ]:
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
    return SectionPortalHealth(
        status=status,
        role=role or "standalone",
    )

def portal_indexer_section(indexer_data: dict) -> SectionPortalIndexer:
    indexes: list[PortalIndexCount] = []

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

    return SectionPortalIndexer(
        indexes=indexes,
        sync_status=sync_status,
    )

def portal_federation_section(validation_data: dict) -> SectionPortalFederation:
    servers: list[PortalFederatedServerStatus] = []

    for server in validation_data.get("serversStatus", []):
        servers.append(
            PortalFederatedServerStatus(
                admin_url=server.get("adminUrl", "unknown"),
                status=server.get("status", "unknown"),
            )
        )

    return SectionPortalFederation(
        servers=servers,
        federation_status=validation_data.get("federationStatus", "unknown"),
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

def log_settings_section(settings: dict) -> SectionArcGISLogSettings:
    level = (
        settings.get("logLevel")
        or settings.get("level")
        or settings.get("loglevel")
        or "UNKNOWN"
    )

    max_age = (
        settings.get("maxLogFileAge")
        or settings.get("maxLogAgeDays")
    )

    log_dir = (
        settings.get("logDir")
        or settings.get("logDirectory")
    )

    return SectionArcGISLogSettings(
        level=str(level),
        max_log_file_age=int(max_age) if max_age is not None else None,
        log_dir=str(log_dir) if log_dir else None,
    )
### Plain text

def output_section(
    section_name: str,
    lines: list[str],
    cache_interval: int | None = None,
) -> None:
    if cache_interval:
        print(f"<<<{section_name}:cached({int(time.time())},{cache_interval})>>>")
    else:
        print(f"<<<{section_name}>>>")
    for line in lines:
        print(line)

def output_piggyback(hostname: str,
    section_name: str,
    lines: list[str],
    cache_interval: int | None = None
) -> None:
    print(f"<<<<{hostname}>>>>")
    output_section(section_name, lines, cache_interval)
    print("<<<<>>>>")

def _safe_text(value: object) -> str:
    return str(value).replace("\n", " ").replace(" ", "_") if value is not None else ""

# def portal_license_lines(license_data: dict) -> list[str]:
#     lines = []

#     lines.append(
#         "summary "
#         f"{license_data.get('currentRegisteredMembers', 0)} "
#         f"{license_data.get('maximumRegisteredMembers', 0)} "
#         f"{license_data.get('version', 'unknown')}"
#     )

#     for user_type in license_data.get("userTypes", []):
#         lines.append(
#             "userType "
#             f"{user_type.get('id', 'unknown')} "
#             f"{user_type.get('currentRegisteredMembers', 0)} "
#             f"{user_type.get('maximumRegisteredMembers', 0)} "
#             f"{user_type.get('expiration', 0)}"
#         )

#     for app_bundle in license_data.get("appBundles", []):
#         lines.append(
#             "appBundle "
#             f"{app_bundle.get('id', 'unknown')} "
#             f"{app_bundle.get('currentRegisteredMembers', 0)} "
#             f"{app_bundle.get('maximumRegisteredMembers', 0)} "
#             f"{app_bundle.get('expiration', 0)}"
#         )

#     for app in license_data.get("apps", []):
#         lines.append(
#             "app "
#             f"{app.get('id', 'unknown')} "
#             f"{app.get('currentRegisteredMembers', 0)} "
#             f"{app.get('maximumRegisteredMembers', 0)} "
#             f"{app.get('expiration', 0)}"
#         )

#     for extension in license_data.get("extensions", []):
#         lines.append(
#             "extension "
#             f"{extension.get('id', 'unknown')} "
#             f"{extension.get('currentRegisteredMembers', 0)} "
#             f"{extension.get('maximumRegisteredMembers', 0)} "
#             f"{extension.get('expiration', 0)}"
#         )

#     return lines

# def server_license_lines(license_data: dict) -> list[str]:
#     lines: list[str] = []

#     edition = license_data.get("edition")
#     if edition:
#         lines.append(
#             "edition "
#             f"{_safe_text(edition.get('name'))} "
#             f"{_safe_text(edition.get('version'))} "
#             f"{str(edition.get('canExpire', False)).lower()} "
#             f"{edition.get('expiration', 0)} "
#             f"{_safe_text(edition.get('featureName'))}"
#         )

#     level = license_data.get("level")
#     if level:
#         lines.append(
#             "level "
#             f"{_safe_text(level.get('name'))} "
#             f"{_safe_text(level.get('version'))} "
#             f"{str(level.get('canExpire', False)).lower()} "
#             f"{level.get('expiration', 0)}"
#         )

#     datafeature = license_data.get("datafeature")
#     if datafeature:
#         lines.append(
#             "datafeature "
#             f"{_safe_text(datafeature.get('name'))} "
#             f"{_safe_text(datafeature.get('version'))} "
#             f"{str(datafeature.get('canExpire', False)).lower()} "
#             f"{datafeature.get('expiration', 0)} "
#             f"{_safe_text(datafeature.get('ecpCode'))}"
#         )

#     for extension in license_data.get("extensions", []):
#         lines.append(
#             "extension "
#             f"{_safe_text(extension.get('name'))} "
#             f"{_safe_text(extension.get('version'))} "
#             f"{str(extension.get('canExpire', False)).lower()} "
#             f"{extension.get('expiration', 0)}"
#         )

#     for feature in license_data.get("features", []):
#         lines.append(
#             "feature "
#             f"{_safe_text(feature.get('name'))} "
#             f"{_safe_text(feature.get('displayName'))} "
#             f"{feature.get('coreCount', 0)} "
#             f"{_safe_text(feature.get('version'))} "
#             f"{str(feature.get('canExpire', False)).lower()} "
#             f"{feature.get('expiration', 0)} "
#             f"{str(feature.get('isValid', True)).lower()}"
#         )

#     return lines

# def portal_indexer_lines(response: dict) -> list[str]:
#     lines: list[str] = []
#     for index in response.get("indexes", []):
#         lines.append(f"{index['name']} {index.get('databaseCount', 0)} {index.get('indexCount', 0)}")
#     lines.append(f"syncStatus {response.get('syncStatus', False)}")
#     return lines

# def portal_validate_federation_lines(response: dict) -> list[str]:
#     #print(f"Federation validation response: {response}")
#     federation_status = response.get("status", "error")
#     #print(f"Parsed federation status: {federation_status}")
#     lines = []
#     #print(f"Processing serversStatus: {response.get('serversStatus', [])}")
#     for server in response.get("serversStatus", []):
#         lines.append(f"{server['adminUrl']} {server.get('status', 'error')}")
#     lines.append(f"federationStatus {federation_status}")
#     #print(f"Parsed federation status lines: {lines}")
#     return lines

# def log_settings_lines(settings: dict) -> list[str]:
#     lines: list[str] = []

#     level = (
#         settings.get("logLevel")
#         or settings.get("log level")
#         or settings.get("level")
#         or settings.get("loglevel")
#         or "UNKNOWN"
#     )

#     lines.append(f"level {level}")

#     max_age = (
#         settings.get("maxLogFileAge")
#         or settings.get("max log file age")
#         or settings.get("maxLogAgeDays")
#     )

#     if max_age is not None:
#         lines.append(f"maxLogFileAge {max_age}")

#     log_dir = (
#         settings.get("logDir")
#         or settings.get("log dir")
#         or settings.get("logDirectory")
#     )

#     if log_dir:
#         lines.append(f"logDir {str(log_dir).replace(' ', '_')}")

#     return lines