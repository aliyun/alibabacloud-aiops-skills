# iofsstat (IO Throughput / Disk Statistics Dashboard)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

Runs **`sysak iofsstat`** on the target instance and returns JSON for **disk/block-device IO statistics dashboard** analysis.

## When to Use (Agent)

- Need a high-level **disk/block IO dashboard** before deciding whether to run **iodiagnose**.

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID | — | `--instance` |
| `timeout` | string/int | no | sampling duration (seconds) | `"15"` | <=0 becomes 15; **>30 is capped to 30** |
| `disk` | string | no | block device name (e.g. `vda`) | `""` | non-empty appends `-d <disk>` |

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
./scripts/osops.sh io iofsstat --channel ecs \
  --region cn-hangzhou --instance i-xxx \
  --params '{"timeout":"20","disk":"vda"}'
```
