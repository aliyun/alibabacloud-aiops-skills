# RAM Permission Guide

All API calls in this Skill are **read-only queries** and do not involve any resource creation, modification, or deletion.

## Required Permission List

### Cloud Monitor (CMS) - Core Permission

- `cms:DescribeMetricList` - Query Cloud Monitor metric data to obtain bandwidth, connection count, packet loss rate, and other monitoring data for all network products. This is the core API for inspection and must be authorized.

### VPC Network Products - Read-Only Queries

- `vpc:DescribeEipAddresses` - Query Elastic IP (EIP) instance list and detailed information (bandwidth limit, IP address, status, etc.)
- `vpc:DescribeCommonBandwidthPackages` - Query Common Bandwidth Package list and detailed information (bandwidth limit, associated EIPs, etc.)
- `vpc:DescribeNatGateways` - Query NAT Gateway instance list and detailed information (specification, VPC binding, status, etc.)
- `vpc:DescribePhysicalConnections` - Query Physical Connection instance list and detailed information (bandwidth, status, access point, etc.)
- `vpc:DescribeVirtualBorderRouters` - Query VBR (Virtual Border Router) instance list and detailed information

### Cloud Enterprise Network (CEN) - Read-Only Queries

- `cbn:DescribeCens` - Query Cloud Enterprise Network instance list
- `cbn:DescribeCenBandwidthPackages` - Query CEN bandwidth package list and bandwidth information
- `cbn:ListTransitRouters` - Query Transit Router (TR) list
- `cbn:ListTransitRouterVpcAttachments` - Query TR VPC attachment list
- `cbn:ListTransitRouterVbrAttachments` - Query TR VBR attachment list
- `cbn:ListTransitRouterRouteTables` - Query TR route table list

### Global Accelerator (GA) - Read-Only Queries

- `ga:ListAccelerators` - Query Global Accelerator instance list and bandwidth information

### Load Balancers - Read-Only Queries

- `slb:DescribeLoadBalancers` - Query Classic Load Balancer (CLB) instance list
- `alb:ListLoadBalancers` - Query Application Load Balancer (ALB) instance list
- `nlb:ListLoadBalancers` - Query Network Load Balancer (NLB) instance list

## Recommended RAM Policy

The following RAM policy contains only read-only permissions and can be safely granted to the inspection account:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "vpc:DescribeEipAddresses",
        "vpc:DescribeCommonBandwidthPackages",
        "vpc:DescribeNatGateways",
        "vpc:DescribePhysicalConnections",
        "vpc:DescribeVirtualBorderRouters",
        "cbn:DescribeCens",
        "cbn:DescribeCenBandwidthPackages",
        "cbn:ListTransitRouters",
        "cbn:ListTransitRouterVpcAttachments",
        "cbn:ListTransitRouterVbrAttachments",
        "cbn:ListTransitRouterRouteTables",
        "ga:ListAccelerators",
        "slb:DescribeLoadBalancers",
        "alb:ListLoadBalancers",
        "nlb:ListLoadBalancers"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Notes

- **Read-only operations**: All APIs are of the Describe/List type and will not make any changes to cloud resources
- **Principle of least privilege**: Only the query permissions required for inspection are requested
- **Insufficient permissions handling**: If a product lacks sufficient API permissions, the Skill will skip that product and mark it as an error in the report, without affecting the inspection of other products
- **Credential security**: Relies on the aliyun CLI default credential chain (e.g., `~/.aliyun/config.json`, environment variables, ECS RAM Role, etc.); credentials are never stored or transmitted by the Skill
