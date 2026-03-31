# SQL Server ConnectionProperties Documentation

## Overview

- **Datasource Type**: `sqlserver`
- **Supported Configuration Modes (ConnectionPropertiesMode)**:
  - UrlMode (Connection String Mode)
  - InstanceMode (Instance Mode)

---

## Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-shanghai | Yes | SQL Server instance region |
| instanceId | String | rm-xxxxx | Yes | SQL Server instance ID |
| database | String | db1 | Yes | Database name |
| username | String | user1 | Yes | Username |
| password | String | pass1 | Yes | Password |
| securityProtocol | String | authTypeNone | No | SSL authentication option. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). Default: `authTypeNone` |
| truststoreFile | String | 1 | No | Truststore certificate file (reference). Required when `securityProtocol=authTypeSsl` |
| truststorePassword | String | apasara | No | Truststore password. Required when `securityProtocol=authTypeSsl` |
| readOnlyDBInstance | String | rm-xxxxx | No | Read-only replica instance ID |
| envType | String | Dev | Yes | Datasource environment information. `Dev` for development environment, `Prod` for production environment |

---

## Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-shanghai | Yes | SQL Server instance region |
| instanceId | String | rm-xxxxx | Yes | SQL Server instance ID |
| database | String | db1 | Yes | Database name |
| username | String | user1 | Yes | Username |
| password | String | pass1 | Yes | Password |
| crossAccountOwnerId | String | 11111 | No | Cross-account owner's primary account ID. Required for cross-account scenarios |
| crossAccountRoleName | String | role-name | No | Role name in the target account for cross-account scenarios |
| securityProtocol | String | authTypeNone | No | SSL authentication option. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). Default: `authTypeNone` |
| truststoreFile | String | 1 | No | Truststore certificate file (reference). Required when `securityProtocol=authTypeSsl` |
| truststorePassword | String | apasara | No | Truststore password. Required when `securityProtocol=authTypeSsl` |
| readOnlyDBInstance | String | rm-xxxxx | No | Read-only replica instance ID |
| envType | String | Dev | Yes | Datasource environment information. `Dev` for development environment, `Prod` for production environment |

---

## Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| address | JSONArray | `[{"host": "127.0.0.1", "port": "1234"}]` | Yes | Only single host address and single port configuration is allowed |
| database | String | db1 | Yes | Database name |
| username | String | user1 | Yes | Username |
| password | String | pass1 | Yes | Password |
| properties | JSON Object | `{"queryTimeout":"1000"}` | No | Driver properties |
| securityProtocol | String | authTypeNone | No | SSL authentication option. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). Default: `authTypeNone` |
| truststoreFile | String | 1 | No | Truststore certificate file (reference). Required when `securityProtocol=authTypeSsl` |
| truststorePassword | String | apasara | No | Truststore password. Required when `securityProtocol=authTypeSsl` |
| envType | String | Dev | Yes | Datasource environment information. `Dev` for development environment, `Prod` for production environment |

---

## Configuration Examples

### Same-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "rm-xxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "securityProtocol": "authTypeNone"
}
```

### Cross-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "rm-xxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "securityProtocol": "authTypeNone",
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
            "port": 5432
        }
    ],
    "database": "db",
    "properties": {
        "queryTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/sql-server
