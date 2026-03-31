# DB2 ConnectionProperties Documentation

## Overview

- **Datasource Type**: `db2`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only allows configuration of one set of host and port. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `jdbcDriver` | String | `db2_1` | Yes | DB2 model type. Valid values: `db2_1`, `as400_1`, `db2_2` |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"currentSchema": "abc"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Represents the datasource environment information. Valid values: `Dev` (Development environment), `Prod` (Production environment). |

---

## Configuration Example

### Connection String Mode

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
        "currentSchema": "abc"
    },
    "jdbcDriver": "db2_1",
    "username": "xxxxx",
    "password": "xxxxx",
    "envType": "Dev"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/db2
