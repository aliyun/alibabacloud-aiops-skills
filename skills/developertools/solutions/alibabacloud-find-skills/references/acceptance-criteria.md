# Acceptance Criteria: alibabacloud-find-skills

**Skill Name**: `alibabacloud-find-skills`
**Purpose**: Validate correct CLI command patterns and ensure skill implementation follows best practices

---

## Prerequisites Validation

### 1. Aliyun CLI Version

#### ✅ CORRECT

```bash
# CLI version check returns >= 3.3.1
aliyun version
# Output: 3.3.2 (or higher)
```

#### ❌ INCORRECT

```bash
# Version too old (< 3.3.1)
aliyun version
# Output: 3.0.0
```

**Why**: This skill requires CLI version >= 3.3.1 for plugin support and modern command features.

---

### 2. Plugin Installation

#### ✅ CORRECT

```bash
# Install agentexplorer plugin
aliyun plugin install --names aliyun-cli-agentexplorer

# Verify installation
aliyun plugin list | grep agentexplorer
```

#### ❌ INCORRECT

```bash
# Incorrect plugin name
aliyun plugin install --names agentexplorer

# Wrong command
aliyun install plugin agentexplorer
```

**Why**: The plugin name must be exact: `aliyun-cli-agentexplorer`. CLI uses `plugin install --names` subcommand.

---

## CLI Command Patterns

### 1. Product Name Verification

#### ✅ CORRECT

```bash
# Correct product name
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills
aliyun agentexplorer search-skills --user-agent AlibabaCloud-Agent-Skills
aliyun agentexplorer get-skill-content --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Wrong product name
aliyun agent-explorer list-categories
aliyun skillexplorer search-skills
aliyun explorerAgent get-skill-content
```

**Why**: The product name is `agentexplorer` (no hyphens, no capitalization).

---

### 2. Command/Action Names

#### ✅ CORRECT

```bash
# Correct command names (lowercase with hyphens)
aliyun agentexplorer list-categories
aliyun agentexplorer search-skills
aliyun agentexplorer get-skill-content
```

#### ❌ INCORRECT

```bash
# Wrong command format (camelCase or incorrect names)
aliyun agentexplorer listCategories
aliyun agentexplorer SearchSkills
aliyun agentexplorer getSkillContent
aliyun agentexplorer list_categories
```

**Why**: Plugin mode uses lowercase with hyphens, NOT camelCase or underscores.

---

### 3. Parameter Names

#### ✅ CORRECT

```bash
# Correct parameter names
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --category-code "computing" \
  --max-results 20 \
  --next-token "abc123" \
  --skip 10 \
  --user-agent AlibabaCloud-Agent-Skills

aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Wrong parameter names
aliyun agentexplorer search-skills --keywords "ECS"  # plural
aliyun agentexplorer search-skills --category "computing"  # missing -code
aliyun agentexplorer search-skills --max-result 20  # singular
aliyun agentexplorer search-skills --nextToken "abc"  # camelCase
aliyun agentexplorer get-skill-content --skillName "name"  # camelCase
aliyun agentexplorer get-skill-content --name "name"  # wrong parameter
```

**Why**: Parameter names must match exactly as defined in `--help` output.

---

### 4. User-Agent Flag (CRITICAL)

#### ✅ CORRECT

```bash
# Every agentexplorer command MUST include user-agent
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills

aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --user-agent AlibabaCloud-Agent-Skills

aliyun agentexplorer get-skill-content \
  --skill-name "example" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Missing user-agent flag
aliyun agentexplorer list-categories

aliyun agentexplorer search-skills --keyword "ECS"

# Wrong user-agent value
aliyun agentexplorer list-categories --user-agent "MyAgent"
```

**Why**: All commands MUST include `--user-agent AlibabaCloud-Agent-Skills` for tracking and compliance.

---

### 5. Required Parameters

#### ✅ CORRECT

```bash
# get-skill-content requires --skill-name
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch" \
  --user-agent AlibabaCloud-Agent-Skills

# search-skills works with no required parameters (but keyword or category recommended)
aliyun agentexplorer search-skills \
  --user-agent AlibabaCloud-Agent-Skills

# list-categories has no required parameters
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Missing required parameter
aliyun agentexplorer get-skill-content \
  --user-agent AlibabaCloud-Agent-Skills
# ERROR: --skill-name is required
```

**Why**: `--skill-name` is mandatory for `get-skill-content`. Other commands have no required params beyond user-agent.

---

## Parameter Value Patterns

### 1. Category Code Format

#### ✅ CORRECT

```bash
# Top-level category
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills

# Subcategory (dot notation)
aliyun agentexplorer search-skills \
  --category-code "computing.ecs" \
  --user-agent AlibabaCloud-Agent-Skills

# Multiple categories (comma-separated)
aliyun agentexplorer search-skills \
  --category-code "computing,database,storage" \
  --user-agent AlibabaCloud-Agent-Skills

# Mixed levels
aliyun agentexplorer search-skills \
  --category-code "computing.ecs,database" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Wrong separator for multiple categories
aliyun agentexplorer search-skills --category-code "computing database"
aliyun agentexplorer search-skills --category-code "computing;database"

# Wrong subcategory format
aliyun agentexplorer search-skills --category-code "computing/ecs"
aliyun agentexplorer search-skills --category-code "computing:ecs"

# Invalid category codes
aliyun agentexplorer search-skills --category-code "invalid-category"
```

**Why**: Use dot notation for subcategories (e.g., `category.subcategory`), comma-separated for multiple.

---

### 2. Max Results Range

#### ✅ CORRECT

```bash
# Valid range: 1-100
aliyun agentexplorer search-skills \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills

aliyun agentexplorer search-skills \
  --max-results 50 \
  --user-agent AlibabaCloud-Agent-Skills

aliyun agentexplorer search-skills \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills

# Default (omit parameter)
aliyun agentexplorer search-skills \
  --user-agent AlibabaCloud-Agent-Skills
# Uses default: 20
```

#### ❌ INCORRECT

```bash
# Out of range
aliyun agentexplorer search-skills --max-results 0
aliyun agentexplorer search-skills --max-results 101
aliyun agentexplorer search-skills --max-results 1000

# Invalid type
aliyun agentexplorer search-skills --max-results "twenty"
```

**Why**: `--max-results` must be an integer between 1 and 100 (inclusive).

---

### 3. Keyword Format

#### ✅ CORRECT

```bash
# Single word
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --user-agent AlibabaCloud-Agent-Skills

# Multiple words (quoted)
aliyun agentexplorer search-skills \
  --keyword "batch command" \
  --user-agent AlibabaCloud-Agent-Skills

# Chinese characters
aliyun agentexplorer search-skills \
  --keyword "云服务器" \
  --user-agent AlibabaCloud-Agent-Skills

# Mixed English and Chinese
aliyun agentexplorer search-skills \
  --keyword "ECS实例管理" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Unquoted multi-word (may cause parsing errors)
aliyun agentexplorer search-skills --keyword batch command

# Special characters without quotes
aliyun agentexplorer search-skills --keyword ECS&RDS
```

**Why**: Multi-word keywords must be quoted. Special characters may need quoting or escaping.

---

### 4. Next Token Usage

#### ✅ CORRECT

```bash
# First page (no token)
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills)

# Extract nextToken from response
NEXT_TOKEN=$(echo "$RESULT" | jq -r '.nextToken')

# Second page (with token)
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 20 \
  --next-token "$NEXT_TOKEN" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Manually crafted token
aliyun agentexplorer search-skills \
  --next-token "page2" \
  --user-agent AlibabaCloud-Agent-Skills

# Modified token
aliyun agentexplorer search-skills \
  --next-token "${NEXT_TOKEN}_modified" \
  --user-agent AlibabaCloud-Agent-Skills

# Using skip instead of next-token for pagination
aliyun agentexplorer search-skills \
  --skip 20 \
  --user-agent AlibabaCloud-Agent-Skills
# Note: --skip is valid but --next-token is preferred for pagination
```

**Why**: `nextToken` must be used exactly as returned by the API, without modification.

---

## Authentication Patterns

### 1. Credential Verification

#### ✅ CORRECT

```bash
# Check credentials before operations
aliyun configure list --user-agent AlibabaCloud-Agent-Skills

# Never read/print credentials
# NEVER do: echo $ALIBABA_CLOUD_ACCESS_KEY_ID
# NEVER do: aliyun configure get --key access_key_id
```

#### ❌ INCORRECT

```bash
# Reading credentials
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET

# Printing credentials
aliyun configure get --key access_key_id

# Asking user to input credentials in conversation
# "Please provide your Access Key ID"
```

**Why**: Credentials must NEVER be read, printed, or requested directly for security reasons.

---

### 2. Configuration Check

#### ✅ CORRECT

```bash
# Use configure list to check status
aliyun configure list --user-agent AlibabaCloud-Agent-Skills

# Check if output shows valid profile
# Example valid output:
# Profile   | Credential         | Valid   | Region
# --------- | ------------------ | ------- | --------
# default * | AK:***abc          | Valid   | cn-hangzhou
```

#### ❌ INCORRECT

```bash
# Don't test credentials by making API calls
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills
# (Use this for functionality, not credential verification)
```

**Why**: Use `configure list` specifically for credential validation before operations.

---

## Output Handling Patterns

### 1. JMESPath Filtering

#### ✅ CORRECT

```bash
# Filter for specific fields
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[].skillName" \
  --user-agent AlibabaCloud-Agent-Skills

# Filter with conditions
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[?installCount > \`100\`]" \
  --user-agent AlibabaCloud-Agent-Skills

# Select first item
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[0]" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT

```bash
# Invalid JMESPath syntax
aliyun agentexplorer search-skills --cli-query "skills.skillName"  # Missing []
aliyun agentexplorer search-skills --cli-query "skills[skillName]"  # Wrong syntax
```

**Why**: JMESPath syntax must be valid. Arrays require `[]`, conditions use `?`, literals use backticks.

---

### 2. Result Display

#### ✅ CORRECT

```markdown
# Display results in table format

| Skill Name             | Display Name  | Category  | Install Count |
| ---------------------- | ------------- | --------- | ------------- |
| alibabacloud-ecs-batch | ECS Batch Ops | Computing | 245           |

# Show key fields

- **Skill Name**: alibabacloud-ecs-batch
- **Description**: Batch manage ECS instances
- **Category**: Computing > ECS
```

#### ❌ INCORRECT

```bash
# Dumping raw JSON
echo "$RESULT"

# No formatting
echo "$RESULT" | jq
```

**Why**: Users need human-readable, formatted output with relevant fields highlighted.

---

## Error Handling Patterns

### 1. Missing Plugin

#### ✅ CORRECT

```bash
# Check plugin before use
if ! aliyun plugin list | grep -q "agentexplorer"; then
  echo "Installing agentexplorer plugin..."
  aliyun plugin install --names aliyun-cli-agentexplorer
fi
```

#### ❌ INCORRECT

```bash
# Assume plugin is installed
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills
# May fail if plugin not installed
```

**Why**: Verify prerequisites before execution to provide helpful error messages.

---

### 2. No Results Handling

#### ✅ CORRECT

```bash
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "nonexistent" \
  --user-agent AlibabaCloud-Agent-Skills)

# Check if skills array is empty
if echo "$RESULT" | jq -e '.skills | length == 0' > /dev/null; then
  echo "No skills found for keyword 'nonexistent'"
  echo "Try: broader keywords, different category, or list all categories"
fi
```

#### ❌ INCORRECT

```bash
# Don't treat empty results as error
RESULT=$(aliyun agentexplorer search-skills --keyword "nonexistent" --user-agent AlibabaCloud-Agent-Skills)
if [ $? -ne 0 ]; then
  echo "Search failed"  # Wrong: empty results return exit code 0
fi
```

**Why**: Empty results are valid responses (exit code 0), not errors.

---

## Workflow Patterns

### 1. Search-Detail-Install Flow

#### ✅ CORRECT

```bash
# Step 1: Search
SEARCH_RESULT=$(aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --user-agent AlibabaCloud-Agent-Skills)

# Step 2: Display results to user, get confirmation
echo "Found skills: ..."
# [User selects: alibabacloud-ecs-batch]

# Step 3: Get details
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch" \
  --user-agent AlibabaCloud-Agent-Skills

# Step 4: User confirms installation
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills --skill alibabacloud-ecs-batch
```

#### ❌ INCORRECT

```bash
# Skip presenting results to user
SKILL=$(aliyun agentexplorer search-skills --keyword "ECS" --cli-query "skills[0].skillName" --user-agent AlibabaCloud-Agent-Skills)
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills --skill "$SKILL"
# Wrong: Should present search results and skill details to user before installing
```

**Why**: Always present search results and skill details to the user before executing installation.

---

## Common Anti-Patterns

### ❌ ANTI-PATTERN 1: Arbitrary Hardcoded Values

```bash
# DON'T use keywords unrelated to the user's request
# e.g., User asks about databases but Agent searches for "ECS"
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --category-code "computing" \
  --user-agent AlibabaCloud-Agent-Skills
```

**✅ CORRECT**: Derive keyword and category from the user's intent.

---

### ❌ ANTI-PATTERN 2: Missing Error Handling

```bash
# DON'T ignore errors
aliyun agentexplorer search-skills --keyword "test" --user-agent AlibabaCloud-Agent-Skills
# Continue regardless of result
```

**✅ CORRECT**: Check exit codes and handle errors.

---

### ❌ ANTI-PATTERN 3: Credential Exposure

```bash
# DON'T print or request credentials
echo "Your AK: $ALIBABA_CLOUD_ACCESS_KEY_ID"
```

**✅ CORRECT**: Use `configure list` to check status only.

---

## Testing Checklist

Before completing the skill, verify:

- [ ] All commands use correct product name: `agentexplorer`
- [ ] All commands use lowercase-with-hyphens format
- [ ] All parameters match `--help` output exactly
- [ ] Every command includes `--user-agent AlibabaCloud-Agent-Skills`
- [ ] Required parameters are always provided
- [ ] Category codes use dot notation for subcategories
- [ ] Pagination uses exact `nextToken` from response
- [ ] Credentials are never read/printed
- [ ] User confirmation required before actions
- [ ] Empty results handled gracefully
- [ ] Errors provide actionable guidance
- [ ] Output formatted for readability

---

## Verification Commands

Run these commands to validate the skill:

```bash
# Test 1: List categories
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills

# Test 2: Search by keyword
aliyun agentexplorer search-skills --keyword "ECS" --user-agent AlibabaCloud-Agent-Skills

# Test 3: Search by category
aliyun agentexplorer search-skills --category-code "computing" --user-agent AlibabaCloud-Agent-Skills

# Test 4: Get skill content
aliyun agentexplorer get-skill-content --skill-name "example-skill" --user-agent AlibabaCloud-Agent-Skills

# Test 5: Check credentials
aliyun configure list --user-agent AlibabaCloud-Agent-Skills
```

All commands should execute without syntax errors (though some may return "no results" or "skill not found", which is acceptable).
