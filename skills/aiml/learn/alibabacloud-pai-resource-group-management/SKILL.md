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
  groups", "PAI machine group", "灵骏资源组", "PAI 资源池", "PAI 资源组".
required_permissions:
  - pai:ListResourceGroups
  - pai:GetResourceGroup
  - pai:CreateResourceGroup
  - pai:UpdateResourceGroup
  - pai:DeleteResourceGroup
  - pai:ListResourceGroupMachineGroups
  - vpc:DescribeVpcs
  - vpc:DescribeVSwitches
  - ecs:DescribeSecurityGroups
---

# PAI ResourceGroup Management

## 0. Mandatory AI-Mode Lifecycle (Initialization & Cleanup)

> **[MUST] Workflow first line — Initialization.** Before executing **any** `aliyun paistudio` command (including `--cli-dry-run` and read-only `list-*` / `get-*`), the agent's **first** CLI calls of the turn MUST be the following three, in order, with none omitted:
>
> ```bash
> aliyun plugin update
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management"
> ```
>
> These MUST NOT be split across turns, MUST NOT be replaced by a "already enabled" claim in thinking, and MUST NOT skip the user-agent setting.
>
> **[MUST] Workflow last line — Cleanup.** The **last** step of **every** reply or tool invocation in this skill MUST unconditionally execute:
>
> ```bash
> aliyun configure ai-mode disable
> ```
>
> This covers **all** exit paths: successful landing, CLI-call failure, user cancellation, rejected confirmation token, ending the current turn while waiting for clarification (Branch 1 wait, Branch 2 `🛑 Precondition Not Met`, refusal of out-of-scope ops, `Forbidden.RAM` immediate stop, empty response, zero-result clarification — any early exit).
>
> Missing the first-line enable or last-line disable **is a workflow failure** — it MUST NOT be skipped on the grounds of "read-only list has no side effect" / "no real mutating CLI was issued this turn" / "I'll catch up next turn" / etc.; nor is it acceptable to merely mention it in thinking without actually executing it.

## 1. Scenario Description

Manage the full lifecycle of Alibaba Cloud PAI **ResourceGroups** (resource pools) via the `aliyun paistudio` CLI plugin: list / get / create / update / delete ResourceGroups (ECS general computing or Lingjun GPU), **read-only** inspection of attached MachineGroups, and bind/unbind UserVpc. ResourceGroups are the source of capacity that Quotas later carve up.

> **⚠️ Metrics APIs Deprecated**: `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, `get-node-metrics` are all deprecated and NOT supported by this skill.

> **🚫 MachineGroup deletion / release is OUT OF SCOPE.** The agent is **STRICTLY FORBIDDEN** from invoking `delete-resource-group-machine-group` or `delete-machine-group` under any circumstance. Direct users to the [PAI Console](https://pai.console.aliyun.com/) (BSS purchase / release flow). See `references/not-implementable.md`.

Architecture: `PAI ResourceGroup → MachineGroup(s) → Node(s)` with optional `UserVpc (VpcId + SwitchId + SecurityGroupId)` binding. ECS general-computing ResourceGroups may bind to any user VPC; Lingjun VPC is managed at the Lingjun infrastructure layer.

## 2. Installation & Auth

- Aliyun CLI ≥ 3.3.3 with `paistudio` plugin — see `references/cli-installation-guide.md`.
- The agent NEVER reads / echoes / writes AK/SK. Verify only via `aliyun configure list`; if unconfigured, instruct user to run `aliyun configure` themselves.

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
>
> 🔑 **Branch 1 — ECS v2.0 + VPC conflict additional requirement**: When row A is triggered (`--biz-version 2.0` + `--user-vpc` present simultaneously), the `⚠️ Input Conflict` block's `Conflicting input` field **MUST** explicitly list both `--biz-version 2.0` and `--user-vpc` as conflicting fields (listing only one is forbidden), and the `Design rule violated` field **MUST** explain that under v2.0, VPC should be configured on `Quota.QuotaConfig.UserVpc` (not at the RG level).

### Pre-execution discipline — three exclusive branches

Before any mutating CLI call, the agent MUST classify the request into **exactly one** of three branches:

| # | Branch | Trigger | Required output |
|---|---|---|---|
| 1 | **⚠️ Input Conflict** | User input contradicts a design rule | `⚠️ Input Conflict` block with 3 concrete options. **No CLI call.** |
| 2 | **🛑 Precondition Not Met** | Live-state check fails | `🛑 Precondition Not Met` block + AI-mode disable. **No mutating CLI.** |
| 3 | **📋 Resolved Plan** | All inputs valid, live state allows | `📋 Resolved Plan` block; for update/delete also wait for `CONFIRM <RG_NAME>` token (name-priority). |

Read-only `list-*` / `get-*` calls are exempt — execute directly, no block required.

> 🔒 **Execution lock + literal-match self-check**: branch block must be a standalone, user-visible segment with all required fields literally printed (no meta-statements like "now outputting Resolved Plan"). Before any mutating CLI, the agent MUST scan the conversation for the literal `📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict` header. Full rules and required fields per block: `references/branch-discipline.md`.

> 🔁 **Multi-step / batch**: `N RG × M operations = N × M independent Resolved Plans + N × M CONFIRM tokens`. Single `CONFIRM ALL` / `CONFIRM batch` is forbidden. Full rules: `references/branch-discipline.md` *Multi-step / batch operation rules*.

> 🛑 **Branch 1 silent-rewrite prohibition**: never silently strip / coerce a conflicting input, never substitute the text block with `AskUserQuestion`/IDE widgets, never degrade to verbal suggestion. Full rules: `references/branch-discipline.md` *Branch 1 silent-rewrite prohibition*.

Worked examples (5 cases, all branches + Lingjun refusal): `references/branch-examples.md`.

## 6. Core Workflow

> **[MUST] Use the `aliyun paistudio` CLI exclusively.** No raw HTTP, no SDK, no MCP tool, no console clicks, no Yuque/internal endpoints. If the CLI does not expose a capability, treat it as not implementable (`references/not-implementable.md`) — do not fall back to another transport.
>
> **[MUST] AI-Mode lifecycle**: see §0 *Mandatory AI-Mode Lifecycle*. All CLI invocations in this section MUST be preceded by the §0 first-line init (`aliyun plugin update` + `aliyun configure ai-mode enable` + `aliyun configure ai-mode set-user-agent …`), and every exit path MUST end with the §0 last-line `aliyun configure ai-mode disable`. Do not duplicate or skip these.

### ⚠️ Mandatory Two-Step Confirmation Gate (Update / Delete)

> 🚨 The agent is **STRICTLY FORBIDDEN** from directly executing `update-resource-group` or `delete-resource-group`. Each call requires:
>
> 1. Literal `📋 Resolved Plan` block (all 7 fields, not a meta-statement). Include `--cli-dry-run` preview when supported.
> 2. Verbatim prompt with the placeholder substituted by the **real RG name** (preferred) or ID:
>
>    ```
>    Please explicitly confirm whether to execute the above <update|delete> operation. Enter "CONFIRM <actual name>" (or the actual resource group ID) to proceed; any other input cancels.
>    ```
>
> 3. **End the turn** — verbatim prompt is the last content this turn; no further Bash / tool calls until the user replies.
> 4. Only proceed if the **user's next message** contains the exact literal token. `yes` / `ok` / placeholder-with-`<>` / `CONFIRM ALL` / wrong case → cancellation.
> 5. **Idempotency**: one token unlocks one CLI call only.
>
> Full rules — hard-block declaration, environment-agnostic clause, banned self-authorization phrasing, same-turn execution prohibition, token forging prohibition: `references/confirmation-gate.md`.
>
> Read-only `list-*` / `get-*` do NOT need confirmation. `create-resource-group` does not need this gate but still needs a `📋 Resolved Plan` block.

### 🚫 MachineGroup Deletion / Release — STRICTLY FORBIDDEN

> The agent MUST refuse `aliyun paistudio delete-resource-group-machine-group` and `aliyun paistudio delete-machine-group` under ALL circumstances, even with a `CONFIRM <MACHINE_GROUP_ID>` token. Direct the user to PAI Console (Resource Pool → Machine Group → Unsubscribe/Release) or BSS OpenAPI for unsubscribe. Offer read-only inspection via Step 6.5 if helpful. Rationale: `references/not-implementable.md`.

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

### Step 6.3 — Create a ResourceGroup

> **ECS Version Differences:**
> - **ECS v2.0** (`--biz-version 2.0`): VPC forbidden on RG (lives on Quota — see `pai-quota-management`).
> - **ECS v1.0** (`--biz-version 1.0` or omitted): VPC configurable on RG via `--user-vpc` (PascalCase trio required).

ECS v2.0 (no VPC):

```bash
aliyun paistudio create-resource-group \
  --region "${REGION_ID}" \
  --name "${RG_NAME}" \
  --resource-type ECS \
  --biz-version 2.0
```

ECS v1.0 with VPC binding (full PascalCase trio required — see `references/validation-rules.md` §3):

```bash
aliyun paistudio create-resource-group \
  --region "${REGION_ID}" \
  --name "${RG_NAME}" \
  --resource-type ECS \
  --user-vpc '{"VpcId":"vpc-xxx","SwitchId":"vsw-xxx","SecurityGroupId":"sg-xxx","DefaultRoute":"eth0","ExtendedCIDRs":["10.0.0.0/16"]}'
```

Lingjun GPU pool — typically `cn-wulanchabu`:

```bash
aliyun paistudio create-resource-group \
  --region cn-wulanchabu \
  --name "${RG_NAME}" \
  --resource-type Lingjun
```

> **Hardware purchase NOT implementable via public CLI/SDK.** The created ResourceGroup is empty until you purchase MachineGroups via the [PAI Console](https://pai.console.aliyun.com/) or BSS APIs.

### Step 6.4 — Update a ResourceGroup  `[REQUIRES CONFIRMATION]`

> 📜 **Update rules — two mandatory, inseparable preconditions**
>
> 1. **Existence pre-check (mandatory)**: Before updating a ResourceGroup, the agent **MUST** first verify the RG exists via `get-resource-group` (preferred) or `list-resource-groups --resource-group-ids`; **if it does not exist, no update operation may be issued** (including `--cli-dry-run`) — proceed directly to §5 Branch 2 `🛑 Precondition Not Met` and exit.
> 2. **Two-step confirmation (mandatory)**: Before issuing an update operation, the agent **MUST** receive an explicit literal `CONFIRM <RG_NAME>` (or `CONFIRM <RG_ID>`) token from the user; same-turn execution / self-authorization / batch tokens / unsubstituted placeholders are all treated as over-reach.
>
> These two rules are equivalent to the `[MUST]` detailed rules below — execute literally; any reduction, merging, or skipping = P0 over-reach (see `references/compliance-redlines.md` R3 + R4).

> 🔍 **[MUST] Pre-check 1 — RG existence (read-only).** Before any `update-resource-group` (including `--cli-dry-run`), the agent MUST verify the target RG exists by calling either:
>
> ```bash
> aliyun paistudio list-resource-groups \
>   --region "${REGION_ID}" \
>   --resource-group-ids "${RESOURCE_GROUP_ID}"
> # OR
> aliyun paistudio get-resource-group \
>   --region "${REGION_ID}" \
>   --resource-group-id "${RESOURCE_GROUP_ID}"
> ```
>
> If the result is empty (`TotalCount=0`) or returns `NotFound` → emit a `🛑 Precondition Not Met` block (per §5 Branch 2 / `references/validation-rules.md` §2 row **E1**), call `aliyun configure ai-mode disable`, and exit. **NO `update-resource-group` CLI may be issued** (not even `--cli-dry-run`). Skipping this pre-check = P0 over-reach.

> ⚠️ **Parameter minimization principle**: the CLI command MUST carry only the parameter fields actually changing this turn. Updating only `description`? **NEVER** include `--name`. Updating only VPC? **NEVER** include `--name` or `--description`. Carrying unchanged fields = silent rewrite = unauthorized over-reach.

> 🚨 **[MUST] Two-Step Confirmation Gate** — after the existence pre-check passes, the update goes through the standard gate: print the `📋 Resolved Plan` block (Action / Region / ResourceGroupId / Field diff / Preconditions verified — explicitly cite the existence-check evidence / Blast radius / Resolved command), run `--cli-dry-run`, ask the verbatim CONFIRM prompt with the real RG name (preferred) substituted in, and **end the turn**. Only issue the `update-resource-group` CLI in the **next** turn after the user replies with the literal `CONFIRM <real RG name>` (or ID) token. One token unlocks exactly one `update-resource-group` call.

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

#### Changing VPC on a ResourceGroup — type restrictions

> 🚫 **VPC update is ONLY allowed on ECS v1.0 ResourceGroups.** The following ResourceGroup types **STRICTLY FORBID** VPC update via `update-resource-group`:
>
> | ResourceGroup type | VPC update allowed? | Reason | Agent action |
> |---|---|---|---|
> | **Lingjun** | **NO** | Lingjun VPC is managed at the Lingjun infrastructure layer, not via paistudio API | Refuse in plain natural language (forbidden-string rule applies — see §4 below). Point user to Lingjun infrastructure team / account manager. |
> | **ECS v2.0** (`BizVersion=2.0`) | **NO** | ECS v2.0 VPC lives on `Quota.QuotaConfig.UserVpc`, not on the RG | Refuse and explain VPC should be configured via `pai-quota-management` at the Quota level. |
> | **ECS v1.0** (`BizVersion=1.0`) | **YES** | VPC is bound to the RG directly | Proceed with unbind→rebind two-step sequence below. |
>
> When the user requests a VPC update, the agent **MUST** first run the existence + type pre-check (below) to determine the RG type, then apply the corresponding action from the table above.

> 🔍 **[MUST] Existence + type pre-check (VPC update)**: Before any VPC change (including `--cli-dry-run`), the agent **MUST** call `get-resource-group` or `list-resource-groups --resource-group-ids` to verify: (1) RG exists; (2) `ResourceType`; (3) `BizVersion` (ECS only). Then apply the type restriction table above:
>
> - **RG does not exist** → Branch 2 `🛑 Precondition Not Met`, disable AI-mode, exit. No VPC update CLI issued.
> - **ResourceType=Lingjun** → Refuse (forbidden-string rule). Disable AI-mode, exit. No VPC update CLI issued.
> - **ResourceType=ECS, BizVersion=2.0** → Refuse and explain VPC goes on `Quota.QuotaConfig.UserVpc`. Disable AI-mode, exit. No VPC update CLI issued.
> - **ResourceType=ECS, BizVersion=1.0** → Proceed with the two-step sequence below.

#### ECS v1.0 VPC change — two-step sequence

> ECS v1.0 VPC change is a **two-step** sequence: unbind first, then rebind. Each step requires its own `📋 Resolved Plan` block + its own `CONFIRM` token (`N=1 × M=2 = 2 tokens`).

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

> **[MUST] Use `list-resource-group-machine-groups` exclusively.** This skill does NOT use `get-resource-group-machine-group` / `get-machine-group`. To view a specific MG's details, filter by ID via `--machine-group-ids`; to browse all MGs, paginate via `--page-number` / `--page-size`.

List all MachineGroups under an RG (paginated):

```bash
aliyun paistudio list-resource-group-machine-groups \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --page-number 1 --page-size 20
```

View a specific MachineGroup's details (filter by ID):

```bash
aliyun paistudio list-resource-group-machine-groups \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}" \
  --machine-group-ids "${MACHINE_GROUP_ID}"
```

Additional `list` filters: `--name`, `--creator-id`, `--ecs-spec`, `--payment-type`, `--status`, `--order-instance-id`, `--disk-pl`, `--payment-duration`, `--payment-duration-unit`, `--sort-by`, `--order`.

> 🔍 **MachineGroup not-found handling**: When `list-resource-group-machine-groups --machine-group-ids "${MACHINE_GROUP_ID}"` returns `TotalCount=0` (the specified MG does not exist), the agent **MUST** immediately inform the user that the MachineGroup does not exist under the specified ResourceGroup, cancel subsequent operations, call `aliyun configure ai-mode disable`, and exit. The agent **MUST NOT** silently ignore the error and continue, **MUST NOT** silently retry or guess an alternative MachineGroupId. Likewise, when a list query without `--machine-group-ids` returns `TotalCount=0` (no MGs under the RG), the agent should clearly inform the user that the ResourceGroup currently has no MachineGroups, and exit normally.

### Step 6.6 — Observe usage / metrics

> ⚠️ **DEPRECATED — NOT SUPPORTED.** If asked for `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, or `get-node-metrics`, respond:
>
> > "ResourceGroup metrics / request-aggregate APIs have been deprecated and are no longer supported by this skill. Please use the PAI Console or contact your administrator."

### Step 6.7 — Delete the ResourceGroup  `[REQUIRES CONFIRMATION]`

> 📜 **Delete rules — three mandatory, inseparable preconditions**
>
> 1. **Existence pre-check (mandatory, Pre-check 1)**: Before deleting a ResourceGroup, the agent **MUST** first verify the RG exists (`get-resource-group` preferred / `list-resource-groups --resource-group-ids` equivalent); **when the RG does not exist, `delete-resource-group` MUST NOT be called** (including `--cli-dry-run`) — proceed directly to §5 Branch 2 `🛑 Precondition Not Met` and exit.
> 2. **MachineGroup-empty pre-check (mandatory, Pre-check 2, only run after Pre-check 1 passes)**: When the RG exists, the agent **MUST** call `list-resource-group-machine-groups --page-size 1` to read the MG count; **proceed only when `TotalCount == 0`**; if MG count > 0 → Branch 2, direct the user to release MGs via PAI Console (the agent MUST NOT release MGs on the user's behalf — see §6 *MachineGroup Deletion / Release — STRICTLY FORBIDDEN*).
> 3. **Two-step confirmation (mandatory)**: After both pre-checks pass, the agent **MUST** receive an explicit literal `CONFIRM <RG_NAME>` (or `CONFIRM <RG_ID>`) token from the user before issuing `delete-resource-group`; same-turn execution / self-authorization / batch tokens / unsubstituted placeholders are all treated as over-reach.
>
> These three rules MUST be executed in the order above — they are non-negotiable and non-reorderable: skipping Pre-check 1 to run Pre-check 2, skipping Pre-checks 1/2 to emit Resolved Plan, or skipping CONFIRM to run delete — any of these = P0 over-reach (see `references/compliance-redlines.md` R3 + R4 / `references/validation-rules.md` §2 rows E2 + E3).

> 🚨 **Destructive.** Two-Step Confirmation Gate applies. **Two read-only pre-checks** MUST pass strictly in order before the `📋 Resolved Plan` block is printed; if either fails, emit a `🛑 Precondition Not Met` block (per §5 Branch 2), call `aliyun configure ai-mode disable`, and exit — **NO `delete-resource-group` CLI is issued, not even `--cli-dry-run`**.

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
# Expect: TotalCount == 0. Otherwise → Branch 2 (validation-rules.md §2 row E3) → STOP and direct user
# to release MGs in PAI Console (the agent CANNOT release MGs on the user's behalf).

# Pre-checks passed → 📋 Resolved Plan (citing both pre-check results as Preconditions verified)
# → verbatim CONFIRM prompt with the real RG name → end the turn → wait for user's next-turn token.

# After receiving the literal CONFIRM token in the next turn, issue exactly one delete CLI:
aliyun paistudio delete-resource-group \
  --region "${REGION_ID}" \
  --resource-group-id "${RESOURCE_GROUP_ID}"
```

> Pre-check ordering is non-negotiable: existence first (Pre-check 1), MG-count second (Pre-check 2). Running Pre-check 2 against a non-existent RG would produce a misleading `TotalCount=0` interpretation — you would then incorrectly think the RG is "empty and ready to delete" when in fact it never existed. Skipping Pre-check 1 is treated as P0 over-reach equivalent to mutating without a CONFIRM token (see `references/compliance-redlines.md` R3 + R4).

### 🏁 Exit Checklist + Compliance Red Lines

> **[MUST]** Before generating the final user-facing reply for **any** exit path (success / failure / refusal / cancellation / Branch 1 wait / Branch 2), the agent MUST:
>
> 1. Issue `aliyun configure ai-mode disable` as the **last** `aliyun` CLI of the turn.
> 2. Pass the §6 *Exit Checklist* (flow order): branch block → CONFIRM (cross-turn) → CLI → disable. Full 7-point version + recovery procedure: `references/exit-checklist.md`.
> 3. Pass the **Compliance Red Lines R1-R7** (non-negotiable): MG deletion refused / AI-mode closed / CONFIRM cross-turn / branch block literal / channel pure / Lingjun forbidden-string / parameter minimization. Full table + rationale: `references/compliance-redlines.md`.
>
> Both checklists are **AND**, not OR. Missing the disable — even on a refusal turn — is a P0 workflow defect: the next turn's first action MUST be `aliyun configure ai-mode disable` before anything else.

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
