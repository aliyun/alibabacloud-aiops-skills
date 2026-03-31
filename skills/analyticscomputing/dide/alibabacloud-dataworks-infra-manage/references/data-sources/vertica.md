# Vertica DataSource ConnectionProperties Documentation

## Attribute Definition

- **Datasource type**: `vertica`
- **Supported configuration mode**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only allows configuration of 1 set of host and port. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | envType indicates datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

---

## Datasource Configuration Example

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

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/vertica
