"""Explicit online operations with immutable baselines."""
from __future__ import annotations

import copy
from urllib.parse import quote, urlencode
from .common import SkillError, compare_payload, dashboard_payload, digest
from .changes import check_snapshot
from .sls_client import CliError
from .validation import require_valid


def prepare(root, target, mode, source_snapshot=None):
    if mode not in {"create", "update"}:
        raise SkillError("Expected create or update mode")
    for key in ("region", "project", "name"):
        if not isinstance(target.get(key), str) or not target[key].strip():
            raise SkillError(f"Publish target requires {key}")
    baseline = check_snapshot(source_snapshot or {}, target) if mode == "update" else None
    if mode == "create" and (not isinstance(root, dict) or not isinstance(root.get("attribute"), dict)
                             or root["attribute"].get("type") not in ("grid", "free")):
        raise SkillError("New dashboards require explicit attribute.type: grid or free", "DASHBOARD_LAYOUT_REQUIRED")
    require_valid(root, baseline)
    payload = dashboard_payload(root)
    if payload.get("dashboardName", target["name"]) != target["name"]:
        raise SkillError("Dashboard name differs from publish target")
    payload["dashboardName"] = target["name"]
    require_valid(payload, baseline)
    return payload, baseline


def publish(client, root, target, mode, source_snapshot=None):
    payload, baseline = prepare(root, target, mode, source_snapshot)
    report = require_valid(payload, baseline)
    url = ("https://sls.console.aliyun.com/lognext/project/" + quote(target["project"], safe="") +
           "/dashboard/" + quote(target["name"], safe="") + "?" + urlencode({"slsRegion": target["region"]}))
    if mode == "update":
        current = client.get_dashboard(target["project"], target["name"])
        if digest(compare_payload(current)) != digest(compare_payload(baseline)):
            raise SkillError("Online dashboard changed since snapshot", "CONFLICT")
    try:
        client.put_dashboard(target["project"], payload, mode)
    except CliError as exc:
        raise SkillError("Write request failed; inspect the target before retrying",
                         "WRITE_UNCERTAIN", originalCode=exc.code, originalMessage=str(exc),
                         target=copy.deepcopy(target),
                         consoleUrl=url) from exc
    return {"status": "published", "target": copy.deepcopy(target), "consoleUrl": url,
            "dashboard": payload, "validation": report}


def delete(client, target, source_snapshot):
    baseline = check_snapshot(source_snapshot, target)
    current = client.get_dashboard(target["project"], target["name"])
    if compare_payload(current) != compare_payload(baseline):
        raise SkillError("Online dashboard changed since snapshot", "CONFLICT")
    failure = None
    try:
        client.delete_dashboard(target["project"], target["name"])
    except CliError as exc:
        failure = exc
    try:
        client.get_dashboard(target["project"], target["name"])
    except CliError as exc:
        if exc.code in {"DashboardNotExist", "DashboardNotFound"}:
            return {"status": "deleted", "target": target}
        raise SkillError("Delete result is unknown; inspect the target before retrying",
                         "DELETE_UNCERTAIN", originalCode=(failure or exc).code) from exc
    raise SkillError("Dashboard still exists after delete; no automatic retry", "DELETE_UNCONFIRMED")
