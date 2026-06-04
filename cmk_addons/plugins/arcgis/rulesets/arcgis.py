from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    Integer,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
    Password,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _server_filter_form() -> Dictionary:
    return Dictionary(
        title=Title("Federated server filtering"),
        help_text=Help(
            "Optional regular expressions used to limit which federated ArcGIS "
            "servers are collected. Patterns are matched against the server name, "
            "URL, and admin URL. Exclude rules win over include rules."
        ),
        elements={
            "include_patterns": DictElement(
                parameter_form=List(
                    title=Title("Only collect federated servers matching"),
                    element_template=String(
                        title=Title("Regular expression"),
                        field_size=FieldSize.LARGE,
                    ),
                    add_element_label=Label("Add include pattern"),
                ),
                required=False,
            ),
            "exclude_patterns": DictElement(
                parameter_form=List(
                    title=Title("Do not collect federated servers matching"),
                    element_template=String(
                        title=Title("Regular expression"),
                        field_size=FieldSize.LARGE,
                    ),
                    add_element_label=Label("Add exclude pattern"),
                ),
                required=False,
            ),
        },
    )


def _cache_interval(title: str, default: int) -> Integer:
    return Integer(
        title=Title(title),
        unit_symbol="seconds",
        prefill=DefaultValue(default),
    )


def _collection_toggle(title: str, label: str, default: bool = True) -> BooleanChoice:
    return BooleanChoice(
        title=Title(title),
        label=Label(label),
        prefill=DefaultValue(default),
    )


def _cache_intervals_form() -> Dictionary:
    return Dictionary(
        title=Title("Cache intervals"),
        help_text=Help(
            "Controls the cache age written to the agent section headers. "
            "Set to 0 to disable Checkmk section caching for that collection."
        ),
        elements={
            "portal_federation": DictElement(
                parameter_form=_cache_interval("Portal federation validation", 300),
                required=False,
            ),
            "portal_license": DictElement(
                parameter_form=_cache_interval("Portal license", 3600),
                required=False,
            ),
            "portal_log_settings": DictElement(
                parameter_form=_cache_interval("Portal log settings", 3600),
                required=False,
            ),
            "server_machines": DictElement(
                parameter_form=_cache_interval("Server machines", 300),
                required=False,
            ),
            "registered_datastores": DictElement(
                parameter_form=_cache_interval("Registered datastore validation", 900),
                required=False,
            ),
            "managed_datastores": DictElement(
                parameter_form=_cache_interval("Managed datastore validation", 900),
                required=False,
            ),
            "server_license": DictElement(
                parameter_form=_cache_interval("Server license", 3600),
                required=False,
            ),
            "server_log_settings": DictElement(
                parameter_form=_cache_interval("Server log settings", 3600),
                required=False,
            ),
            "service_stats": DictElement(
                parameter_form=_cache_interval("Service usage statistics", 300),
                required=False,
            ),
            "web_adaptors": DictElement(
                parameter_form=_cache_interval("Web adaptors", 300),
                required=False,
            ),
            "server_logs": DictElement(
                parameter_form=_cache_interval("Server log query", 300),
                required=False,
            ),
        },
    )


def _collections_form() -> Dictionary:
    return Dictionary(
        title=Title("Collection scope"),
        elements={
            "portal_health": DictElement(
                parameter_form=_collection_toggle(
                    "Portal health",
                    "Collect Portal machine health",
                ),
                required=False,
            ),
            "portal_indexer": DictElement(
                parameter_form=_collection_toggle(
                    "Portal indexer",
                    "Collect Portal indexer status",
                ),
                required=False,
            ),
            "portal_federation": DictElement(
                parameter_form=_collection_toggle(
                    "Portal federation validation",
                    "Collect Portal federation validation",
                ),
                required=False,
            ),
            "portal_license": DictElement(
                parameter_form=_collection_toggle(
                    "Portal license",
                    "Collect Portal license information",
                ),
                required=False,
            ),
            "portal_log_settings": DictElement(
                parameter_form=_collection_toggle(
                    "Portal log settings",
                    "Collect Portal log settings",
                ),
                required=False,
            ),
            "server_machines": DictElement(
                parameter_form=_collection_toggle(
                    "Server machines",
                    "Collect ArcGIS Server machine states",
                ),
                required=False,
            ),
            "server_services": DictElement(
                parameter_form=_collection_toggle(
                    "Server services",
                    "Collect ArcGIS Server service states",
                ),
                required=False,
            ),
            "server_service_stats": DictElement(
                parameter_form=_collection_toggle(
                    "Service usage statistics",
                    "Collect ArcGIS Server service usage statistics (requires usage reports enabled on the server)",
                ),
                required=False,
            ),
            "registered_datastores": DictElement(
                parameter_form=_collection_toggle(
                    "Registered datastores",
                    "Collect registered datastore validation",
                ),
                required=False,
            ),
            "managed_datastores": DictElement(
                parameter_form=_collection_toggle(
                    "Managed datastores",
                    "Collect managed datastore validation",
                ),
                required=False,
            ),
            "server_license": DictElement(
                parameter_form=_collection_toggle(
                    "Server license",
                    "Collect ArcGIS Server license information",
                ),
                required=False,
            ),
            "server_log_settings": DictElement(
                parameter_form=_collection_toggle(
                    "Server log settings",
                    "Collect ArcGIS Server log settings",
                ),
                required=False,
            ),
            "server_mode": DictElement(
                parameter_form=_collection_toggle(
                    "Server mode",
                    "Collect ArcGIS Server site mode (EDITABLE / READ_ONLY)",
                ),
                required=False,
            ),
            "web_adaptors": DictElement(
                parameter_form=_collection_toggle(
                    "Web adaptors",
                    "Collect registered web adaptors for each ArcGIS Server site",
                ),
                required=False,
            ),
            "server_logs": DictElement(
                parameter_form=_collection_toggle(
                    "Server logs",
                    "Collect recent SEVERE and WARNING log entries from each ArcGIS Server",
                ),
                required=False,
            ),
        },
    )


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
                    help_text=Help(
                        "Base URL of your Portal e.g. https://portal.example.com/arcgis"
                    ),
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
            "service_stats_since": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Service statistics time window"),
                    help_text=Help(
                        "Time window used when querying service usage statistics. "
                        "Last hour uses a rolling CUSTOM window (now minus 60 minutes) "
                        "with 10-minute aggregation intervals, matching the behavior of "
                        "ArcGIS Monitor dashboards. Longer windows give trend data but "
                        "metrics will lag behind real activity."
                    ),
                    elements=[
                        SingleChoiceElement(name="LAST_HOUR", title=Title("Last hour (recommended)")),
                        SingleChoiceElement(name="LAST_DAY", title=Title("Last 24 hours")),
                        SingleChoiceElement(name="LAST_WEEK", title=Title("Last 7 days")),
                        SingleChoiceElement(name="LAST_MONTH", title=Title("Last 30 days")),
                    ],
                    prefill=DefaultValue("LAST_HOUR"),
                ),
                required=False,
            ),
            "server_logs_window": DictElement(
                parameter_form=Integer(
                    title=Title("Server log query window (minutes)"),
                    help_text=Help(
                        "How far back to query for SEVERE and WARNING log entries. "
                        "Set to at least 2× the check interval to avoid gaps between "
                        "collections. Default is 15 minutes."
                    ),
                    unit_symbol="minutes",
                    prefill=DefaultValue(15),
                ),
                required=False,
            ),
            "collections": DictElement(
                parameter_form=_collections_form(),
                required=False,
            ),
            "cache_intervals": DictElement(
                parameter_form=_cache_intervals_form(),
                required=False,
            ),
            "server_filter": DictElement(
                parameter_form=_server_filter_form(),
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