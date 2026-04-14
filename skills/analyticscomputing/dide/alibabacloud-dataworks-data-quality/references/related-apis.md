# DataWorks Data Quality Related APIs

All APIs use: `aliyun dataworks-public <ApiName> --user-agent AlibabaCloud-Agent-Skills`

---

## Module 1: Rule Template APIs

### ListDataQualityTemplates — List Rule Templates

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| ProjectId | long | No | Workspace ID (omit to query system built-in templates) | 10000 |
| Name | string | No | Fuzzy match on template name | table_rows |
| Catalog | string | No | Template catalog path filter | /timeliness/ods_layer |
| PageNumber | integer | No | Page number, default 1 | 1 |
| PageSize | integer | No | Page size, default 10 | 10 |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| PageInfo.TotalCount | integer | Total count |
| PageInfo.PageNumber | integer | Current page |
| PageInfo.PageSize | integer | Page size |
| PageInfo.DataQualityTemplates[] | array | Template list |
| - Id | string | Template ID (UUID) |
| - Spec | string | Template configuration JSON |
| - Owner | string | Owner user ID |
| - CreateUser / ModifyUser | string | Creator / last modifier |
| - CreateTime / ModifyTime | long | Timestamps (ms) |

**Example:**
```bash
aliyun dataworks-public ListDataQualityTemplates --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --ProjectId 10000 --PageNumber 1 --PageSize 10
```

---

### GetDataQualityTemplate — Get Rule Template Details

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| Id | string | Yes | Template ID (UUID) | a7ef0634-20ec-4a7c-a214-54020f91xxxx |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| DataQualityTemplate.Id | string | Template ID |
| DataQualityTemplate.ProjectId | long | Workspace ID |
| DataQualityTemplate.Spec | string | Full template configuration JSON |
| DataQualityTemplate.Owner | string | Owner user ID |
| DataQualityTemplate.CreateUser / ModifyUser | string | Creator / last modifier |
| DataQualityTemplate.CreateTime / ModifyTime | long | Timestamps (ms) |

**Example:**
```bash
aliyun dataworks-public GetDataQualityTemplate --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id a7ef0634-20ec-4a7c-a214-54020f91xxxx
```

---

## Module 2: Data Quality Monitor (Scan) APIs

### ListDataQualityScans — List Data Quality Monitors

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| ProjectId | long | Yes | Workspace ID | 10000 |
| PageNumber | integer | Yes | Page number, default 1 | 1 |
| PageSize | integer | Yes | Page size, default 10 | 10 |
| Name | string | No | Fuzzy match on monitor name | test |
| Table | string | No | Fuzzy match on monitored table name | video_album |
| SortBy | string | No | Sort field + direction | ModifyTime Desc |

**SortBy options:** `ModifyTime Desc`, `ModifyTime Asc`, `CreateTime Desc`, `CreateTime Asc`, `Id Desc`, `Id Asc`

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| PageInfo.TotalCount | integer | Total count |
| PageInfo.PageNumber | integer | Current page |
| PageInfo.PageSize | integer | Page size |
| PageInfo.DataQualityScans[] | array | Monitor list |
| - Id | long | Monitor ID |
| - Name | string | Monitor name |
| - Description | string | Description |
| - Owner | string | Owner user ID |
| - CreateTime / ModifyTime | long | Timestamps (ms) |

**Example:**
```bash
aliyun dataworks-public ListDataQualityScans --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --ProjectId 10000 --PageNumber 1 --PageSize 10 --Table video_album --SortBy "ModifyTime Desc"
```

---

### GetDataQualityScan — Get Monitor Details

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| Id | long | Yes | Monitor ID | 10001 |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| DataQualityScan.Id | long | Monitor ID |
| DataQualityScan.Name | string | Monitor name |
| DataQualityScan.Description | string | Description |
| DataQualityScan.ProjectId | long | Workspace ID |
| DataQualityScan.Spec | string | Full rule configuration JSON (table, field, metric, threshold) |
| DataQualityScan.Parameters | array | Execution parameter definitions |
| DataQualityScan.ComputeResource | object | Compute engine configuration |
| DataQualityScan.RuntimeResource | object | Resource group configuration |
| DataQualityScan.Trigger | object | Trigger configuration (ByManual or BySchedule) |
| DataQualityScan.Hooks | array | Post-execution hook configurations |
| DataQualityScan.Owner | string | Owner user ID |
| DataQualityScan.CreateUser / ModifyUser | string | Creator / last modifier |
| DataQualityScan.CreateTime / ModifyTime | long | Timestamps (ms) |

**Example:**
```bash
aliyun dataworks-public GetDataQualityScan --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id 10001
```

---

## Module 3: Alert Rule APIs

### ListDataQualityAlertRules — List Alert Rules

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| ProjectId | long | Yes | Workspace ID | 10001 |
| PageNumber | integer | Yes | Page number | 1 |
| PageSize | integer | Yes | Page size | 10 |
| DataQualityScanId | long | No | Filter by monitor ID | 10001 |
| SortBy | string | No | Sort field + direction | CreateTime Desc |

**SortBy options:** `CreateTime Desc`, `CreateTime Asc`, `Id Desc`, `Id Asc`

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| PageInfo.TotalCount | integer | Total count |
| PageInfo.PageNumber | integer | Current page |
| PageInfo.PageSize | integer | Page size |
| PageInfo.DataQualityAlertRules[] | array | Alert rule list |
| - Id | long | Alert rule ID |
| - ProjectId | long | Workspace ID |
| - Condition | string | Alert trigger condition expression |
| - Target.Type | string | Monitor object type (`DataQualityScan`) |
| - Target.Ids[] | array | Associated monitor IDs |
| - Notification.Channels[] | array | Alert channels |
| - Notification.Receivers[] | array | Alert recipients |

**Example:**
```bash
aliyun dataworks-public ListDataQualityAlertRules --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --ProjectId 10001 --PageNumber 1 --PageSize 10 --DataQualityScanId 10001
```

---

### GetDataQualityAlertRule — Get Alert Rule Details

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| Id | long | Yes | Alert rule ID | 113642 |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| DataQualityAlertRule.Id | long | Alert rule ID |
| DataQualityAlertRule.ProjectId | long | Workspace ID |
| DataQualityAlertRule.Condition | string | Alert condition expression |
| DataQualityAlertRule.Target.Type | string | Monitor type (`DataQualityScan`) |
| DataQualityAlertRule.Target.Ids[] | array | Associated monitor ID list |
| DataQualityAlertRule.Notification.Channels[] | array | Channels: `Dingding`, `Mail`, `Weixin`, `Feishu`, `Phone`, `Sms`, `Webhook` |
| DataQualityAlertRule.Notification.Receivers[] | array | Recipients: type + values |

**Receiver types:** `ShiftSchedule`, `WebhookUrl`, `FeishuUrl`, `TaskOwner`, `WeixinUrl`, `DingdingUrl`, `DataQualityScanOwner`, `AliUid`

**Example:**
```bash
aliyun dataworks-public GetDataQualityAlertRule --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id 113642
```

---

## Module 4: Scan Run APIs

### ListDataQualityScanRuns — List Scan Run Records

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| ProjectId | long | Yes | Workspace ID | 12345 |
| DataQualityScanId | long | No | Filter by monitor ID | 10001 |
| Status | string | No | Status filter: `Pass` / `Running` / `Error` / `Fail` / `Warn` | Fail |
| CreateTimeFrom | long | No | Earliest start time (ms timestamp) | 1710239005000 |
| CreateTimeTo | long | No | Latest start time (ms timestamp) | 1710239605000 |
| SortBy | string | No | Sort field + direction | CreateTime Desc |
| PageNumber | integer | No | Page number, default 1 | 1 |
| PageSize | integer | No | Page size, default 10 | 20 |
| Filter | object | No | Extended filters: `TaskInstanceId`, `RunNumber` | `{"TaskInstanceId":"111"}` |

**SortBy options:** `CreateTime Desc`, `CreateTime Asc`, `Id Desc`, `Id Asc`

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| PageInfo.TotalCount | integer | Total count |
| PageInfo.PageNumber | integer | Current page |
| PageInfo.PageSize | integer | Page size |
| PageInfo.DataQualityScanRuns[] | array | Run record list |
| - Id | long | Scan run ID |
| - Status | string | Execution status |
| - CreateTime | long | Run start time (ms) |
| - FinishTime | long | Run end time (ms) |
| - Parameters[] | array | Runtime parameters (name + value) |

**Example:**
```bash
aliyun dataworks-public ListDataQualityScanRuns --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --ProjectId 12345 --Status Fail --SortBy "CreateTime Desc" --PageNumber 1 --PageSize 20
```

---

### GetDataQualityScanRun — Get Scan Run Details

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| Id | long | Yes | Scan run ID | 1006059507 |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| DataQualityScanRun.Id | long | Scan run ID |
| DataQualityScanRun.Status | string | Overall status: `Pass` / `Running` / `Error` / `Fail` / `Warn` |
| DataQualityScanRun.CreateTime | long | Start time (ms) |
| DataQualityScanRun.FinishTime | long | End time (ms) |
| DataQualityScanRun.Scan | object | Configuration snapshot (Spec, Trigger, ComputeResource, RuntimeResource, Hooks) |
| DataQualityScanRun.Parameters[] | array | Runtime parameters (name + value) |
| DataQualityScanRun.Results[] | array | Per-rule execution results (status, metric value, threshold) |

**Example:**
```bash
aliyun dataworks-public GetDataQualityScanRun --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id 1006059507
```

---

### GetDataQualityScanRunLog — Get Scan Run Log

Supports pagination for large logs (max 512 KB per call). Call repeatedly with `NextOffset` until it returns `-1`.

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|-------------|---------|
| Id | long | Yes | Scan run ID | 10001 |
| Offset | long | No | Byte offset from start of log file (default 0) | 512000 |

**Response Parameters:**

| Name | Type | Description |
|------|------|-------------|
| RequestId | string | Request ID |
| LogSegment.Log | string | Log text content (up to 512 KB) |
| LogSegment.NextOffset | long | Offset for next call; `-1` means end of log |

**Example — first segment:**
```bash
aliyun dataworks-public GetDataQualityScanRunLog --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id 10001
```

**Example — subsequent segment:**
```bash
aliyun dataworks-public GetDataQualityScanRunLog --user-agent AlibabaCloud-Agent-Skills --region cn-hangzhou --endpoint dataworks.cn-hangzhou.aliyuncs.com --Id 10001 --Offset 512000
```

---

## Region and Endpoints

When specifying `--region`, you **must** also add `--endpoint`.

| Scenario | Parameters |
|----------|-----------|
| Public network | `--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com` |
| VPC internal network | `--region <REGION_ID> --endpoint dataworks-vpc.<REGION_ID>.aliyuncs.com` |

### Common Regions

| Region Name | Region ID |
|-------------|-----------|
| China (Hangzhou) | `cn-hangzhou` |
| China (Shanghai) | `cn-shanghai` |
| China (Beijing) | `cn-beijing` |
| China (Shenzhen) | `cn-shenzhen` |
| China (Chengdu) | `cn-chengdu` |
| China (Hong Kong) | `cn-hongkong` |
| Singapore | `ap-southeast-1` |
| Indonesia (Jakarta) | `ap-southeast-5` |
| Japan (Tokyo) | `ap-northeast-1` |
| US (Virginia) | `us-east-1` |
| US (Silicon Valley) | `us-west-1` |
| Germany (Frankfurt) | `eu-central-1` |

> Endpoint naming rule: `dataworks.<REGION_ID>.aliyuncs.com` (public) / `dataworks-vpc.<REGION_ID>.aliyuncs.com` (VPC)

---

## Official Documentation Links

- [ListDataQualityTemplates](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listdataqualitytemplates)
- [GetDataQualityTemplate](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdataqualitytemplate)
- [ListDataQualityScans](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listdataqualityscans)
- [GetDataQualityScan](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdataqualityscan)
- [ListDataQualityAlertRules](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listdataqualityalertrules)
- [GetDataQualityAlertRule](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdataqualityalertrule)
- [ListDataQualityScanRuns](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listdataqualityscanruns)
- [GetDataQualityScanRun](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdataqualityscanrun)
- [GetDataQualityScanRunLog](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdataqualityscanrunlog)
