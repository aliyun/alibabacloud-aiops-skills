#!/usr/bin/env python3
"""
crr_config_check.py -- OSS cross-region replication (CRR) configuration check
==============================================================================
SECURITY: READ-ONLY. Only issues GetBucketReplication (+ GetBucketInfo, and
ListBuckets fallback) to the OSS control plane and GetCallerIdentity to STS.
Never creates, modifies, or deletes any replication rule. Credentials come
exclusively from the default credential chain (environment variables for the
OSS SDK, aliyun CLI default chain for STS); AK/SK are never read, printed,
or passed explicitly.

Checks (verify + advise only; write operations are left to the user):
  * whether any replication rule is configured on the source bucket
  * authorization role (sync_role) presence for the rule
  * replication scope / prefix list
  * delete-marker sync switch (action_list)
  * historical-data sync switch (the most common cause of "replication not
    starting")
  * common mis-configurations: cold/deep-cold archive objects are not
    replicable; cross-border CRR requires transfer acceleration

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 crr_config_check.py --bucket <name> \
      [--endpoint <user-configured-endpoint>] [--region <expected-region>]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

_SKILL_NAME = "alibabacloud-oss-crr-config-check"
_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"

# Region decommission / bulk-migration guidance (region-shutdown migration
# tickets 00069RRZEY / 00094R5CYX / 000EAR42K7; selection question ticket
# 000B9R1U8C). The readable version lives in references/diagnosis-tree.md.
REGION_MIGRATION_GUIDANCE = {
    "decommission_pattern": (
        "Ticket-proven pattern for a region being shut down: enable "
        "same-account cross-region replication from the source-region "
        "bucket to a destination-region bucket WITH historical-data "
        "replication enabled, then switch reads/writes after the backlog "
        "catches up. When the region is already restricted, opening the "
        "replication link may require prior approval via a support "
        "ticket (temporary enablement for migration)."),
    "selection": (
        "Continuous / near-real-time sync until cutover, or disaster "
        "recovery -> cross-region replication (rule-based, incremental). "
        "One-time bulk migration, backfill of an existing dataset, or "
        "source-side filtering -> Data Online Migration service "
        "(migration task with progress tracking). The two combine: "
        "migrate the backlog with online migration, then keep CRR running "
        "for ongoing deltas."),
    "online_migration_doc": (
        "https://help.aliyun.com/zh/data-online-migration/user-guide/"
        "migrate-data-between-oss-buckets"),
    "crr_doc": (
        "https://help.aliyun.com/zh/oss/user-guide/"
        "cross-region-replication-overview"),
}
assert REGION_MIGRATION_GUIDANCE["decommission_pattern"]  # presence guard
assert REGION_MIGRATION_GUIDANCE["selection"]
assert "migrate-data-between-oss-buckets" in \
    REGION_MIGRATION_GUIDANCE["online_migration_doc"]


# Cost-ownership conclusions (C1 / G-3). Official source:
# cross-region-replication-overview.md:64 (retrieval fee) + traffic-fees.
# Emitted verbatim in the report so the fee-attribution answer never drifts
# from the reference module.
COST_OWNERSHIP = {
    "crr_traffic_and_rtc_fee": "charged to the SOURCE account",
    "transfer_acceleration_fee": "charged to the TARGET bucket's account",
    "same_region_replication_fee": (
        "same-region replication (SRR) itself is not billed for traffic"),
    "retrieval_thaw_fee": (
        "replicating Infrequent-Access (IA) or Archive-class source objects "
        "involves NO thaw/restore and incurs NO data-retrieval capacity fee "
        "(official: cross-region-replication-overview.md '低频访问、归档"
        "类型Object复制…不涉及数据解冻操作，不收取数据取回容量费用'); "
        "Cold-Archive / Deep-Cold-Archive objects are NOT replicable at all, "
        "so they never produce a retrieval fee through replication"),
    "billing_dispute_referral": "alibabacloud-oss-billing-diagnosis",
}
assert "NO thaw" in COST_OWNERSHIP["retrieval_thaw_fee"]  # C1 presence guard
assert "SOURCE" in COST_OWNERSHIP["crr_traffic_and_rtc_fee"]


# RTC bandwidth + QPS ceilings (C3 / G-5). Official source: rtc.md:23/26/33/
# 36/40. Used as the capacity-planning basis for the "replication is slow"
# attribution branch (status=doing, no error, no blocker).
RTC_CAPACITY = {
    "bandwidth_gbps": {
        "mainland_region_pair": 10, "non_mainland_region_pair": 2,
        "single_mainland_region": 20, "single_non_mainland_region": 4,
    },
    "qps_non_sequential": {
        "mainland_region_pair": 10000, "non_mainland_region_pair": 5000,
        "single_mainland_region": 20000, "single_non_mainland_region": 10000,
    },
    "qps_sequential_write": 2000,
    "slow_replication_note": (
        "When a rule's status is 'doing' with NO error and NO delete-marker / "
        "WORM / KMS blocker, treat these bandwidth/QPS ceilings (and the "
        "sequential-write 2000 QPS cap) as the capacity-planning basis before "
        "suspecting a configuration defect; exceeding them increases "
        "replication lag. Avoid sequential prefix file names for large "
        "uploads; higher limits need a ticket."),
}
assert RTC_CAPACITY["qps_sequential_write"] == 2000  # C3 presence guard
assert RTC_CAPACITY["qps_non_sequential"]["single_mainland_region"] == 20000
assert RTC_CAPACITY["bandwidth_gbps"]["mainland_region_pair"] == 10


# Runtime-behavior semantics (C5) -- the AUTHORITATIVE single source of truth
# for how a running replication task behaves. The sibling skill
# alibabacloud-oss-cross-account-auth-diagnosis points back here (its SKILL.md
# scope boundary) instead of restating these, so the pair cannot drift.
# Official source: getbucketreplication.md Action / HistoricalObjectReplication
# / Status schema + tickets 00021R6L5D / 000BSR6M8W.
RUNTIME_SEMANTICS = {
    "continuous_until_closed": (
        "A replication task keeps running (incremental) until it is explicitly "
        "closed/deleted: objects written to the source AFTER the rule takes "
        "effect keep syncing; already-synced objects are NOT re-replicated "
        "(ticket 00021R6L5D: '关闭前新产生的文件会同步，已同步过的"
        "不重复复制')."),
    "same_name_overwrite": (
        "Replication copies by key: a source object with the same key as an "
        "existing target object OVERWRITES it (subject to versioning / WORM). "
        "There is no 'only-add-never-overwrite' replication mode; a pure "
        "additive merge needs the Data Online Migration service instead."),
    "delete_sync_action": (
        "action_list ALL (default) syncs PUT+ABORT+DELETE, so a source delete "
        "propagates to the target; action_list PUT syncs writes only, so "
        "source deletes do NOT propagate. Before deleting the source bucket "
        "after a migration, CLOSE the replication task first, otherwise a "
        "delete-sync rule can wipe the target too."),
    "historical_phase": (
        "With historical-data replication enabled the rule first copies the "
        "pre-existing backlog (status 'starting' -> 'doing'; progress via "
        "GetBucketReplicationProgress.historical_object_progress), then keeps "
        "the new-object watermark advancing. With it disabled only objects "
        "written after rule creation ever sync."),
    "status_vocabulary": {
        "starting": "task being prepared after the rule is set",
        "doing": "rule effective, data synchronizing",
        "closing": "rule deleted, OSS finishing cleanup",
    },
}
assert "OVERWRITES" in RUNTIME_SEMANTICS["same_name_overwrite"]  # C5 guard
assert "CLOSE the replication task first" in \
    RUNTIME_SEMANTICS["delete_sync_action"]
assert set(RUNTIME_SEMANTICS["status_vocabulary"]) == {
    "starting", "doing", "closing"}


# Cross-skill referrals (C7) -- script-layer edges complementing the
# references-layer edges. Each entry is ONLY a skill name + one applicability
# condition; the SKILL.md `description` is intentionally left unchanged (its
# length budget is nearly exhausted).
CROSS_SKILL_REFERRALS = [
    {"skill": "alibabacloud-oss-billing-diagnosis",
     "when": "the question is about CRR/SRR traffic, RTC or transfer-"
             "acceleration fee AMOUNTS or a billing dispute (this skill only "
             "states fee OWNERSHIP, never computes a bill)"},
    {"skill": "alibabacloud-oss-deletion-recovery-diagnosis",
     "when": "objects were deleted (possibly via a delete-sync rule) and the "
             "user wants to recover them or inspect delete markers / "
             "historical versions"},
    {"skill": "alibabacloud-oss-endpoint-internal-diagnosis",
     "when": "the failure is an endpoint / region-form or internal-network "
             "access error rather than a replication-rule configuration "
             "problem"},
    {"skill": "alibabacloud-oss-cross-account-auth-diagnosis",
     "when": "the task is to DESIGN the cross-account replication RAM role / "
             "trust policy / target-bucket policy, or attribute an AssumeRole "
             "403 (this skill only checks whether an existing rule is "
             "authorized)"},
]
assert len(CROSS_SKILL_REFERRALS) >= 3  # C7 presence guard
_ref_names = {r["skill"] for r in CROSS_SKILL_REFERRALS}
assert "alibabacloud-oss-billing-diagnosis" in _ref_names
assert "alibabacloud-oss-deletion-recovery-diagnosis" in _ref_names
assert "alibabacloud-oss-endpoint-internal-diagnosis" in _ref_names


# Chinese symptom routing table (C6 / P2-K7). The main script previously had
# ZERO Chinese routing keys, so real ticket wording ('复制不同步', '复制进度
# 不动') never reached the right branch. Each key maps to the diagnosis branch
# + a short guidance line + (optionally) a cross-skill referral. Matched
# longest-key-first so compound symptoms win over generic ones.
SYMPTOM_ROUTING = {
    "复制进度不动": {
        "branch": "progress_stuck",
        "guidance": (
            "Read GetBucketReplicationProgress: separate the historical "
            "backlog percentage from the new-object watermark. A 'doing' "
            "status with 0% historical progress usually means the backlog is "
            "still queuing or historical replication is disabled -- not a "
            "broken rule."),
    },
    "复制进度一直0%": {
        "branch": "progress_stuck",
        "guidance": "Same as '复制进度不动': verify the historical-data switch and the progress watermark.",
    },
    "目标桶没有数据": {
        "branch": "target_empty",
        "guidance": (
            "Most common causes: historical-data sync disabled (only new "
            "writes replicate), prefix scope excludes the objects, cold-"
            "archive objects not replicable, or the backlog is still copying. "
            "Verify with GetBucketReplicationProgress and a read-only source/"
            "target object count (--verify-target)."),
    },
    "复制不同步": {
        "branch": "not_syncing",
        "guidance": (
            "Check in order: rule exists? historical-data switch? prefix "
            "scope? delete-sync/action_list? cold-archive objects? "
            "authorization role trust policy?"),
    },
    "复制规则不生效": {
        "branch": "rule_not_effective",
        "guidance": (
            "A rule stuck in 'starting' is still being prepared; confirm the "
            "historical-data switch and the authorization role, then re-check."),
    },
    "复制慢": {
        "branch": "slow_replication",
        "guidance": RTC_CAPACITY["slow_replication_note"],
        "referral": None,
    },
    "复制很慢": {
        "branch": "slow_replication",
        "guidance": RTC_CAPACITY["slow_replication_note"],
    },
    "复制速度慢": {
        "branch": "slow_replication",
        "guidance": RTC_CAPACITY["slow_replication_note"],
    },
    "复制延迟": {
        "branch": "slow_replication",
        "guidance": RTC_CAPACITY["slow_replication_note"],
    },
    "复制失败": {
        "branch": "replication_failed",
        "guidance": (
            "Attribute NoPermission by the server-log: an extra STS RequestId "
            "points to the role trust policy (Principal.Service must include "
            "oss.aliyuncs.com); no STS RequestId points to a missing RAM "
            "action."),
        "referral": "alibabacloud-oss-cross-account-auth-diagnosis",
    },
    "跨账号复制授权": {
        "branch": "cross_account_auth",
        "guidance": (
            "This skill only CHECKS whether an existing rule is authorized; "
            "designing the cross-account role / trust policy / target-bucket "
            "policy belongs to the sibling skill."),
        "referral": "alibabacloud-oss-cross-account-auth-diagnosis",
    },
    "南京下线": {
        "branch": "region_decommission",
        "guidance": REGION_MIGRATION_GUIDANCE["decommission_pattern"],
        "timeliness": True,
    },
    "区域关停": {
        "branch": "region_decommission",
        "guidance": REGION_MIGRATION_GUIDANCE["decommission_pattern"],
        "timeliness": True,
    },
    "迁移到另一个地域": {
        "branch": "region_migration",
        "guidance": REGION_MIGRATION_GUIDANCE["selection"],
    },
}
assert len(SYMPTOM_ROUTING) >= 10  # C6 presence guard (详情卡 10 键)
for _k, _v in SYMPTOM_ROUTING.items():
    assert _v.get("branch") and _v.get("guidance"), f"symptom {_k} incomplete"
assert SYMPTOM_ROUTING["复制慢"]["branch"] == "slow_replication"
assert SYMPTOM_ROUTING["南京下线"].get("timeliness") is True


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


assert normalize_endpoint("oss-cn-hangzhou.aliyuncs.com") == "oss-cn-hangzhou.aliyuncs.com"  # normal
assert normalize_endpoint("https://OSS-CN-Shanghai-Internal.aliyuncs.com/") == "oss-cn-shanghai-internal.aliyuncs.com"  # boundary: scheme+case+slash
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


assert classify_endpoint("oss-cn-hangzhou.aliyuncs.com") == {"kind": "public", "region": "cn-hangzhou"}  # normal
assert classify_endpoint("oss-cn-hangzhou-internal.aliyuncs.com") == {"kind": "internal", "region": "cn-hangzhou"}  # normal: internal
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


def is_cold_archive(storage_class: str) -> bool:
    """True when the storage class is ColdArchive / DeepColdArchive.

    OSS cannot replicate ColdArchive or DeepColdArchive objects regardless of
    whether they are restored (official limit). Archive / IA / Standard are
    replicable.
    """
    sc = (storage_class or "").strip().lower()
    return sc in ("coldarchive", "deepcoldarchive")


assert is_cold_archive("ColdArchive") is True  # normal: cold archive
assert is_cold_archive("DeepColdArchive") is True  # normal: deep cold archive
assert is_cold_archive("Standard") is False  # boundary: standard
assert is_cold_archive("Archive") is False  # boundary: plain archive IS replicable
assert is_cold_archive("") is False  # invalid: unknown/empty


def delete_sync_status(action_list) -> str:
    """Derive the delete-marker sync switch from the rule's action_list.

    Returns:
      on      -- 'ALL' or 'DELETE' present (deletes are replicated)
      off     -- only write actions ('PUT'/'ABORT') without DELETE/ALL
      unknown -- empty / missing action_list (cannot determine)
    """
    actions = [str(a).strip().upper() for a in (action_list or []) if a]
    if not actions:
        return "unknown"
    if "ALL" in actions or "DELETE" in actions:
        return "on"
    return "off"


assert delete_sync_status(["ALL"]) == "on"  # normal: ALL implies delete sync
assert delete_sync_status(["PUT", "DELETE"]) == "on"  # normal: explicit DELETE
assert delete_sync_status(["PUT"]) == "off"  # boundary: writes only
assert delete_sync_status(["PUT", "ABORT"]) == "off"  # boundary: writes + abort, no delete
assert delete_sync_status([]) == "unknown"  # invalid: empty
assert delete_sync_status(None) == "unknown"  # invalid: missing


def transfer_accel_used(target_transfer_type: str) -> bool:
    """True when the rule's data link is the transfer-acceleration one."""
    return (target_transfer_type or "").strip().lower() == "oss_acc"


assert transfer_accel_used("oss_acc") is True  # normal
assert transfer_accel_used("OSS_ACC") is True  # boundary: case-insensitive
assert transfer_accel_used("") is False  # boundary: plain link
assert transfer_accel_used(None) is False  # invalid: missing


def is_cross_border(source_region: str, target_location: str) -> bool:
    """Detect a mainland-China vs non-mainland replication pair.

    Mainland regions use the cn-* prefix; everything else (ap-*, us-*, eu-*,
    me-*, ...) is non-mainland. Cross-border pairs MUST enable transfer
    acceleration per the official limit.
    """
    src = region_from_location(source_region).strip().lower()
    dst = region_from_location(target_location).strip().lower()
    if not src or not dst:
        return False
    src_mainland = src.startswith("cn-")
    dst_mainland = dst.startswith("cn-")
    return src_mainland != dst_mainland


assert is_cross_border("oss-cn-hangzhou", "oss-us-west-1") is True  # normal: mainland->overseas
assert is_cross_border("oss-cn-hangzhou", "oss-cn-shanghai") is False  # boundary: both mainland
assert is_cross_border("oss-ap-southeast-1", "oss-us-east-1") is False  # boundary: both non-mainland
assert is_cross_border("", "oss-cn-hangzhou") is False  # invalid: missing source


def historical_switch_text(flag) -> str:
    """Human-readable label for the historical-data sync switch."""
    if flag is True:
        return "enabled"
    if flag is False:
        return "disabled"
    return "unknown"


assert historical_switch_text(True) == "enabled"  # normal
assert historical_switch_text(False) == "disabled"  # normal
assert historical_switch_text(None) == "unknown"  # invalid: missing


def route_symptom(symptom_text: str) -> dict:
    """Map free-text (mostly Chinese) symptom wording to a diagnosis branch.

    Pure function. Iterates SYMPTOM_ROUTING longest-key-first so a compound
    symptom ('复制进度不动') wins over a shorter overlapping one. Returns
    {} when nothing matches (the caller then falls back to the normal
    evidence-driven flow), otherwise {matched, branch, guidance, referral?,
    timeliness?}.
    """
    text = (symptom_text or "").strip()
    if not text:
        return {}
    low = text.lower()
    for key in sorted(SYMPTOM_ROUTING, key=lambda k: (-len(k), k)):
        if key in text or key.lower() in low:
            entry = SYMPTOM_ROUTING[key]
            out = {"matched": key, "branch": entry["branch"],
                   "guidance": entry["guidance"]}
            if entry.get("referral"):
                out["referral"] = entry["referral"]
            if entry.get("timeliness"):
                out["timeliness"] = True
            return out
    return {}


assert route_symptom("复制进度不动")["branch"] == "progress_stuck"  # normal
assert route_symptom("我的复制很慢，延迟高")["branch"] == "slow_replication"  # normal
assert route_symptom("复制慢怎么办")["branch"] == "slow_replication"  # normal
assert route_symptom("复制失败，提示权限")["referral"] == \
    "alibabacloud-oss-cross-account-auth-diagnosis"  # normal: referral
assert route_symptom("南京下线了要迁移")["timeliness"] is True  # boundary: timeliness
assert route_symptom("目标桶没有数据")["branch"] == "target_empty"  # boundary
assert route_symptom("") == {}  # invalid: empty
assert route_symptom(None) == {}  # invalid: None
assert route_symptom("下载失败") == {}  # invalid: out-of-domain -> no match


def progress_summary(progress: dict) -> str:
    """Turn a GetBucketReplicationProgress dict into one attribution sentence.

    Pure function. Distinguishes the historical backlog percentage from the
    new-object watermark so 'progress stuck at 0%' is explained instead of
    guessed. Never raises; a missing/None field degrades to an honest 'not
    available' clause.
    """
    if not progress:
        return "replication progress not available (query returned nothing)"
    hist = progress.get("historical_object_progress", None)
    new_wm = (progress.get("new_object_progress") or "").strip()
    status = (progress.get("status") or "").strip() or "unknown"
    if hist is None:
        hist_txt = ("historical replication disabled or not reported "
                    "(only new writes sync)")
    else:
        try:
            hist_txt = f"historical backlog copied: {float(hist):.1f}%"
        except (TypeError, ValueError):
            hist_txt = f"historical backlog copied: {hist}"
    wm_txt = (f"new-object watermark: {new_wm} (source writes before this "
              f"time are already replicated)" if new_wm else
              "new-object watermark not published yet (historical phase "
              "still in progress)")
    return f"status={status}; {hist_txt}; {wm_txt}"


assert "50.0%" in progress_summary(
    {"status": "doing", "historical_object_progress": 50.0,
     "new_object_progress": "Thu, 24 Sep 2015 15:39:18 GMT"})  # normal
assert "disabled" in progress_summary(
    {"status": "doing", "historical_object_progress": None,
     "new_object_progress": ""})  # boundary: hist disabled
assert "not published yet" in progress_summary(
    {"status": "starting", "historical_object_progress": 0,
     "new_object_progress": ""})  # boundary: 0% no watermark
assert "not available" in progress_summary({})  # invalid: empty
assert "not available" in progress_summary(None)  # invalid: None


def compare_object_counts(source: dict, target: dict) -> dict:
    """Compare read-only ListObjectsV2 counts of the source and target side.

    Pure function (C4 post-replication verification). Returns a verdict dict:
      match            -- both counts present and equal (and neither truncated)
      mismatch         -- both present but different
      target_unreachable -- target side could not be listed (the common
                            cross-account case); verification is LIMITED
      truncated        -- either side hit the bounded-scan cap; use Inventory
    Never claims data integrity on a truncated or unreachable side.
    """
    src = source or {}
    dst = target or {}
    src_ok = isinstance(src.get("count"), int)
    dst_ok = isinstance(dst.get("count"), int)
    if src.get("truncated") or dst.get("truncated"):
        return {"verdict": "truncated",
                "detail": "a bounded scan hit its cap; the counts are partial "
                          "-- use the OSS Inventory (清单) for a large-bucket "
                          "comparison instead of this sample",
                "source_count": src.get("count"), "target_count": dst.get("count")}
    if not dst_ok:
        return {"verdict": "target_unreachable",
                "detail": "the target bucket could not be listed with this "
                          "credential (typical for a cross-account target); "
                          "verification is LIMITED to the source side -- ask "
                          "the target account to run the same read-only count "
                          "or use a cross-account Inventory",
                "source_count": src.get("count"), "target_count": None}
    if not src_ok:
        return {"verdict": "source_unreachable",
                "detail": "the source bucket could not be listed; cannot "
                          "compare",
                "source_count": None, "target_count": dst.get("count")}
    if src.get("count") == dst.get("count"):
        return {"verdict": "match",
                "detail": f"source and target object counts match "
                          f"({src.get('count')}); spot-check ETag/Size of the "
                          f"sampled keys before concluding integrity",
                "source_count": src.get("count"), "target_count": dst.get("count")}
    return {"verdict": "mismatch",
            "detail": f"source count {src.get('count')} != target count "
                      f"{dst.get('count')}; replication may be incomplete, "
                      f"still running, or scoped by prefix -- re-check "
                      f"progress and prefix scope",
            "source_count": src.get("count"), "target_count": dst.get("count")}


assert compare_object_counts({"count": 10}, {"count": 10})["verdict"] == "match"  # normal
assert compare_object_counts({"count": 10}, {"count": 7})["verdict"] == "mismatch"  # normal
assert compare_object_counts({"count": 10}, {})["verdict"] == "target_unreachable"  # boundary
assert compare_object_counts({"count": 10, "truncated": True},
                             {"count": 10})["verdict"] == "truncated"  # boundary
assert compare_object_counts({}, {})["verdict"] == "target_unreachable"  # invalid
assert compare_object_counts(None, None)["verdict"] == "target_unreachable"  # invalid


def build_findings(bucket_info: dict, replication: dict) -> list:
    """Generate evidence-based findings/recommendations from the rule fields.

    bucket_info may be a partial dict (degraded) -- every access is guarded.
    replication is {"configured": bool, "rules": [rule dict, ...]} or None.
    """
    findings = []
    storage_class = (bucket_info or {}).get("storage_class", "") if bucket_info else ""
    source_location = (bucket_info or {}).get("location", "") if bucket_info else ""

    # Bucket-level limitation: cold/deep-cold archive default storage class.
    if is_cold_archive(storage_class):
        findings.append(
            f"The bucket's default storage class is {storage_class}. OSS "
            "cannot replicate ColdArchive or DeepColdArchive objects "
            "regardless of whether they are restored (official limit) -- "
            "such objects will be skipped by any replication rule. Move the "
            "data to a replicable class (Standard / IA / Archive) if "
            "replication of those objects is required.")

    if replication is None:
        # The replication query failed outright (permission/not-found/network);
        # do NOT assert "not configured" -- only a definitive 404
        # NoSuchReplicationConfiguration may say that. Findings stop here.
        return findings
    if not replication.get("configured"):
        # Definitive: no rule configured.
        findings.append(
            "No cross-region replication rule is configured on this bucket. "
            "If data replication is intended, create a rule yourself in the "
            "OSS console (a write operation -- left to the user; this skill "
            "only checks and advises).")
        return findings

    for rule in replication.get("rules", []):
        rid = rule.get("rule_id") or "(no-id)"
        # Authorization role.
        role = rule.get("sync_role_name", "")
        if role:
            findings.append(
                f"Rule {rid} uses authorization role '{role}'. If replication "
                "fails with NoPermission, check the role's trust policy first "
                "(Principal.Service must contain oss.aliyuncs.com); see "
                "references/replication-rules.md for the trust-policy vs "
                "RAM-policy attribution method.")
        else:
            findings.append(
                f"Rule {rid} has no explicit sync role (sync_role empty). "
                "For cross-account replication or SSE-KMS encrypted objects a "
                "RAM role (e.g. AliyunOSSRole) whose trust policy allows "
                "oss.aliyuncs.com to assume it is required.")
        # Delete-marker sync switch.
        ds = delete_sync_status(rule.get("action_list"))
        if ds == "on":
            findings.append(
                f"Rule {rid}: delete sync is ON (action_list includes "
                "ALL/DELETE) -- deletes in the source are replicated to the "
                "target.")
        elif ds == "off":
            findings.append(
                f"Rule {rid}: delete sync is OFF (write-only sync) -- delete "
                "operations in the source bucket are NOT replicated to the "
                "target.")
        # Historical-data switch (most common cause of 'replication not starting').
        hist = historical_switch_text(rule.get("is_enable_historical_object_replication"))
        if hist == "disabled":
            findings.append(
                f"Rule {rid}: historical-data sync is DISABLED -- only objects "
                "written AFTER the rule was created are replicated. Pre-"
                "existing objects will never sync; this is the most common "
                "cause of 'replication not starting'. Enable 'replicate "
                "historical data' if existing objects must be copied.")
        elif hist == "enabled":
            findings.append(
                f"Rule {rid}: historical-data sync is ENABLED -- existing "
                "objects are migrated asynchronously; completion depends on "
                "data volume and may take minutes to hours.")
        # Replication scope / prefixes.
        prefixes = rule.get("prefix_list") or []
        if prefixes:
            findings.append(
                f"Rule {rid} scope is limited to prefixes: "
                f"{', '.join(prefixes)}. Objects outside these prefixes are "
                "not replicated.")
            # C2 / G-4 quota: one rule's PrefixSet accepts at most 10 Prefix
            # entries (getbucketreplication.md:13). More than 10 is an
            # impossible/malformed configuration and must be flagged.
            if len(prefixes) > 10:
                findings.append(
                    f"Rule {rid} reports {len(prefixes)} prefixes, which "
                    "EXCEEDS the official per-rule limit of 10 (PrefixSet "
                    "accepts at most 10 Prefix entries). Such a rule cannot "
                    "be created normally -- treat the value as malformed and "
                    "re-read the rule; split the scope across multiple rules "
                    "if more than 10 prefixes are truly needed.")
        else:
            findings.append(
                f"Rule {rid} scope covers the whole bucket (no prefix filter).")
        # Transfer acceleration / cross-border dependency.
        target_loc = rule.get("target_bucket_location", "")
        if is_cross_border(source_location, target_loc):
            if transfer_accel_used(rule.get("target_transfer_type")):
                findings.append(
                    f"Rule {rid} is a cross-border replication and correctly "
                    "uses transfer acceleration (oss_acc). Note the target "
                    "bucket incurs transfer-acceleration charges.")
            else:
                findings.append(
                    f"Rule {rid} appears to be a cross-border replication "
                    f"({region_from_location(source_location) or '?'} -> "
                    f"{region_from_location(target_loc) or '?'}) but transfer "
                    "acceleration is not enabled. Cross-border replication "
                    "between mainland and non-mainland China MUST enable "
                    "transfer acceleration (official limit).")
        elif transfer_accel_used(rule.get("target_transfer_type")):
            findings.append(
                f"Rule {rid} uses transfer acceleration (oss_acc) on a "
                "non-cross-border link; verify this is intentional, as the "
                "target bucket incurs transfer-acceleration charges.")
    return findings


assert isinstance(build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    None), list)  # normal: no replication object
assert any("No cross-region replication rule" in f for f in build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    {"configured": False, "rules": []}))  # normal: explicit not-configured
assert any("ColdArchive" in f or "cannot replicate" in f for f in build_findings(
    {"storage_class": "ColdArchive", "location": "oss-cn-hangzhou"},
    {"configured": False, "rules": []}))  # boundary: cold archive flag
assert any("historical-data sync is DISABLED" in f for f in build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    {"configured": True, "rules": [{
        "rule_id": "r1", "sync_role_name": "AliyunOSSRole",
        "action_list": ["PUT"], "is_enable_historical_object_replication": False,
        "prefix_list": [], "target_bucket_location": "oss-cn-shanghai",
        "target_transfer_type": ""}]}))  # normal: hist off finding
assert any("cross-border" in f for f in build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    {"configured": True, "rules": [{
        "rule_id": "r1", "sync_role_name": "AliyunOSSRole",
        "action_list": ["ALL"], "is_enable_historical_object_replication": True,
        "prefix_list": [], "target_bucket_location": "oss-us-west-1",
        "target_transfer_type": ""}]}))  # boundary: cross-border without accel
assert any("EXCEEDS the official per-rule limit of 10" in f for f in build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    {"configured": True, "rules": [{
        "rule_id": "r1", "sync_role_name": "AliyunOSSRole",
        "action_list": ["PUT"], "is_enable_historical_object_replication": True,
        "prefix_list": [f"p{i}" for i in range(11)],
        "target_bucket_location": "oss-cn-shanghai",
        "target_transfer_type": ""}]}))  # boundary: C2 >10 prefixes flagged
assert not any("EXCEEDS the official per-rule limit" in f for f in build_findings(
    {"storage_class": "Standard", "location": "oss-cn-hangzhou"},
    {"configured": True, "rules": [{
        "rule_id": "r1", "sync_role_name": "AliyunOSSRole",
        "action_list": ["PUT"], "is_enable_historical_object_replication": True,
        "prefix_list": [f"p{i}" for i in range(10)],
        "target_bucket_location": "oss-cn-shanghai",
        "target_transfer_type": ""}]}))  # boundary: exactly 10 is legal, no flag


def summarize_verdict(replication: dict) -> str:
    """Machine-consumable top-level verdict for the report."""
    if not replication:
        return "no_replication_configured"
    if not replication.get("configured"):
        return "no_replication_configured"
    rules = replication.get("rules") or []
    if not rules:
        return "no_replication_configured"
    # Any rule in 'starting' or 'closing' is worth surfacing.
    statuses = [str(r.get("status", "")).lower() for r in rules]
    if any(s == "starting" for s in statuses):
        return "replication_starting"
    if any(s == "closing" for s in statuses):
        return "replication_closing"
    return "replication_configured"


assert summarize_verdict(None) == "no_replication_configured"  # normal: none
assert summarize_verdict({"configured": False, "rules": []}) == "no_replication_configured"  # boundary
assert summarize_verdict({"configured": True, "rules": [{"status": "doing"}]}) == "replication_configured"  # normal
assert summarize_verdict({"configured": True, "rules": [{"status": "starting"}]}) == "replication_starting"  # boundary
assert summarize_verdict({"configured": True, "rules": [{"status": "closing"}]}) == "replication_closing"  # boundary


# ---------------------------------------------------------------------------
# Check orchestration
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
    # C6: when a Chinese symptom phrase was routed, lead the NEXT_ACTION with
    # the matched branch so the customer's own wording is acknowledged and the
    # guidance is branch-specific rather than generic.
    sr = report.get("symptom_routing")
    if sr:
        lead = (f"Symptom '{sr.get('matched')}' routes to branch "
                f"'{sr.get('branch')}': {sr.get('guidance')} ")
        if sr.get("referral"):
            lead += f"(defer to sibling skill {sr['referral']}) "
        if sr.get("timeliness"):
            lead += ("(region-decommission timeliness: the shutdown / "
                     "temporary-whitelist background is time-sensitive "
                     "operational knowledge, not a skill defect -- state the "
                     "migration path and its as-of date) ")
        next_action = lead + next_action
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
        description="Check OSS cross-region replication configuration "
                    "(read-only; verify + advise, never modify)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="Source OSS bucket name to check (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--endpoint", default="",
                        help="The endpoint the user currently uses to reach "
                             "the bucket (optional; used to derive the query "
                             "endpoint)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint when --endpoint is absent)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    parser.add_argument("--symptom", default="",
                        help="Customer's symptom phrase, usually Chinese "
                             "(optional); routed to a concrete diagnosis "
                             "branch (e.g. '复制进度不动', '复制慢', "
                             "'目标桶没有数据', '区域关停') and echoed in "
                             "the report's symptom_routing section")
    parser.add_argument("--verify-target", action="store_true",
                        help="Opt-in post-replication data verification "
                             "(read-only): fetch GetBucketReplicationProgress "
                             "and compare source/target object counts via "
                             "ListObjectsV2. Never writes; a cross-account "
                             "target that cannot be listed is reported as a "
                             "verification LIMIT, not an error")
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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-crr-config-check"),
            "bucket": "",
            "buckets_in_account": _hint,
            "errors": _herrs,
            "auto_filled": [],
            # C6: acknowledge the customer's own symptom wording even on the
            # missing-bucket FAIL path (the most common real-ticket shape:
            # a symptom sentence with no locatable resource). _emit prefixes
            # NEXT_ACTION with the matched branch guidance.
            "symptom_routing": route_symptom(args.symptom) if args.symptom.strip() else None,
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

    # Step 2: resolve the endpoint used to query the control plane.
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
        "skill": _SKILL_NAME,
        "bucket": args.bucket,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "replication": None,
        "verdict": None,
        "findings": [],
        "recommendations": [],
        "cost_ownership": COST_OWNERSHIP,
        "rtc_capacity": RTC_CAPACITY,
        "cross_skill_referrals": CROSS_SKILL_REFERRALS,
        "symptom_routing": route_symptom(args.symptom) if args.symptom.strip() else None,
        "errors": [],
    }

    # Step 3: GetBucketInfo -- storage class (cold-archive limit) + location.
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
                    "storage_class": "",
                    "source": "ListBuckets fallback (GetBucketInfo degraded)",
                }
                bucket_info = report["bucket_info"]
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

    # Step 4: GetBucketReplication -- the core evidence call.
    replication = None
    replication_error = None
    try:
        replication = _oss_client.get_bucket_replication(args.bucket, query_endpoint)
        report["replication"] = replication
    except OssClientError as e:
        if e.category == "no_replication":
            # NORMAL finding: replication simply not configured.
            replication = {"configured": False, "rules": []}
            report["replication"] = replication
        else:
            replication_error = e
            print(f"[WARN] GetBucketReplication degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())

    # Step 4b: post-replication evidence (C4/C5) -- only when a rule exists.
    # GetBucketReplicationProgress separates the historical backlog % from the
    # new-object watermark (the authoritative answer to "progress stuck at 0%");
    # --verify-target additionally does a bounded read-only source/target
    # object-count comparison. Both are strictly read-only and fully degradable.
    _rules = (replication or {}).get("rules", []) or []
    if _rules:
        report["runtime_semantics"] = RUNTIME_SEMANTICS
        progress_list = []
        for rule in _rules:
            rid = rule.get("rule_id") or ""
            if not rid:
                continue
            try:
                prog = _oss_client.get_bucket_replication_progress(
                    args.bucket, query_endpoint, rid)
                progress_list.append({
                    "rule_id": rid,
                    "summary": progress_summary(prog),
                    "historical_object_progress":
                        prog.get("historical_object_progress"),
                    "new_object_progress": prog.get("new_object_progress"),
                    "status": prog.get("status"),
                })
            except OssClientError as e:
                print(f"[WARN] GetBucketReplicationProgress degraded "
                      f"({e.category}) rule_id={rid}: {e}", file=sys.stderr)
                report["errors"].append(e.to_dict())
                progress_list.append({"rule_id": rid,
                                      "summary": progress_summary(None),
                                      "error": e.to_dict()})
        if progress_list:
            report["replication_progress"] = progress_list

        if args.verify_target:
            rule0 = _rules[0]
            tgt_name = rule0.get("target_bucket_name", "") or ""
            tgt_loc = rule0.get("target_bucket_location", "") or ""
            prefixes = rule0.get("prefix_list") or []
            verify_prefix = prefixes[0] if prefixes else ""
            src_count = None
            dst_count = None
            try:
                src_count = _oss_client.count_bucket_objects(
                    args.bucket, query_endpoint, prefix=verify_prefix)
            except OssClientError as e:
                print(f"[WARN] source ListObjectsV2 degraded ({e.category}): {e}",
                      file=sys.stderr)
                report["errors"].append(e.to_dict())
            if tgt_name and tgt_loc.startswith("oss-"):
                tgt_endpoint = tgt_loc + ".aliyuncs.com"
                try:
                    dst_count = _oss_client.count_bucket_objects(
                        tgt_name, tgt_endpoint, prefix=verify_prefix)
                except OssClientError as e:
                    # Cross-account targets are usually NOT listable with this
                    # credential -- that is a verification LIMIT, not a failure.
                    print(f"[WARN] target ListObjectsV2 unavailable "
                          f"({e.category}) bucket={tgt_name}: {e}",
                          file=sys.stderr)
            cmp = compare_object_counts(src_count, dst_count)
            report["target_verification"] = {
                "prefix": verify_prefix,
                "source": src_count,
                "target": dst_count,
                "comparison": cmp,
                "boundary": (
                    "This skill only provides the verification PATH; it never "
                    "promises data integrity on the user's behalf. A 'match' "
                    "on counts still needs an ETag/Size spot-check; a "
                    "truncated or unreachable side must be verified with the "
                    "OSS Inventory instead."),
            }

    # Step 5: verdict + findings from whatever evidence exists.
    # Distinguish a genuine 'no rule configured' finding (GetBucketReplication
    # returned 404 NoSuchReplicationConfiguration) from 'query failed'
    # (permission/not-found/network) -- only the former is a definitive result.
    if replication is None:
        verdict = "query_failed"
    else:
        verdict = summarize_verdict(replication)
    report["verdict"] = {
        "result": verdict,
        "bucket_location": (bucket_info or {}).get("location", "") if bucket_info else "",
        "storage_class": (bucket_info or {}).get("storage_class", "") if bucket_info else "",
        "rule_count": len((replication or {}).get("rules", []) or []),
    }
    findings = build_findings(bucket_info, replication)
    report["findings"] = findings
    report["recommendations"] = [
        "This skill only checks and advises; it never creates, modifies, or "
        "deletes replication rules. Apply any configuration change yourself "
        "in the OSS console.",
        "For NoPermission during replication setup, attribute by the "
        "server-log: an extra STS RequestId means the role trust policy must "
        "allow oss.aliyuncs.com; no STS RequestId means the RAM policy is "
        "missing the required action (see references/replication-rules.md).",
        "Fee amounts, deleted-object recovery, endpoint/region-form errors "
        "and cross-account role DESIGN are out of scope: see "
        "cross_skill_referrals for the sibling skill that owns each (this "
        "skill only states fee OWNERSHIP, never computes a bill).",
    ]

    # Step 6: status + next action.
    # The replication branch has the final say when it produced a real result.
    if replication is not None:
        if verdict == "no_replication_configured":
            # Migration intent (region decommission / bulk move) lands here:
            # surface the selection guidance alongside the setup advice.
            report["region_migration_guidance"] = REGION_MIGRATION_GUIDANCE
            next_action = (
                "No cross-region replication rule is configured on this "
                "bucket. If replication is intended (including migrating "
                "away from a decommissioned region), create a rule in the "
                "OSS console and authorize a RAM role such as "
                "AliyunOSSRole with a trust policy for oss.aliyuncs.com; "
                "for one-time bulk moves consider the Data Online Migration "
                "service instead (see region_migration_guidance); then "
                "re-run this check to verify the rule.")
        elif verdict == "replication_starting":
            next_action = (
                "A replication rule exists and is in the 'starting' state. "
                "Verify the historical-data switch and the authorization role; "
                "if it stays in 'starting', review the findings above.")
        elif verdict == "replication_closing":
            next_action = (
                "The replication rule is being closed; no new data will sync. "
                "Re-create the rule if replication is still required.")
        else:
            next_action = (
                "Replication rule found and inspected; review the findings "
                "above (delete-sync switch, historical-data switch, prefix "
                "scope, transfer-acceleration dependency) and adjust the "
                "configuration manually if needed.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded: no replication result obtained -- attribute the root error.
    root = replication_error.to_dict() if replication_error else (
        report["errors"][0] if report["errors"] else {"category": "unknown"})
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket); verify "
            "the bucket name spelling and the account that owns it, then "
            "re-run the check.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketReplication / "
            "oss:GetBucketInfo / oss:ListBuckets (see references/ram-"
            "policies.md) or confirm the bucket belongs to this account, "
            "then re-run.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with the "
            "endpoint of the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host; verify DNS "
            "resolution and network connectivity, then re-run.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure the "
            "default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    elif cat == "invalid":
        next_action = (
            "The bucket name is invalid (must be 3-63 lowercase letters, "
            "digits and hyphens); fix the name and re-run.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
