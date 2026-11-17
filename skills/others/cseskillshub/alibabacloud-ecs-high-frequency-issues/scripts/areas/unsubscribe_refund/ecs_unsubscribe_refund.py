#!/usr/bin/env python3
"""
ecs_unsubscribe_refund.py -- Single entry point of the ECS Unsubscribe &
Refund Guide skill (STRICTLY READ-ONLY)
===========================================================================
SECURITY: This skill performs read-only queries ONLY. This script calls
exactly the whitelisted read actions below, always through the shared CLI
layer (`aliyun` subprocess, per-call timeout, retry with backoff, credential
masking, per-run session-id User-Agent):

    sts   GetCallerIdentity        (2015-04-01, plugin mode)
    bssopenapi QueryAvailableInstances  (2017-12-14)  refund-side instance ledger
    bssopenapi QueryInstanceBill         (2017-12-14)  consumed-amount reference
    bssopenapi DescribeInstanceBill      (2017-12-14)  per-instance bill rows
    bssopenapi QueryCashCoupons          (2017-12-14)  vouchers at risk on refund
    ecs   DescribeInstances        (2014-05-26)       live charge type / expiry / status

It NEVER invokes any mutating API and NEVER submits anything on the customer's
behalf: unsubscription, refund, order cancellation, invoice reversal,
withdrawal and account closure are commercial actions reserved to the human
customer, performed only via the manual console entries printed here.

Modes (mutually exclusive):
  --inventory   Account-scoped unsubscribable-instance ledger (CL-A + CL-E):
                identity pre-check, QueryAvailableInstances ledger, regional
                DescribeInstances sweep, join, charge-type/expiry/5-day-window
                interpretation and per-instance refund-path guidance.
  --estimate    Reference amount estimation (CL-B): billing-cycle instance
                bills (QueryInstanceBill + DescribeInstanceBill) plus
                currently effective cash coupons (QueryCashCoupons). The
                output ALWAYS carries the dual caliber:
                  ESTIMATE=<consumed reference figure> /
                  AUTHORITATIVE=<value shown on the refund page>.
  --rules       Fixed refund-rule answers with provenance (CL-C/CL-D):
                --list-topics or --topic <key>. No cloud calls.
  --checklist   Mandatory pre-submission notice: five-point refund notice +
                six-item confirmation template (R2 gate / CL-F). No cloud
                calls.

Common flags: --json | --profile <name> | --region <id> (inventory scope)
              | --instance-id <id> | --billing-cycle <YYYY-MM> | --reason <t>

Exit codes: 0 = conclusion produced (STATUS OK or DEGRADED), 1 = no usable
conclusion (STATUS FAIL), 2 = argparse usage error only.
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
from typing import Any, Optional

import _cli
from _constants import (
    DEFAULT_SCAN_REGIONS,
    ECS_PAGE_SIZE,
    ECS_PRODUCT_CODE,
    FIVE_POINT_NOTICE,
    HANDOFF_SKILLS,
    ID_PREFIX_TRIAGE,
    MANUAL_ENTRIES,
    OFFICIAL_DOCS,
    PAGE_SIZE,
    RULE_TOPICS,
    SIX_ITEM_CONFIRMATION,
)

# Instance IDs / order ids accepted from the CLI are strictly validated to a
# conservative resource-ID charset before being passed to any query.
_INSTANCE_ID_RE = re.compile(r"^(?:i|spn|rm)-[A-Za-z0-9-]{4,64}$")
_BILLING_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_FIVE_DAY_WINDOW_DAYS = 5


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------

def mask_order_id(value: str) -> str:
    """Mask an order id to the ticket-relayed shape 20**...**85.

    Pure function; keeps the first two and last two characters. Short
    values (<5 chars) are fully masked. Never raises.
    """
    s = str(value or "").strip()
    if not s:
        return ""
    if len(s) < 5:
        return "****"
    return f"{s[:2]}**...**{s[-2:]}"


def parse_iso_utc(value: str) -> Optional[datetime]:
    """Parse an ISO8601 UTC timestamp like 2026-09-03T23:59:59Z (return None
    on any parse failure; callers must degrade, never guess)."""
    s = str(value or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def days_between(then: datetime, now: datetime) -> int:
    """Whole days from `then` to `now` (may be negative for future dates)."""
    return (now - then).days


def _first(d: dict, keys: list[str], default: Any = "") -> Any:
    """Return the first present, non-empty value among `keys`."""
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _amount(d: dict, keys: list[str]) -> float:
    """Sum-safe numeric extraction (BSS amounts arrive as float or
    numeric-string); anything unparseable counts as 0.0, never guessed."""
    v = _first(d, keys, 0)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Identity pre-check (decision-tree step 1)
# ---------------------------------------------------------------------------

def identity_preflight(profile: Optional[str]) -> tuple[str, str, list[dict]]:
    """Return (uid, identity_type, errors). uid is "" on failure."""
    errors: list[dict] = []
    _cli.check_cli_available()
    try:
        body = _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as e:
        errors.append({
            "step": "sts:GetCallerIdentity",
            "code": e.code or "CredentialChainFailure",
            "message": str(e),
            "category": "credential" if not e.code else "api",
        })
        print(f"[WARN] identity pre-check failed: {e}", file=sys.stderr)
        return "", "", errors
    return (str(body.get("AccountId") or ""),
            str(body.get("IdentityType") or "Unknown"), errors)


# ---------------------------------------------------------------------------
# Mode: --inventory (CL-A eligibility listing + CL-E prefix triage)
# ---------------------------------------------------------------------------

def fetch_bss_ledger(profile: Optional[str], errors: list[dict]) -> list[dict]:
    """QueryAvailableInstances (refund-side order ledger), full PageNum
    pagination. Response shape verified live: a flat list under
    Data.InstanceList with keys InstanceID / CreateTime / EndTime /
    ProductCode / Region / RenewStatus / Status / SubscriptionType. The
    server-side ProductCode filter proved unreliable on live calls (foreign
    product rows came back), so rows are ADDITIONALLY filtered client-side
    to ProductCode == "ecs"."""
    try:
        raw = _cli.paginate_page_num(
            "bssopenapi", "QueryAvailableInstances",
            {"ProductCode": ECS_PRODUCT_CODE},
            items_path=["Data", "InstanceList"],
            page_size=PAGE_SIZE, profile=profile,
        )
        return [r for r in raw if isinstance(r, dict)
                and str(_first(r, ["ProductCode"], "")).lower() == ECS_PRODUCT_CODE]
    except _cli.CliError as e:
        errors.append({"step": "bssopenapi:QueryAvailableInstances",
                       "code": e.code, "message": str(e),
                       "category": _error_category(e.code)})
        print(f"[WARN] QueryAvailableInstances failed: {e}", file=sys.stderr)
        return []


def fetch_ecs_instances(profile: Optional[str], regions: list[str],
                        errors: list[dict]) -> tuple[list[dict], list[str]]:
    """DescribeInstances for the requested regions (page-number
    pagination). Returns (instances, failed_regions)."""
    instances: list[dict] = []
    failed: list[str] = []
    for region in regions:
        try:
            rows = _cli.paginate_page_num(
                "ecs", "DescribeInstances",
                {"RegionId": region},
                items_path=["Instances", "Instance"],
                page_size=ECS_PAGE_SIZE, profile=profile,
                page_key="PageNumber",
            )
            for row in rows:
                row["_RegionId"] = region
                instances.append(row)
        except _cli.CliError as e:
            failed.append(region)
            errors.append({"step": f"ecs:DescribeInstances[{region}]",
                           "code": e.code, "message": str(e),
                           "category": _error_category(e.code)})
            print(f"[WARN] DescribeInstances({region}) failed: {e}",
                  file=sys.stderr)
    return instances, failed


def _error_category(code: str) -> str:
    """Classify an API error code into the report's failure categories
    (permission / parameter / throttling / internal). Permission markers
    anchor on the platform literals NoPermission / ImplicitDeny."""
    c = (code or "").lower()
    if ("nopermission" in c or "implicitdeny" in c or "deny" in c
            or "denied" in c or "unauthorized" in c):
        return "permission"
    if "parameter" in c or "missing" in c or "invalid" in c:
        return "parameter"
    if "throttl" in c:
        return "throttling"
    return "internal"


def interpret_row(ecs_row: dict, bss_rows_by_id: dict[str, dict],
                  now: datetime) -> dict:
    """Merge the ECS live view and the BSS order-ledger view of one instance
    into the report row with refund-path guidance."""
    iid = str(_first(ecs_row, ["InstanceId", "InstanceID"], ""))
    charge = str(_first(ecs_row, ["InstanceChargeType"], ""))
    status = str(_first(ecs_row, ["Status"], ""))
    bss = bss_rows_by_id.get(iid.lower(), {})
    created = parse_iso_utc(str(_first(
        ecs_row, ["CreationTime", "InstanceCreationTime", "StartTime"],
        _first(bss, ["CreateTime"], ""))))

    days_since_creation = days_between(created, now) if created else None
    row = {
        "instance_id": iid,
        "instance_name": str(_first(ecs_row, ["InstanceName"], "")),
        "region": str(_first(ecs_row, ["_RegionId", "RegionId"],
                             _first(bss, ["Region"], ""))),
        "status": status,
        "charge_type": charge,
        "creation_time": str(_first(
            ecs_row, ["CreationTime", "InstanceCreationTime"],
            _first(bss, ["CreateTime"], ""))),
        "expired_time": str(_first(ecs_row, ["ExpiredTime"], "")),
        "bss_end_time": str(_first(bss, ["EndTime"], "")),
        "bss_renew_status": str(_first(bss, ["RenewStatus"], "")),
        "bss_subscription_type": str(_first(bss, ["SubscriptionType"], "")),
        "source": "live-ecs + order-ledger" if bss else "live-ecs",
    }
    if charge == "PrePaid":
        if days_since_creation is not None and 0 <= days_since_creation <= _FIVE_DAY_WINDOW_DAYS:
            row["refund_path"] = (
                "subscription instance created within the five-day window -- "
                "potentially eligible for the five-day no-reason self refund; "
                "FINAL eligibility and amount are shown only on the refund "
                "page (the account-level one-instance-per-calendar-year limit "
                "has no query API)")
        else:
            row["refund_path"] = (
                "subscription instance outside the five-day window -- "
                "non-full refund path (residual value, computed by the "
                "refund page); the API layer cannot state the amount")
    elif charge == "PostPaid":
        row["refund_path"] = (
            "pay-as-you-go instance -- nothing to refund; billing stops by "
            "releasing it manually in the ECS console (stop is NOT release: "
            "disks / public IP / image keep charging; release removes the "
            "instance and, with the default 'release disk with instance' "
            "switch, its disks -- snapshot first, because a disk survives only "
            "when that switch is off)")
    else:
        row["refund_path"] = ("charge type not reported by the API -- verify "
                              "on the console before any refund statement")
    return row


def mode_inventory(args, out: dict) -> None:
    """CL-A: account-scoped unsubscribable-instance ledger."""
    errors: list[dict] = out["errors"]
    uid, idtype, id_errors = identity_preflight(args.profile)
    errors.extend(id_errors)
    if not uid:
        out["status"] = "FAIL"
        out["next_action"] = ("fix the aliyun CLI credential chain "
                              "(run `aliyun sts get-caller-identity`), then rerun "
                              "--inventory; never pass AK/SK manually")
        return
    out["identity"] = {"uid": uid, "identity_type": idtype}

    iid = args.instance_id or ""
    if iid and not _INSTANCE_ID_RE.match(iid):
        errors.append({"step": "input-validation", "code": "InvalidParameter",
                       "category": "parameter",
                       "message": f"instance id {iid!r} rejected by charset guard"})
        out["status"] = "FAIL"
        out["next_action"] = ("re-supply --instance-id with a valid resource "
                              "id (i-... / spn-... / rm-...)")
        return
    prefix = iid.split("-", 1)[0] + "-" if iid else ""
    if prefix in ID_PREFIX_TRIAGE and prefix != "i-":
        triage = ID_PREFIX_TRIAGE[prefix]
        out["object_triage"] = {"id": iid, "kind": triage["kind"],
                                "route": triage["route"]}
        out["summary_lines"].append(
            f"Object {iid} is a {triage['kind']}: {triage['route']}")
        out["summary_lines"].append(
            "This skill queries and explains only; commercial actions on "
            "non-ECS objects go to the owning product line's human ticket.")
        out["status"] = "DEGRADED"
        out["next_action"] = ("relay the triage route; for savings-plan rule "
                              "text run --rules --topic savings-plan-no-unsubscribe")
        return

    regions = [args.region] if args.region else list(DEFAULT_SCAN_REGIONS)
    out["auto_filled"] = []
    if not args.region:
        out["auto_filled"].append(
            f"region: none given -- swept {len(regions)} common regions "
            f"({', '.join(regions)}); pass --region to narrow")

    bss_rows = fetch_bss_ledger(args.profile, errors)
    bss_by_id = {str(_first(r, ["InstanceId", "InstanceID"], "")).lower(): r
                 for r in bss_rows if isinstance(r, dict)}
    ecs_rows, failed_regions = fetch_ecs_instances(args.profile, regions, errors)

    if iid:
        ecs_rows = [r for r in ecs_rows
                    if str(_first(r, ["InstanceId", "InstanceID"], "")).lower() == iid.lower()]
        if not ecs_rows:
            out["summary_lines"].append(
                f"Instance {iid} was NOT found under account UID {uid} in the "
                "scanned regions. First suspect account confusion (the #1 "
                "dead-loop root cause): ask the customer to verify the buying "
                f"account and check the order list page {MANUAL_ENTRIES['order_list']} "
                "(showing ALL orders incl. expired ones).")

    rows = [interpret_row(r, bss_by_id, datetime.now(timezone.utc))
            for r in ecs_rows if isinstance(r, dict)]
    # Order-side subscription records with no live ECS hit (e.g. the instance
    # lives outside the scan scope) must still be listed -- the refund track
    # cannot miss a prepaid order. Live-verified field: SubscriptionType ==
    # "Subscription".
    now = datetime.now(timezone.utc)
    live_ids = {r["instance_id"].lower() for r in rows}
    for r in bss_rows:
        rid = str(_first(r, ["InstanceID", "InstanceId"], ""))
        if not rid or rid.lower() in live_ids or not rid.startswith("i-"):
            continue
        if str(_first(r, ["SubscriptionType"], "")) != "Subscription":
            continue
        created = parse_iso_utc(str(_first(r, ["CreateTime"], "")))
        days = days_between(created, now) if created else None
        if days is not None and 0 <= days <= _FIVE_DAY_WINDOW_DAYS:
            path = ("subscription order visible in the account ledger, "
                    "created within the five-day window -- possibly "
                    "five-day no-reason eligible; final eligibility and "
                    "amount only on the refund page")
        elif days is not None:
            path = ("subscription order visible in the account ledger, "
                    "outside the five-day window -- non-full refund path; "
                    "amount only on the refund page")
        else:
            path = ("subscription order in the ledger; creation date "
                    "unparseable -- eligibility only on the refund page")
        rows.append({
            "instance_id": rid,
            "instance_name": "",
            "region": str(_first(r, ["Region"], "(order-side only)")),
            "status": str(_first(r, ["Status"], "")),
            "charge_type": "PrePaid",
            "creation_time": str(_first(r, ["CreateTime"], "")),
            "expired_time": "",
            "bss_end_time": str(_first(r, ["EndTime"], "")),
            "bss_renew_status": str(_first(r, ["RenewStatus"], "")),
            "bss_subscription_type": "Subscription",
            "source": "order-ledger-only",
            "refund_path": path,
        })
    out["instances"] = rows
    out["bss_ledger_count"] = len(bss_rows)
    out["failed_regions"] = failed_regions

    pre = [r for r in rows if r["charge_type"] == "PrePaid"]
    post = [r for r in rows if r["charge_type"] == "PostPaid"]
    out["summary_lines"].append(
        f"Account UID {uid} ({idtype}): {len(rows)} live ECS instance(s) "
        f"scanned -- {len(pre)} subscription (refund-track), "
        f"{len(post)} pay-as-you-go (release-track, no refund).")
    out["summary_lines"].append(
        "No API exists to show whether an unsubscription REQUEST was already "
        "submitted (not in this skill's read whitelist): never confirm 'your "
        "refund is in progress'; check the refund center and order list pages.")
    out["summary_lines"].append(
        f"Manual self-service entry (customer submits, not this skill): "
        f"{MANUAL_ENTRIES['self_refund']}")
    out["summary_lines"].append(
        "Before any submission the FULL five-point notice must be relayed: "
        "run --checklist and paste it verbatim.")

    bss_only = sorted(set(bss_by_id) - {r["instance_id"].lower() for r in rows})
    if bss_only:
        out["summary_lines"].append(
            f"Order-side ledger carries {len(bss_only)} instance id(s) with no "
            "live ECS record (already released, or in a region not swept).")

    core_ok = bool(bss_rows) or bool(ecs_rows) or not failed_regions
    if not core_ok and errors:
        out["status"] = "FAIL"
        out["next_action"] = "resolve the failing queries (see errors[]), then rerun"
    elif errors or failed_regions:
        out["status"] = "DEGRADED"
        out["next_action"] = ("report the instances found; name every failed "
                              "region/query as a limitation; rerun with "
                              "--region if a region was missed")
    else:
        out["status"] = "OK"
        out["next_action"] = ("for an amount question run --estimate; before "
                              "any refund submission output the --checklist "
                              "notice verbatim")


# ---------------------------------------------------------------------------
# Mode: --estimate (CL-B reference amounts, dual caliber)
# ---------------------------------------------------------------------------

def current_billing_cycle(now: datetime) -> str:
    return now.strftime("%Y-%m")


def mode_estimate(args, out: dict) -> None:
    """CL-B: consumed-amount reference for a billing cycle."""
    errors: list[dict] = out["errors"]
    now = datetime.now(timezone.utc)
    cycle = args.billing_cycle or current_billing_cycle(now)
    if not _BILLING_CYCLE_RE.match(cycle):
        errors.append({"step": "input-validation", "code": "InvalidParameter",
                       "category": "parameter",
                       "message": f"BillingCycle {cycle!r} must be YYYY-MM"})
        out["status"] = "FAIL"
        out["next_action"] = "rerun with --billing-cycle YYYY-MM"
        return
    out["billing_cycle"] = cycle
    if not args.billing_cycle:
        out["auto_filled"].append(
            f"billing-cycle: defaulted to the current month ({cycle}); "
            "declare this in the report")

    uid, idtype, id_errors = identity_preflight(args.profile)
    errors.extend(id_errors)
    if not uid:
        out["status"] = "FAIL"
        out["next_action"] = ("fix the aliyun CLI credential chain "
                              "(run `aliyun sts get-caller-identity`), then rerun "
                              "--estimate; never pass AK/SK manually")
        return
    out["identity"] = {"uid": uid, "identity_type": idtype}

    base = {"BillingCycle": cycle, "ProductCode": ECS_PRODUCT_CODE}
    iid = args.instance_id or ""
    if iid and not _INSTANCE_ID_RE.match(iid):
        errors.append({"step": "input-validation", "code": "InvalidParameter",
                       "category": "parameter",
                       "message": f"instance id {iid!r} rejected by charset guard"})
        out["status"] = "FAIL"
        out["next_action"] = "re-supply --instance-id with a valid i-... id"
        return
    if iid:
        base["InstanceID"] = iid

    # Per-instance bill rows (NextToken pagination).
    rows: list[dict] = []
    try:
        rows = _cli.paginate_next_token(
            "bssopenapi", "DescribeInstanceBill", dict(base),
            items_path=["Data", "Items"], profile=args.profile)
    except _cli.CliError as e:
        errors.append({"step": "bssopenapi:DescribeInstanceBill",
                       "code": e.code, "message": str(e),
                       "category": _error_category(e.code)})
        print(f"[WARN] DescribeInstanceBill failed: {e}", file=sys.stderr)

    # Product-level totals for the cycle (PageNum pagination) -- the two
    # channels cross-check each other.
    totals: list[dict] = []
    try:
        totals = _cli.paginate_page_num(
            "bssopenapi", "QueryInstanceBill",
            {"BillingCycle": cycle, "ProductCode": ECS_PRODUCT_CODE},
            items_path=["Data", "Items"], page_size=PAGE_SIZE,
            profile=args.profile)
    except _cli.CliError as e:
        errors.append({"step": "bssopenapi:QueryInstanceBill",
                       "code": e.code, "message": str(e),
                       "category": _error_category(e.code)})
        print(f"[WARN] QueryInstanceBill failed: {e}", file=sys.stderr)

    # Currently effective cash coupons: these are voided after a refund.
    # Live-verified response shape: list under Data.CashCoupon.
    coupons: list[dict] = []
    try:
        body = _cli.call("bssopenapi", "QueryCashCoupons",
                         {"EffectiveOrNot": True}, profile=args.profile)
        data = body.get("Data") or {}
        got = data.get("CashCoupon") if isinstance(data, dict) else None
        if isinstance(got, dict):
            got = _first(got, ["Coupon"], []) if "Coupon" in got else got
        coupons = [c for c in (got or []) if isinstance(c, dict)]
    except _cli.CliError as e:
        errors.append({"step": "bssopenapi:QueryCashCoupons",
                       "code": e.code, "message": str(e),
                       "category": _error_category(e.code)})
        print(f"[WARN] QueryCashCoupons failed: {e}", file=sys.stderr)

    # Amount fields verified live on DescribeInstanceBill rows: PretaxAmount
    # / PretaxGrossAmount / AfterDiscountAmount / InvoiceDiscount /
    # DeductedByCoupons (there is NO PaymentAmount field on these rows --
    # never sum a hallucinated one).
    per_instance: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        key = str(_first(r, ["InstanceID", "InstanceId"], "(unspecified instance)"))
        rec = per_instance.setdefault(key, {
            "instance_id": key,
            "subscription_type": str(_first(r, ["SubscriptionType"], "")),
            "pretax_gross": 0.0, "invoice_discount": 0.0,
            "pretax_amount": 0.0, "after_discount": 0.0,
            "deducted_by_coupons": 0.0,
            "order_ids": set(),
        })
        rec["pretax_gross"] += _amount(r, ["PretaxGrossAmount"])
        rec["invoice_discount"] += _amount(r, ["InvoiceDiscount"])
        rec["pretax_amount"] += _amount(r, ["PretaxAmount"])
        rec["after_discount"] += _amount(r, ["AfterDiscountAmount"])
        rec["deducted_by_coupons"] += _amount(r, ["DeductedByCoupons"])
        oid = _first(r, ["OrderID", "OrderId"], "")
        if oid:
            rec["order_ids"].add(mask_order_id(str(oid)))

    for rec in per_instance.values():
        rec["order_ids"] = sorted(rec["order_ids"])  # set -> JSON-safe list
        for k, v in rec.items():
            if isinstance(v, float):
                rec[k] = round(v, 2)
    out["instance_bills"] = sorted(per_instance.values(),
                                   key=lambda x: x["instance_id"])
    out["cycle_totals"] = [
        {"product": str(_first(t, ["ProductCode", "ProductName"], "")),
         "subscription_type": str(_first(t, ["SubscriptionType"], "")),
         "pretax_amount": round(_amount(t, ["PretaxAmount"]), 2),
         "after_discount": round(_amount(t, ["AfterDiscountAmount"]), 2)}
        for t in totals if isinstance(t, dict)]
    out["cash_coupons_at_risk"] = [
        {"coupon_id": str(_first(c, ["CouponId", "Id", "CouponNo"], "")),
         "balance": _first(c, ["Balance"], ""),
         "nominal_value": _first(c, ["NominalValue", "Amount"], ""),
         "expiry_time": str(_first(c, ["ExpiryTime", "EndTime"], ""))}
        for c in coupons]

    total_pretax = round(sum(r["pretax_amount"] for r in per_instance.values()), 2)
    out["amount_caliber"] = {
        "ESTIMATE": (f"consumed ECS bill amount (payable, pre-tax) in {cycle} "
                     f"under UID {uid}: {total_pretax} CNY (reference "
                     f"numerator only -- what was already spent)"),
        "AUTHORITATIVE": ("the exact refundable residual value is computed by "
                          "the system from remaining duration and config price "
                          "difference and is shown ONLY on the refund page; "
                          "no read API exposes it"),
    }
    out["summary_lines"].append(
        f"Consumed-amount reference for {cycle} (account UID {uid}): "
        f"{total_pretax} CNY across {len(per_instance)} billing instance(s).")
    out["summary_lines"].append(
        "AMOUNT CALIBER (mandatory): "
        f"ESTIMATE={total_pretax} CNY is ALREADY-CONSUMED context only. "
        "AUTHORITATIVE refund value = the figure shown on the refund page. "
        "Never present the estimate as 'how much you get back'.")
    if out["cash_coupons_at_risk"]:
        out["summary_lines"].append(
            f"{len(out['cash_coupons_at_risk'])} currently effective cash "
            "coupon(s) listed: after a refund, attached gifts (vouchers, "
            "coupons, extended service periods) are voided and cleared -- "
            "warn the customer before submission.")
    else:
        out["summary_lines"].append(
            "No currently effective cash coupon was listed (or the coupon "
            "query degraded; see errors[]).")
    out["summary_lines"].append(
        f"Customer-side check: {MANUAL_ENTRIES['self_refund']} shows the exact "
        "refundable amount per instance; confirm it there before submitting.")

    got_bill = bool(rows) or bool(totals)
    if not got_bill:
        out["status"] = "FAIL"
        out["next_action"] = ("both bill channels failed (see errors[]); "
                              "verify the BSS read permissions in "
                              "references/ram-policies.md, then rerun")
    elif errors:
        out["status"] = "DEGRADED"
        out["next_action"] = ("relay the partial figures WITH the missing-item "
                              "list (errors[]); refund page stays authoritative")
    else:
        out["status"] = "OK"
        out["next_action"] = ("output the five-point notice (--checklist) "
                              "before the customer submits anything")


# ---------------------------------------------------------------------------
# Modes: --rules and --checklist (CL-C/CL-D/CL-F; knowledge, no cloud calls)
# ---------------------------------------------------------------------------

def rule_topics_with_source(key: str) -> tuple[str, list[str]]:
    topic = RULE_TOPICS[key]
    refs = [OFFICIAL_DOCS[r] for r in topic.get("refs", []) if r in OFFICIAL_DOCS]
    provenance = {
        "official-doc": "Source: official Alibaba Cloud help page (reachable at skill build time).",
        "ticket-statement": ("Source: support-agent wording verified from real "
                             "handled tickets -- no located official page; "
                             "relay as the support position."),
    }[topic["source"]]
    return topic["answer"], [provenance] + [f"Ref: {u}" for u in refs]


def mode_rules(args, out: dict) -> None:
    """CL-C/CL-D: fixed rule answers, each with provenance."""
    if args.topic:
        if args.topic not in RULE_TOPICS:
            out["status"] = "FAIL"
            out["summary_lines"].append(
                f"Unknown topic {args.topic!r}. Available: "
                + ", ".join(sorted(RULE_TOPICS)))
            out["next_action"] = "rerun with --list-topics or a valid --topic"
            return
        answer, src_lines = rule_topics_with_source(args.topic)
        out["topic"] = {"key": args.topic,
                        "question": RULE_TOPICS[args.topic]["question"],
                        "answer": answer, "provenance": src_lines}
        out["summary_lines"].append(
            f"{RULE_TOPICS[args.topic]['question']}\n{answer}")
        for line in src_lines:
            out["summary_lines"].append(line)
        out["status"] = "OK"
        out["next_action"] = ("combine with live data (--inventory/--estimate) "
                              "whenever the customer's case needs numbers")
        return
    out["topics"] = [{"key": k, "question": v["question"], "source": v["source"]}
                     for k, v in sorted(RULE_TOPICS.items())]
    out["summary_lines"].append(
        "Embedded rule corpus (provenance-labeled): "
        + ", ".join(k for k in sorted(RULE_TOPICS)))
    out["status"] = "OK"
    out["next_action"] = "answer with --topic <key>; never paraphrase amounts or limits from memory"


def mode_checklist(args, out: dict) -> None:
    """R2 gate + CL-F: mandatory pre-submission notice and confirmation items."""
    iid = args.instance_id or ""
    if iid and not _INSTANCE_ID_RE.match(iid):
        out["status"] = "FAIL"
        out["next_action"] = "re-supply --instance-id with a valid i-.../spn-.../rm-... id"
        return
    out["notice"] = [f"{title}: {body}" for title, body in FIVE_POINT_NOTICE]
    out["confirmation_items"] = list(SIX_ITEM_CONFIRMATION)
    out["entries"] = dict(MANUAL_ENTRIES)
    out["handoffs"] = dict(HANDOFF_SKILLS)
    if iid:
        prefix = iid.split("-", 1)[0] + "-"
        triage = ID_PREFIX_TRIAGE.get(prefix)
        if triage:
            out["object_triage"] = {"id": iid, "kind": triage["kind"],
                                    "route": triage["route"]}
    if args.reason:
        out["refund_reason"] = args.reason

    out["summary_lines"].append(
        "MANDATORY five-point notice (output in full BEFORE guiding any "
        "unsubscription submission):")
    out["summary_lines"] += [f"  {i+1}) {line}" for i, line in enumerate(out["notice"])]
    out["summary_lines"].append(
        "Six-item per-line confirmation the CUSTOMER must reply to "
        "(assisted/special-approval path only; the customer clicks the "
        "confirmation tool themselves -- this skill never submits):")
    out["summary_lines"] += [f"  [{i+1}] {item}"
                             for i, item in enumerate(out["confirmation_items"])]
    out["summary_lines"].append(
        "Data-retention warning: a refund puts the instance in the 'expired "
        "after refund' state, and retention is per resource -- vCPU, memory and "
        "the fixed public IP are released within 24 HOURS, cloud disks within "
        "15 DAYS (kept only if 'release disk with instance' is off). Snapshot "
        "before submitting; renewing the unsubscribed instance manually in the "
        "ECS console before the resources are released can still rescue it, but "
        "data loss or a changed fixed public IP may remain. Stop is NOT "
        "release.")
    out["summary_lines"].append(
        "Amount caliber: any figure relayed must carry "
        "ESTIMATE=<reference> / AUTHORITATIVE=<refund-page value>; the page "
        "value is the only promise.")
    out["status"] = "OK"
    out["next_action"] = ("paste the notice + checklist verbatim into the "
                          "reply; collect the six confirmations before "
                          "submitting a manual unsubscription request")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_unsubscribe_refund.py",
        description=("ECS unsubscription & refund guide -- read-only "
                     "eligibility inventory, reference amounts, rule corpus "
                     "and pre-submission checklist. Never submits anything; "
                     "never calls any mutating API."),
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inventory", action="store_true",
                       help="account-scoped unsubscribable-instance ledger")
    modes.add_argument("--estimate", action="store_true",
                       help="consumed-amount reference for a billing cycle")
    modes.add_argument("--rules", action="store_true",
                       help="answer from the embedded refund-rule corpus")
    modes.add_argument("--checklist", action="store_true",
                       help="five-point notice + six-item confirmation template")
    parser.add_argument("--topic", default=None, help="rule topic key (with --rules)")
    parser.add_argument("--list-topics", action="store_true",
                        help="list rule topics (with --rules)")
    parser.add_argument("--instance-id", default=None,
                        help="i-.../spn-.../rm-... id to focus on")
    parser.add_argument("--region", default=None,
                        help="single region scope for --inventory (default: sweep common regions)")
    parser.add_argument("--billing-cycle", default=None,
                        help="YYYY-MM billing cycle for --estimate (default: current month, declared)")
    parser.add_argument("--reason", default=None,
                        help="customer refund reason line (with --checklist)")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true", help="JSON output")
    return parser


def render_text(out: dict) -> None:
    print("=" * 72)
    print(f" ECS Unsubscribe & Refund -- mode: {out['mode']}")
    print(f" session-id (UA): {_cli.session_id()}")
    ident = out.get("identity") or {}
    if ident.get("uid"):
        print(f" account UID: {ident['uid']} ({ident.get('identity_type', '')})")
    print("=" * 72)
    for line in out["auto_filled"]:
        print(f"[auto-filled] {line}")
    if out.get("object_triage"):
        t = out["object_triage"]
        print(f"[triage] {t['id']} -> {t['kind']}: {t['route']}")
    for row in out.get("instances", []):
        print(f"\n  {row['instance_id']}  ({row['region']})  {row['status']}")
        print(f"    charge={row['charge_type']}  created={row['creation_time']}  "
              f"expired={row['expired_time']}")
        print(f"    refund path: {row['refund_path']}")
    for rec in out.get("instance_bills", []):
        print(f"\n  bill {rec['instance_id']}  [{rec['subscription_type']}]  "
              f"orders={', '.join(rec['order_ids']) or '-'}")
        print(f"    pretax={rec['pretax_amount']}  after-discount={rec['after_discount']}  "
              f"coupon-deductions={rec['deducted_by_coupons']}")
    cal = out.get("amount_caliber")
    if cal:
        print("\n  AMOUNT CALIBER (mandatory, relay both lines):")
        print(f"    ESTIMATE     = {cal['ESTIMATE']}")
        print(f"    AUTHORITATIVE = {cal['AUTHORITATIVE']}")
    topic = out.get("topic")
    if topic:
        print(f"\n  Q: {topic['question']}\n  A: {topic['answer']}")
        for line in topic["provenance"]:
            print(f"  {line}")
    if out.get("topics"):
        print("\n  Topics: " + ", ".join(t["key"] for t in out["topics"]))
    for line in out["summary_lines"]:
        print(line if line.startswith(" ") else line)
    if out.get("failed_regions"):
        print(f"[degraded] failed regions: {', '.join(out['failed_regions'])}")
    if out["errors"]:
        print("\nErrors (recorded, run continued):")
        for e in out["errors"]:
            print(f"  [{e.get('category', 'api')}] {e.get('step')}: "
                  f"{e.get('code') or '-'} {str(e.get('message'))[:200]}")
    print(f"\nSTATUS: {out['status']}")
    print(f"NEXT_ACTION: {out['next_action']}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.rules and not (args.topic or args.list_topics):
        parser.error("--rules requires --topic <key> or --list-topics")

    mode = ("inventory" if args.inventory else
            "estimate" if args.estimate else
            "rules" if args.rules else "checklist")
    out: dict[str, Any] = {
        "skill": "area:unsubscribe-refund",
        "mode": mode,
        "status": "OK",
        "auto_filled": [],
        "summary_lines": [],
        "errors": [],
        "next_action": "",
    }
    if mode == "inventory":
        mode_inventory(args, out)
    elif mode == "estimate":
        mode_estimate(args, out)
    elif mode == "rules":
        mode_rules(args, out)
    else:
        mode_checklist(args, out)

    if args.json:
        printable = {k: v for k, v in out.items() if k != "summary_lines"}
        printable["summary"] = out["summary_lines"]
        print(json.dumps(printable, ensure_ascii=False, indent=2, default=str))
    else:
        render_text(out)

    sys.exit(0 if out["status"] in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
