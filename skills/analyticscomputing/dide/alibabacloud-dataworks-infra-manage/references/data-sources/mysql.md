# MySQL DataSource ConnectionProperties Documentation

## Overview

- **Data Source Type**: `mysql`
- **Supported Configuration Modes**:
  - `UrlMode` (Connection String Mode)
  - `InstanceMode` (Instance Mode)

---

## 1. Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance belongs. Note: Historical non-engine data sources may not have this value. |
| `instanceId` | String | `rm-xxxxxxxxx` | Yes | Instance ID. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication setting. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference). |
| `truststorePassword` | String | `apasara` | No | Truststore password. |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference). |
| `keystorePassword` | String | `apasara` | No | Keystore password. |
| `driverVersion` | String | `8.2.0` | No | Driver version. Enumerated values: (empty), `8.2.0`, `5.1.49`, `5.1.46`. |
| `authType` | String | `PrimaryAccount` | No | Required for OSS Binlog reading support. Values: `PrimaryAccount`, `SubAccount`, `RamRole`. |
| `authIdentity` | String | `123456` | No | Required when `authType` is `SubAccount` (specify sub-account ID) or `RamRole` (specify role ID). Not needed for cross-account scenarios. |
| `readOnlyDBInstance` | String | `rm-uf65l3bwae8w8r35` | No | Standby instance ID. |
| `envType` | String | `Dev` | Yes | Environment type. Values: `Dev` (development environment), `Prod` (production environment). |

### Example

```json
{
    "instanceId": "rm-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

---

## 2. Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance belongs. Note: Historical non-engine data sources may not have this value. |
| `instanceId` | String | `rm-xxxxxxxxx` | Yes | Instance ID. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `crossAccountOwnerId` | String | `1` | Yes | Cross-account target cloud account ID. |
| `crossAccountRoleName` | String | `mysql-role` | Yes | Cross-account target RAM role name. |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication setting. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference). |
| `truststorePassword` | String | `apasara` | No | Truststore password. |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference). |
| `keystorePassword` | String | `apasara` | No | Keystore password. |
| `driverVersion` | String | `8.2.0` | No | Driver version. Enumerated values: (empty), `8.2.0`, `5.1.49`, `5.1.46`. |
| `authType` | String | `PrimaryAccount` | No | Required for OSS Binlog reading support. Values: `RamRole`. |
| `readOnlyDBInstance` | String | `rm-uf65l3bwae8w8r35` | No | Standby instance ID. |
| `envType` | String | `Dev` | Yes | Environment type. Values: `Dev` (development environment), `Prod` (production environment). |

### Example

```json
{
    "instanceId": "rm-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "crossAccountOwnerId": "1234567890",
    "crossAccountRoleName": "my_ram_role",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

---

## 3. Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `address` | Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Allows configuration of multiple host addresses and ports. |
| `database` | String | `mysql_database` | Yes | Database name. |
| `username` | String | `xxxxx` | Yes | Username. |
| `password` | String | `xxxxx` | Yes | Password. |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication setting. Values: `authTypeNone` (no authentication), `authTypeSsl` (enable SSL authentication). |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference). |
| `truststorePassword` | String | `apasara` | No | Truststore password. |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference). |
| `keystorePassword` | String | `apasara` | No | Keystore password. |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| `envType` | String | `Dev` | Yes | Environment type. Values: `Dev` (development environment), `Prod` (production environment). |

### Example

```json
{
    "address": [
        {
            "host": "127.0.0.1",
            "port": 3306
        }
    ],
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx",
    "envType": "Dev"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/mysql
