# PolarDB MySQL & PostgreSQL ConnectionProperties

## Data Source Type: `polardb`

PolarDB supports both MySQL and PostgreSQL engine types.

---

## Mode 1: Same-Account Instance Mode

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regionId` | String | Yes | Region where the instance belongs |
| `clusterId` | String | Yes | PolarDB cluster ID |
| `database` | String | Yes | Database name |
| `dbType` | String | Yes | PolarDB engine type: `mysql` or `postgresql` |
| `username` | String | Yes | Username |
| `password` | String | Yes | Password |
| `securityProtocol` | String | No | SSL authentication: `authTypeNone` or `authTypeSsl` |
| `truststoreFile` | String | No | Truststore certificate file (reference) |
| `truststorePassword` | String | No | Truststore password |
| `keystoreFile` | String | No | Keystore certificate file (reference) |
| `keystorePassword` | String | No | Keystore password |
| `readOnlyDBInstance` | String | No | Read replica connection address |
| `envType` | String | Yes | Environment: `Dev` or `Prod` |

### Example (InstanceMode - MySQL):

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "clusterId": "pc-xxxxx",
  "dbType": "mysql",
  "database": "mydb",
  "username": "root",
  "password": "xxxxxx"
}
```

---

## Mode 2: Cross-Account Instance Mode

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `regionId` | String | Yes | Region where the instance belongs |
| `clusterId` | String | Yes | PolarDB cluster ID |
| `database` | String | Yes | Database name |
| `dbType` | String | Yes | PolarDB engine type: `mysql` or `postgresql` |
| `username` | String | Yes | Username |
| `password` | String | Yes | Password |
| `crossAccountOwnerId` | String | Yes | Cross-account target cloud account ID |
| `crossAccountRoleName` | String | Yes | Cross-account target RAM role name |
| `securityProtocol` | String | No | SSL authentication: `authTypeNone` or `authTypeSsl` |
| `envType` | String | Yes | Environment: `Dev` or `Prod` |

### Example (Cross-Account):

```json
{
  "envType": "Prod",
  "regionId": "cn-beijing",
  "clusterId": "pc-xxxxx",
  "dbType": "mysql",
  "database": "mydb",
  "username": "root",
  "password": "xxxxxx",
  "crossAccountOwnerId": "1234567890123456",
  "crossAccountRoleName": "cross-account-role"
}
```

---

## Mode 3: Connection String Mode

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dbType` | String | Yes | PolarDB engine type: `mysql` or `postgresql` |
| `address` | Array | Yes | Host addresses. Format: `[{"host": "127.0.0.1", "port": 3306}]` |
| `database` | String | Yes | Database name |
| `username` | String | Yes | Username |
| `password` | String | Yes | Password |
| `securityProtocol` | String | No | SSL authentication: `authTypeNone` or `authTypeSsl` |
| `properties` | JSON Object | No | Driver properties. Example: `{"useSSL": "false"}` |
| `envType` | String | Yes | Environment: `Dev` or `Prod` |

### Example (UrlMode - MySQL):

```json
{
  "envType": "Prod",
  "dbType": "mysql",
  "address": [{"host": "pc-xxxxx.rwlb.rds.aliyuncs.com", "port": 3306}],
  "database": "mydb",
  "username": "root",
  "password": "xxxxxx"
}
```

### Example (UrlMode - PostgreSQL):

```json
{
  "envType": "Prod",
  "dbType": "postgresql",
  "address": [{"host": "pc-xxxxx.rwlb.rds.aliyuncs.com", "port": 5432}],
  "database": "mydb",
  "username": "postgres",
  "password": "xxxxxx"
}
```
