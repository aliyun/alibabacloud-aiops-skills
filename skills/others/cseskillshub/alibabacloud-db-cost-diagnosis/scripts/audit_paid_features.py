#!/usr/bin/env python3
"""
audit_paid_features.py -- Attribute DB charges to optional paid features
=======================================================================
SECURITY: READ-ONLY. This script only queries BSS billing APIs
(DescribeInstanceBill / DescribeSplitItemBill). It never reads or writes any
AccessKey / Secret; credentials are resolved by the aliyun CLI default
credential chain. Never pass AK/SK to this script.

Purpose:
    Some database charges come from OPTIONAL paid add-ons (SQL Audit,
    Performance Insight, cross-region backup, database proxy, read-only
    replicas, auto scaling ...) that are easy to forget. This audit walks
    the instance bill of one billing cycle, drills into the split-item bill
    of the costliest instances, and attributes every billing item either to
    a known paid feature, to a base charge, or flags it as an unidentified
    charge candidate.

Dual-audience output:
  - Default (human-readable): a paid-feature attribution table plus a
    plain-language "Summary" section (what was queried / key findings /
    suggested next steps), written for non-technical readers.
  - --json (for Agents): the full detail fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields; empty or failed
    queries still emit these fields so downstream stages can consume them.

Usage:
    python3 audit_paid_features.py [--billing-cycle YYYY-MM] [--product rds] \
        [--json] [--profile <name>]

    --billing-cycle defaults to the CURRENT month (auto-filled when
    omitted; the chosen value is always declared in the output).

Guardrails:
    Only the top SPLIT_ITEM_TOP_N_INSTANCES instances (by cycle cost) get a
    split-item drill-down; the rest are reported by their instance-level
    totals only. Empty data is reported gracefully with exit code 0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime

import _cli
from _constants import (
    BILLING_ITEMS_COMMON,
    DB_PRODUCT_CODES,
    PAID_FEATURE_BILLING_MAP,
    SPLIT_ITEM_TOP_N_INSTANCES,
)

_BILLING_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_UNSPECIFIED_ITEM = "(unspecified item)"


def _billing_cycle_type(value: str) -> str:
    """argparse type validator: --billing-cycle must be YYYY-MM."""
    if not _BILLING_CYCLE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --billing-cycle '{value}': expected format YYYY-MM "
            f"(e.g. 2026-07)")
    return value


# ---------------------------------------------------------------------------
# Pure attribution logic (inline boundary assertions; self-checked on load)
# ---------------------------------------------------------------------------

# Word-boundary patterns per keyword: a keyword only matches when no
# letter/digit sits directly next to it, so compact tokens cannot silently
# absorb unrelated billing items (built once from the map keys).
_PAID_FEATURE_PATTERNS = {
    keyword: re.compile(r"(?<![a-z0-9])" + re.escape(keyword)
                        + r"(?![a-z0-9])")
    for keyword in PAID_FEATURE_BILLING_MAP
}


def match_paid_feature(item_name: str) -> str | None:
    """Match a billing-item name against PAID_FEATURE_BILLING_MAP.

    Case-insensitive word-boundary substring match; returns the matched
    keyword (map key) or None when the item belongs to no known paid
    feature. Non-string or empty input is never an error: it simply does
    not match.
    """
    if not item_name or not isinstance(item_name, str):
        return None
    lowered = item_name.lower()
    for keyword, pattern in _PAID_FEATURE_PATTERNS.items():
        if pattern.search(lowered):
            return keyword
    return None


def classify_billing_item(item_name: str, product_code: str) -> str:
    """Bucket a billing-item name: "paid_feature" / "base" / "residual".

    - paid_feature: matches PAID_FEATURE_BILLING_MAP (optional add-on).
    - base:         matches the product's common base-charge items
                    (instance / storage / backup ... in BILLING_ITEMS_COMMON).
    - residual:     matches neither -> an unidentified charge candidate.
    """
    if match_paid_feature(item_name) is not None:
        return "paid_feature"
    name = (item_name or "").lower()
    if not name or name == _UNSPECIFIED_ITEM:
        return "residual"
    for base_item in BILLING_ITEMS_COMMON.get(product_code, []):
        # Forward containment only: the known base item name must appear
        # inside the billing-item name. Reverse containment (short billing
        # token inside a longer base-item name) is deliberately rejected,
        # otherwise tokens like "fee" would silently absorb unidentified
        # charges into the base bucket.
        if base_item.lower() in name:
            return "base"
    return "residual"


def _run_inline_self_tests() -> None:
    """Module-load self check: normal / boundary / invalid inputs."""
    # match_paid_feature -- normal
    assert match_paid_feature("SQL Audit storage fee") == "sql audit"
    assert match_paid_feature("Database proxy fee") == "database proxy"
    assert match_paid_feature("DB Proxy node fee") == "db proxy"
    assert match_paid_feature("ReadOnly Instance fee") == "readonly instance"
    assert match_paid_feature("Read-only Instance fee") == "read-only instance"
    assert match_paid_feature("DAS Service fee") == "das service"
    assert match_paid_feature("Cross-Region Backup fee") == "cross-region backup"
    # match_paid_feature -- localized (zh-CN) billing labels, \u-escaped:
    # cross-region backup space / read-only instance fee / database proxy.
    assert match_paid_feature("\u5f02\u5730\u5907\u4efd\u7a7a\u95f4") == \
        "\u5f02\u5730\u5907\u4efd"
    assert match_paid_feature("\u53ea\u8bfb\u5b9e\u4f8b\u8d39") == \
        "\u53ea\u8bfb\u5b9e\u4f8b"
    assert match_paid_feature("\u6570\u636e\u5e93\u4ee3\u7406\u8d39") == \
        "\u6570\u636e\u5e93\u4ee3\u7406"
    # match_paid_feature -- boundary (exact keyword, mixed case)
    assert match_paid_feature("sql audit") == "sql audit"
    assert match_paid_feature("PERFORMANCE INSIGHT") == "performance insight"
    # match_paid_feature -- tightened tokens must not over-match
    assert match_paid_feature("proxy fee") is None
    assert match_paid_feature("proxying service") is None
    assert match_paid_feature("read-only traffic") is None
    # match_paid_feature -- invalid / non-matching
    assert match_paid_feature("Instance fee") is None
    assert match_paid_feature("") is None
    assert match_paid_feature(None) is None  # type: ignore[arg-type]

    # classify_billing_item -- normal / boundary / invalid
    assert classify_billing_item("SQL Explorer fee", "rds") == "paid_feature"
    assert classify_billing_item("Instance fee", "rds") == "base"
    assert classify_billing_item("Storage fee", "rds") == "base"
    assert classify_billing_item("Instance fee (primary)", "rds") == "base"
    # Localized (zh-CN) base items: instance spec / storage space are base
    # charges; cross-region backup space is a paid feature and must win
    # over the base bucket even though it also contains the base keyword
    # for backup space (paid features are checked first).
    assert classify_billing_item("\u89c4\u683c", "rds") == "base"
    assert classify_billing_item("\u5b58\u50a8\u7a7a\u95f4", "rds") == "base"
    assert classify_billing_item("\u5907\u4efd\u7a7a\u95f4", "rds") == "base"
    assert classify_billing_item("\u5f02\u5730\u5907\u4efd\u7a7a\u95f4",
                                 "rds") == "paid_feature"
    # reverse containment is rejected: a short token that merely sits
    # inside a known base-item name stays an unidentified candidate.
    assert classify_billing_item("fee", "rds") == "residual"
    assert classify_billing_item("Mystery promo line", "rds") == "residual"
    assert classify_billing_item("", "rds") == "residual"
    assert classify_billing_item(None, "rds") == "residual"  # type: ignore[arg-type]


_run_inline_self_tests()


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def fetch_instance_bill(billing_cycle: str, product_code: str,
                        profile: str | None) -> list[dict]:
    """All instance-level bill rows of the product for one cycle."""
    params = {"BillingCycle": billing_cycle, "ProductCode": product_code}
    return _cli.paginate_next_token("bssopenapi", "DescribeInstanceBill",
                                    params, profile=profile)


def fetch_split_items(billing_cycle: str, instance_id: str,
                      profile: str | None) -> list[dict]:
    """All split-item bill rows of one instance for one cycle."""
    params = {
        "BillingCycle": billing_cycle,
        "InstanceID": instance_id,
        "Granularity": "MONTHLY",
    }
    return _cli.paginate_next_token("bssopenapi", "DescribeSplitItemBill",
                                    params, profile=profile)


def _amount(item: dict, key: str) -> float:
    """Read a numeric amount field from a bill item (defensive)."""
    try:
        return float(item.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def rank_charged_instances(items: list[dict]) -> list[tuple[str, float]]:
    """Return [(instance_id, cost)] for instances with cost > 0, cost desc.

    Rows without an InstanceID (account-level charges) are skipped here and
    surface separately as residual candidates.
    """
    totals: dict[str, float] = defaultdict(float)
    for item in items:
        instance_id = item.get("InstanceID") or ""
        if not instance_id:
            continue
        totals[instance_id] += _amount(item, "PretaxAmount")
    ranked = [(iid, cost) for iid, cost in totals.items() if cost > 0]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked


def attribute_split_items(
    per_instance_items: dict[str, list[dict]],
    product_code: str,
) -> tuple[dict, float, list[dict]]:
    """Attribute every split-item row to a paid feature / base / residual.

    Returns:
        features: {feature_name: {"category", "amount", "instances",
                   "items": {item_name: amount}}}
        base_total: total amount attributed to base charges
        residuals: [{"instance_id", "item", "amount"}] unidentified rows
    """
    features: dict[str, dict] = {}
    base_total = 0.0
    residuals: list[dict] = []

    for instance_id, items in per_instance_items.items():
        for item in items:
            name = (item.get("BillingItem") or item.get("SplitItemName")
                    or _UNSPECIFIED_ITEM)
            cost = _amount(item, "PretaxAmount")
            bucket = classify_billing_item(name, product_code)
            if bucket == "paid_feature":
                keyword = match_paid_feature(name)
                assert keyword is not None  # classify implies a match
                meta = PAID_FEATURE_BILLING_MAP[keyword]
                entry = features.setdefault(meta["feature"], {
                    "category": meta["category"],
                    "note": meta["note"],
                    "amount": 0.0,
                    "instances": set(),
                    "items": defaultdict(float),
                })
                entry["amount"] += cost
                entry["instances"].add(instance_id)
                entry["items"][name] += cost
            elif bucket == "base":
                base_total += cost
            else:
                residuals.append({"instance_id": instance_id,
                                  "item": name, "amount": round(cost, 2)})
    return features, base_total, residuals


# ---------------------------------------------------------------------------
# Summary (shared by both output modes)
# ---------------------------------------------------------------------------

def _build_summary_fields(
    billing_cycle: str,
    cycle_auto_filled: bool,
    product_code: str,
    charged: list[tuple[str, float]],
    analyzed: list[tuple[str, float]],
    features: dict,
    base_total: float,
    residuals: list[dict],
    error: str = "",
) -> tuple[str, list[str], list[str]]:
    product_name = DB_PRODUCT_CODES.get(product_code, product_code)
    cycle_note = (" (auto-filled to the current month)" if cycle_auto_filled
                  else "")

    if error:
        return (
            f"The paid-feature audit of {product_name} for {billing_cycle} "
            f"failed before any data could be read.",
            [f"Query error: {error}"],
            [
                "Check that the CLI credential is configured and has BSS "
                "billing read permission (aliyun configure).",
                "Verify the billing cycle and product, then re-run.",
            ],
        )

    if not charged:
        return (
            f"No billed {product_name} instance was found in billing cycle "
            f"{billing_cycle}{cycle_note}, so there is no paid-feature "
            f"charge to attribute.",
            [
                f"DescribeInstanceBill returned no rows with a positive "
                f"amount for ProductCode={product_code} in {billing_cycle}.",
                "Likely reasons: the account has no such database instance, "
                "the instance was released before the cycle, or the charges "
                "sit under another account / product code.",
            ],
            [
                "Verify the billing cycle; bill data can lag briefly for "
                "the current month, so re-run later if the cycle is recent.",
                "Re-run with a different --product if the database runs "
                "under another product code (e.g. polardb, dds, kvstore).",
            ],
        )

    total_cost = sum(cost for _, cost in charged)
    feature_total = sum(f["amount"] for f in features.values())
    findings = [
        f"{len(charged)} {product_name} instance(s) carried charges in "
        f"{billing_cycle}: {total_cost:.2f} CNY in total.",
        f"Split-item drill-down covered the top {len(analyzed)} instance(s) "
        f"({sum(c for _, c in analyzed):.2f} CNY of the total).",
    ]
    suggestions: list[str] = []
    if features:
        ranked = sorted(features.items(), key=lambda kv: kv[1]["amount"],
                        reverse=True)
        top_name, top = ranked[0]
        findings.append(
            f"{len(features)} paid feature(s) detected; the largest is "
            f"\"{top_name}\" at {top['amount']:.2f} CNY.")
        suggestions.append(
            f"Review whether \"{top_name}\" is still needed; disabling an "
            f"unused add-on stops its charge from the next cycle.")
    else:
        findings.append(
            "No known optional paid feature (SQL Audit / Performance "
            "Insight / cross-region backup / proxy / read-only / auto "
            "scaling) was detected in the analyzed items.")
        suggestions.append(
            "If you expected a paid add-on to appear, check its billing "
            "item name on the console and re-run after the bill settles.")
    if residuals:
        residual_total = sum(r["amount"] for r in residuals)
        findings.append(
            f"{len(residuals)} billing item(s) ({residual_total:.2f} CNY) "
            f"matched neither a known paid feature nor a base charge and "
            f"are listed as unidentified charge candidates.")
        suggestions.append(
            "Inspect the unidentified candidates; an unrecognized line is "
            "often a leftover add-on, a manual price adjustment, or a "
            "marketplace item worth verifying.")
    else:
        findings.append(
            f"Base charges (instance / storage / backup ...) account for "
            f"{base_total:.2f} CNY of the drilled-down amount.")
    return (
        f"Audited paid-feature charges of {product_name} in {billing_cycle}"
        f"{cycle_note}: {len(charged)} charged instance(s), "
        f"{len(features)} paid feature(s) attributed, "
        f"{len(residuals)} unidentified candidate(s).",
        findings,
        suggestions,
    )


# ---------------------------------------------------------------------------
# Rendering (human-readable mode)
# ---------------------------------------------------------------------------

def render(billing_cycle, cycle_auto_filled, product_code, charged, analyzed,
           features, base_total, residuals, skipped_total) -> None:
    product_name = DB_PRODUCT_CODES.get(product_code, product_code)

    print("Paid Feature Audit")
    print("-" * 56)
    print(f"Product        : {product_name} ({product_code})")
    print(f"Billing cycle  : {billing_cycle}"
          + (" (auto-filled: current month)" if cycle_auto_filled else ""))
    print(f"Charged insts  : {len(charged)}")
    print(f"Drilled down   : top {len(analyzed)} instance(s)")
    print()

    if not charged:
        print("No charged instance found for this product and cycle.")
        return

    if features:
        print("Paid features detected:")
        header = (f"| {'Feature':<32} | {'Amount':>10} | {'Instances':>9} |")
        print(header)
        print(f"|{'-' * 34}|{'-' * 12}|{'-' * 11}|")
        for name, entry in sorted(features.items(),
                                  key=lambda kv: kv[1]["amount"],
                                  reverse=True):
            print(f"| {name:<32} | {entry['amount']:>10.2f} "
                  f"| {len(entry['instances']):>9} |")
            for item_name, cost in sorted(entry["items"].items(),
                                          key=lambda kv: kv[1],
                                          reverse=True):
                print(f"|   - {item_name[:26]:<28} | {cost:>10.2f} |")
        print()
    else:
        print("No known optional paid feature was detected.")
        print()

    if residuals:
        print("Unidentified charge candidates (neither paid feature nor "
              "known base charge):")
        for r in sorted(residuals, key=lambda x: x["amount"], reverse=True):
            print(f"  - {r['instance_id']} / {r['item']}: "
                  f"{r['amount']:.2f} CNY")
        print()
    else:
        print(f"No unidentified charge candidate; base charges of the "
              f"drilled-down instances total {base_total:.2f} CNY.")
        print()

    if skipped_total > 0:
        print(f"Note: instances beyond the top-{len(analyzed)} drill-down "
              f"guardrail still carry {skipped_total:.2f} CNY that was only "
              f"seen at instance level (re-run the single-instance bill "
              f"with --split-item to drill into them).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attribute database charges of one billing cycle to "
                    "optional paid features (read-only BSS audit)",
    )
    parser.add_argument("--billing-cycle", default=None,
                        type=_billing_cycle_type,
                        help="Billing cycle YYYY-MM (default: the current "
                             "month, auto-filled and declared in output)")
    parser.add_argument("--product", default="rds",
                        choices=[c for c in DB_PRODUCT_CODES if c != "dbs"],
                        help="Product to audit "
                             "(rds/dds/kvstore/polardb/dts/cbs/cdt; "
                             "default rds)")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of the table")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    args = parser.parse_args()

    cycle_auto_filled = args.billing_cycle is None
    billing_cycle = args.billing_cycle or datetime.now().strftime("%Y-%m")
    if cycle_auto_filled:
        print(f"[_] --billing-cycle not given; auto-filled to the current "
              f"month: {billing_cycle}", file=sys.stderr)

    _cli.check_cli_available()

    print(f"[1/3] Querying instance bill of {args.product} for "
          f"{billing_cycle} ...", file=sys.stderr)
    query_error = ""
    items: list[dict] = []
    try:
        items = fetch_instance_bill(billing_cycle, args.product, args.profile)
    except _cli.CliError as e:
        query_error = str(e)
        print(f"[ERROR] Instance bill query failed: {e}", file=sys.stderr)

    charged = rank_charged_instances(items)
    analyzed = charged[:SPLIT_ITEM_TOP_N_INSTANCES]

    per_instance_items: dict[str, list[dict]] = {}
    split_errors: list[str] = []
    if charged and not query_error:
        print(f"[2/3] Drilling split-item bill of the top {len(analyzed)} "
              f"instance(s) ...", file=sys.stderr)
        for instance_id, _ in analyzed:
            try:
                per_instance_items[instance_id] = fetch_split_items(
                    billing_cycle, instance_id, args.profile)
            except _cli.CliError as e:
                split_errors.append(f"{instance_id}: {e}")
                print(f"[WARN] split-item bill failed for {instance_id}: "
                      f"{e}", file=sys.stderr)
    else:
        print("[2/3] Nothing to drill down (no charged instance).",
              file=sys.stderr)

    print("[3/3] Attributing billing items to paid features ...",
          file=sys.stderr)
    features, base_total, residuals = attribute_split_items(
        per_instance_items, args.product)
    for err in split_errors:
        residuals.append({"instance_id": err.split(":")[0],
                          "item": "(split-item query failed)", "amount": 0.0})

    summary, key_findings, suggestions = _build_summary_fields(
        billing_cycle, cycle_auto_filled, args.product, charged, analyzed,
        features, base_total, residuals, error=query_error)

    if args.json:
        result = {
            "product_code": args.product,
            "product_name": DB_PRODUCT_CODES.get(args.product, args.product),
            "billing_cycle": billing_cycle,
            "billing_cycle_auto_filled": cycle_auto_filled,
            "apis": ["DescribeInstanceBill", "DescribeSplitItemBill"],
            "query_error": query_error or None,
            "charged_instance_count": len(charged),
            "drill_down_limit": SPLIT_ITEM_TOP_N_INSTANCES,
            "drilled_instances": [
                {"instance_id": iid, "cost": round(cost, 2)}
                for iid, cost in analyzed
            ],
            "paid_features": [
                {
                    "feature": name,
                    "category": entry["category"],
                    "note": entry["note"],
                    "amount": round(entry["amount"], 2),
                    "instances": sorted(entry["instances"]),
                    "items": {k: round(v, 2)
                              for k, v in entry["items"].items()},
                }
                for name, entry in sorted(features.items(),
                                          key=lambda kv: kv[1]["amount"],
                                          reverse=True)
            ],
            "base_charge_total": round(base_total, 2),
            "unidentified_candidates": residuals,
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
        print(f"What was queried : paid-feature charges of {args.product} "
              f"for billing cycle {billing_cycle}.")
        print("Key finding      : the query failed, so no bill data could "
              "be read.")
        print("Next steps:")
        for s in suggestions:
            print(f"  - {s}")
        sys.exit(1)

    skipped_total = sum(cost for _, cost in charged[len(analyzed):])
    render(billing_cycle, cycle_auto_filled, args.product, charged, analyzed,
           features, base_total, residuals, skipped_total)

    print("\nSummary")
    print("-------")
    print(f"What was queried : split-item bills of the top {len(analyzed)} "
          f"charged {args.product} instance(s) of {billing_cycle}.")
    print("Key findings:")
    for finding in key_findings:
        print(f"  - {finding}")
    print("Suggested next steps:")
    for s in suggestions:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
