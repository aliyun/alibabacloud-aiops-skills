---
name: alibabacloud-devops
description: |
  Automate Alibaba Cloud Yunxiao DevOps tasks — create and run pipelines, manage code repositories
  and merge requests, track work items and sprints, create test cases, manage artifacts, and drive
  application release workflows across 8 Yunxiao products.
  Triggers: "Yunxiao", "DevOps", "pipeline", "code repository", "merge request", "work item", "sprint", "test case", "application delivery", "artifact repository", "Codeup", "Flow", "Projex", "AppStack", "Packages", "Testhub"
---

# Intelligent DevOps Execution via Yunxiao Tools

This skill translates natural-language DevOps requests into Alibaba Cloud Yunxiao API calls. It supports three invocation channels: Alibaba Cloud CLI (`aliyun devops`), MCP Server, and mcporter CLI. It covers 8 Yunxiao products (~388 CLI commands, ~165 MCP tools).

## 1. Overview

- **Core flow**: Intent classification → Ambiguity resolution → Product mapping → Reference reading → Tool execution → Result verification
- **Scope**: CI/CD, code management, project collaboration, sprints/work items, artifacts, testing, application delivery

For the full product and tool catalog (MCP tools and CLI commands by product), see [references/tool-catalog.md](references/tool-catalog.md).

---

## 2. Prerequisites

### 2.1 Alibaba Cloud CLI Environment Check

> The Alibaba Cloud CLI (`aliyun devops`) is one of three invocation channels alongside MCP Server and mcporter. Full configuration guide: [references/aliyun-cli-setup.md](references/aliyun-cli-setup.md).

**Check flow (execute in order)**:

**Step 1: CLI availability**
```bash
aliyun devops --help >/dev/null 2>&1 && echo "cli ready" || echo "cli not available"
```
- Not available → Skip CLI checks, proceed to 2.2 (use MCP Server or mcporter)
- Available → Continue to Step 2

**Step 2: Identify authentication configuration**

Cloud DevOps (Yunxiao) uses **Personal Access Token** for authentication, not AK/SK profiles. Two configuration methods are supported:

**Method A: Environment variables (recommended)**

| Environment variable | Description | Required (Central) | Required (Region) |
| --- | --- | --- | --- |
| `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` | Yunxiao Personal Access Token | Yes | Yes |
| `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL` | API base URL | No | Yes |
| `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` | Organization ID | Yes | No |

```bash
# Region site
export ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN=<your-personal-access-token>
export ALIBABA_CLOUD_YUNXIAO_API_BASE_URL=<your-api-base-url>

# Central site
export ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN=<your-personal-access-token>
export ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID=<your-organization-id>
```

**Method B: Command-line parameters**

| Parameter | Description | Required (Central) | Required (Region) |
| --- | --- | --- | --- |
| `--yunxiao-access-token` | Yunxiao Personal Access Token | Yes | Yes |
| `--api-base-url` | API base URL | No | Yes |
| `--organization-id` | Organization ID | Yes | No |

**Step 3: Confirm final invocation format**

All commands must include `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/{session-id}"` (see Section 7: Observability). Shown as `--user-agent <UA>` below for brevity:

- Central site (env vars): `aliyun devops <cmd> --user-agent <UA>`
- Central site (params): `aliyun devops <cmd> --yunxiao-access-token=<token> --organization-id=<ID> --user-agent <UA>`
- Region site (env vars): `aliyun devops <cmd> --user-agent <UA>`
- Region site (params): `aliyun devops <cmd> --yunxiao-access-token=<token> --api-base-url=<url> --user-agent <UA>`

> **Decision point**: If Steps 1–3 all pass, CLI channel is ready — skip to Section 3. If CLI is unavailable, proceed to 2.2–2.4.

### 2.2 Pre-check: Node.js/Docker Runtime

This skill invokes `alibabacloud-devops-mcp-server@0.3.38` via `npx` or `docker`. Verify:

```bash
node --version   # Node.js 18+ recommended
npx --version
```

> **Recommended: Pre-install dependencies** (avoid runtime downloads)
> ```bash
> npm install -g alibabacloud-devops-mcp-server@0.3.38 mcporter@0.11.1 --registry=https://registry.npmmirror.com
> ```

### 2.3 Pre-check: Yunxiao Personal Access Token

> **Security Rules:**
> - **NEVER** ask users to paste plaintext tokens in conversation or command line
> - **NEVER** read/print token values using `echo $YUNXIAO_ACCESS_TOKEN` or similar
> - **NEVER** output the token environment variable name literally — use "Yunxiao access token" instead
> - **ONLY** verify via existence check:
>
> ```bash
> [ -n "$YUNXIAO_ACCESS_TOKEN" ] && echo "token configured" || echo "token missing"
> ```
>
> **If not configured, STOP:**
> 1. Guide user to [Yunxiao Personal Access Token](https://help.aliyun.com/zh/yunxiao/developer-reference/obtain-personal-access-token)
> 2. Required scopes: Organization Management (R/W), Project Collaboration (R/W), Code Management (R/W), Pipeline (R/W), Packages (R/W), Application Delivery (R/W), Test Management (R/W)
> 3. Inject env var outside the session (shell profile / IDE MCP config), then retry

**CLI-specific security rules**:
- Do not embed plaintext access tokens in commands; prefer environment variables
- Never output the token environment variable value literally

### 2.4 MCP Server Setup

See [references/mcp-setup.md](references/mcp-setup.md) for three connection modes (Stdio / Docker / SSE). Recommended — Stdio:

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "npx",
      "args": ["-y", "alibabacloud-devops-mcp-server@0.3.38"],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<YOUR_TOKEN>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

---

## 3. Authorization Failure Handling

> **[MUST]** When any tool call returns an authentication/authorization error:
> 1. Consult [references/token-scopes.md](references/token-scopes.md) for the required token scope
> 2. Guide user to add the scope in Yunxiao console under "Personal Access Token"
> 3. Pause execution, wait for user confirmation before proceeding

Common error codes:

| Error | Action |
|-------|--------|
| 401 Authentication failed | Check if token is valid/expired; prompt re-generation |
| 403 Insufficient permissions | Check token scopes (see token-scopes.md and [references/ram-policies.md](references/ram-policies.md)) |
| 404 Resource not found | Use `search_*` / `list_*` to verify resource IDs |
| 400 Parameter error | Check field schema against MCP Schema |
| 500 Server error | Retry up to 3 times with backoff |

---

## 4. Parameter Confirmation

> **IMPORTANT** — Before executing any tool call, all user-defined parameters (organizationId, projectId, repositoryId, pipelineId, branch names, work item subject, sprint dates, app/env names, etc.) **must** be confirmed with the user. Never call based on defaults or guesses.

Common required parameters by product:

| Product | Universal required | Typical scenario parameters |
|---------|-------------------|---------------------------|
| All | `organizationId` | - |
| Codeup | `repositoryId` | `sourceBranch` / `targetBranch` / `filePath` |
| Flow | `pipelineId` | `branch` / `runId` / `jobId` |
| Projex | `projectId` | `workitemTypeId` / `sprintId` / `subject` |
| Testhub | `projectId` | `testcaseId` / `testPlanId` |
| AppStack | `appName` | `envName` / `changeOrderId` |

---

## 5. Core Execution Flow

```
User request → [Step 1] Intent classification → [Step 2] Ambiguity handling → [Step 3] Product mapping
             → [Step 4] Read product references → [Step 5] Execute tool calls → Return results
```

### Step 1: Intent Classification

**Core principle: Identify the core verb, not the noun.**

| Action | Typical verbs | Tool prefix |
|--------|--------------|-------------|
| Create | create, add, initialize, set up | `create_*` |
| Query | view, get, list, search, find | `get_*` / `list_*` / `search_*` |
| Update | update, modify, change, edit | `update_*` |
| Delete | delete, remove, clean up | `delete_*` (**requires confirmation**) |
| Trigger | run, execute, trigger, start, deploy | `create_pipeline_run` / `execute_*` |
| Configure | configure, set up, bind, associate | `update_*` / `create_*` |

Decision tree and examples: [references/intent-classification.md](references/intent-classification.md).

### Step 2: Ambiguity Handling

**Core principle: If the instruction is vague or involves multi-product keywords, never guess — ask.**

| Ambiguity type | Detection condition | Strategy |
|---------------|---------------------|----------|
| Product | Multi-product keywords present | Ask which product |
| Action | Action unclear | Ask for operation type |
| Object | Missing identifiers | Ask for resource name or ID |
| Parameter | Missing key parameters | Ask for missing values |
| Scope | Org/project not specified | Ask for org/project |

### Step 3: Product Mapping

Full mapping: [references/product-mapping.md](references/product-mapping.md).

| Keywords | Product | MCP toolset | CLI prefix |
|----------|---------|-------------|------------|
| Pipeline, build, deploy, CI/CD | Flow | pipeline-management | flow- |
| Code, repo, branch, commit, MR, review | Codeup | code-management | codeup- |
| Artifact, package, Maven, NPM, Docker image | Packages | packages-management | packages- |
| Requirement, work item, sprint, bug, task | Projex | project-management | projex- |
| Test case, test plan, test report | Testhub | test-management | test-hub- |
| Application, orchestration, change order, release | AppStack | application-delivery | app-stack- |
| Organization, member, department, role | - | organization-management | base- |
| Current user info | - | base | base- |

**Ambiguity decision points**:
- "CI/CD full flow" → Build-only → Flow; app lifecycle → AppStack; both → ask
- "Repository" → Code repo → Codeup; artifact repo → Packages; unclear → ask

### Step 4: Read Product References

After determining the target product, **must** consult the Yunxiao documentation index at [references/product-reference.md](references/product-reference.md).

### Step 5: Execute Tool Calls

**Three invocation channels (functionally equivalent)**:

| Method | Scenario | Prerequisites |
|--------|----------|---------------|
| Alibaba Cloud CLI (`aliyun devops`) | Shell environment available | `aliyun` installed with token configured |
| Platform-native MCP | IDE/platform with MCP Server | `use_mcp_tool` available |
| Terminal CLI (mcporter) | Pure terminal, no MCP Server | Node.js 18+ installed |

**Channel selection**: Choose based on availability — CLI configured → CLI; MCP integrated → MCP; Shell + Node.js only → mcporter.

**Region Site Routing (mandatory):** When the user specifies a Yunxiao instance address or token differing from current MCP config:
- MUST prompt user to update MCP Server config (`YUNXIAO_API_BASE_URL` / `YUNXIAO_ACCESS_TOKEN`)
- MUST NOT bypass MCP Server via mcporter — mcporter is only for when MCP Server is absent
- URL with Region keywords (e.g., `cn-shanghai`) → Region edition; `openapi-rdc.aliyuncs.com` or unspecified → Central (default)

**Method A: Alibaba Cloud CLI**

```bash
aliyun devops <command> --<param1> <value1> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"
```

> All `aliyun devops` commands **must** include `--user-agent` with the session-scoped UA value (see Section 7: Observability). When using environment variables for authentication, no additional auth parameters are needed. When using command-line parameters, append `--yunxiao-access-token` and `--organization-id` (central) or `--api-base-url` (region) to each command.

For command discovery by product prefix, use `scripts/discover-commands.sh` or see [references/tool-catalog.md](references/tool-catalog.md).

**Method B: Platform-native MCP**

```
use_mcp_tool(
  server_name: "yunxiao",
  tool_name: "<tool>",
  arguments: { "<key>": "<value>" }
)
```

**Method C: mcporter CLI**

```bash
npx -y mcporter@0.11.1 call --no-coerce --stdio "npx -y alibabacloud-devops-mcp-server@0.3.38" <tool_name> [key:"value" ...]
```

> **MUST** always use `--no-coerce` to prevent auto type conversion of string enums.

Parameter rules: Use `key:"value"` format, space-separated. Do not pass JSON strings. Omit parameters for no-argument tools. Use `scripts/mcporter-call.sh` for convenience.

**Get available tools:**
```bash
npx -y mcporter@0.11.1 list --stdio "npx -y alibabacloud-devops-mcp-server@0.3.38" --schema
```

> **[MUST] Tool selection must be based on dynamic discovery**: Select from registered tool list, never fabricate tool names. Use `mcporter list` or [references/tool-catalog.md](references/tool-catalog.md).

> **[MUST] Never fabricate results**: All tool calls must be actually executed with real return values.

**Pre-execution checklist (mandatory):**
1. Obtain `organizationId` via `get_current_organization_info` (CLI: `aliyun devops base-get-user-by-token`)
2. **[Mandatory]** Verify target resource exists via `list_*` / `search_*` / `get_*` — even if ID is provided
3. All required parameters confirmed with user (Section 4)
4. Delete operations require confirmation
5. **[Mandatory]** Dynamic schema validation before first call to any unfamiliar tool:
   - Method B: Check platform tool registry
   - Method C: `npx -y mcporter@0.11.1 list --stdio "npx -y alibabacloud-devops-mcp-server@0.3.38" --schema 2>&1 | grep -A 30 'function <tool_name>'`
   - If schema returns a different tool name, use the schema's version
   - For Testhub: call `get_testcase_field_config` first
   - For Projex: call `list_work_item_types` first — never use hardcoded type IDs

Full tool catalog: [references/tool-catalog.md](references/tool-catalog.md). Scenario examples: [references/common-scenarios.md](references/common-scenarios.md).

---

## 6. Success Verification

> **[RECOMMENDED]** After `create_*` / `update_*`, call the corresponding `get_*` to verify when budget permits. If API returned success with a resource ID, creation can be considered successful even without read-back.
>
> **Known API limitations**: Some fields may differ between write and read-back — see [references/verification-method.md](references/verification-method.md).

| Operation | Verification tool | Check |
|-----------|------------------|-------|
| Create pipeline | `get_pipeline` | pipelineId + name match |
| Run pipeline | `get_latest_pipeline_run` | status != `FAIL` |
| Create branch | `get_branch` / `list_branches` | Branch appears |
| Create MR | `get_change_request` | state = `OPENED` |
| Create work item | `get_work_item` | subject + workItemTypeId correct |
| Create sprint | `get_sprint` | Date range matches |

More: [references/verification-method.md](references/verification-method.md).

---

## 7. Observability

### User-Agent Declaration (Mandatory)

> **[MUST]** Every `aliyun devops` business command must carry the `--user-agent` flag for attribution and tracing. The UA value follows a fixed template that includes a per-session identifier.

**UA Template:**

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-devops/{session-id}
```

**Session-ID Generation Rule:**

| Item | Rule |
|------|------|
| Format | 32-character lowercase hexadecimal string, e.g., `f47ac10b58cc4372a5670e02b2c3d479` |
| Lifecycle | Generate **once** at the start of each skill invocation session; reuse the same value across **all channels** (CLI, MCP, mcporter) within that session |
| Consistency | The same `{session-id}` must be used for CLI `--user-agent`, MCP request metadata, and mcporter calls within one session |
| Generation method | `python3 -c "import uuid; print(uuid.uuid4().hex)"` or `uuidgen \| tr -d '-' \| tr '[:upper:]' '[:lower:]'` |

**Usage — append to every `aliyun devops` command:**

```bash
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")

aliyun devops <command> --<param1> <value1> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"
```

> **Important**: The `--user-agent` flag is applied **directly on each business command**. Do NOT configure UA through any global mode-setting command — always pass it inline per invocation.

---

## 8. Best Practices

1. **Read before write**: `get_*` before `update_*` / `delete_*` to confirm current state
2. **Pagination**: List APIs paginate by default; pass `page` / `perPage` for large lists
3. **YAML first**: Pipeline creation: `generate_pipeline_yaml` → validate → `create_pipeline_from_description`
4. **Smart search**: `smart_list_pipelines` supports natural-language time ranges
5. **Read-only first**: When uncertain, use `list_*` / `search_*` / `get_*`
6. **Fail fast**: Two consecutive same-parameter failures → change approach. Report: methods tried, errors, root cause, next steps
7. **Budget discipline**: Plan critical path first; debugging ≤3 steps; near limit (≤2 remaining) → stop and report
8. **Clean up**: Delete experimental resources after use

---

## 9. Scenario Quick Reference

Full examples: [references/common-scenarios.md](references/common-scenarios.md).

| Scenario | Product | Key tools |
|----------|---------|-----------|
| Create Java build pipeline | Flow | `list_repositories` → `create_pipeline_from_description` → `get_pipeline` |
| Create MR with review comment | Codeup | `get_repository` → `create_change_request` → `create_change_request_comment` |
| Create sprint and add requirement | Projex | `search_projects` → `create_sprint` → `create_work_item` |
| Run pipeline and view logs | Flow | `get_pipeline` → `create_pipeline_run` → `get_pipeline_run` → `get_pipeline_job_run_log` |
| Batch query artifacts | Packages | `list_package_repositories` → `list_artifacts` |
| Create test cases | Testhub | `list_testcase_directories` → `create_testcase` → `search_testcases` |
| Application release workflow | AppStack | `list_app_release_workflows` → `execute_app_release_stage` |

---

## 10. Reference Index

| Reference file | Content |
|---------------|---------|
| [references/mcp-setup.md](references/mcp-setup.md) | MCP Server connection modes and environment variables |
| [references/intent-classification.md](references/intent-classification.md) | Intent classification decision tree |
| [references/product-mapping.md](references/product-mapping.md) | Keyword → product mapping table |
| [references/product-reference.md](references/product-reference.md) | Yunxiao documentation index and key concepts |
| [references/tool-catalog.md](references/tool-catalog.md) | ~165 MCP tools grouped catalog |
| [references/token-scopes.md](references/token-scopes.md) | Token authorization scopes and troubleshooting |
| [references/common-scenarios.md](references/common-scenarios.md) | End-to-end workflow examples |
| [references/verification-method.md](references/verification-method.md) | Success verification and read-back methods |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Tool call correctness acceptance criteria |
| [references/ram-policies.md](references/ram-policies.md) | Yunxiao permission model vs. standard Alibaba Cloud RAM |

- [Yunxiao Documentation](https://help.aliyun.com/product/150040.html)
- [Yunxiao OpenAPI](https://help.aliyun.com/zh/yunxiao/developer-reference/)
- [alibabacloud-devops-mcp-server](https://www.npmjs.com/package/alibabacloud-devops-mcp-server)
