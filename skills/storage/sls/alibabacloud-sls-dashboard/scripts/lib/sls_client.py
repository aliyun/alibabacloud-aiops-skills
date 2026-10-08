"""Official aliyun SLS plugin adapter. No shell and no credential-file parsing."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import tempfile

from .common import SkillError, resolve_user_agent, source_check, write


class CliError(SkillError):
    pass


def body_of(payload):
    if isinstance(payload, dict) and "body" in payload:
        body = payload["body"]
        if isinstance(body, str):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        if isinstance(body, (dict, list)):
            return body
    return payload


def sql_string(value):
    return "'" + value.replace("'", "''") + "'"


def redact(text):
    text = re.sub(r"(?i)(authorization|access.?key(?:.?secret|.?id)?|security.?token|password)\s*[:=]\s*[^\s,}]+",
                  r"\1=[REDACTED]", text)
    return text[-1200:]


class SlsClient:
    def __init__(self, region, profile=None, executable="aliyun", timeout=60, runner=None, metric_api=None, job_api=None,
                 endpoint=None):
        if not isinstance(region, str) or not region.strip():
            raise SkillError("A region is required")
        if timeout <= 0:
            raise SkillError("Timeout must be positive")
        self.region, self.profile, self.executable = region, profile, executable
        self.timeout = timeout
        self.runner = runner or subprocess.run
        self.metric_api = metric_api
        self.job_api = job_api
        self.endpoint = endpoint
        self.user_agent = resolve_user_agent()

    def metric_transport(self):
        if self.metric_api is None:
            from .metric_api import MetricApi
            self.metric_api = MetricApi(self.profile, self.timeout, self.user_agent, endpoint=self.endpoint)
        return self.metric_api

    def job_transport(self):
        if self.job_api is None:
            from .job_api import JobApi
            self.job_api = JobApi(self.region, self.profile, self.timeout, self.user_agent, endpoint=self.endpoint)
        return self.job_api

    def list_report_jobs(self, project, dashboard_name, offset=0, size=10):
        if not isinstance(dashboard_name, str) or not dashboard_name.strip():
            raise SkillError("A dashboard name is required for Report listing")
        if type(offset) is not int or offset < 0 or type(size) is not int or not 1 <= size <= 100:
            raise SkillError("Invalid Report pagination")
        return self.job_transport().call("ListJobs", project, query={
            "jobType": "Report", "resourceProvider": dashboard_name,
            "offset": str(offset), "size": str(size)})

    def put_report_job(self, project, job, mode):
        if mode not in {"create", "update"} or not isinstance(job, dict) or job.get("type") != "Report":
            raise SkillError("Only Report create/update is supported")
        return self.job_transport().call("CreateJob" if mode == "create" else "UpdateJob", project,
                                         name=job["name"] if mode == "update" else None, body=job)

    def delete_report_job(self, project, name):
        return self.job_transport().call("DeleteJob", project, name=name)

    def metric_window(self, source, start, end, limit):
        source_check(source)
        if source["region"] != self.region:
            raise SkillError("Source and client region differ")
        if type(start) is not int or type(end) is not int or start >= end:
            raise SkillError("Query requires Unix seconds with from < to")
        if type(limit) is not int or not 1 <= limit <= 100000:
            raise SkillError("Invalid result limit")

    def call(self, action, params, body=None):
        command = [self.executable, "sls", action, "--region", self.region,
                   "--user-agent", self.user_agent]
        if self.profile:
            command += ["--profile", self.profile]
        if self.endpoint is not None:
            command += ["--endpoint", self.endpoint]
        for key, value in params.items():
            if value is not None:
                command += ["--" + key, str(value).lower() if isinstance(value, bool) else str(value)]
        with tempfile.TemporaryDirectory(prefix="sls-dashboard-request-") as directory:
            if body is not None:
                path = Path(directory) / "body.json"
                write(path, body)
                command += ["--body-file", str(path)]
            try:
                process = self.runner(command, text=True, capture_output=True, timeout=self.timeout, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise CliError(f"{action}: {type(exc).__name__}", "CLI_UNAVAILABLE" if isinstance(exc, OSError)
                               else "REQUEST_TIMEOUT") from exc
        try:
            payload = json.loads(process.stdout) if process.stdout.strip() else {}
        except json.JSONDecodeError as exc:
            if not process.returncode:
                raise CliError(f"{action}: CLI did not return JSON", "INVALID_RESPONSE") from exc
            payload = {}
        failed = (isinstance(payload, dict) and (
            payload.get("success") is False or payload.get("status") == "error" or payload.get("errorCode")
            or isinstance(payload.get("statusCode"), int) and payload["statusCode"] >= 400))
        if process.returncode or failed:
            error = payload if isinstance(payload, dict) else {}
            if not error and process.stderr.strip().startswith("{"):
                try:
                    error = json.loads(process.stderr)
                except json.JSONDecodeError:
                    pass
            code = str(error.get("errorCode") or error.get("code") or "CLI_ERROR")
            message = str(error.get("errorMessage") or error.get("message") or process.stderr or process.stdout or "request failed")
            if code == "CLI_ERROR":
                match = re.search(r"(?:ErrorCode|errorCode|Code)\s*[:=]\s*[\"']?([A-Za-z][A-Za-z0-9_.]+)", message)
                if match:
                    code = match.group(1)
            raise CliError(f"{action}: {redact(message)}", code)
        return body_of(payload)

    def list_resources(self, project, kind, offset=0, size=100):
        action = {"logstore": "list-log-stores", "metricstore": "list-metric-stores",
                  "storeview": "list-store-views", "dashboard": "list-dashboard"}.get(kind)
        if not action or not 1 <= size <= 500 or offset < 0:
            raise SkillError("Invalid resource kind, offset or size")
        return self.call(action, {"project": project, "offset": offset, "size": size})

    def describe(self, source):
        source_check(source)
        if source["region"] != self.region:
            raise SkillError("Source and client region differ")
        kind = source["type"]
        view = kind.endswith("_storeview")
        action = "get-store-view" if view else "get-log-store" if kind == "logstore" else "get-metric-store"
        return self.call(action, {"project": source["project"], "name" if view or kind != "logstore"
                                else "logstore": source["name"]})

    def index(self, source):
        source_check(source)
        if source["region"] != self.region:
            raise SkillError("Source and client region differ")
        if source["type"] not in {"logstore", "logstore_storeview"}:
            raise SkillError("Index discovery requires a log datasource")
        view = source["type"].endswith("_storeview")
        return self.call("get-store-view-index" if view else "get-index",
                         {"project": source["project"], "name" if view else "logstore": source["name"]})

    def query(self, source, query, start, end, language="sql", query_type="range", step="60s", limit=1000):
        source_check(source)
        if source["region"] != self.region:
            raise SkillError("Source and client region differ")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or start >= end:
            raise SkillError("Query requires Unix seconds with from < to")
        if not 1 <= limit <= 100000 or language not in {"sql", "spl", "promql", "search"}:
            raise SkillError("Invalid query language or result limit")
        if not isinstance(query, str) or not query.strip():
            raise SkillError("Query text is required")
        if re.search(r"\$\{", query):
            raise SkillError("Resolve dashboard tokens with explicit test values before execution")
        if source["type"] == "metricstore_storeview":
            if language != "promql":
                raise SkillError("Metric StoreViews support PromQL, not SQL/SPL", "UNSUPPORTED_QUERY_MODE")
            if query_type not in {"instant", "range"} or not re.fullmatch(r"[1-9][0-9]*(ms|s|m|h|d)", step):
                raise SkillError("Invalid PromQL mode or step")
            return self.metric_transport().query(source, query, start, end, query_type, step, limit)
        if language == "promql":
            if source["type"] not in {"metricstore", "metricsql"}:
                raise SkillError("PromQL requires a Metricstore")
            if query_type not in {"instant", "range"} or not re.fullmatch(r"[1-9][0-9]*(ms|s|m|h|d)", step):
                raise SkillError("Invalid PromQL mode or step")
            function = "promql_query" if query_type == "instant" else "promql_query_range"
            arguments = sql_string(query) + (", " + sql_string(step) if query_type == "range" else "")
            query = f"* | select {function}({arguments}) from metrics limit {limit}"
        # GetLogsV2 also accepts a named log StoreView in its logstore parameter.
        # Keep the view name and source identity; never expand it into member queries.
        effective_limit = min(limit, 100) if language == "search" else limit
        params = {"project": source["project"], "logstore": source["name"],
                  "from": start, "to": end, "query": query,
                  "line": effective_limit if language == "search" else 0,
                  "offset": 0, "session": "mode=scan" if language == "spl" else None}
        raw = self.call("get-logs-v2", params)
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            raise CliError("Query response requires a data array", "INVALID_RESPONSE")
        meta = raw.get("meta", {})
        progress = meta.get("progress") if isinstance(meta, dict) else None
        rows = raw["data"]
        if any(not isinstance(row, dict) for row in rows):
            raise CliError("Query data rows must be JSON objects", "INVALID_RESPONSE")
        return {"source": source, "query": query, "window": {"from": start, "to": end},
                "rows": rows[:limit], "complete": progress == "Complete",
                "progress": progress or "Unknown", "truncated": len(rows) > limit,
                "limitReached": len(rows) >= effective_limit,
                "requestedLimit": limit, "effectiveLimit": effective_limit, "meta": meta, "raw": raw}

    def metrics(self, source, start, end, limit=1000, keyword=""):
        self.metric_window(source, start, end, limit)
        if source["type"] == "metricstore_storeview":
            return self.metric_transport().metrics(source, start, end, limit, keyword)
        if source["type"] not in {"metricstore", "metricsql", "metricstore_storeview"}:
            raise SkillError("Metric discovery requires a metric datasource")
        result = self.query(source, f"* | select promql_label_values('__name__') from metrics limit {limit}",
                            start, end, limit=limit)
        names = set()
        for row in result["rows"]:
            for key in ("metric_name", "__name__", "promql_label_values('__name__')", "promql_label_values", "label", "name"):
                if isinstance(row.get(key), str):
                    names.add(row[key])
                    break
        result["metrics"] = sorted(name for name in names if keyword.lower() in name.lower())
        return result

    def labels(self, source, metric, start, end, limit=1000):
        self.metric_window(source, start, end, limit)
        if not re.fullmatch(r"[a-zA-Z_:][a-zA-Z0-9_:]*", metric):
            raise SkillError("Supply one exact metric name for label sampling")
        if source["type"] == "metricstore_storeview":
            return self.metric_transport().labels(source, metric, start, end, limit)
        result = self.query(source, metric, start, end, language="promql", query_type="instant", limit=limit)
        labels = {}
        for row in result["rows"]:
            values = row.get("labels", {})
            if isinstance(values, str):
                try:
                    values = json.loads(values)
                except json.JSONDecodeError:
                    values = {}
            if isinstance(values, dict):
                for key, value in values.items():
                    labels.setdefault(key, set()).add(str(value))
        result["metric"] = metric
        result["labels"] = {key: {"sampleValues": sorted(values), "sampleCardinality": len(values)}
                            for key, values in sorted(labels.items())}
        return result

    def get_dashboard(self, project, name):
        payload = self.call("get-dashboard", {"project": project, "dashboard-name": name})
        if not isinstance(payload, dict) or not isinstance(payload.get("charts"), list):
            raise CliError("Dashboard response requires charts[]", "INVALID_RESPONSE")
        return payload

    def put_dashboard(self, project, payload, mode):
        if mode not in {"create", "update"}:
            raise SkillError("Invalid publish mode")
        # Required CLI flags are provided; --body-file supplies the complete nested JSON.
        return self.call(mode + "-dashboard",
                         {"project": project, "dashboard-name": payload["dashboardName"],
                          "display-name": payload["displayName"], "charts": "[]"}, body=payload)

    def delete_dashboard(self, project, name):
        return self.call("delete-dashboard", {"project": project, "dashboard-name": name})
