from collections.abc import Mapping
from typing import Any

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
from cmk_addons.plugins.arcgis.lib.arcgis_check_datastore_common import (
    state_for_datastore_status,
    DEFAULT_DATASTORE_VALIDATION_PARAMS,
)


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
    params: Mapping[str, Any],
    section: SectionRegisteredDatastoreValidation,
) -> CheckResult:
    validations_by_item = {
        _service_item(validation): validation
        for validation in section.validations
    }

    validation = validations_by_item.get(item)
    if validation is None:
        yield Result(
            state=state_for_datastore_status("unknown", params),
            summary="Registered datastore missing from agent output",
        )
        return

    state = state_for_datastore_status(validation.status, params)
    summary = f"{validation.store_type} validation {validation.status}"

    if validation.machine:
        summary += f" on {validation.machine}"

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
    check_default_parameters=DEFAULT_DATASTORE_VALIDATION_PARAMS,
    check_ruleset_name="arcgis_datastore_validation",
)
