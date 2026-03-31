# OSS-HDFS ConnectionProperties Documentation

> ⚠️ **Note**: This data source type does not currently support OpenAPI creation/modification. Please configure it through the DataWorks console. Support will be added in future versions.

## Property Definition

- **Data source type (`type`):** `oss_hdfs`
- **Supported configuration mode (`ConnectionPropertiesMode`):** `UrlMode` (Connection string mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `regionId` | String | `cn-beijing` | Yes | The region where OSS-HDFS is located. |
| `endpoint` | String | `cn-beijing.oss-dls.aliyuncs.com` | Yes | OSS-HDFS access endpoint. |
| `bucket` | String | `test-oss-sh` | Yes | OSS-HDFS bucket name. |
| `authType` | String | `RamRole` | Yes | Access identity type. Only supports `RamRole` and `Ak`. |
| `authIdentity` | String | `112345` | Yes | Role ID. |
| `accessId` | String | `xxxxx` | Yes | The accessId used when accessing the data source in AK mode. Required for AK mode. |
| `accessKey` | String | `xxxxx` | Yes | The accessKey used when accessing the data source in AK mode. Required for AK mode. |
| `envType` | String | `Dev` | Yes | Represents the data source environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Data Source Configuration Examples

### Connection String Mode (RamRole Recommended)

> **Note**: OSS-HDFS data source supports both `RamRole` and `Ak` authentication methods. **RamRole is recommended**.

**Create via RAM Role mode (Recommended):**

```json
{
    "envType": "Prod",
    "endpoint": "cn-beijing.oss-dls.aliyuncs.com",
    "bucket": "test-oss-sh",
    "authType": "RamRole",
    "authIdentity": "1123456"
}
```

**Create via AK mode (Alternative):**

```json
{
    "envType": "Prod",
    "endpoint": "cn-beijing.oss-dls.aliyuncs.com",
    "bucket": "test-oss-sh",
    "authType": "Ak",
    "accessId": "xxx",
    "accessKey": "xxx"
}
```

---

*Source: https://help.aliyun.com/zh/dataworks/developer-reference/oss-hdfs*
