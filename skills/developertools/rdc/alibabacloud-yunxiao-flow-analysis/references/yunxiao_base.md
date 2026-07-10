# Yunxiao Fundamentals

## Organization Types

### Regional Organization vs Central Organization Differences

| Comparison Item | Central Organization | Regional Organization |
|----------------|---------------------|----------------------|
| **Domain** | devops.aliyun.com | {org-identifier}-{region}.devops.aliyuncs.com |
| **Access Method** | Public network only | Public network + VPC (public network can be disabled) |
| **Login Method** | Alibaba Cloud RAM only (linked to DingTalk) | Custom accounts/Alibaba Cloud/DingTalk/Feishu/SAML |
| **Billing** | Free basic edition; Advanced edition prepaid monthly/yearly, manual headcount adjustment | Free personal mode (up to 5 people); Enterprise collaboration billed daily, auto-adjustment |
| **IP Whitelist** | Code repository only | All modules |
| **Feature Modules** | 8 (including Knowledge Base) | 5 (Knowledge Base not supported, recommend DingTalk Docs) |

### How to Distinguish Organization Types

| Organization Type | Organization ID Length | Example | org-id Parameter for API Calls |
|-------------------|----------------------|---------|-------------------------------|
| **Central Organization** | 24 characters | `69bba3277c12f71e8ca58f8c` | Required |
| **Regional Organization/Dedicated Organization** | 32 characters | `64c1c73fa4a9f6530c595e17` | Required (Central Edition API) |

### Domain Description

| Organization Type | Domain Example | Description |
|-------------------|----------------|-------------|
| Central Organization | `openapi-rdc.aliyuncs.com` | Yunxiao Central Edition API domain |
| Regional Organization | `xxx-xxx.devops.aliyuncs.com` | Regional organization dedicated domain |

## API Version Description

### Central Edition API

- URL Format: `https://{domain}/oapi/v1/flow/organizations/{organizationId}/...`
- Requires `organizationId` parameter
- Applicable to central organizations

### Region Edition API

- URL Format: `https://{domain}/oapi/v1/flow/pipelines/...`
- Does not require `organizationId` in the path. However, `organizationId` needs to be provided when calling related scripts to determine the organization type.
- Applicable to regional organizations

## Personal Access Token (PAT)

### How to Obtain

1. Log in to Yunxiao Console
2. Go to Personal Settings > Personal Access Tokens
3. Create a new token, select required permissions
4. Copy the token (shown only once)

### Permission Requirements

Pipeline troubleshooting requires the following permissions:
- Pipeline: Read-only
- Pipeline Run Tasks: Read-only

### Token Format

```
pt-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Pipeline Basic Concepts

### Stage

- Basic organizational unit of a pipeline
- Can run in parallel or serial
- Each Stage contains one or more Jobs

### Job

- Execution unit within a Stage
- Runs on build machines
- Contains one or more Steps

### Step

- Smallest execution unit within a Job
- Each Step performs a specific operation (e.g., clone code, execute command, build image, etc.)
- Steps execute in order

## Build Environment Types

| Type | Description | Variable |
|------|-------------|----------|
| Specified Container Environment | User-defined container image | `specify_container` |
| Default Container Environment | Standard container environment provided by Yunxiao | `container` |
| Default VM Environment | Virtual machine environment provided by Yunxiao (private build machine) | `vm` |

## Cache Modes

| Mode | Description | Applicable Scenario |
|------|-------------|---------------------|
| local | Local cache | Private build cluster |
| cloud | Yunxiao managed cache | Public build cluster, VPC build cluster |

## Common Error Codes

| Error Code | Description |
|------------|-------------|
| 1903005 | Run failed, please check logs |
| 401 | Authentication failed (token invalid or expired) |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 500 | Internal server error |

## Yunxiao Default Build Cluster (Public Build Cluster) Egress IPs
| Flow Yunxiao Beijing Build Cluster Public IP Addresses | 47.93.89.246,47.94.150.17 |
| Flow Yunxiao Beijing Build Cluster Internal IP Addresses | 10.0.0.0/8,192.168.0.0/16 |
| Flow Yunxiao Hangzhou Build Cluster Public IP Addresses | 47.96.173.226,116.62.173.28 |
| Flow Yunxiao Hangzhou Build Cluster Internal IP Addresses | 100.0.0.0/8 |
| Flow Yunxiao China Hong Kong Build Cluster Public IP Addresses | 47.57.70.87,47.242.65.197,47.90.29.115,47.57.136.136 |
