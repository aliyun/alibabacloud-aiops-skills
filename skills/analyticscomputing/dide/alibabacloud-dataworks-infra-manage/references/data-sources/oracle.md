# Oracle DataSource ConnectionProperties Documentation

## Property Definition

- **Data source type**: `oracle`
- **Supported configuration mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## Connection String Mode Parameters

| Name | Type | Example Value | Required | Description and Notes |
|------|------|---------------|----------|----------------------|
| `jdbcUrl` | String | `jdbc:oracle:thin:@host:port:SID` | Yes | Oracle's jdbcUrl. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `securityProtocol` | String | `authTypeNone` | No | Authentication option. Valid values: `authTypeNone`, `authTypeSsl`. |
| `truststoreFile` | String | `123` | No | Truststore file ID. Required when `securityProtocol` is `authTypeSsl`. |

---

## DataSource Configuration Example

### Connection String Mode

```json
{
  "jdbcUrl": "jdbc:oracle:thin:@host:port:SID",
  "username": "xxxxx",
  "password": "xxxxx",
  "securityProtocol": "authTypeNone",
  "envType": "Dev"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/oracle
