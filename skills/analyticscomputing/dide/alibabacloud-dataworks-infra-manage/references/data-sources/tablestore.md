# TableStore ConnectionProperties Documentation

## Property Definition

- **Data Source Type (type):** `tablestore`
- **Supported Configuration Mode (ConnectionPropertiesMode):** `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where TableStore is located. |
| `endpoint` | String | `http://test-ots-sh-shanghai.ots.aliyuncs.com` | Yes | TableStore access endpoint. |
| `instanceName` | String | `test-ots-sh` | Yes | TableStore instance name. |
| `accessId` | String | `xxxxx` | Yes | The accessId used to access the data source under AK mode. Required when using AK mode. |
| `accessKey` | String | `xxxxx` | Yes | The accessKey used to access the data source under AK mode. Required when using AK mode. |
| `envType` | String | `Dev` | Yes | Indicates the data source environment information.<ul><li>`Dev`: Development environment</li><li>`Prod`: Production environment</li></ul> |

---

## Configuration Example

### Connection String Mode

```json
{
    "envType": "Prod",
    "endpoint": "http://test-ots-sh-shanghai.ots.aliyuncs.com",
    "instanceName": "test-ots-sh",
    "accessId": "xxx",
    "accessKey": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/tablestore*
