# Search Examples

Examples moved from `SKILL.md` to keep the main skill instructions focused.

All examples use AgentExplorer HTTP API directly through `curl`.

## Common Use Cases & Examples

### Example 1: Simple Single-Capability Request

User: "Find skills for diagnosing ECS instance connectivity and performance issues."

| Requirement | Search Phrase |
| ----------- | ------------- |
| Diagnose ECS instance connectivity and performance | ECS instance diagnosis connectivity CPU disk |

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS instance diagnosis connectivity CPU disk' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Display results table, then get details for the best candidate if needed
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/<selected-skill-name>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Example 2: Category Listing Request

Use category listing when the user asks to list all Skills under a category. After listing all category results, review the enumerated skills and highlight likely matches for the user's subtask. Do not install when the user asks to list only.

User: "List all database Skills and point out which ones may fit RDS daily operations."

```bash
curl -sS 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# If nextToken is returned, fetch the next page
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=database' \
  --data-urlencode 'maxResults=20' \
  --data-urlencode 'nextToken=<next-token-from-previous-response>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Example 3: Natural-Language Intent Search

User: "把本地文件同步到 OSS"

| Requirement | Search Phrase |
| ----------- | ------------- |
| Sync local files to OSS | 把本地文件同步到 OSS |

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=把本地文件同步到 OSS' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Example 4: Refine Weak Results

If the first search only matches surface wording, rewrite the search phrase toward the underlying capability before declaring a gap.

| Requirement | Weak Search Phrase | Capability-Oriented Search Phrase |
| ----------- | ------------------ | --------------------------------- |
| Query internal standards before generating content | internal standards policy names | knowledge base retrieval document Q&A content citation |

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=knowledge base retrieval document Q&A content citation' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Example 5: Compound Request With Support Needs

For compound requests, create one searchable intent unit for each meaningful requirement or support need, then search each unit independently.

User: "Generate an output from a source document, consult internal standards first, and handle setup or runtime blockers if needed."

| Requirement | Search Phrase |
| ----------- | ------------- |
| Generate structured output from source material | document parsing content generation structured output |
| Query internal standards before generation | knowledge base retrieval document Q&A content citation |
| Handle setup or runtime blockers | runtime dependency installation environment troubleshooting |

```bash
curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=document parsing content generation structured output' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=knowledge base retrieval document Q&A content citation' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

curl -sS -G 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=runtime dependency installation environment troubleshooting' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Before installation, present the final de-duplicated install plan:

```text
Final global Skills to install:

| Skill Name | Solves |
| ---------- | ------ |
| <content-generation-skill> | Generates the requested output |
| <knowledge-retrieval-skill> | Retrieves and cites internal standards |
| <environment-guidance-skill> | Handles setup or runtime blockers |
```
