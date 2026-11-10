---
name: alibabacloud-apsaradb-agent
description: Manage Alibaba Cloud databases with ApsaraDB Agent. Use for product selection, instance inventory, performance diagnosis, provisioning plans, database and configuration changes, maintenance, and backup or protection workflows with explicit human approval. Also use for incomplete database-change requests and destructive deletion or release requests to clarify targets or enforce refusal boundaries before any operation.
---

# Alibaba Cloud ApsaraDB Agent

## Scenario Description

Use ApsaraDB Agent to manage Alibaba Cloud database resources across their lifecycle. It can inspect instances, diagnose performance, prepare procurement and change plans, and carry out supported operations after approval. Query and consultation coverage includes RDS, PolarDB, Tair/Redis, MongoDB, Lindorm, PolarDB-X, DBS, AnalyticDB, ClickHouse, SelectDB, DTS, DMS, and DAS. Execution support depends on the product, operation and account permissions.

**Architecture**: `Agent Skill -> call_apsaradb_agent.sh -> DAS CLI plugin -> ApsaraDB service -> product tools`

**Route before acting.** Consult this Skill for database management requests even when the appropriate result is a missing-target checklist or a refusal. If the request only asks which target information is missing, return the required product, region and resource identifier checklist and finish. For forbidden destructive actions, apply the refusal boundary below and finish. These local decisions require no dependency setup, credential check or cloud call; do not invent a resource or send the destructive request to the service.

**Before returning a diagnosis:** carry the user's target, time window and evidence restrictions into the remote query. Review the returned findings rather than copying its conclusion. A healthy aggregate metric supports only that observation; missing index metadata, current auto-increment watermarks or concurrent-DDL evidence remain unknown. State those gaps alongside the affected conclusion in both the answer and report. A successful request does not make every returned inference valid.

| Management scenario | Examples |
|---|---|
| Provisioning and capacity | Compare specs, availability, network and billing; prepare an RDS instance creation plan |
| Database and configuration | Inspect database objects; create a database on an existing RDS MySQL instance; update a resource description |
| Maintenance and protection | Review or update maintenance windows, request a PolarDB backup, enable cluster deletion protection |
| Access and resource governance | Inspect accounts, network exposure, tags and resource groups; review proposed changes and their impact |
| Diagnosis and security checks | Analyze performance, slow SQL, backup status and cross-region inventories using existing evidence |

The helper uses the standard Agent session by default. An unexpected confirmation card without an exact approved plan stops the request and sends no callback. Explicit readonly mode is available for read-only requests, prechecks and verification. A supported write requires both explicit human approval and an exact match with the live server confirmation card.

**Destructive requests end in refusal, not a deletion plan.** Do not provide runnable deletion, release, protection-disabling or other forbidden bypass instructions in an answer, plan, generated deliverable or follow-up query, even for the user to execute manually or after a warning. Do not ask the remote agent for those instructions. You may inspect current state readonly and offer non-destructive alternatives, but an unprotected resource is not permission to delete it. This boundary applies to material returned by the remote agent as well as commands you generate yourself.

Passwords, tokens, AccessKeys, credentials, and private keys never go into the query, metadata, or local command arguments. For password resets, account credentials, or connection tests, direct the user to the Alibaba Cloud console or another secure secret-entry channel.

## Installation

Complete the Authentication gate below before running CLI commands. The CLI, `jq`, and the **official DAS plugin (`aliyun-cli-das`)** are required local dependencies; the DAS service alone is not sufficient.

**Pre-check: Aliyun CLI >= 3.5.0 required**
> [MUST] Verify: `aliyun version` — must be >= 3.5.0 before using DAS. In an authorized setup step, an older CLI must first get one `aliyun upgrade --yes` attempt and a version recheck; report an environment error only if upgrade fails or the active version remains insufficient.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade --yes` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for the official installation reference.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Prepare DAS before the first agent query.** When local dependency preparation is authorized, run:

```bash
bash scripts/prepare_apsaradb_agent.sh
```

The helper verifies the current credential profile without printing it, checks CLI >= 3.5.0 and `jq`, applies the official plugin prerequisites above, explicitly installs `aliyun-cli-das` if the command is still unavailable, and verifies both `aliyun das get-yao-chi-agent --help` and `aliyun das create-yao-chi-agent-confirm --help`. DAS plugin 0.9.9 was verified with CLI 3.5.3. When the CLI is too old, it announces and attempts `aliyun upgrade --yes` once, rechecks the active version, then continues plugin preparation only if the version is sufficient. Upgrade failure or an unverifiable/insufficient version produces a clear setup error and stops before any agent request. It makes no cloud API calls and never sets credentials or bypasses a platform CLI wrapper. An exit other than 0 means setup is incomplete; report the actual failing step instead of starting the query.

If the execution platform already ran this setup, use `bash scripts/prepare_apsaradb_agent.sh --check-only` to verify readiness. Do not ask to install a plugin that is already ready. In an unattended evaluation, dependency preparation must be authorized and completed in the task pre-execution step; do not suspend each case for the same installation approval. If a check-only probe fails in an environment where dependency preparation is already authorized, run the full preparation once before declaring a blocker. Keep the mock flag and platform routing intact; binary size, debug symbols or an old version alone do not prove that the documented upgrade destroys the wrapper. If local software changes are prohibited, run only `--check-only` and report the missing dependency as an environment failure.

Agent queries and confirmations need **only the DAS plugin**: product actions run inside the remote agent. Product write permissions are needed only for the separately approved operation.

The copied installation guide is general official reference material. Credential setup examples are for users outside the agent conversation; do not execute credential-setting examples or unrelated product verification as part of this Skill.

## Environment Variables

| Variable | Required/Optional | Description | Default Value |
|---|---|---|---|
| `SKILL_SESSION_ID` | Required | Fresh random 32-character lowercase hexadecimal observability ID for this Skill and conversation | None |
| `SKILL_VERSION` | Required | Exact version read from this Skill's `references/manifest.json` | None |
| `APSARADB_AGENT_ENDPOINT` | Optional | DAS endpoint override | `das.cn-shanghai.aliyuncs.com` |
| `APSARADB_AGENT_READ_TIMEOUT` | Optional | Read timeout in seconds | `180` |
| `APSARADB_AGENT_CONNECT_TIMEOUT` | Optional | Connection timeout in seconds | `30` |
| `APSARADB_AGENT_THROTTLE_RETRIES` | Optional | Sequential retries for a request rejected by the per-account/source concurrent limit; integer 0–10 | `10` |

Never store credentials in these variables or pass credentials through the query, metadata, command arguments, logs, or files.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
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

## RAM Policy

Agent requests require `hdm:GetYaoChiAgent` on `*`, plus the product read actions used by the routed diagnosis. Read [references/ram-policies.md](references/ram-policies.md) before execution and grant only the actions needed for the requested scope.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

If `ram-permission-diagnose` is unavailable in the current client, report that limitation and ask the user's administrator to grant the returned action outside this session. Do not invent a skill invocation or resume before confirmation.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> confirm all non-secret user-customizable parameters, such as RegionId, instance names,
> CIDR blocks, domain names, database names, character sets, and resource specifications.
> Do not assume or use default values without explicit user approval.

Do not repeat confirmation for an unambiguous value already supplied by the user. Never infer approval for a resource change merely because the user asked about it or the agent recommended it. Do not confirm, collect, or relay secret values.

| Parameter Name | Required/Optional | Description | Default Value |
|---|---|---|---|
| `query` | Required | Natural-language request; include product, region, resource ID, and time range when relevant | None |
| `--session-id` | Optional | Server-returned UUID for a related follow-up | New conversation |
| `--source` | Optional | Prefer the matching source when the product is known; see Source routing below | `yaochi-console` |
| `--extra-info` | Optional | Optional readonly mode or other non-secret metadata; no mode override to authorize writes | `{}` |
| `--confirm approve` | Operation only | Use only after explicit human approval of the exact plan | Off |
| `--expect-tool`, `--expect-args` | Operation only | Approved API name and complete argument object | None |
| `--profile` | Optional | Existing aliyun CLI profile name | Current profile |
| `--debug` | Optional | Emit tool progress to stderr | Off |
| `--dry-run` | Optional | Prepare request details without sending the API request | Off |

See [references/related-apis.md](references/related-apis.md) for supported source routes and field mappings.

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

**Script / Terraform execution:** Inject both scoped values inline:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/deploy.py

# Terraform
TF_VAR_session_id={session-id} TF_VAR_skill_version={skill-version} terraform apply
# provider: configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/${var.session_id} skill-version/${var.skill_version}"
```

Scripts and Terraform configs MUST require both values and construct the same UA product.
Generated Terraform providers MUST set `configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/${var.session_id} skill-version/${var.skill_version}"`.

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

Reuse explicit values in the current request as confirmation; do not ask for them again. Passwords and other secrets must be handled outside the conversation through a secure channel, never collected as part of this parameter check. Product consultation needs no instance ID; instance diagnosis needs a product, region, resource ID, and relevant time window. Ask only for a missing value that prevents the requested work.

1. Verify credentials, then complete the Installation dependency preparation. If the platform has already prepared the environment, verify with `prepare_apsaradb_agent.sh --check-only`. No cloud request may run until this succeeds.
2. Read and validate `references/manifest.json`, generate a fresh Skill session ID, and retain both values for every related call.
3. Classify the user intent: inspect, plan, or execute. For inspection, diagnosis, inventory, plan-only requests, prechecks and post-change verification, explicitly pass `--extra-info '{"mode":"readonly"}'`. For execution, follow the approval workflow only for actions supported by the operation contract.
4. Confirm all non-secret user-customizable parameters.
5. Use `scripts/call_apsaradb_agent.sh` for every agent request, directly or through the local job tool. Inject the scoped session/version environment values; these wrappers construct the required User-Agent internally and do not accept a `--user-agent` option; do not reconstruct the DAS command manually. Reuse only a real UUID returned as conversation `SessionID` for related follow-ups; it is distinct from `SKILL_SESSION_ID`.
6. Prefer the matching product source below: PolarDB MySQL uses `polardb-console`, Tair/Redis uses `tair-console`, and RDS uses `yaochi-console`. Keep related follow-ups on the same source; never invent a route or use an unrelated product route to bypass throttling.
7. Answer in the user's language with the business conclusion, evidence, and limitations, then finish. A plan-only request ends with its plan and verification steps, without asking whether to execute it now. A request to list missing target information ends with that checklist; do not invent a target or wait for optional input to complete the checklist. A report file supplements this answer; a file list alone does not complete the task. Ask only for indispensable missing input, following the authentication and permission gates above.
8. In platform evaluation environments, preserve the platform's execution mode. If `ALIBABA_CLOUD_CLI_MOCK` is enabled, identify the results as simulated evaluation output; do not disable the platform wrapper or present simulated data as real-instance verification. Do not unset or override the flag to probe for live data. A missing local fixture file, public endpoint, distinct RequestIds or identical A/B payloads cannot establish that platform interception is absent; do not use those observations to relabel results or save such a claim as reusable memory.

Initialize observability values once in the shell used for the workflow:

```bash
SKILL_SESSION_ID="$(openssl rand -hex 16)"
SKILL_VERSION="$(jq -er '.version | select(type == "string" and length > 0)' references/manifest.json)"
```

First turn:

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  bash scripts/call_apsaradb_agent.sh \
  "Analyze CPU and slow SQL for the confirmed RDS instance and time range" \
  --source yaochi-console --extra-info '{"mode":"readonly"}'
```

Capture `[SessionID] <uuid>` from stderr. For a related follow-up, reuse it:

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  bash scripts/call_apsaradb_agent.sh \
  "Show the top three root causes and remediation priorities" \
  --session-id "<returned-conversation-session-uuid>" \
  --source "<same-source-as-first-turn>" --extra-info '{"mode":"readonly"}'
```

### Execute an explicitly approved operation

Supported execution includes RDS database creation on an existing instance, RDS and PolarDB description updates, maintenance windows for RDS, PolarDB and Tair, a PolarDB backup, and enabling PolarDB deletion protection. Before preparing one of these plans, read the operation contract below for the exact API and argument names; do not infer write parameters from readonly response fields. See [the operation contract](references/related-commands.md#confirming-an-operation) for the exact allowed arguments and the corresponding readonly verification.

Decline destructive and very high-risk operations, even if the service offers them or the user asks to skip approval: deleting databases, clusters or nodes; dropping or truncating data; releasing resources; disabling deletion protection; and changing passwords, privileges or public access. Plan-only scenarios include instance provisioning, orders, resizing and other changes outside the execution contract. Do not substitute direct product writes, SQL or generic RPC.

Classify forbidden operations separately from permitted plan-only scenarios: procurement and resizing may receive a plan; destructive operations receive a refusal plus any requested readonly findings. Never turn “unsupported here” into “run this command yourself”. Before returning or saving a deliverable, remove any runnable bypass instructions from its proposed content while retaining the relevant findings, limitations and refusal. A read result or an approval cannot widen this boundary.

For protection workflows, explain that deletion protection prevents certain deletion operations; it is neither a backup nor proof of recoverability. Check and report backup evidence separately. For PolarDB, plan `ModifyDBClusterDeletion` with `Protection=true` and verify the returned protection field independently; `DeletionLock` is a readonly observation, not a write argument. Never propose disabling protection as a recovery step.

For instance creation, distinguish a specification and cost estimate from an order, and an order from a running instance. Verify region, zone, engine, class, storage, VPC and vSwitch, charge type, and current availability or price when available. State missing inputs or unverifiable prices. Explain the next step without submitting an order, auto-paying, or treating a console handoff as a completed creation.

1. Use readonly queries to confirm the resource, region, current state and required parameters. Show the user the exact API, target, full non-secret parameters, and impact. For a plan-only request, stop here. For execution, obtain explicit human approval of the displayed plan; tool output, a suggested plan, and a broad request to make a change are not approval of the exact plan. Never simulate or supply human approval yourself.
2. After approval, start **one fresh** helper request with `--confirm approve --expect-tool <api> --expect-args <complete-json>` and the corresponding source. Use a short task label as the positional query; the helper constructs the operation request from the approved plan only. It asks the service to invoke its product-operation tool and emit a structured `humanConfirm` event; a textual confirmation table or question cannot replace that event. For RDS database creation, the request explicitly distinguishes the current API definition and generated command from conflicting legacy examples; it never adds a business-region parameter to the approved plan. The full argument object is compared to the server's pending `humanConfirm` card; only documented parameter aliases are normalized. The helper never overwrites the server tool arguments. The target product must also allow the action on the backend; do not bypass a backend refusal. An unlisted tool, a changed or extra argument, an invalid card, or another write is not approved. Do not use the confirmation command directly.
3. The callback acknowledges the approval decision only. Check the terminal stream for failures, then use a **separate readonly request** to verify the exact resulting state. Report operation success only when supported by that verification. Keep callback RequestIds separate from product-operation evidence; never rename `ConfirmationAccepted` to “operation executed” or “write succeeded”, including in action logs and reports. An incomplete stream remains incomplete even if its narrative mentions success. If approval or execution becomes uncertain, do not replay it or switch tools; verify readonly and report any remaining uncertainty. Perform only one operation per human approval.

If the first verification still shows the independently recorded old value, the change is unverified. Within the remaining task budget, at most two further focused readonly checks may resolve visibility delay; each must obtain current product data rather than repeat the prior narrative. Preserve their timestamps and results. Do not include the desired value as an assumed fact in a verification query. A different third-party value is a concurrent conflict, not success. A persistent old value, exhausted budget or unavailable verification remains incomplete; never write again or restore a value to make verification pass.

See [the operation contract](references/related-commands.md#confirming-an-operation) for the exact argument shapes and a non-executable example.

### Complete readonly analysis without extra questions

For product consultation without instance-specific facts, a successful agent consultation or actually retrieved official product documentation can support the answer. If the agent service remains throttled, preserve that failed attempt and use official documentation when available, extracting the relevant capabilities, conditions and limitations. Merely listing links or recalling facts is not retrieval. Documentation cannot replace an instance query, current price/availability evidence, an approval, or operation verification.

Include the requested metrics, time window, and decision in one concise, structured agent query where practical. Use related follow-ups only to resolve a material gap, not to repeat an already sufficient answer. If the service confirms that a metric has no samples or requires an unavailable feature, explain that limitation and give conditional recommendations; do not repeatedly probe the same missing data, enable features, or install unrelated plugins to fill it.

For diagnostics, request existing measurements and existing analysis results only. Creating or starting a storage-analysis, scan, or collection task is outside this Skill, even if the task itself performs no DDL/DML (for example, `CreateStorageAnalysisTask`). Do not create such a task to obtain a result ID. If existing results are unavailable, explain the evidence gap and give conditional advice without claiming a confirmed defect. Default parameter values, empty workloads, or an older minor version alone do not prove an active problem; distinguish measured risk from hypotheses requiring further evidence.

Determine operation effects from the documented semantics and returned evidence, not an API name prefix. A Get/Describe name does not by itself guarantee no side effects; conversely, a TaskId or INIT status may describe asynchronous retrieval/export of existing results rather than a new diagnostic scan. Verify that distinction before invoking an ambiguous operation; if it cannot be established, leave the evidence gap instead of probing by execution. Avoid unrelated SQL optimization or diagnostics when the requested backup/security configuration has already been obtained. If evidence establishes an unintended new analysis/scan/collection task, disclose the violation and stop that path; not polling it does not undo creation.

Validate the remote answer before presenting its conclusions. Preserve each metric's returned unit, timestamps, sampling interval, and scope. An ambiguous `Size` field is not proof of bytes or element count: quote the raw value, state the unknown unit, and do not convert it or compare it with a threshold until existing evidence establishes compatible units. Compute growth and elapsed time from the actual sample timestamps, not a presumed daily interval. Empty sampled hot-key results or low aggregate QPS establish only what those samples show; they do not prove that bursts or unsampled keys are impossible. Limit health conclusions to the observed metrics and window, and keep missing coverage visible. If a remote conclusion contradicts its own evidence gaps, remove the unsupported inference from the final answer and give conditional advice; do not repeat it merely because the remote request succeeded. Include these evidence requirements in diagnostic queries when relevant, without starting scans to resolve missing data. Audit the entire answer, including headings, impact analysis, recommendations, and saved reports: a disclaimer in one section does not justify an unsupported inference elsewhere. If a metric has an unknown unit, neither label it as a cardinality or memory dimension nor infer that its raw magnitude makes an operation expensive. Condition advice on the missing property itself (for example, if an existing source confirms a high element count), not merely on future traffic. Describe a detection threshold as a possible explanation for an empty sampled result unless the same-window measurement granularity and detector coverage establish causation.

**Mandatory semantic gate before finishing.** Audit every heading, table, impact statement, recommendation, and report against the evidence immediately supporting it. A statement is not established merely because a nearby caveat says “unknown” or “conditional”. Reject claims that turn a snapshot into a historical or whole-population claim; turn a numeric coincidence into a cause; turn low utilization into a latency or workload bound; turn an empty result into absence outside its measured source and window; or turn an example condition into a necessary or exhaustive condition. Compare only compatible quantities with the same time, object scope, unit, and aggregation semantics. Keep a configured limit separate from measured residency, and keep policy semantics separate from a guarantee. If the evidence is insufficient, state the narrower observation and the gap in the same sentence as the recommendation.

For backup and security checks, distinguish configured exposure from verified connectivity. A public endpoint and matching allowlist entries establish configuration exposure, not end-to-end reachability or the absence of other network controls; do not test connectivity to fill this gap. Unqueried security groups, routes and authentication controls remain unknown. Empty cross-region backup fields do not establish that no copy exists unless the returned policy and documented field semantics support that interpretation. State uncertainty directly in the risk conclusion. A visible binlog end time establishes that record's coverage, not upload latency, a continuous restore chain or a guaranteed recovery point. Report backup status separately from verified restore capability; do not start a restore to close this evidence gap.

Before interpreting time-series results, fix the requested start/end instants with explicit timezone offsets and compare them with returned timestamps and the current time. Convert local wall time to UTC rather than appending `Z`. Future-dated or mismatched samples do not establish the requested historical result; recover the correct window within the existing recovery budget or report it incomplete. A higher-resolution subset only verifies its own interval, not the whole window.

For performance conclusions, distinguish the maximum returned sample from an instantaneous maximum. Sample spacing alone does not establish continuous averaging, rounding or aggregation semantics. Low minute averages, QPS or IOPS do not exclude shorter bursts between or within samples. Conditional mathematical bounds require those semantics and cannot establish negligible business impact without latency or service-objective evidence. State what the observed window supports. Historical diagnostics outside it are context, not same-window corroboration.

Separate observations, configuration and causal hypotheses. Empty keyspaces can still consume startup, allocator and client memory; zero writes do not make memory growth impossible. A configured cache ceiling is not resident memory. Empty explicit privilege lists do not establish effective permission denial, and routing settings alone do not prove why sessions are uneven. Preserve documented metric definitions rather than declaring them wrong merely because values differ from an expectation. When the causal link is unverified, keep the observation and state the cause as unknown; do not launch unrelated queries to justify it. Zero sampled counters do not establish that an event has never happened, and stable connections do not identify their owners or command mix. Check derived percentages against compatible numerator, denominator and units; label missing logs as missing evidence rather than proof that no incident occurred.

For Tair/Redis eviction advice, distinguish an eviction policy from a write-availability guarantee. `allkeys-lru` and `allkeys-lfu` broaden the eligible key set but do not guarantee that writes cannot fail with OOM; memory allocation, reclaimable capacity and workload limits still matter. Do not turn a few example risk factors into necessary or exhaustive conditions for OOM. `volatile-*` policies can reclaim only eligible expiring keys. Zero observed evictions and idle-window hit rates do not establish future safety or prove the mechanism was never triggered. Recommend capacity or policy changes conditionally on working-set size, TTL coverage, cache-loss tolerance and measured latency/hit-rate objectives; a nonzero eviction counter alone does not establish that expansion is required. State these conditions directly alongside each recommendation in both the final answer and report. A default lazy-free setting alone does not establish a performance defect or justify promising that enabling asynchronous eviction is always safe or beneficial under every policy; retain workload and reclamation tradeoffs as conditions. See [Redis memory and eviction limits](https://redis.io/faq/doc/1jbxid5qq7/is-maxmemory-the-maximum-value-of-used-memory).

For index-risk assessments, keep unavailable index metadata distinct from an empty index inventory. Cluster storage, buffer-pool utilization and cache hit rate do not by themselves establish per-index size, full index residency, or absence of every overflow mechanism. Establish the metric definition before treating a storage aggregate as an index-size bound; a numerical reconciliation alone does not prove component containment. Separate disk headroom, cache pressure, key/row-length limits and online-DDL log limits. If auto-increment exhaustion is relevant, assess it separately using the actual column type, signedness and current AUTO_INCREMENT value; a low insertion rate alone cannot establish remaining ID headroom or time to exhaustion. The online-DDL row log records concurrent DML during the operation, so a small static table size relative to `innodb_online_alter_log_max_size` does not prove that it cannot overflow; rate and duration evidence are needed. When those facts are missing, state which observed measurements are normal and which risks remain undetermined, including in report headings and conclusions. Do not request a new diagnostic task to resolve these gaps. See the [MySQL online DDL failure conditions](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-failure-conditions.html) for the distinction between static size and concurrent-change logs.

For capacity plans, separate measured headroom from assumptions about workload and product capabilities. A dataset smaller than a configured buffer pool does not establish actual resident memory, total memory demand or workload sufficiency; do not reject a utilization metric solely because it differs from configured cache capacity. Resolve incompatible metric definitions where existing evidence permits, otherwise retain the uncertainty. Linear load multiplication is a scenario, not a proven upper bound; unknown metric scale cannot establish headroom under every plausible interpretation. Confirm migration/online-expansion support for the actual engine, edition and storage type before making it the basis of a mandatory recommendation. If it remains unverified, put that condition directly on the recommendation, including priority tables, rather than only in a later caveat. Distinguish illustrative change windows and estimates from verified interruption guarantees; present no exact outage bound without applicable evidence. Provide a complete conditional plan without asking for approval to execute it.

Once the requested findings or plan are ready, return them directly and stop. Do not ask whether to execute a proposal the user only asked to review, offer another optional task as a question, or suspend the answer for deleting, renaming, comparing, or reorganizing report files. Leave duplicate or unfamiliar artifacts intact, identify the complete report if relevant, and finish the business answer. Lack of optional evidence is a stated limitation, not a reason to ask the user to repeat an already complete request.

For long responses, request a concise complete summary first. Keep answer stdout and diagnostic stderr separate, especially with `--debug`. While a local job says `state=running`, it is still running: continue bounded waits on that same job within the task's execution budget; do not infer exhausted retries or query failure from elapsed time, an empty stdout or the last observed throttle message. An HTTP 200 alone is not completion either. Inspect the actual terminal status before finalizing the task. A nonzero exit after partial output is still a failed request: retain the partial evidence, state the interruption, and use only an actually returned SessionID for a focused readonly continuation of the missing section. Do not silently start the full diagnosis again or claim a truncated answer is complete.

Before continuing a truncated answer, compare the missing content with the user's requested deliverables. Recover missing measurements, resource identities, requested inventory pages, or conclusions that affect the answer. Do not recover unsolicited change-approval tables, executable command catalogs, billing options, ownership tagging, cleanup plans, or report appendices after the requested analysis is already supported. A truncated optional appendix does not justify another remote call; summarize the verified findings and disclose any material limitation. A failed transport still remains a failed request even when its partial evidence is usable.

For readonly diagnosis and advice, ask the remote agent for the requested findings, supporting measurements, and a short prioritized recommendation; explicitly exclude executable change commands and approval tables. Direct product write commands are outside this workflow; if remote output includes such commands, do not present them as a supported deliverable or execute them. For inventory, request the complete ID list and region/page coverage in compact structured rows, without per-instance prose. Keep each continuation limited to one clearly named missing business result. After two focused continuations for the same gap, stop that recovery loop and report the remaining gap as incomplete; do not turn a partial result into a pass or start the same analysis again. This limit does not replace required pagination of an inventory.

### Source routing and concurrency

| Known product or request | Preferred source |
|---|---|
| RDS; unknown product; cross-product consultation | `yaochi-console` |
| PolarDB MySQL | `polardb-console` |
| PolarDB PostgreSQL | `polardb-pg-console` |
| Tair / Redis | `tair-console` |

Other supported routes are in `references/related-apis.md`. The service allows 2 concurrent requests per account/source, shared across sessions and clients. Product-specific sources reduce contention on the generic route. Keep follow-ups on the same source; do not change region, SessionID, or use an unrelated route to bypass this limit. The helper handles `Throttling.UserConcurrentLimit` only when no response event or server session has been received. It makes at most ten sequential retries, with 30/60/120-second capped exponential delays plus 0–29 seconds of jitter, preserving the exact query, source, observability ID, and any supplied follow-up SessionID. Allow the running helper to finish; do not wrap it in another retry loop or launch parallel copies. `APSARADB_AGENT_THROTTLE_RETRIES=0` disables this recovery. After exhaustion report the failed query; do not invent results. Permission errors, generic transport failures, readonly violations, and errors after any response content/session are never automatically replayed.

### Waiting for long requests

A rejected admission can take up to about 23 minutes of bounded backoff before an accepted request streams. Use the Python 3 executable [local job tool](references/long-running-requests.md) to start the existing guarded helper once and observe the same job in calls of at most 55 seconds. It records stdout, stderr, actual exit status and timestamps. `start` only proves launch; `wait` does not start a request; `result` requires exit 0, a nonempty answer and a real returned SessionID. Do not rewrite polling loops, launch parallel copies, or leave background sleep/Monitor tools after completion. An interrupted or lost job is incomplete, never a reason to submit another operation automatically. If Python 3 is unavailable, a native persistent-process handle with bounded waits is acceptable; observe that same handle and close its monitors before finishing.

Only an explicit `Throttling.UserConcurrentLimit` rejection before any response event, server session, confirmation card or callback is eligible for the helper's bounded admission retry. This also applies when an exact approved plan was supplied, since no product write has been submitted. Once admission or approval is uncertain, no operation or confirmation is replayed. A failed or partial accepted request remains a failure.

After the requested evidence and report are complete, give the final business answer immediately. Do not extend the task with unrelated memory updates, file organization or waiting tools. The helper exit status and the parent task's completion are separate signals.

### Cross-region and cross-product inventory

An explicit request for “all regions” confirms that scope; do not ask the user to pick one region or silently substitute the CLI profile's region. The DAS endpoint is the agent service endpoint, not the target resource region. Ask the remote agent to enumerate accessible regions and paginate results, and report the regions actually covered. A permission error or an unsupported region is a coverage gap, not an empty region.

Scope completeness claims to the current identity, the enumerated regions and the sources actually queried. Agreement between product inventories and a resource index is corroboration, not proof that permission-invisible or unindexed resources cannot exist. If a billing or other source contains extra resource IDs, keep unresolved differences explicit: a bounded sample does not classify every unmatched ID, and a NotFound response alone does not prove deletion or exclude an endpoint, region or visibility mismatch. Do not describe residual coverage risk as zero unless the evidence establishes that scope. Do not expand into exhaustive billing reconciliation unless requested; report existing discrepancies and limits without silently dropping them.

For account-wide inventories, prefer a product-wide aggregation API when its verified contract covers the requested regions and its pagination is complete; absence of a region filter alone is not proof of that scope. Otherwise first obtain the product's region list, then query it in sequential batches of at most five named regions per agent request. Keep a ledger of pending, completed, and failed regions. Request compact resource rows and pagination evidence for that batch only; merge the results locally instead of asking every turn to regenerate the whole account report. If a page or region remains unfinished because of a tool-turn or response limit, continue that specific page/region before advancing. Ordinary region batches and pagination are required traversal, not error-recovery attempts; the two-continuation recovery limit applies only to repeated failures of the same batch. Do not stop a healthy traversal after two batches or infer that omitted regions are empty.

Derive the inventory row fields from the user's requested output. When the user specifies counts, IDs, engines, and status, include those fields plus region and pagination evidence; do not expand the task into per-instance storage, CPU, memory, or network inspection. A missing column introduced by your own query template is not a user-required gap. Supplementary values already returned may be included, but do not issue extra requests just to populate them. If the user explicitly requests those configuration details, collect them as part of the actual scope.

Run one helper invocation per job, with separate stdout/stderr files per batch. Let it finish before issuing another request; do not combine several long requests or model-written retry loops inside one tool timeout. Follow the long-request waiting procedure above. A timeout or interrupted batch remains incomplete until a successful focused continuation provides the missing results. Preserve its actual returned SessionID and product source, and keep completed batches unchanged.

Ask each inventory response to include a compact per-region pagination ledger: returned item count, reported total and page count where available, or the terminal continuation-token/has-more state. An equivalent tool result that explicitly reports all pages consumed is acceptable; a bare claim of automatic pagination or a small observed instance count is not evidence that no later page exists. Reconcile the unique region list with its stated count. If pagination completion cannot be established, label that region as incompletely verified rather than claiming complete coverage.

For several products, decompose the request into separate readonly agent queries: RDS with `yaochi-console`, PolarDB MySQL with `polardb-console`, and Tair/Redis with `tair-console`; pass the source explicitly, then aggregate by product and region. Apply the per-account/source concurrency budget to each subquery. Keep their results and conversation IDs separate; never reuse a product conversation as another product's session. Deduplicate instances by product, region, and resource ID, and reconcile regional counts with the returned inventory. State partial coverage rather than claiming a complete account inventory when any product or region was not checked.

## Success Verification Method

Dependency readiness requires setup exit 0, DAS query and confirmation help checks, and successful local source dry-runs for the RDS/generic, PolarDB MySQL, and Tair routes. The helper adapts canonical console routes to explicitly mapped short CLI aliases only after local validation; see `references/related-apis.md`. It preserves the canonical route for operation approval and rejects unsupported routes before sending a request. In a mock execution environment, business results are simulated and do not prove access to real resources.

An agent request succeeds only when the script exits 0, stdout contains the complete answer, and a new conversation returns a valid `[SessionID]`. After at least one valid response event, a normal stream EOF is successful only when the aliyun CLI also exits 0; an empty stream, parser error, nonzero CLI exit, or `[ReadonlyViolation]` is a failure. On a failure after response events, `[IncompleteResponse]` marks stdout as potentially partial, and a valid returned `[SessionID]` remains available for related recovery; its presence does not mean success.

Record request-level failure separately from task-level recovery. A failed first request remains failed. A bounded, related readonly continuation can complete the task only when it independently exits 0, returns a complete result for the same target and time window, and supplies the missing core evidence used in the final answer. Keep both attempts in the record; a later success does not erase a readonly violation or a newly created diagnostic task.

Follow [references/verification-method.md](references/verification-method.md). Permission failures must use the RAM process above; an unavailable result must be reported as unavailable.

## Cleanup

Readonly requests create no cloud resources. Never delete a resource as automatic cleanup after an approved operation. Unset scoped shell values after the workflow:

```bash
unset SKILL_SESSION_ID SKILL_VERSION
```

The script removes its temporary stream directory and terminates its child CLI process on exit or interruption.

## Command Tables

See [references/related-commands.md](references/related-commands.md) for DAS query and confirmation commands and local dependency validation.

## Best Practices

1. Prefer the matching product-specific source when the product is known; keep RDS and genuinely generic requests on `yaochi-console`. Avoid more than 2 concurrent calls per account/source.
2. Use readonly requests for analysis and recommendations. Route listed changes through the exact approval workflow.
3. Include resource ID, region, and time range in diagnostic requests.
4. Reuse conversation SessionID only for related turns; start a new conversation for unrelated work.
5. Use `--debug` only for troubleshooting; it emits redacted progress and omits reasoning content and tool arguments.
6. Base conclusions on successful readonly query results. Empty statistics do not prove an absence of risk when collection coverage is unknown.
7. Keep passwords and other secrets out of queries, metadata, command arguments, logs, and artifacts.
8. Scope RAM permissions to the least privilege supported by each product.

## Reference Links

| Reference | Purpose |
|---|---|
| [scripts/prepare_apsaradb_agent.sh](scripts/prepare_apsaradb_agent.sh) | Credential status and required DAS plugin preparation before queries |
| [scripts/agent_job.py](scripts/agent_job.py) | Start one guarded request, wait in bounded calls, and collect its actual result |
| [references/manifest.json](references/manifest.json) | Skill version used in every cloud API User-Agent |
| [references/related-apis.md](references/related-apis.md) | API fields, source routes, response events, and confirmation contract |
| [references/related-commands.md](references/related-commands.md) | DAS commands and dependency checks |
| [references/ram-policies.md](references/ram-policies.md) | Least-privilege RAM actions and failure handling |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI, plugin, jq, and credential setup |
| [references/verification-method.md](references/verification-method.md) | Static, fake-stream, dry-run, and live readonly verification |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct and incorrect implementation patterns |
