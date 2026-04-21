# memgraph (Memory Dashboard / Memory Panorama)

> Parameter notes are consolidated from SysOM diagnosis scripts and OpenAPI behavior.

## Overview

Runs SysOM memgraph collection on the target instance and returns **`memgraph.json`** for memory-panorama analysis. It covers **system/app memory composition**, and in some versions also includes **TCP memory / socket queue** perspectives.

## When to Use (Agent)

- Need **global memory distribution and composition**, or suspect **TCP/socket queues** contributing to memory pressure.
- User reports latency/stalls and `ss` shows high Send-Q/Recv-Q: include **`memory memgraph --deep-diagnosis`**.
- OOM investigation path requires memgraph outputs (related to **oomcheck** data path).

## `params` Fields (JSON object, passed as string in InvokeDiagnosis)

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region ID | — | can be merged by CLI `--region` |
| `instance` | string | yes* | ECS instance ID or target identifier | — | can be merged by CLI `--instance` |
| `pod` | string | no | Pod name (container scenario) | `""` | non-empty appends `-p <pod>` |
| `profiling_on` | bool | no | enable profiling | `false` | effective in higher versions |
| `pid` | string/int | no | process PID | `null` | used with `profiling_on` |
| `duration` | int | no | profiling duration in **minutes** | `0` | `0` means no profiling append |

\* In **sysom-diagnosis** skill root, when CLI merges `--region` / `--instance` from metadata or command line, JSON can omit both.

## Platform Constraints

| Item | Value |
|----|-----|
| support_channel | **all** |
| support_mode | **all** (`node` / `pod`) |
| minimum version | common node baseline **`3.6.0-1`** |

## Recommended Usage

Run in **sysom-diagnosis skill root** (where `scripts/osops.sh` exists):

```bash
cd <sysom-diagnosis> && ./scripts/osops.sh memory memgraph --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx --timeout 300
```

If classification is uncertain, use **`memory classify --deep-diagnosis`**.  
For complex profiling, use `--params-file`; increase `--timeout` for long-running tasks.
