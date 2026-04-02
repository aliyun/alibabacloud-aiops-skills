# RAM Permission Description

This Skill calls Alibaba Cloud EMR and related services' OpenAPI via `aliyun` CLI to perform cluster full lifecycle management operations. The following lists the minimum RAM permission set required.

## Required Permission List

### EMR Cluster Management

| Action | Description | Operation Type |
|--------|------|---------|
| `emr:ListReleaseVersions` | Query EMR version list | Read-only |
| `emr:ListInstanceTypes` | Query available instance types | Read-only |
| `emr:RunCluster` | Create cluster (recommended, supports full parameters) | Write operation |
| `emr:CreateCluster` | Create cluster (legacy interface) | Write operation |
| `emr:GetCluster` | Query cluster details | Read-only |
| `emr:ListClusters` | Query cluster list | Read-only |
| `emr:ListApplications` | Query cluster application component list | Read-only |
| `emr:UpdateClusterAttribute` | Modify cluster attributes (name, deletion protection, etc.) | Write operation |
| `emr:GetClusterCloneMeta` | Get cluster clone metadata | Read-only |
| `emr:UpdateClusterAutoRenew` | Configure cluster auto renewal | Write operation |

### EMR Node Group Management

| Action | Description | Operation Type |
|--------|------|---------|
| `emr:CreateNodeGroup` | Create node group | Write operation |
| `emr:ListNodeGroups` | Query node group list | Read-only |
| `emr:GetNodeGroup` | Query node group details | Read-only |
| `emr:IncreaseNodes` | Expand nodes | Write operation |
| `emr:DecreaseNodes` | Shrink nodes (only supports TASK node groups) | Write operation (irreversible) |
| `emr:ListNodes` | Query node list | Read-only |

### EMR Auto Scaling

| Action | Description | Operation Type |
|--------|------|---------|
| `emr:PutAutoScalingPolicy` | Create or update auto scaling policy | Write operation |
| `emr:GetAutoScalingPolicy` | Query auto scaling policy | Read-only |
| `emr:RemoveAutoScalingPolicy` | Delete auto scaling policy | Write operation (irreversible) |
| `emr:ListAutoScalingActivities` | Query auto scaling activity history | Read-only |

### Network and Compute Resources (Pre-check)

| Action | Description | Operation Type |
|--------|------|---------|
| `vpc:DescribeVpcs` | Query VPC list | Read-only |
| `vpc:DescribeVSwitches` | Query VSwitch list | Read-only |
| `ecs:DescribeSecurityGroups` | Query security group list | Read-only |
| `ecs:DescribeKeyPairs` | Query SSH key pair list | Read-only |

## RAM Policy Example

Below is a RAM custom policy (JSON format) granting all above permissions, can be created in RAM console:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "emr:ListReleaseVersions",
        "emr:ListInstanceTypes",
        "emr:RunCluster",
        "emr:CreateCluster",
        "emr:GetCluster",
        "emr:ListClusters",
        "emr:ListApplications",
        "emr:UpdateClusterAttribute",
        "emr:GetClusterCloneMeta",
        "emr:UpdateClusterAutoRenew",
        "emr:CreateNodeGroup",
        "emr:ListNodeGroups",
        "emr:GetNodeGroup",
        "emr:IncreaseNodes",
        "emr:DecreaseNodes",
        "emr:ListNodes",
        "emr:PutAutoScalingPolicy",
        "emr:GetAutoScalingPolicy",
        "emr:RemoveAutoScalingPolicy",
        "emr:ListAutoScalingActivities"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "ecs:DescribeSecurityGroups",
        "ecs:DescribeKeyPairs"
      ],
      "Resource": "*"
    }
  ]
}
```

## Least Privilege Principle Recommendations

- **Read-only scenarios** (query cluster status, node info): Only grant all `Get*` and `List*` Actions, plus VPC/ECS read-only permissions
- **Operations scenarios** (scaling, renewal): Add `IncreaseNodes`, `DecreaseNodes`, `UpdateClusterAutoRenew` on top of read-only permissions
- **Full management** (create cluster, node scaling): Grant full policy above, note `DecreaseNodes` is an irreversible operation, recommend only granting to trusted RAM users/roles

## Troubleshooting Insufficient Permissions

When encountering `Forbidden.RAM` error:

1. Check specific missing Action name in error Message
2. Add corresponding permission for current user/role in RAM console
3. If using STS Token, confirm STS policy also contains required Actions (STS permissions = RAM permissions ∩ STS policy permissions)
4. Re-execute operation to verify permissions take effect