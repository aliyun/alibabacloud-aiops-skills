---
name: alibabacloud-ram-permission-diagnose
description: >
  Alibaba Cloud RAM permission diagnosis and repair assistant. When an agent encounters
  any permission-related error while operating Alibaba Cloud resources (403, NoPermission,
  Forbidden, AccessDenied, InvalidSecurityToken, etc.), or when the user describes an
  Alibaba Cloud RAM permission issue, use this skill immediately. Do not wait for the user
  to explicitly request it — proactively start the diagnostic process whenever a permission
  error appears. Also applies when: a developer encounters permission issues while writing
  Alibaba Cloud SDK code, the user asks how to configure minimum permissions for an operation,
  or the user wants to know which permissions the current identity is missing.
compatibility:
  tools:
    - Bash  # for executing aliyun CLI commands (aliyun RAM series commands)
---

# RAM Permission Diagnosis and Repair

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ram-permission-diagnose"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ram-permission-diagnose`

> **Execution constraint**: When executing `aliyun` CLI commands directly (not generating commands for the user to copy), always append `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ram-permission-diagnose`. Do not add this flag to commands shown to users in Path B output or Path C console guidance.

## Overview

When a RAM permission error is detected, run through these steps:

1. **Quick Analysis** — parse raw error fields (no tool calls), output a brief summary, ask the user to choose analysis depth
2. **Deep Analysis** — *(only if user selects path B)* decode if needed, run gap analysis, classify root cause
3. **Generate Recommendations** — least-privilege authorization plan
4. **Execute Repair** — present repair options and wait for user to choose

**Permission level (L0–L3)** is the agent's internal routing state, inferred implicitly from API call results during the flow. It determines diagnostic depth and available repair paths. Never declare or describe the level to the user. See `references/diagnose-flow.md` for level definitions.

---

## Step 1: Quick Analysis

Parse raw error fields without any tool calls, then let the user decide how deep to go.

### 1a. Extract from raw error

- `error_code`: e.g., `NoPermission`, `Forbidden`, `InvalidSecurityToken`
- `missing_action`: e.g., `ecs:StopInstance`
- `principal_type`: `SubUser` / `AssumedRoleUser` / `RootUser` (from `AuthPrincipalType`)
- `principal_display_name`: UserId or role:session (from `AuthPrincipalDisplayName`)
- `no_permission_type`: `ImplicitDeny` or `ExplicitDeny` (from `NoPermissionType`)
- `policy_type`: e.g., `AccountLevelIdentityBasedPolicy`, `AssumeRolePolicy` (from `PolicyType`)
- `encoded_message`: retain `EncodedDiagnosticMessage` if present, for use in Step 2 if needed

### 1b. Output brief summary

Based on the extracted fields, output a concise summary: who is affected, what action is missing, initial root cause inference.

### 1c. Present depth choice and wait for selection

Present the following and **wait for the user to select — do not proceed until a choice is made**:

- **A. Quick path** *(recommended when: ImplicitDeny + all key fields present + common service)* — skip Step 2, generate recommendations directly from raw fields and built-in knowledge
- **B. Deep path** *(recommended when: ExplicitDeny, missing fields, or unfamiliar service)* — run full Step 2 analysis for a more precise result.
  > Requires two optional permissions: `ram:DecodeDiagnosticMessage` (decode encoded errors) and system policy `AliyunRAMReadOnlyAccess` (gap analysis). Missing permissions limit specific capabilities but the flow continues.
- **Skip** — stop here; output manual troubleshooting links

Mark the recommended option clearly and briefly explain why.

**If user selects A**: proceed to Step 3. Note in the recommendation that it is based on quick analysis; the user can request deep analysis at any time.

**If user selects B**: proceed to Step 2.

**If user selects Skip**: output error summary, links to RAM documentation (`https://help.aliyun.com/document_detail/93733.html`) and RAM console (`https://ram.console.aliyun.com/policies`), and a note on how to restart diagnosis.

**Edge case — ExplicitDeny with path A forced**: if `NoPermissionType = ExplicitDeny` and the user still selects A, explain that the specific Deny policy cannot be identified without deep analysis, and provide a limited recommendation with explicit uncertainty noted.

---

## Step 2: Deep Analysis

*Entered only when the user selects path B in Step 1.*

First attempt classification using the raw fields from Step 1. `DecodeDiagnosticMessage` is a supplement — invoke it only when raw data is insufficient to classify with confidence.

**Decode when raw data alone cannot resolve the root cause**: e.g., `ExplicitDeny` is present (need `MatchedPolicies`), `AccessDeniedDetail` was absent, or `PolicyType` is missing. For cases where `NoPermissionType`, `AuthAction`, `AuthPrincipalType`, and `PolicyType` are all available and point to a clear root cause, skip decode and proceed directly.

Transcribe `EncodedDiagnosticMessage` from the raw error and call:

```bash
aliyun ram decode-diagnostic-message --encoded-diagnostic-message "<transcribed-value>"
```

If the call returns `EntityNotExist`, re-run the original failing command and save its output to a temp file (use the system temp dir; name the file after the command context, e.g. `/tmp/aliyun_ecs_stopinstance.txt`). Extract `EncodedDiagnosticMessage` from the file and retry the decode. If the field is not found in the file, mark as L0 and continue.

If `SubUser` identity needs UserName resolution before gap analysis, see `references/diagnose-flow.md` → Identity Resolution. If resolution fails, mark as L0 and continue.

Root cause categories:
- **MissingAction** — identity policy lacks the required Action (most common)
- **ExplicitDeny** — a Deny statement blocks access (may be identity policy or CP control policy)
- **TrustPolicy** — role trust policy does not allow the caller to assume the role
- **STSInsufficient** — STS temporary credential lacks permission; root cause is on the originating Role
- **TokenExpired** — STS token has expired
- **SLRMissing** — service-linked role has not been created
- **ResourcePolicy** — resource-side policy (e.g., OSS Bucket Policy) is restricting access

For gap analysis trigger rules and per-root-cause handling details, see `references/diagnose-flow.md`.

**Gap analysis** (when triggered): query current policies attached to the identity, then compare against the required Action. Use `ListPoliciesForUser` (SubUser), `ListPoliciesForRole` (AssumedRoleUser), or `ListControlPolicies` (RootUser). For Custom policies, fetch the policy document with `GetPolicyVersion`. System policies: use built-in knowledge, do not call `GetPolicyVersion`.

**When permissions are insufficient**: if `DecodeDiagnosticMessage` fails (L0) or policy queries fail (L1), inform the user of the limitation and provide ready-to-use permission request materials for a RAM admin — two independent options: ① decode permission (`ram:DecodeDiagnosticMessage`) as a custom policy; ② RAM read access via system policy `AliyunRAMReadOnlyAccess` (covers gap analysis). Either or both can be requested independently. Then continue to Step 3 without waiting.

---

## Step 3: Generate Recommendations

Before generating, check for caller skill permission hints (see `references/diagnose-flow.md` → Coverage Check).

Knowledge source priority:
1. **Built-in knowledge** — for popular services (ECS, OSS, RDS, FC, SLB, VPC, SLS, STS, etc.), use known Action semantics directly. Reference `references/hot-services-ram.md`.
2. **Caller skill hints** — if `ram-policies.md` was found, use as supplementary context
3. **Web search** — search `{product} RAM authorization site:help.aliyun.com`; prefer manually maintained docs with business examples over auto-generated Action tables
4. **System policy fallback** — recommend `AliyunXxxReadOnlyAccess` or `AliyunXxxFullAccess` with a note to tighten further

**Custom policy naming**: suggest a name based on service and task semantics (e.g., `ai-agent-ecs-permissions`), confirm once, reuse in the same session.

**System policy**: attach directly with a single command, no naming needed.

For the Trust Policy root cause path, recommendations differ — see `references/diagnose-flow.md` → Handling Each Root Cause.

After presenting the recommendation, add a brief note: the current plan is a starting point; the user can request further refinement at any time — for example, scoping down to specific resources, adding conditions, or using resource-level policies (such as OSS bucket policies) instead of identity-level grants.

---

## Step 4: Execute Repair

Before executing any write operation, present the change summary and all available paths to the user, then **wait for the user to select a path — do not proceed or output any commands until the user has chosen**:

- Target (user or role name)
- Change summary (policy name, action, undo method)
- Path options (always present all that are available for the current level — never skip any):
  - **A. Direct CLI execution** — agent runs commands now *(only at L2)*
  - **B. Output CLI commands** — user copies and runs in their own terminal *(all levels)*
  - **C. Console guidance** — step-by-step in RAM console *(all levels)*
  - **Skip** — do not execute

For pre-query requirements before write operations, and full CLI command examples, see `references/ram-cli-commands.md` and `references/diagnose-flow.md`.

**Path A**: agent executes via Bash. On success → L3 confirmed; report result and undo command. On NoPermission → switch to Path B automatically.

**Path B at L0/L1**: output incremental Statement JSON only, with a note that existing policies could not be read and the user must merge manually.

**Path B at L2**: offer two sub-options: ① incremental Statement only, ② complete merged policy JSON.

**Path C**: provide the RAM console entry (`https://ram.console.aliyun.com/policies`) and step-by-step instructions for completing the change in the console UI.

After repair, suggest the user retry the previously failed operation. Offer to retry on their behalf if requested.
