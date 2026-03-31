# AnalyticDB MySQL Datasource Documentation

## Overview

**Last Updated:** October 17, 2024, 10:22:06

## Property Definition

- **Datasource Type:** `analyticdb_for_mysql`
- **Supported Configuration Modes (ConnectionPropertiesMode):**
  - UrlMode (Connection String Mode)
  - InstanceMode (Instance Mode)

---

## Same Account Instance Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| regionId | String | cn-shanghai | Yes | The Region where the ADB MySQL instance is located. |
| instanceId | String | am-xxxxx | Yes | The ADB MySQL instance ID. |
| database | String | database_demo | Yes | ADB MySQL database name. |
| username | String | xxxxx | Yes | Username for ADB MySQL database access. |
| password | String | xxxxx | Yes | Password for ADB MySQL database access. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>• **Dev:** Development environment.<br>• **Prod:** Production environment. |

### Configuration Example - Same Account Instance Mode

```json
{
    "database": "database",
    "password": "***",
    "instanceId": "am-xxxxx",
    "regionId": "cn-shanghai",
    "envType": "Dev",
    "username": "username"
}
```

---

## Cross-Account Instance Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| regionId | String | cn-shanghai | Yes | The Region where the ADB MySQL instance is located. |
| instanceId | String | am-xxxxx | Yes | The ADB MySQL instance ID. |
| database | String | database_demo | Yes | ADB MySQL database name. |
| username | String | xxxxx | Yes | Username for ADB MySQL database access. |
| password | String | xxxxx | Yes | Password for ADB MySQL database access. |
| crossAccountOwnerId | String | <ACCOUNT_ID> | Yes | The cross-AliCloud master account ID of the other party; required in cross-account scenarios. |
| crossAccountRoleName | String | dw-ds2.0-role | Yes | The role name under the other party's account in cross-account scenarios. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>• **Dev:** Development environment.<br>• **Prod:** Production environment. |

### Configuration Example - Cross-Account Instance Mode

```json
{
    "database": "database",
    "password": "***",
    "instanceId": "am-xxxxx",
    "regionId": "cn-shanghai",
    "envType": "Dev",
    "username": "username",
    "crossAccountOwnerId": "<ACCOUNT_ID>",
    "crossAccountRoleName": "dw-ds2.0-role"
}
```

---

## Connection String Mode (UrlMode)

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| database | String | database_demo | Yes | ADB MySQL database name. |
| username | String | xxxxx | Yes | Username for ADB MySQL database access. |
| password | String | xxxxx | Yes | Password for ADB MySQL database access. |
| address | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Structured as an array, but only allows configuration of 1 set of host and port. |
| properties | JSONObject | - | No | JDBC connection advanced parameters. |
| envType | String | Dev | Yes | envType indicates the datasource environment information.<br>• **Dev:** Development environment.<br>• **Prod:** Production environment. |

### Configuration Example - Connection String Mode

```json
{
    "address": [
        {
            "host": "127.0.0.1",
            "port": 5432
        }
    ],
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx",
    "envType": "Dev"
}
```

---

## Summary

| Configuration Mode | Use Case | Key Parameters |
|-------------------|----------|----------------|
| **Same Account Instance Mode** | Connect to ADB MySQL within the same AliCloud account | regionId, instanceId, database, username, password, envType |
| **Cross-Account Instance Mode** | Connect to ADB MySQL in another AliCloud account | regionId, instanceId, database, username, password, crossAccountOwnerId, crossAccountRoleName, envType |
| **Connection String Mode** | Connect using direct host/port connection | address, database, username, password, properties (optional), envType |
