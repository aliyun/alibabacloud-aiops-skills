"""SLS-only chart bindings; inherited pure display/shape logic."""

import re

POSITION_REDUCERS = {"first", "firstNotNull", "last", "lastNotNull"}

NUMERIC_REDUCERS = {
    "min",
    "max",
    "mean",
    "minAboveZero",
    "range",
    "total",
    "step",
    "changeCount",
    "count",
    "difference",
    "differencePercent",
    "distinctCount",
}

REDUCERS = POSITION_REDUCERS | NUMERIC_REDUCERS

REF_IDS = "ABCDEFGH"

METRIC_DATASOURCES = {"metricstore", "metricstore_storeview"}

LOGSTORE_DATASOURCES = {"logstore"}

_GROUPING_RE = re.compile(
    r"\b(?:by|without|on|ignoring|group_left|group_right)\s*\(",
    re.IGNORECASE,
)

_DASHBOARD_TOKEN_RE = re.compile(r"\$\{\{.*?\}\}|\$\{[^{}]*\}", re.DOTALL)

_STRING_RE = re.compile(
    r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`',
    re.DOTALL,
)

def _chart_name(chart: dict) -> str:
    return chart.get("key") or chart.get("title") or "statpro"

def _mask(expression: str, pattern: re.Pattern) -> str:
    return pattern.sub(lambda match: " " * len(match.group(0)), expression)

def _metric_reducer(chart: dict) -> str:
    chart_name = _chart_name(chart)
    stat = chart.get("stat")
    if not isinstance(stat, dict):
        raise ValueError(
            f"chart {chart_name!r} (statpro) metric datasource requires "
            "charts[].stat.reducer"
        )
    unknown = sorted(set(stat) - {"reducer"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (statpro) metric charts[].stat only supports "
            "reducer; "
            "unsupported field(s): " + ", ".join(unknown)
        )
    reducer = str(stat.get("reducer", "") or "").strip()
    if reducer not in REDUCERS:
        raise ValueError(
            f"chart {chart_name!r} (statpro) charts[].stat.reducer must be one of: "
            + ", ".join(sorted(REDUCERS))
        )
    return reducer

def validate_metric_query_shape(
    chart: dict,
    query: dict,
    chart_type: str = "statpro",
) -> None:
    chart_name = _chart_name(chart)
    expression = (
        query.get("expr")
        or query.get("query")
        or query.get("tokenQuery")
        or ""
    )
    if not str(expression).strip():
        raise ValueError(
            f"chart {chart_name!r} ({chart_type}) metric query is empty"
        )
    if chart_type in {"statpro", "burgauge"}:
        return
    masked = _mask(str(expression), _DASHBOARD_TOKEN_RE)
    masked = _mask(masked, _STRING_RE)
    if _GROUPING_RE.search(masked):
        raise ValueError(
            f"chart {chart_name!r} ({chart_type}) metric query must produce one "
            "ungrouped series; use separate queries instead of grouping labels"
        )

def _result_fields(chart: dict) -> list[dict]:
    chart_name = _chart_name(chart)
    entries = chart.get("datasources", []) or []
    if not isinstance(entries, list) or not entries:
        raise ValueError(
            f"chart {chart_name!r} (statpro) requires at least one datasource query"
        )

    results = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"chart {chart_name!r} (statpro) datasource entries must be objects"
            )
        raw_fields = entry.get("queryResultFields")
        if not isinstance(raw_fields, list):
            raise ValueError(
                f"chart {chart_name!r} (statpro) datasource[{index}] "
                "requires queryResultFields"
            )
        fields = {}
        for field in raw_fields:
            if not isinstance(field, dict):
                raise ValueError(
                    f"chart {chart_name!r} (statpro) queryResultFields entries "
                    "must be objects"
                )
            name = str(field.get("name", "") or "").strip()
            data_type = str(field.get("dataType", "") or "").strip().lower()
            if not name:
                raise ValueError(
                    f"chart {chart_name!r} (statpro) queryResultFields requires "
                    "non-empty names"
                )
            if name in fields:
                raise ValueError(
                    f"chart {chart_name!r} (statpro) queryResultFields contains "
                    f"duplicate field {name!r}"
                )
            fields[name] = data_type
        ref = REF_IDS[index] if index < len(REF_IDS) else f"REF{index}"
        results.append({"ref": ref, "fields": fields})
    return results

def direct_binding(chart: dict) -> dict:
    chart_name = _chart_name(chart)
    stat = chart.get("stat")
    if not isinstance(stat, dict):
        raise ValueError(
            f"chart {chart_name!r} (statpro) requires a stat object at charts[].stat"
        )

    mode = str(stat.get("mode", "") or "").strip()
    allowed = (
        {"mode", "valueFields", "reducer"}
        if mode == "calculate"
        else {"mode", "valueFields", "labelField", "limit"}
        if mode == "allValues"
        else {"mode", "valueFields", "reducer", "labelField", "limit"}
    )
    unknown = sorted(set(stat) - allowed)
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (statpro) stat has unsupported field(s) "
            f"for mode {mode!r}: " + ", ".join(unknown)
        )
    if mode not in {"calculate", "allValues"}:
        raise ValueError(
            f"chart {chart_name!r} (statpro) stat.mode must be calculate or allValues"
        )

    value_fields = stat.get("valueFields")
    if (
        not isinstance(value_fields, list)
        or not value_fields
        or any(not isinstance(value, str) or not value.strip() for value in value_fields)
    ):
        raise ValueError(
            f"chart {chart_name!r} (statpro) stat.valueFields must be a non-empty "
            "list of field names"
        )
    value_fields = [value.strip() for value in value_fields]
    if len(value_fields) != len(set(value_fields)):
        raise ValueError(
            f"chart {chart_name!r} (statpro) stat.valueFields must not contain duplicates"
        )

    results = _result_fields(chart)
    occurrences = {
        name: [
            result for result in results
            if name in result["fields"]
        ]
        for name in value_fields
    }
    missing = [name for name, matches in occurrences.items() if not matches]
    if missing:
        raise ValueError(
            f"chart {chart_name!r} (statpro) stat.valueFields absent from "
            "queryResultFields: " + ", ".join(missing)
        )

    if mode == "calculate":
        reducer = str(stat.get("reducer", "") or "").strip()
        if reducer not in REDUCERS:
            raise ValueError(
                f"chart {chart_name!r} (statpro) stat.reducer must be one of: "
                + ", ".join(sorted(REDUCERS))
            )
        if reducer in NUMERIC_REDUCERS:
            non_numeric = [
                name for name, matches in occurrences.items()
                if any(result["fields"][name] != "number" for result in matches)
            ]
            if non_numeric:
                raise ValueError(
                    f"chart {chart_name!r} (statpro) reducer {reducer!r} requires "
                    "dataType=number for: " + ", ".join(non_numeric)
                )
        query_options = {
            result["ref"]: {
                "showField": [
                    name for name in value_fields if name in result["fields"]
                ]
            }
            for result in results
            if any(name in result["fields"] for name in value_fields)
        }
        return {
            "queryOptionMap": query_options,
            "statValueOption": {
                "showMode": "calculate",
                "calculationType": reducer,
                "layoutOrientation": "auto",
                "limitCount": 25,
            },
        }

    if len(value_fields) != 1:
        raise ValueError(
            f"chart {chart_name!r} (statpro) allValues requires exactly one valueField"
        )
    value_field = value_fields[0]
    if any(
        result["fields"][value_field] != "number"
        for result in occurrences[value_field]
    ):
        raise ValueError(
            f"chart {chart_name!r} (statpro) allValues valueField {value_field!r} "
            "must have dataType=number"
        )
    label_field = str(stat.get("labelField", "") or "").strip()
    if not label_field:
        raise ValueError(
            f"chart {chart_name!r} (statpro) allValues requires labelField"
        )
    limit = stat.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError(
            f"chart {chart_name!r} (statpro) allValues limit must be a positive integer"
        )
    matching_results = [
        result for result in occurrences[value_field]
        if label_field in result["fields"]
    ]
    if not matching_results:
        raise ValueError(
            f"chart {chart_name!r} (statpro) allValues labelField {label_field!r} "
            f"must be declared with valueField {value_field!r} in queryResultFields"
        )
    return {
        "queryOptionMap": {
            result["ref"]: {
                "showField": [value_field],
                "associatedField": label_field,
            }
            for result in matching_results
        },
        "statValueOption": {
            "showMode": "allValues",
            "layoutOrientation": "auto",
            "limitCount": limit,
        },
    }

def metric_binding(chart: dict, chart_queries: list[dict]) -> dict:
    """Use calculate mode and let Explorer select all numeric metric fields."""
    chart_name = _chart_name(chart)
    reducer = _metric_reducer(chart)
    if not isinstance(chart_queries, list) or not chart_queries:
        raise ValueError(
            f"chart {chart_name!r} (statpro) requires at least one metric query"
        )

    for query in chart_queries:
        if not isinstance(query, dict):
            raise ValueError(
                f"chart {chart_name!r} (statpro) metric queries must be objects"
            )
        datasource = str(query.get("datasource", "") or "")
        if datasource not in METRIC_DATASOURCES:
            raise ValueError(
                f"chart {chart_name!r} (statpro) cannot infer metric fields for "
                f"datasource {datasource!r}"
            )
        validate_metric_query_shape(chart, query)

    return {
        "statValueOption": {
            "showMode": "calculate",
            "calculationType": reducer,
            "layoutOrientation": "auto",
            "limitCount": 25,
        },
    }

def style_display_patch() -> dict:
    return {
        "statStyleOptions": {
            "textMode": "value_and_name",
            "graphMode": "area",
            "colorMode": "value",
            "textAlignment": "center",
        },
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
            "colorSchame": {"schema": "single", "color": "#7570ff"},
        },
    }

def _display_patch(binding: dict) -> dict:
    return {**binding, **style_display_patch()}

def direct_display_patch(chart: dict) -> dict:
    return _display_patch(direct_binding(chart))

def metric_display_patch(chart: dict, chart_queries: list[dict]) -> dict:
    return _display_patch(metric_binding(chart, chart_queries))
