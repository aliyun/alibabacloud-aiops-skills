---
name: alibabacloud-flink-instance-manage
description: >
  Manage Alibaba Cloud Flink VVP instances and namespaces through create/query
  operations only. Use when user asks to create or query Flink instances,
  namespaces, regions, zones, or tags in Chinese or English. Reject Flink SQL/job
  requests, unrelated cloud services (ECS/Kafka/OSS/DataWorks), and all
  update/delete operations.
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

Operate Alibaba Cloud Flink VVP resources with a strict create/query scope through one wrapper script.

## Scope and Entrypoint

- Always run operations through:
  ```bash
  python scripts/instance_ops.py <command> [options]
  ```
- Allowed commands: `create`, `create_namespace`, `describe`, `describe_regions`, `describe_zones`, `describe_namespaces`, `list_tags`
- Out of scope: update/delete, Flink SQL/job runtime operations, and non-Flink services

## Trigger Rules

Use this skill when prompts are about Flink instance/namespace lifecycle operations.

- Positive intent examples:
  - "Create a Flink instance in cn-beijing"
  - "List Flink instances and status"
  - "Describe namespaces for instance f-cn-xxx"
  - "查询 Flink 实例标签"
  - "Flink 可用区有哪些"
- Negative intent examples:
  - ECS/Kafka/OSS/DataWorks operations
  - Generic questions (weather, translation, etc.)
  - Flink SQL / Flink job authoring or runtime tuning
- Ambiguous prompts:
  - Ask one clarification question: instance/namespace management vs SQL/job operations.

## Intent to Command Mapping

| User intent | Command |
|---|---|
| Query all instances in a region | `describe --region_id <REGION>` |
| Create instance | `create ... --confirm` |
| Query namespaces under an instance | `describe_namespaces --region_id <REGION> --instance_id <ID>` |
| Create namespace | `create_namespace ... --confirm` |
| Query supported regions/zones | `describe_regions` / `describe_zones --region_id <REGION>` |
| Query tags | `list_tags --region_id <REGION> --resource_type <TYPE> [--resource_ids ...]` |

## Operating Rules

1. **Confirmation is mandatory for create commands**
   - `create` and `create_namespace` must include `--confirm`.
2. **Verify create results with read-back**
   - Do not conclude success from create response alone.
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

## Execution Protocol

### Step 1: Classify request
- In-scope create/query for Flink instance/namespace/tag/region/zone -> continue.
- Out-of-scope or non-Flink -> reject or route with explanation.

### Step 2: Validate parameters
- Apply `references/parameter-validation.md`.
- If required parameters are missing, ask user or return clear remediation.

### Step 3: Execute command
- Query commands: run once unless transient query error.
- Create commands: construct final command string and verify `--confirm` is present before execution.

### Step 4: Verify create outcomes
- For `create`: verify with `describe --region_id <REGION>`.
- For `create_namespace`: verify with `describe_namespaces --region_id <REGION> --instance_id <ID>`.
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

## Output Format

All commands return JSON:
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

`confirmation_check` appears on create operations and is used for auditable safety evidence.

Exit codes: `0` = success, `1` = error.
