"""Offline Python validation: chart schema, scope, references, and layout."""
from __future__ import annotations

import copy
import json
import re

from .common import DASHBOARD_DATASOURCES, SkillError, effective_datasource
from .changes import chart_map
from .chart_validator import validate_dashboard

TOKEN = re.compile(r"\$\{\{([^{}|]+)(?:\|[^{}]*)?\}\}|\$\{([^{}|]+)(?:\|[^{}]*)?\}")


def issue(code, path, message):
    return {"code": code, "path": path, "message": message}


def validate(root, baseline=None):
    errors, warnings, unchecked = [], [], []
    if not isinstance(root, dict):
        return {"valid": False, "errors": [issue("DASHBOARD_TYPE", "$", "Expected object")],
                "warnings": [], "unchecked": []}
    try:
        charts = chart_map(root)
        original = chart_map(baseline) if baseline is not None else {}
    except SkillError as exc:
        return {"valid": False, "errors": [issue(exc.code, "$", str(exc))], "warnings": [], "unchecked": []}
    checked = copy.deepcopy(root)
    checked["charts"] = []
    checked_positions = []
    skip_token_checks = set()
    for title, entry in charts.items():
        chart = entry["chart"]
        search = chart.get("search", {})
        queries = search.get("chartQueries", []) if isinstance(search, dict) else []
        typed_sources = isinstance(queries, list) and all(
            isinstance(q, dict) and isinstance(q.get("datasource"), str) and q["datasource"].strip()
            for q in queries)
        unsupported = typed_sources and any(effective_datasource(q) not in DASHBOARD_DATASOURCES for q in queries)
        if unsupported and title in original and chart == original[title]["chart"]:
            unchecked.append(issue("PRESERVED_UNSUPPORTED_SOURCE", title, "Unchanged non-SLS content preserved, not validated"))
            skip_token_checks.add(title)
            continue
        checked["charts"].append(chart)
        checked_positions.append(entry["index"])
    report = validate_dashboard(checked)
    for collection in ("errors", "warnings"):
        for item in report[collection]:
            match = re.match(r"^charts\[(\d+)\]", item.get("path", ""))
            if match:
                position = int(match.group(1))
                item["path"] = f"charts[{checked_positions[position]}]" + item["path"][match.end():]
                chart = checked["charts"][position]
                title = chart["title"]
                preserved = False
                if collection == "errors" and title in original:
                    previous = original[title]["chart"]
                    if item.get("code") == "UNKNOWN_CHART_TYPE":
                        preserved = chart == previous
                if preserved:
                    unchecked.append(issue("PRESERVED_UNKNOWN_CONTENT", item["path"],
                                           "Unchanged configuration preserved without validation of this chart type"))
                    if item.get("code") == "UNKNOWN_CHART_TYPE":
                        skip_token_checks.add(title)
                    continue
            (errors if collection == "errors" else warnings).append(item)

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "unchecked": unchecked}
    titles = set(charts)
    token_keys = set()
    token_owners = {}
    for title, entry in charts.items():
        chart = entry["chart"]
        display = chart.get("display", {})
        if not isinstance(display, dict):
            continue
        option = display.get("dropListOption", {})
        if chart.get("type") == "droplistpro" and isinstance(option, dict) and option.get("type") == "token":
            key = option.get("key")
            if key in token_keys:
                errors.append(issue("DUPLICATE_TOKEN", title, f"Duplicate token key: {key}"))
            token_keys.add(key)
            token_owners[title] = key
        refs = [display.get("belongChart")] + (display.get("charts", []) if isinstance(display.get("charts"), list) else [])
        refs += chart.get("state", {}).get("collaspedCharts", []) if isinstance(chart.get("state"), dict) else []
        for ref in refs:
            if ref and (not isinstance(ref, str) or ref not in titles):
                errors.append(issue("DANGLING_CHART_REFERENCE", title, f"Unknown chart reference: {ref}"))
    dependencies = {}
    used = set()
    for title, entry in charts.items():
        chart = entry["chart"]
        if title in skip_token_checks:
            continue
        display = chart.get("display", {})
        if not isinstance(display, dict):
            continue
        definitions = display.get("innerTokenOption", [])
        local = {item["key"] for item in definitions if isinstance(item, dict) and isinstance(item.get("key"), str)} if isinstance(definitions, list) else set()
        # Actions have click-context variables; scan only query/resource inputs and text templates.
        payload = json.dumps(chart.get("search", {}), ensure_ascii=False)
        query_tokens = {a or b for a, b in TOKEN.findall(payload)}
        for token in query_tokens:
            if token not in local:
                used.add(token)
            if token not in token_keys | local and not token.startswith("__"):
                warnings.append(issue("EXTERNAL_TOKEN", title, f"Token {token} needs a caller-supplied value or default"))
        if title in token_owners:
            dependencies[token_owners[title]] = (query_tokens - local) & token_keys
        content = ""
        if chart.get("type") == "markdownpro":
            content = display.get("markdownStr", "")
        elif chart.get("type") == "textpro":
            option = display.get("contentOption", {})
            if not isinstance(option, dict):
                option = {}
            if option.get("mode", display.get("mode", "markdown")) == "markdown":
                content = next((value for value in (option.get("content"), display.get("content"),
                               display.get("markdownStr"), display.get("text")) if value is not None), "")
        for token in {a or b for a, b in TOKEN.findall(content if isinstance(content, str) else "")}:
            if token in local:
                continue
            if token in token_keys:
                used.add(token)
            elif token.startswith("__"):
                continue
            elif chart.get("search", {}).get("chartQueries"):
                unchecked.append(issue("CONTENT_FIELD_NOT_CHECKED", title,
                                       f"Template {token} needs a matching result field or supplied variable"))
            else:
                warnings.append(issue("EXTERNAL_TOKEN", title, f"Token {token} needs a caller-supplied value or default"))
    def visit(key, active, done):
        if key in active:
            errors.append(issue("TOKEN_CYCLE", key, "Dynamic candidate queries contain a token dependency cycle"))
            return
        if key in done:
            return
        for dependency in dependencies.get(key, set()):
            visit(dependency, active | {key}, done)
        done.add(key)
    done = set()
    for key in dependencies:
        visit(key, set(), done)
    for key in token_keys - used:
        warnings.append(issue("UNUSED_TOKEN", str(key), "No query or content template consumes this token"))
    attribute = root.get("attribute")
    if isinstance(attribute, dict) and attribute.get("type") == "grid":
        rectangles = []
        for title, entry in charts.items():
            display = entry["chart"].get("display", {})
            coords = [display.get(key) for key in ("xPos", "yPos", "width", "height")] if isinstance(display, dict) else []
            if len(coords) != 4 or any(type(value) is not int for value in coords) or display.get("fixedTop"):
                continue
            x, y, w, h = coords
            for other, ox, oy, ow, oh in rectangles:
                if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                    # Do not turn unrelated pre-existing layout debt into a forced rewrite.
                    preserved = (title in original and other in original and
                                 entry["chart"] == original[title]["chart"] and charts[other]["chart"] == original[other]["chart"])
                    (warnings if preserved else errors).append(issue("GRID_OVERLAP", title, f"Overlaps {other}"))
            rectangles.append((title, x, y, w, h))
    unchecked.append(issue("ONLINE_NOT_CHECKED", "$", "Offline validation does not execute queries or verify rendering"))
    return {"valid": not errors, "errors": errors, "warnings": warnings, "unchecked": unchecked}


def require_valid(root, baseline=None):
    report = validate(root, baseline)
    if not report["valid"]:
        raise SkillError("Dashboard validation failed", "VALIDATION_FAILED", report=report)
    return report
