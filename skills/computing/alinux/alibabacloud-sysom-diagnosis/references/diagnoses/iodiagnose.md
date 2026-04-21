# iodiagnose (Deep IO / ioMonitor Diagnosis)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

Runs **`sysak ioMonitor`** on target instances (with fixed yaml, log paths, and diagnosis switches) for deep collection of **IO latency**, **iowait**, and **burst** behavior.

## When to Use (Agent)

- Slow IO / high iowait scenarios that require one-click ioMonitor deep collection (typically after iofsstat overview).

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID | — | `--instance` |
| `timeout` | string/int | no | ioMonitor collection duration (seconds) | `"30"` | invalid/non-positive -> 30; **max 300**; overflow falls back to 30 |

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
./scripts/osops.sh io iodiagnose --channel ecs \
  --region cn-hangzhou --instance i-xxx --params '{"timeout":60}'
```

For long collections, increase outer `--timeout` (polling total timeout) as well.
