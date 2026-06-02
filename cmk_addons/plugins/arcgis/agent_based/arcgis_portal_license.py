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

Section = dict[str, dict[str, str | int]]

def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _expiration_summary(expiration_ms: int) -> tuple[State, str]:
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

def _worst_state(*states: State) -> State:
    order = {
        State.OK: 0,
        State.WARN: 1,
        State.CRIT: 2,
        State.UNKNOWN: 3,
    }
    return max(states, key=lambda state: order[state])

def parse_arcgis_portal_license(string_table: StringTable) -> Section:
    parsed: Section = {}

    for row in string_table:
        if not row:
            continue

        if row[0] == "summary" and len(row) >= 4:
            parsed["summary"] = {
                "kind": "summary",
                "current": _parse_int(row[1]),
                "maximum": _parse_int(row[2]),
                "version": row[3],
            }
            continue

        if len(row) >= 5:
            kind = row[0]
            license_id = row[1]
            current = _parse_int(row[2])
            maximum = _parse_int(row[3])
            expiration = _parse_int(row[4])

            parsed[f"{kind} {license_id}"] = {
                "kind": kind,
                "id": license_id,
                "current": current,
                "maximum": maximum,
                "expiration": expiration,
            }

    return parsed

def discover_arcgis_portal_license(section: Section) -> DiscoveryResult:
    if "summary" in section:
        yield Service(item="summary")

    for item in section:
        if item != "summary":
            yield Service(item=item)

def check_arcgis_portal_license(item: str, section: Section) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="License data missing from agent output")
        return

    license_item = section[item]

    if item == "summary":
        current = int(license_item["current"])
        maximum = int(license_item["maximum"])
        version = str(license_item["version"])

        if maximum <= 0:
            yield Result(
                state=State.UNKNOWN,
                summary=f"Portal {version}, {current} registered members, maximum unknown",
            )
            return

        usage_percent = current / maximum * 100

        if usage_percent >= 95:
            state = State.CRIT
        elif usage_percent >= 85:
            state = State.WARN
        else:
            state = State.OK

        yield Result(
            state=state,
            summary=f"Portal {version}: {current}/{maximum} members used ({usage_percent:.1f}%)",
        )
        return

    kind = str(license_item["kind"])
    license_id = str(license_item["id"])
    current = int(license_item["current"])
    maximum = int(license_item["maximum"])
    expiration = int(license_item["expiration"])

    expiration_state, expiration_text = _expiration_summary(expiration)

    if maximum > 0:
        usage_percent = current / maximum * 100
        usage_text = f"{current}/{maximum} assigned ({usage_percent:.1f}%)"

        if usage_percent >= 95:
            usage_state = State.CRIT
        elif usage_percent >= 85:
            usage_state = State.WARN
        else:
            usage_state = State.OK
    else:
        usage_text = f"{current} assigned, maximum unknown"
        usage_state = State.UNKNOWN

    final_state = _worst_state(usage_state, expiration_state)

    yield Result(
        state=final_state,
        summary=f"{kind} {license_id}: {usage_text}, {expiration_text}",
    )

agent_section_arcgis_portal_license = AgentSection(
    name="arcgis_portal_license",
    parse_function=parse_arcgis_portal_license,
)

check_plugin_arcgis_portal_license = CheckPlugin(
    name="arcgis_portal_license",
    service_name="ArcGIS Portal License %s",
    discovery_function=discover_arcgis_portal_license,
    check_function=check_arcgis_portal_license,
)