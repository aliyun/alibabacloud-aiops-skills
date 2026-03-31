# RAM Permission Statement

This Skill calls Alibaba Cloud Milvus and related product APIs, requires the following RAM permissions.

## Required Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "milvus:ListInstancesV2",
        "milvus:GetInstance",
        "milvus:GetInstanceDetail",
        "milvus:CreateInstance",
        "milvus:DeleteInstance",
        "milvus:UpdateInstance",
        "milvus:UpdateInstanceName",
        "milvus:DescribeInstanceConfigs",
        "milvus:ModifyInstanceConfig",
        "milvus:UpdatePublicNetworkStatus",
        "milvus:DescribeAccessControlList",
        "milvus:UpdateAccessControlList",
        "milvus:ChangeResourceGroup",
        "milvus:CreateDefaultRole"
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Description

| Permission Action | Purpose |
|-------------------|---------|
| `milvus:ListInstancesV2` | Query instance list |
| `milvus:GetInstance` | Query instance basic info |
| `milvus:GetInstanceDetail` | Query instance details |
| `milvus:CreateInstance` | Create instance |
| `milvus:DeleteInstance` | Delete instance |
| `milvus:UpdateInstance` | Change instance config |
| `milvus:UpdateInstanceName` | Modify instance name |
| `milvus:DescribeInstanceConfigs` | Query instance config |
| `milvus:ModifyInstanceConfig` | Modify instance config |
| `milvus:UpdatePublicNetworkStatus` | Enable/disable public network access |
| `milvus:DescribeAccessControlList` | Query access control list |
| `milvus:UpdateAccessControlList` | Update access control list |
| `milvus:ChangeResourceGroup` | Change resource group |
| `milvus:CreateDefaultRole` | Create default role |
| `vpc:DescribeVpcs` | Query VPC list (instance creation prerequisite check) |
| `vpc:DescribeVSwitches` | Query VSwitch list (instance creation prerequisite check) |
| `ecs:DescribeSecurityGroups` | Query security group list (instance creation prerequisite check) |

## Minimum Permission Principle

If following minimum permission principle, can limit `Resource` field to specific instance ARN:

```
"Resource": [
  "acs:milvus:<region>:<account-id>:instance/<instance-id>"
]
```