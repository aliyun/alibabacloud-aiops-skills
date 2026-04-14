# RAM Policies for PAI-FeatureStore FeatureDB Usage Query

This document describes the required RAM (Resource Access Management) permissions for querying and analyzing PAI-FeatureStore FeatureDB usage statistics.

---

## Required API Actions

The following API actions are required for this skill:

| API Action | Purpose | Required |
|------------|---------|----------|
| `paifeaturestore:ListInstances` | List PAI-FeatureStore instances to get InstanceId | Yes |
| `paifeaturestore:GetDatasource` | Get datasource details to verify it's a FeatureDB datasource | Yes |
| `paifeaturestore:ListDatasources` | List datasources to find FeatureDB datasources | Yes |
| `paifeaturestore:ListDatasourceFeatureViews` | Query feature view usage statistics and read/write counts | Yes |

---

## Minimal RAM Policy

Below is the minimal RAM policy required for this skill. This policy grants read-only access to query FeatureDB usage statistics.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "paifeaturestore:ListInstances",
        "paifeaturestore:GetDatasource",
        "paifeaturestore:ListDatasources",
        "paifeaturestore:ListDatasourceFeatureViews"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Policy Configuration Steps

### Option 1: Via Alibaba Cloud Console

1. Log in to the [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Policies** → **Create Policy**
3. Select **JSON** mode
4. Paste the policy JSON above
5. Name the policy (e.g., `PAI-FeatureStore-ReadOnly-UsageQuery`)
6. Click **OK** to create
7. Navigate to **Users** → Select the user → **Add Permissions**
8. Select the policy you just created and grant it to the user

### Option 2: Via Aliyun CLI

**Note**: RAM policy creation via CLI requires elevated permissions. This should be done by an account administrator.

```bash
# Create the policy
aliyun ram create-policy \
  --policy-name PAI-FeatureStore-ReadOnly-UsageQuery \
  --policy-document '{
    "Version": "1",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "paifeaturestore:ListInstances",
          "paifeaturestore:GetDatasource",
          "paifeaturestore:ListDatasources",
          "paifeaturestore:ListDatasourceFeatureViews"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --user-agent AlibabaCloud-Agent-Skills

# Attach the policy to a user
aliyun ram attach-policy-to-user \
  --policy-name PAI-FeatureStore-ReadOnly-UsageQuery \
  --policy-type Custom \
  --user-name <YourUserName> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Resource-Level Permissions

The actions in this skill operate at the account level and require `Resource: "*"`. More granular resource-level permissions are not supported for these specific API actions.

---

## Security Best Practices

1. **Use the principle of least privilege**: Only grant the permissions listed above
2. **Create dedicated RAM users**: Don't use the root account for day-to-day operations
3. **Enable MFA**: Enable multi-factor authentication for RAM users with console access
4. **Rotate credentials regularly**: Change AccessKey pairs periodically
5. **Use temporary credentials**: Consider using STS tokens for temporary access
6. **Audit access logs**: Enable ActionTrail to monitor API calls

---

## Troubleshooting

### Error: "You are not authorized to do this action"

**Cause**: The RAM user lacks the required permissions.

**Solution**:
1. Verify the user has the policy attached: `aliyun ram list-policies-for-user --user-name <UserName> --user-agent AlibabaCloud-Agent-Skills`
2. Check that the policy includes all required actions listed above
3. If using a custom policy, ensure the JSON syntax is correct

### Error: "Invalid RAM policy"

**Cause**: The policy JSON is malformed.

**Solution**:
1. Validate the JSON syntax using a JSON validator
2. Ensure the `Version` is set to `"1"` (not `"2"` or other values)
3. Check that action names are spelled correctly with proper casing

---

## Additional Resources

- [RAM Policy Language Documentation](https://www.alibabacloud.com/help/ram/developer-reference/policy-structure-and-syntax)
- [PAI-FeatureStore API Reference](https://www.alibabacloud.com/help/pai-feature-store/latest/api-overview)
- [RAM Best Practices](https://www.alibabacloud.com/help/ram/security-practices/security-best-practices)
