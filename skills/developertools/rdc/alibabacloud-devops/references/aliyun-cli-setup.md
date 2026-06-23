# Yunxiao Alibaba Cloud CLI Configuration Reference

## 1. Installation

- CLI executable path detection: `which aliyun`
- Version detection: `aliyun version`
- Installation references:
  - Windows: [Install CLI (Windows)](https://help.aliyun.com/zh/cli/install-cli-on-windows)
  - Linux: [Install/Update CLI](https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli)
  - macOS: [Install CLI (macOS)](https://help.aliyun.com/zh/cli/install-cli-on-macos)
- Cloud Shell (browser-based): [Cloud Shell](https://shell.aliyun.com/)

## 2. Authentication Configuration

> **Important**: Yunxiao (DevOps) uses **Personal Access Token** for authentication, not AK/SK profiles. You do not use `aliyun configure` to set up credentials for Yunxiao.

### Obtaining a Personal Access Token

Generate a token at the Yunxiao console. See [Obtain Personal Access Token](https://help.aliyun.com/zh/yunxiao/developer-reference/obtain-personal-access-token).

> - Select minimum required API scopes and set a reasonable expiration time.
> - The token is only shown once at creation time — save it securely.
> - If a token is leaked, delete it immediately.

### Method A: Environment Variables (Recommended)

| Environment Variable | Description | Required (Central) | Required (Region) |
| --- | --- | --- | --- |
| `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` | Yunxiao Personal Access Token | Yes | Yes |
| `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL` | API base URL | No | Yes |
| `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` | Organization ID | Yes | No |

**Region site:**

```bash
export ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN=<your-personal-access-token>
export ALIBABA_CLOUD_YUNXIAO_API_BASE_URL=<your-api-base-url>
```

**Central site:**

```bash
export ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN=<your-personal-access-token>
export ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID=<your-organization-id>
```

### Method B: Command-Line Parameters

| Parameter | Description | Required (Central) | Required (Region) |
| --- | --- | --- | --- |
| `--yunxiao-access-token` | Yunxiao Personal Access Token | Yes | Yes |
| `--api-base-url` | API base URL | No | Yes |
| `--organization-id` | Organization ID | Yes | No |

**Region site:**

```bash
aliyun devops <command> \
  --api-base-url=<your-api-base-url> \
  --yunxiao-access-token=<your-personal-access-token>
```

**Central site:**

```bash
aliyun devops <command> \
  --yunxiao-access-token=<your-personal-access-token> \
  --organization-id=<your-organization-id>
```

## 3. API Base URL (Central vs Region)

| Dimension | Central Site | Region Site |
|-----------|-------------|-------------|
| API base URL | `openapi-rdc.aliyuncs.com` (default, no config needed) | Instance-specific URL from Yunxiao console |
| Organization parameter | `--organization-id` | Not required (derived from base URL) |
| API base URL config | Not required | Required (`--api-base-url` or `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL`) |

For Region site API base URL, see [Service Access Point](https://help.aliyun.com/zh/yunxiao/developer-reference/service-access-point-domain).

## 4. CLI Availability Verification

```bash
# Verify CLI and devops plugin are available
aliyun devops --help >/dev/null 2>&1 && echo "cli ready" || echo "cli not available"

# Check version
aliyun devops version
```

## 5. CLI Command Prefix to Product Mapping

| Product | Command Prefix | Example |
|---------|---------------|---------|
| AppStack | `app-stack-*` | `aliyun devops app-stack-list-applications` |
| Base management | `base-*` | `aliyun devops base-search-members` |
| Codeup | `codeup-*` | `aliyun devops codeup-list-repositories` |
| Flow | `flow-*` | `aliyun devops flow-list-pipelines` |
| Insight | `insight-*` | `aliyun devops insight-query` |
| Lingma | `lingma-*` | `aliyun devops lingma-list-knowledge-bases` |
| Packages | `packages-*` | `aliyun devops packages-list-artifacts` |
| Projex | `projex-*` | `aliyun devops projex-create-sprint` |
| Testhub | `test-hub-*` | `aliyun devops test-hub-create-testcase` |

## 6. Command Discovery

View all available commands:

```bash
aliyun devops --help
```

View parameters for a specific command:

```bash
aliyun devops <command-name> --help
```

## 7. Observability: User-Agent (Mandatory)

When driven by this skill, every `aliyun devops` command must carry `--user-agent` for attribution and tracing:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-devops/{session-id}
```

- `{session-id}`: 32-character lowercase hex string, generated once per skill invocation session
- The same session-id is used consistently across all channels (CLI, MCP, mcporter) within one session
- Apply `--user-agent` **directly on each business command** — never configure UA through a global mode-setting command

Example:

```bash
SESSION_ID=$(python3 -c "import uuid; print(uuid.uuid4().hex)")
aliyun devops flow-list-pipelines --page 1 --per-page 20 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-devops/${SESSION_ID}"
```

## 8. CLI Parameter Format Conventions

- Parameter name format: kebab-case (hyphen-separated), e.g., `--pipeline-id`, `--source-branch`
- Pagination: `--page` and `--per-page`
- JMESPath output filtering: `--cli-query "expression"`
- JSON parameters: pass as quoted JSON string, e.g., `--pagination '{"page":1,"perPage":20}'`

## 9. Usage Examples

### List code repositories

```bash
aliyun devops codeup-list-repositories --page 1 --per-page 20
```

### Search projects

```bash
aliyun devops projex-search-projects --page 1 --per-page 10
```

### List pipelines

```bash
aliyun devops flow-list-pipelines --page 1 --per-page 20
```

### List applications

```bash
aliyun devops app-stack-list-applications --pagination '{"page":1,"perPage":20}' --order-by createdAt
```

### Filter output with JMESPath

```bash
aliyun devops codeup-list-repositories --cli-query 'result[].{name:name,id:id}'
```

### Get flow tag group details

```bash
# Region site (env vars configured)
aliyun devops flow-get-flow-tag-group --id 0

# Central site (command-line params)
aliyun devops flow-get-flow-tag-group --id 603 \
  --yunxiao-access-token=<your-personal-access-token> \
  --organization-id=<your-organization-id>
```

## 10. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Authentication failed | Token expired or invalid | Regenerate the token |
| No permission | Insufficient token scopes | Check and update token scopes |
| API error | Wrong parameters | Check parameter names via `aliyun devops <command> --help` |
| Region site fails | Missing API base URL | Set `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL` or use `--api-base-url` |
| Central site fails | Missing organization ID | Set `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` or use `--organization-id` |
