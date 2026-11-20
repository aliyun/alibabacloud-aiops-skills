"""Build chart display options from Plan queries and chart-specific config."""

from .legend_defaults import legend_option


def _chart_name(chart: dict) -> str:
    return chart.get("id") or chart.get("title") or "aggpro"


def direct_binding(chart: dict) -> dict:
    """Build the explicit Direct Logstore binding."""
    chart_name = _chart_name(chart)
    agg = chart.get("config", {}).get("agg")
    if not isinstance(agg, dict):
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires an agg object at charts[].config.agg"
        )
    unknown = sorted(set(agg) - {"valueField", "aggField"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg has unsupported field(s): " + ", ".join(unknown)
        )
    value_field = str(agg.get("valueField", "") or "").strip()
    agg_field = str(agg.get("aggField", "") or "").strip()
    if not value_field or not agg_field:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) charts[].config.agg requires " "valueField and aggField"
        )
    if value_field == agg_field:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField and agg.aggField must differ"
        )

    entries = chart.get("queries", []) or []
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ValueError(f"chart {chart_name!r} (aggpro) requires exactly one query")
    raw_fields = entries[0].get("fields", [])
    if not isinstance(raw_fields, list):
        raise ValueError(f"chart {chart_name!r} (aggpro) requires queries[].fields")

    fields = {}
    time_fields = []
    for field in raw_fields:
        if not isinstance(field, dict):
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queries[].fields entries must be objects"
            )
        name = str(field.get("name", "") or "").strip()
        data_type = str(field.get("type", "") or "").strip().lower()
        if not name:
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queries[].fields requires non-empty names"
            )
        if name in fields:
            raise ValueError(
                f"chart {chart_name!r} (aggpro) queries[].fields contains duplicate "
                f"field {name!r}"
            )
        fields[name] = data_type
        if data_type == "time":
            time_fields.append(name)

    if len(time_fields) != 1:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) requires exactly one queries[].fields "
            "entry with type=time"
        )
    if value_field not in fields:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField {value_field!r} "
            "is absent from queries[].fields"
        )
    if fields[value_field] != "number":
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.valueField {value_field!r} " "must have type=number"
        )
    if agg_field not in fields:
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.aggField {agg_field!r} "
            "is absent from queries[].fields"
        )
    if fields[agg_field] != "string":
        raise ValueError(
            f"chart {chart_name!r} (aggpro) agg.aggField {agg_field!r} " "must have type=string"
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
    binding = direct_binding(chart)
    return display_patch({chart["queries"][0]["name"]: binding})
