# Hive Datasource Documentation

## Property Definition

- **Datasource Type**: `hive`
- **Supported Configuration Modes (ConnectionPropertiesMode)**:
  - `UrlMode` (Connection String Mode)
  - `InstanceMode` (Instance Mode)
  - `CdhMode` (CDH Cluster Mode)

---

## 1. Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | Region ID |
| `clusterId` | String | `c-d1a993bbcd298315` | Yes | Instance ID |
| `database` | String | `db1` | Yes | Database name |
| `version` | String | `2.3.9` | Yes | Hive version |
| `authType` | String | `Executor` | Yes | OSS access identity. Options: `Executor` (development environment), `PrimaryAccount` (production environment), `SubAccount` (specified sub-account), `RamRole` (specified RAM role) |
| `authIdentity` | String | `123123` | No | Sub-account ID or Role ID. Required when `authType` is `SubAccount` or `RamRole` |
| `loginMode` | String | `Anonymous` | Yes | Hive login method. **Only supports**: `Anonymous`, `LDAP` |
| `username` | String | `xxx` | No | Username. Required when using username/password login |
| `password` | String | `xxx` | No | Password. Required when using username/password login |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication. Options: `authTypeNone` (no auth), `authTypeSsl` (enable SSL), `authTypeKerberos` (enable Kerberos) |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference) |
| `truststorePassword` | String | `apasara` | No | Truststore password |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference) |
| `keystorePassword` | String | `apasara` | No | Keystore password |
| `kerberosFileConf` | String | `123123` | No | Kerberos configuration file (reference) |
| `kerberosFileKeytab` | String | `123123` | No | Kerberos Keytab file (reference) |
| `principal` | String | `xxx@com` | No | Kerberos principal |
| `hiveConfig` | JSON Object | `{"fs.oss.accessKeyId": "xxx"}` | No | Extended parameters |
| `envType` | String | `Dev` | Yes | Environment type. Options: `Dev` (development), `Prod` (production) |

---

## 2. Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `crossAccountOwnerId` | String | `11111` | Yes | Target Alibaba Cloud primary account UID |
| `crossAccountRoleName` | String | `xx-role` | Yes | Target RAM role name |
| `regionId` | String | `cn-shanghai` | Yes | Region ID |
| `clusterId` | String | `c-d1a993bbcd298315` | Yes | Instance ID |
| `database` | String | `db1` | Yes | Database name |
| `version` | String | `2.3.9` | Yes | Hive version |
| `authType` | String | `RamRole` | Yes | OSS access identity (fixed as `RamRole`) |
| `loginMode` | String | `Anonymous` | Yes | Hive login method. **Only supports**: `Anonymous`, `LDAP` |
| `username` | String | `xxx` | No | Username. Required when using username/password login |
| `password` | String | `xxx` | No | Password. Required when using username/password login |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication. Options: `authTypeNone`, `authTypeSsl`, `authTypeKerberos` |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference) |
| `truststorePassword` | String | `apasara` | No | Truststore password |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference) |
| `keystorePassword` | String | `apasara` | No | Keystore password |
| `kerberosFileConf` | String | `123123` | No | Kerberos configuration file (reference) |
| `kerberosFileKeytab` | String | `123123` | No | Kerberos Keytab file (reference) |
| `principal` | String | `xxx@com` | No | Kerberos principal |
| `hiveConfig` | JSON Object | `{"fs.oss.accessKeyId": "xxx"}` | No | Extended parameters |
| `envType` | String | `Dev` | Yes | Environment type. Options: `Dev`, `Prod` |

---

## 3. Connection String Mode (UrlMode)

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `address` | JSON Array | `[{"host":"127.0.0.1","port":"1234"}]` | Yes | Single host address and port only |
| `database` | String | `hive_database` | Yes | Database name |
| `metaType` | String | `HiveMetastore` | Yes | Metadata type. Options: `HiveMetastore`, `DLF1.0` |
| `metastoreUris` | String | `thrift://123:123` | Yes | Metastore URIs |
| `version` | String | `2.3.9` | Yes | Hive version |
| `accessId` | String | `xxxxx` | No | AccessKey ID. Required when `metaType` is `DLF` |
| `accessKey` | String | `xxxxx` | No | AccessKey Secret. Required when `metaType` is `DLF` |
| `properties` | JSON Object | `{"useSSL": "false"}` | No | Driver properties |
| `defaultFS` | String | `xxx` | No | Default FS |
| `loginMode` | String | `Anonymous` | Yes | Hive login method. **Only supports**: `Anonymous`, `LDAP` |
| `username` | String | `xxx` | No | Username. Required when using username/password login |
| `password` | String | `xxx` | No | Password. Required when using username/password login |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication. Options: `authTypeNone`, `authTypeSsl`, `authTypeKerberos` |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference) |
| `truststorePassword` | String | `apasara` | No | Truststore password |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference) |
| `keystorePassword` | String | `apasara` | No | Keystore password |
| `kerberosFileConf` | String | `123123` | No | Kerberos configuration file (reference) |
| `kerberosFileKeytab` | String | `123123` | No | Kerberos Keytab file (reference) |
| `principal` | String | `xxx@com` | No | Kerberos principal |
| `hiveConfig` | JSON Object | `{"fs.oss.accessKeyId": "xxx"}` | No | Extended parameters |
| `envType` | String | `Dev` | Yes | Environment type. Options: `Dev`, `Prod` |

---

## 4. CDH Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `clusterIdentifier` | String | `cdh_cluster` | Yes | CDH cluster identifier |
| `database` | String | `db1` | Yes | Database name |
| `defaultFS` | String | `xxx` | No | Default FS |
| `loginMode` | String | `Anonymous` | Yes | Hive login method. **Only supports**: `Anonymous`, `LDAP` |
| `username` | String | `xxx` | No | Username. Required when using username/password login |
| `password` | String | `xxx` | No | Password. Required when using username/password login |
| `securityProtocol` | String | `authTypeNone` | No | SSL authentication. Options: `authTypeNone`, `authTypeSsl` |
| `truststoreFile` | String | `1` | No | Truststore certificate file (reference) |
| `truststorePassword` | String | `apasara` | No | Truststore password |
| `keystoreFile` | String | `2` | No | Keystore certificate file (reference) |
| `keystorePassword` | String | `apasara` | No | Keystore password |
| `kerberosFileConf` | String | `123123` | No | Kerberos configuration file (reference) |
| `kerberosFileKeytab` | String | `123123` | No | Kerberos Keytab file (reference) |
| `principal` | String | `xxx@com` | No | Kerberos principal |
| `hiveConfig` | JSON Object | `{"fs.oss.accessKeyId": "xxx"}` | No | Extended parameters |
| `envType` | String | `Dev` | Yes | Environment type. Options: `Dev`, `Prod` |

---

## Configuration Examples

### Same-Account Instance Mode
```json
{
    "clusterId": "c-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "loginMode": "Anonymous",
    "version": "2.3.9",
    "authType": "Executor",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

### Cross-Account Instance Mode
```json
{
    "clusterId": "c-xxxxxxxxx",
    "regionId": "cn-shanghai",
    "database": "db",
    "loginMode": "LDAP",
    "version": "2.3.9",
    "authType": "Executor",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

### Connection String Mode
```json
{
    "address": [
        {
            "host": "127.0.0.1",
            "port": 10000
        }
    ],
    "database": "db",
    "properties": {
        "connectTimeout": "2000"
    },
    "username": "aliyun",
    "password": "xxx",
    "metastoreUris": "thrift://127.0.0.1:9083",
    "metaType": "HiveMetastore",
    "version": "2.3.9",
    "loginMode": "Anonymous",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

### CDH Mode
```json
{
    "clusterIdentifier": "c-xxxxxxxxx",
    "database": "db",
    "loginMode": "Anonymous",
    "authType": "Executor",
    "securityProtocol": "authTypeNone",
    "envType": "Dev"
}
```

---

## Important Notes

> ⚠️ **loginMode Parameter Note**: The `loginMode` parameter for Hive data sources **only supports** the following two values:
> - `Anonymous`: Anonymous login
> - `LDAP`: LDAP authentication login
>
> Other values such as `simple` and `disable` are **not supported** and will cause an error: `Unsupported loginMode=simple for Hive data source, only Anonymous and LDAP are supported`
