# PostgreSQL ConnectionProperties Documentation

## Attribute Definition

- **Datasource type**: `postgresql`
- **Supported configuration modes (ConnectionPropertiesMode)**:
  - `UrlMode` (Connection String Mode)
  - `InstanceMode` (Instance Mode)

---

## Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-shanghai | Yes | The region where the instance belongs. Note: Historical non-engine datasources may not have this value. |
| instanceId | String | pgm-xxxxxxxxx | Yes | Instance ID. |
| database | String | postgresql_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| securityProtocol | String | AuthTypeNone | No | SSL authentication setting. Values: `AuthTypeNone` (no authentication), `AuthTypeSsl` (enable SSL authentication). |
| truststoreFile | String | <FILE_ID> | No | Truststore certificate file (reference). |
| keystoreFile | String | <FILE_ID> | No | Keystore certificate file (reference). |
| keyFile | String | <FILE_ID> | No | Private key file (reference). |
| clientPassword | String | abc | No | Private key password. |
| readOnlyDBInstance | String | pgr-uf65l3bwae8w8r35 | No | Read-only replica instance ID. |
| envType | String | Dev | Yes | Datasource environment information. Values: `Dev` (development environment), `Prod` (production environment). |

---

## Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| regionId | String | cn-shanghai | Yes | The region where the instance belongs. Note: Historical non-engine datasources may not have this value. |
| instanceId | String | pgm-xxxxxxxxx | Yes | Instance ID. |
| database | String | postgresql_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| crossAccountOwnerId | String | 1 | Yes | Cross-account target cloud account ID. |
| crossAccountRoleName | String | postgresql-role | Yes | Cross-account target RAM role name. |
| securityProtocol | String | AuthTypeNone | No | SSL authentication setting. Values: `AuthTypeNone` (no authentication), `AuthTypeSsl` (enable SSL authentication). |
| truststoreFile | String | <FILE_ID> | No | Truststore certificate file (reference). |
| keystoreFile | String | <FILE_ID> | No | Keystore certificate file (reference). |
| keyFile | String | <FILE_ID> | No | Private key file (reference). |
| clientPassword | String | abc | No | Private key password. |
| readOnlyDBInstance | String | pgr-uf65l3bwae8w8r35 | No | Read-only replica instance ID. |
| envType | String | Dev | Yes | Datasource environment information. Values: `Dev` (development environment), `Prod` (production environment). |

---

## Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| address | Array | `[{"host": "127.0.0.1", "port": 5432}]` | Yes | Allows configuration of multiple host addresses and ports. |
| database | String | postgresql_database | Yes | Database name. |
| username | String | xxxxx | Yes | Username. |
| password | String | xxxxx | Yes | Password. |
| securityProtocol | String | AuthTypeNone | No | SSL authentication setting. Values: `AuthTypeNone` (no authentication), `AuthTypeSsl` (enable SSL authentication). |
| truststoreFile | String | <FILE_ID> | No | Truststore certificate file (reference). |
| keystoreFile | String | <FILE_ID> | No | Keystore certificate file (reference). |
| keyFile | String | <FILE_ID> | No | Private key file (reference). |
| clientPassword | String | abc | No | Private key password. |
| properties | JSON Object | `{"useSSL": "false"}` | No | Driver properties. |
| envType | String | Dev | Yes | Datasource environment information. Values: `Dev` (development environment), `Prod` (production environment). |

---

## Datasource Configuration Examples

### Same-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "pgm-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "securityProtocol": "AuthTypeNone"
}
```

### Cross-Account Instance Mode

```json
{
    "envType": "Prod",
    "instanceId": "pgm-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "username": "aliyun",
    "password": "xxx",
    "securityProtocol": "AuthTypeNone",
    "crossAccountOwnerId": "1234567890",
    "crossAccountRoleName": "my_ram_role"
}
```

### Connection String Mode

```json
{
    "envType": "Prod",
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
    "username": "aliyun",
    "password": "xxx"
}
```

---

**Source**: https://help.aliyun.com/zh/dataworks/developer-reference/postgresql
