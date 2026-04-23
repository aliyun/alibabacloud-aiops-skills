---
name: alibabacloud-odps-quota-manage
description: |
  MaxCompute Quota Management Skill. Use for managing MaxCompute/ODPS quota resources including pay-as-you-go quota creation, query, and listing operations.
  Triggers: "MaxCompute quota", "ODPS quota", "create quota", "list quotas", "quota management", "CU management".
---

# MaxCompute Quota Management

Manage MaxCompute (ODPS) Quota resources using Alibaba Cloud CLI and SDK. This skill covers **pay-as-you-go quota creation**, quota query, and quota listing operations.

## Limitations and Notes

| Feature | CLI Support | SDK Support | Notes |
|---------|-------------|-------------|-------|
| Create Pay-as-you-go Quota | ✅ Yes | ✅ Yes | Fully supported |
| Create Subscription Quota | ❌ Not Supported | ❌ Not Supported | **Temporarily unavailable** |
| Query Quota (get-quota) | ✅ Yes | ✅ Yes | ⚠️ **Deprecated** - Use query-quota instead |
| Query Quota (query-quota) | ✅ Yes | ✅ Yes | Recommended replacement for get-quota |
| List Quotas | ✅ Yes | ✅ Yes | Fully supported (both payasyougo and subscription) |
| Delete Quota | ❌ No API | ❌ No API | **Not available via API** - Must use Console |
| Modify Quota | ❌ Not in scope | ❌ Not in scope | Not covered in this solution |

> **Important**: 
> - **Create Subscription Quota** is **temporarily NOT supported** in this skill. For subscription quota creation, please use the [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/).
> - **Delete Quota** operation is NOT available through CLI or SDK. You must use the [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/) to delete quotas.
> - **query-quota is preferred** - get-quota is deprecated but acceptable if it returns success
> - **⚠️ CRITICAL: When checking if quota exists, ALWAYS use list-quotas, NEVER use get-quota**
> - **🚨 MANDATORY: Before create-quota, MUST call list-quotas first - NEVER skip this step**

## Architecture

```
Alibaba Cloud Account → MaxCompute Service → Quota Resources (CU)
                                           ├── Pay-as-you-go Quota (后付费) ← **Creation Supported**
                                           └── Subscription Quota (预付费) ← Query/List only
```

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

> **Pre-check: Aliyun CLI plugin setup required**
> [MUST] Install the maxcompute plugin manually: `aliyun plugin install maxcompute`
> [MUST] Update the plugin to latest version: `aliyun plugin update maxcompute`

```bash
# Verify CLI version
aliyun version

# Install maxcompute plugin (confirm when prompted)
aliyun plugin install maxcompute

# Update maxcompute plugin to latest version
aliyun plugin update maxcompute
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-quota-manage`

At the **start** of the Core Workflow (before any CLI invocation):
**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-odps-quota-manage"
```
**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

## Environment Variables

This skill relies on the aliyun CLI default credential chain. No explicit credential configuration is needed.
- Run `aliyun configure` to set up credentials before first use
- Do NOT explicitly handle or pass credential values in commands

**Timeout Configuration:**
- `ALIBABA_CLOUD_CONNECT_TIMEOUT`: Connection timeout (default: 10s)
- `ALIBABA_CLOUD_READ_TIMEOUT`: Read timeout (default: 10s)
- These defaults are sufficient for quota operations; no explicit configuration required

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, quota nicknames, billing types, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

### Input Validation

| Parameter | Validation Rules |
|-----------|------------------|
| `RegionId` | Must be valid Alibaba Cloud region ID (e.g., cn-hangzhou, cn-shanghai) |
| `nickname` | Max 64 characters; alphanumeric, hyphens (-), underscores (_); URL-encode if contains Chinese characters |
| `chargeType` | Must be `payasyougo` (subscription not supported) |
| `commodityCode` | Must be `odps`, `odpsplus`, `odps_intl`, or `odpsplus_intl` |
| `billingType` | Must be `payasyougo`, `subscription`, or `ALL` |

**Security Note:** All user inputs are passed to aliyun CLI which handles parameter sanitization. Do NOT construct commands using string concatenation with raw user input.

| Parameter Name | Required/Optional | Description                                                  | Default Value |
|----------------|-------------------|--------------------------------------------------------------|---------------|
| `RegionId` | Required | Alibaba Cloud region (e.g., cn-hangzhou, cn-shanghai)        | - |
| `chargeType` | Required | Billing type: `payasyougo` only (subscription not supported) | - |
| `commodityCode` | Required | Product code (see table below)                               | - |
| `billingType` | Optional | Filter for listing: `subscription` or `payasyougo` or `ALL`  | `ALL` |
| `maxItem` | Optional | Max items per page for listing                               | `100` |

### Commodity Codes (for Pay-as-you-go)

| Site | Commodity Code |
|------|----------------|
| China (国内站) | `odps` |
| International (国际站) | `odps_intl` |

## Authentication

**Security: Never expose credentials**
- Don't print AK/SK values
- Don't ask user to type AK/SK in chat
- Don't use `aliyun configure set` with hardcoded values

**Check credentials:**
```bash
aliyun configure list
```

If no credentials, ask user to run `aliyun configure` first, then continue.

## Core Workflow

**🚨 STEP 0 - CONFIRM PARAMETERS WITH USER BEFORE ANY EXECUTION:**

Before running any CLI command, you MUST confirm all required parameters with the user:
- **For LIST:** Confirm `region` and `billing-type` (payasyougo / subscription / ALL)
- **For QUERY:** Confirm `region` and `nickname`
- **For CREATE:** Confirm `region`, `charge-type`, and `commodity-code`

Do NOT assume or use default values. Ask the user explicitly and wait for confirmation before proceeding.

**🚨 CRITICAL RULE FOR ALL OPERATIONS:**

| Operation | First Command | Then |
|-----------|---------------|------|
| **CREATE** quota | `list-quotas` | If empty → Create; If exists → Stop |
| **QUERY** quota | `query-quota` | Show results |
| **LIST** quotas | `list-quotas` | Show list |

**⚠️ CREATE without list-quotas first = ERROR**

---

**FORBIDDEN COMMANDS - NEVER USE:**
- ❌ `aliyun quotas` commands - WRONG SERVICE (Quota Center), use MaxCompute instead
- ❌ Any BssOpenApi commands for quota operations - use MaxCompute instead
- ❌ `get-quota` - DEPRECATED, use `query-quota` instead

**MUST USE (plugin mode, kebab-case):**
- ✅ `aliyun maxcompute list-quotas` - For listing/checking quotas
- ✅ `aliyun maxcompute query-quota` - For querying quota details
- ✅ `aliyun maxcompute create-quota` - For creating quota

**⚠️ IMPORTANT:** Use `aliyun maxcompute` commands (MaxCompute service), NOT `aliyun quotas` commands (Quota Center service).

**Command Rules:**
- ALL CLI commands use plugin mode (kebab-case): `create-quota`, `list-quotas`, `query-quota`
- Parameters also use kebab-case: `--charge-type`, `--commodity-code`, `--billing-type`

---

### CREATE Quota (CHECK FIRST - THEN CREATE):

**🚨 PREPAID/SUBSCRIPTION QUOTAS ARE FORBIDDEN:**
This skill ONLY supports **pay-as-you-go** quota creation.
- If user wants **prepaid/subscription** quota → Tell them to use [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/)
- Do NOT attempt to create prepaid quotas

**🚨 FOR CREATE: FIRST RUN LISTQUOTAS - NEVER SKIP THIS:**

**STEP 1 - MANDATORY: Call list-quotas FIRST**
```bash
aliyun maxcompute list-quotas --billing-type payasyougo --region <R>
```
**DO NOT proceed to Step 2 until you get list-quotas result**

**Use MaxCompute service (`aliyun maxcompute`), NOT Quota Center (`aliyun quotas`).**

**AFTER list-quotas result (STEP 2):**

| Result | Action |
|--------|--------|
| List shows quota | **DO NOT CREATE** - Inform user "Quota already exists" → **Done** |
| List is empty | Go to Step 3 (Create) |

**STEP 3 - ONLY IF LIST WAS EMPTY:**

**PRE-CREATE CHECKLIST - ALL MUST BE TRUE:**
- [ ] User wants **pay-as-you-go** (NOT prepaid/subscription)
- [ ] list-quotas was called and returned empty list
- [ ] No existing pay-as-you-go quota in the region
- [ ] User confirmed they want to create

```bash
aliyun maxcompute create-quota --charge-type payasyougo --commodity-code odps --region <R> --client-token <UNIQUE_TOKEN>
```

**For International Site:**
```bash
aliyun maxcompute create-quota --charge-type payasyougo --commodity-code odps_intl --region <R> --client-token <UNIQUE_TOKEN>
```

**CRITICAL:** 
- Use plugin mode (kebab-case): `create-quota`
- Use **MaxCompute** service, NOT BssOpenApi
- **client-token:** Generate a unique token (e.g., UUID) for idempotency on retries
- **commodityCode values:**
  - China site: `odps` or `odpsplus`
  - International site: `odps_intl` or `odpsplus_intl`
  - NEVER use `maxcompute` as commodityCode
  - Note: When `chargeType=payasyougo` is set, commodityCode validation is not strict

**⚠️ OUTPUT HANDLING:**
- Do NOT pipe command output to files (e.g., `| tee ...` or `> file.json`) — if the target directory does not exist, the command will return a non-zero exit code even when the API call succeeds.
- Let the CLI print output directly to stdout, then parse the result inline.
- **When saving output files** (e.g., `existing_quotas.json`, `actions_log.txt`), ALWAYS `mkdir -p <directory>` first before writing any file to ensure the target directory exists.

**FINALLY:**
- Parse result
- Show user
- **Done**

**⚠️ NEVER call create-quota before list-quotas. This causes errors.**

**Note:** If quota already exists, DO NOT create. Only create when list-quotas returns empty list.

### QUERY Quota (when user provides nickname):

**PRIORITY:** Use `query-quota` as the primary API for querying specific quota details by nickname.

**CHECKLIST:**
- [ ] User provided quota nickname
- [ ] Use `query-quota` (NOT `get-quota`)

**USE THIS COMMAND:**
```bash
aliyun maxcompute query-quota --nickname <N> --region <R>
```

**IMPORTANT:** If nickname contains Chinese characters, URL-encode it first before passing to the command.

**FORBIDDEN:** `get-quota` is deprecated - use `query-quota` instead.

- Parse JSON
- Extract: `nickName`, `name`, `id`, `status`
- Show all fields → **Done**

### LIST Quotas:

**⚠️ FOR LISTING QUOTAS: ONLY use MaxCompute list-quotas, NOT BssOpenApi**

**When checking for existing pay-as-you-go quotas (before creation):**
```bash
aliyun maxcompute list-quotas --billing-type payasyougo --region <R>
```
**MUST include `--billing-type payasyougo`** to filter at API level.

**When listing all quotas (user request):**
```bash
aliyun maxcompute list-quotas --billing-type ALL --region <R>
```

**billingType parameter:**
- Valid values: `payasyougo`, `subscription`, `ALL`
- If not set, defaults to `ALL`
- Use `payasyougo` when checking for existing pay-as-you-go quotas

- Parse JSON
- Extract `quotaInfoList` array
- Show list → **Done**

**Response field `odpsSpecCode` enum values:**

| odpsSpecCode | Description |
|--------------|-------------|
| `OdpsStandard` | ODPS Pay-as-you-go Resource |
| `OdpsSpot` | ODPS Spot/Off-peak Resource (Pay-as-you-go) |
| `OdpsDev` | Developer Resource Type |
| `OdpsPlusStandard` | Subscription Resource |
| `OdpsPlusHa` | High Availability Resource |
| `OdpsPlusElasticCU` | ODPS Non-reserved Elastic CU Subscription Resource |

---

## Quick Reference

See [references/related-apis.md](references/related-apis.md) for complete CLI command reference and response format details.

**Key Points:**
- Use `list-quotas --billing-type payasyougo` before creating
- Use `query-quota` (not `get-quota`) for querying
- Use `create-quota` (kebab-case plugin mode) for creating
- Always include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-quota-manage`

---

## Task Completion

**Output Files — MUST create before finishing:**
1. `mkdir -p outputs ran_scripts` — ensure directories exist first
2. Save quota query/list results to `outputs/existing_quotas.json`
3. Save a log of all actions performed to `ran_scripts/actions_log.txt`

> **IMPORTANT:** Always run `mkdir -p` for any target directory BEFORE writing files. Never assume directories already exist.

**Finish with:**
- Summary of what was done
- Key results (nickname, region, status)
- Confirm output files were written (`outputs/existing_quotas.json`, `ran_scripts/actions_log.txt`)
- "✅ Complete"

---

## Error Handling

| Error Code | What to Do |
|------------|------------|
| `QuotaAlreadyExists` | Quota exists → Query it and show details → Task complete |
| `QuotaNotFound` | Quota doesn't exist → Inform user |
| `InvalidParameter` | Wrong parameter format → Check with user |
| `Forbidden` | No permission → Direct to Console |
| `INTERNAL_ERROR` | Retry once or contact support |

---

## Cleanup

> **No Delete API** - Must use [Console](https://maxcompute.console.aliyun.com/) to delete quotas

## API Reference

See [references/related-apis.md](references/related-apis.md) for complete API reference, CLI commands, and response formats.

## Best Practices

1. **Always confirm region with user** before any operation
2. **For creation**: First list to check if quota exists (one per region limit)
3. **If quota exists**: Query it for user instead of trying to create
4. **Use query-quota** (NOT get-quota) for quota details
5. **For subscription quotas**: Direct user to Alibaba Cloud Console

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/related-apis.md](references/related-apis.md) | Complete CLI commands and API reference |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Testing acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |

## Related Documentation

- [MaxCompute Product](https://api.aliyun.com/product/MaxCompute)
- [create-quota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/CreateQuota)
- [get-quota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/GetQuota)
- [list-quotas API](https://api.aliyun.com/api/MaxCompute/2022-01-04/ListQuotas)
- [Java SDK Documentation](https://help.aliyun.com/zh/sdk/developer-reference/v2-java-sdk)
- [Credential Management](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-access-credentials)
