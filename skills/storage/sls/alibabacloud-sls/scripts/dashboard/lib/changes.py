"""Local dashboard comparison and non-destructive composition."""

import copy
from .common import SkillError, digest


def chart_map(root):
    if not isinstance(root, dict):
        raise SkillError("Dashboard must be an object")
    charts = root.get("charts")
    if not isinstance(charts, list):
        raise SkillError("Dashboard requires charts[]")
    result = {}
    for index, chart in enumerate(charts):
        if (
            not isinstance(chart, dict)
            or not isinstance(chart.get("title"), str)
            or not chart["title"]
        ):
            raise SkillError("Every chart needs a non-empty title")
        if chart["title"] in result:
            raise SkillError("Ambiguous duplicate chart title", title=chart["title"])
        result[chart["title"]] = {"index": index, "chart": chart, "hash": digest(chart)}
    return result


def diff(before, after):
    old, new = chart_map(before), chart_map(after)
    return {
        "added": sorted(key for key in new if key not in old),
        "deleted": sorted(key for key in old if key not in new),
        "modified": sorted(
            key for key in old if key in new and old[key]["hash"] != new[key]["hash"]
        ),
        "unchanged": sorted(
            key for key in old if key in new and old[key]["hash"] == new[key]["hash"]
        ),
        "dashboardFieldsChanged": sorted(
            key
            for key in set(before) | set(after)
            if key != "charts" and before.get(key) != after.get(key)
        ),
    }


def merge_additions(base, additions):
    old, new = chart_map(base), chart_map(additions)
    if set(old) & set(new):
        raise SkillError(
            "Added chart titles collide with existing content", titles=sorted(set(old) & set(new))
        )
    result = copy.deepcopy(base)
    result["charts"].extend(copy.deepcopy(additions["charts"]))
    return result
