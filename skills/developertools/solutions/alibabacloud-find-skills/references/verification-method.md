# Verification Methods

This document provides verification steps for each workflow in the `alibabacloud-find-skills` skill.

Discovery workflows use `curl` against AgentExplorer HTTP API.

## Overview

After executing each workflow, verify success by checking:

1. `curl` exits with code `0`
2. Response is valid JSON
3. Response contains the expected field: `data`, `content`, or `requestId`
4. Data content is valid and relevant
5. Errors are handled without switching to Aliyun CLI

## Workflow 1: Search Skills By Keyword

### Success Criteria

The request succeeds:

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Exit code: $?"
```

Expected response fields:

- `data`: array of skill objects
- `totalCount`: number
- `requestId`: string
- `maxResults`: number

Each skill should have:

- `skillName`: non-empty string
- `displayName`: non-empty string
- `description`: non-empty string
- `categoryName`: non-empty string
- `installCount`: non-negative integer
- `likeCount`: non-negative integer

### Minimal Verification Script

```bash
#!/bin/bash
KEYWORD="ECS"

RESULT=$(curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode "keyword=$KEYWORD" \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=5' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)")

if [ $? -ne 0 ]; then
  echo "search request failed"
  exit 1
fi

echo "$RESULT" | grep -q '"data"' || { echo "missing data"; exit 1; }
echo "$RESULT" | grep -q '"skillName"' && echo "skills found" || echo "no skills found"
```

## Workflow 2: Browse Skills By Category

### Success Criteria

List categories succeeds:

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Expected category fields:

- `data`: array
- `code`: category code
- `name`: category display name
- `children`: child category array

Search by category succeeds:

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Search results should contain `categoryCode` matching the requested top-level category.

## Workflow 3: Get Skill Details

### Success Criteria

The request succeeds with a valid skill name:

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/alibabacloud-cli-guidance' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Expected response fields:

- `requestId`: string
- `content`: non-empty markdown string

The `content` value should include skill frontmatter with `name:` and `description:`.

## Workflow 4: Combined Search

### Success Criteria

Combined keyword and category search succeeds:

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=backup' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=10' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Results should be relevant to both the keyword and category.

## Workflow 5: Paginated Category Listing

### Success Criteria

First page returns `nextToken` when more results exist:

```bash
PAGE1=$(curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=2' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)")

echo "$PAGE1" | grep -q '"nextToken"'
```

Second page uses the returned token exactly:

```bash
NEXT_TOKEN="<next-token-from-previous-response>"

curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=2' \
  --data-urlencode "nextToken=$NEXT_TOKEN" \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Do not invent or edit pagination tokens.

## Workflow 6: Install A Skill

Installation is separate from AgentExplorer discovery.

```bash
npx skills add aliyun/alibabacloud-aiops-skills \
  --skill <skill-name> \
  --full-depth \
  --agent qwen-code \
  -g -y
```

Manual checklist:

- [ ] Installation command completed without errors
- [ ] Skill appears in the target agent's skill list
- [ ] Skill can be triggered with appropriate keywords
- [ ] Installed Skill's own prerequisites are followed

## Error Verification

### Missing `x-acs-date`

If `x-acs-date` is omitted, the API returns an error similar to:

```json
{
  "Code": "MissingDate",
  "Message": "Date is mandatory for this action."
}
```

Fix by adding:

```bash
-H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Network Failure

For DNS, proxy, or TLS errors:

1. Retry once
2. Check network/proxy access to `agentexplorer.aliyuncs.com`
3. Report the failure with the attempted endpoint and operation
4. Do not fall back to Aliyun CLI unless the user explicitly requests it

## General Verification Checklist

### Request Execution

- [ ] Uses `curl`, not `aliyun`
- [ ] Uses `https://agentexplorer.aliyuncs.com`
- [ ] Includes `User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills`
- [ ] Includes `x-acs-version: 2026-03-17`
- [ ] Includes `x-acs-date`
- [ ] Uses `--data-urlencode` for query values with spaces, Chinese text, or tokens

### Response Format

- [ ] Search response has `data`
- [ ] Category response has `data`
- [ ] Detail response has `content`
- [ ] Error response is summarized clearly

### User Presentation

- [ ] Results are shown as a table or concise list
- [ ] `skillName`, display name, category, description, and install count are included when available
- [ ] The final install plan is de-duplicated
- [ ] Installation is performed only when the user asked for it
