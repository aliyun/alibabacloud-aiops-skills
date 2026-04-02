---
name: alibabacloud-find-skills
description: >
  Use this skill when users want to search, discover, browse, or find Alibaba Cloud (阿里云) agent skills.
  Triggers include: "find a skill for X", "search alicloud skills", "阿里云有什么 skill",
  "搜索阿里云技能", "有没有管理 ECS/RDS/OSS 的 skill", "阿里云 skills 有哪些类目",
  "帮我找一个 skill", "browse alicloud skills", "list alicloud skill categories",
  "is there an alicloud skill that can...", "what alicloud skills are available", "XX Skill 的内容是什么", "我想了解阿里云 XX Skill 具体做什么",
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

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., keyword, category-code, skill-name, max-results, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter Name  | Required/Optional                | Description                                                      | Default Value |
| --------------- | -------------------------------- | ---------------------------------------------------------------- | ------------- |
| `keyword`       | Optional                         | Search keyword (product name, feature name, or description)      | None          |
| `category-code` | Optional                         | Category code for filtering (e.g., "computing", "computing.ecs") | None          |
| `max-results`   | Optional                         | Maximum number of results per page (1-100)                       | 20            |
| `next-token`    | Optional                         | Pagination token from previous response                          | None          |
| `skip`          | Optional                         | Number of items to skip                                          | 0             |
| `skill-name`    | Required (for get-skill-content) | Unique skill identifier                                          | None          |

## Core Workflow

### Workflow 1: Search Skills by Keyword

**Scenario**: User wants to find skills related to a specific product or feature.

```bash
# Step 1: Confirm search keyword with user
# Example: "ECS", "database backup", "OSS", "monitoring"

# Step 2: Execute search command
aliyun agentexplorer search-skills \
  --keyword "<user-confirmed-keyword>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 3: Parse and display results to user
# Show: skillName, displayName, description, categoryName, installCount, likeCount
```

### Workflow 2: Browse Skills by Category

**Scenario**: User wants to explore skills in a specific category.

```bash
# Step 1: List all available categories
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Confirm category selection with user
# Example: "computing", "database", "computing.ecs"

# Step 3: Search skills in selected category
aliyun agentexplorer search-skills \
  --category-code "<user-confirmed-category>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 4: Display results to user
```

### Workflow 3: Get Skill Details

**Scenario**: User wants to see detailed information about a specific skill.

```bash
# Step 1: Confirm skill name with user
# (Usually obtained from previous search results)

# Step 2: Retrieve skill content
aliyun agentexplorer get-skill-content \
  --skill-name "<user-confirmed-skill-name>" \
  --user-agent AlibabaCloud-Agent-Skills

# Step 3: Display skill details including:
# - Full description
# - Usage instructions
# - Prerequisites
# - Examples
```

### Workflow 4: Install a Skill

**Scenario**: User wants to install a discovered skill.

```bash
# Step 1: Confirm skill name with user

# Step 2: Execute installation command
npx skills add aliyun/alibabacloud-aiops-skills \
  --skill <user-confirmed-skill-name>

# Step 3: Verify installation success
# Check that skill appears in available skills list
```

### Workflow 5: Combined Search (Keyword + Category)

**Scenario**: User wants to narrow down search results using both keyword and category.

```bash
# Step 1: Confirm both keyword and category with user

# Step 2: Execute combined search
aliyun agentexplorer search-skills \
  --keyword "<user-confirmed-keyword>" \
  --category-code "<user-confirmed-category>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 3: Display filtered results
```

### Workflow 6: Paginated Search

**Scenario**: User wants to browse through multiple pages of search results.

```bash
# Step 1: Execute initial search
aliyun agentexplorer search-skills \
  --keyword "<keyword>" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Extract nextToken from response

# Step 3: Fetch next page if user requests more results
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
2. **Confirm parameters with user** — Never assume keyword or category without asking
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

# Step 2: Display results table
# Step 3: If user selects a skill, get details
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

# Step 1: Search using Chinese or English
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
