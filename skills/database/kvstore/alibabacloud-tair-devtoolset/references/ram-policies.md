# RAM Permissions Required — Tair DevToolset

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| R-KVStore | r-kvstore:CreateTairInstance | * | 创建 Tair 企业版实例 |
| R-KVStore | r-kvstore:DescribeInstanceAttribute | * | 查询实例属性（状态轮询） |
| R-KVStore | r-kvstore:ModifySecurityIps | * | 修改 IP 白名单 |
| R-KVStore | r-kvstore:AllocateInstancePublicConnection | * | 分配公网连接地址 |
| R-KVStore | r-kvstore:DescribeDBInstanceNetInfo | * | 查询实例网络信息 |

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

- 以上权限为该 Skill 所涉及的最小权限集
- 如仅需进行只读查询（不创建/删除资源），可仅授予 `Describe*` 权限
- 建议在生产环境中将 `Resource` 限定到具体实例 ARN
