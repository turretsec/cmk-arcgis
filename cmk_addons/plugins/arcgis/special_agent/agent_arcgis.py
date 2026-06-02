import argparse
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
    log_settings_lines,
    output_piggyback,
    output_section,
    portal_indexer_lines,
    portal_license_lines,
    portal_validate_federation_lines,
    server_license_lines,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="CheckMK ArcGIS Enterprise Special Agent")
    parser.add_argument("--username", required=True, help="ArcGIS admin username")
    parser.add_argument("--password-id", required=True, help="Checkmk password store secret ID")
    parser.add_argument("--portal-url", required=True, help="Portal base URL")
    parser.add_argument("--no-verify-ssl", action="store_true")
    parser.add_argument("--token-expiry", type=int, default=60)
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
    CMVGIS-DS1.AD.MOUNTVERNONWA.ORG -> cmvgis-ds1
    cmvgis-ds1 -> cmvgis-ds1
    """
    return machine_name.split(".", 1)[0].lower()

def collect_portal(
    args,
    portal_client: PortalClient,
    collection: CollectionStatus,
) -> list[dict]:
    try:
        portal_machines = portal_client.get_portal_machines()
        all_machine_names = [m["machineName"] for m in portal_machines]

        for machine in portal_machines:
            machine_name = machine["machineName"]
            piggyback_host = machine_piggyback_host(
                args.hostname,
                machine_name,
                all_machine_names,
            )
            machine_status = portal_client.get_portal_machine_status(machine_name)
            role = machine.get("role", "standalone") or "standalone"

            if piggyback_host:
                output_piggyback(
                    piggyback_host,
                    "arcgis_portal_health",
                    [f"{machine_status} {role}"],
                )
            else:
                output_section(
                    "arcgis_portal_health",
                    [f"{machine_status} {role}"],
                )

        collection.ok("portal_health", "portal")

    except Exception as e:
        collection.error("portal_health", "portal", e)
        sys.stderr.write(f"Failed to get Portal health: {e}\n")

    try:
        output_section(
            "arcgis_portal_indexer",
            portal_indexer_lines(portal_client.get_portal_indexer()),
        )
        collection.ok("portal_indexer", "portal")
    except Exception as e:
        collection.error("portal_indexer", "portal", e)

    try:
        output_section(
            "arcgis_portal_federation",
            portal_validate_federation_lines(portal_client.validate_federation()),
            cache_interval=300,
        )
        collection.ok("portal_federation", "portal")
    except Exception as e:
        collection.error("portal_federation", "portal", e)

    try:
        output_section(
            "arcgis_portal_license",
            portal_license_lines(portal_client.get_license()),
            cache_interval=3600,
        )
        collection.ok("portal_license", "portal")
    except Exception as e:
        collection.error("portal_license", "portal", e)

    try:
        output_section(
            "arcgis_portal_log_settings",
            log_settings_lines(portal_client.get_log_settings()),
            cache_interval=3600,
        )
        collection.ok("portal_log_settings", "portal")
    except Exception as e:
        collection.error("portal_log_settings", "portal", e)

    try:
        federated_servers = portal_client.get_federated_servers()
        collection.ok("federated_servers", "portal")
        return federated_servers
    except Exception as e:
        collection.error("federated_servers", "portal", e)
        return []
    
def collect_server_machines(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    machines = server_client.get_machines()

    lines = []

    for machine in machines:
        machine_name = machine.get("machineName") or machine.get("name")
        if not machine_name:
            continue

        status = server_client.get_machine_status(machine_name)

        configured_state = (
            status.get("configuredState")
            or status.get("configured_state")
            or "UNKNOWN"
        )
        realtime_state = (
            status.get("realTimeState")
            or status.get("realTime_state")
            or status.get("realtimeState")
            or "UNKNOWN"
        )

        lines.append(f"{machine_name} {configured_state} {realtime_state}")

    output_piggyback(
        server_name,
        "arcgis_server_machines",
        lines,
        cache_interval=300,
    )
    
def collect_server_services(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    services_data = server_client.get_services()
    # Output service status in piggyback format
    # statuses = get_all_service_statuses(server_url, server_token, verify_ssl, services_data)
    service_list = [
        {
            "folderName": "" if svc.get("folderName", "") == "/" else svc.get("folderName", ""),
            "serviceName": svc["serviceName"],
            "type": svc["type"]
        }
        for svc in services_data
    ]
    statuses = server_client.get_services_report(service_list)

    lines = [
        f"{name} {states['configuredState']} {states['realTimeState']}" 
        for name, states in statuses.items()
    ]
    output_piggyback(server_name, "arcgis_services", lines)

def collect_registered_datastores(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    # Check registered datastores
    registered_datastore_lines = []
    registered_datastores = server_client.get_datastores(managed=False)
    for item in registered_datastores:
        validation = server_client.validate_registered_datastore(item)
        health_items = normalize_registered_datastore_validation(
            item.get("path", ""),
            item.get("type", ""),
            validation,
        )
        for health_item in health_items:
            registered_datastore_lines.append(
                f"{health_item.path} {health_item.store_type} {health_item.status} {health_item.message}"
            )
    output_piggyback(
        server_name,
        "arcgis_registered_datastore_validation",
        registered_datastore_lines,
        cache_interval=900,
    )

def collect_managed_datastores(
    args,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> tuple[int, int]:
    managed_datastores = server_client.get_datastores(managed=True)
    machine_validations: dict[str, list[dict[str, str]]] = {}

    validated_count = 0
    unsupported_count = 0

    for item in managed_datastores:
        item_path = item.get("path", "")

        for machine in item.get("info", {}).get("machines", []):
            machine_name = machine.get("name", "unknown")

            validation = server_client.validate_managed_datastore(item_path, machine)
            classification, message = classify_managed_datastore_response(validation)

            if classification == "unsupported":
                unsupported_count += 1
                continue

            validated_count += 1

            machine_validations.setdefault(machine_name, []).append(
                {
                    "path": item_path,
                    "classification": classification,
                    "message": message,
                }
            )

    for machine_name, validations in machine_validations.items():
        piggyback_host = piggyback_host_from_machine_name(machine_name)

        output_piggyback(
            piggyback_host,
            "arcgis_managed_datastore_validation",
            [
                f"{v['path']} {v['classification']} {v['message']}"
                for v in validations
            ],
            cache_interval=900,
        )

    return validated_count, unsupported_count
def collect_server_license(server_name, server_client: ServerClient, collection: CollectionStatus) -> None:
    # Check license status
    license_data = server_client.get_license()
    output_piggyback(server_name, "arcgis_server_license", server_license_lines(license_data), cache_interval=3600)

def collect_server_log_settings(
    server_name: str,
    server_client: ServerClient,
    collection: CollectionStatus,
) -> None:
    output_piggyback(
        server_name,
        "arcgis_server_log_settings",
        log_settings_lines(server_client.get_log_settings()),
        cache_interval=3600,
    )

def collect_server(
        args,
        server: dict,
        server_client: ServerClient,
        collection: CollectionStatus,
) -> None:
    server_name = server.get("name") or server.get("url") or "unknown"

    try:
        collect_server_machines(server_name, server_client, collection)
        collection.ok("server_machines", server_name)
    except Exception as e:
        collection.error("server_machines", server_name, e)

    try:
        collect_server_services(server_name, server_client, collection)
        collection.ok("server_services", server_name)
    except Exception as e:
        collection.error("server_services", server_name, e)

    try:
        collect_registered_datastores(server_name, server_client, collection)
        collection.ok("registered_datastores", server_name)
    except Exception as e:
        collection.error("registered_datastores", server_name, e)

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

    try:
        collect_server_license(server_name, server_client, collection)
        collection.ok("server_license", server_name)
    except Exception as e:
        collection.error("server_license", server_name, e)

    try:
        collect_server_log_settings(server_name, server_client, collection)
        collection.ok("server_log_settings", server_name)
    except Exception as e:
        collection.error("server_log_settings", server_name, e)

def agent_arcgis(args):
    collection = CollectionStatus()
    verify_ssl = not args.no_verify_ssl

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
            federated_servers = collect_portal(args, portal_client, collection)
        except Exception as e:
            collection.error("Portal", args.portal_url, e)
            output_section("arcgis_collection_status", collection.lines)
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
            collect_server(args, server, server_client, collection)
        
        output_section("arcgis_collection_status", collection.lines)
        return 0

    output_section("arcgis_collection_status", collection.lines)
    return 0

def main() -> int:
    args = parse_arguments(sys.argv[1:])
    return agent_arcgis(args)

if __name__ == "__main__":
    sys.exit(main())