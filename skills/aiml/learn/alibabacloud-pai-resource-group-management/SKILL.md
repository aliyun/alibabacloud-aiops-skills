---
name: alibabacloud-pai-resource-group-management
domain: aiops
description: |
  End-to-end Alibaba Cloud PAI ResourceGroup (resource pool) lifecycle management via `aliyun paistudio`.
  Covers list / get / create / update / delete of ResourceGroups (general computing ECS or Lingjun GPU),
  read-only inspection of MachineGroups, and bind/unbind UserVpc.
  Use when the user asks to list / get / create / update / delete PAI resource groups, inspect machine
  groups, bind/unbind UserVpc, or audit resource-group capacity. Trigger phrases: "PAI resource
  group", "PAI resource pool", "Lingjun resource group", "create PAI resource group", "list PAI resource
  groups", "PAI machine group", "Lingjun resource group (灵骏资源组)", "PAI resource pool (PAI 资源池)", "PAI 资源组".
required_permissions:
  - pai:ListResourceGroups
  - pai:GetResourceGroup
  - pai:CreateResourceGroup
  - pai:UpdateResourceGroup
  - pai:DeleteResourceGroup
  - pai:ListResourceGroupMachineGroups
  - pai:GetResourceGroupMachineGroup
  - vpc:DescribeVpcs
  - vpc:DescribeVSwitches
  - ecs:DescribeSecurityGroups
---

# PAI ResourceGroup Management

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}
```

Example (assuming session-id is `a]1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` command invocation.

**Business API commands ONLY:** `aliyun paistudio list-resource-groups`, `aliyun paistudio get-resource-group`, `aliyun paistudio create-resource-group`, `aliyun paistudio update-resource-group`, `aliyun paistudio delete-resource-group`, `aliyun paistudio list-resource-group-machine-groups`, `aliyun paistudio get-resource-group-machine-group`, etc.

**MUST NOT be added to system / configuration commands:** `aliyun configure list`, `aliyun configure get`, `aliyun plugin update`, `aliyun plugin list`, `aliyun version`. These are local CLI utilities, not business API calls, and do not accept `--user-agent`.

## 1. Scenario Description

Manage the full lifecycle of Alibaba Cloud PAI **ResourceGroups** (resource pools) via the `aliyun paistudio` CLI plugin: list / get / create / update / delete ResourceGroups (ECS general computing or Lingjun GPU), **read-only** inspection of attached MachineGroups, and bind/unbind UserVpc. ResourceGroups are the source of capacity that Quotas later carve up.

> **⚠️ Metrics APIs Deprecated**: `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, `get-node-metrics` are all deprecated and NOT supported by this skill.

> **🚫 MachineGroup deletion / release is OUT OF SCOPE.** The agent is **STRICTLY FORBIDDEN** from invoking `delete-resource-group-machine-group` or `delete-machine-group` under any circumstance. Direct users to the [PAI Console](https://pai.console.aliyun.com/) (BSS purchase / release flow). See `references/not-implementable.md`.

Architecture: `PAI ResourceGroup → MachineGroup(s) → Node(s)` with optional `UserVpc (VpcId + SwitchId + SecurityGroupId)` binding. ECS general-computing ResourceGroups may bind to any user VPC; Lingjun VPC is managed at the Lingjun infrastructure layer.

## 2. Installation & Auth

- Aliyun CLI ≥ 3.3.3 with `paistudio` plugin — see `references/cli-installation-guide.md`.
- The agent NEVER reads / echoes / writes AK/SK. Verify only via `aliyun configure list`; if unconfigured, instruct the user to run `aliyun configure` themselves.

## 3. Environment Variables

| Env | Required | Notes |
| --- | --- | --- |
| `REGION_ID` | Yes | e.g. `cn-shanghai`, `cn-hangzhou`, `cn-wulanchabu` (Lingjun). |
| `RESOURCE_GROUP_ID` | When operating on a specific RG | Obtained from `list-resource-groups`. |
| `MACHINE_GROUP_ID` | When operating on a specific MG | Obtained from `list-resource-group-machine-groups`. |

## 4. RAM Policy

See `references/ram-policies.md` for full read-only and read-write policy JSON. Minimum read scope:

```json
{
  "Version": "1",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "pai:GetResourceGroup", "pai:ListResourceGroups",
      "pai:GetMachineGroup", "pai:GetResourceGroupMachineGroup",
      "pai:ListResourceGroupMachineGroups"
    ],
    "Resource": ["acs:pai:*:*:resourcegroup/*"]
  }]
}
```

Permission failure handling: see `references/validation-rules.md` §5.

## 5. Parameter Confirmation

Before invoking any mutating CLI command, the agent MUST print and confirm:

| Parameter | Required | Source / Validation | Default |
| --- | --- | --- | --- |
| `RegionId` | Yes | `aliyun configure get region` or env `REGION_ID`. | None |
| `Name` | Create / rename | 1-63 chars, kebab-case recommended. **Cannot be empty string on update.** | None |
| `ResourceType` | Create | Enum: `ECS`, `Lingjun`. **⚠️ ACS variants OFFLINE** — see `references/validation-rules.md` §2 row C. | `ECS` (if empty) |
| `Version` | Create (ECS only) | Enum: `1.0`, `2.0`. ECS v2.0 forbids VPC on RG (VPC goes on Quota). | `1.0` (ECS default) |
| `UserVpc.VpcId` / `SwitchId` / `SecurityGroupId` | If binding VPC (ECS v1.0 only) | All three required as a trio (PascalCase). Forbidden for ECS v2.0 / Lingjun. See `references/validation-rules.md` §3. | None |
| `ResourceGroupId` | Update / delete / get | Obtained from `list-resource-groups`. | None |
| `MachineGroupId` | MG operations | Obtained from `list-resource-group-machine-groups`. | None |

> 🚦 **Pre-execution conflict matrix** — before any `aliyun paistudio …` CLI (incl. `--cli-dry-run`), the agent MUST cross-check input against the matrix in `references/validation-rules.md` §2 (rows A-F: ECS v2.0+VPC, Lingjun+VPC, ACS variants, incomplete VPC trio, delete with attached MGs, MG deletion request). Any hit → corresponding branch (mostly Branch 1). **Never** pass-through to the backend and rely on backend errors.

### Pre-execution discipline — three exclusive branches

Before any mutating CLI call, the agent MUST classify the request into **exactly one** of three branches:

| # | Branch | Trigger | Required output |
|---|---|---|---|
| 1 | **⚠️ Input Conflict** | User input contradicts a design rule | `⚠️ Input Conflict` block with 3 concrete options. **No CLI call.** |
| 2 | **🛑 Precondition Not Met** | Live-state check fails | `🛑 Precondition Not Met` block. **No mutating CLI.** |
| 3 | **📋 Resolved Plan** | All inputs valid, live state allows | `📋 Resolved Plan` block; for update/delete also wait for `CONFIRM <RG_NAME>` token (name-priority). |

Read-only `list-*` / `get-*` calls are exempt — execute directly, no block required.

> 🔒 **Execution lock + literal-match self-check**: branch block must be a standalone, user-visible segment with all required fields literally printed (no meta-statements like "now printing Resolved Plan"). Before any mutating CLI, the agent MUST scan the conversation for the literal `📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict` header. Full rules and required fields per block: `references/branch-discipline.md`.

> 🔁 **Multi-step / batch**: `N RG × M operations = N × M independent Resolved Plans + N × M CONFIRM tokens`. A single `CONFIRM ALL` / `CONFIRM batch` token is forbidden. Full rules: `references/branch-discipline.md` *Multi-step / batch operation rules*.

> 🛑 **Branch 1 silent-rewrite prohibition**: never silently strip / coerce a conflicting input, never substitute the text block with `AskUserQuestion` / IDE widgets, never degrade to a verbal suggestion. Full rules: `references/branch-discipline.md` *Branch 1 silent-rewrite prohibition*.

Worked examples (5 cases, all branches + Lingjun refusal): `references/branch-examples.md`.

## 6. Core Workflow

> **[MUST] Use the `aliyun paistudio` CLI exclusively.** No raw HTTP, no SDK, no MCP tool, no console clicks, no internal endpoints. If the CLI does not expose a capability, treat it as not implementable (`references/not-implementable.md`) — do not fall back to another transport.
>
> **[MUST] Observability — per-command `--user-agent`**: see §0.

### Confirmation Gate — HARD STOP (Create / Update / Delete)

> **[CRITICAL — HIGHEST PRIORITY RULE]**
>
> The agent is **ABSOLUTELY FORBIDDEN** from executing `create-resource-group`, `update-resource-group`, or `delete-resource-group` in the same turn as the user's original request. These commands require a **two-turn interaction**:
>
> **Turn 1 (agent):** Print the resolved plan / parameters, then print the confirmation prompt, then **STOP. END THE TURN. DO NOT EXECUTE THE COMMAND. DO NOT PROCEED.**
>
> **Turn 2 (user → agent):** The user replies with the exact confirmation token. **ONLY AFTER** receiving this token in a **separate user message** may the agent execute the command.
>
> If the agent executes `create-resource-group`, `update-resource-group`, or `delete-resource-group` **without first receiving the confirmation token from the user in a prior turn**, this is a **critical workflow violation**.
>
> **Mandatory dry-run before Update / Delete:**
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
> - **Create** (`create-resource-group`): `CONFIRM-CREATE <RG_NAME>` — print resolved parameters (Region, Name, ResourceType, Version, UserVpc if applicable), then ask: `Type "CONFIRM-CREATE <RG_NAME>" to continue; any other input cancels.` **STOP HERE. END THE TURN. WAIT FOR USER INPUT.**
> - **Update / Delete** (`update-resource-group`, `delete-resource-group`): `CONFIRM <RG_NAME>` — first run the command with `--cli-dry-run`, show the output, print the diff, then ask: `Type "CONFIRM <RG_NAME>" (or the actual ResourceGroupId) to proceed; any other input cancels.` **STOP HERE. END THE TURN. WAIT FOR USER INPUT.**
>
> **What "END THE TURN" means:** The agent MUST finish its response after printing the confirmation prompt. It MUST NOT call `create-resource-group` / `update-resource-group` / `delete-resource-group` in that same response. The next action happens ONLY after the user sends a new message containing the exact token.
>
> Read-only operations (`list-*`, `get-*`) do NOT require this gate. Full rules: `references/confirmation-gate.md`.

### Multi-Task Handling

> **[CRITICAL]** When the user requests multiple operations in one message: **decompose** into individual tasks, then process **one mutating operation per turn**. Each task follows its own Step 6.x workflow in full — no step may be skipped or combined. Each task needs its own `📋 Resolved Plan` + its own confirmation token + its own turn. `N RG × M operations = N × M tokens`. The user's multi-step request is a TODO list, not a blanket execution authorization. Full rules + turn-by-turn example: `references/confirmation-gate.md` *Multi-task* and `references/branch-discipline.md` *Multi-step / batch*.

### 🚫 MachineGroup Deletion / Release — STRICTLY FORBIDDEN

> The agent MUST refuse `aliyun paistudio delete-resource-group-machine-group` and `aliyun paistudio delete-machine-group` under ALL circumstances, even with a `CONFIRM <MACHINE_GROUP_ID>` token. Direct the user to the PAI Console (Resource Pool → Machine Group → Unsubscribe / Release) or BSS OpenAPI for unsubscribe. Offer read-only inspection via Step 6.5 if helpful. Rationale: `references/not-implementable.md`.

### Step 6.1 — List existing ResourceGroups

```bash
aliyun paistudio list-resource-groups \
  --region "${REGION_ID}" \
  --page-number 1 --page-size 20
```

Optional filters: `--name`, `--resource-type ECS|Lingjun`, `--resource-group-ids "rg-xxx,rg-yyy"`, `--has-resource true`, `--status`, `--versions`, `--computing-resource-provider`, `--sort-by GmtCreated --order desc`.

### Step 6.2 — Get a ResourceGroup detail

```bash
aliyun paistudio get-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --is-ai-workspace-data-enabled true
```

### Step 6.3 — Create a ResourceGroup  `[REQUIRES CONFIRMATION]`

> **[CRITICAL]** Before `create-resource-group`, resolve every user-supplied parameter against `references/validation-rules.md` §2, print the resolved parameters in a `📋 Resolved Plan` block, then ask for `CONFIRM-CREATE <RG_NAME>`. **END THE TURN AND WAIT.** Do NOT call `create-resource-group` until the user replies with the exact token in a subsequent message.
>
> **ABSOLUTELY FORBIDDEN**: calling `create-resource-group` in the same turn as the user's request — even with `--cli-dry-run`, even with intervening thinking or tool calls. The `CONFIRM-CREATE` token MUST come from the **user's next message**, not from the agent's own continuation.

> **ECS Version Differences:**
> - **ECS v2.0** (`--biz-version 2.0`): VPC forbidden on RG (lives on Quota — see `pai-quota-management`).
> - **ECS v1.0** (`--biz-version 1.0` or omitted): VPC configurable on RG via `--user-vpc` (PascalCase trio required).

ECS v2.0 (no VPC):

```bash
# ⚠️ ONLY execute AFTER receiving CONFIRM-CREATE token from the user in a SEPARATE TURN
aliyun paistudio create-resource-group \
  --region "${REGION_ID}" \
  --name "${RG_NAME}" \
  --resource-type ECS \
  --biz-version 2.0
```

ECS v1.0 with VPC binding (full PascalCase trio required — see `references/validation-rules.md` §3):

```bash
# ⚠️ ONLY execute AFTER receiving CONFIRM-CREATE token from the user in a SEPARATE TURN
aliyun paistudio create-resource-group \
  --region "${REGION_ID}" \
  --name "${RG_NAME}" \
  --resource-type ECS \
  --user-vpc '{"VpcId":"vpc-xxx","SwitchId":"vsw-xxx","SecurityGroupId":"sg-xxx","DefaultRoute":"eth0","ExtendedCIDRs":["10.0.0.0/16"]}'
```

Lingjun GPU pool — typically `cn-wulanchabu`:

```bash
# ⚠️ ONLY execute AFTER receiving CONFIRM-CREATE token from the user in a SEPARATE TURN
aliyun paistudio create-resource-group \
  --region cn-wulanchabu \
  --name "${RG_NAME}" \
  --resource-type Lingjun
```

> **Hardware purchase NOT implementable via public CLI/SDK.** The created ResourceGroup is empty until you purchase MachineGroups via the [PAI Console](https://pai.console.aliyun.com/) or BSS APIs.

### Step 6.4 — Update a ResourceGroup  `[REQUIRES CONFIRMATION]`

> **Mandatory steps (strictly ordered):** 1. Existence pre-check via `get-resource-group` (not found → Branch 2, no CLI) → 2. Compute diff (current → new) → 3. `--cli-dry-run` (MANDATORY) → 4. `CONFIRM <RG_NAME>` gate → **STOP. END THE TURN.** Any shortening / skipping = P0 over-reach (`references/compliance-redlines.md` R3 + R4). Full gate rules: `references/confirmation-gate.md`.

> ⚠️ **Parameter-minimization**: CLI MUST carry only fields actually changing. Carrying unchanged fields = silent rewrite = over-reach.

Update name only:

```bash
aliyun paistudio update-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --name "${NEW_NAME}"
```

Update description only:

```bash
aliyun paistudio update-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --description "..."
```

#### Changing VPC on an ECS v1.0 ResourceGroup

> ECS v1.0 VPC change is a **two-step** sequence: unbind first, then rebind. Each step requires its own `📋 Resolved Plan` block + its own `CONFIRM` token (`N=1 × M=2 = 2 tokens`). For ECS v2.0, VPC changes happen at the Quota level. For Lingjun, see the forbidden-string rule below.

Step 1 — Unbind:

```bash
aliyun paistudio update-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --unbind true
```

Step 2 — Bind new VPC (PascalCase trio required):

```bash
aliyun paistudio update-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --user-vpc '{"VpcId":"vpc-new","SwitchId":"vsw-new","SecurityGroupId":"sg-new","DefaultRoute":"eth0"}'
```

> 🚫 **Lingjun VPC refusal — forbidden-string rule**: when refusing a Lingjun VPC change, the response MUST NOT contain the literal strings `aliyun paistudio update-resource-group` or `--user-vpc` (in any executable form, even as counter-example or dry-run). Refuse in plain natural language and point the user to the Lingjun infrastructure team / account manager. Full rules: `references/validation-rules.md` §4.

### Step 6.5 — List & inspect MachineGroups (read-only)

```bash
aliyun paistudio list-resource-group-machine-groups \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --page-number 1 --page-size 20

aliyun paistudio get-resource-group-machine-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --machine-group-id "${MACHINE_GROUP_ID}"
```

Additional `list` filters: `--machine-group-ids`, `--name`, `--creator-id`, `--ecs-spec`, `--payment-type`, `--status`, `--order-instance-id`, `--disk-pl`, `--payment-duration`, `--payment-duration-unit`, `--sort-by`, `--order`.

### Step 6.6 — Observe usage / metrics

> ⚠️ **DEPRECATED — NOT SUPPORTED.** If asked for `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, or `get-node-metrics`, respond:
>
> > "ResourceGroup metrics / request-aggregate APIs have been deprecated and are no longer supported by this skill. Please use the PAI Console or contact your administrator."

### Step 6.7 — Delete the ResourceGroup  `[REQUIRES CONFIRMATION]`

> **Mandatory steps (strictly ordered):** 1. Existence pre-check via `get-resource-group` (not found → Branch 2, no CLI) → 2. MG-empty pre-check via `list-resource-group-machine-groups --page-size 1` (`TotalCount > 0` → Branch 2, direct user to PAI Console) → 3. `--cli-dry-run` (MANDATORY) → 4. `CONFIRM <RG_NAME>` gate → **STOP. END THE TURN.** Ordering is non-negotiable — existence first, MG-count second, dry-run third, CONFIRM last. Any skipping = P0 over-reach (`references/compliance-redlines.md` R3 + R4). Full gate rules: `references/confirmation-gate.md`.

```bash
# Pre-check 1 — RG existence (read-only). If empty / NotFound → Branch 2 (validation-rules.md §2 row E2) → STOP.
aliyun paistudio list-resource-groups \
  --region "${REGION_ID}" \
  --resource-group-ids "${RESOURCE_GROUP_ID}"
# OR equivalently:
aliyun paistudio get-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}"

# Pre-check 2 — MG count (read-only). Only run AFTER pre-check 1 returned the RG.
aliyun paistudio list-resource-group-machine-groups \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --page-size 1
# Expect: TotalCount == 0. Otherwise → Branch 2 (validation-rules.md §2 row E3) → STOP and direct the user
# to release MGs in the PAI Console (the agent CANNOT release MGs on the user's behalf).

# Dry-run (MANDATORY). Only run AFTER both pre-checks pass.
aliyun paistudio delete-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --cli-dry-run
# Show the dry-run output to the user.

# Pre-checks + dry-run passed → 📋 Resolved Plan (citing both pre-check results as Preconditions verified)
# → verbatim CONFIRM prompt with the real RG name → end the turn → wait for user's next-turn token.

# ONLY execute after receiving CONFIRM token from the user
aliyun paistudio delete-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}"
```

### 🏁 Exit Checklist + Compliance Red Lines

> **[MUST]** Before generating the final user-facing reply for **any** exit path (success / failure / refusal / cancellation / Branch 1 wait / Branch 2), the agent MUST:
>
> 1. Confirm every business API call this turn carried `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"` (with a real session id), and that no system/configuration command (e.g., `aliyun configure …`, `aliyun plugin …`, `aliyun version`) was invoked with `--user-agent`.
> 2. Pass the §6 *Exit Checklist* (flow order): branch block → CONFIRM (cross-turn) → CLI with `--user-agent`. Full 7-point version + recovery procedure: `references/exit-checklist.md`.
> 3. Pass the **Compliance Red Lines R1-R7** (non-negotiable): MG deletion refused / observability `--user-agent` present on every business API call / CONFIRM cross-turn / branch block literal / channel pure / Lingjun forbidden-string / parameter minimization. Full table + rationale: `references/compliance-redlines.md`.
>
> Both checklists are **AND**, not OR. A missing or malformed `--user-agent` on any business API call — even on a refusal turn — is a P0 workflow defect.

## 7. Success Verification

See `references/verification-method.md`. Quick check:

- `get-resource-group --resource-group-id ${ID}` returns the expected `Name`, `ResourceType`, and `UserVpc` (if bound).
- `list-resource-group-machine-groups` is read-only — used to verify MG inventory, not to mutate it.
- After `delete-resource-group`, `get-resource-group` returns a not-found error.

## 8. Cleanup

1. **User releases all MachineGroups via the PAI Console** (this skill cannot and will not delete them).
2. After `list-resource-group-machine-groups` returns `TotalCount=0`, run `delete-resource-group` (subject to the two-step confirmation gate).

## 9. Reference Bundles

| File | Purpose |
| --- | --- |
| `references/validation-rules.md` | Plugin check, conflict matrix (A-F), VPC trio rule, Lingjun forbidden-string rule, RAM permission failure handling. |
| `references/branch-discipline.md` | Three-branch decision detail, execution lock, literal-match self-check, block shapes, multi-step / batch formula, Branch 1 silent-rewrite prohibition. |
| `references/confirmation-gate.md` | Hard-block declaration, banned self-authorization phrasing, same-turn execution prohibition, 5-step gate, token forging prohibition. |
| `references/compliance-redlines.md` | R1-R7 pre-reply red-line table + rationale. |
| `references/exit-checklist.md` | 7-point exit checklist + recovery procedure. |
| `references/branch-examples.md` | 5 worked examples for Branches 1/2/3 + Lingjun refusal pattern. |
| `references/related-commands.md` | Full CLI table (per-action parameters). |
| `references/ram-policies.md` | Read-only + full RAM policy JSON + per-API table. |
| `references/verification-method.md` | V1-V8 step-by-step verification. |
| `references/acceptance-criteria.md` | Correct / incorrect CLI patterns. |
| `references/not-implementable.md` | APIs that exist only in internal / console flow. |
| `references/cli-installation-guide.md` | Aliyun CLI install + plugin setup. |

### Cross-skill dependencies

| Sibling skill | Relationship |
| --- | --- |
| **`pai-quota-management`** | Upstream RG enumeration / inspection. Before `create-quota` (root) or `scale-quota` adjusts `--resource-group-ids`, the quota skill MUST `list-resource-groups` + `get-resource-group` here, then run a homogeneity check on `ClusterId` + `GpuType` (Lingjun) or `ClusterId` + `GpuType` + `UserVpc.{VpcId,SwitchId,SecurityGroupId}` (ECS). ACS variants no longer participate. |
| **`pai-node-management`** | Reads from RGs in this skill via `list-nodes --resource-group-ids` for read-only node inspection. |

External references:

- **Public PAI OpenAPI portal (PaiStudio 2022-01-12)**: https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview — authoritative source for all `Create/Update/Delete/List/Get ResourceGroup[MachineGroup]` request/response shapes. (`DeleteResourceGroupMachineGroup` exists but is intentionally **NOT used** here. `GetResourceGroupTotal` / `GetResourceGroupRequest` / `GetUserViewMetrics` / `GetNodeMetrics` are **deprecated**.)
- PAI AI Computing Resource Management: https://help.aliyun.com/zh/pai/user-guide/ai-computing-resource-management/
- Custom RAM Authorization Policy: https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy
