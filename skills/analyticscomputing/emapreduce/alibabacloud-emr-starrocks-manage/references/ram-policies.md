# RAM Permission Policy Reference

This document lists all RAM permissions required for managing EMR Serverless StarRocks instances with this Skill.

## Permission Overview

Configure the following permissions for the RAM user or role that performs operations. You can create custom policies via the RAM console or attach the corresponding system policies.

## StarRocks Instance Management Permissions

| Permission (Action) | Description | Operation Type |
|---------------------|-------------|----------------|
| `starrocks:CreateInstanceV1` | Create StarRocks instance | Write |
| `starrocks:DescribeInstances` | Query instance list and details | Read-only |
| `starrocks:DescribeNodeGroups` | Query node group details | Read-only |
| `starrocks:DescribeInstanceConfigs` | Query instance configuration | Read-only |
| `starrocks:DescribeConfigHistory` | Query configuration change history | Read-only |


## Configuration and Operations Permissions

| Permission (Action) | Description | Operation Type |
|---------------------|-------------|----------------|
| `starrocks:QueryUpgradableVersions` | Query available upgrade versions | Read-only |

## Gateway Management Permissions

| Permission (Action) | Description | Operation Type |
|---------------------|-------------|----------------|
| `starrocks:ListGateway` | Query gateway list | Read-only |

## Dependent Cloud Product Permissions

Network resources need to be queried when creating instances, requiring the following cloud product permissions:

| Permission (Action) | Description | Operation Type |
|---------------------|-------------|----------------|
| `vpc:DescribeVpcs` | Query VPC list | Read-only |
| `vpc:DescribeVSwitches` | Query VSwitch list | Read-only |
| `ecs:DescribeSecurityGroups` | Query security group list | Read-only |

## Custom Policy Examples

### Read-only Policy (Operations Viewing)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "starrocks:DescribeInstances",
        "starrocks:DescribeNodeGroups",
        "starrocks:DescribeInstanceConfigs",
        "starrocks:DescribeConfigHistory",
        "starrocks:QueryUpgradableVersions",
        "starrocks:ListGateway"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "ecs:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Management Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "starrocks:CreateInstanceV1",
        "starrocks:DescribeInstances",
        "starrocks:DescribeNodeGroups",
        "starrocks:DescribeInstanceConfigs",
        "starrocks:DescribeConfigHistory",
        "starrocks:QueryUpgradableVersions",
        "starrocks:ListGateway"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "ecs:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```
