---
name: alibabacloud-find-skills
description: >
  Use this skill when users want to search, discover, browse, or find Alibaba Cloud (阿里云) agent skills.
  Triggers include: "find a skill for X", "search alicloud skills", "阿里云有什么 skill",
  "搜索阿里云技能", "有没有管理 ECS/RDS/OSS 的 skill", "阿里云 skills 有哪些类目",
  "帮我找一个 skill", "browse alicloud skills", "list alicloud skill categories",
  "is there an alicloud skill that can...", "what alicloud skills are available", "XX Skill 的内容是什么", "我想了解阿里云 XX Skill 具体做什么","帮我安装阿里云 Skill"
  "阿里云 agent skill 市场", "搜一下阿里云的 skill".
---

# Alibaba Cloud Agent Skills Search & Discovery

This skill helps users search, discover, and install Alibaba Cloud official Agent Skills through the `agentexplorer` CLI plugin.

## Scenario Description

This skill enables users to:

1. **Search Skills** — Find Alibaba Cloud Agent Skills by keyword, category, or both
2. **Browse Categories** — Explore available skill categories and subcategories
3. **View Skill Details** — Get detailed information about specific skills
4. **Install Skills** — Guide users through skill installation process

**Architecture**: Alibaba Cloud CLI + agentexplorer Plugin → Skills Repository

### Use Cases

- "Find a skill for managing ECS instances"
- "What Alibaba Cloud skills are available for databases?"
- "阿里云有哪些 OSS 相关的 skill?"
- "Browse all available alicloud skills"
- "Install a skill for RDS management"

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
>
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

### Enable AI-Mode

Aliyun CLI provides AI-Mode. When enabled, the CLI automatically attaches AI identity information, allowing the server to identify and optimize Agent call chains.

```bash
# Enable AI-Mode
aliyun configure ai-mode enable

# Set AI-Mode user-agent identifier
aliyun configure ai-mode set-user-agent

# Disable AI-Mode
aliyun configure ai-mode disable
```

### Update Plugin

After installing plugins, update them periodically to get the latest features and fixes:

```bash
# Update installed CLI plugins
aliyun plugin update
```

### Install agentexplorer Plugin

```bash
# Install the agentexplorer plugin
aliyun plugin install --names agentexplorer

# Verify installation
aliyun agentexplorer --help --user-agent AlibabaCloud-Agent-Skills
```

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
>
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list --user-agent AlibabaCloud-Agent-Skills
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
>
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## RAM Policy

This skill uses read-only APIs from the AgentExplorer service. Required permissions: `agentexplorer:ListCategories`, `agentexplorer:SearchSkills`, `agentexplorer:GetSkillContent`. For the full RAM policy JSON, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
>
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

For detailed permission information, see [references/ram-policies.md](references/ram-policies.md).

## Core Workflow

### Step 1: Search Skills

Based on user intent, choose keyword search, category search, or both:

- **Keyword search**: Extract keywords from the user's request and execute search directly
- **Category search**: Call `list-categories` to get all available categories, select the best match, and search
- **Combined search**: Use both keyword and category to narrow results

```bash
# Keyword search
aliyun agentexplorer search-skills \
  --keyword "<keyword>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Get all categories
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills

# Category search
aliyun agentexplorer search-skills \
  --category-code "<category-code>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Combined search (keyword + category)
aliyun agentexplorer search-skills \
  --keyword "<keyword>" \
  --category-code "<category-code>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 2: Iterate Until Found

If the target skill is not in the results, adjust search criteria and retry automatically:

1. Switch between Chinese and English keywords ("cloud server" → "ECS", "object storage" → "OSS")
2. Broaden keywords (drop qualifiers: "RDS backup automation" → "RDS")
3. Remove category filter, search by keyword only
4. Try synonyms or related terms ("instance" → "ECS", "bucket" → "OSS")
5. Browse the most relevant top-level category without keyword

Repeat until the target skill is found or confirmed not to exist. If all attempts fail, inform the user what was tried.

### Step 3: View Skill Details (Optional)

Optionally retrieve skill content to verify it matches user intent before installation. This step can be skipped if the search results already provide sufficient information.

```bash
aliyun agentexplorer get-skill-content \
  --skill-name "<skill-name>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Install Skill

Execute the installation command for the target skill.

```bash
# Option A: Using npx skills add
npx skills add aliyun/alibabacloud-aiops-skills \
  --skill <skill-name>

# Option B: Using npx clawhub install (recommended for OpenClaw ecosystem)
npx clawhub install <skill-name>
```

Verify the skill appears in the available skills list after installation.

## Command Reference

### Parameters

| Parameter Name  | Required/Optional                | Description                                                      | Default Value |
| --------------- | -------------------------------- | ---------------------------------------------------------------- | ------------- |
| `keyword`       | Optional                         | Search keyword (product name, feature name, or description)      | None          |
| `category-code` | Optional                         | Category code for filtering (e.g., "computing", "computing.ecs") | None          |
| `max-results`   | Optional                         | Maximum number of results per page (1-100)                       | 20            |
| `next-token`    | Optional                         | Pagination token from previous response                          | None          |
| `skip`          | Optional                         | Number of items to skip                                          | 0             |
| `skill-name`    | Required (for get-skill-content) | Unique skill identifier                                          | None          |

### Pagination

When search results span multiple pages, use `next-token` from the previous response to fetch the next page:

```bash
aliyun agentexplorer search-skills \
  --keyword "<keyword>" \
  --max-results 20 \
  --next-token "<next-token-from-previous-response>" \
  --user-agent AlibabaCloud-Agent-Skills
```

## Success Verification

After each operation, verify success by checking:

1. **List Categories**: Response contains categoryCode and categoryName fields
2. **Search Skills**: Response contains skills array with valid skill objects
3. **Get Skill Content**: Response contains complete skill markdown content
4. **Install Skill**: Skill appears in Claude Code skills list

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

## Search Strategies & Best Practices

### 1. Keyword Selection

- **Use product codes**: `ecs`, `rds`, `oss`, `slb`, `vpc` (English abbreviations work best)
- **Chinese names**: Also supported, e.g., "云服务器", "数据库", "对象存储"
- **Feature terms**: "backup", "monitoring", "batch operation", "deployment"
- **Generic terms**: When unsure, use broader terms like "compute", "storage", "network"

### 2. Category Filtering

- **Browse first**: Use `list-categories` to understand available categories
- **Top-level categories**: `computing`, `database`, `storage`, `networking`, `security`, etc.
- **Subcategories**: Use dot notation like `computing.ecs`, `database.rds`
- **Multiple categories**: Separate with commas: `computing,database`

### 3. Result Optimization

- **Start broad**: Begin with keyword-only search, then add category filters
- **Adjust page size**: Use `--max-results` based on display needs (20-50 typical)
- **Check install counts**: Popular skills usually have higher install counts
- **Read descriptions**: Match skill description to your specific use case

### 4. When No Results Found

```bash
# Strategy 1: Try alternative keywords
# Instead of "云服务器" try "ECS" or "instance"

# Strategy 2: Remove filters
# Drop category filter, search by keyword only

# Strategy 3: Browse by category
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills
aliyun agentexplorer search-skills --category-code "computing" --user-agent AlibabaCloud-Agent-Skills

# Strategy 4: Use broader terms
# Instead of "RDS backup automation" try just "RDS" or "database"
```

### 5. Display Results to Users

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

1. **Always verify credentials first** — Use `aliyun configure list` before any search operation
2. **Iterate on search** — Automatically adjust keywords and retry until the target skill is found or confirmed absent
3. **Start with broad searches** — Narrow down with filters if too many results
4. **Show category structure** — Help users understand available categories before filtering
5. **Display results clearly** — Use tables to make skill comparison easy
6. **Provide skill names** — Always show `skillName` field for installation
7. **Handle pagination** — Offer to load more results if `nextToken` is present
8. **Check install counts** — Guide users toward popular, well-tested skills
9. **Show full details** — Use `get-skill-content` before installation recommendation
10. **Test after install** — Verify skill is available after installation

## Common Use Cases & Examples

### Example 1: Find ECS Management Skills

```bash
# User: "Find skills for managing ECS instances"

# Step 1: Search by keyword
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Display results table and get details for the best match
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Example 2: Browse Database Skills

```bash
# User: "What database skills are available?"

# Step 1: List categories to show database category
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Search database category
aliyun agentexplorer search-skills \
  --category-code "database" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 3: Display results grouped by subcategory
```

### Example 3: Search with Chinese Keyword

```bash
# User: "搜索 OSS 相关的 skill"

# Step 1: Search using Chinese or English keyword
aliyun agentexplorer search-skills \
  --keyword "OSS" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Display results in user's preferred language
```

### Example 4: Narrow Down Search

```bash
# User: "Find backup skills for RDS"

# Step 1: Combined search
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database.rds" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Display targeted results
```

## Reference Documentation

| Reference                                                                    | Description                                  |
| ---------------------------------------------------------------------------- | -------------------------------------------- |
| [references/ram-policies.md](references/ram-policies.md)                     | Detailed RAM permission requirements         |
| [references/related-commands.md](references/related-commands.md)             | Complete CLI command reference               |
| [references/verification-method.md](references/verification-method.md)       | Success verification steps for each workflow |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation guide         |
| [references/acceptance-criteria.md](references/acceptance-criteria.md)       | Testing acceptance criteria and patterns     |
| [references/category-examples.md](references/category-examples.md)           | Common category codes and examples           |

## Troubleshooting

### Error: "failed to load configuration"

**Cause**: Alibaba Cloud CLI not configured with credentials.

**Solution**: Follow authentication section above to configure credentials.

### Error: "Plugin not found"

**Cause**: agentexplorer plugin not installed.

**Solution**: Run `aliyun plugin install --names aliyun-cli-agentexplorer`

### No Results Returned

**Cause**: Search criteria too specific or incorrect category code.

**Solutions**:

1. Try broader keywords
2. Remove category filter
3. Use `list-categories` to verify category codes
4. Try English product codes instead of Chinese names

### Pagination Issues

**Cause**: Incorrect nextToken or skip value.

**Solution**: Use exact `nextToken` value from previous response, don't modify it.

## Notes

- **Read-only operations**: This skill only performs queries, no resources are created
- **No credentials required for browsing**: Some operations may work without full credentials
- **Multi-language support**: Keywords support both English and Chinese
- **Regular updates**: Skills catalog is regularly updated with new skills
- **Community skills**: Some skills may be community-contributed, check descriptions carefully
