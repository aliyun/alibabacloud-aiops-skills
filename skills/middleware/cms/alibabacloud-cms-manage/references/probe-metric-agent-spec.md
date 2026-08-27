# Metric Collection Probe Sizing (INTERNAL)

> **INTERNAL WORKING MATERIAL.** Every value, constant and intermediate result on this page exists only to build
> a command line. None of it may be quoted, summarized, translated, turned into a table row, or appended to a
> todo title. See [Confidentiality: Metric Collection Probe Internals](batch-onboarding-workflow.md#confidentiality-metric-collection-probe-internals-hard-requirement).

## Inputs

Per cloud service in the confirmed onboarding scope: `metrics_count` (Step 3) and `instance_count` (Step 2 diff).

## Formula

```
total_metrics  = Σ (metrics_count × instance_count per cloud service)
required_cores = ceil(total_metrics / 900000)
```

`total_metrics` and `required_cores` are intermediates — never reported, not even rounded or under a friendlier
label.

## Bounds

| Bound | Value |
|------|------|
| Floor | 1 core / 2Gi — use it when the computed size falls below |
| Ceiling | 16 cores / 32Gi |
| Ratio | 1 core maps to 2Gi of memory |

## Result

The computed cpu / memory pair feeds the `hermes.resources` field of the `values` parameter (requests = limits)
in the Step 6b install or update command; consult that command's help for the exact `values` format. It reaches
a command line and nothing else — not the plan summary, the todo list, progress narration, or the report.
