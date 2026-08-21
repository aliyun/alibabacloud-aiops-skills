# Module 6: Corroboration (CloudMonitor CPU + ActionTrail) — Optional

## Purpose
Strengthen (or challenge) the SAS-based mining verdict with two additional
read-only signals, **only when `--corroborate` is passed**:

1. **CloudMonitor CPU** — cryptominers saturate CPU; sustained high utilization
   on an affected instance is strong corroboration of active mining, and is
   especially useful for the "high CPU, mining suspected but no clear alert"
   case.
2. **ActionTrail high-risk operation trace** — reveals *how* a miner may have
   been delivered or spread (remote command execution, instance scale-out,
   credential/persistence abuse, security-group egress opening).

This module never changes the no-fabrication rule: corroboration adds evidence,
it does not manufacture a mining verdict on its own.

## Conditional Triggering

Step 4b runs **only when `--corroborate` is passed AND Step 1 confirmed at least
one mining alert.** On a clean account nothing is queried. The single exception:
if `--cpu-instance-id` is supplied, the **CPU check alone** still runs (the
"high CPU, mining suspected but no alert yet" case), while ActionTrail tracing
always waits for confirmed mining (it is account-wide and pointless otherwise).
When a sub-check is skipped, the report records the reason in `cpu_note` /
`trace_note`.

## APIs — Public (read-only)

```
Product: cms          (endpoint metrics.{region}.aliyuncs.com, version 2019-01-01)
Action:  DescribeMetricList
         Namespace=acs_ecs_dashboard, MetricName=CPUUtilization, Period=300

Product: actiontrail  (endpoint actiontrail.{region}.aliyuncs.com, version 2020-07-06)
Action:  LookupEvents  (NextToken pagination)
```

Required permissions (in addition to the core SAS/STS set):
`cms:QueryMetricList`, `actiontrail:LookupEvents`. If either is missing, the
step degrades gracefully — the error is captured and the rest of the report is
unaffected. Omitting `--corroborate` keeps the skill SAS-only.

## CPU Corroboration Logic

- Instance IDs come from `--cpu-instance-id` if provided, otherwise are
  auto-derived from the affected assets (uuid/instanceName values starting with
  `i-`). If none are derivable, the CPU check is skipped with a note.
- CPUUtilization is pulled at 5-minute granularity over the window.
- `MINING_CPU_THRESHOLD` (default 80%) defines "high". If **≥50%** of datapoints
  are at/above the threshold, the instance is flagged `sustainedHighCpu = true`
  (mining-consistent).

## ActionTrail Trace Logic

- Queries `LookupEvents` over the window; by default keeps only the high-risk
  operations in `HIGH_RISK_TRACE_EVENTS` (RunCommand/InvokeCommand,
  RunInstances/CreateInstance, CreateAccessKey/CreateUser,
  AuthorizeSecurityGroup(Egress), ReplaceSystemDisk/CreateImage, …). Use `--all`
  on the standalone script to see every event.
- ActionTrail is account/AK-scoped (not per-instance). Correlate the
  `sourceIpAddress` / actor with the mining-affected assets from Steps 1/3 to
  reconstruct the delivery/spread chain.

## Output (orchestrator, `step4b_corroboration`)

```json
{
  "cpu": [
    {"instanceId": "i-bp1xxx", "avg": 92.4, "max": 99.1,
     "highCount": 66, "datapoints": 72, "highRatio": 0.917,
     "sustainedHighCpu": true}
  ],
  "cpu_note": "",
  "trace": {
    "window": {"start": "...", "end": "..."},
    "total": 4, "successful": 3,
    "sourceIps": ["203.0.113.9"],
    "events": [
      {"eventTime": "...", "eventName": "RunCommand",
       "eventSource": "ecs.aliyuncs.com", "sourceIpAddress": "203.0.113.9",
       "userName": "N/A", "errorCode": ""}
    ]
  },
  "errors": []
}
```

## Standalone Scripts

```bash
# CloudMonitor CPU corroboration
python scripts/query_cpu_metrics.py --instance-id i-bp1xxx,i-bp2yyy --hours 6
python scripts/query_cpu_metrics.py --instance-id i-bp1xxx --days 1 --threshold 80 --format json

# ActionTrail high-risk operation trace
python scripts/query_intrusion_trace.py --days 7
python scripts/query_intrusion_trace.py --days 3 --source-ip 203.0.113.9 --format json
python scripts/query_intrusion_trace.py --days 7 --all   # do not pre-filter to high-risk ops

# Orchestrator with corroboration enabled
python scripts/mining_investigation.py --corroborate
python scripts/mining_investigation.py --corroborate --cpu-instance-id i-bp1xxx
```
