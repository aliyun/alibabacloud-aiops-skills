# Related CLI Commands

Complete reference for all Aliyun CLI commands used in the `alibabacloud-find-skills` skill.

## Command Summary

| Command | Purpose | Required Parameters |
|---------|---------|---------------------|
| `aliyun agentexplorer search-skills` | Search for skills | `--search-mode semantic`, `--endpoint`, `--user-agent` |
| `aliyun agentexplorer list-categories` | List all skill categories | `--endpoint`, `--user-agent` |
| `aliyun agentexplorer get-skill-content` | Get skill details | `--skill-name`, `--endpoint`, `--user-agent` |
| `aliyun plugin install` | Install CLI plugins | `--names` (required) |
| `aliyun configure list` | Check credential configuration | None |
| `aliyun version` | Check CLI version | None |

---

## 1. aliyun agentexplorer search-skills

**Description**: Search for Alibaba Cloud Agent Skills by keyword, category, or both. The upgraded workflow uses semantic search against Skill descriptions, so `--keyword` can be a full intent phrase such as "建一个数据分析项目"; `--category-code` should be filled with the best matching category when the domain is clear.

**Syntax**:
```bash
aliyun agentexplorer search-skills [flags]
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--keyword` | string | No | Search keyword or full intent phrase |
| `--category-code` | string | No | Category code selected from `list-categories`; omit this parameter when no category is selected. Use a top-level `categoryCode` directly. For a child category returned in `subCategories`, pass `<parent-categoryCode>.<child-categoryCode>` (for example, `computing.ecs`). For multiple categories, comma-separate each valid code (for example, `computing.ecs,computing.rds`). Never pass a bare child code like `ecs`; use it as `--keyword` instead. |
| `--search-mode` | string | Conditional | Use `semantic` for intent/keyword/combined search; omit for category listing |
| `--max-results` | int | No | Maximum results per page (1-100, default: 20) |
| `--next-token` | string | No | Pagination token from previous response |
| `--skip` | int | No | Number of items to skip |

**Common Flags**:
- `--endpoint 'agentexplorer.aliyuncs.com'` — **Required**: API endpoint
- `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills` — **Required**: Identify requests from this skill

### Search Parameter Rule

Choose one command shape based on the user request.

#### Semantic Intent Or Keyword Search

Use when the user asks for the best Skill for a task, capability, or natural-language intent. Do not use pagination with semantic search.

```bash
aliyun agentexplorer search-skills \
  --keyword "<keyword-or-intent>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

#### List Skills In A Category

Use when the user asks to list or browse all Skills under a category. Do not pass `--keyword` or `--search-mode semantic`. Use `next-token` to fetch additional pages.

```bash
aliyun agentexplorer search-skills \
  --category-code "<category-code>" \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

aliyun agentexplorer search-skills \
  --category-code "<category-code>" \
  --max-results 20 \
  --next-token "<next-token-from-previous-response>" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

#### Combined Semantic Search

Use only after category selection when the user asks for best matches inside a category.

```bash
aliyun agentexplorer search-skills \
  --keyword "<keyword-or-intent>" \
  --category-code "<category-code>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

**Example Usage**:

```bash
# Semantic search by keyword
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Semantic search by category
aliyun agentexplorer search-skills \
  --keyword "database" \
  --category-code "<category-code>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Semantic search by intent
aliyun agentexplorer search-skills \
  --keyword "建一个数据分析项目" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Combined semantic search
aliyun agentexplorer search-skills \
  --keyword "RDS backup automation" \
  --category-code "<category-code>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

**Output Structure**:
```json
{
  "skills": [
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
  "nextToken": "eyJwYWdlIjoyfQ=="
}
```

---

## 2. aliyun agentexplorer list-categories

**Description**: List all available skill categories and subcategories.

**Syntax**:
```bash
aliyun agentexplorer list-categories [flags]
```

**Parameters**: None required.

**Common Flags**:
- `--endpoint 'agentexplorer.aliyuncs.com'` — **Required**: API endpoint
- `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills` — **Required**: Identify requests from this skill
- `--cli-query <jmespath>` — Filter output using JMESPath expression
- `-q, --quiet` — Suppress output

**Example Usage**:
```bash
# List all categories
aliyun agentexplorer list-categories \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# List categories with JMESPath filtering
aliyun agentexplorer list-categories \
  --cli-query "categories[].categoryName" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

**Output Structure**:
```json
{
  "categories": [
    {
      "categoryCode": "computing",
      "categoryName": "计算",
      "subCategories": [
        {
          "categoryCode": "ecs",
          "categoryName": "云服务器 ECS"
        }
      ]
    }
  ]
}
```

---

## 3. aliyun agentexplorer get-skill-content

**Description**: Retrieve the complete markdown content of a specific skill.

**Syntax**:
```bash
aliyun agentexplorer get-skill-content --skill-name <name> [flags]
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--skill-name` | string | **Yes** | Unique skill identifier (from search results) |

**Common Flags**:
- `--endpoint 'agentexplorer.aliyuncs.com'` — **Required**: API endpoint
- `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills` — **Required**: Identify requests from this skill
- `--cli-query <jmespath>` — Filter output using JMESPath expression
- `-q, --quiet` — Suppress output

**Example Usage**:

```bash
# Get skill content
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Get only the description field
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --cli-query "description" \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

**Output Structure**:
```json
{
  "skillName": "alibabacloud-ecs-batch-command",
  "displayName": "ECS 批量命令执行",
  "description": "批量在多台 ECS 实例上执行命令",
  "content": "---\nname: alibabacloud-ecs-batch-command\n...",
  "categoryCode": "computing",
  "categoryName": "计算",
  "subCategoryCode": "ecs",
  "subCategoryName": "云服务器 ECS",
  "installCount": 245,
  "likeCount": 18,
  "createTime": "2024-01-15T10:30:00Z",
  "updateTime": "2024-03-20T14:45:00Z"
}
```

---

## 4. aliyun plugin install

**Description**: Install Aliyun CLI plugins.

**Syntax**:
```bash
aliyun plugin install --names <plugin-name> [flags]
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--names` | string | **Yes** | Plugin name to install |

**Example Usage**:

```bash
# Install the agentexplorer plugin
aliyun plugin install --names agentexplorer

# Verify the plugin version
aliyun agentexplorer version
```

---

## 5. aliyun configure list

**Description**: List all configured credentials and profiles.

**Syntax**:
```bash
aliyun configure list [flags]
```

**Parameters**: None required.

> **Note**: `aliyun configure list` is a local management command. It does **not** support `--user-agent` or `--endpoint` — do not pass them.

**Example Usage**:

```bash
# List all profiles
aliyun configure list
```

**Output Example**:
```
Profile   | Credential         | Valid   | Region           | Language
--------- | ------------------ | ------- | ---------------- | --------
default * | AK:***abc          | Valid   | cn-hangzhou      | en
profile1  | STS:***def         | Valid   | cn-beijing       | zh
```

---

## 6. aliyun version

**Description**: Display Aliyun CLI version.

**Syntax**:
```bash
aliyun version
```

**Parameters**: None.

**Example Usage**:

```bash
aliyun version
```

**Output Example**:
```
3.3.2
```

---

## 7. aliyun configure set

**Description**: Configure CLI settings. **Run this only after authentication is complete** (verify with `aliyun configure list`).

**Syntax**:
```bash
aliyun configure set [flags]
```

**Common Flags**:
- `--auto-plugin-install <bool>` — Enable/disable automatic plugin installation

> **Note**: `aliyun configure set` is a local management command. It does **not** support `--user-agent` — do not pass it.

**Example Usage**:

```bash
# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true
```

---

## Search Usage Patterns

Use the same semantic-search command shape for both keywords and full intent phrases:

```bash
# Keyword search
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Category search
aliyun agentexplorer search-skills \
  --keyword "database" \
  --category-code "<category-code>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Intent search
aliyun agentexplorer search-skills \
  --keyword "把本地文件同步到 OSS" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Combined search
aliyun agentexplorer search-skills \
  --keyword "把本地文件同步到 OSS" \
  --category-code "<category-code>" \
  --search-mode semantic \
  --max-results 20 \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## Troubleshooting Commands

### Check Plugin Installation

```bash
# List installed plugins
aliyun plugin list

# Check if agentexplorer is installed
aliyun plugin list | grep agentexplorer
```

### Verify Credentials

```bash
# Check if credentials are configured (no --user-agent / --endpoint — local command)
aliyun configure list

# Test API access
aliyun agentexplorer list-categories \
  --endpoint 'agentexplorer.aliyuncs.com' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

---

## Command Comparison Table

| Task | Command | Key Parameters |
|------|---------|----------------|
| Browse all categories | `list-categories` | `--endpoint`, `--user-agent` |
| Search by keyword | `search-skills` | `--keyword`, `--search-mode semantic`, `--max-results`, `--endpoint`, `--user-agent` |
| Search by category | `search-skills` | `--keyword`, `--category-code`, `--search-mode semantic`, `--max-results`, `--endpoint`, `--user-agent` |
| Search by intent | `search-skills` | `--keyword`, `--search-mode semantic`, `--max-results`, `--endpoint`, `--user-agent` |
| Combined search | `search-skills` | `--keyword`, `--category-code`, `--search-mode semantic`, `--max-results`, `--endpoint`, `--user-agent` |
| Get skill details | `get-skill-content` | `--skill-name`, `--endpoint`, `--user-agent` |
| Install plugin | `plugin install` | `--names` |
| Check credentials | `configure list` | None |

---

## Notes

- **Endpoint Required**: Every `aliyun agentexplorer` command MUST include `--endpoint 'agentexplorer.aliyuncs.com'`.
- **User-Agent Required (API only)**: Every `aliyun agentexplorer` command MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills`. Local management commands (`aliyun configure ...`, `aliyun plugin ...`, `aliyun version`) do **not** support `--user-agent`.
- **Plugin Mode**: Commands use plugin mode format (lowercase with hyphens)
- **Semantic Search**: `search-skills` must include `--search-mode semantic`. If `--search-mode` is not shown in command help, install or update the `agentexplorer` plugin.
- **Search Parameters**: Show `--max-results` explicitly when limiting page size.
