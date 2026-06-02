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

from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import parse_json_rows
from cmk_addons.plugins.arcgis.lib.arcgis_sections import (
    RegisteredDatastoreValidation,
    SectionRegisteredDatastoreValidation,
)


def _state_from_registered_datastore_status(status: str) -> State:
    normalized = status.strip().lower()

    if normalized in {"success", "passed", "ok", "true"}:
        return State.OK
    if normalized in {"warning", "warn", "success with warnings"}:
        return State.WARN
    if normalized in {"failure", "failed", "error", "false"}:
        return State.CRIT

    return State.UNKNOWN


def parse_arcgis_registered_datastore_validation(
    string_table: StringTable,
) -> SectionRegisteredDatastoreValidation:
    validations: list[RegisteredDatastoreValidation] = []

    for section in parse_json_rows(string_table, SectionRegisteredDatastoreValidation):
        validations.extend(section.validations)

    return SectionRegisteredDatastoreValidation(validations=validations)


def _service_item(validation: RegisteredDatastoreValidation) -> str:
    if validation.machine:
        return f"{validation.path} on {validation.machine}"
    return validation.path


def discover_arcgis_registered_datastore_validation(
    section: SectionRegisteredDatastoreValidation,
) -> DiscoveryResult:
    for validation in section.validations:
        yield Service(item=_service_item(validation))


def check_arcgis_registered_datastore_validation(
    item: str,
    section: SectionRegisteredDatastoreValidation,
) -> CheckResult:
    validations_by_item = {
        _service_item(validation): validation for validation in section.validations
    }

    validation = validations_by_item.get(item)
    if validation is None:
        yield Result(
            state=State.UNKNOWN,
            summary="Registered datastore missing from agent output",
        )
        return

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
