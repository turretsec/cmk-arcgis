from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    Integer,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostCondition,
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


# ---------------------------------------------------------------------------
# ArcGIS services
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_services() -> Dictionary:
    return Dictionary(
        elements={
            # ---- State handling ----
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
            # ---- Usage statistics thresholds ----
            # These only apply when service stats collection is enabled and the
            # arcgis_service_stats section is present for the service.
            "failure_rate_warn": DictElement(
                parameter_form=Float(
                    title=Title("Warning threshold for request failure rate"),
                    unit_symbol="%",
                    prefill=DefaultValue(5.0),
                ),
                required=True,
            ),
            "failure_rate_crit": DictElement(
                parameter_form=Float(
                    title=Title("Critical threshold for request failure rate"),
                    unit_symbol="%",
                    prefill=DefaultValue(20.0),
                ),
                required=True,
            ),
            "failure_rate_min_requests": DictElement(
                parameter_form=Integer(
                    title=Title("Minimum requests before evaluating failure rate"),
                    prefill=DefaultValue(20),
                ),
                required=True,
            ),
            "timeout_rate_warn": DictElement(
                parameter_form=Float(
                    title=Title("Warning threshold for request timeout rate"),
                    unit_symbol="%",
                    prefill=DefaultValue(5.0),
                ),
                required=True,
            ),
            "timeout_rate_crit": DictElement(
                parameter_form=Float(
                    title=Title("Critical threshold for request timeout rate"),
                    unit_symbol="%",
                    prefill=DefaultValue(20.0),
                ),
                required=True,
            ),
            "timeout_rate_min_requests": DictElement(
                parameter_form=Integer(
                    title=Title("Minimum requests before evaluating timeout rate"),
                    prefill=DefaultValue(20),
                ),
                required=True,
            ),
            "avg_response_time_warn": DictElement(
                parameter_form=Integer(
                    title=Title("Warning threshold for average response time"),
                    unit_symbol="ms",
                    prefill=DefaultValue(5000),
                ),
                required=False,
            ),
            "avg_response_time_crit": DictElement(
                parameter_form=Integer(
                    title=Title("Critical threshold for average response time"),
                    unit_symbol="ms",
                    prefill=DefaultValue(30000),
                ),
                required=False,
            ),
            "max_response_time_warn": DictElement(
                parameter_form=Integer(
                    title=Title("Warning threshold for maximum response time"),
                    unit_symbol="ms",
                    prefill=DefaultValue(30000),
                ),
                required=False,
            ),
            "max_response_time_crit": DictElement(
                parameter_form=Integer(
                    title=Title("Critical threshold for maximum response time"),
                    unit_symbol="ms",
                    prefill=DefaultValue(60000),
                ),
                required=False,
            ),
        }
    )


rule_spec_arcgis_services = CheckParameters(
    name="arcgis_services",
    title=Title("ArcGIS service state and usage statistics"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_services,
    condition=HostAndItemCondition(item_title=Title("ArcGIS service")),
)


# ---------------------------------------------------------------------------
# Log settings
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_log_settings() -> Dictionary:
    return Dictionary(
        elements={
            "info_state": DictElement(
                parameter_form=_state_choice(
                    "State when log level is INFO",
                    "warn",
                ),
                required=True,
            ),
            "off_state": DictElement(
                parameter_form=_state_choice(
                    "State when logging is OFF",
                    "warn",
                ),
                required=True,
            ),
            "debug_state": DictElement(
                parameter_form=_state_choice(
                    "State when log level is DEBUG/FINE/VERBOSE",
                    "crit",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when log level is unknown or empty",
                    "unknown",
                ),
                required=True,
            ),
            "unexpected_state": DictElement(
                parameter_form=_state_choice(
                    "State for unexpected log levels",
                    "warn",
                ),
                required=True,
            ),
            "retention_unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when log retention is unknown",
                    "unknown",
                ),
                required=True,
            ),
            "retention_outside_range_state": DictElement(
                parameter_form=_state_choice(
                    "State when log retention is outside expected range",
                    "warn",
                ),
                required=True,
            ),
            "retention_min_days": DictElement(
                parameter_form=Integer(
                    title=Title("Minimum expected log retention"),
                    unit_symbol="days",
                    prefill=DefaultValue(7),
                ),
                required=True,
            ),
            "retention_max_days": DictElement(
                parameter_form=Integer(
                    title=Title("Maximum expected log retention"),
                    unit_symbol="days",
                    prefill=DefaultValue(365),
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_log_settings = CheckParameters(
    name="arcgis_log_settings",
    title=Title("ArcGIS log settings policy"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_log_settings,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Server machines
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_server_machines() -> Dictionary:
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
                    "warn",
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
                    "State for STARTING or STOPPING machines",
                    "warn",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State for unknown or unexpected machine states",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_server_machines = CheckParameters(
    name="arcgis_server_machines",
    title=Title("ArcGIS Server machine state handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_server_machines,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS Server machine"),
    ),
)


# ---------------------------------------------------------------------------
# Datastores (Managed and Registered)
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_datastore_validation() -> Dictionary:
    return Dictionary(
        elements={
            "success_state": DictElement(
                parameter_form=_state_choice("State for successful validation", "ok"),
                required=True,
            ),
            "warning_state": DictElement(
                parameter_form=_state_choice("State for validation warnings", "warn"),
                required=True,
            ),
            "failure_state": DictElement(
                parameter_form=_state_choice("State for validation failures", "crit"),
                required=True,
            ),
            "error_state": DictElement(
                parameter_form=_state_choice("State for validation errors", "crit"),
                required=True,
            ),
            "unsupported_state": DictElement(
                parameter_form=_state_choice(
                    "State for unsupported managed datastore validations",
                    "ok",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice("State for unknown validation results", "unknown"),
                required=True,
            ),
        }
    )


rule_spec_arcgis_datastore_validation = CheckParameters(
    name="arcgis_datastore_validation",
    title=Title("ArcGIS datastore validation handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_datastore_validation,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS datastore"),
    ),
)


# ---------------------------------------------------------------------------
# ArcGIS Portal License
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_portal_license() -> Dictionary:
    return Dictionary(
        elements={
            "usage_warn_percent": DictElement(
                parameter_form=Float(
                    title=Title("Warning level for license usage"),
                    unit_symbol="%",
                    prefill=DefaultValue(85.0),
                ),
                required=True,
            ),
            "usage_crit_percent": DictElement(
                parameter_form=Float(
                    title=Title("Critical level for license usage"),
                    unit_symbol="%",
                    prefill=DefaultValue(95.0),
                ),
                required=True,
            ),
            "expiration_warn_days": DictElement(
                parameter_form=Integer(
                    title=Title("Warning level for days until expiration"),
                    unit_symbol="days",
                    prefill=DefaultValue(90),
                ),
                required=True,
            ),
            "expiration_crit_days": DictElement(
                parameter_form=Integer(
                    title=Title("Critical level for days until expiration"),
                    unit_symbol="days",
                    prefill=DefaultValue(30),
                ),
                required=True,
            ),
            "maximum_unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when maximum license count is unknown",
                    "unknown",
                ),
                required=True,
            ),
            "expired_state": DictElement(
                parameter_form=_state_choice("State when license is expired", "crit"),
                required=True,
            ),
        }
    )


rule_spec_arcgis_portal_license = CheckParameters(
    name="arcgis_portal_license",
    title=Title("ArcGIS Portal license thresholds"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_portal_license,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS Portal license item"),
    ),
)


# ---------------------------------------------------------------------------
# Server License
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_server_license() -> Dictionary:
    return Dictionary(
        elements={
            "expiration_warn_days": DictElement(
                parameter_form=Integer(
                    title=Title("Warning level for days until expiration"),
                    unit_symbol="days",
                    prefill=DefaultValue(90),
                ),
                required=True,
            ),
            "expiration_crit_days": DictElement(
                parameter_form=Integer(
                    title=Title("Critical level for days until expiration"),
                    unit_symbol="days",
                    prefill=DefaultValue(30),
                ),
                required=True,
            ),
            "expired_state": DictElement(
                parameter_form=_state_choice("State when license is expired", "crit"),
                required=True,
            ),
            "invalid_feature_state": DictElement(
                parameter_form=_state_choice(
                    "State when a licensed feature is invalid",
                    "crit",
                ),
                required=True,
            ),
            "unknown_expiration_state": DictElement(
                parameter_form=_state_choice("State when expiration is unknown", "unknown"),
                required=True,
            ),
            "missing_license_state": DictElement(
                parameter_form=_state_choice(
                    "State when license item is missing from agent output",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_server_license = CheckParameters(
    name="arcgis_server_license",
    title=Title("ArcGIS Server license thresholds"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_server_license,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS Server license item"),
    ),
)


# ---------------------------------------------------------------------------
# Portal Index
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_portal_indexer() -> Dictionary:
    return Dictionary(
        elements={
            "mismatch_state": DictElement(
                parameter_form=_state_choice(
                    "State when database count and index count differ",
                    "crit",
                ),
                required=True,
            ),
            "missing_index_state": DictElement(
                parameter_form=_state_choice(
                    "State when index item is missing from agent output",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_portal_indexer = CheckParameters(
    name="arcgis_portal_indexer",
    title=Title("ArcGIS Portal index count handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_portal_indexer,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS Portal index"),
    ),
)


# ---------------------------------------------------------------------------
# Portal Index Sync
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_portal_indexer_sync() -> Dictionary:
    return Dictionary(
        elements={
            "sync_false_state": DictElement(
                parameter_form=_state_choice(
                    "State when Portal index sync is unhealthy",
                    "crit",
                ),
                required=True,
            ),
            "sync_unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when Portal index sync status is unknown",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_portal_indexer_sync = CheckParameters(
    name="arcgis_portal_indexer_sync",
    title=Title("ArcGIS Portal index sync handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_portal_indexer_sync,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Federated Server Status
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_portal_federation_servers() -> Dictionary:
    return Dictionary(
        elements={
            "warning_state": DictElement(
                parameter_form=_state_choice(
                    "State when a federated server reports warnings",
                    "warn",
                ),
                required=True,
            ),
            "failed_state": DictElement(
                parameter_form=_state_choice(
                    "State when a federated server is unhealthy",
                    "crit",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when federated server status is unknown",
                    "unknown",
                ),
                required=True,
            ),
            "missing_server_state": DictElement(
                parameter_form=_state_choice(
                    "State when federated server is missing from agent output",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_portal_federation_servers = CheckParameters(
    name="arcgis_portal_federation_servers",
    title=Title("ArcGIS federated server handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_portal_federation_servers,
    condition=HostAndItemCondition(
        item_title=Title("ArcGIS federated server"),
    ),
)


def _parameter_form_arcgis_portal_federation_status() -> Dictionary:
    return Dictionary(
        elements={
            "warning_state": DictElement(
                parameter_form=_state_choice(
                    "State when federation reports warnings",
                    "warn",
                ),
                required=True,
            ),
            "failed_state": DictElement(
                parameter_form=_state_choice(
                    "State when federation is unhealthy",
                    "crit",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when federation status is unknown",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_portal_federation_status = CheckParameters(
    name="arcgis_portal_federation_status",
    title=Title("ArcGIS Portal federation status handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_portal_federation_status,
    condition=HostCondition(),
)


# ---------------------------------------------------------------------------
# Collection status
# ---------------------------------------------------------------------------

def _parameter_form_arcgis_collection_status() -> Dictionary:
    return Dictionary(
        elements={
            "warning_state": DictElement(
                parameter_form=_state_choice(
                    "State when a collection step reports a warning",
                    "warn",
                ),
                required=True,
            ),
            "skipped_state": DictElement(
                parameter_form=_state_choice(
                    "State when a collection step is skipped",
                    "warn",
                ),
                required=True,
            ),
            "error_state": DictElement(
                parameter_form=_state_choice(
                    "State when a collection step reports an error",
                    "crit",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when collection status is unknown",
                    "unknown",
                ),
                required=True,
            ),
        }
    )


rule_spec_arcgis_collection_status = CheckParameters(
    name="arcgis_collection_status",
    title=Title("ArcGIS collection status handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_collection_status,
    condition=HostCondition(),
)

# ---------------------------------------------------------------------------
# Server mode
# ---------------------------------------------------------------------------
 
def _parameter_form_arcgis_server_mode() -> Dictionary:
    return Dictionary(
        elements={
            "read_only_state": DictElement(
                parameter_form=_state_choice(
                    "State when site is in READ_ONLY mode",
                    "warn",
                ),
                required=True,
            ),
            "unknown_state": DictElement(
                parameter_form=_state_choice(
                    "State when site mode is unknown or unexpected",
                    "unknown",
                ),
                required=True,
            ),
        }
    )
 
 
rule_spec_arcgis_server_mode = CheckParameters(
    name="arcgis_server_mode",
    title=Title("ArcGIS Server mode handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_server_mode,
    condition=HostCondition(),
)
 
 
# ---------------------------------------------------------------------------
# Web adaptors
# ---------------------------------------------------------------------------
 
def _parameter_form_arcgis_web_adaptors() -> Dictionary:
    return Dictionary(
        elements={
            "missing_state": DictElement(
                parameter_form=_state_choice(
                    "State when a web adaptor is no longer registered",
                    "crit",
                ),
                required=True,
            ),
            "admin_enabled_state": DictElement(
                parameter_form=_state_choice(
                    "State when admin access is enabled on a web adaptor",
                    "warn",
                ),
                required=True,
            ),
        }
    )
 
 
rule_spec_arcgis_web_adaptors = CheckParameters(
    name="arcgis_web_adaptors",
    title=Title("ArcGIS web adaptor handling"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_arcgis_web_adaptors,
    condition=HostAndItemCondition(
        item_title=Title("Web adaptor URL"),
    ),
)