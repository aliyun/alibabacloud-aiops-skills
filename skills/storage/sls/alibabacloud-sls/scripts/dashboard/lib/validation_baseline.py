"""Classify unchanged diagnostics from an update baseline without changing JSON."""

import json
import re

from .changes import chart_map
from .validation_report import result

MISSING = object()


def value_at(value, path):
    for part in re.findall(r"[^.\[\]]+", path):
        if isinstance(value, dict):
            value = value.get(part, MISSING)
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            return MISSING
    return value


def signature(item):
    # Array positions can change when charts are reordered; chartId is stable.
    item = dict(item)
    if "chartId" in item:
        item["path"] = re.sub(r"^charts\[\d+\]\.", "", item["path"])
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def layout(chart):
    display = chart.get("display")
    if not isinstance(display, dict):
        return display
    option = display.get("dropListOption")
    return {
        "type": chart.get("type"),
        "position": [display.get(k) for k in ("xPos", "yPos", "width", "height")],
        "fixedTop": display.get("fixedTop"),
        "showDropListChart": display.get("showDropListChart"),
        "dropListType": option.get("type") if isinstance(option, dict) else option,
    }


def context(root, charts, item):
    code, path = item["code"], item["path"]
    if code in {"DUPLICATE_TOKEN", "TOKEN_CYCLE", "EXTERNAL_TOKEN", "UNUSED_TOKEN"}:
        # Token relationships depend on definitions and consumers across charts.
        return {
            key: {
                "type": entry["chart"].get("type"),
                "search": entry["chart"].get("search"),
                "display": {
                    k: v
                    for k, v in entry["chart"].get("display", {}).items()
                    if k
                    in {
                        "dropListOption",
                        "innerTokenOption",
                        "contentOption",
                        "content",
                        "markdownStr",
                        "text",
                        "mode",
                    }
                },
            }
            for key, entry in charts.items()
            if isinstance(entry["chart"].get("display"), dict)
        }
    chart_id = item.get("chartId")
    if chart_id is None:
        return value_at(root, path)
    chart = charts[chart_id]["chart"]
    path = re.sub(r"^charts\[\d+\]\.", "", path)
    display = chart.get("display")
    display = display if isinstance(display, dict) else {}
    kind = chart.get("type")
    if code.startswith("GRID_"):
        related = item.get("relatedChartId")
        return (
            root.get("attribute"),
            layout(chart),
            layout(charts[related]["chart"]) if related in charts else None,
        )
    if code == "DANGLING_CHART_REFERENCE":
        # A newly missing target produces a new diagnostic in the current report.
        return (kind, display.get("belongChart"), display.get("charts"), chart.get("state"))
    if code.startswith(
        ("QUERY_", "SEARCH_", "METRICSTORE_", "CATEGORY_", "Y_FIELDS_", "INTERVAL_")
    ) or path.startswith("search."):
        return (
            kind,
            chart.get("search"),
            display.get("queryOptionMap"),
            display.get("bindQuery"),
            display.get("isTimeSeries"),
            display.get("dropListOption"),
        )
    if code.startswith("DROPLIST_"):
        return kind, display.get("dropListOption")
    value = value_at(chart, path)
    if value is MISSING and code != "REQUIRED":
        # Unknown path syntax (for example a map key containing dots): be conservative.
        return chart
    return kind, value


def same_value(left, right):
    # JSON booleans and numbers differ, even though Python considers False == 0.
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_value(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)):
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right))
    return left == right


def preserve_issues(root, baseline, report, previous):
    charts, original = chart_map(root), chart_map(baseline)
    old = {signature(item): item for key in ("errors", "warnings") for item in previous[key]}
    errors, warnings = [], []
    for collection in ("errors", "warnings"):
        for item in report[collection]:
            prior = old.get(signature(item))
            preserved = prior is not None and same_value(
                context(root, charts, item), context(baseline, original, prior)
            )
            if preserved:
                warnings.append({**item, "origin": "baseline"})
            else:
                (errors if collection == "errors" else warnings).append(item)
    return result(errors, warnings, unchecked=report["unchecked"])
