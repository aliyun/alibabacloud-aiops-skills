#!/usr/bin/env python3
"""
trace_request.py -- Single-request tracing in the OSS realtime access log
=========================================================================
SECURITY: READ-ONLY. This script only reads the customer's own realtime access
log. It never reads, prints or stores credentials, and it never changes any
configuration or object. Authentication is resolved exclusively by the aliyun
CLI default credential chain. Run it only after the user confirmed the scope.

Three tracing modes
-------------------
  1. --request-id  : pull the exact logged row of one request. Most precise;
                     use it whenever the customer can supply a request ID.
  2. --object      : pull the history of one object key (all operations,
                     chronological). Used for "who removed this file" and for
                     confirming whether an object ever existed.
  3. error summary : aggregate the EC / error-code distribution over the window
                     (default mode when neither --request-id nor --object is
                     given). Used to find which failure dominates.

SLS query constraints honored here (violating them returns an error or zero
rows rather than a wrong answer):
  * every query pins __topic__ to the access-detail topic, because the same
    logstore also carries hourly metering rows;
  * the filter part before '|' may only use indexed fields; non-indexed fields
    such as object / referer / user_agent are filtered in the SQL part;
  * the search syntax has no parenthesised OR for a field, so multi-value
    filters are expressed as SQL "WHERE x IN (...)";
  * object and request_uri are URL encoded, so matching uses url_decode().

Degradation contract: a failed query is recorded as [WARN] on stderr and in the
Graceful Degradation Log; the script still exits 0 with a stable JSON shape.

Usage:
  python3 trace_request.py --bucket my-bucket --region cn-hangzhou \
      --request-id 65A1B2C3D4E5F6G7H8I9J0K1
  python3 trace_request.py --bucket my-bucket --object images/a.png --hours 72
  python3 trace_request.py --bucket my-bucket --hours 6 --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

import _cli
from _constants import (
    ACCESS_LOG_FIELDS,
    LOG_LOGSTORE,
    LOG_PROJECT_TEMPLATE,
    MAX_LOG_LINES,
    MAX_WINDOW_SECONDS,
    DEFAULT_WINDOW_SECONDS,
    TOPIC_ACCESS_LOG,
    TOPIC_BATCH_DELETE_LOG,
    UPLOAD_DATA_OPERATIONS,
)

MODE_REQUEST_ID = "request_id"
MODE_OBJECT = "object_history"
MODE_BATCH_DELETE = "batch_delete"
MODE_ERROR_SUMMARY = "error_summary"
MODE_GENERATE_ONLY = "generate_statements"

# Fields selected when pulling a full request row. Ordered so the report reads
# as identity -> request -> response -> timing.
TRACE_FIELDS = (
    "time", "request_id", "bucket", "object", "operation", "http_method",
    "http_status", "error_code", "ec", "sign_type", "access_id",
    "requester_id", "owner_id", "extend_information", "client_ip", "host",
    "vpc_id", "referer", "user_agent", "object_size", "content_length_in",
    "response_body_length", "response_time", "server_cost_time",
    "sync_request", "bucket_storage_type", "request_uri",
)

MODE_REQUEST_ID = "request_id"
MODE_OBJECT = "object_history"
MODE_ERROR_SUMMARY = "error_summary"


def _warn(message: str) -> None:
    print(f"[WARN] {message}", file=sys.stderr)


def _select_list(fields=TRACE_FIELDS) -> str:
    return ", ".join(fields)


def build_base_filter(bucket: str) -> str:
    """Indexed-field filter placed before the '|' pipe."""
    return f"__topic__: {TOPIC_ACCESS_LOG} AND bucket: {bucket}"


def query_by_request_id(project: str, region: str, bucket: str,
                        request_id: str, from_ts: int, to_ts: int,
                        profile: str | None) -> dict:
    """Pull the logged row of one request ID."""
    # request_id is indexed, so it belongs in the filter part.
    query = f"{build_base_filter(bucket)} AND request_id: {request_id}"
    return _run_query(project, region, query, from_ts, to_ts,
                      line=10, profile=profile, label="request-id lookup")


def query_object_history(project: str, region: str, bucket: str,
                         object_key: str, from_ts: int, to_ts: int,
                         profile: str | None) -> dict:
    """Pull every logged operation on one object key, chronological.

    The object field is URL encoded and usually not indexed, so the key is
    matched in the SQL part with url_decode() rather than in the filter part.
    """
    escaped = object_key.replace("'", "''")
    query = (
        f"{build_base_filter(bucket)} | "
        f"SELECT {_select_list()} FROM log "
        f"WHERE url_decode(object) = '{escaped}' "
        f"ORDER BY __time__ ASC LIMIT {MAX_LOG_LINES}"
    )
    return _run_query(project, region, query, from_ts, to_ts,
                      line=MAX_LOG_LINES, profile=profile,
                      label="object history")


def query_error_summary(project: str, region: str, bucket: str,
                        from_ts: int, to_ts: int,
                        profile: str | None) -> dict:
    """Aggregate the failure distribution over the window.

    ec / error_code / http_status / operation are indexed, so this aggregation
    needs no scan mode and covers the whole window.
    """
    query = (
        f"{build_base_filter(bucket)} | "
        f"SELECT ec, error_code, http_status, operation, sign_type, "
        f"count(*) AS cnt FROM log "
        f"WHERE http_status >= 400 "
        f"GROUP BY ec, error_code, http_status, operation, sign_type "
        f"ORDER BY cnt DESC LIMIT 50"
    )
    return _run_query(project, region, query, from_ts, to_ts,
                      line=50, profile=profile, label="error summary")


def query_concurrent_writes(project: str, region: str, bucket: str,
                            object_key: str, from_ts: int, to_ts: int,
                            profile: str | None) -> dict:
    """List write operations on the same object inside the window.

    Used when the traced failure is a concurrency conflict (StaleFile): it
    shows which operations competed for the same object version.
    """
    ops = ", ".join(f"'{o}'" for o in UPLOAD_DATA_OPERATIONS)
    escaped = object_key.replace("'", "''")
    query = (
        f"{build_base_filter(bucket)} | "
        f"SELECT time, request_id, operation, http_status, ec, sign_type, "
        f"sync_request, client_ip, access_id FROM log "
        f"WHERE url_decode(object) = '{escaped}' AND operation IN ({ops}) "
        f"ORDER BY __time__ ASC LIMIT {MAX_LOG_LINES}"
    )
    return _run_query(project, region, query, from_ts, to_ts,
                      line=MAX_LOG_LINES, profile=profile,
                      label="concurrent write scan")


def query_batch_delete_history(project: str, region: str, bucket: str,
                               object_key: str, request_id: str,
                               from_ts: int, to_ts: int,
                               profile: str | None) -> dict:
    """Read the batch-delete topic for one object key or one request ID.

    A batch delete call logs only ONE row in the access topic; the individual
    removed keys live under the batch-delete topic and join back through
    request_id. Without querying that topic a batch deletion looks like "no
    removal was logged", which is a wrong conclusion.
    """
    if request_id:
        sql = (f"SELECT from_unixtime(__time__) AS time, "
               f"url_decode(object) AS objectname, user_agent, client_ip, "
               f"requester_id, http_status FROM log "
               f"WHERE request_id = '{request_id.replace(chr(39), '')}' "
               f"LIMIT {MAX_LOG_LINES}")
    else:
        escaped = object_key.replace("'", "''")
        sql = (f"SELECT from_unixtime(__time__) AS time, request_id, "
               f"url_decode(object) AS objectname, user_agent, client_ip, "
               f"requester_id, http_status FROM log "
               f"WHERE url_decode(object) = '{escaped}' "
               f"ORDER BY __time__ DESC LIMIT {MAX_LOG_LINES}")
    query = (f"__topic__: {TOPIC_BATCH_DELETE_LOG} AND bucket: {bucket} | {sql}")
    return _run_query(project, region, query, from_ts, to_ts,
                      line=MAX_LOG_LINES, profile=profile,
                      label="batch-delete topic")


def generate_query_statements(bucket: str, region: str, project: str,
                              ip: str = "", object_key: str = "",
                              status: str = "", operation: str = "",
                              access_key: str = "", request_id: str = "",
                              hours: int = 24,
                              exclude_cdn: bool = False) -> list[dict]:
    """Build SLS statements for the customer to run in the console.

    This is the degraded output path: when the log-read channel is unavailable,
    when the caller lacks the log read permission, or when realtime logging is
    not enabled, the skill must still hand over something actionable instead of
    reporting nothing. Statements are generated, never executed here.

    Each entry carries the statement plus the topic it must be run against, so
    a batch-delete question is not answered from the access topic.
    """
    base = f'bucket: "{bucket}"'
    cdn_guard = " AND NOT sync_request: cdn" if exclude_cdn else ""
    access = f"__topic__: {TOPIC_ACCESS_LOG} AND {base}{cdn_guard}"
    out: list[dict] = []

    def add(qid, title, purpose, statement, topic=TOPIC_ACCESS_LOG):
        out.append({"id": qid, "title": title, "purpose": purpose,
                    "statement": statement, "topic": topic})

    if request_id:
        add("T0", "Trace one request ID",
            "Pull the single logged row of this request - the most precise "
            "entry point.",
            f"{access} AND request_id: {request_id}")
    if ip:
        ip_filter = f" AND client_ip: {ip}"
        add("T1a", "What is this client IP doing",
            "Operation and status mix of one client IP.",
            f"{access}{ip_filter} | SELECT operation, http_status, error_code, "
            f"ec, count(*) AS cnt, SUM(content_length_out) AS bytes_out "
            f"FROM log GROUP BY operation, http_status, error_code, ec "
            f"ORDER BY cnt DESC LIMIT 50")
        add("T1b", "Top objects touched by this IP",
            "Which keys this IP is reading; object is URL encoded so decode it.",
            f"{access}{ip_filter} | SELECT url_decode(object) AS object_name, "
            f"count(*) AS cnt, SUM(content_length_out) AS bytes_out FROM log "
            f"GROUP BY object_name ORDER BY cnt DESC LIMIT 20")
    if object_key:
        escaped = object_key.replace("'", "''")
        add("T2", "Who accessed this object",
            "Every logged operation on one object key, chronological.",
            f"{access} | SELECT time, request_id, operation, http_status, "
            f"error_code, ec, client_ip, requester_id, access_id, sign_type "
            f"FROM log WHERE url_decode(object) = '{escaped}' "
            f"ORDER BY __time__ ASC LIMIT 100")
        add("T6b", "Batch-delete forensics for this object",
            "A batch delete logs one request row only; the removed keys live in "
            "the batch-delete topic. user_agent attributes the source (for "
            "example a console-originated deletion).",
            f"__topic__: {TOPIC_BATCH_DELETE_LOG} AND {base} | "
            f"SELECT from_unixtime(__time__) AS time, request_id, "
            f"url_decode(object) AS objectname, user_agent, client_ip, "
            f"requester_id FROM log "
            f"WHERE url_decode(object) = '{escaped}' "
            f"ORDER BY __time__ DESC LIMIT 100",
            topic=TOPIC_BATCH_DELETE_LOG)
    if status:
        add("T4", f"Requests returning HTTP {status}",
            "Who and what is producing this status code.",
            f"{access} AND http_status: {status} | SELECT client_ip, operation, "
            f"error_code, ec, count(*) AS cnt FROM log GROUP BY client_ip, "
            f"operation, error_code, ec ORDER BY cnt DESC LIMIT 50")
    if operation:
        add("T5", f"Trace {operation} operations",
            "Writer attribution for one operation type.",
            f"{access} AND operation: {operation} | SELECT client_ip, "
            f"requester_id, access_id, sign_type, time, http_status, "
            f"url_decode(object) AS objectname FROM log "
            f"ORDER BY __time__ DESC LIMIT 50")
    if access_key:
        add("T7", "Which IPs used this AccessKey",
            "Credential-spread check: one key from many unknown IPs suggests a "
            "leaked credential.",
            f'{access} AND access_id: "{access_key}" | SELECT client_ip, '
            f"operation, http_status, count(*) AS cnt FROM log "
            f"GROUP BY client_ip, operation, http_status "
            f"ORDER BY cnt DESC LIMIT 50")

    # Always-available screening statements.
    add("T3", "Top client IPs (abnormal access screening)",
        "Rank callers by request count, error count and bytes out.",
        f"{access} | SELECT client_ip, count(*) AS cnt, "
        f"SUM(CASE WHEN http_status >= 400 THEN 1 ELSE 0 END) AS err_cnt, "
        f"SUM(content_length_out) AS bytes_out FROM log GROUP BY client_ip "
        f"ORDER BY cnt DESC LIMIT 20")
    add("T4e", "Error distribution by EC code",
        "Find which failure dominates before tracing one instance of it. All "
    "grouped fields are indexed, so no scan mode is needed.",
        f"{access} | SELECT ec, error_code, http_status, operation, sign_type, "
        f"count(*) AS cnt FROM log WHERE http_status >= 400 GROUP BY ec, "
        f"error_code, http_status, operation, sign_type "
        f"ORDER BY cnt DESC LIMIT 50")
    add("T8", "Anonymous versus signed access split",
        "sign_type NotSign with requester_id '-' means anonymous access.",
        f"{access} | SELECT sign_type, requester_id, count(*) AS cnt FROM log "
        f"GROUP BY sign_type, requester_id ORDER BY cnt DESC LIMIT 20")
    add("T6a", "Deletion attribution (single-object deletes)",
        "Who issued removal operations, with the first and last seen time.",
        f"{access} | SELECT client_ip, requester_id, access_id, sign_type, "
        f"count(*) AS cnt, min(time) AS first_seen, max(time) AS last_seen "
        f"FROM log WHERE operation IN ('DeleteObject','DeleteObjects',"
        f"'ExpireObject') GROUP BY client_ip, requester_id, access_id, "
        f"sign_type ORDER BY cnt DESC LIMIT 50")

    return out


def _run_query(project: str, region: str, query: str, from_ts: int,
               to_ts: int, line: int, profile: str | None,
               label: str) -> dict:
    """Execute one log query, returning a stable structure even on failure."""
    try:
        body = _cli.call_sls_get_logs(
            project=project, logstore=LOG_LOGSTORE, region=region,
            query=query, from_ts=from_ts, to_ts=to_ts,
            line=line, offset=0, reverse=False, profile=profile,
        )
    except _cli.CliError as e:
        _warn(f"{label} failed: {e}")
        return {"ok": False, "query": query, "rows": [],
                "error_code": e.code or "", "error_message": str(e)}

    rows = _extract_rows(body)
    meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
    return {
        "ok": True,
        "query": query,
        "rows": rows,
        "row_count": len(rows),
        "progress": str(meta.get("progress") or ""),
        "processed_rows": meta.get("processedRows"),
        "error_code": "",
        "error_message": "",
    }


def _extract_rows(body: dict) -> list[dict]:
    """Normalize the GetLogs payload into a list of row dicts."""
    if not isinstance(body, dict):
        return []
    for key in ("data", "logs", "body", "Logs"):
        candidate = body.get(key)
        if isinstance(candidate, list):
            return [r for r in candidate if isinstance(r, dict)]
    return []


def render_request_row(row: dict) -> list[str]:
    """Render one traced request as aligned lines, skipping empty fields."""
    lines = []
    for field in TRACE_FIELDS:
        value = row.get(field)
        if value in (None, "", "-"):
            continue
        text = str(value)
        if len(text) > 300:
            text = text[:300] + "..."
        lines.append(f"  {field:<24}: {text}")
    # Surface any field present in the row but absent from the curated list, so
    # a schema change never hides evidence silently.
    extra = sorted(set(row) - set(TRACE_FIELDS) - {"__source__", "__time__"})
    for field in extra:
        value = row.get(field)
        if value in (None, "", "-"):
            continue
        text = str(value)
        if len(text) > 200:
            text = text[:200] + "..."
        lines.append(f"  {field:<24}: {text}  (undocumented field)")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trace a single OSS request, an object's history, or the "
                    "error distribution in the realtime access log (read-only).",
    )
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--region", default="cn-hangzhou",
                        help="Region of the bucket (default: cn-hangzhou)")
    parser.add_argument("--uid", default="",
                        help="Account UID; derived via STS when omitted")
    parser.add_argument("--request-id", default="",
                        help="Exact OSS request ID to trace")
    parser.add_argument("--object", default="",
                        help="Object key whose history should be traced")
    parser.add_argument("--ip", default="",
                        help="Client IP filter (IPv4, IPv4 wildcard prefix or IPv6)")
    parser.add_argument("--status", default="",
                        help="HTTP status filter, e.g. 403")
    parser.add_argument("--operation", default="",
                        help="OSS operation filter, e.g. GetObject")
    parser.add_argument("--ak", default="",
                        help="AccessKey ID filter (the logged access_id field)")
    parser.add_argument("--batch-delete", action="store_true",
                        help="Query the batch-delete topic for --object or "
                             "--request-id (a batch delete logs one request row "
                             "only; removed keys live in that topic)")
    parser.add_argument("--exclude-cdn", action="store_true",
                        help="Exclude CDN back-to-origin rows from generated "
                             "statements (their client_ip is a CDN node)")
    parser.add_argument("--generate-only", action="store_true",
                        help="Do not execute any query; only generate the "
                             "statements for the customer to run in the console")
    parser.add_argument("--concurrency", action="store_true",
                        help="Also scan concurrent writes to --object "
                             "(used for conflict-style failures)")
    parser.add_argument("--hours", type=float, default=0.0,
                        help="Look-back window in hours (default 24, max 168)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Deliberately NOT a hard exit. When the log-read channel is unavailable the
    # script degrades to generating statements for the customer to run in the
    # console, which is still an actionable result. Reporting nothing, or
    # reporting an empty log, would both be wrong.
    channel_ok = shutil.which("aliyun") is not None
    channel_why = "" if channel_ok else "aliyun CLI not found on PATH"
    if not channel_ok:
        _warn(f"log-read channel unavailable: {channel_why}")
    generate_only = bool(args.generate_only) or not channel_ok

    window = DEFAULT_WINDOW_SECONDS
    if args.hours > 0:
        window = int(min(args.hours * 3600, MAX_WINDOW_SECONDS))
    to_ts = int(time.time())
    from_ts = to_ts - window

    uid = args.uid.strip()
    uid_source = "user-provided"
    if not uid:
        uid = _cli.resolve_account_id(region=args.region, profile=args.profile)
        uid_source = "auto-derived via sts get-caller-identity"
        if not uid:
            _warn("UID could not be derived; pass --uid explicitly")

    project = LOG_PROJECT_TEMPLATE.format(uid=uid, region=args.region) if uid else ""
    degradation: list[str] = []
    if not project:
        degradation.append("UID unavailable, log project cannot be addressed")

    if args.batch_delete and (args.object or args.request_id):
        mode = MODE_BATCH_DELETE
    elif generate_only:
        mode = MODE_GENERATE_ONLY
    elif args.request_id:
        mode = MODE_REQUEST_ID
    elif args.object:
        mode = MODE_OBJECT
    else:
        mode = MODE_ERROR_SUMMARY

    result: dict = {"ok": False, "rows": [], "query": "",
                    "error_code": "", "error_message": ""}
    concurrency = {"ok": False, "rows": [], "query": ""}
    batch_delete = {"ok": False, "rows": [], "query": ""}

    if generate_only:
        if not channel_ok:
            degradation.append(
                f"log-read channel unavailable ({channel_why}); NO query was "
                f"executed - degraded to generating console statements")
        else:
            degradation.append(
                "--generate-only: no query executed by design")
        print("[1/2] generate-only mode: no log query will be executed",
              file=sys.stderr)
    elif project:
        print(f"[1/2] tracing bucket={args.bucket} region={args.region} "
              f"mode={mode} window={window // 3600}h", file=sys.stderr)
        if mode == MODE_BATCH_DELETE:
            batch_delete = query_batch_delete_history(
                project, args.region, args.bucket, args.object,
                args.request_id, from_ts, to_ts, args.profile)
            result = batch_delete
        elif mode == MODE_REQUEST_ID:
            result = query_by_request_id(project, args.region, args.bucket,
                                        args.request_id, from_ts, to_ts,
                                        args.profile)
        elif mode == MODE_OBJECT:
            result = query_object_history(project, args.region, args.bucket,
                                         args.object, from_ts, to_ts,
                                         args.profile)
        else:
            result = query_error_summary(project, args.region, args.bucket,
                                        from_ts, to_ts, args.profile)

        if not result["ok"]:
            degradation.append(
                f"{mode} query failed: "
                f"{result.get('error_code') or result.get('error_message')}"
            )

        if args.concurrency and args.object:
            print("[2/2] scanning concurrent writes to the same object",
                  file=sys.stderr)
            concurrency = query_concurrent_writes(
                project, args.region, args.bucket, args.object,
                from_ts, to_ts, args.profile)
            if not concurrency["ok"]:
                degradation.append("concurrent write scan failed: "
                                   f"{concurrency.get('error_message')}")
        else:
            print("[2/2] concurrent write scan not requested", file=sys.stderr)
    else:
        # project is empty: already recorded above, do not log it twice.
        pass

    # Statements for the customer to run themselves: always produced, and the
    # primary output whenever nothing could be executed here.
    generated = generate_query_statements(
        args.bucket, args.region, project, ip=args.ip, object_key=args.object,
        status=args.status, operation=args.operation, access_key=args.ak,
        request_id=args.request_id, hours=window // 3600,
        exclude_cdn=args.exclude_cdn)

    rows = result.get("rows") or []
    key_findings = [
        f"Mode: {mode}",
        f"Log project: {project or 'unknown'}",
        f"Window: last {window // 3600}h",
        f"Log-read channel available: {channel_ok}",
        f"Queries executed here: {0 if generate_only else 1}",
        f"Rows returned: {len(rows)}",
        f"Console statements generated: {len(generated)}",
    ]
    if rows and mode == MODE_REQUEST_ID:
        first = rows[0]
        key_findings += [
            f"http_status={first.get('http_status', '-')}, "
            f"error_code={first.get('error_code', '-')}, "
            f"ec={first.get('ec', '-')}",
            f"operation={first.get('operation', '-')}, "
            f"sign_type={first.get('sign_type', '-')}",
        ]
    if rows and mode == MODE_ERROR_SUMMARY:
        top = rows[0]
        key_findings.append(
            f"Dominant failure: ec={top.get('ec', '-')}, "
            f"error_code={top.get('error_code', '-')}, "
            f"operation={top.get('operation', '-')}, "
            f"count={top.get('cnt', '-')}"
        )

    suggestions = [
        "Feed the traced row into diagnose_access_log.py to obtain the "
        "root-cause verdict and the configuration evidence that supports it.",
    ]
    if generate_only:
        suggestions = [
            "NO log query was executed by this run. Run the generated "
            "statements yourself in the SLS console of the bucket's region: "
            f"project {project or 'oss-log-<uid>-<region>'}, logstore "
            f"{LOG_LOGSTORE}. Set the time picker to the incident window "
            f"(last {window // 3600}h) before pasting a statement.",
            "Statements whose topic is the batch-delete topic must be run "
            "against that topic: a batch delete logs one request row in the "
            "access topic while the removed keys live in the batch-delete "
            "topic, joined by request_id.",
            "Paste the result back and re-run for a root-cause verdict, or "
            "restore the direct-read path by installing and configuring the "
            "aliyun CLI with the log read permission.",
        ]
    if mode == MODE_REQUEST_ID and not rows:
        suggestions.insert(0,
            "No row matched this request ID in the window. Widen --hours, "
            "confirm the region, and remember that realtime logging only "
            "covers requests made after it was enabled.")
    if mode == MODE_OBJECT and not rows:
        suggestions.insert(0,
            "No logged operation touched this object key in the window. The "
            "key may be spelled differently (keys are URL encoded in the log), "
            "or the operation happened outside the window, or realtime logging "
            "was not enabled at that time.")

    summary = (
        f"Traced bucket {args.bucket} in {args.region} using mode {mode} over "
        f"the last {window // 3600}h: {len(rows)} row(s) returned. "
        f"UID source: {uid_source}."
    )

    payload = {
        "bucket": args.bucket,
        "region": args.region,
        "uid": uid,
        "uid_source": uid_source,
        "log_project": project,
        "log_logstore": LOG_LOGSTORE,
        "topic": TOPIC_ACCESS_LOG,
        "mode": mode,
        "window": {"from": from_ts, "to": to_ts, "seconds": window},
        "request_id": args.request_id,
        "object": args.object,
        "query": result.get("query", ""),
        "ok": bool(result.get("ok")),
        "row_count": len(rows),
        "rows": rows,
        "error_code": result.get("error_code", ""),
        "error_message": result.get("error_message", ""),
        "concurrent_writes": concurrency,
        "batch_delete": batch_delete,
        "generate_only": generate_only,
        "channel_available": channel_ok,
        "channel_note": channel_why,
        "generated_queries": generated,
        "documented_fields": sorted(ACCESS_LOG_FIELDS),
        "degradation_log": degradation,
        "summary": summary,
        "key_findings": key_findings,
        "suggestions": suggestions,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0

    print("=" * 72)
    print(f"Access-log trace  |  mode: {mode}")
    print("=" * 72)
    print(f"  Bucket      : {args.bucket}")
    print(f"  Region      : {args.region}")
    print(f"  Log project : {project or '-'}")
    print(f"  Window      : last {window // 3600}h")
    if args.request_id:
        print(f"  Request ID  : {args.request_id}")
    if args.object:
        print(f"  Object      : {args.object}")
    print(f"  Rows        : {len(rows)}")
    print(f"  Channel     : {'available' if channel_ok else 'UNAVAILABLE - nothing was queried'}")
    print("-" * 72)

    if generate_only:
        print("\n  NO LOG QUERY WAS EXECUTED BY THIS RUN.")
        print("  The statements below are for you to run in the SLS console of")
        print(f"  the bucket's region: project {project or 'oss-log-<uid>-<region>'},")
        print(f"  logstore {LOG_LOGSTORE}. Set the time picker to the incident")
        print(f"  window (last {window // 3600}h) before pasting a statement.")

    if mode == MODE_ERROR_SUMMARY and rows:
        print(f"  {'ec':<16}{'error_code':<26}{'status':<8}"
              f"{'operation':<26}{'cnt':>8}")
        for row in rows[:20]:
            print(f"  {str(row.get('ec', '-')):<16}"
                  f"{str(row.get('error_code', '-')):<26}"
                  f"{str(row.get('http_status', '-')):<8}"
                  f"{str(row.get('operation', '-')):<26}"
                  f"{str(row.get('cnt', '-')):>8}")
    elif rows:
        for index, row in enumerate(rows[:10], 1):
            print(f"\n  --- row {index} ---")
            for line in render_request_row(row):
                print(line)
    elif generate_only:
        # Nothing was queried, so "no row returned" would be a false statement.
        print("  (no query was executed - see the generated statements below)")
    else:
        print("  (no row returned)")

    if concurrency.get("rows"):
        print("-" * 72)
        print(f"  Concurrent writes to the same object: "
              f"{len(concurrency['rows'])}")
        for row in concurrency["rows"][:20]:
            print(f"    {row.get('time', '-')}  {row.get('operation', '-'):<24}"
                  f" status={row.get('http_status', '-')}"
                  f" sign={row.get('sign_type', '-')}"
                  f" sync={row.get('sync_request', '-')}")

    if generated:
        print("-" * 72)
        heading = ("Console statements (generated, NOT executed here)"
                   if generate_only else
                   "Console statements (also generated for reuse)")
        print(f"  {heading}")
        for item in generated:
            print(f"\n  [{item['id']}] {item['title']}"
                  f"   (topic: {item['topic']})")
            print(f"      purpose: {item['purpose']}")
            statement = item["statement"]
            # Wrap long statements so they stay copy-pasteable in a terminal.
            while len(statement) > 96:
                cut = statement.rfind(" ", 0, 96)
                cut = cut if cut > 40 else 96
                print(f"      {statement[:cut]}")
                statement = statement[cut:].lstrip()
            print(f"      {statement}")

    print("-" * 72)
    print("Graceful Degradation Log")
    if degradation:
        for item in degradation:
            print(f"  [WARN] {item}")
    else:
        print("  none")
    print("=" * 72)
    print("\nSummary")
    print("-------")
    print(f"What was queried : {result.get('query') or '(skipped)'}")
    for finding in key_findings:
        print(f"  - {finding}")
    print("Next step :")
    for i, item in enumerate(suggestions, 1):
        print(f"  {i}. {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
