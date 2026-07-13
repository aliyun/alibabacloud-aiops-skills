# RAM Permission Policy

This skill only involves read-only operations and requires the following minimum RAM permissions.

## Permission Summary

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| API Gateway (cloudapi) | apigateway:DescribeInstances | * | List API Gateway instances in a specified region |
| API Gateway (cloudapi) | apigateway:DescribeInstanceDropPacket | * | View dropped packet count of dedicated instances |
| API Gateway (cloudapi) | apigateway:DescribeInstanceDropConnections | * | View dropped connection count of dedicated instances |
| API Gateway (cloudapi) | apigateway:DescribeInstanceSlbConnect | * | View concurrent connection count of dedicated instances |
| API Gateway (cloudapi) | apigateway:DescribeInstanceTraffic | * | View request and response traffic of dedicated instances |
| API Gateway (cloudapi) | apigateway:DescribeInstanceQps | * | View QPS data of dedicated instances |
| Cloud-Native API Gateway/AI Gateway (apig) | apig:ListGateways | * | Query gateway list |
| Cloud Monitor (cms) | cms:QueryMetricData | * | Query cloud product monitoring data |

## Custom Policy (Recommended)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:DescribeInstances",
        "apigateway:DescribeInstanceDropPacket",
        "apigateway:DescribeInstanceDropConnections",
        "apigateway:DescribeInstanceSlbConnect",
        "apigateway:DescribeInstanceTraffic",
        "apigateway:DescribeInstanceQps",
        "apig:ListGateways",
        "cms:QueryMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Usage Description

- `apigateway:DescribeInstances` - List API Gateway instances in a specified region
- `apigateway:DescribeInstanceDropPacket` - View dropped packet count of dedicated instances within a time period
- `apigateway:DescribeInstanceDropConnections` - View dropped connection count of dedicated instances within a time period
- `apigateway:DescribeInstanceSlbConnect` - View concurrent connection count of dedicated instances within a time period
- `apigateway:DescribeInstanceTraffic` - View request and response traffic of dedicated instances within a time period
- `apigateway:DescribeInstanceQps` - View QPS data of dedicated instances within a time period
- `apig:ListGateways` - Query gateway list (Cloud-Native API Gateway, AI Gateway)
- `cms:QueryMetricData` - Call DescribeMetricData API to query monitoring data for a specific metric of a cloud product
