# EIP Associate - RAM Permission Policies

## Required Permissions

This skill requires the following minimal permissions to operate:

### required_permissions

| Permission | Product | Description | Required |
|------------|---------|-------------|----------|
| `vpc:DescribeEipAddresses` | VPC | Query EIP status and bindings | **Yes** |
| `vpc:AllocateEipAddress` | VPC | Allocate new EIP | **Yes** |
| `vpc:AssociateEipAddress` | VPC | Bind EIP to resource | **Yes** |
| `vpc:UnassociateEipAddress` | VPC | Unbind EIP (cleanup) | **Yes** |
| `vpc:ReleaseEipAddress` | VPC | Release EIP (cleanup) | **Yes** |
| `ecs:DescribeInstances` | ECS | Validate ECS instance | For ECS binding |
| `ecs:DescribeInstanceAttribute` | ECS | Check ECS PIP status | For ECS binding |
| `ecs:DescribeNetworkInterfaces` | ECS | Validate ENI | For ENI binding |
| `slb:DescribeLoadBalancerAttribute` | SLB | Validate CLB | For CLB binding |
| `vpc:DescribeNatGateways` | VPC | Validate NAT Gateway | For NAT binding |
| `vpc:DescribeHaVips` | VPC | Validate HaVip | For HaVip binding |
| `vpc:DescribeVpcs` | VPC | Validate VPC | For IpAddress binding |

## Minimal RAM Policy (Recommended)

Use this policy for production environments:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeEipAddresses",
        "vpc:AllocateEipAddress",
        "vpc:AssociateEipAddress",
        "vpc:UnassociateEipAddress",
        "vpc:ReleaseEipAddress",
        "vpc:DescribeNatGateways",
        "vpc:DescribeHaVips",
        "vpc:DescribeVpcs"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "slb:DescribeLoadBalancerAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Policy (Query Only)

For read-only operations (checking status only):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeEipAddresses",
        "vpc:DescribeNatGateways",
        "vpc:DescribeHaVips",
        "vpc:DescribeVpcs",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceAttribute",
        "ecs:DescribeNetworkInterfaces",
        "slb:DescribeLoadBalancerAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

## Least Privilege Notes

- **No resource creation permissions**: This skill binds EIP to **existing** resources only
- **No deletion permissions** (except EIP): Only EIP release is needed for cleanup
- **Resource scope**: Restrict `Resource` to specific ARNs when possible:
  ```json
  "Resource": "acs:vpc:cn-hangzhou:*:eip/*"
  ```
