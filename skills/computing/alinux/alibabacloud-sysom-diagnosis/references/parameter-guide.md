# Parameter Guide

Validate parameter shape before running remote diagnosis. Avoid collecting
credentials in the conversation.

## Global Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--region` | Remote cross-instance | Alibaba Cloud region ID | `cn-hangzhou` |
| `--instance` | Remote cross-instance | ECS instance ID | `i-bp1cg751dz3lssnbd14a` |
| `--scope` | No | Target scope, defaults to `ecs` | `ecs` |

When running on the target ECS instance, sysom-osops can auto-detect both values
from ECS metadata. For diagnosing another instance, use both flags together.

## Mode Summary

| Mode | Description | Credential required |
|------|-------------|---------------------|
| Local memory classify | Reads local Linux state and returns an Agent envelope | No |
| Remote self diagnosis | Diagnoses the current ECS through SysOM backend | Yes |
| Remote cross-instance diagnosis | Diagnoses a different ECS by explicit region and instance | Yes |

## Memory Parameters

| Command | Parameter | Description |
|---------|-----------|-------------|
| `memory oom` | `--oom-at` | Select an OOM event near a user-provided timestamp |
| `memory oom` | `--time-start`, `--time-end` | Limit OOM event search to a user-provided window |
| `memory oom` | `--select`, `--event-id`, `--index` | Pivot to a different event when the user clearly identifies one |
| `memory filecache` | `--top` | Limit number of cached files in the report |
| `memory filecache` | `--sample-rate` | Adjust sampling rate when a full sample is too expensive |
| `memory filecache` | `--pod` | Scope cached-file attribution to a pod when the user provides it |
| `memory javamem` | `--pod` | Scope Java analysis to a pod when the user provides it |
| `memory javamem` | `--pid` | Target Java PID when known (required for profiling follow-up) |
| `memory javamem` | `--duration` | Profiling duration in **minutes** (`0` = snapshot only; common `3`/`5`/`10`, max `10`). See `references/java/memory/profiling-playbook.md` |
| `memory memgraph` | `--pod` | Scope memory landscape to a pod when the user provides it |
| `memory memgraph` | `--enable-socket` | Include socket buffer and socket holder attribution when socket pressure is visible |
| `memory memcgoffline` | `--max-files`, `--max-items` | Bound offline-cgroup scan output size |
| `memory memcgoffline` | `--cgroup-path` | Narrow analysis to a cgroup already named by SysOM output |
| `memory memcgoffline` | `--verbose` | Toggle detailed output mode (enabled by default) |
| `memory memleak` | `--type` | Choose leak class `slab`/`page`/`vmalloc`/`percpu` (default vmalloc) per the kernel-hidden evidence |
| `memory memleak` | `--interval` | Sampling window in seconds for `slab`/`page`/`percpu` (ignored for the `vmalloc` snapshot) |

`memory javamem` is deprecated in favor of `java analyze --type memory` (see
`references/deep-actions.md`); its parameters stay listed only for sessions
already using it. Route new Java memory work through the `java` domain.

## IO, Load, and Network Parameters

These commands accept **no domain-specific parameters**. Only the global
parameters above (`--region`, `--instance`, `--scope`) apply:

| Domain | Commands | Accepted parameters |
|--------|----------|---------------------|
| IO | `io iodiagnose`, `io iofsstat` | Global only |
| Load | `load delay`, `load loadtask` | Global only |
| Network | `net packetdrop`, `net netjitter` | Global only |

Collection window and sensitivity are decided by the backend; there is no
`--duration`, `--threshold`, `--timeout`, or `--disk` flag on these commands.
When the user supplies a time window or threshold for these domains, carry it in
the narrative interpretation instead of passing it as a flag.

## Unknown Parameters Fail Silently

Passing a flag a command does not define makes the CLI exit non-zero with
**empty stdout and empty stderr** — no envelope and no error message. Never
invent a flag: use only the parameters listed above, and confirm with
`sysom-osops <group> <command> --help` when unsure. See the empty-output rule in
`SKILL.md` for how to recover when it happens.

`--help` is reliable for checking the flags of a command that is already
registered, but it is not a capability inventory: an unregistered deep command
prints its domain group's help instead. If that happens, follow the help-text
rule in `SKILL.md` — it is a credential/catalog problem, not a missing feature.

Use optional parameters only to honor user-provided scope or to fill a missing
entity identified by the envelope.
