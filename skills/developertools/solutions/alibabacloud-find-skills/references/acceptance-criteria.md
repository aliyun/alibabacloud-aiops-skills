# Acceptance Criteria: alibabacloud-find-skills

**Skill Name**: `alibabacloud-find-skills`
**Purpose**: Validate correct AgentExplorer HTTP API usage and skill-discovery behavior.

## Discovery Prerequisites

### Correct

The discovery workflow uses `curl` directly:

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Incorrect

```bash
aliyun version
aliyun plugin search agentexplorer
aliyun plugin install --names aliyun-cli-agentexplorer
aliyun plugin update --name aliyun-cli-agentexplorer
aliyun agentexplorer search-skills --keyword "ECS"
aliyun configure list
```

**Why**: Finding, browsing, and inspecting Skills uses direct HTTP requests and no longer requires Aliyun CLI or the AgentExplorer CLI plugin.

## HTTP API Patterns

### 1. Search Skills

#### Correct

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=RDS backup automation' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

#### Incorrect

```bash
# Missing -G: query params are not appended as intended
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=RDS backup automation'

# Wrong parameter names from CLI mode
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'search-mode=semantic' \
  --data-urlencode 'max-results=20'

# Wrong endpoint path
curl -sS -G 'https://agentexplorer.aliyuncs.com/search-skills'
```

**Why**: HTTP query parameters use API names such as `searchMode`, `maxResults`, `categoryCode`, and `nextToken`.

### 2. List Categories

#### Correct

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

#### Incorrect

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/category'
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/list-categories'
```

### 3. Get Skill Content

#### Correct

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/alibabacloud-cli-guidance' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

#### Incorrect

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'skillName=alibabacloud-cli-guidance'

curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skill/alibabacloud-cli-guidance'
```

**Why**: Skill content uses a path parameter: `/openapi/for-agent/skills/{skillName}`.

## Header Requirements

### Correct

Every discovery API call includes both required headers:

```bash
-H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
-H 'x-acs-version: 2026-03-17'
```

### Incorrect

```bash
# Missing API version header
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills'

# Wrong user agent
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS' \
  -H 'User-Agent: MyAgent'

# Wrong header shape for this workflow
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  -H 'x-acs-api-version: 2026-03-17'
```

**Why**: The skill user-agent is required for attribution. The API version header must be `x-acs-version`.

## Search Parameter Rules

### Correct

```bash
# Intent search
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=把本地文件同步到 OSS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Category listing
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Combined semantic search
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=backup' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Incorrect

```bash
# Category listing should not use semantic mode
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'searchMode=semantic'

# Multi-word values are not URL-encoded
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills?keyword=RDS backup automation'
```

## Pagination Rules

### Correct

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  --data-urlencode 'nextToken=<next-token-from-previous-response>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Incorrect

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'next-token=abc'

curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'nextToken=page2'
```

**Why**: Use the API field name `nextToken`, and pass the returned token exactly.

## Result Handling

### Correct

Present users a concise table:

```markdown
| Skill Name | Display Name | Category | Install Count | Why it fits |
| --- | --- | --- | ---: | --- |
| alibabacloud-ecs-batch | ECS Batch Ops | 计算 > ECS | 245 | Handles batch ECS operations |
```

### Incorrect

```bash
# Dumping raw JSON without summarizing
echo "$RESULT"
```

## Installation Rules

### Correct

Only install when the user asks to install or use a selected Skill:

```bash
npx skills add aliyun/alibabacloud-aiops-skills \
  --skill <skill-name> \
  --full-depth \
  --agent qwen-code \
  -g -y
```

### Incorrect

```bash
# Installing during browse-only/search-only requests
npx skills add aliyun/alibabacloud-aiops-skills --skill <skill-name>
```

## Failure Handling

- On network failure, retry once and report endpoint/network context.
- On weak or empty results, rewrite the search phrase toward the underlying capability.
- Do not tell the user to install or configure Aliyun CLI for this discovery workflow.

## Final Checklist

- [ ] Uses `curl`, not `aliyun`, for discovery
- [ ] Uses `https://agentexplorer.aliyuncs.com/openapi/for-agent/skills` for search/listing
- [ ] Uses `https://agentexplorer.aliyuncs.com/openapi/for-agent/categories` for categories
- [ ] Uses `/openapi/for-agent/skills/{skillName}` for details
- [ ] Includes `User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills`
- [ ] Includes `x-acs-version: 2026-03-17`
- [ ] Uses `--data-urlencode` for query parameters
- [ ] Splits compound requests into searchable intent units
- [ ] Installs selected Skills only when requested
