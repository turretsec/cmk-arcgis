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
    ManagedDatastoreValidation,
    SectionManagedDatastoreValidation,
)
from cmk_addons.plugins.arcgis.lib.arcgis_check_datastore_common import (
    state_for_datastore_status,
    DEFAULT_DATASTORE_VALIDATION_PARAMS,
)


def parse_arcgis_managed_datastore_validation(
    string_table: StringTable,
) -> SectionManagedDatastoreValidation:
    validations: list[ManagedDatastoreValidation] = []

    for section in parse_json_rows(string_table, SectionManagedDatastoreValidation):
        validations.extend(section.validations)

    return SectionManagedDatastoreValidation(validations=validations)


def discover_arcgis_managed_datastore_validation(
    section: SectionManagedDatastoreValidation,
) -> DiscoveryResult:
    for validation in section.validations:
        yield Service(item=validation.path)


def check_arcgis_managed_datastore_validation(
    item: str,
    params: Mapping[str, Any],
    section: SectionManagedDatastoreValidation,
) -> CheckResult:
    validations_by_item = {
        validation.path: validation
        for validation in section.validations
    }

    if item not in validations_by_item:
        yield Result(
            state=state_for_datastore_status("unknown", params),
            summary="Managed datastore missing from agent output",
        )
        return

    validation = validations_by_item[item]
    state = state_for_datastore_status(validation.classification, params)

    normalized = validation.classification.strip().lower()

    if normalized in {"success", "ok", "passed", "true"}:
        summary = "Managed datastore validation successful"
    elif normalized in {"unsupported", "not_supported", "not supported"}:
        summary = "Managed datastore validation unsupported"
    elif normalized in {"failure", "failed", "false"}:
        summary = "Managed datastore validation failed"
    elif normalized == "error":
        summary = "Managed datastore validation returned an error"
    elif normalized in {"warning", "warn"}:
        summary = "Managed datastore validation warning"
    else:
        summary = f"Managed datastore validation status: {validation.classification}"

    if validation.message:
        yield Result(
            state=state,
            summary=summary,
            details=validation.message,
        )
    else:
        yield Result(
            state=state,
            summary=summary,
        )


agent_section_arcgis_managed_datastore_validation = AgentSection(
    name="arcgis_managed_datastore_validation",
    parse_function=parse_arcgis_managed_datastore_validation,
)


check_plugin_arcgis_managed_datastore_validation = CheckPlugin(
    name="arcgis_managed_datastore_validation",
    service_name="ArcGIS Managed Datastore %s",
    discovery_function=discover_arcgis_managed_datastore_validation,
    check_function=check_arcgis_managed_datastore_validation,
    check_default_parameters=DEFAULT_DATASTORE_VALIDATION_PARAMS,
    check_ruleset_name="arcgis_datastore_validation",
)
