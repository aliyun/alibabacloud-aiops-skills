#!/usr/bin/env python3
"""
diagnose_access_log.py -- Root-cause engine for OSS access failures
===================================================================
SECURITY: READ-ONLY. This script reads the customer's own realtime access log
and the customer's own bucket / object / RAM configuration. It never reads,
prints or stores credentials, never modifies any configuration, and never
deletes or rewrites an object. Credentials are resolved by the default
credential chain (environment variables for the oss2 SDK, the aliyun CLI
profile for CLI calls). Confirm the diagnosis scope with the user before
running it.

Single entry point
------------------
This is the mandatory entry point of the skill. It orchestrates identity
resolution, region resolution, log-source probing, single-request tracing,
configuration evidence collection and the rule engine, then emits one report.
Do not hand-assemble the underlying queries.

Module layout (this file is the orchestrator only):
  _constants.py  field catalog, EC knowledge base, policy grammar, doc sources
  _oss_client.py oss2 SDK channel, error categories, region resolution, identity
  _cli.py        aliyun CLI channel for log and RAM reads
  _doc_lookup.py runtime official-documentation verification
  _rules.py      EC resolution and the rule engine (verdict classes A / B / C)
  _report.py     report rendering and the machine-consumable summary fields

The honesty contract: A / B / C verdicts
---------------------------------------
Every conclusion carries a verdict class, and the class decides what the report
is allowed to claim:

  A  provable from the customer's own logs and configuration. The report
     states a conclusion with the matching evidence quoted verbatim.
  B  evidence narrows the cause to a few candidates. The report lists each
     candidate with its own verification step, and states plainly that the
     decisive evidence is not reachable from the customer side.
  C  the decisive evidence is server-side only. The report escalates: it
     produces a support-ticket package and states exactly what could not be
     verified. Guessing a cause is forbidden.

Two downgrades are enforced automatically, because both are ways a confident
answer gets fabricated: no logged request row, or an error code that is normally
decided from logged attributes while the log channel was unusable.

The reason B and C exist: the server-side internal log that carries the
string-to-sign and the precise denial message is not exposed through any
customer-facing API. A signature mismatch therefore cannot be pinpointed from
the customer side, and saying otherwise would be fabrication.

Dual mode
---------
When the log cannot be read here (no CLI, no log permission, or realtime
logging not enabled), the run degrades instead of failing: it derives the log
target, hands over ready-to-run console statements, and states plainly that NO
query was executed. An unexecuted query is never reported as an empty log.

Usage:
  python3 diagnose_access_log.py --bucket my-bucket --region cn-hangzhou \
      --request-id 65A1B2C3D4E5F6G7H8I9J0K1
  python3 diagnose_access_log.py --bucket my-bucket --ec 0003-00000101
  python3 diagnose_access_log.py --bucket my-bucket --object images/a.png --hours 72
  python3 diagnose_access_log.py --bucket my-bucket --json --output report.json
  python3 diagnose_access_log.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import _cli
import _doc_lookup
import _oss_client
import collect_config_evidence as evidence_collector
import log_source_check
import trace_request
from _constants import (
    LOG_PROJECT_TEMPLATE,
    VERDICT_ESCALATE,
    VERDICT_LABELS,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)
from _report import build_summary_fields, generate_text_report
from _rules import (
    RULES,
    build_escalation_package,
    decode_post_policy,
    determine_account_relation,
    lookup_knowledge,
    rule_unknown,
)

SKILL_NAME = "alibabacloud-oss-access-log-trace-diagnosis"

# Report contract lines, relayed verbatim in meaning by the final answer.
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"


def _warn(message: str) -> None:
    """Record a degradation on stderr (observability contract)."""
    print(f"[WARN] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# EC-driven log lookup (orchestration helper)
# ---------------------------------------------------------------------------

def query_by_ec(project: str, region: str, bucket: str, ec: str,
                from_ts: int, to_ts: int, profile: str | None) -> dict:
    """Pull one representative logged row carrying the given EC code."""
    query = (f"{trace_request.build_base_filter(bucket)} AND ec: {ec} | "
             f"SELECT {trace_request._select_list()} FROM log "
             f"ORDER BY __time__ DESC LIMIT 1")
    try:
        body = _cli.call_sls_get_logs(
            project=project, logstore=log_source_check.LOG_LOGSTORE,
            region=region, query=query, from_ts=from_ts, to_ts=to_ts,
            line=1, offset=0, reverse=True, profile=profile)
    except _cli.CliError as e:
        return {"ok": False, "rows": [], "query": query,
                "error_code": e.code or "", "error_message": str(e)}
    rows = trace_request._extract_rows(body)
    return {"ok": True, "rows": rows, "query": query,
            "error_code": "", "error_message": ""}

# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def orchestrate(args) -> dict:
    """Run the full diagnosis and return the report payload.

    Step order matters: the bucket's REAL region must be resolved before the
    log project name is derived, because the project name embeds the region
    (oss-log-<uid>-<region>). Deriving it from an unverified --region would
    make a wrong region look exactly like "realtime logging is not enabled".
    """
    degradation: list[str] = []
    verified: list[str] = []
    unverifiable: list[str] = []
    autofill: list[str] = []

    # Not a hard exit: when the log-read channel is missing the run degrades to
    # configuration evidence plus generated console statements.
    channel_ok, channel_why = log_source_check.channel_available()
    if not channel_ok:
        _warn(f"log-read channel unavailable: {channel_why}")
        degradation.append(
            f"log-read channel unavailable ({channel_why}); NO log query was "
            f"executed")

    window = int(min(max(args.hours, 1.0), 168.0) * 3600)
    to_ts = int(time.time())
    from_ts = to_ts - window

    # --- Step 1: identity -------------------------------------------------
    print("[1/6] verifying the caller identity", file=sys.stderr)
    uid = args.uid.strip()
    uid_source = "user-provided"
    if not uid:
        uid = _oss_client.resolve_uid()
        uid_source = "auto-derived via sts get-caller-identity"
        if uid:
            autofill.append(f"UID auto-derived via the caller-identity check: {uid}")
        else:
            degradation.append("UID could not be derived; the realtime log "
                               "project cannot be addressed")

    # --- Step 2: resolve the bucket's real region -------------------------
    # A wrong region surfaces as AccessDenied "does not belong to you"
    # (measured), so resolving it first prevents a misleading permission error
    # on every later read AND a wrong log project name.
    print("[2/6] resolving the bucket region", file=sys.stderr)
    resolution = _oss_client.resolve_bucket_region(args.bucket, args.region)
    resolved_region = resolution.get("region") or args.region
    endpoint = _oss_client.endpoint_for_region(resolved_region)
    region_source = resolution.get("source", "unresolved")
    prefetched_info = resolution.get("info") or {}
    for warning in resolution.get("warnings") or []:
        _warn(warning)
        degradation.append(f"region resolution: {warning}")
    if region_source == "list_buckets":
        autofill.append(
            f"Region auto-resolved via the bucket listing fallback: "
            f"{resolved_region}")
    elif region_source == "user_provided":
        unverifiable.append(
            f"Bucket region could not be verified; '{resolved_region}' is the "
            f"caller-supplied value and remains an assumption.")
    else:
        verified.append(f"Bucket region resolved from the bucket itself: "
                        f"{resolved_region}")
    if resolved_region != args.region:
        autofill.append(
            f"Region corrected from '{args.region}' to '{resolved_region}' "
            f"(source: {region_source})")

    project = (LOG_PROJECT_TEMPLATE.format(uid=uid, region=resolved_region)
               if uid else "")
    if uid:
        autofill.append(
            f"Realtime log project derived from the naming rule "
            f"oss-log-<uid>-<region>: {project}")

    # --- Step 3: log source ----------------------------------------------
    print(f"[3/6] probing the realtime access-log source ({project or 'n/a'})",
          file=sys.stderr)
    probe = {"status": "skipped", "rows": [], "code": "", "message": ""}
    if project:
        probe = log_source_check.probe_logstore(
            project, resolved_region, args.bucket, from_ts, to_ts, args.profile)
        if probe["status"] != log_source_check.STATUS_OK:
            degradation.append(f"realtime log probe: {probe['status']} "
                               f"({probe.get('code') or probe.get('message')})")
            unverifiable.append(
                "Request-level log evidence: the realtime access log is "
                f"{probe['status']} for this bucket/window.")
        else:
            verified.append("Realtime access log is enabled and readable.")
    else:
        unverifiable.append("Request-level log evidence: no UID, so the log "
                            "project could not be addressed.")

    # --- Step 4: trace the request ---------------------------------------
    print("[4/6] tracing the request in the access log", file=sys.stderr)
    trace: dict = {"ok": False, "rows": [], "query": "", "error_code": "",
                   "error_message": ""}
    object_history: list[dict] = []
    concurrent: list[dict] = []
    batch_delete_rows: list[dict] = []
    row: dict = {}

    log_usable = bool(project) and probe.get("status") == log_source_check.STATUS_OK
    if log_usable:
        if args.request_id:
            trace = trace_request.query_by_request_id(
                project, resolved_region, args.bucket, args.request_id,
                from_ts, to_ts, args.profile)
        elif args.ec:
            trace = query_by_ec(project, resolved_region, args.bucket, args.ec,
                                from_ts, to_ts, args.profile)
        elif args.object:
            trace = trace_request.query_object_history(
                project, resolved_region, args.bucket, args.object,
                from_ts, to_ts, args.profile)
            object_history = trace.get("rows") or []
        else:
            trace = trace_request.query_error_summary(
                project, resolved_region, args.bucket, from_ts, to_ts,
                args.profile)

        if not trace.get("ok"):
            degradation.append("trace query failed: "
                               f"{trace.get('error_code') or trace.get('error_message')}")
        rows = trace.get("rows") or []
        if rows:
            # For an object history the interesting row is the failing one.
            failing = [r for r in rows
                       if str(r.get("http_status") or "").startswith(("4", "5"))]
            row = failing[0] if failing else rows[0]
            verified.append(f"Logged request row retrieved "
                            f"(request_id {row.get('request_id', '-')}).")
        else:
            unverifiable.append("No logged row matched the given filter in the "
                                "queried window.")

        if args.object and args.concurrency and row:
            scan = trace_request.query_concurrent_writes(
                project, resolved_region, args.bucket, args.object,
                from_ts, to_ts, args.profile)
            concurrent = scan.get("rows") or []

        # A removal question is not answered by the access topic alone: a batch
        # delete logs ONE request row there while the removed keys live in the
        # batch-delete topic. Query it whenever a removal is plausible.
        removal_plausible = bool(args.object) and (
            args.batch_delete
            or str(row.get("error_code") or "") == "NoSuchKey"
            or str(row.get("ec") or "") == "0026-00000001")
        if removal_plausible:
            batch = trace_request.query_batch_delete_history(
                project, resolved_region, args.bucket, args.object or "",
                args.request_id, from_ts, to_ts, args.profile)
            batch_delete_rows = batch.get("rows") or []
            if batch_delete_rows:
                verified.append(
                    f"Batch-delete topic queried: "
                    f"{len(batch_delete_rows)} removed-key row(s) found.")
            elif not batch.get("ok"):
                degradation.append(
                    "batch-delete topic query failed: "
                    f"{batch.get('error_code') or batch.get('error_message')}")
    else:
        unverifiable.append("Request-level log evidence: log source unusable, "
                            "so no row was traced.")

    # Console statements are always produced: they are the primary deliverable
    # whenever nothing could be executed here, and a reusable artefact otherwise.
    generated = trace_request.generate_query_statements(
        args.bucket, resolved_region, project, ip=args.ip,
        object_key=args.object, status=args.status, operation=args.operation,
        access_key=args.ak, request_id=args.request_id,
        hours=window // 3600, exclude_cdn=args.exclude_cdn)

    # --- Step 5: configuration evidence ----------------------------------
    print("[5/6] collecting bucket configuration evidence", file=sys.stderr)
    ec_from_row = str(row.get("ec") or "")
    ec = args.ec.strip() or ec_from_row
    knowledge = lookup_knowledge(ec, str(row.get("error_code") or ""),
                                 str(row.get("http_status") or ""))

    with_referer = args.with_referer or _needs_referer(knowledge, row)
    with_website = args.with_website or knowledge.get("error_code") == "MirrorFailed"
    with_logging = bool(args.with_logging) or probe.get("status") in (
        log_source_check.STATUS_NOT_ENABLED,
        log_source_check.STATUS_CHANNEL_UNAVAILABLE,
        log_source_check.STATUS_UNKNOWN,
    )
    object_arg = args.object or (str(row.get("object") or "")
                                 if _needs_object_acl(knowledge) else "")

    # The region was already resolved in Step 2; the bucket-info read from that
    # step is reused so the unconditional evidence call is not issued twice.
    evidence_bundle = evidence_collector.collect_all(
        args.bucket, resolved_region, profile=args.profile,
        object_key=object_arg, with_referer=with_referer,
        with_website=with_website, with_logging=with_logging,
        ram_user=args.ram_user, role_name=args.role_name, endpoint=endpoint,
        prefetched_info=prefetched_info)

    info = evidence_bundle["evidence"]["bucket_info"]
    acl = evidence_bundle["evidence"]["bucket_acl"]
    policy = evidence_bundle["evidence"]["bucket_policy"]
    public_block = evidence_bundle["evidence"]["public_access_block"]
    conditional = evidence_bundle["evidence"]["conditional"]
    ram = evidence_bundle["evidence"]["ram"]
    facts = evidence_bundle["facts"]
    referer_facts = evidence_bundle["referer"]

    for name, item in [("GetBucketInfo", info), ("GetBucketAcl", acl),
                       ("GetBucketPolicy", policy),
                       ("GetPublicAccessBlock", public_block)]:
        if not item.get("available"):
            degradation.append(
                f"{name}: unavailable "
                f"[{item.get('error_category') or '?'}] "
                f"{item.get('error_code') or item.get('error_message') or ''}")
            unverifiable.append(
                f"{name}: not readable, so any conclusion that depends on it "
                f"is unavailable.")
        else:
            verified.append(f"{name} read successfully.")
    degradation += evidence_bundle.get("degradation_log", [])
    owner_id = facts.get("owner_id") or ""
    if not owner_id and uid:
        # The project name needs a UID; prefer the bucket owner (always
        # consistent with the bucket) and fall back to the caller identity.
        owner_id = uid
        autofill.append(
            "Bucket owner UID unavailable; the caller UID was used as the "
            "log-project component instead. If the bucket belongs to another "
            "account the derived project name is wrong.")

    # --- Step 6: rule engine ---------------------------------------------
    print("[6/6] evaluating the rule engine", file=sys.stderr)
    account_relation = determine_account_relation(row, owner_id) if row else {}
    post_policy = decode_post_policy(args.post_policy) if args.post_policy else {}

    ctx = {
        "bucket": args.bucket,
        "region": resolved_region,
        "endpoint": endpoint,
        "region_source": region_source,
        "owner_id": owner_id,
        "facts": facts,
        "evidence": {"bucket_info": info, "bucket_acl": acl,
                     "bucket_policy": policy, "public_access_block": public_block,
                     "conditional": conditional, "ram": ram},
        "account_relation": account_relation,
        "object_history": object_history,
        "concurrent_writes": concurrent,
        "batch_delete": batch_delete_rows,
        "post_policy": post_policy,
        "mime_hint": args.mime_type,
        "log_usable": log_usable,
        "verified": verified,
        "unverifiable": unverifiable,
    }

    handler = RULES.get(knowledge.get("diagnosis") or "unknown", rule_unknown)
    try:
        verdict = handler(row, knowledge, ctx)
    except Exception as exc:  # a rule bug must not abort the whole report
        _warn(f"rule '{knowledge.get('diagnosis')}' raised {type(exc).__name__}: {exc}")
        degradation.append(f"rule {knowledge.get('diagnosis')} failed: {exc}")
        verdict = rule_unknown(row, knowledge, ctx)

    # Without any log row the verdict cannot be stronger than "needs input".
    if not row and verdict.get("verdict") == VERDICT_SELF_DIAGNOSABLE:
        verdict = dict(verdict)
        verdict["verdict"] = VERDICT_NEEDS_CONFIRMATION
        verdict["downgraded"] = (
            "Downgraded from a provable verdict because no logged request row "
            "was available; the conclusion now rests on configuration evidence "
            "alone.")
        unverifiable.append(
            "No logged request row was available, so the conclusion rests on "
            "configuration evidence only.")

    # A verdict whose declared evidence includes log fields cannot stay provable
    # when the log channel was never usable.
    if (not log_usable and verdict.get("verdict") == VERDICT_SELF_DIAGNOSABLE
            and knowledge.get("log_fields")):
        verdict = dict(verdict)
        verdict["verdict"] = VERDICT_NEEDS_CONFIRMATION
        verdict["downgraded"] = (
            "Downgraded because this error code is normally decided from logged "
            "request attributes, and no log query could be executed in this "
            "run.")
        unverifiable.append(
            "Logged request attributes required by this error code were not "
            "available (log source unusable).")

    escalation = {}
    if verdict.get("verdict") == VERDICT_ESCALATE:
        escalation = build_escalation_package(row, ctx, verdict)

    # --- Official documentation verification ------------------------------
    # Only performed when the caller passes the customer's own wording, so a
    # routine run issues no network request. _doc_lookup never raises: an
    # offline host yields a DEGRADED note instead of a failure.
    question = (getattr(args, "question", "") or "").strip()
    if question:
        doc_verification = _doc_lookup.lookup_config_topic(question)
    else:
        doc_verification = {"matched": False, "docs": [],
                            "source": "llms-index",
                            "note": "not requested (pass --question with the "
                                    "customer's own wording to verify against "
                                    "official documentation)"}

    status = STATUS_DEGRADED if degradation else STATUS_OK
    if verdict.get("verdict") == VERDICT_ESCALATE:
        next_action = ("Open a support ticket with the escalation package "
                       "below; the decisive evidence is not reachable from the "
                       "customer side.")
    elif not log_usable:
        next_action = ("Run the generated statements in the SLS console of "
                       f"region {resolved_region} (project "
                       f"{project or 'oss-log-<uid>-<region>'}, logstore "
                       f"oss-log-store), then re-run with the traced row for a "
                       f"root-cause verdict.")
    elif verdict.get("verdict") == VERDICT_NEEDS_CONFIRMATION:
        next_action = ("Complete the verification step listed for each ranked "
                       "candidate, then re-run to narrow the cause.")
    else:
        next_action = ("Apply the recommendation that matches the matched "
                       "statement; this skill is read-only and changed nothing.")

    return {
        "skill": SKILL_NAME,
        "session_id": _oss_client.session_id(),
        "status": status,
        "next_action": next_action,
        "bucket": args.bucket,
        "region": resolved_region,
        "region_source": region_source,
        "endpoint": endpoint,
        "uid": uid,
        "uid_source": uid_source,
        "log_project": project,
        "log_usable": bool(log_usable),
        "channel_available": channel_ok,
        "window": {"from": from_ts, "to": to_ts, "seconds": window},
        "probe_status": probe.get("status", "skipped"),
        "traced_row": row,
        "trace_query": trace.get("query", ""),
        "trace_row_count": len(trace.get("rows") or []),
        "object_history_count": len(object_history),
        "concurrent_write_count": len(concurrent),
        "batch_delete_rows": batch_delete_rows[:50],
        "generated_queries": generated,
        "knowledge": knowledge,
        "verdict_class": verdict.get("verdict"),
        "verdict_label": VERDICT_LABELS.get(verdict.get("verdict"), ""),
        "verdict_downgraded": verdict.get("downgraded", ""),
        "conclusion": verdict.get("conclusion", ""),
        "root_cause": verdict.get("root_cause", ""),
        "recommendations": verdict.get("recommendations", []),
        "evidence": verdict.get("evidence", {}),
        "facts": facts,
        "referer": referer_facts,
        "account_relation": account_relation,
        "conditional_evidence": conditional,
        "ram_evidence": ram,
        "post_policy": {k: v for k, v in post_policy.items() if k != "document"},
        "doc_verification": doc_verification,
        "escalation_package": escalation,
        "autofill_declarations": autofill,
        "verified": verified,
        "unverifiable": unverifiable,
        "degradation_log": degradation,
    }


def _needs_referer(knowledge: dict, row: dict) -> bool:
    """Hotlink protection is worth reading when a referer denial is plausible."""
    if knowledge.get("diagnosis") == "anonymous_denied":
        return True
    referer = str(row.get("referer") or "")
    return bool(referer) and referer != "-"


def _needs_object_acl(knowledge: dict) -> bool:
    return knowledge.get("diagnosis") in ("object_read_denied",
                                         "image_source_validation")

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diagnose why an OSS request failed, using the customer's "
                    "own realtime access log and configuration (read-only).",
    )
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--region", default="cn-hangzhou",
                        help="Region of the bucket (default: cn-hangzhou)")
    parser.add_argument("--request-id", default="",
                        help="Exact OSS request ID to diagnose")
    parser.add_argument("--ec", default="",
                        help="EC error code, when taken from the error response "
                             "body instead of the log")
    parser.add_argument("--object", default="",
                        help="Object key involved in the failing request")
    parser.add_argument("--concurrency", action="store_true",
                        help="Also scan concurrent writes to --object")
    parser.add_argument("--batch-delete", action="store_true",
                        help="Also query the batch-delete topic for --object "
                             "(a batch delete logs one request row in the "
                             "access topic; removed keys live in that topic)")
    parser.add_argument("--ip", default="",
                        help="Client IP filter for the generated statements")
    parser.add_argument("--status", default="",
                        help="HTTP status filter for the generated statements")
    parser.add_argument("--operation", default="",
                        help="Operation filter for the generated statements")
    parser.add_argument("--ak", default="",
                        help="AccessKey ID filter for the generated statements")
    parser.add_argument("--exclude-cdn", action="store_true",
                        help="Exclude CDN back-to-origin rows from generated "
                             "statements")
    parser.add_argument("--with-logging", action="store_true",
                        help="Force reading the periodic log shipping config")
    parser.add_argument("--question", default="",
                        help="The customer's original wording; when given, the "
                             "answer is verified against official OSS "
                             "documentation at runtime and only returned URLs "
                             "may be cited")
    parser.add_argument("--hours", type=float, default=24.0,
                        help="Look-back window in hours (default 24, max 168)")
    parser.add_argument("--uid", default="",
                        help="Account UID; derived via STS when omitted")
    parser.add_argument("--with-referer", action="store_true",
                        help="Force reading the hotlink protection whitelist")
    parser.add_argument("--with-website", action="store_true",
                        help="Force reading static website / mirror rules")
    parser.add_argument("--ram-user", default="",
                        help="RAM user name for the explicit-Deny scan")
    parser.add_argument("--role-name", default="",
                        help="RAM role name whose trust policy should be read")
    parser.add_argument("--post-policy", default="",
                        help="Base64 form-upload policy to decode")
    parser.add_argument("--mime-type", default="",
                        help="Content type hint when the log row lacks it")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Report format (default: text)")
    parser.add_argument("--output", default="",
                        help="Write the report to this path instead of stdout")
    args = parser.parse_args()

    try:
        payload = orchestrate(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[ERROR] diagnosis aborted: {type(exc).__name__}: {exc}\n"
              "[ERROR] Next step: re-run with --format json to see how far the "
              "run got, and check the aliyun CLI credential chain.",
              file=sys.stderr)
        return 1

    payload = build_summary_fields(payload)

    if args.format == "json":
        rendered = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    else:
        rendered = generate_text_report(payload)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except OSError as exc:
            print(f"[ERROR] could not write {args.output}: {exc}",
                  file=sys.stderr)
            return 1
        print(f"[done] report written to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    print("[done] diagnosis complete; no configuration was changed.",
          file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Self-test entry: delegate to the two modules that own the assertions
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run the inline boundary assertions of _rules and _report."""
    import _report
    import _rules
    _rules._self_test()
    _report._self_test()
    print("self-test passed")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
        sys.exit(0)
    sys.exit(main())
