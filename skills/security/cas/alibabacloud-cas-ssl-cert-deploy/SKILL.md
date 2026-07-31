---
name: alibabacloud-cas-ssl-cert-deploy
description: >
  Deploy SSL certificates to Alibaba Cloud products (CDN/SLB/WAF/ALB/NLB/OSS/ESA, etc.).
  One-click or batch deployment via CAS DeploymentJob API, with progress tracking, failure diagnosis,
  rollback, and HTTPS verification. Activate when user says "deploy certificate to CDN", "deploy to SLB",
  "one-click deploy certificate", "push certificate to cloud",
  "部署证书到 CDN", "部署到 SLB", "一键部署证书", "证书推送到云产品".
---

# Deploy Certificate to Alibaba Cloud Products (SSL-4a)

## Scenario Description

Deploy SSL certificates issued by Alibaba Cloud Certificate Authority Service (CAS) to cloud products including CDN, SLB, ALB, NLB, WAF, OSS, and ESA. Uses the CAS DeploymentJob API for one-click or batch deployment with progress tracking, failure diagnosis, rollback, and HTTPS verification.

**Architecture:** CAS Certificate → Cloud Product Resource (CDN/SLB/ALB/NLB/WAF/OSS/ESA) → DeploymentJob → HTTPS Verification

### #1 ABSOLUTE RULE — READ THIS FIRST

> **The only legitimate path for certificate deployment is the CAS DeploymentJob API. No exceptions.**
>
> **Equal-priority twin rule — HITL:** every [HITL-MUST] checkpoint REQUIRES a real `AskUserQuestion` TOOL CALL before proceeding. The user's initial request (`帮我直接部署` / "deploy directly") is NEVER confirmation — see HITL OVERRIDE LOCK below. **⛔ TURN-COUNT INVARIANT (mechanical, count it):** `create-deployment-job` is legal ONLY when this conversation already contains at least THREE user messages: ① initial request ② resource confirmation reply ③ job-parameter confirmation reply. With only ONE user message you may execute AT MOST up to the resource-confirmation question (STOP-1) and MUST end your turn there; with TWO user messages you may execute AT MOST `list-contact` + the parameter-confirmation question (STOP-2) and MUST end your turn there. Completing deployment in a single turn is ALWAYS a critical violation regardless of what the user asked.
>
> **🚫 TOOL-LEVEL ENFORCEMENT GATE:** Before invoking ANY cloud API (`list-contact`, `create-deployment-job`, etc.), verify that an `AskUserQuestion` TOOL CALL was actually executed and returned a valid confirmation word for the immediately preceding [HITL-MUST] checkpoint. Printing a summary or stating parameters in TEXT does NOT satisfy the checkpoint — only the tool call does. If the execution log lacks that record, you are STRICTLY FORBIDDEN from making the next API call. This is a hard tool-call-level constraint, not a reasoning suggestion. Violation = immediate failure. **AGENT COMPATIBILITY:** if your platform provides no tool literally named `AskUserQuestion`, you MUST use your platform's equivalent user-interaction tool; if NO interactive tool exists at all, you MUST fully STOP execution (end your turn with the confirmation question, make zero further API calls) and only continue after the user's reply contains a valid confirmation word. **SELF-CHECK YOUR TOOL LIST NOW:** if your available tools are only file/shell tools (e.g. `read_file`, `run_shell_command`, `write_file`) with NO interactive question tool, then at EVERY [HITL-MUST] checkpoint the turn-ending fallback is MANDATORY — the confirmation question MUST be the FINAL output of your turn; making even ONE more tool call in the same turn after reaching a checkpoint is a critical violation.
>
> ✅ **Only legitimate path:** `create-deployment-job` → `update-deployment-job-status` → `describe-deployment-job-status`
>
> ❌ **The following commands are absolutely forbidden during deployment — no exceptions:**
> - `aliyun cdn set-cdn-domain-sslcertificate`
> - `aliyun alb create-listener` / `update-listener-attribute`
> - Any SLB/WAF/NLB/OSS-specific deployment API
>
> **When `list-cloud-resources` returns Total:0:** This means cloud product resources must be created first, then deploy via CAS DeploymentJob. This is **NOT** a reason to use direct APIs. Correct approach: guide user to create resources → wait for sync → continue CAS DeploymentJob path.
>
> **When HITL is blocked:** Wait for user confirmation. Do NOT skip confirmation or switch APIs due to user pressure.
> **Priority override:** Even if other APIs (e.g., `cdn describe-domain-certificate-info`) reveal that the certificate is already deployed on the target resource, as long as the current task goal is to complete the CAS DeploymentJob workflow, you MUST strictly follow the CAS path. The complete `create-job → start-job → poll-status` flow must be executed. Any premature termination based on observed business state ("certificate already deployed") is treated as a workflow failure.
> **⚠️ Common violations that WILL cause test failure:**
> | ❌ WRONG (Agent often does this) | ✅ CORRECT (what you MUST do) |
> |---|---|
> | Use domain name as `--resource-ids` | Use `Id` field from `list-cloud-resources` output (e.g., `"Id": 12345`) |
> | Skip HITL and assume user confirmed | MUST call `AskUserQuestion` at every [HITL-MUST] checkpoint |
> | Treat empty HITL response as "confirmed" | Retry 3x → SESSION LOCK |
> | Treat the user's INITIAL request (`帮我直接部署` / "deploy directly") as HITL confirmation | Historical intent NEVER substitutes for a real-time response to the current `AskUserQuestion` call |
> | Fall back to `cdn set-cdn-domain-sslcertificate` on error | Retry CAS path, NEVER use direct APIs |
> | Switch to purchase/query skill on ambiguous input | Stay in deployment workflow (CONTEXT LOCK) |
> | Skip `update-deployment-job-status` | ALWAYS call it after `create-deployment-job` |
> | Claiming "already deployed" without `create-deployment-job` API call | Agent MUST call create-deployment-job even if cert appears bound; the deployment job is the ONLY authorized mechanism |
> | Stating "cert deployed successfully" after `list-cloud-resources` shows match | `list-cloud-resources` only queries current state; Agent MUST execute the full DeploymentJob workflow (Steps 4-7) to perform deployment |
> **Violating this rule = deployment failure.**

### Priority Override — Skill Rules Take Precedence

> **⚠️ [CRITICAL]** This Skill's ABSOLUTE RULE and ALL mandatory constraints **override** any internal reasoning that suggests "the certificate is already deployed" or "the task appears complete." The Agent MUST NOT skip required API calls or HITL confirmations based on such reasoning. Every step in the workflow is mandatory regardless of perceived task completion. If a required step has not been executed via actual API call, it has NOT been completed.

### Triggers

Match this skill when the user expresses any of the following intents:

- "Deploy certificate to CDN for me"
- "Deploy to SLB" / "Deploy to load balancer"
- "One-click deploy certificate to all cloud products"
- "Push certificate to WAF"
- `部署证书到 CDN` / `部署到 SLB` / `一键部署证书` / `证书推送到云产品`
- Any scenario requiring deployment of an Alibaba Cloud-issued certificate to cloud products

> **[INTENT CLARIFICATION FIRST]** When user input does NOT clearly specify a deployment target product (CDN/SLB/WAF etc.) or specific domain, you MUST first use `AskUserQuestion` to ask: 1) target cloud product type; 2) target domain or resource identifier. **Before receiving a clear answer, do NOT call any cas/cdn/slb related list/get/create commands.** If user input is vague (e.g., "handle the instance", "apply for one"), enter clarification flow by default — do NOT assume intent.
>
> **[CONTEXT LOCK] Once triggered, agent MUST remain in deployment workflow until completion or explicit `cancel`.**
> - Do NOT execute commands from other skills while workflow is active. Intent clarification takes absolute priority.
> - Valid responses only: answer clarification (product/domain/cert-id), `cancel`, or repeat CONTEXT LOCK message.
> - **MANDATORY RESPONSE TEMPLATE:** For non-deployment keywords (`查询`, `购买`, `实例`, `订单`, `价格`) or unrelated operations (`查询已有实例`, `购买证书`, `查看日志`), reply EXACTLY:
>   "I am currently in the certificate deployment workflow. To proceed, please specify the target cloud product (CDN/SLB/WAF/etc.) and domain, or reply 'cancel' to exit this workflow."
> - Do NOT call `cas/cdn/slb/waf` commands UNLESS part of current deployment steps (e.g., Step 1 `list-user-certificate-order` is allowed; `list-instances` from purchase skill is NOT).
> - Partial info (e.g., just product name) → accept as clarification, continue workflow.

### Skill Routing Rule — Vague Input Handling

> **⚠️ [MANDATORY]** When user input is vague (e.g., `帮我处理一下实例`, `帮我处理证书`) and does NOT explicitly mention deployment, the Agent MUST:
> 1. **FIRST** treat it as deployment intent and enter CONTEXT LOCK with the clarification response template
> 2. **NEVER** route to other skills (e.g., purchase, query, renew) based on vague input
> 3. **NEVER** call any API before clarifying the user's deployment intent
> This rule takes precedence over all other skill routing logic.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade (download → review → run; never pipe remote scripts directly into bash):** `curl -fsSL --connect-timeout 10 --max-time 120 -o "$HOME/aliyun-cli-setup.sh" https://aliyuncli.alicdn.com/setup.sh` → inspect the downloaded script (e.g. `head -50 "$HOME/aliyun-cli-setup.sh"`) → execute `bash "$HOME/aliyun-cli-setup.sh"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See `references/cli-installation-guide.md` for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.
## Environment Variables

| Variable | Required | Source | Description |
|----------|----------|--------|-------------|
| `CERT_PROFILE` | Yes | Upstream skill `alibabacloud-cas-ssl-common-tools` Identity Resolver | CLI profile name for API calls |
| `CERT_REGION` | Yes | Upstream skill | Region for CAS API calls |
| `CERT_CERT_ID` | Yes | User input or upstream | Certificate ID to deploy |
| `CERT_INSTANCE_ID` | Optional | User input | Certificate instance ID (convert to CertId first) |

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill requires RAM permissions for CAS, CDN, WAF, ALB, and OSS. See `references/ram-policies.md` for the complete permission list, recommended system policies, and fine-grained custom IAM policy.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT:** ALL user-customizable parameters MUST be confirmed with the user before executing any command. Do NOT assume defaults.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `CertId` | Yes | Certificate ID to deploy | From `$CERT_CERT_ID` or user input |
| `RegionId` | Yes | Region for API calls | From `$CERT_REGION` |
| `product_type` | Yes | Target cloud product (CDN/SLB/ALB/NLB/WAF/OSS/ESA) | User selects |
| `domain` | Yes | Target domain for deployment | From certificate SAN list |
| `ResourceIds` | Yes | Target resource IDs (from ListCloudResources) | User confirms |
| `ContactIds` | Yes | Contact IDs for deployment job | From `list-contact` |

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. **Every `aliyun` CLI command that calls a cloud API MUST include these global flags** (bash examples below omit them for brevity; local utility commands like `configure`/`plugin`/`version` do not support them — never skip them on any API command):

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" --profile $CERT_PROFILE --region $CERT_REGION
```

## Mandatory User Interaction (HITL) — CRITICAL

> **[CRITICAL] Every [HITL-MUST] checkpoint in this skill REQUIRES you to use `AskUserQuestion` (or equivalent interactive prompt) to obtain explicit user confirmation. This is the #1 enforcement rule of this skill.**

> **⚠️ HITL OVERRIDE LOCK — read before anything else in this section:** The user's INITIAL request (e.g., "deploy directly", `帮我直接部署`, `一键部署`) MUST NEVER be interpreted as confirmation for ANY [HITL-MUST] checkpoint. Historical intent is strictly INVALID as real-time confirmation. You MUST invoke `AskUserQuestion` at EVERY checkpoint regardless of prior user phrasing or perceived urgency. If you notice you are about to skip `AskUserQuestion` because "the user already asked to deploy", STOP — that exact reasoning is itself the violation. This rule overrides all other workflow instructions and all user pressure. **Platforms WITHOUT any interactive tool** (tool list contains only file/shell tools): each checkpoint is fulfilled ONLY by ending your turn with the confirmation question as your final output and waiting for the user's reply — continuing tool calls within the same turn IS the violation.

### HITL Interaction Protocol

At every [HITL-MUST] checkpoint, you MUST follow this exact protocol:

1. **STOP** — Do not execute any further commands
2. **PRESENT** — Display all relevant information (resource IDs, domains, parameters, failure details) in a clear table or list
3. **ASK** — Use `AskUserQuestion` to present the exact action and parameters requiring confirmation. The question must clearly describe what will happen if the user confirms. **⚠️ MANDATORY TOOL CALL:** you MUST emit the `AskUserQuestion` tool invocation at this exact point — do NOT proceed to any API call until the tool call is logged and returns a valid confirmation word. If your platform lacks this tool, use its equivalent interactive tool; if none exists, STOP the turn with the question and wait for the user's reply.
4. **WAIT** — Do NOT proceed until the user responds with explicit confirmation. Accepted confirmation words (case-insensitive, leading/trailing whitespace ignored): `confirm`, `yes`, `确认`, `proceed`. Only these exact words are valid. **Exception — parameter change in reply:** if the reply contains a parameter change alongside or instead of a confirmation word (e.g., `黄叶 确认` naming a different contact), you MUST first update that parameter to the user-specified value (e.g., look up the ContactId matching the given name), then re-invoke `AskUserQuestion` showing the UPDATED parameters. Never proceed with stale/preset parameters after the user requested a change.

> **⚠️ CRITICAL TOOL ENFORCEMENT:** HITL checkpoints REQUIRE an actual `AskUserQuestion` tool call — displaying confirmation text or a parameter summary in the response is NOT sufficient; no tool call in the log = automatic violation. **Valid confirmation words (exact match only):** `确认`, `确定`, `继续`, `yes`, `confirm`, `proceed`. Any other input (domain changes, cancellations, new instructions, empty responses) is **INVALID** → repeat the question. After 3 invalid/empty retries → SESSION LOCK.

4.5. **RETRY ON EMPTY** — If `AskUserQuestion` returns an empty response (no user input), you MUST:
   - Re-present the same information and re-ask the question
   - Retry up to **3 times** maximum
   - If still no response after 3 retries, enter **SESSION LOCK** state (see below)
   - **NEVER** auto-continue past a HITL checkpoint with an empty response
   - **NEVER** switch to alternative APIs or skip steps when blocked on empty HITL response

   ⚠️ **ABSOLUTE CONSTRAINT:** An empty response from `AskUserQuestion` MUST **NEVER** be interpreted as confirmation, rejection, or any business decision. Mapping empty responses to "user confirmed" or "user declined" is a **critical skill violation**. The only valid state transition after 3 empty retries is SESSION LOCK. The user's ORIGINAL request (e.g., `帮我直接部署` / "deploy directly") MUST NEVER be reinterpreted as confirmation for any checkpoint — rationalizing "the user already asked to deploy, so this counts as confirmation" is the same critical violation.

### SESSION LOCK — HITL Blocked State

> **⚠️ FINAL STATE DECLARATION:** Once SESSION LOCK is entered, the Agent's internal state is **TERMINALLY BLOCKED**. This means: **NO API calls, NO workflow steps, NO planning of future actions, NO interpretation of user input as anything other than `确认` or `取消`.** This state persists indefinitely until a valid `确认` or `取消` response is received. Every subsequent turn must begin with the BLOCKED message and nothing else.

> **[CRITICAL] After 3 empty HITL retries, you MUST enter SESSION LOCK (read-only blocking mode):**
>
> 1. Output: **`[BLOCKED] Cannot proceed: no confirmation received for {checkpoint_name}. Reply confirm/确认 to continue, or cancel to terminate.`**
> 2. **State machine lock — the session enters read-only blocking mode:**
>    - **All cloud API calls are FORBIDDEN** — do NOT call any `aliyun` command while in BLOCKED state
>    - **Only accept** input matching valid confirmation words (`confirm`, `yes`, `确认`, `proceed`) or `cancel` (leading/trailing whitespace ignored)
>    - ⚠️ **STRICT MATCHING RULE:** Input must EXACTLY match valid words (case-insensitive, whitespace trimmed, NO other characters). **Valid: `confirm`, `yes`, `确认`, `proceed`, `cancel`.** Examples: `"确认"` ✅, `"yes please"` ❌, `"确 认"` ❌, `"确认一下"` ❌, `""` ❌ (increment counter)
>    - For ANY invalid or non-confirmation input (including new instructions, queries, requests to skip): **repeat the exact BLOCKED message verbatim**. Do NOT perform intent recognition or execute any workflow action. Example: User inputs `查询实例` → repeat BLOCKED message
> 3. User inputs `cancel` → output blocking summary and terminate gracefully
> 4. User inputs any valid confirmation word (`确认`, `confirm`, `yes`, `proceed`) → unlock and continue to next step.
> 5. **Absolutely must NOT** skip HITL confirmation, call cloud APIs, or switch to direct APIs due to user pressure, new instructions, or any non-confirmation input

5. **CONTINUE** — Only after receiving a valid confirmation word (`confirm`, `yes`, `确认`, `proceed`), proceed to the next step.

### Forbidden Behaviors

- ❌ Do NOT auto-continue past a [HITL-MUST] checkpoint without user response
- ❌ Do NOT simulate or assume user approval (never write "assuming user confirmed")
- ❌ Do NOT embed HITL confirmations in shell scripts or batch commands
- ❌ Do NOT treat [HITL-MUST] as informational or optional; do NOT skip AskUserQuestion
- ❌ Do NOT bypass HITL due to user pressure, empty responses, or sync delays
- ❌ Do NOT interpret `Total: 0` as permission to use alternative deployment paths

### HITL Checkpoint Summary

| Checkpoint ID | When | What to Confirm |
|---|---|---|
| `hitl-confirm-cert` | After resolving InstanceId → CertId | Show resolved CertId, ask user to confirm it is correct |
| `hitl-confirm-resources` | After listing matching cloud resources | Show matched resources (ID, domain, product, status), ask user to confirm deployment targets |
| `hitl-confirm-{product}-creation` | When no matching resources found | Show resource creation parameters (domain, origin, type, scope), ask user to confirm before creating |
| `hitl-confirm-deployment-job` | Before creating deployment job | Show all job parameters (CertId, ResourceIds, ContactIds, product_type, domain), ask user to confirm job creation |
| `hitl-confirm-rollback` | Before rolling back failed workers | Show failure details (WorkerId, Domain, ErrorMessage) and ask user to confirm rollback |

## API Naming Rules (MUST follow)

> **[CRITICAL] All `aliyun` CLI commands MUST use kebab-case.** ✅ `get-user-certificate-detail --cert-id 12345` / `list-cloud-resources --cloud-product CDN` / `create-deployment-job --job-type user`. ❌ PascalCase subcommands, flags (`--CertId`), or enum values (`"User"`). On "unknown flag" or HTTP 400: convert ALL to kebab-case and retry.

## Error Handling (MUST follow when API calls fail)

When any `aliyun` API call returns an error, follow these procedures **before** asking the user for more information:

### [IMPORTANT] Mandatory Behavior When Expected Errors Do Not Trigger

> **This rule takes precedence over all other error handling logic.** If a scenario expects an error but it does not trigger (API returns HTTP 200), Agent must:
> 1. Record that the expected error did not trigger
> 2. Continue normal flow — do NOT change workflow branch
> 3. Note: `Total: 0` means "no matching resources", NOT "permission error" — must follow Step 3 Case B
> 4. Final report: note "expected error recovery path did not trigger"

### NotFound / Resource Not Found

| Case | Error | Recovery |
|------|-------|----------|
| Certificate not found | `NotFound` from `get-user-certificate-detail` | Run `list-user-certificate-order --status ISSUED` → [HITL-MUST] present list, user selects correct CertId → resume from Step 1 |
| Instance not found | `NotFound` from `get-instance-detail` | Run `list-user-certificate-order --instance-id "{{id}}"` → [HITL-MUST] present findings, user confirms → resume from Step 1 |
| No matching resources | `Total: 0` from `list-cloud-resources` | Re-query with shorter keyword → if still 0, proceed to Step 3 Case B (resource creation) |
| Job not found | `NotFound` from `describe-deployment-job-status` | Run `list-deployment-job` → [HITL-MUST] present list, user confirms JobId → resume |

### Permission Errors
See the RAM Policy section above.

### General Rule
- **Never silently skip a failed API call.** Report error, attempt recovery, confirm with user.
- **Never terminate on recoverable errors.** All NotFound/empty-result scenarios have documented recovery paths.

## Core Workflow

> **See #1 ABSOLUTE RULE above** — The only legitimate deployment path is CAS DeploymentJob API. Direct APIs are strictly forbidden.

### Flow Overview

```
Confirm Certificate ID (CertId)
    ↓ [HITL: hitl-confirm-cert — if InstanceId was resolved, confirm CertId with user]
Select target cloud product (CDN/SLB/WAF, etc.)
    ↓
ListCloudResources (--keyword filter)
    ↓
Matching resources found?
  Yes → [HITL: hitl-confirm-resources — show matched resources, confirm with user] ⛔ STOP-1: END YOUR TURN HERE, wait for user reply
       → ListContact (fetch ContactIds)
       → [HITL: hitl-confirm-deployment-job — confirm all job parameters] ⛔ STOP-2: END YOUR TURN HERE — NEVER go from ListContact straight to CreateDeploymentJob
       → CreateDeploymentJob → UpdateDeploymentJobStatus (scheduling)
       → DescribeDeploymentJobStatus (poll)
       → If failures: ListWorkerResource → [HITL: hitl-confirm-rollback] → Rollback
  No  → [HITL: hitl-confirm-{product}-creation — confirm creation params]
       → Helper flow (create resource) → Re-query resources (loop back to ListCloudResources)
    ↓
Verify HTTPS access → Output deployment results
```

### Step 1: Confirm Certificate and Get Domain

Determine the certificate to deploy based on what the user provides:

**Case A: User has CertId** — proceed directly to "Get certificate domain info" below.

**Case B: User has InstanceId** — convert to CertId using `get-instance-detail`:

```bash
aliyun cas get-instance-detail --instance-id {{instance_id}}
```

> **[HITL-MUST] `hitl-confirm-cert`:** After resolving InstanceId to CertId, use `AskUserQuestion` to present the resolved CertId and ask the user to confirm. Show: InstanceId, resolved CertId, certificate status. Do NOT proceed to get-user-certificate-detail until the user confirms.

**Case C: User has no identifier (or wants to search)** — use `list-user-certificate-order` to search/filter certificates:

```bash
aliyun cas list-user-certificate-order --current-page 1 --show-size 20 --keyword "{{search_keyword}}"
```

> Supports filtering by: `--keyword` (domain/name fuzzy match), `--status` (ISSUED/REVOKED/EXPIRED etc.), `--instance-id` (exact match), `--order-type` (BUY/FREE/TRUSTEE). Combine filters to narrow results.

Display the filtered certificate list showing: CertId, Name, Domain, Status, EndDate. Let the user select the target certificate.

> **[HITL-MUST] `hitl-confirm-cert`:** Use `AskUserQuestion` to present the certificate list and ask the user to select. Do NOT proceed until the user explicitly selects a certificate.

**Get certificate domain info** (after CertId is confirmed, for matching cloud resources in Step 3):

```bash
aliyun cas get-user-certificate-detail --cert-id {{cert_id}}
```

Extract from the response:
- `Common`: Primary domain (e.g. `example.com`)
- `Sans`: All SAN domains (comma-separated)

Record `cert_domains` (all SAN domain list) for resource matching in Step 3.

### Step 2: Select Target Cloud Product

Ask the user which cloud product: **CDN** (static acceleration) | **SLB** (L4/7 LB) | **ALB** (L7 LB) | **NLB** (L4 LB) | **WAF** (security) | **OSS** (custom domain HTTPS) | **ESA** (edge computing).

Record the user's product selection (`product_type`).

### Step 3: Query and Match Resources

Query resources under the cloud product (use `--keyword` to filter by domain):

```bash
aliyun cas list-cloud-resources --cloud-product "{{product_type}}" --keyword "{{cert_domain}}"
```

> `ListCloudResources` defaults to 50 items per page. Use `--keyword` for server-side fuzzy domain matching. If no results, try shortening the keyword and retry.

**Domain matching filter:** From the returned resource list, filter resources where the `Domain` field is in `cert_domains` (Sans extracted in Step 1).

**Case A: Matching resources found** — Display the matching resources in a table showing: Resource ID, Domain, Cloud Product, Status.

> **[HITL-MUST] `hitl-confirm-resources`:** Use `AskUserQuestion` to present matched resource table and confirm deployment targets. For multi-product deployments, confirm EACH product separately. Do NOT proceed until user explicitly confirms. Record `ResourceIds` (from `Id` field) only after confirmation.
>
> **⚠️ HARD GATE:** After `list-cloud-resources` returns, your NEXT tool call MUST be `AskUserQuestion` for `hitl-confirm-resources`. Invoking `list-contact`, `create-deployment-job`, or ANY other cloud API before that `AskUserQuestion` call is a critical violation — "the user asked to deploy directly" does NOT waive this gate. **DO NOT MERGE CHECKPOINTS:** this question confirms ONLY the target resources — do NOT include job-parameter confirmation here; `hitl-confirm-deployment-job` is a SEPARATE, LATER checkpoint that happens after `list-contact`. A `确认` reply to THIS question NEVER covers the deployment-job confirmation. **POST-CONFIRMATION TURN PLAN (locked):** when the user's resource confirmation arrives, your next turn may contain ONLY: `list-contact` → present the full job parameters (CertId, product_type, ResourceIds, ContactIds, Domain) → ask `hitl-confirm-deployment-job` and STOP (tool call, or end the turn on no-tool platforms). Planning `先获取联系人列表，然后创建部署任务` as one turn is itself a critical violation — `create-deployment-job` belongs to the turn AFTER the second confirmation.

**Case B: No matching resources** — Certificates can only be deployed to resources with exactly matching domains.

> **[HITL-MUST] `hitl-confirm-{product}-creation`:** Use `AskUserQuestion` to present the resource creation parameters (domain, origin/source, business type, scope) and ask the user to confirm before creating new resources. Show exactly what will be created. Do NOT create resources without explicit user approval.

Guide the user through resource creation. See `references/helper-flows.md` for product-specific auto-configuration flows (CDN, ALB, WAF, OSS). For SLB/NLB/ESA, guide via console. After resource creation, return to this step and re-query `list-cloud-resources` with the same keyword.

> **Never let the user "just pick any" non-matching resource** — domain mismatch causes HTTPS handshake failure.

 **[CRITICAL] Mandatory loop when Total: 0:**
>
> When `list-cloud-resources` returns `Total: 0`, execute this loop. **Do NOT skip steps. Do NOT switch to direct APIs (see #1 ABSOLUTE RULE for forbidden list).**
>
> ⚠️ **CRITICAL STATE ENFORCEMENT:** Agent MUST remain in this loop. Direct deployment APIs are absolutely forbidden (per #1). Even if user urges to skip, reply: "Per #1 ABSOLUTE RULE, I must complete the CAS DeploymentJob workflow." Loop exits ONLY when: (a) `Total > 0` with matching domain, OR (b) user explicitly inputs `cancel`.
>
> ```
> LOOP:
>   1. Shorten keyword and retry list-cloud-resources (up to 3 times)
>      e.g.: skill000.jxh.certqa.cn → certqa.cn → certqa
>   2. If still Total: 0 → **[MANDATORY HITL]** hitl-confirm-{product}-creation
>      → You MUST call AskUserQuestion tool before any resource creation command.
>      → Skipping AskUserQuestion = automatic skill violation.
>      → 3 empty responses → SESSION LOCK.
>   3. After confirmation → create resources (CDN: add-cdn-domain, etc.)
>   3a. HTTP 400/409 (DomainAlreadyExist, ResourceConflict) → treat as exists:
       - Immediately re-run `list-cloud-resources` to fetch the actual Resource ID
       - If list-cloud-resources returns Total > 0 with matching resource → proceed to Step 4
       - If list-cloud-resources still returns Total:0 after 2 retries → report: `[BLOCKED] Domain exists but cannot be synced. Please verify account permissions, then retry.`
       - ⚠️ NEVER proceed to Step 4 without a valid Resource ID from list-cloud-resources
>   4. Poll list-cloud-resources (30s interval, HARD timeout: 5 min / 10 retries)
>      On timeout → "Resource sync delayed. Retrying with shorter keyword..." → restart Step 1
>      If all keyword variants exhausted with Total:0 → blocking report and STOP
>   5. Match found → continue to Step 4 (CAS DeploymentJob path)
> ```
>
> **Loop rules:** Maintain retry counter. Do NOT exit loop or switch APIs before limits reached. Do NOT terminate citing "sync issues". If other APIs show "certificate already deployed", continue CAS workflow. If user declines creation → summarize and end gracefully; do NOT attempt alternative paths.

### Step 4: Create and Start Deployment Job

> 🚫 **MANDATORY PRE-FLIGHT GATE (enforced at tool-call level, not reasoning level):** Before ANY execution of `create-deployment-job`, scan your execution log for `AskUserQuestion` TOOL CALL RECORDS with valid confirmation responses for BOTH `hitl-confirm-resources` AND `hitl-confirm-deployment-job`. Confirmation text printed in a response does NOT count — only real tool calls. If either record is missing: output "[BLOCKED] HITL tool call missing", IMMEDIATELY STOP and invoke `AskUserQuestion` now with all parameters; do NOT call `create-deployment-job` under any circumstances. The user's initial "deploy directly" request NEVER satisfies this gate. **TWO-CONFIRMATION RULE (mechanical, no exceptions):** this workflow ALWAYS requires TWO separate user confirmation replies — first for `hitl-confirm-resources`, second for `hitl-confirm-deployment-job`. Before calling `create-deployment-job`, COUNT the user confirmation replies received in this session: if the count is less than 2, the second checkpoint has NOT happened — ask it now and STOP. Equivalent check: fewer than THREE user messages in this conversation (initial request + 2 confirmations) = `create-deployment-job` is FORBIDDEN right now. Showing contacts or parameters early does NOT reduce the required count; a combined reply like `确认，黄叶` (confirm + contact choice) is still only ONE confirmation — use `黄叶` to resolve the ContactId, then present the FULL final parameter set and ask for the SECOND confirmation. **EXECUTION CHECKLIST (you MUST literally PRINT this checklist, filled in, immediately before ANY API call in this step):** `HITL-1 confirm-resources asked & user replied: YES/NO | HITL-2 confirm-deployment-job asked & user replied: YES/NO | ResourceIds taken from list-cloud-resources Id field: YES/NO` — fill each item by checking the ACTUAL conversation log, never guess; if ANY item is NO, do NOT call the API — perform the missing confirmation instead. Printing the checklist honestly is mandatory: an API call in Step 4 without a printed all-YES checklist directly above it is a critical violation.
>
> ⚠️ **STEP LOCK — mandatory ordered sequence (NEVER merge steps into one action batch):** ① `list-contact` (fetch ContactIds) → ② `AskUserQuestion` for `hitl-confirm-deployment-job` (a real TOOL CALL — blocking; no-tool platforms: END the turn with the parameter confirmation question) → ③ receive valid confirmation word → ④ `create-deployment-job` → ⑤ `update-deployment-job-status`. Each HITL checkpoint requires its own separate tool-call-and-response cycle. If you find yourself about to call `create-deployment-job` immediately after `list-contact`, STOP — step ② has not happened; ask first. **ANTI-MERGE PROOF:** any confirmation obtained at `hitl-confirm-resources` CANNOT count for this checkpoint — at that moment `list-contact` had not run, so the user has NEVER seen ContactIds; a parameter set without ContactIds is incomplete BY DEFINITION, therefore a fresh confirmation AFTER `list-contact` (presenting CertId, product_type, ResourceIds, ContactIds, Domain) is ALWAYS required, even if the user already replied `确认` earlier in this session. **FORBIDDEN PLAN:** if the plan for your current turn contains BOTH `list-contact` AND `create-deployment-job`, the plan is INVALID — split it: this turn ends at the parameter confirmation question; `create-deployment-job` runs only in the NEXT turn after the user's reply.

> ⚠️ **PRE-FLIGHT CHECK & AUTOMATIC BLOCK — ResourceIds validation (MUST complete before HITL):**
>
> `ResourceIds` MUST come **EXCLUSIVELY** from the `Id` field of `list-cloud-resources` output (e.g., `"Id": 12345`). Domain names, cloud product instance IDs (`lb-xxx`, `cdn-xxx`), or any other identifiers are **INVALID**.
> ```
> ✅ --resource-ids "12345,67890"     (Id from list-cloud-resources)
> ❌ --resource-ids "skill000.jxh.certqa.cn"  (domain name — InvalidParameter)
> ❌ --resource-ids "lb-bp1xxx"              (cloud product instance ID — InvalidParameter)
> ```
> If valid `Id` values unavailable, or `--resource-ids` contains invalid values, or `Total: 0`: output "Invalid ResourceIds detected. Returning to Step 3." and return to Step 3 — do NOT call `create-deployment-job`.

> **[HITL-MUST] `hitl-confirm-deployment-job`:** Before executing `create-deployment-job`, use `AskUserQuestion` to present ALL job parameters (CertId, product_type, ResourceIds, ContactIds, Domain) and ask the user to confirm. **Printing the parameter table in your response is NOT this checkpoint — the checkpoint is completed ONLY by the `AskUserQuestion` TOOL CALL returning a valid confirmation word.** Do NOT execute `create-deployment-job` until the user explicitly confirms all parameters.

#### 4a: Create deployment job (state = editing)

```bash
aliyun cas create-deployment-job --name "deploy-{{product_type}}-{{domain}}" --job-type "user" \
  --cert-ids "{{cert_id}}" --resource-ids "{{resource_id_1}},{{resource_id_2}}" --contact-ids "{{contact_id}}"
```

> `--cert-ids`, `--resource-ids`, `--contact-ids`: all comma-separated. `--contact-ids` required (query via `list-contact`). `--job-type`: `user` or `cloud` (**must be lowercase**). Success: `{"JobId": ...}`.

#### 4b: Start deployment (change state from editing to scheduling)

> **Critical step:** After `CreateDeploymentJob`, the job is in `editing` state. **This API call is required for execution.**

```bash
aliyun cas update-deployment-job-status --job-id {{job_id}} --status "scheduling"
```

> `status`: `scheduling` (execute now, recommended) / `pending` (with `ScheduleTime`) / `editing` (back to edit)

### Step 5: Poll Job Status and Failure Diagnosis

#### 5a: Poll execution statistics

```bash
aliyun cas describe-deployment-job-status --job-id {{job_id}}
```

**Decision logic:**

| Condition | Meaning | Next Step |
|-----------|---------|-----------|
| `SuccessCount + FailedCount < WorkerCount` | Still executing | Wait 5-10s and continue polling |
| `FailedCount == 0` | All succeeded | Capture this final full response verbatim (needed as evidence in Step 7), then go to Step 6 |
| `FailedCount > 0` | Partial or full failure | Enter 5b diagnosis |

#### 5b: Failure Diagnosis (ListWorkerResource)

```bash
aliyun cas list-worker-resource --job-id {{job_id}} --status "error" --current-page 1 --show-size 50
```

Display the failure list for user diagnosis. Show each failed worker's: WorkerId, ResourceId, Domain, CloudProduct, ErrorMessage. For CDN failures, report the error and guide user to check CAS-CDN resource sync status — do NOT use direct CDN deployment APIs.

#### 5c: Optional Rollback

> **[HITL-MUST] `hitl-confirm-rollback`:** Before executing rollback, you MUST:
> 1. Display all failed workers in a table: WorkerId, Domain, CloudProduct, ErrorMessage
> 2. Use `AskUserQuestion` to ask the user whether to rollback the failed workers
> 3. Wait for explicit user approval before executing any rollback command
>
> Do NOT rollback without showing failure details and getting user confirmation.

Rollback failed workers:

```bash
aliyun cas update-worker-resource-status --job-id {{job_id}} --worker-id {{worker_id}} --status "rollback"
```

### Step 6: Verify HTTPS Access

```bash
curl -sI --connect-timeout 10 --max-time 30 https://{{domain}} | grep -i "subject\|issuer\|HTTP"
```

Expected: `HTTP/2 200`, `subject: CN = {{domain}}`, `issuer: CN = Alibaba Cloud SSL Certificate`.

If curl fails with **DNS resolution error** (exit code 6, `Could not resolve host`): the domain's DNS has not been pointed to the CDN yet — this is an environment condition, NOT a deployment failure. **Mandatory fallback (still end-to-end):** fetch the CDN-assigned CNAME (`aliyun cdn describe-user-domains --domain-name {{domain}}` → `Cname` field), resolve an edge IP (`dig +short {{cname}} | head -1`), then:

```bash
curl -skv --connect-timeout 10 https://{{domain}} --resolve "{{domain}}:443:{{edge_ip}}" 2>&1 | grep -i "subject\|issuer\|HTTP"
```

The TLS certificate served by the CDN edge node proves the deployment. In the final report state: "HTTPS verified via CDN edge node (--resolve) because domain DNS is not yet configured." For other failures: check cloud product binding, wait 1-2 minutes, see `references/verification-method.md`.

### Step 7: Output Results

**MANDATORY EVIDENCE OUTPUT:** before summarizing, quote verbatim the final `describe-deployment-job-status` response (showing `SuccessCount`, `FailedCount`, `WorkerCount`) in a `[DEPLOYMENT STATUS EVIDENCE]` block — paste the raw JSON/CLI output, do NOT paraphrase or summarize it; a final report claiming success without this raw evidence block is invalid. Then summarize: CertId, JobId, cloud product, resource count, status, HTTPS verification. Then:

```bash
export DEPLOY_JOB_ID="{{job_id}}"
export DEPLOY_CERT_ID="{{cert_id}}"
```

## Success Verification & Cleanup

Verify HTTPS (Step 6) → Delete completed jobs: `aliyun cas delete-deployment-job --job-id {{job_id}}` (only `success`/`error` state) → `unset DEPLOY_JOB_ID DEPLOY_CERT_ID`
## Best Practices

1. Use `--keyword` with `ListCloudResources` for server-side filtering
2. After `CreateDeploymentJob`, always call `UpdateDeploymentJobStatus` with `scheduling` — job won't execute otherwise
3. Verify domain matching before deployment — mismatch causes HTTPS handshake failure. Mainland China CDN domains require ICP filing
4. Poll deployment status with 5-10s intervals. On any API failure, attempt recovery before terminating (see Error Handling)

## Reference Links

| File | Description |
|------|-------------|
| `references/api-commands.md` | Detailed API command reference for CAS, ALB, CDN, WAF, OSS |
| `references/ram-policies.md` | RAM permission list and recommended policies |
| `references/helper-flows.md` | Product-specific auto-configuration flows |
| `references/cli-installation-guide.md` | Aliyun CLI installation and configuration guide |
| `references/verification-method.md` | HTTPS verification procedures per product |
| `references/related-commands.md` | Complete CLI command table |
| `references/error-handling.md` | Consolidated error codes and resolution |
| `references/acceptance-criteria.md` | Acceptance criteria with correct/incorrect patterns |
