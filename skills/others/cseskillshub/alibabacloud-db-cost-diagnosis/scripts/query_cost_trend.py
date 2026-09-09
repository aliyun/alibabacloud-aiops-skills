#!/usr/bin/env python3
"""
query_cost_trend.py -- Aggregate DB cost trend per product and detect anomalies
================================================================================
SECURITY: READ-ONLY. This script only queries the BSS billing API
(DescribeInstanceBill). It never reads or writes any AccessKey / Secret;
credentials are resolved by the aliyun CLI default credential chain. Never
pass AK/SK to this script.

Dual-audience output:
  - Default (human-readable): a monthly cost trend table plus a
    plain-language "Summary" section (what was queried / key findings /
    suggested next steps), written for non-technical readers.
  - --json (for Agents): the full detail fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields; empty or failed
    queries still emit these fields so downstream stages can consume them.

Usage:
    python3 query_cost_trend.py [--months 6] [--product rds] \
        [--granularity MONTHLY|DAILY] [--billing-date YYYY-MM-DD] [--json]

Granularity:
    MONTHLY (default): monthly summary over the last N cycles; fast, fits
           almost every scenario.
    DAILY: single-day drill-down of ONE --billing-date (YYYY-MM-DD,
           required; BSS mandates BillingDate for daily bills). It issues a
           single API loop for that day only -- it never iterates day by day.

Anomaly rule: a month-over-month increase is flagged when the relative growth
exceeds 20% OR the absolute growth exceeds 100 CNY. When the baseline month
is non-positive (refund / bill adjustment), the percentage is not computed
and the change is judged by the absolute threshold only.

Billing-cycle math: months are computed by exact calendar-month arithmetic
(N months back from the current month), never by a day-count approximation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime

import _cli
from _constants import (
    ALL_DB_PRODUCT_CODES,
    ANOMALY_THRESHOLD_ABS,
    ANOMALY_THRESHOLD_PCT,
    DB_PRODUCT_CODES,
)


def _billing_date_type(value: str) -> str:
    """argparse type validator: --billing-date must be YYYY-MM-DD."""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --billing-date '{value}': expected format YYYY-MM-DD")
    return value


def get_billing_cycles(months: int) -> list[str]:
    """Return the last `months` billing cycles (YYYY-MM), oldest first.

    Uses exact calendar-month arithmetic: the i-th cycle back is derived from
    the current year/month, so there is no drift (unlike day-based offsets).
    """
    now = datetime.now()
    cycles = []
    for i in range(months - 1, -1, -1):
        # Walk back i calendar months.
        total = now.year * 12 + (now.month - 1) - i
        year, month = divmod(total, 12)
        cycles.append(f"{year:04d}-{month + 1:02d}")
    return cycles


def query_monthly_bill(
    billing_cycle: str,
    product_filter: str | None = None,
    granularity: str = "MONTHLY",
    billing_date: str | None = None,
    profile: str | None = None,
) -> tuple[list[dict], list[str]]:
    """Fetch ALL bill items of every DB product for one cycle (full pagination).

    Each product code is queried separately (DescribeInstanceBill with
    ProductCode), following every NextToken page up to the guardrail. With
    Granularity=DAILY the BillingDate parameter is mandatory (validated
    upstream) and the query covers that single day only.

    Per-product degradation: when one product query fails, the failure is
    logged as [WARN] and the remaining products are still queried, so one
    permission gap or exhausted retry never discards the data already
    collected. Returns (items, warnings).
    """
    product_codes = ([product_filter] if product_filter
                     else list(DB_PRODUCT_CODES.keys()))

    all_items: list[dict] = []
    warnings: list[str] = []
    for product_code in product_codes:
        params = {
            "BillingCycle": billing_cycle,
            "ProductCode": product_code,
            "Granularity": granularity,
            "BillingDate": billing_date,
        }
        try:
            items = _cli.paginate_next_token("bssopenapi",
                                             "DescribeInstanceBill",
                                             params, profile=profile)
        except _cli.CliError as e:
            warning = f"{product_code} {billing_cycle}: {e}"
            print(f"[WARN] bill query failed for one product; continuing with "
                  f"the remaining products -- {warning}", file=sys.stderr)
            warnings.append(warning)
            continue
        all_items.extend(items)
    return all_items, warnings


def detect_anomalies(
    monthly_data: dict[str, dict[str, float]],
    cycles: list[str],
) -> list[dict]:
    """Detect month-over-month cost anomalies per product.

    Flagged when relative growth > ANOMALY_THRESHOLD_PCT (20%) OR absolute
    growth > ANOMALY_THRESHOLD_ABS (100 CNY). When the previous month's cost
    is non-positive (refund / bill adjustment), a percentage would be
    meaningless or sign-flipped, so pct_change is left as None, the entry is
    annotated "baseline non-positive", and the change is judged by the
    absolute threshold only.
    """
    anomalies: list[dict] = []
    for product_code, product_name in DB_PRODUCT_CODES.items():
        if product_code == "dbs":
            continue  # normalized into "cbs"; avoid double reporting
        costs = [monthly_data.get(c, {}).get(product_code, 0.0) for c in cycles]

        for i in range(1, len(costs)):
            prev, curr = costs[i - 1], costs[i]
            abs_change = curr - prev
            if prev <= 0:
                # Refund/adjustment baseline: no percentage, absolute only.
                if abs_change > ANOMALY_THRESHOLD_ABS:
                    anomalies.append({
                        "product": product_name,
                        "product_code": product_code,
                        "month": cycles[i],
                        "prev_month": cycles[i - 1],
                        "prev_cost": round(prev, 2),
                        "curr_cost": round(curr, 2),
                        "abs_change": round(abs_change, 2),
                        "pct_change": None,
                        "note": "baseline non-positive",
                    })
                continue
            pct_change = (abs_change / prev) * 100

            if pct_change > ANOMALY_THRESHOLD_PCT or abs_change > ANOMALY_THRESHOLD_ABS:
                anomalies.append({
                    "product": product_name,
                    "product_code": product_code,
                    "month": cycles[i],
                    "prev_month": cycles[i - 1],
                    "prev_cost": round(prev, 2),
                    "curr_cost": round(curr, 2),
                    "abs_change": round(abs_change, 2),
                    "pct_change": round(pct_change, 2),
                })
    return anomalies


def aggregate(
    cycles: list[str],
    product_filter: str | None,
    granularity: str,
    billing_date: str | None = None,
    profile: str | None = None,
) -> tuple[dict, dict, list[str]]:
    """Fetch and aggregate all cycles.

    With billing_date set (DAILY mode) cycles holds that single date label;
    the API is queried once for the day's cycle with BillingDate attached.

    A failed product query is degraded, never fatal: its warning is collected
    and returned so the report can state the limitation while still showing
    every product/cycle that did return data.

    Returns:
        monthly_data:  { cycle: { product_code: total_cost } }
        instance_costs: { cycle: { product_code: { instance_id: cost } } }
        warnings:      one message per degraded product/cycle query
    """
    monthly_data: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    instance_costs: dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float)))
    warnings: list[str] = []

    for cycle in cycles:
        print(f"      querying {cycle} ...", file=sys.stderr)
        if billing_date:
            items, cycle_warnings = query_monthly_bill(
                billing_date[:7], product_filter, granularity, billing_date,
                profile)
        else:
            items, cycle_warnings = query_monthly_bill(
                cycle, product_filter, granularity, profile=profile)
        warnings.extend(cycle_warnings)
        for item in items:
            product_code = item.get("ProductCode") or ""
            if product_code not in ALL_DB_PRODUCT_CODES:
                continue
            # Normalize the DBS alias: BSS may report 'dbs' or 'cbs'.
            if product_code == "dbs":
                product_code = "cbs"

            try:
                cost = float(item.get("PretaxAmount") or 0)
            except (TypeError, ValueError):
                cost = 0.0
            instance_id = item.get("InstanceID") or ""

            monthly_data[cycle][product_code] += cost
            if instance_id:
                instance_costs[cycle][product_code][instance_id] += cost
    return monthly_data, instance_costs, warnings


def _has_any_cost(monthly_data: dict, cycles: list[str]) -> bool:
    """True when at least one cycle carries a non-zero DB product cost."""
    return any(any(v for v in monthly_data[c].values()) for c in cycles)


def _build_summary_fields(
    cycles: list[str],
    monthly_data: dict,
    anomalies: list[dict],
    product_filter: str | None,
    granularity: str,
    billing_date: str | None,
    error: str = "",
    warnings: list[str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """Build (summary, key_findings, suggestions) shared by both output
    modes. Covers the normal, partially degraded, empty-data and error cases."""
    warnings = warnings or []
    scope_desc = (f"the single day {billing_date}"
                  if granularity == "DAILY"
                  else f"the last {len(cycles)} billing cycles "
                       f"({cycles[0]} to {cycles[-1]})")
    product_desc = (f"for product {DB_PRODUCT_CODES.get(product_filter, product_filter)}"
                    if product_filter else "across all database products")

    if error:
        return (
            f"The DB cost trend query {product_desc} over {scope_desc} "
            f"failed before any data could be read.",
            [f"Query error: {error}"],
            [
                "Check that the CLI credential is configured and has BSS "
                "billing read permission (aliyun configure).",
                "Re-run the query; if it keeps failing, a transient BSS "
                "failure or a permission gap is likely.",
            ],
        )

    if not _has_any_cost(monthly_data, cycles):
        reasons = ("this account has no database services (e.g. no RDS / "
                   "Redis / MongoDB instances), the charges sit under a "
                   "different product code, or the queried window predates "
                   "the usage")
        findings = [
            "Zero cost was recorded for any queried database product in "
            "the window.",
            f"Likely reasons: {reasons}.",
        ]
        if warnings:
            findings.append(
                f"{len(warnings)} product query(ies) were degraded and their "
                f"cost is therefore unknown: {'; '.join(warnings[:3])}.")
        suggestions = []
        if product_filter:
            suggestions.append(
                "Re-run without --product to scan every database product "
                "instead of a single one.")
        else:
            suggestions.append(
                "Verify the billing window; if the period is very recent, "
                "re-run later since bill data can lag.")
        return (
            f"No database cost records were found {product_desc} over "
            f"{scope_desc}.",
            findings,
            suggestions,
        )

    grand_total = sum(sum(monthly_data[c].values()) for c in cycles)
    findings = [
        f"Total database cost in the window: {grand_total:.2f} CNY.",
    ]
    suggestions: list[str] = []
    if warnings:
        findings.append(
            f"Partial data: {len(warnings)} product query(ies) failed and were "
            f"skipped, so the total is a lower bound -- "
            f"{'; '.join(warnings[:3])}.")
        suggestions.append(
            "Re-run the query to cover the degraded product(s); if the failure "
            "persists, check the BSS billing read permission of the "
            "credential.")
    if anomalies:
        findings.append(
            f"{len(anomalies)} month-over-month cost jump(s) exceeded the "
            f"thresholds (+{ANOMALY_THRESHOLD_PCT:.0f}% or "
            f"+{ANOMALY_THRESHOLD_ABS:.0f} CNY).")
        top = max(anomalies, key=lambda a: a["abs_change"])
        findings.append(
            f"Largest jump: {top['product']} {top['prev_month']} -> "
            f"{top['month']}, from {top['prev_cost']:.2f} to "
            f"{top['curr_cost']:.2f} CNY (+{top['abs_change']:.2f}).")
        suggestions.append(
            "Drill into the flagged month: run query_instance_bill.py on "
            "the top instances listed in the anomaly attribution to see "
            "which billing item grew.")
        if granularity == "MONTHLY":
            suggestions.append(
                "For day-level detail of a flagged month, re-run with "
                "--granularity DAILY --billing-date <YYYY-MM-DD>.")
    else:
        findings.append(
            "No significant month-over-month cost jump was detected; the "
            "database cost stayed stable in the window.")
        suggestions.append(
            "If the bill still looks high, the baseline itself may be "
            "oversized: run query_instance_bill.py on the costliest "
            "instance to split its charge by billing item.")
    return (
        f"Queried the database cost trend {product_desc} over "
        f"{scope_desc}: total {grand_total:.2f} CNY, "
        f"{len(anomalies)} anomalous jump(s) detected.",
        findings,
        suggestions,
    )


def _print_summary_section(rows: list[tuple[str, str]]) -> None:
    """Print the plain-language Summary header plus one line per (label, value).

    Label width matches the other Summary blocks of this skill so the
    readable report stays visually consistent across scripts.
    """
    print("\nSummary")
    print("-------")
    for label, value in rows:
        print(f"{label:<16} : {value}")


def render_table(
    cycles: list[str],
    monthly_data: dict,
    instance_costs: dict,
    display_products: list[str],
) -> None:
    """Render the trend table plus anomaly analysis (human-readable mode)."""
    header = "| Month  |"
    sep = "|--------|"
    for pc in display_products:
        header += f" {DB_PRODUCT_CODES.get(pc, pc)} |"
        sep += "------:|"
    header += " Total |"
    sep += "------:|"

    print(f"\nDB Cost Trend (last {len(cycles)} months)"
          if len(cycles) > 1 or len(cycles[0]) == 7
          else f"\nDB Daily Cost Breakdown ({cycles[0]})")
    print("-" * 60)
    print(header)
    print(sep)

    for cycle in cycles:
        row = f"| {cycle} |"
        total = 0.0
        for pc in display_products:
            cost = monthly_data[cycle].get(pc, 0.0)
            total += cost
            row += f" {cost:,.0f} |"
        row += f" {total:,.0f} |"
        print(row)

    anomalies = detect_anomalies(monthly_data, cycles)
    if anomalies:
        print("\nAnomaly detection:")
        for a in sorted(anomalies, key=lambda x: x["abs_change"], reverse=True):
            if a.get("pct_change") is None:
                growth = (f"cost grew +{a['abs_change']:,.0f} CNY "
                          f"(baseline non-positive; percentage not computed)")
            else:
                growth = (f"cost grew {a['pct_change']:.0f}% "
                          f"(+{a['abs_change']:,.0f} CNY)")
            print(f"  - {a['product']} {a['prev_month']} -> {a['month']}: "
                  f"{growth}, "
                  f"from {a['prev_cost']:,.0f} to {a['curr_cost']:,.0f} CNY")

            # Locate the top instances driving the anomaly.
            prev_instances = (instance_costs.get(a["prev_month"], {})
                              .get(a["product_code"], {}))
            curr_instances = (instance_costs.get(a["month"], {})
                              .get(a["product_code"], {}))
            ranked = sorted(curr_instances.items(),
                            key=lambda kv: kv[1], reverse=True)[:3]
            for inst_id, curr_cost in ranked:
                prev_cost = prev_instances.get(inst_id, 0.0)
                if curr_cost - prev_cost > 0:
                    print(f"    - instance {inst_id}: {prev_cost:,.0f} -> "
                          f"{curr_cost:,.0f} CNY (+{curr_cost - prev_cost:,.0f})")
    else:
        print(f"\nNo significant anomaly detected; cost stayed stable over "
              f"the last {len(cycles)} months.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DB cost trend analysis per product with anomaly detection "
                    "(read-only BSS billing query)",
    )
    parser.add_argument("--months", type=int, default=6,
                        help="Number of recent billing cycles to query "
                             "(default 6, range 2-24)")
    parser.add_argument("--product", default=None,
                        choices=[c for c in DB_PRODUCT_CODES if c != "dbs"],
                        help="Restrict the query to one product "
                             "(rds/dds/kvstore/polardb/dts/cbs/cdt)")
    parser.add_argument("--granularity", choices=["MONTHLY", "DAILY"],
                        default="MONTHLY",
                        help="MONTHLY (default) or DAILY (single-day "
                             "drill-down; requires --billing-date)")
    parser.add_argument("--billing-date", default=None,
                        type=_billing_date_type,
                        help="Billing date YYYY-MM-DD; REQUIRED when "
                             "--granularity DAILY is used (single-day "
                             "drill-down, one query loop for that day)")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of the table")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    args = parser.parse_args()

    if args.granularity == "DAILY" and not args.billing_date:
        print("[ERROR] --billing-date YYYY-MM-DD is required when "
              "--granularity DAILY is used: BSS DescribeInstanceBill demands "
              "BillingDate for daily bills (single-day drill-down)",
              file=sys.stderr)
        sys.exit(2)

    if args.months < 2 and args.granularity != "DAILY":
        print("[ERROR] --months must be at least 2 for a month-over-month "
              "trend comparison (a single month cannot show a trend)",
              file=sys.stderr)
        sys.exit(2)

    if args.months > 24 and args.granularity != "DAILY":
        print("[ERROR] --months must not exceed 24: each cycle costs a "
              "full billing query, so longer histories are rejected to "
              "avoid hundreds of API calls (query fewer cycles or split "
              "the range across runs)",
              file=sys.stderr)
        sys.exit(2)

    _cli.check_cli_available()

    granularity_is_daily = args.granularity == "DAILY"
    if granularity_is_daily:
        # Single-day drill-down: one query loop for the given date, keyed by
        # the date itself; no per-day iteration, no multi-month trend.
        cycles = [args.billing_date]
    else:
        cycles = get_billing_cycles(args.months)
    print(f"[1/2] Querying cost of the last {len(cycles)} cycles "
          f"({args.granularity}) ...", file=sys.stderr)
    monthly_data: dict = defaultdict(lambda: defaultdict(float))
    instance_costs: dict = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float)))
    query_error = ""
    warnings: list[str] = []
    try:
        monthly_data, instance_costs, warnings = aggregate(cycles, args.product,
                                                          args.granularity,
                                                          args.billing_date,
                                                          args.profile)
    except _cli.CliError as e:
        query_error = str(e)
        print(f"[ERROR] Bill query failed: {e}", file=sys.stderr)

    # Every product query degraded and nothing was read: that is a failed
    # query, not a "no cost" conclusion -- never report zero cost from it.
    if not query_error and warnings and not _has_any_cost(monthly_data, cycles):
        query_error = (f"all {len(warnings)} product query(ies) failed: "
                       f"{'; '.join(warnings[:3])}")
        print(f"[ERROR] {query_error}", file=sys.stderr)

    print("[2/2] Analyzing trend and anomalies ...", file=sys.stderr)

    anomalies = detect_anomalies(monthly_data, cycles) if not query_error else []
    summary, key_findings, suggestions = _build_summary_fields(
        cycles, monthly_data, anomalies, args.product, args.granularity,
        args.billing_date, error=query_error, warnings=warnings)

    if args.json:
        result = {
            "cycles": cycles,
            "granularity": args.granularity,
            "billing_date": args.billing_date,
            "product_filter": args.product,
            "api": "DescribeInstanceBill",
            "query_error": query_error or None,
            "degraded_queries": warnings,
            "monthly_data": {c: {k: round(v, 2) for k, v in monthly_data[c].items()}
                             for c in cycles},
            "anomalies": anomalies,
            "thresholds": {
                "pct": ANOMALY_THRESHOLD_PCT,
                "abs_cny": ANOMALY_THRESHOLD_ABS,
            },
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }
        print(json.dumps(result, indent=2))
        if query_error:
            sys.exit(1)
        return

    if query_error:
        print("\nSummary")
        print("-------")
        print("What was queried : the database cost trend over the requested "
              "period.")
        print("Key finding      : the query failed, so no cost data could "
              "be read.")
        print("Suggested next steps:")
        for s in suggestions:
            print(f"  - {s}")
        sys.exit(1)

    if not _has_any_cost(monthly_data, cycles):
        scope = (f"the single day {cycles[0]}" if granularity_is_daily
                 else f"the period {cycles[0]} to {cycles[-1]}"
                 if len(cycles) > 1 else f"the period {cycles[0]}")
        print("\nSummary")
        print("-------")
        print(f"What was queried : database product costs over {scope}.")
        print("Key findings:")
        for finding in key_findings:
            print(f"  - {finding}")
        print("Suggested next steps:")
        for s in suggestions:
            print(f"  - {s}")
        return

    # Products to display: keep catalog order, only those with any cost.
    order = list(DB_PRODUCT_CODES.keys())
    display_products = [
        pc for pc in order
        if pc != "dbs" and any(monthly_data[c].get(pc, 0) > 0 for c in cycles)
    ]
    if args.product and args.product not in display_products:
        # An explicit filter is always shown, even with zero cost.
        display_products = [args.product]

    render_table(cycles, monthly_data, instance_costs, display_products)

    scope = (f"the single day {args.billing_date}"
             if args.granularity == "DAILY"
             else f"the last {len(cycles)} months")
    _print_summary_section([
        ("What was queried", f"database costs {scope}, per product."),
    ])
    print("Key findings:")
    for finding in key_findings:
        print(f"  - {finding}")
    print("Suggested next steps:")
    for s in suggestions:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
