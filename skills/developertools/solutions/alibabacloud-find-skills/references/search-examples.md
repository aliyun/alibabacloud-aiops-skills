# Search Examples

Examples moved from `SKILL.md` to keep the main skill instructions focused.

## Common Use Cases & Examples

### Example 1: Simple Single-Capability Request

User: "Find skills for diagnosing ECS instance connectivity and performance issues."

| Requirement | Search Phrase |
| ----------- | ------------- |
| Diagnose ECS instance connectivity and performance | ECS instance diagnosis connectivity CPU disk |

```bash
aliyun agentexplorer search-skills \
  --keyword "ECS instance diagnosis connectivity CPU disk" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Display results table, then get details for the best candidate if needed
aliyun agentexplorer get-skill-content \
  --skill-name "<selected-skill-name>" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 2: Category Listing Request

Use category listing when the user asks to list all Skills under a category. After listing all category results, review the enumerated skills and highlight likely matches for the user's subtask. Do not install when the user asks to list only.

User: "List all database Skills and point out which ones may fit RDS daily operations."

```bash
aliyun agentexplorer list-categories \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

aliyun agentexplorer search-skills \
  --category-code "database" \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# If nextToken is returned, fetch the next page
aliyun agentexplorer search-skills \
  --category-code "database" \
  --max-results 20 \
  --next-token "<next-token-from-previous-response>" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 3: Natural-Language Intent Search

User: "把本地文件同步到 OSS"

| Requirement | Search Phrase |
| ----------- | ------------- |
| Sync local files to OSS | 把本地文件同步到 OSS |

```bash
aliyun agentexplorer search-skills \
  --keyword "把本地文件同步到 OSS" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 4: Refine Weak Results

If the first search only matches surface wording, rewrite the search phrase toward the underlying capability before declaring a gap.

| Requirement | Weak Search Phrase | Capability-Oriented Search Phrase |
| ----------- | ------------------ | --------------------------------- |
| Query internal standards before generating content | internal standards policy names | knowledge base retrieval document Q&A content citation |

```bash
aliyun agentexplorer search-skills \
  --keyword "knowledge base retrieval document Q&A content citation" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

### Example 5: Compound Request With Support Needs

For compound requests, create one searchable intent unit for each meaningful requirement or support need, then search each unit independently.

User: "Generate an output from a source document, consult internal standards first, and handle setup or runtime blockers if needed."

| Requirement | Search Phrase |
| ----------- | ------------- |
| Generate structured output from source material | document parsing content generation structured output |
| Query internal standards before generation | knowledge base retrieval document Q&A content citation |
| Handle setup or runtime blockers | CLI guidance credentials plugins runtime troubleshooting |

```bash
aliyun agentexplorer search-skills \
  --keyword "document parsing content generation structured output" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

aliyun agentexplorer search-skills \
  --keyword "knowledge base retrieval document Q&A content citation" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

aliyun agentexplorer search-skills \
  --keyword "CLI guidance credentials plugins runtime troubleshooting" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
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
