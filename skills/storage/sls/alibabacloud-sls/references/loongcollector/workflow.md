# Collection execution guide

Read this guide before cloud operations or host/cluster access. For local-only
rendering or validation, use the applicable helper and configuration reference.

## Contents

- [Prerequisites](#1-prerequisites), [RAM policy and permission recovery](#2-ram-policy)
- [Parameters](#3-parameter-confirmation), [observability](#4-observability)
- [Workflow selection](#5-workflow-selection), [execution](#6-execution-state-machine)
- [Risk and rollback](#7-risk-approval--rollback), [config/index coupling](#8-config--index-coupling)
- [Lens queries](#9-sls-lens-cloudlens-for-sls-run-logs), [troubleshooting](#10-troubleshooting-no-data-heartbeat)
- [Reports](#11-report-template), [global rules](#12-global-rules)
- [Acceptance](#13-success-verification), [cleanup](#14-cleanup)
- [Best practices](#15-best-practices), [reference index](#references)

## Language and reporting

Use the user's primary language for user-facing messages. Product names, commands,
JSON fields and API status values retain their original spelling. The report
and evidence templates in §11 and `troubleshooting.md` are reference formats.

### Permission recovery reference

The permission-recovery protocol in §2 retains these definitions:

```yaml
messages:
  permission_recovery: "是否已完成所需 RAM 授权并允许重试？请选择：已授权或未授权。"
  permission_recovery_short: "是否已完成所需 RAM 授权并允许重试？"
markers:
  ownership_error: ["不属于当前账号", "项目不属于你"]
  permission_decline: ["未授权", "停止"]
  permission_grant: ["已授权"]
  pending_read: ["未执行待办", "待办"]
```

---

## 1. Prerequisites

Aliyun CLI and SLS plugin setup follow the [shared requirements](../../SKILL.md#requirements)
and [installation guide](../cli-installation-guide.md).

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** use `cat`, `less`, `head`, `tail`, `grep`, `open`, `json.load`, or any file-reading command on credential files (e.g., `~/.aliyun/config.json`, `~/.aws/credentials`). To check file existence use `ls` only — never display contents. Printing plaintext secrets is an immediate task failure and security incident.
> - **NEVER** install or import `aliyun-log-python-sdk` / `aliyun.log` / `LogClient`, or any other SLS SDK, to bypass CLI. `pip install` of a cloud SDK is a task failure.
> - **NEVER** print, `cat`, or paste kubeconfig / client certificates / tokens into the conversation. For opt-in CRD only: write `describe-cluster-user-kubeconfig` output to a `0600` tempfile.
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status. `scripts/loongcollector/preflight.sh` already does this.
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

Run `bash scripts/loongcollector/preflight.sh` for credential and scope checks. `preflight.sh` already invokes `aliyun configure list` internally; running it **is** a valid credential check — do not cat CLI config files, and do not add a standalone `aliyun configure list` just to satisfy a checklist. Full gate details: `references/loongcollector/prerequisites.md`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| (none for credentials) | — | Credentials come from `aliyun configure` profiles; never introduce AK/SK env vars in-session |
| `ALIBABA_CLOUD_SLS_SKILL_SESSION` | Shared setup | Session ID inherited by bundled scripts; see §4. |

---

## 2. RAM Policy

This skill uses the user's own identity and only touches resources they are authorized for. Permissions are layered ReadOnly / Operator / Destructive. Per-workflow RAM Actions are in `references/loongcollector/ram-policies.md` — do not default to broad `AliyunLogFullAccess`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/loongcollector/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

**Runtime detail (same gate, do not skip the three steps above):**
1. Report the missing RAM Action and request ID; output `[Error: permission]`. Reading `references/loongcollector/ram-policies.md` alone is **not** a successful diagnose call.
2. **Try** `ram-permission-diagnose` with the missing Actions and request ID. **FALLBACK:** if it is unavailable, output the Action, request ID and RAM-console guide manually, then ask catalog message `permission_recovery` with last line `[AWAITING: PERMISSION_CONFIRMATION]` and pause.
3. Do not retry the affected write (including `--cli-dry-run`) before confirmation.
4. **READ-PATH HARD STOP:** On 401/403/`Unauthorized`/`AccessDenied` for `project get` / `machine-group get` / `machine-group list-machines` / `logstore get`, first read the message. If it is **ownership** (English ownership text or any catalog `ownership_error` marker) → this is **not** a RAM gate: emit `[BLOCKED: RESOURCE_RESOLUTION_FAILED]` and stop; do **not** ask `permission_recovery_short`, do not create the official `k8s-log-*` name, and do not retry. Otherwise emit `[Error: permission]` with the Action and request ID, then in the **same turn** ask exactly `permission_recovery` with last line `[AWAITING: PERMISSION_CONFIRMATION]`, and issue **zero** further `aliyun sls` calls that turn — including `machine-group get`, `machine-group list-machines`, `machine-group get-applied-configs`, and `logstore get`. Those unread calls are catalog `pending_read` items, not queried conclusions.
5. **After the user's permission answer (same gate for read-path and write/dry-run):**
   - Any catalog `permission_decline` marker or equivalent decline → **zero tools that turn** (no `write_file`, no `aliyun sls`). Explicitly state that execution is terminated, list every **not-yet-run** read as catalog `pending_read` with its RAM Action, then put `[BLOCKED: PERMISSION_REQUIRED]` on the final line. If the task asked for machine-group heartbeat, the pending items **must** include `machine-group get` → `log:GetMachineGroup` and `machine-group list-machines` → `log:ListMachines` (name the group). Never present an unrun heartbeat as a queried conclusion.
   - A catalog `permission_grant` marker → **same turn**, retry the **identical** failed command (if the failure was a dry-run, retry that dry-run first) and emit `[RECOVERED: permission_granted]` in the user-facing text immediately. Explicitly state that the disposition is human intervention followed by retry, so the recovery action is unambiguous.

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
| `project` | Conditional | Target SLS project when required by the installer or cloud collection workflow | none |
| `logstore` | Conditional | Target logstore (create/onboarding/query) | none |
| `machine_group` | Conditional | Machine group name (bind/heartbeat) | none |
| `config_name` | Conditional | Logtail pipeline config name | none |
| `machine_identify_type` | Conditional | `ip` or `userdefined` | none |
| `machine_list` | Conditional | IP list or user-defined identifiers | none |
| `scenario` | Conditional | `host` / `docker` / `k8s` / `host_agentsight` | none |
| `environment` | Conditional | `ecs` / `self_host` / `ack` / `self_k8s` for `install.deploy` | none |
| `instance_id` | Conditional | ECS instance ID for Cloud Assistant | none |
| `cluster_id` | Conditional | ACK / self-k8s cluster id | none |
| `lens_project` / `lens_logstore` | Optional | SLS Lens entry when auto-discovery unavailable | none |

Never substitute placeholder/example values for a missing real resource. Missing required inputs for the selected workflow → STOP and ask.

If a required machine-group identity is unknown, ask whether it uses IP addresses
or user-defined identifiers. Use an identity already supplied by the user. For
installation-only requests, do not ask for collection inputs. If collection
onboarding was requested, collect the identity before preparing the group change.

---

## 4. Observability

Use the [shared session ID and User-Agent setup](../../SKILL.md#observability)
before cloud operations. Direct CLI calls and bundled scripts inherit
`ALIBABA_CLOUD_USER_AGENT`; script reports use `ALIBABA_CLOUD_SLS_SKILL_SESSION`.
Local help, configuration inspection and validation do not require a User-Agent.

**Domain extension — ATOMIC CLOUD-CALL RULE (HARD):** Every tool invocation that calls SLS must contain exactly one direct `aliyun sls ...` command with literal, fully expanded parameter values, and the command must start with `aliyun sls`. Do not hide a cloud call behind shell variables, environment assignments, functions, aliases, wrapper scripts, loops, command substitutions, `eval`, pipes, redirections (including `2>&1`), or compound commands (`;`, `&&`, `||`). Use the SLS command groups, such as `project get`, or the top-level `query` command; never use a PascalCase OpenAPI alias, because it bypasses the validated command/mocking contract. Compute timestamps or JSON in a separate local step, then place the resulting literals in the cloud command. This applies equally to verification and acceptance reads: no loops, no `cd …` prefix, no `$VAR` or `$(…)` substitution, including in `--from`/`--to` and JSON bodies. Never write cloud calls into a `.sh` file and run it; the command record is plain-text notes, not a runnable script. Local validators must receive what the command actually returned — save the real stdout to a file and pass that file; retyping or `echo`-ing an expected response is fabricated evidence. Reuse the session established by the shared setup.

---

## 5. Workflow selection

Use `references/loongcollector/navigation.md` for capability identifiers, required inputs,
and workflow outcomes. Load only the references needed for the selected task.

---

## 6. Execution State Machine

The workflow should follow:
`Classify → Preflight → Observe → Plan → Authorize → Execute → Verify → (Rollback)`.

`install.deploy` verifies collector readiness after installation. This completes
an installation-only request. If collection or end-to-end verification was
requested, continue with collection Observe/Plan and the applicable U1-U6 checks.

- **Classify**: select the capability, scenario (`host/docker/k8s/host_agentsight`),
  environment (`ecs|self_host|ack|self_k8s`) and management plane (`api|crd`). Use the
  SLS API by default. Use CRD only when the user requested `ClusterAliyunPipelineConfig`
  or GitOps/CR management and the kube-apiserver is reachable. Read `crd-pipeline.md`
  for its prerequisites. Clarify missing scope-changing inputs before cloud calls.
  - Agentloop, AgentSight, `input_agentsight`, eBPF Runtime or `ebpf-event` selects
    `config.create` (or `onboarding.cloud` when the group must be created), with
    scenario `host_agentsight`. Read `agentsight-agentloop.md` and `input-agentsight.md`.
    Names remain `runtime-ebpf-agentsight-config` and `ebpf-event`; the host requires
    Linux, kernel >=5.10 and collector >=3.3.9. This is not an OBI/OTLP workflow.
  - Resolve a user-supplied Project prefix with `project list --project <prefix>`,
    then verify the selected full name with `project get`. Zero matches blocks
    resource resolution; multiple matches require user selection. Do not broaden
    the prefix or construct an unrelated name. A list result alone is not existence proof.
- **Preflight**: use `scripts/loongcollector/preflight.sh`. Add `--need-ecs` for ECS,
  `--need-cs` for ACK, or `--need-kubectl` for self-built Kubernetes installation
  and opt-in CRD work. Follow `prerequisites.md` for blocking checks.
  - ECS uses `aliyun ecs run-command --biz-region-id <region> ... --instance-id <id>`
    and `describe-invocation-results --biz-region-id <region> --invoke-id <id>`.
    Use `--instance-id`, not `--instance-id.1`; these ECS plugin commands use
    `--biz-region-id`, not `--region-id` or `--region`.
    A failed help probe is advisory, not evidence of a failed installation.
    Poll a running invocation before continuing with requested collection work.
  - Missing kubectl for self-built Kubernetes installation blocks that installation;
    ask for a usable command and target context. ACK API-based collection does not
    require a kubeconfig.
  - Before self-host installation, check the user's configured SSH channel with
    `ssh -o BatchMode=yes -o ConnectTimeout=8 <alias> -- true`. If it fails, request
    usable SSH access. Do not change SSH configuration, host mappings or host-key
    verification settings, substitute localhost, or switch to another host.
  - With `--need-cs`, a missing CS plugin or failed availability probe blocks
    preflight. Explicit not-enabled responses (`ErrorNotEnabled`, `cskpro`,
    `NotEnabled`) are warnings. After installation is authorized, use
    `ensure_ack_prereq.sh` for first-use setup and retry the failed CS write once.
    Create a cluster only when requested: use `--biz-profile Default`, with
    `ack.standard` before `ack.pro.small`; use the user-selected cluster and VPC.
    Do not substitute `--profile` for `--biz-profile`.
- **Observe**: for collection creation or binding, checks should follow
  **Project → machine group → Logstore → Pipeline configuration and bindings**.
  Read `project get` on the resolved full Project, then `machine-group get`
  (or `machine-group list-machines` for heartbeat), `logstore get`, and the config
  and binding queries. Read collector version from `machines[].binary` before
  choosing plugins; use a version already supplied by the user. If it remains
  unknown, ask for it rather than assume a plugin family. Do not use Lens solely
  to obtain a version. Verify existence with the corresponding `get` operation;
  heartbeat and binding results do not replace resource existence checks.
  Record not-found responses and continue the remaining independent reads,
  including `machine-group get-applied-configs`. Permission failures follow §2.
  Save the full resource objects and bindings as pre-change snapshots. Create a
  missing resource only after its corresponding `get` returns ResourceNotExist.
- **Plan**: prepare target objects and preserve unchanged fields from the snapshots.
  A from-zero `onboarding.cloud` plan includes Project, Logstore, Index, machine group,
  Pipeline configuration and binding unless the user opts out of indexing.
  Use `scripts/loongcollector/render_pipeline.py` to render the target Pipeline,
  and `scripts/loongcollector/validate_pipeline.py` to validate the complete writable
  configuration. A validation error blocks dry-run and the actual write for that
  target. Showing changes as a diff
  is recommended; `normalize_diff.py --kind config|index|auto` provides a normalized
  diff for config, index and other objects. Exit code 3 means the diff contains
  changes, not that comparison failed. Include impact, rollback and verification.
  `mode=plan` performs no cloud writes. For coupled config/index changes, follow §8.
- **Authorize**: installation, collection changes and resource changes require user
  authorization. Show the affected resources and planned changes; a diff is recommended.
  If authorization is declined or deferred, do not execute the pending changes.
- **Execute**: use the authorized scope and the shared observability setup. Run the
  corresponding `--cli-dry-run` before an actual write, except for verified create/apply
  no-ops. If current state matches a create/apply target, skip dry-run and write,
  verify through get/list, and record the skipped operation and its evidence.
  On `AlreadyExist`, get and compare: a match is an existing-state no-op; a mismatch
  is an existing-resource conflict.
  - **config.modify exception**: execute the requested `logtail-pipeline-config update`
    and any coupled `index update` after authorization, even if the snapshot already
    matches. Both writes still need their dry-runs. Create/apply idempotency is unchanged.
  - **AgentSight lock**: render, validate and prepare the changes, obtain authorization,
    then call `logtail-pipeline-config create` even when get already saw the object.
    `AlreadyExist` is the lock; do not update the existing config. Follow
    `agentsight-agentloop.md` for binding and modification behavior.
  - **Error recovery**: keep the error code and request ID; use
    `classify_sls_error.py` to classify the response. Allow at most three retries
    after the initial attempt. For parameter errors, fix the named parameter and retry
    the same API. For throttling, use bounded backoff; for server errors, retry the
    same request. Ownership errors block resource resolution; other permission errors
    follow §2. A failed dry-run blocks its actual write.
  - For `meta.progress=Incomplete`, follow §9's bounded retry procedure. Report the
    returned completeness status; do not fabricate retries or a completed result.
- **Verify**: installation-only requests use collector readiness checks. Collection
  changes use fresh post-write reads: the changed objects' `get` operations,
  `index get` where applicable, both binding directions, `machine-group list-machines`
  and a business-logstore `query`. A machine-group creation needs a post-create
  `machine-group get`; an Observe-phase 404 is not acceptance evidence.
  Use the bounded 15-second polling, up to four attempts, in `verification-method.md`.
  Execute business-data acceptance after config create/update/bind or onboarding,
  including when heartbeat is absent. Report observed row count and progress.
  Empty results do not establish collection success; state that data arrival is
  unverified and give the observed reason. Include the full Project, Logstore,
  machine group and config when reporting cloud collection results.
- **Rollback**: restore from the pre-execution snapshot or declared inverse operation;
  do not reconstruct the old configuration from memory.

Input contracts: `prerequisites.md`. Acceptance commands: `verification-method.md`.

### Scope & adapter rules
- Cloud-only capabilities execute through `aliyun sls` + local validators. These workflows do not use SSH/kubectl.
- `install.deploy` may use `aliyun ecs run-command` + `aliyun ecs describe-invocation-results` (ECS), user SSH (fingerprint confirmed, no private key in chat), `aliyun cs` (addon name **`loongcollector`**), and `kubectl` for **self_k8s package install** plus opt-in CR get/apply. **No `workbench exec` / OOS / `kubectl exec` / `docker exec` / unbounded root shell.** Never print kubeconfig or client certs; write a 0600 tempfile only.
- When collection was requested after installation, the host path continues to `onboarding.cloud`. The K8s path reuses the official Project/machine group and creates the pipeline via SLS API by default, then performs U1–U6 and `query`. CRD apply only on explicit user request (`references/loongcollector/crd-pipeline.md`).
- Fixed within one request: account/profile, region, project, cluster, group, config. Switching scope requires a fresh confirmation.
- One management plane per config: API **or** CRD, never both. If double-write is detected, STOP (`references/loongcollector/pipeline-config.md`, `references/loongcollector/crd-pipeline.md`). A CR-owned config must not be updated via API. Defaulting to API does not authorize creating a second plane.

---

## 7. Risk, Approval & Rollback

| Level | Examples | Authorization |
| --- | --- | --- |
| R0 read | list/get, status, log query | Read operations |
| R1 local | schema validation, rendering, diff | Local preparation |
| R2 reversible write | create/update resources, apply/bind, install collector, `kubectl apply` CR | User authorization |
| R3 high impact | remove/unbind, bulk changes | User authorization; state impact and scope |
| R4 destructive | delete Project/Logstore/config/group | User authorization; identify exact resources and deletion impact |

Snapshot, rollback and cleanup procedures: `risk-and-approval.md`. Get before
Create as described in §6. New-resource rollback does not default to deletion.

---

## 8. Config / Index Coupling

When processors add, remove or rename a field, plan the config and corresponding
index changes together. Show both changes together; a diff is recommended.
The sequence should be:
**snapshot config/index → render target config → validate target config → config diff
→ index diff → config dry-run → index dry-run → config write → index write → verification**.
The resource changes require user authorization. `normalize_diff.py --kind config`
and `--kind index` provide the two diffs. If either dry-run fails, execute neither
write. If config succeeds and index fails, record partial completion and follow
§6's error-recovery procedure for the index; do not report both as complete.

- `status`/`status_code`/`http_status` default to `long`; time/latency/bytes chosen by semantics.
- SLS has no `float` field-index type. Map a floating-point requirement (for example `request_time float`) to `double` and show that mapping in the index diff.
- JSON nested fields: declare parent `json` index or the flattened field index explicitly.
- Prefix change must update index field names and the acceptance query together.
- `processor_rename` is extended-only; JSON rename uses all-extended `processor_json` → `processor_rename` with plural `SourceKeys`/`DestKeys` (never `SourceKey`/`DestKey`/`processor_rename_native`). Index diff must drop old keys and add new ones; `http_status` defaults to `long`. Full examples: `references/loongcollector/index-coupling.md`.

**MANDATORY COMMAND MAPPING:** use the `logtail-pipeline-config` group for Pipeline resources and config-to-group bindings, and `machine-group get-applied-configs` for group-to-config bindings. Resource selectors are `--project`, `--logstore`, `--machine-group` and `--logtail-pipeline-config`. `logstore update` merges supplied settings; include retention values to preserve when changing retention. Never classic `get-config`/`get-logs`/`list-logstore` aliases; stop on unsupported classic `inputDetail` configs. Use `--help` to confirm command usage when needed. Index: existing→`index update`, missing→`index create`; `--line` uses `"chn": true`; a `text` key's `token` is a JSON **array** of delimiter strings — a concatenated string returns `IndexInfoInvalid: field token is of error format`. On `IndexInfoInvalid` / token-format errors, repair **only** via `aliyun sls` (rewrite `--keys` as a JSON array of delimiter strings, or pass keys from a task-workspace JSON file — never `~/.aliyun/config.json`). Do **not** install or call `aliyun-log-python-sdk`. If CLI-side repair still fails after the allowed retries, stop and report the unresolved parameter. Full contracts: `references/loongcollector/cli-contracts.yaml`, `references/loongcollector/index-coupling.md`, `references/loongcollector/field-conventions.md`.

---

**Create resource selectors:** use `--project` for `project create`, `--logstore` for `logstore create`, `--machine-group` for `machine-group create`, and `--logtail-pipeline-config` for `logtail-pipeline-config create`. Confirm command parameters before any write attempt.

## 9. SLS Lens (CloudLens for SLS) run logs

Lens is the primary data source for basic troubleshooting. Run-log query itself uses public `aliyun sls query`.

**Entry discovery.** Verify the business Project with `project get`, then call
`logging get` and `parse_lens_logging.py`. If it returns a usable Lens Project/Store,
verify and use that entry. Otherwise use a user-supplied Lens entry, or ask for its
Project and Logstore after completing the independent non-Lens reads. Do not reuse
the business Project or invent a diagnostic store after discovery fails. If the
user cannot supply an entry, continue machine-group/config/business checks and
report the Lens evidence gap. After obtaining an entry, query `logtail_alarm` and
the version-routed metrics before completing the troubleshooting report.

**Forbidden**: STAROps/JWT/console cookies, UID-guessed Lens stores and treating
missing Lens evidence as absence of alarms. Missing collector version on onboarding
or configuration work asks for the version, not for a Lens entry.

**Query hard constraints** (full: `references/loongcollector/sls-lens-contracts.md`, `references/loongcollector/monitoring-queries.yaml`): no `select *`; version route `>=3`→`loongcollector_metric`, `<3`→`logtail_profile`/`logtail_metric` (must execute that `query` even on failure); `logtail_alarm` filters by `project` (never `config_name` in where); Incomplete → retry the identical request up to four total attempts at 15-second intervals, then report incomplete if it has not completed; Complete → report the returned completed status; report Lens project/logstore/topic/window/route/completeness.

---

**Mandatory version-route call:** for every known collector version `>=3`, including `3.2.6`, execute a distinct `aliyun sls query` query containing `__topic__: loongcollector_metric`. A `logtail_status` query is additional evidence and does not replace the metric query. Execute this call even when an earlier Lens query returns no rows or an error.

## 10. Troubleshooting (no-data, heartbeat)

Check sequence: `classify → heartbeat & version → config & binding → alarm/metric → business data → minimal fix → re-verify`.
- The diagnostic checks should follow the chain above. Record not-found responses
  and run the remaining independent reads, including config bindings and the
  business-store query. A missing business Project does not establish that a Lens
  Project is missing. Follow §9 to obtain a Lens entry before its dependent queries.
  Permission failures follow §2.

- Cloud visibility and collector-side evidence corroborate each other; do not substitute one for the other.
- No data: `logtail-pipeline-config get --logtail-pipeline-config` + `machine-group list-machines` + exact binding queries from §8 → `logtail_alarm` by project → `logtail_status` → version-matched pipeline topic → business logstore.
- Heartbeat abnormal: `machine-group list-machines` → `logtail_status`; if Lens is unavailable, name the host-side items (collector process, reporting region, account id, `user_defined_id`). Cloud-only tasks stay in prose. `install.deploy` may re-use `run-command`/SSH/`kubectl get` for read-only status.
- For evidence fields and report examples, refer to `troubleshooting.md`. Use the
  actual response for each attempted check, and identify missing or unexecuted evidence.


Playbooks and alarm handling cards: `references/loongcollector/troubleshooting.md`, `references/loongcollector/alarm-catalog.yaml`.

---

## 11. Report template

You may use the following template:

- **Conclusion**: done / partial / blocked / rolled back.
- **Scope**: profile, region, target host or cluster; full Project, Logstore, group
  and config where applicable.
- **Evidence**: key responses and observations; Lens Project/Store, topic, window,
  version route and completeness for Lens queries. See `troubleshooting.md` for
  heartbeat, alarm, collection, binding and Pipeline evidence examples.
- **Changes**: planned and executed actions, differences, and verified no-ops.
- **Acceptance**: installation readiness or applicable U1-U6 results; observed data
  arrival and its reason for collection work. Identify incomplete or unexecuted checks.
- **Rollback**: whether restoration is required, executed, and based on which snapshot.
- **Next step**: unresolved blocker or next action. A proposed write fix states its
  resource changes and requires user authorization before execution.

A structured execution record can follow `task-model.yaml`. On an audit request,
provide redacted commands and request IDs (`redact_output.py`). Preserve error codes,
request IDs and redacted failure context. Do not present failed, unexecuted or
unverified steps as successful.

---

## 12. Global Rules

1. Prefer the exact validated mapping in §8 and `references/loongcollector/cli-contracts.yaml`. Use `aliyun sls <group> <operation> --help` or `aliyun sls query --help` to confirm usage when needed. ACK uses `aliyun cs` with addon name `loongcollector`. First-use enablement is `scripts/loongcollector/ensure_ack_prereq.sh` (`open-ack-service` + CS roles). K8s collection **defaults to** `logtail-pipeline-config create` + bind `k8s-group-${cid}`. `kubectl apply` of `ClusterAliyunPipelineConfig` is opt-in only.
2. Use `aliyun sls query` for log queries. Supply `--from` and `--to` or `--time-range`; use fixed absolute endpoints for retries and `--format json` when parsing responses.
3. After approval, run a separate `--cli-dry-run` before every actual write; dry-run is not business approval. For §8 coupled writes, the sequence should follow the config/index workflow there; complete both dry-runs before writing. Verified create/apply no-ops run neither call, subject to the §6 AgentSight exception.
4. For replace updates, read the current configuration and preserve unchanged fields. `logstore update` merges supplied settings; include retention values to preserve when changing retention.
5. Native plugins first when collector version is `>=3.x`. If version is unknown, ask the user for the collector version — do not assume a plugin family. Use extended plugins when native cannot meet the need (e.g. `processor_rename`), and state the trade-off.
6. No `kubectl exec` / `docker exec`; no admin project, no `starops`, no internal MCP, no private console API. SSH/`run-command`/kubectl only for `install.deploy` (and its read-only status follow-up) as specified. Never Workbench/OOS.
7. Unknown alarm codes: consult official docs or `references/loongcollector/alarm-catalog.yaml`; never explain from memory.
8. **NEVER run `aliyun` via `sudo`**. Run it directly as the current user; never switch users, shells, accounts, or credential profiles to bypass an error.
9. Never modify or clear environment variables or CLI config you did not create. On an infrastructure-level failure (not an API error), retry the identical atomic command once, then report the raw output and stop — never fabricate the expected response.
10. Determine command success from its exit code: 0 means success; nonzero means failure. Diagnose failures using the available HTTP status, request ID, error code and error message, together with `references/loongcollector/`. Preserve the returned diagnostics. Never inspect the CLI binary, its install directory, local config files, or the environment to explain why a call behaved as it did; that is outside this skill's scope and risks exposing user configuration.
11. Installation, collection changes and resource changes require user authorization.
12. Every SLS cloud call is one direct atomic command with literal parameters.
13. Bundled `scripts/loongcollector/` helpers: `preflight.sh`, `render_pipeline.py`, `validate_pipeline.py`, `normalize_diff.py`, `redact_output.py`, `classify_sls_error.py`, `parse_lens_logging.py`, `render_loongcollector_install_cmd.py`, `wait_cs_task.sh`, `render_crd.py`, `ensure_ack_prereq.sh`. Use `render_pipeline.py` and `validate_pipeline.py` for the target Pipeline as described in §6; diffs can use `normalize_diff.py`. `classify_sls_error.py` on non-2xx responses; `parse_lens_logging.py` after `logging get`. If the user asked only to render/validate a `ClusterAliyunPipelineConfig` locally, run `render_crd.py` + `validate_pipeline.py` and stop — no `aliyun cs`, no `kubectl`, no cluster connect. Never `pip install` a cloud SDK and never import `aliyun.log`.
14. Ask for missing inputs before using them. Do not supply the user's answer yourself.

---

## 13. Success Verification

Unified acceptance U1-U6 (config object / group binding / applied state / heartbeat & version / data arrival / field & index) with pass conditions and failure routes: `references/loongcollector/acceptance-criteria.md`. Per-step verification commands: `references/loongcollector/verification-method.md`.

---

## 14. Cleanup

Cleanup is R3/R4. Unbind before delete; restate resources on delete. Order for a config created by this skill: `logtail-pipeline-config remove-from-machine-group` → `logtail-pipeline-config delete` → (optional) `index delete` / `logstore delete` only with explicit user confirmation. See `references/loongcollector/risk-and-approval.md`.

---

## 15. Best Practices

1. CLI-first with SLS command groups and `aliyun sls query`, never classic `RunXxx` style or undocumented aliases.
2. Confirm region/project and other user-specific parameters before any cloud call; never hardcode account values.
3. Reuse the shared session ID and User-Agent for cloud calls and bundled scripts.
4. Resource changes require user authorization; showing changes as a diff is recommended. Run dry-run before the corresponding write.
5. Least-privilege RAM from `references/loongcollector/ram-policies.md`; permission errors go through the §2 gate.
6. Destructive cleanup stays behind R3/R4 confirmation; unbind before delete.
7. Progressive disclosure: load only the `references/loongcollector/*` entry for the active capability.
8. When the user defers a decision, wait; do not treat deferral as consent.

---

## References

| File | Contents |
|---|---|
| `references/loongcollector/navigation.md` | Capability router spec (inputs, adapters, states) |
| `references/loongcollector/prerequisites.md` | Preflight gates and input contract |
| `references/cli-installation-guide.md` | Aliyun CLI + SLS plugin install |
| `references/loongcollector/cli-contracts.yaml` | `aliyun sls` command contracts + status |
| `references/loongcollector/related-commands.md` | Full `aliyun sls` command table |
| `references/loongcollector/ram-policies.md` | Per-workflow RAM Actions + permission gate |
| `references/loongcollector/risk-and-approval.md` | R0-R4, snapshot, rollback |
| `references/loongcollector/machine-group.md` | Machine group, identity, heartbeat, version |
| `references/loongcollector/pipeline-config.md` | Pipeline config model, Get-then-Update |
| `references/loongcollector/plugin-version-gates.yaml` | 1.x/2.x/3.x plugin gates |
| `references/loongcollector/index-coupling.md` | Config/index same-batch rules, anti-patterns |
| `references/loongcollector/field-conventions.md` | Field naming, index type mapping |
| `references/loongcollector/task-model.yaml` | Unified task object |
| `references/loongcollector/scenario-matrix.yaml` | host/docker/k8s/host_agentsight signals and inputs |
| `references/loongcollector/agentsight-agentloop.md` | Agentloop AgentSight fixed pipeline, ProbeConfig, masking |
| `references/loongcollector/input-agentsight.md` | `input_agentsight` schema, builtins, version/kernel, RawHttpsFallback |
| `references/loongcollector/sls-lens-contracts.md` | Lens entry state machine, topic/field |
| `references/loongcollector/monitoring-queries.yaml` | Lens SQL library (query) |
| `references/loongcollector/troubleshooting.md` | No-data / heartbeat playbooks |
| `references/loongcollector/alarm-catalog.yaml` | Alarm code handling cards |
| `references/loongcollector/acceptance-criteria.md` | Install stage gate + U1-U6 + CLI acceptance patterns |
| `references/loongcollector/verification-method.md` | Per-step verification commands |
| `references/loongcollector/install/install-ecs.md` | ECS Cloud Assistant + loongcollector.sh |
| `references/loongcollector/install/install-host.md` | Self-host SSH + same script |
| `references/loongcollector/install/install-ack.md` | ACK addon `loongcollector` + first-use `open-ack-service` / CS roles |
| `references/loongcollector/install/install-k8s.md` | Self-k8s custom package |
| `references/loongcollector/crd-pipeline.md` | Opt-in ClusterAliyunPipelineConfig + temp public KubeConfig |
| `references/loongcollector/knowledge-sources.md` | Source provenance, drift tracking |
