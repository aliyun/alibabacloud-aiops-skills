# InvokeDiagnosis (Contract, CLI, and Preconditions)

> This document explains the **InvokeDiagnosis** contract, **local/remote** conventions, and **CLI options**.  
> The main agent path is `memory ... --deep-diagnosis`. For diagnosis-specific `params`, see [diagnoses/](./diagnoses/).

**Permissions and activation**: before remote OpenAPI calls, the remote path runs the same environment checks as `osops precheck`. You may also run precheck independently. See [openapi-permission-guide.md](./openapi-permission-guide.md).

**Local first**: unless users explicitly ask for remote diagnosis, start with local quick checks (see [memory-routing.md](./memory-routing.md)). The "target scope" section below applies to remote deep diagnosis only.

## Diagnosis Target Scope (Required Before Remote Deep Diagnosis)

Before every remote deep diagnosis (`memory ... --deep-diagnosis`), ask users to confirm target scope:

| User choice | CLI behavior | Notes |
|----------|--------|------|
| **A — Current instance** | Omit `--region` / `--instance`; CLI auto-fills from metadata | Agent should not curl metadata manually to inject params |
| **B — Remote instance** | User must provide `--region` and `--instance` | Do not pretend remote diagnosis by using local metadata |

For retries or diagnosis-item switches, keep the same rule: omit both args for current instance; keep user-provided region/instance for remote.

## Request Body Structure (`InvokeDiagnosis`)

| Field | Description |
|------|------|
| `service_name` | String, diagnosis type, must match a key in OpenAPI `diagnosis_item_config.items` |
| `channel` | String, currently usually **`ecs`** (same as CLI `--channel ecs`) |
| `params` | **String** containing **JSON text**. After deserialization it is an object and usually includes **`region`** and **`instance`** for ECS targeting. Diagnosis-specific fields are documented under [diagnoses/](./diagnoses/) |

When forwarded through OpenAPI `invoke_diagnosis`, backend merges **`uid`** into **`params`** from request context, so you usually do not need to set it manually.

**Preconditions**: target ECS must be running with Cloud Assistant installed; diagnosis authorization must be completed in **SysOM / ECS consoles** for target instances (do not use deprecated OpenAPI authorization endpoints); account side should include service-linked roles such as **AliyunServiceRoleForSysom**.

## Routing Hard Constraints (Evaluation Critical)

- Remote diagnosis conclusions must come from SysOM `InvokeDiagnosis` / `GetDiagnosisResult`.
- Do not replace SysOM diagnosis with generic ECS diagnostics APIs or manual `Ecs.RunCommand` / Cloud Assistant command collection (`top`/`ps`/`iostat`/`uptime`).

## CLI and Internal Invoke (Former `diagnosis invoke`)

Public entry: `./scripts/osops.sh memory <subcommand> --deep-diagnosis ...`

| Option | Description |
|------|------|
| `--region` / `--instance` | Merged into `params`; see metadata completion below |
| `--timeout` | Total polling wait for **GetDiagnosisResult**, default `300` seconds |
| `--poll-interval` | Poll interval seconds, default `1` |
| `--verbose-envelope` | Keep full `agent.summary` on success; default is compact to save tokens. Business payload remains in `data.remote` |

**On success**: check `data.routing`, `data.remote` (`remote.result`), and `agent.findings`.

**On failure**: `error.code` / `error.message` are standard business codes; environment failures may return a precheck-like envelope; business failures may include guidance such as `data.remediation`.

### Local Metadata Completion

If `--region` / `--instance` are not passed, CLI requests ECS metadata (`100.100.100.200`) for completion.  
If `error.code` is `Sysom.InvalidParameter` or `instance not found in ecs`, a common reason is account-instance mismatch (including cross-account). Passing precheck only means credentials can call APIs, not that instance ownership is aligned.

Metadata details: [metadata-api.md](./metadata-api.md).

## Params by Diagnosis Type

See [diagnoses/README.md](./diagnoses/README.md) and the corresponding `*.md`.

## Related Entries

- [SKILL.md](../SKILL.md) — capability overview table
- [openapi-permission-guide.md](./openapi-permission-guide.md) — permission and precheck
