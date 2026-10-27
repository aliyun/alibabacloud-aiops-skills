---
name: alibabacloud-apsaradb-agent
description: Readonly Alibaba Cloud ApsaraDB consultation, resource queries, and diagnostics. Use for database product questions, instance configuration and cross-region inventories, performance and slow SQL analysis, backup and security checks, and evidence-based optimization recommendations.
---

# Alibaba Cloud ApsaraDB Agent

## Scenario Description

Use Alibaba Cloud ApsaraDB Agent as a readonly cross-product database expert. Consultation, instance queries, and diagnosis go to the agent in readonly mode. Supported products include PolarDB, Tair/Redis, MongoDB, Lindorm, PolarDB-X, DBS, RDS, AnalyticDB, ClickHouse, SelectDB, DTS, DMS, and DAS. This public release supports analysis and recommendations only; resource creation, deletion, updates, order placement, confirmation execution, and local resource-changing CLI workflows are outside its scope.

**Architecture**: `Agent Skill -> call_apsaradb_agent.sh -> aliyun das get-yao-chi-agent (ExtraInfo.mode=readonly) -> ApsaraDB service -> product Planner and product Skill`

Supported readonly capabilities include instance, cluster, node, endpoint, and configuration queries; CPU, memory, storage, connection, QPS, latency, capacity, slow SQL, execution plan, lock, session, and log analysis; parameter guidance; and backup, recovery, availability, and security checks.

| Capability | Path | Resource-change boundary |
|---|---|---|
| Product consultation | Agent, readonly | No change |
| Instance queries and diagnosis | Agent, readonly | No change |
| Optimization recommendations | Agent, readonly | Explain options and risks; no execution commands or changes |

The script always sends `mode: readonly` and rejects any other mode. The service filters write tools in readonly mode, but treat readonly as a request contract rather than a universal guarantee: if the service ever asks for a write confirmation, the script reports `[ReadonlyViolation]`, never approves it, and exits nonzero.

Passwords, tokens, AccessKeys, credentials, and private keys never go into the query, metadata, or local command arguments. For password resets, account credentials, or connection tests, direct the user to the Alibaba Cloud console or another secure secret-entry channel.

## Installation

Complete the Authentication gate below before running CLI commands. The CLI, `jq`, and the **official DAS plugin (`aliyun-cli-das`)** are required local dependencies; the DAS service alone is not sufficient.

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for the official installation reference.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Prepare DAS before the first agent query.** When local dependency preparation is authorized, run:

```bash
bash scripts/prepare_apsaradb_agent.sh
```

The helper verifies the current credential profile without printing it, checks CLI >= 3.3.3 and `jq`, applies the official plugin prerequisites above, explicitly installs `aliyun-cli-das` if the command is still unavailable, and verifies `aliyun das get-yao-chi-agent --help`. It makes no cloud API calls, never sets credentials, and never upgrades the CLI silently. An exit other than 0 means setup is incomplete; report the actual failing step instead of starting the query.

If the execution platform already ran this setup, use `bash scripts/prepare_apsaradb_agent.sh --check-only` to verify readiness. Do not ask to install a plugin that is already ready. In an unattended evaluation, dependency preparation must be authorized and completed in the task pre-execution step; do not suspend each case for the same installation approval. If local software changes are prohibited, run only `--check-only` and report the missing dependency as an environment failure.

Readonly agent queries need **only the DAS plugin**, not an RDS, PolarDB, or Tair product plugin: product queries happen inside the remote agent. Product-operation plugins and cloud write permissions are not prerequisites of this readonly release.

The copied installation guide is general official reference material. Credential setup examples are for users outside the agent conversation; do not execute credential-setting examples or unrelated product verification as part of this Skill.

## Environment Variables

| Variable | Required/Optional | Description | Default Value |
|---|---|---|---|
| `SKILL_SESSION_ID` | Required | Fresh random 32-character lowercase hexadecimal observability ID for this Skill and conversation | None |
| `SKILL_VERSION` | Required | Exact version read from this Skill's `references/manifest.json` | None |
| `APSARADB_AGENT_ENDPOINT` | Optional | DAS endpoint override | `das.cn-shanghai.aliyuncs.com` |
| `APSARADB_AGENT_READ_TIMEOUT` | Optional | Read timeout in seconds | `180` |
| `APSARADB_AGENT_CONNECT_TIMEOUT` | Optional | Connection timeout in seconds | `30` |
| `APSARADB_AGENT_THROTTLE_RETRIES` | Optional | Sequential retries for a request rejected by the per-account/source concurrent limit; integer 0–10 | `6` |

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
| `--extra-info` | Optional | Request metadata as a JSON object string; `mode` is always forced to `readonly` | `{}` |
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
3. Classify the request: consultation, query, or diagnosis goes to the agent. If the request asks to create, delete, update, purchase, or execute a change, explain that this public release does not support operations and direct the user to the product console. Do not initiate a confirmation flow or substitute a local write command. For mixed requests, complete only the clearly requested readonly analysis and state the unsupported part.
4. Confirm all non-secret user-customizable parameters.
5. Use `scripts/call_apsaradb_agent.sh` for every agent request; do not reconstruct the DAS command manually. Reuse only a real UUID returned as conversation `SessionID` for related follow-ups; it is distinct from `SKILL_SESSION_ID`.
6. Prefer the matching product source below: PolarDB MySQL uses `polardb-console`, Tair/Redis uses `tair-console`, and RDS uses `yaochi-console`. Keep related follow-ups on the same source; never invent a route or use an unrelated product route to bypass throttling.
7. Answer in the user's language with the business conclusion, evidence, and limitations, then finish. A report file supplements this answer; a file list alone does not complete the task. Ask only for indispensable missing input, following the authentication and permission gates above.
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
  --source yaochi-console
```

Capture `[SessionID] <uuid>` from stderr. For a related follow-up, reuse it:

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  bash scripts/call_apsaradb_agent.sh \
  "Show the top three root causes and remediation priorities" \
  --session-id "<returned-conversation-session-uuid>" \
  --source "<same-source-as-first-turn>"
```

### Complete readonly analysis without extra questions

Include the requested metrics, time window, and decision in one concise, structured agent query where practical. Use related follow-ups only to resolve a material gap, not to repeat an already sufficient answer. If the service confirms that a metric has no samples or requires an unavailable feature, explain that limitation and give conditional recommendations; do not repeatedly probe the same missing data, enable features, or install unrelated plugins to fill it.

For diagnostics, request existing measurements and existing analysis results only. Creating or starting a storage-analysis, scan, or collection task is outside this readonly release, even if the task itself performs no DDL/DML (for example, `CreateStorageAnalysisTask`). Do not create such a task to obtain a result ID. If existing results are unavailable, explain the evidence gap and give conditional advice without claiming a confirmed defect. Default parameter values, empty workloads, or an older minor version alone do not prove an active problem; distinguish measured risk from hypotheses requiring further evidence.

Determine operation effects from the documented semantics and returned evidence, not an API name prefix. A Get/Describe name does not by itself guarantee no side effects; conversely, a TaskId or INIT status may describe asynchronous retrieval/export of existing results rather than a new diagnostic scan. Verify that distinction before invoking an ambiguous operation; if it cannot be established, leave the evidence gap instead of probing by execution. Avoid unrelated SQL optimization or diagnostics when the requested backup/security configuration has already been obtained. If evidence establishes an unintended new analysis/scan/collection task, disclose the violation and stop that path; not polling it does not undo creation.

Validate the remote answer before presenting its conclusions. Preserve each metric's returned unit, timestamps, sampling interval, and scope. An ambiguous `Size` field is not proof of bytes or element count: quote the raw value, state the unknown unit, and do not convert it or compare it with a threshold until existing evidence establishes compatible units. Compute growth and elapsed time from the actual sample timestamps, not a presumed daily interval. Empty sampled hot-key results or low aggregate QPS establish only what those samples show; they do not prove that bursts or unsampled keys are impossible. Limit health conclusions to the observed metrics and window, and keep missing coverage visible. If a remote conclusion contradicts its own evidence gaps, remove the unsupported inference from the final answer and give conditional advice; do not repeat it merely because the remote request succeeded. Include these evidence requirements in diagnostic queries when relevant, without starting scans to resolve missing data. Audit the entire answer, including headings, impact analysis, recommendations, and saved reports: a disclaimer in one section does not justify an unsupported inference elsewhere. If a metric has an unknown unit, neither label it as a cardinality or memory dimension nor infer that its raw magnitude makes an operation expensive. Condition advice on the missing property itself (for example, if an existing source confirms a high element count), not merely on future traffic. Describe a detection threshold as a possible explanation for an empty sampled result unless the same-window measurement granularity and detector coverage establish causation.

**Mandatory semantic gate before finishing.** Audit every heading, table, impact statement, recommendation, and report against the evidence immediately supporting it. A statement is not established merely because a nearby caveat says “unknown” or “conditional”. Reject claims that turn a snapshot into a historical or whole-population claim; turn a numeric coincidence into a cause; turn low utilization into a latency or workload bound; turn an empty result into absence outside its measured source and window; or turn an example condition into a necessary or exhaustive condition. Compare only compatible quantities with the same time, object scope, unit, and aggregation semantics. Keep a configured limit separate from measured residency, and keep policy semantics separate from a guarantee. If the evidence is insufficient, state the narrower observation and the gap in the same sentence as the recommendation.

For backup and security checks, distinguish configured exposure from verified connectivity. A public endpoint and matching allowlist entries establish configuration exposure, not end-to-end reachability or the absence of other network controls; do not test connectivity to fill this gap. Unqueried security groups, routes and authentication controls remain unknown. Empty cross-region backup fields do not establish that no copy exists unless the returned policy and documented field semantics support that interpretation. State uncertainty directly in the risk conclusion. A visible binlog end time establishes that record's coverage, not upload latency, a continuous restore chain or a guaranteed recovery point. Report backup status separately from verified restore capability; do not start a restore to close this evidence gap.

Before interpreting time-series results, fix the requested start/end instants with explicit timezone offsets and compare them with returned timestamps and the current time. Convert local wall time to UTC rather than appending `Z`. Future-dated or mismatched samples do not establish the requested historical result; recover the correct window within the existing recovery budget or report it incomplete. A higher-resolution subset only verifies its own interval, not the whole window.

For performance conclusions, distinguish the maximum returned sample from an instantaneous maximum. Sample spacing alone does not establish continuous averaging, rounding or aggregation semantics. Low minute averages, QPS or IOPS do not exclude shorter bursts between or within samples. Conditional mathematical bounds require those semantics and cannot establish negligible business impact without latency or service-objective evidence. State what the observed window supports. Historical diagnostics outside it are context, not same-window corroboration.

Separate observations, configuration and causal hypotheses. Empty keyspaces can still consume startup, allocator and client memory; zero writes do not make memory growth impossible. A configured cache ceiling is not resident memory. Empty explicit privilege lists do not establish effective permission denial, and routing settings alone do not prove why sessions are uneven. Preserve documented metric definitions rather than declaring them wrong merely because values differ from an expectation. When the causal link is unverified, keep the observation and state the cause as unknown; do not launch unrelated queries to justify it. Zero sampled counters do not establish that an event has never happened, and stable connections do not identify their owners or command mix. Check derived percentages against compatible numerator, denominator and units; label missing logs as missing evidence rather than proof that no incident occurred.

For Tair/Redis eviction advice, distinguish an eviction policy from a write-availability guarantee. `allkeys-lru` and `allkeys-lfu` broaden the eligible key set but do not guarantee that writes cannot fail with OOM; memory allocation, reclaimable capacity and workload limits still matter. Do not turn a few example risk factors into necessary or exhaustive conditions for OOM. `volatile-*` policies can reclaim only eligible expiring keys. Zero observed evictions and idle-window hit rates do not establish future safety or prove the mechanism was never triggered. Recommend capacity or policy changes conditionally on working-set size, TTL coverage, cache-loss tolerance and measured latency/hit-rate objectives; a nonzero eviction counter alone does not establish that expansion is required. State these conditions directly alongside each recommendation in both the final answer and report. A default lazy-free setting alone does not establish a performance defect or justify promising that enabling asynchronous eviction is always safe or beneficial under every policy; retain workload and reclamation tradeoffs as conditions. See [Redis memory and eviction limits](https://redis.io/faq/doc/1jbxid5qq7/is-maxmemory-the-maximum-value-of-used-memory).

For index-risk assessments, keep unavailable index metadata distinct from an empty index inventory. Cluster storage, buffer-pool utilization and cache hit rate do not by themselves establish per-index size, full index residency, or absence of every overflow mechanism. Establish the metric definition before treating a storage aggregate as an index-size bound; a numerical reconciliation alone does not prove component containment. Separate disk headroom, cache pressure, key/row-length limits and online-DDL log limits. The online-DDL row log records concurrent DML during the operation, so a small static table size relative to `innodb_online_alter_log_max_size` does not prove that it cannot overflow; rate and duration evidence are needed. When those facts are missing, state which observed measurements are normal and which risks remain undetermined, including in report headings and conclusions. Do not request a new diagnostic task to resolve these gaps. See the [MySQL online DDL failure conditions](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-failure-conditions.html) for the distinction between static size and concurrent-change logs.

For capacity plans, separate measured headroom from assumptions about workload and product capabilities. A dataset smaller than a configured buffer pool does not establish actual resident memory, total memory demand or workload sufficiency; do not reject a utilization metric solely because it differs from configured cache capacity. Resolve incompatible metric definitions where existing evidence permits, otherwise retain the uncertainty. Linear load multiplication is a scenario, not a proven upper bound; unknown metric scale cannot establish headroom under every plausible interpretation. Confirm migration/online-expansion support for the actual engine, edition and storage type before making it the basis of a mandatory recommendation. If it remains unverified, put that condition directly on the recommendation, including priority tables, rather than only in a later caveat. Distinguish illustrative change windows and estimates from verified interruption guarantees; present no exact outage bound without applicable evidence. Provide a complete conditional plan without asking for approval to execute it.

Once the requested findings or plan are ready, return them directly and stop. Do not ask whether to execute a proposal the user only asked to review, offer another optional task as a question, or suspend the answer for deleting, renaming, comparing, or reorganizing report files. Leave duplicate or unfamiliar artifacts intact, identify the complete report if relevant, and finish the business answer. Lack of optional evidence is a stated limitation, not a reason to ask the user to repeat an already complete request.

For long responses, request a concise complete summary first. Keep answer stdout and diagnostic stderr separate, especially with `--debug`. A nonzero exit after partial output is still a failed request: retain the partial evidence, state the interruption, and use only an actually returned SessionID for a focused readonly continuation of the missing section. Do not silently start the full diagnosis again or claim a truncated answer is complete.

Before continuing a truncated answer, compare the missing content with the user's requested deliverables. Recover missing measurements, resource identities, requested inventory pages, or conclusions that affect the answer. Do not recover unsolicited change-approval tables, executable command catalogs, billing options, ownership tagging, cleanup plans, or report appendices after the requested analysis is already supported. A truncated optional appendix does not justify another remote call; summarize the verified findings and disclose any material limitation. A failed transport still remains a failed request even when its partial evidence is usable.

For diagnosis and advice, ask the remote agent for the requested findings, supporting measurements, and a short prioritized recommendation; explicitly exclude executable change commands and approval tables. Resource-operation CLI generation is outside this release; if remote output includes such commands, do not present them as a supported deliverable or execute them. For inventory, request the complete ID list and region/page coverage in compact structured rows, without per-instance prose. Keep each continuation limited to one clearly named missing business result. After two focused continuations for the same gap, stop that recovery loop and report the remaining gap as incomplete; do not turn a partial result into a pass or start the same analysis again. This limit does not replace required pagination of an inventory.

### Source routing and concurrency

| Known product or request | Preferred source |
|---|---|
| RDS; unknown product; cross-product consultation | `yaochi-console` |
| PolarDB MySQL | `polardb-console` |
| PolarDB PostgreSQL | `polardb-pg-console` |
| Tair / Redis | `tair-console` |

Other supported routes are in `references/related-apis.md`. The service allows 2 concurrent requests per account/source, shared across sessions and clients. Product-specific sources reduce contention on the generic route. Keep follow-ups on the same source; do not change region, SessionID, or use an unrelated route to bypass this limit. The helper handles `Throttling.UserConcurrentLimit` only when no response event or server session has been received. It makes at most six sequential retries, with 30/60/120-second capped exponential delays plus 0–29 seconds of jitter, preserving the exact query, source, observability ID, and any supplied follow-up SessionID. Allow the running helper to finish; do not wrap it in another retry loop or launch parallel copies. `APSARADB_AGENT_THROTTLE_RETRIES=0` disables this recovery. After exhaustion report the failed query; do not invent results. Permission errors, generic transport failures, readonly violations, and errors after any response content/session are never automatically replayed.

### Waiting for long requests

Concurrent-limit backoff alone can take more than ten minutes, before the accepted request finishes streaming. A CLI read timeout limits a stalled read; it is not a total execution budget. Use the execution tool's persistent-process/yield facility and poll the same process until it exits. Do not put a long request under a tool deadline that kills it while waiting. Where the tool only supports blocking execution, use the detached local job recipe in [references/long-running-requests.md](references/long-running-requests.md), preserving stdout, stderr, and the actual helper exit code. Start each logical request once; subsequent checks only inspect that job. A returned PID or a successful launch is not query success. Verify the final helper exit code and response using the success criteria below, and report a lost/interrupted job as incomplete rather than launching a duplicate.

### Cross-region and cross-product inventory

An explicit request for “all regions” confirms that scope; do not ask the user to pick one region or silently substitute the CLI profile's region. The DAS endpoint is the agent service endpoint, not the target resource region. Ask the remote agent to enumerate accessible regions and paginate results, and report the regions actually covered. A permission error or an unsupported region is a coverage gap, not an empty region.

Scope completeness claims to the current identity, the enumerated regions and the sources actually queried. Agreement between product inventories and a resource index is corroboration, not proof that permission-invisible or unindexed resources cannot exist. If a billing or other source contains extra resource IDs, keep unresolved differences explicit: a bounded sample does not classify every unmatched ID, and a NotFound response alone does not prove deletion or exclude an endpoint, region or visibility mismatch. Do not describe residual coverage risk as zero unless the evidence establishes that scope. Do not expand into exhaustive billing reconciliation unless requested; report existing discrepancies and limits without silently dropping them.

For account-wide inventories, first obtain the product's region list, then query it in sequential batches of at most five named regions per agent request. Keep a ledger of pending, completed, and failed regions. Request compact resource rows and pagination evidence for that batch only; merge the results locally instead of asking every turn to regenerate the whole account report. If a page or region remains unfinished because of a tool-turn or response limit, continue that specific page/region before advancing. Ordinary region batches and pagination are required traversal, not error-recovery attempts; the two-continuation recovery limit applies only to repeated failures of the same batch. Do not stop a healthy traversal after two batches or infer that omitted regions are empty.

Derive the inventory row fields from the user's requested output. When the user specifies counts, IDs, engines, and status, include those fields plus region and pagination evidence; do not expand the task into per-instance storage, CPU, memory, or network inspection. A missing column introduced by your own query template is not a user-required gap. Supplementary values already returned may be included, but do not issue extra requests just to populate them. If the user explicitly requests those configuration details, collect them as part of the actual scope.

Run one helper invocation per job, with separate stdout/stderr files per batch. Let it finish before issuing another request; do not combine several long requests or model-written retry loops inside one tool timeout. Follow the long-request waiting procedure above. A timeout or interrupted batch remains incomplete until a successful focused continuation provides the missing results. Preserve its actual returned SessionID and product source, and keep completed batches unchanged.

Ask each inventory response to include a compact per-region pagination ledger: returned item count, reported total and page count where available, or the terminal continuation-token/has-more state. An equivalent tool result that explicitly reports all pages consumed is acceptable; a bare claim of automatic pagination or a small observed instance count is not evidence that no later page exists. Reconcile the unique region list with its stated count. If pagination completion cannot be established, label that region as incompletely verified rather than claiming complete coverage.

For several products, decompose the request into separate readonly agent queries: RDS with `yaochi-console`, PolarDB MySQL with `polardb-console`, and Tair/Redis with `tair-console`; pass the source explicitly, then aggregate by product and region. Apply the per-account/source concurrency budget to each subquery. Keep their results and conversation IDs separate; never reuse a product conversation as another product's session. Deduplicate instances by product, region, and resource ID, and reconcile regional counts with the returned inventory. State partial coverage rather than claiming a complete account inventory when any product or region was not checked.

## Success Verification Method

Dependency readiness is established by setup exit 0 and a successful DAS help check. In a mock execution environment, business results are simulated and do not prove access to real resources.

An agent request succeeds only when the script exits 0, stdout contains the complete answer, and a new conversation returns a valid `[SessionID]`. After at least one valid response event, a normal stream EOF is successful only when the aliyun CLI also exits 0; an empty stream, parser error, nonzero CLI exit, or `[ReadonlyViolation]` is a failure. On a failure after response events, `[IncompleteResponse]` marks stdout as potentially partial, and a valid returned `[SessionID]` remains available for related recovery; its presence does not mean success.

Record request-level failure separately from task-level recovery. A failed first request remains failed. A bounded, related readonly continuation can complete the task only when it independently exits 0, returns a complete result for the same target and time window, and supplies the missing core evidence used in the final answer. Keep both attempts in the record; a later success does not erase a readonly violation or a newly created diagnostic task.

Follow [references/verification-method.md](references/verification-method.md). Permission failures must use the RAM process above; an unavailable result must be reported as unavailable.

## Cleanup

Agent requests create no cloud resources. Unset scoped shell values after the workflow:

```bash
unset SKILL_SESSION_ID SKILL_VERSION
```

The script removes its temporary stream directory and terminates its child CLI process on exit or interruption.

## Command Tables

See [references/related-commands.md](references/related-commands.md) for the DAS readonly command and local dependency validation commands.

## Best Practices

1. Prefer the matching product-specific source when the product is known; keep RDS and genuinely generic requests on `yaochi-console`. Avoid more than 2 concurrent calls per account/source.
2. Use the agent for readonly analysis and recommendations; resource changes are outside this release.
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
| [references/manifest.json](references/manifest.json) | Skill version used in every cloud API User-Agent |
| [references/related-apis.md](references/related-apis.md) | API fields, source routes, response events, and readonly contract |
| [references/related-commands.md](references/related-commands.md) | DAS readonly command and dependency checks |
| [references/ram-policies.md](references/ram-policies.md) | Least-privilege RAM actions and failure handling |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI, plugin, jq, and credential setup |
| [references/verification-method.md](references/verification-method.md) | Static, fake-stream, dry-run, and live readonly verification |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct and incorrect implementation patterns |
