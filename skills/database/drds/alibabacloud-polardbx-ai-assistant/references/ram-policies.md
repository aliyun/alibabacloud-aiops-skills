# RAM Policies

## Required Permissions

Using PolarDB-X AI Assistant (YaoChi Agent) requires the following RAM permissions:

### Core Permission - DAS GetYaoChiAgent

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "das:GetYaoChiAgent",
        "das:GetDasAgentSSE"
      ],
      "Resource": "*"
    }
  ]
}
```

### Recommended - DAS Read-Only

For full diagnostic capabilities, grant the following specific DAS read-only permissions:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "das:GetYaoChiAgent",
        "das:GetDasAgentSSE",
        "das:DescribeInstanceDasPro",
        "das:GetInstanceInspections",
        "das:GetQueryOptimizeExecErrorStats"
      ],
      "Resource": "*"
    }
  ]
}
```

### Cross-Account Access - STS AssumeRole

For cross-account access, configure RAM role trust policy on the target account:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "RAM": [
          "acs:ram::<caller-account-id>:root"
        ]
      }
    }
  ]
}
```

## Recommended System Policies

| Policy Name | Description | Use Case |
|-------------|-------------|----------|
| `AliyunDASReadOnlyAccess` | DAS read-only | Daily diagnostic queries |
| `AliyunDASFullAccess` | DAS full access | Execute diagnostic tasks |

## Permission Mapping

| Operation | Required RAM Action |
|-----------|---------------------|
| YaoChi Agent diagnostics | `das:GetYaoChiAgent` |
| DAS Agent SSE | `das:GetDasAgentSSE` |
