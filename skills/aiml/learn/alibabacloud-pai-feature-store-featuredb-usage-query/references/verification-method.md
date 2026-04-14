# Verification Method for PAI-FeatureStore FeatureDB Usage Query

This document provides detailed verification steps for validating the correct execution of each operation in the PAI-FeatureStore FeatureDB Usage Query skill.

---

## Overview

The skill performs read-only query operations, so verification focuses on:
1. Successful command execution
2. Data retrieval completeness
3. Result accuracy
4. Cost calculation correctness

---

## Step-by-Step Verification

### Step 1: Verify PAI-FeatureStore Instance Discovery

**Command**:
```bash
aliyun paifeaturestore list-instances \
  --region <RegionId> \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains `Instances` array
- ✅ At least one instance with `Status: "Running"` is returned
- ✅ Each instance has a valid `InstanceId`

**Verification Commands**:
```bash
# Check if any Running instances exist
RESPONSE=$(aliyun paifeaturestore list-instances \
  --region <RegionId> \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills)

# Verify response is valid JSON
echo "$RESPONSE" | jq . > /dev/null 2>&1 && echo "✅ Valid JSON response" || echo "❌ Invalid JSON"

# Count Running instances
INSTANCE_COUNT=$(echo "$RESPONSE" | jq '.Instances | length')
echo "Found $INSTANCE_COUNT Running instance(s)"

# Extract first InstanceId
INSTANCE_ID=$(echo "$RESPONSE" | jq -r '.Instances[0].InstanceId')
echo "First Instance ID: $INSTANCE_ID"
```

**Expected Output Example**:
```json
{
  "Instances": [
    {
      "InstanceId": "fs-cn-beijing-12345",
      "Status": "Running",
      "Type": "Standard",
      "GmtCreateTime": "2024-01-15T10:30:00Z"
    }
  ],
  "TotalCount": 1,
  "RequestId": "ABC123..."
}
```

**Troubleshooting**:
- **No instances found**: User doesn't have PAI-FeatureStore instances, or instances are not in Running status
- **Permission denied**: Check RAM policy includes `paifeaturestore:ListInstances`
- **Invalid region**: Verify RegionId is correct and supported

---

### Step 2: Verify FeatureDB Datasource Discovery

#### Case A: With WorkspaceId

**Command**:
```bash
aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --workspace-id <WorkspaceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains `Datasources` array
- ✅ All returned datasources have `Type: "FeatureDB"`
- ✅ Each datasource has a valid `DatasourceId`

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --workspace-id <WorkspaceId> \
  --user-agent AlibabaCloud-Agent-Skills)

# Verify all datasources are FeatureDB type
FEATUREDB_COUNT=$(echo "$RESPONSE" | jq '[.Datasources[] | select(.Type=="FeatureDB")] | length')
TOTAL_COUNT=$(echo "$RESPONSE" | jq '.Datasources | length')
echo "FeatureDB datasources: $FEATUREDB_COUNT out of $TOTAL_COUNT"

# Extract first DatasourceId
DATASOURCE_ID=$(echo "$RESPONSE" | jq -r '.Datasources[0].DatasourceId')
echo "First Datasource ID: $DATASOURCE_ID"
```

#### Case B: With DatasourceId

**Command**:
```bash
aliyun paifeaturestore get-datasource \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains datasource details
- ✅ `Type` field equals `"FeatureDB"`

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore get-datasource \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --user-agent AlibabaCloud-Agent-Skills)

# Verify type is FeatureDB
TYPE=$(echo "$RESPONSE" | jq -r '.Type')
if [ "$TYPE" == "FeatureDB" ]; then
  echo "✅ Datasource is FeatureDB"
else
  echo "❌ Datasource is not FeatureDB (Type: $TYPE)"
fi
```

#### Case C: List All FeatureDB Datasources

**Command** (with pagination):
```bash
# First call to get TotalCount
FIRST_RESPONSE=$(aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills)

# Calculate total pages
TOTAL_COUNT=$(echo "$FIRST_RESPONSE" | jq -r '.TotalCount')
PAGE_SIZE=10
TOTAL_PAGES=$(( ($TOTAL_COUNT + $PAGE_SIZE - 1) / $PAGE_SIZE ))

echo "Total FeatureDB datasources: $TOTAL_COUNT"
echo "Total pages to fetch: $TOTAL_PAGES"

# Fetch all pages
for ((page=1; page<=TOTAL_PAGES; page++)); do
  echo "Fetching page $page..."
  aliyun paifeaturestore list-datasources \
    --region <RegionId> \
    --instance-id <InstanceId> \
    --type FeatureDB \
    --page-number $page \
    --page-size 10 \
    --user-agent AlibabaCloud-Agent-Skills
done
```

**Success Criteria**:
- ✅ All pages fetched successfully
- ✅ Total datasources retrieved equals `TotalCount`
- ✅ All datasources have `Type: "FeatureDB"`

---

### Step 3: Verify Usage Statistics Query

#### Function 1: Total Daily Usage

**Command**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains `TotalUsageStatistics` array
- ✅ Number of daily records matches expected date range
- ✅ Each record has `Date`, `ReadCount`, and `WriteCount` fields
- ✅ ReadCount and WriteCount are non-negative integers

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills)

# Count daily records
RECORD_COUNT=$(echo "$RESPONSE" | jq '.TotalUsageStatistics | length')
echo "Daily usage records: $RECORD_COUNT"

# Calculate total reads and writes
TOTAL_READS=$(echo "$RESPONSE" | jq '[.TotalUsageStatistics[].ReadCount] | add')
TOTAL_WRITES=$(echo "$RESPONSE" | jq '[.TotalUsageStatistics[].WriteCount] | add')
echo "Total reads: $TOTAL_READS"
echo "Total writes: $TOTAL_WRITES"

# Verify date range
FIRST_DATE=$(echo "$RESPONSE" | jq -r '.TotalUsageStatistics[0].Date')
LAST_DATE=$(echo "$RESPONSE" | jq -r '.TotalUsageStatistics[-1].Date')
echo "Date range: $FIRST_DATE to $LAST_DATE"
```

**Expected Output Example**:
```json
{
  "TotalUsageStatistics": [
    {
      "Date": "2024-03-01",
      "ReadCount": 150000,
      "WriteCount": 50000
    },
    {
      "Date": "2024-03-02",
      "ReadCount": 180000,
      "WriteCount": 55000
    },
    ...
  ],
  "TotalCount": 25
}
```

#### Function 2: Per-Feature-View Usage

**Command**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-07 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --sort-by ReadCount \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains `FeatureViews` array
- ✅ Each feature view has `UsageStatistics` array
- ✅ Results are sorted correctly (DESC by ReadCount)
- ✅ `TotalUsageStatistics` matches sum of all feature views

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-07 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --sort-by ReadCount \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills)

# Count feature views
FV_COUNT=$(echo "$RESPONSE" | jq '.FeatureViews | length')
echo "Feature views: $FV_COUNT"

# Verify sorting (ReadCount should be descending)
echo "$RESPONSE" | jq -r '.FeatureViews[] | "\(.Name): \(.UsageStatistics[0].ReadCount) reads"' | head -10

# Verify total equals sum of all views
SUM_READS=$(echo "$RESPONSE" | jq '[.FeatureViews[].UsageStatistics[0].ReadCount] | add')
TOTAL_READS=$(echo "$RESPONSE" | jq '.TotalUsageStatistics[0].ReadCount')
echo "Sum of individual views: $SUM_READS"
echo "Total from TotalUsageStatistics: $TOTAL_READS"

if [ "$SUM_READS" -eq "$TOTAL_READS" ]; then
  echo "✅ Totals match"
else
  echo "⚠️ Totals mismatch"
fi
```

#### Function 3: Project-Level Usage

**Command**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --project-name recommendation_system \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains `TotalUsageStatistics` for the specified project
- ✅ If project doesn't exist, API returns appropriate error

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --project-name recommendation_system \
  --user-agent AlibabaCloud-Agent-Skills)

# Extract and display project usage
echo "$RESPONSE" | jq '.TotalUsageStatistics[] | "\(.Date): \(.ReadCount) reads, \(.WriteCount) writes"'
```

#### Function 4: Feature View Trend

**Command**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --project-name recommendation_system \
  --name user_features \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success Criteria**:
- ✅ Command executes without errors
- ✅ Response contains the matching feature view in `FeatureViews` array
- ✅ Feature view has daily `UsageStatistics` for the date range
- ✅ If feature view doesn't exist, `FeatureViews` array is empty or doesn't contain a match

**Verification Commands**:
```bash
RESPONSE=$(aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date 2024-03-01 \
  --end-date 2024-03-07 \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --project-name recommendation_system \
  --name user_features \
  --user-agent AlibabaCloud-Agent-Skills)

# Find the matching feature view
FV=$(echo "$RESPONSE" | jq '.FeatureViews[] | select(.ProjectName=="recommendation_system" and .Name=="user_features")')

if [ -n "$FV" ]; then
  echo "✅ Feature view found"
  echo "$FV" | jq '.UsageStatistics[] | "\(.Date): \(.ReadCount) reads, \(.WriteCount) writes"'
else
  echo "❌ Feature view not found"
fi
```

---

### Step 4: Verify Cost Calculation

**Success Criteria**:
- ✅ Correct pricing tier selected based on region
- ✅ Read cost calculated correctly: `(TotalReads / 10000) × ReadPrice`
- ✅ Write cost calculated correctly: `(TotalWrites / 10000) × WritePrice`
- ✅ Total cost = Read cost + Write cost
- ✅ Results rounded to appropriate decimal places

**Verification Logic**:

```bash
# Example: Calculate costs for cn-beijing region
REGION="cn-beijing"
TOTAL_READS=1500000    # From query result
TOTAL_WRITES=500000    # From query result

# Determine pricing tier
if [[ "$REGION" =~ ^cn-(beijing|hangzhou|shanghai|shenzhen)$ ]]; then
  WRITE_PRICE=0.151
  READ_PRICE=0.0755
  TIER="Mainland China"
else
  WRITE_PRICE=0.2651
  READ_PRICE=0.1326
  TIER="International"
fi

echo "Region: $REGION ($TIER)"
echo "Total reads: $TOTAL_READS"
echo "Total writes: $TOTAL_WRITES"

# Calculate costs
READ_COST=$(echo "scale=4; $TOTAL_READS / 10000 * $READ_PRICE" | bc)
WRITE_COST=$(echo "scale=4; $TOTAL_WRITES / 10000 * $WRITE_PRICE" | bc)
TOTAL_COST=$(echo "scale=4; $READ_COST + $WRITE_COST" | bc)

echo "Read cost: ¥$READ_COST"
echo "Write cost: ¥$WRITE_COST"
echo "Total cost: ¥$TOTAL_COST"
```

**Example Verification**:

For `cn-beijing` with 1,500,000 reads and 500,000 writes:
- Read cost: (1,500,000 / 10,000) × 0.0755 = ¥11.325
- Write cost: (500,000 / 10,000) × 0.151 = ¥7.55
- Total cost: ¥18.875

---

## Common Issues and Troubleshooting

### Issue 1: Empty Response

**Symptoms**: API returns empty arrays or null values

**Possible Causes**:
1. No data exists for the specified date range
2. Wrong datasource ID
3. Feature view or project name doesn't exist

**Verification**:
```bash
# Check if datasource has any feature views
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --all true \
  --user-agent AlibabaCloud-Agent-Skills
```

### Issue 2: Date Range Error

**Symptoms**: API returns error about invalid date range

**Possible Causes**:
1. Date range exceeds 30 days
2. EndDate is before StartDate
3. Date format is incorrect

**Verification**:
```bash
# Verify date format and range
START_DATE="2024-03-01"
END_DATE="2024-03-31"

# Calculate days between dates
DAYS=$(( ($(date -d "$END_DATE" +%s) - $(date -d "$START_DATE" +%s)) / 86400 ))
echo "Date range: $DAYS days"

if [ $DAYS -gt 30 ]; then
  echo "❌ Date range exceeds 30 days"
else
  echo "✅ Date range is valid"
fi
```

### Issue 3: Permission Denied

**Symptoms**: API returns "OperationDenied.NoPermission" error

**Verification**:
```bash
# Check RAM user's policies
aliyun ram list-policies-for-user \
  --user-name <YourUserName> \
  --user-agent AlibabaCloud-Agent-Skills

# Verify policy includes required actions
aliyun ram get-policy \
  --policy-name <PolicyName> \
  --policy-type Custom \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Integration Testing

### End-to-End Test Script

```bash
#!/bin/bash

REGION="cn-beijing"
WORKSPACE_ID="ws-12345"

echo "=== PAI-FeatureStore FeatureDB Usage Query Test ==="

# Step 1: Get instance
echo -e "\n[Step 1] Listing instances..."
INSTANCE_ID=$(aliyun paifeaturestore list-instances \
  --region $REGION \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances[0].InstanceId')

if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" == "null" ]; then
  echo "❌ No Running instance found"
  exit 1
fi
echo "✅ Found instance: $INSTANCE_ID"

# Step 2: Get FeatureDB datasource
echo -e "\n[Step 2] Listing FeatureDB datasources..."
DATASOURCE_ID=$(aliyun paifeaturestore list-datasources \
  --region $REGION \
  --instance-id $INSTANCE_ID \
  --type FeatureDB \
  --workspace-id $WORKSPACE_ID \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Datasources[0].DatasourceId')

if [ -z "$DATASOURCE_ID" ] || [ "$DATASOURCE_ID" == "null" ]; then
  echo "❌ No FeatureDB datasource found"
  exit 1
fi
echo "✅ Found datasource: $DATASOURCE_ID"

# Step 3: Query total usage (last 7 days)
echo -e "\n[Step 3] Querying total usage..."
END_DATE=$(date -d "yesterday" +%Y-%m-%d)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)

USAGE=$(aliyun paifeaturestore list-datasource-feature-views \
  --region $REGION \
  --instance-id $INSTANCE_ID \
  --datasource-id $DATASOURCE_ID \
  --start-date $START_DATE \
  --end-date $END_DATE \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills)

TOTAL_READS=$(echo "$USAGE" | jq '[.TotalUsageStatistics[].ReadCount] | add')
TOTAL_WRITES=$(echo "$USAGE" | jq '[.TotalUsageStatistics[].WriteCount] | add')

echo "✅ Usage query successful"
echo "   Total reads: $TOTAL_READS"
echo "   Total writes: $TOTAL_WRITES"

# Step 4: Calculate cost
echo -e "\n[Step 4] Calculating cost..."
READ_COST=$(echo "scale=4; $TOTAL_READS / 10000 * 0.0755" | bc)
WRITE_COST=$(echo "scale=4; $TOTAL_WRITES / 10000 * 0.151" | bc)
TOTAL_COST=$(echo "scale=4; $READ_COST + $WRITE_COST" | bc)

echo "✅ Cost calculation complete"
echo "   Read cost: ¥$READ_COST"
echo "   Write cost: ¥$WRITE_COST"
echo "   Total cost: ¥$TOTAL_COST"

echo -e "\n=== All tests passed ✅ ==="
```

---

## Performance Metrics

Track these metrics to ensure the skill is performing optimally:

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | < 3 seconds | Time from command invocation to response |
| Data Completeness | 100% | All pages of paginated results retrieved |
| Cost Calculation Accuracy | 100% | Matches manual calculation |
| Error Rate | < 1% | Failed API calls / Total API calls |

---

## Conclusion

Following these verification steps ensures:
- ✅ All API calls execute successfully
- ✅ Data is retrieved completely and accurately
- ✅ Cost calculations are correct
- ✅ User receives actionable insights
- ✅ The skill operates within functional scope
