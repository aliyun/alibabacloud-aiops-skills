# MaxCompute Quota Management - Related APIs

## API Availability Summary

| API Action | CLI Support | SDK Support | Status | Notes |
|------------|-------------|-------------|--------|-------|
| CreateQuota | ✅ | ✅ | Active | Create quota resources |
| GetQuota | ✅ | ✅ | **Deprecated** | Use QueryQuota instead |
| QueryQuota | ✅ | ✅ | Active | Recommended for querying |
| ListQuotas | ✅ | ✅ | Active | List all quotas |
| DeleteQuota | ❌ | ❌ | **Not Available** | Must use Console |

## CLI Commands Reference

| Product | CLI Command | API Action | API Version | Description | Status |
|---------|-------------|------------|-------------|-------------|--------|
| MaxCompute | `aliyun maxcompute CreateQuota` | CreateQuota | 2022-01-04 | Create a new quota | ✅ Active |
| MaxCompute | `aliyun maxcompute get-quota` | GetQuota | 2022-01-04 | Get quota details | ⚠️ Deprecated |
| MaxCompute | `aliyun maxcompute query-quota` | QueryQuota | 2022-01-04 | Get quota details | ✅ Recommended |
| MaxCompute | `aliyun maxcompute list-quotas` | ListQuotas | 2022-01-04 | List all quotas | ✅ Active |

## API Details

### 1. CreateQuota

**Endpoint:** `maxcompute.{regionId}.aliyuncs.com`

> **Note**: The `create-quota` kebab-case subcommand does not exist in the CLI plugin.
> Use the PascalCase API name `CreateQuota` with camelCase parameters.

**CLI Command:**
```bash
aliyun maxcompute CreateQuota \
  --chargeType <payasyougo|subscription> \
  --commodityCode <odps|odpsplus|odps_intl|odpsplus_intl> \
  --partNickName <nickname> \
  --commodityData '<json-data>' \
  --region <regionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chargeType` | String | Yes | Billing type: `payasyougo` or `subscription` |
| `commodityCode` | String | Yes | Product code (see commodity codes table) |
| `partNickName` | String | Yes (subscription) | Quota nickname |
| `commodityData` | String | Yes (subscription) | JSON format specification data |

**CommodityData Format (for subscription):**
```json
{
  "CU": 50,
  "ord_time": "1:Month",
  "autoRenew": false
}
```

**Response:**
```json
{
  "RequestId": "xxx-xxx-xxx",
  "Data": {
    "NickName": "quota-nickname"
  }
}
```

---

### 2. GetQuota (⚠️ Deprecated)

> **Warning**: This API is deprecated and will be removed after **2024-07-31**. Please use **QueryQuota** instead.

**CLI Command:**
```bash
aliyun maxcompute get-quota \
  --nickname <quota-nickname> \
  --region <regionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `nickname` | String | Yes | Quota nickname/alias (URL encoded if contains Chinese) |
| `tenantId` | String | No | Tenant ID (deprecated) |
| `mock` | Boolean | No | Include sub-modules (default: false) |

---

### 3. QueryQuota (✅ Recommended)

**CLI Command:**
```bash
aliyun maxcompute query-quota \
  --nickname <quota-nickname> \
  --region <regionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `nickname` | String | Yes | Quota nickname/alias (URL encoded if contains Chinese) |
| `tenantId` | String | No | Tenant ID |
| `region` | String | No | Region ID |

**Response:**
```json
{
  "RequestId": "xxx-xxx-xxx",
  "NickName": "quota-nickname",
  "Name": "quota-name",
  "Id": "quota-id",
  "Status": "ON"
}
```

---

### 4. ListQuotas

**CLI Command:**
```bash
aliyun maxcompute list-quotas \
  --billing-type <payasyougo|subscription> \
  --max-item <number> \
  --marker <token> \
  --region <regionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `billingType` | String | No | Filter by billing type: `subscription` or `payasyougo` | `subscription` |
| `maxItem` | Long | No | Max items per page | `100` |
| `marker` | String | No | Pagination token |

**Response:**
```json
{
  "RequestId": "xxx-xxx-xxx",
  "NextToken": "token-for-next-page",
  "QuotaInfoList": [
    {
      "NickName": "quota-nickname",
      "Name": "quota-name",
      "Id": "quota-id"
    }
  ]
}
```

---

### 5. DeleteQuota (❌ Not Available)

> **⚠️ LIMITATION**: MaxCompute does **NOT** provide a DeleteQuota API.
>
> To delete a quota, you must use:
> 1. [Alibaba Cloud MaxCompute Console](https://maxcompute.console.aliyun.com/)
> 2. For subscription quotas, cancel the subscription and wait for expiration
>
> **This is a platform limitation.**

---

## Commodity Codes Reference

| Site | Billing Type | Commodity Code | Description |
|------|--------------|----------------|-------------|
| China (国内站) | Pay-as-you-go (后付费) | `odps` | Pay-as-you-go for China site |
| China (国内站) | Subscription (预付费) | `odpsplus` | Subscription for China site |
| International (国际站) | Pay-as-you-go (后付费) | `odps_intl` | Pay-as-you-go for International site |
| International (国际站) | Subscription (预付费) | `odpsplus_intl` | Subscription for International site |

## API Documentation Links

- [CreateQuota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/CreateQuota)
- [GetQuota API](https://api.aliyun.com/api/MaxCompute/2022-01-04/GetQuota)
- [ListQuotas API](https://api.aliyun.com/api/MaxCompute/2022-01-04/ListQuotas)
- [MaxCompute API Overview](https://api.aliyun.com/product/MaxCompute)
