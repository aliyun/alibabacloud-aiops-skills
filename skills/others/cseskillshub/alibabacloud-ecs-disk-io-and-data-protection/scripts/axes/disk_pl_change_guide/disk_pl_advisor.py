#!/usr/bin/env python3
"""
disk_pl_advisor.py -- Single entry point for the ECS cloud disk type &
performance-level change guide
===========================================================================
SECURITY: this script never changes a cloud resource and never writes inside
an instance. Cloud access is the whitelisted query actions -- ecs
DescribeDisks / DescribeInstances / DescribeInstanceTypes / DescribeSnapshots,
cms DescribeMetricLast, sts GetCallerIdentity -- plus ecs RunCommand, used
ONLY to dispatch ONE command taken from the fixed allowlist in _constants.py,
and ONLY after the caller passed an explicit confirmation flag that must be
preceded by telling the customer what runs, on which instance, and that it
writes nothing. Anything outside that allowlist is refused and turned into a
customer-run step. No cloud resource is created, changed, deleted or billed,
and no credential is read, printed or passed explicitly (default credential
chain only).

Modes (the SKILL.md decision tree):
  --mode assess     eligibility of a type / performance-level change, the
                    capacity-derived IOPS/throughput ceilings, the snapshot
                    pre-check, and the manual (customer-run) console steps.
  --mode bottleneck three-layer attribution: per-disk ceiling vs instance
                    storage-bandwidth ceiling vs actual usage (CloudMonitor
                    datapoints or customer-pasted readings).
  --mode guest      allowlisted in-guest diagnostic: prints the announce
                    block and stops unless --confirm was given, then dispatches
                    that ONE command via Cloud Assistant and relays the output.
  --mode verify     post-change re-check of category / PL / size by query only.
  --mode faq        embedded knowledge answers -- makes NO cloud call.

Output contract: every run ends with `STATUS: OK|DEGRADED|FAIL` and a
`NEXT_ACTION:` line, in BOTH readable and --json modes. Exit codes:
  0 = OK or DEGRADED (a usable conclusion was produced)
  1 = FAIL (no usable conclusion: bad/missing input or every call failed)
  2 = argparse usage error only (a diagnosed condition never exits 2)
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import re
import sys
import time

import _cli
from _constants import (
    ALERT_GLOSSARY,
    AUTOPPL_NOTES,
    CALIBER_RULE,
    CATEGORY_NAMES,
    CHANGE_MATRIX_RULES,
    CMS_DISK_METRICS_DEFAULT,
    CMS_NAMESPACE_DEFAULT,
    CONSOLE_STEPS,
    FAQ_TOPICS,
    FIXED_PL_CATEGORY,
    GUEST_ANNOUNCE_TEMPLATE,
    GUEST_COMMAND_ALLOWLIST,
    GUEST_COMMAND_REFUSALS,
    GUEST_COMMAND_TIMEOUT,
    GUEST_DEGRADED_WORDING,
    GUEST_IO_ATTRIBUTION_COMMANDS,
    GUEST_OUTPUT_LIMIT,
    GUEST_POLL_INTERVAL,
    GUEST_POLL_MAX,
    GUEST_SHELL_TYPE,
    HEAVY_CALL_TIMEOUT,
    IMPACT_NOTES,
    INSTANCE_BANDWIDTH_RULE,
    IOSTAT_READING_RULES,
    PERF_FORMULAS,
    PL_RANK,
    REFUSE_WORDING,
    SKILL_NAME,
    VERIFICATION_NOTE,
)

# ---------------------------------------------------------------------------
# Input guards (regex-validated; a resource id is NEVER guessed)
# ---------------------------------------------------------------------------
DISK_ID_RE = re.compile(r"^d-[a-z0-9]{4,40}$")
INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{4,40}$")
REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,30}$")


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable; inline boundary asserts follow each one)
# ---------------------------------------------------------------------------

def ceiling_from_curve(curve: dict, capacity_gib: int) -> dict:
    """Evaluate one capacity curve: value = min(base + per_gib * c, cap).

    A curve with base/per_gib = None is a FIXED maximum (SSD disk): the cap
    is returned unchanged with no growth formula."""
    base, slope, cap = curve.get("base"), curve.get("per_gib"), curve.get("cap")
    if base is None or slope is None:
        value = cap
        formula = f"<= {cap}" if cap is not None else "n/a"
    else:
        grown = base + slope * capacity_gib
        value = min(grown, cap) if cap is not None else grown
        formula = (f"min({base} + {slope:g} * {capacity_gib}, {cap})"
                   if cap is not None else f"{base} + {slope:g} * {capacity_gib}")
    return {"formula": formula, "value": value,
            "provenance": curve.get("provenance", "unknown"),
            "evidence": curve.get("evidence", "")}


# boundary: the numbers reproduced in real support tickets match exactly.
_pl0 = PERF_FORMULAS["PL0"]
assert ceiling_from_curve(_pl0["iops"], 100)["value"] == 3000          # T-B525FD49
assert ceiling_from_curve(_pl0["throughput_mbps"], 100)["value"] == 125  # T-CC0FA37F
assert ceiling_from_curve(_pl0["throughput_mbps"], 200)["value"] == 150  # T-CC0FA37F
_entry = PERF_FORMULAS["cloud_essd_entry"]
assert ceiling_from_curve(_entry["iops"], 40)["value"] == 2120         # T-EE75C111
assert ceiling_from_curve(_entry["iops"], 100)["value"] == 2600        # T-DA6C3114
# boundary: fixed-maximum row (SSD disk) returns its cap, ignores capacity.
assert ceiling_from_curve(PERF_FORMULAS["cloud_ssd"]["iops"], 500)["value"] == 25000
# invalid: zero capacity still evaluates the base line, never crashes.
assert ceiling_from_curve(_pl0["iops"], 0)["value"] == 1800


def disk_ceilings(category: str, performance_level: str | None,
                  capacity_gib: int) -> list[dict]:
    """Expected IOPS / throughput ceilings for a real disk profile."""
    if category == "cloud_auto":
        return [
            {"metric": "iops",
             **ceiling_from_curve(AUTOPPL_NOTES["iops"], capacity_gib),
             "note": "AutoPL BASELINE only; read the provisioned/burst "
                     "figures from the disk's own console row"},
            {"metric": "throughput_mbps",
             **ceiling_from_curve(AUTOPPL_NOTES["throughput_mbps"], capacity_gib),
             "note": CALIBER_RULE},
        ]
    key = performance_level if category == FIXED_PL_CATEGORY else category
    profile = PERF_FORMULAS.get(key)
    if not profile:
        return []
    return [
        {"metric": "iops",
         **ceiling_from_curve(profile["iops"], capacity_gib)},
        {"metric": "throughput_mbps",
         **ceiling_from_curve(profile["throughput_mbps"], capacity_gib)},
    ]


# invalid: unknown category yields an empty ceiling list (never a guess).
assert disk_ceilings("cloud", "x", 100) == []


def normalize_category(value: str | None) -> str | None:
    if not value:
        return None
    aliases = {
        "essd": FIXED_PL_CATEGORY, "cloud_essd": FIXED_PL_CATEGORY,
        "entry": "cloud_essd_entry", "cloud_essd_entry": "cloud_essd_entry",
        "autopl": "cloud_auto", "cloud_auto": "cloud_auto",
        "efficiency": "cloud_efficiency", "ultra": "cloud_efficiency",
        "cloud_efficiency": "cloud_efficiency",
        "ssd": "cloud_ssd", "cloud_ssd": "cloud_ssd",
    }
    return aliases.get(value.strip().lower())


def judge_change(category: str | None, pl: str | None,
                 target_category: str | None, target_pl: str | None) -> dict:
    """Change-direction verdict for (category, PL) -> (target, target PL).

    Verdicts: ALLOWED_ONLINE / ALLOWED / NO_CHANGE / DENIED_ONE_WAY /
    VERIFY_OFFICIAL / NOT_APPLICABLE / UNCONSTRAINED_GUIDE. Every rule that
    is not firmly backed by a cited ticket degrades to VERIFY_OFFICIAL
    (confirm on the console / official page) rather than fabricating a yes."""
    def rule(rid: str, verdict: str, extra: str = "") -> dict:
        for r in CHANGE_MATRIX_RULES:
            if r["id"] == rid:
                note = r["note"] + ((" " + extra) if extra else "")
                return {"verdict": verdict, "rule_id": rid, "note": note}
        return {"verdict": verdict, "rule_id": rid, "note": extra}

    if category == "cloud_regional_disk_auto":
        return rule("regional-excluded", "NOT_APPLICABLE")

    tgt_cat = normalize_category(target_category)
    tgt_pl = target_pl.strip().upper() if target_pl else None

    if tgt_cat is None and tgt_pl is None:
        return {"verdict": "UNCONSTRAINED_GUIDE", "rule_id": "guide",
                "note": "no target specified: the full matrix follows; ask "
                        "the customer which direction they want"}

    # --- AutoPL is a one-way door (ticket T-B525FD49) ------------------------
    if category == "cloud_auto":
        if tgt_pl in PL_RANK:
            return rule("autopl-to-pl", "DENIED_ONE_WAY")
        if tgt_cat in (FIXED_PL_CATEGORY, "cloud_efficiency", "cloud_ssd"):
            return rule("autopl-category-change", "DENIED_ONE_WAY")
        return rule("autopl-category-change", "VERIFY_OFFICIAL")
    if tgt_cat == "cloud_auto":
        return rule("pl-to-autopl", "ALLOWED")

    # --- fixed-PL changes inside ESSD ---------------------------------------
    if category == FIXED_PL_CATEGORY and tgt_cat in (None, FIXED_PL_CATEGORY):
        if tgt_pl is None:
            return {"verdict": "VERIFY_OFFICIAL", "rule_id": "needs-target",
                    "note": "target performance level not specified"}
        if tgt_pl not in PL_RANK:
            return {"verdict": "VERIFY_OFFICIAL", "rule_id": "bad-target",
                    "note": f"'{tgt_pl}' is not a fixed ESSD PL (PL0..PL3)"}
        # An unknown or absent current PL has no rank: claiming "up" from
        # PL_RANK.get(pl, -1) would fabricate an online-capable upgrade for a
        # future tier (e.g. PL5 -> PL2 is a downgrade). Fail closed to VERIFY.
        cur_rank = PL_RANK.get(pl) if pl else None
        if cur_rank is None:
            return rule("essd-pl-down", "VERIFY_OFFICIAL",
                        extra=f"current level '{pl or '(not reported)'}' is "
                              "outside the modeled PL0..PL3 ranks, so the "
                              "direction cannot be determined")
        if PL_RANK[tgt_pl] > cur_rank:
            return rule("essd-pl-up", "ALLOWED_ONLINE")
        if PL_RANK[tgt_pl] == cur_rank:
            return {"verdict": "NO_CHANGE", "rule_id": "same",
                    "note": "target equals the current performance level"}
        return rule("essd-pl-down", "VERIFY_OFFICIAL")

    # --- category changes ----------------------------------------------------
    if category in ("cloud_efficiency", "cloud_ssd"):
        if tgt_cat == FIXED_PL_CATEGORY:
            verdict = ("ALLOWED_ONLINE"
                       if tgt_pl in (None, "PL0", "PL1", "PL2", "PL3")
                       else "VERIFY_OFFICIAL")
            return rule("efficiency-to-essd", verdict)
        return {"verdict": "VERIFY_OFFICIAL", "rule_id": "unknown-pair",
                "note": "pair not modeled; confirm on the console change page"}

    if category == "cloud_essd_entry":
        return rule("entry-to-fixed-pl", "VERIFY_OFFICIAL")

    if category == FIXED_PL_CATEGORY and tgt_cat in ("cloud_efficiency",
                                                     "cloud_ssd",
                                                     "cloud_essd_entry"):
        return rule("essd-to-efficiency", "VERIFY_OFFICIAL")

    return {"verdict": "VERIFY_OFFICIAL", "rule_id": "unknown-pair",
            "note": "pair not modeled; confirm on the console change page"}


# boundary: the two signature ticket outcomes reproduce exactly.
assert judge_change("cloud_auto", None, None, "PL0")["verdict"] == "DENIED_ONE_WAY"
assert judge_change(FIXED_PL_CATEGORY, "PL0", None, "PL1")["verdict"] == "ALLOWED_ONLINE"
assert judge_change("cloud_efficiency", None, FIXED_PL_CATEGORY, "PL0")["verdict"] == "ALLOWED_ONLINE"
assert judge_change(FIXED_PL_CATEGORY, "PL1", "cloud_auto", None)["verdict"] == "ALLOWED"
assert judge_change(FIXED_PL_CATEGORY, "PL1", None, "PL1")["verdict"] == "NO_CHANGE"
# invalid: an out-of-range target PL degrades to VERIFY, never a promise.
assert judge_change(FIXED_PL_CATEGORY, "PL1", None, "PL9")["verdict"] == "VERIFY_OFFICIAL"
# invalid: an unknown CURRENT PL (future tier / empty API field) must never be
# ranked as the floor and promised an online upgrade (phantom PL5 -> PL2 up).
assert judge_change(FIXED_PL_CATEGORY, "PL5", None, "PL2")["verdict"] == "VERIFY_OFFICIAL"
assert judge_change(FIXED_PL_CATEGORY, "", None, "PL2")["verdict"] == "VERIFY_OFFICIAL"


def bottleneck_verdict(disk_bps_ceiling, disk_iops_ceiling,
                       observed_bps_mbps, observed_iops,
                       alert_code: str | None) -> dict:
    """Three-layer attribution: INSTANCE side / DISK side / WORKLOAD side.

    The instance-side numeric ceiling lives in the official spec table (not
    in the queried API), so the ambiguous case asks for that cross-check
    instead of inventing a number."""
    if alert_code and alert_code.strip().upper() == "ECSBASEBPS":
        g = ALERT_GLOSSARY["EcsBaseBPS"]
        return {"layer": "INSTANCE", "confidence": "HIGH",
                "why": g["meaning"], "fix": g["fix"]}
    if observed_bps_mbps is not None and disk_bps_ceiling:
        if observed_bps_mbps >= 0.95 * float(disk_bps_ceiling):
            return {"layer": "DISK", "confidence": "HIGH",
                    "why": (f"observed ~{observed_bps_mbps:g} MB/s sits at "
                            f"the per-disk throughput ceiling "
                            f"({disk_bps_ceiling} MB/s)"),
                    "fix": ("raise the disk side (performance level / AutoPL "
                            "via assess mode); THEN re-check whether the "
                            "instance side becomes the new binding limit")}
    if observed_iops is not None and disk_iops_ceiling:
        if observed_iops >= 0.95 * float(disk_iops_ceiling):
            return {"layer": "DISK", "confidence": "HIGH",
                    "why": (f"observed ~{observed_iops:g} IOPS sits at the "
                            f"per-disk IOPS ceiling ({disk_iops_ceiling})"),
                    "fix": "raise the disk side via assess mode, then re-attribute"}
    if (observed_bps_mbps is not None and disk_bps_ceiling) or \
       (observed_iops is not None and disk_iops_ceiling):
        return {"layer": "INSTANCE_OR_WORKLOAD", "confidence": "MEDIUM",
                "why": ("observed usage is clearly BELOW the disk ceiling: "
                        "either the instance-type storage bandwidth binds "
                        "(check the official spec table for the family) or "
                        "the workload inside the guest is the source"),
                "fix": ("1) compare with the instance spec ceiling -> if "
                        "bound, the fix is an instance-type change (handoff "
                        "area); 2) otherwise send the customer the in-guest "
                        "self-check list and attribute from pasted readings")}
    return {"layer": "UNKNOWN", "confidence": "NONE",
            "why": "no observed readings available yet",
            "fix": ("pass --observed-bps-mbps / --observed-iops (from the "
                    "console curves or the iostat the customer pastes), or "
                    "let the CloudMonitor datapoint fetch supply raw usage")}


# boundary: the PL2-but-alerting case is INSTANCE, the saturated case is DISK.
assert bottleneck_verdict(750, 100000, 360, None, "EcsBaseBPS")["layer"] == "INSTANCE"
assert bottleneck_verdict(125, 3000, 132.86, None, None)["layer"] == "DISK"
assert bottleneck_verdict(125, 3000, 40, None, None)["layer"] == "INSTANCE_OR_WORKLOAD"
# invalid: nothing observed stays UNKNOWN, never a guess.
assert bottleneck_verdict(125, 3000, None, None, None)["layer"] == "UNKNOWN"


# Plain English function words also occur inside FAQ prose ("there", "can",
# "what"...); without filtering them a greeting like "hello there" scores a
# hit and the router serves an unrelated answer instead of degrading, so they
# never count as match evidence.
FAQ_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "will", "can", "did", "does",
    "have", "has", "not", "but", "you", "your", "this", "that", "here",
    "there", "what", "when", "where", "which", "with", "from", "into",
    "about", "after", "before", "because", "how", "why", "too", "out",
    "its", "our", "they", "them", "then", "than", "once", "over", "under",
}


def match_faq(question: str) -> list[str]:
    """Keyword-score the embedded FAQ topics against a free-text question."""
    tokens = set(re.findall(r"[a-z]{3,}", (question or "").lower()))
    tokens -= FAQ_STOPWORDS
    scored = []
    for key, topic in FAQ_TOPICS.items():
        hay = set(re.findall(
            r"[a-z]{3,}", (topic["question"] + " " + topic["answer"]).lower()))
        score = len(tokens & hay)
        if score:
            scored.append((score, key))
    scored.sort(reverse=True)
    return [key for _, key in scored[:3]]


# ---------------------------------------------------------------------------
# Report container (structured evidence + graceful degradation log)
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.errors: list[dict] = []
        self.auto_filled: dict[str, str] = {}
        self.data: dict = {}
        self.status = "OK"

    def h(self, title: str = "") -> None:
        if title:
            self.lines += ["", title, "-" * len(title)]

    def p(self, text: str = "") -> None:
        self.lines.append(text)

    def degrade(self, step: str, err: _cli.CliError) -> None:
        code = err.code or "Unknown"
        c = code.lower()
        perm = ("permission" in c or "denied" in c or "implicitdeny" in c
                or "not authorized" in c or ".ram" in c)
        entry = {
            "step": step,
            "code": code if not perm else "NoPermission",
            "category": "permission" if perm else "query",
            "message": str(err)[:300],
        }
        self.errors.append(entry)
        print(f"[WARN] {step}: {entry['code']}: {entry['message'][:200]}",
              file=sys.stderr)
        if perm:
            print("[WARN] permission gap: grant the exact missing action "
                  "listed in references/ram-policies.md (codes "
                  "NoPermission / ImplicitDeny) and retry.", file=sys.stderr)
        self.status = "DEGRADED"

    def fail(self, why: str) -> None:
        self.status = "FAIL"
        self.data["fail_reason"] = why

    def finalize(self, next_action: str, as_json: bool) -> int:
        if self.status == "FAIL":
            self.data["fail_reason"] = self.data.get(
                "fail_reason", "no usable evidence")
        if as_json:
            self.data.update({
                "status": self.status,
                "next_action": next_action,
                "auto_filled": self.auto_filled,
                "errors": self.errors,
            })
            print(json.dumps(self.data, indent=2, ensure_ascii=False))
        else:
            self.h("Summary")
            if self.status == "FAIL":
                self.p("Conclusion: " + self.data["fail_reason"])
            if self.errors:
                self.p("Graceful Degradation Log:")
                for e in self.errors:
                    self.p(f"  [WARN] {e['step']}: {e['code']} ({e['category']})")
            self.p(f"STATUS: {self.status}")
            self.p(f"NEXT_ACTION: {next_action}")
            for line in self.lines:
                print(line)
        return 1 if self.status == "FAIL" else 0


# ---------------------------------------------------------------------------
# Evidence fetchers (each degrades independently with a [WARN] trace)
# ---------------------------------------------------------------------------

def fetch_disk(rep: Report, region: str, disk_id: str) -> dict | None:
    try:
        items = _cli.paginate_next_token(
            "ecs", "DescribeDisks",
            {"RegionId": region, "DiskIds": json.dumps([disk_id])},
            items_path=["Disks", "Disk"], region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeDisks({disk_id})", e)
        return None
    for it in items:
        if str(it.get("DiskId", "")) == disk_id:
            return it
    rep.errors.append({"step": f"DescribeDisks({disk_id})",
                       "code": "InvalidDiskId.NotFound",
                       "category": "parameter",
                       "message": "disk not visible in this account/region"})
    print(f"[WARN] DescribeDisks: disk {disk_id} not found in {region} "
          f"(InvalidDiskId.NotFound)", file=sys.stderr)
    return None


def fetch_disks_of_instance(rep: Report, region: str,
                            instance_id: str) -> list[dict]:
    try:
        return _cli.paginate_next_token(
            "ecs", "DescribeDisks",
            {"RegionId": region, "InstanceId": instance_id},
            items_path=["Disks", "Disk"], region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeDisks(instance {instance_id})", e)
        return []


def fetch_instance(rep: Report, region: str,
                   instance_id: str) -> dict | None:
    try:
        items = _cli.paginate_next_token(
            "ecs", "DescribeInstances",
            {"RegionId": region, "InstanceIds": json.dumps([instance_id])},
            items_path=["Instances", "Instance"], region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeInstances({instance_id})", e)
        return None
    return items[0] if items else None


def fetch_instance_type(rep: Report, region: str,
                        instance_type: str) -> dict | None:
    try:
        # RepeatList parameter, expanded to the dotted CLI form so the
        # response is filtered server-side to the single queried type.
        items = _cli.paginate_next_token(
            "ecs", "DescribeInstanceTypes",
            {"InstanceTypes.1": instance_type},
            items_path=["InstanceTypes", "InstanceType"], region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeInstanceTypes({instance_type})", e)
        return None
    for it in items:
        if str(it.get("InstanceTypeId", "")) == instance_type:
            return it
    return items[0] if items else None


def fetch_snapshots(rep: Report, region: str, disk_id: str) -> list[dict]:
    try:
        return _cli.paginate_page_number(
            "ecs", "DescribeSnapshots",
            {"RegionId": region, "DiskId": disk_id},
            items_path=["Snapshots", "Snapshot"], region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeSnapshots({disk_id})", e)
        return []


def fetch_metric(rep: Report, region: str, namespace: str, metric: str,
                 dimensions: dict, period: int) -> list[dict]:
    try:
        body = _cli.call(
            "cms", "DescribeMetricLast",
            {"Namespace": namespace, "MetricName": metric,
             "Dimensions": [dimensions], "Period": period, "Length": 30},
            region=region)
    except _cli.CliError as e:
        rep.degrade(f"DescribeMetricLast({metric})", e)
        return []
    raw = body.get("Datapoints")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    return raw if isinstance(raw, list) else []


def datapoint_value(point: dict) -> float | None:
    for key in ("Average", "Maximum", "Value", "Sum", "Minimum"):
        raw = point.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


# ---------------------------------------------------------------------------
# Shared printers
# ---------------------------------------------------------------------------

def print_disk_table(rep: Report, disk: dict) -> None:
    rep.h("Disk inventory (DescribeDisks query)")
    for key in ("DiskId", "DiskName", "Type", "Category", "PerformanceLevel",
                "Status", "Size", "ZoneId", "InstanceId", "MultiAttach",
                "ProvisionedIops"):
        val = disk.get(key)
        if val not in (None, ""):
            rep.p(f"  {key:<18}: {val}")
    label = CATEGORY_NAMES.get(str(disk.get("Category", "")))
    if label:
        rep.p(f"  meaning           : {label}")


def print_ceilings(rep: Report, disk: dict) -> None:
    cat = str(disk.get("Category", ""))
    pl = disk.get("PerformanceLevel")
    size = int(disk.get("Size") or 0)
    rows = disk_ceilings(cat, str(pl) if pl else None, size)
    rep.h(f"Expected per-disk ceilings at {size} GiB (capacity-driven)")
    if not rows:
        rep.p("  category not modeled -- quote the official spec page "
              "instead of a number. " + VERIFICATION_NOTE)
        return
    for r in rows:
        unit = "IOPS" if r["metric"] == "iops" else "MB/s"
        rep.p(f"  {r['metric']:<16}: {r['value']} {unit}   [{r['formula']}]"
              f"  ({r['provenance']})")
        if r.get("evidence"):
            rep.p(f"      evidence     : {r['evidence']}")
        if r.get("note"):
            rep.p(f"      note         : {r['note']}")
    rep.p("  " + VERIFICATION_NOTE)


def print_matrix(rep: Report) -> None:
    rep.h("Change matrix: allowed directions & one-way rules")
    for r in CHANGE_MATRIX_RULES:
        rep.p(f"  [{r['verdict']:<16}] {r['transition']}")
        rep.p(f"      {r['note']}")


def print_impact_and_steps(rep: Report) -> None:
    rep.h("Impact statements (what the customer must know BEFORE changing)")
    for n in IMPACT_NOTES:
        rep.p(f"  - {n}")
    rep.h("Manual console steps (executed BY THE CUSTOMER, never by this skill)")
    for name, steps in CONSOLE_STEPS.items():
        rep.p(f"  {name}:")
        for s in steps:
            rep.p(f"    - {s}")


def print_snapshot_precheck(rep: Report, snaps: list[dict]) -> None:
    rep.h("Snapshot pre-check (DescribeSnapshots, existence only)")
    usable = [s for s in snaps if str(s.get("Status", "")) == "accomplished"]
    if not snaps:
        rep.p("  No snapshot found for this disk (in this account/region).")
        rep.p("  REQUIRED before any change: guide the customer to create a "
              "snapshot FIRST (see the console steps above). This skill "
              "NEVER creates snapshots itself.")
    else:
        latest = max(snaps, key=lambda s: str(s.get("CreationTime", "")))
        rep.p(f"  snapshots visible : {len(snaps)} ({len(usable)} accomplished)")
        rep.p(f"  latest            : {latest.get('SnapshotId')} "
              f"created {latest.get('CreationTime')} status {latest.get('Status')}")
        rep.p("  Pre-check passed only if a snapshot was taken AFTER the "
              "last major data write and shows status 'accomplished'.")


# ---------------------------------------------------------------------------
# Guest diagnostics helpers (allowlist resolution + Cloud Assistant readings)
# ---------------------------------------------------------------------------

GUEST_NON_TERMINAL = ("running", "pending", "invoking", "scheduled", "delayed",
                      "waiting", "saving", "queued")


def resolve_guest_command(raw: str) -> tuple[str, dict] | None:
    """Map input to an ALLOWLIST ENTRY ONLY -- by key or by exact command text.

    The returned command always comes from the embedded table; a caller- or
    customer-supplied string is never dispatched. That is what keeps arbitrary
    shell text out of RunCommand.
    """
    text = (raw or "").strip()
    if not text:
        return None
    if text in GUEST_COMMAND_ALLOWLIST:
        return text, GUEST_COMMAND_ALLOWLIST[text]
    low = text.lower()
    for key, entry in GUEST_COMMAND_ALLOWLIST.items():
        if str(entry.get("command", "")).lower() == low:
            return key, entry
    return None


# boundary: key form and exact command text both resolve to the table entry.
assert resolve_guest_command("df -h")[1]["command"] == "df -h"
assert resolve_guest_command("mount-table")[0] == "mount-table"
# invalid: anything not in the table never resolves, so it cannot be dispatched.
assert resolve_guest_command("lsblk -d -o name,rota") is None
assert resolve_guest_command("df -h && reboot") is None
assert resolve_guest_command("") is None


def invocation_records(body: dict) -> list[dict]:
    """Per-instance invocation records of a DescribeInvocations response.

    Shape: Invocations.Invocation[].InvokeInstances.InvokeInstance[]. A
    single-object (non-list) variant is accepted; missing pieces yield an
    empty list -- nothing is invented.
    """
    invs = body.get("Invocations") if isinstance(body, dict) else None
    invs = (invs.get("Invocation") if isinstance(invs, dict) else None) or []
    if isinstance(invs, dict):
        invs = [invs]
    out: list[dict] = []
    for inv in invs if isinstance(invs, list) else []:
        if not isinstance(inv, dict):
            continue
        recs = (inv.get("InvokeInstances") or {}).get("InvokeInstance")
        if isinstance(recs, dict):
            recs = [recs]
        for rec in recs if isinstance(recs, list) else []:
            if isinstance(rec, dict):
                out.append(rec)
    return out


def decode_guest_output(raw) -> str:
    """Command output comes back Base64-encoded; decode best effort.

    Truncates to GUEST_OUTPUT_LIMIT so a listing can never flood the report.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        text = base64.b64decode(text, validate=True).decode("utf-8", "replace")
    except (ValueError, TypeError):
        pass
    if len(text) > GUEST_OUTPUT_LIMIT:
        return text[:GUEST_OUTPUT_LIMIT] + "\n... [truncated by the script]"
    return text


# boundary: an encoded reading decodes; an absent one stays an empty string.
assert decode_guest_output(base64.b64encode(b"Filesystem  Size  Used").decode()) \
    == "Filesystem  Size  Used"
assert decode_guest_output(None) == ""
# invalid: non-Base64 text is echoed rather than fabricated into something else.
assert decode_guest_output("plain text already") == "plain text already"


def print_guest_checklist(rep: Report) -> None:
    rep.h("In-guest evidence: dispatchable allowlist vs customer-run steps")
    rep.p("  dispatchable through Cloud Assistant, ONE command per explicit")
    rep.p("  confirmation, only after the announce block below was relayed:")
    for key, entry in GUEST_COMMAND_ALLOWLIST.items():
        rep.p(f"    {key:<20}: {entry['command']}")
        rep.p(f"      scope: {entry['scope']}  effect: {entry['effect']}")
        rep.p(f"      why  : {entry['why']}")
    rep.p("  NEVER dispatched (not in the low-risk allowlist) -- refused with")
    rep.p("  this wording: " + REFUSE_WORDING)
    for tool, why, path in GUEST_COMMAND_REFUSALS:
        rep.p(f"    - {tool}: {why} -> {path}")
    rep.p("  customer-run command list for the refused cases (paste readings):")
    for c in GUEST_IO_ATTRIBUTION_COMMANDS:
        rep.p(f"    $ {c}")
    rep.p("  how to read iostat output:")
    for r in IOSTAT_READING_RULES:
        rep.p(f"    - {r}")


# ---------------------------------------------------------------------------
# Region resolution (never guessed for a real call)
# ---------------------------------------------------------------------------

def resolve_region(args: argparse.Namespace, rep: Report) -> str | None:
    if args.region_id:
        if not REGION_RE.match(args.region_id):
            rep.fail(f"invalid region id '{args.region_id}'")
            return None
        return args.region_id
    rep.auto_filled["region_id"] = "cn-hangzhou (default; declare this)"
    return "cn-hangzhou"


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def mode_faq(args: argparse.Namespace, rep: Report) -> int:
    rep.p("FAQ mode -- answer drawn from embedded knowledge; NO cloud "
          "resource was queried.")
    if args.list_topics:
        rep.h("Embedded FAQ topics (grounded in real support tickets)")
        for key, topic in FAQ_TOPICS.items():
            rep.p(f"  {key:<28}: {topic['question']}")
        return rep.finalize(
            "answer the question with: python3 scripts/axes/disk_pl_change_guide/disk_pl_advisor.py "
            "--mode faq --topic <key>", args.json)

    if args.topic:
        if args.topic not in FAQ_TOPICS:
            rep.fail(f"unknown FAQ topic '{args.topic}'; run --list-topics")
            return rep.finalize("pick a topic from --list-topics", args.json)
        keys = [args.topic]
    elif args.question:
        keys = match_faq(args.question)
        if not keys:
            rep.p("  no FAQ topic matched; fall back to references/, or ask "
                  "for a disk id to run assess mode.")
            return rep.finalize("collect a disk id (d-xxx) + region and "
                                "rerun with --mode assess", args.json)
    else:
        rep.fail('faq mode needs --topic <key>, --list-topics, or '
                 '--question "<customer wording>"')
        return rep.finalize("rerun with --topic / --list-topics / --question",
                            args.json)

    rep.data["faq_matches"] = keys
    for key in keys:
        topic = FAQ_TOPICS[key]
        rep.h(f"FAQ [{key}]")
        rep.p(f"  Q: {topic['question']}")
        rep.p(f"  A: {topic['answer']}")
        if topic.get("docs"):
            rep.p("  docs:")
            for d in topic["docs"]:
                rep.p(f"    - {d}")
    if len(keys) > 1:
        rep.p("  (top match first; others by relevance)")
    return rep.finalize(
        "relay the top answer with its doc links; if the customer needs "
        "their own disk checked, rerun with --mode assess --disk-id d-xxx",
        args.json)


def mode_assess(args: argparse.Namespace, rep: Report) -> int:
    region = resolve_region(args, rep)
    if not region:
        return rep.finalize("ask the customer for the region id and rerun",
                            args.json)
    rep.data["region"] = region

    if not args.disk_id and not args.instance_id:
        rep.fail("assess mode needs --disk-id d-xxx or --instance-id i-xxx")
        return rep.finalize("collect a disk or instance id and rerun", args.json)

    disk: dict | None = None
    if args.disk_id:
        if not DISK_ID_RE.match(args.disk_id):
            rep.fail(f"invalid disk id '{args.disk_id}' (expected d-xxxx)")
            return rep.finalize("fix the disk id and rerun", args.json)
        disk = fetch_disk(rep, region, args.disk_id)
    else:
        if not INSTANCE_ID_RE.match(args.instance_id):
            rep.fail(f"invalid instance id '{args.instance_id}' (expected i-xxxx)")
            return rep.finalize("fix the instance id and rerun", args.json)
        disks = fetch_disks_of_instance(rep, region, args.instance_id)
        rep.p("Instance disks (specify --disk-id for a single-disk verdict):")
        for d in disks:
            rep.p(f"  {d.get('DiskId')}  type={d.get('Type')}  "
                  f"category={d.get('Category')}  PL={d.get('PerformanceLevel')}  "
                  f"size={d.get('Size')}GiB")
        rep.data["instance_disks"] = [
            {k: d.get(k) for k in
             ("DiskId", "Type", "Category", "PerformanceLevel", "Size", "Status")}
            for d in disks]
        system = [d for d in disks if d.get("Type") == "system"]
        disk = (system or disks or [None])[0]

    if disk is None:
        rep.fail("disk not visible (deleted, other region, or account scope) "
                 "-- an empty / not-found result IS a valid conclusion")
        rep.p("NOTE: these queries see only the authorized account + "
              "region; ask the customer to confirm both. Do NOT invent data.")
        return rep.finalize("confirm account + region with the customer, "
                            "then rerun", args.json)

    rep.data["disk"] = disk
    print_disk_table(rep, disk)
    print_ceilings(rep, disk)

    verdict = judge_change(str(disk.get("Category", "")),
                           str(disk.get("PerformanceLevel") or ""),
                           args.target_category, args.target_performance_level)
    rep.data["verdict"] = verdict
    rep.h("Change eligibility verdict")
    rep.p(f"  verdict : {verdict['verdict']}")
    rep.p(f"  rule    : {verdict['rule_id']}")
    rep.p(f"  note    : {verdict['note']}")
    if not (args.target_category or args.target_performance_level):
        print_matrix(rep)

    disk_id = str(disk.get("DiskId", ""))
    snaps = fetch_snapshots(rep, region, disk_id)
    rep.data["snapshots_visible"] = len(snaps)
    print_snapshot_precheck(rep, snaps)
    print_impact_and_steps(rep)

    if verdict["verdict"] in ("ALLOWED", "ALLOWED_ONLINE"):
        action = ("guide the customer: snapshot first if the pre-check is "
                  "empty, perform the change in the ECS console (manual "
                  "steps above), then re-verify with --mode verify")
    elif verdict["verdict"] == "VERIFY_OFFICIAL":
        action = ("do NOT promise the transition: confirm the exact "
                  "source/target pair on the console change page / official "
                  "doc before instructing the customer")
    elif verdict["verdict"] == "DENIED_ONE_WAY":
        action = ("state the one-way rule WITH its ticket-cited wording; "
                  "do not open the change path; consider the AutoPL FAQ")
    else:
        action = "relay the matrix and ask the customer which direction they want"
    return rep.finalize(action, args.json)


def mode_bottleneck(args: argparse.Namespace, rep: Report) -> int:
    region = resolve_region(args, rep)
    if not region:
        return rep.finalize("ask the customer for the region id and rerun", args.json)
    if not args.disk_id:
        rep.fail("bottleneck mode needs --disk-id d-xxx (the disk to attribute)")
        return rep.finalize("collect the disk id and rerun", args.json)
    if not DISK_ID_RE.match(args.disk_id):
        rep.fail(f"invalid disk id '{args.disk_id}'")
        return rep.finalize("fix the disk id and rerun", args.json)

    disk = fetch_disk(rep, region, args.disk_id)
    if disk is None:
        rep.fail("disk not visible in this account/region")
        return rep.finalize("confirm account + region with the customer", args.json)

    rep.data["region"] = region
    rep.data["disk"] = disk
    print_disk_table(rep, disk)
    print_ceilings(rep, disk)

    rows = disk_ceilings(str(disk.get("Category", "")),
                         str(disk.get("PerformanceLevel") or ""),
                         int(disk.get("Size") or 0))
    bps_cap = next((r["value"] for r in rows if r["metric"] == "throughput_mbps"), None)
    iops_cap = next((r["value"] for r in rows if r["metric"] == "iops"), None)

    # --- instance layer ------------------------------------------------------
    instance_id = str(disk.get("InstanceId") or args.instance_id or "")
    if instance_id and INSTANCE_ID_RE.match(instance_id):
        inst = fetch_instance(rep, region, instance_id)
        if inst:
            itype = str(inst.get("InstanceType", ""))
            rep.data["instance"] = {"instance_id": instance_id,
                                    "instance_type": itype,
                                    "status": inst.get("Status")}
            rep.h("Instance side (min(instance ceiling, disk ceiling) rule)")
            rep.p(f"  {instance_id}  type: {itype}  status: {inst.get('Status')}")
            spec = fetch_instance_type(rep, region, itype) if itype else None
            if spec:
                rep.data["instance_type_info"] = {
                    k: spec.get(k) for k in
                    ("InstanceTypeId", "InstanceTypeFamily", "CpuCoreCount",
                     "MemorySize", "LocalStorageCategory")}
                rep.p(f"  family: {spec.get('InstanceTypeFamily')}  "
                      f"cpu: {spec.get('CpuCoreCount')}  "
                      f"mem: {spec.get('MemorySize')} GiB")
                if "u1" in str(spec.get("InstanceTypeFamily", "")):
                    rep.p("  hint    : u1-family instances often sit at a few "
                          "Gbit/s storage bandwidth (3 Gbit/s = 375 MB/s) -- "
                          "the classic 'PL2 but still alerting' cause "
                          "(ticket T-39B4EB79).")
            rep.p("  rule   : " + INSTANCE_BANDWIDTH_RULE["rule"])
            rep.p("  example: " + INSTANCE_BANDWIDTH_RULE["example"])
            rep.p("  look up the storage-bandwidth / IOPS row of THIS "
                  "instance type in the official spec table "
                  "(https://help.aliyun.com/zh/ecs/user-guide/"
                  "overview-of-instance-families#u1) -- it is NOT exposed by "
                  "the queried API, so do NOT guess it.")
    else:
        rep.h("Instance side")
        rep.p("  disk is not attached to a visible instance; the instance "
              "layer cannot be evaluated (an unmounted disk still has its "
              "own ceiling).")

    # --- alert code ----------------------------------------------------------
    if args.alert_code:
        code = args.alert_code.strip()
        rep.data["alert_code"] = code
        g = ALERT_GLOSSARY.get(code) or ALERT_GLOSSARY.get(code.upper())
        if g:
            rep.p(f"\n  alert {code}: {g['meaning']}  Fix: {g['fix']}  "
                  f"[{g['evidence']}]")

    # --- actual usage --------------------------------------------------------
    obs_bps, obs_iops = args.observed_bps_mbps, args.observed_iops
    if (obs_bps is None and obs_iops is None and not args.no_metrics
            and instance_id and INSTANCE_ID_RE.match(instance_id)):
        rep.h("Actual usage (CloudMonitor DescribeMetricLast, latest window)")
        dims = {"instanceId": instance_id, "diskId": args.disk_id}
        metrics: dict[str, list] = {}
        for metric in (args.cms_metric or CMS_DISK_METRICS_DEFAULT):
            pts = fetch_metric(rep, region,
                               args.cms_namespace or CMS_NAMESPACE_DEFAULT,
                               metric, dims, args.cms_period)
            vals = [v for p in pts if (v := datapoint_value(p)) is not None]
            if vals:
                rep.p(f"  {metric:<16}: max {max(vals):,.0f}  last {vals[-1]:,.0f}")
            else:
                rep.p(f"  {metric:<16}: no datapoints returned")
            metrics[metric] = pts[:20]
        rep.p("  unit note: trust the console chart for the metric unit; to "
              "get a deterministic verdict feed --observed-bps-mbps in MB/s. "
              "This API returns LATEST datapoints only; historical curves "
              "stay in the CloudMonitor console.")
        rep.data["metrics"] = metrics
    elif obs_bps is not None or obs_iops is not None:
        rep.data["observed"] = {"bps_mbps": obs_bps, "iops": obs_iops}

    v = bottleneck_verdict(bps_cap, iops_cap, obs_bps, obs_iops, args.alert_code)
    rep.data["bottleneck"] = {"disk_bps_ceiling": bps_cap,
                              "disk_iops_ceiling": iops_cap, "verdict": v}
    rep.h("Bottleneck attribution")
    rep.p(f"  layer      : {v['layer']}")
    rep.p(f"  confidence : {v['confidence']}")
    rep.p(f"  why        : {v['why']}")
    rep.p(f"  fix        : {v['fix']}")

    print_guest_checklist(rep)
    rep.p("\n  Platform-side history (background migration / replica "
          "rebuild) is NOT visible through any cloud query API: if the "
          "customer insists on that hypothesis (ticket T-CC0FA37F), escalate "
          "to a human support ticket -- never assert it.")

    if v["layer"] == "INSTANCE":
        action = ("state that the disk is NOT the limit; guide the customer "
                  "to the instance-spec change area "
                  "(references/disk-pl-change-guide__handoff-boundaries.md)")
    elif v["layer"] == "DISK":
        action = ("run --mode assess on the same disk to plan the "
                  "performance-level change (snapshot-first guidance included)")
    else:
        action = ("for an allowlisted in-guest reading run --mode guest "
                  "--instance-id i-xxx --guest-command <key> (it prints the "
                  "announce block first and dispatches only after explicit "
                  "confirmation); for the refused tools send the customer the "
                  "self-check list and rerun with --observed-* once readings "
                  "are pasted back")
    return rep.finalize(action, args.json)


def mode_guest(args: argparse.Namespace, rep: Report) -> int:
    """Capability C5: ONE allowlisted non-mutating guest diagnostic, gated."""
    region = resolve_region(args, rep)
    if not region:
        return rep.finalize("ask the customer for the region id and rerun", args.json)
    rep.data["region"] = region

    if args.list_guest_commands:
        print_guest_checklist(rep)
        return rep.finalize(
            "choose a --guest-command key, relay the announce block, get an "
            "explicit confirmation, then rerun with --confirm", args.json)

    if not args.instance_id or not INSTANCE_ID_RE.match(args.instance_id):
        rep.fail("guest mode needs --instance-id i-xxxx (the instance to "
                 "inspect); never an id guessed from a disk id")
        return rep.finalize("ask the customer which instance to inspect", args.json)
    instance_id = args.instance_id

    resolved = resolve_guest_command(args.guest_command)
    if resolved is None:
        rep.status = "DEGRADED"
        rep.h("Refused: request is not in the low-risk allowlist")
        rep.p("  " + REFUSE_WORDING)
        rep.p(f"  requested value (echoed back, never executed): "
              f"{args.guest_command or '(no --guest-command given)'}")
        rep.p("  allowlist keys: " + ", ".join(GUEST_COMMAND_ALLOWLIST))
        print_guest_checklist(rep)
        return rep.finalize(
            "offer the customer-run command list above and interpret what the "
            "customer pastes back", args.json)
    key, entry = resolved
    rep.data["guest_command"] = {"key": key, "command": entry["command"]}

    rep.h("Pre-execution notice (mandatory, must be relayed BEFORE --confirm)")
    rep.p("  " + GUEST_ANNOUNCE_TEMPLATE.format(
        instance_id=instance_id, command=entry["command"], scope=entry["scope"],
        effect=entry["effect"], reversible=entry["reversible"],
        why=entry["why"]))
    if not args.confirm:
        rep.status = "DEGRADED"
        rep.p("  NOT EXECUTED: this run carried no confirmation, so nothing "
              "was dispatched into the instance.")
        return rep.finalize(
            "relay the notice above verbatim, obtain an explicit yes for THIS "
            "single command, then rerun the same call with --confirm", args.json)

    inst = fetch_instance(rep, region, instance_id)
    if inst is None:
        rep.status = "DEGRADED"
        rep.p("  instance not visible in this account/region: nothing was "
              "dispatched. Confirm the account and region, do not guess them.")
        return rep.finalize("confirm account + region with the customer", args.json)
    os_label = f"{inst.get('OSType') or ''} {inst.get('OSName') or ''}".strip()
    rep.data["instance"] = {"instance_id": instance_id,
                            "instance_type": inst.get("InstanceType"),
                            "status": inst.get("Status"), "os": os_label}
    if os_label.lower().startswith("win"):
        rep.status = "DEGRADED"
        rep.h("Refused: Windows instance")
        rep.p("  The allowlist is POSIX shell text only and this tier has no "
              "Windows guest evidence, so nothing is dispatched here; "
              "escalate Windows in-guest diagnosis to human support "
              "(references/disk-pl-change-guide__handoff-boundaries.md).")
        return rep.finalize("hand the Windows case to human support", args.json)
    if str(inst.get("Status") or "").lower() not in ("running",):
        rep.p(f"  caution: instance status is {inst.get('Status')}; Cloud "
              "Assistant may not answer, in which case this degrades.")

    content = base64.b64encode(entry["command"].encode("utf-8")).decode("ascii")
    try:
        dispatched = _cli.call("ecs", "RunCommand", {
            "RegionId": region,
            "Type": GUEST_SHELL_TYPE,
            "CommandContent": content,
            "Name": f"{SKILL_NAME}-{key}",
            "Description": "allowlisted non-mutating diagnostic, confirmed "
                           "by the customer for this single call",
            "Timeout": GUEST_COMMAND_TIMEOUT,
            "InstanceId.1": instance_id,
        }, region=region, timeout=HEAVY_CALL_TIMEOUT)
    except _cli.CliError as e:
        rep.degrade(f"RunCommand({key})", e)
        rep.p("  " + GUEST_DEGRADED_WORDING)
        rep.p(f"  equivalent step for the customer: run `{entry['command']}` "
              "inside the instance and paste the output.")
        return rep.finalize(
            "report the failure verbatim and give the customer the equivalent "
            "command to run", args.json)

    invoke_id = str(dispatched.get("InvokeId") or "")
    rep.data["invoke_id"] = invoke_id
    rep.h(f"Dispatched (Cloud Assistant invoke {invoke_id or 'id not returned'})")
    rep.p(f"  instance : {instance_id}")
    rep.p(f"  command  : {entry['command']}")
    if not invoke_id:
        rep.degrade("RunCommand", _cli.CliError(
            "the response carried no InvokeId, so the result cannot be "
            "tracked; nothing more was attempted"))
        rep.p("  " + GUEST_DEGRADED_WORDING)
        return rep.finalize("ask the customer to run the command and paste the "
                            "output", args.json)

    record: dict = {}
    for attempt in range(1, GUEST_POLL_MAX + 1):
        try:
            polled = _cli.call("ecs", "DescribeInvocations",
                               {"RegionId": region, "InvokeId": invoke_id},
                               region=region, timeout=HEAVY_CALL_TIMEOUT)
        except _cli.CliError as e:
            rep.degrade("DescribeInvocations", e)
            break
        records = invocation_records(polled)
        record = next((r for r in records
                       if str(r.get("InstanceId") or "") == instance_id),
                      records[0] if records else {})
        state = str(record.get("InvocationStatus")
                    or record.get("RecordStatus") or "")
        if record and state.strip().lower() not in GUEST_NON_TERMINAL:
            break
        if attempt < GUEST_POLL_MAX:
            time.sleep(GUEST_POLL_INTERVAL)

    state = str(record.get("InvocationStatus")
                or record.get("RecordStatus") or "no record returned")
    exit_code = record.get("ExitCode")
    output = decode_guest_output(record.get("Output"))
    rep.p(f"  status   : {state}")
    rep.p(f"  exit code: {exit_code if exit_code is not None else 'not reported'}")
    if record.get("StatusDescription"):
        rep.p(f"  detail   : {record['StatusDescription']}")
    rep.p("  output:")
    for line in (output.splitlines() or ["(empty)"]):
        rep.p(f"    | {line}")
    rep.data["guest_reading"] = {"status": state, "exit_code": exit_code,
                                 "output": output}
    rep.p("  note: a non-zero exit code is itself a reading (e.g. a missing "
          "directory means the tool never recorded anything) -- interpret it, "
          "do not retry blindly. Output is only what the API returned.")

    got_reading = bool(output) or exit_code is not None or "finish" in state.lower() \
        or "success" in state.lower()
    if not got_reading:
        rep.status = "DEGRADED"
        rep.p("  " + GUEST_DEGRADED_WORDING)
        action = ("relay the status above; ask the customer to run the "
                  "equivalent command and paste the output, or check that the "
                  "Cloud Assistant agent is installed and the instance is "
                  "running")
    else:
        action = ("interpret the reading together with the disk/instance "
                  "ceilings; for per-process attribution send the customer the "
                  "refused-tool list (atop/iostat) and re-run bottleneck mode "
                  "with --observed-* once pasted")
    return rep.finalize(action, args.json)


def mode_verify(args: argparse.Namespace, rep: Report) -> int:
    region = resolve_region(args, rep)
    if not region:
        return rep.finalize("ask the customer for the region id and rerun", args.json)
    if not args.disk_id:
        rep.fail("verify mode needs --disk-id d-xxx")
        return rep.finalize("collect the disk id and rerun", args.json)
    if not DISK_ID_RE.match(args.disk_id):
        rep.fail(f"invalid disk id '{args.disk_id}'")
        return rep.finalize("fix the disk id and rerun", args.json)

    disk = fetch_disk(rep, region, args.disk_id)
    if disk is None:
        rep.fail("disk not visible; verification impossible")
        return rep.finalize("confirm account + region, then rerun", args.json)

    rep.data["region"] = region
    rep.data["disk"] = disk
    print_disk_table(rep, disk)

    rep.h("Post-change verification (current values vs expectation)")
    checks, mismatch = [], False
    pairs = [("Category", args.expected_category),
             ("PerformanceLevel", args.expected_performance_level),
             ("Size", str(args.expected_size) if args.expected_size else None)]
    for field, expected in pairs:
        if expected is None:
            continue
        actual = str(disk.get(field, ""))
        ok = actual.strip().upper() == expected.strip().upper()
        mismatch = mismatch or not ok
        checks.append({"field": field, "expected": expected,
                       "actual": actual, "ok": ok})
        rep.p(f"  {field:<18}: expected {expected}  actual {actual}  "
              f"{'OK' if ok else 'MISMATCH'}")
    rep.data["verify_checks"] = checks
    print_ceilings(rep, disk)

    if not checks:
        rep.status = "DEGRADED"
        action = ("no expected values passed: supply --expected-category / "
                  "--expected-performance-level to make this a real check")
    elif mismatch:
        rep.status = "DEGRADED"
        action = ("the change has NOT taken effect yet: check the async task "
                  "status in the ECS console task list, then rerun "
                  "verification")
    else:
        action = ("change verified effective; remind the customer to watch "
                  "IO behavior during the next peak")
    return rep.finalize(action, args.json)


# ---------------------------------------------------------------------------
# Argument parser & entry
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="disk_pl_advisor.py",
        description=("Guidance & diagnosis for ECS cloud disk type / "
                     "performance-level changes (ESSD PL0-PL3, Entry, AutoPL, "
                     "ultra/SSD disks); no cloud resource is changed and only "
                     "allowlisted non-mutating guest diagnostics can be "
                     "dispatched, one at a time, after confirmation"),
    )
    p.add_argument("--mode",
                   choices=["assess", "bottleneck", "guest", "verify", "faq"],
                   default="assess", help="decision-tree branch to run")
    p.add_argument("--region-id", default=None, help="e.g. cn-hangzhou")
    p.add_argument("--disk-id", default=None, help="d-xxxx")
    p.add_argument("--instance-id", default=None, help="i-xxxx")
    p.add_argument("--target-category", default=None,
                   help="desired disk category for the eligibility check")
    p.add_argument("--target-performance-level", default=None,
                   help="desired PL (PL0/PL1/PL2/PL3)")
    p.add_argument("--expected-category", default=None, help="verify mode")
    p.add_argument("--expected-performance-level", default=None, help="verify mode")
    p.add_argument("--expected-size", type=int, default=None,
                   help="verify mode, GiB")
    p.add_argument("--alert-code", default=None,
                   help="customer-visible alert reason code, e.g. EcsBaseBPS")
    p.add_argument("--observed-bps-mbps", type=float, default=None,
                   help="observed disk throughput MB/s (console/iostat paste)")
    p.add_argument("--observed-iops", type=float, default=None,
                   help="observed disk IOPS (console/iostat paste)")
    p.add_argument("--no-metrics", action="store_true",
                   help="skip the CloudMonitor datapoint fetch")
    p.add_argument("--cms-namespace", default=None,
                   help="override metric namespace")
    p.add_argument("--cms-metric", action="append", default=None,
                   help="override/extend metric names (repeatable)")
    p.add_argument("--cms-period", type=int, default=60,
                   help="datapoint aggregation period seconds")
    p.add_argument("--question", default=None,
                   help="customer original wording (faq matching; echoed to report)")
    p.add_argument("--topic", default=None, help="faq mode topic key")
    p.add_argument("--list-topics", action="store_true",
                   help="list embedded FAQ topics (no cloud call)")
    p.add_argument("--guest-command", default=None,
                   help="guest mode: an allowlist key (or the exact allowlisted "
                        "command); anything else is refused, never executed")
    p.add_argument("--confirm", action="store_true",
                   help="guest mode ONLY: the customer explicitly approved THIS "
                        "single command after the announce block was relayed")
    p.add_argument("--list-guest-commands", action="store_true",
                   help="print the dispatch allowlist and the refusal list")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine-readable JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    args = build_parser().parse_args(argv)
    rep = Report()
    rep.data["mode"] = args.mode
    if args.question:
        rep.data["customer_question"] = args.question

    # faq mode and the allowlist listing need no cloud access; identity
    # pre-check otherwise.
    if args.mode != "faq" and not (args.mode == "guest"
                                   and args.list_guest_commands):
        _cli.check_cli_available()
        uid = _cli.resolve_account_id(profile=args.profile)
        if uid:
            rep.data["uid"] = uid
        else:
            rep.degrade("sts get-caller-identity",
                        _cli.CliError("identity pre-check failed"))
            rep.p("[!] identity pre-check failed: configure the aliyun CLI "
                  "default credential chain (`aliyun sts get-caller-identity`); this skill "
                  "never handles AK/SK directly.")

    handlers = {"assess": mode_assess, "bottleneck": mode_bottleneck,
                "guest": mode_guest, "verify": mode_verify, "faq": mode_faq}
    return handlers[args.mode](args, rep)


# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no subprocess): run with
#   python3 scripts/axes/disk_pl_change_guide/disk_pl_advisor.py --selftest
# Locks the change-decision arithmetic a wrong verdict turns into a wrong
# customer action: ceiling curves, the one-way-door matrix (incl. the
# fail-closed rule that an UNKNOWN current PL is never ranked as the floor and
# promised an online upgrade), the 0.95 bottleneck boundary, the dispatch
# allowlist resolution and the invocation-record parser.
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    rc = 0
    checked: list = []

    def expect(name, cond):
        nonlocal rc
        checked.append(name)
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    import base64 as _b64

    # --- ceiling curves -----------------------------------------------------
    pl0 = PERF_FORMULAS["PL0"]
    r = ceiling_from_curve(pl0["iops"], 100)
    expect("curve_pl0_100iops", r["value"] == 3000)
    expect("curve_formula_text", r["formula"] == "min(1800 + 12 * 100, 10000)")
    expect("curve_cap_plateau",
           ceiling_from_curve(pl0["iops"], 1000)["value"] == 10000)
    expect("curve_zero_cap_base",
           ceiling_from_curve(pl0["iops"], 0)["value"] == 1800)
    entry = PERF_FORMULAS["cloud_essd_entry"]
    expect("curve_entry_40",
           ceiling_from_curve(entry["iops"], 40)["value"] == 2120)
    ssd = PERF_FORMULAS["cloud_ssd"]
    r = ceiling_from_curve(ssd["iops"], 500)
    expect("curve_fixed_max", r["value"] == ssd["iops"]["cap"]
           and r["formula"].startswith("<="))

    # --- disk_ceilings routing ---------------------------------------------
    rows = disk_ceilings("cloud_essd", "PL0", 100)
    expect("ceilings_essd_by_pl",
           len(rows) == 2 and rows[0]["value"] == 3000)
    rows = disk_ceilings("cloud_auto", "PL2", 100)
    expect("ceilings_autopl_baseline_note",
           any("BASELINE" in str(x.get("note", "")) for x in rows))
    expect("ceilings_unknown_empty", disk_ceilings("cloud", "x", 100) == [])

    # --- judge_change matrix ------------------------------------------------
    E = FIXED_PL_CATEGORY
    expect("jc_pl_up_online",
           judge_change(E, "PL0", None, "PL1")["verdict"] == "ALLOWED_ONLINE")
    expect("jc_pl_down_verify",
           judge_change(E, "PL2", None, "PL1")["verdict"] == "VERIFY_OFFICIAL")
    expect("jc_same_no_change",
           judge_change(E, "PL2", None, "PL2")["verdict"] == "NO_CHANGE")
    # anti-regression (this round's fix): an unknown current PL must never be
    # ranked as the floor and promised an online-capable upgrade.
    v = judge_change(E, "PL5", None, "PL2")
    expect("jc_unknown_pl_never_online", v["verdict"] == "VERIFY_OFFICIAL")
    expect("jc_unknown_pl_direction_note",
           "cannot be determined" in v["note"])
    expect("jc_empty_pl_verify",
           judge_change(E, "", None, "PL2")["verdict"] == "VERIFY_OFFICIAL")
    expect("jc_bad_target_verify",
           judge_change(E, "PL1", None, "PL9")["verdict"] == "VERIFY_OFFICIAL")
    expect("jc_autopl_to_pl_denied",
           judge_change("cloud_auto", None, None, "PL2")["verdict"]
           == "DENIED_ONE_WAY")
    expect("jc_autopl_to_essd_denied",
           judge_change("cloud_auto", None, E, None)["verdict"]
           == "DENIED_ONE_WAY")
    expect("jc_to_autopl_allowed",
           judge_change(E, "PL1", "cloud_auto", None)["verdict"] == "ALLOWED")
    expect("jc_regional_not_applicable",
           judge_change("cloud_regional_disk_auto", None, None,
                        "PL1")["verdict"] == "NOT_APPLICABLE")
    expect("jc_efficiency_to_essd_online",
           judge_change("cloud_efficiency", None, E,
                        "PL0")["verdict"] == "ALLOWED_ONLINE")
    expect("jc_no_target_guide",
           judge_change(E, "PL1", None, None)["verdict"]
           == "UNCONSTRAINED_GUIDE")
    # security-style invariant: no unknown/future PL shape yields a promise.
    phantom_ok = True
    for cur in ("PL4", "PL9", "pl-x", "NONE", "", "PL0 "):
        for tgt in ("PL0", "PL1", "PL2", "PL3"):
            got = judge_change(E, cur, None, tgt)["verdict"]
            if cur == "PL0 " and got == "ALLOWED_ONLINE":
                continue  # PL_RANK keys are upper/trusted from the API field
            if cur.strip().upper() in PL_RANK and tgt in PL_RANK:
                continue
            if got in ("ALLOWED_ONLINE", "ALLOWED") and cur not in PL_RANK:
                phantom_ok = False
    expect("invariant_unknown_current_pl_never_promised", phantom_ok)

    # --- normalize_category -------------------------------------------------
    expect("norm_essd_alias", normalize_category(" ESSD ") == E)
    expect("norm_autopl_alias", normalize_category("AutoPL") == "cloud_auto")
    expect("norm_unknown_none", normalize_category("cloud_xyz") is None)

    # --- bottleneck_verdict 0.95 boundary -----------------------------------
    expect("bn_exact_95_is_disk",
           bottleneck_verdict(125, 3000, 118.75, None, None)["layer"] == "DISK")
    expect("bn_just_under_is_instance_or_workload",
           bottleneck_verdict(100, 3000, 94.9, None, None)["layer"]
           == "INSTANCE_OR_WORKLOAD")
    expect("bn_alert_beats_disk_saturation",
           bottleneck_verdict(125, 3000, 132, 999999, "EcsBaseBPS")["layer"]
           == "INSTANCE")
    expect("bn_iops_saturation_disk",
           bottleneck_verdict(1000, 3000, 10, 2900, None)["layer"] == "DISK")
    expect("bn_zero_ceiling_not_promise",
           bottleneck_verdict(0, 0, 50, 100, None)["layer"] == "UNKNOWN")

    # --- match_faq ----------------------------------------------------------
    m = match_faq("why is my disk IOPS lower than the official numbers")
    expect("faq_iops_top_match", m and m[0] == "why-iops-lower-than-doc")
    expect("faq_unrelated_empty", match_faq("hello there") == [])

    # --- resolve_guest_command (dispatch allowlist) --------------------------
    key, entry = resolve_guest_command("df -h")
    expect("guest_by_command_text", key == "disk-usage"
           and entry["command"] == "df -h")
    key_mount = resolve_guest_command("mount-table")
    expect("guest_by_key",
           key_mount is not None and key_mount[0] == "mount-table"
           and key_mount[1]["command"] == "findmnt")
    expect("guest_refuses_extra_tools",
           resolve_guest_command("lsblk -d -o name,rota") is None)
    expect("guest_refuses_chained", resolve_guest_command("df -h && reboot") is None)
    expect("guest_refuses_empty", resolve_guest_command("") is None)

    # --- invocation_records -------------------------------------------------
    recs = invocation_records({"Invocations": {"Invocation": [
        {"InvokeInstances": {"InvokeInstance": [
            {"InstanceId": "i-a"}, {"InstanceId": "i-b"}]}}]}})
    expect("inv_nested_lists", [r.get("InstanceId") for r in recs] == ["i-a", "i-b"])
    recs = invocation_records({"Invocations": {"Invocation": {
        "InvokeInstances": {"InvokeInstance": {"InstanceId": "i-solo"}}}}})
    expect("inv_dict_variants", [r.get("InstanceId") for r in recs] == ["i-solo"])
    expect("inv_garbage_empty",
           invocation_records({"Invocations": "x"}) == [] and invocation_records({}) == [])

    # --- decode_guest_output ------------------------------------------------
    expect("decode_b64", decode_guest_output(
        _b64.b64encode(b"Filesystem  Size").decode()) == "Filesystem  Size")
    expect("decode_plain_echo",
           decode_guest_output("plain already") == "plain already")
    expect("decode_none_empty", decode_guest_output(None) == "")
    big = _b64.b64encode(b"x" * 5000).decode()
    out = decode_guest_output(big)
    expect("decode_truncated_at_cap",
           len(out) < 5000 and out.endswith("[truncated by the script]"))

    # --- datapoint_value ----------------------------------------------------
    expect("dp_average_str_cast", datapoint_value({"Average": "12.5"}) == 12.5)
    expect("dp_skip_bad_to_next",
           datapoint_value({"Average": "abc", "Maximum": 3}) == 3.0)
    expect("dp_none_absent", datapoint_value({"Minimum": None}) is None)

    print(f"--selftest: {len(checked)} checks, "
          f"{'ALL PASS' if rc == 0 else 'FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
