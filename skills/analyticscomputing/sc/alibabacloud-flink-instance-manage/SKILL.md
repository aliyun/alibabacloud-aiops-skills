---
name: alibabacloud-flink-instance-manage
description: >
  Use when asked to create or query Alibaba Cloud Flink instances, create or
  list Flink namespaces, list supported Flink regions or availability zones, or
  query Flink resource tags. For Flink AI service, use only when the operation
  directly targets the account's regional service to query its status or free
  quota and usage, activate or deactivate the service, or query or change its
  closure protection (deletion protection).
license: Apache-2.0
compatibility: >
  Requires Python dependencies from assets/requirements.txt, valid Alibaba Cloud
  credentials, and network access to Flink OpenAPI (2021-10-28). Aliyun CLI is
  optional and only used for environment diagnostics/credential inspection.
metadata:
  domain: aiops
  owner: flink-team
  contact: flink-team@alibaba-inc.com
---

# Alibaba Cloud Flink Instance Manage

Use one script to manage Alibaba Cloud Flink instances, namespaces, and regional Flink AI services.

## Scope and Entrypoint

- Always run operations through:
  ```bash
  python scripts/instance_ops.py <command> [options]
  ```
- Instance, namespace, and discovery commands include `create`, `create_namespace`, `describe`, `describe_regions`, `describe_zones`, `describe_namespaces`, and `list_tags`.
- AI service commands include `get_flink_ai_service`, `get_flink_ai_service_free_quota`, `open_flink_ai_service`, `close_flink_ai_service`, and `modify_ai_service_protection`.
- Instance or namespace updates and deletions, Flink SQL and job operations, AI assistant conversations, intelligent patrol, and other cloud products are outside this skill's scope.

## Trigger Rules

Match the requested action and its target to a command below. For Flink AI service, the action must match a service management command and directly target the regional service or its closure protection. Route by the requested action when Flink AI service is mentioned as the location of a feature. Use the Flink workspace operations skill for ordinary job troubleshooting and the Flink AI operations skill for cloud AI assistant conversations, assistant diagnosis, and intelligent patrol or its reports.

- Positive intent examples:
  - "Create a Flink instance in cn-beijing"
  - "List Flink instances and status"
  - "Describe namespaces for instance f-cn-xxx"
- Chinese trigger examples:
  - "查询 Flink 实例标签"
  - "Flink 可用区有哪些"
  - "查询杭州的 Flink AI 服务是否开通"
  - "查看 Flink AI 服务的免费额度使用情况"
  - "在上海开通 Flink AI 服务"
  - "关闭北京的 Flink AI 服务"
  - "开启 Flink AI 服务的关闭保护"
- Negative intent examples:
  - ECS/Kafka/OSS/DataWorks operations
  - Generic questions (weather, translation, etc.)
  - Flink SQL, job authoring or runtime tuning, and ordinary job troubleshooting such as checkpoint timeouts. Use the Flink workspace operations skill.
  - Cloud AI assistant conversations or diagnosis. Use the Flink AI operations skill for requests such as "用 Flink AI 服务里的云端智能助手诊断我的作业为什么检查点超时。"
  - Intelligent patrol or patrol reports. Use the Flink AI operations skill for requests such as "查询 Flink AI 服务里的智能巡检报告。"
- Ambiguous prompts:
  - Ask one clarification question: instance/namespace management vs SQL/job operations.
  - Clarify whether "开启 AI" refers to activating the regional Flink AI service, using the AI assistant, or configuring patrol.

## Intent to Command Mapping

Initialize `SKILL_SESSION_ID` and `SKILL_VERSION` before running an AI service command. [Session setup](#initialize-the-session)

| User intent | Command |
|---|---|
| Query all instances in a region | `describe --region_id <REGION>` |
| Create instance | `create ... --confirm` |
| Query namespaces under an instance | `describe_namespaces --region_id <REGION> --instance_id <ID>` |
| Create namespace | `create_namespace ... --confirm` |
| Query supported regions/zones | `describe_regions` / `describe_zones --region_id <REGION>` |
| Query tags | `list_tags --region_id <REGION> --resource_type <TYPE> [--resource_ids ...]` |
| Query Flink AI service status | `get_flink_ai_service --region_id <REGION>` |
| Query Flink AI service free quota | `get_flink_ai_service_free_quota --region_id <REGION>` |
| Activate Flink AI service | `open_flink_ai_service --region_id <REGION> --confirm` |
| Deactivate Flink AI service | `close_flink_ai_service --region_id <REGION> --confirm` |
| Change closure protection | `modify_ai_service_protection --region_id <REGION> --deletion_protection <BOOL> --confirm` |

## Operating Rules

1. **Confirm write operations**
   - Confirm the target and parameters before creating instances or namespaces. Pass `--confirm` when running the command.
   - For AI service activation, deactivation, and either direction of a closure protection change, follow the [AI service write authorization](#ai-service-write-authorization) procedure.
2. **Verify changes with a follow-up query**
   - After the API accepts the request, query the resource to verify that it reached the requested state.
3. **Retry policy is strict**
   - Maximum 2 attempts for the same command (initial + one corrected retry).
4. **No automatic operation switching**
   - If an operation fails, do not switch to a different operation without user approval.
5. **Lifecycle target lock**
   - In `create -> create_namespace` flow, namespace must target the same newly created `InstanceId` unless user approves fallback.
6. **Namespace pre-check is required**
   - Before `create_namespace`, check instance status/resources and existing namespace allocation.
7. **No secret exposure**
   - Do not output or request plaintext AK/SK. Use default credential chain guidance.
8. **Do not invent parameters**
   - Never fabricate VPC/VSwitch/instance IDs.
9. **Keep auditable confirmation evidence**
   - Lifecycle outputs must contain `SafetyCheckRequired` or explicit `--confirm` evidence.
10. **No partial-completion claims for lifecycle flows**
   - For flows requiring both `create` and `create_namespace`, overall status can be `completed` only when both create operations succeed.
11. **No automatic capacity scaling**
   - If `create_namespace` fails due to insufficient resources, report it clearly and ask user to manually scale resources outside this skill scope.

## RAM Authorization

Check the required permissions in the [RAM reference](references/ram-policies.md#flink-ai-service).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If the file is missing, invalid, or the field is absent/empty/not a string, STOP and report the error. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. When switching skills or returning to this skill, reread this skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag below to every actual execution, including commands generated or extended at runtime; do not repeat UA boilerplate in every example block.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-flink-instance-manage/{session-id} skill-version/{skill-version}"
```

The entire UA value MUST be double-quoted because it contains a space. Do not skip, alter, or omit it on any `aliyun` API command.

### Initialize the Session

Run the following from the skill root before this skill's first cloud API request in a conversation.

```bash
SKILL_VERSION="$(python3 -c '
import json
with open("references/manifest.json", encoding="utf-8") as manifest:
    data = json.load(manifest)
version = data.get("version") if isinstance(data, dict) else None
if not isinstance(version, str) or not version.strip():
    raise SystemExit("Invalid skill version in references/manifest.json")
print(version)
')" &&
SKILL_SESSION_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')" &&
export SKILL_VERSION SKILL_SESSION_ID
```

If initialization fails, stop and report the error. Run subsequent commands in the same shell or pass both values when using a separate shell. When returning to this skill, rerun the version lookup and reuse the session ID generated for this skill in the current conversation.

**Python SDK execution**

Pass both scoped values to `scripts/instance_ops.py` to construct the same User-Agent. AI service commands require both values. Confirm the region before running the command.

```bash
SKILL_SESSION_ID="$SKILL_SESSION_ID" SKILL_VERSION="$SKILL_VERSION" \
  python3 scripts/instance_ops.py get_flink_ai_service --region_id "$FLINK_REGION"
```

## Execution Protocol

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

### Step 1: Classify request
- Match the requested Flink instance, namespace, tag, region, zone, or AI service operation to a command above.
- Out-of-scope or non-Flink -> reject or route with explanation.

### Step 2: Validate parameters
- Apply `references/parameter-validation.md`.
- If required parameters are missing, ask user or return clear remediation.
- AI service commands target the Alibaba Cloud account associated with the current credentials and the explicitly specified region. Validate the target using the [AI service guide](references/flink-ai-service.md).

### Step 3: Execute command
- Query commands: run once unless transient query error.
- Check for `--confirm` before running a write command.
- For a real AI service write, apply the authorization procedure below before adding `--confirm` or sending the API request.

### AI Service Write Authorization

1. Query the current state in the user-confirmed region. Present the Alibaba Cloud account, region, current state, exact proposed operation, and its impact. For a protection change, include the current and requested protection settings.
2. Ask the user to authorize that specific write and wait for an explicit affirmative response to the plan. The initial request starts this approval process. Keep the write pending if the reply is absent, ambiguous, or declines approval.
3. Pass `--confirm` only for the approved write. Obtain separate approval for any subsequent write, including closing the service after disabling protection. Recheck the state before requesting approval to retry after an uncertain result.

### Step 4: Verify changes with a follow-up query
- For `create`: verify with `describe --region_id <REGION>`.
- For `create_namespace`: verify with `describe_namespaces --region_id <REGION> --instance_id <ID>`.
- After an AI service change, run `get_flink_ai_service` in the same region. Verify `RUNNING` after activation, `CLOSED` after deactivation, or the requested `DeletionProtection` value after changing protection.
- Use up to 3 read checks with short backoff before concluding the create is not reflected yet.
- For chained `create -> create_namespace`:
  - poll `describe --region_id <REGION>` on the same `InstanceId` every 30 seconds
  - max wait: 10 minutes
  - if still not `RUNNING`, stop and provide next action (wait/retry later)
  - do not switch to another instance without explicit user approval
  - if namespace create fails, mark lifecycle chain as `failed`/`not_ready`, not `completed`
  - for `InsufficientResources`, ask user to manually scale the instance and retry later

## Key References

- Start here:
  - `references/README.md`
  - `references/quick-start.md`
  - `references/trigger-recognition-guide.md`
  - `references/core-execution-flow.md`
  - `references/command-templates.md`

| Document | Purpose |
|----------|---------|
| `references/parameter-validation.md` | Pre-execution validation checklist |
| `references/e2e-playbooks.md` | Complete execution sequences |
| `references/common-failures.md` | Typical mistakes and fixes |
| `references/required-confirmation-model.md` | Confirmation gate rules |
| `references/instance-state-management.md` | Instance state and readiness checks |
| `references/output-handling.md` | Output parsing and retry policy |
| `references/verification-method.md` | Verification patterns after create/query |
| `references/acceptance-criteria.md` | Completion checklist for normal operations |
| `references/python-environment-setup.md` | Python dependency and auth setup |
| `references/cli-installation-guide.md` | Aliyun CLI diagnostics setup |
| `references/ram-policies.md` | Required RAM permissions |
| `references/related-apis.md` | API and command mapping |
| `references/flink-ai-service.md` | AI service commands, billing, deactivation impact, and status verification |

## Output Format

The script writes operation results as JSON to stdout.
```json
{
  "success": true,
  "operation": "<command>",
  "confirmation_check": {
    "required_flag": "--confirm",
    "provided": true,
    "status": "passed"
  },
  "data": {},
  "request_id": "..."
}
```

`confirmation_check` records the presence of `--confirm` for instance and namespace creation, AI service activation and deactivation, and closure protection changes. The agent obtains the human authorization separately for each real AI service write.

Exit code `0` indicates success and `1` indicates an operation error. Argument parsing errors print usage information to stderr and exit with code `2`.
