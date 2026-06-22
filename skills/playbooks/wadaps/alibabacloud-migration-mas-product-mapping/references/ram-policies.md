# Required RAM Permissions

The pricing service calls multiple Alibaba Cloud product OpenAPIs. Attach the following minimum permission policy to a RAM sub-account.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bssapi:GetSubscriptionPrice",
        "bssapi:QueryPriceEntity",
        "ecs:DescribePrice",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeAvailableResource",
        "rds:DescribePrice",
        "rds:DescribeAvailableClasses",
        "kvstore:DescribePrice",
        "polardb:DescribeClassList",
        "polardb:DescribeDBClusterPrice"
      ],
      "Resource": "*"
    }
  ]
}
```

## API Permissions Reference

| API Call | Purpose | RAM Action |
|---------|---------|------------|
| BSS GetSubscriptionPrice | General pricing for RDS / Redis / MongoDB / Kafka / WAF / DDoS / NAT / EIP / SLB / ES / GPDB | bssapi:GetSubscriptionPrice |
| BSS QueryPriceEntity | Query price entity details | bssapi:QueryPriceEntity |
| ECS DescribePrice | ECS instance + system disk + data disk combined pricing | ecs:DescribePrice |
| ECS DescribeInstanceTypes | Validate spec availability in target region | ecs:DescribeInstanceTypes |
| ECS DescribeAvailableResource | Check resource availability | ecs:DescribeAvailableResource |
| RDS DescribePrice | RDS subscription pricing | rds:DescribePrice |
| RDS DescribeAvailableClasses | Query available RDS classes | rds:DescribeAvailableClasses |
| Redis DescribePrice | Redis cloud-native pricing | kvstore:DescribePrice |
| PolarDB DescribeClassList | PolarDB single-node reference price | polardb:DescribeClassList |
| PolarDB DescribeDBClusterPrice | PolarDB cluster pricing | polardb:DescribeDBClusterPrice |

## Security Principles

- Use a dedicated RAM sub-account (never use root account)
- Grant minimum required permissions only (read-only + pricing)
- Rely on the default credential provider chain for authentication
- Never hardcode credentials in source files
