# Agentloop AgentSight (`input_agentsight`)

Host eBPF runtime collection for Agentloop. Maps the SLS console confirm-access flow (`obviz-integration` / `ai-runtime-ebpf`) onto `aliyun sls` pipeline APIs.

This is **not** OBI and **not** OTLP Metrics/Traces. The collector runs AgentSight eBPF on the host, filters processes by cmdline/domain, and writes runtime events to the current Project's `ebpf-event`.

## Coverage (this skill)

| Item | Status |
|---|---|
| `input_agentsight` in validator allowlist | yes (was missing; only `input_file` / `input_container_stdio`) |
| Scenario `host_agentsight` (alias `agentloop`) | yes, host-only |
| Fixed names + empty `ProbeConfig` default | yes, `assets/pipeline-templates/host_agentsight.json` |
| Probe lists + masking variant | yes, `assets/pipeline-templates/host_agentsight_probe_mask.json` |
| Console `EnableProductLog.json` / `createNewV2.json` | **out of channel** — this skill uses `aliyun sls` only, never private console ajax |

## Fixed names (do not invent)

| Resource | Value |
|---|---|
| Protocol id | `loongcollector-runtime` |
| Scenario | `host` / `host_agentsight` only — never docker/k8s |
| Logstore | `ebpf-event` |
| ProductLog | `agentloop.ebpf_event` |
| Config name | `runtime-ebpf-agentsight-config` |

Project comes from the user's AgentSpace / confirmed `--project`. Machine group is **user-selected or user-created**; this skill does not generate a group name.

Pilot "log resource initialization" enables `ebpf-event` but does **not** create this collection config.

## Classify / inputs

- Signals: Agentloop, AgentSight, `input_agentsight`, eBPF Runtime, `ai-runtime-ebpf`, `ebpf-event`, `runtime-ebpf-agentsight-config`.
- Capability: `config.create` when Project/Logstore/group exist; `onboarding.cloud` only if the group itself must be created. Never `config.modify` for first-time confirm-access.
- Required: `region`, `project`, `machine_group` (name). Confirm identify type only when creating a group.
- Optional: probe form (`cmdline_whitelist` / `cmdline_blacklist` / `domains` / `verbose` / `log_path` / `desensitize`). Default all empty, masking off.
- Collector: Linux host, kernel `>= 5.10`, `machines[].binary` **`>= 3.3.9`** (SLS help). Plugin in-tree still says 3.3.4 — cloud jobs follow 3.3.9. Unknown version → ask. Windows / container / kernel too old → stop.

## Cloud mapping (console ajax → CLI)

Console confirm-access is three POSTs. This skill does the equivalent with public `aliyun sls` commands. Do **not** call `/console/ProductLog/EnableProductLog.json` or `/config/ajax/createNewV2.json`.

| Console step | Skill step | Notes |
|---|---|---|
| `EnableProductLog` `{product: agentloop.ebpf_event, logstore: ebpf-event, isOverwrite: false}` | `get-log-store --logstore ebpf-event` | If missing → `[BLOCKED: RESOURCE_RESOLUTION_FAILED]` and tell the user to Enable ProductLog `agentloop.ebpf_event` (Pilot usually did this). Do not silently `create-log-store`; a bare logstore is not ProductLog. |
| `createNewV2` | `get-logtail-pipeline-config` then maybe `create-logtail-pipeline-config` | `ConfigAlreadyExist` = success, **never overwrite**. |
| `applyConfig` `{ConfigName, NewGroupName}` | `apply-config-to-machine-group` | If `get-applied-configs` already lists `runtime-ebpf-agentsight-config`, lock: skip create and skip apply. |

Render/validate:

```bash
SKILL_SESSION_ID=<session-id> python3 scripts/render_pipeline.py --input task.json
SKILL_SESSION_ID=<session-id> python3 scripts/validate_pipeline.py --file rendered.json --collector-version <v>
```

Default `task.json`:

```json
{
  "scenario": "host_agentsight",
  "config_name": "runtime-ebpf-agentsight-config",
  "logstore": "ebpf-event",
  "probe": {}
}
```

Decoded pipeline (empty form — what confirm-access ships by default):

```json
{
  "configName": "runtime-ebpf-agentsight-config",
  "global": {},
  "inputs": [{ "Type": "input_agentsight", "ProbeConfig": {} }],
  "processors": [],
  "flushers": [{ "Type": "flusher_sls", "Logstore": "ebpf-event" }]
}
```

`global` is `{}` (not `TopicType: machine_group_topic`). `ProbeConfig: {}` means the collector injects its built-in cmdline whitelist and HTTPS hosts.

## ProbeConfig mapping

`buildProbeConfigPayload` only emits non-empty fields. Filling a list **replaces** that list entirely (no merge with built-ins).

| Form | Wire field | Rule |
|---|---|---|
| Cmdline whitelist | `CmdlineWhitelist` | `[{AgentType, Args}]`. Keep a row only when both `AgentType` and `Args` are non-empty. Empty `[]` is illegal — omit the field instead. |
| Cmdline blacklist | `CmdlineBlacklist` | Array of glob-string arrays, e.g. `[["ssh","scp"]]`. Higher priority than whitelist. |
| Domain whitelist | `Https` / `Http` | Starts with `:`, starts with a digit, or ends with `:\d+` → `Http`; else `Https`. Example: `api.openai.com` → Https; `:443` / `8080` / `127.0.0.1:8080` → Http. |
| Verbose / log path | `Verbose` / `LogPath` | Default omit. Emit `Verbose` only when `1`; emit `LogPath` only when non-empty. |
| Data masking | processors, not ProbeConfig | See below. |

Do not emit `EventStreamFormat` / `MessageDeltaOnly` / `RawHttpsFallback` unless the user explicitly set them (collector defaults: stream+delta on, raw HTTPS off). `RawHttpsFallback` needs inner `main` + `libagentsight >= 0.9.0` and writes **unmasked** bodies — never turn it on for Agentloop empty-form create.

Filled example: `assets/pipeline-templates/host_agentsight_probe_mask.json`.

## Masking processors

Default `processors` is empty. Masking on appends **exactly one** `processor_spl`. Type and Script are fixed; do not substitute `processor_desensitize_native`. Mode is the literal `buildin` (not `builtin`).

```json
{
  "Type": "processor_spl",
  "TimeoutMilliSeconds": 1000,
  "Script": "* | extend \"gen_ai.input.messages\" = mask(\"gen_ai.input.messages\",'[{\"mode\":\"buildin\",\"types\":[\"IP_ADDRESS\",\"EMAIL\",\"LANDLINE_PHONE\",\"CREDIT_CARD\",\"PHONE\",\"IDCARD\"],\"maskType\":\"placeholder\"}]') | extend \"gen_ai.output.messages\" = mask(\"gen_ai.output.messages\",'[{\"mode\":\"buildin\",\"types\":[\"IP_ADDRESS\",\"EMAIL\",\"LANDLINE_PHONE\",\"CREDIT_CARD\",\"PHONE\",\"IDCARD\"],\"maskType\":\"placeholder\"}]')"
}
```

`processor_spl` cannot mix with native/extended processors. This pipeline has no other processors.

## Idempotency (Agentloop exception)

Product behavior: existing config is a lock, not a conflict.

1. `get-applied-configs` already contains `runtime-ebpf-agentsight-config` → skip create and skip apply; report lock.
2. `get-logtail-pipeline-config` returns the object (or create returns `ConfigAlreadyExist` / `AlreadyExist`) → **do not update**, even if `ProbeConfig` differs. Emit `[Idempotent-Skip] create-logtail-pipeline-config skipped; verified via get-logtail-pipeline-config that runtime-ebpf-agentsight-config exists (Agentloop lock, no overwrite).`
3. Changing probe/mask on an existing config is a separate `config.modify` after a new confirmation — never piggy-backed on confirm-access.

This overrides the generic `EXISTING_RESOURCE_CONFLICT` rule **only** for this fixed config name during Agentloop create/bind.

## Execute order (after approval)

1. `get-project` / `get-log-store ebpf-event` / `get-machine-group` (existence).
2. `list-machines` → version gate `>= 3.3.9`. Confirm Linux kernel `>= 5.10` with the user in prose if host evidence is missing.
3. `get-applied-configs` → if already bound, lock and go to Verify.
4. `get-logtail-pipeline-config --config-name runtime-ebpf-agentsight-config` → exist: skip create; missing: `--cli-dry-run` then `create-logtail-pipeline-config`.
5. If not bound: `--cli-dry-run` then `apply-config-to-machine-group`.
6. Do not auto-rollback a later step if an earlier step succeeded; report each result (matches console: a later-step failure does not roll back earlier successes).

Create flags: `--project` `--config-name` `--inputs` `--flushers` `[--processors]` `--global '{}'`. Strip `_`-prefixed template keys before send.

## Verify (U1–U6)

- U1: `get-logtail-pipeline-config` — `inputs[0].Type=input_agentsight`, `flushers[0].Logstore=ebpf-event`.
- U2: both binding directions for this config name + the user-selected group.
- U4: heartbeat; `binary` >= 3.3.9.
- U5/U6: `get-logs-v2` on `ebpf-event`. Dotted fields need double quotes. Do not `select *`. Pair request/response by `gen_ai.turn.id` / `gen_ai.step.id`, **not** by assuming a shared `event.id`. Example:

```text
* | select __time__, "event.name", "gen_ai.agent.type", "gen_ai.session.id" limit 5
```

Do not rename `gen_ai.*` fields. Index is owned by ProductLog Enable; do not invent a coupled index update on first create.

## Out of scope

- OOS / cloud assistant install of LoongCollector (lifecycle).
- Console ProductLog dashboards, OBI, Kubernetes AgentSight.
- Overwriting `runtime-ebpf-agentsight-config` because probe defaults “look empty”.
