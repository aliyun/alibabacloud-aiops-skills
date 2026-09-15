#!/usr/bin/env python3
"""
ossfs_mount_diagnosis.py -- OSS ossfs / container-mount pre-flight diagnosis
=============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo (+ ListBuckets fallback) to
the OSS control plane and GetCallerIdentity to STS. Never mutates anything,
and NEVER executes any mount / fusermount / ossfs command -- this skill only
diagnoses and advises (the evaluation/runtime environment cannot perform a
real mount; knowledge judgment + configuration checks are the primary form).
Credentials come exclusively from the default credential chain (environment
variables for the OSS SDK, aliyun CLI default chain for STS); AK/SK are
never read, printed, or passed explicitly.

Diagnoses (pre-mount and mount-failure attribution):
  * bucket region vs. user-configured mount endpoint matching (GetBucketInfo)
  * internal vs public endpoint selection for the mount host (ECS/container)
  * archive direct-read risk: bucket storage class vs archive read 403
    (Archive objects are unreadable when mounted unless restored or the
    bucket enables archive direct read; ColdArchive/DeepColdArchive are not
    covered by archive direct read at all)
  * symptom routing (mount failed / mount directory disappeared / container
    storage-volume 403 / archive read 403) to the knowledge guidance in
    references/

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 ossfs_mount_diagnosis.py --bucket <name> \
      [--endpoint <user-configured-endpoint>] [--region <expected-region>] \
      [--symptom <symptom-or-error-text>] [--platform <ecs|ack|acs|docker|local>]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name (including dot-bearing
# endpoint-shaped strings) must degrade to the unified
# OssClientError(category="invalid") -- never a bare oss2 ClientError
# Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__ raises ClientError
# 'The bucket_name is invalid'; _build_bucket converts it, the entry records
# [WARN] + errors[] and still emits STATUS: DEGRADED with exit 0). No
# network call happens on this path.
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name
try:
    _oss_client._build_bucket("oss-cn-shenzhen.aliyuncs.com",
                              "oss-cn-hangzhou.aliyuncs.com")
    _DOTTED_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _DOTTED_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _DOTTED_BUCKET_CATEGORY = "unexpected-traceback"
assert _DOTTED_BUCKET_CATEGORY == "invalid"  # invalid: endpoint-shaped bucket name

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# Storage classes returned by GetBucketInfo (measured against oss2 2.19.x).
_ARCHIVE_CLASSES = ("Archive",)
_DEEP_ARCHIVE_CLASSES = ("ColdArchive", "DeepColdArchive")


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def normalize_endpoint(raw: str) -> str:
    """Strip scheme, surrounding whitespace, trailing slashes; lowercase."""
    ep = (raw or "").strip().lower()
    for scheme in ("https://", "http://"):
        if ep.startswith(scheme):
            ep = ep[len(scheme):]
    return ep.rstrip("/")


assert normalize_endpoint("oss-cn-hangzhou-internal.aliyuncs.com") == "oss-cn-hangzhou-internal.aliyuncs.com"  # normal
assert normalize_endpoint("https://OSS-CN-Beijing.aliyuncs.com/") == "oss-cn-beijing.aliyuncs.com"  # boundary: scheme+case+slash
assert normalize_endpoint("") == ""  # invalid: empty string
assert normalize_endpoint(None) == ""  # invalid: missing value


def classify_endpoint(endpoint: str) -> dict:
    """Classify an OSS endpoint string.

    Returns {"kind": public|internal|accelerate|invalid, "region": str|None}.
    """
    ep = normalize_endpoint(endpoint)
    if not ep:
        return {"kind": "invalid", "region": None}
    if ep in ("oss-accelerate.aliyuncs.com",
              "oss-accelerate-overseas.aliyuncs.com"):
        return {"kind": "accelerate", "region": None}
    if not ep.startswith("oss-") or not ep.endswith(".aliyuncs.com"):
        return {"kind": "invalid", "region": None}
    host = ep[len("oss-"):-len(".aliyuncs.com")]
    internal = False
    if host.endswith("-internal"):
        internal = True
        host = host[:-len("-internal")]
    parts = host.split("-")
    if not host or any(not p for p in parts) or len(parts) < 2:
        return {"kind": "invalid", "region": None}
    if not all(p.isalnum() for p in parts):
        return {"kind": "invalid", "region": None}
    if not parts[0].isalpha():
        return {"kind": "invalid", "region": None}
    return {"kind": "internal" if internal else "public", "region": host}


assert classify_endpoint("oss-cn-hangzhou.aliyuncs.com") == {"kind": "public", "region": "cn-hangzhou"}  # normal: public
assert classify_endpoint("oss-cn-hangzhou-internal.aliyuncs.com") == {"kind": "internal", "region": "cn-hangzhou"}  # normal: internal
assert classify_endpoint("HTTPS://oss-ap-southeast-1-internal.aliyuncs.com") == {"kind": "internal", "region": "ap-southeast-1"}  # boundary: scheme+case
assert classify_endpoint("") == {"kind": "invalid", "region": None}  # invalid: empty
assert classify_endpoint("example.com") == {"kind": "invalid", "region": None}  # invalid: non-OSS host


def region_from_location(location: str) -> str:
    """Convert a bucket location (e.g. 'oss-cn-hangzhou') to its region."""
    loc = (location or "").strip().lower()
    if loc.startswith("oss-"):
        return loc[len("oss-"):]
    return loc


assert region_from_location("oss-cn-hangzhou") == "cn-hangzhou"  # normal
assert region_from_location("cn-shanghai") == "cn-shanghai"  # boundary: already a region
assert region_from_location("") == ""  # invalid: empty


def match_verdict(user_region, bucket_region) -> str:
    """Compare the region of the user's mount endpoint with the bucket
    location. Returns matched | mismatch | unknown."""
    if not user_region or not bucket_region:
        return "unknown"
    return "matched" if user_region == bucket_region else "mismatch"


assert match_verdict("cn-hangzhou", "cn-hangzhou") == "matched"  # normal
assert match_verdict("cn-beijing", "cn-hangzhou") == "mismatch"  # normal: wrong region
assert match_verdict(None, "cn-hangzhou") == "unknown"  # boundary: region-less endpoint
assert match_verdict("cn-hangzhou", "") == "unknown"  # invalid: missing location


def archive_direct_read_verdict(storage_class: str) -> dict:
    """Judge archive direct-read risk from the bucket storage class.

    Official rules (help.aliyun.com/zh/oss/user-guide/archive-direct-reading):
      * Archive objects are NOT readable (GetObject -> 403/InvalidObjectState)
        unless the object is restored or the bucket enables archive direct
        read; ossfs/CSI reads of such objects surface the same 403.
      * Archive direct read covers ONLY the Archive storage class;
        ColdArchive / DeepColdArchive objects can never be read directly and
        must be restored first.
      * Other classes (Standard/IA/...) have no archive read restriction.
    GetBucketInfo exposes the storage class but NOT the archive-direct-read
    switch, so for Archive buckets the switch state is reported as
    "must be checked by the user" (console or GetBucketArchiveDirectRead).
    """
    sc = (storage_class or "").strip()
    if not sc:
        return {"status": "unknown", "at_risk": False,
                "storage_class": None,
                "note": "storage class not obtained; archive direct-read "
                        "risk cannot be judged"}
    if sc in _ARCHIVE_CLASSES:
        return {
            "status": "archive_check_required",
            "at_risk": True,
            "storage_class": sc,
            "note": "bucket storage class is Archive: reading unrestored "
                    "archive objects through a mount returns 403 "
                    "(InvalidObjectState) unless the bucket has archive "
                    "direct read enabled (or each object is restored "
                    "first). The archive-direct-read switch is NOT visible "
                    "via GetBucketInfo -- verify it in the OSS console "
                    "(Data Management > Archive Direct Read) or via "
                    "GetBucketArchiveDirectRead.",
        }
    if sc in _DEEP_ARCHIVE_CLASSES:
        return {
            "status": "archive_direct_read_not_applicable",
            "at_risk": True,
            "storage_class": sc,
            "note": f"bucket storage class is {sc}: archive direct read "
                    "covers only the Archive class; these objects must be "
                    "restored before any read, and mounting them for "
                    "on-demand reads is not a supported pattern.",
        }
    return {
        "status": "no_archive_issue",
        "at_risk": False,
        "storage_class": sc,
        "note": f"storage class is {sc}: no archive direct-read problem "
                "for this bucket; archive-read 403 does not apply.",
    }


assert archive_direct_read_verdict("Archive")["status"] == "archive_check_required"  # normal: archive at risk
assert archive_direct_read_verdict("Archive")["at_risk"] is True  # normal: risk flag
assert archive_direct_read_verdict("ColdArchive")["status"] == "archive_direct_read_not_applicable"  # boundary: deep classes not covered
assert archive_direct_read_verdict("DeepColdArchive")["at_risk"] is True  # boundary: deep cold also at risk
assert archive_direct_read_verdict("Standard") == {  # normal: non-archive bucket
    "status": "no_archive_issue", "at_risk": False, "storage_class": "Standard",
    "note": "storage class is Standard: no archive direct-read problem "
            "for this bucket; archive-read 403 does not apply."}
assert archive_direct_read_verdict("IA")["status"] == "no_archive_issue"  # boundary: IA class
assert archive_direct_read_verdict("")["status"] == "unknown"  # invalid: empty
assert archive_direct_read_verdict(None)["status"] == "unknown"  # invalid: missing


def classify_symptom(text: str) -> str:
    """Route the user's symptom description to a diagnosis category.

    Returns one of: archive_read_403 | container_403 | dir_disappeared |
    mount_failed | generic. Checked in priority order (archive first, then
    container context, then disappearance, then generic mount failure).
    """
    t = (text or "").lower()
    if not t.strip():
        return "generic"
    # The Chinese literals below are match tokens, not prose: real tickets arrive
    # in Chinese ("挂载后读取归档文件报403"), so each signature must also be
    # recognisable from its Chinese synonyms. MUST 4.1.2 constrains the language
    # of SKILL.md and references/*.md; these are matching data inside scripts/,
    # and dropping them would make the classifier deaf to Chinese wording.
    archive_sig = ("archive" in t or "归档" in t or "restore" in t
                   or "解冻" in t or "invalidobjectstate" in t)
    container_sig = any(k in t for k in (
        "k8s", "ack", "acs", "csi", "pod", "kubelet", "容器", "存储卷",
        "volume", "pv", "secret", "rrsa"))
    if archive_sig:
        return "archive_read_403"
    if container_sig and ("403" in t or "accessdenied" in t
                           or "denied" in t or "权限" in t):
        return "container_403"
    if container_sig:
        return "container_403"
    if ("transport endpoint is not connected" in t
            or "disappear" in t or "消失" in t or "不见了" in t
            or "not connected" in t):
        return "dir_disappeared"
    if any(k in t for k in ("mount", "挂载", "ossfs", "fuse")):
        return "mount_failed"
    return "generic"


assert classify_symptom("ossfs mount failed with 403 on ECS") == "mount_failed"  # normal
assert classify_symptom("reading archive object through the mount returns 403") == "archive_read_403"  # normal: archive priority
assert classify_symptom("挂载后读取归档文件报403") == "archive_read_403"  # normal: zh archive
assert classify_symptom("ACS 容器存储卷挂载 403") == "container_403"  # normal: container 403
assert classify_symptom("K8s PV mount OSS fails with AccessDenied") == "container_403"  # boundary: container without explicit 403 word
assert classify_symptom("mount directory disappeared, Transport endpoint is not connected") == "dir_disappeared"  # normal: disappeared
assert classify_symptom("挂载目录消失了") == "dir_disappeared"  # normal: zh disappeared
assert classify_symptom("") == "generic"  # invalid: empty
assert classify_symptom(None) == "generic"  # invalid: missing
assert classify_symptom("billing question about my bucket") == "generic"  # invalid: unrelated


def classify_mount_error(text: str) -> str:
    """Classify a concrete ossfs/mount error message into a cause category.

    Categories (all grounded in the official ossfs FAQ
    help.aliyun.com/zh/oss/developer-reference/ossfs-faq):
      endpoint_mismatch | preflight_permission | transport_disconnected |
      creds_file_perm | conf_syntax | empty_credential | fuse_missing |
      mountpoint_not_empty | permission_403 | unclassified
    """
    t = (text or "").lower()
    if not t.strip():
        return "unclassified"
    if "specified endpoint" in t:
        return "endpoint_mismatch"
    if "does not belong to you" in t or "不属于您" in t or "不属于你" in t:
        # The two Chinese strings are the localized variants of the same official
        # error text as seen in Chinese tickets, kept as match tokens (see the
        # note in classify_symptom: MUST 4.1.2 governs SKILL.md / references/*.md
        # prose, not the customer-wording literals this classifier matches on).
        # G3-11: official doc states this message is a client-side pre-check
        # permission failure (missing oss:ListObjects on the bucket-level
        # resource, or oss:GetBucketInfo), NOT a bucket-ownership problem.
        return "preflight_permission"
    if "transport endpoint is not connected" in t:
        return "transport_disconnected"
    if "credentials file" in t and "others permissions" in t:
        return "creds_file_perm"
    if "must be set on the commandline" in t:
        return "conf_syntax"
    if "empty credential" in t:
        return "empty_credential"
    if "device not found" in t and "fuse" in t:
        return "fuse_missing"
    if "is not empty" in t and ("mountpoint" in t or "mount" in t):
        return "mountpoint_not_empty"
    if "403" in t or "accessdenied" in t or "access denied" in t:
        return "permission_403"
    return "unclassified"


assert classify_mount_error("The bucket you are attempting to access must be addressed using the specified endpoint") == "endpoint_mismatch"  # normal
assert classify_mount_error("HTTP 403: The bucket you access does not belong to you") == "preflight_permission"  # normal (pre-check permission before generic 403)
assert classify_mount_error("The bucket you access does not belong to you") == "preflight_permission"  # normal (no HTTP prefix)
assert classify_mount_error("挂载报错：该Bucket不属于您") == "preflight_permission"  # boundary: Chinese variant
assert classify_mount_error("HTTP 403: The bucket you access does not belong to you") != "ownership"  # G3-11 regression guard: old ownership label must be gone
assert classify_mount_error("Transport endpoint is not connected") == "transport_disconnected"  # normal
assert classify_mount_error("ossfs: credentials file /etc/passwd-ossfs should not have others permissions") == "creds_file_perm"  # normal
assert classify_mount_error("--oss_bucket must be set on the commandline") == "conf_syntax"  # normal
assert classify_mount_error("empty credential") == "empty_credential"  # normal
assert classify_mount_error("fuse: device not found, try 'modprobe fuse'") == "fuse_missing"  # normal
assert classify_mount_error("Mountpoint directory /tmp/ossfs is not empty") == "mountpoint_not_empty"  # normal
assert classify_mount_error("HTTP response code 403 was returned") == "permission_403"  # boundary: generic 403
assert classify_mount_error("") == "unclassified"  # invalid: empty
assert classify_mount_error(None) == "unclassified"  # invalid: missing


def build_mount_recommendations(bucket_info, classified, verdict, archive,
                                symptom, platform) -> list:
    """Generate evidence-based pre-mount / mount-failure advice.

    Detailed knowledge lives in references/ (M1-M3); the strings below only
    surface the conclusions derivable from the collected evidence.
    """
    recs = []
    location = bucket_info.get("location", "") if bucket_info else ""
    intranet = bucket_info.get("intranet_endpoint", "") if bucket_info else ""
    extranet = bucket_info.get("extranet_endpoint", "") if bucket_info else ""
    kind = classified.get("kind", "") if classified else ""
    plat = (platform or "").lower()
    on_alibaba_cloud = plat in ("ecs", "ack", "acs", "docker", "pai",
                                "lightweight", "轻量")

    if verdict == "mismatch" and location:
        recs.append(
            f"Endpoint region mismatch: the bucket's location is {location}; "
            f"the mount endpoint must be rebuilt from it -- public: "
            f"{extranet or location + '.aliyuncs.com'}, internal: "
            f"{intranet or location + '-internal.aliyuncs.com'}. ossfs "
            "reports 'must be addressed using the specified endpoint' when "
            "the bucket and endpoint regions differ (see "
            "references/ossfs-mount-knowledge.md).")
    elif verdict == "matched" and kind == "public" and on_alibaba_cloud:
        recs.append(
            f"The mount host runs on Alibaba Cloud in the same region; use "
            f"the internal endpoint "
            f"({intranet or 'oss-<region>-internal.aliyuncs.com'}) in the "
            "ossfs / PV configuration: internal access avoids public network "
            "traffic cost and is more stable (official guidance discourages "
            "mounting through the public endpoint).")
    elif verdict == "matched" and kind == "internal" and not on_alibaba_cloud \
            and plat:
        recs.append(
            "An internal endpoint only resolves inside the Alibaba Cloud "
            "network of the bucket's region; a mount host outside the cloud "
            "gets DNS failures -- use the public endpoint there.")
    if kind == "invalid" and classified is not None:
        recs.append(
            "The provided mount endpoint is not a valid OSS endpoint. Valid "
            "forms: oss-<region>.aliyuncs.com (public), "
            "oss-<region>-internal.aliyuncs.com (internal).")

    if archive and archive.get("status") == "archive_check_required":
        recs.append(
            "Archive bucket: reading unrestored archive objects through the "
            "mount returns 403. Manual guidance: either enable archive "
            "direct read for the bucket (OSS console > Data Management > "
            "Archive Direct Read; incurs RetrievalDataArchiveDirect "
            "retrieval cost) or restore objects before reading. This skill "
            "does not change the switch (see "
            "references/archive-direct-read.md).")
    if archive and archive.get("status") == "archive_direct_read_not_applicable":
        recs.append(
            f"{archive.get('storage_class')} bucket: archive direct read "
            "only covers the Archive class; objects must be restored before "
            "any read. Mounting such a bucket for on-demand reads is not "
            "recommended (see references/archive-direct-read.md).")
    if archive and archive.get("status") == "unknown":
        recs.append(
            archive["note"] + " -- re-run after the bucket query succeeds to "
            "complete the archive direct-read check.")
    if archive and archive.get("status") == "no_archive_issue":
        recs.append(archive["note"])

    if symptom == "container_403":
        recs.append(
            "Container storage-volume 403: first separate the two "
            "authorization models -- the mount credential (Secret AK or "
            "RRSA RAM role attached to the CSI mount) decides whether the "
            "mount itself can access the bucket; a Bucket Policy grants "
            "cross-account principals and does NOT replace the mount "
            "credential's RAM permission. Then verify: credential account "
            "owns the bucket, RAM policy allows oss:GetObject/"
            "oss:ListObjects on it, endpoint region matches, and the "
            "storage class is not archive-unrestored (see "
            "references/container-volume-403.md).")
    if symptom == "dir_disappeared":
        recs.append(
            "'Transport endpoint is not connected' / disappeared mountpoint "
            "means the ossfs process has exited while the mount entry "
            "remains: manual guidance -- fusermount -u the stale mount, "
            "check OOM / dmesg and ossfs debug logs, then remount. Also "
            "verify the mountpoint directory still exists (see "
            "references/ossfs-mount-knowledge.md).")
    if symptom == "archive_read_403":
        recs.append(
            "Archive read 403 through a mount: the object's storage class "
            "and the bucket's archive-direct-read switch decide the fix -- "
            "restore the object or enable archive direct read (Archive "
            "class only); see references/archive-direct-read.md.")
    if symptom == "mount_failed":
        recs.append(
            "Mount failure pre-flight checklist: (1) credential file "
            "/etc/passwd-ossfs format '<bucket>:<AK-ID>:<AK-Secret>' with "
            "permission 640 (ossfs 1.0) or OSS_ACCESS_KEY_ID/SECRET env "
            "vars + ossfs2.conf with '--' prefixed keys (ossfs 2.0); "
            "(2) credential account owns the bucket; (3) endpoint region "
            "matches the bucket location; (4) FUSE kernel module available "
            "(containers need /dev/fuse or --privileged); (5) mountpoint "
            "exists and is empty (see "
            "references/ossfs-mount-knowledge.md).")

    if not recs and bucket_info:
        recs.append(
            "Bucket metadata verified and consistent with the provided "
            "mount configuration; if the mount still fails, collect the "
            "ossfs debug log (-o dbglevel=dbg) and route the exact error "
            "message via references/ossfs-mount-knowledge.md.")
    return recs


assert isinstance(build_mount_recommendations(
    {"location": "oss-cn-hangzhou",
     "intranet_endpoint": "oss-cn-hangzhou-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-hangzhou.aliyuncs.com"},
    classify_endpoint("oss-cn-beijing.aliyuncs.com"), "mismatch",
    archive_direct_read_verdict("Standard"), "mount_failed", "ecs"), list)  # normal
assert any("internal endpoint" in r for r in build_mount_recommendations(
    {"location": "oss-cn-hangzhou",
     "intranet_endpoint": "oss-cn-hangzhou-internal.aliyuncs.com",
     "extranet_endpoint": "oss-cn-hangzhou.aliyuncs.com"},
    classify_endpoint("oss-cn-hangzhou.aliyuncs.com"), "matched",
    archive_direct_read_verdict("Standard"), "mount_failed", "ecs"))  # normal: internal advice
assert any("archive direct read" in r for r in build_mount_recommendations(
    {"location": "oss-cn-hangzhou"}, None, "unknown",
    archive_direct_read_verdict("Archive"), "archive_read_403", "ack"))  # normal: archive advice
assert any("RAM" in r for r in build_mount_recommendations(
    {"location": "oss-cn-hangzhou"}, None, "unknown",
    archive_direct_read_verdict("Standard"), "container_403", "acs"))  # normal: container 403 advice
assert build_mount_recommendations(None, None, "unknown",
                                   archive_direct_read_verdict(""), "generic", "") != []  # boundary: empty evidence still yields the honest unknown-archive note
assert any("cannot be judged" in r for r in build_mount_recommendations(
    None, None, "unknown", archive_direct_read_verdict(""), "generic", ""))  # boundary: unknown archive note present


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Official-doc verification hook (runtime doc lookup, batch-3 integration)
# ---------------------------------------------------------------------------

_CUSTOMER_QUESTION = ""


def _doc_verification(status: str):
    """Step B: verify the customer's original wording against official OSS
    docs. Skipped when --question is absent (no-arg regression unchanged)
    or when Step A already answered (status OK) a non-consultation error
    question. Returns the constant four-key dict from _doc_lookup; never
    raises and never blocks the main diagnosis."""
    q = _CUSTOMER_QUESTION.strip()
    if not q:
        return None
    if status == "OK" and not _doc_lookup.is_consult_question(q):
        return None  # Step A hit on a pure error question
    return _doc_lookup.lookup_config_topic(q)


assert _doc_verification("OK") is None  # invalid: no --question -> unchanged
_CUSTOMER_QUESTION = "InvalidObjectState error, rule not effective"
assert _doc_verification("OK") is None  # normal: Step A hit, non-consultation
_CUSTOMER_QUESTION = "how to configure it?"
assert _doc_lookup.is_consult_question(_CUSTOMER_QUESTION) is True  # signal
_CUSTOMER_QUESTION = ""


def _emit(report: dict, status: str, next_action: str) -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines."""
    report["status"] = status
    report["next_action"] = next_action
    dv = _doc_verification(status)
    if dv is not None:
        report["doc_verification"] = dv
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose ossfs / container OSS mount problems: "
                    "pre-flight configuration check + failure attribution "
                    "(read-only, never executes any mount command)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to mount / diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--endpoint", default="",
                        help="The endpoint configured for the mount "
                             "(optional; analyzed and matched against the "
                             "bucket region)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint when --endpoint is absent)")
    parser.add_argument("--symptom", default="",
                        help="Symptom or error-message text (optional; "
                             "routed to knowledge guidance, e.g. mount "
                             "failure / disappeared mountpoint / container "
                             "403 / archive read 403)")
    parser.add_argument("--platform", default="",
                        help="Mount host platform (optional): ecs | ack | "
                             "acs | docker | pai | local")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args()

    # UA-SKILL-VERSION: resolve and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run. The
    # version is never invented, guessed or reused -- a missing or invalid
    # manifest stops the run (STATUS: FAIL, exit 1) with no cloud call made.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as _e:
        print(f"[WARN] skill version unavailable: {_e}", file=sys.stderr)
        print(json.dumps({
            "skill": "alibabacloud-oss-ossfs-mount-diagnosis",
            "status": "FAIL",
            "errors": [{"category": "invalid_arguments",
                        "code": "SkillVersionUnavailable",
                        "message": str(_e)[:200]}],
        }, ensure_ascii=False, indent=2))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix this skill's references/manifest.json (a valid "
              "`version` field is required to build the User-Agent); no cloud "
              "call was made and no conclusion can be drawn without it.")
        sys.exit(1)

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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-ossfs-mount-diagnosis"),
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
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    auto_filled = []
    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label).
    uid = _oss_client.resolve_uid()

    # Step 2: route the symptom + classify any concrete error message.
    symptom = classify_symptom(args.symptom)
    error_cause = classify_mount_error(args.symptom)

    # Step 3: resolve the endpoint used to query GetBucketInfo.
    user_endpoint = normalize_endpoint(args.endpoint)
    user_classified = classify_endpoint(user_endpoint) if user_endpoint else None
    query_endpoint = ""
    if user_endpoint and user_classified and user_classified["kind"] != "invalid":
        query_endpoint = user_endpoint
    elif args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: {query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --endpoint/--region provided)")

    report = {
        "skill": "alibabacloud-oss-ossfs-mount-diagnosis",
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "user_endpoint": user_endpoint or None,
        "query_endpoint": query_endpoint,
        "symptom_input": args.symptom or None,
        "symptom_category": symptom,
        "error_cause": error_cause if error_cause != "unclassified" else None,
        "platform": args.platform or None,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "verdict": None,
        "archive_verdict": None,
        "recommendations": [],
        "errors": [],
        "note": "read-only pre-flight diagnosis; no mount command was or "
                "will be executed by this skill",
    }

    # Step 4: GetBucketInfo -- the core evidence call.
    bucket_info = None
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
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
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): {e2}",
                  file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Re-derive the query endpoint from the bucket's real location. GetBucketInfo
    # answers on any public endpoint but reports the serving region, and the
    # ListBuckets fallback carries the same location; the region-scoped calls
    # below only succeed on that region's endpoint.
    _loc = str((bucket_info or {}).get("location") or "")
    if _loc.startswith("oss-"):
        _ep = _loc + ".aliyuncs.com"
        if _ep != query_endpoint:
            auto_filled.append(
                "query endpoint re-derived from bucket location %s: %s"
                % (_loc, _ep))
            query_endpoint = _ep
            report["query_endpoint"] = _ep

    # Identity-chain guard: identity.uid is resolved from the aliyun CLI
    # default profile while bucket evidence comes from the SDK credential
    # chain, so the two can belong to different accounts and silently
    # mislabel the scope of every conclusion below.
    _owner = str((bucket_info or {}).get("owner_id") or "")
    if _owner:
        try:
            report["identity"]["bucket_owner_uid"] = _owner
            report["identity"]["uid_matches_bucket_owner"] = (_owner == str(uid or ""))
        except Exception:
            pass
        if _owner != str(uid or ""):
            print(f"[WARN] identity consistency: caller UID {uid} (aliyun CLI "
                  f"default profile) differs from bucket owner UID {_owner} "
                  f"(resolved through the data-plane credential); findings "
                  f"reflect the data-plane account only.",
                  file=sys.stderr)

    # Step 5: verdicts from whatever evidence exists.
    bucket_location = bucket_info.get("location") if bucket_info else None
    storage_class = bucket_info.get("storage_class") if bucket_info else None
    bucket_region = region_from_location(bucket_location) if bucket_location else None
    user_region = user_classified["region"] if user_classified else None
    verdict = match_verdict(user_region, bucket_region)
    archive = archive_direct_read_verdict(storage_class)
    report["verdict"] = {
        "user_endpoint_kind": user_classified["kind"] if user_classified else None,
        "user_endpoint_region": user_region,
        "bucket_location": bucket_location,
        "bucket_region": bucket_region,
        "region_match": verdict,
    }
    report["archive_verdict"] = archive
    report["recommendations"] = build_mount_recommendations(
        bucket_info, user_classified, verdict, archive, symptom,
        args.platform)

    # Step 6: status + next action.
    if bucket_info:
        if verdict == "mismatch":
            next_action = (
                f"Fix the mount endpoint to the bucket's region "
                f"({bucket_location}) before mounting; use the internal "
                "endpoint for same-region Alibaba Cloud mount hosts.")
        elif archive.get("at_risk"):
            next_action = (
                "Bucket endpoint configuration is consistent, but the "
                f"storage class is {archive.get('storage_class')}: verify "
                "the archive-direct-read switch (or restore objects) before "
                "reading archived objects through the mount.")
        else:
            next_action = (
                "Pre-flight checks passed: bucket exists, endpoint region "
                "matches, and no archive direct-read risk was found; follow "
                "the recommendations for credential/FUSE/mountpoint "
                "configuration before mounting.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded: no bucket info obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the account that owns it -- a "
            "nonexistent bucket is itself a common ossfs mount-failure "
            "root cause. Re-run after correction.")
    elif cat == "permission":
        next_action = (
            "Access denied (403) during the pre-check: grant the caller "
            "oss:GetBucketInfo / oss:ListBuckets (see "
            "references/ram-policies.md) or confirm the bucket belongs to "
            "this account, then re-run. Note: a mount credential of a "
            "different account than the bucket owner is a classic mount "
            "403 cause.")
    elif cat == "endpoint":
        next_action = (
            "The pre-check hit the wrong region's endpoint; re-run with the "
            "endpoint of the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host: verify DNS "
            "resolution; internal endpoints resolve only inside the "
            "Alibaba Cloud network of that region.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure the "
            "default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    elif cat == "invalid":
        next_action = (
            "The supplied bucket name is invalid (bucket names are 3-63 "
            "lowercase letters/digits/hyphens, no dots); fix the spelling "
            "and re-run.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
