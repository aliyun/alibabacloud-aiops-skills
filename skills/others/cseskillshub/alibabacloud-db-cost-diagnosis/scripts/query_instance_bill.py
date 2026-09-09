#!/usr/bin/env python3
"""
query_instance_bill.py -- Query the bill detail of a single database instance
==============================================================================
SECURITY: READ-ONLY. This script only queries BSS billing APIs
(DescribeInstanceBill / DescribeSplitItemBill). It never reads or writes any
AccessKey / Secret; credentials are resolved by the aliyun CLI default
credential chain. Never pass AK/SK to this script.

Dual-audience output:
  - Default (human-readable): a per-billing-item cost table plus a
    plain-language "Summary" section (what was queried / key findings /
    suggested next steps), written for non-technical readers.
  - --json (for Agents): the full detail fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields; empty or failed
    queries still emit these fields so downstream stages can consume them.

Usage:
    python3 query_instance_bill.py --instance-id <ID> --billing-cycle YYYY-MM \
        [--split-item] [--granularity MONTHLY|DAILY] \
        [--billing-date YYYY-MM-DD] [--json]

Granularity:
    MONTHLY (default): monthly summary; fast, fits almost every scenario.
    DAILY: daily breakdown; heavier, only use it to drill down a specific
           anomalous month. DAILY requires --billing-date YYYY-MM-DD (BSS
           mandates BillingDate for daily bills; it must fall inside the
           billing cycle).

Consistency note: DescribeSplitItemBill data can lag briefly after usage is
recorded; when a split-item query returns zero rows the script retries once
before concluding the instance has no charges.

Full pagination: all NextToken pages are fetched (up to the MAX_PAGES
guardrail), unlike first-page-only queries.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime

import _cli
from _constants import INSTANCE_ID_PREFIXES_ORDERED, INSTANCE_ID_PREFIX_MAP

# Billing item label used when an item carries no billing-item name.
# Kept distinct from the table's TOTAL row to avoid visual collision.
_TOTAL_LABEL = "(unspecified item)"
_UNKNOWN_PRODUCT = "Unknown product"

# Wait before the single empty-result retry of a split-item query (seconds).
_SPLIT_ITEM_RETRY_WAIT_S = 5

_BILLING_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# BSS stores instance bill rows under two ID shapes: Subscription rows keep
# the bare instance ID, while PayAsYouGo rows are stored region-qualified as
# "<instance-id>;<region-id>" (verified on real bills). DescribeInstanceBill
# / DescribeSplitItemBill match the InstanceID parameter EXACTLY, so a bare
# ID silently misses the region-qualified rows (a query for a running
# pay-as-you-go instance returns zero rows). The bare ID is always tried
# first, then the region-suffixed candidates below are probed in order; one
# instance's rows live under at most one region-qualified form, so the scan
# stops at the first suffixed hit.
_INSTANCE_ID_REGION_SUFFIXES = (
    ";cn-hangzhou", ";cn-beijing", ";cn-shanghai", ";cn-shenzhen",
    ";cn-qingdao", ";cn-zhangjiakou", ";cn-huhehaote", ";cn-chengdu",
    ";cn-wulanchabu", ";cn-guangzhou",
)


def candidate_instance_ids(instance_id: str) -> list[str]:
    """Ordered InstanceID candidates for the BSS exact-match filter.

    The bare ID always comes first; region-qualified variants are appended
    only for bare input. An already region-qualified ID (containing ';') or
    an empty string is returned verbatim as the single candidate.
    """
    if not instance_id or ";" in instance_id:
        return [instance_id]
    return [instance_id] + [instance_id + suffix
                            for suffix in _INSTANCE_ID_REGION_SUFFIXES]


# Inline boundary assertions (normal / boundary / invalid):
assert candidate_instance_ids("rm-abc")[0] == "rm-abc"
assert candidate_instance_ids("rm-abc")[1] == "rm-abc;cn-hangzhou"
assert len(candidate_instance_ids("rm-abc")) == 11
assert candidate_instance_ids("rm-abc;cn-beijing") == ["rm-abc;cn-beijing"]
assert candidate_instance_ids("") == [""]


def _billing_date_type(value: str) -> str:
    """argparse type validator: --billing-date must be YYYY-MM-DD."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --billing-date '{value}': expected format YYYY-MM-DD")
    return value


def _billing_cycle_type(value: str) -> str:
    """argparse type validator: --billing-cycle must be YYYY-MM."""
    if not _BILLING_CYCLE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --billing-cycle '{value}': expected format YYYY-MM "
            f"(e.g. 2026-07)")
    return value


def detect_product(instance_id: str) -> tuple[str, str]:
    """Identify the DB product from the instance-id prefix.

    Longer / more specific prefixes are matched first, so "rm-" wins over the
    generic "r-" prefix. Returns (product_code, display_name).
    """
    for prefix in INSTANCE_ID_PREFIXES_ORDERED:
        if instance_id.startswith(prefix):
            return INSTANCE_ID_PREFIX_MAP[prefix]
    return "", _UNKNOWN_PRODUCT


def _fetch_bill_items_once(
    instance_id: str,
    billing_cycle: str,
    action: str,
    granularity: str,
    billing_date: str | None,
    profile: str | None,
) -> list[dict]:
    """One full-pagination bill query for a single exact InstanceID."""
    params = {
        "BillingCycle": billing_cycle,
        "InstanceID": instance_id,
        "Granularity": granularity,
        "BillingDate": billing_date,
    }
    return _cli.paginate_next_token("bssopenapi", action, params,
                                    profile=profile)


def fetch_bill_items(
    instance_id: str,
    billing_cycle: str,
    split_item: bool,
    granularity: str,
    billing_date: str | None = None,
    profile: str | None = None,
) -> list[dict]:
    """Fetch ALL bill items of the instance for the cycle (full pagination).

    Uses DescribeSplitItemBill when --split-item is set (per split item /
    billing item), otherwise DescribeInstanceBill. With Granularity=DAILY the
    BillingDate parameter is mandatory for both APIs (validated upstream).

    InstanceID probe order: the bare ID first, then the region-qualified
    "<id>;<region>" candidates (BSS stores pay-as-you-go rows under that
    form and filters by exact match); rows found under a region-qualified
    ID are merged with any bare-ID rows. The probe stops right after the
    first region-qualified hit because one instance's rows live under at
    most one such form.

    Split-item data can lag briefly (eventual consistency); when a
    split-item query comes back empty, it is retried once after a short wait
    before the result is trusted.
    """
    action = "DescribeSplitItemBill" if split_item else "DescribeInstanceBill"
    items = _probe_instance_id_candidates(
        instance_id, billing_cycle, action, granularity, billing_date,
        profile)
    if not items and split_item:
        print(f"[WARN] split-item bill returned 0 rows; retrying once after "
              f"{_SPLIT_ITEM_RETRY_WAIT_S}s (split-item data can lag briefly)",
              file=sys.stderr)
        time.sleep(_SPLIT_ITEM_RETRY_WAIT_S)
        items = _probe_instance_id_candidates(
            instance_id, billing_cycle, action, granularity, billing_date,
            profile)
    return items


def _probe_instance_id_candidates(
    instance_id: str,
    billing_cycle: str,
    action: str,
    granularity: str,
    billing_date: str | None,
    profile: str | None,
) -> list[dict]:
    """Run the candidate-ID scan once and return the merged bill rows."""
    items: list[dict] = []
    for candidate in candidate_instance_ids(instance_id):
        found = _fetch_bill_items_once(candidate, billing_cycle, action,
                                       granularity, billing_date, profile)
        if not found:
            continue
        items.extend(found)
        if candidate != instance_id:
            print(f"[_] bill rows matched under the region-qualified ID "
                  f"{candidate} (BSS stores pay-as-you-go rows as "
                  f"<instance-id>;<region-id>)", file=sys.stderr)
            break  # one instance's rows share at most one region form
    return items


def _amount(item: dict, key: str) -> float:
    """Read a numeric amount field from a bill item (defensive)."""
    try:
        return float(item.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def aggregate_by_billing_item(items: list[dict]) -> tuple[dict, dict, str]:
    """Aggregate bill items by billing item.

    Returns (per_item_totals, grand_totals, subscription_type). Each totals
    dict holds: original / discount / payment / cash.
    """
    bill_map: dict[str, dict[str, float]] = {}
    totals = {"original": 0.0, "discount": 0.0, "payment": 0.0, "cash": 0.0}
    subscription_type = items[0].get("SubscriptionType", "") if items else ""

    for item in items:
        key = (item.get("BillingItem") or item.get("SplitItemName")
               or _TOTAL_LABEL)
        # Real BSS payload: PretaxGrossAmount (list price), InvoiceDiscount +
        # DeductedByCoupons (discounts), PretaxAmount (payable after
        # discount); PaymentAmount may be absent until the bill is settled.
        if item.get("PretaxGrossAmount") is not None:
            original = _amount(item, "PretaxGrossAmount")
        else:
            original = _amount(item, "PretaxAmount")
        discount = (_amount(item, "InvoiceDiscount")
                    + _amount(item, "DeductedByCoupons"))
        payment = _amount(item, "PaymentAmount")
        cash = original - discount

        entry = bill_map.setdefault(
            key, {"original": 0.0, "discount": 0.0, "payment": 0.0, "cash": 0.0})
        entry["original"] += original
        entry["discount"] += discount
        entry["payment"] += payment
        entry["cash"] += cash

        totals["original"] += original
        totals["discount"] += discount
        totals["payment"] += payment
        totals["cash"] += cash

    return bill_map, totals, str(subscription_type or "Unknown")


def _dominant_item(bill_map: dict) -> tuple[str, float]:
    """Return (name, original_amount) of the largest billing item."""
    name, values = max(bill_map.items(), key=lambda kv: kv[1]["original"])
    return name, values["original"]


def _build_summary_fields(
    items: list[dict],
    instance_id: str,
    billing_cycle: str,
    granularity: str,
    billing_date: str | None,
    split_item: bool,
    error: str = "",
) -> tuple[str, list[str], list[str]]:
    """Build (summary, key_findings, suggestions) shared by both output
    modes. Covers the normal, empty-data and error cases."""
    scope = f"{billing_cycle}" if granularity == "MONTHLY" \
        else f"{billing_date} (daily drill-down of {billing_cycle})"

    if error:
        return (
            f"The bill query for instance {instance_id} in {scope} failed "
            f"before any data could be read.",
            [f"Query error: {error}"],
            [
                "Check that the CLI credential is configured and has BSS "
                "billing read permission (aliyun configure).",
                "Verify the instance ID and billing cycle, then re-run the "
                "query.",
            ],
        )

    if not items:
        return (
            f"No cost records were found for instance {instance_id} in "
            f"{scope}.",
            [
                f"Instance {instance_id} has no bill rows in {scope}.",
            ],
            [
                "Double-check the instance ID (a released instance keeps its "
                "old ID on historical bills).",
                "Verify the billing cycle; split-item data can also lag by "
                "up to ~48 hours, so re-run later if the window is recent.",
                "If the instance belongs to another account, switch to the "
                "correct credential profile.",
            ],
        )

    bill_map, totals, _ = aggregate_by_billing_item(items)
    name, amount = _dominant_item(bill_map)
    share = (amount / totals["original"] * 100
             if totals["original"] > 0 else 0.0)
    settled = any(item.get("PaymentAmount") is not None for item in items)
    paid_text = (f"{totals['payment']:.2f} CNY actually paid"
                 if settled
                 else "payment has not been settled yet (the bill is "
                      "typically finalized after the cycle ends)")
    findings = [
        f"Total charge in {scope}: {totals['original']:.2f} CNY list "
        f"price; {paid_text}.",
        (f"Largest billing item: \"{name}\" at {amount:.2f} CNY "
         f"({share:.0f}% of the list price)." if len(bill_map) > 1
         else f"All of the charge comes from a single billing item "
              f"(\"{name}\")."),
    ]
    suggestions = [
        (f"To cut cost, review the \"{name}\" item first; it accounts for "
         f"{share:.0f}% of the charge." if len(bill_map) > 1
         else "The charge comes from a single billing item; check whether "
              "the instance spec / usage behind it matches your need."),
    ]
    if not split_item:
        suggestions.append(
            "Re-run with --split-item for a finer per-split-item breakdown.")
    if granularity == "MONTHLY":
        suggestions.append(
            "To see when the charge accrued, re-run with --granularity DAILY "
            "--billing-date <a day in this month>.")
    return (
        f"Queried the bill of instance {instance_id} for {scope}: "
        f"{len(items)} bill row(s) found, total list price "
        f"{totals['original']:.2f} CNY.",
        findings,
        suggestions,
    )


def format_bill_output(
    items: list[dict],
    instance_id: str,
    billing_cycle: str,
    granularity: str,
    billing_date: str | None,
    split_item: bool,
) -> None:
    """Render the human-readable bill table plus the plain-language Summary."""
    product_code, product_name = detect_product(instance_id)

    if not items:
        print(f"[WARN] No bill data found for instance {instance_id} "
              f"in billing cycle {billing_cycle}")
        summary, _findings, suggestions = _build_summary_fields(
            items, instance_id, billing_cycle, granularity, billing_date,
            split_item)
        print("\nSummary")
        print("-------")
        print(f"What was queried : the bill of instance {instance_id} for "
              f"billing cycle {billing_cycle} ({granularity}).")
        print(f"Key finding      : {summary}")
        print("Possible reasons : there was no charge for it in that month; "
              "the instance ID or month may be wrong; or the billing data "
              "has not been produced yet (split-item data can lag ~48 "
              "hours).")
        print("Next steps:")
        for s in suggestions:
            print(f"  - {s}")
        return

    bill_map, totals, subscription_type = aggregate_by_billing_item(items)

    print("Instance Bill Detail")
    print("-" * 56)
    print(f"Instance ID      : {instance_id}")
    print(f"Product          : {product_name}"
          + (f" ({product_code})" if product_code else ""))
    print(f"Billing cycle    : {billing_cycle}")
    print(f"Granularity      : {granularity}")
    print(f"Subscription type: {subscription_type}")
    print(f"Bill items       : {len(items)}")
    print()
    header = (f"| {'Billing Item':<24} | {'Original':>10} | {'Discount':>10} "
              f"| {'Payment':>10} | {'Cash':>10} |")
    print(header)
    print(f"|{'-' * 26}|{'-' * 12}|{'-' * 12}|{'-' * 12}|{'-' * 12}|")

    for name, v in bill_map.items():
        print(f"| {name:<24} | {v['original']:>10.2f} | {v['discount']:>10.2f} "
              f"| {v['payment']:>10.2f} | {v['cash']:>10.2f} |")
    print(f"| {'TOTAL':<24} | {totals['original']:>10.2f} "
          f"| {totals['discount']:>10.2f} | {totals['payment']:>10.2f} "
          f"| {totals['cash']:>10.2f} |")

    # Cost share analysis (items contributing more than 5%).
    if totals["original"] > 0:
        print("\nCost share analysis:")
        ranked = sorted(bill_map.items(),
                        key=lambda kv: kv[1]["original"], reverse=True)
        for name, v in ranked:
            pct = v["original"] / totals["original"] * 100
            if pct > 5:
                bar = "#" * int(pct / 5)
                print(f"  {name:<24} {pct:>5.1f}% {bar}")

    summary, findings, suggestions = _build_summary_fields(
        items, instance_id, billing_cycle, granularity, billing_date,
        split_item)
    print("\nSummary")
    print("-------")
    scope = (f"the whole month of {billing_cycle}"
             if granularity == "MONTHLY"
             else f"a single day ({billing_date}) inside {billing_cycle}")
    print(f"What was queried : the bill of instance {instance_id} for "
          f"{scope} ({'by split item' if split_item else 'by billing item'})."
          )
    print("Key findings:")
    for finding in findings:
        print(f"  - {finding}")
    print("Suggested next steps:")
    for s in suggestions:
        print(f"  - {s}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query the bill detail of a single database instance "
                    "(read-only BSS billing query)",
    )
    parser.add_argument("--instance-id", required=True,
                        help="Instance ID, e.g. rm-xxx / r-xxx / pc-xxx")
    parser.add_argument("--billing-cycle", required=True,
                        type=_billing_cycle_type,
                        help="Billing cycle, format YYYY-MM")
    parser.add_argument("--split-item", action="store_true",
                        help="Use DescribeSplitItemBill (per split item / "
                             "billing item breakdown)")
    parser.add_argument("--granularity", choices=["MONTHLY", "DAILY"],
                        default="MONTHLY",
                        help="MONTHLY (default) or DAILY (heavy; only to "
                             "drill down an anomalous month)")
    parser.add_argument("--billing-date", default=None,
                        type=_billing_date_type,
                        help="Billing date YYYY-MM-DD; REQUIRED when "
                             "--granularity DAILY is used (must fall inside "
                             "--billing-cycle)")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of the table")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    args = parser.parse_args()

    # BSS mandates BillingDate (same month as BillingCycle) for DAILY bills.
    if args.granularity == "DAILY" and not args.billing_date:
        print("[ERROR] --billing-date YYYY-MM-DD is required when "
              "--granularity DAILY is used: BSS DescribeInstanceBill / "
              "DescribeSplitItemBill demand BillingDate for daily bills",
              file=sys.stderr)
        sys.exit(2)
    if (args.billing_date
            and args.billing_date[:7] != args.billing_cycle):
        print(f"[ERROR] --billing-date {args.billing_date} must fall inside "
              f"--billing-cycle {args.billing_cycle} (same month)",
              file=sys.stderr)
        sys.exit(2)

    _cli.check_cli_available()

    print(f"[1/2] Querying bill of instance {args.instance_id} for "
          f"{args.billing_cycle} ({args.granularity}) ...", file=sys.stderr)
    items: list[dict] = []
    query_error = ""
    try:
        items = fetch_bill_items(args.instance_id, args.billing_cycle,
                                 args.split_item, args.granularity,
                                 args.billing_date, args.profile)
    except _cli.CliError as e:
        query_error = str(e)
        print(f"[ERROR] Bill query failed: {e}", file=sys.stderr)

    print(f"[2/2] Fetched {len(items)} bill item(s); rendering output ...",
          file=sys.stderr)

    summary, key_findings, suggestions = _build_summary_fields(
        items, args.instance_id, args.billing_cycle, args.granularity,
        args.billing_date, args.split_item, error=query_error)

    if args.json:
        product_code, product_name = detect_product(args.instance_id)
        bill_map, totals, subscription_type = aggregate_by_billing_item(items)
        result = {
            "instance_id": args.instance_id,
            "product_code": product_code or None,
            "product_name": product_name,
            "billing_cycle": args.billing_cycle,
            "billing_date": args.billing_date,
            "granularity": args.granularity,
            "api": ("DescribeSplitItemBill" if args.split_item
                    else "DescribeInstanceBill"),
            "query_error": query_error or None,
            "subscription_type": subscription_type,
            "item_count": len(items),
            "totals": {k: round(v, 2) for k, v in totals.items()},
            "by_billing_item": {
                name: {k: round(v, 2) for k, v in values.items()}
                for name, values in bill_map.items()
            },
            "items": [
                {
                    "billing_item": item.get("BillingItem"),
                    "split_item_name": item.get("SplitItemName"),
                    "billing_date": item.get("BillingDate"),
                    "subscription_type": item.get("SubscriptionType"),
                    "pretax_gross_amount": item.get("PretaxGrossAmount"),
                    "invoice_discount": item.get("InvoiceDiscount"),
                    "deducted_by_coupons": item.get("DeductedByCoupons"),
                    "pretax_amount": item.get("PretaxAmount"),
                    "after_discount_amount": item.get("AfterDiscountAmount"),
                    "payment_amount": item.get("PaymentAmount"),
                }
                for item in items
            ],
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }
        print(json.dumps(result, indent=2))
        if query_error:
            sys.exit(1)
    else:
        if query_error:
            print("\nSummary")
            print("-------")
            print(f"What was queried : the bill of instance "
                  f"{args.instance_id} for billing cycle "
                  f"{args.billing_cycle}.")
            print(f"Key finding      : the query failed, so no bill data "
                  f"could be read.")
            print("Next steps:")
            for s in suggestions:
                print(f"  - {s}")
            sys.exit(1)
        format_bill_output(items, args.instance_id, args.billing_cycle,
                           args.granularity, args.billing_date,
                           args.split_item)


if __name__ == "__main__":
    main()
