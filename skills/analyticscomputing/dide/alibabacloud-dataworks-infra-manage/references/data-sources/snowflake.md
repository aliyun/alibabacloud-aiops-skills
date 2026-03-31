# Snowflake Datasource Documentation

## Property Definition

- **Datasource Type**: `snowflake`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `UrlMode` (Connection String Mode)

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `accountUrl` | String | `xy12345.snowflakecomputing.com` | Yes | Complete account URL. Format: `account_locator.cloud_region_id` or `account_locator.cloud_region_id.cloud` or `account_locator.gov_compliance.cloud_region_id.cloud` |
| `warehouseName` | String | `my_warehouse` | No | Compute resource, similar to Hologres compute group. |
| `database` | String | `my_db` | Yes | Database name to access. |
| `securityProtocol` | String | `authTypeClientPassword` | Yes | Authentication method. Values:<br>• `authTypeClientPassword`: Password authentication (default)<br>• `authTypePrivateKey`: Private key authentication |
| `username` | String | `myuser` | Yes | Username. |
| `password` | String | `xxx` | Conditional | Password. Required when `securityProtocol=authTypeClientPassword`. |
| `privateKeyFileId` | Long | `123` | Conditional | PEM format private key file ID. Required when `securityProtocol=authTypePrivateKey`. |
| `privateKeyPassword` | String | `xxx` | No | Password for PEM format private key. |
| `role` | String | `my_role` | No | Role for data access. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### Password Authentication Mode

```json
{
  "envType": "Prod",
  "accountUrl": "xy12345.snowflakecomputing.com",
  "database": "my_db",
  "securityProtocol": "authTypeClientPassword",
  "username": "myuser",
  "password": "<PASSWORD>",
  "warehouseName": "my_warehouse"
}
```

### Private Key Authentication Mode

```json
{
  "envType": "Prod",
  "accountUrl": "xy12345.snowflakecomputing.com",
  "database": "my_db",
  "securityProtocol": "authTypePrivateKey",
  "username": "myuser",
  "privateKeyFileId": "<FILE_ID>",
  "privateKeyPassword": "<PASSWORD>",
  "role": "my_role"
}
```
