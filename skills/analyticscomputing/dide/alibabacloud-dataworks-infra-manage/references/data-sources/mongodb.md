# MongoDB Datasource Documentation

## Property Definition

- **Datasource Type**: `mongodb`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode`, `UrlMode`

---

## InstanceMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the MongoDB instance belongs. |
| `instanceId` | String | `dds-2zebc89f45b238b4` | Yes | MongoDB instance ID. |
| `database` | String | `my_db` | Yes | Database name. |
| `username` | String | `root` | Yes | Username. |
| `password` | String | `xxx` | Yes | Password. |
| `authDb` | String | `admin` | Yes | Authentication database. |
| `engineVersion` | String | `4.x` | No | MongoDB engine version. Values: `4.x`, `5.x`, `6.x`, `7.x`. |
| `authType` | String | `authTypeNone` | No | Authentication method. Values:<br>• `authTypeNone`: No SSL<br>• `authTypeSsl`: SSL authentication |
| `truststoreFile` | String | `<FILE_ID>` | Conditional | Truststore certificate file ID. Required when `authType=authTypeSsl`. |
| `truststorePassword` | String | `xxx` | No | Truststore password. |
| `properties` | JSON Object | `{"ssl": "true"}` | No | Advanced properties. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": "27017"}]` | Yes | MongoDB connection address. |
| `database` | String | `my_db` | Yes | Database name. |
| `username` | String | `root` | Yes | Username. |
| `password` | String | `xxx` | Yes | Password. |
| `authDb` | String | `admin` | Yes | Authentication database. |
| `engineVersion` | String | `4.x` | No | MongoDB engine version. Values: `4.x`, `5.x`, `6.x`, `7.x`. |
| `authType` | String | `authTypeNone` | No | Authentication method. Values:<br>• `authTypeNone`: No SSL<br>• `authTypeSsl`: SSL authentication |
| `truststoreFile` | String | `<FILE_ID>` | Conditional | Truststore certificate file ID. Required when `authType=authTypeSsl`. |
| `truststorePassword` | String | `xxx` | No | Truststore password. |
| `properties` | JSON Object | `{"ssl": "true"}` | No | Advanced properties. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### InstanceMode

```json
{
  "envType": "Prod",
  "instanceId": "dds-xxxxx",
  "regionId": "cn-shanghai",
  "database": "my_db",
  "username": "root",
  "password": "<PASSWORD>",
  "authDb": "admin",
  "engineVersion": "5.x"
}
```

### UrlMode

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "27017"}],
  "database": "my_db",
  "username": "root",
  "password": "<PASSWORD>",
  "authDb": "admin",
  "engineVersion": "5.x"
}
```

### UrlMode with SSL

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "27017"}],
  "database": "my_db",
  "username": "root",
  "password": "<PASSWORD>",
  "authDb": "admin",
  "engineVersion": "5.x",
  "authType": "authTypeSsl",
  "truststoreFile": "<FILE_ID>"
}
```
