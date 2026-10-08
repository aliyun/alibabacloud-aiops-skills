"""SLS-only chart bindings; inherited pure display/shape logic."""

from typing import Optional

from .legend_defaults import legend_option

def _display_patch(
    query_option_map: Optional[dict] = None,
    tooltip_mode: str = "single",
) -> dict:
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
        "tooltipOption": {"mode": tooltip_mode, "sortOrder": "none"},
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
    if query_option_map is not None:
        patch["queryOptionMap"] = query_option_map
    return patch

def direct_display_patch(
    chart: dict,
    x_key: str,
    y_keys: list[str],
    metricstore_like: bool,
    legend_multi: bool,
) -> dict:
    query_option_map = None
    if not metricstore_like:
        chart_name = chart.get("key") or chart.get("title") or "linepro"
        if not x_key:
            raise ValueError(
                f"chart {chart_name!r} (linepro) cannot infer a time or "
                "dimension field; declare charts[].datasources[].queryResultFields "
                "with accurate dataType values"
            )
        if not y_keys:
            raise ValueError(
                f"chart {chart_name!r} (linepro) cannot infer at least one value "
                "field; declare charts[].datasources[].queryResultFields with "
                "accurate dataType values"
            )
        query_option_map = {
            "A": {"xAxisKey": x_key, "yAxisKeys": y_keys},
        }
    return _display_patch(
        query_option_map,
        tooltip_mode="all" if legend_multi else "single",
    )
