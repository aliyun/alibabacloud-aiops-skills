# Acceptance Criteria: alibabacloud-ebs-disk-events

**Scenario**: EBS disk risk event query and analysis  
**Purpose**: Skill test acceptance criteria and verification patterns

---

## Correct CLI Command Patterns

### 1. Product Name Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou
```

- Product name is `ebs` (lowercase)
- The product exists in the Aliyun CLI EBS plugin

#### ❌ Incorrect

```bash
aliyun EBS describe-events --RegionId cn-hangzhou
```

- **Error**: Product name is case-sensitive, must be lowercase
- **Fix**: Use `ebs` instead of `EBS`

```bash
aliyun elastic-block-storage describe-events --RegionId cn-hangzhou
```

- **Error**: Product name is `ebs`, not the full service name
- **Fix**: Use `ebs`

---

### 2. Command/Action Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou
```

- Command is `describe-events` (kebab-case)
- Corresponds to API `DescribeEvents`

#### ❌ Incorrect

```bash
aliyun ebs DescribeEvents --RegionId cn-hangzhou
```

- **Error**: PascalCase command name `DescribeEvents` is deprecated, use kebab-case
- **Fix**: Use `describe-events`

```bash
aliyun ebs describe-event --RegionId cn-hangzhou
```

- **Error**: Command name misspelled
- **Fix**: Use `describe-events`

---

### 3. Required Parameter Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou
```

- `--RegionId` is present (required parameter)
- Region ID format is correct

#### ❌ Incorrect

```bash
aliyun ebs describe-events
```

- **Error**: Missing required parameter `--RegionId`
- **Fix**: Add `--RegionId` and specify a valid region

```bash
aliyun ebs describe-events --region-id cn-hangzhou
```

- **Error**: Parameter name should be `--RegionId` (PascalCase), not `--region-id`
- **Fix**: Use `--RegionId`

---

### 4. Parameter Name Validation

#### ✅ Correct

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --EventName DiskIOHang \
  --ResourceId d-bp67acfmxazb4p**** \
  --ResourceType disk \
  --Status WillExecute \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z \
  --EventLevel WARN \
  --MaxResults 10 \
  --NextToken AAAAAdDWBF2****
```

- All parameter names match the `aliyun ebs describe-events --help` output exactly
- Use PascalCase parameter names

#### ❌ Incorrect

```bash
aliyun ebs describe-events \
  --regionId cn-hangzhou \
  --eventName DiskIOHang
```

- **Error**: Parameter name casing is incorrect. Should be `--RegionId`, `--EventName`
- **Fix**: Use PascalCase parameter names

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --Event_Name DiskIOHang
```

- **Error**: Parameter name is incorrect
- **Fix**: Use `--EventName`

---

### 5. EventName Value Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventName DiskIOHang
aliyun ebs describe-events --RegionId cn-hangzhou --EventName NoSnapshot
aliyun ebs describe-events --RegionId cn-hangzhou --EventName CostOptimizationNeeded
aliyun ebs describe-events --RegionId cn-hangzhou --EventName DiskIONo4kAligned
```

- All values are from the allowed event name list
- Case-sensitive, exact match

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventName diskiohang
```

- **Error**: Event name is case-sensitive
- **Fix**: Use `DiskIOHang`

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventName IOHang
```

- **Error**: Event name does not exist
- **Fix**: Use `DiskIOHang`

---

### 6. Time Format Validation

#### ✅ Correct

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 2024-01-15T00:00:00Z \
  --EndTime 2024-01-15T23:59:59Z
```

- ISO 8601 format: `yyyy-MM-ddTHH:mm:ssZ`
- Use UTC+0 timezone (Z suffix)

#### ❌ Incorrect

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime "2024-01-15 00:00:00"
```

- **Error**: Not ISO 8601 format (missing T and Z)
- **Fix**: Use `2024-01-15T00:00:00Z`

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 1705276800000
```

- **Error**: API does not accept Unix millisecond timestamp string as input
- **Fix**: Use ISO 8601 format

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --StartTime 2024-01-15T08:00:00+08:00
```

- **Error**: Must use UTC+0 (Z), other timezones are not allowed
- **Fix**: Convert to UTC and use `2024-01-14T16:00:00Z`

---

### 7. MaxResults Value Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 1
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 50
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 100
```

- Value is in the range 1~100

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 0
```

- **Error**: 0 is not in the allowed range
- **Fix**: Use an integer between 1 and 100

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --MaxResults 200
```

- **Error**: Exceeds maximum allowed value 100
- **Fix**: Use a value not exceeding 100

---

### 8. EventLevel Value Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventLevel INFO
aliyun ebs describe-events --RegionId cn-hangzhou --EventLevel WARN
aliyun ebs describe-events --RegionId cn-hangzhou --EventLevel CRITICAL
```

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventLevel warn
```

- **Error**: Event level is case-sensitive
- **Fix**: Use `WARN`

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --EventLevel WARNING
```

- **Error**: `WARNING` does not exist, should be `WARN`

---

### 9. Status Value Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --Status WillExecute
aliyun ebs describe-events --RegionId cn-hangzhou --Status Executing
aliyun ebs describe-events --RegionId cn-hangzhou --Status Executed
aliyun ebs describe-events --RegionId cn-hangzhou --Status Ignore
aliyun ebs describe-events --RegionId cn-hangzhou --Status Expired
aliyun ebs describe-events --RegionId cn-hangzhou --Status Deleted
```

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --Status Pending
```

- **Error**: `Pending` does not exist, the pending status is `WillExecute`

---

### 10. ResourceType Value Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --ResourceType disk
```

- Currently only `disk` is supported

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --ResourceType Disk
```

- **Error**: `disk` must be lowercase
- **Fix**: Use `disk`

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --ResourceType ecs
```

- **Error**: `DescribeEvents` currently only supports disk resources
- **Fix**: Use `disk` or omit this parameter

---

### 11. ResourceId Format Validation

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --ResourceId d-bp67acfmxazb4p****
```

- Disk ID starts with `d-`

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --ResourceId i-bp67acfmxazb4p****
```

- **Error**: `i-` prefix is an ECS instance ID, not a disk ID
- **Fix**: Use the correct disk ID (`d-` prefix)

---

### 12. NextToken Usage Validation

#### ✅ Correct

```bash
aliyun ebs describe-events \
  --RegionId cn-hangzhou \
  --MaxResults 100 \
  --NextToken AAAAAdDWBF2****
```

- `NextToken` value is the `NextToken` returned from the previous API call
- Used with `MaxResults` for pagination

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --NextToken AAAAAdDWBF2****
```

- **Error**: Using `NextToken` alone without setting `MaxResults` may not trigger pagination mode
- **Fix**: Set `MaxResults` at the same time

---

### 13. Region ID Format

#### ✅ Correct

```bash
aliyun ebs describe-events --RegionId cn-hangzhou
aliyun ebs describe-events --RegionId cn-shanghai
aliyun ebs describe-events --RegionId cn-beijing
aliyun ebs describe-events --RegionId ap-southeast-1
```

- Use standard Alibaba Cloud region IDs
- Format: `{area}-{location}` or `{area}-{location}-{number}`

#### ❌ Incorrect

```bash
aliyun ebs describe-events --RegionId hangzhou
```

- **Error**: Missing country/region prefix
- **Fix**: Use `cn-hangzhou`

```bash
aliyun ebs describe-events --RegionId cn_hangzhou
```

- **Error**: Region ID uses hyphens, not underscores
- **Fix**: Use `cn-hangzhou`

---

## Response Validation Patterns

### 1. Successful Response Structure

#### ✅ Correct Response

```json
{
  "RequestId": "473469C7-AA6F-4DC5-B3DB-A3DC0DE3****",
  "TotalCount": 1,
  "NextToken": "AAAAAdDWBF2****",
  "ResourceEvents": [
    {
      "EventType": "Alert",
      "EventName": "DiskIOHang",
      "ResourceId": "d-bp67acfmxazb4p****",
      "ResourceType": "disk",
      "Status": "WillExecute",
      "StartTime": "1684204822000",
      "EndTime": "1679538083000",
      "Description": "...",
      "RecommendAction": "AdjustProvision",
      "RecommendParams": "4296",
      "EventLevel": "INFO",
      "ExtraAttributes": "{\\\"EcsInstanceId\\\":\\\"i-xxx\\\",\\\"Adapter\\\":\\\"hda\\\"}"
    }
  ]
}
```

- Contains `RequestId`
- `TotalCount` indicates the total count
- `ResourceEvents` is the event array
- Each event contains key fields

#### ❌ Incorrect Response

```json
{
  "Code": "InvalidParameter",
  "Message": "The parameter EventName is invalid."
}
```

- This is an error response, not a success response
- Check whether parameter values are in the allowed list

---

### 2. Distinguishing Empty Results from Errors

#### ✅ Empty Result (Valid)

```json
{
  "RequestId": "473469C7-AA6F-4DC5-B3DB-A3DC0DE3****",
  "TotalCount": 0,
  "NextToken": "",
  "ResourceEvents": []
}
```

- Valid response, just no events matching the criteria

#### ❌ Incorrect Response

```json
{
  "Code": "Forbidden",
  "Message": "User is not authorized to operate."
}
```

- Permission error, check RAM policy

---

## Common Error Patterns and Fixes

| Error Code | Cause | Fix |
|--------|------|------|
| `InvalidParameter` | Parameter value not in allowed list | Check `EventName`, `Status`, `EventLevel`, etc. |
| `InvalidParameter.EndTime` | `EndTime` is earlier than `StartTime` | Adjust time range |
| `MissingParameter` | Missing required parameter `RegionId` | Add `--RegionId` |
| `Forbidden` | Missing `ebs:DescribeEvents` permission | Grant corresponding RAM permission |
| `InvalidApi.NotFound` | Wrong product or command name | Use `aliyun ebs describe-events` |
| `RequestTimeout` | Query data volume too large | Narrow time range or use pagination |

---

## Test Checklist

Before considering the Skill complete, verify:

- [ ] Product name uses lowercase `ebs`
- [ ] Command uses kebab-case `describe-events`
- [ ] Parameter names use PascalCase (`--RegionId`, `--EventName`, etc.)
- [ ] Required parameter `--RegionId` is provided
- [ ] `EventName` is in the allowed value list with correct casing
- [ ] `EventLevel` is `INFO`, `WARN`, or `CRITICAL`
- [ ] `Status` is in the allowed value list
- [ ] `ResourceType` uses lowercase `disk`
- [ ] `ResourceId` is in the correct disk ID format (`d-` prefix)
- [ ] Time format is ISO 8601 with `Z` suffix
- [ ] `MaxResults` is in the range 1~100
- [ ] `NextToken` is used with `MaxResults` for pagination
- [ ] Region ID uses standard Alibaba Cloud format
- [ ] Success response contains `RequestId`
- [ ] Empty `ResourceEvents` is handled correctly
- [ ] `NextToken` is handled correctly for pagination

---

## References

- [Alibaba Cloud CLI Documentation](https://www.alibabacloud.com/help/en/cli)
- [EBS DescribeEvents API](https://api.aliyun.com/api/ebs/2021-07-30/DescribeEvents)
- Command verification: `aliyun ebs describe-events --help`
