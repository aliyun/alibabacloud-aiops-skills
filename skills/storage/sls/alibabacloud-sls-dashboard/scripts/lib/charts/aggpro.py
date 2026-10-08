"""SLS-only chart bindings; inherited pure display/shape logic."""

import re

from .legend_defaults import legend_option

METRIC_DATASOURCES = {"metricstore", "metricstore_storeview"}

LOGSTORE_DATASOURCES = {"logstore"}

_LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_BY_RE = re.compile(r"\bby\s*\(([^()]*)\)", re.IGNORECASE)

_UNSAFE_GROUPING_RE = re.compile(
    r"\b(?:without|group_left|group_right)\s*\(",
    re.IGNORECASE,
)

_DASHBOARD_TOKEN_RE = re.compile(r"\$\{\{.*?\}\}|\$\{[^{}]*\}", re.DOTALL)

_STRING_RE = re.compile(
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`',
    re.DOTALL,
)

def _chart_name(chart: dict) -> str:
    return chart.get("key") or chart.get("title") or "aggpro"

def direct_binding(chart: dict) -> dict:
    """Build the explicit Direct Logstore binding."""
    chart_name = _chart_name(chart)
    agg = chart.get("agg")
    if not isinstance(agg, dict):
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires an agg object at charts[].agg"
        )
    unknown = sorted(set(agg) - {"valueField", "aggField"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg has unsupported field(s): "
            + ", ".join(unknown)
        )
    value_field = str(agg.get("valueField", "") or "").strip()
    agg_field = str(agg.get("aggField", "") or "").strip()
    if not value_field or not agg_field:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) charts[].agg requires "
            "valueField and aggField"
        )
    if value_field == agg_field:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField and agg.aggField must differ"
        )

    entries = chart.get("datasources", []) or []
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires exactly one datasource query"
        )
    raw_fields = entries[0].get("queryResultFields")
    if not isinstance(raw_fields, list):
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires queryResultFields"
        )

    fields = {}
    time_fields = []
    for field in raw_fields:
        if not isinstance(field, dict):
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queryResultFields entries must be objects"
            )
        name = str(field.get("name", "") or "").strip()
        data_type = str(field.get("dataType", "") or "").strip().lower()
        if not name:
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queryResultFields requires non-empty names"
            )
        if name in fields:
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queryResultFields contains duplicate "
                f"field {name!r}"
            )
        fields[name] = data_type
        if data_type == "time":
            time_fields.append(name)

    if len(time_fields) != 1:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires exactly one queryResultFields "
            "entry with dataType=time"
        )
    if value_field not in fields:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField {value_field!r} "
            "is absent from queryResultFields"
        )
    if fields[value_field] != "number":
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField {value_field!r} "
            "must have dataType=number"
        )
    if agg_field not in fields:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.aggField {agg_field!r} "
            "is absent from queryResultFields"
        )
    if fields[agg_field] != "string":
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.aggField {agg_field!r} "
            "must have dataType=string"
        )
    return {
        "xAxisKey": time_fields[0],
        "yAxisKey": value_field,
        "aggField": agg_field,
    }

def display_patch(query_option_map: dict) -> dict:
    return {
        "isTimeSeries": True,
        "queryOptionMap": query_option_map,
        "graphOptions": {
            "lineInterpolation": "smooth",
            "lineWidth": 1.5,
            "showPoint": "always",
            "fillOpacity": 40,
            "gradientMode": "opacity",
        },
        "legendOption": legend_option("aggpro"),
        "tooltipOption": {"mode": "all", "sortOrder": "none"},
        "yAxisOption": {"show": True, "position": 3, "stackingMode": "none"},
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
        },
    }

def direct_display_patch(chart: dict) -> dict:
    return display_patch({"A": direct_binding(chart)})
