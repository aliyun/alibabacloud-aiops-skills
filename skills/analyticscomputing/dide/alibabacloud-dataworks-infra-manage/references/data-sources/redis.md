# Redis Datasource Documentation

## Property Definition

- **Datasource Type**: `redis`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode`, `UrlMode`

---

## InstanceMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `instanceId` | String | `r-2zelhj0qqp6tvxyxql` | Yes | Redis instance ID. |
| `password` | String | `xxx` | Yes | Password. |
| `regionId` | String | `cn-beijing` | Yes | Region where the instance belongs. |
| `securityProtocol` | String | `authTypeNone` | Yes | Authentication method. Values:<br>• `authTypeNone`: No SSL<br>• `authTypeSsl`: SSL authentication |
| `truststoreFile` | String | `<FILE_ID>` | Conditional | Truststore certificate file ID. Required when `securityProtocol=authTypeSsl`. |
| `truststorePassword` | String | `xxx` | No | Truststore password. |
| `keystoreFile` | String | `<FILE_ID>` | No | Keystore certificate file ID. |
| `keystorePassword` | String | `xxx` | No | Keystore password. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": "6379"}]` | Yes | Redis connection address. Only single host/port configuration allowed. |
| `password` | String | `xxx` | Yes | Password. |
| `securityProtocol` | String | `authTypeNone` | Yes | Authentication method. Values:<br>• `authTypeNone`: No SSL<br>• `authTypeSsl`: SSL authentication |
| `truststoreFile` | String | `<FILE_ID>` | Conditional | Truststore certificate file ID. Required when `securityProtocol=authTypeSsl`. |
| `truststorePassword` | String | `xxx` | No | Truststore password. |
| `keystoreFile` | String | `<FILE_ID>` | No | Keystore certificate file ID. |
| `keystorePassword` | String | `xxx` | No | Keystore password. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### InstanceMode

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "instanceId": "r-xxxxx",
  "password": "<PASSWORD>",
  "securityProtocol": "authTypeNone"
}
```

### InstanceMode with SSL

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "instanceId": "r-xxxxx",
  "password": "<PASSWORD>",
  "securityProtocol": "authTypeSsl",
  "truststoreFile": "<FILE_ID>"
}
```

### UrlMode

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "6379"}],
  "password": "<PASSWORD>",
  "securityProtocol": "authTypeNone"
}
```
