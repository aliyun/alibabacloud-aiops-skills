"""SLS-only chart bindings; inherited pure display/shape logic."""

from .legend_defaults import legend_option


def display_patch(legend_multi: bool = False) -> dict:
    patch = {
        "isTimeSeries": True,
        "graphOptions": {
            "seriesStyle": "lines",
            "lineInterpolation": "linear",
            "lineWidth": 1.5,
            "showPoint": "never",
            "fillOpacity": 0,
            "gradientMode": "opacity",
        },
        "legendOption": legend_option("linepro"),
        "tooltipOption": {"mode": "all" if legend_multi else "single", "sortOrder": "none"},
        "xAxisOption": {
            "show": True,
            "timeRangeMode": "dataTime",
            "zoomTarget": "global",
        },
        "yAxisOption": {
            "show": True,
            "position": 3,
            "stackingMode": "none",
        },
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
        },
    }
    return patch
