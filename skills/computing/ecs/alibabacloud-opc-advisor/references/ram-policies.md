# RAM Policies

This skill uses read-only Alibaba Cloud API calls for pricing queries and image listing.
No write/modify/delete operations are performed.

## Minimum Required Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribePrice",
        "ecs:DescribeImages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "swas-open:DescribePrice"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribePrice"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "esa:DescribeRatePlanPrice"
      ],
      "Resource": "*"
    }
  ]
}
```

## CLI Commands Used

| Service | Command | Purpose |
|---|---|---|
| ECS | `aliyun ecs describe-price` | Query ECS instance pricing (Starter/Lite/Pro SKUs) |
| ECS | `aliyun ecs describe-images` | List available system images for ImageFamily validation |
| SWAS | `aliyun swas-open describe-price` | Query Simple Application Server pricing (Starter fallback) |
| RDS | `aliyun rds describe-price` | Query RDS instance pricing (Lite/Pro database tier) |
| ESA | `aliyun esa describe-rate-plan-price` | Query Edge Security Acceleration pricing (Pro tier) |

## Notes

- All operations are **read-only** (Describe/List). This skill never creates, modifies, or deletes cloud resources.
- The advisor recommends SKUs and generates purchase URLs; actual provisioning is handled by the downstream `alibabacloud-opc-deploy` skill.
- Pricing queries use `--region-id cn-beijing` as the default region.
