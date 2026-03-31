# DRDS Datasource Documentation

## Property Definition

- **Datasource Type**: `drds`
- **Supported Configuration Mode (ConnectionPropertiesMode)**: `InstanceMode`, `UrlMode`

---

## InstanceMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | DRDS instance region. |
| `instanceId` | String | `drdsfacbzeu9f7z2` | Yes | DRDS instance ID. |
| `database` | String | `db1` | Yes | Database name. |
| `username` | String | `user1` | Yes | Username. |
| `password` | String | `pass1` | Yes | Password. |
| `crossAccountOwnerId` | String | `<ACCOUNT_ID>` | No | Cross-account target Alibaba Cloud main account ID. |
| `crossAccountRoleName` | String | `role-name` | No | Cross-account role name. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## UrlMode Parameters

| Name | Type | Example Value | Required | Description |
|------|------|---------------|----------|-------------|
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": "3306"}]` | Yes | Connection address. Only single host/port configuration allowed. |
| `database` | String | `db1` | Yes | Database name. |
| `username` | String | `user1` | Yes | Username. |
| `password` | String | `pass1` | Yes | Password. |
| `properties` | JSON Object | `{"prop1": "value1"}` | No | Driver properties. |
| `envType` | String | `Prod` | Yes | Environment type. Values: `Dev`, `Prod`. |

---

## Configuration Examples

### InstanceMode

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "instanceId": "drds-xxxxx",
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```

### InstanceMode (Cross-Account)

```json
{
  "envType": "Prod",
  "regionId": "cn-shanghai",
  "instanceId": "drds-xxxxx",
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>",
  "crossAccountOwnerId": "<ACCOUNT_ID>",
  "crossAccountRoleName": "cross-account-role"
}
```

### UrlMode

```json
{
  "envType": "Prod",
  "address": [{"host": "192.168.1.100", "port": "3306"}],
  "database": "mydb",
  "username": "root",
  "password": "<PASSWORD>"
}
```
