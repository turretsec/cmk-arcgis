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
    RegisteredDatastoreValidation,
    SectionRegisteredDatastoreValidation,
)

Section = dict[str, dict[str, str]]

def _state_from_registered_datastore_status(status: str) -> State:
    normalized = status.strip().lower()

    if normalized in {"success", "passed", "ok", "true"}:
        return State.OK

    if normalized in {"warning", "warn", "success with warnings"}:
        return State.WARN

    if normalized in {"failure", "failed", "error", "false"}:
        return State.CRIT

    return State.UNKNOWN

def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()


def parse_arcgis_registered_datastore_validation(
    string_table: StringTable,
) -> SectionRegisteredDatastoreValidation:
    raw = _raw_section_text(string_table)

    if raw.startswith("{"):
        return SectionRegisteredDatastoreValidation.model_validate_json(raw)

    # Old text-row fallback
    validations: list[RegisteredDatastoreValidation] = []

    for row in string_table:
        if len(row) < 3:
            continue

        validations.append(
            RegisteredDatastoreValidation(
                path=row[0],
                store_type=row[1],
                status=row[2],
                message=" ".join(row[3:]) if len(row) > 3 else "",
            )
        )

    return SectionRegisteredDatastoreValidation(validations=validations)

def discover_arcgis_registered_datastore_validation(
    section: SectionRegisteredDatastoreValidation,
):
    for validation in section.validations:
        if validation.machine:
            yield Service(item=f"{validation.path} on {validation.machine}")
        else:
            yield Service(item=validation.path)

def check_arcgis_registered_datastore_validation(
    item: str,
    section: SectionRegisteredDatastoreValidation,
):
    validations_by_item = {}

    for validation in section.validations:
        item_name = (
            f"{validation.path} on {validation.machine}"
            if validation.machine
            else validation.path
        )
        validations_by_item[item_name] = validation

    if item not in validations_by_item:
        yield Result(
            state=State.UNKNOWN,
            summary="Registered datastore missing from agent output",
        )
        return

    validation = validations_by_item[item]
    state = _state_from_registered_datastore_status(validation.status)

    summary = f"{validation.store_type} validation {validation.status}"

    if validation.message:
        yield Result(state=state, summary=summary, details=validation.message)
    else:
        yield Result(state=state, summary=summary)

agent_section_arcgis_registered_datastore_validation = AgentSection(
    name="arcgis_registered_datastore_validation",
    parse_function=parse_arcgis_registered_datastore_validation,
)

check_plugin_arcgis_registered_datastore_validation = CheckPlugin(
    name="arcgis_registered_datastore_validation",
    service_name="ArcGIS Registered Datastore %s",
    discovery_function=discover_arcgis_registered_datastore_validation,
    check_function=check_arcgis_registered_datastore_validation,
)