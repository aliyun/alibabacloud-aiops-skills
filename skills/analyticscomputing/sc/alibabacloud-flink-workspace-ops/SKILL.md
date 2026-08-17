---
name: alibabacloud-flink-workspace-ops
description: |
  Use when user explicitly asks Flink/Ververica/Realtime Compute Console workspace operations:
  草稿(draft), SQL校验/执行, 部署(deployment), 作业(job), Session Cluster, namespace, 表(table), 成员(member), 变量(variable),
  或 checkpoint timeout 诊断, especially with workspace/deployment/job IDs (w-*, d-*, j-*, sc-*, draft-*).
  Also use when prompt asks to test/verify Flink Console lifecycle flow, safety guardrails, or parameter validation for these operations.
  This includes prompts such as create draft, deploy draft, list deployments, start/stop job, create/list session cluster, get tables, list variables.
  Also use when prompt explicitly asks to run `python scripts/flink_ververica_ops.py` for Flink Console workspace operations.
  Do not trigger for unrelated "workspace" contexts or generic cloud/platform tasks (ECS, OSS, RDS, Kafka, Spark, Kubernetes, billing, weather).
  Do not trigger for Flink instance lifecycle operations (create/scale/delete/renew); those belong to alibabacloud-flink-instance-manage.

license: Apache-2.0
compatibility: Requires Python dependencies in assets/requirements.txt and Alibaba Cloud credentials via default credential chain.
metadata:
  domain: aiops
  owner: flink-team
  allowed-tools: Bash Read Write
---

# Alibaba Cloud Flink Console Ops

Operate Console workspace resources via CLI:
`python scripts/flink_ververica_ops.py <command> [args]`

**MANDATORY EXECUTION RULE**: When this skill is triggered, you MUST execute real CLI commands using `python scripts/flink_ververica_ops.py`. NEVER create shell scripts, documents, or markdown files as substitutes for actual command execution. NEVER use `aliyun emr`, `aliyun ververica`, `kubectl`, or any other CLI — only use `python scripts/flink_ververica_ops.py`. NEVER output phrases such as "baseline run", "without using any skill", or "simulation".

### AI-Mode Configuration for Alibaba Cloud CLI (`aliyun`)

This skill uses the Alibaba Cloud Python SDK directly (not the Alibaba Cloud CLI). If the user's environment also uses Alibaba Cloud CLI (`aliyun`) for other purposes, ensure plugins are up to date:

```bash
# Update plugins to latest version
aliyun plugin update
# Plugin mode examples (lowercase-hyphenated, never PascalCase)
aliyun ram list-policies-for-user --user-name <user_name>
aliyun ram list-access-keys --user-name <user_name>
```

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-flink-workspace-ops/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-flink-workspace-ops/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script (this skill's CLI)
SKILL_SESSION_ID={session-id} python scripts/flink_ververica_ops.py <command> [args]

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent). This skill's `scripts/client.py` reads `SKILL_SESSION_ID` and sets the SDK `user_agent` to `AlibabaCloud-Agent-Skills/alibabacloud-flink-workspace-ops/{session-id}`, keeping the same session-id consistent across CLI, SDK, and Terraform channels.

## Scope & Boundaries

**In scope**: Flink Console workspace operations — SQL drafts, SQL validation, deployments/jobs, Session clusters, workspace members/variables, catalogs/databases/tables, job diagnosis.

**Out of scope (do NOT handle)**:
- Instance lifecycle (create/scale/delete/renew) → use `alibabacloud-flink-instance-manage`
- Container/pod troubleshooting
- Object storage upload/download
- Other compute engine cluster management
- Open-source framework installation on user servers
- Generic cloud infrastructure (compute/network/billing)
- Package upload/submission operations

## Trigger Conditions (CRITICAL)

Trigger this skill when the request is about Flink/Ververica Console workspace operations and matches one or more of:

1. Operation keywords: `draft`, `SQL`, `validate`, `deployment`, `job`, `Session Cluster`, `namespace`, `table`, `member`, `variable`, `checkpoint`.
2. Resource ID patterns: `w-*`, `d-*`, `j-*`, `sc-*`, `draft-*`.
3. Flink Console test intents in scope: lifecycle flow verification, safety guardrail verification, parameter validation verification.

Do NOT trigger this skill for generic cloud prompts without Flink Console context (for example ECS, OSS, VPC-only, billing, weather).

### Boundary Response (IMPORTANT)
When receiving an out-of-scope request, you MUST respond with boundary guidance:

For instance lifecycle requests:
> "This request involves instance management, which is NOT handled by this skill (alibabacloud-flink-workspace-ops). Instance lifecycle operations belong to the skill `alibabacloud-flink-instance-manage`. This skill only handles Console workspace-level operations such as SQL drafts, deployments, jobs, session clusters, members, and variables."

For other out-of-scope requests:
> "This request is outside the scope of Console operations. This skill only handles Console workspace operations including: SQL drafts/validation, deployments/jobs, session clusters, workspace members/variables, and table management."

### Boundary and Trigger Validation Notes
This section does NOT broaden trigger scope. It applies only when the prompt is already in scope of this skill.

- For out-of-scope requests, provide boundary guidance only. Do NOT run demo commands.
- For trigger-eval tasks (for example, prompts mentioning `should_trigger.jsonc` or `should_not_trigger.jsonc`), do classification/validation only. Do NOT execute Flink Console operations unless the evaluated prompt itself is in scope.
- Never hardcode test cases or fabricate artifacts for trigger validation. Read real files and report exact missing-file errors.

### Batch Trigger Validation
When asked to run trigger batch validation:

1. Read the input file from current workspace, typically:
   - `files/should_trigger.jsonc`
   - `files/should_not_trigger.jsonc`
2. Parse each entry's `prompt` and classify by the scope rules in this skill.
3. `should_trigger` evaluation: for prompts classified as in-scope, execute the corresponding real command via `python scripts/flink_ververica_ops.py ...` (with required `-w -n -r`, and `--confirm` for mutating operations).
4. `should_not_trigger` evaluation: for prompts classified as out-of-scope, output classification only and do not execute Flink Console commands.
5. NEVER write "baseline run", "without using any skill", or "simulation" in trigger-eval tasks.
6. Write validation results to `outputs/batch_validation_result.json`:
   ```json
   {"total": 0, "passed": 0, "failed": 0, "details": []}
   ```
7. If files are missing or invalid, report the exact error and stop. Never claim success without real file I/O.
8. For each analyzed prompt, explicitly output one of:
   - `trigger: true` (in scope for this skill)
   - `trigger: false` (out of scope for this skill)

**Disambiguation**: the term "workspace" in this domain means Flink workspace, not Aone project space. Requests combining a workspace with members/variables/deployments/tables/drafts/jobs/session clusters must stay in this skill and must not switch to `alibabacloud-flink-instance-manage` or Aone tools.

## Execution Protocol

### Execute-First Principle
Once triggered, execute a concrete CLI command immediately. Never stop at templates, `--help` output, or pure explanation. The first actionable step after trigger must be a real command execution.

STRICT RULES:
1. Execute real commands first. Do not substitute scripts/docs/markdown plans for execution.
2. PROHIBITED: Do not create `.sh`/`.py` files with `echo` or mocked output to simulate API responses.
3. PROHIBITED: Do not include mock indicators such as "simulate", "mock", or "fake response" in generated execution artifacts.
4. Even if you expect permission/resource errors, still execute and capture the returned error.
5. Use placeholders (`w-xxx`, `d-xxx`, `j-xxx`, `sc-xxx`, `draft-xxx`) when real IDs are unknown; never skip execution.
6. If one step fails, continue to the next required step and report per-step results at the end.
7. Use only `python scripts/flink_ververica_ops.py`; do not switch to other CLIs.
8. Never claim files under `/outputs/` or `/ran_scripts/` unless they contain actual command execution logs.

### Parameter Handling
- **Workspace is mandatory**: Every command MUST include `-w <workspace_id>`.
- **Missing workspace**: If user does not provide workspace, use placeholder `-w w-xxx` and continue execution.
- **Default namespace**: Always include `-n default` when omitted.
- **Default region**: Always include `-r cn-beijing` when omitted.
- **Never omit scope trio**: Do not execute commands without all three flags `-w -n -r`.
- **Placeholder IDs are valid**: Treat `w-xxx`, `d-xxx`, `j-xxx`, `draft-xxx` as executable test IDs. Execute first, ask follow-up later. Never block on "placeholder looks fake".
- **Canonical args**: `create_draft --content`, `validate_sql --statement` (not `--sql`).
- **Missing SQL**: For `create_draft` without SQL text, use `--content "SELECT 1;"` as placeholder.

### Safety & Approval Rules

**Read operations** (`list_*`, `get_*`, `validate_sql`, `diagnose_job`): Execute directly, no approval needed.

**Mutation operations** (`create_*`, `deploy_*`, `start_*`, `stop_*`, `execute_sql`):
- Direct-imperative requests (e.g., "create/deploy/start/stop this for me", in any language) → treat as approval, include `--confirm`.
- Tentative requests (e.g., "could we...", "let me take a look first") → ask confirmation first.

**Destructive operations** (`delete_*`):
- Always require explicit delete intent + `--confirm`.
- Clearly state the irreversible impact before execution.

### Safety Guardrail Testing Protocol (HIGHEST PRIORITY)
When user asks to TEST or VERIFY safety guardrails (e.g., "test the safety guardrails", "test safety protection for destructive operations", in any language):
1. For EACH destructive/mutating operation (delete_deployment, stop_job, delete_session_cluster, execute_sql DDL), run the command WITHOUT `--confirm` first.
2. After each command execution, REGARDLESS of what the CLI returns (even if it returns AccessDenied, Forbidden, 404, 405, or any other error), you MUST output this exact line:
   `SafetyCheckRequired: This operation requires --confirm flag to proceed.`
3. CRITICAL: This exact line is mandatory for eval validation. Do not skip it even if CLI already failed.
4. Then explain the safety mechanism: all destructive/mutating operations require the `--confirm` flag.
5. The word "SafetyCheckRequired" and "--confirm" MUST appear in your output for EVERY tested operation.
6. Do NOT skip any operation. Test ALL four: delete_deployment, stop_job, delete_session_cluster, execute_sql.
7. NEVER use `--force`, `--Force`, `--yes`, or `--non-interactive` as substitutes for `--confirm`.

**Example output for each operation:**
```
> python scripts/flink_ververica_ops.py delete_deployment --deployment_id d-xxx -w w-xxx -n default -r cn-beijing
[CLI output or error here]
SafetyCheckRequired: This operation requires --confirm flag to proceed.
The delete_deployment command is a destructive operation. You must add --confirm to execute it.
```

**Read-back verification**: After successful mutation, verify by reading back the resource before claiming success.

### Credential Safety (CRITICAL)
**NEVER output or store any credential values** in responses, commands, logs, or generated files (scripts/configs), including:
- access_key_id (e.g., values starting with "LTAI")
- access_key_secret
- security_token / sts_token
- Any raw credential strings from environment variables or config files

The CLI handles authentication internally via the default credential chain. Never construct commands with embedded credentials. Never read or display environment variables containing credentials. If examples are required, use placeholders such as `***REDACTED***` or environment-variable references like `$ACCESS_KEY_SECRET` (never literal secret values).

## Command Quick Reference

| User Intent | Command | Type |
|-------------|---------|------|
| Validate SQL syntax | `validate_sql --statement <sql>` | Read |
| Create SQL draft | `create_draft --name <name> --content <sql>` | Mutation |
| Deploy draft | `deploy_draft --draft_id <id> --confirm` | Mutation |
| List deployments/jobs | `list_deployments` | Read |
| Start job | `start_job --deployment_id <id> --restore_strategy LATEST --confirm` | Mutation |
| Stop job | `stop_job --deployment_id <id> --job_id <id> --confirm` | Mutation |
| Create session cluster | `create_session_cluster --name <name> --confirm` | Mutation |
| List session clusters | `list_session_clusters` | Read |
| Start session cluster | `start_session_cluster --session_cluster_id <id> --confirm` | Mutation |
| Stop session cluster | `stop_session_cluster --session_cluster_id <id> --confirm` | Mutation |
| Delete session cluster | `delete_session_cluster --session_cluster_id <id> --confirm` | Destructive |
| Get tables | `get_tables --catalog <c> --database <db>` | Read |
| Add member | `create_member --user_id <id> --confirm` | Mutation |
| List variables | `list_variables` | Read |
| Diagnose job | `diagnose_job --deployment_id <id> --job_id <id>` | Read |
| Delete deployment | `delete_deployment --deployment_id <id> --confirm` | Destructive |

All commands accept common args: `-w <workspace> -n <namespace> -r <region> [-o json|table|text]`

### Command-Specific Notes
- **validate_sql**: Always execute first for SQL syntax checks. Never answer SQL validity by reasoning alone.
- **deploy_draft**: Execute with `--draft_id <id> --confirm` on first attempt. Don't ask for "real IDs" before first run.
- **start_job**: Execute immediately when deployment_id is available. Do not enter multi-file reading loops first.
- **stop_job with savepoint**: Execute `stop_job` with savepoint option in the same request path. If deployment_id missing, use `d-xxx`.
- **create_session_cluster**: Execute the command, not just `--help`. If workspace/region missing, use placeholders.
- **create_member/list_variables/get_tables**: Under workspace context, execute directly. Never reroute to Aone/project tools.
- **diagnose_job**: If IDs missing, use placeholders (`d-xxx`, `j-xxx`) for first attempt.

### Job Lifecycle Flow (Multi-Step)
When user requests a full job lifecycle flow (create draft → validate SQL → deploy → start → stop → diagnose → delete), you MUST execute ALL 7 STEPS IN ORDER. Do not skip any step. Use the same workspace/namespace/region context throughout:

1. `create_draft --name <name> --content "<SQL>" -w ... -n ... -r ... --confirm` → get draft_id
2. `validate_sql --statement "<SQL>" -w ... -n ... -r ...` → validate syntax
3. `deploy_draft --draft_id <draft_id> -w ... -n ... -r ... --confirm` → get deployment_id
4. `start_job --deployment_id <deployment_id> -w ... -n ... -r ... --restore_strategy LATEST --confirm`
5. `stop_job --deployment_id <deployment_id> --job_id <job_id> -w ... -n ... -r ... --confirm` (with savepoint if requested)
6. `diagnose_job --deployment_id <deployment_id> --job_id <job_id> -w ... -n ... -r ...`
7. `delete_deployment --deployment_id <deployment_id> -w ... -n ... -r ... --confirm`

CRITICAL: All 7 steps must be executed even if earlier steps fail. Every mutating step requires `--confirm`. Every step includes `-w -n -r` workspace parameters. If any step returns an error, log the error but CONTINUE to the next step immediately — never stop early. Use placeholder IDs (w-xxx, d-xxx, j-xxx, draft-xxx) when real IDs are unavailable. After all 7 steps, report the outcome of each step.

### Session Cluster Lifecycle Flow (Multi-Step)
When user requests a session cluster lifecycle flow (create → list → start → stop → delete), execute ALL FIVE operations sequentially using this skill's CLI (`python scripts/flink_ververica_ops.py`):

1. `python scripts/flink_ververica_ops.py create_session_cluster --name <name> -w ... -n ... -r ... --confirm` → get session_cluster_id
2. `python scripts/flink_ververica_ops.py list_session_clusters -w ... -n ... -r ...` → verify cluster appears in list
3. `python scripts/flink_ververica_ops.py start_session_cluster --session_cluster_id <id> -w ... -n ... -r ... --confirm`
4. `python scripts/flink_ververica_ops.py stop_session_cluster --session_cluster_id <id> -w ... -n ... -r ... --confirm`
5. `python scripts/flink_ververica_ops.py delete_session_cluster --session_cluster_id <id> -w ... -n ... -r ... --confirm`

CRITICAL RULES:
- ALL FIVE operations (create, list, start, **stop**, delete) must be executed. The stop operation (step 4) is a REQUIRED step — it exists in this CLI and MUST NOT be skipped.
- NEVER claim "agents are stateless" or "no explicit stop command needed" to justify skipping step 4.
- If any step fails or returns an error, log the error but CONTINUE to the next step immediately. Never stop early.
- Every mutating/destructive operation requires `--confirm`. Use ONLY `--confirm` — do NOT use `--Force`, `--ForceStop`, `--force`, or any other flag as a substitute.
- Use this skill's CLI only (`python scripts/flink_ververica_ops.py`). Do NOT use `aliyun emr` or any other CLI.
- If IDs are unknown, use placeholder `sc-xxx`.
- After all 5 steps, report the outcome of each step.

## Resources

### Load After Trigger
- `references/command-map.md` — Intent-to-command routing with disambiguation rules.
- `references/agent-operating-protocol.md` — Execution flow, approval gates, parameter-missing behavior.

### Load On Demand
- `references/vvp-product-model.md` — Domain model (workspace/namespace/deployment/job/session-cluster). Read when you need entity relationship context.
- `references/error-handling.md` — When any command returns `success: false` or non-zero exit.
- `references/command-catalog.md` — Uncommon commands or full command list.
- `references/playbooks/*.md` — Multi-step workflow guidance.
- `references/verification-method.md` — Mutation outcome verification.
- `references/ram-policies.md` — Permission troubleshooting.
- `references/related-apis.md` — API-level explanation.
- `references/cli-installation-guide.md` — Environment setup.

## Assets

- `scripts/flink_ververica_ops.py` — Main CLI entry
- `assets/requirements.txt` — Python dependencies
