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
    ManagedDatastoreValidation,
    SectionManagedDatastoreValidation,
)
from cmk_addons.plugins.arcgis.lib.arcgis_section_parsing import (
    looks_like_json_rows,
    raw_section_rows,
)

Section = dict[str, dict[str, str]]

def _state_from_managed_datastore_classification(
    classification: str,
    message: str,
) -> State:
    normalized = classification.strip().lower()
    lowered_message = message.strip().lower()

    if normalized in {"success", "ok", "passed", "healthy", "true"}:
        return State.OK

    if normalized in {"warning", "warn", "healthywithwarning", "success_with_warnings"}:
        return State.WARN

    if normalized in {"failure", "failed", "unhealthy", "stopped", "false"}:
        return State.CRIT

    if normalized == "unsupported":
        return State.OK

    if normalized == "error":
        # These are not necessarily failed datastores; some are unsupported API paths.
        if (
            "could not find resource or operation 'validate'" in lowered_message
            or "not installed in the current configuration" in lowered_message
        ):
            return State.OK

        return State.UNKNOWN

    return State.UNKNOWN

def _raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()

def parse_arcgis_managed_datastore_validation(
    string_table: StringTable,
) -> SectionManagedDatastoreValidation:
    raw_rows = raw_section_rows(string_table)

    if looks_like_json_rows(raw_rows):
        validations: list[ManagedDatastoreValidation] = []

        for raw in raw_rows:
            section = SectionManagedDatastoreValidation.model_validate_json(raw)
            validations.extend(section.validations)

        return SectionManagedDatastoreValidation(validations=validations)

    # Old text-row fallback
    validations: list[ManagedDatastoreValidation] = []

    for row in string_table:
        if len(row) < 2:
            continue

        validations.append(
            ManagedDatastoreValidation(
                path=row[0],
                classification=row[1],
                message=" ".join(row[2:]) if len(row) > 2 else "",
            )
        )

    return SectionManagedDatastoreValidation(validations=validations)

def discover_arcgis_managed_datastore_validation(
    section: SectionManagedDatastoreValidation,
):
    for validation in section.validations:
        yield Service(item=validation.path)

def check_arcgis_managed_datastore_validation(
    item: str,
    section: SectionManagedDatastoreValidation,
):
    validations_by_item = {
        validation.path: validation
        for validation in section.validations
    }

    if item not in validations_by_item:
        yield Result(
            state=State.UNKNOWN,
            summary="Managed datastore missing from agent output",
        )
        return

    validation = validations_by_item[item]

    state = _state_from_managed_datastore_classification(
        validation.classification,
        validation.message,
    )

    normalized = validation.classification.strip().lower()

    if normalized == "success":
        summary = "Managed datastore validation successful"
    elif normalized == "unsupported":
        summary = "Managed datastore type is not installed or not supported by this validation method"
    elif normalized == "error":
        summary = "Managed datastore validation returned an error"
    elif normalized in {"failure", "failed"}:
        summary = "Managed datastore validation failed"
    elif normalized in {"warning", "warn"}:
        summary = "Managed datastore validation warning"
    else:
        summary = f"Managed datastore validation status: {validation.classification}"

    if validation.message:
        yield Result(state=state, summary=summary, details=validation.message)
    else:
        yield Result(state=state, summary=summary)

agent_section_arcgis_managed_datastore_validation = AgentSection(
    name="arcgis_managed_datastore_validation",
    parse_function=parse_arcgis_managed_datastore_validation,
)

check_plugin_arcgis_managed_datastore_validation = CheckPlugin(
    name="arcgis_managed_datastore_validation",
    service_name="ArcGIS Managed Datastore %s",
    discovery_function=discover_arcgis_managed_datastore_validation,
    check_function=check_arcgis_managed_datastore_validation,
)