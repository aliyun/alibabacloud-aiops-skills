# Related CLI Commands

Complete reference for all Aliyun CLI commands used in the `alibabacloud-find-skills` skill.

## Command Summary

| Command | Purpose | Required Parameters |
|---------|---------|---------------------|
| `aliyun agentexplorer list-categories` | List all skill categories | None |
| `aliyun agentexplorer search-skills` | Search for skills | None (keyword or category-code recommended) |
| `aliyun agentexplorer get-skill-content` | Get skill details | `--skill-name` (required) |
| `aliyun plugin install` | Install CLI plugins | `--names` (required) |
| `aliyun configure list` | Check credential configuration | None |
| `aliyun version` | Check CLI version | None |

---

## 1. aliyun agentexplorer list-categories

**Description**: List all available skill categories and subcategories.

**Syntax**:
```bash
aliyun agentexplorer list-categories [flags]
```

**Parameters**: None required.

**Common Flags**:
- `--user-agent AlibabaCloud-Agent-Skills` — **Required**: Identify requests from this skill
- `--cli-query <jmespath>` — Filter output using JMESPath expression
- `-q, --quiet` — Suppress output

**Example Usage**:
```bash
# List all categories
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills

# List categories with JMESPath filtering
aliyun agentexplorer list-categories \
  --cli-query "categories[].categoryName" \
  --user-agent AlibabaCloud-Agent-Skills
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

## 2. aliyun agentexplorer search-skills

**Description**: Search for Alibaba Cloud Agent Skills by keyword, category, or both.

**Syntax**:
```bash
aliyun agentexplorer search-skills [flags]
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--keyword` | string | No | Search keyword (product name, feature, description) |
| `--category-code` | string | No | Category code filter (comma-separated for multiple) |
| `--max-results` | int | No | Maximum results per page (1-100, default: 20) |
| `--next-token` | string | No | Pagination token from previous response |
| `--skip` | int | No | Number of items to skip |

**Common Flags**:
- `--user-agent AlibabaCloud-Agent-Skills` — **Required**: Identify requests from this skill
- `--cli-query <jmespath>` — Filter output using JMESPath expression
- `--pager` — Auto-merge all pages
- `-q, --quiet` — Suppress output

**Example Usage**:

```bash
# Search by keyword only
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --user-agent AlibabaCloud-Agent-Skills

# Search by category only
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills

# Search by subcategory (dot notation)
aliyun agentexplorer search-skills \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills

# Combined keyword and category
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database.rds" \
  --max-results 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Multiple categories
aliyun agentexplorer search-skills \
  --category-code "computing,database" \
  --user-agent AlibabaCloud-Agent-Skills

# Paginated search (page 2)
aliyun agentexplorer search-skills \
  --keyword "monitoring" \
  --max-results 20 \
  --next-token "<token-from-previous-response>" \
  --user-agent AlibabaCloud-Agent-Skills

# Skip first N results
aliyun agentexplorer search-skills \
  --keyword "OSS" \
  --skip 10 \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills

# Filter results with JMESPath
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[].skillName" \
  --user-agent AlibabaCloud-Agent-Skills
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
- `--user-agent AlibabaCloud-Agent-Skills` — **Required**: Identify requests from this skill
- `--cli-query <jmespath>` — Filter output using JMESPath expression
- `-q, --quiet` — Suppress output

**Example Usage**:

```bash
# Get skill content
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --user-agent AlibabaCloud-Agent-Skills

# Get only the description field
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --cli-query "description" \
  --user-agent AlibabaCloud-Agent-Skills
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
# Install agentexplorer plugin
aliyun plugin install --names aliyun-cli-agentexplorer

# Install multiple plugins (comma-separated)
aliyun plugin install --names aliyun-cli-agentexplorer,aliyun-cli-another-plugin
```

---

## 5. aliyun configure list

**Description**: List all configured credentials and profiles.

**Syntax**:
```bash
aliyun configure list [flags]
```

**Parameters**: None required.

**Common Flags**:
- `--user-agent AlibabaCloud-Agent-Skills` — **Required**: Identify requests from this skill

**Example Usage**:

```bash
# List all profiles
aliyun configure list --user-agent AlibabaCloud-Agent-Skills
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

**Description**: Configure CLI settings (used for enabling auto plugin install).

**Syntax**:
```bash
aliyun configure set [flags]
```

**Common Flags**:
- `--auto-plugin-install <bool>` — Enable/disable automatic plugin installation

**Example Usage**:

```bash
# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true
```

---

## Advanced Usage Patterns

### Pattern 1: Search with Auto-pagination

```bash
# Automatically fetch all pages
aliyun agentexplorer search-skills \
  --keyword "monitoring" \
  --pager \
  --user-agent AlibabaCloud-Agent-Skills
```

### Pattern 2: Filter Output with JMESPath

```bash
# Get only skill names from search results
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[].skillName" \
  --user-agent AlibabaCloud-Agent-Skills

# Get skills with install count > 100
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[?installCount > \`100\`]" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Pattern 3: Hierarchical Category Search

```bash
# Search all computing skills
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills

# Search only ECS skills (computing.ecs)
aliyun agentexplorer search-skills \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Pattern 4: Multi-category Search

```bash
# Search across multiple top-level categories
aliyun agentexplorer search-skills \
  --category-code "computing,database,storage" \
  --user-agent AlibabaCloud-Agent-Skills

# Search across multiple subcategories
aliyun agentexplorer search-skills \
  --category-code "computing.ecs,database.rds,storage.oss" \
  --user-agent AlibabaCloud-Agent-Skills
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
# Check if credentials are configured
aliyun configure list --user-agent AlibabaCloud-Agent-Skills

# Test API access
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills
```

### Debug Mode

```bash
# Enable debug logging
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --log-level DEBUG \
  --user-agent AlibabaCloud-Agent-Skills
```

### Dry Run Mode

```bash
# Preview request without sending
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-dry-run \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Command Comparison Table

| Task | Command | Key Parameters |
|------|---------|----------------|
| Browse all categories | `list-categories` | None |
| Search by keyword | `search-skills` | `--keyword` |
| Search by category | `search-skills` | `--category-code` |
| Combined search | `search-skills` | `--keyword`, `--category-code` |
| Get skill details | `get-skill-content` | `--skill-name` |
| Paginate results | `search-skills` | `--max-results`, `--next-token` |
| Install plugin | `plugin install` | `--names` |
| Check credentials | `configure list` | None |

---

## Notes

- **User-Agent Required**: All `aliyun agentexplorer` commands MUST include `--user-agent AlibabaCloud-Agent-Skills`
- **Plugin Mode**: Commands use plugin mode format (lowercase with hyphens)
- **Pagination**: Use `--next-token` from response for subsequent pages
- **Category Codes**: Use dot notation for subcategories (e.g., `computing.ecs`)
- **Multiple Values**: Comma-separate for multiple category codes
- **JMESPath**: Use `--cli-query` for client-side filtering
