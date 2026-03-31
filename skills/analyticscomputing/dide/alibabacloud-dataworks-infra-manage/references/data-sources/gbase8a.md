# GBASE 8A ConnectionProperties Documentation

## Data Source Type

- **Type**: `gbase8a`

## Supported Configuration Modes

- **ConnectionPropertiesMode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description & Notes |
|------|------|---------------|----------|---------------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only 1 set of host and port is allowed. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Represents the data source environment information.<br>- `Dev`: Development environment.<br>- `Prod`: Production environment. |

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
        "connectTimeout": "2000"
    },
    "username": "xxxxx",
    "password": "xxxxx",
    "envType": "Dev"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/gbase-8a
