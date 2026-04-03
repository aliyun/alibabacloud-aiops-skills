# RAM Policies - RDS Copilot

## Required Permissions

Using the RDS Copilot skill requires the following RAM permissions:

| Action | Resource | Description |
|--------|----------|-------------|
| `rdsai:ChatMessages` | `*` | Call RDS AI Assistant dialogue API |

## Custom Policy

Create a custom RAM policy to grant RDS Copilot access:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rdsai:ChatMessages"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy Description

### Least Privilege Principle

The above policy contains only the minimum permissions required to call the RDS AI Assistant API. If recommendations returned by RDS Copilot require executing other operations (such as querying instances, modifying parameters, etc.), additional RDS permissions need to be granted.

### Extended Permissions (Optional)

If you need RDS Copilot to execute RDS operations mentioned in query recommendations, you can add the following permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rdsai:ChatMessages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute",
        "rds:DescribeDBInstancePerformance",
        "rds:DescribeSlowLogRecords",
        "rds:DescribeParameters"
      ],
      "Resource": "*",
      "Condition": {}
    }
  ]
}
```

## Credential Configuration

This skill uses Alibaba Cloud CLI for authentication. Please ensure:

1. The RAM user or role associated with the AccessKey has been granted the above permissions
2. Configure credentials via `aliyun configure` (relies on default credential chain):
   ```bash
   aliyun configure --profile rdsai
   ```

## Security Recommendations

1. **Use RAM User**: Avoid using root account AccessKey, recommend creating a dedicated RAM user
2. **Least Privilege**: Only grant necessary permissions
3. **Regular Rotation**: Regularly rotate AccessKey
4. **Use CLI Configuration**: Configure credentials via `aliyun configure`, rely on default credential chain
