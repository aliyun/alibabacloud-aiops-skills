# Acceptance Criteria: pai-featurestore-featuredb-usage-query

**Scenario**: PAI-FeatureStore FeatureDB Usage Query and Analysis
**Purpose**: Skill testing acceptance criteria to ensure correct CLI command patterns and execution

---

## Correct CLI Command Patterns

### 1. Product Name Verification

The product name for PAI-FeatureStore CLI is `paifeaturestore` (all lowercase, no hyphens).

#### ✅ CORRECT
```bash
aliyun paifeaturestore list-instances
aliyun paifeaturestore list-datasources
aliyun paifeaturestore get-datasource
aliyun paifeaturestore list-datasource-feature-views
```

#### ❌ INCORRECT
```bash
aliyun pai-featurestore list-instances     # Wrong: has hyphen
aliyun PAIFeatureStore list-instances       # Wrong: case sensitive
aliyun pai_featurestore list-instances      # Wrong: has underscore
aliyun featurestore list-instances          # Wrong: missing 'pai' prefix
```

---

### 2. Action/Command Verification

All actions use lowercase words connected with hyphens (plugin mode format).

#### ✅ CORRECT
```bash
aliyun paifeaturestore list-instances
aliyun paifeaturestore get-datasource
aliyun paifeaturestore list-datasources
aliyun paifeaturestore list-datasource-feature-views
```

#### ❌ INCORRECT
```bash
aliyun paifeaturestore ListInstances              # Wrong: uses API format (PascalCase)
aliyun paifeaturestore GetDatasource              # Wrong: uses API format
aliyun paifeaturestore listInstances              # Wrong: camelCase
aliyun paifeaturestore list_datasources           # Wrong: uses underscores
```

**Note**: The CLI plugin mode uses kebab-case (lowercase-with-hyphens), NOT the API PascalCase format.

---

### 3. Parameter Name Verification

All parameter names use lowercase words connected with hyphens, prefixed with `--`.

#### ✅ CORRECT - Common Parameters
```bash
--region cn-beijing
--instance-id fs-cn-beijing-12345
--datasource-id ds-12345
--workspace-id ws-12345
--start-date 2024-03-01
--end-date 2024-03-31
--page-number 1
--page-size 10
--sort-by ReadCount
--order DESC
--user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Boolean Parameters
```bash
--verbose true
--verbose false
--show-storage-usage true
--show-storage-usage false
--all true
```

#### ❌ INCORRECT - Parameter Names
```bash
--RegionId cn-beijing                    # Wrong: uses PascalCase
--InstanceId fs-12345                    # Wrong: uses PascalCase
--instanceId fs-12345                    # Wrong: uses camelCase
--instance_id fs-12345                   # Wrong: uses snake_case
--StartDate 2024-03-01                   # Wrong: uses PascalCase
--pageNumber 1                           # Wrong: uses camelCase
--user_agent AlibabaCloud-Agent-Skills   # Wrong: uses snake_case
```

#### ❌ INCORRECT - Boolean Parameters
```bash
--verbose=true                           # Wrong: uses = instead of space
--verbose                                # Wrong: missing value for boolean flag
--verbose True                           # Wrong: capital T (should be lowercase)
--show-storage-usage 1                   # Wrong: should be true/false, not 1/0
```

---

### 4. Required User-Agent Flag

**EVERY** `aliyun` CLI command in this skill MUST include the `--user-agent` flag with value `AlibabaCloud-Agent-Skills`.

#### ✅ CORRECT
```bash
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills

aliyun paifeaturestore list-datasources \
  --region cn-beijing \
  --instance-id fs-12345 \
  --type FeatureDB \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Missing --user-agent flag
aliyun paifeaturestore list-instances \
  --region cn-beijing

# Wrong user-agent value
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent MyAgent

# User-agent in wrong format
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent=AlibabaCloud-Agent-Skills    # Wrong: uses = instead of space
```

---

### 5. Date Format Verification

All date parameters must use `yyyy-MM-dd` format.

#### ✅ CORRECT
```bash
--start-date 2024-03-01
--end-date 2024-03-31
--start-date 2024-01-15
--end-date 2024-01-15      # Same date is valid for single-day query
```

#### ❌ INCORRECT
```bash
--start-date 2024/03/01    # Wrong: uses / separator
--start-date 03-01-2024    # Wrong: wrong order (MM-dd-yyyy)
--start-date 2024-3-1      # Wrong: missing leading zeros
--start-date 20240301      # Wrong: no separators
--start-date "Mar 1, 2024" # Wrong: text format
```

---

### 6. Region ID Verification

Region IDs must be valid Alibaba Cloud region identifiers.

#### ✅ CORRECT - Supported Regions
```bash
--region cn-beijing
--region cn-hangzhou
--region cn-shanghai
--region cn-shenzhen
--region cn-hongkong
--region ap-southeast-1
--region ap-southeast-5
--region us-west-1
--region eu-central-1
```

#### ❌ INCORRECT
```bash
--region beijing           # Wrong: missing 'cn-' prefix
--region CN-BEIJING        # Wrong: must be lowercase
--region cn_beijing        # Wrong: uses underscore instead of hyphen
--region singapore         # Wrong: should be ap-southeast-1
--region us-east-1         # Wrong: not a supported region for this skill
```

---

### 7. Enum Parameter Verification

Some parameters accept only specific enumerated values.

#### ✅ CORRECT - Status Parameter
```bash
--status Running
--status Initializing
--status Failure
```

#### ✅ CORRECT - Type Parameter
```bash
--type FeatureDB
--type Hologres
--type MaxCompute
--type TableStore
```

#### ✅ CORRECT - Sort Order
```bash
--order ASC
--order DESC
```

#### ✅ CORRECT - Sort By
```bash
--sort-by ReadCount
--sort-by WriteCount
--sort-by GmtCreateTime
--sort-by GmtModifiedTime
```

#### ❌ INCORRECT - Enum Values
```bash
--status running           # Wrong: must be PascalCase
--status RUNNING           # Wrong: all caps not accepted
--type featuredb           # Wrong: must be PascalCase
--type feature-db          # Wrong: no hyphens in type name
--order asc                # Wrong: must be uppercase
--order Ascending          # Wrong: must use ASC
--sort-by readCount        # Wrong: must be PascalCase
--sort-by read-count       # Wrong: no hyphens
```

---

### 8. Pagination Parameters

Pagination parameters must be positive integers.

#### ✅ CORRECT
```bash
--page-number 1
--page-size 10
--page-number 2
--page-size 50
```

#### ❌ INCORRECT
```bash
--page-number 0            # Wrong: must be >= 1
--page-number -1           # Wrong: must be positive
--page-size 0              # Wrong: must be >= 1
--page-number "1"          # Wrong: quoted (though CLI may accept)
```

---

### 9. Complete Command Examples

#### ✅ CORRECT - List Instances
```bash
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --status Running \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - List Datasources
```bash
aliyun paifeaturestore list-datasources \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --type FeatureDB \
  --workspace-id ws-12345 \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Get Datasource
```bash
aliyun paifeaturestore get-datasource \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --datasource-id ds-12345 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Query Total Usage
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --datasource-id ds-12345 \
  --start-date 2024-03-01 \
  --end-date 2024-03-31 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Query Per-Feature-View Usage
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --datasource-id ds-12345 \
  --start-date 2024-03-07 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --sort-by ReadCount \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Query Project Usage
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --datasource-id ds-12345 \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --project-name recommendation_system \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ✅ CORRECT - Query Feature View Trend
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region cn-beijing \
  --instance-id fs-cn-beijing-12345 \
  --datasource-id ds-12345 \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --project-name recommendation_system \
  --name user_features \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Correct Response Handling

### 1. JSON Response Parsing

All CLI responses return JSON that should be parsed with `jq` or similar tools.

#### ✅ CORRECT
```bash
# Parse response with jq
RESPONSE=$(aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills)

INSTANCE_ID=$(echo "$RESPONSE" | jq -r '.Instances[0].InstanceId')
TOTAL_COUNT=$(echo "$RESPONSE" | jq -r '.TotalCount')
```

#### ❌ INCORRECT
```bash
# Trying to parse JSON with grep/awk (fragile)
INSTANCE_ID=$(aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills | grep -o '"InstanceId":"[^"]*"' | cut -d'"' -f4)
```

---

### 2. Error Handling

Check command exit codes and response structure.

#### ✅ CORRECT
```bash
RESPONSE=$(aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills 2>&1)

if [ $? -ne 0 ]; then
  echo "Error: Command failed"
  echo "$RESPONSE"
  exit 1
fi

# Check if response has expected fields
if ! echo "$RESPONSE" | jq -e '.Instances' > /dev/null 2>&1; then
  echo "Error: Invalid response structure"
  exit 1
fi
```

#### ❌ INCORRECT
```bash
# Not checking exit code
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --user-agent AlibabaCloud-Agent-Skills > response.json

# Assuming command always succeeds
INSTANCE_ID=$(jq -r '.Instances[0].InstanceId' response.json)
```

---

## Correct Cost Calculation

### 1. Pricing Tier Selection

#### ✅ CORRECT
```bash
REGION="cn-beijing"

# Mainland China regions
if [[ "$REGION" =~ ^cn-(beijing|hangzhou|shanghai|shenzhen)$ ]]; then
  WRITE_PRICE=0.151
  READ_PRICE=0.0755
# International regions
elif [[ "$REGION" =~ ^(cn-hongkong|ap-southeast-1|ap-southeast-5|us-west-1|eu-central-1)$ ]]; then
  WRITE_PRICE=0.2651
  READ_PRICE=0.1326
else
  echo "Error: Unknown region pricing"
  exit 1
fi
```

#### ❌ INCORRECT
```bash
# Using wrong pricing for all regions
WRITE_PRICE=0.151
READ_PRICE=0.0755

# Or using hardcoded pricing without region check
```

---

### 2. Cost Calculation Formula

#### ✅ CORRECT
```bash
TOTAL_READS=1500000
TOTAL_WRITES=500000
READ_PRICE=0.0755
WRITE_PRICE=0.151

# Divide by 10,000 (pricing is per 10k operations)
READ_COST=$(echo "scale=4; $TOTAL_READS / 10000 * $READ_PRICE" | bc)
WRITE_COST=$(echo "scale=4; $TOTAL_WRITES / 10000 * $WRITE_PRICE" | bc)
TOTAL_COST=$(echo "scale=4; $READ_COST + $WRITE_COST" | bc)

echo "Read cost: ¥$READ_COST"
echo "Write cost: ¥$WRITE_COST"
echo "Total cost: ¥$TOTAL_COST"
```

#### ❌ INCORRECT
```bash
# Forgetting to divide by 10,000
READ_COST=$(echo "scale=4; $TOTAL_READS * $READ_PRICE" | bc)    # Wrong!

# Using wrong arithmetic
READ_COST=$(echo "$TOTAL_READS / 10000 * $READ_PRICE" | bc)     # Wrong: no scale, loses precision
```

---

## Correct Date Range Handling

### 1. Date Range Validation

#### ✅ CORRECT
```bash
START_DATE="2024-03-01"
END_DATE="2024-03-31"

# Calculate days between dates
START_TS=$(date -d "$START_DATE" +%s)
END_TS=$(date -d "$END_DATE" +%s)
DAYS=$(( ($END_TS - $START_TS) / 86400 ))

if [ $DAYS -gt 30 ]; then
  echo "Error: Date range exceeds 30 days (max allowed)"
  exit 1
fi

if [ $DAYS -lt 0 ]; then
  echo "Error: End date is before start date"
  exit 1
fi
```

#### ❌ INCORRECT
```bash
# Not validating date range before API call
aliyun paifeaturestore list-datasource-feature-views \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \      # Wrong: 365 days exceeds 30-day limit!
  --user-agent AlibabaCloud-Agent-Skills
```

---

### 2. Default Date Range

#### ✅ CORRECT
```bash
# Default for total usage: last 30 days
END_DATE=$(date -d "yesterday" +%Y-%m-%d)
START_DATE=$(date -d "30 days ago" +%Y-%m-%d)

# Default for project/feature view: last 7 days
END_DATE=$(date -d "yesterday" +%Y-%m-%d)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)
```

#### ❌ INCORRECT
```bash
# Using "today" as end date (data may not be complete)
END_DATE=$(date +%Y-%m-%d)

# Using fixed dates
START_DATE="2024-01-01"
END_DATE="2024-01-31"
```

---

## Functional Scope Validation

### ✅ CORRECT - In-Scope Requests

These requests are within the skill's functional scope:

1. "Query FeatureDB read/write usage for last month"
2. "Show me yesterday's feature view usage sorted by read count"
3. "Calculate my FeatureDB costs for the last 7 days"
4. "What's the usage trend for project 'recommendation_system'?"
5. "Show read/write trend for feature view 'user_features'"

### ❌ INCORRECT - Out-of-Scope Requests

These requests are OUT of scope and must be politely declined:

1. "Create a new FeatureDB datasource" - Creating resources
2. "Delete feature view 'user_features'" - Deleting resources
3. "Update datasource configuration" - Modifying resources
4. "Write data to FeatureDB" - Write operations
5. "Execute SQL query on FeatureDB" - Direct database operations
6. "Export feature data to CSV" - Data export operations

**Correct Response for Out-of-Scope**:
```
I apologize, but [requested action] is outside the scope of this skill.
This skill only supports querying and analyzing FeatureDB read/write usage statistics.

Supported functions:
1. Query daily read/write totals over a date range
2. Query per-feature-view usage on a specific date
3. Query project-level usage trends
4. Query feature view usage trends
5. Calculate costs based on official pricing

Would you like to query your FeatureDB usage statistics?
```

---

## Language Response Validation

### ✅ CORRECT - Match User's Language

**User asks in Chinese**:
```
User: "查询FeatureDB的读写量"
Agent: "好的,我来帮您查询FeatureDB的读写量。首先需要确认一些信息..."
```

**User asks in English**:
```
User: "Query FeatureDB read/write usage"
Agent: "Sure, I'll help you query FeatureDB read/write usage. First, I need to confirm some information..."
```

### ❌ INCORRECT - Language Mismatch

**User asks in Chinese, Agent responds in English**:
```
User: "查询FeatureDB的读写量"
Agent: "Sure, I'll help you query FeatureDB usage..."   # Wrong! Should respond in Chinese
```

**User asks in English, Agent responds in Chinese**:
```
User: "Query FeatureDB usage"
Agent: "好的,我来帮您查询..."   # Wrong! Should respond in English
```

---

## Summary Checklist

Before considering the skill complete, verify:

- [ ] All `aliyun` commands use `paifeaturestore` (lowercase, no hyphens)
- [ ] All actions use kebab-case format (e.g., `list-instances`, not `ListInstances`)
- [ ] All parameters use kebab-case with `--` prefix (e.g., `--instance-id`, not `--InstanceId`)
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills`
- [ ] All date parameters use `yyyy-MM-dd` format
- [ ] All region IDs are valid and lowercase with hyphens
- [ ] All enum values use correct casing (PascalCase for types, UPPERCASE for order)
- [ ] Boolean parameters use `true`/`false`, not `1`/`0`
- [ ] Pagination parameters are positive integers
- [ ] Date ranges don't exceed 30 days
- [ ] Cost calculations divide by 10,000 and use correct pricing tier
- [ ] Responses match user's question language
- [ ] Out-of-scope requests are politely declined with feature list
- [ ] JSON responses parsed with `jq`, not grep/awk
- [ ] Error handling checks exit codes and response structure
