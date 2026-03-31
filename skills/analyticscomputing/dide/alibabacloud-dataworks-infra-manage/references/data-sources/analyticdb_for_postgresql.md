# AnalyticDB PostgreSQL DataSource Documentation

## Overview

- **DataSource Type**: `analyticdb_for_postgresql`
- **Supported Configuration Modes**:
  - `UrlMode` (Connection String Mode)
  - `InstanceMode` (Instance Mode)

---

## Configuration Modes

### 1. Same-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | ADB PostgreSQL instance Region. |
| `instanceId` | String | `gp-xxxxx` | Yes | ADB PostgreSQL instance ID. |
| `database` | String | `database_demo` | Yes | ADB PostgreSQL database name. |
| `username` | String | `xxxxx` | Yes | ADB PostgreSQL database access username. |
| `password` | String | `xxxxx` | Yes | ADB PostgreSQL database access password. |
| `envType` | String | `Dev` | Yes | Datasource environment info. Values: `Dev` (Development), `Prod` (Production). |

**Example:**
```json
{
    "database": "dw",
    "password": "***",
    "instanceId": "gp-xxxxx",
    "regionId": "cn-hangzhou",
    "envType": "Prod",
    "username": "dw"
}
```

---

### 2. Cross-Account Instance Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `regionId` | String | `cn-shanghai` | Yes | ADB PostgreSQL instance Region. |
| `instanceId` | String | `gp-xxxxx` | Yes | ADB PostgreSQL instance ID. |
| `database` | String | `database_demo` | Yes | ADB PostgreSQL database name. |
| `username` | String | `xxxxx` | Yes | ADB PostgreSQL database access username. |
| `password` | String | `xxxxx` | Yes | ADB PostgreSQL database access password. |
| `crossAccountOwnerId` | String | `<ACCOUNT_ID>` | Yes | Cross-account target Alibaba Cloud main account ID (required for cross-account scenarios). |
| `crossAccountRoleName` | String | `dw-ds2.0-role` | Yes | Role name under the target account for cross-account scenarios. |
| `envType` | String | `Dev` | Yes | Datasource environment info. Values: `Dev` (Development), `Prod` (Production). |

**Example:**
```json
{
    "crossAccountOwnerId": "<ACCOUNT_ID>",
    "crossAccountRoleName": "dw-role",
    "database": "dw",
    "password": "***",
    "instanceId": "gp-xxxxx",
    "regionId": "cn-shanghai",
    "envType": "Prod",
    "username": "dw"
}
```

---

### 3. Connection String Mode

| Name | Type | Example | Required | Description |
|------|------|---------|----------|-------------|
| `database` | String | `database_demo` | Yes | ADB PostgreSQL database name. |
| `username` | String | `xxxxx` | Yes | ADB PostgreSQL database access username. |
| `password` | String | `xxxxx` | Yes | ADB PostgreSQL database access password. |
| `address` | JSON Array | `[{"host": "127.0.0.1", "port": 3306}]` | Yes | Array format, but only allows 1 set of host and port configuration. |
| `properties` | JSONObject | - | No | JDBC connection advanced parameters. |
| `envType` | String | `Dev` | Yes | Datasource environment info. Values: `Dev` (Development), `Prod` (Production). |

**Example:**
```json
{
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
    "password": "xxx",
    "envType": "Dev"
}
```

---

## Summary Table

| Mode | Required Parameters |
|------|---------------------|
| Same-Account Instance | `regionId`, `instanceId`, `database`, `username`, `password`, `envType` |
| Cross-Account Instance | `regionId`, `instanceId`, `database`, `username`, `password`, `crossAccountOwnerId`, `crossAccountRoleName`, `envType` |
| Connection String | `address`, `database`, `username`, `password`, `envType` (optional: `properties`) |
