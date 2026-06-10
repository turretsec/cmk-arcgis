from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import State


def state_from_param(value: object) -> State:
    return {
        "ok": State.OK,
        "warn": State.WARN,
        "crit": State.CRIT,
        "unknown": State.UNKNOWN,
    }.get(str(value).strip().lower(), State.UNKNOWN)


def param_str(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
) -> str:
    return str(params.get(key, defaults[key]))


def param_int(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
) -> int:
    return int(params.get(key, defaults[key]))


def param_float(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
) -> float:
    return float(params.get(key, defaults[key]))


def worst_state(*states: State) -> State:
    order = {
        State.OK: 0,
        State.WARN: 1,
        State.CRIT: 2,
        State.UNKNOWN: 3,
    }
    return max(states, key=lambda state: order[state])