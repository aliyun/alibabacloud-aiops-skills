#!/usr/bin/env python3
"""
query_ecs_bill.py -- ECS cost attribution & bill check (single entry point)
===========================================================================
SECURITY: This skill is strictly READ-ONLY. Every cloud call performed here
is a whitelisted billing / monitoring / instance METADATA read issued through
the aliyun CLI (see _cli.py). This script never modifies any resource, order
or configuration, never executes commands inside a guest OS, and never
reads, prints or passes credentials explicitly: authentication is resolved
exclusively by the aliyun CLI default credential chain.

Modes (mutually exclusive):
  (default)      attribution   : DescribeInstanceBill (billing-item rows) for
                                one or more cycles -> product -> billing item
                                -> region -> resource attribution with
                                usage x price recomputation, subscription /
                                post-paid contradiction flags and undeducted
                                row detection.
  --overview     per-product spend of one cycle (QueryBillOverview).
  --monthly-total cycle total rows (QueryBill).
  --settlement   settlement-bill amounts (QuerySettleBill).
  --reconcile    overview vs monthly vs settlement cross-check + timing
                 caliber + evidence pack when the layers disagree.
  --daily        per-day amount series of a cycle (DescribeInstanceBill
                 Granularity=DAILY), traffic spike-day flagging.
  --traffic-check  instance bandwidth billing mode (DescribeInstances) +
                 CloudMonitor egress series (DescribeMetricList) vs bill
                 usage (bill/usage cross-check, timeliness notes).
  --deduction-report  rows in fee with zero deductions + the deterministic
                 deduction-failure reason checklist (degraded: no package
                 inventory API is whitelisted).
  --instance-info  instance charge / stop / bandwidth metadata
                 (DescribeInstances).
  --list-topics / --topic <key>  embedded FAQ knowledge (no cloud call).
  --explain-timing embedded timing-caliber statements (no cloud call).

Output contract: human-readable report by default, machine JSON with --json;
every run ends with "STATUS: OK|DEGRADED|FAIL" and a "NEXT_ACTION:" line.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import datetime as dt
import json
import math
import os
import re
import statistics
import sys

import _cli
from _constants import (
    AMOUNT_FIELDS,
    BILLING_ITEMS,
    CONSOLE_PATHS,
    DEDUCTION_FAILURE_REASONS,
    DEFAULT_METRIC_NAMESPACE,
    DEFAULT_REGION,
    DEFAULT_TRAFFIC_METRIC,
    FAQ_TOPICS,
    FAQ_CONSOLE_ENTRY,
    FAQ_CONSOLE_DEFAULT,
    RULE_ONLY_TOPICS,
    INVOICE_CREATE_URL,
    COUPON_RULES_URL,
    STUDENT_COUPON_SPEC_SNAPSHOT,
    REFUND_ENTRY_URL,
    RECHARGE_URL,
    REFUND_EXPLAIN_INTENT_RE,
    RELEASE_HOUR_INTENT_RE,
    ASKED_PRODUCT_CUES,
    CHARGE_COMPLAINT_INTENT_RE,
    RULE_TOPIC_ASKED_ITEM,
    FAQ_TOPIC_SUBJECT_RE,
    TOTALS_INTENT_RE,
    STOP_ALL_INTENT_RE,
    NON_ECS_STOP_BRIEF,
    STOP_ALL_ECS_ITEMS,
    NON_ECS_SHORT_LABEL,
    STOP_ALL_DETAILED_PRODUCTS,
    WHERE_CHARGE_INTENT_RE,
    USAGE_DETAIL_INTENT_RE,
    QUERY_PATH_INTENT_RE,
    RESOURCE_INVENTORY_INTENT_RE,
    TRAFFIC_GENERATORS,
    SNAPSHOT_PROGRESS_INTENT_RE,
    SNAPSHOT_RECURRING_INTENT_RE,
    SNAPSHOT_DELETE_INTENT_RE,
    SPLIT_BILL_INTENT_RE,
    SPLIT_BILL_URL,
    MONTHLY_ESTIMATE_INTENT_RE,
    CONVERSION_INTENT_RE,
    SETTLEMENT_INTENT_RE,
    CONVERSION_DOC_URL,
    DEFERRED_STOP_INTENT_RE,
    BILLING_ACCOUNT_URL,
    HANDOFF_RULES,
    MAX_DAILY_DAYS,
    MAX_PAGES,
    MAX_RESULTS,
    METRIC_PERIOD_SECONDS,
    NON_ECS_PRODUCT_TOKENS,
    NON_ECS_BILLING_RULES,
    NON_ECS_CONSOLE_FILTER,
    NON_ECS_FUND_FLOW_NOTE,
    STOP_BILLING_ROUTES,
    ASKED_ITEM_PATTERNS,
    RULE_INTENT_PATTERNS,
    RULE_FALLBACK_TOPICS,
    CONTRACT_INTENT_RE,
    CONTRACT_POLICY_ANSWER,
    SPECIALTY_BILLING_ITEMS,
    STOP_BILLING_GUIDE,
    TIMING_CALIBER,
)

_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_REGION_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# Amounts below this are treated as zero when flagging "in fee".
_EPS = 0.005


# ---------------------------------------------------------------------------
# Pure helpers (with inline boundary self-checks at the bottom of the file)
# ---------------------------------------------------------------------------

def g(item: dict, *keys: str) -> str:
    """First non-empty string value among the given response keys."""
    for key in keys:
        val = item.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            return text
    return ""


def public_ips_of(inst: dict) -> list[str]:
    """Public IP strings from an ECS instance, tolerating both response shapes.

    The CLI returns PublicIpAddress.IpAddress as a list of plain strings, while
    SDK/JSON variants may nest {"IpAddress": ...} objects or flatten to a scalar.
    """
    def _one(raw) -> list[str]:
        if isinstance(raw, str):
            return [raw.strip()] if raw.strip() else []
        if isinstance(raw, dict):
            return _one(raw.get("IpAddress"))
        if isinstance(raw, list):
            return [ip for item in raw for ip in _one(item)]
        return []

    return _one(inst.get("PublicIpAddress"))


def num(item: dict, *keys: str) -> float:
    """First parseable numeric value among the given response keys, else 0."""
    for key in keys:
        val = item.get(key)
        if val is None or str(val).strip() == "":
            continue
        try:
            return float(str(val).replace(",", ""))
        except (TypeError, ValueError):
            continue
    return 0.0


def valid_cycle(text: str) -> bool:
    return bool(_CYCLE_RE.match(text or ""))


def previous_cycle(cycle: str) -> str:
    year, month = int(cycle[:4]), int(cycle[5:7])
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def walk_cycles(cycle: str, months: int) -> list[str]:
    out, cur = [], cycle
    for _ in range(max(1, months)):
        out.append(cur)
        cur = previous_cycle(cur)
    return sorted(out)


def days_in_cycle(cycle: str) -> int:
    year, month = int(cycle[:4]), int(cycle[5:7])
    if month == 12:
        nxt_start = dt.date(year + 1, 1, 1)
    else:
        nxt_start = dt.date(year, month + 1, 1)
    return (nxt_start - dt.date(year, month, 1)).days


def last_days_of_cycle(cycle: str, days: int) -> list[str]:
    """The final `days` calendar days of the cycle (capped, in order)."""
    total = days_in_cycle(cycle)
    days = max(1, min(days, total, MAX_DAILY_DAYS))
    year, month = int(cycle[:4]), int(cycle[5:7])
    start = total - days + 1
    return [f"{cycle}-{d:02d}" for d in range(start, total + 1)]


def cycle_window_epoch_ms(cycle: str) -> tuple[int, int]:
    """(start, end) millisecond epoch of the whole cycle (UTC based)."""
    year, month = int(cycle[:4]), int(cycle[5:7])
    start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc)
    if month == 12:
        end = dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
    else:
        end = dt.datetime(year, month + 1, 1, tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)
    end = min(end, now)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def cycle_is_unsettled(cycle: str) -> bool:
    """True until the cycle's final bill is issued: 12:00 UTC+8 on the 3rd next.

    The timing caliber was printed on every run, including cycles closed years
    ago, where calling the figures provisional is simply wrong. Measured on 80
    billing tickets it cost 124 characters and one of the 16 answer lines each
    time, so it now ships only when the cycle really is unsettled or the customer
    asked about settlement.
    """
    year, month = int(cycle[:4]), int(cycle[5:7])
    if month == 12:
        year, month = year + 1, 1
    else:
        month += 1
    issued = dt.datetime(year, month, 3, 12, 0,
                         tzinfo=dt.timezone(dt.timedelta(hours=8)))
    return dt.datetime.now(dt.timezone.utc) < issued


def map_charge_date_to_cycle(charge_date: str) -> str:
    """C3: a balance deduction at the start of month N pays cycle N-1."""
    return previous_cycle(charge_date[:7])


def match_item_key(row: dict) -> str:
    """Map a bill row to the embedded billing-item dictionary (or '').

    Chinese-language accounts return localized BillingItem values, so the
    match tries the raw token first (CJK included) and only then the
    ASCII-only lowercase form.
    """
    code = (row.get("product_code") or "").strip().lower()
    if code and code != "ecs":
        return ""
    hay = f"{row.get('item', '')} {row.get('item_code', '')}"
    hay_l = hay.lower()
    best_key, best_len = "", 0
    for key, meta in BILLING_ITEMS.items():
        for token in meta["names"]:
            token_h = "".join(ch for ch in token if ord(ch) < 128).lower()
            if token in hay:
                width = len(token)
            elif token_h and token_h in hay_l:
                width = len(token_h)
            else:
                continue
            if width > best_len:
                best_key, best_len = key, width
    return best_key


def is_traffic_row(row: dict) -> bool:
    return match_item_key(row) == "network_out"


# ---------------------------------------------------------------------------
# Bill row normalization
# ---------------------------------------------------------------------------

def row_view(item: dict) -> dict:
    row = {
        "product": g(item, "ProductName") or g(item, "ProductCode") or "(unknown product)",
        "product_code": g(item, "ProductCode"),
        "item": g(item, "BillingItem") or "(unspecified item)",
        "item_code": g(item, "BillingItemCode"),
        "region": g(item, "Region") or "(no region reported)",
        "resource": g(item, "InstanceID") or "(no instance id)",
        "instance_id": g(item, "InstanceID"),
        "subscription": g(item, "SubscriptionType"),
        "usage": num(item, "Usage"),
        "usage_unit": g(item, "UsageUnit"),
        "price": num(item, "ListPrice"),
        "price_unit": g(item, "ListPriceUnit"),
        "gross": num(item, "PretaxGrossAmount"),
        "discount": num(item, "InvoiceDiscount"),
        "pkg": num(item, "DeductedByResourcePackage"),
        "coupon": num(item, "DeductedByCoupons"),
        "payable": num(item, "PretaxAmount"),
        "after_discount": num(item, "AfterDiscountAmount"),
        "outstanding": num(item, "OutstandingAmount"),
        "date": g(item, "BillingDate"),
        "currency": g(item, "Currency") or "CNY",
    }
    row["item_key"] = match_item_key(row)
    return row


def recompute_check(row: dict) -> str:
    """usage x list price vs gross amount: 'ok' | 'mismatch' | 'skip'."""
    if row["usage"] <= 0 or row["price"] <= 0 or row["gross"] <= 0:
        return "skip"
    calc = row["usage"] * row["price"]
    diff = abs(calc - row["gross"])
    tol = max(row["gross"] * 0.10, 0.5)
    return "ok" if diff <= tol else "mismatch"


def fmt(x: float) -> str:
    return f"{x:.2f}"


def ip_text(entry) -> str:
    """Public-IP entries arrive either as plain strings or as objects with
    an IpAddress field depending on API shape; normalize to text."""
    if isinstance(entry, dict):
        return str(entry.get("IpAddress") or "")
    return str(entry or "")


# ---------------------------------------------------------------------------
# Data fetching (read-only, degraded per-call, errors[] collected)
# ---------------------------------------------------------------------------

def fetch_rows(cycle: str, product_code: str | None, instance_id: str | None,
               errors: list[str], profile: str | None) -> tuple[list[dict] | None, str]:
    """Billing-item rows of one cycle. Primary DescribeInstanceBill, with a
    permission-degradation fallback to QueryInstanceBill (both whitelisted
    reads; the fallback fires only when the primary call fails)."""
    params: dict = {"BillingCycle": cycle, "IsBillingItem": True}
    if product_code:
        params["ProductCode"] = product_code
    if instance_id:
        params["InstanceID"] = instance_id
    try:
        items = _cli.paginate_next_token(
            "bssopenapi", "DescribeInstanceBill", params, profile=profile)
        return [row_view(i) for i in items if isinstance(i, dict)], "DescribeInstanceBill"
    except _cli.CliError as e:
        errors.append(f"DescribeInstanceBill {cycle}: {e.code or 'error'}: {e}")
        print(f"[WARN] DescribeInstanceBill failed ({e.code or 'error'}); "
              f"degrading to QueryInstanceBill for {cycle}", file=sys.stderr)
        params2: dict = {"BillingCycle": cycle, "IsBillingItem": True}
        if product_code:
            params2["ProductCode"] = product_code
        try:
            items = _cli.paginate_page_num(
                "bssopenapi", "QueryInstanceBill", params2, profile=profile)
            return [row_view(i) for i in items if isinstance(i, dict)], "QueryInstanceBill(fallback)"
        except _cli.CliError as e2:
            errors.append(f"QueryInstanceBill {cycle}: {e2.code or 'error'}: {e2}")
            return None, ""


def fetch_instances(region: str, instance_ids: list[str], errors: list[str],
                    profile: str | None) -> list[dict]:
    params: dict = {"RegionId": region}
    if instance_ids:
        params["InstanceIds"] = json.dumps(instance_ids)
    try:
        body = _cli.call("ecs", "DescribeInstances", params, region=region,
                         profile=profile)
    except _cli.CliError as e:
        errors.append(f"DescribeInstances {region}: {e.code or 'error'}: {e}")
        return []
    inst = (body.get("Instances") or {}).get("Instance") or []
    return [i for i in inst if isinstance(i, dict)]


# The documented parameter set of QueryBillOverview is BillingCycle plus
# owner/product filters -- no PageNum/PageSize: it is called with plain
# parameters and both item shapes (Data.Items list / Data.Items.Item
# wrapper) are tolerated.
def fetch_overview_rows(cycle: str, product_code: str | None,
                        profile: str | None) -> list[dict]:
    params: dict = {"BillingCycle": cycle}
    if product_code:
        params["ProductCode"] = product_code
    body = _cli.call("bssopenapi", "QueryBillOverview", params, profile=profile)
    data = body.get("Data") or {}
    items = data.get("Items")
    if isinstance(items, dict):
        items = items.get("Item")
    if not isinstance(items, list):
        items = []
    return [row_view(i) for i in items if isinstance(i, dict)]


# QuerySettleBill is read with its documented pagination (MaxResults +
# NextToken). Response record-set field names are NOT assumed: every
# *Amount / *Balance leaf inside Data is relayed verbatim, whatever the
# record shape (real values only, per the no-fabrication contract).
def fetch_settle_amounts(cycle: str, profile: str | None) -> dict:
    amounts: dict = {}
    token: str | None = None
    for _page in range(MAX_PAGES):
        params: dict = {"BillingCycle": cycle, "MaxResults": MAX_RESULTS}
        if token:
            params["NextToken"] = token
        body = _cli.call("bssopenapi", "QuerySettleBill", params, profile=profile)
        data = body.get("Data") or {}
        _walk_amounts(data, "Data", amounts)
        token = str(data.get("NextToken") or "") or None
        if not token:
            break
    return amounts


def fetch_metric_points(namespace: str, metric: str, dimensions: str,
                        start_ms: int, end_ms: int, region: str,
                        errors: list[str],
                        profile: str | None) -> list[dict]:
    """CloudMonitor datapoints for one instance metric window (hourly)."""
    points: list[dict] = []
    token: str | None = None
    for _page in range(10):
        params: dict = {
            "Namespace": namespace,
            "MetricName": metric,
            "Dimensions": dimensions,
            "StartTime": str(start_ms),
            "EndTime": str(end_ms),
            "Period": METRIC_PERIOD_SECONDS,
            "Length": "1440",
        }
        if token:
            params["NextToken"] = token
        try:
            body = _cli.call("cms", "DescribeMetricList", params,
                             region=region, profile=profile)
        except _cli.CliError as e:
            errors.append(f"DescribeMetricList {metric}: {e.code or 'error'}: {e}")
            return points
        raw = body.get("Datapoints") or "[]"
        try:
            batch = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            errors.append("DescribeMetricList: unparseable Datapoints payload")
            return points
        if isinstance(batch, list):
            points.extend(p for p in batch if isinstance(p, dict))
        token = str(body.get("NextToken") or "") or None
        if not token:
            break
    return points


# ---------------------------------------------------------------------------
# Attribution aggregation
# ---------------------------------------------------------------------------

def aggregate_rows(rows: list[dict]) -> dict:
    tree: dict = {}
    for r in rows:
        key = (r["product"], r["item"], r["region"])
        node = tree.setdefault(key, {
            "gross": 0.0, "discount": 0.0, "pkg": 0.0, "coupon": 0.0,
            "payable": 0.0, "usage": 0.0, "count": 0, "resources": {},
            "mismatches": 0, "sub_traffic": False, "undeducted": False,
            "currency": r["currency"],
        })
        for f in ("gross", "discount", "pkg", "coupon", "payable", "usage"):
            node[f] += r[f]
        node["count"] += 1
        res = node["resources"].setdefault(
            r["resource"], {"payable": 0.0, "usage": 0.0, "unit": r["usage_unit"],
                            "price": r["price"], "price_unit": r["price_unit"]})
        res["payable"] += r["payable"]
        res["usage"] += r["usage"]
        if r["price"] > res["price"]:
            res["price"], res["price_unit"] = r["price"], r["price_unit"]
        if r["subscription"] == "Subscription" and is_traffic_row(r):
            node["sub_traffic"] = True
        if r["payable"] > _EPS and (r["pkg"] + r["coupon"]) <= _EPS:
            node["undeducted"] = True
        if recompute_check(r) == "mismatch":
            node["mismatches"] += 1
    return tree


def render_tree(tree: dict, out: list[str], top_resources: int = 3) -> None:
    products: dict = {}
    for (prod, item, region), node in tree.items():
        products.setdefault(prod, []).append((item, region, node))
    for prod in sorted(products, key=lambda p: -sum(n["payable"] for _, _, n in products[p])):
        prod_total = sum(n["payable"] for _, _, n in products[prod])
        out.append(f"PRODUCT: {prod}   payable total: {fmt(prod_total)}")
        for item, region, node in sorted(products[prod], key=lambda t: -t[2]["payable"]):
            flags = []
            if node["sub_traffic"]:
                flags.append("SUBSCRIPTION-INSTANCE-WITH-POSTPAID-TRAFFIC")
            if node["undeducted"]:
                flags.append("IN-FEE-WITH-ZERO-DEDUCTION")
            if node["mismatches"]:
                flags.append(f"PRICE-X-USAGE-MISMATCH:{node['mismatches']}"
                             "-ROW(S) (needs backend review)")
            flag_txt = ("  [" + "; ".join(flags) + "]") if flags else ""
            out.append(
                f"  item={item or '(unspecified item)'} region={region} "
                f"rows={node['count']} gross={fmt(node['gross'])} "
                f"discount={fmt(node['discount'])} pkgDeduct={fmt(node['pkg'])} "
                f"couponDeduct={fmt(node['coupon'])} payable={fmt(node['payable'])}"
                f"{flag_txt}")
            tops = sorted(node["resources"].items(), key=lambda kv: -kv[1]["payable"])[:top_resources]
            for res_id, res in tops:
                price_txt = (f" x price {res['price']} {res['price_unit']}".rstrip()
                             if res["price"] > 0 else "")
                out.append(
                    f"      resource={res_id} payable={fmt(res['payable'])}"
                    f" usage={fmt(res['usage'])} {res['unit']}{price_txt}")


def cycle_totals(rows: list[dict]) -> dict:
    totals = {k: 0.0 for k in
              ("gross", "discount", "pkg", "coupon", "payable", "outstanding")}
    for r in rows:
        totals["gross"] += r["gross"]
        totals["discount"] += r["discount"]
        totals["pkg"] += r["pkg"]
        totals["coupon"] += r["coupon"]
        totals["payable"] += r["payable"]
        totals["outstanding"] += r["outstanding"]
    return totals


def top_faq_hints(rows: list[dict]) -> list[str]:
    keys = {r["item_key"] for r in rows if r["payable"] > _EPS}
    hints = []
    mapping = {
        "network_out": "traffic-not-traceable",
        "snapshot_capacity": "snapshot-free-quota",
        "disk_capacity": "disk-still-billed",
        "instance_config": "charged-while-stopped",
        "system_disk": "charged-while-stopped",
        "surplus_credit": "burstable-surplus",
        "image_license": "savings-stop",
        "eip": "savings-stop",
    }
    for k in sorted(keys):
        if k in mapping:
            hints.append(f"faq --topic {mapping[k]}")
    any_payable = any(r["payable"] > _EPS for r in rows)
    if any_payable:
        hints.append("faq --topic charge-on-1st")
    return hints


# ---------------------------------------------------------------------------
# Evidence pack (for backend / handoff tickets; raw values preserved)
# ---------------------------------------------------------------------------

def build_evidence_pack(mode: str, cycle: str, uid: str, rows: list[dict] | None,
                        errors: list[str]) -> dict:
    return {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "billing_cycle": cycle,
        "account_uid": uid or "(not resolved)",
        "errors": errors,
        "bill_rows": [
            {k: r[k] for k in ("product", "product_code", "item", "region",
                               "resource", "subscription", "usage",
                               "usage_unit", "price", "payable", "pkg",
                               "coupon", "outstanding", "date")}
            for r in (rows or [])[:80]
        ],
    }


# ---------------------------------------------------------------------------
# Report skeleton
# ---------------------------------------------------------------------------

class Report:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.lines: list[str] = []
        self.data: dict = {"mode": mode}
        self.errors: list[str] = []
        self.auto_filled: list[str] = []
        self.findings: list[str] = []
        self.suggestions: list[str] = []
        self.status = "OK"
        self.next_action = ""
        self.uid = ""

    def note(self, text: str) -> None:
        self.lines.append(text)

    def degrade(self) -> None:
        if self.status == "OK":
            self.status = "DEGRADED"


def finish(rep: Report, as_json: bool) -> int:
    if rep.errors:
        rep.degrade()
    rep.data["status"] = rep.status
    rep.data["next_action"] = rep.next_action or "review the report"
    rep.data["uid"] = rep.uid or None
    rep.data["auto_filled"] = rep.auto_filled
    rep.data["errors"] = rep.errors
    rep.data["summary"] = (
        f"mode={rep.mode}; status={rep.status}; "
        f"errors={len(rep.errors)}; findings={len(rep.findings)}")
    rep.data["key_findings"] = rep.findings
    rep.data["suggestions"] = rep.suggestions

    if as_json:
        print(json.dumps(rep.data, indent=2, ensure_ascii=False))
    else:
        print("=" * 78)
        if rep.uid:
            print(f"Account {rep.uid}")
        print("=" * 78)
        for line in rep.lines:
            print(line)
        if rep.auto_filled:
            print("\nAuto-filled parameters (MUST be declared to the user):")
            for a in rep.auto_filled:
                print(f"  - {a}")
        if rep.errors:
            print("\nErrors / degradations ([WARN] equivalents):")
            for e in rep.errors:
                print(f"  - {e}")
        print("\nSummary")
        print("-------")
        print(f"What was checked : {rep.data['summary']}")
        for f_ in rep.findings:
            print(f"Key finding     : {f_}")
        for s in rep.suggestions:
            print(f"Suggestion      : {s}")
    print(f"\nSTATUS: {rep.status}")
    print(f"NEXT_ACTION: {rep.next_action or 'review the report above'}")
    return 0 if rep.status in ("OK", "DEGRADED") else 1


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def attribute_payable_lead(rep: Report, payable_rows: list, asked_question: str) -> None:
    """Name what the bill read actually attributed, in the verdict rather than the body.

    A charge-inquiry question is answered by naming the product, item, region and
    resource that carry the payable. When the customer states an amount, the row
    matching that amount is the subject of the question - picking the account's
    largest row instead answers a different question than the one asked.
    """
    if not payable_rows:
        return
    attributed: dict = {}
    item_of: dict = {}
    code_of: dict = {}
    prepaid_only: dict = {}
    for row in payable_rows:
        key = (row["product"] or row["product_code"], row["item"],
               row["region"], row["resource"])
        entry = attributed.setdefault(key, 0.0)
        attributed[key] = entry + row["payable"]
        item_of[key] = row.get("item_key") or ""
        code_of[key] = (row.get("product_code") or "").strip().lower()
        prepaid_only[key] = (prepaid_only.get(key, True)
                             and row.get("subscription") == "Subscription")
    stated = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", asked_question or "")]
    matched = [key for key, amount in attributed.items()
               if any(abs(amount - value) <= 0.01 for value in stated)]
    pool = matched
    asked_item = ""
    narrowed_by_ask = False
    if not pool:
        for pattern, item_key in ASKED_ITEM_PATTERNS:
            if re.search(pattern, asked_question or ""):
                asked_item = item_key
                break
        if asked_item and asked_item != "instance_config":
            pool = [key for key in attributed if item_of[key] == asked_item]
            narrowed_by_ask = bool(pool)
    if not pool:
        for pattern, product_code in ASKED_PRODUCT_CUES:
            if re.search(pattern, asked_question or ""):
                pool = [key for key in attributed if code_of[key] == product_code]
                if pool:
                    narrowed_by_ask = True
                    break
    if not pool and asked_item:
        pool = [key for key in attributed if item_of[key] == asked_item]
        narrowed_by_ask = bool(pool)
    if pool and all(prepaid_only.get(key) for key in pool):
        metered = [key for key in attributed if not prepaid_only.get(key)]
        if metered:
            pool = metered
    if not pool and asked_item:
        if re.search(CHARGE_COMPLAINT_INTENT_RE, asked_question or ""):
            meta = BILLING_ITEMS.get(asked_item) or {}
            others = sorted({str(key[0]) for key in attributed})
            rep.note(("MUST-LEAD: [bill-asked-item-not-in-fee] %s carries no payable row "
                      "in this cycle, so it is not what is being charged now; the in-fee "
                      "products are %s"
                      % (meta.get("label", asked_item), ", ".join(others)[:80]))[:220])
        return
    pool = pool or list(attributed)
    named = max(pool, key=lambda key: attributed[key])
    lead = "MUST-LEAD: [bill-payable-attributed] %s / %s payable %s" % (
        str(named[0])[:36], str(named[1])[:28], fmt(attributed[named]))
    if named[2]:
        lead += " in %s" % str(named[2])[:24]
    if named[3]:
        lead += " resource %s" % str(named[3])[:26]
    if narrowed_by_ask:
        outside = [key for key in attributed if key not in pool]
        if outside:
            other = max(outside, key=lambda key: attributed[key])
            if attributed[other] > attributed[named]:
                extra = "; larger in-fee item: %s %s" % (str(other[1])[:24],
                                                        fmt(attributed[other]))
                if len(lead) + len(extra) > 220 and named[3]:
                    lead = lead.split(" resource ")[0]
                lead += extra
    rep.note(lead[:220])


def rule_lead_for(asked_question: str) -> tuple:
    """The rule sentence this first question earns, plus its topic key."""
    for pattern, topic_key in RULE_INTENT_PATTERNS:
        if re.search(pattern, asked_question):
            topic = FAQ_TOPICS.get(topic_key)
            if not topic:
                return "", topic_key
            lead = ". ".join(topic["answer"].split(". ")[:2]).rstrip(".")
            if len(lead) > 260:
                lead = topic["answer"].split(". ")[0].rstrip(".")
            return lead, topic_key
    return "", ""


def rule_topic_is_grounded(topic_key: str, payable_rows: list,
                           resource_gone: bool = False,
                           asked_question: str = "") -> bool:
    """A mechanism rule tied to the bill's own state is not a broad fallback.

    PIT-337 keeps broad FAQ topics from taking the lead slot away from a
    bill-grounded answer. Two of those topics are not broad: the excess-credit
    rule explains a SurplusCredit row that is actually in fee, and the
    released-but-charged rule explains the settlement delay precisely when the
    compute item is NOT in fee. Withholding them there hid the only sentence that
    answered the question.
    """
    if topic_key == "burstable-surplus":
        return any(row["item_key"] == "surplus_credit" and row["payable"] > _EPS
                   for row in payable_rows)
    if topic_key == "released-still-charged":
        if resource_gone or re.search(RELEASE_HOUR_INTENT_RE, asked_question):
            return False
        return not any(row["item_key"] == "instance_config" and row["payable"] > _EPS
                       for row in payable_rows)
    return False


def mode_attribution(rep: Report, args) -> int:
    cycles = walk_cycles(args.billing_cycle, args.months)
    rep.data["billing_cycles"] = cycles
    if len(cycles) > 1:
        rep.note("Billing cycle(s) analyzed: %s  (source: %s)"
                 % (", ".join(cycles), args.cycle_source))
    opening_question = os.environ.get("ECS_CUSTOMER_QUESTION", "")
    if (re.search(SETTLEMENT_INTENT_RE, opening_question)
            or any(cycle_is_unsettled(c) for c in cycles)):
        rep.note("Timing caliber: a cycle's final bill is issued 12:00 on the 3rd "
                 "of the next month; rows lag ~24h, instance fields ~48h; "
                 "current-month figures are provisional.")
    per_cycle_rows: dict[str, list[dict]] = {}
    totals_per_cycle: dict[str, dict] = {}
    used_api = ""
    for cycle in cycles:
        rows, used = fetch_rows(cycle, args.product_code, args.instance_id,
                                rep.errors, args.profile)
        if rows is None:
            rep.note(f"\nCYCLE {cycle}: billing-item query FAILED "
                     f"(see errors below)")
            continue
        used_api = used
        per_cycle_rows[cycle] = rows
        totals_per_cycle[cycle] = cycle_totals(rows)
        rep.note(f"\nCYCLE {cycle}: {len(rows)} billing-item rows "
                 f"(via {used}"
                 + (f"; source: {args.cycle_source}" if len(cycles) == 1 else "")
                 + ")")
        rep.note("  TOTALS: " + "  ".join(
            f"{label}={fmt(totals_per_cycle[cycle][key])}"
            for key, label in (("gross", "gross"), ("discount", "discount"),
                               ("pkg", "pkgDeduct"), ("coupon", "couponDeduct"),
                               ("payable", "payable"))))
        render_tree(aggregate_rows(rows), rep.lines)
        if len(cycles) > 1:
            base = [totals_per_cycle[c]["payable"] for c in cycles
                    if c != cycle and c in totals_per_cycle]
            if base:
                med = statistics.median([b for b in base if b > 0] or [0]) or 0
                if med > 0 and totals_per_cycle[cycle]["payable"] > 3 * med:
                    rep.note(f"  [FLAG] cycle {cycle} payable "
                             f"{fmt(totals_per_cycle[cycle]['payable'])} is "
                             f">3x the median of the other cycles "
                             f"({fmt(med)}) - month-over-month surge.")
    all_rows = [r for rows in per_cycle_rows.values() for r in rows]
    rep.data["rows"] = all_rows if args.json else None
    if not all_rows and all(c not in per_cycle_rows for c in cycles):
        rep.status = "FAIL"
        rep.next_action = ("resolve the query errors first (credential, then "
                           "the missing RAM action per "
                           "references/ram-policies.md), then rerun")
        return finish(rep, args.json)
    if not all_rows:
        rep.findings.append("no billing rows for the queried cycle(s): a "
                            "cycle without usage produces NO rows at all - a "
                            "valid finding, not an error")
        empty_question = os.environ.get("ECS_CUSTOMER_QUESTION", "")
        rep.findings.append(
            "Have the customer take the empty-bill answer first: this cycle has no "
            "in-fee row at all, so nothing is metering now; an amount already "
            "deducted belongs to an EARLIER cycle - query that cycle to attribute it.")
        empty_lead, _empty_topic = rule_lead_for(empty_question)
        if empty_lead:
            rep.findings.append(
                "Have the customer take the rule answer: %s." % empty_lead)
        if re.search(SNAPSHOT_RECURRING_INTENT_RE, empty_question):
            rep.findings.append(
                "Have the customer confirm the snapshot state: ECS console > Snapshots "
                "and the automatic snapshot policy. No snapshot and no row means no "
                "new snapshot fee; releasing the instance does not stop a snapshot fee.")
        rep.next_action = ("confirm the cycle with the customer (a deduction "
                           "on the 1st maps to the PREVIOUS cycle) and rerun")
        return finish(rep, args.json)

    payable_rows = [r for r in all_rows if r["payable"] > _EPS]
    top = sorted(payable_rows, key=lambda r: -r["payable"])[:5]
    rep.findings.append(
        "top in-fee rows: " + "; ".join(
            f"{r['product']}/{r['item']}/{r['region']}/{r['resource']}="
            f"{fmt(r['payable'])}" for r in top))
    undeducted = [r for r in payable_rows
                  if r["pkg"] + r["coupon"] <= _EPS]
    if undeducted:
        rep.findings.append(
            f"{len(undeducted)} row(s) are in fee with ZERO deductions "
            f"(package/coupon) - run --deduction-report for the reason matrix")
        rep.suggestions.append("run the same cycle with --deduction-report")
    conflicts = [r for r in all_rows
                 if r["subscription"] == "Subscription" and is_traffic_row(r)]
    if conflicts:
        rep.findings.append(
            "Subscription instances carry a post-paid outbound-traffic item "
            "(pay-by-traffic bandwidth) - this is the usual 'monthly server "
            "yet still billed' explanation")
        rep.suggestions.append(
            "confirm bandwidth billing mode with --instance-info / "
            "--traffic-check; switching to fixed bandwidth is a manual "
            "console action with a fee-change consequence")
    asked_question = os.environ.get("ECS_CUSTOMER_QUESTION", "")
    led_item_key = ""
    led_topic = ""
    resource_gone = False
    settlement_led = False
    release_time = ""
    policy_only = bool(re.search(CONTRACT_INTENT_RE, asked_question))
    if not policy_only:
        attribute_payable_lead(rep, payable_rows, asked_question)
    stop_all = bool(re.search(STOP_ALL_INTENT_RE, asked_question))
    where_charge = bool(re.search(WHERE_CHARGE_INTENT_RE, asked_question))
    usage_detail = bool(re.search(USAGE_DETAIL_INTENT_RE, asked_question))
    query_path = bool(re.search(QUERY_PATH_INTENT_RE, asked_question))
    inventory_path = bool(re.search(RESOURCE_INVENTORY_INTENT_RE, asked_question))
    snapshot_progress = bool(re.search(SNAPSHOT_PROGRESS_INTENT_RE, asked_question))
    snapshot_recurring = bool(re.search(SNAPSHOT_RECURRING_INTENT_RE, asked_question))
    snapshot_delete = bool(re.search(SNAPSHOT_DELETE_INTENT_RE, asked_question))
    split_bill = bool(re.search(SPLIT_BILL_INTENT_RE, asked_question))
    totals_intent = bool(re.search(TOTALS_INTENT_RE, asked_question))
    refund_explain = bool(re.search(REFUND_EXPLAIN_INTENT_RE, asked_question))
    monthly_estimate = bool(re.search(MONTHLY_ESTIMATE_INTENT_RE, asked_question))
    conversion_intent = bool(re.search(CONVERSION_INTENT_RE, asked_question))
    deferred_stop = bool(re.search(DEFERRED_STOP_INTENT_RE, asked_question))
    if policy_only:
        for line in CONTRACT_POLICY_ANSWER:
            rep.findings.append(line)
    billed_ids = sorted({r["resource"] for r in payable_rows
                         if (r["product_code"] or "").strip().lower() == "ecs"
                         and (r["resource"] or "").startswith("i-")})
    probe_ids = [args.instance_id] if args.instance_id else billed_ids[:1]
    if probe_ids:
        errors_before = len(rep.errors)
        live = fetch_instances(args.region, probe_ids, rep.errors, args.profile)
        matched = [i for i in live
                   if (i.get("InstanceId") or "") in probe_ids]
        if len(rep.errors) > errors_before:
            rep.note("WITHHELD-LEAD: the instance read failed, so whether the billed "
                     "instance still exists was not established")
            rep.findings.append(
                "Have the customer confirm in ECS console > Instances whether %s still "
                "exists: this run could not read it, so a release must not be assumed."
                % ", ".join(probe_ids))
        elif not matched:
            resource_gone = True
        else:
            status = (matched[0].get("Status") or "").strip()
            resource_gone = status in ("Released", "Deleted")
            release_time = matched[0].get("ReleaseTime") or ""
    rule_lead, rule_topic = ("", "") if policy_only else rule_lead_for(asked_question)
    fallback_lead, fallback_topic = "", ""
    if (rule_topic in RULE_FALLBACK_TOPICS
            and not rule_topic_is_grounded(rule_topic, payable_rows, resource_gone,
                                           asked_question)):
        fallback_lead, fallback_topic = rule_lead, rule_topic
        rule_lead, rule_topic = "", ""
    if rule_topic:
        if rule_lead:
            rep.findings.append(
                "Have the customer take the rule answer first: %s." % rule_lead)
            led_topic = rule_topic
    else:
        for pattern, item_key in (() if (resource_gone or policy_only)
                                  else ASKED_ITEM_PATTERNS):
            if re.search(pattern, asked_question):
                meta = BILLING_ITEMS.get(item_key)
                if meta and meta.get("note"):
                    in_fee = any(r["item_key"] == item_key and r["payable"] > _EPS
                                 for r in payable_rows)
                    if in_fee:
                        lead = ". ".join(meta["note"].split(". ")[:2]).rstrip(".")
                        rep.findings.append(
                            "Have the customer take the %s rule first: %s."
                            % (meta.get("label", item_key), lead))
                        led_item_key = item_key
                    else:
                        rep.findings.append(
                            "Have the customer take the asked-item answer first: "
                            "%s has NO payable row in this cycle, so it is not "
                            "what is being charged now - confirm in the console "
                            "that the resource is already deleted/released; the "
                            "amount below comes from the items that ARE in fee."
                            % meta.get("label", item_key))
                        led_item_key = item_key
                        item_rule, item_topic = rule_lead_for(asked_question)
                        if (item_rule
                                and RULE_TOPIC_ASKED_ITEM.get(item_topic) == item_key
                                and not any("MUST-LEAD" in line for line in rep.lines)):
                            rep.note(("MUST-LEAD: [bill-item-rule] " + item_rule)[:220])
                break
    if resource_gone:
        others = sorted({(r["product"] or r["product_code"]) for r in payable_rows
                         if (r["product_code"] or "").strip().lower() != "ecs"
                         and r["payable"] > _EPS})
        lifecycle_lead = (
            "Have the customer then take the lifecycle answer: "
            if (led_topic or led_item_key) else
            "Have the customer take the lifecycle answer first: ")
        rep.findings.append(
            lifecycle_lead +
            "the billed instance no longer exists (already released%s), so this "
            "is the delayed settlement of usage BEFORE the release, and no new fee "
            "accrues after it; do not release or stop anything again."
            % (" at %s" % release_time if release_time else ""))
        rep.findings.append(
            "Have the customer check the release time against the last billed hour: "
            "billing is hourly, so a release at 15:30 still owes the 15:00-16:00 hour, "
            "issued after 16:00. " + (
            "No other product is in fee in this cycle."
            if not others else
            "These other products ARE still in fee and need their own check: "
            + ", ".join(others) + "."))
    rule_only = led_topic in RULE_ONLY_TOPICS
    if led_topic == "postpaid-cycle-provisional":
        rep.findings.append(
            "Have the customer keep the resources running: nothing has to be "
            "released or stopped for this figure to settle - it is this cycle's "
            "metered post-paid usage, and the exact amount is deducted when the "
            "final bill is issued at 12:00 on the 3rd of next month.")
        rep.findings.append(
            "Have the customer reconcile that cycle rather than the account total: "
            "Billing console -> Bill Details, select the cycle, and compare the "
            "payable and paid columns; Account Overview shows the balance the "
            "settlement will draw from.")
    if led_topic == "postpaid-invoice-timing":
        rep.findings.append(
            "Have the customer invoice the part that is already invoiceable: "
            "already-paid pre-paid orders can be applied for now at "
            + INVOICE_CREATE_URL +
            "; the post-paid cycle stays unavailable until it is issued.")
    if led_topic == "student-coupon-spec-scope":
        rep.findings.append(
            "Have the customer treat this list as REFERENCE ONLY - activity scope "
            "changes often, so verify the current list on the official page and "
            "note this skill does not guarantee the link or the list stays "
            "current: " + COUPON_RULES_URL + ". Specifications seen in tickets: "
            + STUDENT_COUPON_SPEC_SNAPSHOT + ".")
    if snapshot_progress:
        rep.findings.append(
            "Have the customer read the creation progress in ECS console > Snapshots: "
            "the snapshot is complete only at 100%, and only then is it usable as a "
            "restore point.")
        rep.findings.append(
            "Have the customer know snapshot billing starts only AFTER the creation "
            "completes, is pay-as-you-go by snapshot type and capacity settled per "
            "region, and appears in the bill the next day; the row's own price is "
            "authoritative.")
        rep.findings.append(
            "Have the customer KEEP this snapshot while a rollback is still possible - "
            "it is the disk's restore point; delete it only after they confirm no "
            "restore point is needed, and deletion is irreversible.")
        rep.findings.append(
            "Have the customer note the fee comes out of the account balance and a "
            "Subscription instance is NOT stopped by arrears; a snapshot with a fixed "
            "retention is released automatically when the retention ends.")
    if snapshot_recurring:
        rep.findings.append(
            "Have the customer confirm the snapshot state before acting: ECS console > "
            "Snapshots and the automatic snapshot policy. If no snapshot remains, no "
            "new snapshot fee accrues and the amount seen is the earlier cycles' "
            "settlement - releasing the instance does not stop a snapshot fee.")
    if snapshot_delete:
        rep.findings.append(
            "Have the customer clear the dependency before deleting: a snapshot still "
            "referenced by a custom image cannot be deleted - delete that image first, "
            "and cancel the share before deleting a shared image.")
        rep.findings.append(
            "Have the customer delete the automatic snapshot policy too, or new "
            "snapshots keep accruing; deleting a snapshot leaves the running instance "
            "untouched but removes that restore point for good.")
    if split_bill:
        rep.findings.append(
            "Have the customer read the association in Split Bill, not Bill Details: "
            "it names the disk or instance each snapshot-chain charge belongs to.")
        rep.note("Split Bill for this cycle: %s?BillingCycle=%s."
                 % (SPLIT_BILL_URL, cycles[0] if cycles else ""))
    if any(row["item_key"] == "surplus_credit" for row in payable_rows):
        rep.findings.append(
            "Have the customer confirm when unlimited mode was turned on: read the "
            "operation log (ActionTrail) for ModifyInstanceAttribute with "
            "CreditSpecification=Unlimited on that instance.")
    if totals_intent:
        rep.findings.append(
            "Have the customer read the Payable amount column as the final figure "
            "(after discounts and deductions), not the gross/list column - that is "
            "the column to compare against an externally generated estimate.")
        rep.findings.append(
            "Have the customer include snapshot fees in the ECS total: snapshots "
            "are billed under ECS, not as a separate product.")
        rep.findings.append(
            "Have the customer total each product over the whole period in Bill "
            "Overview by product at "
            + CONSOLE_PATHS["month-bill-by-product"]["url"] +
            " and sum the payable column per product; one month of one billing "
            "item cannot validate a yearly multi-product figure.")
    if monthly_estimate:
        rep.findings.append(
            "Have the customer size the month from the per-day rows: open "
            + CONSOLE_PATHS["expense-detail-usercenter"]["url"] +
            ", select Day granularity and export the CSV; the rows carry the "
            "billing item, unit price, usage and package deduction, so multiply the "
            "observed daily figure by the days the resource will be kept.")
    if conversion_intent:
        rep.findings.append(
            "Have the customer convert the instance in ECS console > instance "
            "details > All Actions > Switch to Subscription, set the term and "
            "confirm the payment (" + CONVERSION_DOC_URL + ").")
        rep.findings.append(
            "Have the customer note the conversion covers the instance "
            "specification and the system disk only: a pay-by-traffic bandwidth "
            "still produces traffic fees, so switch the bandwidth to fixed "
            "bandwidth after placing the conversion order.")
    if deferred_stop:
        rep.findings.append(
            "Have the customer check the deferred-suspension allowance on the "
            "account at " + BILLING_ACCOUNT_URL + ": the page shows whether it is "
            "enabled and lets them turn it off; while it is on, post-paid usage "
            "keeps being paid for a limited allowance after arrears.")
        rep.findings.append(
            "Have the customer know an arrears stop is not a release: the "
            "pay-as-you-go instance still occupies compute and storage, so the "
            "specification fee continues; only after they confirm the data is "
            "backed up may they release it themselves (irreversible, never done "
            "for them).")
    non_ecs = [r for r in payable_rows
               if any(t in (r["product_code"] + " " + r["product"]).lower()
                      for t in NON_ECS_PRODUCT_TOKENS)]
    if non_ecs:
        totals = {}
        for row in non_ecs:
            code = (row["product_code"] or "").strip().lower()
            entry = totals.setdefault(code, {"label": row["product"], "payable": 0.0})
            entry["payable"] += row["payable"]
        lead_code = max(totals, key=lambda code: totals[code]["payable"])
        lead = totals[lead_code]
        ecs_payable = sum(r["payable"] for r in payable_rows
                          if (r["product_code"] or "").strip().lower() == "ecs")
        prepaid = any(r["subscription"] == "Subscription" for r in all_rows
                      if (r["product_code"] or "").strip().lower() == "ecs")
        contrast = ("not ECS (Subscription, prepaid)" if prepaid
                    else "not only ECS (in fee at %s)" % fmt(ecs_payable))
        rules = NON_ECS_BILLING_RULES.get(lead_code)
        stop = ("; to stop it, %s" % rules["stop"]) if rules else ""
        if stop_all:
            ranked = sorted(totals, key=lambda code: -totals[code]["payable"])
            for code in ranked[:STOP_ALL_DETAILED_PRODUCTS]:
                entry = totals[code]
                rep.findings.append(
                    "Have the customer stop %s (%s): %s."
                    % (NON_ECS_SHORT_LABEL.get(code, entry["label"]),
                       fmt(entry["payable"]),
                       NON_ECS_STOP_BRIEF.get(
                           code, "release or delete the resource in its own console")))
            tail = ranked[STOP_ALL_DETAILED_PRODUCTS:]
            if tail:
                rep.findings.append(
                    "Have the customer also stop %s: %s."
                    % (" and ".join(
                        "%s (%s)" % (NON_ECS_SHORT_LABEL.get(code, totals[code]["label"]),
                                     fmt(totals[code]["payable"])) for code in tail),
                       ", then ".join(
                           NON_ECS_STOP_BRIEF.get(
                               code, "release or delete the resource in its own console")
                           for code in tail)))
            rep.findings.append(
                "Have the customer do each deletion themselves after a verified "
                "backup: irreversible, data unrecoverable, never done for them.")
            rep.findings.append(
                "Have the customer unsubscribe pre-paid resources at "
                + REFUND_ENTRY_URL + ": a release does not end a subscription; back "
                "up first, data is cleared (ECS kept 15 days), refund in ~2 working "
                "days, invoiceable quota drops, gifted coupons void.")
        else:
            rep.findings.append(
                "Have the customer note the charge is from %s (payable %s), %s%s."
                % (lead["label"], fmt(lead["payable"]), contrast, stop))
            if re.search(RELEASE_HOUR_INTENT_RE, asked_question):
                settlement_led = True
                rep.findings.append(
                    "Have the customer know the ECS bill dated after the release is "
                    "the last hourly cycle settling late, not a new ECS fee.")
            rest = [code for code in sorted(totals, key=lambda c: -totals[c]["payable"])
                    if code != lead_code]
            if rest:
                rep.findings.append(
                    "Have the customer also check the other products in fee: %s - "
                    "each is billed by its own product rules."
                    % ", ".join("%s (%s)" % (totals[code]["label"],
                                             fmt(totals[code]["payable"]))
                                for code in rest))
            if rules:
                rep.findings.append(
                    "Have the customer know %s%s."
                    % (rules["rule"],
                       "" if (where_charge or rules.get("package_entry"))
                       else "; " + rules["package"]))
                if rules.get("package_entry") and not where_charge:
                    rep.findings.append(
                        "Have the customer buy one resource package per item at "
                        + rules["package_entry"] + ": " + rules["package_choice"] + ".")
                if rules.get("console_entry") and not where_charge:
                    rep.findings.append(
                        "Have the customer use the product's own console to turn the "
                        "pay-as-you-go feature off: " + rules["console_entry"] + ".")
                if not where_charge:
                    rep.findings.append(
                        "Have the customer note %s%s."
                        % (rules["scope"],
                           "; " + NON_ECS_CONSOLE_FILTER
                           + ("" if rules.get("package_entry")
                              else NON_ECS_FUND_FLOW_NOTE)))
        rep.suggestions.append(
            "hand the product-specific follow-up to that product's channel "
            "(references/billing-attribution-bill-check__handoff-map.md)")
    for hint in top_faq_hints(all_rows):
        rep.suggestions.append(hint)
    overdue = [r for r in all_rows if r["outstanding"] > _EPS]
    if overdue:
        due_total = sum(r["outstanding"] for r in overdue)
        lead_due = max(overdue, key=lambda r: r["outstanding"])
        rep.findings.append(
            "Have the customer clear the overdue %s on %s: %s, so top up at least "
            "%s at %s; the top-up is first frozen against the bill (cash balance "
            "is not available credit), then deducted on the 3rd of next month."
            % (fmt(due_total), lead_due["item"],
               "arrears interrupt the account's other post-paid services"
               if resource_gone else "arrears stops the instance",
               fmt(due_total), RECHARGE_URL))
        recurring = min((r["payable"] for r in overdue if r["payable"] > _EPS),
                        default=0.0)
        keep = (" above the recurring %s fee" % fmt(recurring)) if recurring else ""
        rep.findings.append(
            "Have the customer keep the balance%s and enable the balance alert."
            % keep)
        question = os.environ.get("ECS_CUSTOMER_QUESTION", "")
        if re.search(r"(?i)(无法访问|访问不了|打不开|域名|网站|unreachable|inaccessible|website|domain)",
                     question):
            rep.findings.append(
                "Have the customer verify the domain status and DNS resolution "
                "are normal first: the arrears stop is on the server, not the name.")
            rep.findings.append(
                "Have the customer retry after the top-up; if https still fails "
                "there is no certificate - test http://<host>/ in a private window.")
    daily_requested = bool(re.search(r"(每天|每日|一天|日均|per day|daily)",
                                     os.environ.get("ECS_CUSTOMER_QUESTION", "")))
    ecs_payable_rows = [r for r in payable_rows
                        if (r["product_code"] or "").strip().lower() == "ecs"]
    top_ecs = max(ecs_payable_rows, key=lambda r: r["payable"], default=None)
    asked_item = None
    for pattern, key in ASKED_ITEM_PATTERNS:
        if re.search(pattern, os.environ.get("ECS_CUSTOMER_QUESTION", "")):
            asked_item = key
            break
    if asked_item:
        named = [r for r in ecs_payable_rows if r["item_key"] == asked_item]
        if named:
            top_ecs = max(named, key=lambda r: r["payable"])
    else:
        specialty = [r for r in ecs_payable_rows
                     if r["item_key"] in SPECIALTY_BILLING_ITEMS]
        if specialty:
            top_ecs = max(specialty, key=lambda r: r["payable"])
    specialty_asked = bool(
        asked_item in SPECIALTY_BILLING_ITEMS
        and any(r["item_key"] == asked_item and r["payable"] > _EPS
                for r in ecs_payable_rows))
    stop_route = (STOP_BILLING_ROUTES.get(top_ecs["item_key"])
                  if (top_ecs and not non_ecs and not overdue
                      and not resource_gone and not policy_only
                      and not rule_only
                      and not stop_all
                      and not snapshot_progress
                      and not totals_intent
                      and not conversion_intent
                      and not deferred_stop
                      and not refund_explain
                      and led_topic != "plan-quota-remaining-but-charged")
                  else None)
    if led_topic == "plan-quota-remaining-but-charged" and ecs_payable_rows:
        named_ids = sorted({r["resource"] for r in ecs_payable_rows
                            if (r["resource"] or "").startswith("i-")})
        rep.findings.append(
            "Have the customer check this per instance, not account-wide: the "
            "payable rows here belong to %s - open ECS console > Instances and "
            "read that instance's specification change history, then compare the "
            "specification before and after the change with the plan's covered "
            "list. Any instance still listed in the plan's deduction detail is "
            "being offset normally and must NOT be released. The remedy for the "
            "uncovered usage is to top up the account balance."
            % (", ".join(named_ids) if named_ids else "the instances in the rows above"))
    focused = bool(overdue or non_ecs or daily_requested or stop_route
                   or led_topic or led_item_key or resource_gone)
    in_fee_keys = {r["item_key"] for r in payable_rows if r["item_key"]}
    if overdue:
        in_fee_keys = set()
    for key in sorted(in_fee_keys):
        meta = BILLING_ITEMS.get(key)
        redundant = led_topic and stop_route and top_ecs and key == top_ecs["item_key"]
        if (meta and meta.get("note") and key != led_item_key
                and not (specialty_asked and key != asked_item)
                and not redundant and not resource_gone and not policy_only
                and not rule_only
                and not (snapshot_progress and key == "snapshot_capacity")
                and not totals_intent
                and not (conversion_intent or deferred_stop)
                and (not stop_all or key in STOP_ALL_ECS_ITEMS)):
            if focused:
                note = meta.get("metering") or re.split(r"[.;] ", meta["note"])[0]
            else:
                note = meta["note"]
            rep.findings.append(
                "Have the customer understand the %s: %s"
                % (meta.get("label", key), note))
    if stop_route:
        stop_meta = BILLING_ITEMS.get(top_ecs["item_key"]) or {}
        stop_label = stop_meta.get("label") or top_ecs["item"]
        if stop_label.lower().endswith(" fee"):
            stop_label = stop_label[:-4]
        rep.findings.append(
            "Have the customer stop the %s fee this way: %s."
            % (stop_label, stop_route))
    if re.search(r"(?i)(费用明细|账单明细|扣费模式|收支明细|明细|导出|账单|统计|invoice|bill detail)",
                 os.environ.get("ECS_CUSTOMER_QUESTION", "")) and not (
                     where_charge or usage_detail or totals_intent):
        rep.findings.append(
            "Have the customer read and export the figures: Billing console -> "
            "Bill Details (per product/item, CSV export) and Fund Flow Detail; "
            "compare the payable and paid columns.")
    if where_charge:
        rep.findings.append(
            "Have the customer locate the charging product first: Bill Overview "
            "by product at " + CONSOLE_PATHS["month-bill-by-product"]["url"] + ".")
        rep.findings.append(
            "Have the customer then read the exact hour of every charge: "
            + CONSOLE_PATHS["bill-detail-by-instance"]["url"]
            + "?BillingCycle=" + cycles[-1]
            + "&StatisticItem=DEFAULT_CHARGE_ITEM&StatisticCycle=HOURLY. Post-paid "
            "rows lag behind usage, so the newest hours can be missing; once no new "
            "row appears after an hour, metering has caught up to that point.")
    if usage_detail:
        rep.findings.append(
            "Have the customer export the usage detail, not only the amount: "
            "Bill Details -> View Usage Detail, set Commodity Name = ECS and "
            "Billing Item = Internet Outbound Traffic, then export the CSV.")
        rep.findings.append(
            "Have the customer know what generates outbound traffic: "
            + TRAFFIC_GENERATORS + "; read the hourly series to locate the burst "
            "before attributing it.")
    if inventory_path:
        rep.findings.append(
            "Have the customer list what still exists at "
            + CONSOLE_PATHS["ecs-instance-list"]["url"]
            + ", switching the region at the top one by one: the list is per region, so "
            "one region can look empty while another still bills. Orders are at "
            + CONSOLE_PATHS["order-list"]["url"] + ".")
    elif query_path and not usage_detail:
        rep.findings.append(
            "Have the customer read the usage, not just the amount: "
            + CONSOLE_PATHS["expense-detail-usercenter"]["url"]
            + " -> View Usage Detail, set Commodity Name and Billing Item, export the CSV; "
            "order records are at " + CONSOLE_PATHS["order-list"]["url"] + ".")
    if not resource_gone and not deferred_stop and not settlement_led and re.search(
            RELEASE_HOUR_INTENT_RE, os.environ.get("ECS_CUSTOMER_QUESTION", "")):
        rep.findings.append(
            "Have the customer check the release time against the last billed hour: "
            "billing is hourly, so a release at 15:30 still owes the 15:00-16:00 hour, "
            "issued after 16:00 (the row settles 2-3 hours later); no new fee accrues after that."
            if focused else
            "Have the customer check the release time against the last billed hour: "
            "billing is hourly, so a release at 15:30 still owes the 15:00-16:00 hour, "
            "issued after 16:00 (the row settles 2-3 hours later); usage stops at the release "
            "moment and no new fee accrues after that once no other product is in fee.")
    if fallback_lead and not payable_rows and not (
            led_topic or led_item_key or resource_gone):
        rep.findings.append("Have the customer also know: %s." % fallback_lead)
    rep.suggestions.append(
        "console cross-check: " + CONSOLE_PATHS["bill-detail-by-instance"]["url"]
        + " with BillingCycle=" + cycles[-1]
        + "&StatisticItem=DEFAULT_CHARGE_ITEM&StatisticCycle=MONTHLY")
    mismatch_rows = [r for r in all_rows if recompute_check(r) == "mismatch"]
    if mismatch_rows:
        rep.findings.append(
            f"{len(mismatch_rows)} row(s) where usage x price does not "
            f"explain the amount within 10% - do NOT round it off; needs "
            f"backend review with the evidence pack")
        rep.data["evidence_pack"] = build_evidence_pack(
            rep.mode, cycles[-1], rep.uid, all_rows, rep.errors)
    rep.next_action = (
        "for the dominant item run --daily for the per-day series and "
        "--traffic-check when the item is outbound traffic; settle every "
        "statement against the printed amounts (no fabrication)")
    if all_rows:
        totals = cycle_totals(all_rows)
        if daily_requested:
            rates = {}
            for row in ecs_payable_rows:
                if (row["price"] > 0 and not is_traffic_row(row)
                        and "hour" in (row["price_unit"] or row["usage_unit"] or "").lower()):
                    key = (row["resource"], row["item_key"])
                    rates[key] = max(rates.get(key, 0.0), row["price"])
            hourly_rate = sum(rates.values())
            if hourly_rate > 0:
                rep.findings.append(
                    "Have the customer take the daily figure as the current run rate, "
                    "not the cycle total divided by calendar days: these ECS items are "
                    "priced at %s per hour in the rows, so about %s per day while they "
                    "run, with outbound traffic metered per GB on top. %s is still in "
                    "progress, so its total is provisional."
                    % (fmt(hourly_rate), fmt(hourly_rate * 24), cycles[-1]))
            else:
                days = days_in_cycle(cycles[-1])
                rep.findings.append(
                    "Have the customer read the daily figure from the per-day series "
                    "instead of dividing the cycle: %s payable so far in %s (%d calendar "
                    "days) is provisional, so a total-over-days average understates the "
                    "current run rate."
                    % (fmt(totals["payable"]), cycles[-1], days))
            rep.findings.append(
                "Have the customer know the system disk is already inside the instance "
                "specification price, while an added data disk is a separate item whose "
                "hourly price is shown on the order page. To lower the recurring cost, "
                "lower the instance specification or the disk capacity - stopping does "
                "not stop the specification fee.")
        rep.note("Confirm every figure in Bill Details for this cycle: "
                 + CONSOLE_PATHS["bill-detail-by-instance"]["url"]
                 + "?BillingCycle=" + cycles[-1] + ".")
    else:
        rep.note("Have the customer open Billing console -> Bill Details "
                 "(filter: instance id + BillingCycle=" + cycles[-1] + ") and "
                 "paste the rows back; read every amount from the rows, never "
                 "estimate it.")
    return finish(rep, args.json)


def mode_overview(rep: Report, args) -> int:
    try:
        rows = fetch_overview_rows(args.billing_cycle, args.product_code,
                                   args.profile)
    except _cli.CliError as e:
        rep.errors.append(f"QueryBillOverview: {e.code or 'error'}: {e}")
        rep.status = "FAIL"
        rep.next_action = ("check the credential and the bss bill-read "
                           "permission (references/ram-policies.md), then "
                           "rerun")
        return finish(rep, args.json)
    rep.note(f"Cycle {args.billing_cycle}: {len(rows)} overview rows")
    render_tree(aggregate_rows(rows), rep.lines)
    totals = cycle_totals(rows)
    rep.note("TOTALS: payable=" + fmt(totals["payable"]) +
             "  pkgDeduct=" + fmt(totals["pkg"]) +
             "  couponDeduct=" + fmt(totals["coupon"]))
    if not rows:
        rep.findings.append("the cycle has no entries at all: zero usage "
                            "billed -> no bill rows exist (valid finding)")
    else:
        rep.findings.append("cycle payable total = " + fmt(totals["payable"]))
    rep.data["rows"] = rows if args.json else None
    rep.suggestions.append("drill into the dominant product with the default "
                           "attribution mode (--billing-cycle "
                           + args.billing_cycle + ")")
    rep.next_action = ("run the attribution mode on the cycle to split each "
                       "product into billing items / regions / resources")
    return finish(rep, args.json)


def mode_monthly_total(rep: Report, args) -> int:
    params = {"BillingCycle": args.billing_cycle}
    try:
        items = _cli.paginate_page_num("bssopenapi", "QueryBill", params,
                                       profile=args.profile)
    except _cli.CliError as e:
        rep.errors.append(f"QueryBill: {e.code or 'error'}: {e}")
        rep.status = "FAIL"
        rep.next_action = "fix the credential / permission, then rerun"
        return finish(rep, args.json)
    payable = sum(num(i, "PretaxAmount", "PayableAmount") for i in items
                  if isinstance(i, dict))
    gross = sum(num(i, "PretaxGrossAmount") for i in items if isinstance(i, dict))
    rep.note(f"Cycle {args.billing_cycle}: {len(items)} bill-record rows; "
             f"gross={fmt(gross)} payable={fmt(payable)}")
    rep.findings.append(f"QueryBill cycle payable = {fmt(payable)}")
    rep.data["bill_records"] = items if args.json else None
    rep.suggestions.append("compare with --overview and --settlement in "
                           "--reconcile mode")
    rep.next_action = "run --reconcile to cross-check all amount layers"
    return finish(rep, args.json)


def _walk_amounts(obj, prefix: str, out: dict) -> None:
    """Collect every leaf whose key looks like an amount field (relay of
    returned values only - no interpretation)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                _walk_amounts(v, path, out)
            elif any(t in k for t in ("Amount", "Balance")):
                try:
                    out[path] = float(str(v).replace(",", ""))
                except (TypeError, ValueError):
                    pass
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            _walk_amounts(v, f"{prefix}[{idx}]", out)


def mode_settlement(rep: Report, args) -> int:
    try:
        amounts = fetch_settle_amounts(args.billing_cycle, args.profile)
    except _cli.CliError as e:
        rep.errors.append(f"QuerySettleBill: {e.code or 'error'}: {e}")
        rep.status = "FAIL"
        rep.next_action = "fix the credential / permission, then rerun"
        return finish(rep, args.json)
    rep.note(f"QuerySettleBill cycle {args.billing_cycle}: {len(amounts)} "
             f"amount field(s) relayed verbatim from the response")
    if amounts:
        for path, val in sorted(amounts.items()):
            rep.note(f"  {path} = {fmt(val)}")
        rep.findings.append("settlement amounts above are relayed verbatim "
                            "from the API (field-caliber definitions in "
                            "references/billing-attribution-bill-check__billing-timing-and-caliber.md)")
    else:
        rep.findings.append("no amount fields returned; the cycle has no "
                            "settlement records")
    rep.data["settlement_amounts"] = amounts if args.json else None
    rep.next_action = "run --reconcile to compare the layers against each other"
    return finish(rep, args.json)


def mode_reconcile(rep: Report, args) -> int:
    cycle = args.billing_cycle
    overview_payable = bill_payable = None
    try:
        ov = fetch_overview_rows(cycle, None, args.profile)
        overview_payable = sum(r["payable"] for r in ov)
    except _cli.CliError as e:
        rep.errors.append(f"QueryBillOverview: {e.code or 'error'}: {e}")
    try:
        bq = _cli.paginate_page_num("bssopenapi", "QueryBill",
                                    {"BillingCycle": cycle},
                                    profile=args.profile)
        bill_payable = sum(num(i, "PretaxAmount", "PayableAmount")
                           for i in bq if isinstance(i, dict))
    except _cli.CliError as e:
        rep.errors.append(f"QueryBill: {e.code or 'error'}: {e}")
    settle_amounts: dict = {}
    try:
        settle_amounts = fetch_settle_amounts(cycle, args.profile)
    except _cli.CliError as e:
        rep.errors.append(f"QuerySettleBill: {e.code or 'error'}: {e}")

    rep.note(f"Four-layer reconciliation for {cycle}")
    rep.note(f"  L1 overview payable  : "
             + ("-" if overview_payable is None else fmt(overview_payable)))
    rep.note(f"  L2 bill payable      : "
             + ("-" if bill_payable is None else fmt(bill_payable)))
    rep.note(f"  L3 settlement amounts: "
             + (", ".join(f"{k}={fmt(v)}" for k, v in sorted(settle_amounts.items()))
                or "none returned"))
    if overview_payable is not None and bill_payable is not None:
        delta = overview_payable - bill_payable
        tol = max(abs(bill_payable) * 0.01, 0.5)
        verdict = "CONSISTENT" if abs(delta) <= tol else "MISMATCH"
        rep.note(f"  L1-L2 delta        : {fmt(delta)} -> {verdict}")
        rep.findings.append(f"L1/L2 cross-check: {verdict} "
                            f"(delta {fmt(delta)}, tolerance {fmt(tol)})")
    rep.note("\nAmount-field caliber (definitions, relayed from references):")
    for k, v in AMOUNT_FIELDS.items():
        rep.note(f"  {k}: {v}")
    rep.note("\nTiming caliber (MUST be stated to the customer):")
    for t in TIMING_CALIBER:
        rep.note(f"  - {t}")
    rep.findings.append("the account's unpaid/arrears figure mixes prior "
                        "cycles and unsettled items; bill-total equality "
                        "with 'amount due' is NOT expected while a cycle is "
                        "provisional")
    mismatch = False
    if overview_payable is not None and bill_payable is not None:
        mismatch = abs(overview_payable - bill_payable) > max(
            abs(bill_payable) * 0.01, 0.5)
    if mismatch or rep.errors:
        rep.data["evidence_pack"] = build_evidence_pack(
            "reconcile", cycle, rep.uid, None, rep.errors)
        rep.suggestions.append("if the customer still disputes the layers "
                               "after this caliber explanation, attach the "
                               "EVIDENCE PACK (data.evidence_pack) to a "
                               "backend review ticket - do not guess a "
                               "cause")
    rep.next_action = (
        "explain every remaining delta with the caliber + timing above; "
        "anything unexplained goes to the backend ticket with the evidence "
        "pack")
    return finish(rep, args.json)


def mode_daily(rep: Report, args) -> int:
    dates = last_days_of_cycle(args.billing_cycle, args.days)
    rep.note(f"Per-day series for {args.billing_cycle}: {dates[0]} .. "
             f"{dates[-1]} ({len(dates)} day(s), cap {MAX_DAILY_DAYS})")
    series: list[dict] = []
    for d in dates:
        params: dict = {"BillingCycle": args.billing_cycle,
                        "Granularity": "DAILY", "BillingDate": d,
                        "IsBillingItem": True}
        if args.instance_id:
            params["InstanceID"] = args.instance_id
        if args.product_code:
            params["ProductCode"] = args.product_code
        try:
            items = _cli.paginate_next_token(
                "bssopenapi", "DescribeInstanceBill", params,
                profile=args.profile)
        except _cli.CliError as e:
            rep.errors.append(f"DescribeInstanceBill {d}: {e.code or 'error'}: {e}")
            continue
        rows = [row_view(i) for i in items if isinstance(i, dict)]
        traffic = [r for r in rows if is_traffic_row(r)]
        series.append({
            "date": d,
            "payable": sum(r["payable"] for r in rows),
            "traffic_usage": sum(r["usage"] for r in traffic),
            "traffic_payable": sum(r["payable"] for r in traffic),
            "traffic_unit": next((r["usage_unit"] for r in traffic if r["usage_unit"]), ""),
            "items": sorted({r["item"] for r in rows if r["payable"] > _EPS}),
        })
    if not series:
        rep.status = "FAIL"
        rep.next_action = "billing-date granularity failed for every day; " \
                          "check the RAM permission then rerun"
        return finish(rep, args.json)
    for s in series:
        rep.note(f"  {s['date']}  payable={fmt(s['payable'])}"
                 f"  traffic_usage={fmt(s['traffic_usage'])} {s['traffic_unit']}"
                 f"  traffic_payable={fmt(s['traffic_payable'])}"
                 + ("  items=" + ",".join(s["items"]) if s["items"] else ""))
    vals = [s["traffic_payable"] for s in series if s["traffic_payable"] > 0]
    if len(vals) >= 4:
        med = statistics.median(vals)
        mx = max(vals)
        if med > 0 and mx > 3 * med:
            spike = max(series, key=lambda s: s["traffic_payable"])
            rep.findings.append(
                f"traffic spike day flagged: {spike['date']} "
                f"({fmt(spike['traffic_payable'])} vs median "
                f"{fmt(med)}) - >3x the typical day")
            rep.suggestions.append(
                "correlate the spike with CloudMonitor bandwidth via "
                "--traffic-check; per-destination traffic is NOT "
                "traceable cloud-side (privacy) - handoff per "
                "references/billing-attribution-bill-check__handoff-map.md")
    rep.data["series"] = series
    rep.findings.append(f"{len(series)} day(s) sampled of {len(dates)} requested")
    rep.suggestions.append("amounts are bill-side and lag ~24h; state the "
                           "timing caliber when presenting the series")
    rep.next_action = ("attribute the flagged day with the attribution mode "
                       "using --instance-id, and cross-check usage with "
                       "--traffic-check")
    return finish(rep, args.json)


def mode_traffic_check(rep: Report, args) -> int:
    if not args.instance_id:
        rep.status = "FAIL"
        rep.next_action = ("ask the customer for the instance ID (i-...) "
                           "whose traffic fee is questioned; the bill rows "
                           "from attribution mode also carry it")
        return finish(rep, args.json)
    if not _REGION_RE.match(args.region):
        rep.status = "FAIL"
        rep.next_action = "supply a valid --region (e.g. cn-hangzhou)"
        return finish(rep, args.json)
    rep.auto_filled.append(
        f"region defaulted to {DEFAULT_REGION}" if args.region_defaulted
        else f"region {args.region} taken from the customer/bill row")
    instances = fetch_instances(args.region, [args.instance_id], rep.errors,
                                args.profile)
    if instances:
        i0 = instances[0]
        public_ips = [ip_text(a)
                      for a in (i0.get("PublicIpAddress") or {}).get("IpAddress", [])]
        rep.note("Instance metadata (DescribeInstances):")
        rep.note(f"  InstanceChargeType : {g(i0, 'InstanceChargeType') or '-'}")
        rep.note(f"  InternetChargeType : {g(i0, 'InternetChargeType') or '-'}")
        rep.note(f"  MaxBandwidthOut    : {g(i0, 'InternetMaxBandwidthOut') or '-'} Mbps")
        rep.note(f"  Status / StoppedMode: {g(i0, 'Status') or '-'} / "
                 f"{g(i0, 'StoppedMode') or '-'}")
        rep.note(f"  InstanceType       : {g(i0, 'InstanceType') or '-'}")
        rep.note(f"  Public IPs         : {', '.join([p for p in public_ips if p]) or '-'}")
        charge = g(i0, "InternetChargeType")
        if charge == "PayByBandwidth":
            rep.findings.append(
                "bandwidth is billed by FIXED BANDWIDTH, not by traffic: no "
                "per-GB traffic bill detail exists for this instance; a "
                "traffic line item cannot be produced (matches the console "
                "'no traffic rows' trap)")
            rep.next_action = ("confirm with the customer which resource "
                               "actually carries the traffic fee (another "
                               "instance / EIP / shared-bandwidth package) "
                               "using the attribution mode")
            return finish(rep, args.json)
        if charge == "PayByTraffic":
            rep.findings.append(
                "bandwidth is billed BY TRAFFIC, outbound direction only - "
                "every GB egress produces a post-paid row")
    else:
        rep.note("[degraded] no instance metadata returned (released "
                 "instance, wrong region, or permission gap): the bill-side "
                 "analysis below still runs")
        rep.degrade()

    start_ms, end_ms = cycle_window_epoch_ms(args.billing_cycle)
    dimensions = json.dumps([{"instanceId": args.instance_id}])
    points = fetch_metric_points(args.metric_namespace, args.metric_name,
                                 dimensions, start_ms, end_ms, args.region,
                                 rep.errors, args.profile)
    hours = 0
    total_bytes = 0.0
    peak_bps = 0.0
    for p in points:
        avg = p.get("Average", p.get("Value", p.get("Maximum")))
        try:
            avg = float(avg)
        except (TypeError, ValueError):
            continue
        peak_bps = max(peak_bps, avg)
        total_bytes += avg / 8.0 * int(METRIC_PERIOD_SECONDS)
        hours += 1
    approx_gb = total_bytes / 1_000_000_000

    rows, used = fetch_rows(args.billing_cycle, None, args.instance_id,
                            rep.errors, args.profile)
    bill_traffic_usage = bill_traffic_pay = 0.0
    if rows:
        tr = [r for r in rows if is_traffic_row(r)]
        bill_traffic_usage = sum(r["usage"] for r in tr)
        bill_traffic_pay = sum(r["payable"] for r in tr)

    rep.note(f"\nCloudMonitor {args.metric_namespace}/{args.metric_name} "
             f"for {args.instance_id} ({args.billing_cycle}):")
    rep.note(f"  datapoints(h) : {hours}")
    rep.note(f"  peak (bit/s)  : {fmt(peak_bps)}")
    rep.note(f"  approx egress : {fmt(approx_gb)} GB (decimal GB, "
             f"sum of hourly averages - approximate by construction)")
    rep.note(f"  bill side ({used or 'query failed'}): usage={fmt(bill_traffic_usage)} "
             f"payable={fmt(bill_traffic_pay)}")
    if hours and bill_traffic_usage and not math.isclose(
            bill_traffic_usage, approx_gb, rel_tol=0.15):
        rep.findings.append(
            f"bill usage ({fmt(bill_traffic_usage)}) differs from monitor "
            f"usage ({fmt(approx_gb)} GB approx, >15%): expected - bill "
            f"detail lags 24h and instance fields 48h, and the monitor sum "
            f"is approximate. Show both numbers; if a gap persists after "
            f"the final bill (3rd 12:00 next month) it goes to backend "
            f"review with the evidence pack")
        rep.data["evidence_pack"] = build_evidence_pack(
            "traffic-check", args.billing_cycle, rep.uid, rows, rep.errors)
    elif hours == 0:
        rep.degrade()
        rep.findings.append(
            "monitor returned no datapoints: verify the namespace/metric "
            f"in the CloudMonitor console (defaults used: "
            f"{args.metric_namespace}/{args.metric_name}) or note that "
            "monitor retention may not cover the whole cycle")
    else:
        rep.findings.append(
            "bill usage and monitor usage agree within 15% for the window")
    rep.suggestions.append(
        "the bill CANNOT say which destinations the traffic went to: "
        "historical traffic attribution is not retained cloud-side for "
        "privacy - offer guest access logs / NIS flow analysis (paid) / "
        "iftop (live) and hand off (references/billing-attribution-bill-check__handoff-map.md)")
    rep.suggestions.append("FAQ traffic-not-traceable states the customer- "
                           "facing wording")
    rep.next_action = ("present the usage x price math from the bill rows "
                       "first; only then discuss reduction options (fixed "
                       "bandwidth / shared traffic plan) as manual console "
                       "actions")
    return finish(rep, args.json)


def mode_deduction_report(rep: Report, args) -> int:
    rows, used = fetch_rows(args.billing_cycle, args.product_code,
                            args.instance_id, rep.errors, args.profile)
    if rows is None:
        rep.status = "FAIL"
        rep.next_action = "resolve the billing query error first, then rerun"
        return finish(rep, args.json)
    undeducted = [r for r in rows
                  if r["payable"] > _EPS and r["pkg"] + r["coupon"] <= _EPS]
    covered = [r for r in rows if r["pkg"] + r["coupon"] > _EPS]
    rep.note(f"Cycle {args.billing_cycle} via {used or 'no API'}: "
             f"{len(undeducted)} row(s) in fee with zero deductions, "
             f"{len(covered)} row(s) partially/fully deducted")
    for r in sorted(undeducted, key=lambda x: -x["payable"])[:20]:
        rep.note(f"  UNDEDUCTED  {r['product']}/{r['item']} region={r['region']} "
                 f"resource={r['resource']} payable={fmt(r['payable'])}")
    for r in sorted(covered, key=lambda x: -(x["pkg"] + x["coupon"]))[:10]:
        rep.note(f"  DEDUCTED    {r['product']}/{r['item']} region={r['region']} "
                 f"resource={r['resource']} pkg={fmt(r['pkg'])} "
                 f"coupon={fmt(r['coupon'])} payable_left={fmt(r['payable'])}")
    rep.note("\nDeduction-failure reason matrix (classify with the row "
             "fields above + the package facts the customer states; this "
             "skill has NO package-inventory API -> DEGRADED confidence):")
    for rule in DEDUCTION_FAILURE_REASONS:
        rep.note(f"  [{rule['id']}] {rule['rule']}")
    rep.findings.append(
        "deduction analysis is triple-based (payable / deducted / paid): it "
        "proves WHERE nothing was deducted, never WHY inside the package - "
        "the WHY matches one of the reasons above or goes to a backend "
        "ticket (e.g. 'properly associated but still not deducted')")
    rep.suggestions.append(
        "console entries: resource packages and coupons are listed under "
        "the billing console (see references/billing-attribution-bill-check__bill-console-paths.md); "
        "purchases/unsubscriptions are manual commercial actions")
    rep.data["undeducted_rows"] = undeducted
    rep.next_action = ("pair this report with the customer-stated package "
                       "facts, quote the matching reason, and state the "
                       "degraded confidence honestly")
    return finish(rep, args.json)


def mode_instance_info(rep: Report, args) -> int:
    ids = [x.strip() for x in (args.instance_ids or "").split(",") if x.strip()]
    if args.instance_id and args.instance_id not in ids:
        ids.insert(0, args.instance_id)
    for x in ids:
        if not _ID_RE.match(x):
            rep.status = "FAIL"
            rep.next_action = f"invalid instance id form: {x!r}"
            return finish(rep, args.json)
    rep.auto_filled.append(
        f"region defaulted to {DEFAULT_REGION}" if args.region_defaulted
        else f"region {args.region}")
    instances = fetch_instances(args.region, ids, rep.errors, args.profile)
    if not instances:
        scope = ("requested ids: " + ", ".join(ids)) if ids else "no id filter"
        rep.note(f"DescribeInstances in {args.region}: no instance matched "
                 f"({scope})")
        rep.degrade()
        rep.findings.append("empty result: instance may live in another "
                            "region (rerun per region from the bill rows), "
                            "or was released (metadata disappears while the "
                            "final bill rows remain)")
        rep.next_action = ("rerun --instance-info with each region seen in "
                           "the bill rows (the InstanceID region column "
                           "lists them)")
        return finish(rep, args.json)
    rep.note(f"DescribeInstances ({args.region}): {len(instances)} instance(s)")
    for i0 in instances:
        rep.note(f"  {g(i0, 'InstanceId')} charge={g(i0, 'InstanceChargeType')} "
                 f"internet={g(i0, 'InternetChargeType')} "
                 f"bwOut={g(i0, 'InternetMaxBandwidthOut')} "
                 f"status={g(i0, 'Status')} stoppedMode={g(i0, 'StoppedMode')} "
                 f"spec={g(i0, 'InstanceType')} "
                 f"ips={','.join(public_ips_of(i0)) or '-'}")
    rep.findings.append(
        "Subscription + PayByTraffic => post-paid traffic rows are expected "
        "on a monthly instance; PayAsYouGo + Stopped => spec fee depends on "
        "stop mode (savings stop suspends spec/fixed-bandwidth/image only, "
        "disks/snapshots/EIP keep billing)")
    rep.next_action = ("combine with the attribution rows of the same "
                       "InstanceID to answer 'why still charged'")
    return finish(rep, args.json)


def mode_faq(rep: Report, args) -> int:
    if args.list_topics or not args.topic:
        rep.note("Embedded FAQ topics (ticket-derived, this skill's scope):")
        for key in sorted(FAQ_TOPICS):
            rep.note(f"  {key}: {FAQ_TOPICS[key]['question']}")
        rep.findings.append(f"{len(FAQ_TOPICS)} topics available")
        rep.next_action = "run --topic <key> for the full answer"
        return finish(rep, args.json)
    topic = FAQ_TOPICS.get(args.topic)
    if topic is None:
        rep.status = "FAIL"
        rep.next_action = f"unknown topic {args.topic!r}; run --list-topics"
        return finish(rep, args.json)
    subject_re = FAQ_TOPIC_SUBJECT_RE.get(args.topic)
    asked_question = os.environ.get("ECS_CUSTOMER_QUESTION", "")
    if subject_re and asked_question.strip() and not re.search(
            subject_re, asked_question):
        rep.note("Q: %s\n\nA: not this run's subject - the question does not ask "
                 "about it, so the bill attribution answer carries the reply."
                 % topic["question"])
        rep.findings.append("FAQ topic %s is not the asked subject" % args.topic)
        rep.next_action = "answer the subject the question actually asks about"
        return finish(rep, args.json)
    rep.note(f"Q: {topic['question']}\n\nA: {topic['answer']}")
    entry = FAQ_CONSOLE_ENTRY.get(args.topic, FAQ_CONSOLE_DEFAULT)
    rep.note("Have the customer open " + entry + " and paste the rows back; "
             "the rule above explains the item, the rows prove the amount.")
    rep.findings.append(f"answered from embedded knowledge: {args.topic}")
    rep.next_action = ("ground any account-specific part in a bill query "
                       "mode before answering")
    return finish(rep, args.json)


def mode_explain_timing(rep: Report, args) -> int:
    rep.note("Authoritative timing & caliber statements for this skill:")
    for t in TIMING_CALIBER:
        rep.note(f"  - {t}")
    rep.note("\nStop-billing guidance (manual only; risk notes attached):")
    for s in STOP_BILLING_GUIDE:
        rep.note(f"  [{s['item']}] {s['action']}  RISK: {s['risk']}")
    rep.note("\nHandoff rules (out-of-scope symptoms):")
    for h in HANDOFF_RULES:
        rep.note(f"  {h['symptom']}  ->  {h['target']}")
    rep.findings.append("relay these verbatim; they resolve most 'bill "
                        "looks wrong' disputes")
    rep.next_action = "combine with concrete amounts from attribution mode"
    return finish(rep, args.json)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def resolve_cycle(args, rep: Report) -> None:
    """C3: charge-date -> cycle mapping + defaulting, all declared."""
    if args.billing_cycle:
        return
    if args.charge_date:
        args.billing_cycle = map_charge_date_to_cycle(args.charge_date)
        args.cycle_source = "derived from charge date " + args.charge_date
        rep.auto_filled.append(
            f"billing cycle auto-set to {args.billing_cycle}: a balance "
            f"deduction on {args.charge_date[:10]} settles the "
            f"{args.billing_cycle} post-paid bill (monthly settlement "
            f"occurs at the start of the following month)")
        return
    today = dt.datetime.now(dt.timezone.utc)
    args.billing_cycle = previous_cycle(f"{today.year}-{today.month:02d}")
    args.cycle_source = "defaulted to the most recently completed cycle"
    rep.auto_filled.append(
        f"billing cycle auto-defaulted to {args.billing_cycle} (the most "
        f"recent completed cycle); current month data is provisional")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="query_ecs_bill.py",
        description="Read-only ECS cost attribution and bill reconciliation "
                    "via whitelisted BSS/CMS/ECS metadata reads.",
    )
    m = p.add_mutually_exclusive_group()
    m.add_argument("--overview", action="store_true",
                   help="per-product spend of one cycle")
    m.add_argument("--monthly-total", action="store_true",
                   help="cycle total rows (QueryBill)")
    m.add_argument("--settlement", action="store_true",
                   help="settlement-bill amounts (QuerySettleBill)")
    m.add_argument("--reconcile", action="store_true",
                   help="cross-check overview vs bill vs settlement")
    m.add_argument("--daily", action="store_true",
                   help="per-day series of a cycle")
    m.add_argument("--traffic-check", action="store_true",
                   help="bandwidth billing mode + monitor vs bill usage")
    m.add_argument("--deduction-report", action="store_true",
                   help="in-fee rows with zero deductions + reason matrix")
    m.add_argument("--instance-info", action="store_true",
                   help="instance charge/stop/bandwidth metadata")
    m.add_argument("--list-topics", action="store_true",
                   help="list embedded FAQ topics (no cloud call)")
    m.add_argument("--topic", help="print one embedded FAQ topic")
    m.add_argument("--explain-timing", action="store_true",
                   help="print timing/caliber statements (no cloud call)")

    p.add_argument("--billing-cycle", help="YYYY-MM; default: previous cycle")
    p.add_argument("--charge-date", help="YYYY-MM-DD of a balance deduction; "
                                         "maps it to the previous cycle")
    p.add_argument("--months", type=int, default=1,
                   help="analyze N consecutive cycles ending at --billing-cycle "
                        "(1-12, month-over-month)")
    p.add_argument("--days", type=int, default=7,
                   help="per-day walk-back for --daily (1-%d)" % MAX_DAILY_DAYS)
    p.add_argument("--product-code", help="filter bill rows by BSS product "
                                          "code (e.g. ecs, snapshot)")
    p.add_argument("--instance-id", help="instance / resource id (i-..., "
                                         "d-..., snap-...)")
    p.add_argument("--instance-ids", help="comma-separated ids for "
                                          "--instance-info")
    p.add_argument("--region", default=DEFAULT_REGION,
                   help="region for ecs/cms reads (default %(default)s)")
    p.add_argument("--metric-namespace", default=DEFAULT_METRIC_NAMESPACE,
                   help="CloudMonitor namespace for --traffic-check")
    p.add_argument("--metric-name", default=DEFAULT_TRAFFIC_METRIC,
                   help="CloudMonitor metric for --traffic-check")
    p.add_argument("--profile", default=None,
                   help="aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine JSON output")
    return p


def validate(args, rep: Report) -> bool:
    if args.months < 1 or args.months > 12:
        rep.status = "FAIL"
        rep.next_action = "--months must be within 1..12"
        return False
    if args.days < 1 or args.days > MAX_DAILY_DAYS:
        rep.status = "FAIL"
        rep.next_action = f"--days must be within 1..{MAX_DAILY_DAYS}"
        return False
    if args.billing_cycle and not valid_cycle(args.billing_cycle):
        rep.status = "FAIL"
        rep.next_action = ("--billing-cycle must look like 2026-08 "
                           "(YYYY-MM); relay this format rule to the "
                           "customer, do not guess")
        return False
    if args.charge_date and not _DATE_RE.match(args.charge_date):
        rep.status = "FAIL"
        rep.next_action = "--charge-date must look like 2026-08-01"
        return False
    if args.instance_id and not _ID_RE.match(args.instance_id):
        rep.status = "FAIL"
        rep.next_action = "--instance-id has an invalid character form"
        return False
    return True


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.cycle_source = "user-provided"
    args.region_defaulted = args.region == DEFAULT_REGION

    mode = "attribution"
    for name in ("overview", "monthly_total", "settlement", "reconcile",
                 "daily", "traffic_check", "deduction_report", "instance_info",
                 "list_topics", "topic", "explain_timing"):
        if getattr(args, name):
            mode = name
            break
    rep = Report(mode)

    if mode in ("faq", "explain_timing", "list_topics", "topic"):
        rep = Report("faq" if mode in ("faq", "list_topics") else mode)

    if not validate(args, rep):
        sys.exit(finish(rep, args.json))

    needs_cycle = mode not in ("instance_info", "list_topics", "topic",
                               "explain_timing", "faq")
    if needs_cycle:
        resolve_cycle(args, rep)

    reads_cloud = needs_cycle or mode == "instance_info"
    if reads_cloud:
        _cli.check_cli_available()
        uid = _cli.resolve_account_id(profile=args.profile)
        rep.uid = uid
        if not uid:
            rep.degrade()
            rep.errors.append(
                "sts GetCallerIdentity failed: the default credential chain "
                "is unusable; run `aliyun sts get-caller-identity` (never pass AK/SK "
                "explicitly) and rerun")
            if mode == "instance_info":
                sys.exit(finish(rep, args.json))

    dispatch = {
        "attribution": mode_attribution,
        "overview": mode_overview,
        "monthly_total": mode_monthly_total,
        "settlement": mode_settlement,
        "reconcile": mode_reconcile,
        "daily": mode_daily,
        "traffic_check": mode_traffic_check,
        "deduction_report": mode_deduction_report,
        "instance_info": mode_instance_info,
        "list_topics": mode_faq,
        "topic": mode_faq,
        "faq": mode_faq,
        "explain_timing": mode_explain_timing,
    }
    fn = dispatch[mode]
    sys.exit(fn(rep, args))


# ---------------------------------------------------------------------------
# Inline boundary self-checks for the pure helpers (normal / boundary /
# invalid inputs). They run at import time only for these offline functions.
# ---------------------------------------------------------------------------

assert previous_cycle("2026-01") == "2025-12"
assert previous_cycle("2026-08") == "2026-07"
assert walk_cycles("2026-08", 3) == ["2026-06", "2026-07", "2026-08"]
assert days_in_cycle("2026-02") == 28
assert days_in_cycle("2024-02") == 29
assert days_in_cycle("2026-12") == 31
assert last_days_of_cycle("2026-08", 3) == ["2026-08-29", "2026-08-30", "2026-08-31"]
assert last_days_of_cycle("2026-02", 99) == last_days_of_cycle("2026-02", 28)
assert map_charge_date_to_cycle("2026-08-01") == "2026-07"
assert valid_cycle("2026-08") and not valid_cycle("2026-13")
assert not valid_cycle("2026/08")
_num_probe = num({"a": "1,234.50"}, "a")
assert abs(_num_probe - 1234.5) < 1e-9
assert num({"a": ""}, "a") == 0.0
assert num({}, "missing") == 0.0
assert recompute_check({"usage": 1722, "price": 0.8, "gross": 1377.64,
                        "item": "", "item_code": ""}) == "ok"
assert recompute_check({"usage": 100, "price": 0.8, "gross": 30,
                        "item": "", "item_code": ""}) == "mismatch"
assert recompute_check({"usage": 0, "price": 0.8, "gross": 30,
                        "item": "", "item_code": ""}) == "skip"
_match_probe = {"item": "NetworkOut", "item_code": ""}
assert is_traffic_row(_match_probe)
assert not is_traffic_row({"item": "SystemDisk", "item_code": ""})
# Real CLI shape: IpAddress is a list of plain strings (was AttributeError).
assert public_ips_of({"PublicIpAddress": {"IpAddress": ["47.1.2.3"]}}) == ["47.1.2.3"]
assert public_ips_of({"PublicIpAddress": {"IpAddress": ["47.1.2.3", "47.1.2.4"]}}) == \
    ["47.1.2.3", "47.1.2.4"]
# SDK/nested-dict and flattened scalar shapes stay supported.
assert public_ips_of({"PublicIpAddress": {"IpAddress": [{"IpAddress": "47.1.2.3"}]}}) == \
    ["47.1.2.3"]
assert public_ips_of({"PublicIpAddress": {"IpAddress": "47.1.2.3"}}) == ["47.1.2.3"]
assert public_ips_of({"PublicIpAddress": "47.1.2.3"}) == ["47.1.2.3"]
assert public_ips_of({"PublicIpAddress": {}}) == []
assert public_ips_of({}) == []

if __name__ == "__main__":
    main()
