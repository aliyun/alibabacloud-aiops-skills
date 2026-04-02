# Verification Methods

This document provides detailed verification steps for each workflow in the `alibabacloud-find-skills` skill.

## Overview

After executing each workflow, verify success by checking:

1. Command exit code (0 = success)
2. Response structure matches expected format
3. Data content is valid and non-empty
4. Appropriate error handling for edge cases

---

## Workflow 1: Search Skills by Keyword

### Success Criteria

✅ **Command executes successfully**

```bash
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 20 \
  --user-agent AlibabaCloud-Agent-Skills
echo "Exit code: $?"  # Should be 0
```

✅ **Response contains expected fields**

```bash
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "skills[0].skillName" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return a valid skill name, not null
```

✅ **Skills array is not empty** (when results exist)

```bash
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --cli-query "length(skills)" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return a number > 0
```

✅ **Each skill has required fields**

- `skillName` — Non-empty string
- `displayName` — Non-empty string
- `description` — Non-empty string
- `categoryName` — Non-empty string
- `installCount` — Non-negative integer
- `likeCount` — Non-negative integer

### Verification Script

```bash
#!/bin/bash
KEYWORD="ECS"

echo "=== Verifying Search Skills by Keyword ==="

# Execute search
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "$KEYWORD" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Command executed successfully (exit code: $EXIT_CODE)"
else
  echo "❌ Command failed (exit code: $EXIT_CODE)"
  echo "$RESULT"
  exit 1
fi

# Check if result contains skills array
if echo "$RESULT" | grep -q '"skills"'; then
  echo "✅ Response contains 'skills' array"
else
  echo "❌ Response missing 'skills' array"
  exit 1
fi

# Check skill count
SKILL_COUNT=$(echo "$RESULT" | grep -o '"skillName"' | wc -l)
if [ $SKILL_COUNT -gt 0 ]; then
  echo "✅ Found $SKILL_COUNT skills"
else
  echo "⚠️  No skills found for keyword '$KEYWORD'"
fi

echo "=== Verification Complete ==="
```

---

## Workflow 2: Browse Skills by Category

### Success Criteria

✅ **List categories succeeds**

```bash
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills
echo "Exit code: $?"  # Should be 0
```

✅ **Categories structure is valid**

```bash
aliyun agentexplorer list-categories \
  --cli-query "categories[0].categoryCode" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return a valid category code
```

✅ **Search by category returns filtered results**

```bash
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --cli-query "skills[0].categoryCode" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return "computing"
```

### Verification Script

```bash
#!/bin/bash

echo "=== Verifying Browse Skills by Category ==="

# Step 1: List categories
echo "Step 1: Listing categories..."
CATEGORIES=$(aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ list-categories succeeded"
else
  echo "❌ list-categories failed"
  echo "$CATEGORIES"
  exit 1
fi

# Extract first category code
CATEGORY_CODE=$(echo "$CATEGORIES" | grep -o '"categoryCode":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$CATEGORY_CODE" ]; then
  echo "✅ Found category code: $CATEGORY_CODE"
else
  echo "❌ No category codes found"
  exit 1
fi

# Step 2: Search by category
echo "Step 2: Searching skills in category '$CATEGORY_CODE'..."
SKILLS=$(aliyun agentexplorer search-skills \
  --category-code "$CATEGORY_CODE" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ search-skills by category succeeded"
else
  echo "❌ search-skills by category failed"
  echo "$SKILLS"
  exit 1
fi

# Verify results belong to the category
if echo "$SKILLS" | grep -q "\"categoryCode\":\"$CATEGORY_CODE\""; then
  echo "✅ Results correctly filtered by category"
else
  echo "⚠️  Results may not be filtered correctly"
fi

echo "=== Verification Complete ==="
```

---

## Workflow 3: Get Skill Details

### Success Criteria

✅ **Command succeeds with valid skill name**

```bash
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --user-agent AlibabaCloud-Agent-Skills
echo "Exit code: $?"  # Should be 0
```

✅ **Response contains content field**

```bash
aliyun agentexplorer get-skill-content \
  --skill-name "alibabacloud-ecs-batch-command" \
  --cli-query "content" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return non-empty markdown content
```

✅ **Content is valid markdown**

- Starts with `---` (YAML frontmatter)
- Contains `name:` field
- Contains `description:` field

### Verification Script

```bash
#!/bin/bash

echo "=== Verifying Get Skill Details ==="

# First, search for a skill to get a valid skill name
echo "Step 1: Finding a valid skill name..."
SEARCH_RESULT=$(aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

SKILL_NAME=$(echo "$SEARCH_RESULT" | grep -o '"skillName":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$SKILL_NAME" ]; then
  echo "❌ Could not find a valid skill name"
  exit 1
fi

echo "✅ Found skill name: $SKILL_NAME"

# Step 2: Get skill content
echo "Step 2: Retrieving skill content..."
CONTENT=$(aliyun agentexplorer get-skill-content \
  --skill-name "$SKILL_NAME" \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ get-skill-content succeeded"
else
  echo "❌ get-skill-content failed"
  echo "$CONTENT"
  exit 1
fi

# Verify content field exists and is not empty
if echo "$CONTENT" | grep -q '"content"'; then
  echo "✅ Response contains 'content' field"
else
  echo "❌ Response missing 'content' field"
  exit 1
fi

# Extract content and check for markdown frontmatter
MARKDOWN_CONTENT=$(echo "$CONTENT" | grep -o '"content":"[^"]*"' | cut -d'"' -f4)

if echo "$MARKDOWN_CONTENT" | grep -q '---'; then
  echo "✅ Content appears to be valid markdown"
else
  echo "⚠️  Content may not be valid markdown"
fi

echo "=== Verification Complete ==="
```

---

## Workflow 4: Install a Skill

### Success Criteria

✅ **Installation command succeeds**

```bash
npx skills add https://github.com/aliyun/alibabacloud-aiops-skills --skill <skill-name>
echo "Exit code: $?"  # Should be 0
```

✅ **Skill appears in Claude Code skills list**

```bash
# Verify skill is installed (implementation-specific)
# Check in Claude Code UI or skills directory
```

### Verification Steps

1. **Before Installation**: Check that skill is not already installed
2. **During Installation**: Monitor output for errors
3. **After Installation**: Verify skill is available
4. **Test Skill**: Trigger the skill to ensure it works

### Manual Verification Checklist

- [ ] Installation command completed without errors
- [ ] Skill appears in Claude Code skills list
- [ ] Skill can be triggered with appropriate keywords
- [ ] Skill loads successfully when triggered
- [ ] Skill's functions work as expected

---

## Workflow 5: Combined Search (Keyword + Category)

### Success Criteria

✅ **Combined search executes successfully**

```bash
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database.rds" \
  --user-agent AlibabaCloud-Agent-Skills
echo "Exit code: $?"  # Should be 0
```

✅ **Results match both filters**

- Each result's `categoryCode` or `subCategoryCode` matches the filter
- Each result's `displayName` or `description` contains keyword (case-insensitive)

### Verification Script

```bash
#!/bin/bash

KEYWORD="backup"
CATEGORY="database"

echo "=== Verifying Combined Search ==="

# Execute combined search
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "$KEYWORD" \
  --category-code "$CATEGORY" \
  --max-results 10 \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ Combined search succeeded"
else
  echo "❌ Combined search failed"
  echo "$RESULT"
  exit 1
fi

# Check if results contain the category
if echo "$RESULT" | grep -q "\"categoryCode\":\"$CATEGORY\""; then
  echo "✅ Results correctly filtered by category '$CATEGORY'"
else
  echo "⚠️  No results with category '$CATEGORY' found"
fi

# Count results
SKILL_COUNT=$(echo "$RESULT" | grep -o '"skillName"' | wc -l)
echo "Found $SKILL_COUNT skills matching both filters"

echo "=== Verification Complete ==="
```

---

## Workflow 6: Paginated Search

### Success Criteria

✅ **First page returns results and nextToken**

```bash
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "monitoring" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills)

echo "$RESULT" | grep -q '"nextToken"'
# Should find nextToken if more results exist
```

✅ **Second page uses nextToken correctly**

```bash
NEXT_TOKEN=$(echo "$RESULT" | grep -o '"nextToken":"[^"]*"' | cut -d'"' -f4)

aliyun agentexplorer search-skills \
  --keyword "monitoring" \
  --max-results 5 \
  --next-token "$NEXT_TOKEN" \
  --user-agent AlibabaCloud-Agent-Skills
# Should return different results
```

✅ **No duplicate results across pages**

### Verification Script

```bash
#!/bin/bash

KEYWORD="ECS"
PAGE_SIZE=5

echo "=== Verifying Paginated Search ==="

# Page 1
echo "Fetching page 1..."
PAGE1=$(aliyun agentexplorer search-skills \
  --keyword "$KEYWORD" \
  --max-results $PAGE_SIZE \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -ne 0 ]; then
  echo "❌ Page 1 fetch failed"
  exit 1
fi

echo "✅ Page 1 fetched successfully"

# Extract nextToken
NEXT_TOKEN=$(echo "$PAGE1" | grep -o '"nextToken":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$NEXT_TOKEN" ]; then
  echo "⚠️  No nextToken found (may be last page)"
  echo "=== Verification Complete ==="
  exit 0
fi

echo "✅ Found nextToken: ${NEXT_TOKEN:0:20}..."

# Page 2
echo "Fetching page 2..."
PAGE2=$(aliyun agentexplorer search-skills \
  --keyword "$KEYWORD" \
  --max-results $PAGE_SIZE \
  --next-token "$NEXT_TOKEN" \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ Page 2 fetched successfully"
else
  echo "❌ Page 2 fetch failed"
  exit 1
fi

# Check for different skill names
SKILLS_PAGE1=$(echo "$PAGE1" | grep -o '"skillName":"[^"]*"' | cut -d'"' -f4 | sort)
SKILLS_PAGE2=$(echo "$PAGE2" | grep -o '"skillName":"[^"]*"' | cut -d'"' -f4 | sort)

if [ "$SKILLS_PAGE1" != "$SKILLS_PAGE2" ]; then
  echo "✅ Page 2 contains different results from page 1"
else
  echo "⚠️  Pages may contain duplicate results"
fi

echo "=== Verification Complete ==="
```

---

## General Verification Checklist

Use this checklist after implementing any workflow:

### Command Execution

- [ ] Command exits with code 0 on success
- [ ] Command exits with non-zero code on error
- [ ] Error messages are clear and actionable

### Response Format

- [ ] Response is valid JSON
- [ ] Response contains expected top-level keys
- [ ] All required fields are present
- [ ] Field types match expected types (string, int, array, etc.)

### Data Validity

- [ ] String fields are non-empty when expected
- [ ] Numeric fields are non-negative
- [ ] Array fields contain valid elements
- [ ] Nested objects have correct structure

### Edge Cases

- [ ] Empty results handled gracefully (no error)
- [ ] Invalid parameters return appropriate errors
- [ ] Missing required parameters return clear error messages
- [ ] Pagination works correctly at boundaries

### User Experience

- [ ] Results are displayed in user-friendly format
- [ ] Tables align properly
- [ ] Important information is highlighted
- [ ] Next steps are clear to the user

---

## Automated Test Suite

Create a comprehensive test script:

```bash
#!/bin/bash

# Test suite for alibabacloud-find-skills

set -e  # Exit on first error

echo "========================================"
echo "  alibabacloud-find-skills Test Suite"
echo "========================================"

# Test 1: List Categories
echo -e "\n[Test 1] List Categories"
aliyun agentexplorer list-categories \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "categories[0].categoryCode" > /dev/null
echo "✅ PASS"

# Test 2: Search by Keyword
echo -e "\n[Test 2] Search by Keyword"
aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "skills[0].skillName" > /dev/null
echo "✅ PASS"

# Test 3: Search by Category
echo -e "\n[Test 3] Search by Category"
aliyun agentexplorer search-skills \
  --category-code "computing" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "skills[0].categoryCode" > /dev/null
echo "✅ PASS"

# Test 4: Combined Search
echo -e "\n[Test 4] Combined Search"
aliyun agentexplorer search-skills \
  --keyword "backup" \
  --category-code "database" \
  --max-results 5 \
  --user-agent AlibabaCloud-Agent-Skills > /dev/null
echo "✅ PASS"

# Test 5: Get Skill Content
echo -e "\n[Test 5] Get Skill Content"
SKILL_NAME=$(aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 1 \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "skills[0].skillName" 2>/dev/null | tr -d '"' | tr -d '\n')

if [ -n "$SKILL_NAME" ]; then
  aliyun agentexplorer get-skill-content \
    --skill-name "$SKILL_NAME" \
    --user-agent AlibabaCloud-Agent-Skills \
    --cli-query "content" > /dev/null
  echo "✅ PASS"
else
  echo "⚠️  SKIP (no skills found)"
fi

# Test 6: Pagination
echo -e "\n[Test 6] Pagination"
RESULT=$(aliyun agentexplorer search-skills \
  --keyword "ECS" \
  --max-results 2 \
  --user-agent AlibabaCloud-Agent-Skills 2>/dev/null)

if echo "$RESULT" | grep -q '"nextToken"'; then
  echo "✅ PASS"
else
  echo "⚠️  SKIP (no pagination needed)"
fi

echo -e "\n========================================"
echo "  All Tests Completed Successfully!"
echo "========================================"
```

Save as `test-skill.sh` and run with:

```bash
chmod +x test-skill.sh
./test-skill.sh
```

---

## Troubleshooting Verification Failures

### Issue: Command returns non-zero exit code

**Check**:

1. Credentials configured: `aliyun configure list --user-agent AlibabaCloud-Agent-Skills`
2. Plugin installed: `aliyun plugin list | grep agentexplorer`
3. CLI version: `aliyun version` (should be >= 3.3.1)
4. Network connectivity: `ping api.aliyun.com`

### Issue: Response missing expected fields

**Check**:

1. CLI version is up-to-date
2. Plugin version is latest: `aliyun plugin list`
3. API version changes (check official docs)

### Issue: No results returned

**Check**:

1. Keyword spelling
2. Category code validity
3. Try broader search terms
4. Check if any skills exist in category

---

## Success Metrics

Track these metrics to assess skill effectiveness:

| Metric                    | Target      | Measurement                              |
| ------------------------- | ----------- | ---------------------------------------- |
| Command success rate      | > 99%       | Exit code 0 / total commands             |
| Average response time     | < 3 seconds | Time to receive response                 |
| Empty results rate        | < 20%       | Searches with 0 results / total searches |
| Installation success rate | > 95%       | Successful installs / install attempts   |
| User satisfaction         | > 4/5       | User feedback rating                     |

---

## Continuous Monitoring

Set up periodic checks:

```bash
# Cron job example (run daily at 2 AM)
0 2 * * * /path/to/test-skill.sh >> /var/log/skill-tests.log 2>&1
```

Monitor for:

- API availability
- Response time degradation
- New error patterns
- Skill catalog updates
