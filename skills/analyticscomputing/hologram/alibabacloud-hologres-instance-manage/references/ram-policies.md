# RAM Permissions Required

This document lists all RAM permissions required for the Hologres Instance Management skill.

## Summary Table

| Product | RAM Action | Resource Scope | Access Level | Description |
|---------|-----------|----------------|--------------|-------------|
| Hologram | hologram:ListInstances | `acs:hologram:{#regionId}:{#accountId}:instance/*` | list | List all Hologres instances |
| Hologram | hologram:GetInstance | `acs:hologram:{#regionId}:{#accountId}:instance/{#InstanceId}` | get | Get details of a specific instance |

## RAM Policy Document

### Minimum Required Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hologram:ListInstances",
        "hologram:GetInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

### Resource-Scoped Policy (Recommended for Production)

For tighter security, scope permissions to specific regions or instances:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hologram:ListInstances"
      ],
      "Resource": "acs:hologram:cn-hangzhou:*:instance/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "hologram:GetInstance"
      ],
      "Resource": "acs:hologram:cn-hangzhou:*:instance/hgprecn-cn-*"
    }
  ]
}
```

## System Policy Alternative

Instead of creating a custom policy, you can attach the following system policy:

| Policy Name | Description |
|-------------|-------------|
| `AliyunHologresReadOnlyAccess` | Read-only access to all Hologres resources |

## Applying the Policy

### Option 1: Attach System Policy

1. Go to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Users** or **Roles**
3. Select the target user/role
4. Click **Add Permissions**
5. Search for `AliyunHologresReadOnlyAccess`
6. Select and confirm

### Option 2: Create Custom Policy

1. Go to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Policies** → **Create Policy**
3. Select **Script** mode
4. Paste the policy JSON above
5. Name the policy (e.g., `HologresInstanceReadAccess`)
6. Attach to the target user/role

## Permission Verification

After granting permissions, verify access:

```bash
# Test ListInstances permission
aliyun hologram POST /api/v1/instances --header "Content-Type=application/json" --body "{}" --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills

# Test GetInstance permission (replace with actual instance ID)
aliyun hologram GET /api/v1/instances/hgprecn-cn-your-instance-id --read-timeout 4 --user-agent AlibabaCloud-Agent-Skills
```

## Common Permission Errors

| Error Code | Message | Solution |
|------------|---------|----------|
| NoPermission | RAM user permission is insufficient | Grant `hologram:ListInstances` or `hologram:GetInstance` |
| Forbidden.RAM | Access denied | Check if the policy is correctly attached |
| InvalidAccessKeyId.NotFound | AccessKey not found | Verify credentials are configured correctly |

## Best Practices

1. **Use Least Privilege**: Only grant the minimum permissions needed
2. **Scope to Resources**: Use resource ARNs to limit access to specific regions/instances
3. **Use RAM Roles**: Prefer RAM roles over long-term access keys when possible
4. **Regular Auditing**: Periodically review and revoke unused permissions
5. **Enable MFA**: Require multi-factor authentication for sensitive operations
