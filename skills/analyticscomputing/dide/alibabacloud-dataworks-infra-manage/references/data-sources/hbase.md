# HBase Datasource Documentation

## Overview

**Datasource Type:** `hbase`

**Supported Configuration Mode:** `UrlMode` (Connection String Mode)

---

## ConnectionProperties Parameters (UrlMode)

| Name | Type | Example Value | Required | Description & Notes |
|------|------|---------------|----------|---------------------|
| `hbaseConfig` | JSON Object | `{"hbase.zookeeper.quorum":"localhost:2181", "hbaseVersion":"0.9.4"}` | Yes | HBase configuration. |
| `securityProtocol` | String | `authTypeNone` | No | Authentication option. Valid values: `authTypeNone`, `authTypeClientPassword`, `authTypeKerberos` |
| `username` | String | `xxxx` | No | Username. Required when `authTypeClientPassword` is used. |
| `password` | String | `xxxx` | No | Password. Required when `authTypeClientPassword` is used. |
| `kerberosFileConf` | String | `<FILE_ID>` | No | Kerberos authentication Conf file (reference). Required when `authTypeKerberos` is used. |
| `kerberosFileKeytab` | String | `<FILE_ID>` | No | Kerberos authentication Keytab file (reference). Required when `authTypeKerberos` is used. |
| `principal` | String | `xxx@com` | No | Principal. |
| `envType` | String | `Dev` | Yes | Indicates the datasource environment. Valid values: `Dev` (Development environment), `Prod` (Production environment). |

---

## Configuration Example (UrlMode)

```json
{
  "hbaseConfig": {
    "hbase.zookeeper.quorum": "localhost:2181",
    "hbaseVersion": "0.9.4"
  },
  "securityProtocol": "authTypeClientPassword",
  "username": "xxxxx",
  "password": "xxxxx",
  "envType": "Dev"
}
```

---

## Authentication Types Summary

| Type | Description | Required Additional Parameters |
|------|-------------|-------------------------------|
| `authTypeNone` | No authentication | None |
| `authTypeClientPassword` | Username/password authentication | `username`, `password` |
| `authTypeKerberos` | Kerberos authentication | `kerberosFileConf`, `kerberosFileKeytab`, `principal` |

---

**Last Updated:** 2024-11-06
