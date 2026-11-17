#!/usr/bin/env python3
"""
billing_lifecycle_diagnosis.py -- single entry point of the
area:arrears-trial-billing-stop skill
===========================================================================
SECURITY: strictly READ-ONLY. This script only issues the five allow-listed
read actions (sts GetCallerIdentity, bssopenapi QueryAccountBalance,
bssopenapi QueryBillOverview, ecs DescribeInstances, cms DescribeMetricLast)
through the shared aliyun-CLI layer (_cli.py), with per-call timeouts,
retry-with-backoff on transient errors, credential masking, and a
per-run User-Agent session-id. It NEVER reads, prints or passes AK/SK/STS
tokens explicitly (the CLI default credential chain resolves auth), it
performs NO write/mutating call, and it writes NO files.

WHAT IT DOES (decision-tree Steps 0-7 of SKILL.md):
  Step 0  identity pre-check (guards against wrong-account analysis)
  Step 1  intent routing (arrears / trial-expiry / stop-billing / auto)
  Step 2  account arrears status (QueryAccountBalance)
  Step 3  instance status sweep across regions (DescribeInstances)
  Step 4  bill attribution per product/region (QueryBillOverview)
  Step 5  attached-resource cross-analysis; enumeration of snapshots,
          auto snapshot policies, standalone disks, EIPs and VPCs is NOT
          part of the authorized read set, so this step degrades to the
          console self-check checklist and marks the report DEGRADED
  Step 6  optional usage corroboration (cms DescribeMetricLast, --check-usage)
  Step 7  evidence report: verdicts with API-field citations, manual
          guidance branches, the MANDATORY risk-disclosure gate, handoff
          detections, and the STATUS / NEXT_ACTION contract lines.

Exit codes: 0 = OK or DEGRADED conclusion, 1 = no usable conclusion,
2 = argparse usage error only.

Usage examples:
  python3 billing_lifecycle_diagnosis.py
  python3 billing_lifecycle_diagnosis.py --intent arrears --months 2
  python3 billing_lifecycle_diagnosis.py --regions cn-beijing,cn-hangzhou \
      --guidance stop-billing
  python3 billing_lifecycle_diagnosis.py --check-usage --json
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
from datetime import datetime, timezone

import _cli
from _constants import (
    CMS_ALLOWED_METRICS,
    CMS_ECS_NAMESPACE,
    CONSOLE_LINKS,
    DEGRADED_ENUMERATION,
    DOC_LINKS,
    GUIDE_RESUME,
    GUIDE_STOP_BILLING,
    HANDOFF_MAP,
    MAX_USAGE_CHECK_INSTANCES,
    RETENTION_QUALIFIED,
    RISK_GATE,
    SKILL_NAME,
    SWEEP_REGIONS,
)

_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_REGION_RE = re.compile(r"^[a-z][a-z0-9-]{2,24}$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{6,}$", re.I)
_ACCOUNT_UID_RE = re.compile(r"^\d{6,}$")

# Heuristic low-balance warning threshold (CNY). It is a warning line, not a
# billable fact; it is always declared in the output with its value.
DEFAULT_LOW_BALANCE_THRESHOLD = 10.0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _to_float(value) -> float | None:
    """Parse a BSS money field ("1,234.56" / 1234.56 / None) to float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def current_cycle() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def walk_back_cycles(cycle: str, months: int) -> list[str]:
    """[cycle, cycle-1, ...] for `months` billing cycles ending at cycle."""
    year, mon = int(cycle[:4]), int(cycle[5:7])
    out = []
    for _ in range(max(1, months)):
        out.append(f"{year:04d}-{mon:02d}")
        mon -= 1
        if mon < 1:
            mon, year = 12, year - 1
    return out


def error_entry(step: str, err: _cli.CliError) -> dict:
    category = _cli.classify_error(err)
    return {
        "step": step,
        "category": category,
        "code": err.code or "Unknown",
        "message": str(err)[:300],
    }


# ---------------------------------------------------------------------------
# evidence steps
# ---------------------------------------------------------------------------

def step_identity(profile) -> tuple[dict | None, dict | None]:
    try:
        body = _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
        return body, None
    except _cli.CliError as e:
        return None, error_entry("identity(sts GetCallerIdentity)", e)


def step_balance(profile) -> tuple[dict | None, dict | None]:
    try:
        body = _cli.call("bssopenapi", "QueryAccountBalance", {},
                         profile=profile)
        return body.get("Data") or {}, None
    except _cli.CliError as e:
        return None, error_entry("balance(bssopenapi QueryAccountBalance)", e)


def step_bill_overview(cycle: str, profile) -> tuple[list[dict], dict | None]:
    try:
        body = _cli.call("bssopenapi", "QueryBillOverview",
                         {"BillingCycle": cycle}, profile=profile)
        data = body.get("Data") or {}
        items = (data.get("Items") or {}).get("Item")
        if items is None:
            items = data.get("Items") or []
        return [x for x in items if isinstance(x, dict)], None
    except _cli.CliError as e:
        return [], error_entry(f"bill(bssopenapi QueryBillOverview "
                               f"{cycle})", e)


def step_instances(region: str, instance_id: str | None,
                   profile) -> tuple[list[dict], dict | None]:
    params: dict = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    try:
        items, _total = _cli.paginate_page_number(
            "ecs", "DescribeInstances", params, region=region,
            profile=profile)
        return items, None
    except _cli.CliError as e:
        return [], error_entry(f"instances(ecs DescribeInstances {region})",
                               e)


def step_usage(instances: list[dict], namespace: str, metric: str,
               profile) -> list[dict]:
    """Optional CloudMonitor corroboration: is the resource still producing
    usage? Returns [] with degradation recorded on failure."""
    rows = []
    for inst in instances[:MAX_USAGE_CHECK_INSTANCES]:
        # instances arrive as instance_view() projections (snake_case keys).
        inst_id = str(inst.get("instance_id") or "")
        if not inst_id:
            continue
        try:
            body = _cli.call(
                "cms", "DescribeMetricLast",
                {
                    "Namespace": namespace,
                    "MetricName": metric,
                    "Dimensions": json.dumps([{"instanceId": inst_id}]),
                },
                region=inst.get("region_id") or None,
                profile=profile,
            )
            raw = body.get("Datapoints")
            points = json.loads(raw) if isinstance(raw, str) and raw else (
                raw or [])
            latest = points[-1] if isinstance(points, list) and points else {}
            rows.append({
                "instance_id": inst_id,
                "metric": f"{namespace}:{metric}",
                "timestamp": latest.get("timestamp") or latest.get(
                    "Timestamp"),
                "value": latest.get("Average", latest.get("Maximum")),
                "unit": latest.get("unit") or latest.get("Unit"),
            })
        except (_cli.CliError, json.JSONDecodeError) as e:
            err = e if isinstance(e, _cli.CliError) else _cli.CliError(str(e))
            rows.append(error_entry(
                f"usage(cms DescribeMetricLast {inst_id})", err))
    return rows


# ---------------------------------------------------------------------------
# interpretation
# ---------------------------------------------------------------------------

def route_intent(args, question: str) -> list[str]:
    """Step 1: which of the three areas the run serves."""
    if args.intent != "auto":
        return [args.intent]
    q = (question or "").lower()
    intents = []
    if any(k in q for k in ("overdue", "arrears", "insufficient balance",
                            "stopped due", "locked", "unpaid", "top up",
                            "recharge", "settle", "restore service",
                            "欠费", "欠款", "余额不足", "停机", "结清")):
        intents.append("arrears")
    if any(k in q for k in ("trial", "expir", "first purchase", "new user",
                            "savings plan", "renew", "到期", "试用", "续费")):
        intents.append("trial")
    if any(k in q for k in ("stop billing", "stop ecs billing", "stop charge",
                            "stop charging", "stop deduct", "how to stop",
                            "no longer charge", "release", "delete all",
                            "unsubscribe", "shut down", "cleanup", "彻底删除",
                            "停止计费", "不再扣费", "退掉", "注销", "释放")):
        intents.append("stop-billing")
    return intents or ["arrears", "trial", "stop-billing"]


def detect_handoffs(question: str) -> list[dict]:
    """Identify out-of-scope symptom phrases and name the receiving channel."""
    hits = []
    q = (question or "").lower()
    for channel, keywords in HANDOFF_MAP.items():
        matched = [k for k in keywords if k.lower() in q]
        if matched:
            hits.append({
                "channel": channel,
                "matched_keywords": matched,
                "action": ("Finish the account/billing exclusion first, then "
                           "hand off: "
                           "state this skill's billing-side conclusion, the "
                           "customer's own symptom wording, and the named "
                           "resource IDs, and route the case to the channel "
                           "above."),
            })
    return hits


def instance_view(raw: dict) -> dict:
    """Project the fields of this tier from one DescribeInstances row."""
    locks = raw.get("OperationLocks") or {}
    lock_reasons = [
        str(x.get("LockReason"))
        for x in (locks.get("LockReason") or []) if isinstance(x, dict)
    ]
    eip = raw.get("EipAddress") or {}
    return {
        "instance_id": raw.get("InstanceId"),
        "region_id": raw.get("RegionId"),
        "status": raw.get("Status"),
        "charge_type": raw.get("InstanceChargeType"),
        "expired_time": raw.get("ExpiredTime"),
        "creation_time": raw.get("CreationTime"),
        "operation_lock_reasons": lock_reasons,
        "public_ips": (raw.get("PublicIpAddress") or {}).get(
            "IpAddress") or [],
        "eip": eip.get("IpAddress"),
    }


def bill_view(items: list[dict]) -> dict:
    """Aggregate QueryBillOverview rows: per-product outstanding, rows and
    billing-item names.

    Measured live on the evaluation account: overview rows carry no Region
    field (region attribution therefore comes from the instance sweep and
    the console bill-statement detail page -- the optional Region read below
    stays only as a defensive pass-through for tenants where it is present).
    The row-level "Item" field names the billing item within the product and
    IS present -- collected per product for item-level attribution.
    """
    by_product: dict[str, dict] = {}
    total_pretax = 0.0
    total_outstanding = 0.0
    for it in items:
        name = str(it.get("ProductName") or it.get("ProductCode") or
                   "(unknown product)")
        pretax = _to_float(it.get("PretaxAmount")) or 0.0
        outstanding = _to_float(it.get("OutstandingAmount")
                                or it.get("OutStandingAmount")) or 0.0
        bucket = by_product.setdefault(name, {
            "pretax": 0.0, "outstanding": 0.0, "rows": 0,
            "regions": set(), "subscription_types": set(),
            "billing_items": set(),
        })
        bucket["pretax"] += pretax
        bucket["outstanding"] += outstanding
        bucket["rows"] += 1
        region = str(it.get("Region") or "").strip()
        if region:
            bucket["regions"].add(region)
        sub = str(it.get("SubscriptionType") or "").strip()
        if sub:
            bucket["subscription_types"].add(sub)
        item_name = str(it.get("Item") or "").strip()
        if item_name and item_name != "None":
            bucket["billing_items"].add(item_name)
        total_pretax += pretax
        total_outstanding += outstanding
    for bucket in by_product.values():
        bucket["regions"] = sorted(bucket["regions"])
        bucket["subscription_types"] = sorted(bucket["subscription_types"])
        bucket["billing_items"] = sorted(bucket["billing_items"])
    return {
        "by_product": by_product,
        "total_pretax": round(total_pretax, 4),
        "total_outstanding": round(total_outstanding, 4),
    }


def build_verdicts(balance, bills_by_cycle, instances, errors,
                   low_threshold: float) -> list[dict]:
    """Step 5 cross-analysis: every verdict cites the API + field it rests on.
    No evidence, no claim: gaps become DEGRADED notes, never guesses."""
    verdicts: list[dict] = []
    currency = ""
    available = None
    if balance:
        available = _to_float(balance.get("AvailableAmount"))
        currency = str(balance.get("Currency") or "")

    balance_failed = any("balance" in e["step"] for e in errors)
    if balance_failed:
        verdicts.append({
            "id": "account-status",
            "claim": "DEGRADED: the account balance could not be read, so "
                     "no arrears verdict is possible this run.",
            "evidence": "QueryAccountBalance failed (see errors[])",
            "confidence": "degraded",
        })
    elif available is not None:
        if available < 0:
            verdicts.append({
                "id": "account-status",
                "claim": f"The account IS overdue: available amount "
                         f"{available:,.2f} {currency} (negative = arrears).",
                "evidence": "bssopenapi QueryAccountBalance -> "
                            "Data.AvailableAmount",
                "confidence": "confirmed",
            })
        else:
            verdicts.append({
                "id": "account-status",
                "claim": f"The account is NOT overdue: available amount "
                         f"{available:,.2f} {currency}.",
                "evidence": "bssopenapi QueryAccountBalance -> "
                            "Data.AvailableAmount",
                "confidence": "confirmed",
            })
            if available < low_threshold:
                verdicts.append({
                    "id": "low-balance-risk",
                    "claim": f"Available amount {available:,.2f} {currency} is "
                             f"below the configured warning threshold "
                             f"({low_threshold:g} {currency or 'CNY'}) - a "
                             "heuristic line configured via "
                             "--low-balance-threshold, not a billing fact. "
                             "Pay-as-you-go deductions can tip the account "
                             "into arrears.",
                    "evidence": "QueryAccountBalance Data.AvailableAmount "
                                "vs CLI threshold",
                    "confidence": "heuristic",
                })

    unpaid_products = []
    for cycle, bv in bills_by_cycle.items():
        for product, bucket in bv["by_product"].items():
            if bucket["outstanding"] > 0:
                unpaid_products.append(
                    (bucket["outstanding"],
                     f"{cycle}/{product}: outstanding "
                     f"{bucket['outstanding']:g}"))
    if unpaid_products:
        # Top-N by amount: the shared test account legitimately bills dozens
        # of products; the VERDICT must stay readable and still be complete.
        unpaid_products.sort(key=lambda t: -t[0])
        shown = [text for _amt, text in unpaid_products[:10]]
        more = len(unpaid_products) - len(shown)
        listing = "; ".join(shown) + (
            f" (+{more} more products with outstanding amounts; full list in "
            "the bill attribution section)" if more > 0 else "")
        verdicts.append({
            "id": "bill-outstanding",
            "claim": ("Billing cycles still carry outstanding amounts per "
                      "product (top 10 by amount): " + listing),
            "evidence": "bssopenapi QueryBillOverview -> Items[].Outstanding"
                        "Amount aggregated by ProductName",
            "confidence": "confirmed",
        })

    live = [i for i in instances if i["status"] in ("Running", "Stopped",
                                                    "Pending", "Stopping",
                                                    "Starting")]
    locked_financial = [i for i in live if "financial" in
                        [r.lower() for r in i["operation_lock_reasons"]]]
    if locked_financial:
        verdicts.append({
            "id": "arrears-locked-instances",
            "claim": "Instances carrying a financial operation lock "
                     "(arrears-driven): " + ", ".join(
                         f"{i['instance_id']}@{i['region_id']}"
                         for i in locked_financial),
            "evidence": "ecs DescribeInstances -> OperationLocks.LockReason"
                        "[].LockReason == financial",
            "confidence": "confirmed",
        })
    if live:
        verdicts.append({
            "id": "instance-inventory",
            "claim": "Live instances found in the swept regions: " + ", ".join(
                f"{i['instance_id']}@{i['region_id']} [{i['status']}, "
                f"{i['charge_type']}]" for i in live),
            "evidence": "ecs DescribeInstances -> Status / "
                        "InstanceChargeType",
            "confidence": "confirmed",
        })
    else:
        verdicts.append({
            "id": "instance-inventory",
            "claim": "No ECS instances exist in the swept regions "
                     "(released or never created, or located in a region "
                     "outside the sweep list).",
            "evidence": "ecs DescribeInstances over the swept region list",
            "confidence": "confirmed-with-scope-note",
        })

    region_failed = [e for e in errors if e["step"].startswith("instances")]
    if region_failed:
        verdicts.append({
            "id": "instance-sweep-degraded",
            "claim": f"DEGRADED: {len(region_failed)} region(s) of the "
                     "instance sweep failed; absence of instances there is "
                     "NOT proven.",
            "evidence": "see errors[]",
            "confidence": "degraded",
        })

    # attached-resource signal: bill rows persist for products while no
    # instance inventory explains them
    if not live and bills_by_cycle:
        latest = bills_by_cycle[max(bills_by_cycle)]
        others = [p for p in latest["by_product"]
                  if not any(t in p.lower() for t in ("ecs", "云服务器"))]
        if others:
            verdicts.append({
                "id": "attached-resource-charges",
                "claim": "No live instances, yet the latest billing cycle "
                         f"still shows charged products: {', '.join(others)}. "
                         "This is the signature of attached resources "
                         "(snapshots, auto snapshot policies, standalone "
                         "disks, EIPs, images) that outlive the instance.",
                "evidence": "QueryBillOverview by_product vs "
                            "DescribeInstances sweep",
                "confidence": "strong-inference",
            })
    return verdicts


# ---------------------------------------------------------------------------
# guidance branches (manual-only output; nothing here is executed)
# ---------------------------------------------------------------------------

def guidance_blocks(intents, balance, instances) -> dict:
    blocks: dict[str, list[str]] = {}
    available = None
    if balance:
        available = _to_float(balance.get("AvailableAmount"))

    if "arrears" in intents:
        blocks["resume-service"] = list(GUIDE_RESUME) + [
            f"Official overdue-payment rules (authoritative source): "
            f"{DOC_LINKS['overdue']}",
            f"Pay-as-you-go starter guide: {DOC_LINKS['payg-guide']}",
        ]
    if "trial" in intents:
        blocks["trial-expiry"] = [
            "A 'free trial' ECS server is a pay-as-you-go instance billed "
            "normally and offset by trial entitlements (savings-plan / "
            "resource-package deduction); there is no separate free server "
            "product.",
            "Trial expiry does NOT auto-release the instance: with a "
            "positive balance it keeps running and bills pay-as-you-go; "
            "only prolonged arrears can trigger automatic release. Read "
            "references/arrears-trial-billing-stop__trial-expiry-rules.md.",
            "The expiry date of the trial entitlement itself (savings plan / "
            "resource package) is NOT visible through this skill's "
            "authorized read set (DEGRADED): verify it in the Expenses and "
            "Costs console, or from the SMS/notification's own product "
            "name.",
            "To keep the instance: renew (subscription) or convert the "
            "billing method IN THE DIRECTION the customer asked for - pick "
            "the matching console doc; do not hand over the opposite-"
            "direction link.",
            "Campaign plans (fixed-price activity packages) generally "
            "cannot be renewed onto a trial instance; migration means "
            "custom image -> new purchase -> switch system disk to the "
            "image (public IP is NOT preserved). See "
            f"references/arrears-trial-billing-stop__trial-expiry-rules.md and {DOC_LINKS['create-custom-image']}.",
        ]
    if "stop-billing" in intents:
        blocks["stop-billing"] = list(GUIDE_STOP_BILLING) + [
            f"Release-an-instance doc: {DOC_LINKS['release-instance']}",
            f"Stop vs release (economical mode): "
            f"{DOC_LINKS['economical-mode']}",
            f"Delete-snapshot doc (irreversible): "
            f"{DOC_LINKS['delete-snapshot']}",
            f"Snapshot billing: {DOC_LINKS['snapshot-billing']}",
            f"VPC/vSwitch removal doc: {DOC_LINKS['vpc-delete']}",
        ]
        blocks["console-self-check"] = list(DEGRADED_ENUMERATION) + [
            f"Billing statement detail: {CONSOLE_LINKS['expense-detail']}",
        ]
    if available is not None and available < 0 and "stop-billing" in intents:
        blocks["arrears-first"] = [
            "While the account is overdue, some console operations are "
            "restricted: settle the arrears first, then continue the "
            "cleanup order.",
        ]
    if instances:
        blocks["backup-pointer"] = [
            f"Backup before any release: {DOC_LINKS['create-snapshot']} "
            f"or a custom image {DOC_LINKS['create-custom-image']}",
        ]
    return blocks


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def render_readable(report: dict) -> None:
    print("=" * 74)
    print(f" ECS arrears / trial-expiry / stop-billing diagnosis  [{SKILL_NAME}]")
    print("=" * 74)

    acct = report["account"]
    print("\n-- Step 0  Identity -------------------------------------------")
    print(f"  Account UID   : {acct['uid'] or 'UNRESOLVED'}")
    print(f"  Identity type : {acct.get('identity_type', '')}")

    print("\n-- Step 2  Account balance ------------------------------------")
    bal = report["balance"]
    if bal:
        for key in sorted(bal):
            print(f"  {key:<18}: {bal[key]}")
    else:
        print("  (unavailable - see errors[])")

    print("\n-- Step 4  Bill attribution (QueryBillOverview) ---------------")
    for cycle, bv in report["bills"].items():
        print(f"  cycle {cycle}: pretax total {bv['total_pretax']:g}, "
              f"outstanding {bv['total_outstanding']:g}")
        for product, bucket in sorted(bv["by_product"].items()):
            regions = ",".join(bucket["regions"]) or "-"
            items_txt = ",".join(bucket.get("billing_items", [])) or "-"
            print(f"    - {product:<28} pretax={bucket['pretax']:<10g} "
                  f"outstanding={bucket['outstanding']:<10g} "
                  f"rows={bucket['rows']} regions={regions} "
                  f"items={items_txt} "
                  f"types={','.join(bucket['subscription_types']) or '-'}")

    print("\n-- Step 3  Instance sweep -------------------------------------")
    print(f"  regions swept: {', '.join(report['auto_filled']['regions'])}")
    if report["instances"]:
        for i in report["instances"]:
            locks = ",".join(i["operation_lock_reasons"]) or "-"
            print(f"  {i['instance_id']} @ {i['region_id']}: {i['status']} "
                  f"| {i['charge_type']} | expires {i['expired_time']} "
                  f"| locks {locks} | eip {i['eip'] or '-'}")
    else:
        print("  no instances in the swept regions")

    if report.get("usage"):
        print("\n-- Step 6  Usage corroboration (cms DescribeMetricLast) ----")
        for row in report["usage"]:
            if "step" in row:
                print(f"  [WARN] {row['step']}: {row['message'][:160]}")
            else:
                print(f"  {row['instance_id']}: {row['metric']} = "
                      f"{row['value']} {row['unit'] or ''} @ "
                      f"{row['timestamp'] or '-'}")

    print("\n-- Step 5  Verdicts (each cites its evidence) -----------------")
    for v in report["verdicts"]:
        print(f"  [{v['confidence']}] {v['claim']}")
        print(f"      evidence: {v['evidence']}")

    if report["intents"] != ["none"]:
        print("\n-- Manual guidance (this skill executes nothing) ------------")
        for name, lines in report["guidance"].items():
            print(f"  [{name}]")
            for line in lines:
                print(f"    {line}")

    if report["risk_gate_applied"]:
        print("\n-- MANDATORY risk disclosure (applies to ALL cleanup "
              "guidance above) --")
        for n, item in enumerate(RISK_GATE, 1):
            print(f"  {n}. {item}")

    if report["handoffs"]:
        print("\n-- Out-of-scope symptoms detected -> handoff ---------------")
        for h in report["handoffs"]:
            print(f"  channel : {h['channel']}")
            print(f"  matched : {', '.join(h['matched_keywords'])}")
            print(f"  action  : {h['action']}")

    if report["degraded_notes"]:
        print("\n-- Graceful degradation log --------------------------------")
        for note in report["degraded_notes"]:
            print(f"  [WARN|DEGRADE] {note}")

    if report["errors"]:
        print("\n-- Errors ---------------------------------------------------")
        for e in report["errors"]:
            print(f"  [{e['category']}] {e['step']}: {e['message'][:200]}")

    print("\nSummary")
    print("-------")
    print(report["summary"])
    print(f"\nSTATUS: {report['status']}")
    print(f"NEXT_ACTION: {report['next_action']}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="billing_lifecycle_diagnosis.py",
        description=(
            "Read-only evidence run for ECS arrears shutdown/recovery, "
            "free-trial expiry, and stopping all billing (this skill "
            "performs no write operations)"
        ),
    )
    parser.add_argument("--intent",
                        choices=["auto", "arrears", "trial", "stop-billing"],
                        default="auto",
                        help="decision-tree area; auto infers from "
                             "--question and the data")
    parser.add_argument("--question", default="",
                        help="customer's own wording (used for intent "
                             "routing and out-of-scope handoff detection)")
    parser.add_argument("--regions", default=None,
                        help=f"comma-separated RegionId sweep list "
                             f"(default: built-in list of "
                             f"{len(SWEEP_REGIONS)} regions)")
    parser.add_argument("--instance-id", default=None,
                        help="optional instance filter (must look like "
                             "i-xxxxxxxx)")
    parser.add_argument("--billing-cycle", default=None,
                        help="billing cycle YYYY-MM (default: current "
                             "month, auto-filled and declared)")
    parser.add_argument("--months", type=int, default=1,
                        help="number of billing cycles to walk back "
                             "(1-3, default 1)")
    parser.add_argument("--check-usage", action="store_true",
                        help="optional Step 6: corroborate whether swept "
                             "instances still produce usage via CloudMonitor")
    parser.add_argument("--namespace", default=CMS_ECS_NAMESPACE,
                        help="CloudMonitor namespace (default "
                             f"{CMS_ECS_NAMESPACE})")
    parser.add_argument("--metric", default="CPUUtilization",
                        help="CloudMonitor metric; allowed: "
                             + ", ".join(CMS_ALLOWED_METRICS))
    parser.add_argument("--low-balance-threshold", type=float,
                        default=DEFAULT_LOW_BALANCE_THRESHOLD,
                        help="heuristic warning threshold in account "
                             "currency (default 10)")
    parser.add_argument("--guidance",
                        choices=["auto", "resume", "stop-billing", "both",
                                 "none"],
                        default="auto",
                        help="which manual guidance branches to print")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    _cli.check_cli_available()
    errors: list[dict] = []
    degraded_notes: list[str] = []

    # ---- validations (parameter hygiene before any call) ----
    cycle = args.billing_cycle or current_cycle()
    cycle_auto = args.billing_cycle is None
    if not _CYCLE_RE.match(cycle):
        print(f"[ERROR] --billing-cycle must be YYYY-MM, got {cycle!r}",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: rerun with a valid --billing-cycle YYYY-MM")
        sys.exit(1)
    if not 1 <= args.months <= 3:
        print("[ERROR] --months must be 1..3", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: rerun with --months 1..3")
        sys.exit(1)
    if args.metric not in CMS_ALLOWED_METRICS:
        print(f"[ERROR] --metric must be one of {CMS_ALLOWED_METRICS}",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: pick a metric from the documented list")
        sys.exit(1)

    regions = SWEEP_REGIONS
    if args.regions:
        regions = [r.strip() for r in args.regions.split(",") if r.strip()]
        if not regions or not all(_REGION_RE.match(r) for r in regions):
            print("[ERROR] --regions contains an invalid RegionId token",
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: pass comma-separated RegionIds such as "
                  "cn-beijing,cn-hangzhou")
            sys.exit(1)

    instance_id = None
    if args.instance_id:
        cand = args.instance_id.strip()
        if _INSTANCE_ID_RE.match(cand):
            instance_id = cand
        elif _ACCOUNT_UID_RE.match(cand):
            print(f"[WARN] {cand!r} looks like an ACCOUNT UID, not an "
                  "instance ID (instance IDs start with 'i-'). It was NOT "
                  "used as an instance filter. Verify the account identity "
                  "from Step 0 instead, and find the real instance ID in "
                  "the ECS console or the order list "
                  f"({CONSOLE_LINKS['orders']}).", file=sys.stderr)
        else:
            print(f"[WARN] {cand!r} is not a valid instance ID pattern; "
                  "the filter was ignored.", file=sys.stderr)
        if instance_id:
            # A single instance ID still needs its region: query the sweep
            # with the filter (an ID is unique within a region, and the
            # sweep covers every common region).
            regions = list(dict.fromkeys(regions))

    cycles = walk_back_cycles(cycle, args.months)

    # ---- Step 0 identity ----
    identity, err = step_identity(args.profile)
    if err:
        errors.append(err)
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: fix credentials / permissions first: verify the "
              "aliyun CLI default credential chain (aliyun sts get-caller-identity) and "
              "the sts:GetCallerIdentity grant in "
              "references/ram-policies.md, then rerun")
        print(json.dumps({"errors": errors}, indent=2, ensure_ascii=False))
        sys.exit(1)
    uid = str((identity or {}).get("AccountId") or "")

    # ---- Step 2 balance ----
    balance, err = step_balance(args.profile)
    if err:
        errors.append(err)
        print(f"[WARN] {err['step']}: {err['message'][:200]}", file=sys.stderr)

    # ---- Step 4 bill overview (per cycle) ----
    bills: dict[str, dict] = {}
    for c in cycles:
        items, err = step_bill_overview(c, args.profile)
        if err:
            errors.append(err)
            print(f"[WARN] {err['step']}: {err['message'][:200]}",
                  file=sys.stderr)
            continue
        bills[c] = bill_view(items)

    # ---- Step 3 instance sweep ----
    instances: list[dict] = []
    ok_regions = 0
    for region in regions:
        rows, err = step_instances(region, instance_id, args.profile)
        if err:
            errors.append(err)
            print(f"[WARN] {err['step']}: {err['message'][:200]}",
                  file=sys.stderr)
            continue
        ok_regions += 1
        for raw in rows:
            view = instance_view(raw)
            view["region_id"] = view["region_id"] or region
            instances.append(view)

    # ---- Step 5 degradation note for non-enumerable attached resources ----
    degraded_notes.append(
        "Snapshots, auto snapshot policies, standalone disks, EIPs and VPCs "
        "cannot be enumerated with this skill's authorized read-only set "
        "(their query APIs are not part of the verified contract). The "
        "console self-check checklist below the guidance sections is the "
        "authorized alternative; every conclusion that would need their "
        "inventory is marked DEGRADED.")
    degraded_notes.append(
        "Trial entitlement (savings plan / resource package) expiry dates "
        "are not queryable through the authorized read set; only the "
        "instance-level ExpiredTime is evidence. Entitlement expiry must be "
        "verified in the Expenses and Costs console.")
    degraded_notes.append(RETENTION_QUALIFIED)

    # ---- Step 6 optional usage ----
    usage: list[dict] = []
    if args.check_usage:
        usage = step_usage(instances, args.namespace, args.metric,
                           args.profile)
        if not instances:
            degraded_notes.append(
                "--check-usage skipped its metric calls: the sweep found no "
                "live instances to measure.")

    # ---- Step 1 intents + Step 7 verdicts / guidance ----
    intents = route_intent(args, args.question)
    if args.guidance == "none":
        intents_for_guidance: list[str] = []
    elif args.guidance == "both":
        intents_for_guidance = ["arrears", "trial", "stop-billing"]
    elif args.guidance == "resume":
        intents_for_guidance = ["arrears"]
    elif args.guidance == "stop-billing":
        intents_for_guidance = ["stop-billing"]
    else:
        intents_for_guidance = list(intents)

    verdicts = build_verdicts(balance, bills, instances, errors,
                              args.low_balance_threshold)
    guidance = guidance_blocks(intents_for_guidance, balance, instances)
    risk_gate_applied = "stop-billing" in intents_for_guidance or any(
        "release" in " ".join(lines).lower() or
        "delete" in " ".join(lines).lower()
        for lines in guidance.values())
    handoffs = detect_handoffs(args.question)

    # ---- STATUS ----
    core_failed = [e for e in errors
                   if e["step"].startswith(("balance", "bill", "instances"))]
    no_balance = balance is None
    no_bills = not bills
    no_regions_ok = ok_regions == 0
    if no_balance and no_bills and no_regions_ok:
        status = "FAIL"
        next_action = ("every evidence call failed: check the RAM grants in "
                       "references/ram-policies.md (NoPermission / "
                       "ImplicitDeny codes) and the credential chain, then "
                       "rerun")
    elif core_failed:
        status = "DEGRADED"
        next_action = ("relay the degraded part honestly, name the missing "
                       "evidence, apply the console self-check paths, and "
                       "re-run the failed step after the grant/parameter is "
                       "fixed")
    else:
        status = "OK"
        next_action = ("compose the customer answer from verdicts + "
                       "guidance + risk gate"
                       + ("; apply the handoff guidance for the out-of-scope "
                          "symptoms detected" if handoffs else "")
                       + "; re-run next billing cycle to confirm charges "
                       "stopped")

    available = _to_float((balance or {}).get("AvailableAmount"))
    if available is None:
        balance_line = ("Balance: UNAVAILABLE (degraded)." if not balance
                        else "Balance: available amount unreadable "
                             "(field absent).")
    else:
        balance_line = (f"Balance: available {available:,.2f} "
                        f"{(balance or {}).get('Currency', '')}.")
    summary_bits = [
        f"Identity: account {uid or 'UNRESOLVED'}.",
        balance_line,
        (f"Bills: cycles {', '.join(sorted(bills))} attributed by product; "
         f"latest outstanding {bills[max(bills)]['total_outstanding']:g}."
         if bills else "Bills: no cycle could be read (degraded)."),
        (f"Instances: {len(instances)} live row(s) across "
         f"{ok_regions}/{len(regions)} swept region(s)."
         if instances else
         "Instances: none found in the swept regions."),
        "Guidance is manual-only; this skill performs no write operation.",
    ]
    auto_filled = {
        "billing_cycle": (f"{cycle} auto-defaulted to the current month"
                          if cycle_auto else f"{cycle} (user-provided)"),
        "cycles_queried": cycles,
        "regions": list(regions),
        "regions_note": ("built-in sweep list (a script constant, not an "
                         "API); override with --regions"
                         if args.regions is None else "user-provided"),
        "instance_filter": instance_id or "none",
        "uid": f"{uid or 'n/a'} derived via sts GetCallerIdentity",
    }

    report = {
        "skill": SKILL_NAME,
        "status": status,
        "intents": intents,
        "account": {
            "uid": uid,
            "identity_type": (identity or {}).get("IdentityType"),
            "arn": (identity or {}).get("Arn"),
        },
        "balance": balance or {},
        "bills": bills,
        "instances": instances,
        "usage": usage,
        "verdicts": verdicts,
        "guidance": guidance,
        "risk_gate_applied": risk_gate_applied,
        "handoffs": handoffs,
        "degraded_notes": degraded_notes,
        "errors": errors,
        "auto_filled": auto_filled,
        "summary": " ".join(summary_bits),
        "next_action": next_action,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        render_readable(report)

    if status == "FAIL":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
