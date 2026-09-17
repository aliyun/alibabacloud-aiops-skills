#!/usr/bin/env python3
"""
log_source_check.py -- Realtime access-log source probe and self-check
======================================================================
SECURITY: READ-ONLY. This script only reads the customer's own realtime access
log and the bucket's own logging configuration. It never reads, prints or
stores credentials, and it never changes any configuration. Authentication is
resolved exclusively by the aliyun CLI default credential chain.

Purpose
-------
Every later diagnosis step depends on the realtime access log existing and
producing rows. This probe answers four questions before any tracing starts:

  1. Which project / logstore should be queried?  (derived, never guessed)
  2. Is realtime logging enabled at all?          (ProjectNotExist means no)
  3. Does the caller have permission to read it?  (denied means a RAM gap)
  4. Are there rows for this bucket in the window? (zero rows is a finding)

It deliberately distinguishes those four outcomes, because "no data" and "not
enabled" and "not permitted" need completely different customer actions.

Degradation contract: a failure here never aborts the run. It is recorded as
[WARN] on stderr, reported in the Graceful Degradation Log section, and the
script still exits 0 with a structured result so the diagnosis can continue on
configuration evidence alone.

Usage:
  python3 log_source_check.py --bucket my-bucket --region cn-hangzhou
  python3 log_source_check.py --bucket my-bucket --region cn-hangzhou --hours 6
  python3 log_source_check.py --bucket my-bucket --json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time

import _cli
import _oss_client
from _constants import (
    ACCESS_LOG_FIELDS,
    DEFAULT_TIMEOUT,
    DEFAULT_WINDOW_SECONDS,
    LOG_LOGSTORE,
    LOG_PROJECT_TEMPLATE,
    MAX_LOG_LINES,
    TOPIC_ACCESS_LOG,
    USUALLY_INDEXED_FIELDS,
)

# Probe outcomes. Kept as stable string constants so downstream scripts and the
# JSON contract never depend on prose.
STATUS_OK = "available"
STATUS_NO_DATA = "no_data_in_window"
STATUS_NOT_ENABLED = "not_enabled"
STATUS_NOT_PERMITTED = "not_permitted"
# The log channel itself is unusable (no aliyun CLI, or the CLI does not serve
# the log product). This is NOT "no data": nothing was queried. The skill must
# degrade to deriving the log target and generating query statements for the
# customer to run in the console, and say so plainly.
STATUS_CHANNEL_UNAVAILABLE = "channel_unavailable"
STATUS_UNKNOWN = "unknown"


def _log_warn(message: str) -> None:
    """Record a degradation on stderr (observability contract)."""
    print(f"[WARN] {message}", file=sys.stderr)


def resolve_uid(region: str, profile: str | None) -> str:
    """Derive the account UID; return "" when it cannot be resolved."""
    uid = _cli.resolve_account_id(region=region, profile=profile)
    if not uid:
        _log_warn(
            "sts get-caller-identity did not return an AccountId; the "
            "realtime log project name cannot be derived. Later steps must be "
            "given --uid explicitly."
        )
    return uid


def build_query(bucket: str) -> str:
    """Build the probe query.

    The topic filter is mandatory: one logstore carries both access-detail rows
    (oss_access_log) and hourly metering rows (oss_metering_log). Without the
    topic pin, a count over the logstore mixes the two kinds.
    """
    return f"__topic__: {TOPIC_ACCESS_LOG} AND bucket: {bucket}"


def channel_available() -> tuple[bool, str]:
    """Report whether the log-read channel can be used at all.

    Checked before any query so that a missing CLI is reported as "nothing was
    queried" rather than being mistaken for "the log is empty".
    """
    if shutil.which("aliyun") is None:
        return False, "aliyun CLI not found on PATH"
    return True, ""


def probe_logstore(project: str, region: str, bucket: str,
                   from_ts: int, to_ts: int,
                   profile: str | None) -> dict:
    """Attempt one minimal read and classify the outcome."""
    ok, why = channel_available()
    if not ok:
        return {"status": STATUS_CHANNEL_UNAVAILABLE, "code": "CliMissing",
                "message": why, "rows": []}

    query = build_query(bucket)
    try:
        body = _cli.call_sls_get_logs(
            project=project, logstore=LOG_LOGSTORE, region=region,
            query=query, from_ts=from_ts, to_ts=to_ts,
            line=1, offset=0, reverse=True, profile=profile,
        )
    except _cli.CliError as e:
        code = (e.code or "").strip()
        text = f"{code} {e}".lower()
        # The CLI itself cannot serve this product: nothing was queried, so the
        # result must not be worded as an empty log.
        if _cli.is_channel_missing(e):
            return {"status": STATUS_CHANNEL_UNAVAILABLE, "code": code,
                    "message": str(e), "rows": []}
        if "projectnotexist" in text or "project not exist" in text:
            return {"status": STATUS_NOT_ENABLED, "code": code,
                    "message": str(e), "rows": []}
        if "logstorenotexist" in text or "logstore not exist" in text:
            return {"status": STATUS_NOT_ENABLED, "code": code,
                    "message": str(e), "rows": []}
        if any(marker in text for marker in (
                "unauthorized", "denied", "nopermission", "forbidden",
                "signaturenotmatch", "invalidaccesskeyid")):
            return {"status": STATUS_NOT_PERMITTED, "code": code,
                    "message": str(e), "rows": []}
        return {"status": STATUS_UNKNOWN, "code": code,
                "message": str(e), "rows": []}

    rows = _extract_rows(body)
    if rows:
        return {"status": STATUS_OK, "code": "", "message": "", "rows": rows}
    return {"status": STATUS_NO_DATA, "code": "", "message": "", "rows": []}


def _extract_rows(body: dict) -> list[dict]:
    """Normalize the GetLogs payload into a list of row dicts.

    The response shape carries the rows under 'data' (or 'body'/'logs' in some
    CLI renderings) and query metadata under 'meta'. All variants are tolerated
    so the JSON contract of this script stays stable.
    """
    if not isinstance(body, dict):
        return []
    for key in ("data", "logs", "body", "Logs"):
        candidate = body.get(key)
        if isinstance(candidate, list) and candidate:
            return [r for r in candidate if isinstance(r, dict)]
    return []


def describe_schema(rows: list[dict]) -> dict:
    """Report which documented fields actually appear, and which are missing.

    Field presence varies with the logstore's index configuration and with the
    request type, so this is measured rather than assumed.
    """
    if not rows:
        return {"present": [], "absent": sorted(ACCESS_LOG_FIELDS)}
    seen = set()
    for row in rows:
        seen.update(row.keys())
    present = sorted(f for f in ACCESS_LOG_FIELDS if f in seen)
    absent = sorted(f for f in ACCESS_LOG_FIELDS if f not in seen)
    return {"present": present, "absent": absent,
            "extra": sorted(seen - set(ACCESS_LOG_FIELDS))}


def probe_log_shipping(bucket: str, region: str, profile: str | None) -> dict:
    """Fallback evidence: is periodic log shipping configured on the bucket?

    Reached only when realtime logging cannot be used. This read goes through
    the oss2 SDK and is a conditional call, so it is intentionally absent from
    related_apis.yaml.
    """
    result = _oss_client.read_config("GetBucketLogging", bucket, region,
                                     timeout=DEFAULT_TIMEOUT)
    if not result.get("available"):
        error = result.get("error") or {}
        _log_warn(f"oss GetBucketLogging unavailable: "
                  f"{error.get('code') or error.get('message')}")
        return {"queried": True, "available": False, "enabled": False,
                "error": error.get("code") or error.get("message", ""),
                "target_bucket": "", "target_prefix": ""}
    data = result.get("data") or {}
    return {"queried": True, "available": True,
            "enabled": bool(data.get("enabled")),
            "target_bucket": data.get("target_bucket", ""),
            "target_prefix": data.get("target_prefix", ""),
            "error": ""}


def build_guidance(status: str, project: str, region: str, bucket: str) -> list[str]:
    """Return the customer action items that match the probe outcome."""
    if status == STATUS_NOT_ENABLED:
        return [
            f"Realtime log query is not enabled for this account/region, so "
            f"project {project} does not exist. Enable it in the OSS console: "
            f"bucket {bucket} -> monitoring -> realtime log query.",
            "Realtime logging only captures requests made AFTER it is enabled. "
            "Historical requests cannot be recovered this way; state this "
            "plainly instead of implying the log is empty.",
            "If periodic log shipping to a bucket is configured instead, those "
            "log objects can be downloaded and parsed offline; the script "
            "reports whether shipping is enabled.",
        ]
    if status == STATUS_NOT_PERMITTED:
        return [
            "The credential can reach the log service but is not allowed to "
            "read this logstore. Grant log:GetLogStoreLogs on "
            f"acs:log:*:*:project/{project}/logstore/{LOG_LOGSTORE}, then "
            "re-run this probe.",
            "See references/ram-policies.md for the minimal read-only policy.",
        ]
    if status == STATUS_NO_DATA:
        return [
            f"The logstore exists but returned no row for bucket {bucket} in "
            f"the queried window. Widen the window (--hours), verify the "
            f"bucket name and its region, and confirm that requests actually "
            f"reached this bucket in that period.",
            "A bucket in a different region writes to a different project "
            "(one project per account per region); re-run with the correct "
            "--region.",
        ]
    if status == STATUS_CHANNEL_UNAVAILABLE:
        return [
            "The log-read channel is unavailable on this host, so NO log query "
            "was executed. This is not the same as an empty log: nothing was "
            "asked of the log service.",
            "Degrade to the console path: derive the realtime log target "
            f"(project {project or 'oss-log-<uid>-<region>'}, logstore "
            f"{LOG_LOGSTORE}) and hand the customer the query statements to run "
            f"in the SLS console themselves.",
            "To restore the direct-read path, install and configure the aliyun "
            "CLI, and confirm it serves the log service product.",
        ]
    if status == STATUS_OK:
        return [
            "Realtime access log is readable. Proceed to trace_request.py to "
            "pull the specific request, then to diagnose_access_log.py for the "
            "root-cause verdict.",
        ]
    return [
        "The probe failed for a reason that could not be classified. Record "
        "the raw error, then continue the diagnosis on configuration evidence "
        "alone and state that no log evidence was available.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe whether the OSS realtime access log is enabled, "
                    "readable and producing rows for a bucket (read-only).",
    )
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--region", default="cn-hangzhou",
                        help="Region of the bucket (default: cn-hangzhou)")
    parser.add_argument("--uid", default="",
                        help="Account UID; derived via STS when omitted")
    parser.add_argument("--hours", type=float, default=0.0,
                        help="Look-back window in hours (default 24, max 168)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Deliberately NOT a hard exit: when the CLI is missing the probe reports
    # channel_unavailable and the skill degrades to query-statement generation
    # instead of refusing to produce a report.
    channel_ok, channel_why = channel_available()
    if not channel_ok:
        _log_warn(f"log-read channel unavailable: {channel_why}")

    window = DEFAULT_WINDOW_SECONDS
    if args.hours > 0:
        window = int(min(args.hours, 168) * 3600)
    to_ts = int(time.time())
    from_ts = to_ts - window

    uid = args.uid.strip()
    uid_source = "user-provided"
    if not uid:
        uid = resolve_uid(args.region, args.profile)
        uid_source = "auto-derived via sts get-caller-identity"

    degradation: list[str] = []
    if not uid:
        degradation.append("UID could not be derived; project name unknown")
        project = ""
        result = {"status": STATUS_UNKNOWN, "code": "", "rows": [],
                  "message": "UID unavailable, probe skipped"}
    else:
        project = LOG_PROJECT_TEMPLATE.format(uid=uid, region=args.region)
        print(f"[1/2] probing {project} / {LOG_LOGSTORE} "
              f"({args.region}, last {window // 3600}h)", file=sys.stderr)
        result = probe_logstore(project, args.region, args.bucket,
                                from_ts, to_ts, args.profile)
        if result["status"] != STATUS_OK:
            degradation.append(
                f"realtime log probe: {result['status']} "
                f"({result.get('code') or result.get('message')})"
            )

    # Fallback evidence only when the realtime log cannot be used.
    shipping = {"queried": False, "available": False, "enabled": False,
                "target_bucket": "", "target_prefix": "", "error": ""}
    if result["status"] in (STATUS_NOT_ENABLED, STATUS_UNKNOWN,
                            STATUS_CHANNEL_UNAVAILABLE):
        print("[2/2] checking periodic log shipping on the bucket",
              file=sys.stderr)
        shipping = probe_log_shipping(args.bucket, args.region, args.profile)
    else:
        print("[2/2] realtime log usable; skipping the log-shipping fallback",
              file=sys.stderr)

    schema = describe_schema(result.get("rows") or [])
    guidance = build_guidance(result["status"], project, args.region, args.bucket)

    payload = {
        "bucket": args.bucket,
        "region": args.region,
        "uid": uid,
        "uid_source": uid_source,
        "log_project": project,
        "log_logstore": LOG_LOGSTORE,
        "topic": TOPIC_ACCESS_LOG,
        "window": {"from": from_ts, "to": to_ts, "seconds": window},
        "status": result["status"],
        "error_code": result.get("code", ""),
        "error_message": result.get("message", ""),
        "sample_row_count": len(result.get("rows") or []),
        "field_schema": schema,
        "usually_indexed_fields": list(USUALLY_INDEXED_FIELDS),
        "log_shipping": shipping,
        "degradation_log": degradation,
        "summary": "",
        "key_findings": [],
        "suggestions": guidance,
    }

    status_text = {
        STATUS_OK: "realtime access log is readable and returning rows",
        STATUS_NO_DATA: "logstore reachable but no row in this window",
        STATUS_NOT_ENABLED: "realtime log query is NOT enabled",
        STATUS_NOT_PERMITTED: "logstore reachable but reading is NOT permitted",
        STATUS_CHANNEL_UNAVAILABLE: "log-read channel unavailable; NO query was "
                                    "executed (degraded to console guidance)",
        STATUS_UNKNOWN: "probe outcome could not be classified",
    }[result["status"]]

    payload["summary"] = (
        f"Probed the realtime access log for bucket {args.bucket} in "
        f"{args.region}: {status_text}. UID source: {uid_source}."
    )
    payload["key_findings"] = [
        f"Log project: {project or 'unknown'}",
        f"Logstore: {LOG_LOGSTORE}, topic filter: {TOPIC_ACCESS_LOG}",
        f"Probe status: {result['status']}",
        f"Fields observed: {len(schema.get('present') or [])} of "
        f"{len(ACCESS_LOG_FIELDS)} documented fields",
        f"Periodic log shipping enabled: {shipping.get('enabled')}",
    ]

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("=" * 68)
        print("Realtime access-log source probe")
        print("=" * 68)
        print(f"  Bucket        : {args.bucket}")
        print(f"  Region        : {args.region}")
        print(f"  UID           : {uid or '-'}  ({uid_source})")
        print(f"  Log project   : {project or '-'}")
        print(f"  Logstore      : {LOG_LOGSTORE}")
        print(f"  Topic filter  : {TOPIC_ACCESS_LOG}")
        print(f"  Window        : last {window // 3600}h")
        print(f"  Status        : {result['status']}")
        if result.get("code"):
            print(f"  Error code    : {result['code']}")
        if result.get("message"):
            print(f"  Error detail  : {str(result['message'])[:200]}")
        if schema.get("present"):
            print(f"  Fields seen   : {len(schema['present'])} "
                  f"(missing: {len(schema.get('absent') or [])})")
        print(f"  Log shipping  : enabled={shipping.get('enabled')}")
        print("-" * 68)
        print("Graceful Degradation Log")
        if degradation:
            for item in degradation:
                print(f"  [WARN] {item}")
        else:
            print("  none")
        print("=" * 68)
        print("\nSummary")
        print("-------")
        print(f"What was checked : whether {project or 'the realtime log project'} "
              f"is enabled, readable and producing rows for {args.bucket}.")
        print(f"Key finding      : {status_text}.")
        print("Next step        :")
        for i, item in enumerate(guidance, 1):
            print(f"  {i}. {item}")

    # Always exit 0: an unusable log source is a finding to report, not a
    # script failure. A non-zero exit would abort the whole diagnosis.
    return 0


if __name__ == "__main__":
    sys.exit(main())
