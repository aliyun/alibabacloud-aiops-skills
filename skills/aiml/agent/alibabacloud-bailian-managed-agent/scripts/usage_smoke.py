#!/usr/bin/env python3
"""Read-only Usage API contract probes using existing resources (stdlib only).

Preview by default; --execute sends queries, never creates resources or runs agents.
Reports omit credentials, resource bodies, model/tool names and opaque cursors.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import secrets
import urllib.error
import urllib.parse
import urllib.request

from user_agent import create_user_agent

TZ = timezone(timedelta(hours=8))
TOKEN_FIELDS = "input_tokens output_tokens total_tokens cache_read_tokens cache_creation_tokens".split()
COUNT_FIELDS = "model_call_count tool_call_count builtin_tool_call_count mcp_tool_call_count custom_tool_call_count turns steps interrupt_error_count model_failed_count tool_failed_count".split()
TOTAL_UNITS = {**dict.fromkeys(TOKEN_FIELDS, "tokens"), **dict.fromkeys(COUNT_FIELDS, "count"), "cache_hit_ratio": "ratio", "runtime_ms": "ms"}
MODEL_UNITS = {**dict.fromkeys(TOKEN_FIELDS, "tokens"), "cache_hit_ratio": "ratio", "call_count": "count", "failed_count": "count"}
TOOL_UNITS = {"call_count": "count", "failed_count": "count"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_metrics(metrics, units):
    for name, unit in units.items():
        item = metrics[name]
        require(item["unit"] == unit, f"{name}: wrong unit")
        value = item["value"]
        if value is not None:
            types = (int, float) if unit == "ratio" else (int,)
            require(type(value) in types and math.isfinite(value) and value >= 0, f"{name}: invalid value")
    if "total_tokens" in units:
        values = {k: v["value"] for k, v in metrics.items()}
        inp, out = values["input_tokens"], values["output_tokens"]
        expected = None if inp is None or out is None else inp + out
        require(values["total_tokens"] == expected, "total_tokens double-counted or lost unknown value")
        read = values["cache_read_tokens"]
        ratio = values["cache_hit_ratio"]
        if inp in (None, 0) or read is None:
            require(ratio is None, "undefined cache ratio must be null")
        else:
            require(ratio is not None and math.isclose(ratio, read / inp, abs_tol=5.1e-9, rel_tol=0), "cache ratio mismatch")


def validate_usage(usage):
    validate_metrics(usage["total"], TOTAL_UNITS)
    require(isinstance(usage["models"], list) and isinstance(usage["tools"], list), "details must be arrays")
    for row in usage["models"]:
        require(row["model_name"] is None or isinstance(row["model_name"], str), "invalid model name")
        validate_metrics(row["usage"], MODEL_UNITS)
    for row in usage["tools"]:
        require(row["source"] in (None, "builtin", "mcp", "custom"), "invalid tool source")
        require(row["tool_name"] is None or isinstance(row["tool_name"], str), "invalid tool name")
        validate_metrics(row["usage"], TOOL_UNITS)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a bearer credential to a redirected host.


class Probe:
    def __init__(self, base, key, ua, output):
        self.base = base
        self.headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": ua}
        self.opener = urllib.request.build_opener(NoRedirect)
        self.output = output
        self.report = {"tested_at": datetime.now(TZ).isoformat(timespec="seconds"), "endpoint_host": urllib.parse.urlsplit(base).hostname, "user_agent": ua, "requests": [], "checks": []}

    def save(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(self.report, indent=2) + "\n")

    def check(self, name, fn):
        try:
            details = fn()
            row = {"name": name, "status": "passed"}
            if details is not None:
                row["details"] = details
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            row = {"name": name, "status": "failed", "reason": str(exc)}
        self.report["checks"].append(row)
        self.save()
        print(json.dumps(row), flush=True)

    def call(self, label, kind, body, expected=200, error_code=None):
        request = urllib.request.Request(self.base + "/usage/" + kind, data=json.dumps(body).encode(), headers=self.headers, method="POST")
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.status
            result = json.load(response)
            code = result.get("error", result).get("code")
            self.report["requests"].append({"label": label, "endpoint": kind, "status": status, "code": code, "request_id": result.get("request_id") or response.headers.get("x-request-id")})
            self.save()
        if status in (401, 403, 429) or status >= 500:
            raise RuntimeError(f"Stop probes after HTTP {status}; see saved request_id. Resolve auth/throttling/service readiness before retrying.")
        require(status == expected, f"expected HTTP {expected}, got {status} ({code})")
        if error_code:
            require(code == error_code, f"expected {error_code}, got {code}")
        if status != 200:
            return None
        require(bool(result.get("request_id")), "missing request_id")
        data = result["data"]
        updated = data["data_updated_at"]
        require(updated is None or updated.endswith("+08:00"), "wrong update timezone")
        if kind == "summary":
            validate_usage(data["usage"])
            require(("query_range" in data) == (body["dimension"] != "session"), "wrong query_range presence")
        else:
            require(data["granularity"] in ("hour", "day", "month"), "invalid response granularity")
            require(type(data["has_more"]) is bool, "has_more must be boolean")
            token = data["next_page_token"]
            require(isinstance(token, str) and bool(token.strip()) if data["has_more"] else token is None, "invalid cursor termination")
            starts = []
            for point in data["points"]:
                validate_usage(point["usage"])
                require(point["start_time"].endswith("+08:00") and point["end_time"].endswith("+08:00"), "wrong point timezone")
                require(data["query_range"]["start_time"] <= point["start_time"] < point["end_time"] <= data["query_range"]["end_time"], "point outside range")
                starts.append(point["start_time"])
            require(starts == sorted(set(starts)), "points unordered or duplicated")
            require(len(starts) <= body.get("page_size", 100), "page_size exceeded")
        if "query_range" in data:
            require(all(v.endswith("+08:00") for v in data["query_range"].values()), "wrong range timezone")
        return data


def total_values(data):
    return {k: v["value"] for k, v in data["usage"]["total"].items()}


def run(probe, args):
    base = {"dimension": "workspace", "time_range": {"start_time": args.start_time, "end_time": args.end_time}, "granularity": "day"}
    summary = {}

    def workspace():
        summary.update(probe.call("workspace", "summary", base))
        return {"query_range": summary["query_range"], "data_updated_at": summary["data_updated_at"], "total": total_values(summary), "model_groups": len(summary["usage"]["models"]), "tool_groups": len(summary["usage"]["tools"])}
    probe.check("workspace_summary", workspace)

    def pagination():
        query = {**base, "page_size": 1}
        points, ranges, seen = [], [], set()
        first = probe.call("trend_first", "trend", query)
        current = first
        page_count = 0
        while True:
            page_count += 1
            points.extend(current["points"])
            ranges.append(current["query_range"])
            if not current["has_more"]:
                break
            if page_count >= args.max_pages:
                raise AssertionError("page budget reached: partial results must not be called complete")
            token = current["next_page_token"]
            require(token not in seen, "repeated cursor")
            seen.add(token)
            current = probe.call("trend_next", "trend", {**query, "page_token": token})
        require(all(r == first["query_range"] for r in ranges), "query_range changed between pages")
        starts = [p["start_time"] for p in points]
        require(starts == sorted(set(starts)), "cross-page duplicate or order violation")
        if first["has_more"]:
            continuation = {**query, "page_token": first["next_page_token"]}
            probe.call("cursor_retry", "trend", continuation)
            utc = {k: datetime.fromisoformat(v).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z") for k, v in base["time_range"].items()}
            probe.call("cursor_equivalent_timezone", "trend", {**continuation, "time_range": utc})
            probe.call("cursor_changed_page_size", "trend", {**continuation, "page_size": 2}, 400, "invalid_page_token")
            changed_range = {**base["time_range"], "start_time": (datetime.fromisoformat(args.start_time) + timedelta(seconds=1)).isoformat(timespec="seconds")}
            probe.call("cursor_changed_raw_boundary", "trend", {**continuation, "time_range": changed_range}, 400, "invalid_page_token")
        if summary and points:
            require(first["query_range"] == summary["query_range"], "summary/trend range mismatch")
            sums = {k: sum(p["usage"]["total"][k]["value"] for p in points) for k in TOTAL_UNITS if k != "cache_hit_ratio" and all(p["usage"]["total"][k]["value"] is not None for p in points)}
            mismatch = [k for k, value in sums.items() if value != summary["usage"]["total"][k]["value"]]
            require(not mismatch, "summary/trend mismatch (may require a settled-window rerun): " + ", ".join(mismatch))
        return {"pages": page_count, "points": len(points), "cursor_checks": "passed" if first["has_more"] else "not exercised: only one page", "additive_reconciliation": "passed" if summary and points else "not exercised: no data"}
    probe.check("workspace_trend_pagination_and_reconciliation", pagination)

    def alignment(grain, start, end, expected_start, expected_end):
        body = {"dimension": "workspace", "time_range": {"start_time": start, "end_time": end}, "granularity": grain}
        expected = {"start_time": expected_start, "end_time": expected_end}
        for kind in ("summary", "trend"):
            data = probe.call("alignment_" + grain, kind, body)
            require(data["query_range"] == expected, f"{grain} alignment mismatch")
    day = datetime.fromisoformat(args.start_time).astimezone(TZ).date().isoformat()
    probe.check("second_precision_hour_alignment", lambda: alignment("hour", day + "T10:15:30+08:00", day + "T14:00:01+08:00", day + "T10:00:00+08:00", day + "T15:00:00+08:00"))
    probe.check("exact_hour_boundary", lambda: alignment("hour", day + "T10:00:00+08:00", day + "T14:00:00+08:00", day + "T10:00:00+08:00", day + "T14:00:00+08:00"))
    next_day = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    probe.check("natural_day_alignment", lambda: alignment("day", day + "T10:15:30+08:00", day + "T14:00:01+08:00", day + "T00:00:00+08:00", next_day + "T00:00:00+08:00"))
    probe.check("natural_month_alignment", lambda: alignment("month", "2026-09-15T10:15:30+08:00", "2026-10-02T00:00:01+08:00", "2026-09-01T00:00:00+08:00", "2026-11-01T00:00:00+08:00"))

    for end, grain in (("2026-08-04T00:00:00+08:00", "hour"), ("2026-08-04T00:00:01+08:00", "day"), ("2026-11-01T00:00:00+08:00", "day"), ("2026-11-01T00:00:01+08:00", "month")):
        def auto(end=end, grain=grain):
            data = probe.call("auto_" + grain, "trend", {"dimension": "workspace", "time_range": {"start_time": "2026-08-01T00:00:00+08:00", "end_time": end}, "page_size": 1})
            require(data["granularity"] == grain, "auto granularity boundary mismatch")
        probe.check("auto_granularity_" + end, auto)

    if args.agent_id:
        agent = {**base, "dimension": "agent", "agent_id": args.agent_id}
        for kind in ("summary", "trend"):
            probe.check("agent_" + kind, lambda kind=kind: probe.call("agent", kind, agent) and None)
        if args.agent_version:
            probe.check("agent_version", lambda: probe.call("agent_version", "summary", {**agent, "agent_version": args.agent_version}) and None)
            probe.check("agent_version_trend", lambda: probe.call("agent_version", "trend", {**agent, "agent_version": args.agent_version}) and None)
            def exact_version():
                data = probe.call("untrimmed_version", "summary", {**agent, "agent_version": " " + args.agent_version + " "})
                require(all(v is None for v in total_values(data).values()), "version unexpectedly trimmed or matched")
            probe.check("version_preserves_whitespace", exact_version)
        def null_version():
            a = probe.call("version_omitted", "summary", agent)
            b = probe.call("version_null", "summary", {**agent, "agent_version": None})
            require(a["usage"] == b["usage"], "null version differs from all-version aggregate")
        probe.check("null_version_merges_versions", null_version)
        def empty():
            query = {**agent, "agent_version": "probe-no-such-version-" + secrets.token_hex(8)}
            data = probe.call("no_matching_version", "summary", query)
            require(all(v is None for v in total_values(data).values()), "empty values must be null")
            require(data["usage"]["models"] == [] and data["usage"]["tools"] == [] and data["data_updated_at"] is None, "invalid empty summary")
            trend = probe.call("no_matching_version", "trend", query)
            require(trend["points"] == [] and not trend["has_more"] and trend["next_page_token"] is None and trend["data_updated_at"] is None, "invalid empty trend")
        probe.check("empty_summary_and_trend", empty)
    else:
        probe.report["checks"].append({"name": "agent_checks", "status": "skipped", "reason": "Supply --agent-id and optionally --agent-version"})

    if args.session_id:
        def session():
            return total_values(probe.call("session", "summary", {"dimension": "session", "session_id": args.session_id}))
        probe.check("session_lifetime_summary", session)
    else:
        probe.report["checks"].append({"name": "session_lifetime_summary", "status": "skipped", "reason": "Supply --session-id"})
    if args.empty_session_id:
        def empty_session():
            data = probe.call("empty_session", "summary", {"dimension": "session", "session_id": args.empty_session_id})
            require(all(v is None for v in total_values(data).values()), "existing empty Session must have unknown metrics")
            require(data["usage"]["models"] == [] and data["usage"]["tools"] == [] and data["data_updated_at"] is None, "invalid empty Session details")
        probe.check("existing_session_without_records", empty_session)
    else:
        probe.report["checks"].append({"name": "existing_session_without_records", "status": "skipped", "reason": "Supply --empty-session-id"})

    invalid = [
        ("dimension_case", "summary", {**base, "dimension": "Workspace"}),
        ("trend_session", "trend", {"dimension": "session", "session_id": args.session_id or "sesn_test"}),
        ("agent_missing_id", "summary", {**base, "dimension": "agent"}),
        ("agent_blank_id", "summary", {**base, "dimension": "agent", "agent_id": " "}),
        ("workspace_agent_filter", "summary", {**base, "agent_id": args.agent_id or "agent_test"}),
        ("session_time_range", "summary", {**base, "dimension": "session", "session_id": args.session_id or "sesn_test"}),
        ("session_blank_id", "summary", {"dimension": "session", "session_id": " "}),
        ("version_blank", "summary", {**base, "dimension": "agent", "agent_id": args.agent_id or "agent_test", "agent_version": " "}),
        ("range_null", "summary", {**base, "time_range": None}),
        ("granularity_null", "summary", {**base, "granularity": None}),
        ("minute_unsupported", "summary", {**base, "granularity": "minute"}),
        ("fractional_seconds", "summary", {**base, "time_range": {**base["time_range"], "start_time": day + "T00:00:00.123+08:00"}}),
        ("missing_timezone", "summary", {**base, "time_range": {**base["time_range"], "start_time": day + "T00:00:00"}}),
        ("reversed_range", "summary", {**base, "time_range": {"start_time": args.end_time, "end_time": args.start_time}}),
        *[("page_size_" + str(size), "trend", {**base, "page_size": size}) for size in (0, 101, None)],
        ("page_token_null", "trend", {**base, "page_token": None}),
    ]
    for label, kind, body in invalid:
        probe.check(label, lambda label=label, kind=kind, body=body: probe.call(label, kind, body, 400, "invalid_parameter"))
    for label, token in (("empty_cursor", ""), ("blank_cursor", " "), ("malformed_cursor", "not-a-cursor")):
        probe.check(label, lambda label=label, token=token: probe.call(label, "trend", {**base, "page_token": token}, 400, "invalid_page_token"))
    probe.check("unknown_session", lambda: probe.call("unknown_session", "summary", {"dimension": "session", "session_id": "sesn_01" + secrets.token_hex(12).upper()}, 404, "not_found"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--bl-config", type=Path, help="Use this JSON profile's api_key/base_url as a pair")
    parser.add_argument("--start-time", required=True, help="Historical range with settled records, RFC 3339 seconds")
    parser.add_argument("--end-time", required=True)
    parser.add_argument("--agent-id")
    parser.add_argument("--agent-version")
    parser.add_argument("--session-id")
    parser.add_argument("--empty-session-id", help="Existing Session known to have no recorded activity")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("/tmp/ma-usage-" + secrets.token_hex(5) + ".json"))
    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error("--max-pages must be positive")
    if not args.execute:
        print(json.dumps({"mode": "preview", "scope": "POST /usage/summary and /usage/trend only; existing resources; no model calls", "range": [args.start_time, args.end_time], "output": str(args.output)}))
        return 0
    if args.bl_config:
        config = json.loads(args.bl_config.expanduser().read_text())
        endpoint, key = config["base_url"], config["api_key"]
    else:
        endpoint, key = os.environ["AGENTSTUDIO_URL"], os.environ["DASHSCOPE_API_KEY"]
    base = endpoint.rstrip("/")
    if not base.endswith("/api/v1/agentstudio"):
        base += "/api/v1/agentstudio"
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".maas.aliyuncs.com") or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/api/v1/agentstudio":
        raise ValueError("Expected an authorized HTTPS workspace-scoped Alibaba Cloud endpoint")
    ua = os.environ.get("BAILIAN_MANAGED_AGENT_SKILL_UA") or create_user_agent()
    probe = Probe(base, key, ua, args.output.expanduser().resolve())
    # Do not overwrite previous evidence, and keep operational metadata private.
    probe.output.parent.mkdir(parents=True, exist_ok=True)
    with probe.output.open("x"):
        pass
    probe.output.chmod(0o600)
    try:
        run(probe, args)
    except (RuntimeError, urllib.error.URLError, TimeoutError) as exc:
        probe.report["aborted"] = str(exc)
    probe.report["counts"] = {status: sum(c["status"] == status for c in probe.report["checks"]) for status in ("passed", "failed", "skipped")}
    probe.save()
    print(json.dumps({"output": str(probe.output), "counts": probe.report["counts"], "aborted": probe.report.get("aborted")}))
    return int(bool(probe.report.get("aborted") or probe.report["counts"]["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
