# loadtask (System Load Diagnosis)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

Runs **`sysak -g loadtask`** on target instances, reads `summary.json` plus temporary logs, and analyzes **high load average**, **CPU queueing**, and **load-driving tasks**.

## When to Use (Agent)

- High load average, CPU queueing, or load-task analysis scenarios.
- Must go through `./scripts/osops.sh load loadtask ...` to trigger SysOM `InvokeDiagnosis`; do not replace with generic ECS diagnostics or manual RunCommand collection.

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID | — | `--instance` |

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
./scripts/osops.sh load loadtask --channel ecs \
  --region cn-hangzhou --instance i-xxx --timeout 300
```
