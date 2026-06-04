import argparse
import logging
import sys
import urllib3
import re

from cmk_addons.plugins.arcgis.lib.arcgis_client import (
    ArcGISTokenProvider,
    PortalClient,
    ServerClient,
)
from cmk_addons.plugins.arcgis.lib.arcgis_collection import CollectionStatus
from cmk_addons.plugins.arcgis.lib.arcgis_normalize import (
    classify_managed_datastore_response,
    normalize_registered_datastore_validation,
)
from cmk_addons.plugins.arcgis.lib.arcgis_output import (
    arcgis_service_stats_section,
    arcgis_services_section,
    arcgis_server_machines_section,
    log_settings_section,
    output_json_piggyback,
    output_json_section,
    portal_federation_section,
    portal_health_section,
    portal_indexer_section,
    portal_license_section,
    server_license_section,
    server_mode_section,
    web_adaptors_section,
)
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    ManagedDatastoreValidation,
    RegisteredDatastoreValidation,
    SectionManagedDatastoreValidation,
    SectionRegisteredDatastoreValidation,
)

# Logging config
AGENT = "arcgis"
LOGGER = logging.getLogger(f"agent_{AGENT}")


def configure_logging(args: argparse.Namespace) -> None:
    if args.debug or args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format=f"%(levelname)s [{AGENT}]: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def log_collection_error(
    component: str,
    target: str,
    exc: Exception,
) -> None:
    LOGGER.warning(
        "Failed to collect %s for %s: %s",
        component,
        target,
        exc,
    )
    LOGGER.debug(
        "Traceback while collecting %s for %s",
        component,
        target,
        exc_info=True,
    )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc

    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be greater than or equal to 0")

    return parsed


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="CheckMK ArcGIS Enterprise Special Agent")
    parser.add_argument("--username", required=True, help="ArcGIS admin username")
    parser.add_argument("--password-id", required=True, help="Checkmk password store secret ID")
    parser.add_argument("--portal-url", required=True, help="Portal base URL")
    parser.add_argument("--no-verify-ssl", action="store_true")
    parser.add_argument("--token-expiry", type=int, default=60)
    parser.add_argument(
        "--portal-federation-cache",
        type=non_negative_int,
        default=300,
        help="Cache interval in seconds for Portal federation validation. Use 0 to disable.",
    )
    parser.add_argument(
        "--portal-license-cache",
        type=non_negative_int,
        default=3600,
        help="Cache interval in seconds for Portal license data. Use 0 to disable.",
    )
    parser.add_argument(
        "--portal-log-settings-cache",
        type=non_negative_int,
        default=3600,
        help="Cache interval in seconds for Portal log settings. Use 0 to disable.",
    )
    parser.add_argument(
        "--server-machines-cache",
        type=non_negative_int,
        default=300,
        help="Cache interval in seconds for ArcGIS Server machine states. Use 0 to disable.",
    )
    parser.add_argument(
        "--registered-datastores-cache",
        type=non_negative_int,
        default=900,
        help="Cache interval in seconds for registered datastore validation. Use 0 to disable.",
    )
    parser.add_argument(
        "--managed-datastores-cache",
        type=non_negative_int,
        default=900,
        help="Cache interval in seconds for managed datastore validation. Use 0 to disable.",
    )
    parser.add_argument(
        "--server-license-cache",
        type=non_negative_int,
        default=3600,
        help="Cache interval in seconds for ArcGIS Server license data. Use 0 to disable.",
    )
    parser.add_argument(
        "--server-log-settings-cache",
        type=non_negative_int,
        default=3600,
        help="Cache interval in seconds for ArcGIS Server log settings. Use 0 to disable.",
    )
    parser.add_argument(
        "--service-stats-cache",
        type=non_negative_int,
        default=300,
        help="Cache interval in seconds for service usage statistics. Use 0 to disable.",
    )
    parser.add_argument(
        "--service-stats-since",
        choices=["LAST_HOUR", "LAST_DAY", "LAST_WEEK", "LAST_MONTH"],
        default="LAST_HOUR",
        help="Time window for service usage statistics (default: LAST_HOUR).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. Use -v for info, -vv for debug.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging. Equivalent to -vv.",
    )
    parser.add_argument("--no-portal-health", action="store_true")
    parser.add_argument("--no-portal-indexer", action="store_true")
    parser.add_argument("--no-portal-federation", action="store_true")
    parser.add_argument("--no-portal-license", action="store_true")
    parser.add_argument("--no-portal-log-settings", action="store_true")

    parser.add_argument("--no-server-machines", action="store_true")
    parser.add_argument("--no-server-services", action="store_true")
    parser.add_argument("--no-registered-datastores", action="store_true")
    parser.add_argument("--no-managed-datastores", action="store_true")
    parser.add_argument("--no-server-license", action="store_true")
    parser.add_argument("--no-server-log-settings", action="store_true")
    parser.add_argument("--no-service-stats", action="store_true")
    parser.add_argument("--no-server-mode", action="store_true")
    parser.add_argument("--no-web-adaptors", action="store_true")
    parser.add_argument(
        "--web-adaptors-cache",
        type=non_negative_int,
        default=300,
        help="Cache interval in seconds for web adaptor collection. Use 0 to disable.",
    )

    parser.add_argument(
        "--server-include-regex",
        action="append",
        default=[],
        help=(
            "Only collect federated servers whose name, URL, or admin URL matches "
            "this regular expression. Can be specified multiple times."
        ),
    )
    parser.add_argument(
        "--server-exclude-regex",
        action="append",
        default=[],
        help=(
            "Do not collect federated servers whose name, URL, or admin URL matches "
            "this regular expression. Can be specified multiple times. Excludes win over includes."
        ),
    )
    parser.add_argument("hostname", help="Target hostname")
    return parser.parse_args(argv)


def _server_filter_text(server: dict) -> str:
    values = [
        str(server.get("name", "")),
        str(server.get("url", "")),
        str(server.get("adminUrl", "")),
        str(server.get("admin_url", "")),
    ]

    return " ".join(value for value in values if value)


def _matches_any_regex(
    text: str,
    patterns: list[str],
) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def federated_server_is_included(
    server: dict,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> bool:
    text = _server_filter_text(server)

    if exclude_patterns and _matches_any_regex(text, exclude_patterns):
        LOGGER.info("Excluding federated server by exclude regex: %s", text)
        return False

    if include_patterns and not _matches_any_regex(text, include_patterns):
        LOGGER.info(
            "Excluding federated server because it does not match include regex: %s",
            text,
        )
        return False

    return True


def filter_federated_servers(
    servers: list[dict],
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> list[dict]:
    return [
        server
        for server in servers
        if federated_server_is_included(server, include_patterns, exclude_patterns)
    ]


def cache_interval(value: int) -> int | None:
    if value <= 0:
        return None
    return value


def server_collection_enabled(args: argparse.Namespace) -> bool:
    return any(
        [
            not args.no_server_machines,
            not args.no_server_services,
            not args.no_registered_datastores,
            not args.no_managed_datastores,
            not args.no_server_license,
            not args.no_server_log_settings,
            not args.no_service_stats,
            not args.no_server_mode,
            not args.no_web_adaptors,
        ]
    )


def log_disabled_collection(component: str, target: str) -> None:
    LOGGER.info(
        "Skipping %s collection for %s because it is disabled by rule",
        component,
        target,
    )


def hostname_matches_machine(hostname: str, machine_name: str) -> bool:
    """Check if hostname refers to this portal machine.
    Matches exact or FQDN prefix (e.g. 'gisserver' matches 'gisserver.acme.com').
    """
    hostname_lower = hostname.lower()
    machine_lower = machine_name.lower()
    return hostname_lower == machine_lower or machine_lower.startswith(hostname_lower + ".")


def machine_piggyback_host(hostname: str, machine_name: str, all_machine_names: list[str]) -> str:
    """Determine piggyback header for a portal machine.
    Returns empty string when the machine is the queried host itself,
    otherwise returns the lowercased machine name for piggyback.
    """
    if hostname_matches_machine(hostname, machine_name):
        return ""
    hostname_matches_any = any(hostname_matches_machine(hostname, m) for m in all_machine_names)
    if not hostname_matches_any and len(all_machine_names) == 1:
        return ""
    hostname = machine_name.split(".")[0]
    return hostname.lower()


def piggyback_host_from_machine_name(machine_name: str) -> str:
    """Convert ArcGIS machine/FQDN names to Checkmk host names.

    Example:
        GIS-SERVER-01.EXAMPLE.ORG -> gis-server-01
        gis-server-01 -> gis-server-01
    """
    return machine_name.split(".", 1)[0].lower()


def _service_to_resource_uri(service: dict) -> str:
    """Build a usage-report resourceURI from a service dict.

    The resourceURI format expected by the usage report API is:
        services/<ServiceName>.<Type>            (root folder)
        services/<FolderName>/<ServiceName>.<Type>  (sub-folder)
    """
    folder = (service.get("folderName") or "").strip("/")
    name = service["serviceName"]
    svc_type = service["type"]
    if folder:
        return f"services/{folder}/{name}.{svc_type}"
    return f"services/{name}.{svc_type}"


# ---------------------------------------------------------------------------
# Collection functions - Portal
# ---------------------------------------------------------------------------

def collect_portal(
    args,
    portal_client: PortalClient,
    collection: CollectionStatus,
) -> list[dict]:
    if args.no_portal_health:
        log_disabled_collection("portal_health", "portal")
    else:
        try:
            LOGGER.info("Collecting portal machines")
            portal_machines = portal_client.get_portal_machines()
            LOGGER.debug("Portal machines: %s", portal_machines)
            all_machine_names = [
                machine["machineName"]
                for machine in portal_machines
                if machine.get("machineName")
            ]
            for machine in portal_machines:
                machine_name = machine.get("machineName")
                if not machine_name:
                    LOGGER.debug("Skipping portal machine without machineName: %r", machine)
                    continue
                piggyback_host = machine_piggyback_host(
                    args.hostname,
                    machine_name,
                    all_machine_names,
                )
                LOGGER.info(
                    "Collecting portal health for machine %s (piggyback host: '%s')",
                    machine_name,
                    piggyback_host,
                )
                machine_status = portal_client.get_portal_machine_status(machine_name)
                LOGGER.debug("Machine status for %s: %s", machine_name, machine_status)
                role = machine.get("role", "standalone") or "standalone"

                if piggyback_host:
                    output_json_piggyback(
                        piggyback_host,
                        "arcgis_portal_health",
                        portal_health_section(machine_status, role),
                    )
                else:
                    output_json_section(
                        "arcgis_portal_health",
                        portal_health_section(machine_status, role),
                    )

            collection.ok("portal_health", "portal")

        except Exception as e:
            collection.error("portal_health", "portal", e)
            log_collection_error("portal_health", "portal", e)

    if args.no_portal_indexer:
        log_disabled_collection("portal_indexer", "portal")
    else:
        try:
            LOGGER.info("Collecting portal indexer status")
            output_json_section(
                "arcgis_portal_indexer",
                portal_indexer_section(portal_client.get_portal_indexer()),
            )
            collection.ok("portal_indexer", "portal")
        except Exception as e:
            collection.error("portal_indexer", "portal", e)
            log_collection_error("portal_indexer", "portal", e)

    if args.no_portal_federation:
        log_disabled_collection("portal_federation", "portal")
    else:
        try:
            LOGGER.info("Collecting portal federation validation")
            output_json_section(
                "arcgis_portal_federation",
                portal_federation_section(portal_client.validate_federation()),
                cache_interval=cache_interval(args.portal_federation_cache),
            )
            collection.ok("portal_federation", "portal")
        except Exception as e:
            collection.error("portal_federation", "portal", e)
            log_collection_error("portal_federation", "portal", e)

    if args.no_portal_license:
        log_disabled_collection("portal_license", "portal")
    else:
        try:
            LOGGER.info("Collecting portal license")
            output_json_section(
                "arcgis_portal_license",
                portal_license_section(portal_client.get_license()),
                cache_interval=cache_interval(args.portal_license_cache),
            )
            collection.ok("portal_license", "portal")
        except Exception as e:
            collection.error("portal_license", "portal", e)
            log_collection_error("portal_license", "portal", e)

    if args.no_portal_log_settings:
        log_disabled_collection("portal_log_settings", "portal")
    else:
        try:
            LOGGER.info("Collecting portal log settings")
            output_json_section(
                "arcgis_portal_log_settings",
                log_settings_section(portal_client.get_log_settings()),
                cache_interval=cache_interval(args.portal_log_settings_cache),
            )
            collection.ok("portal_log_settings", "portal")
        except Exception as e:
            collection.error("portal_log_settings", "portal", e)
            log_collection_error("portal_log_settings", "portal", e)

    if not server_collection_enabled(args):
        log_disabled_collection("federated_servers", "portal")
        return []

    try:
        LOGGER.info("Collecting portal federated servers")
        federated_servers = portal_client.get_federated_servers()
        LOGGER.debug("Federated servers: %s", federated_servers)
        federated_servers = filter_federated_servers(
            federated_servers,
            args.server_include_regex,
            args.server_exclude_regex,
        )
        LOGGER.debug("Filtered federated servers: %s", federated_servers)
        collection.ok("federated_servers", "portal")
        return federated_servers
    except Exception as e:
        collection.error("federated_servers", "portal", e)
        log_collection_error("federated_servers", "portal", e)
        return []


# ---------------------------------------------------------------------------
# Collection functions - Server
# ---------------------------------------------------------------------------

def collect_server_machines(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> None:
    LOGGER.info("Collecting server machines for %s", server_name)
    machines = server_client.get_machines()
    LOGGER.debug("Server machines for %s: %s", server_name, machines)

    machine_statuses = []

    for machine in machines:
        machine_name = machine.get("machineName") or machine.get("name")
        if not machine_name:
            LOGGER.debug(
                "Skipping machine with missing name in server %s: %s",
                server_name,
                machine,
            )
            continue

        status = server_client.get_machine_status(machine_name)
        LOGGER.debug(
            "Machine status for %s in server %s: %s",
            machine_name,
            server_name,
            status,
        )

        machine_statuses.append(
            {
                "name": machine_name,
                "configured_state": status.get("configuredState", "UNKNOWN"),
                "realtime_state": status.get("realTimeState", "UNKNOWN"),
            }
        )

    output_json_piggyback(
        server_name,
        "arcgis_server_machines",
        arcgis_server_machines_section(machine_statuses),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_server_services(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting server services for %s", server_name)
    services_data = server_client.get_services()
    LOGGER.debug("Server services for %s: %s", server_name, services_data)
    service_list = [
        {
            "folderName": "" if svc.get("folderName", "") == "/" else svc.get("folderName", ""),
            "serviceName": svc["serviceName"],
            "type": svc["type"],
        }
        for svc in services_data
    ]
    LOGGER.info(
        "Getting service statuses for %d services in server %s",
        len(service_list),
        server_name,
    )
    statuses = server_client.get_services_report(service_list)
    LOGGER.debug("Service statuses for %s: %s", server_name, statuses)

    output_json_piggyback(
        server_name,
        "arcgis_services",
        arcgis_services_section(statuses),
    )


def collect_service_stats(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    since: str,
    cache_seconds: int,
) -> None:
    """Collect per-service usage statistics via a transient usage report.

    Fetches the full service list independently so this collection works
    correctly even when server-services collection is disabled.
    """
    LOGGER.info("Collecting service stats for %s (since=%s)", server_name, since)

    services_data = server_client.get_services()
    LOGGER.debug(
        "Services for stats collection on %s: %d services",
        server_name,
        len(services_data),
    )

    resource_uris = [
        _service_to_resource_uri(svc)
        for svc in services_data
        if svc.get("serviceName") and svc.get("type")
    ]

    if not resource_uris:
        LOGGER.info("No services found for stats collection on %s", server_name)
        return

    LOGGER.debug(
        "Querying usage report for %d services on %s",
        len(resource_uris),
        server_name,
    )
    report_data = server_client.get_service_stats(resource_uris, since)
    LOGGER.debug("Usage report data for %s: %s", server_name, report_data)

    output_json_piggyback(
        server_name,
        "arcgis_service_stats",
        arcgis_service_stats_section(report_data, since),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_registered_datastores(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> None:
    LOGGER.info("Collecting registered datastores for %s", server_name)
    validations: list[RegisteredDatastoreValidation] = []

    registered_datastores = server_client.get_datastores(managed=False)
    LOGGER.debug("Registered datastores for %s: %s", server_name, registered_datastores)

    for item in registered_datastores:
        LOGGER.debug(
            "Validating registered datastore %s for %s",
            item.get("path", ""),
            server_name,
        )
        validation = server_client.validate_registered_datastore(item)
        LOGGER.debug(
            "Validation result for %s in %s: %s",
            item.get("path", ""),
            server_name,
            validation,
        )
        health_items = normalize_registered_datastore_validation(
            item.get("path", ""),
            item.get("type", ""),
            validation,
        )
        LOGGER.debug(
            "Normalized validation items for %s in %s: %s",
            item.get("path", ""),
            server_name,
            health_items,
        )

        for health_item in health_items:
            validations.append(
                RegisteredDatastoreValidation(
                    path=health_item.path,
                    store_type=health_item.store_type,
                    status=health_item.status,
                    message=health_item.message,
                    machine=getattr(health_item, "machine", None),
                )
            )

    output_json_piggyback(
        server_name,
        "arcgis_registered_datastore_validation",
        SectionRegisteredDatastoreValidation(validations=validations),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_managed_datastores(
    args,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> tuple[int, int]:
    managed_datastores = server_client.get_datastores(managed=True)
    LOGGER.info("Collecting managed datastores")
    LOGGER.debug("Managed datastores: %s", managed_datastores)

    machine_validations: dict[str, list[ManagedDatastoreValidation]] = {}

    validated_count = 0
    unsupported_count = 0

    for item in managed_datastores:
        item_path = item.get("path", "")

        for machine in item.get("info", {}).get("machines", []):
            machine_name = machine.get("name", "unknown")
            LOGGER.debug(
                "Validating managed datastore %s on machine %s",
                item_path,
                machine_name,
            )
            validation = server_client.validate_managed_datastore(item_path, machine)
            LOGGER.debug(
                "Validation result for managed datastore %s on machine %s: %s",
                item_path,
                machine_name,
                validation,
            )
            classification, message = classify_managed_datastore_response(validation)
            LOGGER.debug(
                "Classification for managed datastore %s on machine %s: %s, message: %s",
                item_path,
                machine_name,
                classification,
                message,
            )

            if classification == "unsupported":
                unsupported_count += 1
                continue

            validated_count += 1

            machine_validations.setdefault(machine_name, []).append(
                ManagedDatastoreValidation(
                    path=item_path,
                    classification=classification,
                    message=message,
                )
            )

    for machine_name, validations in machine_validations.items():
        pb_host = piggyback_host_from_machine_name(machine_name)
        LOGGER.debug(
            "Outputting managed datastore validation for machine %s with piggyback host '%s'",
            machine_name,
            pb_host,
        )

        output_json_piggyback(
            pb_host,
            "arcgis_managed_datastore_validation",
            SectionManagedDatastoreValidation(validations=validations),
            cache_interval=cache_interval(cache_seconds),
        )

    return validated_count, unsupported_count


def collect_server_license(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> None:
    LOGGER.info("Collecting server license for %s", server_name)
    license_data = server_client.get_license()
    LOGGER.debug("Server license data for %s: %s", server_name, license_data)
    output_json_piggyback(
        server_name,
        "arcgis_server_license",
        server_license_section(license_data),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_server_log_settings(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> None:
    LOGGER.info("Collecting server log settings for %s", server_name)
    output_json_piggyback(
        server_name,
        "arcgis_server_log_settings",
        log_settings_section(server_client.get_log_settings()),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_server_mode(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting server mode for %s", server_name)
    mode_data = server_client.get_server_mode()
    LOGGER.debug("Server mode for %s: %s", server_name, mode_data)
    output_json_piggyback(
        server_name,
        "arcgis_server_mode",
        server_mode_section(mode_data),
    )


def collect_web_adaptors(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
    cache_seconds: int,
) -> None:
    LOGGER.info("Collecting web adaptors for %s", server_name)
    adaptors_data = server_client.get_web_adaptors()
    LOGGER.debug("Web adaptors for %s: %s", server_name, adaptors_data)
    output_json_piggyback(
        server_name,
        "arcgis_web_adaptors",
        web_adaptors_section(adaptors_data),
        cache_interval=cache_interval(cache_seconds),
    )


def collect_server(
    args,
    server: dict,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting data for server %s", server.get("name", "unknown"))
    server_name = server.get("name") or server.get("url") or "unknown"

    if args.no_server_machines:
        log_disabled_collection("server_machines", server_name)
    else:
        try:
            collect_server_machines(
                server_name,
                server_client,
                collection,
                args.server_machines_cache,
            )
            collection.ok("server_machines", server_name)
        except Exception as e:
            collection.error("server_machines", server_name, e)
            log_collection_error("server_machines", server_name, e)

    if args.no_server_services:
        log_disabled_collection("server_services", server_name)
    else:
        try:
            collect_server_services(server_name, server_client, collection)
            collection.ok("server_services", server_name)
        except Exception as e:
            collection.error("server_services", server_name, e)
            log_collection_error("server_services", server_name, e)

    if args.no_service_stats:
        log_disabled_collection("service_stats", server_name)
    else:
        try:
            collect_service_stats(
                server_name,
                server_client,
                collection,
                args.service_stats_since,
                args.service_stats_cache,
            )
            collection.ok("service_stats", server_name)
        except Exception as e:
            collection.error("service_stats", server_name, e)
            log_collection_error("service_stats", server_name, e)

    if args.no_registered_datastores:
        log_disabled_collection("registered_datastores", server_name)
    else:
        try:
            collect_registered_datastores(
                server_name,
                server_client,
                collection,
                args.registered_datastores_cache,
            )
            collection.ok("registered_datastores", server_name)
        except Exception as e:
            collection.error("registered_datastores", server_name, e)
            log_collection_error("registered_datastores", server_name, e)

    if args.no_managed_datastores:
        log_disabled_collection("managed_datastores", server_name)
    else:
        try:
            validated_count, unsupported_count = collect_managed_datastores(
                args,
                server_client,
                collection,
                args.managed_datastores_cache,
            )
            collection.add(
                "managed_datastores",
                server_name,
                "OK",
                f"validated_{validated_count}_unsupported_{unsupported_count}",
            )
        except Exception as e:
            collection.error("managed_datastores", server_name, e)
            log_collection_error("managed_datastores", server_name, e)

    if args.no_server_license:
        log_disabled_collection("server_license", server_name)
    else:
        try:
            collect_server_license(
                server_name,
                server_client,
                collection,
                args.server_license_cache,
            )
            collection.ok("server_license", server_name)
        except Exception as e:
            collection.error("server_license", server_name, e)
            log_collection_error("server_license", server_name, e)

    if args.no_server_log_settings:
        log_disabled_collection("server_log_settings", server_name)
    else:
        try:
            collect_server_log_settings(
                server_name,
                server_client,
                collection,
                args.server_log_settings_cache,
            )
            collection.ok("server_log_settings", server_name)
        except Exception as e:
            collection.error("server_log_settings", server_name, e)
            log_collection_error("server_log_settings", server_name, e)

    if args.no_server_mode:
        log_disabled_collection("server_mode", server_name)
    else:
        try:
            collect_server_mode(server_name, server_client, collection)
            collection.ok("server_mode", server_name)
        except Exception as e:
            collection.error("server_mode", server_name, e)
            log_collection_error("server_mode", server_name, e)

    if args.no_web_adaptors:
        log_disabled_collection("web_adaptors", server_name)
    else:
        try:
            collect_web_adaptors(
                server_name,
                server_client,
                collection,
                args.web_adaptors_cache,
            )
            collection.ok("web_adaptors", server_name)
        except Exception as e:
            collection.error("web_adaptors", server_name, e)
            log_collection_error("web_adaptors", server_name, e)


def agent_arcgis(args):
    collection = CollectionStatus()
    verify_ssl = not args.no_verify_ssl

    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        LOGGER.warning("SSL certificate verification is disabled")

    LOGGER.info(
        "Starting collection for ArcGIS Enterprise at %s with user %s",
        args.portal_url,
        args.username,
    )

    token_provider = ArcGISTokenProvider(
        portal_url=args.portal_url,
        username=args.username,
        password_id=args.password_id,
        expiry=args.token_expiry,
        verify_ssl=verify_ssl,
    )
    portal_client = PortalClient(
        portal_url=args.portal_url,
        token_provider=token_provider,
        verify_ssl=verify_ssl,
    )

    if args.portal_url:
        try:
            LOGGER.info("Collecting data from portal at %s", args.portal_url)
            federated_servers = collect_portal(args, portal_client, collection)
            LOGGER.debug("Collected federated servers: %s", federated_servers)
        except Exception as e:
            collection.error("portal", args.portal_url, e)
            log_collection_error("portal", args.portal_url, e)
            output_json_section("arcgis_collection_status", collection.section())
            return 1

        for server in federated_servers:
            server_url = server.get("url")
            server_name = str(server.get("name") or server_url or "unknown_server")
            if not server_url:
                collection.warn("server_discovery", server_name, "missing server URL")
                continue

            server_client = ServerClient(
                server_url=server_url,
                token_provider=token_provider,
                verify_ssl=verify_ssl,
            )
            LOGGER.info("Collecting data for server %s", server_name)
            collect_server(args, server, server_client, collection)

        output_json_section("arcgis_collection_status", collection.section())
        return 0

    output_json_section("arcgis_collection_status", collection.section())
    return 0


def main() -> int:
    args = parse_arguments(sys.argv[1:])
    configure_logging(args)

    LOGGER.debug(
        "Starting ArcGIS agent: portal_url=%s hostname=%s verify_ssl=%s token_expiry=%s",
        args.portal_url,
        args.hostname,
        not args.no_verify_ssl,
        args.token_expiry,
    )

    return agent_arcgis(args)


if __name__ == "__main__":
    sys.exit(main())