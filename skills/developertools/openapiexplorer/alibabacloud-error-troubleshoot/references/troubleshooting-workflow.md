# OpenAPI Troubleshoot — Diagnostic Workflow

End-to-end playbook for diagnosing Alibaba Cloud OpenAPI failures using Aliyun CLI.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  User reports API failure                                       │
│  (Request ID and/or error code/message)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │  Has Request ID?        │
              └────────────┬────────────┘
                    yes    │    no
              ┌────────────▼────────────┐     ┌──────────────────────────┐
              │  get-own-request-log    │     │  get-error-code-solutions│
              │  (or get-request-log)   │     │  (need errorCode + product)│
              └────────────┬────────────┘     └────────────┬─────────────┘
                           │                               │
              ┌────────────▼────────────┐                  │
              │  Analyze logInfo        │                  │
              │  - basicInfo            │                  │
              │  - callerInfo           │                  │
              │  - parameters           │                  │
              │  - responses            │                  │
              └────────────┬────────────┘                  │
                           │                               │
              ┌────────────▼───────────────────────────────▼─┐
              │  get-error-code-solutions                  │
              │  (errorCode + product + errorMessage)      │
              └────────────┬─────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │  Present diagnosis      │
              │  + recommended actions  │
              └─────────────────────────┘
```

This mirrors troubleshoot-server behavior:

- `request_log_service.getRequestLogPermission` tries **GetOwnRequestLog** first, then **GetRequestLog**
- `sdkAgentService.getErrorCodeSolutions` calls **GetErrorCodeSolutions** with caching by `errorCode:product:language`

---

## Scenario A: User Has Request ID

### A1. Normalize Request ID

Request IDs are UUIDs and **must be uppercase**:

```
be7c768f-946f-5b46-80d4-f22fcfaf67c0  →  BE7C768F-946F-5B46-80D4-F22FCFAF67C0
```

### A2. Query Log (Own Account First)

```bash
aliyun openapiexplorer get-own-request-log \
  --log-request-id BE7C768F-946F-5B46-80D4-F22FCFAF67C0 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

**If 404 `NotFound.RequestLog`:**

| Situation | Next step |
|-----------|-----------|
| User is sub-account, Request ID from main account or sibling sub-account | Use `get-request-log` — same parent account scope |
| User is sub-account, Request ID from an unrelated account | Cannot access — returns 404; explain scope limitation |
| Request ID is old (> ~3 days) | Log may have expired; ask user for a recent Request ID |
| Request ID is wrong / typo | Verify from original API error response |

### A3. Analyze Log Fields

**Success path (HTTP 200, empty errorCode):**

- API call succeeded at gateway level
- If user still sees an error, check `responses.responseBody` for business-level errors
- Verify this is the correct Request ID

**Failure path (non-empty errorCode or HTTP != 200):**

Extract from `logInfo.basicInfo`:

| Field | Example | Use |
|-------|---------|-----|
| `product` | `Ecs` | Pass to `get-error-code-solutions --product` |
| `api` | `RunInstances` | Identify which API failed |
| `errorCode` | `InvalidInstanceId.NotFound` | Pass to solution lookup |
| `errorMessage` | `The specified InstanceId does not exist.` | Pass to solution lookup |
| `httpStatusCode` | `404` | Distinguish gateway vs business errors |
| `regionId` | `cn-hangzhou` | Context for region-specific issues |
| `throttlingResult` | `FC.PASS` | Check if throttled |

**Caller context** from `logInfo.callerInfo`:

| Field | Use |
|-------|-----|
| `callerType` | `sub` / `AssumedRoleUser` / main — affects RAM diagnosis |
| `callerAccountId` | Which account made the call |
| `masterAccountId` | Parent account for sub-accounts |
| `callerIp` | Source IP for security-group / whitelist checks |

**Request parameters** from `logInfo.parameters`:

- Cross-check against API documentation (`basicInfo.apiDoc.aliyunSite`)
- Common issues: wrong region, missing required param, invalid resource ID

### A4. Fetch Solutions

```bash
aliyun openapiexplorer get-error-code-solutions \
  --product Ecs \
  --error-code InvalidInstanceId.NotFound \
  --error-message "The specified InstanceId does not exist." \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

If `solutions` is empty, provide analysis from log fields and link to API docs.

### A5. Present Diagnosis Template

```markdown
## Diagnosis Summary

**API:** RunInstances (Ecs, cn-hangzhou)
**Request ID:** BE7C768F-946F-5B46-80D4-F22FCFAF67C0
**Status:** HTTP 404 — InvalidInstanceId.NotFound

**Root cause:** The InstanceId `i-xxx` in the request does not exist in region cn-hangzhou.

**Caller:** Sub-account 275736439980740661 (master: 1635505437615342)

**Recommended actions:**
1. Verify the instance ID exists: `aliyun ecs describe-instances --region-id cn-hangzhou --instance-ids '["i-xxx"]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}`
2. Check if the instance is in a different region
3. ...

**Official solution:** (from get-error-code-solutions)
> ...
```

---

## Scenario B: User Has Error Code Only (No Request ID)

### B1. Gather Context

Ask or infer:

- **Product code** — which cloud product? (Ecs, Rds, Oss, Dysmsapi, …)
- **Error message** — exact text from SDK/CLI/API response
- **When it happened** — recent vs historical

### B2. Query Solutions Directly

```bash
aliyun openapiexplorer get-error-code-solutions \
  --product <PRODUCT> \
  --error-code <ERROR_CODE> \
  --error-message "<ERROR_MESSAGE>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

### B3. If Solutions Empty

- Search OpenAPI troubleshoot portal: `https://api.aliyun.com/troubleshoot?q=<ErrorCode>&product=<Product>`
- Check if error code is product-specific (always pass `--product`)
- Ask user for Request ID to get full log context

---

## Scenario C: Permission / RAM Errors

When `errorCode` contains `AccessDenied`, `NoPermission`, `Forbidden.RAM`, or similar:

1. From log: identify `callerType` (sub-account vs STS role vs main)
2. Check which API action failed (`basicInfo.api`)
3. Verify RAM policy grants the action on the target resource
4. For STS: check trust policy and session policy
5. Fetch solutions:

```bash
aliyun openapiexplorer get-error-code-solutions \
  --product <PRODUCT> \
  --error-code NoPermission \
  --error-message "<exact message from log>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

---

## Scenario D: Throttling Errors

When `throttlingResult` is not `FC.PASS` or errorCode indicates throttling:

1. Note the API and product from log
2. Check call frequency and quota limits
3. Fetch solutions for throttling error codes (e.g. `Throttling`, `Throttling.User`)

---

## get-request-log vs get-own-request-log — Decision Guide

| Question | Answer → Command |
|----------|------------------|
| Did **I** (current account) make this API call? | `get-own-request-log` |
| Is the Request ID from the **main account or a sibling sub-account** under the same parent account? | `get-request-log` |
| Is the Request ID from an **unrelated account**? | Cannot access — neither command works (404) |
| Sub-account querying main account's Request ID? | `get-request-log` (same parent account) |
| Not sure? | Start with `get-own-request-log`; on 404, retry with `get-request-log` if the Request ID likely belongs to the same parent account |

---

## Log Retention & Caching

- Request logs are retained for a limited period (typically ~3 days). Older Request IDs return `NotFound.RequestLog`.
- troubleshoot-server caches log and solution results in Redis (~3 days). CLI calls hit the live API directly.

---

## Error Handling Checklist

When CLI commands fail, check in order:

1. `aliyun version` >= 3.4.0
2. Plugin installed: `aliyun plugin list | grep openapiexplorer`
3. Credentials valid: `aliyun sts get-caller-identity`
4. Request ID uppercase UUID
5. Correct command for account scope
6. RAM permissions: [ram-policies.md](ram-policies.md)
7. Log not expired
