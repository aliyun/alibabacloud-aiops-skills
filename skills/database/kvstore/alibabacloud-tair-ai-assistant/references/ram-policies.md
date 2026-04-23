# RAM Policies

## Required Permissions

Tair AI Assistant (YaoChi Agent) requires the following RAM permissions.

### Standard Edition

RAM sub-accounts must have:
- **AliyunKvstoreReadOnlyAccess** - Tair/Redis read-only access
- **AliyunYaoChiAgentAccess** - YaoChi Agent access

For authorization instructions, see [Grant permissions to RAM users](https://help.aliyun.com/document_detail/116146.html).

### Professional Edition

RAM sub-accounts must have the service-linked role created:
- **AliyunServiceRolePolicyForTairAgent** - Tair Agent service-linked role

## Custom Policy (Minimum Permissions)

If you need to create a custom policy with minimum required permissions:

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

## Cross-Account Access - STS AssumeRole

For cross-account access, configure trust policy on the target account's RAM role:

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

## System Policy Reference

| Policy Name | Description | Use Case |
|-------------|-------------|----------|
| `AliyunKvstoreReadOnlyAccess` | Tair/Redis read-only access | Required for Standard Edition |
| `AliyunYaoChiAgentAccess` | YaoChi Agent access | Required for Standard Edition |

## Permission Mapping

| Operation | Required RAM Action |
|-----------|---------------------|
| Invoke YaoChi Agent | `das:GetYaoChiAgent` |
| Invoke DAS Agent SSE | `das:GetDasAgentSSE` |
