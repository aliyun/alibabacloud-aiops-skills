# StarRocks Datasource - ConnectionProperties Documentation

## Overview

- **Datasource Type:** `starrocks`
- **Last Updated:** 2024-10-15 09:30:16

## Supported Configuration Modes

| Mode | Description |
|------|-------------|
| UrlMode | Connection string mode |
| InstanceMode | Instance mode |

---

## Query StarRocks Instances

Before creating a StarRocks data source, you can query the list of available instances.

### OLAP Type (Semi-Managed Mode)

> **Note**: OLAP type uses EMR API to query cluster list.

```bash
aliyun emr ListClusters --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" 2>/dev/null | jq -r '
  .Clusters[] | select(.ClusterType == "OLAP") |
  "Cluster ID: \(.ClusterId) | Name: \(.ClusterName) | Status: \(.ClusterState)"
'
```

### Serverless Type

> **Note**: The current aliyun CLI does not support querying the StarRocks Serverless instance list. Please guide users to obtain the instance ID manually through the [EMR Serverless StarRocks Console](https://emr.console.aliyun.com/).

**Steps to Get Instance ID**:
1. Log in to the [EMR Serverless StarRocks Console](https://emr.console.aliyun.com/)
2. Select the corresponding region
3. View the **Instance ID** in the instance list (format: `c-xxxxx`)
4. Use the instance ID for the `instanceId` parameter when creating the data source

---

## 1. Same-Account Instance Mode

| Field | Type | Example | Required | Description |
|-------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance resides |
| `instanceType` | String | `serverless` | Yes | Instance type. Options: `emr-olap` (semi-managed mode), `serverless` (serverless mode) |
| `instanceId` | String | `c-12345` | Yes | Instance mode instance ID |
| `database` | String | `dbName` | Yes | Database name |
| `username` | String | `srUser` | Yes | Username |
| `password` | String | `srPassword` | Yes | Password |
| `envType` | String | `Dev` | Yes | Datasource environment info. Options: `Dev` (development), `Prod` (production) |

### Example

```json
{
    "envType": "Prod",
    "instanceType": "serverless",
    "regionId": "cn-shanghai",
    "instanceId": "c-107e2047ef787c2e",
    "database": "my_database",
    "username": "xxxxx",
    "password": "xxxxx"
}
```

---

## 2. Cross-Account Instance Mode

| Field | Type | Example | Required | Description |
|-------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | The region where the instance resides |
| `instanceId` | String | `c-12345` | Yes | Instance mode instance ID |
| `instanceType` | String | `serverless` | Yes | Instance type. Options: `emr-olap` (semi-managed mode), `serverless` (serverless mode) |
| `database` | String | `dbName` | Yes | Database name |
| `crossAccountOwnerId` | String | `<ACCOUNT_ID>` | Yes | The target Alibaba Cloud main account ID for cross-account scenarios |
| `crossAccountRoleName` | String | `mc-accross-role-name` | Yes | Role name under the target account for cross-account scenarios |
| `username` | String | `srUser` | Yes | Username |
| `password` | String | `srPassword` | Yes | Password |
| `envType` | String | `Dev` | Yes | Datasource environment info. Options: `Dev` (development), `Prod` (production) |

### Example

```json
{
    "envType": "Prod",
    "instanceType": "serverless",
    "regionId": "cn-shanghai",
    "instanceId": "c-107e2047ef787c2e",
    "database": "my_database",
    "username": "xxxxx",
    "password": "xxxxx",
    "crossAccountRoleName": "cross-role",
    "crossAccountOwnerId": "123123123"
}
```

---

## 3. Connection String Mode

| Field | Type | Example | Required | Description |
|-------|------|---------|----------|-------------|
| `database` | String | `dbName` | Yes | Database name |
| `username` | String | `srUser` | Yes | Username |
| `password` | String | `srPassword` | Yes | Password |
| `properties` | JSON | `{"connectTimeout": "2000"}` | No | Connection string mode connection properties (key-value pairs) |
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Array format, but **only allows 1 set of host and port** |
| `loadAddress` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Array format, **allows 1 or more sets of host and port** |
| `envType` | String | `Dev` | Yes | Datasource environment info. Options: `Dev` (development), `Prod` (production) |

### Example

```json
{
    "envType": "Prod",
    "address": [
        {
            "host": "127.0.0.1",
            "port": 3306
        }
    ],
    "loadAddress": [
        {
            "host": "127.0.0.1",
            "port": 3306
        }
    ],
    "database": "asdf",
    "username": "xxxxx",
    "password": "xxxxx",
    "properties": {
        "socketTimeout": 2000
    }
}
```

---

## Quick Reference Summary

| Parameter | Instance Mode | Cross-Account Mode | Connection String Mode |
|-----------|---------------|-------------------|----------------------|
| `regionId` | Required | Required | - |
| `instanceId` | Required | Required | - |
| `instanceType` | Required | Required | - |
| `database` | Required | Required | Required |
| `username` | Required | Required | Required |
| `password` | Required | Required | Required |
| `envType` | Required | Required | Required |
| `address` | - | - | Required |
| `loadAddress` | - | - | Required |
| `properties` | - | - | Optional |
| `crossAccountOwnerId` | - | Required | - |
| `crossAccountRoleName` | - | Required | - |
