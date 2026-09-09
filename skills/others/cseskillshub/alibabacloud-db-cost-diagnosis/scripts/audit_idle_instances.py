#!/usr/bin/env python3
"""
audit_idle_instances.py -- Cross-check billed RDS instances against load
========================================================================
SECURITY: READ-ONLY. This script only queries BSS billing APIs
(DescribeInstanceBill) and CloudMonitor (DescribeMetricList). It never reads
or writes any AccessKey / Secret; credentials are resolved by the aliyun CLI
default credential chain. Never pass AK/SK to this script.

Purpose:
    An RDS instance that is billed every month but shows almost no load is a
    strong release / downscale candidate. This audit first finds the RDS
    instances with a positive charge in a billing cycle (billing side), then
    samples their CPU / connection / IOPS / disk utilization from
    CloudMonitor over the last CMS_WINDOW_DAYS days (load side) and renders
    a three-state verdict per instance: idle / low_load / active.

Verdict rules (all thresholds live in _constants.py):
    idle      -- average CPU < IDLE_CPU_AVG_PCT AND average connection
                 usage < IDLE_CONN_AVG_PCT AND at least IDLE_LOW_POINT_RATIO
                 of the hourly points stay below the CPU threshold. An idle
                 verdict additionally requires REAL data for BOTH dimensions
                 (CPU and connection); a missing dimension is never
                 back-filled with zero.
    low_load  -- not idle, but average CPU < IDLE_LOW_LOAD_CPU_AVG_PCT.
    active    -- everything else with data.
    inconclusive -- metric data missing for the instance entirely OR for
                 any single dimension; it is NEVER judged idle without
                 complete evidence (reported with a [WARN]).

Degradation:
    When CloudMonitor fails entirely, the audit degrades to the billing-side
    listing with a "load data unavailable" note -- it never aborts the
    billing part.

Dual-audience output:
  - Default (human-readable): a verdict table plus a plain-language
    "Summary" section, written for non-technical readers.
  - --json (for Agents): the full detail fields plus machine-consumable
    "summary" / "key_findings" / "suggestions" fields; empty or failed
    queries still emit these fields so downstream stages can consume them.

Usage:
    python3 audit_idle_instances.py [--billing-cycle YYYY-MM] [--json] \
        [--profile <name>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta

import _cli
from _constants import (
    CMS_BATCH_SIZE,
    CMS_MAX_PAGES,
    CMS_METRICS_RDS,
    CMS_NAMESPACE,
    CMS_PERIOD,
    CMS_WINDOW_DAYS,
    DB_PRODUCT_CODES,
    IDLE_CONN_AVG_PCT,
    IDLE_CPU_AVG_PCT,
    IDLE_LOW_LOAD_CPU_AVG_PCT,
    IDLE_LOW_POINT_RATIO,
)

_BILLING_CYCLE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Metric that defines a "low point" sample (the primary idle signal).
_LOW_POINT_METRIC = "CpuUsage"


def strip_bss_region_suffix(instance_id: str) -> str:
    """Normalize a billing-side instance id to the bare CloudMonitor id.

    BSS bill rows of pay-as-you-go instances store the id as
    "<instance-id>;<region-id>", but CloudMonitor Dimensions only accept
    the bare instance id (a region-suffixed id silently returns zero
    datapoints). Everything from the first ';' on is therefore dropped.
    """
    if not instance_id:
        return instance_id
    return instance_id.split(";", 1)[0]


assert strip_bss_region_suffix("rm-abc;cn-hangzhou") == "rm-abc"
assert strip_bss_region_suffix("rm-abc") == "rm-abc"
assert strip_bss_region_suffix("") == ""


def _billing_cycle_type(value: str) -> str:
    """argparse type validator: --billing-cycle must be YYYY-MM."""
    if not _BILLING_CYCLE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid --billing-cycle '{value}': expected format YYYY-MM "
            f"(e.g. 2026-07)")
    return value


# ---------------------------------------------------------------------------
# Pure verdict logic (inline boundary assertions; self-checked on load)
# ---------------------------------------------------------------------------

def classify_instance_load(cpu_avg: float, conn_avg: float,
                           low_point_ratio: float, has_cpu: bool,
                           has_conn: bool) -> str:
    """Three-state (+inconclusive) load verdict for one instance.

    - Any dimension without real data (has_cpu / has_conn False) ->
      "inconclusive": a missing average is never back-filled with 0.0, so
      it must never tip the instance into "idle".
    - idle:     cpu_avg < IDLE_CPU_AVG_PCT AND conn_avg < IDLE_CONN_AVG_PCT
                AND low_point_ratio >= IDLE_LOW_POINT_RATIO.
    - low_load: not idle, but cpu_avg < IDLE_LOW_LOAD_CPU_AVG_PCT.
    - active:   everything else.
    All thresholds are strict lower bounds except the low-point ratio.
    """
    if not (has_cpu and has_conn):
        return "inconclusive"
    if (cpu_avg < IDLE_CPU_AVG_PCT and conn_avg < IDLE_CONN_AVG_PCT
            and low_point_ratio >= IDLE_LOW_POINT_RATIO):
        return "idle"
    if cpu_avg < IDLE_LOW_LOAD_CPU_AVG_PCT:
        return "low_load"
    return "active"


def _run_inline_self_tests() -> None:
    """Module-load self check: normal / boundary / invalid inputs."""
    # Normal: clearly active / clearly idle.
    assert classify_instance_load(60.0, 40.0, 0.10, True, True) == "active"
    assert classify_instance_load(1.0, 1.0, 0.95, True, True) == "idle"
    # Boundary: ratios are inclusive, averages are strict lower bounds.
    assert classify_instance_load(1.0, 1.0, IDLE_LOW_POINT_RATIO,
                                  True, True) == "idle"
    assert classify_instance_load(IDLE_CPU_AVG_PCT, 1.0, 0.99,
                                  True, True) != "idle"
    assert classify_instance_load(1.0, IDLE_CONN_AVG_PCT, 0.99,
                                  True, True) != "idle"
    assert classify_instance_load(IDLE_LOW_LOAD_CPU_AVG_PCT - 0.01, 60.0,
                                  0.0, True, True) == "low_load"
    assert classify_instance_load(IDLE_LOW_LOAD_CPU_AVG_PCT, 60.0,
                                  0.0, True, True) == "active"
    # Invalid / degenerate: no data must never yield "idle".
    assert classify_instance_load(0.0, 0.0, 0.0, False, False) == "inconclusive"
    assert classify_instance_load(0.0, 0.0, 1.0, False, False) == "inconclusive"
    # Single-dimension gap: CPU present but connection datapoints missing
    # (conn_avg would be a 0.0 fallback) must stay inconclusive, never idle.
    assert classify_instance_load(1.0, 0.0, 0.95, True, False) == "inconclusive"
    # The mirror case: connection data only, CPU missing.
    assert classify_instance_load(0.0, 1.0, 0.0, False, True) == "inconclusive"

    # BSS ";region" suffix stripping for CloudMonitor dimensions.
    assert strip_bss_region_suffix("rm-bp1abc;cn-hangzhou") == "rm-bp1abc"
    assert strip_bss_region_suffix("rm-bp1abc") == "rm-bp1abc"
    assert strip_bss_region_suffix("") == ""


_run_inline_self_tests()


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------

def fetch_charged_rds_instances(billing_cycle: str,
                                profile: str | None) -> list[tuple[str, float]]:
    """[(instance_id, cost)] with cost > 0 for ProductCode=rds, cost desc."""
    params = {"BillingCycle": billing_cycle, "ProductCode": "rds"}
    items = _cli.paginate_next_token("bssopenapi", "DescribeInstanceBill",
                                     params, profile=profile)
    totals: dict[str, float] = {}
    for item in items:
        instance_id = item.get("InstanceID") or ""
        if not instance_id:
            continue
        try:
            cost = float(item.get("PretaxAmount") or 0)
        except (TypeError, ValueError):
            cost = 0.0
        totals[instance_id] = totals.get(instance_id, 0.0) + cost
    charged = [(iid, cost) for iid, cost in totals.items() if cost > 0]
    charged.sort(key=lambda pair: pair[1], reverse=True)
    return charged


def fetch_metric_points(metric_name: str, instance_ids: list[str],
                        start_ms: int, end_ms: int,
                        profile: str | None) -> list[dict]:
    """All CMS datapoints of one metric for a batch of <=CMS_BATCH_SIZE ids.

    Datapoints arrive as a JSON *string* that needs a second json.loads;
    pagination is NextToken-based with a hard page guardrail.
    """
    dimensions = json.dumps([{"instanceId": iid} for iid in instance_ids])
    base_params = {
        "Namespace": CMS_NAMESPACE,
        "MetricName": metric_name,
        "Period": str(CMS_PERIOD),
        "StartTime": str(start_ms),
        "EndTime": str(end_ms),
        "Dimensions": dimensions,
    }
    points: list[dict] = []
    next_token: str | None = None
    for page in range(CMS_MAX_PAGES):
        params = dict(base_params)
        if next_token:
            params["NextToken"] = next_token
        body = _cli.call("cms", "DescribeMetricList", params,
                         profile=profile)
        raw = body.get("Datapoints", "")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    points.extend(p for p in parsed if isinstance(p, dict))
            except json.JSONDecodeError:
                print(f"[WARN] cms {metric_name}: unparseable Datapoints "
                      f"payload on page {page + 1}; page skipped",
                      file=sys.stderr)
        next_token = body.get("NextToken") or None
        if not next_token:
            break
    else:
        print(f"[WARN] cms {metric_name}: pagination stopped at the "
              f"{CMS_MAX_PAGES}-page guardrail; points may be incomplete",
              file=sys.stderr)
    return points


def collect_load_stats(instance_ids: list[str],
                       profile: str | None) -> tuple[dict, list[str]]:
    """Sample every CMS metric for all instances (batched).

    Returns (stats, failed_metrics):
        stats: {instance_id: {"cpu": [avgs], "conn": [avgs]}}
        failed_metrics: metric names whose query failed entirely.
    """
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - CMS_WINDOW_DAYS * 24 * 3600 * 1000
    stats: dict[str, dict[str, list[float]]] = {
        iid: {"cpu": [], "conn": []} for iid in instance_ids
    }
    failed_metrics: list[str] = []

    # CloudMonitor wants bare instance ids; billing-side ids may carry a
    # ";<region>" suffix, so query by bare id and map datapoints back to
    # the billed key(s).
    dim_to_billed: dict[str, list[str]] = {}
    for iid in instance_ids:
        dim_to_billed.setdefault(strip_bss_region_suffix(iid), []).append(iid)
    bare_ids = sorted(dim_to_billed)

    metric_to_key = {"CpuUsage": "cpu", "ConnectionUsage": "conn"}
    for metric in CMS_METRICS_RDS:
        for start in range(0, len(bare_ids), CMS_BATCH_SIZE):
            batch = bare_ids[start:start + CMS_BATCH_SIZE]
            try:
                points = fetch_metric_points(metric, batch, start_ms, end_ms,
                                             profile)
            except _cli.CliError as e:
                failed_metrics.append(metric)
                print(f"[WARN] cms {metric} query failed: {e}",
                      file=sys.stderr)
                break  # other batches of this metric would fail alike
            key = metric_to_key.get(metric)
            if key is None:
                continue  # IOPS/disk points are fetched for coverage only
            for point in points:
                bare = point.get("instanceId") or ""
                for billed_key in dim_to_billed.get(bare, []):
                    try:
                        value = float(point.get("Average")
                                      if point.get("Average") is not None
                                      else point.get("Value") or 0)
                    except (TypeError, ValueError):
                        continue
                    stats[billed_key][key].append(value)
    return stats, failed_metrics


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ---------------------------------------------------------------------------
# Summary (shared by both output modes)
# ---------------------------------------------------------------------------

def _build_summary_fields(
    billing_cycle: str,
    cycle_auto_filled: bool,
    charged: list[tuple[str, float]],
    verdicts: dict[str, dict],
    load_available: bool,
    error: str = "",
) -> tuple[str, list[str], list[str]]:
    cycle_note = (" (auto-filled to the current month)" if cycle_auto_filled
                  else "")

    if error:
        return (
            f"The idle-instance audit of RDS for {billing_cycle} failed "
            f"before any data could be read.",
            [f"Query error: {error}"],
            [
                "Check that the CLI credential is configured and has BSS "
                "billing read permission (aliyun configure).",
                "Verify the billing cycle, then re-run.",
            ],
        )

    if not charged:
        return (
            f"No billed RDS instance was found in billing cycle "
            f"{billing_cycle}{cycle_note}; there is nothing to check for "
            f"idleness.",
            [
                "DescribeInstanceBill returned no RDS row with a positive "
                f"amount in {billing_cycle}.",
                "Likely reasons: the account has no RDS instance, the "
                "instance was released before the cycle, or the charges sit "
                "under another account.",
            ],
            [
                "Verify the billing cycle; bill data can lag briefly for "
                "the current month, so re-run later if the cycle is recent.",
            ],
        )

    idle = [iid for iid, v in verdicts.items() if v["verdict"] == "idle"]
    low_load = [iid for iid, v in verdicts.items()
                if v["verdict"] == "low_load"]
    inconclusive = [iid for iid, v in verdicts.items()
                    if v["verdict"] == "inconclusive"]
    idle_cost = sum(v["cost"] for iid, v in verdicts.items()
                    if v["verdict"] == "idle")

    findings = [
        f"{len(charged)} RDS instance(s) carried charges in "
        f"{billing_cycle} ({sum(c for _, c in charged):.2f} CNY in total).",
    ]
    suggestions: list[str] = []
    if not load_available:
        findings.append(
            "CloudMonitor load data was unavailable, so no instance could "
            "be judged idle; the listing above is the billing side only.")
        suggestions.append(
            "Re-run later or check CloudMonitor permissions "
            "(cms:DescribeMetricList) to get load-based verdicts.")
        return (
            f"Audited {len(charged)} billed RDS instance(s) of "
            f"{billing_cycle}{cycle_note}: load data unavailable, "
            f"verdicts inconclusive.",
            findings,
            suggestions,
        )

    findings.append(
        f"Verdicts over the last {CMS_WINDOW_DAYS} days: {len(idle)} idle, "
        f"{len(low_load)} low-load, {len(inconclusive)} inconclusive.")
    if idle:
        findings.append(
            f"Idle instances account for {idle_cost:.2f} CNY of the cycle "
            f"charge: {', '.join(idle)}.")
        suggestions.append(
            "Confirm the idle instances truly serve no traffic (check "
            "connections / last-login time), then release them or switch "
            "them to a pay-as-you-go test spec to stop the charge.")
    if low_load:
        suggestions.append(
            "For low-load instances, evaluate a spec downgrade instead of "
            "a full release.")
    if inconclusive:
        findings.append(
            f"Missing or incomplete metric data for: {', '.join(inconclusive)} "
            f"(no data at all, or one of the CPU/connection dimensions "
            f"empty) -- they are NOT judged idle without complete "
            f"evidence.")
        suggestions.append(
            "For inconclusive instances, verify monitoring is enabled or "
            "the instances were created only recently (no samples yet).")
    if not idle and not low_load:
        suggestions.append(
            "No idle candidate was found; if the bill still looks high, "
            "run audit_paid_features.py to check optional add-on charges.")
    return (
        f"Audited {len(charged)} billed RDS instance(s) of {billing_cycle}"
        f"{cycle_note} against {CMS_WINDOW_DAYS} days of load data: "
        f"{len(idle)} idle, {len(low_load)} low-load.",
        findings,
        suggestions,
    )


# ---------------------------------------------------------------------------
# Rendering (human-readable mode)
# ---------------------------------------------------------------------------

def render(billing_cycle, cycle_auto_filled, charged, verdicts,
           load_available) -> None:
    print("Idle Instance Audit (RDS)")
    print("-" * 56)
    print(f"Billing cycle  : {billing_cycle}"
          + (" (auto-filled: current month)" if cycle_auto_filled else ""))
    print(f"Load window    : last {CMS_WINDOW_DAYS} days, "
          f"period {CMS_PERIOD}s")
    print(f"Billed insts   : {len(charged)}")
    if charged:
        print(f"Load data      : "
              f"{'available' if load_available else 'UNAVAILABLE'}")
    print()

    if not charged:
        print("No billed RDS instance found for this cycle.")
        return

    header = (f"| {'Instance':<26} | {'Cost':>10} | {'CPU%':>6} "
              f"| {'Conn%':>6} | {'LowPts':>6} | {'Verdict':<12} |")
    print(header)
    print(f"|{'-' * 28}|{'-' * 12}|{'-' * 8}|{'-' * 8}|{'-' * 8}"
          f"|{'-' * 14}|")
    order = {"idle": 0, "low_load": 1, "inconclusive": 2, "active": 3}
    for iid, v in sorted(verdicts.items(),
                         key=lambda kv: (order.get(kv[1]["verdict"], 9),
                                         -kv[1]["cost"])):
        cpu = (f"{v['cpu_avg']:>6.1f}" if v["cpu_points"] else "   n/a")
        conn = (f"{v['conn_avg']:>6.1f}" if v["conn_points"] else "   n/a")
        low = (f"{v['low_point_ratio']:>6.2f}" if v["cpu_points"]
               else "   n/a")
        print(f"| {iid:<26} | {v['cost']:>10.2f} | {cpu} | {conn} "
              f"| {low} | {v['verdict']:<12} |")

    if not load_available:
        print("\nCloudMonitor load data was unavailable; verdicts stay "
              "inconclusive and no instance is claimed idle.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-check billed RDS instances against CloudMonitor "
                    "load to find idle / low-load instances (read-only)",
    )
    parser.add_argument("--billing-cycle", default=None,
                        type=_billing_cycle_type,
                        help="Billing cycle YYYY-MM (default: the current "
                             "month, auto-filled and declared in output)")
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

    print(f"[1/3] Querying billed RDS instances of {billing_cycle} ...",
          file=sys.stderr)
    query_error = ""
    charged: list[tuple[str, float]] = []
    try:
        charged = fetch_charged_rds_instances(billing_cycle, args.profile)
    except _cli.CliError as e:
        query_error = str(e)
        print(f"[ERROR] Bill query failed: {e}", file=sys.stderr)

    verdicts: dict[str, dict] = {}
    load_available = False
    failed_metrics: list[str] = []
    if charged and not query_error:
        instance_ids = [iid for iid, _ in charged]
        print(f"[2/3] Sampling CMS load of {len(instance_ids)} instance(s) "
              f"({len(CMS_METRICS_RDS)} metrics, {CMS_WINDOW_DAYS}d) ...",
              file=sys.stderr)
        stats, failed_metrics = collect_load_stats(instance_ids, args.profile)
        # Load counts as available when at least one metric returned.
        load_available = len(failed_metrics) < len(CMS_METRICS_RDS)
        for iid, cost in charged:
            cpu_points = stats[iid]["cpu"]
            conn_points = stats[iid]["conn"]
            has_cpu = bool(cpu_points)
            has_conn = bool(conn_points)
            cpu_avg = _avg(cpu_points)
            conn_avg = _avg(conn_points)
            low_ratio = (sum(1 for v in cpu_points if v < IDLE_CPU_AVG_PCT)
                         / len(cpu_points)) if cpu_points else 0.0
            verdict = classify_instance_load(cpu_avg, conn_avg, low_ratio,
                                             has_cpu, has_conn)
            if not (has_cpu and has_conn):
                missing = [name for name, ok in
                           (("CpuUsage", has_cpu),
                            ("ConnectionUsage", has_conn)) if not ok]
                print(f"[WARN] incomplete CMS data for {iid} "
                      f"({', '.join(missing)} has no datapoint in the "
                      f"window); verdict=inconclusive (not judged idle)",
                      file=sys.stderr)
            verdicts[iid] = {
                "cost": round(cost, 2),
                "cpu_avg": round(cpu_avg, 2),
                "conn_avg": round(conn_avg, 2),
                "low_point_ratio": round(low_ratio, 3),
                "cpu_points": len(cpu_points),
                "conn_points": len(conn_points),
                "has_data": has_cpu and has_conn,
                "verdict": verdict,
            }
    else:
        print("[2/3] Nothing to sample (no charged RDS instance).",
              file=sys.stderr)

    print("[3/3] Rendering verdicts ...", file=sys.stderr)

    summary, key_findings, suggestions = _build_summary_fields(
        billing_cycle, cycle_auto_filled, charged, verdicts, load_available,
        error=query_error)

    if args.json:
        result = {
            "product_code": "rds",
            "product_name": DB_PRODUCT_CODES.get("rds", "RDS"),
            "billing_cycle": billing_cycle,
            "billing_cycle_auto_filled": cycle_auto_filled,
            "apis": ["DescribeInstanceBill", "cms:DescribeMetricList"],
            "query_error": query_error or None,
            "cms_namespace": CMS_NAMESPACE,
            "cms_metrics": CMS_METRICS_RDS,
            "cms_failed_metrics": sorted(set(failed_metrics)),
            "cms_window_days": CMS_WINDOW_DAYS,
            "cms_period": CMS_PERIOD,
            "load_data_available": load_available,
            "charged_instance_count": len(charged),
            "verdicts": verdicts,
            "thresholds": {
                "idle_cpu_avg_pct": IDLE_CPU_AVG_PCT,
                "idle_conn_avg_pct": IDLE_CONN_AVG_PCT,
                "idle_low_point_ratio": IDLE_LOW_POINT_RATIO,
                "low_load_cpu_avg_pct": IDLE_LOW_LOAD_CPU_AVG_PCT,
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
        print(f"What was queried : billed RDS instances of billing cycle "
              f"{billing_cycle}.")
        print("Key finding      : the query failed, so no bill data could "
              "be read.")
        print("Next steps:")
        for s in suggestions:
            print(f"  - {s}")
        sys.exit(1)

    render(billing_cycle, cycle_auto_filled, charged, verdicts,
           load_available)

    print("\nSummary")
    print("-------")
    print(f"What was queried : {len(charged)} billed RDS instance(s) of "
          f"{billing_cycle} against the last {CMS_WINDOW_DAYS} days of "
          f"CloudMonitor load.")
    print("Key findings:")
    for finding in key_findings:
        print(f"  - {finding}")
    print("Suggested next steps:")
    for s in suggestions:
        print(f"  - {s}")


if __name__ == "__main__":
    main()
