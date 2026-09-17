#!/usr/bin/env python3
"""
oss_deletion_recovery_diagnosis.py -- OSS accidental-deletion recovery and
deletion-residue diagnosis
===========================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketVersioning,
ListMultipartUploads (+ ListBuckets fallback) to the OSS control plane and
GetCallerIdentity to STS. It NEVER restores a version, NEVER removes a
delete marker, NEVER aborts a multipart upload, and NEVER deletes anything;
every recovery / cleanup action is emitted as manual guidance for the user
to execute. Credentials come exclusively from the default credential chain
(environment variables for the OSS SDK, aliyun CLI default chain for STS);
AK/SK are never read, printed, or passed explicitly.

Diagnoses:
  * accidental object deletion recoverability -- versioning status decision
    tree (enabled -> restore path guidance; suspended -> partial recovery;
    never configured -> expectation management + prevention advice)
  * failed bucket deletion (BucketNotEmpty) residue classes -- leftover
    objects, unfinished multipart-upload fragments, historical versions /
    delete markers
  * storage usage / cost not dropping after deletion -- residue attribution
  * prevention suggestions (versioning, lifecycle, backup, access logging)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_deletion_recovery_diagnosis.py --bucket <name> \
      [--object <deleted-object-key>] [--scope recover|residue|all] \
      [--region <expected-region>] [--question "<customer original wording>"]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
from _doc_lookup import SKILL_TOPICS, lookup_config_topic
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name must degrade to the
# unified OssClientError(category="invalid") -- never a bare oss2
# ClientError Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__
# raises ClientError 'The bucket_name is invalid'; _build_bucket converts
# it, the entry records [WARN] + errors[] and still emits STATUS: DEGRADED
# with exit 0). No network call happens on this path.
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name


# Official-doc verification leg (read-only, help.aliyun.com only): enabled by
# --question alone, per the documented contract in SKILL.md.

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
_VALID_SCOPES = ("recover", "residue", "all")

# Bucket-name lock after an overdue-driven release (ticket 000EAR1NT7;
# readable copy in references/recovery-decision-tree.md §3).
RELEASED_BUCKET_NAME_LOCK_NOTE = (
    "After a bucket is released through the overdue-payment cleanup, the "
    "bucket NAME is locked by the system for a cooldown window and cannot "
    "be re-created or reused right away; the released data itself is "
    "unrecoverable per the overdue-payment policy. Workaround "
    "(ticket-verified): create a NEW bucket under a different name and "
    "bind the original custom domain (CNAME) to it, so application "
    "endpoints built on the custom domain keep working without code "
    "changes.")
assert "cooldown" in RELEASED_BUCKET_NAME_LOCK_NOTE  # presence guard
assert "custom domain" in RELEASED_BUCKET_NAME_LOCK_NOTE


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def normalize_versioning_status(raw) -> str:
    """Normalize a GetBucketVersioning raw status string.

    Returns one of: enabled | suspended | not_configured | unknown.
    Measured raw values on oss2 2.19.1: 'Enabled', 'Suspended', None/''
    (versioning never configured).
    """
    s = (str(raw).strip().lower() if raw is not None else "")
    if s == "enabled":
        return "enabled"
    if s == "suspended":
        return "suspended"
    if s in ("", "none", "null"):
        return "not_configured"
    return "unknown"


assert normalize_versioning_status("Enabled") == "enabled"  # normal
assert normalize_versioning_status("Suspended") == "suspended"  # normal
assert normalize_versioning_status(None) == "not_configured"  # boundary: never configured
assert normalize_versioning_status("") == "not_configured"  # boundary: empty string
assert normalize_versioning_status("  ENABLED ") == "enabled"  # boundary: case+whitespace
assert normalize_versioning_status("weird-value") == "unknown"  # invalid: unexpected value


def endpoint_from_location(location: str) -> str:
    """Derive the public query endpoint from a bucket location string."""
    loc = (location or "").strip().lower()
    if not loc:
        return ""
    if not loc.startswith("oss-"):
        loc = "oss-" + loc
    return loc + ".aliyuncs.com"


assert endpoint_from_location("oss-cn-hangzhou") == "oss-cn-hangzhou.aliyuncs.com"  # normal
assert endpoint_from_location("cn-shanghai") == "oss-cn-shanghai.aliyuncs.com"  # boundary: bare region
assert endpoint_from_location("") == ""  # invalid: empty


def recovery_verdict(versioning_status: str, object_key: str = "") -> dict:
    """Decide the recoverability of an accidentally deleted object.

    versioning_status: normalized value from normalize_versioning_status().
    Returns {"recoverable": yes|partial|no|unknown, "mechanism": str,
             "guidance": [str,...]}. Guidance is MANUAL instruction only --
    this skill never executes any restore operation.
    """
    target = f"'{object_key}'" if object_key else "the deleted object"
    if versioning_status == "enabled":
        return {
            "recoverable": "yes",
            "mechanism": (
                "With versioning enabled, deleting without a version id only "
                "inserts a delete marker; all historical versions of "
                f"{target} are retained and recoverable."),
            "guidance": [
                "Locate the object's versions (console: file list -> show "
                "historical versions; API: GetBucketVersions / "
                "ListObjectVersions) and identify the version from before "
                "the deletion.",
                "Restore it manually: restore that historical version to be "
                "the current version (console 'restore' action or `ossutil "
                "revert oss://<bucket>/<object> <versionId>`), or delete "
                "the topmost delete marker so the previous version becomes "
                "current again.",
                "This skill is read-only: the restore / delete-marker "
                "removal must be executed by the user; verify the version "
                "id before acting, permanent deletion of a specific version "
                "is irreversible.",
            ],
        }
    if versioning_status == "suspended":
        return {
            "recoverable": "partial",
            "mechanism": (
                "Versioning is suspended: a delete WITHOUT version id creates "
                "a delete marker (versionId=null) and historical versions are "
                f"NOT affected — {target} may still be recoverable by removing "
                "the null delete marker or restoring a historical version. "
                "Only a delete WITH an explicit version id permanently removes "
                "that specific version."),
            "guidance": [
                "List the historical versions of the object (GetBucketVersions "
                "/ console historical versions); if a pre-suspension version "
                "exists, it can be recovered by removing the topmost null "
                "delete marker or using ossutil revert.",
                "If the object was deleted WITH an explicit version id during "
                "suspension, that version is permanently gone — state this "
                "honestly.",
                "Objects newly written during suspension carry versionId=null "
                "and lack true version protection; consider re-enabling "
                "versioning (PutBucketVersioning, user executes).",
            ],
        }
    if versioning_status == "not_configured":
        return {
            "recoverable": "no",
            "mechanism": (
                "Versioning was never configured on this bucket and OSS "
                "provides no recycle bin: a plain delete permanently removes "
                f"{target}; the data is not recoverable from OSS itself."),
            "guidance": [
                "Check whether a copy exists elsewhere: cross-region "
                "replication target bucket, local/client backups, or a "
                "backup system (e.g. cloud backup of OSS).",
                "If OSS access logging / real-time log delivery was enabled "
                "before the deletion, the logs can at least attribute when "
                "and by which request the object was deleted (they do not "
                "restore data).",
                "Prevention: enable versioning, configure lifecycle "
                "carefully, and keep backups for critical data.",
            ],
        }
    return {
        "recoverable": "unknown",
        "mechanism": (
            "The versioning status could not be determined (query degraded "
            "or returned an unexpected value); recoverability cannot be "
            "concluded."),
        "guidance": [
            "Re-run after fixing the recorded errors, or check the bucket's "
            "versioning state in the OSS console manually before concluding "
            "whether the deleted object is recoverable.",
        ],
    }


_r = recovery_verdict("enabled", "uploads/a.pdf")
assert _r["recoverable"] == "yes" and any("delete marker" in g for g in _r["guidance"])  # normal: enabled
_r = recovery_verdict("suspended")
assert _r["recoverable"] == "partial"  # normal: suspended
_r = recovery_verdict("not_configured", "")
assert _r["recoverable"] == "no" and "recycle bin" in _r["mechanism"].lower()  # boundary: no object key
_r = recovery_verdict("unknown")
assert _r["recoverable"] == "unknown"  # invalid/degraded status
del _r


def residue_verdict(multipart: dict, versioning_status: str) -> dict:
    """Classify deletion residue that blocks bucket deletion / holds storage.

    multipart: {"count": int, "truncated": bool} or None when degraded.
    Returns {"classes": [str,...], "details": [str,...]} describing the
    residue classes found (objects / multipart fragments / versions).
    """
    classes: list = []
    details: list = []
    if multipart is not None:
        count = int(multipart.get("count", 0) or 0)
        truncated = bool(multipart.get("truncated", False))
        if count > 0:
            classes.append("multipart_fragments")
            shown = f">= {count}" if truncated else str(count)
            details.append(
                f"{shown} unfinished multipart upload(s) keep their parts "
                "stored and billed until aborted; they count toward 'bucket "
                "is not empty' (BucketNotEmpty) and keep storage usage from "
                "dropping. Cleanup is a write operation -- the user must "
                "abort them (console fragment management, or ossutil rm -m "
                "-r -f, or a lifecycle AbortMultipartUpload rule).")
        else:
            details.append(
                "No unfinished multipart uploads found; fragments are not "
                "the residue source.")
    else:
        details.append(
            "Multipart fragment check degraded; fragment residue cannot be "
            "excluded (ListMultipartUploads failed or was skipped).")
    if versioning_status in ("enabled", "suspended"):
        classes.append("historical_versions")
        details.append(
            "Versioning is/was active: historical versions and delete "
            "markers keep consuming storage even after the current version "
            "is deleted, and block bucket deletion. Review them via the "
            "console historical-version view or GetBucketVersions; "
            "permanent deletion of versions is a user-executed write "
            "operation.")
    return {"classes": classes, "details": details}


_rv = residue_verdict({"count": 3, "truncated": False}, "enabled")
assert "multipart_fragments" in _rv["classes"] and "historical_versions" in _rv["classes"]  # normal: both residues
_rv = residue_verdict({"count": 0, "truncated": False}, "not_configured")
assert _rv["classes"] == []  # normal: no residue
_rv = residue_verdict(None, "unknown")
assert _rv["classes"] == [] and any("degraded" in d for d in _rv["details"])  # boundary: degraded multipart
del _rv


def build_recommendations(versioning_status: str, verdict: dict,
                          residue: dict, scope: str) -> list:
    """Compose prevention / next-step recommendations from the evidence."""
    recs: list = []
    if verdict.get("recoverable") == "yes":
        recs.append(
            "Recovery is possible via versioning: follow the manual restore "
            "steps above; this skill only outputs the guidance, the user "
            "executes the restore.")
    elif verdict.get("recoverable") == "no":
        recs.append(
            "Without versioning the deleted data cannot be recovered from "
            "OSS; set expectations honestly and rely on external backups / "
            "replication copies if any exist.")
    if versioning_status != "enabled":
        recs.append(
            "Prevention: enable versioning on the bucket (PutBucketVersioning, "
            "user-executed) so future accidental deletions only insert a "
            "delete marker and stay recoverable; note historical versions "
            "are billed as storage, so pair it with a lifecycle rule for "
            "noncurrent versions.")
    if residue.get("classes"):
        recs.append(
            "Residue found (" + ", ".join(residue["classes"]) + "): clean it "
            "with the user-executed steps in "
            "references/deletion-residue-checklist.md before expecting the "
            "bucket to be deletable or storage usage to drop.")
    if scope in ("residue", "all"):
        recs.append(
            "If the goal is to stop billing by deleting the bucket, "
            "BucketNotEmpty persists until objects, multipart fragments and "
            "(if versioned) all historical versions and delete markers are "
            "removed; the console delete-bucket wizard scans these items "
            "automatically.")
    recs.append(
        "Prevention baseline (official four mechanisms): enable versioning; "
        "for compliance-critical buckets set a WORM retention policy "
        "(BucketWorm) so no user - including the owner - can delete before "
        "the retention period expires; keep cross-region replication with an "
        "add/update-only policy or scheduled Cloud Backup for critical data "
        "(Cloud Backup supports only Standard/Infrequent Access buckets and "
        "objects, and does not back up or restore object ACLs); additionally "
        "enable real-time log delivery (access logs) to trace future "
        "deletions and gate delete permissions with least-privilege RAM "
        "policies.")
    return recs


assert any("Recovery is possible" in r for r in build_recommendations(
    "enabled", recovery_verdict("enabled"), residue_verdict({"count": 0}, "enabled"), "all"))  # normal
assert any("cannot be recovered" in r for r in build_recommendations(
    "not_configured", recovery_verdict("not_configured"), residue_verdict({"count": 0}, "not_configured"), "recover"))  # normal: unrecoverable
assert any("BucketNotEmpty" in r for r in build_recommendations(
    "enabled", recovery_verdict("enabled"), residue_verdict({"count": 2}, "enabled"), "residue"))  # boundary: residue scope
assert isinstance(build_recommendations("unknown", recovery_verdict("unknown"), residue_verdict(None, "unknown"), "all"), list)  # invalid: all degraded


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

def _emit(report: dict, status: str, next_action: str, question: str = "") -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines.
    When --question is supplied, attach the official-doc verification leg
    (never changes STATUS / NEXT_ACTION and never raises)."""
    if question:
        report["doc_verification"] = lookup_config_topic(
            question, SKILL_TOPICS)
    report["status"] = status
    report["next_action"] = next_action
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    if question and "doc_verification" in report:
        # Human-readable Doc verification tail (spec section 2.4).
        dv = report["doc_verification"]
        if dv.get("matched"):
            print("Doc verification: matched via official OSS docs "
                  "(llms-index):")
            for doc in dv["docs"]:
                print(f"  - {doc['title']}: {doc['url']}")
        else:
            print("Doc verification: DEGRADED (offline) — conclusions are "
                  "based on embedded knowledge only.")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS accidental-deletion recoverability and "
                    "deletion residue (read-only; never restores anything)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--object", default="",
                        help="The accidentally deleted object key "
                             "(optional; used in the recovery guidance)")
    parser.add_argument("--scope", default="all", choices=_VALID_SCOPES,
                        help="recover = recoverability assessment only; "
                             "residue = residue/attribution only; "
                             "all (default) = both")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint)")
    parser.add_argument("--question", default="",
                        help="Customer's original question wording; enables "
                             "the official-doc verification leg "
                             "(doc_verification section in the JSON)")
    args = parser.parse_args()

    # Missing-bucket guard: most real tickets never name a bucket, so a bare
    # argparse exit 2 leaves the customer with no next step. Ask for the name
    # and surface the buckets this credential can actually see.
    if not (args.bucket or "").strip():
        _hint = []
        _herrs = []
        try:
            try:
                _all = _oss_client.list_buckets()
            except TypeError:
                _all = _oss_client.list_buckets(prefix="")
            _hint = [b["name"] for b in _all][:30]
        except Exception as e:
            _herrs.append({"category": "degraded", "code": "ListBucketsFailed",
                           "message": str(e)[:200]})
            print(f"[WARN] ListBuckets bucket-name hint degraded: {e}",
                  file=sys.stderr)
        _rep = {
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-deletion-recovery-diagnosis"),
            "bucket": "",
            "buckets_in_account": _hint,
            "errors": _herrs,
            "auto_filled": [],
        }
        _na = ("Ask the user which OSS bucket the issue concerns; "
               "buckets_in_account lists up to 30 buckets visible to the "
               "current credential.")
        if not _hint:
            _na += (" No bucket is listable with the current credential: ask "
                    "for the exact bucket name and its region instead.")
        return _emit(_rep, "FAIL", _na)
    question = args.question.strip() if isinstance(args.question, str) else ""

    auto_filled = []
    degraded_steps = 0

    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: resolve the initial query endpoint.
    if args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: "
                           f"{query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --region provided)")

    report = {
        "skill": "alibabacloud-oss-deletion-recovery-diagnosis",
        "bucket": args.bucket,
        "object": args.object or None,
        "scope": args.scope,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "versioning": None,
        "recovery": None,
        "residue": None,
        "recommendations": [],
        "errors": [],
    }
    if question:
        report["question"] = question

    # Step 3: GetBucketInfo -- core evidence call (location/storage class).
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
        degraded_steps += 1
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
        # Fallback: ListBuckets prefix lookup to locate the bucket region.
        try:
            located = _oss_client.list_buckets(prefix=args.bucket)
            hits = [b for b in located if b["name"] == args.bucket]
            if hits:
                report["bucket_info"] = {
                    "name": hits[0]["name"],
                    "location": hits[0]["location"],
                    "source": "ListBuckets fallback (GetBucketInfo degraded)",
                }
                bucket_info = report["bucket_info"]
            elif located is not None:
                report["errors"].append({
                    "category": "not_found",
                    "code": "ListBucketsNoMatch",
                    "message": f"ListBuckets(prefix={args.bucket}) returned "
                               f"{len(located)} bucket(s), none named "
                               f"'{args.bucket}' in this account",
                })
        except OssClientError as e2:
            degraded_steps += 1
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): {e2}",
                  file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Use the bucket's real location for subsequent metadata calls.
    if bucket_info and bucket_info.get("location"):
        located_endpoint = endpoint_from_location(bucket_info["location"])
        if located_endpoint and located_endpoint != query_endpoint:
            auto_filled.append(
                f"query endpoint re-derived from bucket location "
                f"{bucket_info['location']}: {located_endpoint}")
            query_endpoint = located_endpoint
            report["query_endpoint"] = query_endpoint

    have_bucket = bucket_info is not None

    # Step 4: GetBucketVersioning -- the recoverability decision input.
    versioning_status = None
    if args.scope in ("recover", "all") and have_bucket:
        try:
            vres = _oss_client.get_bucket_versioning(args.bucket,
                                                     query_endpoint)
            report["versioning"] = vres
            versioning_status = normalize_versioning_status(
                vres.get("status"))
        except OssClientError as e:
            degraded_steps += 1
            print(f"[WARN] GetBucketVersioning degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
    elif args.scope == "residue" and have_bucket:
        # Residue attribution still needs the versioning state to decide
        # whether historical versions hold storage.
        try:
            vres = _oss_client.get_bucket_versioning(args.bucket,
                                                     query_endpoint)
            report["versioning"] = vres
            versioning_status = normalize_versioning_status(
                vres.get("status"))
        except OssClientError as e:
            degraded_steps += 1
            print(f"[WARN] GetBucketVersioning degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())

    normalized_status = (versioning_status if versioning_status is not None
                         else "unknown")

    # Step 5: residue check (ListMultipartUploads), optional-degraded.
    multipart = None
    if args.scope in ("residue", "all") and have_bucket:
        try:
            multipart = _oss_client.list_multipart_uploads(
                args.bucket, query_endpoint)
        except OssClientError as e:
            degraded_steps += 1
            print(f"[WARN] ListMultipartUploads degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())

    # Step 6: pure-function verdicts from whatever evidence exists.
    if args.scope in ("recover", "all"):
        verdict = recovery_verdict(normalized_status, args.object)
        report["recovery"] = verdict
    residue = residue_verdict(multipart, normalized_status)
    report["residue"] = residue
    report["recommendations"] = build_recommendations(
        normalized_status, report.get("recovery") or {}, residue, args.scope)

    # Step 7: status + next action.
    if have_bucket:
        if degraded_steps:
            next_action = (
                "Diagnosis partially degraded: review the recorded [WARN] "
                "errors (permissions/endpoint/network), fix them, and re-run "
                "to complete the evidence set; conclusions above are limited "
                "to the data actually returned.")
            sys.exit(_emit(report, "DEGRADED", next_action, question))
        recoverable = (report["recovery"] or {}).get("recoverable")
        if recoverable == "yes":
            next_action = (
                "Versioning is enabled: restore the pre-deletion version or "
                "remove the topmost delete marker manually (guidance in the "
                "report; this skill never executes writes).")
        elif recoverable == "partial":
            next_action = (
                "Versioning is suspended: a delete without version id creates "
                "a null delete marker — check historical versions; if one "
                "exists, guide the user to remove the delete marker or use "
                "ossutil revert to restore. Only version-id-specific deletes "
                "are permanently unrecoverable.")
        elif recoverable == "no":
            next_action = (
                "Versioning was never configured: the deleted data cannot "
                "be recovered from OSS; rely on backups/replication copies "
                "and enable versioning to prevent recurrence.")
        else:
            next_action = (
                "Bucket metadata verified; residue findings and prevention "
                "suggestions are in the report.")
        sys.exit(_emit(report, "OK", next_action, question))

    # Degraded: no bucket info obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        # Ticket 000EAR1NT7 basis: after an overdue-driven release the old
        # bucket name is locked and cannot be re-created; surface it here.
        report["released_bucket_name_note"] = RELEASED_BUCKET_NAME_LOCK_NOTE
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); if the "
            "bucket itself was deleted, object data is not recoverable "
            "without a backup/replication copy. If it disappeared after an "
            "overdue release, the name is locked by the system and cannot "
            "be re-created (see released_bucket_name_note). Verify the "
            "bucket name spelling and owning account, then re-run.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketInfo / "
            "oss:GetBucketVersioning / oss:ListMultipartUploads / "
            "oss:ListBuckets (see references/ram-policies.md) or confirm "
            "the bucket belongs to this account, then re-run.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with "
            "--region of the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host; verify the "
            "network and re-run -- never conclude 'unrecoverable' from a "
            "failed call.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure the "
            "default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action, question))


if __name__ == "__main__":
    sys.exit(main())
