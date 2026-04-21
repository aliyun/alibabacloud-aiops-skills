---
name: alibabacloud-sysom-diagnosis
version: 1.14.0
description: Perform deep Linux diagnostics for memory, network, IO, and load issues. Use when symptoms include high/insufficient memory, OOM/oom-killer, Java memory pressure, and memory panorama analysis (including socket queue and TCP memory views); packet loss or latency jitter (complements memgraph); disk statistics and slow IO; scheduling delay and system load. Outputs a structured diagnostic envelope for automated follow-up runs.

layer: application
category: os-ops
lifecycle: operations

tags:
  - os-ops
  - sysom
  - diagnosis
  - ecs
  - memory
  - oom
  - oom-killer
  - low-memory
  - kernel-logs
  - io
  - network
  - load

status: beta
---

# SysOM Diagnosis (sysom-diagnosis)

Run diagnostics with **`./scripts/osops.sh`** under **`sysom-diagnosis/`** (skill root). stdout is a **JSON envelope**. By default it performs a **local quick check without cloud invocation**; remote deep diagnosis is triggered by **`--deep-diagnosis`** (memory domain) or **`io`/`net`/`load` subcommands**, with built-in environment checks.

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> Then [MUST] run `aliyun plugin update` to ensure local plugins are up-to-date.
>
> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sysom-diagnosis"
> ```
>
> At the **end** of the workflow (after success or failure):
> **[MUST] Disable AI-Mode** — AI-mode must be disabled after skill execution completes.
> ```bash
> aliyun configure ai-mode disable
> ```

## Core Agent Behaviors

1. **Local first**: run memory quick checks first; do not ask for region/instance by default.
2. **Intent routing**:
   - **Memory domain**: high usage/panorama → `memgraph`; OOM/oom-killer → `oom`; Java → `javamem`; unknown → `classify`. See [memory-routing.md](./references/memory-routing.md).
   - **Non-memory domain**: IO/network/load → use corresponding `io`/`net`/`load` subcommands and go directly to remote deep diagnosis. See [non-memory-routing.md](./references/non-memory-routing.md).
   - **Hard constraint for remote deep diagnosis**: for `--deep-diagnosis`, `io/*`, `net/*`, and `load/*`, SysOM `InvokeDiagnosis` must be triggered via `./scripts/osops.sh`; do not degrade to generic ECS diagnostics APIs or manual `Ecs.RunCommand`/Cloud Assistant collection (`top`/`ps`/`iostat`) as replacements.
3. **Follow envelope instructions**: always read `agent.summary` and execute `agent.next`. Quick output is signal detection only. If `agent.next` contains a command, execute it before summarizing to the user.
4. **Envelope is source of truth**: base conclusions on envelope `data`; no extra ad-hoc collection is needed.
5. **Latency + socket queue backlog**: if `net netjitter`/`net packetdrop` has been run and looks normal but `ss` shows high Send-Q/Recv-Q, cross-check with `memory memgraph --deep-diagnosis`.

For full conventions (execution directory, credential safety, precheck noise reduction, etc.), see [agent-conventions.md](./references/agent-conventions.md).

## Envelope Output

CLI stdout is a JSON envelope (`format: sysom_agent`, `version: 3.4`). The agent directly consumes `agent.summary` (summary), `agent.findings` (key metrics), and `agent.next` (next-step command, executed with Bash in the skill root). Business payload is in `data.routing`, `data.local`, and `data.remote`. See [output-format.md](./references/output-format.md).

### Precheck / Authentication Failure

On authentication failure, the envelope includes `data.remediation` (standalone precheck) or `data.precheck_gate.remediation` (deep-diagnosis merged flow). Guide users according to envelope instructions. See [agent-conventions.md](./references/agent-conventions.md).

## Subcommand Quick Reference

### Memory Domain

| Subcommand | Capability | Reference |
|--------|------|------|
| `memory memgraph` | Memory panorama/dashboard, including TCP memory and socket queues | [memgraph.md](./references/diagnoses/memgraph.md) |
| `memory oom` | OOM / oom-killer diagnosis | [oomcheck.md](./references/diagnoses/oomcheck.md) |
| `memory javamem` | Java memory diagnosis | [javamem.md](./references/diagnoses/javamem.md) |
| `memory classify` | Comprehensive classification (fallback when uncertain) | Routing: [memory-routing.md](./references/memory-routing.md) |

### IO Domain

| Subcommand | Capability | Reference |
|--------|------|------|
| `io iofsstat` | IO dashboard (disk statistics) | [iofsstat.md](./references/diagnoses/iofsstat.md) |
| `io iodiagnose` | Deep IO analysis (slow IO, latency) | [iodiagnose.md](./references/diagnoses/iodiagnose.md) |

### Network Domain

| Subcommand | Capability | Reference |
|--------|------|------|
| `net packetdrop` | Packet loss (rtrace) | [packetdrop.md](./references/diagnoses/packetdrop.md) |
| `net netjitter` | Jitter (latency fluctuation) | [netjitter.md](./references/diagnoses/netjitter.md) |

### Load Domain

| Subcommand | Capability | Reference |
|--------|------|------|
| `load delay` | Scheduling delay (nosched) | [delay.md](./references/diagnoses/delay.md) |
| `load loadtask` | System load | [loadtask.md](./references/diagnoses/loadtask.md) |

## Quick Start

```bash
cd <sysom-diagnosis>
./scripts/osops.sh memory classify                                          # local classification
./scripts/osops.sh memory memgraph                                          # local memory panorama
./scripts/osops.sh memory memgraph --deep-diagnosis --channel ecs --timeout 300  # remote memory deep diagnosis
./scripts/osops.sh io iofsstat --channel ecs --timeout 300                  # IO dashboard
./scripts/osops.sh net packetdrop --channel ecs --region cn-hangzhou --instance i-xxx  # packet loss diagnosis
./scripts/osops.sh load delay --channel ecs --params '{"duration":30}'      # scheduling delay
```

For other instances, add `--region <id> --instance <i-xxx>`. For first-time setup, run `./scripts/init.sh`.

## Three Remote OpenAPI Requirements

| Requirement | Description |
|------|------|
| Identity | AK/SK or instance RAM Role |
| Policy | `AliyunSysomFullAccess` |
| Activation & SLR | Activate SysOM in console; SLR details: [service-linked-role-subaccount.md](./references/service-linked-role-subaccount.md) |

## Key Path Index

| Need | Document |
|------|------|
| Memory intent → subcommand mapping | [memory-routing.md](./references/memory-routing.md) |
| IO/network/load routing | [non-memory-routing.md](./references/non-memory-routing.md) |
| Remote invocation contract / CLI options / metadata | [invoke-diagnosis.md](./references/invoke-diagnosis.md) |
| Permissions / credentials / precheck | [permission-guide.md](./references/permission-guide.md) → [openapi-permission-guide.md](./references/openapi-permission-guide.md) |
| Envelope output format | [output-format.md](./references/output-format.md) |
| Agent behavior conventions | [agent-conventions.md](./references/agent-conventions.md) |
| Params fields per diagnosis | [diagnoses/README.md](./references/diagnoses/README.md) |
