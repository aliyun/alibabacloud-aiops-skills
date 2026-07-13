# RAM Policies - Elasticsearch Instance & Config Management

This document lists the RAM (Resource Access Management) permissions required for the two modules of this skill:

- **Instance Lifecycle** (referenced by [instance-manage.md](instance-manage.md))
- **Instance Config** — Snapshot + Dict (referenced by [config-manage.md](config-manage.md))

## Table of Contents

- [Required Permissions Overview](#required-permissions-overview)
- [Minimum Required Policy](#minimum-required-policy)
- [Permissions by Module](#permissions-by-module)
  - [Instance Lifecycle Module](#instance-lifecycle-module)
  - [Snapshot Module](#snapshot-module)
  - [Dict Module](#dict-module)
- [Resource-Level Policy (Recommended)](#resource-level-policy-recommended)
- [Region-Specific Policy](#region-specific-policy)
- [Read-Only Policy](#read-only-policy)
- [Additional Permissions for VPC Resources](#additional-permissions-for-vpc-resources)
- [Additional Permissions for OSS (Dict / Snapshot)](#additional-permissions-for-oss-dict--snapshot)
- [System Policies](#system-policies)
  - [Attach System Policy via CLI](#attach-system-policy-via-cli)
- [Policy Best Practices](#policy-best-practices)
- [References](#references)

---

## Required Permissions Overview

### Instance Lifecycle

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| createInstance | `elasticsearch:CreateInstance` | Create Elasticsearch Instance |
| DescribeInstance | `elasticsearch:DescribeInstance` | Query Instance Details |
| ListInstance | `elasticsearch:ListInstance` | List Instances |
| ListAllNode | `elasticsearch:ListAllNode` | Query Cluster Node Information |
| RestartInstance | `elasticsearch:RestartInstance` | Restart Instance |
| UpdateInstance | `elasticsearch:UpdateInstance` | Upgrade/Downgrade Instance Configuration |
| UpdateAdminPassword | `elasticsearch:UpdateAdminPassword` | Update elastic admin password |
| UpdateDescription | `elasticsearch:UpdateDescription` | Update instance name |
| UpdateInstanceChargeType | `elasticsearch:UpdateInstanceChargeType` | Convert pay-as-you-go to subscription |
| UpgradeEngineVersion | `elasticsearch:UpgradeEngineVersion` | Upgrade instance version or kernel patch |
| UpgradeInfo | `elasticsearch:DescribeInstance` | Query available upgrade versions (shares permission with DescribeInstance) |
| ListActionRecords | `elasticsearch:ListActionRecords` | Query instance change records / upgrade progress |
| ContinueEsVersionUpgrade | `elasticsearch:ContinueEsVersionUpgrade` | Continue gray upgrade of remaining nodes |

### Snapshot Management

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| UpdateSnapshotSetting | `elasticsearch:UpdateSnapshotSetting` | Configure auto-snapshot policy |
| DescribeSnapshotSetting | `elasticsearch:DescribeSnapshotSetting` | Query auto-snapshot policy |
| CreateSnapshot | `elasticsearch:CreateSnapshot` | Trigger one-shot snapshot |

### Dict Management

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| ListDicts | `elasticsearch:ListDicts` | List analyzer dicts |
| UpdateDict | `elasticsearch:UpdateDict` | Cold-update IK analyzer dicts |
| UpdateHotIkDicts | `elasticsearch:UpdateDict` | Hot-update IK analyzer dicts (shares permission with UpdateDict) |
| UpdateSynonymsDicts | `elasticsearch:UpdateDict` | Update synonyms dict (shares permission with UpdateDict) |
| UpdateAliwsDict | `elasticsearch:UpdateDict` | Update AliNLP (AliWS) dict (shares permission with UpdateDict) |

### Kibana Settings

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| DescribeKibanaSettings | `elasticsearch:DescribeKibanaSettings` | Query Kibana configuration |
| UpdateKibanaSettings | `elasticsearch:UpdateKibanaSettings` | Update Kibana language settings |

### ES Cluster YML Configuration

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| UpdateInstanceSettings | `elasticsearch:UpdateInstanceSettings` | Update ES YML configuration (triggers restart) |

### Plugin Management

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| ListPlugins | `elasticsearch:ListPlugin` | List system plugins |
| ListUserPlugin | `elasticsearch:ListPlugin` | List user custom plugins (shares permission with ListPlugins) |
| InstallSystemPlugin | `elasticsearch:InstallSystemPlugin` | Install system plugin |
| UninstallPlugin | `elasticsearch:UninstallPlugin` | Uninstall system plugin |
| PluginAnalysis | `elasticsearch:UploadPlugin` | Upload custom plugin to library (validate/upload) |
| InstallUserPlugins | `elasticsearch:InstallUserPlugins` | Install user custom plugins |

> Snapshot module additionally requires OSS access on the snapshot repository bucket; Dict module additionally requires OSS read access on the dict-source bucket. See [Additional Permissions for OSS](#additional-permissions-for-oss-dict--snapshot).

---

## Minimum Required Policy

Grant the union of the actions for whichever modules will be used. Below is the **full union** for all modules:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:CreateInstance",
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance",
        "elasticsearch:ListAllNode",
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance",
        "elasticsearch:UpdateAdminPassword",
        "elasticsearch:UpdateDescription",
        "elasticsearch:UpdateInstanceChargeType",
        "elasticsearch:UpgradeEngineVersion",
        "elasticsearch:ListActionRecords",
        "elasticsearch:ContinueEsVersionUpgrade",
        "elasticsearch:UpdateSnapshotSetting",
        "elasticsearch:DescribeSnapshotSetting",
        "elasticsearch:CreateSnapshot",
        "elasticsearch:ListDicts",
        "elasticsearch:UpdateDict",
        "elasticsearch:DescribeKibanaSettings",
        "elasticsearch:UpdateKibanaSettings",
        "elasticsearch:UpdateInstanceSettings",
        "elasticsearch:ListPlugin",
        "elasticsearch:InstallSystemPlugin",
        "elasticsearch:UninstallPlugin",
        "elasticsearch:UploadPlugin",
        "elasticsearch:InstallUserPlugins"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permissions by Module

When the principal only uses one module, grant just that module's actions.

### Instance Lifecycle Module

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:CreateInstance",
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance",
        "elasticsearch:ListAllNode",
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance",
        "elasticsearch:UpdateAdminPassword",
        "elasticsearch:UpdateDescription",
        "elasticsearch:UpdateInstanceChargeType",
        "elasticsearch:UpgradeEngineVersion",
        "elasticsearch:ListActionRecords",
        "elasticsearch:ContinueEsVersionUpgrade"
      ],
      "Resource": "*"
    }
  ]
}
```

### Snapshot Module

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:UpdateSnapshotSetting",
        "elasticsearch:DescribeSnapshotSetting",
        "elasticsearch:CreateSnapshot"
      ],
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

> `DescribeInstance` is included so the agent can run the mandatory pre-check (instance status must be `active`).

### Dict Module

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListDicts",
        "elasticsearch:UpdateDict"
      ],
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

---

## Resource-Level Policy (Recommended)

For better security, restrict permissions to specific resources. `CreateInstance` cannot bind to a specific instance ID and must use `Resource: *`.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:CreateInstance"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance",
        "elasticsearch:ListAllNode",
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance",
        "elasticsearch:UpdateAdminPassword",
        "elasticsearch:UpdateDescription",
        "elasticsearch:UpdateInstanceChargeType",
        "elasticsearch:UpgradeEngineVersion",
        "elasticsearch:ListActionRecords",
        "elasticsearch:ContinueEsVersionUpgrade",
        "elasticsearch:UpdateSnapshotSetting",
        "elasticsearch:DescribeSnapshotSetting",
        "elasticsearch:CreateSnapshot",
        "elasticsearch:ListDicts",
        "elasticsearch:UpdateDict",
        "elasticsearch:DescribeKibanaSettings",
        "elasticsearch:UpdateKibanaSettings",
        "elasticsearch:UpdateInstanceSettings",
        "elasticsearch:ListPlugin",
        "elasticsearch:InstallSystemPlugin",
        "elasticsearch:UninstallPlugin",
        "elasticsearch:UploadPlugin",
        "elasticsearch:InstallUserPlugins"
      ],
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

---

## Region-Specific Policy

Restrict operations to specific regions (example: `cn-hangzhou`):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:CreateInstance",
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance",
        "elasticsearch:ListAllNode",
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance",
        "elasticsearch:UpdateAdminPassword",
        "elasticsearch:UpdateDescription",
        "elasticsearch:UpdateInstanceChargeType",
        "elasticsearch:UpgradeEngineVersion",
        "elasticsearch:ListActionRecords",
        "elasticsearch:ContinueEsVersionUpgrade",
        "elasticsearch:UpdateSnapshotSetting",
        "elasticsearch:DescribeSnapshotSetting",
        "elasticsearch:CreateSnapshot",
        "elasticsearch:ListDicts",
        "elasticsearch:UpdateDict",
        "elasticsearch:DescribeKibanaSettings",
        "elasticsearch:UpdateKibanaSettings",
        "elasticsearch:UpdateInstanceSettings",
        "elasticsearch:ListPlugin",
        "elasticsearch:InstallSystemPlugin",
        "elasticsearch:UninstallPlugin",
        "elasticsearch:UploadPlugin",
        "elasticsearch:InstallUserPlugins"
      ],
      "Resource": "acs:elasticsearch:cn-hangzhou:*:instances/*"
    }
  ]
}
```

---

## Read-Only Policy

For users who only need to view instance information, snapshot settings, dict listings, Kibana config, and plugin listings:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance",
        "elasticsearch:ListAllNode",
        "elasticsearch:DescribeSnapshotSetting",
        "elasticsearch:ListDicts",
        "elasticsearch:DescribeKibanaSettings",
        "elasticsearch:ListPlugin"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Additional Permissions for VPC Resources

When **creating** Elasticsearch instances, you may also need VPC-related permissions to look up VPC / VSwitch information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Additional Permissions for OSS (Dict / Snapshot)

Dict and Snapshot modules rely on OSS:

- **Dict module**: when `sourceType=OSS`, the ES service reads dict files from your OSS bucket. The bucket MUST be in the same region as the ES instance and publicly readable, or you must grant the ES service role read access.
- **Snapshot module**: snapshots are stored in an OSS repository configured for the instance.

Minimum OSS permissions for the principal that operates these APIs (so it can verify and stage files before calling the ES API):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:GetBucketInfo",
        "oss:ListObjects"
      ],
      "Resource": [
        "acs:oss:*:*:<your-dict-bucket>",
        "acs:oss:*:*:<your-dict-bucket>/*",
        "acs:oss:*:*:<your-snapshot-bucket>",
        "acs:oss:*:*:<your-snapshot-bucket>/*"
      ]
    }
  ]
}
```

> Replace `<your-dict-bucket>` / `<your-snapshot-bucket>` with the actual bucket names. If you also need to upload dict files via OSS APIs, additionally grant `oss:PutObject` on the dict bucket.

---

## System Policies

Alibaba Cloud provides built-in system policies for Elasticsearch:

| Policy Name | Description |
|-------------|-------------|
| `AliyunElasticsearchFullAccess` | Full Management Permissions (covers all instance / snapshot / dict APIs) |
| `AliyunElasticsearchReadOnlyAccess` | Read-Only Permissions |

### Attach System Policy via CLI

> **`--user-agent` applies ONLY to business API commands** (e.g. `aliyun elasticsearch ...`); such commands MUST pass `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}` (see `SKILL.md#observability` for `SESSION_ID` generation rule). **System / tool commands** (`aliyun configure`, `aliyun version`, `aliyun plugin update`, `aliyun help`, `aliyun ram ...`, etc.) **MUST NOT** carry `--user-agent` — they do not support the flag.

```bash
# Attach full access policy to RAM user
aliyun ram attach-policy-to-user \
  --policy-type System \
  --policy-name AliyunElasticsearchFullAccess \
  --user-name <UserName> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}

# Attach read-only policy to RAM user
aliyun ram attach-policy-to-user \
  --policy-type System \
  --policy-name AliyunElasticsearchReadOnlyAccess \
  --user-name <UserName> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-elasticsearch-instance-manage/${SESSION_ID}
```

---

## Policy Best Practices

1. **Principle of Least Privilege**: Grant only the minimum permissions required for the modules in use.
2. **Use Resource-Level Restrictions**: Restrict to specific instances / buckets when possible.
3. **Separate Read and Write**: Use different policies for different operation types (e.g. Read-Only Policy for monitoring agents).
4. **Module Isolation**: For multi-tenant use, grant only the relevant module's actions (instance vs snapshot vs dict).
5. **Regular Auditing**: Review and audit permissions periodically.
6. **Use RAM Roles**: For applications, use RAM roles / STS rather than hardcoded credentials.

---

## References

- [Elasticsearch RAM Policies](https://help.aliyun.com/document_detail/187755.html)
- [RAM Policy Structure](https://help.aliyun.com/document_detail/93739.html)
- [RAM Console](https://ram.console.aliyun.com/)
- [OSS Permission Reference](https://help.aliyun.com/document_detail/100680.html)
