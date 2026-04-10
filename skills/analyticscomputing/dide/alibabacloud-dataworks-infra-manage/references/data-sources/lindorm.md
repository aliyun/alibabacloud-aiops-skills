# Lindorm Datasource Documentation

**Last Updated:** 2024-10-15 09:31:57

## Property Definition

| Property | Value |
|----------|-------|
| **Data Source Type (type)** | `lindorm` |
| **Supported Configuration Mode (ConnectionPropertiesMode)** | `UrlMode` (Connection String Mode), `InstanceMode` (Instance Mode) |

> **Note:**
> - **Wide Table Engine**: Only supports `UrlMode` (Connection String Mode).
> - **Compute Engine**: Supports both `UrlMode` and `InstanceMode`. `InstanceMode` supports cross-account access.

---

## Connection String Mode Parameters (UrlMode)

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `seedserver` | String | `ld-xxxxxxxxxxxxx.rds.aliyuncs.com:30020` | Yes | Connection address. |
| `username` | String | `user` | Yes | Username for accessing Lindorm. |
| `password` | String | `pass` | Yes | Password for accessing Lindorm. |
| `namespace` | String | `default` | Yes | Namespace / Database name. |
| `envType` | String | `Dev` | Yes | Environment type: `Dev` (Development), `Prod` (Production). |

---

## Instance Mode Parameters (InstanceMode)

> **Applicable to:** Compute Engine only.

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `regionId` | String | `cn-xxxxx` | Yes | Region ID. |
| `instanceId` | String | `ld-xxxxxxxxxxxxx` | Yes | Lindorm instance ID. |
| `namespace` | String | `db` | Yes | Namespace / Database name. |
| `username` | String | `user` | Yes | Username for accessing Lindorm. |
| `password` | String | `pass` | Yes | Password for accessing Lindorm. |
| `engineType` | String | `compute` | Yes | Engine type. Fixed value: `compute` (Compute Engine). |
| `envType` | String | `Prod` | Yes | Environment type: `Dev` (Development), `Prod` (Production). |
| `crossAccountOwnerId` | String | `111111111` | No | Target Alibaba Cloud primary account UID (cross-account only). |
| `crossAccountRoleName` | String | `xx-role` | No | Target RAM role name (cross-account only). |

---

## Configuration Examples

### Connection String Mode (UrlMode)

```json
{
  "seedserver": "ld-xxxxxxxxxxxxx.rds.aliyuncs.com:30020",
  "username": "user",
  "password": "pass",
  "namespace": "default",
  "envType": "Dev"
}
```

### Instance Mode (InstanceMode) - Compute Engine

```json
{
  "envType": "Prod",
  "engineType": "compute",
  "regionId": "cn-xxxxx",
  "instanceId": "ld-xxxxxxxxxxxxx",
  "namespace": "db",
  "username": "user",
  "password": "pass"
}
```

### Instance Mode (InstanceMode) - Cross-Account Compute Engine

```json
{
  "envType": "Prod",
  "engineType": "compute",
  "regionId": "cn-xxxxx",
  "instanceId": "ld-xxxxxxxxxxxxx",
  "namespace": "db",
  "username": "user",
  "password": "pass",
  "crossAccountOwnerId": "111111111",
  "crossAccountRoleName": "xx-role"
}
```

---

## API Reference Summary

- **Source:** DataWorks Developer Reference > Appendix > Data Source Connection Information (ConnectionProperties)
- **Platform:** Alibaba Cloud DataWorks
- **Navigation:** Previous: KingbaseES | Next: LogHub

## Related Lindorm OpenAPIs

| API | Description | Documentation |
|-----|-------------|---------------|
| `GetLindormInstance` | Get detailed information about a Lindorm instance. | [GetLindormInstance](https://help.aliyun.com/zh/lindorm/developer-reference/api-hitsdb-2020-06-15-getlindorminstance) |
| `GetLindormInstanceEngineList` | Get the list of engine types supported by a Lindorm instance. | [GetLindormInstanceEngineList](https://help.aliyun.com/zh/lindorm/developer-reference/api-hitsdb-2020-06-15-getlindorminstanceenginelist) |
| `GetLindormInstanceList` | Get the list of Lindorm instances. | [GetLindormInstanceList](https://help.aliyun.com/zh/lindorm/developer-reference/api-hitsdb-2020-06-15-getlindorminstancelist) |
