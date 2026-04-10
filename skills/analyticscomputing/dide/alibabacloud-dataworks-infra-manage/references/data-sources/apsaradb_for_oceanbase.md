# OceanBase ConnectionProperties Documentation

## Property Definition

- **Datasource Type**: `apsaradb_for_oceanbase`
- **Supported Configuration Modes (ConnectionPropertiesMode)**:
  - UrlMode (Connection String Mode)
  - InstanceMode (Instance Mode)

---

## Same-Account Instance Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| regionId | String | cn-shanghai | Yes | The Region where the instance belongs. |
| instanceId | String | ob5nj51ns6qjr4 | Yes | OceanBase cluster instance ID. |
| tenant | String | t5nnecr8dppi8 | Yes | OceanBase tenant ID. |
| database | String | ob_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| readOnlyDBInstance | String | t62zwpvyehmps-ro0.cn-beijing.oceanbase.aliyuncs.com:1521 | No | Standby database address. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Cross-Account Instance Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| regionId | String | cn-shanghai | Yes | The Region where the instance belongs. |
| instanceId | String | ob5nj51ns6qjr4 | Yes | OceanBase cluster instance ID. |
| tenant | String | t5nnecr8dppi8 | Yes | OceanBase tenant ID. |
| database | String | ob_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| crossAccountOwnerId | String | 1 | Yes | Cross-account target cloud account ID. |
| crossAccountRoleName | String | cross-role | Yes | Cross-account target RAM role name. |
| readOnlyDBInstance | String | t62zwpvyehmps-ro0.cn-beijing.oceanbase.aliyuncs.com:1521 | No | Standby database address. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Connection String Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| dbMode | String | mysql | No | Database mode. Valid values:<br>- `mysql`<br>- `oracle` |
| address | Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Only a single address is allowed. |
| database | String | ob_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| properties | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Datasource Configuration Examples

### Same-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "obxxxxxxxxxx",
    "tenant": "txxxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx"
}
```

### Cross-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "obxxxxxxxxxx",
    "tenant": "txxxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "crossAccountOwnerId": "1234567890",
    "crossAccountRoleName": "my_ram_role"
}
```

### Connection String Mode

```json
{
    "envType": "Prod",
    "address": [
        {
            "host": "127.0.0.1",
            "port": "5432"
        }
    ],
    "dbMode": "mysql",
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/oceanbase
