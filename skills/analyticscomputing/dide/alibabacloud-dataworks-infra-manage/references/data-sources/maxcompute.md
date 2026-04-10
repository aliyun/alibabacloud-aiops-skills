# MaxCompute Datasource Documentation

## Overview

| Property | Value |
|----------|-------|
| **Datasource Type** | `maxcompute` |
| **Supported Configuration Mode** | `UrlMode` (Connection String Mode) |

---

## Query MaxCompute Projects

Before creating a MaxCompute data source, you can query the list of available MaxCompute projects.

> **Reference**: [MaxCompute ListProjects API](https://help.aliyun.com/zh/maxcompute/user-guide/api-maxcompute-2022-01-04-listprojects)

```bash
aliyun maxcompute ListProjects --user-agent AlibabaCloud-Agent-Skills --RegionId "<REGION>" --maxItem 50 2>/dev/null | jq -r '
  .data.projects[] |
  "Project Name: \(.name) | Status: \(.status)"
'
```

---

## ConnectionProperties Parameters

### 1. Same-Account Access Identity Mode

| Name | Type | Required | Example | Description |
|------|------|----------|---------|-------------|
| `project` | String | Yes | `hello_mc_project` | MaxCompute project name |
| `regionId` | String | Yes | `cn-shanghai` | Region identifier where the MaxCompute project resides. Examples: `cn-shanghai` (Shanghai), `cn-beijing` (Beijing) |
| `endpointMode` | String | Yes | `SelfAdaption` | Access address configuration mode. Values: `SelfAdaption` (adaptive), `Custom` (custom access address) |
| `endpoint` | String | No | `http://service.cn-shanghai.maxcompute.aliyun-inc.com/api` | MaxCompute Service access endpoint (classic network). Format: `service.${regionId}.maxcompute.aliyun-inc.com/api` or `service.${regionId}-intranet.maxcompute.aliyun-inc.com/api` |
| `tunnelServer` | String | No | `http://dt.cn-shanghai.maxcompute.aliyun-inc.com` | MaxCompute Tunnel access endpoint (classic network). Format: `dt.${regionId}.maxcompute.aliyun-inc.com` or `dt.${regionId}-intranet.maxcompute.aliyun-inc.com` |
| `authType` | String | Yes | `Executor` | Datasource access identity. Values (case-insensitive): `Executor`, `TaskOwner`, `PrimaryAccount`, `SubAccount`, `RamRole`, `HadoopUser` |
| `authIdentity` | String | No | `<ACCOUNT_ID>` | Cloud account ID of the task submitter (same-account scenario) |
| `envType` | String | Yes | `Dev` | Datasource environment. Values: `Dev` (development), `Prod` (production) |

---

### 2. Cross-Account Mode

| Name | Type | Required | Example | Description |
|------|------|----------|---------|-------------|
| `project` | String | Yes | `hello_mc_project` | MaxCompute project name |
| `regionId` | String | Yes | `cn-shanghai` | Region identifier. Examples: `cn-shanghai`, `cn-beijing` |
| `endpointMode` | String | Yes | `SelfAdaption` | Access address configuration mode: `SelfAdaption` or `Custom` |
| `endpoint` | String | No | `http://service.cn-shanghai.maxcompute.aliyun-inc.com/api` | MaxCompute Service access endpoint (classic network) |
| `tunnelServer` | String | No | `http://dt.cn-shanghai.maxcompute.aliyun-inc.com` | MaxCompute Tunnel access endpoint (classic network) |
| `authType` | String | Yes | `RamRole` | Fixed value: `RamRole` |
| `crossAccountOwnerId` | String | Yes | `<ACCOUNT_ID>` | Target Alibaba Cloud primary account ID (required for cross-account) |
| `crossAccountRoleName` | String | Yes | `mc-accross-role-name` | Role name under the target account |
| `envType` | String | Yes | `Dev` | Datasource environment: `Dev` or `Prod` |

---

## Configuration Examples

### PrimaryAccount Access Identity Mode (Recommended)

> **Note**: MaxCompute data source does not support `Executor` identity. Please use `PrimaryAccount`.

```json
{
    "envType": "Prod",
    "project": "skyfire_20221228",
    "regionId": "cn-shanghai",
    "endpointMode": "SelfAdaption",
    "authType": "PrimaryAccount"
}
```

### Custom Endpoint Mode

```json
{
    "endpoint": "http://service.cn-shanghai.maxcompute.aliyun-inc.com/api",
    "envType": "Prod",
    "project": "skyfire_20221228",
    "authType": "PrimaryAccount",
    "endpointMode": "Custom",
    "regionId": "cn-shanghai"
}
```

### Cross-Account Mode

```json
{
    "project": "skyfire_20221228",
    "crossAccountOwnerId": "<ACCOUNT_ID>",
    "crossAccountRoleName": "mc-accross-role-name",
    "endpointMode": "SelfAdaption",
    "envType": "Prod",
    "authType": "RamRole",
    "regionId": "cn-shanghai"
}
```

## AuthType Enum Values

> **Note**: MaxCompute data source **does not support** `Executor` identity. `PrimaryAccount` is recommended.

| Value | Description | MaxCompute Support |
|-------|-------------|-------------------|
| `Executor` | Executor identity | **Not Supported** |
| `TaskOwner` | Task owner identity | Supported |
| `PrimaryAccount` | Primary account identity | **Recommended** |
| `SubAccount` | Specified sub-account identity | Supported |
| `RamRole` | Specified RAM role identity | Supported (cross-account scenario) |
| `HadoopUser` | Identity mapping for EMR/Hadoop scenarios | Supported |

## Endpoint Format Notes

- **Service Endpoint Formats:**
  - Classic: `service.${regionId}.maxcompute.aliyun-inc.com/api`
  - New format: `service.${regionId}-intranet.maxcompute.aliyun-inc.com/api`

- **Tunnel Endpoint Formats:**
  - Classic: `dt.${regionId}.maxcompute.aliyun-inc.com`
  - New format: `dt.${regionId}-intranet.maxcompute.aliyun-inc.com`
