"""Offline Python validation: chart schema, scope, references, and layout."""

from .common import SkillError
from .changes import chart_map
from .chart_validator import participates_in_grid, validate_dashboard
from .validation_report import result
from .validation_baseline import preserve_issues
from .validation_tokens import query_inputs, token_requirements


def issue(code, path, message, **details):
    return {"code": code, "path": path, "message": message, **details}


def _validate(root):
    errors, warnings, unchecked = [], [], []
    if not isinstance(root, dict):
        return result([issue("DASHBOARD_TYPE", "$", "Expected object")], unchecked=[])
    try:
        charts = chart_map(root)
    except SkillError as exc:
        return result([issue(exc.code, "$", str(exc))], unchecked=[])
    report = validate_dashboard(root)
    errors.extend(report["errors"])
    warnings.extend(report["warnings"])
    unchecked.extend(report.get("unchecked", []))
    titles = set(charts)
    token_keys = set()
    token_owners = {}
    for title, entry in sorted(charts.items()):
        chart = entry["chart"]
        display = chart.get("display", {})
        if not isinstance(display, dict):
            continue
        option = display.get("dropListOption", {})
        if (
            chart.get("type") == "droplistpro"
            and isinstance(option, dict)
            and option.get("type") == "token"
        ):
            key = option.get("key")
            if isinstance(key, str) and key:
                if key in token_keys:
                    errors.append(
                        issue(
                            "DUPLICATE_TOKEN", title, f"Duplicate token key: {key}", chartId=title
                        )
                    )
                token_keys.add(key)
                token_owners[title] = key
        refs = [display.get("belongChart")] + (
            display.get("charts", []) if isinstance(display.get("charts"), list) else []
        )
        state = chart.get("state", {})
        children = state.get("collaspedCharts") if isinstance(state, dict) else None
        refs += children if isinstance(children, list) else []
        for ref in refs:
            if ref and (not isinstance(ref, str) or ref not in titles):
                errors.append(
                    issue(
                        "DANGLING_CHART_REFERENCE",
                        title,
                        f"Unknown chart reference: {ref}",
                        chartId=title,
                    )
                )
    dependencies = {}
    used = set()
    for title, entry in sorted(charts.items()):
        chart = entry["chart"]
        display = chart.get("display", {})
        if not isinstance(display, dict):
            continue
        definitions = display.get("innerTokenOption", [])
        local = (
            {
                item["key"]
                for item in definitions
                if isinstance(item, dict) and isinstance(item.get("key"), str)
            }
            if isinstance(definitions, list)
            else set()
        )
        # Actions have click-context variables; scan only query/resource inputs and text templates.
        search = chart.get("search", {})
        if not isinstance(search, dict):
            search = {}
        requirements = token_requirements(query_inputs(chart))
        query_tokens = set(requirements)
        for token in sorted(query_tokens):
            if token not in local:
                used.add(token)
            if (
                requirements[token]
                and token not in token_keys | local
                and not token.startswith("__")
            ):
                warnings.append(
                    issue(
                        "EXTERNAL_TOKEN",
                        title,
                        f"Token {token} needs a caller-supplied value or default",
                        chartId=title,
                    )
                )
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
                content = next(
                    (
                        value
                        for value in (
                            option.get("content"),
                            display.get("content"),
                            display.get("markdownStr"),
                            display.get("text"),
                        )
                        if value is not None
                    ),
                    "",
                )
        for token, needs_value in sorted(token_requirements([content]).items()):
            if token in local:
                continue
            if token in token_keys:
                used.add(token)
            elif token.startswith("__") or not needs_value:
                continue
            elif search.get("chartQueries"):
                unchecked.append(
                    issue(
                        "CONTENT_FIELD_NOT_CHECKED",
                        title,
                        f"Template {token} needs a matching result field or supplied variable",
                    )
                )
            else:
                warnings.append(
                    issue(
                        "EXTERNAL_TOKEN",
                        title,
                        f"Token {token} needs a caller-supplied value or default",
                        chartId=title,
                    )
                )

    def visit(key, active, done):
        if key in active:
            errors.append(
                issue(
                    "TOKEN_CYCLE", key, "Dynamic candidate queries contain a token dependency cycle"
                )
            )
            return
        if key in done:
            return
        for dependency in sorted(dependencies.get(key, set())):
            visit(dependency, active | {key}, done)
        done.add(key)

    done = set()
    for key in sorted(dependencies):
        visit(key, set(), done)
    for key in sorted(token_keys - used):
        warnings.append(
            issue("UNUSED_TOKEN", str(key), "No query or content template consumes this token")
        )
    attribute = root.get("attribute")
    if isinstance(attribute, dict) and attribute.get("type") == "grid":
        rectangles = []
        for title, entry in sorted(charts.items()):
            display = entry["chart"].get("display", {})
            coords = (
                [display.get(key) for key in ("xPos", "yPos", "width", "height")]
                if isinstance(display, dict)
                else []
            )
            if (
                not participates_in_grid(entry["chart"])
                or len(coords) != 4
                or any(type(value) is not int for value in coords)
            ):
                continue
            x, y, w, h = coords
            for other, ox, oy, ow, oh in rectangles:
                if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                    warnings.append(
                        issue(
                            "GRID_OVERLAP",
                            title,
                            f"Overlaps {other}",
                            chartId=title,
                            relatedChartId=other,
                        )
                    )
            rectangles.append((title, x, y, w, h))
    unchecked.append(
        issue(
            "ONLINE_NOT_CHECKED",
            "$",
            "Offline validation does not execute queries or verify rendering",
        )
    )
    return result(errors, warnings, unchecked=unchecked)


def validate(root, baseline=None, *, mode="standalone"):
    if mode not in {"standalone", "update"}:
        return result(
            [issue("VALIDATION_MODE", "$", "Expected standalone or update mode")], unchecked=[]
        )
    if mode == "standalone" and baseline is not None:
        return result(
            [issue("BASELINE_MODE", "$", "A baseline requires update mode")], unchecked=[]
        )
    if mode == "update":
        if not isinstance(baseline, dict):
            return result(
                [
                    issue(
                        "BASELINE_REQUIRED",
                        "$",
                        "Update validation requires the original dashboard",
                    )
                ],
                unchecked=[],
            )
        try:
            chart_map(baseline)
        except SkillError as exc:
            return result([issue("BASELINE_INVALID", "$", str(exc))], unchecked=[])
        if (
            isinstance(root, dict)
            and baseline.get("dashboardName") is not None
            and root.get("dashboardName") != baseline["dashboardName"]
        ):
            return result(
                [
                    issue(
                        "BASELINE_TARGET_MISMATCH",
                        "dashboardName",
                        "Dashboard identity differs from the baseline",
                    )
                ],
                unchecked=[],
            )
    report = _validate(root)
    if (
        mode == "update"
        and isinstance(root, dict)
        and not any(item["path"] == "$" for item in report["errors"])
    ):
        report = preserve_issues(root, baseline, report, _validate(baseline))
    return report
