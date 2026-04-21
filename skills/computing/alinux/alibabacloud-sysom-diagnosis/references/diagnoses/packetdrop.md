# packetdrop (Network Packet Loss Diagnosis)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

- **Realtime** (`is_history` false, default): runs **`sysak -g rtrace --drop-unity`** on target instances.
- **Historical** (`is_history` true): performs offline analysis with server-side aggregated metrics (for example Prometheus-like data).

## When to Use (Agent)

- Packet loss, retransmission, NIC-side rtrace clues, or historical time-window analysis (`is_history`).

## Complement with `memory memgraph`

This diagnosis does **not** cover full socket queue panorama or TCP memory composition. A normal `packetdrop` result does not exclude app backpressure causing Send-Q backlog or TCP-memory-related latency.  
If such clues appear, also run `memory memgraph --deep-diagnosis`. See [non-memory-routing.md](../non-memory-routing.md) and [memgraph.md](./memgraph.md).

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID (can include `:port`, implementation extracts host) | — | `--instance` |
| `is_history` | bool | no | use historical/offline analysis | `false` | set true with `anomaly_start`/`anomaly_end` |
| `anomaly_start` | number | conditional | historical start timestamp (seconds) | `0` | |
| `anomaly_end` | number | conditional | historical end timestamp (seconds) | `0` | |

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
./scripts/osops.sh net packetdrop --channel ecs \
  --region cn-hangzhou --instance i-xxx
```

Historical mode example: `--params '{"is_history":true,"anomaly_start":...,"anomaly_end":...}'`.
