# netjitter (Network Jitter Diagnosis)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

- **Realtime** (`is_history` = 0/false): runs **`sysak rtrace --jitter-unity`** with **`threshold`** (ms) and **`duration`** (s).
- **Historical** (`is_history` != 0): queries local tables by **`anomaly_start`/`anomaly_end`** (window **<= 1 hour and within 7 days**).

## When to Use (Agent)

- Network jitter and latency fluctuation scenarios.

## Complement with `memory memgraph`

This diagnosis does **not** collect socket send/receive queue backlog or TCP-memory composition from memgraph.  
If `netjitter` appears normal but users still report latency and `ss` shows high Send-Q/Recv-Q, run `memory memgraph --deep-diagnosis`.  
See [non-memory-routing.md](../non-memory-routing.md) and [memgraph.md](./memgraph.md).

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID (strip `:port`) | — | `--instance` |
| `is_history` | int/bool | no | historical mode toggle | `0` | non-zero enters historical query |
| `anomaly_start` | int | conditional | start Unix timestamp | `0` | required in historical mode |
| `anomaly_end` | int | conditional | end Unix timestamp | `0` | required in historical mode |
| `duration` | int | no | realtime collection duration in **seconds** | `20` | **must be <= 60** |
| `threshold` | int | no | jitter threshold in **ms** | `10` | passed to `rtrace --jitter-unity -t` |

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
./scripts/osops.sh net netjitter --channel ecs \
  --region cn-hangzhou --instance i-xxx \
  --params '{"duration":30,"threshold":10}'
```
