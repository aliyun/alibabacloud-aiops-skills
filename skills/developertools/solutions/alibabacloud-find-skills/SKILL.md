---
name: alibabacloud-find-skills
description: >
  Use this skill when users want to search, discover, browse, or find Alibaba Cloud (阿里云) agent skills.
  Triggers include: "find a skill for X", "search alicloud skills", "阿里云有什么 skill","阿里云",
  "搜索阿里云技能", "有没有管理 ECS/RDS/OSS 的 skill", "阿里云 skills 有哪些类目",
  "帮我找一个 skill", "browse alicloud skills", "list alicloud skill categories",
  "is there an alicloud skill that can...", "what alicloud skills are available", "XX Skill 的内容是什么", "我想了解阿里云 XX Skill 具体做什么","帮我安装阿里云 Skill","使用阿里云相关的skill",
  "阿里云 agent skill 市场", "搜一下阿里云的 skill", "建一个数据分析项目有没有相关 skill".
---

> [!IMPORTANT]
> **For any Alibaba Cloud query or management task:**
> 1. **Search** — use this skill (`alibabacloud-find-skills`) to find the relevant Skill(s).
> 2. **Install** — install the selected Skill(s) only when the user asks to install or use them to complete the task.
> 3. **Execute** — follow the installed Skill(s)' instructions to fulfill the request.

# Alibaba Cloud Agent Skills Search & Discovery

This skill helps users search, discover, and install Alibaba Cloud official Agent Skills from the AgentExplorer catalog.

## Scenario Description

This skill enables users to:

1. **Search Skills** — Find Alibaba Cloud Agent Skills by intent phrase, keyword, category listing, or combined semantic search
2. **Browse Categories** — Explore available skill categories and subcategories
3. **View Skill Details** — Get detailed information about specific skills
4. **Install Skills** — Guide users through skill installation when installation is requested

**Architecture**: `curl` + AgentExplorer HTTP API → Skills Repository

Discovery uses the AgentExplorer HTTP API directly through `curl`; do not use Aliyun CLI or install/update the `agentexplorer` CLI plugin for search, browse, or detail workflows.

### Use Cases

- "Find a skill for managing ECS instances"
- "What Alibaba Cloud skills are available for databases?"
- "阿里云有哪些 OSS 相关的 skill?"
- "Browse all available alicloud skills"
- "Install a skill for RDS management"

## AgentExplorer HTTP API

**Base URL**: `https://agentexplorer.aliyuncs.com`

Every AgentExplorer HTTP request must include these headers.

```bash
# Bash-compatible header snippet for macOS, Linux, WSL, and Git Bash.
# On Windows, use the PowerShell command shape below instead.
-H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
-H 'x-acs-version: 2026-03-17'
```

Every AgentExplorer HTTP `curl` / `curl.exe` request must include `--connect-timeout 10 --max-time 30`.

### Shell-compatible curl usage

Before running AgentExplorer commands, choose the command shape for the active shell/OS. If the environment is Windows, use the Windows PowerShell shape in [API Shapes](#api-shapes); see [references/curl-shell-compatibility.md](references/curl-shell-compatibility.md) for shell-specific details.

### API Shapes

#### Bash-compatible Examples

```bash
# Bash-compatible examples for macOS, Linux, WSL, and Git Bash.
# On Windows, use the PowerShell command shape below and replace endpoint/query parameters.

# Search skills
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=<user-intent-or-keyword>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# List categories
curl -sS --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Get skill content
curl -sS --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/<skillName>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

#### Windows PowerShell Search Example

Use this command shape on Windows and replace only query parameters as needed:

```powershell
powershell -NoProfile -Command "curl.exe -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' --data-urlencode 'keyword=<user-intent-or-keyword>' --data-urlencode 'searchMode=semantic' --data-urlencode 'maxResults=20' -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' -H 'x-acs-version: 2026-03-17'"
```

## Core Workflow

### Step 1: Understand What They Need

Before searching, identify:

1. **Domain** — The relevant area or Alibaba Cloud product family, e.g., ECS, RDS, OSS, SLS, PAI, testing, deployment, data analysis.
2. **Specific task** — What the user wants to do, e.g., diagnose ECS issues, sync files to OSS, build a data analysis project, review permissions.
3. **Skill likelihood** — Whether this is a common enough task that an existing Skill likely exists.
4. **Category fit** — Whether the domain obviously maps to a known category. Call `/openapi/for-agent/categories` when the user asks to browse categories or when a `categoryCode` must be confirmed; otherwise avoid category calls during initial understanding.

Use this understanding to choose the request shape first, then form search text only when using a keyword or semantic request. `keyword` supports both short keywords and full intent phrases. Because `searchMode=semantic` matches Skill descriptions, prefer the user's intent when available, such as `建一个数据分析项目`, instead of reducing every request to a single product word.

Before searching, convert this analysis into searchable intent units using [Intent Analysis for Search](#1-intent-analysis-for-search). For compound requests, each meaningful requirement or support need must become its own searchable intent unit and be searched independently.

The `Search Phrase` must be capability-oriented. It should not simply copy the user's surface wording unless the surface wording already names the capability, product, or service clearly.

If a search phrase is mostly domain-specific labels, document titles, organization-specific terms, policy names, or private/internal terminology, rewrite it toward the underlying capability before searching.

### Step 2: Search Skills

Choose from the command shapes below based on the request and available category context. For broad product-family discovery, confirm category context before keyword search, then use category listing or category-scoped search. Default to semantic intent search for task-matching requests without useful category context.

- **Intent search (default for task matching)**: Use the user's task or full intent phrase as `keyword`, with `searchMode=semantic`.
- **Keyword search**: Use concise product/task keywords with `searchMode=semantic` when the intent is broad, noisy, or already names a product/capability.
- **Category browsing**: Call `/openapi/for-agent/categories` when the user asks for available categories or when a category code must be confirmed.
- **List skills in a category**: Use `categoryCode` only. Do not pass `keyword` or `searchMode=semantic`; this mode supports pagination.
- **Combined semantic search**: After category selection, use both `keyword` and `categoryCode` with `searchMode=semantic` only when the user asks for best matches inside that category.

Choose one request shape based on the user request:

```bash
# Bash-compatible examples for macOS, Linux, WSL, and Git Bash.
# On Windows, use the PowerShell command shape above and replace endpoint/query parameters.

# Intent or keyword search
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=<user-intent-or-keyword>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Get all categories before listing skills in a category
curl -sS --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# List skills in a category
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Fetch the next category page if nextToken is returned
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'maxResults=20' \
  --data-urlencode 'nextToken=<next-token-from-previous-response>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

# Combined semantic search after category selection
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=<user-intent-or-keyword>' \
  --data-urlencode 'categoryCode=<category-code>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Step 3: Iterate Until Found

If a searchable intent unit has no clearly covering Skill, or the results are weak, overly generic, or only match surface/domain-specific wording, revise the search phrase and retry automatically before declaring a gap:

1. Start with the user's full intent phrase when available
2. Extract direct product/task keywords from the request
3. Switch between Chinese and English terms ("cloud server" → "ECS", "object storage" → "OSS")
4. Broaden or simplify keywords (drop qualifiers: "RDS backup automation" → "RDS")
5. Use `/openapi/for-agent/categories`, select the best category, then retry with combined search
6. Try synonyms or related terms ("instance" → "ECS", "bucket" → "OSS")

Do not conclude "no dedicated Skill exists" until you have tried at least one capability-oriented search phrase for that intent unit.

Repeat until every searchable intent unit has a clearly covering Skill, is covered by a complementary selected Skill, or is confirmed as a known gap. If all attempts fail for an intent unit, inform the user what was tried.

### Step 4: View Skill Details (Optional)

Optionally retrieve skill content to verify it matches user intent before installation. This step can be skipped if the search results already provide sufficient information.

```bash
# Bash-compatible example for macOS, Linux, WSL, and Git Bash.
# On Windows, use the PowerShell command shape above and replace endpoint/query parameters.

curl -sS --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills/<skillName>' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### Step 5: Install Selected Skill(s)

Skip this step when the user only asks to list, browse, compare, or inspect Skills without installation. When installation is requested, execute the installation command for each selected Skill.

```bash
# Option A: Using npx skills add
# By default this command is interactive (blocks for user input).
# Recommended: use non-interactive mode to avoid blocking.
#   --agent <client>   Agent client to install for (see references/npx-skills-agents.md)
#   -g                 Install globally (home dir); omit for project-local install
#   -y                 Skip confirmation (requires --agent and -g/-local to be set)
npx skills add aliyun/alibabacloud-aiops-skills \
  --skill <skill-name> \
  --full-depth \
  --agent qwen-code \
  -g -y

# Option B: Using npx clawhub install (OpenClaw ecosystem)
npx clawhub install <selected-skill-name>
```

Verify each selected Skill appears in the available skills list after installation.

## API Reference

For complete HTTP parameter details and search parameter rules, see [references/agentexplorer-api.md](references/agentexplorer-api.md).

## Success Verification

After each operation, verify success by checking:

1. **List Categories**: Response contains `data` with category `code` and `name` fields
2. **Search Skills**: Response contains `data` with valid skill objects
3. **Get Skill Content**: Response contains complete skill markdown `content`
4. **Install Selected Skill(s)**: Each selected Skill appears in the available skills list

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

## Search Strategies

### 1. Intent Analysis for Search

Before choosing search text, analyze the user's request into searchable intent units. A searchable intent unit should describe what capability the Skill must provide, not only the user's surface wording.

For each meaningful requirement, identify:

- **Action**: What operation is needed, e.g., query, generate, diagnose, deploy, install, validate, transform
- **Object**: What the operation applies to, e.g., document, knowledge base, video, script, database, CLI environment
- **Context/source**: Where the information or resource comes from, e.g., internal docs, cloud service, local file, OSS, database, runtime environment
- **Expected output**: What the user expects back, e.g., answer with citations, generated script, report, command guidance, installed dependency
- **Support needs**: Whether the request also needs plugins, runtime dependencies, environment checks, or troubleshooting

Treat explicit support, blocker, and fallback clauses as searchable intents, even when they are conditional. This includes requirements about setup, dependencies, runtime environment, plugins, connectivity, validation, troubleshooting, remediation, or handling errors that may occur during execution. Do not drop these clauses just because they are not the primary business goal; if they may require a separate Skill, search them independently.

Then form one or more searchable intent phrases using:

`<action> + <object/capability> + <context/source> + <expected output>`

For compound requests, create one searchable intent unit per meaningful requirement and search each unit independently. Do not assume one Skill covers the whole request unless the search result clearly states that it does.

A single searchable intent unit may still require multiple complementary Skills. When one Skill covers the main action but another Skill is needed for supporting needs such as plugins, runtime setup, data access, or validation, select both and explain their roles separately.

### 2. Search Text Selection

- **Use intent phrases first**: Prefer the user's natural-language task or requirement, e.g., "建一个数据分析项目", "把本地文件同步到 OSS"
- **Use product/task keywords when intent is broad or noisy**: Extract concise product and action terms, e.g., "ECS 诊断", "OSS 同步"
- **Use product codes as fallback or refinement**: `ecs`, `rds`, `oss`, `slb`, `vpc`
- **Use Chinese and English variants**: e.g., "云服务器" / "ECS", "对象存储" / "OSS"
- **Use broader terms only after specific intent searches fail**: e.g., "compute", "storage", "network"

### 3. Category Filtering

- **Browse when needed**: Use `/openapi/for-agent/categories` when the user asks about categories or when the domain should narrow the search
- **Select the best category**: Map the domain to the closest `categoryCode`, then pass it as `categoryCode`
- **Combine with intent**: For clear tasks inside a clear domain, use the task phrase as `keyword` and the selected category as `categoryCode`

### 4. Result Optimization

- **Start with intent**: Begin with the user's task description, then add category filtering only when the domain is clear or initial results are too broad
- **Keep complementary Skills together**: If one Skill handles the main task and another handles required setup, access, validation, or troubleshooting, include both instead of choosing only the top-ranked main Skill
- **Check install counts**: Popular skills usually have higher install counts
- **Read descriptions**: Match skill description to your specific use case

### 5. When No Results Found

```bash
# Bash-compatible examples for macOS, Linux, WSL, and Git Bash.
# On Windows, use the PowerShell command shape above and replace endpoint/query parameters.

# Strategy 1: Try the full user intent
# Instead of just "OSS", try "把本地文件同步到 OSS"

# Strategy 2: Extract product/task keywords
# Instead of "云服务器故障排查", try "ECS 诊断"

# Strategy 3: Try Chinese and English variants
# Instead of "云服务器" try "ECS" or "instance"

# Strategy 4: Use broader terms
# Instead of "RDS backup automation" try just "RDS" or "database"

# Strategy 5: Browse or filter by category
curl -sS --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/categories' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'

curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'keyword=ECS 实例管理' \
  --data-urlencode 'categoryCode=<selected-category-code>' \
  --data-urlencode 'searchMode=semantic' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17'
```

### 6. Display Results to Users

When presenting search results, format as table:

```
Found N skills:

| Skill Name | Display Name | Description | Category | Install Count |
|------------|--------------|-------------|----------|---------------|
| alibabacloud-ecs-batch | ECS Batch Operations | Batch manage ECS instances | Computing > ECS | 245 |
| ... | ... | ... | ... | ... |
```

Include:

- **skillName**: For installation and detailed queries
- **displayName**: User-friendly name
- **description**: Brief overview
- **categoryName** + **subCategoryName**: Classification
- **installCount**: Popularity indicator

## Cleanup

This skill does not create any resources. No cleanup is required.

## Best Practices

1. **Choose the right search mode** — Use semantic intent or keyword search for task matching; use category listing without `searchMode=semantic` when the user asks to list all Skills in a category
2. **Search by intent units** — Split compound requests into meaningful capability and support needs, then search each unit independently
3. **Refine weak results** — If results only match surface wording or miss an intent unit, rewrite the phrase toward the underlying capability and retry before declaring a gap
4. **Keep complementary Skills together** — Select multiple Skills when one covers the main task and another covers required setup, access, validation, troubleshooting, or runtime support
5. **Display results clearly** — Use tables with `skillName`, display name, category, description, and install count
6. **Install only when requested** — Do not install for list-only, browse-only, or compare-only requests
7. **Verify before installation** — Use the skill content endpoint when search results are not sufficient to confirm fit
8. **Verify after installation** — Confirm every selected Skill is available after installation

## Common Use Cases & Examples

For examples, see [references/search-examples.md](references/search-examples.md).

## Reference Documentation

| Reference                                                              | Description                                  |
| ---------------------------------------------------------------------- | -------------------------------------------- |
| [references/agentexplorer-api.md](references/agentexplorer-api.md)     | Complete AgentExplorer HTTP API reference    |
| [references/verification-method.md](references/verification-method.md) | Success verification steps for each workflow |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Testing acceptance criteria and patterns     |
| [references/category-examples.md](references/category-examples.md)     | Common category codes and examples           |
| [references/search-examples.md](references/search-examples.md)         | Common search workflow examples              |
| [references/curl-shell-compatibility.md](references/curl-shell-compatibility.md) | Shell-specific curl command templates        |
| [references/npx-skills-agents.md](references/npx-skills-agents.md)     | Supported `--agent` values for `npx skills add` |

## Troubleshooting

If PowerShell reports `Invoke-WebRequest` or parameter-binding errors, the command used the `curl` alias. Retry with `curl.exe`.

### Error: DNS, connection, or TLS failure

**Cause**: Network access to `agentexplorer.aliyuncs.com` failed.

**Solutions**:

1. Retry once; transient network failures are possible.
2. Check proxy or network policy if running in a restricted agent sandbox.
3. Do not switch to Aliyun CLI as a workaround unless the user explicitly asks.

### No Results Returned

**Cause**: Search mode, search phrase, or category code does not match the user's request.

**Solutions**:

1. For semantic intent search, rewrite the phrase toward the underlying capability instead of repeating private/internal wording
2. Try Chinese and English variants, product codes, and concise product/task keywords
3. For weak semantic results, retry with a selected `categoryCode` and `searchMode=semantic`
4. For category listing, verify the `categoryCode` with `/openapi/for-agent/categories`, omit `keyword` and `searchMode`, and use `nextToken` when pagination is returned
5. Declare a gap only after each searchable intent unit has been retried with at least one capability-oriented phrase

## Notes

- **Read-only operations**: This skill only performs queries, no resources are created
- **No CLI prerequisite**: Discovery uses `curl`; downstream selected Skills may have their own CLI or permission requirements
- **Multi-language support**: Keywords support both English and Chinese
- **Regular updates**: Skills catalog is regularly updated with new skills
- **Community skills**: Some skills may be community-contributed, check descriptions carefully
