from datetime import datetime, timezone

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, dict[str, str | int | bool]]

def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _parse_bool(value: str, default: bool = False) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default

def _worst_state(*states: State) -> State:
    order = {
        State.OK: 0,
        State.WARN: 1,
        State.CRIT: 2,
        State.UNKNOWN: 3,
    }
    return max(states, key=lambda state: order[state])

def _expiration_state(expiration_ms: int, can_expire: bool) -> tuple[State, str]:
    if not can_expire:
        return State.OK, "does not expire"

    if expiration_ms <= 0:
        return State.UNKNOWN, "expiration unknown"

    now = datetime.now(timezone.utc)
    expiration = datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc)
    days_left = (expiration - now).days
    expiration_text = expiration.strftime("%Y-%m-%d")

    if days_left < 0:
        return State.CRIT, f"expired on {expiration_text}"

    if days_left <= 7:
        return State.CRIT, f"expires on {expiration_text} ({days_left} days)"

    if days_left <= 30:
        return State.WARN, f"expires on {expiration_text} ({days_left} days)"

    return State.OK, f"expires on {expiration_text} ({days_left} days)"

def parse_arcgis_server_license(string_table: StringTable) -> Section:
    parsed: Section = {}

    for row in string_table:
        if len(row) < 5:
            continue

        kind = row[0]

        if kind in {"edition", "level", "datafeature", "extension"}:
            name = row[1]
            version = row[2]
            can_expire = _parse_bool(row[3])
            expiration = _parse_int(row[4])
            extra = " ".join(row[5:]) if len(row) > 5 else ""

            item_name = f"{kind} {name}"

            parsed[item_name] = {
                "kind": kind,
                "name": name,
                "version": version,
                "can_expire": can_expire,
                "expiration": expiration,
                "extra": extra,
                "is_valid": True,
                "core_count": 0,
                "display_name": name,
            }

        elif kind == "feature" and len(row) >= 8:
            name = row[1]
            display_name = row[2].replace("_", " ")
            core_count = _parse_int(row[3])
            version = row[4]
            can_expire = _parse_bool(row[5])
            expiration = _parse_int(row[6])
            is_valid = _parse_bool(row[7], default=True)

            item_name = f"{kind} {name}"

            parsed[item_name] = {
                "kind": kind,
                "name": name,
                "display_name": display_name,
                "core_count": core_count,
                "version": version,
                "can_expire": can_expire,
                "expiration": expiration,
                "is_valid": is_valid,
                "extra": "",
            }

    return parsed

def discover_arcgis_server_license(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)

def check_arcgis_server_license(item: str, section: Section) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="License data missing from agent output")
        return

    license_item = section[item]

    kind = str(license_item["kind"])
    name = str(license_item["name"])
    display_name = str(license_item.get("display_name", name))
    version = str(license_item["version"])
    can_expire = bool(license_item["can_expire"])
    expiration = int(license_item["expiration"])
    is_valid = bool(license_item.get("is_valid", True))
    core_count = int(license_item.get("core_count", 0))

    expiration_state, expiration_text = _expiration_state(expiration, can_expire)

    if not is_valid:
        validity_state = State.CRIT
        validity_text = "invalid"
    else:
        validity_state = State.OK
        validity_text = "valid"

    final_state = _worst_state(expiration_state, validity_state)

    if kind == "feature":
        if core_count > 0:
            summary = (
                f"{display_name}: {validity_text}, version {version}, "
                f"{core_count} licensed core(s), {expiration_text}"
            )
        else:
            summary = (
                f"{display_name}: {validity_text}, version {version}, "
                f"{expiration_text}"
            )
    else:
        summary = f"{kind} {name}: version {version}, {expiration_text}"

    yield Result(state=final_state, summary=summary)


agent_section_arcgis_server_license = AgentSection(
    name="arcgis_server_license",
    parse_function=parse_arcgis_server_license,
)

check_plugin_arcgis_server_license = CheckPlugin(
    name="arcgis_server_license",
    service_name="ArcGIS Server License %s",
    discovery_function=discover_arcgis_server_license,
    check_function=check_arcgis_server_license,
)