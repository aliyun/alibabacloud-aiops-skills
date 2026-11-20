# Agentloop AgentSight (`input_agentsight`)

Host eBPF runtime collection for Agentloop. Maps the SLS console confirm-access flow (`obviz-integration` / `ai-runtime-ebpf`) onto `aliyun sls` pipeline APIs.

This is **not** OBI and **not** OTLP Metrics/Traces. The collector runs AgentSight eBPF on the host, filters processes by cmdline/domain, and writes runtime events to the current Project's `ebpf-event`.

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
- Collector: Linux host, kernel `>= 5.10`, `machines[].binary` **`>= 3.3.9`** (SLS help). Unknown version → ask. Windows / container / kernel too old → stop.

## Cloud mapping (console ajax → CLI)

Console confirm-access is three POSTs. This skill does the equivalent with public `aliyun sls` commands. Do **not** call `/console/ProductLog/EnableProductLog.json` or `/config/ajax/createNewV2.json`.

| Console step | Skill step | Notes |
|---|---|---|
| `EnableProductLog` `{product: agentloop.ebpf_event, logstore: ebpf-event, isOverwrite: false}` | `logstore get --logstore ebpf-event` | If missing → stop resource resolution and tell the user to Enable ProductLog `agentloop.ebpf_event` (Pilot usually did this). Do not silently `logstore create`; a bare logstore is not ProductLog. |
| `createNewV2` | `logtail-pipeline-config get` then `logtail-pipeline-config create` | `ConfigAlreadyExist` = success, **never overwrite**. |
| `applyConfig` `{ConfigName, NewGroupName}` | `logtail-pipeline-config apply-to-machine-group` | If both binding directions already match, skip apply; the create call still follows the Agentloop lock workflow below. |

Render/validate:

```bash
python3 scripts/loongcollector/render_pipeline.py --input task.json
python3 scripts/loongcollector/validate_pipeline.py --file rendered.json --collector-version <v>
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

Filled example: `references/loongcollector/assets/pipeline-templates/host_agentsight_probe_mask.json`.

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

Lock forbids **overwrite**, not Plan / HITL / the create call:

1. Still render with `scripts/loongcollector/render_pipeline.py` (empty `ProbeConfig`) and validate with `scripts/loongcollector/validate_pipeline.py`. Showing changes as a diff is recommended; `normalize_diff.py` supplies a normalized diff. Obtain user authorization before changing resources.
2. After confirm, still issue `--cli-dry-run` then `logtail-pipeline-config create`. If `machine-group get-applied-configs` already contains the name, still create (AlreadyExist is the lock) and skip apply only when both bind directions already match.
3. If get returns the object or create returns `ConfigAlreadyExist` / `AlreadyExist`,
   **do not update**, even if `ProbeConfig` differs. Record the existing config and
   the create result after the authorized create attempt.

4. Changing probe/mask on an existing config is a separate `config.modify` after a new confirmation — never piggy-backed on confirm-access.

This overrides the generic `EXISTING_RESOURCE_CONFLICT` rule **only** for this fixed config name during Agentloop create/bind.

## Execute order (after authorization)

Execution should follow this order:

1. `project get` / `logstore get ebpf-event` / `machine-group get` (existence).
2. `machine-group list-machines` → version gate `>= 3.3.9`. Confirm Linux kernel `>= 5.10` with the user in prose if host evidence is missing.
3. After authorization: `--cli-dry-run` then `logtail-pipeline-config create` even if get already saw the object (`AlreadyExist` = lock, do not update).
4. If not bound: `--cli-dry-run` then `logtail-pipeline-config apply-to-machine-group`. If both bind directions already match, skip apply and record the lock.
5. Do not auto-rollback a later step if an earlier step succeeded; report each result (matches console: a later-step failure does not roll back earlier successes).

Create flags: `--project` `--logtail-pipeline-config` `--inputs` `--flushers` `[--processors]` `--global '{}'`. Strip `_`-prefixed template keys before send.

## Verify (U1–U6)

- U1: `logtail-pipeline-config get` — `inputs[0].Type=input_agentsight`, `flushers[0].Logstore=ebpf-event`.
- U2: both binding directions for this config name + the user-selected group.
- U4: heartbeat; `binary` >= 3.3.9.
- U5/U6: `query` on `ebpf-event`. Dotted fields need double quotes. Do not `select *`. Pair request/response by `gen_ai.turn.id` / `gen_ai.step.id`, **not** by assuming a shared `event.id`. Example:

```text
* | select __time__, "event.name", "gen_ai.agent.type", "gen_ai.session.id" limit 5
```

Do not rename `gen_ai.*` fields. Index is owned by ProductLog Enable; do not invent a coupled index update on first create.

## Out of scope

- OOS / cloud assistant install of LoongCollector (lifecycle).
- Console ProductLog dashboards, OBI, Kubernetes AgentSight.
- Overwriting `runtime-ebpf-agentsight-config` because probe defaults “look empty”.
