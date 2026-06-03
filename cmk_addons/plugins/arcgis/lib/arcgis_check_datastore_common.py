from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import State
from cmk_addons.plugins.arcgis.lib.arcgis_check_helpers import (
    param_str,
    state_from_param,
)

DEFAULT_DATASTORE_VALIDATION_PARAMS = {
    "success_state": "ok",
    "warning_state": "warn",
    "failure_state": "crit",
    "error_state": "crit",
    "unsupported_state": "ok",
    "unknown_state": "unknown",
}


def state_for_datastore_status(
    status: str,
    params: Mapping[str, Any],
) -> State:
    normalized = status.strip().lower()

    if normalized in {"success", "ok", "passed", "true"}:
        return state_from_param(
            param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "success_state")
        )

    if normalized in {"warning", "warn", "success with warnings"}:
        return state_from_param(
            param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "warning_state")
        )

    if normalized in {"failure", "failed", "false", "unhealthy", "stopped"}:
        return state_from_param(
            param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "failure_state")
        )

    if normalized == "error":
        return state_from_param(
            param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "error_state")
        )

    if normalized in {"unsupported", "not_supported", "not supported"}:
        return state_from_param(
            param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "unsupported_state")
        )

    return state_from_param(
        param_str(params, DEFAULT_DATASTORE_VALIDATION_PARAMS, "unknown_state")
    )