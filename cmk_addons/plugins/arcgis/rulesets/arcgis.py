from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    String,
    Password,
    BooleanChoice,
    List,
    Integer,
    DefaultValue,
    FieldSize,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

def _parameter_form() -> Dictionary:
    return Dictionary(
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("ArcGIS admin username"),
                    field_size=FieldSize.MEDIUM,
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("ArcGIS admin password"),
                    help_text=Help("Password for the ArcGIS admin account"),
                ),
                required=True,
            ),
            "portal_url": DictElement(
                parameter_form=String(
                    title=Title("Portal URL"),
                    help_text=Help("Base URL of your Portal e.g. https://portal.example.com/arcgis"),
                    field_size=FieldSize.LARGE,
                ),
                required=True,
            ),
            "verify_ssl": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificates"),
                    label=Label("Enable SSL verification"),
                    prefill=DefaultValue(True),
                ),
                required=False,
            ),
            "token_expiry": DictElement(
                parameter_form=Integer(
                    title=Title("Token expiry (minutes)"),
                    help_text=Help("How long the admin token is valid for"),
                    prefill=DefaultValue(60),
                ),
                required=False,
            ),
        }
    )


rule_spec_arcgis = SpecialAgent(
    name="arcgis",
    title=Title("ArcGIS Enterprise"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
    help_text=Help(
        "Monitor ArcGIS Enterprise components including Portal, "
        "Server, and Image Server via the ArcGIS REST Admin API. "
        "Outputs piggyback data to the configured host objects."
    ),
)