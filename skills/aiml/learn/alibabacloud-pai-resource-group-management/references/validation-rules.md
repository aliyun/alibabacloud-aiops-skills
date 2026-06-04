# Pre-execution Validation Rules

Authoritative rules for input validation, plugin/channel checks, and forbidden-string compliance. Referenced by `SKILL.md` §5 and §6.

## 1. Plugin state strict validation

Before executing **any** `aliyun paistudio …` command, the agent MUST run:

```bash
aliyun plugin list | grep paistudio
```

- If the output shows `paistudio` plugin **not installed** (no matching line / `ENABLED=false` / command error), the agent MUST immediately terminate the workflow and prompt the user to run:

  ```bash
  aliyun plugin install --names aliyun-cli-paistudio
  ```

- **STRICTLY FORBIDDEN** to fall back on `resourcemanager` / `pai` / `aiworkspace` or any other product namespace as a substitute when `paistudio` is unavailable. These are **different products'** APIs — invoking them does not reach the PAI ResourceGroup backend and pollutes the RAM audit log = severe over-reach.
- **STRICTLY FORBIDDEN** for the agent to run `aliyun plugin install` itself (writes to user environment). The user must install and re-issue the request.
- If the plugin is installed but its version is too low to cover an action, treat it as "not installed" and prompt the user to run `aliyun plugin update --name aliyun-cli-paistudio`.

## 2. Pre-execution interception rules

After parsing user input and **before** any `aliyun paistudio …` CLI (including `--cli-dry-run`), the agent MUST cross-check the matrix below. Any row that hits triggers §5 Branch 1 → emit `⚠️ Input Conflict` block. **Never** pass-through to the backend and rely on backend errors.

| # | Trigger | Design rule | Branch |
|---|---|---|---|
| A | `--biz-version 2.0` **and** `--user-vpc` together (create), OR `update-resource-group --user-vpc` on an existing ECS v2.0 RG (`BizVersion=2.0` confirmed by pre-check) | ECS v2.0 RG forbids `UserVpc`; VPC must live on `Quota.QuotaConfig.UserVpc`. The Branch 1 `Conflicting input` block MUST explicitly list both `--biz-version 2.0` and `--user-vpc` fields, and the `Design rule violated` section MUST explain that VPC should be configured on the Quota rather than on the RG | Branch 1 (create) / Refuse + explain Quota path (update) |
| B | `--resource-type Lingjun` **and** `--user-vpc` together (create), OR `update-resource-group --user-vpc` / `--unbind` on an existing Lingjun RG (`ResourceType=Lingjun` confirmed by pre-check) | Lingjun VPC is managed at the Lingjun infrastructure layer; **no** VPC modification is possible via paistudio API | Branch 1 refusal (create) / Refuse in plain natural language + forbidden-string rule (update) |
| C | `--resource-type` is `SelfManagedAckPro` / `SelfManagedAckLingjun` / `SelfManagedASI` | All three ACS self-managed variants are OFFLINE | Branch 1 + explicit "ACS offline" message |
| D | `--user-vpc` JSON missing any of `VpcId` / `SwitchId` / `SecurityGroupId` (and RG is ECS v1.0) | ECS v1.0 VPC required-trio rule (§3 below) | Branch 1 |
| E1 | `update-resource-group` request and target RG **not found** in `list-resource-groups --resource-group-ids "<id>"` (or `get-resource-group` returns `NotFound`) | A read-only existence pre-check is **mandatory** before any update; cannot mutate a non-existent resource | Branch 2 (precondition not met) — **NO `update-resource-group` CLI is issued, including `--cli-dry-run`** |
| E2 | `delete-resource-group` request and target RG **not found** in `list-resource-groups --resource-group-ids "<id>"` (or `get-resource-group` returns `NotFound`) | A read-only existence pre-check is **mandatory** before any delete; cannot delete a non-existent resource | Branch 2 (precondition not met) — **NO `delete-resource-group` CLI is issued, including `--cli-dry-run`** |
| E3 | `delete-resource-group` request and target RG exists, but `list-resource-group-machine-groups --resource-group-id "<id>" --page-size 1` returns `TotalCount > 0` | All MGs must be released by user via PAI Console first; the agent cannot release MGs on the user's behalf | Branch 2 (precondition not met) — **NO `delete-resource-group` CLI is issued** |
| F | Any MachineGroup deletion / release request (with or without CONFIRM token) | MG deletion is OUT OF SCOPE — always refuse | Direct refusal, no branch block |

> 🔍 **Mandatory pre-check sequence for `update-resource-group`** — strictly in this order:
>
> 1. **Existence check** — `aliyun paistudio list-resource-groups --region "${REGION_ID}" --resource-group-ids "${RESOURCE_GROUP_ID}"` (or `get-resource-group --resource-group-id "${RESOURCE_GROUP_ID}"`). If the result is empty / `NotFound` → row E1 → Branch 2 → exit (run `aliyun configure ai-mode disable` and STOP).
> 2. **`📋 Resolved Plan` block** with the field diff and `Resolved command` (only the changed fields, per §6.4 *parameter minimization*).
> 3. **Verbatim CONFIRM prompt** with the placeholder substituted by the real RG name (preferred) / ID. **End the turn.**
> 4. **Wait for the user's NEXT-turn literal `CONFIRM <name|id>` token**, then issue exactly one `update-resource-group` CLI bound to that token.
>
> 🔍 **Mandatory pre-check sequence for `delete-resource-group`** — strictly in this order:
>
> 1. **Existence check** — same as above. If empty / `NotFound` → row E2 → Branch 2 → exit.
> 2. **MG-count check** — `aliyun paistudio list-resource-group-machine-groups --region "${REGION_ID}" --resource-group-id "${RESOURCE_GROUP_ID}" --page-size 1`. If `TotalCount > 0` → row E3 → Branch 2 → exit. The Branch 2 block MUST quote the verbatim `TotalCount=N` from the CLI response.
> 3. **`📋 Resolved Plan` block** + **verbatim CONFIRM prompt** + **end the turn**.
> 4. **Wait for the user's NEXT-turn literal `CONFIRM <name|id>` token**, then issue exactly one `delete-resource-group` CLI bound to that token.
>
> Skipping either pre-check (e.g., issuing `update-resource-group` straight off a user request without first verifying existence, or issuing `delete-resource-group` without verifying both existence and MG-count) is treated as a **P0 over-reach** equivalent to mutating without a CONFIRM token. Specifically: every mutating call requires a unique CONFIRM token from the previous user turn (R3), and a structured branch block header must exist before each mutating CLI call (R4).

**STRICTLY FORBIDDEN** to compress any A-D conflict into a verbal suggestion ("I noticed X conflicts with Y — would you like to change it to Z"); the only legitimate response is the §5 Branch 1 `⚠️ Input Conflict` text block with 3 concrete options. **STRICTLY FORBIDDEN** to "send the request through and see what the backend says" — backend rejection is recorded in RAM audit log as agent over-reach.

## 3. ECS v1.0 VPC required-trio rule

When configuring `--user-vpc` for an ECS v1.0 ResourceGroup (create or update), the JSON payload MUST contain all three: `VpcId`, `SwitchId`, `SecurityGroupId`. Any missing field is hard-rejected by the backend, and the agent MUST refuse via §5 Branch 1 — never submit an incomplete trio.

- Partial inputs (only `VpcId` / only `VpcId + SwitchId` / only `VpcId + SecurityGroupId` / only `SwitchId + SecurityGroupId`) are all `Input Conflict` (missing required field) → Branch 1 with 3 concrete completion options.
- **STRICTLY FORBIDDEN** for the agent to call `aliyun vpc describe-vswitches` / `aliyun ecs describe-security-groups` to "auto-complete" a missing field with "the default" or "the first one" — that is silent rewrite of user intent (Branch 1 prohibition). The user must provide the missing field explicitly in the next turn.

JSON field names MUST be PascalCase (`VpcId`, `SwitchId`, `SecurityGroupId`); camelCase variants (`vpcId`, `switchId`, `securityGroupId`) are rejected by the backend.

## 4. Lingjun VPC refusal — forbidden-string rule

When the user requests modification of a Lingjun ResourceGroup's VPC, the agent must first read-only probe to confirm `ResourceType=Lingjun`, then output an explicit refusal pointing to Lingjun infrastructure / account manager. The refusal text (including explanation, refusal block, output files, reference links) MUST NOT contain the following literal strings:

- `aliyun paistudio update-resource-group` (in any form: backtick code block, inline `<code>`, shell example, or sentences like "cannot be changed via the `aliyun paistudio update-resource-group` API")
- `--user-vpc` (in Lingjun refusal context)
- Any SDK / curl / kubectl / Terraform fallback fragment for Lingjun VPC modification

Even with `--cli-dry-run` preview, even as a counter-example, even when explaining "why it's not feasible" — **as long as these strings appear in executable command form in the response**, that implies the path is feasible = guides the user to try = unauthorized guidance. Correct approach: state in plain natural language "Lingjun VPC cannot be modified via paistudio API; please contact the Lingjun infrastructure team / your account manager" — show **no specific CLI commands**.

## 5. Permission failure handling

If any CLI call returns `Forbidden.RAM` / `NoPermission`, STOP immediately, print the failing `Action` and `Resource`, and direct the user to attach the missing RAM action for that specific CLI command (e.g., `pai:ListResourceGroups` for `list-resource-groups`, `pai:UpdateResourceGroup` for `update-resource-group`). Do NOT broaden the policy with wildcards (no `pai:*`); add only the failing action.
