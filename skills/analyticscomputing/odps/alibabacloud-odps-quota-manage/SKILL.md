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
| Query Quota (GetQuota) | ✅ Yes | ✅ Yes | ⚠️ **Deprecated** - Use QueryQuota instead |
| Query Quota (QueryQuota) | ✅ Yes | ✅ Yes | Recommended replacement for GetQuota |
| List Quotas | ✅ Yes | ✅ Yes | Fully supported (both payasyougo and subscription) |
| Delete Quota | ❌ No API | ❌ No API | **Not available via API** - Must use Console |
| Modify Quota | ❌ Not in scope | ❌ Not in scope | Not covered in this solution |

> **Important**: 
> - **Create Subscription Quota** is **temporarily NOT supported** in this skill. For subscription quota creation, please use the [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/).
> - **Delete Quota** operation is NOT available through CLI or SDK. You must use the [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/) to delete quotas.
> - **QueryQuota is preferred** - GetQuota is deprecated but acceptable if it returns success
> - **⚠️ CRITICAL: When checking if quota exists, ALWAYS use ListQuotas API, NEVER use GetQuota**
> - **🚨 MANDATORY: Before CreateQuota, MUST call ListQuotas first - NEVER skip this step**

## Architecture

```
Alibaba Cloud Account → MaxCompute Service → Quota Resources (CU)
                                           ├── Pay-as-you-go Quota (后付费) ← **Creation Supported**
                                           └── Subscription Quota (预付费) ← Query/List only
```

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Verify CLI version
aliyun version

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | Yes | Alibaba Cloud Access Key ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | Yes | Alibaba Cloud Access Key Secret |

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

**🚨 CRITICAL RULE FOR ALL OPERATIONS:**

| Operation | First Command | Then |
|-----------|---------------|------|
| **CREATE** quota | `list-quotas` | If empty → Create; If exists → Stop |
| **QUERY** quota | `query-quota` | Show results |
| **LIST** quotas | `list-quotas` | Show list |

**⚠️ CREATE without ListQuotas first = ERROR**

---

**FORBIDDEN COMMANDS - NEVER USE:**
- ❌ `aliyun maxcompute create-quota` - WRONG CASE (kebab-case), use PascalCase `CreateQuota`
- ❌ `aliyun maxcompute GetQuota` - DEPRECATED, use `query-quota` instead
- ❌ `aliyun bssopenapi CreateInstance` - WRONG API (BssOpenApi), use MaxCompute CreateQuota instead
- ❌ `aliyun bssopenapi QueryAvailableInstances` - WRONG API for listing quotas, use MaxCompute ListQuotas instead
- ❌ `aliyun quotas` commands - WRONG SERVICE (Quota Center), use MaxCompute instead

**MUST USE INSTEAD:**
- ✅ `aliyun maxcompute list-quotas` - For listing/checking quotas (MaxCompute service, NOT BssOpenApi)
- ✅ `aliyun maxcompute query-quota` - For querying quota details (MaxCompute service)
- ✅ `aliyun maxcompute CreateQuota` - For creating quota (MaxCompute service)

**⚠️ IMPORTANT:** Use `aliyun maxcompute` commands (MaxCompute service), NOT `aliyun quotas` commands (Quota Center service).

**Command Case Rules:**
- API actions use PascalCase: `CreateQuota`
- CLI commands use kebab-case: `list-quotas`, `query-quota`

---

### CREATE Quota (CHECK FIRST - THEN CREATE):

**🚨 PREPAID/SUBSCRIPTION QUOTAS ARE FORBIDDEN:**
This skill ONLY supports **pay-as-you-go** quota creation.
- If user wants **prepaid/subscription** quota → Tell them to use [Alibaba Cloud Console](https://maxcompute.console.aliyun.com/)
- Do NOT attempt to create prepaid quotas

**🚨 FOR CREATE: FIRST RUN LISTQUOTAS - NEVER SKIP THIS:**

**STEP 1 - MANDATORY: Call ListQuotas FIRST**
```bash
aliyun maxcompute list-quotas --billing-type payasyougo --region <R>
```
**DO NOT proceed to Step 2 until you get ListQuotas result**

**Use MaxCompute service (`aliyun maxcompute`), NOT Quota Center (`aliyun quotas`).**

**AFTER ListQuotas result (STEP 2):**

| Result | Action |
|--------|--------|
| List shows quota | **DO NOT CREATE** - Inform user "Quota already exists" → **Done** |
| List is empty | Go to Step 3 (Create) |

**STEP 3 - ONLY IF LIST WAS EMPTY:**

**PRE-CREATE CHECKLIST - ALL MUST BE TRUE:**
- [ ] User wants **pay-as-you-go** (NOT prepaid/subscription)
- [ ] ListQuotas was called and returned empty list
- [ ] No existing pay-as-you-go quota in the region
- [ ] User confirmed they want to create

```bash
aliyun maxcompute CreateQuota --chargeType payasyougo --commodityCode odps --region <R> --ClientToken <UNIQUE_TOKEN>
```

**For International Site:**
```bash
aliyun maxcompute CreateQuota --chargeType payasyougo --commodityCode odps_intl --region <R> --ClientToken <UNIQUE_TOKEN>
```

**CRITICAL:** 
- Use `CreateQuota` (PascalCase), NOT `create-quota` (kebab-case)
- **FORBIDDEN:** `create-quota`, `create-quota-odps-paygo`, or any kebab-case variant
- Use **MaxCompute** CreateQuota, NOT **BssOpenApi** CreateInstance
- Do NOT use `aliyun bssopenapi CreateInstance`
- **ClientToken:** Generate a unique token (e.g., UUID) for idempotency on retries
- **commodityCode values:**
  - China site: `odps` or `odpsplus`
  - International site: `odps_intl` or `odpsplus_intl`
  - NEVER use `maxcompute` as commodityCode
  - Note: When `chargeType=payasyougo` is set, commodityCode validation is not strict

**FINALLY:**
- Parse result
- Show user
- **Done**

**⚠️ NEVER call CreateQuota before ListQuotas. This causes errors.**

**Note:** If quota already exists, DO NOT create. Only create when ListQuotas returns empty list.

### QUERY Quota (when user provides nickname):

**PRIORITY:** Use `query-quota` as the primary API for querying specific quota details by nickname.

**CHECKLIST:**
- [ ] User provided quota nickname
- [ ] Use `query-quota` (NOT `GetQuota`)

**USE THIS COMMAND:**
```bash
aliyun maxcompute query-quota --nickname <N> --region <R>
```

**IMPORTANT:** If nickname contains Chinese characters, URL-encode it first before passing to the command.

**FORBIDDEN:** `aliyun maxcompute GetQuota` - use `query-quota` instead.

- Parse JSON
- Extract: `nickName`, `name`, `id`, `status`
- Show all fields → **Done**

### LIST Quotas:

**⚠️ FOR LISTING QUOTAS: ONLY use MaxCompute ListQuotas, NOT BssOpenApi QueryAvailableInstances**

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

---

## Quick Reference

See [references/related-apis.md](references/related-apis.md) for complete CLI command reference and response format details.

**Key Points:**
- Use `list-quotas --billing-type payasyougo` before creating
- Use `query-quota` (not `get-quota`) for querying
- Use `CreateQuota` (PascalCase) for creating
- Always include `--user-agent AlibabaCloud-Agent-Skills`

---

## Task Completion

**Finish with:**
- Summary of what was done
- Key results (nickname, region, status)
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
- [CreateQuota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/CreateQuota)
- [GetQuota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/GetQuota)
- [ListQuotas API](https://api.aliyun.com/api/MaxCompute/2022-01-04/ListQuotas)
- [Java SDK Documentation](https://help.aliyun.com/zh/sdk/developer-reference/v2-java-sdk)
- [Credential Management](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-access-credentials)
