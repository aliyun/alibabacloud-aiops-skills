"""Local snapshots and non-destructive dashboard composition."""
from __future__ import annotations

import copy
from .common import SkillError, compare_payload, digest


def chart_map(root):
    charts = root.get("charts")
    if not isinstance(charts, list):
        raise SkillError("Dashboard requires charts[]")
    result = {}
    for index, chart in enumerate(charts):
        if not isinstance(chart, dict) or not isinstance(chart.get("title"), str) or not chart["title"]:
            raise SkillError("Every chart needs a non-empty title")
        if chart["title"] in result:
            raise SkillError("Ambiguous duplicate chart title", title=chart["title"])
        result[chart["title"]] = {"index": index, "chart": chart, "hash": digest(chart)}
    return result


def snapshot(root, target):
    for key in ("region", "project", "name"):
        if not isinstance(target.get(key), str) or not target[key].strip():
            raise SkillError(f"Snapshot target requires {key}")
    if root.get("dashboardName", target["name"]) != target["name"]:
        raise SkillError("Source dashboardName differs from snapshot target")
    return {"version": 1, "target": copy.deepcopy(target), "dashboard": copy.deepcopy(root),
            "hash": digest(compare_payload(root)),
            "charts": [{"title": key, "index": value["index"], "hash": value["hash"]}
                       for key, value in chart_map(root).items()]}


def check_snapshot(value, target):
    if value.get("version") != 1 or value.get("target") != target:
        raise SkillError("Snapshot belongs to a different publish target", "BASELINE_TARGET_MISMATCH")
    root = value.get("dashboard", {})
    if value.get("hash") != digest(compare_payload(root)):
        raise SkillError("Snapshot content hash does not match", "BASELINE_INVALID")
    chart_map(root)
    return root


def diff(before, after):
    old, new = chart_map(before), chart_map(after)
    retained_before = [key for key in old if key in new]
    retained_after = [key for key in new if key in old]
    return {"added": [key for key in new if key not in old],
            "deleted": [key for key in old if key not in new],
            "modified": [key for key in old if key in new and old[key]["hash"] != new[key]["hash"]],
            "unchanged": [key for key in old if key in new and old[key]["hash"] == new[key]["hash"]],
            "existingOrderPreserved": retained_before == retained_after,
            "dashboardFieldsChanged": sorted(key for key in set(before) | set(after)
                                             if key != "charts" and before.get(key) != after.get(key))}


def merge_additions(base, additions):
    old, new = chart_map(base), chart_map(additions)
    if set(old) & set(new):
        raise SkillError("Added chart titles collide with existing content", titles=sorted(set(old) & set(new)))
    result = copy.deepcopy(base)
    result["charts"].extend(copy.deepcopy(additions["charts"]))
    return result
