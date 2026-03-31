# Data Lake Formation Datasource Documentation

> ⚠️ **Note**: This data source type does not currently support OpenAPI creation/modification (not supported in some regions). Please configure it through the DataWorks console. Support will be added in future versions.

## Property Definition

- **Datasource type**: `dlf`
- **Supported configuration mode (ConnectionPropertiesMode)**:
  - `InstanceMode` (Instance Mode)

---

## Property Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `regionId` | String | `cn-hangzhou` | Yes | Region ID. |
| `catalogId` | String | `clg-paimon-xxx` | Yes | DLF catalog ID. |
| `catalogName` | String | `xxx` | Yes | DLF catalog name. |
| `database` | String | `db1` | Yes | Database name. |
| `authType` | String | `Executor` | Yes | DLF access identity. Enumerated values:<br>• `Executor`: Executor (Development environment)<br>• `PrimaryAccount`: Primary account (Production environment)<br>• `SubAccount`: Specified sub-account (Production environment)<br>• `RamRole`: Specified RAM role (Production environment) |
| `authIdentity` | String | `123123` | No | Sub-account ID or Role ID. Required when `authType` is `SubAccount` or `RamRole`. |
| `envType` | String | `Dev` | Yes | Datasource environment information.<br>• `Dev`: Development environment<br>• `Prod`: Production environment |
| `endpoint` | String | `http://cn-hangzhou-vpc.dlf.aliyuncs.com` | Yes | DLF access endpoint. |

---

## Datasource Configuration Example

```json
{
  "envType": "Prod",
  "authType": "SubAccount",
  "database": "testdb01",
  "catalogId": "clg-paimon-xx",
  "catalogName": "xx",
  "endpoint": "http://cn-hangzhou-vpc.dlf.aliyuncs.com",
  "authIdentity": "xxx"
}
```
