# Related APIs

Complete API reference for MaxCompute Cost Analysis operations.

## API Overview

| Product | API Version | CLI Command | API Action | Method | Description |
|---------|-------------|-------------|------------|--------|-------------|
| MaxCompute | 2022-01-04 | `aliyun maxcompute list-instances` | ListInstances | GET | Get instance list for cost analysis |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-bills` | SumBills | POST | Summarize bills by project or fee item |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-bills-by-date` | SumBillsByDate | POST | Daily bill trends |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-daily-bills-by-item` | SumDailyBillsByItem | POST | Daily bill details (paginated) |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-storage-metrics-by-type` | SumStorageMetricsByType | POST | Storage usage by type |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-storage-metrics-by-date` | SumStorageMetricsByDate | POST | Storage usage by date |
| MaxCompute | 2022-01-04 | `aliyun maxcompute list-compute-metrics-by-instance` | ListComputeMetricsByInstance | POST | Compute metrics by instance |
| MaxCompute | 2022-01-04 | `aliyun maxcompute list-compute-metrics-by-signature` | ListComputeMetricsBySignature | POST | Compute metrics by SQL signature |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-compute-metrics-by-usage` | SumComputeMetricsByUsage | POST | Compute usage trends |
| MaxCompute | 2022-01-04 | `aliyun maxcompute sum-compute-metrics-by-record` | SumComputeMetricsByRecord | POST | Compute record counts |

---

## 1. list-instances

**Endpoint:** `GET /api/v1/bills/instances`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| startDate | integer | Yes | Start time (ms timestamp) |
| endDate | integer | Yes | End time (ms timestamp) |

### CLI Command

```bash
aliyun maxcompute list-instances --region {REGION_ID} --startDate {START_MS} --endDate {END_MS} --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| requestId | string | Request ID |
| httpCode | integer | Status code |
| data | array | Instance list |
| data[].name | string | Project name |

---

## 2. sum-bills

**Endpoint:** `POST /api/v1/bills/sum`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | No | Start time (ms timestamp) |
| endDate | integer | No | End time (ms timestamp) |
| statsType | string | No | `PROJECT` or `FEE_ITEM` |
| topN | integer | No | Top N items by cost |

### CLI Command

```bash
aliyun maxcompute sum-bills --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","topN":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data.totalCost | string | Total cost |
| data.currency | string | Currency (CNY) |
| data.itemBills | array | Cost item list |
| data.itemBills[].itemName | string | Item name |
| data.itemBills[].cost | string | Cost amount |
| data.itemBills[].percentage | number | Percentage of total |

### Fee Item Types

| Item | Description |
|------|-------------|
| Storage | Standard storage |
| LowFreqStorage | Infrequent access storage |
| ColdStorage | Long-term storage |
| DRStorage | Multi-AZ storage |
| ComputationSql | SQL compute |
| Download | Data download |

---

## 3. sum-bills-by-date

**Endpoint:** `POST /api/v1/bills/sumByDate`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | No | Start time (ms timestamp) |
| endDate | integer | No | End time (ms timestamp) |
| statsType | string | No | `PROJECT` or `FEE_ITEM` |
| topN | integer | No | Top N items |

### CLI Command

```bash
aliyun maxcompute sum-bills-by-date --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","topN":8}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data | array | Daily bill list |
| data[].dateTime | string | Date (yyyyMMdd) |
| data[].cost | string | Daily total cost |
| data[].currency | string | Currency (RMB) |
| data[].itemBills | array | Item breakdown |
| data[].itemBills[].itemName | string | Item name |
| data[].itemBills[].cost | string | Cost |
| data[].itemBills[].percentage | number | Percentage |

---

## 4. sum-daily-bills-by-item

**Endpoint:** `POST /api/v1/dailyBills/sumByItem`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | No | Start time (ms timestamp) |
| endDate | integer | No | End time (ms timestamp) |
| statsType | string | No | `PROJECT` or `FEE_ITEM` |
| types | array | No | Metering types (e.g., `["ComputationSql"]`) |
| pageNumber | integer | No | Page number |
| pageSize | integer | No | Page size |

### CLI Command

```bash
aliyun maxcompute sum-daily-bills-by-item --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"FEE_ITEM","pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data.itemSummaryBills | array | Cost summary list |
| data.itemSummaryBills[].itemName | string | Item name |
| data.itemSummaryBills[].totalCost | string | Total cost |
| data.itemSummaryBills[].currency | string | Currency (CNY) |
| data.itemSummaryBills[].percentage | number | Percentage |
| data.itemSummaryBills[].specCode | string | Spec code |
| data.itemSummaryBills[].dailySumBills | array | Daily breakdown |
| data.totalCount | integer | Total records |
| data.pageNumber | integer | Current page |
| data.pageSize | integer | Page size |

---

## 5. sum-storage-metrics-by-type

**Endpoint:** `POST /api/v1/storageMetrics/sumByType`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | No | Start time (ms timestamp) |
| endDate | integer | No | End time (ms timestamp) |
| statsType | string | No | `PROJECT` or `STORAGE_TYPE` |

### CLI Command

```bash
aliyun maxcompute sum-storage-metrics-by-type --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"PROJECT"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data | array | Storage metrics |
| data[].storageType | string | Storage type |
| data[].usage | number | Total usage |
| data[].unit | string | Unit (GB) |
| data[].dailyStorageMetrics | array | Daily metrics |
| data[].dailyStorageMetrics[].dateTime | string | Date (yyyyMMdd) |
| data[].dailyStorageMetrics[].usage | number | Usage |
| data[].dailyStorageMetrics[].percentage | number | Percentage |

### Storage Types

| Type | Description |
|------|-------------|
| Storage | Standard storage |
| LowFreqStorage | Infrequent access storage |
| ColdStorage | Long-term storage |
| DRStorage | Multi-AZ storage |
| RecycleBinStorage | Backup storage |
| $sum | Total storage |

---

## 6. sum-storage-metrics-by-date

**Endpoint:** `POST /api/v1/storageMetrics/sumByDate`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | **Yes** | Start time (ms timestamp) |
| endDate | integer | **Yes** | End time (ms timestamp) |
| statsType | string | **Yes** | `PROJECT` or `STORAGE_TYPE` |

### CLI Command

```bash
aliyun maxcompute sum-storage-metrics-by-date --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"statsType":"PROJECT"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data | array | Date-based metrics |
| data[].storageType | string | Storage type |
| data[].dateTime | string | Date (yyyyMMdd) |
| data[].usage | string | Total usage |
| data[].unit | string | Unit (GB) |
| data[].itemStorageMetrics | array | Item breakdown |
| data[].itemStorageMetrics[].itemName | string | Project or type name |
| data[].itemStorageMetrics[].usage | string | Usage |
| data[].itemStorageMetrics[].percentage | number | Percentage |

---

## 7. list-compute-metrics-by-instance

**Endpoint:** `POST /api/v1/computeMetrics/listByInstance`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | No | Start time (ms timestamp) |
| endDate | integer | No | End time (ms timestamp) |
| instanceId | string | No | Job instance ID |
| jobOwner | string | No | Job owner |
| signature | string | No | SQL signature |
| pageNumber | integer | No | Page number |
| pageSize | integer | No | Page size (default 10) |
| types | array | No | Metering types |
| specCodes | array | No | Spec codes |

### CLI Command

```bash
aliyun maxcompute list-compute-metrics-by-instance --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"types":["ComputationSql"],"pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data.instanceComputeMetrics | array | Job compute metrics |
| data.instanceComputeMetrics[].instanceId | string | Job ID |
| data.instanceComputeMetrics[].type | string | Metering type |
| data.instanceComputeMetrics[].specCode | string | Spec code |
| data.instanceComputeMetrics[].jobOwner | string | Job owner |
| data.instanceComputeMetrics[].projectName | string | Project name |
| data.instanceComputeMetrics[].submitTime | integer | Submit time |
| data.instanceComputeMetrics[].endTime | integer | End time |
| data.instanceComputeMetrics[].signature | string | SQL signature |
| data.instanceComputeMetrics[].usage | number | Usage (GB/CU-hours) |
| data.instanceComputeMetrics[].unit | string | Unit |
| data.totalCount | integer | Total count |
| data.pageNumber | integer | Current page |
| data.pageSize | integer | Page size |

### Compute Types

| Type | Description |
|------|-------------|
| ComputationSql | Internal table SQL |
| ComputationSqlOTS | OTS external table SQL |
| ComputationSqlOSS | OSS external table SQL |
| MapReduce | MapReduce jobs |
| spark | Spark jobs |
| mars | Mars jobs |

### Spec Codes

| Code | Description |
|------|-------------|
| OdpsStandard | Pay-as-you-go standard |
| OdpsSpot | Pay-as-you-go spot |

---

## 8. list-compute-metrics-by-signature

**Endpoint:** `POST /api/v1/computeMetrics/listBySignature`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | **Yes** | Start time (ms timestamp) |
| endDate | integer | **Yes** | End time (ms timestamp) |
| instanceId | string | No | Instance ID |
| jobOwner | string | No | Job owner |
| signature | string | No | SQL signature |
| pageNumber | integer | No | Page number |
| pageSize | integer | No | Page size (default 10) |
| types | array | No | Metering types |

### CLI Command

```bash
aliyun maxcompute list-compute-metrics-by-signature --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"types":["ComputationSql"],"pageNumber":1,"pageSize":10}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data.signatureComputeMetrics | array | Signature-level metrics |
| data.signatureComputeMetrics[].signature | string | SQL signature |
| data.signatureComputeMetrics[].projectNames | array | Project names |
| data.signatureComputeMetrics[].usage | number | Total usage |
| data.signatureComputeMetrics[].unit | string | Unit (GBCplx) |
| data.signatureComputeMetrics[].instances | array | Instance list |
| data.signatureComputeMetrics[].instances[].instanceId | string | Instance ID |
| data.signatureComputeMetrics[].instances[].startTime | integer | Start time |
| data.signatureComputeMetrics[].instances[].endTime | integer | End time |
| data.totalCount | integer | Total count |

---

## 9. sum-compute-metrics-by-usage

**Endpoint:** `POST /api/v1/computeMetrics/sumByUsage`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | **Yes** | Start time (ms timestamp) |
| endDate | integer | **Yes** | End time (ms timestamp) |
| usageType | string | No | `CU` (CU-hours) or `SCAN` (scan volume) |

### CLI Command

```bash
aliyun maxcompute sum-compute-metrics-by-usage --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS},"usageType":"SCAN"}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data | array | Usage data |
| data[].type | string | Metering type |
| data[].dailyComputeMetrics | array | Daily metrics |
| data[].dailyComputeMetrics[].dateTime | string | Date (yyyyMMdd) |
| data[].dailyComputeMetrics[].usage | string | Usage amount |
| data[].dailyComputeMetrics[].unit | string | Unit (GBCplx) |

---

## 10. sum-compute-metrics-by-record

**Endpoint:** `POST /api/v1/computeMetrics/sumByRecord`

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| projectNames | array | No | Project name list |
| startDate | integer | **Yes** | Start time (ms timestamp) |
| endDate | integer | **Yes** | End time (ms timestamp) |

### CLI Command

```bash
aliyun maxcompute sum-compute-metrics-by-record --region {REGION_ID} --body '{"startDate":{START_MS},"endDate":{END_MS}}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-cost-analysis
```

### Response

| Field | Type | Description |
|-------|------|-------------|
| data | array | Record data |
| data[].type | string | Usage type |
| data[].dailyComputeRecords | array | Daily records |
| data[].dailyComputeRecords[].dateTime | string | Date (yyyyMMdd) |
| data[].dailyComputeRecords[].record | string | Record count |
| data[].dailyComputeRecords[].percentage | number | Percentage |

---

## Error Codes

| HTTP Status | Description | Solution |
|-------------|-------------|----------|
| 400 | Invalid parameters | Check timestamp format (milliseconds), verify range <= 31 days |
| 403 | Permission denied | Verify RAM permissions |
| 500 | Server error | Retry later or contact support |
