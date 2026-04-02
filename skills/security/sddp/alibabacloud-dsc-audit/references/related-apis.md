# Data Security Center API Reference

## Service Configuration

| Configuration | Value |
|---------------|-------|
| Product Code | Sddp |
| Endpoint | sddp.cn-zhangjiakou.aliyuncs.com |
| API Version | 2019-01-03 |
| API Style | RPC |

## API List

| API Name | Description | Method |
|----------|-------------|--------|
| DescribeRiskRules | Query security risk events | POST |
| PreHandleAuditRisk | Handle security risk events | POST |

---

## DescribeRiskRules - Query Security Risk Events

### API Description

Paginated query of security risk event list from the Data Security Center. Increment the `CurrentPage` parameter to retrieve all risk events.

### Request Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| CurrentPage | Integer | No | Current page number | 1 |
| PageSize | Integer | No | Records per page | 10 |
| HandleStatus | String | No | Processing status | UNPROCESSED |

### HandleStatus Enum Values

| Value | Description |
|-------|-------------|
| UNPROCESSED | Not processed |
| PROCESSED | Processed |

### Request Example

```json
{
  "CurrentPage": 1,
  "PageSize": 10,
  "HandleStatus": "UNPROCESSED"
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| TotalCount | Integer | Total number of risk events |
| PageSize | Integer | Records per page |
| CurrentPage | Integer | Current page number |
| Items | Array | Risk event list |

### Items Array Element Structure

| Field | Type | Description |
|-------|------|-------------|
| **RiskId** | Long | Risk event ID, **must use this ID for handling** |
| RuleName | String | Rule name |
| RuleId | Long | Rule ID |
| WarnLevel | Integer | Risk level value |
| WarnLevelName | String | Risk level name (High Risk/Medium Risk/Low Risk) |
| ProductCode | String | Product type (RDS/OSS, etc.) |
| AlarmCount | Integer | Alert count |
| InstanceCount | Integer | Number of affected assets |
| ClientIpCount | Integer | Number of client IPs |
| FirstAlarmTime | Long | First discovery time (timestamp) |
| LastAlarmTime | Long | Last discovery time (timestamp) |
| HandleStatus | String | Processing status |
| RuleCategoryName | String | Rule category name |

### Response Example

```json
{
  "code": 200,
  "data": {
    "TotalCount": 1,
    "PageSize": 10,
    "CurrentPage": 1,
    "Items": [
      {
        "RiskId": 75110196,
        "ClientIpCount": 2,
        "FirstAlarmTime": 1772075549000,
        "ProductCode": "RDS",
        "RuleId": 9953728,
        "RuleCategoryId": 11,
        "TotalInstanceCount": 2,
        "LastAlarmTime": 1773387801000,
        "AlarmSource": "DSC",
        "AlertFrequency": "1/day",
        "InstanceCount": 2,
        "WarnLevel": 3,
        "SupportAi": false,
        "HandleMarkTime": 0,
        "HandleStatus": "UNPROCESSED",
        "TotalUserNameCount": 4,
        "RuleCategoryName": "Database Dump Attack",
        "TotalAlarmCount": 18,
        "TotalClientIpCount": 2,
        "UserNameCount": 4,
        "WarnLevelName": "High Risk",
        "RuleName": "jiangyu_test_mysqldump",
        "AlarmCount": 18
      }
    ]
  },
  "requestId": "95755da3-6dcf-4978-a693-0dcf270da272",
  "success": true
}
```

---

## PreHandleAuditRisk - Handle Security Risk Events

### API Description

Perform handling operations on specified security risk events.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| RiskId | Long | Yes | Risk event ID, obtained from DescribeRiskRules API |
| HandleInfoList | Array | Yes | Handling method list |

### HandleInfoList Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| HandleType | String | Yes | Handling type, fixed as `Manual` (manual handling) |
| HandleContent | Object | Yes | Handling content |

### HandleContent Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| HandleMethod | Integer | Yes | Handling method, fixed as `0` |
| HandleDetail | String | Yes | Handling details, requires user to input specific description |

### Request Example (Original Format)

```json
{
  "RiskId": 75110196,
  "HandleInfoList": [
    {
      "HandleType": "Manual",
      "HandleContent": {
        "HandleMethod": 0,
        "HandleDetail": "Confirmed as false positive, closing this alert"
      }
    }
  ]
}
```

### Request Example (Flat Mode - SDK Usage)

In RPC-style APIs, complex objects need to be converted to flat mode:

```json
{
  "RiskId": 75110196,
  "HandleInfoList.1.HandleType": "Manual",
  "HandleInfoList.1.HandleContent": "{\"HandleMethod\": 0, \"HandleDetail\": \"Confirmed as false positive, closing this alert\"}"
}
```

### Response Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| RequestId | String | Request ID |
| Success | Boolean | Whether the operation was successful |

### Response Example

```json
{
  "RequestId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "Success": true
}
```

---

## Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| InvalidParameter | Invalid parameter | Check parameter format and constraints |
| MissingParameter | Missing required parameter | Add required parameters |
| Forbidden | Access denied | Check RAM permissions |
| Throttling | Request rate exceeded | Implement retry with backoff |
| ServiceUnavailable | Service temporarily unavailable | Retry after delay |
| InternalError | Internal service error | Contact technical support with RequestId |
