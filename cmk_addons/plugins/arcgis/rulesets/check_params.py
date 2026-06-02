from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    Topic,
)

def _state_choice(title: str, default: str) -> SingleChoice:
    return SingleChoice(
        title=Title(title),
        elements=[
            SingleChoiceElement(name="ok", title=Title("OK")),
            SingleChoiceElement(name="warn", title=Title("WARN")),
            SingleChoiceElement(name="crit", title=Title("CRIT")),
            SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
        ],
        prefill=DefaultValue(default),
    )

def _parameter_form_arcgis_services() -> Dictionary:
    return Dictionary(
        elements={
            "started_not_started_state": DictElement(
                parameter_form=_state_choice(
                    "State when configured STARTED but realtime is not STARTED",
                    "crit",
                ),
                required=True,
            ),
            "stopped_stopped_state": DictElement(
                parameter_form=_state_choice(
                    "State when configured STOPPED and realtime STOPPED",
                    "ok",
                ),
                required=True,
            ),
            "stopped_not_stopped_state": DictElement(
                parameter_form=_state_choice(
                    "State when configured STOPPED but realtime is not STOPPED",
                    "warn",
                ),
                required=True,
            ),
            "transitional_state": DictElement(
                parameter_form=_state_choice(
                    "State for STARTING or STOPPING services",
                    "warn",
                ),
                required=True,
            ),
            "failed_state": DictElement(
                parameter_form=_state_choice(
                    "State for FAILED services",
                    "crit",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State for unknown or unexpected service states",
                    "unknown",
                ),
                required=True,
            ),
        }
    )

rule_spec_arcgis_services = CheckParameters(
    name="arcgis_services",
    title=Title("ArcGIS service state handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_services,
    condition=HostAndItemCondition(item_title=Title("ArcGIS service")),
)