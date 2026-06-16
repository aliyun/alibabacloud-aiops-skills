# Acceptance Criteria — PAI ResourceGroup

## Product / action

- ✅ `aliyun paistudio list-resource-groups`
- ✅ `aliyun paistudio create-resource-group`
- ❌ `aliyun pai list-resource-groups` (wrong product prefix — plugin is `paistudio`)
- ❌ `aliyun paistudio ListResourceGroups` (PascalCase — CLI uses kebab-case)

## Required parameters

- ✅ Always pass `--region "${REGION_ID}"` (no implicit region inference).
- ✅ `create-resource-group` requires `--name` and `--resource-type`.
- ✅ `update-resource-group` / `delete-resource-group` require `--resource-group-id`.
- ❌ Omitting `--region` and relying on `aliyun configure get region` — the skill must pass `--region` explicitly.

## Enums

- ✅ `--resource-type ECS` or `--resource-type Lingjun`. These are the **only two supported** ResourceType values.
- ✅ `--biz-version 1.0` or `--biz-version 2.0` (ECS only).
- ❌ `--resource-type SelfManagedAckPro` / `SelfManagedAckLingjun` / `SelfManagedASI` — **ACS variants are OFFLINE and no longer supported.** Agent MUST refuse with a clear "ACS resource type is offline" message and offer `ECS` or `Lingjun` as the only valid alternatives.
- ❌ `--resource-type ACS` (alias for the offline variants — also rejected).
- ❌ `--resource-type GeneralComputing` (not a valid enum).
- ❌ `--resource-type lingjun` (case-sensitive; must be `Lingjun`).

## ECS Version and VPC Rules

- ✅ ECS v2.0 (`--biz-version 2.0`): created WITHOUT `--user-vpc` (VPC goes on the Quota instead).
- ✅ ECS v1.0 (`--biz-version 1.0` or omitted): VPC can be set via `--user-vpc` on the ResourceGroup.
- ❌ ECS v2.0 + `--user-vpc` (backend rejects: "configuring VPC in rg is forbidden in ECS version 2").

## VPC JSON

- ✅ `--user-vpc '{"VpcId":"vpc-xxx","SwitchId":"vsw-xxx","SecurityGroupId":"sg-xxx"}'` — single-quoted, valid JSON, PascalCase keys.
- ✅ **【ECS v1.0 VPC required-trio rule — none of the three is optional】** Whenever an ECS v1.0 ResourceGroup is being created or updated with `--user-vpc`, the JSON payload **MUST** contain **all three** of `VpcId`, `SwitchId`, `SecurityGroupId` together. Missing any one of them is a Branch 1 **Input Conflict** — the agent MUST NOT fabricate a default, MUST NOT call `vpc describe-vpcs` / `vpc describe-vswitches` / `ecs describe-security-groups` to "auto-resolve" the missing field, and MUST stop to ask the user to supply the complete trio.
- ❌ `--user-vpc '{"VpcId":"vpc-xxx"}'` — only `VpcId`, missing `SwitchId` + `SecurityGroupId`. Backend rejects; the agent MUST refuse pre-submission via Branch 1.
- ❌ `--user-vpc '{"VpcId":"vpc-xxx","SwitchId":"vsw-xxx"}'` — missing `SecurityGroupId`. Backend rejects; refuse via Branch 1.
- ❌ `--user-vpc '{"VpcId":"vpc-xxx","SecurityGroupId":"sg-xxx"}'` — missing `SwitchId`. Backend rejects; refuse via Branch 1.
- ❌ `--user-vpc '{"vpcId":"vpc-xxx"}'` (camelCase keys rejected).
- ❌ `--vpc-id vpc-xxx --switch-id vsw-xxx` (no such flat flags; must be JSON).
- ❌ Silently auto-filling a missing field by calling `aliyun vpc describe-vswitches --vpc-id <…>` and picking "the first one" — that is a silent rewrite of user intent (Branch 1 violation).

## Mutating operations (create / update / delete)

- ✅ For create: print resolved plan, then ask for `CONFIRM-CREATE <RESOURCE_GROUP_NAME>` and wait for user reply before executing `create-resource-group`.
- ✅ For update / delete: print resolved plan + `--cli-dry-run` output, then ask for `CONFIRM <RESOURCE_GROUP_NAME>` (or `CONFIRM <RESOURCE_GROUP_ID>`) and wait for user reply before executing.
- ❌ Running `create-resource-group` directly without waiting for `CONFIRM-CREATE` token from the user.
- ❌ Running `delete-resource-group` directly after the user says "yes" / "go" / "ok".
- ❌ Skipping the precondition check that the RG has zero MachineGroups before calling `delete-resource-group`.

## MachineGroup deletion / release — 🚫 forbidden by this skill

- ✅ When the user asks to delete or release a MachineGroup, refuse explicitly and redirect to the [PAI Console](https://pai.console.aliyun.com/) (Resource Pool → Machine Group → unsubscribe / release) or `aliyun bssopenapi` unsubscribe APIs.
- ✅ `list-resource-group-machine-groups` / `get-resource-group-machine-group` / `get-machine-group` remain allowed (read-only).
- ❌ Invoking `aliyun paistudio delete-resource-group-machine-group` under any circumstance — even with a `CONFIRM <MACHINE_GROUP_ID>` token.
- ❌ Invoking `aliyun paistudio delete-machine-group` under any circumstance.
- ❌ Falling back to MCP, SDK, curl, or Terraform to release a MachineGroup after the CLI is refused.

## ECS VPC change (v1.0 only)

- ✅ Two-step: `--unbind true` first, then a second call with `--user-vpc <new JSON>`.
- ✅ When providing `--user-vpc`, ALL three fields (`VpcId`, `SwitchId`, `SecurityGroupId`) MUST be present in the same JSON object — see **VPC JSON** above for the required-trio rule. The trio applies equally to **create** and **update**; partial trios are rejected by the backend AND by the agent's pre-submission Branch 1 check.
- ❌ Single-call `update-resource-group --user-vpc <new JSON>` to swap VPC in place — fails or silently misbehaves.
- ❌ Providing partial VPC (e.g. only `VpcId` without `SwitchId` and `SecurityGroupId`, or any two-of-three combination) — backend rejects, and the agent MUST also refuse pre-submission via Branch 1 rather than letting the backend error surface.
- ❌ Asking the user to supply only `VpcId` and silently calling `aliyun vpc describe-vswitches` to pick a default vSwitch — the trio must come from the user, not be auto-completed.
- ❌ Attempting VPC change on ECS v2.0 RG — VPC is on the Quota, not the RG.

## Tool selection

- ✅ All operations through `aliyun paistudio <action>`.
- ❌ Falling back to MCP `pai_list_resource_groups`, raw curl, Python SDK, or Terraform when the CLI exists.
