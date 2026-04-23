# RAM Policies

Minimum RAM permissions required for PAI-EAS service deployment.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eas:CreateService",
        "eas:DescribeService",
        "eas:ListServices",
        "eas:DescribeServiceEndpoints",
        "eas:DescribeServiceEvent",
        "eas:DescribeMachineSpec",
        "eas:ListResources",
        "eas:ListGateway",
        "eas:DescribeGateway"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aiworkspace:ListWorkspaces",
        "aiworkspace:ListImages",
        "aiworkspace:GetImage",
        "aiworkspace:ListDatasets"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:ListBuckets",
        "oss:GetBucketLocation",
        "oss:ListObjects"
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "nlb:ListLoadBalancers"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Details

### EAS Service Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `eas:CreateService` | Create service | Deploy new service |
| `eas:DescribeService` | Query service details | View status, get endpoints |
| `eas:ListServices` | List services | View existing services |
| `eas:DescribeServiceEndpoints` | Query service endpoints | Get access URL |
| `eas:DescribeServiceEvent` | Query service events | Diagnose issues |
| `eas:DescribeMachineSpec` | Query machine specs | Select instance type |
| `eas:ListResources` | List resource groups | Query dedicated resources |
| `eas:ListGateway` | List gateways | Query available gateways |
| `eas:DescribeGateway` | Query gateway details | Get gateway VPC info |

### AIWorkSpace Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `aiworkspace:ListWorkspaces` | List workspaces | Select workspace |
| `aiworkspace:ListImages` | List images | Query available images |
| `aiworkspace:GetImage` | Get image details | View image config |
| `aiworkspace:ListDatasets` | List datasets | Select dataset mount |

### OSS Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `oss:ListBuckets` | List buckets | Select OSS storage |
| `oss:GetBucketLocation` | Get bucket region | Verify cross-region access |
| `oss:ListObjects` | List objects | Browse model files |

### VPC Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `vpc:DescribeVpcs` | Query VPCs | Network config |
| `vpc:DescribeVSwitches` | Query VSwitches | Network config |

### ECS Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `ecs:DescribeSecurityGroups` | Query security groups | Network config |

### NLB Permissions

| Action | Description | Use Case |
|--------|-------------|----------|
| `nlb:ListLoadBalancers` | List load balancers | NLB network config |

## Extended Operations Permissions (Optional)

For more complete PAI-EAS operations (update, delete services, etc.), add these permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eas:UpdateService",
        "eas:DeleteService",
        "eas:ScaleService",
        "eas:DescribeServiceLog",
        "eas:ResumeService",
        "eas:SuspendService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aiworkspace:ListImages",
        "aiworkspace:ListImageLabels",
        "aiworkspace:GetImage",
        "aiworkspace:ListWorkspaces",
        "aiworkspace:ListDatasets"
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:ListBuckets",
        "oss:GetBucketLocation",
        "oss:ListObjects"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "nlb:ListLoadBalancers",
        "nlb:GetLoadBalancerAttribute"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Check

Check current user permissions:

```bash
aliyun ram get-login-profile --user-name <username>
```

Or check user authorization policies via the RAM Console.
