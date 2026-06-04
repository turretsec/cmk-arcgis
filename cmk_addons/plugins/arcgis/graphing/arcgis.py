# Covers all metrics yielded by the arcgis_services check plugin when the
# arcgis_service_stats section is present.

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.metrics import (
    Color,
    CriticalOf,
    DecimalNotation,
    Metric,
    Unit,
    WarningOf,
)
from cmk.graphing.v1.perfometers import (
    Closed,
    FocusRange,
    Open,
    Perfometer,
)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

# Request volume

metric_arcgis_request_count = Metric(
    name="arcgis_request_count",
    title=Title("Total requests"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
 
metric_arcgis_requests_per_second = Metric(
    name="arcgis_requests_per_second",
    title=Title("Requests per second"),
    unit=Unit(DecimalNotation("/s")),
    color=Color.BLUE,
)
 
# Failures
 
metric_arcgis_failed_requests = Metric(
    name="arcgis_failed_requests",
    title=Title("Failed requests"),
    unit=Unit(DecimalNotation("")),
    color=Color.RED,
)
 
metric_arcgis_failure_rate = Metric(
    name="arcgis_failure_rate",
    title=Title("Failure rate"),
    unit=Unit(DecimalNotation("%")),
    color=Color.RED,
)
 
# Timeouts
 
metric_arcgis_timed_out_requests = Metric(
    name="arcgis_timed_out_requests",
    title=Title("Timed-out requests"),
    unit=Unit(DecimalNotation("")),
    color=Color.ORANGE,
)
 
metric_arcgis_timeout_rate = Metric(
    name="arcgis_timeout_rate",
    title=Title("Timeout rate"),
    unit=Unit(DecimalNotation("%")),
    color=Color.ORANGE,
)
 
# Response times (milliseconds)
 
metric_arcgis_avg_response_time = Metric(
    name="arcgis_avg_response_time",
    title=Title("Avg response time"),
    unit=Unit(DecimalNotation("ms")),
    color=Color.GREEN,
)
 
metric_arcgis_max_response_time = Metric(
    name="arcgis_max_response_time",
    title=Title("Max response time"),
    unit=Unit(DecimalNotation("ms")),
    color=Color.YELLOW,
)
 
# Wait times (milliseconds)
# Only present when requests were queued waiting for a free instance.
 
metric_arcgis_avg_wait_time = Metric(
    name="arcgis_avg_wait_time",
    title=Title("Avg instance wait time"),
    unit=Unit(DecimalNotation("ms")),
    color=Color.PURPLE,
)
 
metric_arcgis_max_wait_time = Metric(
    name="arcgis_max_wait_time",
    title=Title("Max instance wait time"),
    unit=Unit(DecimalNotation("ms")),
    color=Color.PINK,
)
 
# Instance pool
 
metric_arcgis_max_running_instances = Metric(
    name="arcgis_max_running_instances",
    title=Title("Max running instances"),
    unit=Unit(DecimalNotation("")),
    color=Color.PURPLE,
)
 
 
# ---------------------------------------------------------------------------
# Perfometer
# ---------------------------------------------------------------------------
# Shows requests/sec as an activity indicator in the service table.
# The focus range is Open(10) so the scale auto-extends for very busy
# services, but a service doing ~1–10 req/s fills roughly half the bar,
# giving a meaningful impression.
# ---------------------------------------------------------------------------
 
perfometer_arcgis_services = Perfometer(
    name="arcgis_services",
    focus_range=FocusRange(Closed(0), Open(10)),
    segments=["arcgis_requests_per_second"],
)
 
 
# ---------------------------------------------------------------------------
# Graph templates
# ---------------------------------------------------------------------------
 
# 1. Request rate - single metric, area fill, auto-scaled
graph_arcgis_request_rate = Graph(
    name="arcgis_request_rate",
    title=Title("Request Rate"),
    compound_lines=["arcgis_requests_per_second"],
)
 
# 2. Failure & timeout rates - stacked areas so the two rates don't hide
#    each other, plus dashed warn/crit threshold lines pulled from the
#    levels stored on arcgis_failure_rate by the check plugin.
#    MinimalRange(0, 5) keeps the Y-axis at ≥ 5 % height so a tiny spike
#    is still visible and not visually zero on a zoomed-out axis.
graph_arcgis_failure_timeout_rates = Graph(
    name="arcgis_failure_timeout_rates",
    title=Title("Failure & Timeout Rates"),
    minimal_range=MinimalRange(0, 5),
    compound_lines=[
        "arcgis_failure_rate",
        "arcgis_timeout_rate",
    ],
    simple_lines=[
        WarningOf("arcgis_failure_rate"),
        CriticalOf("arcgis_failure_rate"),
    ],
    optional=["arcgis_timeout_rate"],
)
 
# 3. Response & wait times - avg response time as filled area (primary
#    signal), max response time as a line overlay (spike detection), and
#    wait times as optional lines that only appear when instance queuing
#    occurred.  All share the same ms axis so spikes stand out clearly.
graph_arcgis_response_times = Graph(
    name="arcgis_response_times",
    title=Title("Response & Wait Times"),
    compound_lines=["arcgis_avg_response_time"],
    simple_lines=[
        "arcgis_max_response_time",
        "arcgis_avg_wait_time",
        "arcgis_max_wait_time",
    ],
    optional=[
        "arcgis_avg_wait_time",
        "arcgis_max_wait_time",
    ],
)
 
# 4. Instance pool - how many ArcSOC instances peaked during the window.
#    Lets operators spot capacity pressure without needing a dedicated
#    service (comparable to ArcGIS Monitor's "Instance Used" panel).
graph_arcgis_instance_utilization = Graph(
    name="arcgis_instance_utilization",
    title=Title("Running Instances"),
    compound_lines=["arcgis_max_running_instances"],
)
 
 
# ---------------------------------------------------------------------------
# Portal Indexer metrics
# ---------------------------------------------------------------------------
 
metric_arcgis_index_database_count = Metric(
    name="arcgis_index_database_count",
    title=Title("Database count"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
 
metric_arcgis_index_count = Metric(
    name="arcgis_index_count",
    title=Title("Index count"),
    unit=Unit(DecimalNotation("")),
    color=Color.GREEN,
)
 
# Both counts on the same graph: when in sync the lines overlap perfectly.
# Any visible gap means the index is drifting behind the database, which is
# the key signal this check is designed to catch.
graph_arcgis_portal_index_counts = Graph(
    name="arcgis_portal_index_counts",
    title=Title("Portal Index vs Database Count"),
    simple_lines=[
        "arcgis_index_database_count",
        "arcgis_index_count",
    ],
)
 
 
# ---------------------------------------------------------------------------
# License metrics
# ---------------------------------------------------------------------------
 
# Portal summary (named-user members)
metric_arcgis_portal_members_used = Metric(
    name="arcgis_portal_members_used",
    title=Title("Members used"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
 
metric_arcgis_portal_member_usage_percent = Metric(
    name="arcgis_portal_member_usage_percent",
    title=Title("Member license usage"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)
 
# Portal per-item / server license usage
metric_arcgis_license_used = Metric(
    name="arcgis_license_used",
    title=Title("Licenses used"),
    unit=Unit(DecimalNotation("")),
    color=Color.BLUE,
)
 
metric_arcgis_license_usage_percent = Metric(
    name="arcgis_license_usage_percent",
    title=Title("License usage"),
    unit=Unit(DecimalNotation("%")),
    color=Color.BLUE,
)
 
# Days remaining (portal per-item + server license)
metric_arcgis_license_expiration_days = Metric(
    name="arcgis_license_expiration_days",
    title=Title("Days until expiration"),
    unit=Unit(DecimalNotation(" days")),
    color=Color.YELLOW,
)
 
 
# ---------------------------------------------------------------------------
# License perfometers
# ---------------------------------------------------------------------------
 
# Portal member usage: fills 0→100% as members are consumed.
perfometer_arcgis_portal_license = Perfometer(
    name="arcgis_portal_license",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["arcgis_portal_member_usage_percent"],
)
 
# Per-item license usage (portal license items that have counts).
perfometer_arcgis_license_usage = Perfometer(
    name="arcgis_license_usage",
    focus_range=FocusRange(Closed(0), Closed(100)),
    segments=["arcgis_license_usage_percent"],
)
 
 
# ---------------------------------------------------------------------------
# License graphs
# ---------------------------------------------------------------------------
 
# Portal member usage with warn/crit threshold lines.
graph_arcgis_portal_member_usage = Graph(
    name="arcgis_portal_member_usage",
    title=Title("Portal Member License Usage"),
    minimal_range=MinimalRange(0, 100),
    compound_lines=["arcgis_portal_member_usage_percent"],
    simple_lines=[
        WarningOf("arcgis_portal_member_usage_percent"),
        CriticalOf("arcgis_portal_member_usage_percent"),
    ],
)
 
# Per-item license usage - applies to portal per-item checks.
graph_arcgis_license_usage = Graph(
    name="arcgis_license_usage",
    title=Title("License Usage"),
    minimal_range=MinimalRange(0, 100),
    compound_lines=["arcgis_license_usage_percent"],
    simple_lines=[
        WarningOf("arcgis_license_usage_percent"),
        CriticalOf("arcgis_license_usage_percent"),
    ],
)
 
# Days until expiration - a declining trend line approaching zero.
# MinimalRange(0, 365) keeps the y-axis readable even for licenses with
# years remaining; the line will visibly approach the x-axis as expiry nears.
graph_arcgis_license_expiration = Graph(
    name="arcgis_license_expiration",
    title=Title("Days Until License Expiration"),
    minimal_range=MinimalRange(0, 365),
    compound_lines=["arcgis_license_expiration_days"],
)
 
 
# ---------------------------------------------------------------------------
# Server log metrics
# ---------------------------------------------------------------------------
 
metric_arcgis_severe_log_count = Metric(
    name="arcgis_severe_log_count",
    title=Title("Severe log errors"),
    unit=Unit(DecimalNotation("")),
    color=Color.RED,
)
 
metric_arcgis_warning_log_count = Metric(
    name="arcgis_warning_log_count",
    title=Title("Warning log messages"),
    unit=Unit(DecimalNotation("")),
    color=Color.ORANGE,
)
 
# Perfometer: severe error count as a 0–Open(10) bar.  An empty bar means
# a clean server.  Any fill at all is immediately visible in the service list.
perfometer_arcgis_server_logs = Perfometer(
    name="arcgis_server_logs",
    focus_range=FocusRange(Closed(0), Open(10)),
    segments=["arcgis_severe_log_count"],
)
 
# Graph: severe errors as a filled area (the critical signal) with warning
# counts as an overlay line. Threshold lines show the configured warn/crit
# levels for SEVERE directly on the chart.
graph_arcgis_server_log_counts = Graph(
    name="arcgis_server_log_counts",
    title=Title("Server Log Error Counts"),
    compound_lines=["arcgis_severe_log_count"],
    simple_lines=[
        "arcgis_warning_log_count",
        WarningOf("arcgis_severe_log_count"),
        CriticalOf("arcgis_severe_log_count"),
    ],
    optional=["arcgis_warning_log_count"],
)