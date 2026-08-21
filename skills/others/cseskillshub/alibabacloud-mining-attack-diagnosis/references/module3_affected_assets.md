# Module 3: Affected Asset Scope

## Purpose
Determine which cloud assets are affected by the mining activity and put it in
account-level context. Grouping alerts by asset reveals the blast radius and
whether the miner is spreading (worm-style lateral movement).

## APIs — Public SAS (version 2018-12-03)

```
Product: sas  (endpoint tds.{region}.aliyuncs.com, version 2018-12-03)
Actions:
  DescribeSecurityStatInfo  -- account security overview (pending alerts, vulns, health)
  DescribeFieldStatistics   -- asset-fleet risk statistics
```

## Asset Grouping (client-side)

The Step 1 mining alerts are grouped by asset key
(`uuid` → `instanceName` → `internetIp`). For each asset the report shows:

| Field | Meaning |
|-------|---------|
| Asset | Instance name (or masked uuid) |
| IP | Internet / intranet IP |
| Alerts | Number of mining alerts on this asset |
| Event Names | Distinct mining alert names observed |
| maxLevelRank | Highest severity among the asset's alerts |

Assets are sorted by highest severity first.

## Account Overview

`DescribeSecurityStatInfo` provides a quick account posture snapshot:

- `SecurityEvent` — counts by level (serious / suspicious / remind) and total
- `Vulnerability` — outstanding vulnerability counts by urgency
- `HealthCheck` — baseline/config check warnings
- `AttackEvent` — recent attack counts

`DescribeFieldStatistics` provides fleet-level counts (total instances,
exposed instances, at-risk instances, unprotected instances) used to gauge how
representative the mining incident is of the wider environment.

## Spread Assessment

- **1 asset affected** → contained single-host compromise.
- **>1 asset affected** → possible lateral movement / worm (e.g. sysrv, kinsing
  self-propagation via SSH keys or exploited services). Treat all affected
  hosts as compromised and hunt for the shared sample/IOC across the fleet.

## Standalone Query

Asset grouping is performed by the orchestrator. The account overview APIs can
also be exercised implicitly via `mining_investigation.py` Step 3 logging.
