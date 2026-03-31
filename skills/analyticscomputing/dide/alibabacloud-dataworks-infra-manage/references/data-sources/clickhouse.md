# ClickHouse Datasource Documentation

## Property Definition

- **Datasource Type**: `clickhouse`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description & Notes |
|------|------|---------------|----------|---------------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 8123}]` | Yes | Only a single address is allowed. ClickHouse HTTP port is typically 8123, native port is 9000. |
| `database` | String | `xxx_db` | Yes | ClickHouse database name. |
| `properties` | JSONObject | `{"useSSL": "false"}` | No | Driver properties. |
| `username` | String | `xxx_username` | Yes | Username for ClickHouse database access. |
| `password` | String | `xxx_password` | Yes | Password for ClickHouse database access. |
| `securityProtocol` | String | `authTypeNone` | No | Authentication method. Enum values:<br>• `authTypeNone`: No SSL configuration<br>• `authTypeSsl`: SSL enabled<br>**Default**: `authTypeNone` |
| `sslRootCertificateFile` | String | `123` | No | SSL certificate ID. Required when `securityProtocol` is `authTypeSsl`. |
| `envType` | String | `Dev` | Yes | Datasource environment information.<br>• `Dev`: Development environment<br>• `Prod`: Production environment |

---

## Datasource Configuration Example

### Connection String Mode

```json
{
    "address": [
        {
            "host": "127.0.0.1",
            "port": 8123
        }
    ],
    "securityProtocol": "authTypeNone",
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx",
    "envType": "Dev"
}
```
