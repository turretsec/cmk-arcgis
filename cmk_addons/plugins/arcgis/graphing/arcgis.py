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