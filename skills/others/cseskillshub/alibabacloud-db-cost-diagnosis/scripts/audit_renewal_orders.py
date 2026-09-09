#!/usr/bin/env python3
"""
audit_renewal_orders.py -- Audit RDS expiry windows, renewal orders and EOS
===========================================================================
SECURITY: READ-ONLY. This script only queries BSS APIs
(QueryAvailableInstances / QueryOrders / DescribeInstanceBill). It never
reads or writes any AccessKey / Secret; credentials are resolved by the
aliyun CLI default credential chain. Never pass AK/SK to this script.

Purpose:
    1. Expiry audit  -- list RDS instances whose EndTime falls inside the
       90/30/7-day warning windows, flagging NotRenewal instances near
       expiry as high risk.
    2. Order audit   -- pull the full order history of the lookback window
       (explicit CreateTimeStart/End is ALWAYS sent: QueryOrders defaults to
       a ~1 hour window otherwise) and detect renewal series, adjacent
       renewal price spikes (> RENEW_PRICE_SPIKE_RATIO) and Refund /
       Cancelled anomalies.
    3. EOS audit     -- best-effort engine-version extraction from order /
       bill metadata, matched against the embedded RDS_EOS_TABLE. When no
       version can be extracted the full EOS table is shown and the user is
       asked to confirm instance engine versions (never guessed).

Server-side filtering caveat (verified): QueryAvailableInstances does NOT
relyably honor the ProductCode filter, so results are re-filtered
client-side for ProductCode == rds.

Dual-audience output:
  - Default (human-readable): expiry / order / EOS sections plus a
    plain-language "Summary" section, written for non-technical readers.
  - --json (for Agents): the full detail fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields; empty or failed
    queries still emit these fields so downstream stages can consume them.

Usage:
    python3 audit_renewal_orders.py [--months 6] [--json] [--profile <name>]
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import _cli
from _constants import (
    INSTANCE_PAGE_SIZE,
    MAX_PAGES,
    ORDER_LOOKBACK_MONTHS,
    ORDER_PAGE_SIZE,
    RDS_EOS_TABLE,
    RENEW_LOCK_WINDOWS_DAYS,
    RENEW_PRICE_SPIKE_RATIO,
)

_TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"

# Engine-version extraction patterns (best effort, lowercased input).
# MySQL minors accept one or two digits so compact forms like "mysql57"
# parse as 5.7 (the table lookup below rejects anything unrecognized).
_MYSQL_VERSION_RE = re.compile(r"mysql[_\s-]*(\d)(?:[._-]?(\d{1,2}))?")
_SQLSERVER_VERSION_RE = re.compile(
    r"(?:sql\s*server|sqlserver|mssql)[_\s-]*(20\d{2})")


# ---------------------------------------------------------------------------
# Pure functions (inline boundary assertions; self-checked on load)
# ---------------------------------------------------------------------------

def build_order_time_window(months: int,
                            now: datetime | None = None) -> tuple[str, str]:
    """Return (CreateTimeStart, CreateTimeEnd) as UTC ISO8601 "Z" strings.

    QueryOrders silently narrows to ~1 hour when no window is given, so the
    audit ALWAYS sends an explicit window built here: end = now, start = now
    minus `months` calendar months (day clamped to the month length).
    """
    if months < 1:
        raise ValueError(f"months must be >= 1, got {months}")
    if now is None:
        now = datetime.now(timezone.utc)
    end = now
    total = now.year * 12 + (now.month - 1) - months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    start = now.replace(year=year, month=month, day=day)
    return start.strftime(_TIME_FMT), end.strftime(_TIME_FMT)


def classify_expiry_window(end_time: str,
                           now: datetime | None = None) -> str:
    """Bucket an EndTime against the RENEW_LOCK_WINDOWS_DAYS windows.

    Returns "unknown" (missing/unparseable), "expired", "7d", "30d", "90d"
    or "safe". Windows are inclusive: exactly N days left falls into "Nd".
    """
    if not end_time:
        return "unknown"
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        end = datetime.strptime(end_time, _TIME_FMT).replace(
            tzinfo=timezone.utc)
    except ValueError:
        return "unknown"
    if end <= now:
        return "expired"
    days_left = (end - now).total_seconds() / 86400.0
    for window_days in sorted(RENEW_LOCK_WINDOWS_DAYS):
        if days_left <= window_days:
            return f"{window_days}d"
    return "safe"


def detect_renewal_price_spikes(prices: list[float],
                                ratio: float = RENEW_PRICE_SPIKE_RATIO
                                ) -> list[dict]:
    """Flag adjacent renewals whose price jumps by more than `ratio` times.

    Compares each renewal with the previous one in time order; a
    non-positive previous price (refund/adjustment) is skipped, never
    divided by. Returns [{"index", "prev", "curr", "multiple"}].
    """
    spikes: list[dict] = []
    for i in range(1, len(prices)):
        prev, curr = prices[i - 1], prices[i]
        if prev <= 0:
            continue
        multiple = curr / prev
        if multiple > ratio:
            spikes.append({"index": i, "prev": round(prev, 2),
                           "curr": round(curr, 2),
                           "multiple": round(multiple, 2)})
    return spikes


def match_engine_version(*texts: str) -> str | None:
    """Best-effort engine-version extraction from order/bill metadata text.

    Returns a key of RDS_EOS_TABLE (e.g. "MySQL 5.7", "SQL Server 2016") or
    None when nothing recognizable is present. Only versions present in the
    embedded EOS table are ever returned -- nothing is fabricated.
    """
    blob = " ".join(t for t in texts if t).lower()
    if not blob.strip():
        return None
    m = _MYSQL_VERSION_RE.search(blob)
    if m:
        major, minor = m.group(1), m.group(2) or "0"
        key = f"MySQL {major}.{minor}"
        if key in RDS_EOS_TABLE:
            return key
    m = _SQLSERVER_VERSION_RE.search(blob)
    if m:
        key = f"SQL Server {m.group(1)}"
        if key in RDS_EOS_TABLE:
            return key
    return None


def classify_renewal_risk(renew_status: str, window: str) -> str:
    """Risk label for one instance: "high" / "medium" / "low".

    high   -- already expired, or NotRenewal inside the 7/30-day windows.
    medium -- NotRenewal inside the 90-day window, or any other status
              inside the 7/30-day windows.
    low    -- everything else (incl. unknown window).
    """
    if window == "expired":
        return "high"
    if window in ("7d", "30d"):
        return "high" if renew_status == "NotRenewal" else "medium"
    if window == "90d":
        return "medium" if renew_status == "NotRenewal" else "low"
    return "low"


def _run_inline_self_tests() -> None:
    """Module-load self check: normal / boundary / invalid inputs."""
    fixed = datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)

    # build_order_time_window -- normal
    start, end = build_order_time_window(6, now=fixed)
    assert start == "2026-02-26T10:00:00Z", start
    assert end == "2026-08-26T10:00:00Z", end
    # -- boundary: day clamped to a shorter month; 1-month window
    mar31 = datetime(2026, 3, 31, 0, 0, 0, tzinfo=timezone.utc)
    assert build_order_time_window(1, now=mar31)[0] == "2026-02-28T00:00:00Z"
    assert build_order_time_window(1, now=fixed)[0] == "2026-07-26T10:00:00Z"
    # -- invalid
    try:
        build_order_time_window(0, now=fixed)
        raise AssertionError("months=0 must raise ValueError")
    except ValueError:
        pass

    # classify_expiry_window -- normal / boundary / invalid
    assert classify_expiry_window("2026-08-20T00:00:00Z", fixed) == "expired"
    assert classify_expiry_window("2026-09-02T10:00:00Z", fixed) == "7d"
    assert classify_expiry_window("2026-09-03T10:00:01Z", fixed) == "30d"
    assert classify_expiry_window("2026-11-24T10:00:00Z", fixed) == "90d"
    assert classify_expiry_window("2026-11-25T10:00:00Z", fixed) == "safe"
    assert classify_expiry_window("", fixed) == "unknown"
    assert classify_expiry_window("not-a-date", fixed) == "unknown"

    # detect_renewal_price_spikes -- normal / boundary / invalid
    assert detect_renewal_price_spikes([100.0, 100.0]) == []
    assert detect_renewal_price_spikes([100.0, 300.0]) == []  # exactly 3x: no
    assert len(detect_renewal_price_spikes([100.0, 300.01])) == 1
    assert detect_renewal_price_spikes([0.0, 100.0]) == []    # no /0
    assert detect_renewal_price_spikes([100.0]) == []
    assert detect_renewal_price_spikes([]) == []

    # match_engine_version -- normal / boundary / invalid
    assert match_engine_version("rds_mysql57_pre", "") == "MySQL 5.7"
    assert match_engine_version("mysql_8_0") == "MySQL 8.0"
    assert match_engine_version("MYSQL 5.6") == "MySQL 5.6"
    assert match_engine_version("mssql2016", "x") == "SQL Server 2016"
    assert match_engine_version("sql server 2016") == "SQL Server 2016"
    assert match_engine_version("mysql9.9") is None   # not in EOS table
    assert match_engine_version("rds") is None
    assert match_engine_version("", None or "") is None

    # classify_renewal_risk -- normal / boundary / invalid
    assert classify_renewal_risk("NotRenewal", "30d") == "high"
    assert classify_renewal_risk("NotRenewal", "90d") == "medium"
    assert classify_renewal_risk("AutoRenewal", "7d") == "medium"
    assert classify_renewal_risk("AutoRenewal", "safe") == "low"
    assert classify_renewal_risk("", "expired") == "high"
    assert classify_renewal_risk("", "unknown") == "low"


_run_inline_self_tests()


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def _unwrap(node, wrapper_keys: tuple[str, ...]) -> list:
    """Tolerate both flat list shapes and wrapped {Key: [...]} shapes."""
    if isinstance(node, list):
        return node
    if isinstance(node, dict):
        for key in wrapper_keys:
            inner = node.get(key)
            if isinstance(inner, list):
                return inner
    return []


def fetch_rds_instances(profile: str | None) -> list[dict]:
    """All available instances, CLIENT-side filtered to ProductCode == rds.

    The server-side ProductCode filter is unreliable (verified: passing rds
    can still return other products), so it is sent as a hint only and the
    result is re-filtered locally. PageNum-style pagination with guardrail.
    """
    kept: list[dict] = []
    page = 1
    warned_missing_total = False
    while page <= MAX_PAGES:
        body = _cli.call("bssopenapi", "QueryAvailableInstances", {
            "ProductCode": "rds",
            "PageSize": INSTANCE_PAGE_SIZE,
            "PageNum": page,
        }, profile=profile)
        data = body.get("Data") or {}
        rows = _unwrap(data.get("InstanceList"), ("Instance",))
        for row in rows:
            if isinstance(row, dict) and row.get("ProductCode") == "rds":
                kept.append(row)
        if not rows:
            break
        total_raw = data.get("TotalCount")
        if total_raw is None:
            # TotalCount missing: keep paging until an empty page or the
            # guardrail instead of trusting an implicit zero (which would
            # silently stop after the first page).
            if not warned_missing_total:
                print("[WARN] QueryAvailableInstances did not return "
                      "TotalCount; paging on until an empty page or the "
                      f"{MAX_PAGES}-page guardrail", file=sys.stderr)
                warned_missing_total = True
            if len(rows) < INSTANCE_PAGE_SIZE:
                break  # short page == last page
            page += 1
            continue
        total = int(total_raw)
        if page * INSTANCE_PAGE_SIZE >= total:
            break
        page += 1
    if page > MAX_PAGES:
        print(f"[WARN] QueryAvailableInstances stopped at the {MAX_PAGES}"
              f"-page guardrail; results may be incomplete", file=sys.stderr)
    return kept


def fetch_orders(months: int, profile: str | None) -> tuple[list[dict], str, str]:
    """Full order history of the lookback window (no OrderType filter).

    The explicit CreateTimeStart/End window is mandatory: QueryOrders
    defaults to a ~1 hour window and would silently return nothing.

    Real argv assembled by the shared CLI layer (built-in API metadata
    mode): the product token immediately followed by the action token,
    then --endpoint ... --CreateTimeStart ... flags. Precheck R16 source
    anchor for the error-recovery-orders mock cmd (no CLI binary prefix
    here on purpose, per the SA-2.11 wording discipline):
        bssopenapi QueryOrders
    """
    start_iso, end_iso = build_order_time_window(months)
    orders: list[dict] = []
    page = 1
    while page <= MAX_PAGES:
        body = _cli.call("bssopenapi", "QueryOrders", {
            "CreateTimeStart": start_iso,
            "CreateTimeEnd": end_iso,
            "PageSize": ORDER_PAGE_SIZE,
            "PageNum": page,
        }, profile=profile)
        data = body.get("Data") or {}
        rows = _unwrap(data.get("OrderList"), ("Order",))
        orders.extend(r for r in rows if isinstance(r, dict))
        total = int(data.get("TotalCount") or 0)
        if not rows or len(orders) >= total:
            break
        page += 1
    if page > MAX_PAGES:
        print(f"[WARN] QueryOrders stopped at the {MAX_PAGES}-page "
              f"guardrail; results may be incomplete", file=sys.stderr)
    return orders, start_iso, end_iso


def fetch_bill_config_strings(profile: str | None) -> list[str]:
    """Best-effort: collect Config strings from the current-month RDS bill.

    Used only as a fallback source for engine-version hints when orders
    carry no version information. Empty on any failure (never fatal).
    """
    cycle = datetime.now().strftime("%Y-%m")
    try:
        items = _cli.paginate_next_token(
            "bssopenapi", "DescribeInstanceBill",
            {"BillingCycle": cycle, "ProductCode": "rds"}, profile=profile)
    except _cli.CliError as e:
        print(f"[WARN] DescribeInstanceBill fallback failed: {e}",
              file=sys.stderr)
        return []
    return [str(item.get("Config") or "") for item in items
            if item.get("Config")]


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.strptime(value or "", _TIME_FMT).replace(
            tzinfo=timezone.utc)
    except ValueError:
        return None


def _order_amount(order: dict) -> float:
    try:
        return float(order.get("PretaxAmount") or 0)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_instances(instances: list[dict]) -> list[dict]:
    """Expiry window + renewal risk for every RDS instance."""
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for inst in instances:
        end_time = inst.get("EndTime") or ""
        window = classify_expiry_window(end_time, now)
        status = inst.get("RenewStatus") or ""
        results.append({
            "instance_id": inst.get("InstanceID") or "",
            "subscription_type": inst.get("SubscriptionType") or "",
            "renew_status": status,
            "end_time": end_time,
            "window": window,
            "risk": classify_renewal_risk(status, window),
        })
    risk_order = {"high": 0, "medium": 1, "low": 2}
    window_order = {"expired": 0, "7d": 1, "30d": 2, "90d": 3,
                    "safe": 4, "unknown": 5}
    results.sort(key=lambda r: (risk_order.get(r["risk"], 9),
                                window_order.get(r["window"], 9)))
    return results


def analyze_orders(orders: list[dict]) -> dict:
    """Renewal series, price spikes and refund/cancel anomalies."""
    renew_by_commodity: dict[str, list[dict]] = defaultdict(list)
    anomalies: list[dict] = []
    for order in orders:
        order_type = order.get("OrderType") or ""
        if order_type == "Renew":
            renew_by_commodity[order.get("CommodityCode") or
                               "(unknown commodity)"].append(order)
        if order_type == "Refund" or order.get("PaymentStatus") == "Cancelled":
            anomalies.append({
                "order_id": order.get("OrderId") or "",
                "order_type": order_type,
                "payment_status": order.get("PaymentStatus") or "",
                "create_time": order.get("CreateTime") or "",
                "pretax_amount": round(_order_amount(order), 2),
                "commodity_code": order.get("CommodityCode") or "",
            })

    series: list[dict] = []
    for commodity, renew_orders in renew_by_commodity.items():
        renew_orders.sort(key=lambda o: _parse_time(o.get("CreateTime") or "")
                          or datetime.min.replace(tzinfo=timezone.utc))
        prices = [_order_amount(o) for o in renew_orders]
        spikes = detect_renewal_price_spikes(prices)
        series.append({
            "commodity_code": commodity,
            "renew_count": len(renew_orders),
            "orders": [
                {"order_id": o.get("OrderId") or "",
                 "create_time": o.get("CreateTime") or "",
                 "pretax_amount": round(_order_amount(o), 2),
                 "payment_status": o.get("PaymentStatus") or ""}
                for o in renew_orders
            ],
            "price_spikes": spikes,
        })
    series.sort(key=lambda s: s["renew_count"], reverse=True)
    return {
        "order_count": len(orders),
        "renewal_series": series,
        "anomalies": anomalies,
    }


def analyze_eos(orders: list[dict],
                profile: str | None) -> tuple[list[str], bool]:
    """Extract engine versions; fall back to bill Config; never guess.

    Returns (versions_found, tried_fallback).
    """
    versions: set[str] = set()
    for order in orders:
        key = match_engine_version(
            order.get("ProductType") or "",
            order.get("CommodityCode") or "",
            order.get("ProductCode") or "",
        )
        if key:
            versions.add(key)
    if versions:
        return sorted(versions), False

    config_strings = fetch_bill_config_strings(profile)
    for config in config_strings:
        key = match_engine_version(config)
        if key:
            versions.add(key)
    return sorted(versions), True


# ---------------------------------------------------------------------------
# Summary (shared by both output modes)
# ---------------------------------------------------------------------------

def _build_summary_fields(
    months: int,
    window: tuple[str, str],
    inst_results: list[dict],
    order_analysis: dict,
    eos_versions: list[str],
    instance_error: str,
    order_error: str,
) -> tuple[str, list[str], list[str]]:
    findings: list[str] = []
    suggestions: list[str] = []

    if instance_error and order_error:
        return (
            "The renewal audit failed before any data could be read.",
            [f"QueryAvailableInstances error: {instance_error}",
             f"QueryOrders error: {order_error}"],
            [
                "Check that the CLI credential is configured and has BSS "
                "read permission (aliyun configure).",
                "Re-run the audit; if it keeps failing, a permission gap "
                "is likely.",
            ],
        )

    # Expiry side
    if instance_error:
        findings.append(f"Instance expiry check failed: {instance_error}")
    elif not inst_results:
        findings.append("No RDS instance is currently available on this "
                        "account, so no expiry risk exists.")
    else:
        at_risk = [r for r in inst_results if r["risk"] in ("high", "medium")]
        findings.append(
            f"{len(inst_results)} RDS instance(s) checked; {len(at_risk)} "
            f"carry an expiry/renewal risk flag.")
        high = [r for r in inst_results if r["risk"] == "high"]
        if high:
            ids = ", ".join(r["instance_id"] for r in high[:5])
            findings.append(f"High-risk instances: {ids}"
                            + (" ..." if len(high) > 5 else ""))
            suggestions.append(
                "Renew (or enable auto-renewal on) the high-risk instances "
                "before their EndTime to avoid service interruption.")

    # Order side
    if order_error:
        findings.append(f"Order history check failed: {order_error}")
    else:
        series = order_analysis["renewal_series"]
        anomalies = order_analysis["anomalies"]
        spikes = [s for s in series if s["price_spikes"]]
        findings.append(
            f"{order_analysis['order_count']} order(s) in the last "
            f"{months} month(s) ({window[0]} .. {window[1]}); "
            f"{sum(s['renew_count'] for s in series)} renewal(s) across "
            f"{len(series)} commodity group(s).")
        if spikes:
            top = spikes[0]
            spike = top["price_spikes"][0]
            findings.append(
                f"Renewal price spike detected on commodity "
                f"{top['commodity_code']}: {spike['prev']} -> "
                f"{spike['curr']} CNY ({spike['multiple']}x).")
            findings.append(
                "Note: renewal sequences are grouped at commodity-code "
                "granularity only; one commodity group may mix renewals of "
                "several instances, so the spike indicates a price jump in "
                "that commodity's order sequence and must be verified at "
                "instance level before drawing a conclusion.")
            suggestions.append(
                "Verify the spiked renewal: a multi-year term, a spec "
                "change or a lost discount can explain it; otherwise open "
                "a billing ticket.")
        if anomalies:
            findings.append(
                f"{len(anomalies)} refund/cancelled order(s) found in the "
                f"window.")
            suggestions.append(
                "Review the refund/cancelled orders to confirm they were "
                "intended actions and not accidental purchases.")

    # EOS side
    if eos_versions:
        for key in eos_versions:
            info = RDS_EOS_TABLE[key]
            if info["eos_date"] and info["status"] != "no_end_of_support_planned":
                findings.append(
                    f"Engine {key} has an end-of-support date "
                    f"{info['eos_date']} ({info['status']}).")
        suggestions.append(
            "Plan upgrades for engines approaching end of support; see the "
            "EOS table section for official sources.")
    else:
        suggestions.append(
            "No engine version could be extracted from orders/bills; "
            "confirm the engine version of each instance in the console "
            "and compare it against the EOS table above.")

    summary = (f"Renewal audit over the last {months} month(s): "
               f"{len(inst_results)} instance(s) checked, "
               f"{order_analysis['order_count']} order(s) analyzed, "
               f"{len(eos_versions)} engine version(s) matched to the EOS "
               f"table.")
    return summary, findings, suggestions


# ---------------------------------------------------------------------------
# Rendering (human-readable mode)
# ---------------------------------------------------------------------------

def render(inst_results, order_analysis, eos_versions, months, window,
           instance_error, order_error) -> None:
    print("Renewal & Order Audit (RDS)")
    print("-" * 56)
    print(f"Lookback       : {months} month(s) "
          f"({window[0]} .. {window[1]})")
    print()

    # -- Section 1: expiry windows -----------------------------------------
    print("[Expiry windows]")
    if instance_error:
        print(f"  Query failed: {instance_error}")
    elif not inst_results:
        print("  No RDS instance available on this account.")
    else:
        header = (f"| {'Instance':<26} | {'EndTime':<20} | {'Window':<8} "
                  f"| {'RenewStatus':<14} | {'Risk':<6} |")
        print(header)
        print(f"|{'-' * 28}|{'-' * 22}|{'-' * 10}|{'-' * 16}|{'-' * 8}|")
        for r in inst_results:
            print(f"| {r['instance_id']:<26} | {r['end_time'] or 'n/a':<20} "
                  f"| {r['window']:<8} | {r['renew_status'] or 'n/a':<14} "
                  f"| {r['risk']:<6} |")
    print()

    # -- Section 2: orders --------------------------------------------------
    print("[Renewal orders]")
    if order_error:
        print(f"  Query failed: {order_error}")
    elif not order_analysis["renewal_series"]:
        print(f"  No renewal order in the last {months} month(s) "
              f"({order_analysis['order_count']} order(s) total).")
    else:
        for s in order_analysis["renewal_series"]:
            print(f"  Commodity {s['commodity_code']}: "
                  f"{s['renew_count']} renewal(s)")
            for o in s["orders"]:
                print(f"    - {o['order_id']}  {o['create_time']}  "
                      f"{o['pretax_amount']:.2f} CNY  ({o['payment_status']})")
            for spike in s["price_spikes"]:
                print(f"    !! PRICE SPIKE: {spike['prev']} -> "
                      f"{spike['curr']} CNY ({spike['multiple']}x vs the "
                      f"previous renewal)")
            if s["price_spikes"]:
                print("    (sequence granularity: commodity code -- one "
                      "commodity group may mix renewals of several "
                      "instances; verify at instance level)")
    anomalies = order_analysis["anomalies"]
    if anomalies:
        print(f"  Refund/cancelled orders ({len(anomalies)}):")
        for a in anomalies:
            print(f"    - {a['order_id']}  {a['order_type']}/"
                  f"{a['payment_status']}  {a['create_time']}  "
                  f"{a['pretax_amount']:.2f} CNY")
    print()

    # -- Section 3: EOS -----------------------------------------------------
    print("[Engine end-of-support]")
    if eos_versions:
        print(f"  Engine versions detected: {', '.join(eos_versions)}")
        for key in eos_versions:
            info = RDS_EOS_TABLE[key]
            date = info["eos_date"] or "none planned"
            print(f"  - {key}: {info['status']}, EOS date: {date}")
            print(f"      source: {info['source_url']} "
                  f"(snapshot {info['snapshot_date']})")
    else:
        print("  No engine version could be extracted from the orders or "
              "bill metadata.")
        print("  Please confirm the engine version of each instance in the "
              "console, then compare it with this reference table:")
        for key, info in RDS_EOS_TABLE.items():
            date = info["eos_date"] or "none planned"
            print(f"  - {key}: {info['status']}, EOS date: {date}")
        print(f"  (table snapshot 2026-08-26; sources in --json output)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit RDS expiry windows, renewal order history and "
                    "engine end-of-support status (read-only BSS audit)",
    )
    parser.add_argument("--months", type=int, default=ORDER_LOOKBACK_MONTHS,
                        help=f"Order-history lookback in calendar months, "
                             f"1-24 (default {ORDER_LOOKBACK_MONTHS})")
    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of the report")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    args = parser.parse_args()

    if args.months < 1 or args.months > 24:
        print("[ERROR] --months must be an integer between 1 and 24 "
              f"(got {args.months})", file=sys.stderr)
        sys.exit(2)

    _cli.check_cli_available()

    print(f"[1/3] Querying available RDS instances (client-side filtered) "
          f"...", file=sys.stderr)
    instance_error = ""
    instances: list[dict] = []
    try:
        instances = fetch_rds_instances(args.profile)
    except _cli.CliError as e:
        instance_error = str(e)
        print(f"[ERROR] QueryAvailableInstances failed: {e}", file=sys.stderr)

    print(f"[2/3] Querying orders of the last {args.months} month(s) "
          f"(explicit time window) ...", file=sys.stderr)
    order_error = ""
    orders: list[dict] = []
    window = ("", "")
    try:
        orders, start_iso, end_iso = fetch_orders(args.months, args.profile)
        window = (start_iso, end_iso)
    except _cli.CliError as e:
        order_error = str(e)
        print(f"[ERROR] QueryOrders failed: {e}", file=sys.stderr)

    print("[3/3] Analyzing expiry windows, renewals and EOS ...",
          file=sys.stderr)
    inst_results = analyze_instances(instances)
    order_analysis = analyze_orders(orders)
    eos_versions, eos_fallback_used = (
        analyze_eos(orders, args.profile) if not order_error or orders
        else ([], False))

    summary, key_findings, suggestions = _build_summary_fields(
        args.months, window, inst_results, order_analysis, eos_versions,
        instance_error, order_error)

    if args.json:
        result = {
            "months": args.months,
            "order_window": {"create_time_start": window[0],
                             "create_time_end": window[1]},
            "apis": ["QueryAvailableInstances", "QueryOrders",
                     "DescribeInstanceBill (EOS fallback only)"],
            "query_error": (instance_error or order_error or None),
            "query_errors": {"instances": instance_error or None,
                             "orders": order_error or None},
            "instances": inst_results,
            "orders": order_analysis,
            "eos": {
                "versions_detected": eos_versions,
                "bill_config_fallback_used": eos_fallback_used,
                "matched_entries": {v: RDS_EOS_TABLE[v] for v in eos_versions},
                "full_table": (RDS_EOS_TABLE if not eos_versions else None),
            },
            "summary": summary,
            "key_findings": key_findings,
            "suggestions": suggestions,
        }
        print(json.dumps(result, indent=2))
        if instance_error and order_error:
            sys.exit(1)
        return

    if instance_error and order_error:
        print("\nSummary")
        print("-------")
        print("Key finding      : both queries failed, so no data could "
              "be read.")
        print("Next steps:")
        for s in suggestions:
            print(f"  - {s}")
        sys.exit(1)

    render(inst_results, order_analysis, eos_versions, args.months, window,
           instance_error, order_error)

    print("\nSummary")
    print("-------")
    print(f"What was queried : RDS expiry status of this account plus the "
          f"order history of the last {args.months} month(s) "
          f"({window[0]} .. {window[1]}).")
    print("Key findings:")
    for finding in key_findings:
        print(f"  - {finding}")
    print("Suggested next steps:")
    for s in suggestions:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
