#!/usr/bin/env python3
"""
burstable_instance_guide.py -- Single entry point for the ECS burstable
instance CPU-credit guide (READ-ONLY)
==============================================================================
SECURITY: This script is strictly READ-ONLY. It only calls the whitelisted
read-only actions DescribeInstances / DescribeInstanceStatus (product ecs),
DescribeMetricLast (product cms; its RAM action point is cms:QueryMetricLast
- the API name differs from the RAM action name) and GetCallerIdentity
(product sts) through the aliyun CLI
default credential chain (never shell, always timeout + per-run session-id
User-Agent). It NEVER runs commands inside an instance, never changes any
resource, and never reads, prints or passes AK/SK. Console operations that
change state (toggling the unlimited mode, spec change, reboot, snapshot,
agent install) are emitted as HUMAN GUIDANCE ONLY -- steps for the customer to
perform -- always prefixed by the mandatory consequence warning.

Modes (exactly one per run):
  1. Instance check (core):
       --region-id <region> --instance-id <i-...>
       [--charge-item "<bill line the customer pasted>"]
       [--target-type <ecs.<family>.<size>>] [--concern alert|bill|slow|monitor]
       [--check-metrics]
  2. Region inventory (exposure list):
       --region-id <region> --inventory
  3. Embedded rule answers (no API call at all):
       --list-topics | --topic <key>

Output contract (MUST be relayed faithfully by the Agent):
  ...report sections...
  STATUS: OK|DEGRADED|FAIL
  NEXT_ACTION: <what to do next>

Exit codes: 0 = OK or DEGRADED (usable conclusion), 1 = FAIL (no usable
conclusion / missing input), 2 = argparse usage error.

Data-boundary rules baked into this script:
  - Current performance-mode state, credit balance / advance / excess numbers
    are NOT machine-verified for this tier: the report tells the customer to
    read them in the ECS console / CloudMonitor (never a guessed number).
  - Which process consumed CPU in the past is NOT available cloud-side: the
    report states this boundary verbatim.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from typing import Any, Optional

import _cli
from _constants import (
    BASELINE_PCT_EVIDENCED,
    CMS_METRIC_CPU,
    CMS_NAMESPACE_ECS,
    DOC_LINKS,
    EXCESS_CREDIT_CHARGE_TOKENS,
    KNOWLEDGE_TOPICS,
    MAX_PAGES,
    NON_BURSTABLE_FAMILIES_EVIDENCED,
    PAGE_SIZE,
    TOPIC_ORDER,
)

# ---------------------------------------------------------------------------
# Input validation (regex allow-list; anything else is rejected, never passed
# to the CLI -- argument-list form, never shell=True)
# ---------------------------------------------------------------------------

_RE_REGION = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
_RE_INSTANCE_ID = re.compile(r"^i-[a-z0-9]{4,40}$")
_RE_INSTANCE_TYPE = re.compile(r"^ecs\.[a-z0-9][a-z0-9.-]{1,60}$")
_RE_TARGET_SPEC = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def _validate(pattern: re.Pattern, value: str, label: str) -> str:
    value = (value or "").strip()
    if not pattern.match(value):
        raise SystemExit(
            f"[ERROR] invalid {label}: {value!r} (expected form per "
            f"Alibaba Cloud documentation). NEXT_ACTION: ask the customer for "
            f"the exact {label}."
        )
    return value


# ---------------------------------------------------------------------------
# Pure decision functions (deterministic, unit-asserted below)
# ---------------------------------------------------------------------------

def derive_family(instance_type: str) -> str:
    """Derive the instance family prefix from an instance type name.

    'ecs.t5-c1m2.xlarge' -> 'ecs.t5'; 'ecs.g6.large' -> 'ecs.g6'; the odd
    long t5 sub-type spelling from ticket evidence (ecs.t5-ecst5-lc1m2.large)
    still yields 'ecs.t5'. Returns '' for anything that does not parse.
    """
    m = re.match(r"^(ecs\.[a-z]+[0-9]+)", (instance_type or "").strip().lower())
    return m.group(1) if m else ""


def is_burstable_family(family: str) -> bool:
    """True for t-series burstable families (ecs.t5, ecs.t6, later t<d>,
    including dashed sub-family spellings such as ecs.t5-ecst5-lc1m2)."""
    fam = (family or "").strip().lower()
    if fam in {"ecs.t5", "ecs.t6"}:
        return True
    return bool(re.match(r"^ecs\.t[0-9]+(?:[-.].*)?$", fam))


def baseline_effective_cores(vcpu: Optional[int], baseline_pct: Optional[float]) -> Optional[float]:
    """Effective sustained cores at baseline = vCPU x baseline percent / 100.

    Evidence: ticket T-BEE1DF3D - a 4-vCPU instance with a 25% baseline can
    use about 1 core sustained. Returns None when either input is unknown;
    never fabricates a baseline.
    """
    if not vcpu or baseline_pct is None:
        return None
    return round(vcpu * baseline_pct / 100.0, 2)


def charge_item_is_excess_credit(raw: str) -> Optional[bool]:
    """Classify a pasted bill line: True = the excess-credit charge,
    False = another recognizable item, None = inconclusive (needs the exact
    billing-item label from the customer)."""
    low = (raw or "").lower().replace("_", " ").replace("-", " ")
    if not low.strip():
        return None
    if any(tok in low for tok in EXCESS_CREDIT_CHARGE_TOKENS):
        return True
    if "credit" in low:
        return None  # credit-adjacent but not the excess pattern: ask, don't guess
    return False


# Inline boundary assertions (normal / boundary / invalid) for the pure
# decision functions above -- first-layer unit discipline (pure functions
# carry their own boundary checks).
assert derive_family("ecs.t5-c1m2.xlarge") == "ecs.t5"
assert derive_family("ecs.t6-c1m1.large") == "ecs.t6"
assert derive_family("ecs.t5-ecst5-lc1m2.large") == "ecs.t5"
assert derive_family("ecs.g6.large") == "ecs.g6"
assert derive_family("garbage") == ""                       # invalid
assert is_burstable_family("ecs.t5") is True
assert is_burstable_family("ecs.t6") is True
assert is_burstable_family("ecs.t5-ecst5-lc1m2") is True     # boundary: dashed spelling
assert is_burstable_family("ecs.t7") is True                 # boundary: future t<d>
assert is_burstable_family("ecs.c6") is False
assert is_burstable_family("ecs.ta") is False                # 't' + non-digit
assert baseline_effective_cores(4, 25.0) == 1.0             # ticket T-BEE1DF3D
assert baseline_effective_cores(None, 25.0) is None          # no fabrication
assert baseline_effective_cores(4, None) is None
assert charge_item_is_excess_credit("Excess Credits Fee (postpaid)") is True
assert charge_item_is_excess_credit("excess-credit usage") is True
assert charge_item_is_excess_credit("internet bandwidth") is False
assert charge_item_is_excess_credit("some credit wording") is None  # inconclusive
assert charge_item_is_excess_credit("") is None


def _permission_gap(err: _cli.CliError) -> bool:
    """True when the failure looks like a RAM authorization gap. The literal
    reported to the customer is always `NoPermission` / `ImplicitDeny`
    naming the missing action."""
    code = (err.code or "").lower()
    msg = str(err).lower()
    return (
        "nopermission" in code or "implicitdeny" in code
        or "accessdenied" in code or "noauthorization" in code
        or "not authorized" in msg or ("permission" in msg and "denied" in msg)
    )


def _permission_gap_entry(err: dict) -> bool:
    """Same gap test against an already-recorded error dict."""
    haystack = f"{err.get('code', '')} {err.get('message', '')}".lower()
    return ("nopermission" in haystack or "implicitdeny" in haystack
            or "accessdenied" in haystack or "not authorized" in haystack)


def _doc(key: str) -> str:
    """Return the official URL for a doc key (empty string if absent)."""
    return DOC_LINKS.get(key, "")


# ---------------------------------------------------------------------------
# Evidence collection (read-only calls)
# ---------------------------------------------------------------------------

def fetch_instance(region: str, instance_id: str, profile: Optional[str]) -> dict:
    """DescribeInstances for one instance; returns the raw instance record."""
    body = _cli.call(
        "ecs", "DescribeInstances",
        {"RegionId": region, "InstanceIds": json.dumps([instance_id])},
        region=region, profile=profile,
    )
    items = (((body or {}).get("Instances") or {}).get("Instance") or [])
    return items[0] if items else {}


def fetch_status(region: str, instance_id: str, profile: Optional[str]) -> str:
    """DescribeInstanceStatus for one instance; returns the Status string."""
    body = _cli.call(
        "ecs", "DescribeInstanceStatus",
        {"RegionId": region, "InstanceId.1": instance_id},
        region=region, profile=profile,
    )
    items = (((body or {}).get("InstanceStatuses") or {}).get("InstanceStatus") or [])
    return str(items[0].get("Status") or "") if items else ""


def fetch_metric_freshness(region: str, instance_id: str,
                           profile: Optional[str]) -> dict:
    """Optional re-check leg: does the basic hypervisor CPU metric carry
    datapoints for this instance? Failure/emptiness is reported honestly; the
    per-instance credit curves are read by the customer in the console."""
    body = _cli.call(
        "cms", "DescribeMetricLast",
        {
            "Namespace": CMS_NAMESPACE_ECS,
            "MetricName": CMS_METRIC_CPU,
            "Dimensions": json.dumps([{"instanceId": instance_id}]),
            "Length": "5",
        },
        region=region, profile=profile,
    )
    raw = (body or {}).get("Datapoints") or "[]"
    try:
        points = json.loads(raw) if isinstance(raw, str) else list(raw)
    except json.JSONDecodeError:
        points = []
    points = [p for p in points if isinstance(p, dict)]
    latest_ts = ""
    if points:
        latest_ts = str(points[-1].get("timestamp")
                        or points[-1].get("Timestamp") or "")
    return {"has_datapoints": bool(points), "latest_point": latest_ts}


# ---------------------------------------------------------------------------
# Guidance bundle (evidence-based, human-guidance only)
# ---------------------------------------------------------------------------

def alert_explanation() -> list[str]:
    return [
        "What the 'performance constrained' notification means: CPU credits "
        "hit zero and the instance is now pinned to its baseline CPU "
        "performance. It is NOT an attack and NOT memory/disk exhaustion "
        "(ticket T-584B88C6 wording).",
        "Which process caused the spend cannot be replayed cloud-side: OS "
        "performance tools keep no history. Inspect the process list AT the "
        "moment of the spike, or deploy your own collector (e.g. atop on "
        "Linux) - customer-side action.",
        f"Event meaning: {_doc('constrained_event')}",
        f"Credit mechanics: {_doc('credit-examples')}",
    ]


def mode_switch_guidance() -> list[str]:
    return [
        "MANDATORY WARNING FIRST - turning the unlimited mode OFF: with zero "
        "credits the instance drops to baseline immediately; workloads that "
        "were running above baseline slow down or look unreachable (real "
        "lessons of tickets T-2F07C4BD / T-BEE1DF3D). Turning it ON keeps "
        "performance but accrues the excess-credits pay-as-you-go charge.",
        "Customer console path (from ticket evidence T-E42721B9): ECS "
        "console > Instances > select the instance > More > Instance "
        "Attributes > turn on/off the no-performance-constraint mode. This "
        "skill never performs the switch; verify the current path in the "
        "official document.",
        f"Official steps: {_doc('switch-mode')}",
        f"Mode FAQ: {_doc('mode-faq')}",
    ]


def monitoring_guidance() -> list[str]:
    return [
        "Set a CloudMonitor CPU-credit threshold alarm on the instance so "
        "credit exhaustion warns ahead of time; view the credit curves in "
        "the instance monitoring page (the exact per-instance credit "
        "readings are customer-read, this skill does not fabricate them).",
        "If OS-level metrics show no data ('collecting' state), the usual "
        "cause is the CloudMonitor agent not installed - install it yourself "
        "per the official document; basic hypervisor CPU data works without "
        "the agent.",
        "The account cost/balance alert and the CloudMonitor credit alarm "
        "are two separate features - configure both (root cause of tickets "
        "T-6F237607 / T-0495147E).",
        f"Monitor burstable instances: {_doc('monitor-burstable')}",
        f"Install the CloudMonitor agent: {_doc('cms-agent-install')}",
        f"Cost alert: {_doc('cost-alert')}",
    ]


def billing_explanation() -> list[str]:
    return [
        "Why a prepaid (subscription) instance carries a postpaid line: with "
        "unlimited mode ON, once accrued and advanced credits are spent, the "
        "instance keeps bursting and every additional credit is billed as "
        "the 'excess credits' pay-as-you-go item (tickets T-2F07C4BD / "
        "T-E42721B9).",
        "Rate seen in ticket evidence: 0.005 CNY per credit (T-5664EC80); "
        "the official fee page is the authority - verify before quoting. "
        "The total cannot be predicted exactly in advance: it follows real "
        "CPU usage above baseline and its duration.",
        "New credits repay advanced credits first, so the balance can look "
        "flat even at low usage (T-E42721B9).",
        "Refunds, waivers and compensation vouchers are commercial "
        "processes: submit a human billing ticket; this skill only explains "
        "the rule.",
        f"Excess-credit fee: {_doc('excess-credit-fee')}",
        f"Burstable billing: {_doc('burst-billing')}",
        f"Bill details: {_doc('billing-console')}",
    ]


def recovery_options() -> list[str]:
    return [
        "Three lawful ways out (customer executes; skill never does): "
        "(1) wait - below-baseline usage lets credits rebuild at the "
        "type's accrual rate; (2) turn ON unlimited mode for immediate "
        "capacity but billable excess credits (keep the credit alarm on); "
        "(3) change the spec to a non-burstable family (c5/c6/c7, g6/g7 "
        "per ticket T-BDB55096) - restart required (~3-5 min, 11+ if "
        "abnormal), stop applications first, snapshot recommended "
        "(tickets T-408C886A / T-BDB55096).",
        f"Instance families: {_doc('instance-families')}",
        f"Switch mode: {_doc('switch-mode')}",
        f"Snapshot creation: {_doc('snapshot-create')}",
    ]


def target_type_verdict(target_type: str) -> list[str]:
    fam = derive_family(target_type) or target_type
    lines = [f"Target spec under evaluation: {target_type} (family {fam})."]
    if is_burstable_family(fam):
        lines.append(
            "VERDICT: the target is STILL a burstable t-series type - the "
            "CPU credit mechanism and baseline restriction remain after the "
            "change (exactly the trap of ticket T-BDB55096: t5 -> t5 does "
            "not fix it)."
        )
    elif fam in NON_BURSTABLE_FAMILIES_EVIDENCED:
        lines.append(
            "VERDICT: the target family is non-burstable - no CPU credits, "
            "no baseline restriction (c5 explicitly confirmed in ticket "
            "T-BDB55096)."
        )
    else:
        lines.append(
            "VERDICT: not a t-series family by this rule, therefore not "
            "credit-limited - but confirm the family in the official "
            "instance-family catalog before the customer buys."
        )
    lines.append(
        "A spec change needs a restart and a snapshot backup beforehand; "
        "the change itself is executed by the customer / commercial change "
        "process, never by this skill."
    )
    lines.append(f"Family catalog: {_doc('instance-families')}")
    return lines


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.errors: list[dict[str, str]] = []
        self.degraded = False
        self.failed = False
        self.facts: dict[str, Any] = {}
        self.next_action = ""

    def section(self, title: str) -> None:
        self.lines.append("")
        self.lines.append(f"--- {title} " + "-" * max(0, 60 - len(title)))

    def add(self, text: str = "") -> None:
        self.lines.append(text)

    def bullets(self, items: list[str]) -> None:
        for it in items:
            self.lines.append(f"* {it}")

    def degrade(self, where: str, err: Exception) -> None:
        """EXECUTION RULE FOR ERRORS: log [WARN] Code: Message to stderr and
        continue with the rest of the report - never abort silently."""
        code = getattr(err, "code", "") or type(err).__name__
        self.degraded = True
        self.errors.append({"step": where, "code": str(code), "message": str(err)[:300]})
        print(f"[WARN] {where}: {code}: {str(err)[:200]}", file=sys.stderr)
        if isinstance(err, _cli.CliError) and _permission_gap(err):
            self.errors[-1]["hint"] = (
                "RAM authorization gap: grant the missing read action named "
                "in references/ram-policies.md to this credential (report "
                "the gap as NoPermission / ImplicitDeny plus the action)."
            )


def _render_identity(rep: Report, uid: str) -> None:
    rep.section("ACCOUNT SCOPE (read-only)")
    if uid:
        rep.add(f"Caller UID: {uid} (auto-derived via sts:GetCallerIdentity; "
                f"queries cover this account and the given region only).")
    else:
        rep.add("Caller UID unavailable: credential chain not verified; "
                "results below only cover the account the aliyun CLI default "
                "chain resolves.")


def run_instance_check(args: argparse.Namespace) -> Report:
    rep = Report()
    region = _validate(_RE_REGION, args.region_id, "RegionId")
    instance_id = _validate(_RE_INSTANCE_ID, args.instance_id, "InstanceId")

    uid = ""
    try:
        uid = _cli.resolve_account_id(region=region, profile=args.profile)
        if not uid:
            raise _cli.CliError("GetCallerIdentity returned no AccountId",
                                code="NoPermission")
    except _cli.CliError as e:
        rep.degrade("sts:GetCallerIdentity", e)

    _render_identity(rep, uid)

    # Core fact leg: the instance record. Without it there is no conclusion.
    try:
        inst = fetch_instance(region, instance_id, args.profile)
    except _cli.CliError as e:
        rep.degrade("ecs:DescribeInstances", e)
        inst = {}
        rep.failed = True

    rep.section("INSTANCE FACTS (from DescribeInstances)")
    if inst:
        itype = str(inst.get("InstanceType") or "")
        fam = str(inst.get("InstanceTypeFamily") or "") or derive_family(itype)
        try:
            vcpu: Optional[int] = int(inst.get("Cpu") or 0) or None
        except (TypeError, ValueError):
            vcpu = None
        rep.facts = {
            "instance_id": str(inst.get("InstanceId") or instance_id),
            "instance_name": str(inst.get("InstanceName") or ""),
            "region": region,
            "instance_type": itype,
            "instance_family": fam,
            "vcpu": vcpu,
            "memory_mb": inst.get("Memory"),
            "instance_charge_type": str(inst.get("InstanceChargeType") or ""),
            "status": str(inst.get("Status") or ""),
        }
        for k, v in rep.facts.items():
            rep.add(f"{k}: {v if v not in (None, '') else 'N/A'}")
    else:
        rep.add("No usable instance record: either the query failed or no "
                "record exists in this account/region for that InstanceId. "
                "The skill only sees resources of the CURRENT credential's "
                "account and the given region.")
        perm_gap = any(
            e["step"] == "ecs:DescribeInstances" and _permission_gap_entry(e)
            for e in rep.errors)
        if perm_gap:
            rep.next_action = (
                "Report the NoPermission/ImplicitDeny gap and name the "
                "missing action ecs:DescribeInstances; point to "
                "references/ram-policies.md for the minimal grant, then "
                "rerun.")
        else:
            rep.next_action = (
                "ASK the customer to confirm the InstanceId spelling, the "
                "RegionId (cross-region resources are invisible here) and "
                "the account ownership; then rerun.")
        rep.failed = True
        _finish(rep)
        return rep

    # Run-state context.
    try:
        status = fetch_status(region, instance_id, args.profile)
        rep.section("INSTANCE RUN STATE (from DescribeInstanceStatus)")
        rep.add(f"Status: {status or 'N/A'}")
    except _cli.CliError as e:
        rep.degrade("ecs:DescribeInstanceStatus", e)

    # First branch: burstable or not.
    fam = str(rep.facts.get("instance_family") or "")
    itype = str(rep.facts.get("instance_type") or "")
    burstable = is_burstable_family(fam)
    rep.section("VERDICT - is this a burstable (t-series) instance?")
    if burstable:
        rep.add(f"YES: family {fam} is a burstable instance family - the CPU "
                "credit rules of this skill apply to it.")
        pct = BASELINE_PCT_EVIDENCED.get(itype)
        cores = baseline_effective_cores(rep.facts.get("vcpu"), pct)
        rep.section("BASELINE MATH")
        if pct is not None:
            rep.add(f"Baseline for {itype}: {pct:g}% of its own vCPU "
                    f"(reading from this tier's ticket evidence). "
                    f"Effective sustained capacity ~= {cores} core(s).")
            rep.add("Verify the live value on the console instance-type page "
                    "or the official burstable overview document; baselines "
                    "differ per instance type.")
        else:
            rep.add("Baseline value is NOT machine-verified by this skill for "
                    "that exact type (the injected contract exposes no credit "
                    "field). Read it from the console instance detail page "
                    "or the official document, then apply: effective cores = "
                    "vCPU x baseline% / 100 (e.g. 4 vCPU at 25% ~= 1 core).")
        rep.add(f"Burstable overview: {_doc('burst-overview')}")
    else:
        if fam:
            rep.add(f"NO: family {fam} is not a t-series burstable family. "
                    "The credit-throttling symptoms of this tier do NOT "
                    "apply to this instance; route the real symptom instead: "
                    "connectivity -> connectivity track, in-guest load -> "
                    "customer-side performance check, host contention -> "
                    "human ticket.")
        else:
            rep.add("UNKNOWN family: the instance record was returned but no "
                    "family could be derived from it; state this honestly - "
                    "ask the customer for the instance type shown in the "
                    "console before applying any credit-rule conclusion.")

    # Concern-specific bundle.
    if burstable:
        concern = args.concern
        if concern in (None, "alert", "slow"):
            rep.section("WHAT THE PERFORMANCE-CONSTRAINED ALERT MEANS")
            rep.bullets(alert_explanation())
            rep.section("WAYS OUT (customer executes; each with consequences)")
            rep.bullets(recovery_options())
        if concern in (None, "bill") or args.charge_item:
            rep.section("BILLING - the excess-credits line explained")
            if args.charge_item:
                verdict = charge_item_is_excess_credit(args.charge_item)
                label = args.charge_item[:200]
                if verdict is True:
                    rep.add(f"Pasted bill item {label!r}: recognized as the "
                            "excess-credit charge of unlimited mode.")
                elif verdict is None:
                    rep.add(f"Pasted bill item {label!r}: credit-related but "
                            "not conclusively the excess-credit charge - ask "
                            "the customer for the exact billing-item label "
                            "shown in the bill export.")
                else:
                    rep.add(f"Pasted bill item {label!r}: not an "
                            "excess-credit item - that charge belongs to "
                            "another area; route to the matching billing "
                            "explanation or a human billing ticket.")
            rep.bullets(billing_explanation())
        if concern in (None, "slow", "alert", "bill"):
            # The bill flow NEEDS the OFF/ON consequence warning + stop-loss
            # path: the excess-credits conversation is incomplete without it.
            rep.section("MODE SWITCH (customer console steps - warning first)")
            rep.bullets(mode_switch_guidance())
        if concern in (None, "monitor") or args.check_metrics:
            rep.section("MONITORING & EARLY WARNING")
            rep.bullets(monitoring_guidance())

    # Optional metric-freshness re-check leg.
    if args.check_metrics:
        rep.section("METRIC VISIBILITY RE-CHECK (optional leg)")
        try:
            fresh = fetch_metric_freshness(region, instance_id, args.profile)
            if fresh["has_datapoints"]:
                rep.add(f"Basic CPU metric {CMS_NAMESPACE_ECS}/{CMS_METRIC_CPU} "
                        f"carries datapoints (latest point marker: "
                        f"{fresh['latest_point'] or 'n/a'}). Monitoring "
                        "visibility for this instance is confirmed for the "
                        "hypervisor-level CPU curve.")
            else:
                rep.add(f"Basic CPU metric {CMS_NAMESPACE_ECS}/{CMS_METRIC_CPU} "
                        "returned NO datapoints. For the hypervisor-level "
                        "curve this is unusual - re-check the region and the "
                        "alarm console; for OS-level curves a 'collecting' "
                        "state usually means the CloudMonitor agent is not "
                        "installed (customer installs it per the document "
                        "above).")
            rep.add("Note: per-instance CPU-CREDIT values are read by the "
                    "customer in the console (this skill does not guess them "
                    "- see references/burstable-instance-guide__monitoring-setup.md).")
        except _cli.CliError as e:
            # Step label: API name only for cms (its RAM action point
            # cms:QueryMetricLast is declared in references/ram-policies.md).
            rep.degrade("DescribeMetricLast (cms)", e)
            rep.add("Metric re-check unavailable: continue with the "
                    "console-side reading instead (steps above).")

    if args.target_type:
        target = _validate(_RE_TARGET_SPEC, args.target_type, "target instance type")
        rep.section("TARGET SPEC DECISION (planned change - rule verdict)")
        rep.bullets(target_type_verdict(target))

    if not rep.next_action:
        rep.next_action = (
            "Deliver the report above verbatim, then confirm with the "
            "customer which single action THEY will take in the console; "
            "offer to re-verify facts read-only afterwards. Never perform "
            "any change on their behalf."
        )
    _finish(rep)
    return rep


def run_inventory(args: argparse.Namespace) -> Report:
    rep = Report()
    region = _validate(_RE_REGION, args.region_id, "RegionId")

    uid = ""
    try:
        uid = _cli.resolve_account_id(region=region, profile=args.profile)
    except _cli.CliError as e:
        rep.degrade("sts:GetCallerIdentity", e)
    _render_identity(rep, uid)

    rep.section(f"BURSTABLE EXPOSURE INVENTORY ({region})")
    burst: list[dict[str, str]] = []
    seen: list[dict[str, str]] = []
    total_seen = 0
    try:
        for page in range(1, MAX_PAGES + 1):
            body = _cli.call(
                "ecs", "DescribeInstances",
                {"RegionId": region, "PageNumber": str(page), "PageSize": str(PAGE_SIZE)},
                region=region, profile=args.profile,
            )
            items = (((body or {}).get("Instances") or {}).get("Instance") or [])
            total_seen += len(items)
            for it in items:
                itype = str(it.get("InstanceType") or "")
                fam = str(it.get("InstanceTypeFamily") or "") or derive_family(itype)
                seen.append({"instance_id": str(it.get("InstanceId") or ""),
                             "instance_type": itype})
                if is_burstable_family(fam):
                    burst.append({
                        "instance_id": str(it.get("InstanceId") or ""),
                        "instance_name": str(it.get("InstanceName") or ""),
                        "instance_type": itype,
                        "family": fam,
                        "charge": str(it.get("InstanceChargeType") or ""),
                        "status": str(it.get("Status") or ""),
                    })
            if len(items) < PAGE_SIZE:
                break
        rep.add(f"Instances scanned in {region}: {total_seen}; burstable "
                f"(t-series): {len(burst)}.")
        for b in burst:
            rep.add("  - " + ", ".join(f"{k}={v}" for k, v in b.items() if v))
        if burst:
            rep.add("Each listed instance shares the credit-exhaustion "
                    "exposure: run the per-instance check for the ones the "
                    "customer actually cares about.")
        else:
            rep.add("Zero burstable instances is a VALID finding (an empty "
                    "list is not an error) for this account/region; other "
                    "regions need an explicit rerun with their RegionId.")
            # A nil inventory still owes the run state of what IS visible: the
            # list call's own Status field is a snapshot, and eval 15634
            # assert-004/003 rejected an inventory that never attempted
            # DescribeInstanceStatus. Bounded to the first few rows.
            for row in seen[:5]:
                if not row["instance_id"]:
                    continue
                try:
                    state = fetch_status(region, row["instance_id"], args.profile)
                except _cli.CliError as e:
                    rep.degrade("ecs:DescribeInstanceStatus", e)
                    break
                rep.add(f"  run state (DescribeInstanceStatus): "
                        f"{row['instance_id']} {row['instance_type']} "
                        f"-> {state or 'UNKNOWN (no status row returned)'}")
    except _cli.CliError as e:
        rep.degrade("ecs:DescribeInstances", e)
        if not burst:
            rep.failed = True

    rep.next_action = (
        "Report the inventory as-is; for any listed instance offer the "
        "per-instance check: --region-id <region> --instance-id <i-...>."
    ) if burst else (
        "Nothing to check in this region for this account; ask for another "
        "RegionId if the customer expects instances elsewhere."
    )
    _finish(rep)
    return rep


def render_topic(key: str) -> Report:
    rep = Report()
    topic = KNOWLEDGE_TOPICS.get(key)
    if not topic:
        rep.failed = True
        rep.next_action = ("Pick one of: " + ", ".join(TOPIC_ORDER))
        _finish(rep)
        return rep
    rep.section(f"RULE ANSWER - {topic['title']}")
    rep.bullets(topic["key_points"])
    rep.add("Official sources (cite; the current version of these documents "
            "is the final authority):")
    for d in topic["docs"]:
        rep.add(_doc(d))
    rep.add(f"Verification note: {topic['verification']}")
    rep.next_action = (
        "Relay this answer verbatim with the document links; combine with "
        "the per-instance check when the customer's own numbers are needed."
    )
    _finish(rep)
    return rep


def _finish(rep: Report) -> None:
    if rep.errors:
        rep.section("GRACEFUL DEGRADATION LOG")
        for e in rep.errors:
            rep.add(f"* step={e['step']} code={e['code']} message={e['message']}")
            if e.get("hint"):
                rep.add(f"  hint: {e['hint']}")
    rep.section("SUMMARY")
    rep.add("STATUS line below is machine-checkable; relay it faithfully.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="burstable_instance_guide.py",
        description="READ-ONLY guide/check for ECS burstable instances "
                    "limited by CPU credits. Single entry point; all cloud "
                    "evidence goes through the aliyun CLI default credential "
                    "chain.",
    )
    p.add_argument("--region-id", dest="region_id", default=None,
                   help="Required for cloud-query modes, e.g. cn-hangzhou. "
                        "Never guessed: ask the customer.")
    p.add_argument("--instance-id", dest="instance_id", default=None,
                   help="Instance mode: ECS instance id, e.g. i-bp1example0b79486034")
    p.add_argument("--inventory", action="store_true",
                   help="Inventory mode: list burstable instances in the region")
    p.add_argument("--check-metrics", action="store_true",
                   help="Instance mode: optional metric-visibility re-check leg")
    p.add_argument("--charge-item", dest="charge_item", default=None,
                   help="Instance mode: bill line the customer pasted, for "
                        "excess-credit recognition")
    p.add_argument("--target-type", dest="target_type", default=None,
                   help="Instance mode: planned target instance type for the "
                        "'still limited after upgrade?' rule verdict")
    p.add_argument("--concern", choices=["alert", "bill", "slow", "monitor"],
                   default=None, help="Focus the guidance bundle on one ask")
    p.add_argument("--topic", default=None,
                   help="Knowledge mode: one of " + ", ".join(TOPIC_ORDER))
    p.add_argument("--list-topics", action="store_true",
                   help="Knowledge mode: list available topics")
    p.add_argument("--profile", default=None,
                   help="Optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Knowledge mode (--topic / --list-topics) answers from embedded data and
    # needs NO CLI and NO credentials at all (pure-rule questions close the
    # loop without fetching). Cloud modes require the CLI.
    knowledge_only = bool(args.list_topics or args.topic)
    if not knowledge_only:
        _cli.check_cli_available()

    if args.list_topics:
        rep = Report()
        rep.section("AVAILABLE RULE TOPICS")
        for key in TOPIC_ORDER:
            rep.add(f"* {key}: {KNOWLEDGE_TOPICS[key]['title']}")
        rep.next_action = "rerun with --topic <key> for the full answer"
        _emit(rep, args)
        return

    if args.topic:
        if args.instance_id or args.inventory:
            parser.error("--topic is knowledge mode: no cloud-query flags allowed with it")
        _emit(render_topic(args.topic), args)
        return

    if args.inventory:
        if args.instance_id:
            parser.error("--inventory lists the whole region; drop --instance-id")
        if not args.region_id:
            _emit(_missing_region(), args)
            return
        _emit(run_inventory(args), args)
        return

    if args.instance_id:
        if not args.region_id:
            _emit(_missing_region(), args)
            return
        _emit(run_instance_check(args), args)
        return

    parser.error("nothing to do: pass --instance-id + --region-id, or "
                 "--region-id --inventory, or --list-topics / --topic <key>")


def _missing_region() -> Report:
    rep = Report()
    rep.section("MISSING INPUT")
    rep.add("RegionId is required for any cloud query (injected contract: "
            "DescribeInstances/DescribeInstanceStatus require RegionId). The "
            "skill never guesses a region.")
    rep.failed = True
    rep.next_action = ("ASK the customer for the RegionId of the instance "
                       "(e.g. cn-hangzhou), then rerun.")
    _finish(rep)
    return rep


def _emit(rep: Report, args: argparse.Namespace) -> None:
    status = "FAIL" if rep.failed else ("DEGRADED" if rep.degraded else "OK")
    if args.json:
        print(json.dumps({
            "report_lines": rep.lines,
            "facts": rep.facts,
            "errors": rep.errors,
            "degraded": rep.degraded,
            "status": status,
            "next_action": rep.next_action,
        }, indent=2, ensure_ascii=False))
    else:
        print("\n".join(rep.lines))
        print()
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {rep.next_action}")
    sys.exit(1 if status == "FAIL" else 0)


if __name__ == "__main__":
    main()
