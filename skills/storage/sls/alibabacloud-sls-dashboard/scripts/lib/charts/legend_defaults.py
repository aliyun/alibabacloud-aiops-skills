"""SLS-only chart bindings; inherited pure display/shape logic."""

LEGEND_CHART_TYPES = {
    "aggpro",
    "barpro",
    "chinadistrictmap",
    "funnelpro",
    "histogram",
    "linepro",
    "metricspro",
    "piepro",
    "radarchart",
    "scatterchart",
    "timelinepro",
    "worlddistrictmap",
}

_NO_MODE_CHART_TYPES = {"funnelpro", "radarchart", "timelinepro"}

def legend_option(chart_type: str) -> dict:
    """Return the LinePro-aligned defaults supported by this chart type."""
    if chart_type not in LEGEND_CHART_TYPES:
        return {}
    option = {"show": True}
    if chart_type not in _NO_MODE_CHART_TYPES:
        option["mode"] = "table"
    option.update({
        "position": "bottom",
        "sortOrder": "desc",
        "actionMode": "single",
        "maxContent": 30,
    })
    return option

def display_patch(chart_type: str) -> dict:
    option = legend_option(chart_type)
    return {"legendOption": option} if option else {}
