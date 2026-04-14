# Related APIs and CLI Commands

This document provides a comprehensive reference of all APIs and CLI commands used in the PAI-FeatureStore FeatureDB Usage Query skill.

---

## API Overview

| Product | CLI Command | API Action | API Version | Description |
|---------|-------------|------------|-------------|-------------|
| PAI-FeatureStore | `aliyun paifeaturestore list-instances` | ListInstances | 2023-06-21 | List all PAI-FeatureStore instances |
| PAI-FeatureStore | `aliyun paifeaturestore get-datasource` | GetDatasource | 2023-06-21 | Get details of a specific datasource |
| PAI-FeatureStore | `aliyun paifeaturestore list-datasources` | ListDatasources | 2023-06-21 | List all datasources under an instance |
| PAI-FeatureStore | `aliyun paifeaturestore list-datasource-feature-views` | ListDatasourceFeatureViews | 2023-06-21 | List feature views and query usage statistics |

---

## Detailed API Reference

### 1. ListInstances

**Purpose**: List all PAI-FeatureStore instances in a region.

**CLI Command**:
```bash
aliyun paifeaturestore list-instances \
  --region <RegionId> \
  --status Running \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --region | string | Yes | Region ID (e.g., cn-beijing, cn-hangzhou) |
| --status | string | No | Filter by status: Initializing, Running, Failure |
| --page-number | int | No | Page number for pagination (default: 1) |
| --page-size | int | No | Page size for pagination (default: 10) |
| --sort-by | string | No | Sort by: GmtCreateTime, GmtModifiedTime |
| --order | string | No | Sort order: ASC, DESC |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| Instances | array | Array of instance objects |
| Instances[].InstanceId | string | Instance ID |
| Instances[].Status | string | Instance status |
| Instances[].Type | string | Instance type |
| Instances[].GmtCreateTime | string | Creation time |
| TotalCount | int | Total number of instances |

**API Documentation**: [ListInstances](https://api.aliyun.com/api/PaiFeatureStore/2023-06-21/ListInstances)

---

### 2. GetDatasource

**Purpose**: Get detailed information about a specific datasource.

**CLI Command**:
```bash
aliyun paifeaturestore get-datasource \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --region | string | Yes | Region ID |
| --instance-id | string | Yes | Instance ID from ListInstances |
| --datasource-id | string | Yes | Datasource ID to query |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| DatasourceId | string | Datasource ID |
| Name | string | Datasource name |
| Type | string | Datasource type (FeatureDB, Hologres, MaxCompute, TableStore) |
| Config | string | Datasource configuration (JSON string) |
| Uri | string | Datasource connection URI |
| GmtCreateTime | string | Creation time |
| WorkspaceId | string | Workspace ID |

**API Documentation**: [GetDatasource](https://api.aliyun.com/api/PaiFeatureStore/2023-06-21/GetDatasource)

---

### 3. ListDatasources

**Purpose**: List all datasources under an instance, optionally filtered by type and workspace.

**CLI Command**:
```bash
aliyun paifeaturestore list-datasources \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --type FeatureDB \
  --workspace-id <WorkspaceId> \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --region | string | Yes | Region ID |
| --instance-id | string | Yes | Instance ID from ListInstances |
| --type | string | No | Filter by type: FeatureDB, Hologres, MaxCompute, TableStore |
| --workspace-id | string | No | Filter by workspace ID |
| --name | string | No | Filter by datasource name (fuzzy match) |
| --page-number | int | No | Page number (default: 1) |
| --page-size | int | No | Page size (default: 10) |
| --sort-by | string | No | Sort field |
| --order | string | No | Sort order: ASC, DESC |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| Datasources | array | Array of datasource objects |
| Datasources[].DatasourceId | string | Datasource ID |
| Datasources[].Name | string | Datasource name |
| Datasources[].Type | string | Datasource type |
| Datasources[].WorkspaceId | string | Workspace ID |
| TotalCount | int | Total number of datasources |
| PageNumber | int | Current page number |
| PageSize | int | Current page size |

**Pagination Handling**:
```bash
# Calculate total pages: ceil(TotalCount / PageSize)
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

**API Documentation**: [ListDatasources](https://api.aliyun.com/api/PaiFeatureStore/2023-06-21/ListDatasources)

---

### 4. ListDatasourceFeatureViews

**Purpose**: List feature views under a datasource and query usage statistics (read/write counts).

**CLI Command**:

**For Total Usage Query (Function 1 & 3)**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <yyyy-MM-dd> \
  --end-date <yyyy-MM-dd> \
  --verbose false \
  --show-storage-usage false \
  --page-size 1 \
  --project-name <ProjectName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**For Per-Feature-View Query (Function 2)**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <yyyy-MM-dd> \
  --end-date <yyyy-MM-dd> \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --sort-by <ReadCount|WriteCount> \
  --order <ASC|DESC> \
  --user-agent AlibabaCloud-Agent-Skills
```

**For Feature View Trend Query (Function 4)**:
```bash
aliyun paifeaturestore list-datasource-feature-views \
  --region <RegionId> \
  --instance-id <InstanceId> \
  --datasource-id <DatasourceId> \
  --start-date <yyyy-MM-dd> \
  --end-date <yyyy-MM-dd> \
  --verbose true \
  --show-storage-usage false \
  --all true \
  --project-name <ProjectName> \
  --name <FeatureViewName> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --region | string | Yes | Region ID |
| --instance-id | string | Yes | Instance ID from ListInstances |
| --datasource-id | string | Yes | Datasource ID |
| --start-date | string | No | Query start date (yyyy-MM-dd format) |
| --end-date | string | No | Query end date (yyyy-MM-dd format) |
| --verbose | bool | No | Show detailed statistics (true) or only totals (false). Default: true |
| --show-storage-usage | bool | No | Show storage usage statistics. Default: true |
| --all | bool | No | Return all data without pagination |
| --page-number | int | No | Page number (default: 1) |
| --page-size | int | No | Page size (default: 10) |
| --project-name | string | No | Filter by project name |
| --name | string | No | Filter by feature view name (fuzzy match) |
| --type | string | No | Filter by type: Batch, Stream, Sequence |
| --sort-by | string | No | Sort by field (e.g., ReadCount, WriteCount) |
| --order | string | No | Sort order: ASC, DESC |

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| FeatureViews | array | Array of feature view objects (only when verbose=true) |
| FeatureViews[].FeatureViewId | string | Feature view ID |
| FeatureViews[].Name | string | Feature view name |
| FeatureViews[].ProjectName | string | Project name |
| FeatureViews[].Type | string | Feature view type |
| FeatureViews[].UsageStatistics | array | Array of daily usage statistics |
| FeatureViews[].UsageStatistics[].Date | string | Date (yyyy-MM-dd) |
| FeatureViews[].UsageStatistics[].ReadCount | long | Number of read operations |
| FeatureViews[].UsageStatistics[].WriteCount | long | Number of write operations |
| TotalUsageStatistics | array | Total usage statistics across all feature views |
| TotalUsageStatistics[].Date | string | Date (yyyy-MM-dd) |
| TotalUsageStatistics[].ReadCount | long | Total read count for the date |
| TotalUsageStatistics[].WriteCount | long | Total write count for the date |
| TotalCount | int | Total number of feature views |

**Date Range Limits**:
- Maximum span: 30 days between StartDate and EndDate
- Default behavior if dates not specified:
  - Total usage query (Function 1): Last 30 days
  - Project/Feature view query (Function 3/4): Last 7 days

**API Documentation**: [ListDatasourceFeatureViews](https://api.aliyun.com/api/PaiFeatureStore/2023-06-21/ListDatasourceFeatureViews)

---

## Common Parameter Patterns

### User Agent

**All CLI commands in this skill MUST include the user-agent flag**:
```bash
--user-agent AlibabaCloud-Agent-Skills
```

### Region Specification

Use the `--region` flag for all commands:
```bash
--region cn-beijing
```

### Date Format

All date parameters must use `yyyy-MM-dd` format:
```bash
--start-date 2024-01-01
--end-date 2024-01-31
```

### Boolean Parameters

Boolean flags are specified without values:
```bash
--verbose true      # Show detailed statistics
--verbose false     # Show only totals
--all true          # Return all data (no pagination)
```

---

## Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| InvalidParameter | Invalid parameter value | Check parameter format and allowed values |
| ResourceNotFound | Instance/Datasource not found | Verify the ID exists using list commands |
| OperationDenied.NoPermission | Insufficient RAM permissions | Check RAM policy configuration |
| InvalidDateRange | Date range exceeds maximum span | Reduce date range to <= 30 days |
| Throttling | Request rate limit exceeded | Implement retry with exponential backoff |

---

## Example Request-Response Flows

### Example 1: List Instances

**Request**:
```bash
aliyun paifeaturestore list-instances \
  --region cn-beijing \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response**:
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
  "TotalCount": 1
}
```

### Example 2: Query Total Usage

**Request**:
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
  --user-agent AlibabaCloud-Agent-Skills
```

**Response**:
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

---

## Additional Resources

- [PAI-FeatureStore API Overview](https://www.alibabacloud.com/help/pai-feature-store/latest/api-overview)
- [Aliyun CLI Plugin Mode Documentation](https://www.alibabacloud.com/help/cli/cli-v3-0)
- [API Error Codes](https://www.alibabacloud.com/help/pai-feature-store/latest/error-codes)
