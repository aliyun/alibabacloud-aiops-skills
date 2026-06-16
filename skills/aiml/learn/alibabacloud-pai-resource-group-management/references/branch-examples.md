# Branch Decision — Worked Examples

Concrete examples of the three-branch discipline from `SKILL.md` §5. Use these to calibrate which branch a request lands in and what the corresponding block must look like.

## Example 1 — ECS v2.0 + VPC requested  →  Branch 1 (Input Conflict)

**User request**: "Create ECS 2.0 ResourceGroup `test-rg-v2` in `cn-shanghai` and bind VPC `vpc-xxx` / `vsw-xxx` / `sg-xxx`."

### ✅ Correct (Branch 1)

```
⚠️ Input Conflict
Conflicting input  : `--biz-version 2.0` + `--user-vpc {VpcId:vpc-xxx, SwitchId:vsw-xxx, SecurityGroupId:sg-xxx}`
Design rule        : ECS v2.0 RG forbids `UserVpc`; VPC must live on `QuotaConfig.UserVpc` (see §5 VPC rules).
Options:
  1) Create the ECS v2.0 RG without VPC, then configure VPC on the Quota later via `pai-quota-management`.
  2) Switch to ECS v1.0 and bind the VPC directly to the RG.
  3) Provide a different combination.
Please choose 1 / 2 / 3, or re-supply the configuration.
```

### ❌ Wrong

- Silently dropping `--user-vpc` and submitting `create-resource-group --biz-version 2.0` (loses user intent).
- Emitting `🛑 Precondition Not Met` (this is a design conflict, not a state failure).
- Refusing without listing concrete options.
- Using `AskUserQuestion` / IDE multi-choice widget instead of the literal text block.

## Example 2 — ECS v1.0 VPC trio missing `SecurityGroupId`  →  Branch 1

**User request**: "create ECS 1.0 RG with `--user-vpc '{\"VpcId\":\"vpc-xxx\",\"SwitchId\":\"vsw-xxx\"}'`"

### ✅ Correct (Branch 1)

```
⚠️ Input Conflict
Conflicting input  : `--user-vpc` JSON missing `SecurityGroupId`.
Design rule        : ECS v1.0 VPC required-trio — `VpcId` / `SwitchId` / `SecurityGroupId`, all three are mandatory (§5).
Options:
  1) Supply the actual `SecurityGroupId` (please provide it and resubmit the complete trio).
  2) Drop VPC binding (remove the entire `--user-vpc` field).
  3) Switch to ECS v2.0 and let the Quota layer handle VPC (`pai-quota-management` takes over).
Please choose 1 / 2 / 3, or re-supply the configuration.
```

### ❌ Wrong

- Auto-completing `SecurityGroupId` via `aliyun ecs describe-security-groups` and silently submitting (silent rewrite of user intent).
- Submitting the partial JSON to the backend "to see what error returns" (let the user fail upstream of the API).

## Example 3 — Delete RG with attached MachineGroups  →  Branch 2 (Precondition Not Met)

**User request**: "Delete ResourceGroup rg-prod-1"

**Live state**: `list-resource-group-machine-groups --resource-group-id rg-prod-1` returns `TotalCount=3`.

### ✅ Correct (Branch 2)

```
🛑 Precondition Not Met
Intended action       : aliyun paistudio delete-resource-group --resource-group-id rg-prod-1
Skipped steps         :
  - Step A: print 📋 Resolved Plan — skipped (precondition failed below).
  - Step B: ask CONFIRM token — skipped.
  - Step C: invoke delete-resource-group — skipped.
Failed precondition   :
  - Check : list-resource-group-machine-groups --resource-group-id rg-prod-1 --page-size 1
  - Result: TotalCount=3 (expected 0)
  - CLI evidence: { "TotalCount": 3, "MachineGroups": [...] }
Why this matters      : delete-resource-group will fail at the backend if any MachineGroup is still attached.
Next steps for the user:
  1. In the PAI Console (Resource Pool → Machine Group), unsubscribe / release the remaining 3 MachineGroups.
  2. Re-run `list-resource-group-machine-groups` and confirm `TotalCount=0`.
  3. Re-issue the `delete-resource-group` request.
```

After printing → exit the turn. **No CONFIRM prompt.**

## Example 4 — Plain update of description  →  Branch 3 (Resolved Plan)

**User request**: "Change the description of RG `test-rg` (region `cn-shanghai`) to `prod cluster for team x`"

**Live state**: `get-resource-group` returns RG with current description `dev cluster`, ResourceType `ECS`, BizVersion `2.0`.

### ✅ Correct (Branch 3)

```
📋 Resolved Plan
Action                  : update-resource-group (description only)
Region                  : cn-shanghai
ResourceGroupId         : rg-abc123 (name: test-rg)
Field diff              : description: "dev cluster" → "prod cluster for team x"
Preconditions verified  :
  - RG exists (get-resource-group returned 200)
  - User did NOT supply --name → name field will not be sent (parameter-minimization principle)
  - User did NOT supply --user-vpc → VPC unchanged
Blast radius            : metadata-only change; no impact on attached MachineGroups, Quotas, or VPC.
Resolved command        : aliyun paistudio update-resource-group --region cn-shanghai --resource-group-id rg-abc123 --description "prod cluster for team x" --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"
```

Then ask verbatim:

```
Please explicitly confirm whether to execute the above update operation. Type "CONFIRM test-rg" (or the actual ResourceGroupId) to proceed; any other input cancels.
```

**End the turn.** Wait for the user's next message to contain literal `CONFIRM test-rg` or `CONFIRM rg-abc123` before issuing the CLI call. Anything else (including "yes" / "go" / `CONFIRM <RESOURCE_GROUP_NAME>` with brackets retained) cancels.

### ❌ Wrong

- Including `--name` in the resolved command even though the user only changed description (violates parameter-minimization principle).
- Saying "now I will print Resolved Plan" without the structured 7-field block.
- Asking for `CONFIRM <RESOURCE_GROUP_ID>` with brackets retained, or `CONFIRM ALL`.
- Issuing the `update-resource-group` CLI in the same turn as the verbatim prompt (must end turn first).
- Defaulting to the internal ID (`CONFIRM rg-abc123`) when the user referred to the RG by name (`test-rg`) — name-priority applies.
- Omitting the `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"` flag from the resolved command.

## Example 5 — Lingjun VPC change request  →  Refusal (no branch block, but follow §6.4 forbidden-string rule)

**User request**: "Please change the VPC of Lingjun ResourceGroup `lingj1xxx` in `cn-wulanchabu` to `vpc-newlj` / `vsw-newlj` / `sg-newlj`."

**Live state**: `get-resource-group` confirms `ResourceType=Lingjun`.

### ✅ Correct (refusal)

> The VPC of a Lingjun ResourceGroup is managed by the Lingjun infrastructure layer and **cannot** be changed via PAI paistudio public APIs. Please contact the Lingjun infrastructure team or your account manager to go through the infrastructure-side change procedure.
>
> I cannot perform this mutating call on your behalf, and I will not substitute it with any fallback channel such as SDK / curl / Terraform / kubectl.

Then exit the turn.

### ❌ Wrong (forbidden-string violation)

- *"It cannot be changed via the `aliyun paistudio update-resource-group` API"* — the command string appears verbatim.
- Showing a counter-example code block such as `aliyun paistudio update-resource-group --user-vpc '{...}'` (even with a `# do not run` comment).
- Writing "if you insist, you could try the SDK as a fallback" or attaching an SDK snippet.
