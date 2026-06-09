# AgentExplorer HTTP API Reference

Complete reference for HTTP requests used by the `alibabacloud-find-skills` skill.

Discovery uses `curl` directly. Do not install Aliyun CLI or the `agentexplorer` CLI plugin for this skill's search, browse, or detail workflows.

## Common Request Headers

Every AgentExplorer request must include:

```bash
-H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
-H 'x-acs-version: 2026-03-17' \
-H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

`x-acs-date` is mandatory and must be current UTC time.

For Windows PowerShell, Command Prompt, macOS, Linux, WSL, and Git Bash curl templates, see [curl-shell-compatibility.md](curl-shell-compatibility.md).

## API Summary

| API | Purpose | Required values |
| --- | --- | --- |
| `GET /openapi/for-agent/skills` | Search or list skills | Common headers; query params depend on mode |
| `GET /openapi/for-agent/categories` | List skill categories | Common headers |
| `GET /openapi/for-agent/skills/{skillName}` | Get skill details | Common headers; path `skillName` |

Base URL:

```text
https://agentexplorer.aliyuncs.com
```

## 1. Search Or List Skills

**Endpoint**:

```text
GET https://agentexplorer.aliyuncs.com/openapi/for-agent/skills
```

**Query parameters**:

| Parameter | Required | Description |
| --- | --- | --- |
| `keyword` | No | Search keyword or full intent phrase |
| `categoryCode` | No | Top-level category code, dot-form child category, or comma-separated category list |
| `searchMode` | Conditional | Use `semantic` for intent/keyword/combined search; omit for pure category listing |
| `maxResults` | No | Maximum results per page, default `20`, max `100` |
| `nextToken` | No | Pagination token returned by the previous response |
| `skip` | No | Number of records to skip; prefer `nextToken` for pagination |

### Semantic Intent Or Keyword Search

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=<keyword-or-intent>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### List Skills In A Category

Use when the user asks to list or browse all Skills under a category. Do not pass `keyword` or `searchMode=semantic`.

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Fetch the next page only when `nextToken` is returned:

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'maxResults=20' \
  --data-urlencode 'nextToken=<next-token-from-previous-response>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Combined Semantic Search

Use only after category selection when the user asks for best matches inside a category.

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=<keyword-or-intent>' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

**Response shape**:

```json
{
  "data": [
    {
      "skillName": "alibabacloud-ecs-batch-command",
      "displayName": "ECS 批量命令执行",
      "description": "批量在多台 ECS 实例上执行命令",
      "categoryCode": "computing",
      "categoryName": "计算",
      "subCategoryCode": "ecs",
      "subCategoryName": "云服务器 ECS",
      "installCount": 245,
      "likeCount": 18
    }
  ],
  "totalCount": 100,
  "nextToken": "eyJwYWdlIjoyfQ==",
  "maxResults": 20,
  "requestId": "..."
}
```

## 2. List Categories

**Endpoint**:

```text
GET https://agentexplorer.aliyuncs.com/openapi/for-agent/categories
```

**Example**:

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

**Response shape**:

```json
{
  "data": [
    {
      "code": "computing",
      "name": "计算",
      "children": [
        {
          "code": "ecs",
          "name": "云服务器 ECS"
        }
      ]
    }
  ],
  "requestId": "..."
}
```

## 3. Get Skill Content

**Endpoint**:

```text
GET https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/{skillName}
```

**Example**:

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/<skillName>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

**Response shape**:

```json
{
  "requestId": "...",
  "content": "---\nname: alibabacloud-ecs-batch-command\n..."
}
```

## Category Code Rules

- Top-level category: use the category code directly, e.g. `computing`
- Child category: use dot notation only when the API supports it for the target category, e.g. `computing.ecs`
- Multiple categories: comma-separate category codes, e.g. `computing,database`
- If a bare child category such as `ecs` does not filter as expected, use it as `keyword` or confirm the current category list first

## Search Usage Patterns

Use the same semantic-search shape for both keywords and full intent phrases:

```bash
# Keyword search
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Intent search
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=把本地文件同步到 OSS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

## Notes

- Do not use Aliyun CLI flags such as `--endpoint`, `--region`, `--user-agent`, or `--cli-query` in the HTTP workflow.
- Use `jq` only if it is already available; otherwise inspect the JSON response directly and summarize the relevant fields.
