#!/usr/bin/env python3
"""Query VVP dashboards and historical Metrics with a user-provided Cookie."""

import getpass
import json
import math
import os
import re
import sys
import warnings
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from client import SkillIdentityError, add_common_args, build_user_agent, error_response, output, require_args, success_response


class MetricError(RuntimeError):
    def __init__(self, message, code="MetricQueryError", request_id=""):
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward the Cookie to a login page or another domain.
        return None


def read_cookie(args):
    if args.cookie_stdin:
        if sys.stdin.isatty():
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                try:
                    value = getpass.getpass("VVP Cookie (input hidden): ")
                except getpass.GetPassWarning:
                    raise MetricError("Unable to disable terminal echo; provide the Cookie through standard input instead.", "MetricAuthError")
        else:
            value = sys.stdin.readline()
    else:
        value = os.environ.get("VVP_COOKIE", "")
    value = value.strip()
    if not value:
        raise MetricError("Cookie is missing; provide it as described in references/diagnosis/job-observability.md.", "MetricAuthError")
    if "=" not in value or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise MetricError("Invalid Cookie format; copy the single-line Cookie value from the request headers.", "MetricAuthError")
    return value


def redact(value, cookie):
    # Ignore short values such as language codes and flags to preserve ordinary labels.
    # Always redact the complete authentication Cookie.
    secrets = [cookie]
    for part in cookie.split(";"):
        key, _, secret = part.strip().partition("=")
        if len(secret) >= 8 or re.search(r"(?i)session|ticket|token|csrf|auth", key):
            secrets.extend([secret, quote(secret, safe="")])
    if isinstance(value, str):
        for secret in sorted(set(secrets), key=len, reverse=True):
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return value
    if isinstance(value, list):
        return [redact(item, cookie) for item in value]
    if isinstance(value, dict):
        return {key: redact(item, cookie) for key, item in value.items()}
    return value


def unwrap(value, request_id=""):
    """Unwrap console envelopes and nested JSON strings while checking service errors."""
    for _ in range(8):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise MetricError("VVP returned non-JSON data; the response may be a login page or the API may have changed.", request_id=request_id)
        elif isinstance(value, dict):
            request_id = value.get("requestId") or request_id
            if value.get("authenticated") is False:
                raise MetricError("VVP authentication failed; provide a fresh Cookie.", "MetricAuthError", request_id)
            if value.get("success") is False or value.get("status") == "error":
                detail = value.get("errorMessage") or value.get("message") or value.get("error") or "Query failed"
                raise MetricError(str(detail), request_id=request_id)
            if "data" not in value:
                return value
            value = value["data"]
        else:
            return value
    raise MetricError("Unrecognized VVP response envelope.", request_id=request_id)


class ConsoleClient:
    def __init__(self, args, cookie):
        for name in ("region_id", "workspace", "namespace"):
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", getattr(args, name) or ""):
                raise MetricError(f"Invalid {name} format.", "ValidationError")
        self.origin = f"https://flink-{args.region_id}.data.aliyun.com"
        self.base = self.origin + f"/api/v2/namespaces/{args.namespace}"
        self.headers = {
            "Cookie": cookie, "workspace": args.workspace,
            "Accept": "application/json", "Content-Type": "application/json",
            "Origin": self.origin, "Referer": self.origin + f"/web/{args.workspace}/zh/",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.opener = build_opener(NoRedirect())

    def request(self, path, body=None):
        self.headers["User-Agent"] = build_user_agent()
        request = Request(self.base + path, headers=self.headers,
                          data=json.dumps(body).encode() if body is not None else None)
        try:
            with self.opener.open(request, timeout=30) as response:
                value = json.load(response)
        except HTTPError as exc:
            request_id = exc.headers.get("x-request-id", "")
            exc.close()
            if exc.code in (301, 302, 303, 307, 308, 401, 403):
                raise MetricError(f"HTTP {exc.code}: the login has expired or the account lacks access. Verify the account and provide a fresh Cookie.",
                                  "MetricAuthError", request_id)
            raise MetricError(f"HTTP {exc.code}: VVP query failed. Verify the region, resource, and API parameters.", request_id=request_id)
        except (TimeoutError, URLError):
            raise MetricError("The VVP connection failed or timed out. Check the network and region.")
        except (ValueError, UnicodeError):
            raise MetricError("VVP returned non-JSON data; the response may be a login page or the API may have changed.")
        request_id = value.get("requestId", "") if isinstance(value, dict) else ""
        return unwrap(value, request_id), request_id

    def job(self, deployment_id, job_id=None):
        path = "/jobs/" + quote(job_id or deployment_id, safe="") + ("" if job_id else "/latest")
        job, _ = self.request(path)
        if not isinstance(job, dict) or not job.get("jobId"):
            raise MetricError("Job not found. Verify the Deployment or provide the target Job UUID.")
        if job.get("deploymentId") != deployment_id or (job_id and job.get("jobId") != job_id):
            raise MetricError("The returned Job does not match the target Deployment or Job.")
        return {key: job.get(key) for key in
                ("jobId", "deploymentId", "deploymentName", "status", "startTime", "endTime")}


def dashboard_panels(value):
    """Inherit UIDs only from Dashboard nodes, never from datasource nodes."""
    panels = []

    def walk(node, dashboard_id=None):
        if isinstance(node, str):
            try:
                walk(json.loads(node), dashboard_id)
            except ValueError:
                pass
        elif isinstance(node, list):
            for item in node:
                walk(item, dashboard_id)
        elif isinstance(node, dict):
            if node.get("uid") and ("panels" in node or "rows" in node):
                dashboard_id = node["uid"]
            if dashboard_id and isinstance(node.get("targets"), list):
                panels.append({
                    "dashboard_id": dashboard_id, "panel_id": node.get("id"),
                    "title": node.get("title"), "description": node.get("description"),
                    "field_config": node.get("fieldConfig"), "axes": node.get("yaxes"),
                    "targets": [{key: target.get(key) for key in ("refId", "expr", "legendFormat", "hide")}
                                for target in node["targets"] if isinstance(target, dict) and target.get("refId")],
                })
            for item in node.values():
                walk(item, dashboard_id)

    walk(value)
    if not panels:
        raise MetricError("The dashboard returned no usable Dashboard, Panel, or Target. Inspect the API response.")
    return panels


def query_data(client, args):
    if args.start_time < 0 or args.end_time <= args.start_time or args.step <= 0:
        raise MetricError("Provide a valid Unix-second time range and a step greater than zero.", "ValidationError")
    if (args.end_time - args.start_time) // args.step > 11000:
        raise MetricError("The query requests too many data points. Increase the step or shorten the time range.", "ValidationError")
    job = client.job(args.deployment_id, args.job_id)
    body = {
        "startInSec": str(args.start_time), "endInSec": str(args.end_time), "stepInSec": args.step,
        "dashboardId": args.dashboard_id, "queryParams": {"panelId": args.panel_id, "refId": args.ref_id},
        "variables": {"deploymentId": args.deployment_id, "jobId": args.job_id},
    }
    data, request_id = client.request("/metric/data", body)
    if not isinstance(data, dict) or data.get("resultType") != "matrix" or not isinstance(data.get("result"), list):
        raise MetricError("The Metric response is not the expected time-series matrix.", request_id=request_id)
    series = []
    for item in data["result"]:
        if not isinstance(item, dict) or not isinstance(item.get("metric"), dict) or not isinstance(item.get("values"), list):
            raise MetricError("Unrecognized Metric time-series structure.", request_id=request_id)
        points = []
        for point in item["values"]:
            if not isinstance(point, list) or len(point) != 2:
                raise MetricError("Unrecognized Metric sample structure.", request_id=request_id)
            timestamp, value = point
            if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
                raise MetricError("Invalid Metric timestamp.", request_id=request_id)
            if args.start_time <= timestamp <= args.end_time:
                try:
                    number = float(value)
                except (ValueError, TypeError):
                    number = math.nan
                points.append([timestamp, value if math.isfinite(number) else None])
        series.append({"metric": item["metric"], "values": points,
                       "valid_points": sum(value is not None for _, value in points)})
    return {
        "job": job, "start_time": args.start_time, "end_time": args.end_time, "step": args.step,
        "dashboard_id": args.dashboard_id, "panel_id": args.panel_id, "ref_id": args.ref_id,
        "status": "data" if any(item["valid_points"] for item in series) else "no_data", "series": series,
    }, request_id


def cmd_metric(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    cookie = ""
    client = None
    try:
        build_user_agent()
        cookie = read_cookie(args)
        client = ConsoleClient(args, cookie)
        if args.subcommand == "get_metric_dashboard":
            job = client.job(args.deployment_id, args.job_id)
            dashboard, request_id = client.request("/metric/dashboard?language=zh-CN")
            data = {"job": job, "panels": dashboard_panels(dashboard)}
        else:
            data, request_id = query_data(client, args)
        result = success_response(args.subcommand, data, request_id)
    except SkillIdentityError as exc:
        result = error_response(args.subcommand, "SkillIdentityError", str(exc))
    except MetricError as exc:
        result = error_response(args.subcommand, exc.code, str(exc), exc.request_id)
    except Exception:
        # Do not expose exceptions, stack traces, or raw responses that may contain request headers.
        result = error_response(args.subcommand, "MetricQueryError", "The VVP query did not complete because of a response or connection error.")
    finally:
        if client:
            client.headers.clear()
    output(redact(result, cookie) if cookie else result, args.output)


def register(subparsers):
    for name, help_text in (("get_metric_dashboard", "Get Job and historical Metric dashboard definitions"),
                            ("get_metric_data", "Query historical VVP Metrics with a Cookie")):
        parser = subparsers.add_parser(name, help=help_text)
        add_common_args(parser)
        parser.add_argument("--deployment_id", required=True, help="Deployment ID")
        parser.add_argument("--job_id", required=name == "get_metric_data", help="Job UUID; dashboard queries use the latest streaming Job when omitted")
        parser.add_argument("--cookie_stdin", action="store_true", help="Read the Cookie from standard input; defaults to VVP_COOKIE")
        if name == "get_metric_data":
            parser.add_argument("--dashboard_id", required=True, help="Dashboard UID returned by the dashboard query")
            parser.add_argument("--panel_id", required=True, type=int, help="Panel ID returned by the dashboard query")
            parser.add_argument("--ref_id", required=True, help="Target refId returned by the dashboard query")
            parser.add_argument("--start_time", required=True, type=int, help="Start time in Unix seconds")
            parser.add_argument("--end_time", required=True, type=int, help="End time in Unix seconds")
            parser.add_argument("--step", type=int, default=5, help="Query step in seconds (default: 5)")
        parser.set_defaults(func=cmd_metric, subcommand=name)
