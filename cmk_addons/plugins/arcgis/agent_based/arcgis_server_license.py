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

from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    SectionServerLicense,
    ServerLicenseEntry,
)

Section = dict[str, dict[str, str | int | bool]]

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




def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()


def _parse_bool(value: str, default: bool = False) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default


def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_arcgis_server_license(
    string_table: StringTable,
) -> SectionServerLicense:
    raw = _raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionServerLicense.model_validate_json(raw)

    # Old text-row fallback
    entries: list[ServerLicenseEntry] = []

    for row in string_table:
        if len(row) < 5:
            continue

        kind = row[0]

        if kind in {"edition", "level", "datafeature", "extension"}:
            entries.append(
                ServerLicenseEntry(
                    kind=kind,
                    name=row[1],
                    version=row[2],
                    can_expire=_parse_bool(row[3]),
                    expiration=_parse_int(row[4]),
                    extra=" ".join(row[5:]) if len(row) > 5 else "",
                )
            )

        elif kind == "feature" and len(row) >= 8:
            entries.append(
                ServerLicenseEntry(
                    kind=kind,
                    name=row[1],
                    display_name=row[2].replace("_", " "),
                    core_count=_parse_int(row[3]),
                    version=row[4],
                    can_expire=_parse_bool(row[5]),
                    expiration=_parse_int(row[6]),
                    is_valid=_parse_bool(row[7], default=True),
                )
            )

    return SectionServerLicense(entries=entries)

def discover_arcgis_server_license(section: SectionServerLicense) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)

def check_arcgis_server_license(item: str, section: SectionServerLicense) -> CheckResult:
    entries_by_item = {
        f"{entry.kind} {entry.name}": entry
        for entry in section.entries
    }

    if item not in entries_by_item:
        yield Result(state=State.UNKNOWN, summary="License data missing from agent output")
        return

    license_item = entries_by_item[item]

    kind = str(license_item.kind)
    name = str(license_item.name)
    display_name = str(license_item.display_name or name)
    version = str(license_item.version)
    can_expire = bool(license_item.can_expire)
    expiration = int(license_item.expiration)
    is_valid = bool(license_item.is_valid)
    core_count = int(license_item.core_count)

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