---
name: alibabacloud-loongcollector-ops
description: |
  Alibaba Cloud Simple Log Service (SLS) ingestion management for an already-deployed LoongCollector.
  Triggers: "SLS 日志采集接入", "修改采集配置", "SLS 机器组", "新建 Logtail Pipeline 采集配置", "Logtail Pipeline", "SLS Lens 查询", "无数据排查", "心跳异常", "SLS 采集权限排查", "Logtail", "iLogtail".
---

# LoongCollector Cloud-Side Ops

Turn natural-language collection-ops requests into executable, verifiable, rollbackable `aliyun sls` workflows for users operating **their own** Alibaba Cloud SLS resources.

**Architecture**: `SLS Project + Logstore + Index + MachineGroup + Logtail Pipeline Config + Config-MachineGroup binding + SLS Lens (CloudLens for SLS) run logs`

**Scope.** Assumes LoongCollector is **already installed and reporting heartbeat**. Covers:
- Cloud onboarding: Project / Logstore / Index / MachineGroup / Pipeline Config / binding.
- Config management: create, modify, apply, remove, data acceptance (U1-U6).
- Machine group management: IP / user-defined identity, members, heartbeat, version.
- SLS Lens: run-log query (`get-logs-v2`), topic/field contracts, version routing, degradation.
- Basic troubleshooting: no-data, heartbeat abnormal.

## Language and HITL Delivery Contract

**Hard language rule:** when the user's request is primarily Chinese, every user-facing message MUST use Simplified Chinese. This includes plans, clarification questions, confirmation questions and their answer options, reports, and error guidance. Product names, identifiers, CLI commands, JSON fields, error codes, and fixed status tags may remain English. Never switch the surrounding prose to English.

**Stable Chinese HITL subjects:** ask short, direct questions, and reuse the identical sentence whenever the same question comes up again, so re-asking never looks like a new question:

- Missing task scope: `请补充要执行的具体操作目标、地域和 SLS Project。`
- Missing Lens parameters: `请补充业务 Project、地域和查询时间范围。`
- Machine-group identity choice: `请选择机器组标识类型：IP 或 userdefined。`
- R2 approval (config update / non-create plan): `是否确认执行上述变更计划？请选择：确认执行或取消。`
- Create-and-bind approval (from-zero create, machine-group create+bind, pipeline create+bind): `是否确认创建上述资源并完成绑定？请选择：确认执行或取消。` Prefer this subject whenever the approved plan creates resources or bindings; do not invent alternate confirmation wording.
- Unbind approval: `是否确认将上述旧配置从机器组解绑？请选择：确认解绑或取消。`
- Permission recovery: `是否已完成所需 RAM 授权并允许重试？请选择：已授权或未授权。`
- Lens-entry fallback: `请提供 SLS Lens 服务日志的 Project 和 Logstore。`

Do not replace these with long English prose, bilingual tables, or newly invented status labels. Whenever you re-ask, reproduce the same short Chinese question verbatim after the required `[AWAITING: ...]` tag.

**Out of scope.** Installation, upgrade, rollback, uninstall, restart; Windows/ACK/self-built K8s deploy; CRD controller/operator management; advanced troubleshooting (delay, duplicate, parse failure, container filter, data loss/truncation). If the user asks for installation or lifecycle, state clearly that it is not covered by this skill and do not improvise host/SSH/kubectl execution.

---

## 1. Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3 (>= 3.3.5 recommended).
> - First install or major upgrade: `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - Routine update (CLI >= 3.3.5): `aliyun upgrade`.
> - See `references/cli-installation-guide.md`.

**Pre-check: SLS plugin required**
> [MUST] `aliyun configure set --auto-plugin-install true` then `aliyun plugin install --names aliyun-cli-sls` and `aliyun plugin update`.
> Collection subcommands are provided by the `aliyun-cli-sls` plugin (hyphenated subcommands such as `aliyun sls get-logs-v2`). Verify with `aliyun sls --help`.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** use `cat`, `less`, `head`, `tail`, `grep`, or any file-reading command on credential files (e.g., `~/.aliyun/config.json`, `~/.aws/credentials`). To check file existence use `ls` only — never display contents. Printing plaintext secrets is an immediate task failure and security incident.
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

Run `bash scripts/preflight.sh` to check CLI version, plugin, credential presence, and scope in one step. Full gate details: `references/prerequisites.md`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| (none for credentials) | — | Credentials come from `aliyun configure` profiles; never introduce AK/SK env vars in-session |
| `SKILL_SESSION_ID` | Injected at script run | Same 32-hex session id as `--user-agent`; set inline when invoking bundled scripts (see §4) |

---

## 2. RAM Policy

This skill uses the user's own identity and only touches resources they are authorized for. Permissions are layered ReadOnly / Operator / Destructive. Per-workflow RAM Actions are in `references/ram-policies.md` — do not default to broad `AliyunLogFullAccess`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

**Runtime detail (same gate, do not skip the three steps above):**
1. Report the missing RAM Action and `requestID`; output `[Error: permission]`. Reading `references/ram-policies.md` alone is **not** a successful diagnose call.
2. **Try** `ram-permission-diagnose` with the missing Actions and `requestID`. **FALLBACK:** if it is unavailable, output Action/`requestID`/RAM-console guide manually, then `[AWAITING: PERMISSION_CONFIRMATION]` and pause.
3. Do not retry the affected write (including `--cli-dry-run`) before confirmation.
4. **READ-PATH HARD STOP:** On 401/403/`Unauthorized`/`AccessDenied` for `get-project` / `get-machine-group` / `list-machines` / `get-log-store`, emit `[Error: permission]` with Action/`requestID`, then in the **same turn** ask exactly `是否已完成所需 RAM 授权并允许重试？请选择：已授权或未授权。`, and issue no further `aliyun sls` call that turn. If the user answers 未授权 or otherwise declines, emit `[BLOCKED: PERMISSION_REQUIRED] ...` and end.

On `Unauthorized`/`AccessDenied` from a **core write or its dry-run**: stop the current write, enter the §6 permission-recovery branch, and never switch account/profile or widen scope.

---

## 3. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|---|---|---|---|
| `region` | Required | SLS region id, e.g. `cn-hangzhou` | none |
| `project` | Required | Target SLS project | none |
| `logstore` | Conditional | Target logstore (create/onboarding/query) | none |
| `machine_group` | Conditional | Machine group name (bind/heartbeat) | none |
| `config_name` | Conditional | Logtail pipeline config name | none |
| `machine_identify_type` | Conditional | `ip` or `userdefined` | none |
| `machine_list` | Conditional | IP list or user-defined identifiers | none |
| `scenario` | Conditional | `host` / `docker` / `k8s` | none |
| `lens_project` / `lens_logstore` | Optional | SLS Lens entry when auto-discovery unavailable | none |

Never substitute placeholder/example values for a missing real resource. Missing `region`, `project`, or a scope-changing target → STOP and ask.

For a Chinese request with a missing `machine_identify_type`, ask exactly `请选择机器组标识类型：IP 或 userdefined。` using Chinese option descriptions. Do not emit a custom English status label or an English selection table.

---

## 4. Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun sls list-machines --project my-proj --machine-group my-group --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/validate_pipeline.py --file rendered.json

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent).

**Domain extension — ATOMIC CLOUD-CALL RULE (HARD):** Every tool invocation that calls SLS must contain exactly one direct `aliyun sls ...` command with literal, fully expanded parameter values, and the command must start with `aliyun sls`. Do not hide a cloud call behind shell variables, environment assignments, functions, aliases, wrapper scripts, loops, command substitutions, `eval`, pipes, or compound commands (`;`, `&&`, `||`). Compute timestamps or JSON in a separate local step, then place the resulting literals in the cloud command. This applies equally to verification and acceptance reads: no loops, no `cd …` prefix, no `$VAR` or `$(…)` substitution, including in `--from`/`--to` and JSON bodies. Never write cloud calls into a `.sh` file and run it; the command record is plain-text notes, not a runnable script. Local validators must receive what the command actually returned — save the real stdout to a file and pass that file; retyping or `echo`-ing an expected response is fabricated evidence. Generate the session ID with `python3 -c 'import secrets; print(secrets.token_hex(16))'` and validate `^[0-9a-f]{32}$`; never copy the example ID above into live commands.

---

## 5. Capability Router

Classify the request into exactly one capability, then load its `references/navigation.md` entry before acting. Do not load the whole knowledge base into context.

| Capability | Trigger | Required inputs | Adapters | Success state |
|---|---|---|---|---|
| `config.modify` | Change an existing config / parse / fields | region, project, config | `aliyun_sls`, local validator | config + index + data verified |
| `config.create` | Base resources exist, only create a config | region, project, logstore, machine_group, scenario | `aliyun_sls`, local validator | config exists, bound, has data |
| `onboarding.cloud` | Collector installed, wire up cloud side | region, project, logstore, machine_group, source | `aliyun_sls`, local validator | U1-U6 pass |
| `machine_group.manage` | Create/modify group, members, binding | region, project, group | `aliyun_sls` | object + relations match target |
| `lens.query` | Query collection alarms/status/metrics | business project, time range, lens entry | `aliyun_sls` | query complete with context |
| `troubleshoot.basic` | No data / heartbeat abnormal | region, project, optional logstore/config/group | `aliyun_sls`, Lens | root cause or single blocker |

Full router spec (`when_to_use` / `out_of_scope` / `entry_signals` / `success|blocked|failure_state`): `references/navigation.md`. Track multi-step work with the unified task object in `references/task-model.yaml`.

---

## 6. Execution State Machine

`Classify → Preflight → Observe → Plan → Approve → Execute → Verify → (Rollback)`

- **Classify**: pick capability, scenario (`host/docker/k8s`), management plane. Ask for scope-changing inputs; never guess. If the user names SLS / Log Service / 日志采集 / LoongCollector / Logtail without a concrete operation (create/modify/bind/query/troubleshoot), **stay in this skill**: clarify region, project/resource locator, and the intended operation before any cloud call; never improvise outside scope.

  **INTENT / PARAM CLARIFICATION STOP (hard):** Ask at most **one** clarifying question, in Chinese, using the applicable exact subject from the Language and HITL Delivery Contract: general scope `请补充要执行的具体操作目标、地域和 SLS Project。`; Lens `请补充业务 Project、地域和查询时间范围。`. If the user still gives no concrete values — undecided, wants only the checklist, or asks you not to run commands — **do not ask again**. In that same turn output a minimal checklist (region, Project/resource locator, operation goal; for Lens-only asks: business project or Lens entry + time range), put `[BLOCKED: MISSING_REQUIRED_INPUT]` on the final line, and end the turn — no further questions, cloud calls, Preflight, or Observe. Resume only when the user supplies concrete values.

  Project locator: exact user prefix/handoff only — at most one `list-project --project-name <prefix>`, then `get-project` on the resolved full name; a `list-project` hit alone never proves the target nor authorizes work on it. Never broaden/synthesize names. Zero matches → `[BLOCKED: RESOURCE_RESOLUTION_FAILED] …`; multiple → ask user to choose.
- **Preflight**: `scripts/preflight.sh` (CLI/plugin/credential/scope). On any hard-gate failure, output `[BLOCKED: PREFLIGHT_FAILED] gate=<gate>; <reason>` and stop.
- **Observe (read-only)**: Get current objects + bindings + heartbeat; save a snapshot. Read collector version **before** choosing plugins.
  **MANDATORY VERIFICATION COMMANDS:** existence is proven only by `get-project`, `get-machine-group`, and `get-log-store` (the last before any create/bind on that logstore). `list-machines` / `get-applied-configs` / `list-log-stores` prove heartbeat or binding, never existence. Enter create only after a `get-*` returns ResourceNotExist.
- **Plan**: build target objects. **MANDATORY CHECKPOINT:** every planned R2/R3/R4 resource or relation change (including Project, Logstore, MachineGroup, binding, and unbinding) MUST have a target JSON and an executed `scripts/normalize_diff.py` result; use `--kind auto` for non-config/index objects. Never substitute raw `diff`, visual inspection, or a handwritten diff. Exit code `3` means "valid diff contains changes", not failure. Config/index coupling uses this fixed order: snapshot config and index → validate the full target config with `scripts/validate_pipeline.py` → run `scripts/normalize_diff.py --kind config` → run `scripts/normalize_diff.py --kind index`. Exit code `1` from validation blocks the write. Do not enter Approve until every applicable mandatory script has executed successfully. Include impact, risk, rollback, and verification. `mode=plan` MUST NOT call write commands.
  **VALIDATION FAILURE HARD STOP:** if `scripts/validate_pipeline.py` returns exit code `1` or `status=invalid`, immediately output `[BLOCKED: VALIDATION_FAILED]` and end the turn. Do not run `--cli-dry-run`; do not execute any create/update/apply/remove/delete command; do not treat a server-side 4xx from an actual write as validation evidence. This rule overrides user approval and every later Execute step.
- **Approve**: HARD GATE. For every R2 operation (create resource, update config, apply/bind, create/update index) you MUST, before Execute, explicitly output the normalized diff, ask the user to confirm, and end the turn. Ask at most one confirmation question per turn. For a Chinese request it must be the applicable exact subject from the Language and HITL Delivery Contract, with Chinese options (`确认执行` / `取消`), never English ones. Only an explicit positive answer authorizes a write. R3: explicit impact confirmation. R4: second confirmation, restate resources.

  **DO NOT SKIP CONFIRMATION:** Automation, urgency, and complete parameters never waive this gate. While the answer is outstanding, the state is `[AWAITING: R2_CONFIRMATION]`: emit that tag with the confirmation question, end the turn, and wait for the user's next message.

  **HARD GATE CHECKLIST (Approve → Execute):**
  0. Ask only once the plan is real: `scripts/validate_pipeline.py` has passed on any config payload and `scripts/normalize_diff.py` has run for every planned write. Asking approval for a plan you have not validated and diffed is a gate failure.
  1. Nothing you produce yourself is an answer. If the turn ends without the user having stated a decision, output `[AWAITING: R2_CONFIRMATION]` with the identical question and wait.
  2. Never treat the original task wording, “parameters are complete”, or an already-rendered plan table as approval.
  3. Enter Execute only after the user explicitly answers yes/confirm/approve or equivalent.
  4. `--cli-dry-run` for any R2 write is part of Execute: it is **forbidden** before that explicit approval. Showing a plan without asking, then dry-running, is a gate failure.
  5. Violating this gate is a task failure.

  **NON-ANSWER RULE (hard stop):** A reply that defers the decision instead of making it — blank, "later", "not sure yet", or any equivalent — is not approval. In the same turn, restate in one line which resources and operation are still waiting, then re-ask the identical Chinese confirmation subject; a bare repeated question without that context, or a "take your time" soft-close with no question, both fail this rule. After three asks without a decision, emit `[BLOCKED: R2_CONFIRMATION_TIMEOUT]` as the sole content of that turn. Explicit reject/cancel → sole content `[CANCELLED: R2_CONFIRMATION_REJECTED]`. Full semantics: `references/risk-and-approval.md`.

  **TERMINAL-STATE HARD STOP:** Any `[BLOCKED: …]` / `[CANCELLED: …]` tag is the **final content of the current turn** — no further tools, dry-runs, writes, or Verify in that turn. Resume only with a fresh Plan + confirmation after the user re-opens the work.
- **Execute**: approved commands only, with `--user-agent` and §4 atomic rule. Always run `--cli-dry-run` as its own call before the real write, so a rejected request surfaces before anything mutates state. **Idempotency:** get before create/apply; if state matches, skip both dry-run and write, verify via get/list, and emit exact `[Idempotent-Skip] <create/apply-command> skipped; verified via <get/list-command> that state matches expectation.` in `Changes`. If get already proves target Project/Logstore shard/TTL, any `create-project`/`create-log-store` (incl. dry-run) is a task failure. On `AlreadyExist`, get+compare → matching Idempotent-Skip, or `[BLOCKED: EXISTING_RESOURCE_CONFLICT]` if mismatched.
  **Error recovery (≤3 retries / 4 total; keep `errorCode` + `requestID`):** Prefer `python3 scripts/classify_sls_error.py` and emit its `error_tag` **before** narration. Mapping: 400/`ParameterInvalid`→`[Error: parameter]` then fix+retry same API →`[RECOVERED: parameter_fixed]`; 429/`WriteQuotaExceed`→`[Error: throttling]` + backoff →`[RECOVERED: throttling_retry]`; 500→`[Error: internal]` + same-command retry →`[RECOVERED: internal_retry]`; 401/403→`[Error: permission]` then §2 Permission Failure Handling (Chinese ask: `是否已完成所需 RAM 授权并允许重试？请选择：已授权或未授权。`) →`[RECOVERED: permission_granted]` or `[BLOCKED: PERMISSION_REQUIRED]`. Dry-run failures use the same branch; real write only after dry-run succeeds.
- When `get-logs-v2` returns `meta.progress=Incomplete`, that is an incomplete query (not a transport success to treat as final): output `[Query: Incomplete] attempt=<n>/4`, then retry the identical request per §9.
- **Verify**: acceptance evidence must be re-read **after** Execute — every created or changed object through its own `get-*` (`get-log-store`, `get-machine-group`, `get-logtail-pipeline-config`, `get-index`), both binding directions, and `list-machines` for heartbeat. Observe-phase reads describe the old state and never count as acceptance. Bounded polling (15s × up to 4) against U1-U6. After every config create/update/bind or onboarding flow, **must** execute a business-logstore `get-logs-v2` acceptance query before the final answer — skipping it because “config already verified” is a task failure. Report observed count/progress; if no rows arrive, state an evidence-based reason such as no new source logs, heartbeat/binding failure, or unavailable source-side evidence. Never equate zero rows with successful delivery.
- **Rollback**: only from the pre-execution snapshot or declared inverse; never rebuild config from memory.

Input contract and stop conditions: `references/prerequisites.md`.

### Scope & adapter rules
- This skill executes **only** through `aliyun sls` + local validators. **No SSH / kubectl / docker exec** — if host-side evidence is required, state the limitation and describe in plain language what the user should check on the host (collector process running, identity file content, reporting region, account id). Do not emit host shell commands, and do not inspect local processes or install directories either: the collector runs on the user's hosts, never where this skill executes.
- Fixed within one request: account/profile, region, project, group, config. Switching scope requires a fresh confirmation.
- One management plane per config: API **or** CRD, never both. If double-write is detected, STOP (`references/pipeline-config.md`).

---

## 7. Risk, Approval & Rollback

| Level | Examples | Approval |
|---|---|---|
| R0 read | list/get, status, log query | auto |
| R1 local | schema validate, render, diff | auto |
| R2 reversible write | create resource, update config, apply/bind, create/update index | show diff + one confirmation |
| R3 high impact | remove/unbind, bulk changes | confirm after stating impact |
| R4 destructive | delete project/logstore/config/group | second confirmation, restate resources |

> **R2 confirmation is a hard gate.** Only an explicit affirmative answer authorizes execution; task wording is never implicit approval. Rejection and timeout use the exact terminal statuses in §6, and rollback is a new approval workflow. The §6 **TERMINAL-STATE HARD STOP** covers `[BLOCKED: PERMISSION_REQUIRED]` and every other terminal tag: once emitted, no further cloud write (including dry-run) until a fresh Plan + approval cycle completes.

Details, snapshot format, and rollback: `references/risk-and-approval.md`. Get before Update (Update is overwrite semantics — carry unchanged fields back). Get before Create (see §6 Execute — idempotent handling of `AlreadyExist`). New resources' rollback does not default to deletion.

---

## 8. Config / Index Coupling (hard rule)

When processors add, remove, or rename a field, you MUST: 1) generate the config diff **and** the corresponding index diff together; 2) present both diffs to the user in **one combined approval** and request a single confirmation; 3) after approval, run both direct dry-run calls first (`config dry-run` → `index dry-run`), then execute the two actual writes as **two consecutive standalone invocations** (`config write`, then immediately `index write`) with no other command, wait, status check, or pause between them. "Back-to-back" means two separate calls in a row — never join them with `&&`, `;`, or any other shell chaining; §4 forbids that and a chained failure leaves the pair half-applied. Never "update config now, add index later", and never split the two changes into two confirmations. If a dry-run fails, issue neither actual write. If the index write fails after the config write succeeded, the batch is incomplete: immediately re-issue the identical index command through the §6 error-recovery branch in the same turn, keep the original `errorCode`/`requestID`, and report both outcomes together — do not redesign the payload by guessing, and do not end the turn with the config updated and the index pending. If the backend auto-syncs the index, say so in the plan and in the same confirmation.
- `status`/`status_code`/`http_status` default to `long`; time/latency/bytes chosen by semantics.
- SLS has no `float` field-index type. Map a floating-point requirement (for example `request_time float`) to `double` and show that mapping in the index diff.
- JSON nested fields: declare parent `json` index or the flattened field index explicitly.
- Prefix change must update index field names and the acceptance query together.
- `processor_rename` is extended-only; JSON rename uses all-extended `processor_json` → `processor_rename` with plural `SourceKeys`/`DestKeys` (never `SourceKey`/`DestKey`/`processor_rename_native`). Index diff must drop old keys and add new ones; `http_status` defaults to `long`. Full examples: `references/index-coupling.md`.
- Use this exact Plan order: config/index snapshots → `scripts/validate_pipeline.py` on the full target config → `scripts/normalize_diff.py --kind config` → `scripts/normalize_diff.py --kind index`; raw `diff` is not acceptable.

**MANDATORY COMMAND MAPPING:** use Pipeline names only (`*-logtail-pipeline-config`, `get-applied-configs` / `get-applied-machine-groups`, `apply-config-to-machine-group` / `remove-config-from-machine-group`). Create flags: `--project-name` / `--logstore-name` / `--group-name`; read/bind: `--project` / `--logstore` / `--machine-group`. `update-log-store` needs both `--logstore` and `--logstore-name`. Never classic `get-config`/`get-logs`/`list-logstore` aliases; classic `inputDetail` configs → `[BLOCKED: CLASSIC_CONFIG_UNSUPPORTED]`. Commands in this mapping are already verified, so do **not** spend a call on `--help` for them. Index: existing→`update-index`, missing→`create-index`; `--line` uses `"chn": true`; a `text` key's `token` is a JSON **array** of delimiter strings — a concatenated string returns `IndexInfoInvalid: field token is of error format`. Full contracts: `references/cli-contracts.yaml`, `references/index-coupling.md`, `references/field-conventions.md`.

---

## 9. SLS Lens (CloudLens for SLS) run logs

Lens is the primary data source for basic troubleshooting. Run-log query itself uses public `aliyun sls get-logs-v2`.

**Entry discovery.** Verify the business project with `get-project` first — a missing business project explains an empty query and must not be reported as a Lens failure. Then run `get-logging` once on it (even if missing) and `python3 scripts/parse_lens_logging.py`. State machine: (1) usable entry → verify+use; (2) else user-supplied `lens_project`/`lens_logstore` → verify+use; (3) else ask once exactly `请提供 SLS Lens 服务日志的 Project 和 Logstore。`, end turn, wait — **never** reuse the business Project or invent `internal-diagnostic_log` on it; after the user answers, **must** run planned `logtail_alarm` + version-routed metric queries; (4) if user cannot provide → continue independent MG/config/business checks with `resource_status: Resource not found`, never fabricate “no alarms”.

**Forbidden**: STAROps/JWT/console cookie; guessing `log-service-{uid}-{region}`; Lens topics on the business Project after discovery failed; skipping the ask-once HITL.

**Query hard constraints** (full: `references/sls-lens-contracts.md`, `references/monitoring-queries.yaml`): no `select *`; version route `>=3`→`loongcollector_metric`, `<3`→`logtail_profile`/`logtail_metric` (must execute that `get-logs-v2` even on failure); `logtail_alarm` filters by `project` (never `config_name` in where); Incomplete → `[Query: Incomplete] attempt=<n>/4` + identical retry ≤4; report Lens project/logstore/topic/window/route/completeness.

---

## 10. Troubleshooting (no-data, heartbeat)

Fixed chain: `classify → heartbeat & version → config & binding → alarm/metric → business data → minimal fix → re-verify`.
- **HARD RULE — the diagnostic chain never stops early.** If a read-only step returns `ResourceNotExist`/`ProjectNotExist`/`LogStoreNotExist`/`LoggingNotExist`, execute every remaining independent diagnostic step. For Lens-dependent steps, follow §9 (ask once → wait → then query) after **any** entry-discovery failure — `LoggingNotExist` and `ProjectNotExist` alike, since the Lens entry lives in a different project and a missing business project says nothing about it. Reporting the Lens entry as not found without having asked for it is a task failure. Run each corresponding get/query command once (or after HITL supplies the entry), preserve its exact command and error code, record `resource_status: Resource not found` when applicable, and continue. Breaking off midway is a task failure. This continuation rule does not authorize writes and does not override the permission hard stop.
- Cloud visibility and collector-side evidence corroborate each other; do not substitute one for the other.
- No data: `get-logtail-pipeline-config --config-name` + `list-machines` + exact binding queries from §8 → `logtail_alarm` by project → `logtail_status` → version-matched pipeline topic → business logstore.
- Heartbeat abnormal: `list-machines` → `logtail_status`; if Lens is unavailable, name the host-side items the user should verify (collector process, reporting region, account id, `user_defined_id`) in prose — no shell commands, no host access.
- Every troubleshooting conclusion MUST emit the exact field-complete evidence lines defined in `references/troubleshooting.md` (`Heartbeat` / `Alarm` / `Collection`, plus `Binding` / `Pipeline` when those checks run). Use `N/A`/`unknown` instead of omitting a field; omitting any mandatory field is a task failure.

Playbooks and alarm handling cards: `references/troubleshooting.md`, `references/alarm-catalog.yaml`.

---

## 11. Output Contract

Every execution outputs at least: **Conclusion** (done/partial/blocked/rolled-back) · **Scope** (profile-id/region/project/logstore/group) · **Evidence** (key results; troubleshooting must reproduce every applicable §10 evidence line, including Binding/Pipeline) · **Changes** (normalized diff + actual actions, including every Idempotent-Skip note) · **Acceptance** (U1-U6 results) · **Rollback** (needed? executed? snapshot/inverse) · **Next step** (single blocker or next minimal action).

Do not print secrets, full command history, or unrelated logs; on audit request output redacted commands + request IDs (`scripts/redact_output.py`). On failure keep the original error code / request ID / redacted context; never fake success.

---

## 12. Global Rules

1. `aliyun sls` is the only execution channel. Prefer the exact validated mapping in §8 and `references/cli-contracts.yaml`; those commands are pre-verified, so do not re-check them with `--help`. Use `aliyun sls <cmd> --help` only for an undocumented command, before Plan. Never probe shorter aliases.
2. Use `get-logs-v2` (never the deprecated `get-logs`). `get-logs-v2` `--from`/`--to` are UNIX seconds.
3. After approval, run a separate `--cli-dry-run` before every actual write; dry-run is not business approval. For §8 coupled writes, complete both dry-runs before the two uninterrupted actual writes. An exact `Idempotent-Skip` runs neither call.
4. Get before Update; Update is overwrite — carry unchanged fields.
5. Native plugins first; use extended plugins only when native cannot meet the need, and state the trade-off.
6. No SSH/kubectl/docker exec; no admin project, no `starops`, no internal MCP, no private console API.
7. Unknown alarm codes: consult official docs or `references/alarm-catalog.yaml`; never explain from memory.
8. **NEVER run `aliyun` via `sudo`**. Run it directly as the current user; never switch users, shells, accounts, or credential profiles to bypass an error.
9. Never modify or clear environment variables or CLI config you did not create. On an infrastructure-level failure (not an API error), retry the identical atomic command once, then report the raw output and stop — never fabricate the expected response.
10. Diagnose a failed call from its own response — `errorCode`, `requestID`, message — plus `references/`. Never inspect the CLI binary, its install directory, local config files, or the environment to explain why a call behaved as it did; that is outside this skill's scope and risks exposing user configuration.
11. The original request and complete parameters are never implicit R2+ authorization; only explicit post-diff approval is valid.
12. Every SLS cloud call is one direct atomic command with literal parameters.
13. Only the bundled `scripts/` helpers may be used: `preflight.sh`, `render_pipeline.py`, `validate_pipeline.py`, `normalize_diff.py`, `redact_output.py`, `classify_sls_error.py`, `parse_lens_logging.py`. `validate_pipeline.py`/`normalize_diff.py` are mandatory at the §6/§8 workflow points; `classify_sls_error.py` on non-2xx responses; `parse_lens_logging.py` after `get-logging`.
14. Ask at most one question per turn, end the turn there, and wait for the user's next message; never answer your own question.

---

## 13. Success Verification

Unified acceptance U1-U6 (config object / group binding / applied state / heartbeat & version / data arrival / field & index) with pass conditions and failure routes: `references/acceptance-criteria.md`. Per-step verification commands: `references/verification-method.md`.

---

## 14. Cleanup

Cleanup is R3/R4. Unbind before delete; restate resources on delete. Order for a config created by this skill: `remove-config-from-machine-group` → `delete-logtail-pipeline-config` → (optional) `delete-index` / `delete-log-store` only with explicit user confirmation. See `references/risk-and-approval.md`.

---

## 15. Best Practices

1. CLI-first with plugin-mode hyphenated subcommands (`aliyun sls get-logs-v2`), never classic `RunXxx` style or undocumented aliases.
2. Confirm region/project and other user-specific parameters before any cloud call; never hardcode account values.
3. One session-wide `--user-agent` id on every cloud call; inject `SKILL_SESSION_ID` for scripts.
4. Approve with normalized diff before any R2+ write; dry-run and write as separate atomic calls.
5. Least-privilege RAM from `references/ram-policies.md`; permission errors go through the §2 gate.
6. Destructive cleanup stays behind R3/R4 confirmation; unbind before delete.
7. Progressive disclosure: load only the `references/*` entry for the active capability.
8. While a decision is pending, restate the same question and wait; silence and deferral are never consent.

---

## References

| File | Contents |
|---|---|
| `references/navigation.md` | Capability router spec (inputs, adapters, states) |
| `references/prerequisites.md` | Preflight gates and input contract |
| `references/cli-installation-guide.md` | Aliyun CLI + SLS plugin install |
| `references/cli-contracts.yaml` | `aliyun sls` command contracts + status |
| `references/related-commands.md` | Full `aliyun sls` command table |
| `references/ram-policies.md` | Per-workflow RAM Actions + permission gate |
| `references/risk-and-approval.md` | R0-R4, snapshot, rollback |
| `references/machine-group.md` | Machine group, identity, heartbeat, version |
| `references/pipeline-config.md` | Pipeline config model, Get-then-Update |
| `references/plugin-version-gates.yaml` | 1.x/2.x/3.x plugin gates |
| `references/index-coupling.md` | Config/index same-batch rules, anti-patterns |
| `references/field-conventions.md` | Field naming, index type mapping |
| `references/task-model.yaml` | Unified task object |
| `references/scenario-matrix.yaml` | host/docker/k8s signals and inputs |
| `references/sls-lens-contracts.md` | Lens entry state machine, topic/field |
| `references/monitoring-queries.yaml` | Lens SQL library (get-logs-v2) |
| `references/troubleshooting.md` | No-data / heartbeat playbooks |
| `references/alarm-catalog.yaml` | Alarm code handling cards |
| `references/acceptance-criteria.md` | U1-U6 + CLI acceptance patterns |
| `references/verification-method.md` | Per-step verification commands |
| `references/knowledge-sources.md` | Source provenance, drift tracking |
