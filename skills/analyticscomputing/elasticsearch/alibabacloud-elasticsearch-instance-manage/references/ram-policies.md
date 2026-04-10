# RAM Policies - Elasticsearch Instance Management

This document lists the RAM (Resource Access Management) permissions required for Elasticsearch instance management operations.

## Table of Contents

- [Required Permissions Overview](#required-permissions-overview)
- [Minimum Required Policy](#minimum-required-policy)
- [Resource-Level Policy (Recommended)](#resource-level-policy-recommended)
- [Region-Specific Policy](#region-specific-policy)
- [Read-Only Policy](#read-only-policy)
- [Full Management Policy](#full-management-policy)
- [Additional Permissions for VPC Resources](#additional-permissions-for-vpc-resources)
- [System Policies](#system-policies)
  - [Attach System Policy via CLI](#attach-system-policy-via-cli)
- [Policy Best Practices](#policy-best-practices)
- [References](#references)

---

## Required Permissions Overview

| API Action | Required Permission | Description |
|------------|---------------------|-------------|
| createInstance | `elasticsearch:CreateInstance` | Create Elasticsearch Instance |
| DescribeInstance | `elasticsearch:DescribeInstance` | Query Instance Details |
| ListInstance | `elasticsearch:ListInstance` | List Instances |
| ListAllNode | `elasticsearch:ListAllNode` | Query Cluster Node Information |
| RestartInstance | `elasticsearch:RestartInstance` | Restart Instance |
| UpdateInstance | `elasticsearch:UpdateInstance` | Upgrade/Downgrade Instance Configuration |

---

## Minimum Required Policy

The following policy grants the minimum permissions needed for Elasticsearch instance management:

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
        "elasticsearch:UpdateInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Resource-Level Policy (Recommended)

For better security, restrict permissions to specific resources:

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
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance"
      ],
      "Resource": "acs:elasticsearch:*:*:instances/*"
    }
  ]
}
```

---

## Region-Specific Policy

Restrict operations to specific regions:

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
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance"
      ],
      "Resource": "acs:elasticsearch:cn-hangzhou:*:instances/*"
    }
  ]
}
```

---

## Read-Only Policy

For users who only need to view instance information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticsearch:DescribeInstance",
        "elasticsearch:ListInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Additional Permissions for VPC Resources

When creating Elasticsearch instances, you may also need VPC-related permissions:

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
        "elasticsearch:RestartInstance",
        "elasticsearch:UpdateInstance"
      ],
      "Resource": "*"
    },
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

## System Policies

Alibaba Cloud provides built-in system policies for Elasticsearch:

| Policy Name | Description |
|-------------|-------------|
| `AliyunElasticsearchFullAccess` | Full Management Permissions |
| `AliyunElasticsearchReadOnlyAccess` | Read-Only Permissions |

### Attach System Policy via CLI

```bash
# Attach full access policy to RAM user
aliyun ram AttachPolicyToUser \
  --PolicyType System \
  --PolicyName AliyunElasticsearchFullAccess \
  --UserName <UserName> \
  --user-agent AlibabaCloud-Agent-Skills

# Attach read-only policy to RAM user
aliyun ram AttachPolicyToUser \
  --PolicyType System \
  --PolicyName AliyunElasticsearchReadOnlyAccess \
  --UserName <UserName> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Policy Best Practices

1. **Principle of Least Privilege**: Grant only the minimum permissions required
2. **Use Resource-Level Restrictions**: Restrict to specific instances when possible
3. **Separate Read and Write**: Use different policies for different operation types
4. **Regular Auditing**: Review and audit permissions periodically
5. **Use RAM Roles**: For applications, use RAM roles instead of hardcoded credentials

---

## References

- [Elasticsearch RAM Policies](https://help.aliyun.com/document_detail/187755.html)
- [RAM Policy Structure](https://help.aliyun.com/document_detail/93739.html)
- [RAM Console](https://ram.console.aliyun.com/)
