# Module 3: Cost Audit Orchestration (Renewal / Idle / Paid Features)

Proactive, read-only cost audits that complement the reactive bill diagnostics
orchestrated from SKILL.md: instead of explaining a
bill that already hurt, these audits inventory expiry risk, idle capacity and
optional paid features before they become disputes. Every audit MUST run
through its single entry script; never re-assemble the underlying `aliyun`
CLI calls by hand.

## Which script to use

| User signal | Script | Capability |
|---|---|---|
| "Which instances are about to expire / not set to renew?", "was I auto-renewed without knowing?", "a renewal looks much more expensive than before", engine end-of-support questions | `scripts/audit_renewal_orders.py` | C - renewal & order audit |
| "Am I paying for a database nobody uses?", "find idle / low-load instances" | `scripts/audit_idle_instances.py` | D - idle & low-load detection |
| "What am I actually paying for?", "unexplained charge / unknown feature on the bill" | `scripts/audit_paid_features.py` | E - paid-feature & unexplained-charge audit |

When the request is a generic "audit my database costs", run C, D and E in
that order and merge the scripts' `Summary` sections; they are independent
and each exits 0 even on empty data.

## Capability C - `audit_renewal_orders.py`

```bash
python3 scripts/audit_renewal_orders.py [--months N] [--json] [--profile NAME]
```

`--months` (>= 1, default 6) is the order-history lookback in calendar
months; the script always sends an explicit `CreateTimeStart` /
`CreateTimeEnd` window, because QueryOrders silently narrows to roughly a
1-hour window when no window is given (a known pitfall).

Three analysis sections:

1. **Expiry windows** - `QueryAvailableInstances` lists the account's
   available instances. The server-side `ProductCode` filter is unreliable
   (verified: requesting `rds` can still return other products), so the
   script re-filters client-side for `ProductCode == rds`. Each instance's
   `EndTime` is graded into a window:

   | Window | Meaning |
   |---|---|
   | `expired` | EndTime already passed |
   | `7d` / `30d` / `90d` | EndTime within N days (inclusive) |
   | `safe` | Beyond the 90-day window |
   | `unknown` | EndTime missing or unparseable |

   `RenewStatus` then sets the risk label: **high** = expired, or
   `NotRenewal` inside 7d/30d; **medium** = `NotRenewal` inside 90d, or any
   other status inside 7d/30d; **low** = everything else.

2. **Renewal orders** - `QueryOrders` (full history of the window, no
   OrderType filter). Renewals are grouped by commodity code in time order;
   the script flags adjacent renewals whose price ratio exceeds **3x**
   (non-positive previous prices are skipped, never divided by) and lists
   `Refund` / `Cancelled` orders as anomalies. A 3x jump typically means a
   longer renewal term, a spec change, or a lost discount - verify at order
   level; bill APIs carry no term/discount dimension (see FAQ section 4).

3. **Engine end-of-support (EOS)** - engine versions are best-effort
   extracted from order metadata (`ProductType` / `CommodityCode` /
   `ProductCode`) and, when orders carry none, from the `Config` strings of
   the current-month RDS bill. Only versions present in the embedded table
   below are ever matched. When nothing can be extracted, output the full
   table and ask the user to confirm each instance's engine version in the
   console - **never guess or fabricate a version**.

### EOS reference table (snapshot 2026-08-26)

Static knowledge embedded in `scripts/_constants.py`; dates follow the
official Alibaba Cloud lifecycle documentation as read on the snapshot date,
and official announcements always take precedence over this table.

| Engine | Status | EOS date | Source |
|---|---|---|---|
| MySQL 5.5 | End of support | 2021-12-08 | https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/major-version-lifecycle-description |
| MySQL 5.6 | Planned end of support (extended) | 2028-02-05 | https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/support-for-apsaradb-rds-for-mysql-instances-that-run-mysql-5-6-and-5-7-is-extended |
| MySQL 5.7 | Planned end of support (extended) | 2028-10-21 | same extension announcement as MySQL 5.6 |
| MySQL 8.0 | No end of support planned | - | major-version-lifecycle-description (above) |
| MySQL 8.4 | No end of support planned | - | major-version-lifecycle-description (above) |
| SQL Server 2016 | End of patch updates | 2026-07-14 | https://help.aliyun.com/zh/rds/apsaradb-rds-for-sql-server/new-patches-are-no-longer-provided-for-apsaradb-rds-instances-running-sql-server-2016 |

## Capability D - `audit_idle_instances.py`

```bash
python3 scripts/audit_idle_instances.py [--billing-cycle YYYY-MM] [--json] [--profile NAME]
```

Flow: bill discovery first, then load sampling.

1. `DescribeInstanceBill(ProductCode=rds)` finds the billed RDS instances of
   the cycle. **Empty result is a normal outcome**: the script reports "no
   billed RDS instance" and exits 0 - do not treat it as an error.
2. CloudMonitor `DescribeMetricList` samples namespace
   `acs_rds_dashboard`, metrics `CpuUsage` / `ConnectionUsage` /
   `IOPSUsage` / `DiskUsage` (note: `CPUUsage` does NOT exist; the verified
   name is `CpuUsage`), over the last **7 days** at **3600 s** period, at
   most **50 instances per Dimensions batch**. IOPS/disk are fetched for
   coverage only; the verdict is driven by CPU and connections.

Verdict semantics (thresholds are strict lower bounds, the low-point ratio
is inclusive):

| Verdict | Rule |
|---|---|
| `idle` | avg CPU < 5% AND avg connections < 5% AND >= 80% of hourly CPU points below 5%; requires REAL datapoints for BOTH the CPU and the connection dimension |
| `low_load` | not idle, but avg CPU < 15% (downscale candidate, not release) |
| `active` | everything else with data |
| `inconclusive` | no metric datapoints at all, or one of the CPU/connection dimensions empty (a missing average is never back-filled with zero) - NEVER judged idle without complete evidence |

Degradation: if CloudMonitor fails entirely, the audit degrades to the
billing-side listing with a "load data unavailable" note and never aborts;
verdicts stay inconclusive.

## Capability E - `audit_paid_features.py`

```bash
python3 scripts/audit_paid_features.py [--billing-cycle YYYY-MM] [--product rds] [--json] [--profile NAME]
```

`--product` accepts `rds|dds|kvstore|polardb|dts|cbs|cdt` (default `rds`).
Flow: `DescribeInstanceBill(ProductCode)` of the cycle ->
`DescribeSplitItemBill` drill-down of the **top 10** costliest instances
(guardrail; instances beyond it are reported at instance level only) ->
every split-item row is attributed to one bucket:

- **paid_feature** - matches the billing-item keyword map below;
- **base** - matches the product's common base items (instance / storage /
  backup ...);
- **residual** - matches neither -> an unidentified charge candidate worth
  inspecting (leftover add-on, manual adjustment, marketplace item).

### Paid-feature billing-item map

Case-insensitive word-boundary match on the billing-item name (a keyword
only matches when no letter/digit sits directly next to it, so compact
tokens cannot absorb unrelated items):

| Keyword | Feature | Category | Note |
|---|---|---|---|
| `sql audit`, `sql explorer`, `sql collector` | SQL Audit (SQL Explorer) | observability | Audit log storage; billed by retention and volume |
| `performance insight` | Performance Insight | observability | Extended retention is the paid tier |
| `cross-region backup` | Cross-region Backup | backup | Charged on top of standard local backup |
| `database proxy`, `db proxy` | Database Proxy | connection | Dedicated proxy nodes bill separately |
| `read-only instance`, `readonly instance` | Read-only Instance | compute | Each replica carries its own instance fee |
| `auto scaling` | Auto Scaling (storage/compute) | elasticity | Expanded capacity bills until shrunk back |
| `das service` | DAS Pro (Database Autonomy Service) | observability | Paid autonomy/insight tier |

## Output contract (all three scripts)

Every script emits a human-readable report ending with a plain-language
`Summary` section, and with `--json` the same conclusion as `summary` /
`key_findings` / `suggestions` plus a `query_error` field; both are
populated even on empty or failed queries. Exit codes: **0** success
(including the empty-data case), **2** invalid parameters, **1** query
failure. The Agent's final numbers must be quoted verbatim from these
outputs.

## Known limitations

- Engine-version extraction is best effort: order/bill metadata often carries
  no version, in which case the EOS table is shown and the user confirms.
- `QueryAvailableInstances` server-side `ProductCode` filtering is
  unreliable; the client-side re-filter is the authoritative boundary.
- The renewal audit's `DescribeInstanceBill` call is only a fallback source
  of engine-version hints (current-month RDS bill `Config` strings); it is
  skipped gracefully on failure.
- CloudMonitor datapoints of freshly created instances may not exist yet;
  such instances stay `inconclusive` on purpose.
