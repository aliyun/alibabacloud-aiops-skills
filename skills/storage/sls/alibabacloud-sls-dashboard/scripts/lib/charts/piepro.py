"""SLS-only chart bindings; inherited pure display/shape logic."""

from .aggpro import METRIC_DATASOURCES

REDUCERS = {
    "first",
    "firstNotNull",
    "last",
    "lastNotNull",
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

def _chart_name(chart: dict) -> str:
    return chart.get("key") or chart.get("title") or "piepro"

def _metric_reducer(chart: dict) -> str:
    chart_name = _chart_name(chart)
    pie = chart.get("pie")
    if not isinstance(pie, dict):
        raise ValueError(
            f"chart {chart_name!r} (piepro) metric datasource requires "
            "charts[].pie.reducer"
        )
    unknown = sorted(set(pie) - {"reducer"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (piepro) metric charts[].pie only supports "
            "reducer; "
            "unsupported field(s): " + ", ".join(unknown)
        )
    reducer = str(pie.get("reducer", "") or "").strip()
    if reducer not in REDUCERS:
        raise ValueError(
            f"chart {chart_name!r} (piepro) charts[].pie.reducer must be one of: "
            + ", ".join(sorted(REDUCERS))
        )
    return reducer

def _result_fields(chart: dict) -> dict[str, str]:
    chart_name = _chart_name(chart)
    entries = chart.get("datasources", []) or []
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ValueError(
            f"chart {chart_name!r} (piepro) requires exactly one datasource query"
        )
    raw_fields = entries[0].get("queryResultFields")
    if not isinstance(raw_fields, list):
        raise ValueError(
            f"chart {chart_name!r} (piepro) requires queryResultFields"
        )

    fields = {}
    for field in raw_fields:
        if not isinstance(field, dict):
            raise ValueError(
                f"chart {chart_name!r} (piepro) queryResultFields entries must be objects"
            )
        name = str(field.get("name", "") or "").strip()
        data_type = str(field.get("dataType", "") or "").strip().lower()
        if not name:
            raise ValueError(
                f"chart {chart_name!r} (piepro) queryResultFields requires non-empty names"
            )
        if name in fields:
            raise ValueError(
                f"chart {chart_name!r} (piepro) queryResultFields contains duplicate "
                f"field {name!r}"
            )
        fields[name] = data_type
    return fields

def _field_list(value, path: str, chart_name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(
            f"chart {chart_name!r} (piepro) {path} must be a non-empty "
            "list of field names"
        )
    fields = [item.strip() for item in value]
    if len(fields) != len(set(fields)):
        raise ValueError(
            f"chart {chart_name!r} (piepro) {path} must not contain duplicates"
        )
    return fields

def _require_field(
    fields: dict[str, str],
    name: str,
    expected_type: str,
    path: str,
    chart_name: str,
) -> None:
    if name not in fields:
        raise ValueError(
            f"chart {chart_name!r} (piepro) {path} {name!r} "
            "is absent from queryResultFields"
        )
    if fields[name] != expected_type:
        raise ValueError(
            f"chart {chart_name!r} (piepro) {path} {name!r} "
            f"must have dataType={expected_type}"
        )

def direct_binding(chart: dict) -> dict:
    chart_name = _chart_name(chart)
    pie = chart.get("pie")
    if not isinstance(pie, dict):
        raise ValueError(
            f"chart {chart_name!r} (piepro) requires a pie object at charts[].pie"
        )

    mode = str(pie.get("mode", "") or "").strip()
    allowed = (
        {"mode", "categoryField", "valueField", "concatFields"}
        if mode == "categoryValue"
        else {"mode", "calculation"}
        if mode == "dataCalculation"
        else {
            "mode",
            "categoryField",
            "valueField",
            "concatFields",
            "calculation",
        }
    )
    unknown = sorted(set(pie) - allowed)
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (piepro) pie has unsupported field(s) "
            f"for mode {mode!r}: " + ", ".join(unknown)
        )
    if mode not in {"categoryValue", "dataCalculation"}:
        raise ValueError(
            f"chart {chart_name!r} (piepro) pie.mode must be "
            "categoryValue or dataCalculation"
        )

    fields = _result_fields(chart)
    if mode == "categoryValue":
        category_field = str(pie.get("categoryField", "") or "").strip()
        value_field = str(pie.get("valueField", "") or "").strip()
        if not category_field or not value_field:
            raise ValueError(
                f"chart {chart_name!r} (piepro) categoryValue requires "
                "categoryField and valueField"
            )
        concat_fields = pie.get("concatFields", [])
        if not isinstance(concat_fields, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in concat_fields
        ):
            raise ValueError(
                f"chart {chart_name!r} (piepro) pie.concatFields must be "
                "a list of field names"
            )
        concat_fields = [item.strip() for item in concat_fields]
        if len(concat_fields) != len(set(concat_fields)):
            raise ValueError(
                f"chart {chart_name!r} (piepro) pie.concatFields must not "
                "contain duplicates"
            )
        _require_field(
            fields, category_field, "string", "pie.categoryField", chart_name
        )
        _require_field(fields, value_field, "number", "pie.valueField", chart_name)
        for field in concat_fields:
            _require_field(
                fields, field, "string", "pie.concatFields field", chart_name
            )
        return {
            "pieDataMode": "queryOptionMap",
            "queryOptionMap": {
                "A": {
                    "showFieldKey": category_field,
                    "numFieldKey": value_field,
                    "xAxisConcatKeys": concat_fields,
                }
            },
        }

    calculation = pie.get("calculation")
    if not isinstance(calculation, dict):
        raise ValueError(
            f"chart {chart_name!r} (piepro) dataCalculation requires "
            "a calculation object"
        )
    calculation_mode = str(calculation.get("mode", "") or "").strip()
    unknown = sorted(set(calculation) - {"mode", "valueFields", "reducer"})
    if unknown:
        raise ValueError(
            f"chart {chart_name!r} (piepro) pie.calculation has unsupported "
            f"field(s) for mode {calculation_mode!r}: " + ", ".join(unknown)
        )
    if calculation_mode != "calculate":
        raise ValueError(
            f"chart {chart_name!r} (piepro) pie.calculation.mode must be "
            "calculate"
        )

    value_fields = _field_list(
        calculation.get("valueFields"),
        "pie.calculation.valueFields",
        chart_name,
    )
    for field in value_fields:
        _require_field(
            fields,
            field,
            "number",
            "pie.calculation.valueFields field",
            chart_name,
        )

    reducer = str(calculation.get("reducer", "") or "").strip()
    if reducer not in REDUCERS:
        raise ValueError(
            f"chart {chart_name!r} (piepro) pie.calculation.reducer "
            "must be one of: " + ", ".join(sorted(REDUCERS))
        )
    numeric_fields = [
        name for name, data_type in fields.items() if data_type == "number"
    ]
    if len(value_fields) > 1 and set(value_fields) != set(numeric_fields):
        raise ValueError(
            f"chart {chart_name!r} (piepro) multiple calculate valueFields "
            "must be the complete set of numeric queryResultFields"
        )
    return {
        "pieDataMode": "dataOption",
        "dataOption": {
            "showMode": "calculate",
            "calculationType": reducer,
            "fields": " " if len(value_fields) > 1 else value_fields[0],
        },
    }

def metric_binding(chart: dict, chart_queries: list[dict]) -> dict:
    """Reduce every numeric time-series field into one pie slice."""
    chart_name = _chart_name(chart)
    reducer = _metric_reducer(chart)
    if len(chart_queries) != 1 or not isinstance(chart_queries[0], dict):
        raise ValueError(
            f"chart {chart_name!r} (piepro) requires exactly one metric query"
        )
    query = chart_queries[0]
    datasource = str(query.get("datasource", "") or "")
    if datasource not in METRIC_DATASOURCES:
        raise ValueError(
            f"chart {chart_name!r} (piepro) cannot infer metric fields for "
            f"datasource {datasource!r}"
        )
    expression = (
        query.get("expr")
        or query.get("query")
        or query.get("tokenQuery")
        or ""
    )
    if not str(expression).strip():
        raise ValueError(
            f"chart {chart_name!r} (piepro) metric query is empty"
        )

    return {
        "pieDataMode": "dataOption",
        "dataOption": {
            "showMode": "calculate",
            "calculationType": reducer,
            "fields": " ",
        },
    }

def _display_patch(binding: dict) -> dict:
    return {
        **binding,
        "pieOption": {
            "chartType": "PieChart",
            "labelType": "type_num_percent",
            "showLabel": True,
        },
        "legendOption": {"show": True, "position": "bottom"},
        "standardOption": {
            "format": "none",
            "decimals": 2,
            "unit": {"unit": "none"},
        },
    }

def direct_display_patch(chart: dict) -> dict:
    return _display_patch(direct_binding(chart))

def metric_display_patch(chart: dict, chart_queries: list[dict]) -> dict:
    return _display_patch(metric_binding(chart, chart_queries))
