---
name: alibabacloud-dsc-column-encryption
description: "Help users protect sensitive database columns and control who can view plaintext in Alibaba Cloud Data Security Center (DSC). Use when users ask to find columns by region, asset type, encryption state, classification template, model or sensitivity level; enable or disable column encryption; change database-account access or expiry; choose an encryption algorithm or KMS key; synchronize assets; or upgrade a database kernel for column encryption. Applies to the DSC column-encryption console and Sddp 2026-01-20 architecture."
---

# DSC Column Encryption

Use the bundled Python scripts to select targets, run read-only preflight checks, and verify results. All online requests use an explicit Alibaba Cloud CLI profile: OAuth, AK, StsToken or RamRoleArn. Coverage: 25 `Sddp/2026-01-20` actions (19 queries and 6 changes), plus KMS `DescribeKey` for key inspection. See [api-contract.md](references/api-contract.md).

Console entry: <https://yundun.console.aliyun.com/?p=sddp#/DE/cn-zhangjiakou>. The linked region is a starting point, not a fixed region for all operations. Prefer the scripts; use the user's chosen browser when page inspection is necessary.

Choose the entry point by intent:

- Queries: `scripts/query_column_encryption.py`.
- Approved AgentHub bounded discovery evaluation: [discovery-eval.md](references/discovery-eval.md), using `scripts/discover_column_encryption.py`. Other user queries retain their explicit filters and scope.
- Create encryption rules: `scripts/create_column_encryption.py`.
- Delete rules, change account access, change algorithms or keys, synchronize assets, or upgrade kernels: `scripts/manage_column_encryption.py`.

## Resolve the user's scope

Resolve the requested endpoint before choosing commands. A request to explain a workflow or identify the applicable capability ends with an explanation; it does not authorize discovery, preflight or submission. An offline draft ends after local validation, without inspecting authentication. If the user only asks what information is missing, list that information and stop. When an interactive clarification is needed, ask once and wait for the user's answer; an answer declining further work ends the workflow.

An operation mentioned in a supplied historical response is evidence to interpret, not a new operation to submit. For an explanation-only request, interpret that record without replaying its query, preflight or write. Distinguish a historical `FinalState` being discussed from the outcome of a request actually submitted in this workflow.

Users may describe console conditions directly, for example, "张家口金融行业模板下 RDS 的 S3 以上未加密列" or "把指定实例的 app_user 改为明文权限，保留到期时间". Map those conditions using [console-workflows.md](references/console-workflows.md). Resolve template, level and model IDs from query results instead of asking users to guess them.

`UserList[].AccountId` must be the database account name returned as `ListDataAssetAccounts.Items[].AccountName`, not the record's numeric `Id`. Verify the account against the specific product and instance.

Preserve every supplied filter. For combined queries, select-all requests and bulk operations, verify pagination completeness; never describe the first page or a truncated result as all targets. Build an exact instance/column/account plan before preflight. Query filters do not restrict instance-wide account, algorithm or key changes.

## Runtime and permissions

Follow [runtime-constraints.md](references/runtime-constraints.md) for Python 3.10+, Alibaba Cloud CLI 3.4.10+ (or exactly 3.3.23 with a preconfigured StsToken profile), and credential setup performed by the user or trusted platform outside the agent session. OAuth remains the recommended interactive setup. AK/SK, STS temporary credentials and RamRoleArn are also supported through named CLI profiles; do not ask users to paste credentials into chat. The scripts use only the Python standard library; no SDK installation is needed. All three entry points accept `--profile`, defaulting to `dsc-oauth`. Use the same profile and authentication mode throughout query, preflight and execution. Replace `dsc-oauth` in the examples with the user's selected profile for other modes.

Read [ram-policies.md](references/ram-policies.md) before online use. It separates query permissions, opt-in change permissions and key-scoped `kms:DescribeKey`. Dependency declarations do not grant permissions. Never attach RAM policies or expand access automatically.

Preserve each script invocation's actual exit status and output. Use the shell tool's working-directory option or an absolute script path; `cd <skill-dir> && python3 ...` is an alternative only when the task permits shell wrapping. If the task requires a bare command, add no wrappers, pipes or redirection; save captured stdout through a separate file operation when requested. If the task requires the initial working directory, leave it unchanged and use an absolute script path. Do not append `echo` or `printf`, use `|| true`, or pipe the invocation in a way that turns a script failure into a successful tool result. A printed exit-code label is not the tool's exit status. Use the tool's exit-status metadata. A log or artifact write failure does not prove that the RPC was not executed. Preserve and reuse the original tool output; never repeat a query, preflight or submission merely to repair logging. If its original output cannot be recovered, stop and report the missing evidence.

On a failed query, stdout may contain validated `HTTPStatus: ...` and `ErrorCode: ...` diagnostic lines; stderr retains the structured JSON error. These fields come from the actual CLI failure. They do not expose the raw error message, request ID, signed URL or credential data, and they do not make the failed command successful.

For creation and other changes, validated `HTTPStatus`/`ErrorCode` diagnostic lines go to stderr while stdout remains the structured JSON event/result stream. Classify a failure from its observed status and code; do not infer a different failing action or an undeclared-call failure merely from a code suffix.

Reports of this workflow's execution describe observed facts, not hypothetical failures or lists of unrelated error codes. Avoid repeating an unobserved error code merely to deny it; any necessary denial must be explicit, supported by the complete current trace and consistent with its indicator. For explanation-only requests, retain the relevant error code supplied by the user and clearly label it as a given or historical scenario, not as a result observed in this workflow. Reading such evidence never authorizes replaying it. When a task requests an undeclared-call indicator, an optional `UnexpectedCommandSeen=false` requires complete evidence from this workflow's actual calls; use `unknown` if the evidence is incomplete. This indicator cannot replace script results or an actual error. Always retain an observed failure's status/code, report what stopped, and follow the existing no-write/no-retry boundaries.

Keep the final answer self-contained across approval turns, including a failed or stopped preflight. A successful preflight awaiting the first required approval is an intermediate state, not a terminal report: present the fresh plan, directly ask whether the user approves that exact scope, and wait for a genuine external reply. Do not treat your own question, planned approval, or a completed task-plan item as approval. Use this closing order only when the requested workflow has reached its endpoint, including refusal or an actual execution blocker:
1. Finish only the requested and permitted execution steps. Retain their original stdout, stderr and actual tool exit status; do not rerun a step to format its report.
2. Prepare and check the complete report against retained outputs, save requested artifacts, then finish task-plan bookkeeping. If using a plan tool, define its last item as preparing and checking the report, not sending it; complete that item before the final response. Completing this item does not make a failed business operation successful.
3. Send the complete terminal report as the last response, with no tools or completion notice afterward: the actual local Mode/Executable and DraftPlan scope, the approved effective scope when applicable, then the observed final result and verification. Include every requested field even if an earlier approval turn or file already contains it. If bookkeeping was mistakenly performed after an earlier report, the final response must still contain the complete report from retained outputs, without rerunning anything. An artifact link, “all steps completed” summary or file-saved message is not a substitute.

Use the requested field names exactly. For machine-checked fields, prefer one JSON object with each key assigned once on its own line; retain native booleans, nulls, arrays and objects. Put explanations and source paths outside it without repeating key=value assignments with annotations. An explicitly returned false or null is a value, not a missing field. Report absent fields as missing; never fill Observed* from the plan, the prompt or expected results. For synchronization, inspect the final result's root Action and Verification. Optional undeclared-call commentary can be omitted; when required, determine its value from the complete actual trace and do not repeat that scalar assignment in prose. After an error, explicitly state whether a write was submitted and whether a retry occurred, in the requested language (for example, “No write was submitted. No retry.” when the trace supports both). This reports execution facts without inventing a write FinalState for an operation that was never sent. Label calculated query statistics as derived and identify their actual source fields.

For read-only queries, a requested `RegionId` or `InstanceId` can describe request scope rather than a returned field. Echo its exact value from that step's actually executed command as `RegionId=value` / `InstanceId=value`, and label `ScopeSource=executed-command` (or equivalent prose), even if stdout does not echo it. Explain a missing response echo separately; do not replace the key/value assignment with that explanation. This exception does not authorize taking values from a plan, prompt, unexecuted command or another step. Business results and `Observed*` must still come from actual script stdout; report missing when absent.

The release version comes from [manifest.json](references/manifest.json). The shared transport adds this user agent to every DSC and KMS request:

```text
AlibabaCloud-Agent-Skills/alibabacloud-dsc-column-encryption/{session-id} skill-version/{version}
```

For a workflow spanning multiple script invocations, generate one non-secret 32-character lowercase hexadecimal session ID and pass the same `ALIBABA_CLOUD_SKILL_SESSION_ID` value to each invocation. Do not reuse it for unrelated workflows. Without this override, the transport generates one ID per Python process, shared by DSC and KMS calls in that process. Invalid IDs or missing/invalid manifests stop requests before submission. Do not bypass the transport or hardcode a version in a command. For a single-script task requiring a bare command, start with `python3` and rely on that per-process ID rather than adding an environment-assignment prefix. Preserve any legitimate inherited binding; this does not authorize setting, clearing or changing Mock switches, profiles or credentials.

## Read-only queries and target selection

Choose the query for the requested object. For the eligibility of one known instance, use `check-instance`; `page` is the broader overview and statistics query, not a prerequisite for that check. For database-account access, expiry or account-name searches, use `accounts`; this does not require selecting columns with `masking-columns`. Preserve the requested filters and page budget. See [query-guide.md](references/query-guide.md) for these commands and their exact arguments.

For an authorized online query with an available selected profile, when the instance, database, table, columns or `TemplateId` are incomplete, discover them in this order. These commands are read-only and do not require production-write confirmation. They are not prerequisites for explanation-only, routing-only or offline requests. `<skill-dir>` always means the directory containing this `SKILL.md`, not the user's application repository.

```bash
# 1. Regions and classification templates
python3 <skill-dir>/scripts/query_column_encryption.py regions --profile dsc-oauth
python3 <skill-dir>/scripts/query_column_encryption.py templates --all-pages --profile dsc-oauth

# 2. Instances; choose TemplateId from the preceding query
python3 <skill-dir>/scripts/query_column_encryption.py instances \
  --region-id cn-hangzhou --template-id 123456 --all-pages \
  --profile dsc-oauth

# 3. Databases, tables, then columns
python3 <skill-dir>/scripts/query_column_encryption.py databases \
  --region-id cn-hangzhou --product-code RDS --instance-id rm-xxx --all-pages \
  --profile dsc-oauth
python3 <skill-dir>/scripts/query_column_encryption.py tables \
  --region-id cn-hangzhou --template-id 123456 --product-code RDS \
  --instance-id rm-xxx --db-name app_db --all-pages \
  --profile dsc-oauth
python3 <skill-dir>/scripts/query_column_encryption.py masking-columns \
  --region-id cn-hangzhou --template-id 123456 --product-code RDS \
  --instance-id rm-xxx --db-name app_db --table-name users --all-pages \
  --profile dsc-oauth
```

Prefer `masking-columns` for final column selection: it includes sensitivity levels, identification models and current encryption states. Use `columns` for the console's all-columns selector. Preserve returned `schema.table` names for PostgreSQL and Oracle.

For overview statistics, filter options, an instance page and each instance's eligibility checks:

```bash
python3 <skill-dir>/scripts/query_column_encryption.py page \
  --region-id cn-zhangjiakou --template-id 123456 \
  --profile dsc-oauth
```

See [query-guide.md](references/query-guide.md) for all commands, console mappings, state semantics and template compatibility.

## Create encryption rules

Choose the terminal branch before following the submission sequence below:

- Explanation or offline draft only: explain or validate locally and stop. Do not run online preflight merely because the described workflow includes it.
- Preflight requested but submission declined: show the returned plan and stop without a write, even if preflight passed and returned a token. Do not repeatedly ask for approval after an explicit refusal.
- Local validation or preflight failed: report the failing stage and error; stop before submission. A parameter correction, another identity or a retry is not implicitly authorized.
- Submission requested: proceed only when validation and preflight pass and the user has approved the exact effective plan. The same branches apply to all operations in **Other changes**.

A stopped workflow has no write `FinalState`: report that no write was submitted and why. Do not invent `SUCCESS`, `FAILED` or another write outcome for a request that was never sent. A hypothetical or supplied historical response is evidence to interpret, not a request to replay the action.

1. Collect and restate the target:
   - Instance `RegionId` and classification `TemplateId`, selected from queries.
   - `ProductCode`: `RDS`, `POLARDB` or `PolarDBX2`; exact `InstanceId`.
   - Database, table and columns; combine columns of the same table in one `Columns` string.
   - Optional algorithm: inherit existing configuration; only a new instance defaults to the first currently available algorithm.
   - Optional key mode: inherit existing mode and key; a new instance defaults to `client_key`. An explicit `kms_key` requires the exact `EncryptionKeyId`, or an existing KMS key inherited during preflight.
   - Optional allowlisted database account names in `UserList[].AccountId`.
   - Optional account-expiry policy: `PRESERVE`, `CLEAR` or `SET`.
2. Create a temporary JSON plan from [config.example.json](references/config.example.json). Store business parameters only, never OAuth tokens or cloud credentials.
3. Validate locally:

   ```bash
   python3 <skill-dir>/scripts/create_column_encryption.py --config /absolute/path/to/plan.json
   ```

   This is the terminal step for an offline draft. Continue to online preflight only when that endpoint is requested and permitted.

4. Run online read-only preflight:

   ```bash
   python3 <skill-dir>/scripts/create_column_encryption.py --config /absolute/path/to/plan.json --preflight --profile dsc-oauth
   ```

   Validate the supplied `TemplateId`, exact columns and accounts, instance eligibility, algorithm availability and KMS key when applicable. Use a separate algorithm/key change for an already-configured instance. Use the returned `EffectivePlan` and `ConfirmationToken`, not a local draft fingerprint.
5. Show the exact region, template, product, instance, every `db.table.column`, effective algorithm, key mode, allowlisted accounts, expiry policy and unique column count. If submission is requested and preflight passed but approval is still missing, directly ask the user to approve or decline this exact plan, then wait for their actual reply. This is an intermediate approval boundary, not a completed submission. Distinguish a permitted simulated plan from a real-cloud write; simulated approval never authorizes a real-cloud write. An explicit refusal ends the workflow without submission.
6. Submit once with the approved preflight token:

   ```bash
   python3 <skill-dir>/scripts/create_column_encryption.py --config /absolute/path/to/plan.json --execute --confirm-token TOKEN --profile dsc-oauth
   ```

7. Report the script's `FinalState`:
   - `SUCCESS`: all target columns are `Success`; instance algorithm/key and specified account access/expiry have also been verified.
   - `FAILED`: at least one column is `Failed`; include its error code and message.
   - `PENDING`: accepted but not fully completed within the observation window; explicitly say processing continues.
   - `UNKNOWN`: the write outcome is uncertain and target records cannot be found; do not retry. Continue read-only checks or ask the user for direction.

## Other changes

Use [write-guide.md](references/write-guide.md) to build a single-operation JSON plan for `DeleteDataMaskingRule`, `UpdateDataMaskingUsers`, `UpdateDataMaskingEncryptionAlgorithm`, `SyncDataAssets` or `UpgradeKernelVersion`.

Choose the same terminal branch described above before using these modes. A local-only request ends after validation; a preflight-only request, refusal or failed preflight has no submission stage.

```bash
# Local-only endpoint: validation without authentication or cloud requests
python3 <skill-dir>/scripts/manage_column_encryption.py --config /absolute/path/to/operation.json

# Online read-only endpoint: preflight, when requested and permitted
python3 <skill-dir>/scripts/manage_column_encryption.py --config /absolute/path/to/operation.json \
  --preflight --profile dsc-oauth

# Write endpoint: submit once, only after successful preflight and explicit approval
python3 <skill-dir>/scripts/manage_column_encryption.py --config /absolute/path/to/operation.json \
  --execute --confirm-token TOKEN --profile dsc-oauth
```

Execution repeats preflight. Changes to target state, effective engine or available versions invalidate the old token. Show the effective scope and impact before seeking approval. Reuse an existing approval only for the same exact plan when renewed preflight confirms its scope and state are unchanged. Creating this skill, querying, or producing a dry-run plan does not authorize changes to live resources.

Interpret results as follows:

- `SUCCESS`: read-only queries observed the intended state.
- `FAILED`: explicit write rejection, or a failed column-deletion state.
- `PENDING`: accepted, but the intended state was not observed within the wait window.
- `ACCEPTED_UNVERIFIED`: asset synchronization only; acceptance is known but this page has no query that proves synchronization completed.
- `UNKNOWN`: uncertain transport outcome that read-only checks could not resolve. Never retry automatically.

## Mandatory safety boundaries

- A successful `CreateDataMaskingRule` response means asynchronous acceptance, not completed encryption.
- Disable CLI automatic retries for every change and submit once. Timeouts or disconnections may occur after acceptance; inspect current state before considering another write.
- In the final answer after an authentication, permission or throttling error, report the observed status/code, what stopped and whether a retry occurred. When no retry occurred, explicitly state that fact in the user's requested language, for example `No retry`; distinguish any read-only verification from resubmitting the failed operation. Report uncertainty when the trace cannot establish this fact.
- Create/delete plans contain one instance. Include all its target sub-rules in one request; do not split them into adjacent requests or modify one instance concurrently. Account-access updates may include multiple instances within one region and product under the public contract.
- `TemplateId` is query context for selection, statistics and verification. It is bound into confirmation tokens but none of the six write APIs exposes it. Never send it to a write API or claim it narrows instance-wide or region/product-wide changes.
- Route with `RegionId` only. Reject legacy `ServiceRegionId` and `BackendRegionId`; do not send private `ResourceGroupId` or `CooperationChannel` fields.
- `SubRuleList[]` sends only `DbName`, `TableName` and `Columns`. Creation `UserList[]` sends only `AccountId`; account-access updates send `AccountId` and `InstanceId`.
- `SET` expiry requires a future Unix timestamp in milliseconds, no later than `2038-01-01T10:10:10Z`. `PRESERVE` and `CLEAR` must not carry `ExpireTime`.
- Verify that the selected profile uses OAuth, AK, StsToken or RamRoleArn before online calls; reject unsupported modes and mode changes within a workflow. Ignore inherited AK/STS environment credentials in every mode. Never switch profiles or modes automatically after login, configuration or permission failures. The CLI owns signing and supported refresh flows; neither scripts nor agents read, export or copy credentials. StsToken credentials do not auto-refresh: stop on expiry and ask the user or trusted platform to renew them outside this session.
- To inspect authentication, run only `python3 <skill-dir>/scripts/aliyun_cli.py --profile dsc-oauth`. It reads the non-secret profile mode, not raw configuration or token fields. Never display raw `aliyun configure list` output. A KMS key ID is a business parameter, but avoid unrelated disclosure.
- Confirmation tokens bind the profile name and authentication mode, not an independently verified account identity. Changing either invalidates the token. If credentials or a role change to another identity under the same profile and mode, rediscover targets and repeat preflight; matching profile metadata is insufficient.
- Requests to query, generate a configuration, assess impact or take a look authorize only dry runs and read-only checks. Asset synchronization and kernel upgrades also require explicit approval of their full scope or availability impact.

## Troubleshooting and references

- API fields and state semantics: [api-contract.md](references/api-contract.md).
- Complete read-only commands: [query-guide.md](references/query-guide.md).
- Non-creation change plans and verification: [write-guide.md](references/write-guide.md).
- Product editions, algorithms, KMS and runtime constraints: [runtime-constraints.md](references/runtime-constraints.md). Documented version thresholds are code defaults; live configuration may override them. Read-only preflight is authoritative.
- `sale_instance_quota_exception`: reduce the requested columns or increase capacity, then repeat preflight. Do not split an instance to bypass quota or concurrency limits.
- `Column is being processed`: continue queries; do not create the same rule again.
- Missing/unsupported CLI, missing profile, expired credentials or denied role assumption: follow the runtime guide. Do not install an SDK or switch credentials as a workaround. [requirements.txt](scripts/requirements.txt) contains no third-party dependencies.
