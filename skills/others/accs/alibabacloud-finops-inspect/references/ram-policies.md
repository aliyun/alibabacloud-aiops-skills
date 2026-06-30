# RAM Policies for Alibaba Cloud FinOps Resource Inspection

## Required Permissions

This skill requires **read-only** RAM permissions across multiple Alibaba Cloud services:

### ECS Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `ecs:DescribeRegions` | DescribeRegions | Discover enabled regions |
| `ecs:DescribeInstances` | DescribeInstances | Query ECS instances |
| `ecs:DescribeDisks` | DescribeDisks | Query cloud disks |

### RDS Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `rds:DescribeDBInstances` | DescribeDBInstances | Query RDS instances |

### VPC Permissions (EIP, NAT)

| Permission | API Action | Description |
|------------|------------|-------------|
| `vpc:DescribeEipAddresses` | DescribeEipAddresses | Query EIPs |
| `vpc:DescribeNatGateways` | DescribeNatGateways | Query NAT gateways |
| `vpc:DescribeSnatTableEntries` | DescribeSnatTableEntries | Query SNAT rules |
| `vpc:DescribeForwardTableEntries` | DescribeForwardTableEntries | Query DNAT rules |

### SLB (CLB) Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `slb:DescribeLoadBalancers` | DescribeLoadBalancers | Query CLB instances |
| `slb:DescribeLoadBalancerListeners` | DescribeLoadBalancerListeners | Query CLB listeners |

### ALB Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `alb:ListLoadBalancers` | ListLoadBalancers | Query ALB instances |
| `alb:ListListeners` | ListListeners | Query ALB listeners |
| `alb:ListServerGroups` | ListServerGroups | Query ALB server groups |
| `alb:ListServerGroupServers` | ListServerGroupServers | Query ALB server group servers |

### NLB Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `nlb:ListLoadBalancers` | ListLoadBalancers | Query NLB instances |
| `nlb:ListListeners` | ListListeners | Query NLB listeners |
| `nlb:ListServerGroups` | ListServerGroups | Query NLB server groups |

### CloudMonitor (CMS) Permissions

| Permission | API Action | Description |
|------------|------------|-------------|
| `cms:DescribeMetricLast` | DescribeMetricLast | Query latest CloudMonitor metrics |
| `cms:DescribeMetricList` | DescribeMetricList | Query CloudMonitor metric history |

## RAM Policy JSON

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeRegions",
        "ecs:DescribeInstances",
        "ecs:DescribeDisks"
      ],
      "Resource": [
        "acs:ecs:*:*:instance/*",
        "acs:ecs:*:*:disk/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances"
      ],
      "Resource": [
        "acs:rds:*:*:dbinstance/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeEipAddresses",
        "vpc:DescribeNatGateways",
        "vpc:DescribeSnatTableEntries",
        "vpc:DescribeForwardTableEntries"
      ],
      "Resource": [
        "acs:vpc:*:*:eip/*",
        "acs:vpc:*:*:natgateway/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "slb:DescribeLoadBalancers",
        "slb:DescribeLoadBalancerListeners"
      ],
      "Resource": [
        "acs:slb:*:*:loadbalancer/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:ListLoadBalancers",
        "alb:ListListeners",
        "alb:ListServerGroups",
        "alb:ListServerGroupServers"
      ],
      "Resource": [
        "acs:alb:*:*:loadbalancer/*",
        "acs:alb:*:*:listener/*",
        "acs:alb:*:*:servergroup/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "nlb:ListLoadBalancers",
        "nlb:ListListeners",
        "nlb:ListServerGroups"
      ],
      "Resource": [
        "acs:nlb:*:*:loadbalancer/*",
        "acs:nlb:*:*:listener/*",
        "acs:nlb:*:*:servergroup/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricLast",
        "cms:DescribeMetricList"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

## Permission Scope

- **Minimum Permission**: Read-only access across ECS, RDS, VPC, SLB, ALB, NLB, and CMS
- **Recommended Policy**: Use combination of system read-only policies:
  - `AliyunECSReadOnlyAccess`
  - `AliyunRDSReadOnlyAccess`
  - `AliyunVPCReadOnlyAccess`
  - `AliyunSLBReadOnlyAccess`
  - Custom policy for CMS (`cms:DescribeMetricLast`, `cms:DescribeMetricList`)
- **Resource Scope**: All regions and all resources under the account

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
