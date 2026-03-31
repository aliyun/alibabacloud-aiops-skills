# DM (Dameng) Datasource ConnectionProperties Documentation

## Overview

- **Datasource Type**: `dm`
- **Supported Configuration Mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only allows configuration of **1 set** of host and port. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"schema": "db1"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Indicates the datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

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
    "properties": {
        "schema": "db1"
    },
    "username": "xxxxx",
    "password": "xxxxx",
    "envType": "Dev"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/dm
