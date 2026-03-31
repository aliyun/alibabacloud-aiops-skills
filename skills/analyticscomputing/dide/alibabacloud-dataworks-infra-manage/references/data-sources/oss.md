# OSS Data Source Documentation

## Property Definition

- **Data source type**: `oss`
- **Supported configuration mode (ConnectionPropertiesMode)**: `UrlMode` (Connection string mode)

## Connection String Mode Parameters

| Name | Type | Example | Required | Description and Notes |
|------|------|---------|----------|----------------------|
| regionId | String | cn-shanghai | Yes | The region where OSS is located. |
| endpoint | String | http://oss-beijing.aliyuncs.com | Yes | OSS access endpoint. |
| bucket | String | test-oss-sh | Yes | The OSS bucket name. |
| authType | String | RamRole | Yes | Access identity type. Only supports `RamRole` and `Ak`. |
| authIdentity | String | 112345 | No | Role ID. Required when using `RamRole` access identity. |
| accessId | String | xxxxx | No | AccessId used for accessing the data source in AK mode. Required in AK mode. |
| accessKey | String | xxxxx | No | AccessKey used for accessing the data source in AK mode. Required in AK mode. |
| envType | String | Dev | Yes | envType indicates the data source environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

## Data Source Configuration Examples

### Connection String Mode (RamRole Recommended)

> **Note**: OSS data source supports both `RamRole` and `Ak` authentication methods. **RamRole is recommended**.

**Create via RAM Role Mode (Recommended):**

```json
{
    "envType": "Prod",
    "endpoint": "http://oss-beijing.aliyuncs.com",
    "bucket": "test-oss-sh",
    "authType": "RamRole",
    "authIdentity": "1123455"
}
```

**Create via AK Mode (Alternative):**

```json
{
    "envType": "Prod",
    "endpoint": "http://oss-beijing.aliyuncs.com",
    "bucket": "test-oss-sh",
    "authType": "Ak",
    "accessId": "xxx",
    "accessKey": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/oss*
