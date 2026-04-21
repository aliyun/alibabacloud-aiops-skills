# delay (Scheduling Latency / nosched Diagnosis)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.  
> OpenAPI `service_name` is `delay`; implementation uses **`sysak -g nosched`** (scheduler delay, not ICMP RTT).

## Overview

- **Realtime** (`is_history` = 0): runs **`sysak -g nosched`** with **`threshold`** (ms) and **`duration`** (s).
- **Historical** (`is_history` != 0): timestamp-based query (**<= 1 hour and within 7 days**).

## When to Use (Agent)

- Scheduling latency, runqueue pressure, and nosched-observable stalls.
- Do **not** treat this as the sole method for ICMP network latency.

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID (strip `:port`) | — | `--instance` |
| `is_history` | int | no | historical mode toggle | `0` | non-zero enters historical query |
| `anomaly_start` / `anomaly_end` | int | conditional | Unix timestamps | `0` | required in historical mode |
| `duration` | int | no | realtime collection duration in seconds | `20` | **must be <= 60** |
| `threshold` | int | no | threshold in ms | `20` | passed to `nosched -t` |

\* CLI `--region` / `--instance` can be merged into params; for current ECS instance, metadata can auto-fill them.

## Platform Constraints

| Item | Value |
|----|-----|
| support_channel | **ecs \| eflo** |
| support_mode | **node only** |
| minimum sysak version | **`3.6.0-1`** |

## Recommended Usage

Run in `sysom-diagnosis/` (skill root):

```bash
./scripts/osops.sh load delay --channel ecs \
  --region cn-hangzhou --instance i-xxx \
  --params '{"duration":30,"threshold":20}'
```
