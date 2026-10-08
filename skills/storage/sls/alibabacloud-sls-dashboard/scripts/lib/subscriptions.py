"""Dashboard subscriptions: one Report Job per dashboard, multiple notification channels."""
from __future__ import annotations

import copy
import re
from urllib.parse import urlsplit

from .common import DATASOURCES, SkillError, effective_datasource, load

JOB_FIELDS = ("name", "displayName", "description", "type", "state", "recyclable", "configuration", "schedule")


def check_target(target):
    if not isinstance(target, dict) or any(not isinstance(target.get(k), str) or not target[k].strip()
                                           for k in ("region", "project", "name")):
        raise SkillError("Subscription target requires region, project and dashboard name")


def job_payload(value):
    return {key: copy.deepcopy(value[key]) for key in JOB_FIELDS if key in value}


def normalize_job(value, target):
    check_target(target)
    if not isinstance(value, dict) or value.get("type") != "Report":
        raise SkillError("Dashboard subscriptions require type=Report")
    job = copy.deepcopy(value)
    for key in ("name", "displayName"):
        if not isinstance(job.get(key), str) or not job[key].strip():
            raise SkillError(f"Report requires {key}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", job["name"]):
        raise SkillError("Invalid Report Job name")
    if job.get("state") not in {"Enabled", "Disabled"}:
        raise SkillError("Report state must be Enabled or Disabled")
    if "recyclable" in job and type(job["recyclable"]) is not bool:
        raise SkillError("Report recyclable must be boolean")
    config = job.get("configuration")
    if not isinstance(config, dict) or config.get("dashboard") != target["name"]:
        raise SkillError("Report configuration.dashboard differs from the target", "REPORT_TARGET_MISMATCH")
    for field in ("allowAnonymousAccess", "attachCsv", "customizePeriod", "enableWatermark"):
        if field in config and type(config[field]) is not bool:
            raise SkillError(f"Report configuration.{field} must be boolean")
    if "extraParams" in config and not isinstance(config["extraParams"], str):
        raise SkillError("Report extraParams must remain its encoded string")
    channels = config.get("notificationList")
    if not isinstance(channels, list) or not channels:
        raise SkillError("At least one Report notification channel is required")
    for channel in channels:
        if not isinstance(channel, dict) or not isinstance(channel.get("type"), str) or not channel["type"]:
            raise SkillError("Every notification channel requires its supplied type")
        if channel["type"] == "Email":
            addresses = channel.get("emailList")
            if isinstance(addresses, str):
                addresses = [x.strip() for x in addresses.split(",")]
            if not isinstance(addresses, list) or not addresses or any(
                    not isinstance(x, str) or not re.fullmatch(r"[^\s@,]+@[^\s@,]+", x) for x in addresses):
                raise SkillError("Email requires an emailList array or comma-separated recipient string")
            channel["emailList"] = addresses
            if "subject" in channel and not isinstance(channel["subject"], str):
                raise SkillError("Email subject must be a string")
        else:
            # Exact webhook type literals come from supplied/exported configuration.
            uri = channel.get("serviceUri")
            try:
                parsed = urlsplit(uri) if isinstance(uri, str) else None
            except ValueError:
                parsed = None
            if parsed is None or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise SkillError("Webhook channels require a valid serviceUri")
            if "title" in channel and not isinstance(channel["title"], str):
                raise SkillError("Webhook title must be a string")
    schedule = job.get("schedule")
    if not isinstance(schedule, dict) or schedule.get("type") not in {"Hourly", "Daily", "Weekly", "FixedRate", "Cron"}:
        raise SkillError("A supported Report schedule is required")
    if schedule["type"] in {"Daily", "Weekly"} and (
            type(schedule.get("hour")) is not int or not 0 <= schedule["hour"] <= 23):
        raise SkillError("Daily/Weekly schedule hour must be an integer from 0 through 23")
    if schedule["type"] == "Weekly" and "dayOfWeek" not in schedule:
        raise SkillError("Weekly schedule requires dayOfWeek")
    if schedule["type"] == "Cron" and not str(schedule.get("cronExpression", "")).strip():
        raise SkillError("Cron schedule requires cronExpression")
    if schedule["type"] == "FixedRate" and not schedule.get("interval"):
        raise SkillError("FixedRate schedule requires interval")
    if "runImmediately" in schedule and type(schedule["runImmediately"]) is not bool:
        raise SkillError("schedule.runImmediately must be boolean")
    return job_payload(job)


def check_dashboard(root, target, client=None):
    """Reject explicit cross-project sources; view members are checked when online."""
    if not isinstance(root, dict) or not isinstance(root.get("charts"), list):
        raise SkillError("A complete dashboard configuration is required")
    if root.get("dashboardName", target["name"]) != target["name"]:
        raise SkillError("Dashboard identity differs from subscription target")
    unchecked, views = [], set()
    for chart in root["charts"]:
        if not isinstance(chart, dict) or not isinstance(chart.get("search", {}), dict):
            raise SkillError("Malformed dashboard chart")
        search = chart.get("search", {})
        if "chartQueries" not in search and search.get("query") not in (None, "", "@"):
            raise SkillError("Resolve legacy chart datasource coordinates before subscribing",
                             "UNRESOLVED_SUBSCRIPTION_SOURCE")
        queries = search.get("chartQueries", [])
        if not isinstance(queries, list):
            raise SkillError("Dashboard chartQueries must be an array")
        for query in queries:
            if (not isinstance(query, dict) or not isinstance(query.get("datasource"), str)
                    or effective_datasource(query) not in DATASOURCES):
                raise SkillError("Subscription datasource must be a resolved supported SLS source",
                                 "UNRESOLVED_SUBSCRIPTION_SOURCE")
            project = query.get("project")
            if not isinstance(project, str) or not project or "$" in project:
                raise SkillError("Resolve the datasource Project before subscribing",
                                 "UNRESOLVED_SUBSCRIPTION_SOURCE")
            if project != target["project"]:
                raise SkillError("Dashboard subscriptions cannot query another Project",
                                 "CROSS_PROJECT_SUBSCRIPTION")
            if effective_datasource(query).endswith("_storeview"):
                name = query.get("logstore")
                if not isinstance(name, str) or not name or "$" in name:
                    raise SkillError("Resolve the StoreView name before subscribing",
                                     "UNRESOLVED_SUBSCRIPTION_SOURCE")
                views.add((effective_datasource(query), name))
    for kind, name in sorted(views):
        if client is None:
            unchecked.append(f"StoreView member Projects require online verification: {name}")
            continue
        metadata = client.describe({"id": name, "type": kind, "name": name,
                                    "project": target["project"], "region": target["region"]})
        members = metadata.get("stores") if isinstance(metadata, dict) else None
        if not isinstance(members, list) or not members:
            raise SkillError("Cannot establish StoreView member Projects", "UNRESOLVED_SUBSCRIPTION_SOURCE")
        for member in members:
            project = member.get("projectName", member.get("project")) if isinstance(member, dict) else None
            if not isinstance(project, str) or not project:
                raise SkillError("Cannot establish StoreView member Project", "UNRESOLVED_SUBSCRIPTION_SOURCE")
            if project != target["project"]:
                raise SkillError("StoreView includes data from another Project",
                                 "CROSS_PROJECT_SUBSCRIPTION")
    return unchecked


def list_reports(client, target, size=10):
    check_target(target)
    results, seen, offset = [], set(), 0
    while True:
        page = client.list_report_jobs(target["project"], target["name"], offset, size)
        rows = page.get("results") if isinstance(page, dict) else None
        if not isinstance(rows, list):
            raise SkillError("ListJobs response requires results[]", "INVALID_RESPONSE")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str) or row["name"] in seen:
                raise SkillError("ListJobs returned malformed or repeated jobs", "INVALID_RESPONSE")
            config = row.get("configuration")
            if row.get("type") != "Report" or not isinstance(config, dict) or config.get("dashboard") != target["name"]:
                raise SkillError("ListJobs returned a job outside the requested dashboard", "REPORT_TARGET_MISMATCH")
            seen.add(row["name"])
            results.append(row)
        offset += len(rows)
        total = page.get("total")
        if total is not None:
            if isinstance(total, str) and total.isdigit():
                total = int(total)
            if type(total) is not int or total < offset:
                raise SkillError("Invalid ListJobs total", "INVALID_RESPONSE")
            if offset >= total:
                break
            if not rows:
                raise SkillError("ListJobs pagination ended before total", "INCOMPLETE_JOB_LIST")
        elif len(rows) < size:
            break
        if offset >= 10000:
            raise SkillError("Report listing exceeded its bound; no write attempted", "INCOMPLETE_JOB_LIST")
    return {"version": 1, "target": copy.deepcopy(target), "results": results,
            "total": len(results), "complete": True}


def baseline_job(baseline, target):
    if not isinstance(baseline, dict) or baseline.get("version") != 1 or baseline.get("target") != target or baseline.get("complete") is not True:
        raise SkillError("Use an unmodified subscription list result for the same target as baseline",
                         "REPORT_BASELINE_INVALID")
    rows = baseline.get("results")
    if not isinstance(rows, list) or len(rows) != 1:
        raise SkillError("Update/delete requires exactly one baseline Report Job", "REPORT_BASELINE_INVALID")
    return normalize_job(rows[0], target)


def prepare(action, target, value=None, baseline=None, dashboard=None):
    check_target(target)
    previous = baseline_job(baseline, target) if action in {"update", "delete"} else None
    job = normalize_job(value, target) if action in {"validate", "create", "update"} else None
    if job and previous and job["name"] != previous["name"]:
        raise SkillError("Update cannot rename or retarget a Report Job", "REPORT_TARGET_MISMATCH")
    unchecked = []
    if action != "delete" and not (action == "update" and job["state"] == "Disabled"):
        unchecked = (check_dashboard(dashboard, target) if dashboard is not None
                     else ["Dashboard source Projects have not been checked offline"])
    return {"status": "prepared", "action": action, "target": target,
            "job": job or previous, "unchecked": unchecked}


def contains_requested(actual, requested):
    if isinstance(requested, dict):
        return isinstance(actual, dict) and all(k in actual and contains_requested(actual[k], v)
                                               for k, v in requested.items())
    if isinstance(requested, list):
        return isinstance(actual, list) and len(actual) == len(requested) and all(
            contains_requested(a, b) for a, b in zip(actual, requested))
    return actual == requested


def apply(client, action, target, value=None, baseline=None):
    if action not in {"create", "update", "delete"}:
        raise SkillError("Invalid Report mutation")
    prepared = prepare(action, target, value, baseline)
    job = prepared["job"]
    current = list_reports(client, target)["results"]
    if action == "create":
        if current:
            raise SkillError("This dashboard already has a Report Job; update its notificationList",
                             "REPORT_ALREADY_EXISTS")
    else:
        expected = baseline_job(baseline, target)
        if len(current) != 1 or job_payload(current[0]) != expected:
            raise SkillError("Report changed since baseline; reload it before editing", "REPORT_CONFLICT")
    if action != "delete" and not (action == "update" and job["state"] == "Disabled"):
        check_dashboard(client.get_dashboard(target["project"], target["name"]), target, client)
    failure = None
    try:
        if action == "delete":
            client.delete_report_job(target["project"], job["name"])
        else:
            client.put_report_job(target["project"], job, action)
    except SkillError as exc:
        failure = exc
    try:
        online = list_reports(client, target)
    except SkillError:
        raise SkillError("Report write result is uncertain; inspect before retrying",
                         "REPORT_WRITE_UNCERTAIN") from None
    if action == "delete":
        matched = not online["results"]
    else:
        matched = len(online["results"]) == 1 and contains_requested(online["results"][0], job)
    if not matched:
        raise SkillError("Report write could not be confirmed; no automatic retry",
                         "REPORT_WRITE_UNCERTAIN" if failure else "REPORT_READBACK_MISMATCH")
    return {"status": "deleted" if action == "delete" else "saved", "action": action,
            "target": target, "subscription": online, "reconciledAfterError": failure is not None,
            "unchecked": ["Notification delivery and the shared daily mailbox quota were not verified"]}


def configure_cli(commands):
    parser = commands.add_parser("subscription", help="List, validate, create, update or delete Report subscriptions")
    actions = parser.add_subparsers(dest="subscription_action", required=True)
    for action in ("list", "validate", "create", "update", "delete"):
        sub = actions.add_parser(action)
        for key in ("region", "project", "name"):
            sub.add_argument("--" + key, required=True, help="Dashboard target" if key == "name" else None)
        sub.add_argument("--output")
        if action in {"validate", "create", "update"}:
            sub.add_argument("--input", required=True, help="Complete Report Job JSON")
            sub.add_argument("--dashboard", help="Local Dashboard JSON for offline source checks")
        if action in {"update", "delete"}:
            sub.add_argument("--baseline", required=True, help="Unmodified subscription list JSON")
        if action != "validate":
            sub.add_argument("--profile")
            sub.add_argument("--endpoint", help="SLS service endpoint override (host or HTTP(S) base URL)")
            sub.add_argument("--timeout", type=int, default=60)
            sub.add_argument("--aliyun", default="aliyun")
        if action in {"create", "update", "delete"}:
            sub.add_argument("--execute", action="store_true")


def run_cli(args, client_factory):
    target = {key: getattr(args, key) for key in ("region", "project", "name")}
    action = args.subscription_action
    if action == "list":
        return list_reports(client_factory(args.region, args.profile, args.aliyun, args.timeout,
                                           endpoint=args.endpoint), target)
    value = load(args.input) if getattr(args, "input", None) else None
    baseline = load(args.baseline) if getattr(args, "baseline", None) else None
    dashboard = load(args.dashboard) if getattr(args, "dashboard", None) else None
    result = prepare(action, target, value, baseline, dashboard)
    if getattr(args, "execute", False):
        return apply(client_factory(args.region, args.profile, args.aliyun, args.timeout, endpoint=args.endpoint),
                     action, target, value, baseline)
    return result
