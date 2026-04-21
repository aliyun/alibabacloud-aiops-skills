# Non-Memory Domains: IO / Network / Load Routing

This document complements [memory-routing.md](./memory-routing.md).  
`io`/`net`/`load` subcommands are direct entries to remote SysOM diagnosis and include built-in environment checks.

## Hard Constraints (Avoid Misrouting)

- In `io/*`, `net/*`, and `load/*` scenarios, diagnosis must go through `./scripts/osops.sh` to invoke SysOM remote diagnosis (`InvokeDiagnosis`).
- Do not replace diagnosis items with generic ECS diagnostics APIs or manual `Ecs.RunCommand`/Cloud Assistant commands (`top`, `ps`, `iostat`, `uptime`, etc.).

## Recommended Entries

Subcommand names match **`service_name`**. `--channel`, `--params`, `--region`, `--instance`, and polling options follow [invoke-diagnosis.md](./invoke-diagnosis.md).

| Subsystem | Subcommand | Reference |
|--------|--------|------|
| **`io`** | `iofsstat` | [iofsstat.md](./diagnoses/iofsstat.md) |
| **`io`** | `iodiagnose` | [iodiagnose.md](./diagnoses/iodiagnose.md) |
| **`net`** | `packetdrop` | [packetdrop.md](./diagnoses/packetdrop.md) |
| **`net`** | `netjitter` | [netjitter.md](./diagnoses/netjitter.md) |
| **`load`** | `delay` | [delay.md](./diagnoses/delay.md) |
| **`load`** | `loadtask` | [loadtask.md](./diagnoses/loadtask.md) |

Examples:

```bash
./scripts/osops.sh io iofsstat --channel ecs --timeout 300
./scripts/osops.sh net packetdrop --channel ecs --region cn-hangzhou --instance i-xxx
```

## Cross-check with `memory memgraph` (Latency / Socket Queues)

`net packetdrop` / `net netjitter` cover packet loss, rtrace, and jitter thresholds, but they do **not** provide the SysOM memgraph perspective for full-memory view + socket queue + TCP memory usage.

If users report **latency/stalls** and local `ss` already shows **Send-Q / Recv-Q backlog**, you should still run:

```bash
./scripts/osops.sh memory memgraph --deep-diagnosis --channel ecs --timeout 300
```

For current-instance ECS, omit `--region` / `--instance`; same rule as [invoke-diagnosis.md](./invoke-diagnosis.md).  
See [memgraph.md](./diagnoses/memgraph.md) for details.
