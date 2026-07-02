# OpenAPI Troubleshoot — CLI API Reference

Product: **OpenAPIExplorer** (`openapiexplorer`)
API version: **2024-11-30**

All commands share these global flags:

| Flag | Description |
|------|-------------|
| `--cli-query <jmespath>` | Filter output with JMESPath |
| `--cli-dry-run` | Print request without sending |
| `--region <regionId>` | Override region (default endpoint: `openapi-mcp.cn-hangzhou.aliyuncs.com`) |
| `--endpoint <url>` | Override endpoint |
| `-q, --quiet` | Suppress output |
| `--user-agent <value>` | **Required** — see [SKILL.md](../SKILL.md) Observability section |

---

## get-own-request-log

**API:** `GetOwnRequestLog`
**Description:** Query request log details for API calls made by the **current account**. Use this as the default troubleshooting entry point.

```bash
aliyun openapiexplorer get-own-request-log \
  --log-request-id <REQUEST_ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--log-request-id` | string | **Yes** | Request ID from API response. UUID format, **must be uppercase**. |

**Scope:** Only returns logs for API calls initiated by the authenticated account (including sub-accounts querying their own calls). Returns 404 if the Request ID belongs to another account (even the main account, when queried by a sub-account).

**Example — project key fields:**

```bash
aliyun openapiexplorer get-own-request-log \
  --log-request-id BE7C768F-946F-5B46-80D4-F22FCFAF67C0 \
  --cli-query 'logInfo.basicInfo.{product:product,api:api,errorCode:errorCode,errorMessage:errorMessage,httpStatusCode:httpStatusCode}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

---

## get-request-log

**API:** `GetRequestLog`
**Description:** Query request log details for Request IDs under the **same parent account**. Covers the main account and all sub-accounts within that organization. Requires `GetRequestLog` RAM permission.

```bash
aliyun openapiexplorer get-request-log \
  --log-request-id <REQUEST_ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--log-request-id` | string | **Yes** | Request ID from API response. UUID format, **must be uppercase**. |

**Scope:**

- **Can query:** Request IDs from the main account or any sub-account under the same parent account
- **Cannot query:** Request IDs from unrelated accounts (returns 404 `NotFound.RequestLog`)
- Logs may also return 404 if expired or the Request ID is invalid

**Response structure:** Identical to `get-own-request-log`. Key paths:

```
logInfo
├── authenticationInfo    # AK type, signature method (redact ak in output)
├── basicInfo             # api, product, errorCode, errorMessage, httpStatusCode, regionId, apiDoc
├── callerInfo            # callerAccountId, callerType, masterAccountId, callerIp
├── parameters[]          # { name, type, value }
└── responses             # { responseBody }
```

---

## get-error-code-solutions

**API:** `GetErrorCodeSolutions`
**Description:** Fetch curated diagnostic solutions for an error code. Same backend as troubleshoot-server `sdkAgentService.getErrorCodeSolutions`.

```bash
aliyun openapiexplorer get-error-code-solutions \
  --error-code <ERROR_CODE> \
  [--product <PRODUCT_CODE>] \
  [--error-message "<MESSAGE>"] \
  [--accept-language zh-CN|en-US] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--error-code` | string | **Yes** | Error code to look up (e.g. `Account.Arrearage`) |
| `--product` | string | Recommended | Product code from `logInfo.basicInfo.product` or OpenAPI portal URL |
| `--error-message` | string | Optional | Narrows solution matches; use with `--error-code` |
| `--accept-language` | string | Optional | `zh-CN` (default) or `en-US`. Returns empty if no translation exists. |

**Response:**

```json
{
  "requestId": "...",
  "solutions": [
    {
      "solutionId": "...",
      "errorCode": "Account.Arrearage",
      "errorMessage": "Your account has been in arrears.",
      "product": "Ecs",
      "productName": "Elastic Compute Service (ECS)",
      "content": "Your account balance is insufficient. Please top up before performing this operation.\n====\n\n..."
    }
  ]
}
```

An empty `solutions` array means no curated solution exists for that combination.

**Examples:**

```bash
# With product (recommended)
aliyun openapiexplorer get-error-code-solutions \
  --product Ecs \
  --error-code Account.Arrearage \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}

# With error message for better matching
aliyun openapiexplorer get-error-code-solutions \
  --product Ecs \
  --error-code InvalidParameter \
  --error-message "The specified InstanceId does not exist." \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}

# English solutions
aliyun openapiexplorer get-error-code-solutions \
  --product Ecs \
  --error-code Account.Arrearage \
  --accept-language en-US \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

---

## Common Error Codes

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| `NotFound.RequestLog` | 404 | Log not found, expired, or no permission | Check Request ID, try other command, verify RAM policy |
| `InvalidParameter` | 400 | Bad parameter (e.g. malformed Request ID) | Ensure uppercase UUID format |
| `Unauthorized` / `AccessDenied` | 403 | Missing RAM permission | See [ram-policies.md](ram-policies.md) |

When CLI returns a `Recommend` URL like `https://api.aliyun.com/troubleshoot?q=...&product=...`, include it in the diagnosis summary for the user.
