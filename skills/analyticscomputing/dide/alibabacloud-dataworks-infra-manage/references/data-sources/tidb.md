# TiDB Datasource ConnectionProperties Documentation

## Property Definition

- **Datasource Type**: `tidb`
- **Supported Configuration Mode (ConnectionPropertiesMode)**:
  - `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `address` | JSONArray | `[{"host": "127.0.0.1", "port": "1234"}]` | Yes | Only allowed to configure as a single host address and single port format |
| `database` | String | `db1` | Yes | Database name |
| `username` | String | `user1` | Yes | Username |
| `password` | String | `pass1` | Yes | Password |
| `properties` | JSON Object | `{"queryTimeout": "1000"}` | No | Driver properties |
| `securityProtocol` | String | `authTypeNone` | No | Whether to use SSL authentication. Values:<br>- `authTypeNone` (No authentication)<br>- `authTypeSsl` (Enable SSL authentication)<br>Default: `authTypeNone` |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference). Required when `securityProtocol=authTypeSsl` |
| `truststorePassword` | String | `apasara` | No | Truststore password. Required when `securityProtocol=authTypeSsl` |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference) |
| `keystorePassword` | String | `apasara` | No | Keystore password |
| `envType` | String | `Dev` | Yes | `envType` indicates the datasource environment information:<br>- Development environment: `Dev`<br>- Production environment: `Prod` |

---

## Datasource Configuration Example

### Connection String Mode

Configuration via host address and port number:

```json
{
    "envType": "Prod",
    "securityProtocol": "authTypeNone",
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

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/tidb
