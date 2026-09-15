#!/usr/bin/env python3
"""
oss_lifecycle_runtime_diagnosis.py -- OSS lifecycle runtime & archive
restore diagnosis
==============================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo / GetBucketVersioning /
GetBucketLifecycle (+ ListBuckets fallback) to the OSS control plane and
GetCallerIdentity to STS. Never mutates anything: PutBucketLifecycle is
deliberately NOT called (this skill only outputs rule templates as advice),
RestoreObject is NOT called (restore commands are emitted as user-executed
guidance only). Credentials come exclusively from the default credential
chain; AK/SK are never read, printed, or passed explicitly.

Diagnoses:
  * lifecycle rule not taking effect: rule loading window (24h + daily
    8:00 Beijing-time run), prefix/tag matching, disabled rules,
    longest-prefix conflict coverage, delete-over-transition priority,
    one-way storage-class transition ladder, versioning behavior
  * archive / cold archive restore: per-class restore tiers and duration,
    restore (retrieval) fee composition, InvalidObjectState /
    RestoreAlreadyInProgress error routing, replica validity window
  * storage tiering strategy advice (read-only suggestions; never writes)

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_lifecycle_runtime_diagnosis.py --bucket <name> \
      [--scope lifecycle|restore|strategy|all] [--object <key>] \
      [--object-class <storage-class>] [--error <error-code-or-message>] \
      [--days-since-created <N>] [--region <expected-region>]
"""

from __future__ import annotations

import argparse
import json
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def normalize_storage_class(raw: str) -> str:
    """Normalize any user-supplied storage-class wording to the canonical
    OSS value: Standard | IA | Archive | ColdArchive | DeepColdArchive | ''.
    """
    s = (raw or "").strip().lower().replace(" ", "").replace("_", "")
    if not s:
        return ""
    aliases = {
        "standard": "Standard", "std": "Standard", "标准": "Standard",
        "标准存储": "Standard",
        "ia": "IA", "infrequentaccess": "IA", "低频": "IA",
        "低频访问": "IA", "低频访问存储": "IA", "低频存储": "IA",
        "archive": "Archive", "归档": "Archive", "归档存储": "Archive",
        "coldarchive": "ColdArchive", "冷归档": "ColdArchive",
        "冷归档存储": "ColdArchive",
        "deepcoldarchive": "DeepColdArchive", "深度冷归档": "DeepColdArchive",
        "深度冷归档存储": "DeepColdArchive",
    }
    return aliases.get(s, "")


assert normalize_storage_class("Standard") == "Standard"  # normal
assert normalize_storage_class("cold archive") == "ColdArchive"  # boundary: space
assert normalize_storage_class("冷归档") == "ColdArchive"  # boundary: zh alias
assert normalize_storage_class("") == ""  # invalid: empty
assert normalize_storage_class("bogus-class") == ""  # invalid: unknown


def storage_ladder_rank(storage_class: str):
    """Cost/access-frequency rank on the one-way lifecycle ladder.

    Standard(0) -> IA(1) -> Archive(2) -> ColdArchive(3) -> DeepColdArchive(4).
    Lifecycle may ONLY move an object DOWN this ladder; there is no
    automatic upward path (measured: reverse conversion is not supported).
    Returns None for unknown classes.
    """
    rank = {"Standard": 0, "IA": 1, "Archive": 2,
            "ColdArchive": 3, "DeepColdArchive": 4}
    return rank.get(normalize_storage_class(storage_class))


assert storage_ladder_rank("Standard") == 0  # normal
assert storage_ladder_rank("DeepColdArchive") == 4  # normal: coldest
assert storage_ladder_rank("archive") == 2  # boundary: case
assert storage_ladder_rank("") is None  # invalid: empty
assert storage_ladder_rank("unknown") is None  # invalid: unknown


def transition_verdict(from_class: str, to_class: str) -> str:
    """Judge whether a lifecycle storage-class transition is legal.

    valid   -- strictly downward on the ladder
    same    -- source and target are the same class (no-op)
    invalid -- upward (one-way ladder) or either side unknown
    """
    a, b = storage_ladder_rank(from_class), storage_ladder_rank(to_class)
    if a is None or b is None:
        return "invalid"
    if a == b:
        return "same"
    return "valid" if b > a else "invalid"


assert transition_verdict("Standard", "IA") == "valid"  # normal: downward
assert transition_verdict("IA", "Archive") == "valid"  # normal: downward
assert transition_verdict("Archive", "IA") == "invalid"  # boundary: upward (one-way)
assert transition_verdict("Archive", "Archive") == "same"  # boundary: same class
assert transition_verdict("", "IA") == "invalid"  # invalid: missing source
assert transition_verdict("Standard", "") == "invalid"  # invalid: missing target


def rule_matches_key(prefix: str, key: str) -> str:
    """Decide whether a lifecycle rule prefix applies to an object key.

    matched     -- key starts with the prefix (empty prefix = whole bucket)
    not_matched -- key exists but does not start with the prefix
    unknown     -- no key supplied (cannot judge at bucket level)
    """
    p = (prefix or "").strip()
    k = (key or "").strip()
    if not k:
        return "unknown"
    return "matched" if k.startswith(p) else "not_matched"


assert rule_matches_key("logs/", "logs/a.log") == "matched"  # normal
assert rule_matches_key("", "anything.txt") == "matched"  # boundary: bucket-wide rule
assert rule_matches_key("dir1/", "dir2/x.txt") == "not_matched"  # normal: other prefix
assert rule_matches_key("logs/", "") == "unknown"  # invalid: no key


def longest_prefix_rule(rules: list, key: str):
    """Pick the single rule OSS executes for a key (longest-prefix match).

    Measured platform behavior: when several rule prefixes contain each
    other, OSS applies ONLY the longest matching prefix rule -- rules do
    not stack and execution never falls back to a shorter prefix.
    Returns the rule dict, or None when no rule matches / no key given.
    """
    k = (key or "").strip()
    if not k or not rules:
        return None
    best = None
    for r in rules:
        p = (r.get("prefix") or "").strip()
        if k.startswith(p):
            if best is None or len(p) > len((best.get("prefix") or "")):
                best = r
    return best


assert longest_prefix_rule(
    [{"id": "A", "prefix": "trace/"}, {"id": "B", "prefix": "trace/archive/"}],
    "trace/archive/f.txt")["id"] == "B"  # normal: longest prefix wins
assert longest_prefix_rule(
    [{"id": "A", "prefix": "trace/"}], "other/f.txt") is None  # normal: no match
assert longest_prefix_rule([], "x") is None  # invalid: no rules
assert longest_prefix_rule([{"id": "A", "prefix": "trace/"}], "") is None  # invalid: no key


def detect_action_conflicts(rules: list) -> list:
    """Find rule pairs sharing the same scope (identical prefix AND both
    untagged) where one deletes (expiration) and one transitions storage
    class. Measured platform rule: for the same scope the deletion action
    wins and the conflicting transition rule does NOT take effect.
    Returns a list of {"deleting_rule", "blocked_rule", "prefix"}.
    """
    conflicts = []
    scoped = [r for r in rules
              if not r.get("has_tagging") and r.get("status") == "Enabled"]
    for i, a in enumerate(scoped):
        for b in scoped[i + 1:]:
            if (a.get("prefix") or "") != (b.get("prefix") or ""):
                continue
            a_del = bool(a.get("has_expiration"))
            b_del = bool(b.get("has_expiration"))
            a_tr = bool(a.get("transitions"))
            b_tr = bool(b.get("transitions"))
            if a_del and b_tr and not b_del:
                conflicts.append({"deleting_rule": a.get("id"),
                                  "blocked_rule": b.get("id"),
                                  "prefix": a.get("prefix") or "(bucket-wide)"})
            elif b_del and a_tr and not a_del:
                conflicts.append({"deleting_rule": b.get("id"),
                                  "blocked_rule": a.get("id"),
                                  "prefix": a.get("prefix") or "(bucket-wide)"})
    return conflicts


assert detect_action_conflicts([
    {"id": "r1", "prefix": "abc", "status": "Enabled", "has_expiration": True,
     "transitions": [], "has_tagging": False},
    {"id": "r2", "prefix": "abc", "status": "Enabled", "has_expiration": False,
     "transitions": [{"days": 30, "storage_class": "IA"}], "has_tagging": False},
])[0]["blocked_rule"] == "r2"  # normal: delete beats transition on same scope
assert detect_action_conflicts([
    {"id": "r1", "prefix": "a/", "status": "Enabled", "has_expiration": True,
     "transitions": [], "has_tagging": False},
    {"id": "r2", "prefix": "b/", "status": "Enabled", "has_expiration": False,
     "transitions": [{"days": 30, "storage_class": "IA"}], "has_tagging": False},
]) == []  # boundary: different scopes never conflict
assert detect_action_conflicts([]) == []  # invalid: no rules


def parse_restore_error(err_text: str) -> dict:
    """Route a data-plane error message to the restore knowledge path.

    Returns {"kind": invalid_object_state|restore_in_progress|restore_days_
    expired|unrecognized, "message": str}. InvalidObjectState is the
    canonical error when reading an Archive/ColdArchive/DeepColdArchive
    object that is frozen or still restoring.
    """
    t = (err_text or "").strip()
    low = t.lower()
    if not t:
        return {"kind": "unrecognized", "message": ""}
    if "invalidobjectstate" in low:
        return {"kind": "invalid_object_state", "message": t}
    if "restorealreadyinprogress" in low:
        return {"kind": "restore_in_progress", "message": t}
    if "restoredays" in low or "restorehasexpired" in low or \
            "restore days" in low:
        return {"kind": "restore_days_expired", "message": t}
    return {"kind": "unrecognized", "message": t}


assert parse_restore_error("InvalidObjectState: The operation is not valid for the object's state")["kind"] == "invalid_object_state"  # normal (official ErrorMessage)
assert parse_restore_error("InvalidObjectState: The operation is not valid for the object's storage class")["kind"] == "invalid_object_state"  # robustness: legacy variant still routes correctly (parser matches ErrorCode substring only)
assert parse_restore_error("RestoreAlreadyInProgress")["kind"] == "restore_in_progress"  # normal
assert parse_restore_error("restore days expired")["kind"] == "restore_days_expired"  # boundary
assert parse_restore_error("")["kind"] == "unrecognized"  # invalid: empty
assert parse_restore_error("NoSuchKey")["kind"] == "unrecognized"  # invalid: unrelated code


def restore_profile(storage_class: str) -> dict:
    """Evidence table of restore tiers / duration / replica window per class.

    Source: help.aliyun.com OSS restore documentation (measured wording):
      Archive       -- restore ~1 minute; replica kept 1-7 days; archive
                       direct-read is an alternative (billed separately)
      ColdArchive   -- Expedited ~1h / Standard ~2-5h / Bulk ~5-12h;
                       replica 1-365 days
      DeepColdArchive -- Expedited ~12h / Standard ~48h; replica 1-365 days
      Standard/IA   -- no restore needed (real-time read; IA retrieval fee)
    """
    cls = normalize_storage_class(storage_class)
    if cls == "Archive":
        return {"class": "Archive", "restore_required": True,
                "tiers": ["restore completes in about 1 minute"],
                "replica_days_range": "1-7",
                "note": "Archive Direct Read (归档直读) can replace manual "
                        "restore for this class; it is billed separately."}
    if cls == "ColdArchive":
        return {"class": "ColdArchive", "restore_required": True,
                "tiers": ["Expedited: about 1 hour",
                          "Standard: about 2-5 hours",
                          "Bulk: about 5-12 hours"],
                "replica_days_range": "1-365",
                "note": "Restore duration is fixed by the tier, NOT by the "
                        "object size."}
    if cls == "DeepColdArchive":
        return {"class": "DeepColdArchive", "restore_required": True,
                "tiers": ["Expedited: about 12 hours",
                          "Standard: about 48 hours"],
                "replica_days_range": "1-365",
                "note": "Restoring does not change the object's storage "
                        "class; it only creates a temporary readable replica."}
    if cls in ("Standard", "IA"):
        fee = "" if cls == "Standard" else (
            "Reading IA data produces a data-retrieval fee, but no "
            "restore is needed.")
        return {"class": cls, "restore_required": False,
                "tiers": ["real-time read, no restore needed"],
                "replica_days_range": "", "note": fee}
    return {"class": cls or "Unknown", "restore_required": None,
            "tiers": [], "replica_days_range": "",
            "note": "Storage class unknown; verify the object's actual "
                    "storage class before judging restore behavior."}


assert restore_profile("Archive")["tiers"][0].startswith("restore completes")  # normal
assert len(restore_profile("ColdArchive")["tiers"]) == 3  # normal: three tiers
assert len(restore_profile("DeepColdArchive")["tiers"]) == 2  # normal: two tiers
assert restore_profile("Standard")["restore_required"] is False  # boundary: no restore
assert restore_profile("")["restore_required"] is None  # invalid: unknown class


def days_gap_verdict(days_since_created):
    """Judge the Days-policy 24h spacing requirement.

    Measured platform rule: for a Days-based lifecycle policy, the gap
    between the object's last-modified time and the daily 08:00 (Beijing
    time) execution must be at least 24 hours, otherwise the object is
    skipped in the current run and handled on the NEXT day.
    Returns "ready" | "pending_next_run" | "unknown".
    """
    if days_since_created is None:
        return "unknown"
    try:
        d = int(days_since_created)
    except (TypeError, ValueError):
        return "unknown"
    if d < 0:
        return "unknown"
    return "pending_next_run" if d < 1 else "ready"


assert days_gap_verdict(30) == "ready"  # normal
assert days_gap_verdict(0) == "pending_next_run"  # boundary: < 24h gap
assert days_gap_verdict(None) == "unknown"  # invalid: missing
assert days_gap_verdict(-5) == "unknown"  # invalid: negative


def build_lifecycle_findings(lifecycle: dict, versioning: str,
                             object_key: str, days_since_created,
                             bucket_default_class: str = "") -> list:
    """Pure attribution engine for "lifecycle rule not taking effect".

    Every finding is a {"code", "detail"} dict grounded ONLY in the fetched
    configuration; nothing is invented.
    """
    findings = []
    if not lifecycle or not lifecycle.get("configured"):
        detail = ("GetBucketLifecycle returned NoSuchLifecycle: the "
                  "bucket has NO lifecycle rule configured at all -- "
                  "nothing will ever run. If a rule was configured, it "
                  "was on a different bucket or was removed.")
        if object_key:
            detail += (f" The supplied --object '{object_key}' is echoed "
                       "here for traceability: with zero configured rules "
                       "there is no rule that can match any object key.")
        findings.append({
            "code": "no_rules_configured",
            "detail": detail,
        })
        return findings
    rules = lifecycle.get("rules", []) or []
    if not rules:
        detail = ("The lifecycle configuration exists but contains no "
                  "rules.")
        if object_key:
            detail += (f" The supplied --object '{object_key}' is echoed "
                       "here for traceability: with an empty rule set "
                       "there is no rule that can match any object key.")
        findings.append({
            "code": "empty_rule_list",
            "detail": detail,
        })
        return findings
    findings.append({
        "code": "loading_window",
        "detail": "A lifecycle rule is loaded within 24 hours after it is "
                  "created, and execution always starts at 08:00 Beijing "
                  "time daily; a rule created today cannot take effect "
                  "immediately.",
    })
    disabled = [r for r in rules if r.get("status") != "Enabled"]
    if disabled:
        findings.append({
            "code": "disabled_rules",
            "detail": "Rule(s) not in Enabled status (skipped at runtime): "
                      + ", ".join(f"{r.get('id') or '(no-id)'}[{r.get('status')}]"
                                  for r in disabled),
        })
    matching = rules
    if object_key:
        matching = [r for r in rules
                    if rule_matches_key(r.get("prefix"), object_key) == "matched"]
        unmatched = [r for r in rules
                     if rule_matches_key(r.get("prefix"), object_key) == "not_matched"]
        if unmatched:
            findings.append({
                "code": "prefix_not_matched",
                "detail": f"Object '{object_key}' does NOT match the prefix "
                          "of rule(s): "
                          + ", ".join(f"{r.get('id') or '(no-id)'}"
                                      f"(prefix={r.get('prefix')!r})"
                                      for r in unmatched)
                          + " -- a rule only touches objects whose key "
                          "starts with its exact prefix (no wildcard or "
                          "suffix matching).",
            })
        if not matching:
            findings.append({
                "code": "no_rule_matches_key",
                "detail": f"No lifecycle rule matches object '{object_key}' "
                          "by prefix; tag-matching rules additionally "
                          "require the object to carry ALL configured tags.",
            })
    best = longest_prefix_rule(matching, object_key) if object_key else None
    if best and len(matching) > 1:
        shadowed = [r for r in matching if r is not best]
        findings.append({
            "code": "longest_prefix_only",
            "detail": f"Multiple rules match '{object_key}'; OSS executes "
                      f"ONLY rule {best.get('id') or '(no-id)'} "
                      f"(longest prefix {best.get('prefix')!r}) -- rules do "
                      "not stack and shorter-prefix rules never fall back: "
                      + ", ".join(r.get('id') or '(no-id)' for r in shadowed)
                      + " are shadowed for this key.",
        })
    for conflict in detect_action_conflicts(rules):
        findings.append({
            "code": "delete_beats_transition",
            "detail": f"On scope '{conflict['prefix']}' the deletion action "
                      f"of rule {conflict['deleting_rule']} wins over the "
                      f"storage-class transition of rule "
                      f"{conflict['blocked_rule']} (deletion takes priority "
                      "over transition on the same scope).",
        })
    default_class = normalize_storage_class(bucket_default_class)
    for r in matching:
        for tr in r.get("transitions") or []:
            target = normalize_storage_class(tr.get("storage_class"))
            if not target:
                continue
            # The bucket default class is the only source class we can
            # evidence; object-level classes need the user's input, so the
            # source assumption is flagged in the finding detail.
            if not default_class:
                continue
            if transition_verdict(default_class, target) == "invalid":
                findings.append({
                    "code": "transition_upward",
                    "severity": "warn",
                    "detail": f"Rule {r.get('id') or '(no-id)'} transitions "
                              f"objects from {default_class} to {target}: "
                              "an UPWARD move on the one-way storage-class "
                              "ladder (Standard -> IA -> Archive -> "
                              "ColdArchive -> DeepColdArchive). Lifecycle "
                              "only converts downward, so this transition "
                              "cannot take effect. Evidence boundary: the "
                              "source class is assumed from the bucket "
                              "default storage class because this skill "
                              "does not query object-level classes.",
                })
    v = days_gap_verdict(days_since_created)
    if v == "pending_next_run":
        findings.append({
            "code": "days_policy_spacing",
            "detail": "The object is younger than the Days policy's 24-hour "
                      "spacing requirement (last-modified time vs 08:00 "
                      "Beijing time): it is skipped today and will be "
                      "handled on the next daily run.",
        })
    if versioning == "Enabled":
        findings.append({
            "code": "versioning_semantics",
            "detail": "Versioning is Enabled: an Expiration action on the "
                      "current version only adds a delete marker (the data "
                      "becomes a historical version, still restorable); "
                      "permanent removal requires NoncurrentVersionExpiration.",
        })
    return findings


assert any(f["code"] == "no_rules_configured" for f in
           build_lifecycle_findings({"configured": False, "rules": []},
                                    "", "", None))  # normal: no rules
# zero rules + --object supplied: the object key MUST be echoed back and
# the conclusion MUST state that no rule can match it (F-7 regression).
_f = build_lifecycle_findings({"configured": False, "rules": []},
                             "", "logs/a.log", None)
assert _f[0]["code"] == "no_rules_configured"
assert "logs/a.log" in _f[0]["detail"] and "no rule that can match" in _f[0]["detail"]
_f = build_lifecycle_findings({"configured": True, "rules": []},
                             "", "logs/a.log", None)
assert _f[0]["code"] == "empty_rule_list"
assert "logs/a.log" in _f[0]["detail"] and "no rule that can match" in _f[0]["detail"]
# boundary: zero rules WITHOUT --object keeps the original wording
_f = build_lifecycle_findings({"configured": False, "rules": []},
                             "", "", None)
assert "--object" not in _f[0]["detail"]
assert any(f["code"] == "prefix_not_matched" for f in
           build_lifecycle_findings(
               {"configured": True, "rules": [
                   {"id": "r1", "prefix": "logs/", "status": "Enabled",
                    "has_expiration": True, "expiration_days": 30,
                    "transitions": [], "has_tagging": False}]},
               "", "photos/a.jpg", None))  # normal: prefix mismatch
assert any(f["code"] == "disabled_rules" for f in
           build_lifecycle_findings(
               {"configured": True, "rules": [
                   {"id": "r1", "prefix": "", "status": "Disabled",
                    "has_expiration": True, "expiration_days": 30,
                    "transitions": [], "has_tagging": False}]},
               "", "", None))  # boundary: disabled rule
assert any(f["code"] == "delete_beats_transition" for f in
           build_lifecycle_findings(
               {"configured": True, "rules": [
                   {"id": "d", "prefix": "abc", "status": "Enabled",
                    "has_expiration": True, "expiration_days": 20,
                    "transitions": [], "has_tagging": False},
                   {"id": "t", "prefix": "abc", "status": "Enabled",
                    "has_expiration": False,
                    "transitions": [{"days": 10, "storage_class": "IA"}],
                    "has_tagging": False}]},
               "", "", None))  # normal: conflict detection
assert any(f["code"] == "versioning_semantics" for f in
           build_lifecycle_findings(
               {"configured": True, "rules": [
                   {"id": "r1", "prefix": "", "status": "Enabled",
                    "has_expiration": True, "expiration_days": 30,
                    "transitions": [], "has_tagging": False}]},
               "Enabled", "", None))  # boundary: versioned bucket
assert build_lifecycle_findings(None, "", "", None) != []  # invalid: missing evidence
assert any(f["code"] == "transition_upward" for f in
           build_lifecycle_findings(
               {"configured": True, "rules": [
                   {"id": "up", "prefix": "", "status": "Enabled",
                    "has_expiration": False, "has_tagging": False,
                    "transitions": [{"days": 30,
                                     "storage_class": "IA"}]}]},
               "", "", None, "Archive"))  # boundary: upward transition (Archive->IA) flagged
assert not any(f["code"] == "transition_upward" for f in
               build_lifecycle_findings(
                   {"configured": True, "rules": [
                       {"id": "down", "prefix": "", "status": "Enabled",
                        "has_expiration": False, "has_tagging": False,
                        "transitions": [{"days": 30,
                                         "storage_class": "Archive"}]}]},
                   "", "", None, "Standard"))  # normal: downward transition legal
assert not any(f["code"] == "transition_upward" for f in
               build_lifecycle_findings(
                   {"configured": True, "rules": [
                       {"id": "up", "prefix": "", "status": "Enabled",
                        "has_expiration": False, "has_tagging": False,
                        "transitions": [{"days": 30,
                                         "storage_class": "IA"}]}]},
                   "", "", None, ""))  # invalid: no source-class evidence -> no claim


def build_recommendations(bucket_info: dict, lifecycle: dict,
                          scope: str, object_class: str) -> list:
    """Evidence-based advice (manual guidance only; nothing is applied)."""
    recs = []
    default_class = normalize_storage_class(
        bucket_info.get("storage_class", "")) if bucket_info else ""
    if scope in ("lifecycle", "all"):
        if not lifecycle or not lifecycle.get("configured"):
            recs.append(
                "No lifecycle rule exists. Configuration template for the "
                "user to apply manually (this skill never writes rules): "
                "console Bucket -> Data Management -> Lifecycle -> Create "
                "Rule, or PutBucketLifecycle with a rule carrying Prefix, "
                "Status=Enabled, and Expiration/Transition actions. Remember "
                "the 24-hour loading window and the daily 08:00 run.")
        else:
            recs.append(
                "Do not update lifecycle rules frequently: an update can "
                "abort the same day's lifecycle task.")
    if scope in ("strategy", "all"):
        if default_class == "Standard":
            recs.append(
                "Storage tiering strategy (advice only): objects rarely "
                "re-read can move Standard -> IA (min storage 30 days, "
                "64 KB minimum metering, retrieval fee applies) -> Archive "
                "(min 60 days) -> ColdArchive / DeepColdArchive (min 180 "
                "days, restore tier required before reading). Conversion is "
                "ONE-WAY downward via lifecycle; moving back to Standard is "
                "a manual user operation (e.g. ossutil set-meta or "
                "RestoreObject replica), never automatic.")
        elif default_class in ("IA", "Archive", "ColdArchive",
                               "DeepColdArchive"):
            recs.append(
                f"The bucket default storage class is {default_class}. "
                "Note the minimum storage duration of this class: deleting "
                "or re-converting objects before it elapses still bills the "
                "'insufficient duration' capacity fee. The bucket-level "
                "storage class itself cannot be changed after creation; "
                "only object-level conversion is supported.")
    if scope in ("restore", "all") and object_class:
        prof = restore_profile(object_class)
        if prof["restore_required"]:
            recs.append(
                f"To read this {prof['class']} object the user must run a "
                "restore themselves (RestoreObject via console / SDK / "
                f"ossutil restore): choose the tier by urgency -- "
                + "; ".join(prof["tiers"])
                + f" -- and set the replica validity days "
                f"({prof['replica_days_range']} days). Every restore bills "
                "a data-retrieval fee (capacity-based) plus restore request "
                "fees for ColdArchive/DeepColdArchive; plan the validity "
                "window to avoid repeated restores. " + prof["note"])
    if not recs:
        recs.append("Configuration verified; see the findings above for "
                    "details. All suggestions are manual guidance -- this "
                    "skill applies nothing.")
    return recs


assert any("No lifecycle rule exists" in r for r in
           build_recommendations({"storage_class": "Standard"},
                                 {"configured": False, "rules": []},
                                 "all", ""))  # normal: no rules
assert any("tiering strategy" in r for r in
           build_recommendations({"storage_class": "Standard"},
                                 {"configured": True, "rules": []},
                                 "strategy", ""))  # normal: strategy
assert any("RestoreObject" in r for r in
           build_recommendations({}, None, "restore", "ColdArchive"))  # normal: restore advice
assert build_recommendations(None, None, "strategy", "") != []  # boundary: empty evidence
assert isinstance(build_recommendations(None, None, "restore", ""), list)  # invalid: no class


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
        description="Diagnose OSS lifecycle rule runtime behavior and "
                    "archive/cold-archive restore issues (read-only)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--scope", default="all",
                        choices=["lifecycle", "restore", "strategy", "all"],
                        help="Diagnosis focus (default: all)")
    parser.add_argument("--object", default="",
                        help="Object key the user cares about (optional; "
                             "used for prefix-matching attribution)")
    parser.add_argument("--object-class", default="",
                        help="The object's actual storage class if known "
                             "(Standard/IA/Archive/ColdArchive/"
                             "DeepColdArchive); drives restore advice")
    parser.add_argument("--error", default="",
                        help="Data-plane error the user hit, e.g. "
                             "InvalidObjectState (optional)")
    parser.add_argument("--days-since-created", default="",
                        help="Days since the object's last modification "
                             "(optional; checks the Days-policy spacing)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint)")
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
            "skill": "alibabacloud-oss-lifecycle-runtime-diagnosis",
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
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-lifecycle-runtime-diagnosis"),
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

    # Step 2: resolve the query endpoint.
    if args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: {query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --region provided)")

    days_arg = None
    if args.days_since_created.strip():
        try:
            days_arg = int(args.days_since_created.strip())
        except ValueError:
            days_arg = None
            auto_filled.append("--days-since-created is not an integer; "
                               "ignored (Days spacing check skipped)")

    report = {
        "skill": "alibabacloud-oss-lifecycle-runtime-diagnosis",
        "bucket": args.bucket,
        "scope": args.scope,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity; empty "
                             "means the identity pre-check degraded"},
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "versioning": None,
        "lifecycle": None,
        "findings": [],
        "restore": None,
        "recommendations": [],
        "errors": [],
    }

    # Step 3: GetBucketInfo -- the core evidence call.
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

    # Step 4: versioning + lifecycle evidence (degraded with [WARN]).
    if bucket_info:
        try:
            report["versioning"] = _oss_client.get_bucket_versioning(
                args.bucket, query_endpoint) or ""
        except OssClientError as e:
            print(f"[WARN] GetBucketVersioning degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
        try:
            report["lifecycle"] = _oss_client.get_bucket_lifecycle(
                args.bucket, query_endpoint)
        except OssClientError as e:
            print(f"[WARN] GetBucketLifecycle degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())

    # Step 5: pure-function attribution from whatever evidence exists.
    if args.scope in ("lifecycle", "all"):
        report["findings"] = build_lifecycle_findings(
            report["lifecycle"], report["versioning"] or "",
            args.object, days_arg,
            (bucket_info or {}).get("storage_class", ""))

    # Restore routing: always emit the knowledge verdict when the scope
    # covers restore (evidence: user-supplied class/error + bucket default).
    if args.scope in ("restore", "all"):
        err = parse_restore_error(args.error)
        obj_class = normalize_storage_class(args.object_class)
        if not obj_class and bucket_info:
            obj_class = normalize_storage_class(
                bucket_info.get("storage_class", ""))
            if obj_class:
                auto_filled.append(
                    f"object storage class auto-defaulted to the bucket "
                    f"default class {obj_class} (no --object-class given)")
        profile = restore_profile(obj_class)
        report["restore"] = {
            "error_kind": err["kind"],
            "error_message": err["message"] or None,
            "object_class": obj_class or None,
            "profile": profile,
        }
        if err["kind"] == "invalid_object_state":
            report["findings"].append({
                "code": "invalid_object_state",
                "detail": "InvalidObjectState means the object is in an "
                          "archive-class storage tier and is frozen (never "
                          "restored) or still restoring: it cannot be read "
                          "until a restore completes. Restore is a "
                          "user-executed operation (this skill only advises).",
            })
        elif err["kind"] == "restore_in_progress":
            report["findings"].append({
                "code": "restore_already_in_progress",
                "detail": "RestoreAlreadyInProgress: a restore request is "
                          "already running; a same-tier repeat returns 409 "
                          "Conflict. Only a HIGHER tier request can speed it "
                          "up; otherwise wait for the tier's completion "
                          "window.",
            })

    report["recommendations"] = build_recommendations(
        bucket_info, report["lifecycle"], args.scope, args.object_class)

    # Step 6: status + next action.
    if bucket_info:
        # Bucket-level evidence obtained: OK even if auxiliary calls
        # degraded (those are recorded in `errors`).
        if args.scope == "restore" and report["restore"]:
            next_action = (
                "Restore guidance emitted from the evidence table; the user "
                "must execute the restore (console/SDK/ossutil) -- pick the "
                "tier by urgency and set replica validity days to avoid "
                "repeated retrieval fees.")
        elif report["lifecycle"] is not None and \
                report["lifecycle"].get("configured") is False:
            next_action = (
                "No lifecycle rule exists on this bucket; apply the "
                "configuration template manually (console or "
                "PutBucketLifecycle), then wait for the 24-hour loading "
                "window plus the next 08:00 Beijing-time run.")
        else:
            next_action = (
                "Lifecycle configuration verified against the fetched rules; "
                "follow the findings to fix matching/coverage/wait windows; "
                "all changes are user-executed -- this skill is read-only.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded: no bucket info obtained -- attribute the root error.
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
            "oss:GetBucketLifecycle / oss:GetBucketVersioning (see "
            "references/ram-policies.md) or confirm the bucket belongs to "
            "this account, then re-run.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with the "
            "endpoint of the region where the bucket was created "
            "('must use specified endpoint').")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host: verify DNS "
            "resolution and local network, then re-run; never conclude "
            "'rule missing' from a failed call.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    elif cat == "invalid":
        next_action = (
            "The supplied bucket name is not a valid OSS bucket name; "
            "confirm the exact name with the user and re-run.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors and "
            "re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
