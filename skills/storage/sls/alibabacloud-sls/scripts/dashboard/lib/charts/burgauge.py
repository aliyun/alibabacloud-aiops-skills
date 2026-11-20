"""Build chart display options from Plan queries and chart-specific config."""

from typing import Dict, List, Tuple

from ..common import METRIC as METRIC_DATASOURCES
from .common import REDUCERS
from .statpro import validate_metric_query_shape


def _chart_name(chart: dict) -> str:
    return chart.get("id") or chart.get("title") or "burgauge"


def _result_fields(chart: dict) -> Dict[str, str]:
    chart_name = _chart_name(chart)
    entries = chart.get("queries", []) or []
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ValueError(f"chart {chart_name!r} (burgauge) requires exactly one query")
    raw_fields = entries[0].get("fields", [])
    if not isinstance(raw_fields, list):
        raise ValueError(f"chart {chart_name!r} (burgauge) requires queries[].fields")

    fields = {}
    for field in raw_fields:
        if not isinstance(field, dict):
            raise ValueError(
                f"chart {chart_name!r} (burgauge) queries[].fields entries " "must be objects"
            )
        name = str(field.get("name", "") or "").strip()
        data_type = str(field.get("type", "") or "").strip().lower()
        if not name:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) queries[].fields requires " "non-empty names"
            )
        if name in fields:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) queries[].fields contains "
                f"duplicate field {name!r}"
            )
        fields[name] = data_type
    return fields


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _fixed_range(chart: dict, gauge: dict) -> dict:
    chart_name = _chart_name(chart)
    range_config = gauge.get("range")
    if not isinstance(range_config, dict):
        raise ValueError(f"chart {chart_name!r} (burgauge) metric gauge.range must be an object")
    range_mode = str(range_config.get("mode", "") or "").strip()
    unknown = sorted(set(range_config) - {"mode", "min", "max"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric gauge.range has unsupported "
            f"field(s) for mode {range_mode!r}: " + ", ".join(unknown)
        )
    if range_mode != "fixed":
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric gauge.range.mode must be " "fixed"
        )
    minimum = range_config.get("min")
    if not _number(minimum):
        raise ValueError(f"chart {chart_name!r} (burgauge) metric gauge.range.min must be a number")
    maximum = range_config.get("max")
    if not _number(maximum):
        raise ValueError(f"chart {chart_name!r} (burgauge) metric fixed range max must be a number")
    if maximum <= minimum:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric fixed range max must be " "greater than min"
        )
    return range_config


def _metric_config(chart: dict) -> Tuple[str, dict]:
    chart_name = _chart_name(chart)
    gauge = chart.get("config", {}).get("gauge")
    if not isinstance(gauge, dict):
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric datasource requires " "charts[].config.gauge"
        )
    unknown = sorted(set(gauge) - {"data", "range"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric charts[].config.gauge only supports "
            "data and range; unsupported field(s): " + ", ".join(unknown)
        )

    data = gauge.get("data")
    if not isinstance(data, dict) or set(data) != {"reducer"}:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) metric charts[].config.gauge.data "
            "requires only reducer"
        )
    reducer = str(data.get("reducer", "") or "").strip()
    if reducer not in REDUCERS:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) charts[].config.gauge.data.reducer "
            "must be one of: " + ", ".join(sorted(REDUCERS))
        )

    range_config = _fixed_range(chart, gauge)
    return reducer, range_config


def metric_binding(chart: dict, chart_queries: List[dict]) -> dict:
    """Reduce every numeric time-series field into one Gauge."""
    chart_name = _chart_name(chart)
    reducer, range_config = _metric_config(chart)
    if not isinstance(chart_queries, list) or not chart_queries:
        raise ValueError(f"chart {chart_name!r} (burgauge) requires at least one metric query")

    for query in chart_queries:
        if not isinstance(query, dict):
            raise ValueError(f"chart {chart_name!r} (burgauge) metric queries must be objects")
        datasource = str(query.get("datasource", "") or "")
        if datasource not in METRIC_DATASOURCES:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) cannot infer metric fields for "
                f"datasource {datasource!r}"
            )
        validate_metric_query_shape(chart, query, "burgauge")

    styles = {
        "displayMode": "basic",
        "minRange": range_config["min"],
        "maxRange": range_config["max"],
        "showUnfilledArea": True,
    }

    return {
        "burGaugeValueOption": {
            "showMode": "calculate",
            "calculationType": reducer,
            "layoutOrientation": "horizontal",
            "showGaugeTitle": True,
            "gaugeLabelMode": "value",
        },
        "burGaugeStylesOption": styles,
    }


def direct_binding(chart: dict) -> dict:
    chart_name = _chart_name(chart)
    gauge = chart.get("config", {}).get("gauge")
    if not isinstance(gauge, dict):
        raise ValueError(
            f"chart {chart_name!r} (burgauge) requires a gauge object at " "charts[].config.gauge"
        )
    unknown = sorted(set(gauge) - {"data", "range", "labelMode"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge has unsupported field(s): " + ", ".join(unknown)
        )

    data = gauge.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"chart {chart_name!r} (burgauge) gauge.data must be an object")
    data_mode = str(data.get("mode", "") or "").strip()
    allowed_data = (
        {"mode", "valueFields", "reducer"}
        if data_mode == "calculate"
        else {"mode", "valueFields", "labelField", "limit"}
        if data_mode == "allValues"
        else {"mode", "valueFields", "reducer", "labelField", "limit"}
    )
    unknown = sorted(set(data) - allowed_data)
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data has unsupported field(s) "
            f"for mode {data_mode!r}: " + ", ".join(unknown)
        )
    if data_mode not in {"calculate", "allValues"}:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data.mode must be " "calculate or allValues"
        )

    value_fields = data.get("valueFields")
    if (
        not isinstance(value_fields, list)
        or not value_fields
        or any(not isinstance(value, str) or not value.strip() for value in value_fields)
    ):
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data.valueFields must be "
            "a non-empty list of field names"
        )
    value_fields = [value.strip() for value in value_fields]
    if len(value_fields) != len(set(value_fields)):
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data.valueFields must not " "contain duplicates"
        )

    fields = _result_fields(chart)
    missing = [name for name in value_fields if name not in fields]
    if missing:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data.valueFields absent from "
            "queries[].fields: " + ", ".join(missing)
        )
    non_numeric = [name for name in value_fields if fields[name] != "number"]
    if non_numeric:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.data.valueFields must have "
            "type=number: " + ", ".join(non_numeric)
        )

    query_option = {"showField": value_fields}
    value_option = {
        "showMode": data_mode,
        "layoutOrientation": "horizontal",
        "showGaugeTitle": True,
    }
    if data_mode == "calculate":
        reducer = str(data.get("reducer", "") or "").strip()
        if reducer not in REDUCERS:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) gauge.data.reducer must be one of: "
                + ", ".join(sorted(REDUCERS))
            )
        value_option["calculationType"] = reducer
    else:
        if len(value_fields) != 1:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) allValues requires exactly " "one valueField"
            )
        label_field = str(data.get("labelField", "") or "").strip()
        if not label_field:
            raise ValueError(f"chart {chart_name!r} (burgauge) allValues requires labelField")
        if label_field not in fields:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) allValues labelField "
                f"{label_field!r} is absent from queries[].fields"
            )
        if fields[label_field] != "string":
            raise ValueError(
                f"chart {chart_name!r} (burgauge) allValues labelField "
                f"{label_field!r} must have type=string"
            )
        limit = data.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) allValues limit must be " "a positive integer"
            )
        query_option["associatedField"] = label_field
        value_option["limitCount"] = limit

    range_config = gauge.get("range")
    if not isinstance(range_config, dict):
        raise ValueError(f"chart {chart_name!r} (burgauge) gauge.range must be an object")
    range_mode = str(range_config.get("mode", "") or "").strip()
    allowed_range = (
        {"mode", "min", "max"}
        if range_mode == "fixed"
        else {"mode", "min", "maxField"}
        if range_mode == "queryField"
        else {"mode", "min", "max", "maxField"}
    )
    unknown = sorted(set(range_config) - allowed_range)
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.range has unsupported field(s) "
            f"for mode {range_mode!r}: " + ", ".join(unknown)
        )
    if range_mode not in {"fixed", "queryField"}:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.range.mode must be " "fixed or queryField"
        )
    minimum = range_config.get("min")
    if not _number(minimum):
        raise ValueError(f"chart {chart_name!r} (burgauge) gauge.range.min must be a number")

    styles_option = {
        "displayMode": "basic",
        "minRange": minimum,
        "showUnfilledArea": True,
    }
    if range_mode == "fixed":
        maximum = range_config.get("max")
        if not _number(maximum):
            raise ValueError(f"chart {chart_name!r} (burgauge) fixed range max must be a number")
        if maximum <= minimum:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) fixed range max must be greater " "than min"
            )
        styles_option["maxRange"] = maximum
    else:
        max_field = str(range_config.get("maxField", "") or "").strip()
        if not max_field:
            raise ValueError(f"chart {chart_name!r} (burgauge) queryField range requires maxField")
        if max_field not in fields:
            raise ValueError(
                f"chart {chart_name!r} (burgauge) range maxField {max_field!r} "
                "is absent from queries[].fields"
            )
        if fields[max_field] != "number":
            raise ValueError(
                f"chart {chart_name!r} (burgauge) range maxField {max_field!r} "
                "must have type=number"
            )
        query_option.update({"useQuery": True, "queryField": max_field})

    label_mode = str(gauge.get("labelMode", "") or "").strip()
    if label_mode not in {"value", "percent"}:
        raise ValueError(
            f"chart {chart_name!r} (burgauge) gauge.labelMode must be value or percent"
        )
    value_option["gaugeLabelMode"] = label_mode

    return {
        "queryOptionMap": {chart["queries"][0]["name"]: query_option},
        "burGaugeValueOption": value_option,
        "burGaugeStylesOption": styles_option,
    }


def direct_display_patch(chart: dict) -> dict:
    return {
        **direct_binding(chart),
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
            "colorSchame": {"schema": "threshold"},
        },
    }


def metric_display_patch(chart: dict, chart_queries: List[dict]) -> dict:
    return {
        **metric_binding(chart, chart_queries),
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
            "colorSchame": {"schema": "threshold"},
        },
    }
