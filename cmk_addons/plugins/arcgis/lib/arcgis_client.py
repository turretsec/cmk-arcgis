import json
import requests
from pathlib import Path
import time

from cmk.utils import password_store 

class ArcGISTokenProvider:
    def __init__(
        self,
        portal_url: str,
        username: str,
        password_id: str,
        expiry: int,
        verify_ssl: bool,
        timeout: int = 30,
    ) -> None:
        self.portal_url = portal_url.rstrip("/")
        self.username = username
        self.password_id = password_id
        self.expiry = expiry
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self._password: str | None = None
        self._portal_token: str | None = None
        self._server_tokens: dict[str, str] = {}

    def _resolve_password(self) -> str:
        if self._password is None:
            pw_id, pw_path = self.password_id.split(":", 1)
            password = password_store.lookup(Path(pw_path), pw_id)
            if not isinstance(password, str):
                raise RuntimeError("Password lookup failed")
            self._password = password
        return self._password

    def _generate_token(self, referer: str, server_url: str | None = None) -> str:
        password = self._resolve_password()

        data = {
            "username": self.username,
            "password": password,
            "client": "referer",
            "expiration": self.expiry,
            "f": "json",
            "referer": referer,
        }

        if server_url:
            data["serverURL"] = f"<{server_url}>"

        response = requests.post(
            f"{self.portal_url}/sharing/rest/generateToken",
            data=data,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json()

        if "token" not in payload:
            raise RuntimeError(
                f"Token generation failed: {payload.get('error', payload)}"
            )

        return payload["token"]

    def get_portal_token(self) -> str:
        if self._portal_token is None:
            self._portal_token = self._generate_token(
                referer=self.portal_url,
            )

        return self._portal_token

    def get_server_token(self, server_url: str) -> str:
        server_url = server_url.rstrip("/")

        if server_url not in self._server_tokens:
            self._server_tokens[server_url] = self._generate_token(
                referer=server_url,
                server_url=server_url,
            )

        return self._server_tokens[server_url]
    
class PortalClient:
    def __init__(
        self,
        portal_url: str,
        token_provider: ArcGISTokenProvider,
        verify_ssl: bool,
        timeout: int = 30,
    ) -> None:
        self.portal_url = portal_url.rstrip("/")
        self.token_provider = token_provider
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def get_json(self, path: str, params: dict | None = None) -> dict:
        token = self.token_provider.get_portal_token()

        query = {
            "token": token,
            "f": "json",
        }

        if params:
            query.update(params)

        response = requests.get(
            f"{self.portal_url}{path}",
            params=query,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    def get_portal_machines(self) -> list[dict]:
        return self.get_json("/portaladmin/machines").get("machines", [])
    
    def get_portal_machine_status(self, machine_name: str) -> str:
        return self.get_json(f"/portaladmin/machines/status/{machine_name}").get("status", "error")
    
    def get_portal_indexer(self) -> dict:
        return self.get_json("/portaladmin/system/indexer/status")

    def get_federated_servers(self) -> list[dict]:
        return self.get_json("/portaladmin/federation/servers").get("servers", [])

    def validate_federation(self) -> dict:
        return self.get_json("/portaladmin/federation/servers/validate")

    def get_indexer_status(self) -> dict:
        return self.get_json("/portaladmin/system/indexer/status")

    def get_license(self) -> dict:
        return self.get_json("/portaladmin/license")
    
    def get_log_settings(self) -> dict:
        return self.get_json("/portaladmin/logs/settings")
    
class ServerClient:
    def __init__(
        self,
        server_url: str,
        token_provider: ArcGISTokenProvider,
        verify_ssl: bool,
        timeout: int = 30,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.token_provider = token_provider
        self.verify_ssl = verify_ssl
        self.timeout = timeout

    def get_json(self, path: str, params: dict | None = None) -> dict:
        token = self.token_provider.get_server_token(self.server_url)

        query = {
            "token": token,
            "f": "json",
        }

        if params:
            query.update(params)

        response = requests.get(
            f"{self.server_url}{path}",
            params=query,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, data: dict | None = None) -> dict:
        token = self.token_provider.get_server_token(self.server_url)

        payload = {
            "token": token,
            "f": "json",
        }

        if data:
            payload.update(data)

        response = requests.post(
            f"{self.server_url}{path}",
            data=payload,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
    
    def get_machines(self) -> list[dict]:
        response = self.get_json("/admin/machines")
        return response.get("machines", [])


    def get_machine_status(self, machine_name: str) -> dict:
        return self.get_json(f"/admin/machines/{machine_name}/status")

    def get_services(self) -> list[dict]:
        root = self.get_json("/admin/services")
        services = root.get("services", [])

        for folder in root.get("folders", []):
            folder_services = self.get_json(f"/admin/services/{folder}").get("services", [])
            services.extend(folder_services)
        return services

    def get_services_report(self, services: list[dict]) -> dict:
        response = self.post_json(
            "/admin/services/report",
            {
                "parameters": '["status"]',
                "services": json.dumps(services),
            },
        )
        result = {}
        for report in response.get("reports", []):
            folder = report.get("folderName", "").strip("/")
            name = report["serviceName"]
            svc_type = report["type"]
            full_name = f"{folder}/{name}.{svc_type}".lstrip("/")
            result[full_name] = report.get("status", {})
        return result
    
    def get_datastores(self, managed: bool) -> list[dict]:
        response = self.post_json("/admin/data/findItems", {"managed": managed})
        return response.get("items", [])
    
    def validate_registered_datastore(self, item: dict) -> dict:
        response = self.post_json("/admin/data/validateDataItem", {"item": json.dumps(item)})
        return response
    
    def validate_managed_datastore(self, path: str, machine: dict) -> dict:
        response = self.post_json(f"/admin/data/items{path}/machines/{machine.get('name')}/validate")
        return response
    
    def get_license(self) -> dict:
        return self.get_json("/admin/system/licenses")
    
    def get_log_settings(self) -> dict:
        return self.get_json("/admin/logs/settings")
    

    def create_usage_report(
        self,
        report_name: str,
        since: str,
        queries: list[dict],
        metadata: dict | None = None,
        from_ms: int | None = None,
        to_ms: int | None = None,
        aggregation_interval: int | None = None,
    ) -> dict:
        """Create a usage report on the server.
 
        Pass ``metadata={"temp": True}`` for a transient report that should be
        deleted after querying.  The report name must be unique.
 
        For ``since="CUSTOM"`` supply ``from_ms`` and ``to_ms`` as millisecond
        epoch timestamps.  ``aggregation_interval`` (minutes) controls the
        time-slice granularity; when omitted the server uses its default.
        """
        report: dict = {
            "reportname": report_name,
            "since": since,
            "queries": queries,
            "metadata": json.dumps(metadata or {}),
        }
        if from_ms is not None:
            report["from"] = from_ms
        if to_ms is not None:
            report["to"] = to_ms
        if aggregation_interval is not None:
            report["aggregationInterval"] = aggregation_interval
 
        return self.post_json(
            "/admin/usagereports/add",
            {"usagereport": json.dumps(report)},
        )
 
    def get_usage_report_data(self, report_name: str) -> dict:
        """Retrieve aggregated data for a previously created usage report."""
        return self.get_json(
            f"/admin/usagereports/{report_name}/data",
            {"filter": '{"machines":"*"}'},
        )
 
    def delete_usage_report(self, report_name: str) -> dict:
        """Delete a usage report by name."""
        return self.post_json(f"/admin/usagereports/{report_name}/delete")
 
    def get_service_stats(
        self,
        service_resource_uris: list[str],
        since: str = "LAST_HOUR",
    ) -> dict:
        """Fetch per-service usage statistics using a transient usage report.
 
        Creates a temporary report covering all requested *service_resource_uris*,
        queries its data, deletes it, and returns the raw report dict.
 
        ``since`` controls the time window.  The special value ``"LAST_HOUR"``
        maps to a CUSTOM window of ``now - 1 hour`` to ``now`` with a 10-minute
        aggregation interval (6 data points), matching the "within the last hour"
        view used by ArcGIS Monitor dashboards.  The standard values
        ``"LAST_DAY"``, ``"LAST_WEEK"``, and ``"LAST_MONTH"`` are passed to the
        API directly.
 
        All metrics are requested in a single query (valid from ArcGIS Enterprise
        11.1+, where ServiceRunningInstancesMax can be combined with the others).
 
        Returns an empty dict when *service_resource_uris* is empty.
        """
        if not service_resource_uris:
            return {}
 
        report_name = f"checkmk_{int(time.time() * 1000)}"
 
        queries = [
            {
                "resourceURIs": service_resource_uris,
                "metrics": [
                    "RequestCount",
                    "RequestsFailed",
                    "RequestsTimedOut",
                    "RequestAvgResponseTime",
                    "RequestMaxResponseTime",
                    "RequestAvgWaitTime",
                    "RequestMaxWaitTime",
                    "ServiceRunningInstancesMax",
                ],
            }
        ]
 
        metadata = {"temp": True, "title": report_name, "managerReport": False}
 
        if since == "LAST_HOUR":
            # Use CUSTOM with dynamic timestamps so every collection run
            # reflects "the last 60 minutes" rather than a fixed calendar day.
            # 10-minute intervals yield 6 data points, matching ArcGIS Monitor.
            now_ms = int(time.time() * 1000)
            self.create_usage_report(
                report_name,
                "CUSTOM",
                queries,
                metadata,
                from_ms=now_ms - 3_600_000,
                to_ms=now_ms,
                aggregation_interval=10,
            )
        else:
            self.create_usage_report(report_name, since, queries, metadata)
 
        try:
            return self.get_usage_report_data(report_name)
        finally:
            # Best-effort cleanup: if delete fails, the temporary report may remain
            # in ArcGIS Server Admin and can be removed manually.
            try:
                self.delete_usage_report(report_name)
            except Exception:
                pass