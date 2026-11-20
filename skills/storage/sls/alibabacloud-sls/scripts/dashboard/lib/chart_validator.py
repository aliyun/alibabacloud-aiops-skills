"""Python chart/dashboard validation against the packaged display contract."""

from functools import lru_cache
import json
import math

from .common import DASHBOARD_DATASOURCES, ROOT, effective_datasource
from .validation_report import result

MISSING = object()
LAYOUT_FIELDS = {
    "xPos",
    "yPos",
    "width",
    "height",
    "version",
    "displayName",
    "zIndex",
    "fixedTop",
    "fixedTopOrder",
}
# Shared fields documented in references/dashboard/features/basic-options.md and
# references/dashboard/features/standard-options.md.
COMMON_OPTIONS = {
    "display.basicOptions": {"description": "string", "links": "array"},
    "display.standardOption": {"noValue": "string"},
    "display": {"innerTokenOption": "array"},
}
COMMON_FIELDS = {
    "fieldOptions": "array",
    "actionOptions": "array",
    "belongChart": "string",
    "charts": "array",
}
LEGACY_BASIC_FIELDS = {"showTitle", "showBackground", "showBorder"}
LEGACY_CHART_TYPES = {
    "number",
    "line",
    "metric",
    "droplist",
    "table",
    "progress",
    "pie",
    "agg",
    "markdown",
    "boxplot",
    "colorblock",
    "column",
}
SOURCES = sorted(DASHBOARD_DATASOURCES)
METRIC_SOURCES = ["metricstore", "metricstore_storeview"]
QUERY_TEXT_FIELDS = ["query", "tokenQuery", "expr", "spl"]
POSITIONS = ("xPos", "yPos", "width", "height")


@lru_cache(maxsize=1)
def schemas():
    with (ROOT / "references/dashboard/contracts/chart-display.json").open(
        encoding="utf-8"
    ) as stream:
        return json.load(stream)["charts"]


def get_supported_chart_types():
    return sorted(schemas())


def value_type(value):
    if value is MISSING:
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def truthy(value):
    if value is MISSING or value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value)
    if type(value) in (int, float):
        return value != 0 and not (isinstance(value, float) and math.isnan(value))
    return True


def integer(value):
    return (
        type(value) is int or type(value) is float and math.isfinite(value) and value.is_integer()
    )


def error(path, message, actual=MISSING, expected=MISSING, code="INVALID_VALUE"):
    return {
        k: v
        for k, v in {
            "path": path,
            "message": message,
            "actualValue": actual,
            "expectedValue": expected,
            "code": code,
        }.items()
        if v is not MISSING
    }


def expected_type(path, value, expected, errors):
    if not expected:
        return
    types = expected if isinstance(expected, list) else [expected]
    actual = value_type(value)
    if actual not in types:
        errors.append(
            error(
                path,
                f"Type mismatch: expected {' or '.join(types)}, got {actual}",
                actual,
                expected,
                "TYPE_MISMATCH",
            )
        )


def display_schema(display, schema, path, errors, warnings):
    children = schema.get("children", {})
    for key, value in display.items():
        if key in LAYOUT_FIELDS:
            continue
        key_path = f"{path}.{key}" if path else key
        if key in COMMON_FIELDS:
            expected_type(key_path, value, COMMON_FIELDS[key], errors)
            continue
        child = children.get(key, children.get("*"))
        if (
            child is None
            and path == "display"
            and key in LEGACY_BASIC_FIELDS
            and "basicOptions" in children
        ):
            basic = display.get("basicOptions")
            if (
                isinstance(basic, dict)
                and type(value) is bool
                and type(basic.get(key)) is bool
                and value == basic[key]
            ):
                continue
        if child is None and key in COMMON_OPTIONS.get(path, {}):
            expected_type(key_path, value, COMMON_OPTIONS[path][key], errors)
            continue
        if child is None:
            warnings.append(
                error(
                    key_path,
                    "Field is not described by the local display schema",
                    code="UNKNOWN_FIELD",
                )
            )
            continue
        elif child.get("children"):
            if not isinstance(value, dict):
                errors.append(
                    error(
                        key_path,
                        f"Expected object for nested field {key}",
                        value,
                        "object",
                        "TYPE_MISMATCH",
                    )
                )
            else:
                display_schema(value, child, key_path, errors, warnings)
        else:
            descriptor = child.get("descriptor", {})
            if value not in descriptor.get("allowedValues", []):
                expected_type(key_path, value, descriptor.get("expectedType"), errors)
    for key, child in children.items():
        if key != "*" and child.get("descriptor", {}).get("required") and key not in display:
            errors.append(error(f"{path}.{key}", "Required field is missing", code="REQUIRED"))


def participates_in_grid(chart):
    """Use the same effective placement for coordinates and overlap checks."""
    display = chart.get("display")
    if not isinstance(display, dict):
        return False
    if chart.get("type") == "connect":
        return False
    if chart.get("type") != "droplistpro":
        return True
    option = display.get("dropListOption")
    adhoc = isinstance(option, dict) and option.get("type") == "adhoc"
    fixed = display["fixedTop"] if type(display.get("fixedTop")) is bool else adhoc
    return truthy(display.get("showDropListChart")) and not fixed


def grid_position(chart, warnings):
    if not participates_in_grid(chart):
        return
    display = chart["display"]
    values = {}
    for field in POSITIONS:
        path = f"display.{field}"
        if field not in display:
            warnings.append(
                error(
                    path,
                    f"Grid chart must explicitly include {field}",
                    expected="number",
                    code="GRID_POSITION_REQUIRED",
                )
            )
            continue
        value = display[field]
        if type(value) not in (int, float) or not math.isfinite(value):
            warnings.append(
                error(
                    path,
                    f"Grid chart {field} must be a finite number",
                    value,
                    "number",
                    "GRID_POSITION_TYPE",
                )
            )
        elif not integer(value):
            warnings.append(
                error(
                    path,
                    f"Grid chart {field} must be an integer",
                    value,
                    "integer",
                    "GRID_POSITION_INTEGER",
                )
            )
        else:
            values[field] = value
    for field in POSITIONS:
        if field not in values:
            continue
        position = field in ("xPos", "yPos")
        if values[field] < 0 if position else values[field] <= 0:
            phrase, bound = (
                ("greater than or equal to 0", ">= 0") if position else ("greater than 0", "> 0")
            )
            warnings.append(
                error(
                    f"display.{field}",
                    f"Grid chart {field} must be {phrase}",
                    values[field],
                    bound,
                    "GRID_POSITION_RANGE",
                )
            )
    if "xPos" in values and "width" in values and values["xPos"] + values["width"] > 24:
        warnings.append(
            error(
                "display.width",
                "Grid chart exceeds the 24-column layout",
                values["xPos"] + values["width"],
                "xPos + width <= 24",
                "GRID_X_OVERFLOW",
            )
        )


def query_string(query, field, base, errors, required=False):
    path, value = f"{base}.{field}", query.get(field, MISSING)
    if field not in query:
        if required:
            errors.append(
                error(
                    path,
                    f'Query field "{field}" is required',
                    value,
                    "non-empty string",
                    "QUERY_PARAMETER_REQUIRED",
                )
            )
    elif not isinstance(value, str):
        errors.append(
            error(
                path,
                f'Query field "{field}" must be a string',
                value,
                "string",
                "QUERY_PARAMETER_TYPE",
            )
        )
    elif required and not value.strip():
        errors.append(
            error(
                path,
                f'Query field "{field}" must not be empty',
                value,
                "non-empty string",
                "QUERY_PARAMETER_REQUIRED",
            )
        )


def enum_value(path, value, choices, code, errors, warnings):
    if not isinstance(value, str):
        errors.append(error(path, "Expected a string", value, "string", "TYPE_MISMATCH"))
    elif value not in choices:
        warnings.append(
            error(path, "Value is not recognized by the local validator", value, choices, code)
        )


def query_config(chart, query, datasource, base, errors, warnings):
    if datasource == "builtin":
        return
    display = chart["display"]
    option = display.get("dropListOption")
    adhoc = (
        chart.get("type") == "droplistpro"
        and isinstance(option, dict)
        and option.get("type") == "adhoc"
    )
    static_control = (
        chart.get("type") == "droplistpro"
        and isinstance(option, dict)
        and option.get("type") in ("filter", "token")
        and not truthy(display.get("bindQuery"))
    )
    active = query.get("hide") is not True and not static_control
    if not adhoc:
        for field in QUERY_TEXT_FIELDS:
            if field in query and not isinstance(query[field], str):
                errors.append(
                    error(
                        f"{base}.{field}",
                        f'Query text field "{field}" must be a string',
                        query[field],
                        "string",
                        "QUERY_TEXT_TYPE",
                    )
                )
        if active and not any(
            isinstance(query.get(f), str) and query[f].strip() for f in ("tokenQuery", "query")
        ):
            errors.append(
                error(
                    base,
                    f'Datasource "{datasource}" requires non-empty query text',
                    query,
                    ["tokenQuery", "query"],
                    "QUERY_TEXT_REQUIRED",
                )
            )
    metric = datasource in METRIC_SOURCES
    if "limit" in query:
        if not metric:
            warnings.append(
                error(
                    f"{base}.limit",
                    f'Datasource "{datasource}" does not consume query.limit',
                    query["limit"],
                    code="QUERY_LIMIT_UNSUPPORTED",
                )
            )
        elif not integer(query["limit"]) or query["limit"] <= 0:
            errors.append(
                error(
                    f"{base}.limit",
                    "Metricstore query.limit must be a positive integer",
                    query["limit"],
                    "positive integer",
                    "QUERY_LIMIT_INVALID",
                )
            )
    if "format" in query:
        if not metric:
            warnings.append(
                error(
                    f"{base}.format",
                    f'Datasource "{datasource}" does not consume query.format',
                    query["format"],
                    code="QUERY_FORMAT_UNSUPPORTED",
                )
            )
        else:
            enum_value(
                f"{base}.format",
                query["format"],
                ["time_series", "table"],
                "QUERY_FORMAT_INVALID",
                errors,
                warnings,
            )
    if "queryType" in query and metric:
        enum_value(
            f"{base}.queryType",
            query["queryType"],
            ["instant", "range"],
            "METRICSTORE_QUERY_TYPE_INVALID",
            errors,
            warnings,
        )
    query_string(query, "logstore", base, errors, active)
    query_string(query, "project", base, errors)


def chart_queries(chart, errors, warnings):
    search = chart.get("search")
    if not isinstance(search, dict):
        return
    if "query" in search and not isinstance(search["query"], str):
        errors.append(
            error(
                "search.query",
                "Legacy search.query must be a string",
                search["query"],
                "string",
                "SEARCH_QUERY_TYPE",
            )
        )
    if "dataSourceType" in search:
        enum_value(
            "search.dataSourceType",
            search["dataSourceType"],
            ["current", "mixed"],
            "QUERY_DATASOURCE_MODE",
            errors,
            warnings,
        )
    display = chart["display"]
    option = display.get("dropListOption")
    bound = chart.get("type") == "droplistpro" and (
        truthy(display.get("bindQuery"))
        or isinstance(option, dict)
        and option.get("type") == "adhoc"
    )
    if "chartQueries" not in search:
        legacy = search.get("query")
        if bound:
            errors.append(
                error(
                    "search.chartQueries",
                    "This control requires search.chartQueries[] for its query or metric resource",
                    expected="array",
                    code="QUERY_LIST_REQUIRED",
                )
            )
        elif isinstance(legacy, str) and legacy.strip() and legacy != "@":
            warnings.append(
                error(
                    "search.query",
                    "Legacy query format: only basic query structure is checked; the saved format is preserved",
                    code="LEGACY_QUERY_FORMAT",
                )
            )
        return
    queries = search["chartQueries"]
    if not isinstance(queries, list):
        errors.append(
            error(
                "search.chartQueries",
                "search.chartQueries must be an array",
                queries,
                "array",
                "QUERY_LIST_TYPE",
            )
        )
        return
    if bound and not queries:
        errors.append(
            error(
                "search.chartQueries",
                "This control requires at least one query or metric resource",
                queries,
                "non-empty array",
                "QUERY_LIST_REQUIRED",
            )
        )
    names, refs, bindings = set(), set(), []
    for index, query in enumerate(queries):
        base = f"search.chartQueries[{index}]"
        if not isinstance(query, dict):
            errors.append(
                error(base, "Chart query must be an object", query, "object", "QUERY_ITEM_TYPE")
            )
            continue
        name = query.get("name", MISSING)
        if not isinstance(name, str) or not name.strip():
            errors.append(
                error(
                    f"{base}.name",
                    "Chart query name must be a non-empty string",
                    name,
                    "non-empty string",
                    "QUERY_NAME_REQUIRED",
                )
            )
        elif name in names:
            errors.append(
                error(
                    f"{base}.name",
                    f'Duplicate query name "{name}"',
                    name,
                    "unique query name",
                    "QUERY_NAME_DUPLICATE",
                )
            )
        else:
            names.add(name)
            if name not in bindings:
                bindings.append(name)
        ref = name if isinstance(name, str) and name.strip() else ""
        if "refId" in query:
            value = query["refId"]
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    error(
                        f"{base}.refId",
                        "Query refId must be a non-empty string when provided",
                        value,
                        "non-empty string",
                        "QUERY_REF_TYPE",
                    )
                )
                ref = ""
            else:
                ref = value
                if value not in bindings:
                    bindings.append(value)
        if ref:
            if ref in refs:
                field = "refId" if "refId" in query else "name"
                errors.append(
                    error(
                        f"{base}.{field}",
                        f'Duplicate query ref "{ref}"',
                        ref,
                        "unique query ref",
                        "QUERY_REF_DUPLICATE",
                    )
                )
            else:
                refs.add(ref)
        if "hide" in query and type(query["hide"]) is not bool:
            errors.append(
                error(
                    f"{base}.hide",
                    "Query hide must be boolean",
                    query["hide"],
                    "boolean",
                    "QUERY_HIDE_TYPE",
                )
            )
        source = query.get("datasource", MISSING)
        if source is not MISSING and not isinstance(source, str):
            errors.append(
                error(
                    f"{base}.datasource",
                    "Query datasource must be a string",
                    source,
                    "string",
                    "QUERY_DATASOURCE_TYPE",
                )
            )
            continue
        if source is MISSING or not source.strip():
            errors.append(
                error(
                    f"{base}.datasource",
                    "Query datasource must be a non-empty string",
                    source,
                    SOURCES,
                    "QUERY_DATASOURCE_REQUIRED",
                )
            )
            continue
        datasource = effective_datasource(query)
        if datasource not in SOURCES:
            warnings.append(
                error(
                    f"{base}.datasource",
                    f'Query datasource "{datasource}" is not recognized by the local validator',
                    source,
                    SOURCES,
                    "QUERY_DATASOURCE_UNSUPPORTED",
                )
            )
            continue
        query_config(chart, query, datasource, base, errors, warnings)
    options = chart["display"].get("queryOptionMap")
    if (
        chart.get("type") == "linepro"
        and chart["display"].get("isTimeSeries") is False
        and len(queries) > 1
    ):
        errors.append(
            error(
                "search.chartQueries",
                "A category-axis line chart supports a single query result",
                code="CATEGORY_QUERY_COUNT",
            )
        )
    if isinstance(options, dict) and chart.get("type") in {"linepro", "barpro", "timelinepro"}:
        for ref, binding in options.items():
            if not isinstance(binding, dict) or "yAxisKeys" not in binding:
                continue
            value = binding["yAxisKeys"]
            path = f"display.queryOptionMap.{ref}.yAxisKeys"
            keys = [value] if isinstance(value, str) else value
            if not isinstance(keys, list) or any(not isinstance(k, str) or not k for k in keys):
                errors.append(error(path, "Select non-empty field names", code="Y_FIELDS_INVALID"))
            elif (
                chart.get("type") in {"barpro", "timelinepro"}
                and binding.get("aggField")
                and len(keys) > 1
            ):
                warnings.append(
                    error(
                        path,
                        "Only one Y field is used for category splitting when aggField is set",
                        code="Y_FIELDS_COUNT",
                    )
                )
            if (
                chart.get("type") == "timelinepro"
                and binding.get("isChangeChart")
                and not isinstance(value, str)
            ):
                errors.append(
                    error(
                        path,
                        "For explicit start/end intervals, supply a single field name as a string",
                        code="INTERVAL_FIELD_TYPE",
                    )
                )
    if queries and isinstance(options, dict):
        for ref in options:
            if ref not in bindings:
                warnings.append(
                    error(
                        f"display.queryOptionMap.{ref}",
                        f'No input query matches "{ref}"; these options apply only if a transformation produces a result with this name',
                        ref,
                        bindings,
                        "QUERY_OPTION_REF_UNKNOWN",
                    )
                )


def droplist_defaults(chart, errors):
    option = chart["display"].get("dropListOption")
    if chart.get("type") != "droplistpro" or not isinstance(option, dict):
        return
    field = (
        "tokenDefault"
        if option.get("type") == "token"
        else "listDefault"
        if option.get("type") == "filter"
        else None
    )
    if not field or option.get(field) is None:
        return
    defaults = option[field]
    path = f"display.dropListOption.{field}"
    if not isinstance(defaults, list):
        errors.append(
            error(
                path,
                "DropListPro default selection must be a boolean array aligned with list",
                defaults,
                "boolean[]",
                "DROPLIST_DEFAULT_TYPE",
            )
        )
        return
    values = option.get("list") if isinstance(option.get("list"), list) else []
    for index, value in enumerate(defaults):
        if type(value) is not bool:
            errors.append(
                error(
                    f"{path}[{index}]",
                    "DropListPro default selection entries must be booleans, not option values",
                    value,
                    "boolean",
                    "DROPLIST_DEFAULT_ITEM_TYPE",
                )
            )
        elif value and (index >= len(values) or values[index] is None or values[index] == ""):
            errors.append(
                error(
                    f"{path}[{index}]",
                    "DropListPro true default must point at an existing list value",
                    value,
                    "matching display.dropListOption.list entry",
                    "DROPLIST_DEFAULT_MISSING_LIST_VALUE",
                )
            )


def validate_chart(chart, layout_type=None):
    errors, warnings, unchecked = [], [], []
    if not isinstance(chart, dict):
        return result(
            [error("chart", f"Invalid chart payload: expected object, got {value_type(chart)}")]
        )
    for key in ("type", "title"):
        value = chart.get(key, MISSING)
        if not isinstance(value, str) or not value:
            errors.append(error(key, f'Field "{key}" must be a non-empty string', value, "string"))
    if not isinstance(chart.get("search"), dict):
        errors.append(
            error(
                "search",
                'Field "search" must be an object',
                chart.get("search", MISSING),
                "object",
                "CHART_SEARCH_TYPE",
            )
        )
    if not isinstance(chart.get("display"), dict):
        errors.append(
            error(
                "display",
                'Field "display" must be an object',
                chart.get("display", MISSING),
                "object",
            )
        )
        return result(errors, warnings)
    kind = chart.get("type")
    if isinstance(kind, str):
        schema = schemas().get(kind)
        if schema is None:
            if kind in LEGACY_CHART_TYPES:
                warnings.append(
                    error(
                        "type",
                        f'Legacy chart type "{kind}": only basic structure is checked; the saved format is preserved',
                        code="LEGACY_CHART_FORMAT",
                    )
                )
            else:
                warnings.append(
                    error(
                        "type",
                        f'Chart type "{kind}" is not registered in validator schema',
                        kind,
                        f"Supported chart types: {', '.join(get_supported_chart_types())}",
                        "UNKNOWN_CHART_TYPE",
                    )
                )
        elif schema.get("children"):
            display_schema(chart["display"], schema, "display", errors, warnings)
        else:
            unchecked.append(
                error(
                    "display",
                    f'Chart type "{kind}" has only basic validation',
                    code="PARTIAL_CHART_VALIDATION",
                )
            )
    if not isinstance(kind, str):
        return result(errors, warnings)
    if layout_type == "grid":
        grid_position(chart, warnings)
    chart_queries(chart, errors, warnings)
    droplist_defaults(chart, errors)
    return result(errors, warnings, unchecked=unchecked)


def validate_dashboard(dashboard):
    errors, warnings, unchecked = [], [], []
    if not isinstance(dashboard, dict):
        return result(
            [
                error(
                    "dashboard",
                    f"Invalid dashboard payload: expected object, got {value_type(dashboard)}",
                )
            ]
        )
    display_name = dashboard.get("displayName", MISSING)
    if not isinstance(display_name, str) or not display_name.strip():
        errors.append(
            error(
                "displayName",
                'Field "displayName" must be a non-empty string',
                display_name,
                "non-empty string",
                "DASHBOARD_DISPLAY_NAME_REQUIRED",
            )
        )
    attribute = dashboard.get("attribute")
    layout_type = "free"
    if attribute is not None and not isinstance(attribute, dict):
        errors.append(
            error(
                "attribute",
                'Field "attribute" must be an object',
                attribute,
                "object",
                "DASHBOARD_ATTRIBUTE_TYPE",
            )
        )
    else:
        layout_type = (attribute or {}).get("type")
        if layout_type in (None, ""):
            layout_type = "free"
        elif layout_type not in ("grid", "free"):
            enum_value(
                "attribute.type",
                layout_type,
                ["grid", "free"],
                "DASHBOARD_LAYOUT_TYPE",
                errors,
                warnings,
            )
            layout_type = None
    charts = dashboard.get("charts", MISSING)
    if not isinstance(charts, list):
        errors.append(error("charts", 'Field "charts" must be an array', charts, "array"))
        return result(errors, warnings)
    for index, chart in enumerate(charts):
        report = validate_chart(chart, layout_type)
        for field, destination in (
            ("errors", errors),
            ("warnings", warnings),
            ("unchecked", unchecked),
        ):
            for entry in report.get(field, []):
                item = {**entry, "path": f"charts[{index}].{entry['path']}"}
                if isinstance(chart, dict) and isinstance(chart.get("title"), str):
                    item["chartId"] = chart["title"]
                destination.append(item)
    return result(errors, warnings, unchecked=unchecked)
