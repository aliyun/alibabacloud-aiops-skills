# SAP HANA ConnectionProperties Documentation

## Property Definition

- **Datasource type (`type`)**: `saphana`
- **Supported configuration mode (`ConnectionPropertiesMode`)**: `UrlMode` (Connection String Mode)

---

## Connection String Mode

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Formally an array, but only **1 set of host and port** is allowed. |
| `database` | String | `mysql_database` | No | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Represents the datasource environment information.<br>- `Dev`: Development environment<br>- `Prod`: Production environment |

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

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/sap-hana
