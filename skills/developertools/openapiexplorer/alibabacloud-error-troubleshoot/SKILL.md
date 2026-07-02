---
name: alibabacloud-error-troubleshoot
description: |
  Alibaba Cloud OpenAPI troubleshooting skill. Use this skill when the user needs to diagnose API call failures
  using Request ID, error codes, or error messages — via Aliyun CLI `openapiexplorer` plugin commands.
  Triggers: "RequestId 排查", "Request ID 诊断", "错误码解决方案", "API 调用失败", "get-request-log",
  "get-own-request-log", "get-error-code-solutions", "OpenAPI 故障排查", "API troubleshoot",
  "diagnose OpenAPI", "diagnose OpenAPI error codes", "diagnose OpenAPI error messages",
  "Diagnose OpenAPI API call failures using Request ID".
---

# Alibaba Cloud OpenAPI Troubleshoot

Guide users to diagnose Alibaba Cloud OpenAPI call failures using the **OpenAPI Explorer troubleshoot APIs** exposed as Aliyun CLI commands. These CLI commands call the same backend as the [OpenAPI Diagnostic Portal](https://api.aliyun.com/troubleshoot).

---

## Prerequisites

### Install Aliyun CLI

Run `aliyun version` to verify version **>= 3.4.0**. If not installed or outdated, follow [references/cli-installation-guide.md](references/cli-installation-guide.md).

### Install OpenAPI Explorer Plugin (MUST do this first)

This skill depends on the `aliyun-cli-openapiexplorer` plugin, which provides the three required CLI commands:
`openapiexplorer get-own-request-log`, `openapiexplorer get-request-log`, `openapiexplorer get-error-code-solutions`.

**Plugin name is `aliyun-cli-openapiexplorer` (NOT `openapiexplorer`).** The install command uses `--names`:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --names aliyun-cli-openapiexplorer
aliyun plugin update
```

Verify it is available before running any troubleshoot command:

```bash
aliyun plugin list | grep openapiexplorer
aliyun openapiexplorer get-own-request-log --help
```

**Command format rule (mandatory).** Every troubleshoot command in this skill MUST use the exact
kebab-case form under the `openapiexplorer` plugin:

- `aliyun openapiexplorer get-own-request-log ...`
- `aliyun openapiexplorer get-request-log ...`
- `aliyun openapiexplorer get-error-code-solutions ...`

**PascalCase subcommands are strictly forbidden.** Never invent or attempt any
`aliyun <product> <PascalCaseApi>` style call as a substitute. If a troubleshoot command returns
`not a valid api`, the `openapiexplorer` plugin is missing — re-run the install command above
instead of switching to ActionTrail, web search, or re-issuing the original failing API. These
three commands live **only** under the `openapiexplorer` plugin and have no equivalent in core
product subcommands.

### Check Alibaba Cloud Credentials

Run `aliyun configure list` to verify credentials are configured.
If no valid profile is shown, **STOP** and ask the user to run `aliyun configure` outside this session.

**Security rules:**

- **NEVER** read, echo, or print AK/SK values
- **NEVER** ask the user to paste AK/SK into the conversation
- **ONLY** use `aliyun configure list` to check credential status
- **Redact** sensitive fields in log output (`authenticationInfo.ak`, tokens, etc.) when presenting results

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID once for the entire session:

- **Format:** 32-character lowercase hex string (e.g. `a1b2c3d4e5f6789012345678901234ab`)
- **When:** Generate once at session start; reuse the same value for every cloud API call in this session
- **Placeholder:** Use it as `{session-id}` in all commands below

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

---

## Scenario Description

Use this skill when the user wants to:

- Look up **request log details** by **Request ID** (UUID from an API response or error)
- Understand **why an API call failed** (HTTP status, error code, caller identity, request parameters)
- Get **official diagnostic solutions** for a specific **error code**
- Troubleshoot **permission / RAM / throttling / parameter** issues on OpenAPI calls

---

## RAM Permission Requirements

| API | CLI Command | Purpose |
|-----|-------------|---------|
| GetOwnRequestLog | `get-own-request-log` | Query logs for API calls made by the **current account** |
| GetRequestLog | `get-request-log` | Query logs for Request IDs under the **same parent account** — main account and all its sub-accounts |
| GetErrorCodeSolutions | `get-error-code-solutions` | Fetch diagnostic solutions for an error code |

See [references/ram-policies.md](references/ram-policies.md) for minimum RAM policy JSON.

> **Permission failure handling:** If a call returns `Unauthorized` or `AccessDenied`, stop and surface [references/ram-policies.md](references/ram-policies.md). Do **not** retry with a different account without explicit user confirmation.

---

## Core Diagnostic Workflow

Follow this decision tree. Full details: [references/troubleshooting-workflow.md](references/troubleshooting-workflow.md).

```
User has Request ID?
├── YES → Step 1: Query request log
│         ├── Default: get-own-request-log (current account only)
│         └── Request ID from sibling sub-account or main account: get-request-log
│         ├── Step 1 returns NotFound.RequestLog (404)?
│         │     └── TERMINATE: do NOT call get-error-code-solutions with `NotFound.RequestLog`.
│         │        Report log-unavailable cause (expired / wrong scope / no permission),
│         │        ask user for a fresh Request ID or the original error code, end the run.
│         ├── Step 2: Extract errorCode, errorMessage, product from logInfo.basicInfo
│         └── Step 3: If errorCode present → get-error-code-solutions
│            → Step 4: Summarize root cause + solutions + next steps
└── NO, only error code/message
    └── Step 3 directly: get-error-code-solutions (provide product if known)
```

> ⛔ **Hard stop on log-NotFound:** `NotFound.RequestLog` is the troubleshoot-API's own status for "no log available", **not a business error code of the user's failed call**. Feeding it to `get-error-code-solutions` will return irrelevant or empty results and is **strictly forbidden**. Always end the workflow at the NotFound branch and surface a user-facing recovery message instead.

### Step 1: Query Request Log by Request ID

**Request ID format:** UUID, **uppercase** (e.g. `BE7C768F-946F-5B46-80D4-F22FCFAF67C0`).

**Choose the right command:**

| Command | Scope | When to use |
|---------|-------|-------------|
| `get-own-request-log` | Current account's own API calls only | **Default** — user troubleshooting their own failed API call |
| `get-request-log` | Same **parent account** only — main account + all sub-accounts under it | Sub-account querying main account or sibling sub-account Request IDs; **cannot** access unrelated accounts |

**Prefer `get-own-request-log` first** — this mirrors the [OpenAPI Diagnostic Portal](https://api.aliyun.com/troubleshoot) behavior (GetOwnRequestLog is tried before GetRequestLog).

```bash
# Default: current account
aliyun openapiexplorer get-own-request-log \
  --log-request-id <REQUEST_ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}

# Same parent account — main account or sibling sub-accounts
aliyun openapiexplorer get-request-log \
  --log-request-id <REQUEST_ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

**Extract key fields** from `logInfo` (use `--cli-query` to project):

```bash
aliyun openapiexplorer get-own-request-log \
  --log-request-id <REQUEST_ID> \
  --cli-query 'logInfo.basicInfo.{product:product,api:api,errorCode:errorCode,errorMessage:errorMessage,httpStatusCode:httpStatusCode,regionId:regionId,logRequestId:logRequestId}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

| Field path | Meaning |
|------------|---------|
| `logInfo.basicInfo.product` | Product code (needed for solution lookup) |
| `logInfo.basicInfo.api` | API action name |
| `logInfo.basicInfo.errorCode` | Error code from the failed call |
| `logInfo.basicInfo.errorMessage` | Error message |
| `logInfo.basicInfo.httpStatusCode` | HTTP status (200 with business error vs 4xx/5xx) |
| `logInfo.basicInfo.regionId` | Region |
| `logInfo.callerInfo` | Caller account, IP, caller type (main/sub/STS) |
| `logInfo.parameters` | Request parameters sent to the API |
| `logInfo.responses.responseBody` | Raw response body (may contain nested error details) |

### Step 2: Analyze the Log

Before fetching solutions, interpret the log:

0. **`NotFound.RequestLog` (HTTP 404 from the lookup itself)** — log is unavailable. **STOP HERE.** Do NOT proceed to Step 3. See "Hard stop on log-NotFound" above and "Troubleshooting CLI Errors → 6" below.
1. **HTTP 200 + empty errorCode** — call succeeded; user may be looking at the wrong Request ID or a downstream issue
2. **HTTP 4xx/5xx or non-empty errorCode** — proceed to Step 3
3. **Throttling** — check `basicInfo.throttlingResult` (e.g. `FC.PASS` vs throttle codes)
4. **RAM / permission errors** — look for `AccessDenied`, `NoPermission`, `Forbidden.RAM` in `errorCode` or response body; check `callerInfo.callerType` and whether STS role is involved
5. **Parameter errors** — cross-check `logInfo.parameters` against API documentation linked in `basicInfo.apiDoc`

### Step 3: Get Error Code Solutions

Maps to troubleshoot-server `sdkAgentService.getErrorCodeSolutions` → OpenAPI `GetErrorCodeSolutions`.

> ⛔ **Precondition — `errorCode` MUST come from `logInfo.basicInfo.errorCode` of a successfully retrieved log (or from the user's original error report).** Never pass the lookup's own meta-status codes (`NotFound.RequestLog`, `Unauthorized`, `AccessDenied` produced by the get-*-request-log call itself) as `--error-code`. If Step 1 returned NotFound, the workflow has already terminated — do not enter Step 3.

```bash
aliyun openapiexplorer get-error-code-solutions \
  --error-code <ERROR_CODE> \
  --product <PRODUCT_CODE> \
  --error-message "<ERROR_MESSAGE>" \
  --accept-language zh-CN \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```

| Parameter | Required | Notes |
|-----------|----------|-------|
| `--error-code` | **Yes** | From log `basicInfo.errorCode` or user's error report |
| `--product` | Recommended | From log `basicInfo.product`; narrows solution matches |
| `--error-message` | Optional | Improves match quality when multiple solutions exist for the same code |
| `--accept-language` | Optional | `zh-CN` (default) or `en-US`; empty if no English content |

**Product code sources:**

- `logInfo.basicInfo.product` from Step 1 (preferred)
- OpenAPI portal URL: `https://api.aliyun.com/product/<ProductCode>` → ProductCode is the segment after `/product/`

Present each solution's `title`/`content` clearly. An empty `solutions` array means no curated solution exists — fall back to log analysis and API documentation.

### Step 4: Present Diagnosis

Always include:

1. **What happened** — API, product, region, HTTP status, error code/message
2. **Who called** — caller account type and ID (redact AK)
3. **Root cause** — from log analysis + solutions
4. **Recommended actions** — from solution content + any parameter/RAM fixes identified
5. **CLI commands used** — full copy-paste-ready commands (redact secrets)

---

## Command Quick Reference

See [references/api-reference.md](references/api-reference.md) for full parameter lists and examples.

| CLI | API | Description |
|-----|-----|-------------|
| `aliyun openapiexplorer get-own-request-log` | GetOwnRequestLog | Current account's request log |
| `aliyun openapiexplorer get-request-log` | GetRequestLog | Request log under the same parent account |
| `aliyun openapiexplorer get-error-code-solutions` | GetErrorCodeSolutions | Error code diagnostic solutions |

---

## Global Rules

- **Always prefer `get-own-request-log`** unless the Request ID belongs to the main account or another sub-account under the same parent account
- **Request ID must be uppercase UUID** — normalize before calling
- **Always pass `--product`** to `get-error-code-solutions` when available from the log
- **Do not** guess product codes — derive from log or OpenAPI portal URL
- **Logs expire** — if `NotFound.RequestLog`, the log may have expired (typically retained ~3 days) or the caller lacks permission
- **Link to OpenAPI troubleshoot portal** when helpful: `https://api.aliyun.com/troubleshoot?q=<ErrorCode>&product=<Product>`

---

## Troubleshooting CLI Errors

Walk through in order when the user reports errors:

1. **CLI version** — `aliyun version` >= 3.4.0?
2. **Plugin installed** — `aliyun plugin list | grep openapiexplorer`?
3. **Credentials** — `aliyun configure list` shows valid profile?
4. **Request ID format** — uppercase UUID?
5. **Wrong command for scope** — 404 on `get-own-request-log` for main account or sibling sub-account Request ID? Retry with `get-request-log` (same parent account only). If still 404, the Request ID is from an unrelated account, expired, or invalid
6. **NotFound.RequestLog (404)** — log expired, wrong Request ID, or no permission. Message: *"The log related to this logRequestId does not exist, has expired, or you do not have permission to view it."*
   - **Hard rule:** TERMINATE the diagnostic workflow here. Do **NOT** call `get-error-code-solutions` with `--error-code NotFound.RequestLog` (or any of the lookup's own meta-status codes like `Unauthorized` / `AccessDenied` produced by the get-*-request-log call). They are status codes of the troubleshoot API itself, not of the user's failing call — solution lookup will return irrelevant or empty results.
   - **Standard recovery message to the user:** explain that the log is unavailable (expired ~3 days / Request ID is outside current account scope / lacks `GetRequestLog` permission), then ask for either (a) a fresh Request ID generated by a recent failing call from the current account, or (b) the original error code from the user's application logs — and end this turn.
7. **Unauthorized / AccessDenied** — see [references/ram-policies.md](references/ram-policies.md)
8. **Empty solutions** — no curated solution; analyze log fields and API docs instead

Full playbook: [references/troubleshooting-workflow.md](references/troubleshooting-workflow.md).

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI >= 3.4.0 install, plugin setup, credentials |
| [references/api-reference.md](references/api-reference.md) | Full CLI command reference for all three APIs |
| [references/troubleshooting-workflow.md](references/troubleshooting-workflow.md) | End-to-end diagnostic playbook with examples |
| [references/ram-policies.md](references/ram-policies.md) | Minimum RAM policies for troubleshoot APIs |
