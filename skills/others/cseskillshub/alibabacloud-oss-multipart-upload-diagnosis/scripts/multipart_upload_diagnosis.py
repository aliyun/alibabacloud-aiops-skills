#!/usr/bin/env python3
"""
multipart_upload_diagnosis.py -- OSS large-file multipart upload diagnosis
==========================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo (+ ListBuckets fallback),
ListMultipartUploads to the OSS control plane and GetCallerIdentity to STS.
Never mutates anything: fragment cleanup (AbortMultipartUpload) is a WRITE
operation and is intentionally NOT executed by this skill -- it only emits
manual cleanup guidance and command templates for the user
(references/fragment-cleanup-guide.md). Credentials come exclusively from
the default credential chain; AK/SK are never read, printed, or passed.

Diagnoses:
  * stuck / interrupted / failed large-file uploads: server-side vs
    client-side vs network attribution decision tree
  * multipart parameter sanity: file size -> recommended part size /
    concurrency; validation of a user-supplied part size against the OSS
    limits (file <= 48.8 TB, 1..10000 parts, part 100 KB..5 GB,
    PutObject <= 5 GB)  [official: help.aliyun.com multipart-upload doc]
  * fragment identification: unfinished multipart uploads enumerated with
    the read-only ListMultipartUploads, age analysis and storage-cost impact
    explanation (uploaded-but-never-completed parts keep incurring storage
    fees; official: AbortMultipartUpload doc note)
  * resumable (breakpoint) upload guidance for interrupted transfers

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 multipart_upload_diagnosis.py --bucket <name> \
      [--file-size 40GB] [--part-size 10MB] [--concurrency 8] \
      [--prefix <object-prefix>] [--endpoint <endpoint>] [--region <region>] \
      [--symptom stuck|slow|interrupted|fragment|failed] \
      [--question "<customer original wording>"]
"""

from __future__ import annotations

import argparse
import json
import math
import re
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


# Official-doc verification leg (read-only, help.aliyun.com only). The leg
# runs for EVERY status (OK / DEGRADED / FAIL) whenever --question is
# supplied: the customer's original wording deserves official-doc evidence
# (or an explicit offline-degradation statement) regardless of how the
# diagnosis itself concludes. is_advisory_question below stays as a pure,
# self-tested wording classifier (configuration / usage question vs. a pure
# error report).
_ADVISORY_SIGNALS = (
    "怎么", "怎样", "如何", "是否", "能否", "能不能", "可以", "可不可以",
    "配置", "开通", "设置", "开启", "支持", "限制", "办法", "如何反驳",
    "how ", "how to", "can i", "is it possible", "what is", "how do",
)


def is_advisory_question(question: str) -> bool:
    """Pure check: does the customer wording look like a configuration /
    usage advisory question (as opposed to a pure error report)?"""
    if not isinstance(question, str):
        return False
    text = question.strip().lower()
    if not text:
        return False
    return any(sig in text for sig in _ADVISORY_SIGNALS)


assert is_advisory_question("分片上传怎么设置分片大小？") is True      # normal: zh signal
assert is_advisory_question("how do I resume an interrupted upload?") is True  # normal: en signal
assert is_advisory_question("上传大文件一直失败，报错超时") is False  # boundary: pure error report
assert is_advisory_question("") is False and is_advisory_question(None) is False  # invalid

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# ---------------------------------------------------------------------------
# OSS multipart upload limits (verified against official documentation,
# https://help.aliyun.com/zh/oss/user-guide/multipart-upload, 2026-08):
#   * single object via multipart upload: <= 48.8 TB
#   * number of parts: 1 .. 10,000
#   * single part size: 100 KB .. 5 GB (the LAST part may be smaller than
#     100 KB)
# Simple upload (PutObject) limit, verified against
# https://help.aliyun.com/zh/oss/user-guide/simple-upload, 2026-08:
#   * PutObject: <= 5 GB per request
# Fragment billing, verified against
# https://help.aliyun.com/zh/oss/developer-reference/abortmultipartupload:
#   * uploaded-but-unfinished/unaborted parts occupy storage space and keep
#     incurring storage fees until completed or aborted.
# ---------------------------------------------------------------------------
MAX_OBJECT_SIZE = int(48.8 * (1024 ** 4))      # 48.8 TB
MAX_PART_COUNT = 10000
MIN_PART_SIZE = 100 * 1024                     # 100 KB
MAX_PART_SIZE = 5 * (1024 ** 3)                # 5 GB
PUT_OBJECT_LIMIT = 5 * (1024 ** 3)             # simple upload cap

_UNIT_MULTIPLIERS = {
    "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4,
}


# ---------------------------------------------------------------------------
# Pure functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def parse_size(text) -> int:
    """Parse a human size literal ('40GB', '512 mb', '1048576') to bytes.

    Returns -1 for any invalid / missing / negative input. Units are
    case-insensitive binary multipliers (KB=1024 B). Bare numbers are bytes.
    """
    if text is None:
        return -1
    s = str(text).strip().upper()
    if not s:
        return -1
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB)?", s)
    if not m:
        return -1
    value = float(m.group(1))
    unit = m.group(2) or "B"
    size = int(value * _UNIT_MULTIPLIERS[unit])
    return size if size >= 0 else -1


assert parse_size("40GB") == 40 * 1024 ** 3            # normal: GB
assert parse_size("512 mb") == 512 * 1024 ** 2         # normal: space + lowercase unit
assert parse_size("1048576") == 1048576                # boundary: bare bytes
assert parse_size("100KB") == 102400                   # boundary: minimal part size
assert parse_size("") == -1                            # invalid: empty
assert parse_size(None) == -1                          # invalid: missing
assert parse_size("abc") == -1                         # invalid: non-numeric
assert parse_size("-5GB") == -1                        # invalid: negative


def human_size(num) -> str:
    """Render bytes as a short human string (B/KB/MB/GB/TB, 1 decimal)."""
    try:
        n = float(num)
    except (TypeError, ValueError):
        return ""
    if n < 0:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1024.0
    return ""


assert human_size(1024) == "1 KB"                       # normal
assert human_size(40 * 1024 ** 3) == "40 GB"            # normal: whole GB
assert human_size(1536) == "1.5 KB"                     # boundary: fraction
assert human_size(0) == "0 B"                           # boundary: zero
assert human_size(-5) == ""                             # invalid: negative
assert human_size(None) == ""                           # invalid: missing


def recommend_part_params(file_size: int) -> dict:
    """Recommend multipart parameters for a file size (pure function).

    Returns {"strategy", "part_size_bytes", "part_size_human",
             "part_count", "concurrency", "notes"}.
      strategy: simple  -- file <= 5 GB: PutObject is enough
                multipart -- within the 48.8 TB object limit
                unsupported -- beyond 48.8 TB or non-positive size
    Part size targets ~1000 parts, clamped to [1 MB, 5 GB] and rounded up
    to whole MB; concurrency scales with part count, clamped to [1, 16].
    """
    if file_size is None or file_size <= 0:
        return {"strategy": "unsupported", "part_size_bytes": 0,
                "part_size_human": "", "part_count": 0, "concurrency": 0,
                "notes": ["file size missing or non-positive"]}
    if file_size > MAX_OBJECT_SIZE:
        return {"strategy": "unsupported", "part_size_bytes": 0,
                "part_size_human": "", "part_count": 0, "concurrency": 0,
                "notes": ["file exceeds the 48.8 TB per-object limit of "
                          "multipart upload"]}
    if file_size <= PUT_OBJECT_LIMIT:
        return {"strategy": "simple", "part_size_bytes": file_size,
                "part_size_human": human_size(file_size),
                "part_count": 1, "concurrency": 1,
                "notes": ["file <= 5 GB: simple upload (PutObject) is "
                          "sufficient; multipart adds no benefit"]}
    target = file_size / 1000.0
    part_size = max(1024 * 1024, min(int(math.ceil(target / 1048576)) * 1048576,
                                     MAX_PART_SIZE))
    part_count = int(math.ceil(file_size / part_size))
    concurrency = max(1, min(16, part_count, 4 * max(1, int(math.log2(
        max(2, part_size // (1024 * 1024)))))))
    return {"strategy": "multipart", "part_size_bytes": part_size,
            "part_size_human": human_size(part_size),
            "part_count": part_count, "concurrency": concurrency,
            "notes": []}


assert recommend_part_params(40 * 1024 ** 3)["strategy"] == "multipart"      # normal: 40 GB
assert recommend_part_params(40 * 1024 ** 3)["part_count"] <= MAX_PART_COUNT  # normal: part budget respected
assert recommend_part_params(100 * 1024 ** 2)["strategy"] == "simple"        # boundary: 100 MB -> PutObject
assert recommend_part_params(PUT_OBJECT_LIMIT)["strategy"] == "simple"       # boundary: exactly 5 GB
assert recommend_part_params(PUT_OBJECT_LIMIT + 1)["strategy"] == "multipart"  # boundary: 5 GB + 1
assert recommend_part_params(MAX_OBJECT_SIZE)["strategy"] == "multipart"     # boundary: exactly 48.8 TB
assert recommend_part_params(MAX_OBJECT_SIZE + 1)["strategy"] == "unsupported"  # invalid: over limit
assert recommend_part_params(-1)["strategy"] == "unsupported"                # invalid: negative


def validate_part_params(part_size: int, file_size: int) -> dict:
    """Validate a user-chosen part size against OSS multipart limits.

    Returns {"valid": bool, "errors": [str]}. Rules (official limits):
      * part size in [100 KB, 5 GB]
      * resulting part count <= 10,000
      * file size <= 48.8 TB (0/unknown file size: only the part size bound
        is checked)
    """
    errors = []
    if part_size <= 0:
        errors.append("part size must be positive")
    elif part_size < MIN_PART_SIZE:
        errors.append(
            f"part size {human_size(part_size)} is below the 100 KB minimum "
            "(only the LAST part may be smaller than 100 KB)")
    elif part_size > MAX_PART_SIZE:
        errors.append(
            f"part size {human_size(part_size)} exceeds the 5 GB per-part "
            "maximum")
    if file_size and file_size > 0:
        if file_size > MAX_OBJECT_SIZE:
            errors.append("file exceeds the 48.8 TB multipart object limit")
        elif part_size > 0:
            count = int(math.ceil(file_size / part_size))
            if count > MAX_PART_COUNT:
                errors.append(
                    f"part count {count} exceeds 10,000; increase part size "
                    f"to at least {human_size(int(math.ceil(file_size / MAX_PART_COUNT)))}")
    return {"valid": not errors, "errors": errors}


assert validate_part_params(10 * 1024 * 1024, 40 * 1024 ** 3)["valid"]      # normal
assert not validate_part_params(1024, 1024 ** 3)["valid"]                    # boundary: below 100 KB
assert validate_part_params(MIN_PART_SIZE, 1024)["valid"]                    # boundary: exactly 100 KB
assert not validate_part_params(6 * 1024 ** 3, 10 * 1024 ** 3)["valid"]      # boundary: above 5 GB
assert not validate_part_params(1024 ** 2, 20 * 1024 ** 3)["valid"]          # boundary: >10000 parts
assert not validate_part_params(0, 0)["valid"]                               # invalid: zero part size
assert validate_part_params(5 * 1024 ** 2, 0)["valid"]                       # boundary: unknown file size


def classify_fragment_age(age_hours) -> str:
    """Bucket an unfinished upload by age since InitiateMultipartUpload.

      recent    -- < 1 h: an upload may legitimately still be in progress
      stale     -- 1 h .. 24 h: likely interrupted; resume or abort soon
      abandoned -- > 24 h: almost certainly abandoned; fragment (storage cost)
      unknown   -- no valid age
    """
    if age_hours is None:
        return "unknown"
    try:
        h = float(age_hours)
    except (TypeError, ValueError):
        return "unknown"
    if h < 0:
        return "unknown"
    if h < 1:
        return "recent"
    if h <= 24:
        return "stale"
    return "abandoned"


assert classify_fragment_age(0.2) == "recent"           # normal
assert classify_fragment_age(6) == "stale"              # normal
assert classify_fragment_age(48) == "abandoned"         # normal
assert classify_fragment_age(0) == "recent"             # boundary: zero age
assert classify_fragment_age(1) == "stale"              # boundary: 1 h edge
assert classify_fragment_age(24) == "stale"             # boundary: 24 h edge
assert classify_fragment_age(24.1) == "abandoned"       # boundary: just over 24 h
assert classify_fragment_age(None) == "unknown"         # invalid: missing
assert classify_fragment_age("x") == "unknown"          # invalid: non-numeric


def triage_symptom(symptom: str) -> dict:
    """Map a user-reported symptom to the three-way attribution tree
    (server-side / client-side / network) plus first-hop checks.

    Returns {"branch", "checks": [str]}. Unknown symptoms map to a generic
    evidence-first branch.
    """
    s = (symptom or "").strip().lower()
    if s in ("stuck", "slow"):
        return {"branch": "network-or-client",
                "checks": [
                    "Compare client-side elapsed time with the OSS Request "
                    "ID: keep the x-oss-request-id of a hung UploadPart and "
                    "check whether the request ever reached OSS (client "
                    "logs / ossutil output 'Response: ... RequestId').",
                    "response_time >> server_cost_time in access logs means "
                    "network transfer dominates: check client egress "
                    "bandwidth, proxies/firewalls, and cross-region or "
                    "internet upload paths.",
                    "Too-small part size or too-low concurrency stalls a "
                    "large transfer: verify part size/concurrency against "
                    "the recommendation of this script.",
                ]}
    if s in ("interrupted", "resume"):
        return {"branch": "client-or-network",
                "checks": [
                    "Interruption is client-side (process crash, timeout) "
                    "or network-side (reset/DNS); the server never aborts "
                    "an upload on its own.",
                    "Use the SDK resumable_upload (breakpoint resume) with "
                    "a checkpoint directory, or ossutil cp with --checkpoint-dir, "
                    "so the transfer continues from the already-uploaded "
                    "parts instead of restarting.",
                    "Leftover parts of the interrupted upload are "
                    "fragments: list them here and follow the manual "
                    "cleanup guidance if they are no longer needed.",
                ]}
    if s in ("failed", "error"):
        return {"branch": "server-or-client",
                "checks": [
                    "HTTP 4xx = client/permission/parameter problem; "
                    "HTTP 5xx = service-side (retry with backoff).",
                    "Single-request errors of simple upload (EntityTooLarge, "
                    "AccessDenied, SignatureDoesNotMatch) belong to "
                    "alibabacloud-oss-transfer-error-code-diagnosis; this "
                    "skill focuses on multipart/resumable flows.",
                    "NoSuchUpload means the uploadId was already aborted or "
                    "completed -- re-initiate the multipart upload.",
                ]}
    if s in ("fragment", "fragments", "cleanup", "cost"):
        return {"branch": "fragment-management",
                "checks": [
                    "Unfinished multipart uploads are stored as fragments "
                    "and keep incurring storage fees until completed or "
                    "aborted (official AbortMultipartUpload doc).",
                    "This skill only LISTS fragments (read-only); cleanup "
                    "must be executed by the user per "
                    "references/fragment-cleanup-guide.md.",
                    "Consider a lifecycle AbortIncompleteMultipartUpload "
                    "rule so future leftovers expire automatically.",
                ]}
    return {"branch": "unspecified",
            "checks": [
                "Run the diagnosis with --bucket to collect evidence first "
                "(unfinished uploads, bucket location), then attribute "
                "server-side vs client-side vs network.",
            ]}


assert triage_symptom("stuck")["branch"] == "network-or-client"       # normal
assert triage_symptom("interrupted")["branch"] == "client-or-network"  # normal
assert triage_symptom("failed")["branch"] == "server-or-client"       # normal
assert triage_symptom("fragment")["branch"] == "fragment-management"  # normal
assert triage_symptom("STUCK ")["branch"] == "network-or-client"      # boundary: case+space
assert triage_symptom("")["branch"] == "unspecified"                  # invalid: empty
assert triage_symptom(None)["branch"] == "unspecified"                # invalid: missing


def build_fragment_findings(upload_list: dict) -> dict:
    """Aggregate fragment evidence from a ListMultipartUploads result.

    Returns {"count", "age_distribution", "oldest_age_hours",
             "storage_cost_note"}.
    """
    uploads = upload_list.get("uploads", []) if upload_list else []
    dist = {"recent": 0, "stale": 0, "abandoned": 0, "unknown": 0}
    oldest = None
    for u in uploads:
        bucket = classify_fragment_age(u.get("age_hours"))
        dist[bucket] += 1
        age = u.get("age_hours")
        if isinstance(age, (int, float)) and (oldest is None or age > oldest):
            oldest = age
    return {
        "count": len(uploads),
        "age_distribution": dist,
        "oldest_age_hours": oldest,
        "storage_cost_note": (
            "Uploaded-but-unfinished multipart parts are stored as "
            "fragments and keep incurring storage fees until the upload is "
            "completed or aborted; this enumeration is read-only -- cleanup "
            "must be executed by the user "
            "(see references/fragment-cleanup-guide.md)."),
    }


assert build_fragment_findings({"uploads": []})["count"] == 0          # boundary: empty
assert build_fragment_findings({"uploads": [
    {"age_hours": 0.2}, {"age_hours": 48}, {"age_hours": None}]})[
    "age_distribution"] == {"recent": 1, "stale": 0, "abandoned": 1,
                            "unknown": 1}                               # normal: mixed
assert build_fragment_findings(None)["count"] == 0                     # invalid: missing input
assert build_fragment_findings({"uploads": [{"age_hours": 3}]})[
    "oldest_age_hours"] == 3                                           # normal: oldest tracking


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

def _emit(report: dict, status: str, next_action: str, question: str = "") -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines.
    When --question is supplied, attach the official-doc verification leg
    for every status (OK / DEGRADED / FAIL; never changes STATUS /
    NEXT_ACTION and never raises)."""
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
        elif str(dv.get("note") or "").startswith("DEGRADED"):
            print("Doc verification: DEGRADED (offline) — conclusions are "
                  "based on embedded knowledge only.")
        else:
            print("Doc verification: no matching official doc found in the "
                  "help.aliyun.com index; state this explicitly, never "
                  "fabricate doc URLs.")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS large-file multipart upload problems: "
                    "stuck/interrupted/failed uploads, parameter sanity, "
                    "fragment identification (read-only)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--file-size", default="",
                        help="Size of the file being uploaded, e.g. 40GB / "
                             "512MB / 1048576 (optional; drives part size/"
                             "concurrency recommendation)")
    parser.add_argument("--part-size", default="",
                        help="Part size the user configured, e.g. 10MB "
                             "(optional; validated against OSS limits)")
    parser.add_argument("--concurrency", default="",
                        help="Concurrency the user configured (optional; "
                             "sanity-checked against the part count)")
    parser.add_argument("--prefix", default="",
                        help="Object key prefix filter for the fragment "
                             "listing (optional)")
    parser.add_argument("--endpoint", default="",
                        help="The endpoint the user currently configured "
                             "(optional; used to locate the bucket)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; derives the query "
                             "endpoint when --endpoint is absent)")
    parser.add_argument("--symptom", default="",
                        help="stuck | slow | interrupted | failed | "
                             "fragment (optional; selects the attribution "
                             "branch of the decision tree)")
    parser.add_argument("--question", default="",
                        help="Customer's original question wording; enables "
                             "the official-doc verification leg "
                             "(doc_verification section in the JSON)")
    args = parser.parse_args()
    question = args.question.strip() if isinstance(args.question, str) else ""

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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-multipart-upload-diagnosis"),
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
        return _emit(_rep, "FAIL", _na, question)

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: parameter sanity (pure functions, no network).
    file_size = parse_size(args.file_size) if args.file_size.strip() else None
    part_size = parse_size(args.part_size) if args.part_size.strip() else None
    if args.file_size.strip() and file_size is not None and file_size <= 0:
        print(f"[WARN] parameter check: --file-size '{args.file_size}' "
              "parsed to a non-positive value; ignored", file=sys.stderr)
        file_size = None
    if args.part_size.strip() and part_size is not None and part_size <= 0:
        print(f"[WARN] parameter check: --part-size '{args.part_size}' "
              "parsed to a non-positive value; ignored", file=sys.stderr)
        part_size = None
    concurrency = None
    if args.concurrency.strip():
        try:
            concurrency = int(args.concurrency)
        except ValueError:
            concurrency = None
        if concurrency is None or concurrency <= 0:
            print(f"[WARN] parameter check: --concurrency "
                  f"'{args.concurrency}' is not a positive integer; ignored",
                  file=sys.stderr)
            concurrency = None

    recommendation = recommend_part_params(file_size) if file_size else None
    part_validation = (validate_part_params(part_size, file_size or 0)
                       if part_size is not None else None)
    triage = triage_symptom(args.symptom)

    # Step 3: resolve the endpoint used to locate the bucket.
    user_endpoint = args.endpoint.strip().lower()
    for scheme in ("https://", "http://"):
        if user_endpoint.startswith(scheme):
            user_endpoint = user_endpoint[len(scheme):]
    user_endpoint = user_endpoint.rstrip("/")
    query_endpoint = ""
    if user_endpoint:
        query_endpoint = user_endpoint
    elif args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(
            f"query endpoint derived from --region: {query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --endpoint/--region provided)")

    report = {
        "skill": "alibabacloud-oss-multipart-upload-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "inputs": {
            "file_size_bytes": file_size,
            "file_size_human": human_size(file_size) if file_size else None,
            "part_size_bytes": part_size,
            "part_size_human": human_size(part_size) if part_size else None,
            "concurrency": concurrency,
            "prefix": args.prefix or None,
            "symptom": args.symptom or None,
            "question": question or None,
        },
        "auto_filled": auto_filled,
        "bucket_info": None,
        "parameter_check": {
            "recommendation": recommendation,
            "validation": part_validation,
            "concurrency_check": None,
        },
        "fragments": None,
        "triage": triage,
        "recommendations": [],
        "errors": [],
    }

    # Concurrency sanity (pure, cross-checked against the part count).
    if concurrency and recommendation and recommendation["strategy"] == "multipart":
        if concurrency > recommendation["part_count"]:
            report["parameter_check"]["concurrency_check"] = (
                f"concurrency {concurrency} exceeds the part count "
                f"{recommendation['part_count']}; extra workers stay idle")
        elif concurrency > 32:
            report["parameter_check"]["concurrency_check"] = (
                f"concurrency {concurrency} is very high; OSS recommends "
                "sizing concurrency to bandwidth and device load to avoid "
                "client-side congestion")

    # Step 4: locate the bucket (GetBucketInfo, ListBuckets fallback) so the
    # fragment listing hits the bucket's real region.
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
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
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): "
                  f"{e2}", file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Step 5: enumerate unfinished multipart uploads (fragments) at the
    # bucket's real endpoint. Never executes AbortMultipartUpload.
    if bucket_info and bucket_info.get("location"):
        location = bucket_info["location"]
        region = location[len("oss-"):] if location.startswith("oss-") else location
        data_endpoint = f"{location}.aliyuncs.com"
        auto_filled.append(
            f"fragment-listing endpoint derived from bucket location "
            f"{location}: {data_endpoint}")
        try:
            upload_list = _oss_client.list_multipart_uploads(
                args.bucket, data_endpoint, prefix=args.prefix)
            report["fragments"] = build_fragment_findings(upload_list)
            report["fragments"]["sample_uploads"] = upload_list["uploads"][:10]
            report["fragments"]["truncated"] = upload_list["truncated"]
        except OssClientError as e:
            print(f"[WARN] ListMultipartUploads degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
    elif not bucket_info:
        report["fragments"] = None  # cannot list without a located bucket

    # Step 6: recommendations from evidence (all manual guidance -- this
    # skill never aborts/cleans fragments itself).
    recs = []
    if part_validation and not part_validation["valid"]:
        recs.extend([f"Invalid part configuration: {err}"
                     for err in part_validation["errors"]])
    if recommendation and recommendation["strategy"] == "simple":
        recs.append(
            f"File {recommendation['part_size_human']} fits simple upload "
            "(PutObject limit 5 GB); a single PutObject avoids multipart "
            "and fragment leftovers entirely.")
    elif recommendation and recommendation["strategy"] == "multipart":
        recs.append(
            f"Recommended multipart parameters for a "
            f"{human_size(file_size)} file: part size "
            f"{human_size(recommendation['part_size_bytes'])} "
            f"x {recommendation['part_count']} parts, concurrency "
            f"{recommendation['concurrency']} (OSS limits: file <= 48.8 TB, "
            f"parts 1..10000, part 100 KB..5 GB; source: "
            f"help.aliyun.com multipart-upload doc).")
    elif recommendation and recommendation["strategy"] == "unsupported":
        recs.extend(recommendation["notes"])
    frag = report["fragments"]
    if frag and frag["count"] > 0:
        recs.append(
            f"Found {frag['count']} unfinished multipart upload(s) "
            f"(age distribution: {frag['age_distribution']}); unfinished "
            "parts are fragments that keep incurring storage fees. This "
            "skill is read-only -- follow "
            "references/fragment-cleanup-guide.md to complete or abort "
            "them yourself (AbortMultipartUpload / lifecycle "
            "AbortIncompleteMultipartUpload).")
    elif frag and frag["count"] == 0:
        recs.append(
            "No unfinished multipart uploads (fragments) found under the "
            "given prefix; a stuck upload is therefore client-side or "
            "network-side, not a server-held transfer.")
    if triage["branch"] != "unspecified":
        recs.append("Attribution checklist (" + triage["branch"] + "): "
                    + " ".join(triage["checks"][:2]))
    if not recs:
        recs.append(
            "Provide --file-size / --part-size or --symptom for parameter "
            "and attribution analysis; the fragment listing above shows the "
            "current unfinished-upload state of the bucket.")
    report["recommendations"] = recs

    # Step 7: status + next action.
    if report["fragments"] is not None and not report["errors"]:
        if frag and frag["count"] > 0:
            next_action = (
                f"{frag['count']} unfinished multipart upload(s) found "
                "(fragments incur storage fees); resume the intended "
                "upload with breakpoint resume, or clean the leftovers "
                "manually per references/fragment-cleanup-guide.md "
                "(this skill never executes AbortMultipartUpload).")
        else:
            next_action = (
                "No unfinished multipart uploads found; attribute the "
                "problem client-side or network-side using the recorded "
                "Request IDs and the triage checklist, and re-run with "
                "--file-size/--part-size for parameter sanity checks.")
        sys.exit(_emit(report, "OK", next_action, question))

    # Degraded: no fragment evidence obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the account that owns it, then "
            "re-run the diagnosis.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketInfo / "
            "oss:ListBuckets / oss:ListMultipartUploads (see "
            "references/ram-policies.md) or confirm the bucket belongs to "
            "this account, then re-run.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with the "
            "endpoint of the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host; verify DNS "
            "resolution and note internal endpoints resolve only inside "
            "the Alibaba Cloud network of that region.")
    elif cat == "credentials":
        next_action = (
            "Credential chain problem (missing env credentials or the "
            "presented AccessKey/STS token was rejected by OSS); "
            "configure/refresh the default credential chain (aliyun "
            "configure / environment variables), never pass AK/SK "
            "manually, then re-run.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors "
            "and re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action, question))


if __name__ == "__main__":
    sys.exit(main())
