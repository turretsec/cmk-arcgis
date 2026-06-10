from typing import Iterator

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    HostConfig,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


class ServerFilterParams(BaseModel):
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)


class CacheIntervalParams(BaseModel):
    portal_federation: int = Field(default=300, ge=0)
    portal_license: int = Field(default=3600, ge=0)
    portal_log_settings: int = Field(default=3600, ge=0)
    server_machines: int = Field(default=300, ge=0)
    registered_datastores: int = Field(default=900, ge=0)
    managed_datastores: int = Field(default=900, ge=0)
    server_license: int = Field(default=3600, ge=0)
    server_log_settings: int = Field(default=3600, ge=0)
    service_stats: int = Field(default=300, ge=0)
    web_adaptors: int = Field(default=300, ge=0)
    server_logs: int = Field(default=300, ge=0)
    portal_logs: int = Field(default=300, ge=0)


class CollectionParams(BaseModel):
    portal_health: bool = True
    portal_indexer: bool = True
    portal_federation: bool = True
    portal_license: bool = True
    portal_log_settings: bool = True
    server_machines: bool = True
    server_services: bool = True
    server_service_stats: bool = True
    server_mode: bool = True
    web_adaptors: bool = True
    server_logs: bool = True
    registered_datastores: bool = True
    managed_datastores: bool = True
    server_license: bool = True
    server_log_settings: bool = True
    portal_logs: bool = True


class LogFilterParams(BaseModel):
    ignore_patterns: list[str] = Field(default_factory=list)
    ignore_codes: list[int] = Field(default_factory=list)


class Params(BaseModel):
    username: str
    password: Secret
    portal_url: str
    verify_ssl: bool = True
    token_expiry: int = 60
    service_stats_since: str = "LAST_HOUR"
    server_logs_window: int = 15
    collections: CollectionParams = Field(default_factory=CollectionParams)
    cache_intervals: CacheIntervalParams = Field(default_factory=CacheIntervalParams)
    server_filter: ServerFilterParams = Field(default_factory=ServerFilterParams)
    portal_logs_window: int = 15
    portal_log_filter: LogFilterParams = Field(default_factory=LogFilterParams)
    server_log_filter: LogFilterParams = Field(default_factory=LogFilterParams)


def _append_server_filter_args(
    args: list[str | Secret],
    server_filter: ServerFilterParams,
) -> None:
    for pattern in server_filter.include_patterns:
        args.extend(["--server-include-regex", pattern])

    for pattern in server_filter.exclude_patterns:
        args.extend(["--server-exclude-regex", pattern])


def _append_log_filter_args(
    args: list[str | Secret],
    prefix: str,
    log_filter: LogFilterParams,
) -> None:
    for pattern in log_filter.ignore_patterns:
        args.extend([f"--{prefix}-log-ignore-regex", pattern])

    for code in log_filter.ignore_codes:
        args.extend([f"--{prefix}-log-ignore-code", str(code)])


def _append_cache_interval_args(
    args: list[str | Secret],
    cache_intervals: CacheIntervalParams,
) -> None:
    args.extend(
        [
            "--portal-federation-cache",
            str(cache_intervals.portal_federation),
            "--portal-license-cache",
            str(cache_intervals.portal_license),
            "--portal-log-settings-cache",
            str(cache_intervals.portal_log_settings),
            "--server-machines-cache",
            str(cache_intervals.server_machines),
            "--registered-datastores-cache",
            str(cache_intervals.registered_datastores),
            "--managed-datastores-cache",
            str(cache_intervals.managed_datastores),
            "--server-license-cache",
            str(cache_intervals.server_license),
            "--server-log-settings-cache",
            str(cache_intervals.server_log_settings),
            "--service-stats-cache",
            str(cache_intervals.service_stats),
            "--web-adaptors-cache",
            str(cache_intervals.web_adaptors),
            "--server-logs-cache",
            str(cache_intervals.server_logs),
            "--portal-logs-cache",
            str(cache_intervals.portal_logs),
        ]
    )


def _append_disabled_collection_flags(
    args: list[str | Secret],
    collections: CollectionParams,
) -> None:
    disabled_flags = [
        (collections.portal_health, "--no-portal-health"),
        (collections.portal_indexer, "--no-portal-indexer"),
        (collections.portal_federation, "--no-portal-federation"),
        (collections.portal_license, "--no-portal-license"),
        (collections.portal_log_settings, "--no-portal-log-settings"),
        (collections.server_machines, "--no-server-machines"),
        (collections.server_services, "--no-server-services"),
        (collections.server_service_stats, "--no-service-stats"),
        (collections.server_mode, "--no-server-mode"),
        (collections.web_adaptors, "--no-web-adaptors"),
        (collections.server_logs, "--no-server-logs"),
        (collections.registered_datastores, "--no-registered-datastores"),
        (collections.managed_datastores, "--no-managed-datastores"),
        (collections.server_license, "--no-server-license"),
        (collections.server_log_settings, "--no-server-log-settings"),
        (collections.portal_logs, "--no-portal-logs"),
    ]

    for enabled, flag in disabled_flags:
        if not enabled:
            args.append(flag)


def _generate_arcgis_command(
    params: Params,
    host_config: HostConfig,
) -> Iterator[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--username",
        params.username,
        "--password-id",
        params.password,
        "--portal-url",
        params.portal_url,
        "--token-expiry",
        str(params.token_expiry),
        "--service-stats-since",
        params.service_stats_since,
        "--server-logs-window",
        str(params.server_logs_window),
        "--portal-logs-window",
        str(params.portal_logs_window),
    ]

    if not params.verify_ssl:
        args.append("--no-verify-ssl")

    _append_disabled_collection_flags(args, params.collections)
    _append_cache_interval_args(args, params.cache_intervals)
    _append_server_filter_args(args, params.server_filter)
    _append_log_filter_args(args, "portal", params.portal_log_filter)
    _append_log_filter_args(args, "server", params.server_log_filter)

    args.append(host_config.name)

    yield SpecialAgentCommand(command_arguments=args)


special_agent_arcgis = SpecialAgentConfig(
    name="arcgis",
    parameter_parser=Params.model_validate,
    commands_function=_generate_arcgis_command,
)