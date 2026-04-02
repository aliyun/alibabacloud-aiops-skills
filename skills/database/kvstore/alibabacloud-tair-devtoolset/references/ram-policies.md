# RAM Permissions Required — Tair DevToolset

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| R-KVStore | r-kvstore:CreateTairInstance | * | Create Tair Enterprise Edition instance |
| R-KVStore | r-kvstore:DescribeInstanceAttribute | * | Query instance attribute (status polling) |
| R-KVStore | r-kvstore:ModifySecurityIps | * | Modify IP whitelist |
| R-KVStore | r-kvstore:AllocateInstancePublicConnection | * | Allocate public connection endpoint |
| R-KVStore | r-kvstore:DescribeDBInstanceNetInfo | * | Query instance network info |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "r-kvstore:CreateTairInstance",
        "r-kvstore:DescribeInstanceAttribute",
        "r-kvstore:ModifySecurityIps",
        "r-kvstore:AllocateInstancePublicConnection",
        "r-kvstore:DescribeDBInstanceNetInfo"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The above permissions are the minimum permission set required by this Skill
- For read-only queries (without creating/deleting resources), only `Describe*` permissions are needed
- It is recommended to limit `Resource` to specific instance ARN in production environments
