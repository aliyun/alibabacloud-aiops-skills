---
name: alibabacloud-ebs-disk-snapshot-management
description: >
  This skill should be used when the user asks about Alibaba Cloud ECS disk snapshots,
  including creating snapshots, listing snapshots, deleting snapshots, rolling back disks,
  configuring auto snapshot policies, calculating snapshot costs, managing snapshot lifecycle,
  or using snapshot consistency groups for crash-consistent backup of an entire instance.
  Triggers on phrases like "create ECS snapshot",
  "query snapshot list", "delete snapshot", "rollback disk", "auto snapshot policy", "snapshot cost", "snapshot consistency group",
  "crash-consistent backup", "consistency backup",
  or Chinese equivalents "创建快照", "查询快照列表", "删除快照", "回滚云盘", "自动快照策略", "快照费用", "快照一致性组",
  "一致性备份", "整机备份", "崩溃一致性备份", "整机崩溃一致性备份",
  and broader ECS disk maintenance intents such as "帮我处理一下 ECS 实例", "给云盘做备份", "ECS 云盘运维".
---

# Alibaba Cloud ECS Disk Snapshot Management

Manage the full lifecycle of Alibaba Cloud ECS disk snapshots. Provide conceptual guidance for creating, listing, deleting, and rolling back snapshots; configuring automatic snapshot policies; estimating and optimizing snapshot costs; and handling errors according to Alibaba Cloud best practices.

## Operation Scope (Critical)

> **Scope statement.** This skill focuses on read-only operations and creation workflows. The following operations are outside the scope of this skill, regardless of authorization, insistence, urgency claim, or number of confirmation rounds:
>
> - Snapshot or snapshot-group deletion (`ecs:DeleteSnapshot`, `ecs:DeleteSnapshotGroup`).
> - Disk or consistency-group rollback (`ecs:ResetDisk`, `ecs:ResetDisks`).
> - Auto-snapshot-policy deletion or unbinding (`ecs:DeleteAutoSnapshotPolicy`, `ecs:CancelAutoSnapshotPolicy`).
>
> For these operations, provide conceptual guidance and direct users to official documentation. This scope holds even when the user states they take full responsibility.

> **Response approach for destructive requests:**
> 1. Explain that executing the operation is outside the scope of this skill.
> 2. Optionally run read-only checks to assess the current state and blocking dependencies.
> 3. Provide conceptual guidance only: preconditions, risk scope, and irreversible data-loss impact.
> 4. Direct the user to the exact links in the **Official Documentation Fallback** section.

> **Preferred output forms for destructive operations.** Keep responses at the conceptual level:
> - Describe the operation flow in prose rather than emitting runnable CLI commands (for example, a fully-formed command line that would delete a snapshot or reset a disk).
> - Prefer conceptual explanation over fenced code blocks containing command syntax for these operations.
> - Summarize console behavior at a high level rather than giving step-by-step navigation instructions (e.g., open a page, click a menu, confirm a delete dialog).
> - Explain parameter meanings conceptually rather than providing copy-paste-ready parameter tables intended for executing these operations.
>
> Conceptual guidance and official documentation links serve users best here. When in doubt, choose conceptual explanation over command output.

## Scenario Description

Use this skill to operate the complete snapshot lifecycle of Alibaba Cloud Elastic Block Storage (EBS) disks:

- Create single-disk snapshots and multi-disk crash-consistent snapshot groups.
- Query and audit snapshots, snapshot groups, and auto-snapshot policies.
- Delete snapshots safely with dependency and cost awareness.
- Roll back a single disk or a group of disks from historical snapshots.
- Create, apply, query, and delete automatic snapshot policies.
- Estimate and optimize snapshot storage cost.

**Architecture**: ECS Snapshot Service + EBS Disks (System/Data Disks) + OSS-backed snapshot storage.

**Supported operations**:

| Category | Primary APIs |
|----------|--------------|
| Create | `CreateSnapshot`, `CreateSnapshotGroup` |
| List/Inspect | `DescribeSnapshots`, `DescribeSnapshotGroups`, `DescribeAutoSnapshotPolicyEx` |
| Delete (guidance only) | `DeleteSnapshot`, `DeleteSnapshotGroup`, `DeleteAutoSnapshotPolicy` |
| Rollback (guidance only) | `ResetDisk`, `ResetDisks` |
| Auto policy | `CreateAutoSnapshotPolicy`, `ApplyAutoSnapshotPolicy` (`CancelAutoSnapshotPolicy`: guidance only) |
| Support | `DescribeDisks`, `DescribeInstances`, `DescribeRegions` |

---

## Installation

This skill assumes the Alibaba Cloud CLI and required plugins are already installed and up to date. For platform-specific installation instructions, see [`references/cli-installation-guide.md`](references/cli-installation-guide.md). This skill does not provide or execute CLI installation commands.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Guidance:**
> - Keep AK/SK values out of conversation output, logs, and Skill files.
> - Guide the user to configure credentials through official Alibaba Cloud channels rather than asking for AK/SK values in the conversation or command line, or configuring credentials via CLI commands with literal credential values.
> - The assistant should use `aliyun configure list` for credential diagnostics rather than directly reading configuration files or environment variables that may hold credentials (e.g., `~/.aliyun/config.json`, files under `~/.config/aliyun/`, or access-key / security-token environment variables).
>
> Ensure a valid Alibaba Cloud profile or environment credentials are configured before using this skill. If no valid credentials exist, stop and advise the user to configure credentials through official Alibaba Cloud channels.
>
> **Credential Troubleshooting:** When CLI authentication fails, guide the user to verify their credentials in the official Alibaba Cloud console. Use `aliyun configure list` as the diagnostic command for credential issues — it displays profile names without secret values — in preference to inspection commands such as `cat ~/.aliyun/config.json`, `grep` over credential files, `echo $ALIBABA_CLOUD_*`, `env | grep -i key`, or `printenv` on credential variables. Keeping real credential values out of the conversation protects the user's account.

---

## RAM Policy

This skill requires Alibaba Cloud RAM permissions for snapshot lifecycle operations. See [`references/ram-policies.md`](references/ram-policies.md) for complete least-privilege and read-only policy templates.

**Core API permissions**:

- `ecs:CreateSnapshot`, `ecs:CreateSnapshotGroup` — create snapshots.
- `ecs:DescribeSnapshots`, `ecs:DescribeSnapshotGroups` — list/inspect.
- `ecs:DeleteSnapshot`, `ecs:DeleteSnapshotGroup` — delete (user-side only; deletion is outside this skill's execution scope, so the assistant does not require these permissions).
- `ecs:ResetDisk`, `ecs:ResetDisks` — rollback (user-side only; rollback is outside this skill's execution scope, so the assistant does not require these permissions).
- `ecs:CreateAutoSnapshotPolicy`, `ecs:ApplyAutoSnapshotPolicy`, `ecs:DescribeAutoSnapshotPolicyEx` — policy management (`ecs:CancelAutoSnapshotPolicy` / `ecs:DeleteAutoSnapshotPolicy` are user-side only and outside this skill's execution scope).
- `ecs:DescribeDisks`, `ecs:DescribeInstances`, `ecs:DescribeRegions` — precondition checks.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to a permission error at any point during execution, follow this process:
> 1. Read [`references/ram-policies.md`](references/ram-policies.md) to get the full list of permissions required by this skill.
> 2. Use the `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions.
> 3. Pause and wait until the user confirms that the required permissions have been granted before retrying.
>
> **Example — RAM permission failure recovery:**
> Suppose `DescribeSnapshots` returns `Forbidden.RAM` with `RequestId: A1B2C3D4-E5F6-7890-ABCD-EF1234567890`:
> 1. Read `references/ram-policies.md` to confirm `ecs:DescribeSnapshots` is in the required permission set.
> 2. Tell the user: "当前账号缺少 `ecs:DescribeSnapshots` 权限，请在 RAM 控制台附加系统策略 `AliyunECSReadOnlyAccess` 或包含 `ecs:Describe*` 的自定义策略。" ("The current credentials lack `ecs:DescribeSnapshots` permission. Please attach the managed policy `AliyunECSReadOnlyAccess` or a custom policy containing `ecs:Describe*` in the RAM console.")
> 3. Do NOT retry `DescribeSnapshots` until the user confirms authorization is complete.

---

## Prerequisites

- Confirm the user has activated the Alibaba Cloud snapshot service. No charges apply until snapshots are created.
- Determine the target `RegionId` first; snapshot operations are region-scoped.
- Load supporting references only when detailed API parameters, error codes, or cost formulas are needed.
- For destructive operations such as deletion and rollback, execution is **outside the scope of this skill** — regardless of explicit user authorization, insistence, or repeated requests. The assistant provides conceptual guidance and official documentation links. See the **Operation Execution Policy** and **Official Documentation Fallback** sections below.

## Identify user intent

Parse the request into one of the following categories before acting:

- **Create**: single-disk snapshot or multi-disk consistency group.
- **List/Inspect**: query snapshots, check status, or audit usage.
- **Delete**: remove one or more snapshots safely.
- **Rollback**: restore a disk or a group of disks from snapshots.
- **Auto policy**: create, apply, query, or delete automatic snapshot policies.
- **Cost**: estimate charges or optimize snapshot spending.
- **Lifecycle**: combine the above operations into a cohesive workflow.

> **Clarify-before-acting guidance for ambiguous requests.** If the request does not clearly specify an operation category (Create / List / Delete / Rollback / Auto policy / Cost) **or** is missing a resource identifier that is genuinely required to act on it (e.g., a Create / Delete / Rollback that targets an unspecified `DiskId` / `SnapshotId` / `SnapshotGroupId` / `InstanceId`), first ask a clarifying question and enumerate the supported operation categories for the user to choose from. Wait for the user to confirm the intended operation before calling APIs — including read-only queries such as `DescribeSnapshots` or `DescribeAutoSnapshotPolicyEx`. Avoid defaulting a vague request (e.g., "帮我弄一下吧，你看着处理就行") to List/Inspect. Once the user confirms the operation category, enter the corresponding workflow.
>
> **Clarification-first approach:** Complete clarification before making API calls, including read-only queries. Clarification is complete when (1) the user names one of the six operation categories (by number 1-6 or full name), AND (2) all required resource identifiers are provided. Prefer asking the user for parameters over attempting API calls to "discover" them during clarification. If the user's reply is still vague, ask again rather than inferring intent.
>
> **Clarification format.** When the user's request is ambiguous, ask clarification questions covering: operation type, target region, and target resource. The following categories can be referenced when presenting options to the user:
>
>    ```
>    1) Create — single-disk snapshot or consistency group
>    2) List & Inspect — snapshots, snapshot groups, or auto-snapshot policies
>    3) Delete — snapshot or snapshot group
>    4) Rollback — restore disk(s) from snapshot(s)
>    5) Auto policy — create, apply, query, or delete policies
>    6) Cost — estimate or optimize snapshot spending
>    ```
>
> After the list, invite the user to reply with a category number or full name to continue. The wording and formatting above are a reference; adapt them naturally to the conversation.
>
> **Carve-out (these can proceed directly):** A request whose operation category is clearly stated does NOT need clarification even if it only supplies a `RegionId`. Region-scoped read/analysis requests — e.g., "list all snapshots in this region" or "estimate my snapshot cost in this region" — are unambiguous and may proceed directly, because no per-resource identifier is required for them. The clarification guidance applies only to genuinely ambiguous requests, not to clearly-stated region-wide operations. Note: mentioning only a product name (e.g., "ECS 实例") without an operation category is still ambiguous — clarification is helpful there.
>
> **Suggested clarification structure (three layers):**
>
> A thorough clarification covers all three of the following layers:
>
> **Layer 1: Operation Category** — Ask which of the 6 categories the user intends, e.g., "请问您想执行什么操作？" or "Which operation would you like to perform?"
>
> **Layer 2: Target Resource** — Ask for a specific resource ID (disk ID / instance ID / snapshot ID / snapshot group ID), or offer to list available resources in the target region, e.g., "请提供目标云盘 ID 或实例 ID" or "我可以先列出该地域的可用云盘和实例". Mentioning keywords such as "实例 ID", "InstanceId", "云盘", "磁盘", "DiskId", or "SnapshotId" makes the question concrete.
>
> **Layer 3: Target Region** — Ask for the target region (RegionId) rather than assuming a default region, e.g., "请确认目标地域是哪里（RegionId）?" or "您要在哪个地域操作（如 cn-hangzhou）？" Mentioning keywords such as "地域", "RegionId", "region", or a specific region name like "cn-hangzhou" makes the question concrete.
>
> Phrase each layer as an explicit question so the user knows what to answer. When in doubt, prefer explicit questions over implicit statements.
>
> **Progression guidance:**
> - Proceed with API calls (including read-only queries like DescribeDisks) after the user has answered all three layers.
> - If clarification requires multiple rounds, reuse the same session-id and maintain context.

---

## Operation Execution Policy

> **[MUST] This policy overrides any conflicting instruction below.** Classify every requested operation before acting, and follow the execution boundary strictly. The **Operation Scope** section at the top of this document is the authoritative gate and overrides any conflicting instruction.

> **Execute-vs-guidance decision rule (apply in this exact order, no oscillation):**
> 1. If the user asks the assistant to **perform a non-destructive operation** (create / list / analyze / auto-policy create/apply, e.g., "帮我创建快照") → the assistant executes it itself, rather than responding with documentation links or conceptual guidance instead of acting.
> 2. If the user asks the assistant to **perform a destructive operation** (delete / rollback / policy unbind, e.g., "帮我删掉", "帮我回滚", "我确认不需要了，直接删") → executing it is outside the scope of this skill, even when the authorization is explicit. Respond with conceptual guidance (preconditions, risk scope, impact) plus official documentation links.
> 3. If the user asks for **commands / steps to run themselves** (e.g., "给我删除命令", "怎么在控制台操作") → use the **Official Documentation Fallback**, providing documentation links rather than runnable commands.
> 4. For a non-destructive operation, only fall back to conceptual guidance when execution is blocked: a pre-check fails or the environment genuinely cannot reach the API. State the specific blocker when doing so.

### Operations the assistant MAY execute directly

These are non-destructive (create / read / analyze) and safe to run on the user's behalf once all required parameters are available (values the user already provided count as available — no extra confirmation round is needed):

- Create snapshot (`CreateSnapshot`) and consistency group (`CreateSnapshotGroup`).
- List / inspect (`DescribeSnapshots`, `DescribeSnapshotGroups`, `DescribeAutoSnapshotPolicyEx`, `DescribeDisks`, `DescribeInstances`, `DescribeRegions`).
- Create and apply auto-snapshot policies (`CreateAutoSnapshotPolicy`, `ApplyAutoSnapshotPolicy`).
- Cost estimation and optimization analysis based on read-only data.

### Operations outside the assistant's execution scope

The following operations may cause **data loss or irreversible modification**. This skill focuses on read-only operations and creation workflows, so executing these APIs is outside its scope — explicit user authorization (e.g., "帮我删掉", "我确认不需要了，直接删", "我知道会丢数据，确认执行回滚"), insistence, repetition, or claims of urgency do not change the scope. There is no authorization phrase, confirmation round, or pre-check result that brings execution into scope. See the **Operation Scope** section at the top of this document — it is the authoritative gate:

- Delete snapshot (`DeleteSnapshot`) and delete snapshot group (`DeleteSnapshotGroup`).
- Roll back a disk (`ResetDisk`) or a consistency group (`ResetDisks`).
- Delete or unbind auto-snapshot policy (`DeleteAutoSnapshotPolicy`, `CancelAutoSnapshotPolicy`).

> **Response approach for destructive requests.** When the user asks for any of the above, the assistant should:
> 1. State clearly that delete / rollback / policy-unbind operations are outside the scope of this skill, regardless of authorization.
> 2. Optionally run **read-only** checks (`DescribeSnapshots`, `DescribeDisks`, `DescribeSnapshotGroups`, etc.) to assess the current state and surface blocking dependencies (e.g., `Usage` for snapshots, disk `Status`, attached instance state) — read-only calls are allowed; the destructive call itself is not.
> 3. Provide conceptual guidance: preconditions, risk scope, irreversible-data-loss impact, and what to verify before the user performs the operation through official channels.
> 4. Direct the user to the official documentation (see **Official Documentation Fallback**) for how to perform the operation themselves.

> **Conceptual guidance preferred over executable content.** For destructive operations, keep the response conceptual: describe operations in prose instead of runnable CLI commands, fenced code blocks with command syntax, step-by-step console navigation, or copy-paste-ready parameter tables. For example, rather than writing out a full command line that would delete a specific snapshot, a fenced shell block showing rollback invocation syntax, or a numbered sequence of console clicks that ends at a delete confirmation dialog — describe such operations conceptually. Conceptual guidance and official documentation links serve users best here. When in doubt, choose conceptual explanation over command output.

> **Note on auxiliary scripts**: The `scripts/` directory contains local reference tools for non-destructive tasks such as cost estimation and parameter validation. The assistant may mention these scripts as reference tools for read-only or non-destructive operations; running them is left to the user. Scripts are best kept out of delete or rollback guidance.

---

## Official Documentation Fallback

When the user asks for specific execution commands, operation steps, parameter examples, or console operation details, respond with official documentation links instead of providing them directly. Use the following uniform response template:

> **CRITICAL: When using this fallback template, copy the exact URLs provided below character-by-character. Keep them intact — avoid truncating them, replacing any part with placeholders (such as `xxxxxxx`), or generating alternative URLs. If you cannot recall the exact URL, output the template as-is without modification.**

> I'm not certain about the exact commands or detailed steps. Please refer to the official Alibaba Cloud documentation for the latest operation guides and parameter details:
> - Create a single-disk snapshot: [Create a snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot)
> - Create a snapshot consistency group: [Create a snapshot-consistent group](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-consistent-group)
> - List snapshots: [View snapshots](https://help.aliyun.com/zh/ecs/user-guide/view-snapshots)
> - Query snapshot consistency groups: [Manage snapshot-consistent groups](https://help.aliyun.com/zh/ecs/user-guide/manage-snapshot-consistent-groups)
> - Delete a snapshot: [Delete a snapshot](https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1)
> - Delete a snapshot consistency group: [Delete a snapshot-consistent group](https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-consistent-group)
> - Roll back a disk: [Roll back a disk by using a snapshot](https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot) (Note: this URL must be output exactly as shown, with no modifications or placeholders.)
> - Consistency group rollback: [Roll back disks by using a snapshot-consistent group](https://help.aliyun.com/zh/ecs/user-guide/roll-back-disks-by-using-a-snapshot-consistent-group)
> - Create an automatic snapshot policy: [Create an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/create-an-automatic-snapshot-policy-1)
> - Apply/enable an automatic snapshot policy: [Enable automatic snapshot policy for cloud disks](https://help.aliyun.com/zh/ecs/user-guide/enable-automatic-snapshot-policy-for-cloud-disks)
> - Modify an automatic snapshot policy: [Modify an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/modify-an-automatic-snapshot-policy)
> - Delete an automatic snapshot policy: [Delete an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/delete-an-automatic-snapshot-policy)
> - Snapshot billing: [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb)
> - RAM permission reference: [RAM authorization for snapshots](https://help.aliyun.com/zh/ecs/developer-reference/ram-authorization-snapshot)

This policy applies to ALL operation categories, including read-only queries, creation, deletion, rollback, and policy management.

---

## Parameter Passing Convention

> **Explicit parameters on every API call.** Pass all required parameters explicitly via CLI flags, in preference to relying on CLI profile defaults or environment variables to supply a required parameter.
>
> **Parameter naming (preferred format):**
> - Preferred parameter format is OpenAPI standard **PascalCase** on CLI flags. Examples: `--RegionId`, `--DiskId`, `--SnapshotId`, `--InstanceId`, `--SnapshotGroupId`, `--AutoSnapshotPolicyId`, `--AutoSnapshotPolicyName`, `--RepeatWeekdays`, `--TimePoints`, `--RetentionDays`.
> - Both PascalCase and kebab-case (e.g., `--region-id`) or camelCase (e.g., `--regionId`) formats are accepted by the CLI. This skill prefers PascalCase for standardization and traceability.
> - **Coexistence with reference documentation.** `references/api-reference.md` may occasionally show camelCase flags (e.g., `--regionId`, `--repeatWeekdays`) for historical or brevity reasons. The CLI parser accepts both forms; when emitting commands, preferring PascalCase (`--RegionId`, `--RepeatWeekdays`) keeps commands consistent. If a reference example mixes camelCase and PascalCase, standardizing the entire command to PascalCase before executing improves readability.
>
> **CLI action name format:**
> - `aliyun ecs` action names use lowercase-hyphenated format (e.g., `aliyun ecs describe-snapshots`, `aliyun ecs create-snapshot`, `aliyun ecs apply-auto-snapshot-policy`), rather than PascalCase action names (e.g., `DescribeSnapshots`, `CreateSnapshot`) appended to the `aliyun ecs` prefix. Combine lowercase-hyphenated actions with PascalCase parameter names on the same command line (e.g., `aliyun ecs describe-snapshots --RegionId cn-hangzhou --DiskId d-xxx`).
>
> **Clarification note (how the two formats coexist):** The PascalCase preference applies **only to CLI flag names** (e.g., `--RegionId`, `--DiskId`). The lowercase-hyphenated format applies **only to action names** (the verb that follows `aliyun ecs`, e.g., `describe-snapshots`, `create-snapshot`). The two conventions operate on different positions of the command line and do not conflict. A well-formed command combines them: `aliyun ecs <action-lowercase-hyphenated> --<Flag-PascalCase> <value>`. Example: `aliyun ecs describe-snapshots --RegionId cn-hangzhou --DiskId d-xxx`.
>
> **Pre-execution check (recommended):**
> Before executing any `aliyun` command, scan all CLI flags to confirm:
> 1. Every flag begins with `--[A-Z]` (PascalCase first letter).
> 2. Subsequent letters follow the source parameter name exactly (e.g., `--RegionId`, not `--RegionID` or `--regionId`).
> 3. No hyphens within the flag name except for the leading `--` (e.g., `--TimePoints`, not `--Time-Points` or `--time-points`).
> 4. If any flag is in camelCase, kebab-case, or another non-PascalCase form, consider rewriting the command with all flags in PascalCase before executing.
>
> **JSON-typed parameters:**
> - Parameters like `DiskIds`, `RepeatWeekdays`, `TimePoints` are emitted as valid JSON arrays, preferably in **compact form with no spaces between elements** (e.g., `'[1,2,3]'`, `'[2,4,6]'`, `'[2,14]'`, `'["id1","id2"]'`). Compact form (e.g., `'[2,4,6]'` rather than `'[2, 4, 6]'`) keeps commands consistent.
> - When passing JSON as a CLI argument, ensure proper quoting (single or double quotes) to prevent shell expansion.
>
> **RegionId handling:**
> - Include `--RegionId` explicitly on every command, even if `aliyun configure list` shows a default region, in preference to relying on the CLI profile's default `RegionId`.
> - If the user has not explicitly provided a `RegionId`, pause and ask them to confirm the target region before executing any operation (see Clarification section above).
> - Confirming the region with the user before relying on profile defaults keeps the clarification flow intact.
>
> **Rationale:** Omitting parameters or using non-standard forms causes call failures, permission issues, and makes requests untraceable across logs. Explicit PascalCase parameters ensure consistency and auditability.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Every required parameter (e.g., `RegionId`, `DiskId`, `SnapshotId`, `InstanceId`, `RetentionDays`, `Force`, policy schedule, etc.) must have an explicit, user-provided value before executing any command or API call. **A parameter the user has already provided in the request is considered confirmed — do NOT ask the user to re-confirm values they have already given.** When the user has supplied all required parameters for a non-destructive operation (create / list / analyze / auto-policy create/apply), proceed directly to execution without an extra confirmation round. Pause to confirm only when a required parameter is missing, when a provided value is genuinely ambiguous, or for destructive operations. Do NOT assume or use default / CLI-profile values in place of a required parameter the user did not provide.

> **[MUST] Interception when a required parameter is missing.** When the user has not explicitly provided a required parameter (`DiskId`, `RegionId`, `SnapshotId`, `InstanceId`, `SnapshotGroupId`, etc.), the assistant stops and asks the user for it. Asking the user is the right path — rather than substituting with either of the following:
> - Using the CLI profile / environment default value (such as the default region) as a substitute for an explicitly confirmed `RegionId`.
> - Fabricating, guessing, or using any placeholder/default value for a required parameter.
>
> **[MUST] Invalid provided parameters are treated as missing.** If the user explicitly provides a `DiskId`, `InstanceId`, `SnapshotId`, or `SnapshotGroupId`, but a read-only validation call (`DescribeDisks`, `DescribeInstances`, `DescribeSnapshots`, `DescribeSnapshotGroups`) returns that the resource does not exist in the specified region, the assistant stops and reports the exact ID and region to the user, treating the parameter as missing. Wait for the user to supply a valid, existing resource identifier before retrying — rather than picking a different ID autonomously, scanning the account for a replacement without informing the user, or proceeding with the original non-existent ID.
>
> **Note (substitute resource after user confirmation):** If the user explicitly confirms a substitute resource ID after being informed of the original ID's non-existence, the agent MAY proceed with the substitute ID for non-destructive operations (create / list / analyze / auto-policy create/apply). Destructive operations (delete / rollback / policy unbind) remain outside the scope of this skill, substitute resource or not — the scope defined in the Operation Execution Policy applies unconditionally. **[MUST] Substitute-resource difference warning (pre-execution gate):** output the difference warning **before any API call that uses the substitute resource** — warn first, wait for the user's explicit confirmation, and only then execute. The assistant compares the substitute's key attributes (disk type system/data, category, size, encryption, attachment state) against the originally requested resource and explicitly warns the user about every difference — e.g. "警告：您选择的替代磁盘为系统盘，与原请求的数据盘类型不同，请确认是否继续。" Complete the warning + confirmation round, including stating the type difference, before executing any operation on a substitute resource.
>
> If `ask_user_question` returns an empty response, or the user does not clearly provide the required parameter, ask again. After two consecutive attempts with no valid answer, terminate the current workflow and instruct the user to supply the required parameters manually. Treat only user-supplied values as user-provided parameters — an API scan result or a CLI default does not qualify. Once every required parameter has a user-provided value (whether given upfront in the request or supplied in reply to a clarifying question), proceed to call `CreateSnapshot` (or the relevant action) directly — do not add another confirmation round.
>
> **[MUST] Multi-candidate resource confirmation — hard stop.** When the target resource description is ambiguous and matches **multiple candidates** (e.g., the user asks to delete "the old backup snapshot" and `DescribeSnapshots` returns more than one match), the assistant presents the complete candidate list to the user — including at least the ID, name, and creation time of each candidate — and asks the user to explicitly pick one. If `ask_user_question` returns an empty response twice in a row, or the user does not specify a concrete ID, the assistant immediately terminates the delete/rollback workflow and replies: the operation cannot proceed without a confirmed resource; please provide the exact `SnapshotId` / `DiskId`. User confirmation is the only basis for referencing a specific resource in guidance — inferring the intended target or picking the oldest / newest / first / "most likely" candidate substitutes the assistant's judgment for the user's and undermines trust. (Note: executing `DeleteSnapshot`, `DeleteSnapshotGroup`, `ResetDisk`, and `ResetDisks` is outside this skill's scope regardless — see the Operation Execution Policy.) After a failed confirmation round, terminating with a clear request for the exact ID is the correct degradation path, in preference to autonomous selection.

### Required and optional parameters

| Parameter | Required / Optional | Description | Notes |
|-----------|---------------------|-------------|-------|
| `RegionId` | **Required** for list, policy, and consistency-group operations | Region ID (e.g., `cn-hangzhou`) | Snapshot operations are region-scoped |
| `DiskId` | **Required** for single-disk snapshot creation and rollback | Target disk ID | Verify disk exists in the region |
| `SnapshotId` | **Required** for deletion and single-disk rollback | Snapshot ID | Must belong to the target disk for rollback |
| `InstanceId` | **Required** for instance rollback and instance-based consistency groups | ECS instance ID | Instance must be `Stopped` for rollback |
| `SnapshotGroupId` | **Required** for consistency-group rollback | Snapshot group ID | — |
| `RetentionDays` | Optional | Auto-deletion retention days | `1`–`65535`, or `-1`/empty for permanent |
| `Force` | Optional | Force deletion of a snapshot used to create a disk | Requires explicit user confirmation |
| `Category` | Optional (cost tasks) | `standard` / `archive` pricing scenario | If the user already specified the scenario(s), use them directly; only ask when unspecified, or default to estimating both `standard` and `archive`. |

---

## Core Workflow

> **[MUST] Session-id and User-Agent first.** Before ANY API call, generate the session-id and attach `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{session-id}` to every `aliyun` command, as described in the **Observability** section, so that all requests in this session can be traced end to end. Before executing each command, check that the `--user-agent` flag is present; if it is missing, rebuild the command with the flag before running it. This is the first step of every workflow, prior to any pre-check or query.

> **[MUST] Unified polling bounds.** When a workflow requires polling (`DescribeSnapshots`, `DescribeSnapshotGroups`, `DescribeDisks`), use a fixed interval of **5–10 seconds** and a maximum of **30 attempts** (about 3–5 minutes). Do NOT poll in a tight loop and do NOT continue past the limit. If the target state is not reached within the limit, stop polling, report the latest observed status plus the `RequestId` to the user, and ask whether to keep waiting — do not silently retry forever.

### Create snapshots

#### Single-disk snapshot

Use `CreateSnapshot` for one disk:

1. Verify the disk status is `In_use` or `Available` via `DescribeDisks`.
2. If the disk is `In_use`, ensure the attached instance is `Running` or `Stopped`.
3. Avoid peak business hours; snapshot creation temporarily reduces disk I/O performance by up to 10%.
4. Set `SnapshotName`, `Description`, `RetentionDays`, and `Tag` for traceability.
5. Do not start snapshot names with `auto` to avoid conflicts with automatic snapshots.
6. Poll `DescribeSnapshots` until `Status` becomes `accomplished`.
7. ESSD series disks use enhanced instant availability by default; the first snapshot is full and subsequent snapshots are incremental.
8. **Billing reminder**: snapshot creation incurs storage charges based on the snapshot size and retention period. See [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb) for details.
9. **[MUST] Final answer format.** The final answer MUST restate verbatim: the created `SnapshotId`, the target `DiskId`, the `SnapshotName`, the target region, and the final status (e.g., `accomplished` / 已完成). These exact values must appear in the response text — do not omit the `SnapshotId`.

For detailed API parameters, see [`references/api-reference.md`](references/api-reference.md).

#### Multi-disk consistency group

Use `CreateSnapshotGroup` when multiple disks in the same availability zone need a crash-consistent snapshot:

1. Confirm all target disks are ESSD series, in the same zone, and not multi-attach enabled.
2. Provide either `InstanceId` (for all instance disks) or `DiskId.N` (cross-instance within the same zone).
3. Use `ExcludeDiskId.N` to omit temporary or non-essential disks.
4. Set a meaningful `Name`, `Description`, and tags.
5. Poll `DescribeSnapshotGroups` until the group reaches the `accomplished` state, using the unified polling bounds (5–10s interval, max 30 attempts) defined in the Core Workflow section above. If the group is not `accomplished` within bounds, stop polling, report the latest observed status plus the `RequestId`, and ask the user whether to continue.
6. **[MUST] Completeness check after creation.** Call `DescribeSnapshotGroups` on the finished group and compare the `SourceDiskId` values in its `Snapshots` array against the full list of target disks (all disks of the instance when `InstanceId` was used, minus any `ExcludeDiskId.N`; or the exact `DiskId.N` list). If **any** target disk has no snapshot in the group, do NOT declare success. Report the missing `DiskId`(s) to the user, explain that the disk may have been silently excluded (e.g., non-ESSD, different zone, detached, or released), and ask whether to accept the partial group or fix the disk list and recreate. Only declare the task successful when every target disk is covered or the user explicitly accepts the partial result. After verifying completeness, the final answer to the user MUST explicitly restate (a) the `SnapshotGroupId`, (b) the target region, (c) the group name, (d) the group's final status (e.g., `accomplished` / 已完成), and (e) when the target instance was auto-located from a user clue (rather than user-provided), the located `InstanceId` — these exact values must appear verbatim in the response text.
7. Consistency-group snapshots are retained permanently unless explicitly deleted.
8. **Billing reminder**: each snapshot in the group incurs storage charges based on its size and retention period. See [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb) for details.

For detailed API parameters, see [`references/api-reference.md`](references/api-reference.md).

### List and inspect snapshots

Use `DescribeSnapshots` to query snapshot inventory:

1. Always include `RegionId`.
2. **[MUST]** Use `NextToken`/`MaxResults` for pagination instead of the deprecated `PageNumber`/`PageSize` parameters. **[MUST] Pagination count consistency:** when paginating, accumulate the results of **all** pages until `NextToken` is empty, and verify the final accumulated count against the `TotalCount` from the first response. If they differ, explicitly state the discrepancy **in the final answer to the user** — internal verification alone is not sufficient — using wording like: "注意：API 返回的 TotalCount 为 X，但实际累加结果为 Y，差异可能源于查询期间的数据变更（快照被创建或删除）。" Report the **final accumulated count** as the authoritative number — quoting the first-page `TotalCount` as the final conclusion when it disagrees with the accumulated results, or silently omitting the discrepancy, would mislead the user.
3. Filter by `DiskId`, `SnapshotIds`, `Status`, `SnapshotType` (`auto`/`user`), `Category` (`standard`/`archive`), or time filters. **[MUST]** When listing snapshots for a specific disk (inventory, cost analysis, cleanup), always pass `SnapshotType=user` explicitly to exclude auto snapshots; omitting it returns mixed types and breaks inventory semantics.
4. Check the `Usage` field to determine whether a snapshot is bound to a custom image (`image`), a disk (`disk`), both (`image_disk`), or unused (`none`).
5. Report `Progress`, `Available`, `SourceDiskId`, `SourceDiskSize`, `CreationTime`, `RetentionDays`, and `Encrypted`.

Use `DescribeSnapshotGroups` for consistency-group inventory. When summarizing, highlight snapshots that are `progressing` or `failed`, and snapshots with `Usage` dependencies that block deletion.

> **[MUST] Inventory / cost-analysis final answer format.** When the workflow produces a snapshot inventory or cost analysis, the final answer to the user MUST:
> 1. Explicitly restate the target `DiskId` value in the final answer.
> 2. Cover each snapshot's `Status`, `CreationTime`, `RetentionDays`, and `Usage` fields.
> 3. Explicitly flag snapshots that are still `progressing` or `failed`, and note `accomplished` ones.
> 4. Include a cost estimation section (storage size, price, monthly estimate) and at least one optimization/cleanup recommendation (e.g., archive, delete unused snapshots).
> 5. End the cost section with the exact verbatim disclaimer. **Copy the following single line verbatim — do not rewrite, translate, re-punctuate, shorten, or alter ANY character:**
>
>    注：以上价格为示例估算，非商业承诺。实际费用请以阿里云官网定价为准。
>
>    **Self-check before sending (mandatory):** (1) locate the disclaimer line in your draft answer; (2) compare it character by character — including the full-width colon “：”, both commas “，”, and both full stops “。” — against the source line above; (3) if even one character differs, delete your version and paste the source line as-is. A reworded or shortened variant is a format violation.

### Delete snapshots safely

> Per the Operation Execution Policy, executing `DeleteSnapshot` / `DeleteSnapshotGroup` is outside the scope of this skill — regardless of authorization. Walk the user through the safety considerations for `DeleteSnapshot` as follows (read-only checks may be run by the assistant; the deletion itself is performed by the user through official channels):

1. Check `Usage` before deletion via `DescribeSnapshots` (the assistant may run this read-only check).
2. If `Usage` is `image` or `image_disk`, stop and tell the user to delete the custom image first.
3. If `Usage` is `disk` or `image_disk`, `Force=true` is required; warn that the disk created from the snapshot can no longer be reinitialized.
4. For bulk deletion, identify candidates based on age, retention settings, and dependencies, and estimate cost savings conceptually.
5. Deleting a `progressing` snapshot cancels the creation task.
6. Advise the user that after they perform the deletion through official channels, the inventory should be re-queried to confirm the snapshot no longer appears — the assistant may run this read-only verification on request.

If the user asks for the exact delete command or steps, use the **Official Documentation Fallback** response and point to the [Delete a snapshot](https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1) documentation.

### Rollback disks

> Per the Operation Execution Policy, executing `ResetDisk` / `ResetDisks` is outside the scope of this skill — regardless of authorization. Walk the user through the safety considerations for `ResetDisk` as follows (read-only checks may be run by the assistant; the rollback itself is performed by the user through official channels):

#### Single-disk rollback

Guide the user through the safety considerations for `ResetDisk` to roll back one disk to a historical snapshot. **This is irreversible.**

1. Check the disk attachment state first via `DescribeDisks`. If the disk is **unattached** (`Status` = `Available`, no `InstanceId`), the instance-stop precondition does not apply — proceed with the remaining checks directly. If the disk is attached, confirm the target instance is `Stopped`. If it uses post-paid billing and VPC, use normal shutdown mode rather than economical mode.
2. Verify the snapshot `SnapshotId` was created from the target `DiskId` via read-only checks (`DescribeSnapshots` / `DescribeDisks`).
3. Check encryption consistency between the disk and the snapshot.
4. Advise the user to create a new snapshot of the current disk state before rollback to preserve recent data.
5. Explain conceptually that, before the actual rollback, preconditions can be validated in dry-run mode through official Alibaba Cloud tools. Do NOT output a `DryRun` command or any executable rollback command — this is a destructive-operation workflow and is subject to the "no executable content" rule in the Operation Execution Policy.
6. Warn that rollback is irreversible and data written after the snapshot will be lost.
7. **Post-rollback verification guidance:** Advise the user that after their rollback completes, disk readiness is verified by polling `DescribeDisks` with the target `DiskId` until `Status` returns to `In_use` or `Available` — not by polling `DescribeSnapshots`, since snapshot status does not reflect disk readiness. The assistant may run this read-only verification on request.

#### Consistency-group rollback

Guide the user through the safety considerations for `ResetDisks` to roll back multiple disks from a snapshot consistency group (per the Operation Execution Policy: executing it is outside this skill's scope — guidance only):

1. Ensure the instance is `Stopped` in normal shutdown mode.
2. Verify no disk in the group has been released, detached, or has a snapshot in `progressing` state.
3. Advise creating a new consistency group or individual snapshots as a pre-rollback backup.
4. Let the user select the disks to roll back and decide whether to start the instance after rollback.

If the user asks for the exact rollback command or steps, use the **Official Documentation Fallback** response and point to the [Roll back a disk by using a snapshot](https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot) or [Roll back disks by using a snapshot-consistent group](https://help.aliyun.com/zh/ecs/user-guide/roll-back-disks-by-using-a-snapshot-consistent-group) documentation.

> **[MUST] Rollback refusal wording.** When declining to execute a rollback (single-disk or consistency-group), the final answer should satisfy all three conditions below:
> 1. **Explicit refusal.** State the refusal actively and unambiguously using wording such as "不会执行" or "不代为执行", in preference to vague hedges like "建议不执行" or "暂时不执行".
> 2. **Official channel redirect.** Point the user to the official documentation or console path for performing the rollback themselves, mentioning "官方文档" or "控制台".
> 3. **Risk explanation (at least two distinct risks).** Explain at least two concrete risks: (a) irreversible data loss — data written after the snapshot point will be permanently lost and this operation is "不可逆"; (b) the instance must be stopped ("停机" / `Stopped` state) before rollback. Additionally, recommend creating a fresh "备份" (backup snapshot) of the current disk state before the user performs the rollback.
>
> **Example refusal template (verbatim pattern — Chinese or English):**
> - English: "I will not execute this rollback. Please consult the official Alibaba Cloud documentation at https://help.aliyun.com/ for step-by-step instructions. Rollback is an irreversible operation and may cause permanent data loss for any writes after the snapshot — create a fresh backup snapshot before proceeding."
> - Chinese (in double quotes only): "不会执行此回滚操作。请参阅阿里云官方文档自行操作。回滚是不可逆的，可能导致快照后写入的数据永久丢失，建议先创建备份快照。"
>
> The refusal should include: (a) an explicit refusal phrase ("不会执行" / "不代为执行" / "will not execute" / "cannot execute"), (b) an official channel pointer ("官方文档" / "控制台" / "help.aliyun.com" / "official documentation"), and (c) at least two risk keywords from: "不可逆", "丢失", "风险", "停机", "Stopped", "备份", "irreversible", "data loss", "backup".

### Manage auto-snapshot policies

1. Create a policy with `create-auto-snapshot-policy` (the assistant may execute this):
   - `AutoSnapshotPolicyName`: Policy name (string). Example: `weekly-backup`. Pass as: `--AutoSnapshotPolicyName weekly-backup` (PascalCase preferred over `--auto-snapshot-policy-name`).
   - `RegionId`: Target region (string). Example: `cn-hangzhou`. Pass as: `--RegionId cn-hangzhou`. **Pass explicitly, in preference to the CLI profile default.**
   - `RepeatWeekdays`: JSON array of integers `1` (Monday) through `7` (Sunday). Example: `[2,4,6]` for Tuesday, Thursday, Saturday. Pass as: `--RepeatWeekdays '[2,4,6]'` (PascalCase preferred over `--repeat-weekdays`).
   - `TimePoints`: JSON array of integers `0` through `23` representing the hour in UTC+8. Example: `[2,14]` for 2:00 and 14:00. Pass as: `--TimePoints '[2,14]'` (PascalCase preferred over `--time-points`).
   - `RetentionDays`: `-1` for permanent, or `1` to `65535` days. Example: `--RetentionDays 7`. Optional if not specified; defaults to permanent.
2. Apply the policy to disks with `ApplyAutoSnapshotPolicy` (the assistant may execute this — pass `DiskIds` as a JSON array). Each disk can have up to 10 policies; new applications add to existing ones rather than replacing them.
   > **[MUST] Failure handling for ApplyAutoSnapshotPolicy:** If the call returns a `403` or `ParameterInvalid` error indicating the specified `DiskIds` are invalid or not found, immediately call `DescribeDisks` to verify the disk exists in the target region. If the disk does not exist (`TotalCount=0`), **stop execution**, report the failure to the user with the exact `DiskId` and `RegionId`, and request a valid disk ID before retrying — rather than proceeding or marking the task as completed. If the disk exists but the initial apply call failed transiently, retry the apply call once after confirming disk state. **Keep the same IDs on retry:** the policy ID used in the retry remains the one created/specified for this task, and a retry with different IDs happens only after the user explicitly provides them via `ask_user_question`. Asking the user is the right path here — scanning the account for an existing policy or disk and silently swapping it in would substitute the assistant's judgment for the user's.
3. Query policies with `DescribeAutoSnapshotPolicyEx` (read-only, the assistant may execute this).
4. To delete or unbind an unused policy (`DeleteAutoSnapshotPolicy` / `CancelAutoSnapshotPolicy`), executing the operation is outside the scope of this skill — regardless of authorization. Give the user a conceptual risk explanation and direct them to the official documentation.
5. Respect regional quotas: 100 policies per region per account.
6. **[MUST] Final answer format.** After creating and/or applying a policy, the final answer MUST restate verbatim: the created `AutoSnapshotPolicyId`, the policy name, the target region, the `DiskId`(s) the policy was applied to, and the apply result (成功/失败). Do not omit the policy ID.

**Schedule guidelines**: spread `TimePoints` across low-traffic hours; use `RepeatWeekdays` to match business-day or daily protection; set `RetentionDays` based on recovery-point objectives and compliance needs; avoid overlapping too many policies on the same disk.

For parameter validation, see [`scripts/auto_snapshot_policy_helper.py`](scripts/auto_snapshot_policy_helper.py) as a local reference tool. The assistant does not execute this script on the user's behalf.

### Snapshot preheating

Snapshot preheating accelerates the initialization of disks created from snapshots by pre-loading snapshot data. This is a **chargeable** operation.

- Preheating is typically used when creating a new disk from a snapshot and fast first-read performance is required.
- The cost depends on the preheated snapshot size and the preheating duration.
- Before preheating, confirm the target snapshot is in `accomplished` and `Available` state.
- **Billing reminder**: snapshot preheating incurs additional charges on top of snapshot storage. See [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb) for details.

### Snapshot replication / cross-region copy

Snapshot replication copies snapshots to another region for disaster recovery or migration. This is a **chargeable** operation.

- Cross-region replication consumes both source-region snapshot storage and target-region snapshot storage.
- Cross-region traffic charges may also apply.
- Before replication, confirm the source snapshot is in `accomplished` state and understand the target-region retention policy.
- **Billing reminder**: snapshot replication incurs storage charges in the target region plus potential cross-region traffic charges. See [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb) for details.

### Calculate and optimize snapshot costs

1. Estimate costs by classifying snapshots by `Category` (`standard` vs `archive`) and by disk, using snapshot list data and region-specific unit prices.
2. See [`references/cost-formulas.md`](references/cost-formulas.md) for formulas and pricing examples.
3. See [`scripts/snapshot_cost_calculator.py`](scripts/snapshot_cost_calculator.py) as a local reference tool for cost estimation. The assistant does not execute this script on the user's behalf.
4. Generate optimization recommendations conceptually:
   - Delete expired or redundant snapshots.
   - Archive low-frequency, long-retention snapshots (minimum 60 days; early deletion incurs a penalty).
   - Reduce `RetentionDays` for non-critical disks.
   - Disable unused cross-region copy.
   - Purchase OSS standard-LRS storage packages or SCU where appropriate.
5. **[MUST] Mandatory pricing disclaimer.** Every cost-estimation answer MUST end with the following disclaimer. **Copy the following single line verbatim into the final answer — do not rewrite, translate, re-punctuate, shorten, or alter ANY character:**

   注：以上价格为示例估算，非商业承诺。实际费用请以阿里云官网定价为准。

   **Self-check before sending (mandatory):** (1) locate the disclaimer line in your draft answer; (2) compare it character by character (including punctuation ： ， 。) against the source line above; (3) if any character differs, replace your version with the exact source text. Writing a different disclaimer of your own (e.g. "注: 以上费用基于 PayByTraffic 模式..." or "注: 以上成本为估算值，实际费用以阿里云账单为准") does NOT satisfy this requirement. Also refer users to the [Snapshot billing](https://help.aliyun.com/zh/ecs/snapshots-1?spm=a2c4g.11186623.help-menu-25365.d_2_0_1_4.45debec9mZ2rEb) documentation and the [Alibaba Cloud pricing page](https://www.aliyun.com/price/detail) for current rates. An estimation answer without this exact disclaimer is an incomplete answer.

---

## Observability

All Alibaba Cloud CLI (`aliyun ecs ...`) invocations issued by this skill MUST attach a unified User-Agent so that every request can be traced end to end across the UA and the API request log.

> **[MUST] Pre-call User-Agent self-check (applies to every request).** Every ECS API request issued through the `aliyun` CLI, an SDK, or **any wrapper/internal tool** MUST carry `AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{session-id}` — via the `--user-agent` flag for CLI calls, or an equivalent User-Agent header/parameter for non-CLI invocation paths. Before executing each call, verify the command/request actually contains the flag with the correct session-id; if it is missing, do NOT run the call — rebuild the command with the flag first. A workflow in which any API call lacks the User-Agent marker is non-compliant, even if the call itself succeeds.

### User-Agent template

Append the following flag to every `aliyun` command:

```bash
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ebs-disk-snapshot-management/{session-id}
```

- `AlibabaCloud-Agent-Skills` is the fixed product prefix.
- `alibabacloud-ebs-disk-snapshot-management` is this skill's name and MUST match the `name` field in the frontmatter.
- `{session-id}` is the per-session identifier defined below.

### Session-id generation rules

- Generate exactly one `session-id` at the start of each skill session and reuse the same value for all API calls within that session.
- **A skill session spans the entire conversation thread for a single user request, including all follow-up clarification rounds and parameter corrections.** Generate the `session-id` once at the very first step and keep the same value throughout — even if the user provides new parameters, replies to a clarifying question, or the workflow branches. If the agent loses context, recover the original `session-id` from the conversation history (e.g., from a previously issued `aliyun` command's `--user-agent` value) rather than generating a new one.
- Format: a 32-character lowercase hexadecimal string (for example, `a1b2c3d4e5f60789a1b2c3d4e5f60789`).
- Reuse the same `session-id` consistently across every invocation method used in the session — whether the request is issued via the Alibaba Cloud CLI, an SDK, or Terraform.
- Keep the `session-id` stable for the whole session, and use a fresh `session-id` for each new session rather than reusing one across sessions.
- When an operation fails, report the `session-id` alongside the `RequestId` so the failure can be correlated between the User-Agent and the Alibaba Cloud API request log.

---

## Handle errors and retries

> **[MUST] Environment Integrity.** When executing CLI commands:
> - Leave environment variables that control CLI behavior (e.g., `ALIBABA_CLOUD_CLI_MOCK`, `MOCK_MODE`, `CLI_PROFILE`, `ALIBABA_CLOUD_CREDENTIALS_FILE`) untouched — the runtime environment is pre-configured; altering it breaks observability and testing hooks.
> - Use only documented flags; add flags such as `--no-mock`, `--skip-verify`, or `--dry-run` only when explicitly requested by the user.
> - Issue CLI invocations directly, rather than wrapping them inside shell scripts, subshells, or `env -i` launchers that strip environment context.
> - Every `aliyun ecs <subcommand>` call is issued as a direct, single-line command with all parameters inline — no indirection, no piping through intermediate scripts.
> - If an API call returns an unexpected success when an error was anticipated, report the anomaly and re-check the command format rather than silently proceeding.

Map common errors to concrete actions:

> **[MUST] Report failures before continuing.** When any `aliyun` call returns a non-zero exit code or an error body, first execute the matching handling rule below and report the error code, `RequestId`, and affected resource IDs to the user before proceeding to the next workflow step or declaring the task successful. Surfacing every error keeps the user informed and the workflow trustworthy.

> **[MUST] Four-class error decision table — execute EXACTLY as written, no improvisation.** Before handling any failed call, extract two fields verbatim from the error output: `ErrorCode` and `RequestId`. Then match the `ErrorCode` string against the four classes below **in order** and execute the prescribed steps literally. Preserve the `RequestId` and echo it verbatim in the final answer for every failure — keep it complete and unaltered rather than paraphrasing, truncating, or omitting it.
>
> **Class 1 — Throttling (identification: `ErrorCode` contains `Throttling`, e.g. `Throttling.User`):**
> - Approach: retry with exponential backoff, up to 5 attempts — wait before each retry rather than retrying immediately, stay on the SAME command rather than switching to a different API, and give the retries a chance rather than giving up after the first hit.
> - Steps: retry the SAME command with exponential backoff — wait **1s** before retry 1, **2s** before retry 2, **4s** before retry 3, **8s** before retry 4, **16s** before retry 5 (max **5** retries total). Use `sleep 1` / `sleep 2` / `sleep 4` / `sleep 8` / `sleep 16` between attempts. If it still fails after 5 retries, stop, report `ErrorCode` + `RequestId` to the user, and ask whether to continue later. If a retry succeeds, continue the workflow normally.
>
> **Class 2 — Server-side internal error (identification: `ErrorCode` contains `InternalError`, `ServiceUnavailable`, or the HTTP status is 5xx):**
> - Approach: retry up to 3 times rather than treating the first hit as fatal, keep the `RequestId` rather than discarding it, and surface the failed step rather than silently skipping it.
> - Steps: retry the SAME command at most **3** times with a fixed interval of about **2 seconds** between attempts (`sleep 2`). Preserve the `RequestId` from the FIRST failure. If a retry succeeds, continue the workflow (e.g., keep polling to completion). If all 3 retries fail, stop, report `ErrorCode` + the preserved `RequestId`, and suggest opening an Alibaba Cloud ticket with that `RequestId`.
>
> **Class 3 — Parameter / client error (identification: `ErrorCode` contains `ParameterInvalid`, `InvalidParameter`, `InvalidDiskId.NotFound`, `InvalidSnapshotId.NotFound`, `InvalidInstanceId.NotFound`, or the HTTP status is 4xx and it is not a permission or throttling error):**
> - Approach: validate first rather than blindly re-running the same failed command, keep the user's resource ID rather than substituting a different one on the assistant's own initiative, and resolve the error before moving to later steps or declaring the task complete.
> - Steps: **first** call the matching read-only validation API (`DescribeDisks` for disk parameters, `DescribeInstances` for instance parameters, `DescribeSnapshots` for snapshot parameters) in the same region to verify the resource exists and the parameter format is correct. If validation confirms the resource exists and the parameters are correct, retry the original command **once**. If validation shows the resource does not exist (`TotalCount=0` or empty list), STOP execution, report the exact resource ID + `RegionId` + `ErrorCode` + `RequestId` to the user, and wait for the user to supply a valid ID — waiting for the user is the right path here, in preference to retrying or swapping in another resource.
>
> **Class 4 — Permission error (identification: `ErrorCode` contains `Forbidden` — e.g. `Forbidden.RAM` — or `NoPermission`, or the HTTP status is 403):**
> - Approach: permission failures are NOT transient, so hold off on re-running the same API (in identical form or with changed parameters, casing, pagination, or action-name variant) until the user confirms authorization is complete; use `aliyun configure list` rather than reading credential files to diagnose; when a query cannot complete, report that fact rather than presenting fabricated results or declaring success. This no-retry approach applies only to the API that returned the permission error — other, unrelated APIs that the workflow legitimately needs can proceed.
> - Steps: stop immediately on the first permission error. Report to the user, all in the final answer: (1) the exact error code string (e.g. `Forbidden.RAM`), (2) the complete `RequestId` copied verbatim from the error body, (3) the affected operation and resource IDs. Then provide RAM authorization guidance: state that the current credentials lack the required permission (e.g. `ecs:DescribeSnapshots`), recommend attaching the managed policy `AliyunECSReadOnlyAccess` or a custom policy containing `ecs:Describe*`, and direct the user or their administrator to complete authorization in the RAM console before retrying. Wait for the user's confirmation before retrying.

Additional per-error rules:

- `IncorrectDiskStatus` / `IncorrectInstanceStatus`: **[MUST]** immediately call `DescribeDisks`/`DescribeInstances` to fetch the current state, report it to the user, and then either wait for the blocking state to clear (e.g. an in-progress snapshot reaching `accomplished`) and retry, or ask the user how to proceed. Do NOT skip the step, do NOT fall through to later steps, and do NOT declare success while the error is unresolved.
- `SnapshotCreatedImage`: block deletion and list the image IDs that must be removed first.
- `SnapshotCreatedDisk`: require `Force=true` and explicit confirmation.
- **`CreateSnapshotGroup` failures — keep the consistency-group workflow rather than silently downgrading to a single-disk snapshot.** When the request is for a consistency group, keep the consistency-group workflow and diagnose the specific error rather than falling back to `CreateSnapshot`:
  - `InvalidInstanceId.NotFound` (or `404`): call `DescribeInstances` to confirm the instance exists and that its region matches the requested `RegionId`. Report the mismatch and ask the user to correct it.
  - `DiskCategory.OperationNotSupported` (or `400`): call `DescribeDisks` to confirm all target disks are ESSD series and located in the same availability zone. Report exactly which disks fail the condition.
  - On any validation failure, report the specific unmet condition to the user and request correction. **Keep `CreateSnapshotGroup` as the target action rather than silently replacing it with `CreateSnapshot`.** Only after `CreateSnapshotGroup` succeeds, poll `DescribeSnapshotGroups` until `Status=accomplished`.
- `QuotaExceed.Snapshot` / `QuotaExceed.AppliedAutoSnapshotPolicyQuota`: run cleanup planning or remove unused policies.
- `InvalidParameter.Mismatch` during rollback: verify encryption and source-disk consistency.
- `InvalidAccountStatus.NotEnoughBalance`: pause operations and advise account recharge.
- `InvalidDiskId.NotFound` / `ParameterInvalid` on `ApplyAutoSnapshotPolicy`: follow Class 3 above — verify disk existence via `DescribeDisks` in the specified region; if the disk is missing (`TotalCount=0`), halt execution and inform the user with the exact `DiskId` and `RegionId`, leaving the task unmarked until a valid ID arrives.
- `404 Not Found` on signed API POSTs while the endpoint host is reachable (a bare `curl` to the host returns 400/normal): this is usually a **recoverable local environment issue**, most commonly a **proxy interfering with the signed request** — not a skill, credential, or CLI-version bug. Before giving up, try these in order: (1) **Clear proxy variables and retry** by prefixing the command with `HTTPS_PROXY= HTTP_PROXY= ALL_PROXY= no_proxy="*"` — this resolves the majority of such 404s; (2) if it persists, verify DNS resolution and endpoint format (`ecs.<region>.aliyuncs.com` vs the global `ecs.aliyuncs.com`); (3) only after the above are ruled out, conclude the environment genuinely cannot reach the ECS OpenAPI, inform the user, and fall back to conceptual guidance. Do not blindly loop through many alternate endpoints, but do perform the proxy-clear retry — it is the single most common fix.
- Server-side 5xx errors: follow Class 2 above — retry up to 3 times with ~2s interval, preserve `RequestId`, and suggest opening an Alibaba Cloud ticket.

When an operation fails, always include the `RequestId` in the response so the user can provide it to Alibaba Cloud support.

For a comprehensive error-code handbook, see [`references/error-code-handbook.md`](references/error-code-handbook.md).

---

## Success Verification Method

After each operation, verify:

1. **Response status**: confirm a `RequestId` is present (indicates a successful API call).
2. **Create**: poll `DescribeSnapshots` / `DescribeSnapshotGroups` until `Status` is `accomplished` and `Available` is `true`.
3. **Delete**: re-query and confirm the snapshot no longer appears in the inventory.
4. **Rollback**: poll `DescribeDisks` (NOT `DescribeSnapshots`) with the target `DiskId` until the disk status returns to `In_use`/`Available`, and, if applicable, confirm the instance starts successfully.
5. **Auto policy**: query `DescribeAutoSnapshotPolicyEx` and confirm `Status` is `Normal` and `DiskNums` reflects the applied disks.
6. **No blocking warnings**: review any warnings and unmet preconditions before reporting success.

---

## Cleanup

- Snapshot creation, snapshot preheating, snapshot replication, and auto-snapshot policies may incur storage, preheating, cross-region traffic, or policy charges — remind the user to delete unneeded snapshots, disable unused cross-region copy, and remove unused policies to control cost.
- Read-only operations (list/inspect/cost) create no resources and require no cleanup.

---

## Best Practices

- Create snapshots during low-traffic windows to minimize I/O impact.
- Always set meaningful `SnapshotName`, `Description`, and tags for traceability.
- Use `RetentionDays` to avoid runaway storage costs.
- Poll until `Status` is `accomplished` before relying on a snapshot for rollback or image creation.
- Always create a pre-rollback backup snapshot before performing a rollback.
- Use dry-run validation to check rollback preconditions before the actual call.
- For detailed lifecycle recommendations, see [`references/best-practices.md`](references/best-practices.md).

---

## Reference Links

| Reference File | Description |
|----------------|-------------|
| [`references/api-reference.md`](references/api-reference.md) | API parameter tables and JSON examples. |
| [`references/error-code-handbook.md`](references/error-code-handbook.md) | Error scenarios and remediation. |
| [`references/cost-formulas.md`](references/cost-formulas.md) | Billing formulas and optimization tips. |
| [`references/best-practices.md`](references/best-practices.md) | Lifecycle management recommendations. |
| [`references/ram-policies.md`](references/ram-policies.md) | Least-privilege RAM policies. |
| [`references/workflow-decision-tree.md`](references/workflow-decision-tree.md) | Decision tree for choosing operations. |

### Scripts

The following scripts are provided as **local reference tools only**. They do not execute destructive operations, and the assistant does not run them on the user's behalf. They may be referenced when discussing non-destructive tasks such as cost estimation or parameter validation.

| Script | Description |
|--------|-------------|
| [`scripts/snapshot_cost_calculator.py`](scripts/snapshot_cost_calculator.py) | Cost estimation from a snapshot JSON list. |
| [`scripts/snapshot_cleanup_planner.py`](scripts/snapshot_cleanup_planner.py) | Generate a read-only cleanup plan without deleting anything. |
| [`scripts/snapshot_lifecycle_validator.py`](scripts/snapshot_lifecycle_validator.py) | Validate preconditions against a local JSON state file. |
| [`scripts/auto_snapshot_policy_helper.py`](scripts/auto_snapshot_policy_helper.py) | Validate policy parameters and generate sample values. |

---

## Common Issues and Solutions

**Issue**: "IncorrectInstanceStatus" when rolling back a disk.
- **Solution**: Stop the instance first; `ResetDisk`/`ResetDisks` require the instance to be `Stopped`.

**Issue**: "SnapshotCreatedDisk" when deleting a snapshot.
- **Solution**: A disk was created from this snapshot. Confirm with the user, then set `Force=true`. The created disk can no longer be reinitialized afterward.

**Issue**: "SnapshotCreatedImage" when deleting a snapshot.
- **Solution**: The snapshot backs a custom image. Delete the image first, then delete the snapshot.

**Issue**: Every API call returns `404 Not Found`, but the ECS endpoint host is reachable (bare `curl` returns 400).
- **Solution**: This is usually a **local proxy interfering with the signed request**, which is recoverable. First retry with proxy variables cleared: `HTTPS_PROXY= HTTP_PROXY= ALL_PROXY= no_proxy="*" aliyun ecs <Action> ...` — this fixes most cases. If it still fails, check DNS resolution and endpoint format. Only after proxy and DNS are ruled out should you conclude the environment cannot reach the ECS OpenAPI and fall back to conceptual guidance. Do not treat the first 404 as unrecoverable.

**Issue**: `CreateSnapshotGroup` fails.
- **Solution**: Confirm all disks are ESSD series, in the same availability zone, not multi-attach, and within the 16-disk group limit.

**Issue**: "QuotaExceed.Snapshot".
- **Solution**: Identify deletable snapshots conceptually, or request a quota increase.

**Issue**: Permission / "Forbidden" error.
- **Solution**: Follow the Permission Failure Handling process — read [`references/ram-policies.md`](references/ram-policies.md) and use the `ram-permission-diagnose` skill.
