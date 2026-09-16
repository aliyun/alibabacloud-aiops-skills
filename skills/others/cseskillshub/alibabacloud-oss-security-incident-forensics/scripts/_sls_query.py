#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only executor for the customer's OWN OSS real-time log (SLS).

Boundary (identical to the rest of this skill):
  * The only project ever queried is `oss-log-<bucket-owner-uid>-<regionId>`,
    i.e. the log project that belongs to the account whose bucket is being
    audited. No cross-account project name is ever constructed.
  * Only two read APIs are used: `sls GetLogs` and `sls GetHistograms`.
    Nothing is written, no logstore is created, no configuration changes.
    CLI form (deliberate, do not "normalize" it): the two cmd lists below use
    the CLI's built-in operation form because it is the only form that honours
    the global `--user-agent` flag, which this skill MUST send so every call of
    a run carries its session-id User-Agent. Measured with aliyun CLI 3.4.5:
    the `aliyun sls get-logs` / `aliyun sls get-histograms` plugin form accepts
    but silently ignores unknown flags (a `--bogus-flag` probe is not
    rejected), so the UA header would be dropped without any error. Both forms
    issue the identical ROA request (verified with `--cli-dry-run`: same
    Method/URL/API Action), and the plugin-mode names are what SKILL.md and
    references/ document for manual use.
  * Credentials come exclusively from the aliyun CLI default credential
    chain (ALIBABA_CLOUD_PROFILE / environment / config file). AK/SK are
    never accepted as arguments and never printed.
  * Every call is bounded by a timeout and runs through subprocess with an
    argument list (never shell=True).

Failure contract -- this module NEVER raises and NEVER aborts the audit.
The real-time log is an optional evidence leg: it is free but must be
enabled by the customer, and on most accounts it is not. Each outcome is
therefore reported as data:

  outcome="ok"            rows returned, safe to interpret
  outcome="not_enabled"   ProjectNotExist / LogStoreNotExist /
                          IndexConfigNotExist -- a VALID FINDING ("the
                          real-time log is not enabled for this region"),
                          not an error
  outcome="no_data"       the query executed but matched nothing in the
                          window -- also a finding, not an error
  outcome="incomplete"    the histogram reports a non-Complete progress or
                          the window holds more than LOG_SCAN_CAP entries,
                          so the rows are a partial sample and must not be
                          read as a conclusion
  outcome="error"         permission / throttling / syntax / network /
                          server -- carries `category` and `message`

Measured response shapes (aliyun CLI 3.4.5, SLS `GET /logstores/[logstore]
?type=log`), all verified live against oss-log-<uid>-cn-hangzhou:
  success  -> exit 0, stdout is a JSON array of flat objects whose values
              are ALL STRINGS ({"client_ip":"1.2.3.4","cnt":"3"}), plus the
              injected __source__ / __time__ keys
  failure  -> exit 1, stdout empty, stderr is
              "ERROR: SDKError:\n   StatusCode: 404\n   Code: ProjectNotExist\n
               Message: ...\n   Data: {"httpCode":404,"requestId":"..."}"
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

from _oss_client import session_id, user_agent

_SLS_QUERY_TIMEOUT = 90    # seconds per GetLogs call
_VOLUME_TIMEOUT = 60       # seconds per GetHistograms call

# A single SLS analysis scans at most this many log entries before the
# result silently becomes a sample. Above it the window must be split.
LOG_SCAN_CAP = 300_000

# The OSS real-time log keeps a rolling 7 days; asking for more returns
# nothing extra, so the window is clamped instead of failing.
MAX_LOG_DAYS = 7

_NOT_ENABLED_CODES = frozenset({
    "ProjectNotExist",       # real-time log never enabled in this region
    "LogStoreNotExist",      # project exists, oss-log-store missing
    "IndexConfigNotExist",   # logstore exists, no index -> cannot query
})

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
_ERR_LINE_RE = re.compile(r"^\s*(StatusCode|Code|Message|Data)\s*:\s*(.*)$")
_REQUEST_ID_RE = re.compile(r'"requestId"\s*:\s*"([^"]+)"')
_DAYS_RE = re.compile(r"(\d+)\s*(?:day|days|d\b|天)", re.IGNORECASE)
_HOURS_RE = re.compile(r"(\d+)\s*(?:hour|hours|h\b|小时)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Pure helpers (each carries inline normal / boundary / invalid assertions)
# ---------------------------------------------------------------------------

def parse_cli_error(stderr: str) -> dict:
    """Parse an `aliyun` CLI SDKError block into structured fields.

    Returns {"status_code", "code", "message", "request_id"}; every field
    degrades to None / "" rather than raising, because a truncated or
    localized stderr must still produce a usable category.
    """
    text = _ANSI_ESCAPE_RE.sub("", stderr or "")
    status_code, code, message = None, "", ""
    for line in text.splitlines():
        m = _ERR_LINE_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key == "StatusCode":
            try:
                status_code = int(value)
            except ValueError:
                status_code = None
        elif key == "Code" and not code:
            code = value
        elif key == "Message" and not message:
            message = value
    rid = _REQUEST_ID_RE.search(text)
    return {
        "status_code": status_code,
        "code": code,
        "message": message,
        "request_id": rid.group(1) if rid else "",
    }


_E1 = parse_cli_error(
    "ERROR: SDKError:\n   StatusCode: 404\n   Code: ProjectNotExist\n"
    '   Message: The Project does not exist: oss-log-1-cn-hangzhou\n'
    '   Data: {"httpCode":404,"requestId":"6A97D2FE952C","statusCode":404}')
assert _E1["status_code"] == 404 and _E1["code"] == "ProjectNotExist"  # normal
assert _E1["request_id"] == "6A97D2FE952C"  # normal: request id extracted
assert _E1["message"].startswith("The Project does not exist")  # normal
assert parse_cli_error("") == {"status_code": None, "code": "", "message": "",
                               "request_id": ""}  # invalid: empty stderr
assert parse_cli_error("some random text")["code"] == ""  # invalid: unstructured
assert parse_cli_error("StatusCode: abc")["status_code"] is None  # invalid: non-numeric
assert parse_cli_error(None)["code"] == ""  # invalid: None


def classify_sls_failure(err: dict) -> str:
    """Map a parsed CLI error onto this skill's failure categories.

    `not_enabled` is deliberately separate from `error`: a missing log
    project is the expected state on most accounts and is itself the
    finding, so it must never be reported as a failure of the audit.
    """
    code = str((err or {}).get("code") or "")
    status = (err or {}).get("status_code")
    if code in _NOT_ENABLED_CODES:
        return "not_enabled"
    if status in (401, 403) or code in ("Unauthorized", "AccessDenied",
                                        "Forbidden", "PermissionDenied",
                                        "InvalidAccessKeyId",
                                        "SignatureDoesNotMatch"):
        return "permission"
    if status == 400 or "SyntaxError" in code or code in (
            "ParameterInvalid", "InvalidParameter", "InvalidQueryString"):
        return "invalid_query"
    if status == 429 or code in ("WriteQuotaExceed", "ReadQuotaExceed",
                                 "Throttling", "RequestTimeExpired"):
        return "throttling"
    if status is not None and 500 <= status < 600:
        return "server"
    if code in ("RequestError", "ServerBusy", "InternalError"):
        return "server"
    if status == 404:
        return "not_found"
    return "unknown"


assert classify_sls_failure({"code": "ProjectNotExist", "status_code": 404}) == "not_enabled"  # normal
assert classify_sls_failure({"code": "LogStoreNotExist", "status_code": 404}) == "not_enabled"  # normal
assert classify_sls_failure({"code": "AccessDenied", "status_code": 403}) == "permission"  # normal
assert classify_sls_failure({"code": "", "status_code": 401}) == "permission"  # boundary: status only
assert classify_sls_failure({"code": "ParameterInvalid", "status_code": 400}) == "invalid_query"  # normal
assert classify_sls_failure({"code": "SyntaxError.ErrorPosition", "status_code": 400}) == "invalid_query"  # boundary: substring match
assert classify_sls_failure({"code": "ReadQuotaExceed", "status_code": 429}) == "throttling"  # normal
assert classify_sls_failure({"code": "", "status_code": 503}) == "server"  # boundary: 5xx by status
assert classify_sls_failure({"code": "NoSuchThing", "status_code": 404}) == "not_found"  # boundary: other 404
assert classify_sls_failure({}) == "unknown"  # invalid: empty
assert classify_sls_failure(None) == "unknown"  # invalid: None


def resolve_window(time_window: str, now_ts: int,
                   log_days: int = 1) -> dict:
    """Turn the human-readable --time-window into a UNIX-second range.

    SLS GetLogs takes a left-closed right-open [from, to) interval in UNIX
    seconds. The real-time log only retains a rolling 7 days, so any larger
    request is clamped and the clamp is reported (never silently applied).
    """
    now = int(now_ts)
    text = str(time_window or "").strip()
    days = int(log_days) if log_days and int(log_days) > 0 else 1
    clamped = False
    # FO-6 fix: record WHICH input the window actually came from. The
    # priority is time-window text > --log-days, and an auto-fill message
    # that attributes a text-parsed 7-day window to "--log-days 1" misleads
    # the reader about which knob to turn.
    source = "--log-days fallback"
    m = _DAYS_RE.search(text)
    if m:
        days = int(m.group(1))
        source = "--time-window text"
    else:
        h = _HOURS_RE.search(text)
        if h:
            days = max(1, (int(h.group(1)) + 23) // 24)
            source = "--time-window text"
    # A non-positive window would make from == to, which SLS rejects outright.
    days = max(1, days)
    if days > MAX_LOG_DAYS:
        days = MAX_LOG_DAYS
        clamped = True
    return {
        "from": now - days * 86400,
        "to": now,
        "days": days,
        "clamped_to_retention": clamped,
        "window_source": source,
        "description": (f"last {days} day(s) ending now; the OSS real-time "
                        f"log keeps a rolling {MAX_LOG_DAYS} days, so this is "
                        f"the widest window available"
                        if clamped else f"last {days} day(s) ending now"),
    }


_NOW = 1_800_000_000
_W = resolve_window("last 7 days", _NOW, 1)
assert _W["days"] == 7 and _W["to"] - _W["from"] == 7 * 86400  # normal: parsed from text
assert _W["clamped_to_retention"] is False  # normal: 7 == retention
# FO-6 regression: the window source is recorded so the auto-fill message
# can attribute the 7 days to the time-window text, not to --log-days.
assert _W["window_source"] == "--time-window text"  # normal: text wins the priority
assert resolve_window("", _NOW, 3)["window_source"] == "--log-days fallback"  # boundary: no text
assert resolve_window("2026-08-20 to 2026-08-26", _NOW, 2)["window_source"] == "--log-days fallback"  # boundary: unparseable text
assert resolve_window("last 12 hours", _NOW, 1)["window_source"] == "--time-window text"  # boundary: hours text
assert resolve_window("last 30 days", _NOW, 1)["days"] == MAX_LOG_DAYS  # boundary: clamped
assert resolve_window("last 30 days", _NOW, 1)["clamped_to_retention"] is True
assert resolve_window("last 12 hours", _NOW, 1)["days"] == 1  # boundary: hours round up to a day
assert resolve_window("", _NOW, 3)["days"] == 3  # boundary: no text -> --log-days
assert resolve_window("2026-08-20 to 2026-08-26", _NOW, 2)["days"] == 2  # boundary: unparseable -> --log-days
assert resolve_window("last 0 days", _NOW, 0)["days"] == 1  # invalid: non-positive fallback
assert resolve_window(None, _NOW, None)["days"] == 1  # invalid: both missing
assert resolve_window("last 7 days", _NOW, 1)["from"] < _NOW  # invariant: from < to


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def _cli_available() -> bool:
    return shutil.which("aliyun") is not None


def _run(cmd: list, timeout: int) -> tuple:
    """Run an argument-list subprocess. Returns (returncode, stdout, stderr).

    stdin is DEVNULL so a credential prompt can never hang the audit, and
    the timeout is always set. Never shell=True.
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except OSError as exc:
        return 125, "", f"could not execute aliyun CLI: {exc}"
    return (result.returncode,
            (result.stdout or "").strip(),
            _ANSI_ESCAPE_RE.sub("", result.stderr or "").strip())


def get_log_volume(project: str, logstore: str, region: str, query: str,
                   from_ts: int, to_ts: int,
                   timeout: int = _VOLUME_TIMEOUT) -> dict:
    """Pre-count the window with GetHistograms before scanning it.

    Returns {"outcome", "total_count", "complete", "buckets", "error"}.
    `complete` is False when any histogram bucket reports a progress other
    than "Complete", which means SLS answered from a partial scan -- the
    same signal the SDK exposes as resp.is_completed().
    """
    if not project or not logstore:
        return {"outcome": "error", "category": "invalid_arguments",
                "total_count": None, "complete": False, "buckets": 0,
                "error": "project and logstore are both required"}
    if not _cli_available():
        return {"outcome": "error", "category": "cli_missing",
                "total_count": None, "complete": False, "buckets": 0,
                "error": "aliyun CLI not found on PATH"}
    cmd = ["aliyun", "sls", "GetHistograms",
           "--project", project, "--logstore", logstore,
           "--from", str(int(from_ts)), "--to", str(int(to_ts)),
           "--user-agent", user_agent()]
    if region:
        cmd += ["--region", region]
    if query:
        cmd += ["--query", query]
    rc, out, err = _run(cmd, timeout)
    if rc != 0:
        parsed = parse_cli_error(err)
        return {"outcome": "not_enabled" if classify_sls_failure(parsed)
                == "not_enabled" else "error",
                "category": classify_sls_failure(parsed),
                "total_count": None, "complete": False, "buckets": 0,
                "error": parsed["code"] or err[:200],
                "request_id": parsed["request_id"]}
    try:
        rows = json.loads(out) if out else []
    except json.JSONDecodeError:
        return {"outcome": "error", "category": "invalid_response",
                "total_count": None, "complete": False, "buckets": 0,
                "error": f"GetHistograms returned non-JSON output: {out[:120]}"}
    if not isinstance(rows, list):
        rows = []
    total = 0
    complete = True
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            total += int(row.get("count") or 0)
        except (TypeError, ValueError):
            pass
        if str(row.get("progress") or "").strip().lower() not in ("", "complete"):
            complete = False
    over_cap = total > LOG_SCAN_CAP
    return {
        "outcome": "incomplete" if (over_cap or not complete) else "ok",
        "total_count": total,
        "complete": complete and not over_cap,
        "over_scan_cap": over_cap,
        "scan_cap": LOG_SCAN_CAP,
        "buckets": len(rows),
        "error": "",
    }


def run_sls_query(project: str, logstore: str, region: str, query: str,
                  from_ts: int, to_ts: int, line: int = 100,
                  timeout: int = _SLS_QUERY_TIMEOUT) -> dict:
    """Execute one GetLogs statement. Returns the outcome dict, never raises.

    SLS returns every value as a string; numeric coercion is the caller's
    job (see _log_evidence) so this layer stays a faithful transport.
    """
    if not project or not logstore or not str(query or "").strip():
        return {"outcome": "error", "category": "invalid_arguments",
                "rows": [], "row_count": 0,
                "error": "project, logstore and query are all required",
                "request_id": ""}
    if not _cli_available():
        return {"outcome": "error", "category": "cli_missing", "rows": [],
                "row_count": 0, "error": "aliyun CLI not found on PATH",
                "request_id": ""}
    cmd = ["aliyun", "sls", "GetLogs",
           "--project", project, "--logstore", logstore,
           "--from", str(int(from_ts)), "--to", str(int(to_ts)),
           "--line", str(max(1, min(int(line or 100), 100))),
           "--query", query,
           "--user-agent", user_agent()]
    if region:
        cmd += ["--region", region]
    rc, out, err = _run(cmd, timeout)
    if rc == 124:
        return {"outcome": "error", "category": "timeout", "rows": [],
                "row_count": 0, "error": err, "request_id": ""}
    if rc != 0:
        parsed = parse_cli_error(err)
        category = classify_sls_failure(parsed)
        return {
            "outcome": "not_enabled" if category == "not_enabled" else "error",
            "category": category,
            "rows": [], "row_count": 0,
            "error": parsed["message"] or parsed["code"] or err[:300],
            "error_code": parsed["code"],
            "status_code": parsed["status_code"],
            "request_id": parsed["request_id"],
        }
    try:
        rows = json.loads(out) if out else []
    except json.JSONDecodeError:
        return {"outcome": "error", "category": "invalid_response",
                "rows": [], "row_count": 0,
                "error": f"GetLogs returned non-JSON output: {out[:200]}",
                "request_id": ""}
    if not isinstance(rows, list):
        rows = [rows] if isinstance(rows, dict) else []
    rows = [r for r in rows if isinstance(r, dict)]
    return {
        "outcome": "ok" if rows else "no_data",
        "category": "",
        "rows": rows,
        "row_count": len(rows),
        "error": "",
        "request_id": "",
    }


def execute_query_plan(queries: list, project: str, logstore: str,
                       region: str, window: dict, session_label: str = "",
                       max_steps: int = 0) -> dict:
    """Run the generated query sequence against the customer's own log.

    Strictly additive: this never raises and never decides the audit's
    STATUS. It pre-counts the window once (GetHistograms) and skips the
    scan when the volume exceeds LOG_SCAN_CAP, because a partial scan
    would otherwise be reported as a conclusion.

    `session_label` is only a traceability string echoed into the result.
    """
    result = {
        "executed": False,
        "session_id": session_label or session_id(),
        "project": project,
        "logstore": logstore,
        "region": region,
        "window": window,
        "volume": None,
        "results": [],
        "outcome": "skipped",
        "note": "",
    }
    if not project or not logstore:
        result["outcome"] = "not_enabled"
        result["note"] = ("the real-time-log project name could not be "
                          "derived (needs the bucket owner UID and the "
                          "bucket region), so no query was executed")
        return result
    if not _cli_available():
        result["outcome"] = "error"
        result["category"] = "cli_missing"
        result["note"] = "aliyun CLI not found on PATH"
        return result

    base_query = f"__topic__: oss_access_log"
    volume = get_log_volume(project, logstore, region, base_query,
                            window["from"], window["to"])
    result["volume"] = volume
    if volume["outcome"] == "not_enabled":
        result["outcome"] = "not_enabled"
        result["note"] = (
            "the OSS real-time log is NOT enabled for this region "
            f"({volume.get('error')}). Real-time log collection starts at "
            "enablement and is not retroactive, so the traffic that already "
            "happened cannot be recovered; enable it now (OSS console -> "
            "bucket -> Data Management -> Real-time Log Query) so the next "
            "anomaly is traceable.")
        return result
    if volume["outcome"] == "error":
        result["outcome"] = "error"
        result["category"] = volume.get("category", "unknown")
        result["note"] = f"volume pre-count failed: {volume.get('error')}"
        return result
    if volume.get("over_scan_cap"):
        result["outcome"] = "incomplete"
        result["note"] = (
            f"the window holds {volume['total_count']} log entries, above "
            f"the {LOG_SCAN_CAP} single-scan cap; results would be a partial "
            "sample. Narrow the window (or add a bucket/operation filter) "
            "and re-run before drawing a conclusion.")
        return result

    result["executed"] = True
    limit = int(max_steps) if max_steps and int(max_steps) > 0 else len(queries)
    for step in list(queries)[:limit]:
        if not isinstance(step, dict):
            continue
        query = str(step.get("query") or "")
        if not query:
            continue
        outcome = run_sls_query(project, logstore, region, query,
                                window["from"], window["to"])
        outcome["step"] = step.get("step", "")
        outcome["purpose"] = step.get("purpose", "")
        outcome["query"] = query
        result["results"].append(outcome)
        if outcome["outcome"] == "error" and \
                outcome.get("category") in ("permission", "cli_missing"):
            # Fail fast: every remaining statement would hit the same wall.
            result["outcome"] = "error"
            result["category"] = outcome["category"]
            result["note"] = (
                f"stopped after '{outcome['step']}': "
                f"{outcome.get('error')}")
            return result
    result["outcome"] = "ok"
    result["note"] = (
        f"{len(result['results'])} statement(s) executed over "
        f"{volume.get('total_count')} log entries")
    return result


_V = resolve_window("last 1 day", _NOW, 1)
# Every assertion below must stay offline: incomplete input short-circuits
# before any subprocess is spawned.
assert get_log_volume("", "", "", "", _V["from"], _V["to"])["category"] == "invalid_arguments"  # invalid: empty project
assert get_log_volume("p", "", "", "", _V["from"], _V["to"])["category"] == "invalid_arguments"  # invalid: empty logstore
assert run_sls_query("", "", "", "", _V["from"], _V["to"])["category"] == "invalid_arguments"  # invalid: empty project
assert run_sls_query("p", "l", "r", "", _V["from"], _V["to"])["rows"] == []  # invalid: empty query never spawns a call
assert execute_query_plan([], "", "", "", _V)["outcome"] == "not_enabled"  # invalid: no project -> not_enabled, never a crash
assert execute_query_plan([], "p", "", "", _V)["outcome"] == "not_enabled"  # invalid: no logstore
assert execute_query_plan([], "", "", "", _V)["executed"] is False  # invariant: nothing ran
assert isinstance(_V, dict) and _V["from"] < _V["to"]  # invariant: window is a valid interval


if __name__ == "__main__":
    print(json.dumps({"module": "_sls_query", "log_scan_cap": LOG_SCAN_CAP,
                      "max_log_days": MAX_LOG_DAYS}, indent=2))
    sys.exit(0)
