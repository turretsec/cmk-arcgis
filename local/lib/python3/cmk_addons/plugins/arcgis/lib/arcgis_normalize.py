from cmk_addons.plugins.arcgis.lib.arcgis_models import (
    RegisteredDataStoreHealth,
)

def normalize_registered_datastore_validation(
    item_path: str,
    store_type: str,
    response: dict,
) -> list[RegisteredDataStoreHealth]:
    # Simple success shape
    if response.get("status") == "success":
        return [
            RegisteredDataStoreHealth(
                path=item_path,
                store_type=store_type,
                status="success",
                message="Validation successful",
            )
        ]

    # Machine/detail shape
    machines = response.get("machines", [])
    if machines:
        results = []

        for machine in machines:
            machine_name = machine.get("machine", "unknown")
            machine_status = machine.get("status", "unknown")

            data_items = machine.get("dataItems", [])

            if not data_items:
                results.append(
                    RegisteredDataStoreHealth(
                        path=item_path,
                        store_type=store_type,
                        status=machine_status,
                        machine=machine_name,
                        message=f"Machine validation status: {machine_status}",
                    )
                )
                continue

            for data_item in data_items:
                validation_state = data_item.get("validationState", "UNKNOWN")
                message = data_item.get("message", "")
                path_message = data_item.get("path", "")

                status = (
                    "success"
                    if validation_state.upper() in {"PASSED", "SUCCESS"}
                    else "failure"
                )

                full_message = " - ".join(
                    part for part in [message, path_message] if part
                )

                results.append(
                    RegisteredDataStoreHealth(
                        path=data_item.get("dataItem", item_path),
                        store_type=store_type,
                        status=status,
                        machine=machine_name,
                        message=full_message,
                    )
                )

        return results

    # Fallback weird shape
    return [
        RegisteredDataStoreHealth(
            path=item_path,
            store_type=store_type,
            status="unknown",
            message=f"Unexpected validation response: {response}",
        )
    ]

def classify_managed_datastore_response(response: dict) -> tuple[str, str]:
    status = str(response.get("status", "")).lower()
    messages = response.get("messages", [])
    message = " ".join(str(m) for m in messages)

    lowered = message.lower()

    if "not installed in the current configuration" in lowered:
        return "unsupported", message

    if "validation path" in lowered and "could not be determined" in lowered:
        return "unsupported", message

    if "could not find resource or operation 'validate'" in lowered:
        return "unsupported", message

    if status == "success":
        return "success", message

    if status == "error":
        return "error", message

    return "unknown", message