---
name: alibabacloud-pai-quota-management
domain: aiops
description: |
  End-to-end Alibaba Cloud PAI Quota lifecycle management via `aliyun paistudio` (Quota CRUD, scale,
  workload inspection) and `aliyun aiworkspace` (binding Quotas to Workspaces). Covers root and child
  quota creation, absolute scaling, metadata update, deletion, listing quota workloads / active user
  usages, plus attaching and detaching quotas to PAI workspaces. Use when the user asks to list / get /
  create / update / scale / delete PAI quotas, inspect quota workloads or active users, or attach /
  detach quotas to a workspace. Trigger phrases: "PAI quota", "create PAI quota", "scale PAI quota",
  "child quota", "quota tree", "bind quota to workspace", "list PAI quotas", "Lingjun quota",
  "PAI 资源配额", "Quota 扩缩容".
required_permissions:
  - pai:ListQuotas
  - pai:GetQuota
  - pai:CreateQuota
  - pai:UpdateQuota
  - pai:ScaleQuota
  - pai:DeleteQuota
  - pai:ListQuotaWorkloads
  - pai:ListQuotaActiveUserUsages
  - pai:GetResourceGroup
  - pai:ListResourceGroups
  - pai:UpdateResourceGroup
  - aiworkspace:ListWorkspaces
  - aiworkspace:GetWorkspace
  - aiworkspace:ListResources
  - aiworkspace:CreateWorkspaceResource
  - aiworkspace:UpdateWorkspaceResource
  - aiworkspace:DeleteWorkspaceResource
  - vpc:DescribeVpcs
  - vpc:DescribeVSwitches
  - ecs:DescribeSecurityGroups
---

# PAI Quota Management

## 0. Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-quota-management/{session-id}
```

Example (assuming session-id is `a]1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-quota-management/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` command invocation.

**Plugin freshness (one-time per session, optional system command — NO `--user-agent`):**

```bash
aliyun plugin update
```

Every command omits the `--user-agent` flag for readability. **The agent MUST append it to every actual business API invocation** following the rules above. Missing or malformed `--user-agent` on a business API call is a workflow violation.

## 1. Scenario Description

Manage the full lifecycle of Alibaba Cloud PAI **Quotas** via the `aliyun paistudio` CLI plugin (and `aliyun aiworkspace` for workspace binding). Quotas carve a ResourceGroup's capacity into tree-structured allocations (root -> children), are scaled in absolute terms via `scale-quota`, and are attached to PAI workspaces via the `aiworkspace` product.

Architecture: `ResourceGroup(s) -> root Quota -> child Quota(s) -> Workspace binding`.

## 2. Installation & Auth

- Aliyun CLI >= 3.3.3 with the `paistudio` and `aiworkspace` plugins. See `references/cli-installation-guide.md`.
- The agent NEVER reads / echoes / writes AK/SK. Verify only via `aliyun configure list`.

## 3. Environment Variables

| Env | Required | Notes |
| --- | --- | --- |
| `REGION_ID` | Yes | e.g. `cn-shanghai`, `cn-wulanchabu`. |
| `QUOTA_ID` | When operating on a specific quota | From `list-quotas`. |
| `WORKSPACE_ID` | For workspace binding | From `aliyun aiworkspace list-workspaces`. |

## 4. RAM Policy

See `references/ram-policies.md` for full read-only and read-write policy JSON. On `Forbidden.RAM` / `NoPermission`, STOP, print the failing `Action` and `Resource`, and direct the user to attach the missing action. Do NOT use wildcards.

## 5. Parameter Confirmation

| Parameter | Required | Source / Validation | Default |
| --- | --- | --- | --- |
| `RegionId` | Yes | `aliyun configure get region`. | None |
| `QuotaName` | Create / rename | 1-63 chars. | None |
| `ResourceType` | Create | **Derived — NOT user-supplied.** Root: from `get-resource-group`. Child: from `get-quota` on parent. Enum: `ECS`, `Lingjun`, `ACS`. | None |
| `ResourceGroupIds` | Create root | Space-separated list (repeated positional). | None |
| `ParentQuotaId` | Create child | From `list-quotas --layout-mode Tree`. | None |
| `AllocateStrategy` | Create | Enum: `ByNodeSpecs`, `ByMachineGroupIds`. | `ByNodeSpecs` |
| `Min` | Create / scale | JSON, e.g. `{"NodeSpecs":[{"NodeSpec":"ecs.gn7i-c8g1.2xlarge","Count":4}]}`. | None |
| `QuotaConfig` | Update VPC / queue | JSON. See `references/validation-rules.md` §4 for VPC mutability. | None |
| `QueueStrategy` | Update | Enum: `PaiStrategyIntelligent` (auto), `PaiStrategyStrictFIFO` (FIFO), `PaiStrategyBalance` (fair), `PaiStrategyRoundRobin` (round-robin). Case-sensitive. | None |
| `Labels` | Update | Space-separated `Key=K Value=V` pairs. | None |
| `WorkspaceId` | Binding | From `aliyun aiworkspace list-workspaces`. | None |

## 6. Core Workflow

> **[MUST] Use the `aliyun` CLI exclusively.** No raw HTTP, no SDK, no MCP tool, no console clicks, no Yuque/internal endpoints. If the CLI does not expose a capability, treat it as not implementable (`references/not-implementable.md`).
>
> **[MUST] Observability — per-command `--user-agent`**: see §0. Every business API call (`aliyun paistudio …`, `aliyun aiworkspace …`), including `--cli-dry-run` and read-only `list-*` / `get-*`, MUST carry `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-quota-management/{session-id}"` with the real session id substituted in. Code samples below omit the flag for readability — the agent MUST append it on every actual invocation.

### Confirmation Gate — HARD STOP (Create / Update / Scale / Delete / Detach)

> **[CRITICAL — HIGHEST PRIORITY RULE]**
>
> The agent is **ABSOLUTELY FORBIDDEN** from executing `create-quota`, `update-quota`, `scale-quota`, `delete-quota`, or `aiworkspace delete-workspace-resource` in the same turn as the user's original request. These commands require a **two-turn interaction**:
>
> **Turn 1 (agent):** Print the resolved plan / parameters, then print the confirmation prompt, then **STOP. END THE TURN. DO NOT EXECUTE THE COMMAND. DO NOT PROCEED.**
>
> **Turn 2 (user → agent):** The user replies with the exact confirmation token. **ONLY AFTER** receiving this token in a **separate user message** may the agent execute the command.
>
> If the agent executes `create-quota`, `update-quota`, `scale-quota`, `delete-quota`, or `delete-workspace-resource` **without first receiving the confirmation token from the user in a prior turn**, this is a **critical workflow violation**.
>
> **Mandatory dry-run before Update / Scale / Delete / Detach:**
>
> Before asking for the confirmation token, the agent **MUST** first execute the command with `--cli-dry-run` and show the output to the user. This is non-negotiable — **no dry-run, no confirmation prompt, no execution**. The sequence is:
> 1. Run `<command> ... --cli-dry-run` to preview the resolved request payload.
> 2. Show the dry-run output to the user.
> 3. Ask for the confirmation token.
> 4. **STOP. END THE TURN.**
>
> Skipping the `--cli-dry-run` step is a **critical workflow violation**, equivalent to executing without confirmation.
>
> **Confirmation tokens:**
> - **Create** (`create-quota`): `CONFIRM-CREATE <QUOTA_NAME>` — print resolved parameters (ResourceGroupIds, ResourceType, QuotaName, Min, etc.), then ask: `Type "CONFIRM-CREATE <QUOTA_NAME>" to continue; any other input cancels.` **STOP HERE. END THE TURN. WAIT FOR USER INPUT.**
> - **Update / Scale** (`update-quota`, `scale-quota`): `CONFIRM <QUOTA_ID>` — first run `update-quota`/`scale-quota` with `--cli-dry-run`, show the output, print the diff, then ask: `Type "CONFIRM <QUOTA_ID>" to proceed; any other input cancels.` **STOP HERE. END THE TURN. WAIT FOR USER INPUT.** (Scale-down below active usage requires `CONFIRM-FORCE <QUOTA_ID>` instead.)
> - **Delete / Detach** (`delete-quota`, `delete-workspace-resource`): `CONFIRM <QUOTA_ID>` — first run `delete-quota` with `--cli-dry-run`, show the output + workload check, then ask for the token. **STOP HERE. END THE TURN. WAIT FOR USER INPUT.** Never batch tokens across multiple quotas.
>
> **What "END THE TURN" means:** The agent MUST finish its response after printing the confirmation prompt. It MUST NOT call `create-quota` / `update-quota` / `scale-quota` / `delete-quota` / `delete-workspace-resource` in that same response. The next action happens ONLY after the user sends a new message containing the exact token.
>
> Read-only operations (`list-*`, `get-*`) do NOT require this gate.

### Multi-Task Handling — Decompose first, then follow each task's Step 6.x workflow exactly

> **[CRITICAL]** When the user requests multiple operations in a single message, the agent MUST:
>
> **Phase 1 — Decompose:** Break the user's request into individual tasks. Map each task to its corresponding workflow step (Step 6.2 / 6.3 / 6.4 / 6.5 / 6.9 etc.).
>
> **Phase 2 — Execute one task at a time:** Process each task sequentially, following the **EXACT SAME workflow** as if it were the only task the user requested. **No step may be skipped, shortened, or combined just because the task is part of a batch.**
>
> This means every individual task MUST:
> - Follow its own Step 6.x pre-requisites in full (existence check, workload check, etc.)
> - For update / scale / delete: run `--cli-dry-run` and show the output to the user — **this is mandatory even in multi-task mode**
> - For update with queue strategy: use the exact enum value `PaiStrategyStrictFIFO` (case-sensitive) — **not** `FIFO`, `fifo`, `PaiStrategyFifo`, or any other alias
> - Ask for its own confirmation token (`CONFIRM-CREATE` / `CONFIRM` / `CONFIRM-FORCE`)
> - **STOP. END THE TURN. WAIT** for the user to confirm before executing
> - Only after execution, move to the next task
>
> **ONE mutating operation per turn. The agent MUST NOT execute or prepare the second task until the first one is fully confirmed and executed.**
>
> **Example — user sends: "Create root quota X, scale Y to Count=1, rename Z to Z2, delete W":**
>
> | Turn | Actor | Action |
> | --- | --- | --- |
> | 1 | Agent | Decompose into 4 tasks. Start task 1: follow Step 6.2 (resolve RGs, validate, print plan). Ask `CONFIRM-CREATE X`. **STOP.** |
> | 2 | User | `CONFIRM-CREATE X` |
> | 3 | Agent | Execute `create-quota` for X. Start task 2: follow Step 6.4 (get-quota, list-quota-workloads, print diff, **run `scale-quota --cli-dry-run`**, show output). Ask `CONFIRM <QUOTA_ID>`. **STOP.** |
> | 4 | User | `CONFIRM <QUOTA_ID>` |
> | 5 | Agent | Execute `scale-quota`. Start task 3: follow Step 6.5 (get-quota, print diff, **run `update-quota --cli-dry-run`**, show output). Ask `CONFIRM <QUOTA_ID>`. **STOP.** |
> | 6 | User | `CONFIRM <QUOTA_ID>` |
> | 7 | Agent | Execute `update-quota`. Start task 4: follow Step 6.9 (get-quota, list-quota-workloads, **run `delete-quota --cli-dry-run`**, show output). Ask `CONFIRM <QUOTA_ID>`. **STOP.** |
> | 8 | User | `CONFIRM <QUOTA_ID>` |
> | 9 | Agent | Execute `delete-quota`. All tasks complete. |
>
> **Common violations in multi-task mode (ALL are critical failures):**
> - Skipping `--cli-dry-run` for update/scale/delete because "there are more tasks to do"
> - Using `FIFO` or `PaiStrategyFifo` instead of `PaiStrategyStrictFIFO`
> - Executing multiple mutating commands in one turn
> - Skipping the confirmation gate because "the user already asked for all of them"
> - Printing multiple confirmation prompts in one turn
>
> **The user's multi-step request is a TODO list, not a blanket execution authorization.** Each task follows its own Step 6.x workflow in full — no shortcuts.

### Candidate Resolution (`create-quota`)

> **[MUST]** Before `create-quota`, resolve every user-supplied identifier against the live API, print the resolved parameters, then ask for `CONFIRM-CREATE <QUOTA_NAME>`. **END THE TURN AND WAIT.** Do NOT call `create-quota` until the user replies with the exact token in a subsequent message. Full rules: `references/validation-rules.md` §1.

### Step 6.1 — List quotas / inspect a quota

```bash
aliyun paistudio list-quotas \
  --region "${REGION_ID}" --page-number 1 --page-size 20 --verbose true

aliyun paistudio get-quota \
  --region "${REGION_ID}" --quota-id "${QUOTA_ID}" --verbose true --with-node-meta true
```

Filters for list: `--quota-name`, `--resource-type ECS|Lingjun|ACS`, `--parent-quota-id`, `--quota-ids`, `--workspace-ids`, `--workspace-name`, `--statuses`, `--labels`, `--layout-mode Tree|List`, `--sort-by`, `--order asc|desc`.

### Step 6.2 — Create a root Quota from ResourceGroups

> **Pre-requisites (all mandatory, in order):**
> 1. **Candidate Resolution** — resolve `--resource-group-ids` via `list-resource-groups` / `get-resource-group`. See `references/validation-rules.md` §1.
> 2. **Homogeneity validation** — Step A (ResourceType match) + Step B (per-type invariants). See `references/validation-rules.md` §2.
> 3. **NodeSpec availability** — call `list-node-types --resource-group-ids` and validate. See `references/validation-rules.md` §3.
> 4. **CONFIRM-CREATE gate** — print resolved parameters, ask for `CONFIRM-CREATE <QUOTA_NAME>`. **STOP. END THE TURN. WAIT FOR USER INPUT.** Do NOT call `create-quota` in this turn. Only execute `create-quota` after the user replies with the exact `CONFIRM-CREATE <QUOTA_NAME>` token in a new message.

```bash
# ONLY execute after receiving CONFIRM-CREATE token from the user
aliyun paistudio create-quota \
  --region "${REGION_ID}" \
  --quota-name "${QUOTA_NAME}" \
  --resource-type "${RESOURCE_TYPE_FROM_RG}" \
  --resource-group-ids rg-aaa rg-bbb \
  --allocate-strategy ByNodeSpecs \
  --min '{"NodeSpecs":[{"NodeSpec":"ecs.gn7i-c8g1.2xlarge","Count":2}]}'
```

> `${RESOURCE_TYPE_FROM_RG}` is derived from the source ResourceGroups (all must be identical per Step A). The agent derives it — never asks the user.

### Step 6.3 — Create a child Quota under a parent

> **Pre-requisites (all mandatory, in order):**
> 1. **Parent existence check via `get-quota`** — call `get-quota --quota-id ${PARENT} --verbose true`. If the parent returns 404 / QuotaNotFound, STOP and refuse. Do NOT issue `create-quota`. If the parent exists, read from the response: `ResourceType`, `Min.NodeSpecs`, and `QuotaConfig.UserVpc` — these are the authoritative source for deriving the child's configuration.
> 2. **Derive `--resource-type`** from the parent quota's `ResourceType` field returned by `get-quota` (inherited, never user-supplied).
> 3. **NodeSpec validation against parent** — from the parent's `get-quota` response, check `Min.NodeSpecs`. Every `NodeSpec` in the child's `--min` JSON MUST exist in the parent's `Min.NodeSpecs`, and the requested `Count` MUST NOT exceed the parent's available (unallocated) count. If validation fails, STOP and refuse.
> 4. **CONFIRM-CREATE gate** — print the resolved parameters and ask: `Type "CONFIRM-CREATE <QUOTA_NAME>" to continue; any other input cancels.` **STOP. END THE TURN. WAIT FOR USER INPUT.** The agent MUST NOT call `create-quota` in this turn. Only execute after the user replies with the exact `CONFIRM-CREATE <QUOTA_NAME>` token in a new message.

```bash
# ONLY execute after receiving CONFIRM-CREATE token from the user
aliyun paistudio create-quota \
  --region "${REGION_ID}" \
  --quota-name "${CHILD_NAME}" \
  --resource-type "${RESOURCE_TYPE_FROM_PARENT}" \
  --parent-quota-id "${PARENT_QUOTA_ID}" \
  --allocate-strategy ByNodeSpecs \
  --min '{"NodeSpecs":[{"NodeSpec":"ecs.gn7i-c8g1.2xlarge","Count":1}]}'
```

### Step 6.4 — Scale a Quota  `[REQUIRES CONFIRMATION]`

> **Mandatory steps before execution:**
> 1. **Existence check** — `get-quota --quota-id ${QUOTA_ID} --verbose true`. If 404 / QuotaNotFound, inform the user and STOP — do NOT dry-run, do NOT issue `scale-quota`.
> 2. `list-quota-workloads --quota-id ${QUOTA_ID}` — check in-flight workloads.
> 3. Print diff: current `Min` vs target `Min`.
> 4. **Dry-run (MANDATORY — MUST NOT SKIP)** — run `scale-quota ... --cli-dry-run` to preview the resolved request payload. Show the dry-run output to the user. If this step is skipped, the agent MUST NOT proceed to the CONFIRM gate or execute scale-quota.
> 5. **CONFIRM gate (mandatory)** — ONLY after dry-run output is shown, ask for `CONFIRM <QUOTA_ID>` (or `CONFIRM-FORCE <QUOTA_ID>` if scaling down below current usage). **STOP. END THE TURN. WAIT FOR USER INPUT.** The agent MUST NOT call `scale-quota` in this turn. Only execute after the user replies with the exact token in a new message.
>
> When `--resource-group-ids` changes, additionally re-run homogeneity validation (`references/validation-rules.md` §2) against the FINAL post-scale RG set.

```bash
# ONLY execute after receiving CONFIRM token from the user
aliyun paistudio scale-quota \
  --region "${REGION_ID}" \
  --quota-id "${QUOTA_ID}" \
  --resource-group-ids rg-aaa rg-bbb \
  --min '{"NodeSpecs":[{"NodeSpec":"ecs.gn7i-c8g1.2xlarge","Count":4}]}'
```

`scale-quota` reapplies the new `Min` (absolute target). Incremental `ScaleInQuota` / `ScaleOutQuota` are not exposed — see `references/not-implementable.md`.

### Step 6.5 — Update Quota metadata  `[REQUIRES CONFIRMATION]`

> **Mandatory steps before execution:**
> 1. **Existence check** — `get-quota --quota-id ${QUOTA_ID} --verbose true`. If 404 / QuotaNotFound, inform the user and STOP — do NOT dry-run, do NOT issue `update-quota`.
> 2. Compute and print diff: show each field being changed (current value -> new value). Only include fields the user requested to change.
> 3. **Dry-run (MANDATORY — MUST NOT SKIP)** — run `update-quota ... --cli-dry-run` to preview the resolved request payload. Show the dry-run output to the user. If this step is skipped, the agent MUST NOT proceed to the CONFIRM gate or execute update-quota.
> 4. **CONFIRM gate (mandatory)** — ONLY after dry-run output is shown, ask for `CONFIRM <QUOTA_ID>`. **STOP. END THE TURN. WAIT FOR USER INPUT.** The agent MUST NOT call `update-quota` in this turn. Only execute after the user replies with the exact token in a new message.

```bash
# ONLY execute after receiving CONFIRM token from the user
aliyun paistudio update-quota \
  --region "${REGION_ID}" \
  --quota-id "${QUOTA_ID}" \
  --quota-name "${NEW_NAME}" \
  --description "Updated by skill" \
  --queue-strategy PaiStrategyIntelligent \
  --labels Key=Owner Value=team-a Key=Env Value=prod
```

Updatable fields: `--quota-name`, `--description`, `--labels`, `--queue-strategy`, `--quota-config`. VPC update constraints: see `references/validation-rules.md` §4.

### Step 6.6 — Bind a Quota to a Workspace

```bash
aliyun aiworkspace list-workspaces --region "${REGION_ID}" --page-number 1 --page-size 20

aliyun aiworkspace create-workspace-resource \
  --region "${REGION_ID}" \
  --workspace-id "${WORKSPACE_ID}" \
  --option Attach \
  --resources '[{"ProductType":"PAI","ResourceType":"ECS","WorkspaceId":"'"${WORKSPACE_ID}"'","Quotas":[{"Id":"'"${QUOTA_ID}"'"}]}]'
```

> Inside `--resources` JSON, `ResourceType` must be one of `MaxCompute | ECS | Lingjun | ACS | FLINK`.

### Step 6.7 — List & inspect Quota usage

```bash
aliyun paistudio list-quota-workloads --region "${REGION_ID}" --quota-id "${QUOTA_ID}" --page-size 50
aliyun paistudio list-quota-active-user-usages --region "${REGION_ID}" --quota-id "${QUOTA_ID}" --page-size 50
```

### Step 6.8 — Detach a Quota from a Workspace  `[REQUIRES CONFIRMATION]`

```bash
aliyun aiworkspace delete-workspace-resource \
  --region "${REGION_ID}" \
  --workspace-id "${WORKSPACE_ID}" \
  --option Detach \
  --resource-type ECS \
  --resource-ids "${WS_RESOURCE_ID}"
```

`WS_RESOURCE_ID` is obtained from `aliyun aiworkspace list-resources --workspace-id ${WORKSPACE_ID}`. `--option` enum: `Detach` (disassociate only) or `DetachAndDelete` (default).

### Step 6.9 — Delete a Quota  `[REQUIRES CONFIRMATION]`

> **Mandatory steps before execution:**
> 1. **Existence check** — call `get-quota --quota-id ${QUOTA_ID}`. If 404 / QuotaNotFound, inform the user and STOP — do NOT dry-run, do NOT issue `delete-quota`.
> 2. **Workload check** — call `list-quota-workloads --quota-id ${QUOTA_ID}` to surface in-flight workloads.
> 3. **Dry-run (MANDATORY — MUST NOT SKIP, only when quota exists)** — run `delete-quota ... --cli-dry-run` to preview the resolved request payload. Show the dry-run output to the user. If this step is skipped, the agent MUST NOT proceed to the CONFIRM gate or execute delete-quota.
> 4. **CONFIRM gate (mandatory)** — ONLY after dry-run output is shown, ask for `CONFIRM <QUOTA_ID>`. **STOP. END THE TURN. WAIT FOR USER INPUT.** The agent MUST NOT call `delete-quota` in this turn. Only execute after the user replies with the exact token in a new message.
>
> Delete order: detach from all workspaces -> delete child quotas bottom-up -> delete root quota. Each child and the root require their own `CONFIRM` token — never batch. Each `CONFIRM` requires a separate turn (agent asks → user confirms → agent executes).

```bash
# ONLY execute after receiving CONFIRM token from the user
aliyun paistudio delete-quota --region "${REGION_ID}" --quota-id "${CHILD_QUOTA_ID}"
# Ask for CONFIRM again for the next quota — END THE TURN AND WAIT
aliyun paistudio delete-quota --region "${REGION_ID}" --quota-id "${ROOT_QUOTA_ID}"
```

## 7. Success Verification

See `references/verification-method.md`. Quick check: `get-quota --quota-id ${ID}` returns expected spec and `Status=Enabled`; after deletion it returns not-found.

## 8. Cleanup

Detach from all workspaces -> delete child quotas bottom-up -> delete root quota (each step requires a fresh confirmation token).

## 9. Reference Bundles

| File | Purpose |
| --- | --- |
| `references/validation-rules.md` | Candidate resolution, homogeneity validation, NodeSpec availability, VPC constraints, confirmation gate details. |
| `references/related-commands.md` | Full CLI table for `paistudio` + `aiworkspace`. |
| `references/ram-policies.md` | Read-only + full RAM policy JSON. |
| `references/verification-method.md` | V1-V9 verification steps. |
| `references/acceptance-criteria.md` | Correct / incorrect CLI command patterns. |
| `references/not-implementable.md` | APIs that exist only in the internal Yuque spec. |
| `references/cli-installation-guide.md` | Aliyun CLI install + plugin setup. |

### Cross-skill dependencies

| Sibling skill | When this skill calls it |
| --- | --- |
| **`pai-resource-group-management`** | **Mandatory** before `create-quota` (root) and `scale-quota` whenever `--resource-group-ids` is supplied or changed. Used to enumerate candidate RGs and fetch `ClusterId` / `GpuType` / `UserVpc` for homogeneity validation. |
| **`pai-node-management`** | Optional. After a root Quota is created or scaled, use it to inspect the actual nodes carved out from the source RGs. |

### External references

- **Public PAI OpenAPI portal (PaiStudio 2022-01-12)**: https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview
- **Public AIWorkSpace OpenAPI portal (AIWorkSpace 2021-02-04)**: https://next.api.aliyun.com/document/AIWorkSpace/2021-02-04/overview
- PAI AI Computing Resource Management: https://help.aliyun.com/zh/pai/user-guide/ai-computing-resource-management/
- Custom RAM Authorization Policy: https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy
