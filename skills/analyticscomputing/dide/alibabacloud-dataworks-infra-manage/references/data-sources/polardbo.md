# PolarDB-O ConnectionProperties Documentation

## Overview

| Attribute | Value |
|-----------|-------|
| **Datasource Type** | `polardbo` |
| **Supported ConnectionPropertiesMode** | `UrlMode` (Connection String Mode), `InstanceMode` (Instance Mode) |

---

## Configuration Modes

### 1. Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance is located. **Note:** Historical non-engine datasource records may not have this value. |
| `instanceId` | String | `pc-xxxxx` | Yes | PolarDB O cluster ID. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `envType` | String | `Dev` | Yes | Datasource environment information. Values: `Dev` (Development environment), `Prod` (Production environment). |

**Example:**

```json
{
    "envType": "Prod",
    "ownerId": "<ACCOUNT_ID>",
    "regionId": "cn-beijing",
    "instanceId": "pxc-bjrikym49rir1s",
    "database": "my_database",
    "username": "my_username",
    "password": "<PASSWORD>",
    "properties": {
        "socketTimeout": "2000"
    }
}
```

---

### 2. Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance is located. **Note:** Historical non-engine datasource records may not have this value. |
| `instanceId` | String | `pc-xxxxx` | Yes | PolarDB O cluster ID. |
| `database` | String | `polardbx_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `crossAccountOwnerId` | String | `1` | Yes | Cross-account target cloud account ID. |
| `crossAccountRoleName` | String | `cross-role` | Yes | Cross-account target RAM role name. |
| `envType` | String | `Dev` | Yes | Datasource environment information. Values: `Dev` (Development environment), `Prod` (Production environment). |

**Example:**

```json
{
    "envType": "Prod",
    "regionId": "cn-beijing",
    "instanceId": "pxc-bjrikym49rir1s",
    "database": "my_database",
    "username": "my_username",
    "password": "<PASSWORD>",
    "properties": {
        "socketTimeout": "2000"
    },
    "crossAccountOwnerId": "123123123",
    "crossAccountRoleName": "cross-role"
}
```

---

### 3. Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `address` | Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Only a single address is allowed. |
| `database` | String | `polardbx_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Datasource environment information. Values: `Dev` (Development environment), `Prod` (Production environment). |

**Example:**

```json
{
    "envType": "Prod",
    "address": [
        {
            "host": "127.0.0.1",
            "port": "3306"
        }
    ],
    "database": "my_database",
    "username": "my_username",
    "password": "<PASSWORD>",
    "properties": {
        "socketTimeout": "2000"
    }
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/polardb-o
