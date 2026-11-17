# CloudMonitor metric catalogue for this tier

This is the reading dictionary behind every number in a report. It exists so that a
conclusion can be checked without re-opening the console, and so that the gaps are
visible instead of silently filled.

Query shape used by `scripts/areas/resource_bottleneck/cms_metrics.py`:

| Field | Value used | Status |
| --- | --- | --- |
| `Namespace` | `acs_ecs_dashboard` | working value for ECS metrics; not confirmed by the tier's API review, so it is a single constant in `scripts/areas/resource_bottleneck/_constants.py` and is printed in every report |
| `Dimensions` | `[{"instanceId":"<instance-id>"}]` | one instance per run, which is the whole scope of this skill |
| `Period` | `300` seconds | default; a 5-minute bucket is what "sustained" is measured on |
| `StartTime` / `EndTime` | ISO-8601 UTC, `YYYY-MM-DDThh:mm:ssZ` | taken from the customer when they give a timestamp, otherwise a look-back window derived from `--hours` and labelled as auto-derived |
| `Length` | `1440` | one page ceiling for the series |

The window, the period and the statistic are printed next to every reading. Two
tickets show why that is not decoration: `T-46B31B3D`, where the agent quoted a
60-80% **average** while the customer held a 100% **peak** screenshot, and
`T-3941829E`, where the customer's own objection was that a percentage looked the
same no matter which window was selected.

## Metrics this build queries

All five names below appear in the tier's reviewed ticket dialogue or in the tier's
API notes. Nothing else is queried automatically.

| MetricName | Area | Unit | Needs agent in guest | Statistical output | Caliber that must be quoted with it |
| --- | --- | --- | --- | --- | --- |
| `CPUUtilization` | compute | % | no | average **and** maximum, plus peak timestamp | hypervisor-side view of the instance; on ARM families it absorbs a fixed virtualisation overhead |
| `memory_usedutilization` | memory | % | **yes** | average and maximum | OS-level view; a flat refusal to return data here usually means the agent is not installed, which is itself a finding |
| `DiskReadBPS` | disk IO | Byte/s | **yes** | average and maximum | throughput, not IOPS; an average close to the maximum means the area was pinned, not briefly spiky |
| `DiskWriteBPS` | disk IO | Byte/s | **yes** | average and maximum | the write direction, i.e. the paging-out side of the memory chain |
| `IntranetInRate` | network (intranet) | bit/s | no | average and maximum | intranet inbound only; it says nothing about the public band |

A metric that returns no point in the window is reported as an evidence gap under
rule `R6`, and any conclusion that would depend on it is withheld. An empty series
is never read as "0%" and never read as "normal".

## Caliber pairs that cause disputes, and how to state them

| Pair | What differs | How this skill states it |
| --- | --- | --- |
| average vs maximum | same window, different statistic | both, always, with the timestamp of the maximum |
| host view vs in-guest view | where the sampling sits | `CPUUtilization` is labelled host view; the guest's own `top`/`vmstat` output is labelled in-guest. The two can legitimately disagree and that is a caliber answer, not a monitoring defect |
| percent vs absolute value | 95% of 0.5 GiB is not 95% of 32 GiB | the instance's vCPU and memory in MiB are printed above every area reading (`DescribeInstances`) |
| instance aggregate vs single-disk ceiling | which object is saturated | disk readings are counted against the disk inventory returned by `DescribeDisks`, and no disk ceiling is computed here (see below) |

## Known gaps: metric names this build does not have

The tier needs these areas. Their exact `MetricName` values were **not** confirmed
during this build, so the script refuses to invent one and the gap is declared in
every report instead. Until the metric dictionary review lands, the fallback is
named in the last column and is a real fallback, not an equivalent.

| Missing metric family | Area | Fallback used by this build |
| --- | --- | --- |
| load average (`load_1m` / `load_5m` / `load_15m` style names) | compute / queue | guest `uptime` and `cat /proc/loadavg` behind the confirmation gate |
| swap usage and paging rate (`si`/`so` style names) | memory | guest `vmstat 1 3` (the `si`/`so` columns) and `free -m` for swap totals |
| public (Internet) inbound and outbound rate | network | none available: the public-band conclusion stays qualitative and is handed to the network tier |
| burstable-instance CPU credit balance and consumption | compute | none available: the t-series note in a report is a caliber explanation of what "100%" means, never a credit measurement |
| in-guest `cpu_total` as a distinct queryable series | compute | unconfirmed which `MetricName` corresponds to the console's operating-system view; the guest reading is taken inside the instance instead |
| per-disk IOPS series alongside the BPS series | disk IO | `DescribeDisks` category and size only |

## Disk ceilings are not computed here

Whether a disk reading has reached its provisioned ceiling depends on the
performance contract of that specific disk category and size. The formula a
customer quoted in ticket `T-CC0FA37F` is not a supported basis, so this skill
states the measured throughput and the disk inventory, and hands the ceiling
question to the disk IO tier
([escalation-map.md](resource-bottleneck__escalation-map.md)). A joint CPU-and-disk spike is still
detected, because that is a comparison between two measured series and not a
claim about a limit.

## Adding a metric once its name is confirmed

1. Add the name to `METRICS_EVIDENCED` in `scripts/areas/resource_bottleneck/_constants.py`, with where the
   name came from.
2. Add its area, unit and caliber sentence to `METRIC_PROFILE` in
   `scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py`.
3. Remove the matching line from the gap table above and from `GAPS_DECLARED`.
4. Only then may a rule reference the new area; rules must not get ahead of the
   catalogue.
