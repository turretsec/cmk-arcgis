import argparse
import logging
import sys
import urllib3

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
    output_json_piggyback,
    output_json_section,
    portal_license_section,
    server_license_section,
    portal_health_section,
    portal_indexer_section,
    portal_federation_section,
    arcgis_services_section,
    arcgis_server_machines_section,
    log_settings_section,
)

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    RegisteredDatastoreValidation,
    SectionRegisteredDatastoreValidation,
    ManagedDatastoreValidation,
    SectionManagedDatastoreValidation,
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

# Argument parsing

def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="CheckMK ArcGIS Enterprise Special Agent")
    parser.add_argument("--username", required=True, help="ArcGIS admin username")
    parser.add_argument("--password-id", required=True, help="Checkmk password store secret ID")
    parser.add_argument("--portal-url", required=True, help="Portal base URL")
    parser.add_argument("--no-verify-ssl", action="store_true")
    parser.add_argument("--token-expiry", type=int, default=60)
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
    parser.add_argument("hostname", help="Target hostname")
    return parser.parse_args(argv)

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
    hostname = machine_name.split('.')[0]
    return hostname.lower()

def piggyback_host_from_machine_name(machine_name: str) -> str:
    """Convert ArcGIS machine/FQDN names to Checkmk host names.

    Example:
    GIS-SERVER-01.EXAMPLE.ORG -> gis-server-01
    gis-server-01 -> gis-server-01
    """
    return machine_name.split(".", 1)[0].lower()

def collect_portal(
    args,
    portal_client: PortalClient,
    collection: CollectionStatus,
) -> list[dict]:
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
            LOGGER.info("Collecting portal health for machine %s (piggyback host: '%s')", machine_name, piggyback_host)
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

    try:
        LOGGER.info("Collecting portal federation validation")
        output_json_section(
            "arcgis_portal_federation",
            portal_federation_section(portal_client.validate_federation()),
            cache_interval=300,
        )
        collection.ok("portal_federation", "portal")
    except Exception as e:
        collection.error("portal_federation", "portal", e)
        log_collection_error("portal_federation", "portal", e)

    try:
        LOGGER.info("Collecting portal license")
        output_json_section(
            "arcgis_portal_license",
            portal_license_section(portal_client.get_license()),
            cache_interval=3600,
        )
        collection.ok("portal_license", "portal")
    except Exception as e:
        collection.error("portal_license", "portal", e)
        log_collection_error("portal_license", "portal", e)

    try:
        LOGGER.info("Collecting portal log settings")
        output_json_section(
            "arcgis_portal_log_settings",
            log_settings_section(portal_client.get_log_settings()),
            cache_interval=3600,
        )
        collection.ok("portal_log_settings", "portal")
    except Exception as e:
        collection.error("portal_log_settings", "portal", e)
        log_collection_error("portal_log_settings", "portal", e)
    try:
        LOGGER.info("Collecting portal federated servers")
        federated_servers = portal_client.get_federated_servers()
        LOGGER.debug("Federated servers: %s", federated_servers)
        collection.ok("federated_servers", "portal")
        return federated_servers
    except Exception as e:
        collection.error("federated_servers", "portal", e)
        log_collection_error("federated_servers", "portal", e)
        return []
    
def collect_server_machines(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    LOGGER.info("Collecting server machines for %s", server_name)
    machines = server_client.get_machines()
    LOGGER.debug("Server machines for %s: %s", server_name, machines)

    machine_statuses = []

    for machine in machines:
        machine_name = machine.get("machineName") or machine.get("name")
        if not machine_name:
            LOGGER.debug("Skipping machine with missing name in server %s: %s", server_name, machine)
            continue

        status = server_client.get_machine_status(machine_name)
        LOGGER.debug("Machine status for %s in server %s: %s", machine_name, server_name, status)

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
        cache_interval=300,
    )
    
def collect_server_services(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
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
    LOGGER.info("Getting service statuses for %d services in server %s", len(service_list), server_name)
    statuses = server_client.get_services_report(service_list)
    LOGGER.debug("Service statuses for %s: %s", server_name, statuses)

    output_json_piggyback(
        server_name,
        "arcgis_services",
        arcgis_services_section(statuses),
    )

def collect_registered_datastores(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting registered datastores for %s", server_name)
    validations: list[RegisteredDatastoreValidation] = []

    registered_datastores = server_client.get_datastores(managed=False)
    LOGGER.debug("Registered datastores for %s: %s", server_name, registered_datastores)

    for item in registered_datastores:
        LOGGER.debug("Validating registered datastore %s for %s", item.get("path", ""), server_name)
        validation = server_client.validate_registered_datastore(item)
        LOGGER.debug("Validation result for %s in %s: %s", item.get("path", ""), server_name, validation)
        health_items = normalize_registered_datastore_validation(
            item.get("path", ""),
            item.get("type", ""),
            validation,
        )
        LOGGER.debug("Normalized validation items for %s in %s: %s", item.get("path", ""), server_name, health_items)

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
        cache_interval=900,
    )

def collect_managed_datastores(
    args,
    server_client: ServerClient,
    collection: CollectionStatus,
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
            LOGGER.debug("Validating managed datastore %s on machine %s", item_path, machine_name)
            validation = server_client.validate_managed_datastore(item_path, machine)
            LOGGER.debug("Validation result for managed datastore %s on machine %s: %s", item_path, machine_name, validation)
            classification, message = classify_managed_datastore_response(validation)
            LOGGER.debug("Classification for managed datastore %s on machine %s: %s, message: %s", item_path, machine_name, classification, message)

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
        piggyback_host = piggyback_host_from_machine_name(machine_name)
        LOGGER.debug("Outputting managed datastore validation for machine %s with piggyback host '%s'", machine_name, piggyback_host)

        output_json_piggyback(
            piggyback_host,
            "arcgis_managed_datastore_validation",
            SectionManagedDatastoreValidation(validations=validations),
            cache_interval=900,
        )

    return validated_count, unsupported_count

def collect_server_license(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    # Check license status
    LOGGER.info("Collecting server license for %s", server_name)
    license_data = server_client.get_license()
    LOGGER.debug("Server license data for %s: %s", server_name, license_data)
    output_json_piggyback(
        server_name,
        "arcgis_server_license",
        server_license_section(license_data),
        cache_interval=3600,
    )

def collect_server_log_settings(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting server log settings for %s", server_name)
    output_json_piggyback(
        server_name,
        "arcgis_server_log_settings",
        log_settings_section(server_client.get_log_settings()),
        cache_interval=3600,
    )

def collect_server(
        args,
        server: dict,
        server_client: ServerClient,
        collection: CollectionStatus,
) -> None:
    LOGGER.info("Collecting data for server %s", server.get("name", "unknown"))
    server_name = server.get("name") or server.get("url") or "unknown"

    try:
        collect_server_machines(server_name, server_client, collection)
        collection.ok("server_machines", server_name)
    except Exception as e:
        collection.error("server_machines", server_name, e)
        log_collection_error("server_machines", server_name, e)

    try:
        collect_server_services(server_name, server_client, collection)
        collection.ok("server_services", server_name)
    except Exception as e:
        collection.error("server_services", server_name, e)
        log_collection_error("server_services", server_name, e)

    try:
        collect_registered_datastores(server_name, server_client, collection)
        collection.ok("registered_datastores", server_name)
    except Exception as e:
        collection.error("registered_datastores", server_name, e)
        log_collection_error("registered_datastores", server_name, e)

    try:
        validated_count, unsupported_count = collect_managed_datastores(
            args,
            server_client,
            collection,
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

    try:
        collect_server_license(server_name, server_client, collection)
        collection.ok("server_license", server_name)
    except Exception as e:
        collection.error("server_license", server_name, e)  
        log_collection_error("server_license", server_name, e)
    try:
        collect_server_log_settings(server_name, server_client, collection)
        collection.ok("server_log_settings", server_name)
    except Exception as e:
        collection.error("server_log_settings", server_name, e)
        log_collection_error("server_log_settings", server_name, e)

def agent_arcgis(args):
    collection = CollectionStatus()
    verify_ssl = not args.no_verify_ssl

    
    if not verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        LOGGER.warning("SSL certificate verification is disabled")

    LOGGER.info("Starting collection for ArcGIS Enterprise at %s with user %s", args.portal_url, args.username)

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