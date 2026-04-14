---
name: alibabacloud-pai-feature-store-featuredb-usage-query
description: |
  Query FeatureDB read/write usage data from PAI-FeatureStore. Use for analyzing consumption, usage trends, and cost estimation by official pricing. Supports date range queries with breakdowns.
  Triggers: "FeatureDB read/write volume", "PAI-FeatureStore usage", "FeatureDB usage", "FeatureDB statistics", "Feature View usage", "PAI-FeatureStore billing"
---

# PAI-FeatureStore FeatureDB Usage Query and Analysis

**Architecture**: PAI-FeatureStore Instance → FeatureDB Datasource → Feature Views → Usage Statistics

### Key Features

1. **Total Usage Analysis**: Query daily read/write totals across a date range (up to 30 days)
2. **Feature View Details**: Query specific feature view usage on a given date with sorting by read/write count
3. **Project-Level Analysis**: Query daily read/write totals for a specific project (up to 30 days)
4. **Feature View Trends**: Query daily read/write trends for a specific feature view (up to 30 days)
5. **Cost Calculation**: Calculate costs based on official pricing tiers for different regions

### Supported Regions

`cn-beijing`, `cn-hangzhou`, `cn-shanghai`, `cn-shenzhen`, `cn-hongkong`, `ap-southeast-1`, `ap-southeast-5`, `us-west-1`, `eu-central-1`

---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
>
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low, see `references/cli-installation-guide.md` for installation instructions.
>
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

The PAI-FeatureStore CLI plugin will be automatically installed when first used if auto-plugin-install is enabled.

**Timeout**: Default 10s is sufficient for all API calls.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** output any string resembling a key (e.g., `LTAI5t***`, `AccessKeyId: xxx`, `ak-***`)
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**

---

## Required Parameters

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks, passwords, domain names, resource specifications, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|-------------------|-------------|---------------|
| RegionId | Required | Alibaba Cloud region ID. Must be one of the supported regions listed above. | None |
| WorkspaceId | Optional* | PAI workspace ID (numeric, e.g., `12345`). Required if DatasourceId is not provided. | None |
| DatasourceId | Optional* | FeatureDB datasource ID (numeric, e.g., `67890`). Required if WorkspaceId is not provided. | None |
| StartDate | Optional | Query start date in yyyy-MM-dd format. | 30 days ago (for total usage) or 7 days ago (for project/feature view) |
| EndDate | Optional | Query end date in yyyy-MM-dd format. | Yesterday |
| ProjectName | Optional | Project name (required for project-level and feature view queries). | None |
| FeatureViewName | Optional | Feature view name (required for feature view trend queries). | None |
| SortBy | Optional | Sort field: `ReadCount` or `WriteCount` | `ReadCount` |
| Order | Optional | Sort order: `ASC` or `DESC` | `DESC` |

**Note:** Either WorkspaceId or DatasourceId must be provided. If neither is provided, the skill will list all available FeatureDB datasources for user selection.

---

## RAM Permissions

This skill requires the following RAM permissions. See `references/ram-policies.md` for detailed policy configuration.

**Required Actions:**
- `paifeaturestore:ListInstances`
- `paifeaturestore:GetDatasource`
- `paifeaturestore:ListDatasources`
- `paifeaturestore:ListDatasourceFeatureViews`

---

## Core Workflow

### Functional Scope (MUST CHECK FIRST)

**This skill ONLY supports querying FeatureDB read/write usage statistics.** Any requests outside of "querying historical read/write counts or costs" are out of scope and must be politely declined with a list of supported features.

> **[MUST]** If request is out of scope, reject politely and list supported features:
>> "Sorry, this Skill only supports querying FeatureDB read/write usage statistics, not [user request]. Supported features: 1) Daily read/write totals 2) Feature view details 3) Usage trends 4) Cost calculation"

## Feature Selection Logic

Which features to execute depends on user's request:

| Scenario | Action |
|----------|--------|
| **Request out of scope or unsupported** | **Reject and list supported features** (see above) |
| User specifies supported feature(s) | Execute the specified feature(s) |
| User doesn't specify any feature | Execute **default behavior** (see below) |

### Supported Functions

1. **Query daily FeatureDB read/write totals from StartDate to EndDate** with analysis (max 30-day span)
2. **Query per-feature-view read/write counts for a specific date**, with sorting and analysis
3. **Query daily FeatureDB read/write totals for a specific project** from StartDate to EndDate with analysis (max 30-day span)
4. **Query daily FeatureDB read/write trends for a specific feature view** from StartDate to EndDate with analysis (max 30-day span)
5. **Calculate costs** based on official pricing and query results

### User-Friendly Prompts

Use descriptive names instead of function numbers when prompting, because "Function 3" is meaningless to users who haven't read this document.

### Execution Steps

#### Step 1: Verify PAI-FeatureStore Instance

```bash
aliyun paifeaturestore list-instances \
  --region <RegionId> \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output**: A list of running instances with their InstanceIds.

**Error Handling** (if no running instances found — **STOP, do NOT guess InstanceId**):
> No running PAI-FeatureStore instances found in this region. Please verify:
> 1. Is the RegionId correct?
> 2. Do you need to switch to a different region?
> 3. To activate PAI-FeatureStore, visit the [console](https://pai.console.aliyun.com/)

#### Step 2: Identify FeatureDB Datasource

**Case A: User provided WorkspaceId**

```bash
aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --workspace-id <WorkspaceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Case B: User provided DatasourceId**

> **[MUST]** When user provides DatasourceId, you MUST call GetDatasource to verify the datasource type is `FeatureDB`. Do NOT skip this validation step.

```bash
aliyun paifeaturestore get-datasource \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Validation**: Check the `Type` field in the response. If `Type` is NOT `FeatureDB`, stop and inform the user that this datasource is not a FeatureDB datasource.

**Case C: Neither WorkspaceId nor DatasourceId provided**

```bash
aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --user-agent AlibabaCloud-Agent-Skills
```

**Note**: This API is paginated. Calculate total pages from `TotalCount` and `PageSize`, then fetch all pages.

**Example pagination logic**:
```bash
# First call to get TotalCount
FIRST_RESPONSE=$(aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills)

# Extract TotalCount and calculate total pages
# Then iterate through all pages
for page in {1..total_pages}; do
  aliyun paifeaturestore list-datasources \
    --region <RegionId> \
    --instance-id <InstanceId> \
    --type FeatureDB \
    --page-number $page \
    --page-size 10 \
    --user-agent AlibabaCloud-Agent-Skills
done
```

Present all FeatureDB datasources to the user. If only ONE datasource exists, use it directly.

**When MULTIPLE datasources exist, behavior depends on query type:**

| Query Type | User Confirmation Required |
|------------|---------------------------|
| **Total usage (Function 1)** | Ask: "Query aggregated usage for all N datasources, or select a specific one?" Then proceed based on user's choice. |
| **Feature view details / Project / Trends (Function 2/3/4)** | Must select ONE datasource. These queries are datasource-specific and cannot span multiple datasources. |

**Error Handling**:
- If WorkspaceId or DatasourceId is invalid, fall back to Case C and list all available datasources.

#### Step 3: Query Usage Statistics

**Date Validation (before API call):**
- Format: Must be `yyyy-MM-dd` (e.g., `2024-03-15`). If user provides other formats (e.g., `3/15`, `2024.03.15`), convert to correct format.
- Range: `EndDate - StartDate` must be ≤ 30 days. If exceeded, ask user to narrow the range or split into multiple queries.
- Boundary: `EndDate` ≤ today; `StartDate` ≤ `EndDate`.

**Relative Date Ranges** ("last 7 days", "last 30 days"): Calculate `StartDate` = N days ago, `EndDate` = yesterday. Run `date` command separately first, then use the literal result in `--start-date`/`--end-date`. **NEVER** embed `$(...)` in CLI commands.

Execute queries based on user requirements:

##### Function 1: Query Total Daily Read/Write Usage

Query daily totals from StartDate to EndDate (default: last 30 days).

```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <StartDate> \
  --end-date <EndDate> \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Output**: Extract `TotalUsageStatistics` from the response.

##### Function 2: Query Per-Feature-View Usage for a Specific Date

Query all feature views' read/write counts on a specific date, with sorting.

```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <TargetDate> \
  --end-date <TargetDate> \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --sort-by <ReadCount|WriteCount> \
  --order <ASC|DESC> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Output**: Extract `FeatureViews` array from the response.

##### Function 3: Query Daily Usage for a Specific Project

Query daily totals for a specific project from StartDate to EndDate (default: last 7 days).

```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <StartDate> \
  --end-date <EndDate> \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --project-name <ProjectName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Output**: Extract `TotalUsageStatistics` from the response.

**Error Handling**:
- If the API returns an error indicating the project does not exist, recommend querying Function 2 first to get the complete list of queryable projects (deduplicate by project name).

##### Function 4: Query Daily Usage for a Specific Feature View

Query daily trends for a specific feature view from StartDate to EndDate (default: last 7 days).

```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <StartDate> \
  --end-date <EndDate> \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --project-name <ProjectName> \
  --name <FeatureViewName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Output**: Extract the matching feature view from the `FeatureViews` array.

**Error Handling**:
- If no matching feature view is found in the response, the feature view does not exist. Recommend querying Function 2 first to get the complete list of queryable feature views.

#### Step 4: Analyze Results and Calculate Costs

Based on user requirements:

1. **Analyze usage trends** from the query results
2. **Calculate costs**
Official Pricing (per 10,000 requests):

| Region | Write Cost | Read Cost |
|--------|------------|----------|
| Beijing, Shanghai, Hangzhou, Shenzhen | ¥0.151 | ¥0.0755 |
| Hong Kong, Singapore, Silicon Valley, Frankfurt, Jakarta | ¥0.2651 | ¥0.1326 |

3. **Present insights**:
   - Identify high-traffic feature views
   - Highlight usage patterns (spikes, trends)
   - Provide cost breakdown and optimization suggestions if applicable

4. **Offer next steps**:
   - Ask if the user wants to drill down into specific projects or feature views
   - Offer to calculate costs if not already done
   - Suggest further analysis options

---

## Success Verification

The skill execution is successful if:

1. ✅ Valid PAI-FeatureStore instance is found
2. ✅ FeatureDB datasource is identified or selected
3. ✅ Usage statistics are successfully retrieved
4. ✅ Results are analyzed and presented clearly
5. ✅ Cost calculations are accurate (if requested)
6. ✅ Response language matches user's question language

For detailed verification steps, see `references/verification-method.md`.

---

## Cleanup

This skill performs read-only operations and does not create any resources. No cleanup is required.

---

## Best Practices

1. **Always confirm the RegionId** with the user before executing any commands
2. **Use pagination properly** when listing datasources to ensure all results are retrieved
3. **Provide context in analysis**: Don't just show numbers—explain trends and patterns
4. **Offer actionable insights**: Suggest which feature views or projects to investigate further
5. **Handle errors gracefully**: If a project or feature view doesn't exist, guide the user to list all available options first
6. **Calculate costs accurately**: Use the correct pricing tier based on the region
7. **Keep user engaged**: After showing results, ask if they want to drill deeper or analyze specific aspects
8. **Decline out-of-scope requests politely**: If a request is not about querying usage statistics, politely decline and list supported features

---

## Reference Documentation

| Reference | Description |
|-----------|-------------|
| [RAM Policies](references/ram-policies.md) | Required RAM permissions and policy configuration |
| [Related APIs](references/related-apis.md) | Complete list of APIs and CLI commands used |
| [Verification Method](references/verification-method.md) | Detailed verification steps for each operation |
| [CLI Installation Guide](references/cli-installation-guide.md) | Aliyun CLI installation and setup instructions |
| [Acceptance Criteria](references/acceptance-criteria.md) | Testing patterns and validation criteria |
