# SysOM Diagnosis Index (by `service_name`)

Each **`*.md`** in this directory documents diagnosis-specific fields in `params` and recommended usage patterns (based on SysOM diagnosis scripts and OpenAPI behavior; if implementation is outside this package, production behavior is authoritative).

## Document Responsibilities (Avoid Duplication)

| Content | Read here |
|------|--------|
| **Current/remote target selection, InvokeDiagnosis request body, `region`/`instance`, metadata completion** | [invoke-diagnosis.md](../invoke-diagnosis.md) |
| **ECS metadata endpoints, common paths, IMDS** | [metadata-api.md](../metadata-api.md) |
| **precheck, credentials, three requirements, scenario matrix A-K** | [openapi-permission-guide.md](../openapi-permission-guide.md) |
| **Field tables for each `service_name` in this directory** | Index below → corresponding `*.md` |

## Maintenance Conventions

- OpenAPI full diagnosis items are authoritative on the Alibaba Cloud SysOM service side (this package does not embed server `config` files).
- `service_name` coverage in this skill follows [SKILL.md](../SKILL.md) and the index below. If server exposes additional items, console and OpenAPI are authoritative.
- Per-item docs should align with `service_scripts` implementation. If inconsistent with console text, prioritize code and online behavior.

### Working Directory for Commands

`cwd` conventions are documented in [agent-conventions.md](../agent-conventions.md).

## Category Index (Aligned with SKILL Table)

Capabilities are aligned with the overview table in [SKILL.md](../SKILL.md). Links below point to per-item `params` docs.

### Memory and Java / Go

| service_name | Document |
|--------------|------|
| memgraph | [memgraph.md](./memgraph.md) |
| oomcheck | [oomcheck.md](./oomcheck.md) |
| javamem | [javamem.md](./javamem.md) |
| gomemdump (if still available server-side; **not exposed in this skill CLI**) | [gomemdump.md](./gomemdump.md) |

### IO and Storage (CLI: `io`)

| service_name | Document |
|--------------|------|
| iofsstat | [iofsstat.md](./iofsstat.md) |
| iodiagnose | [iodiagnose.md](./iodiagnose.md) |

### Networking (CLI: `net`)

| service_name | Document |
|--------------|------|
| packetdrop | [packetdrop.md](./packetdrop.md) |
| netjitter | [netjitter.md](./netjitter.md) |

### Load and Scheduling (CLI: `load`)

| service_name | Document |
|--------------|------|
| delay | [delay.md](./delay.md) |
| loadtask | [loadtask.md](./loadtask.md) |

## Implementation Sources (Troubleshooting)

On SysOM diagnosis service side, each item is typically implemented by `*_pre.py` or similarly named scripts, and executed on instances through OpenAPI `invoke_diagnosis`.  
If source code is outside this repository skill package, production behavior is authoritative.
