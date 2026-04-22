# RAM Policies for alibabacloud-find-skills

This document lists all RAM permissions required by the `alibabacloud-find-skills` skill.

## Required Permissions

The skill uses the following AgentExplorer service APIs:

| API Operation | Description | Permission Required |
|---------------|-------------|---------------------|
| `ListCategories` | List all available skill categories | `agentexplorer:ListCategories` |
| `SearchSkills` | Search skills by keyword and category | `agentexplorer:SearchSkills` |
| `GetSkillContent` | Retrieve detailed skill content | `agentexplorer:GetSkillContent` |

## Minimal RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentexplorer:ListCategories",
        "agentexplorer:SearchSkills",
        "agentexplorer:GetSkillContent"
      ],
      "Resource": "*"
    }
  ]
}
```

## Policy Explanation

### agentexplorer:ListCategories

- **Purpose**: Retrieve the complete catalog of skill categories and subcategories
- **Resource**: Public catalog, no resource-specific restrictions
- **Risk Level**: Low (read-only, public data)

### agentexplorer:SearchSkills

- **Purpose**: Query skills based on keywords, categories, or filters
- **Resource**: Public skills repository, no resource-specific restrictions
- **Risk Level**: Low (read-only, public data)

### agentexplorer:GetSkillContent

- **Purpose**: Fetch the full markdown content of a specific skill
- **Resource**: Public skill content, no resource-specific restrictions
- **Risk Level**: Low (read-only, public data)

## How to Apply This Policy

### Option 1: Via Alibaba Cloud Console

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select **JSON** tab
5. Paste the minimal RAM policy JSON above
6. Name the policy (e.g., `AgentExplorerReadOnly`)
7. Click **OK**
8. Attach the policy to your RAM user or role

### Option 2: Via Aliyun CLI

```bash
# Create the policy
aliyun ram create-policy \
  --policy-name AgentExplorerReadOnly \
  --policy-document '{
    "Version": "1",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "agentexplorer:ListCategories",
        "agentexplorer:SearchSkills",
        "agentexplorer:GetSkillContent"
      ],
      "Resource": "*"
    }]
  }' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Attach to RAM user
aliyun ram attach-policy-to-user \
  --policy-name AgentExplorerReadOnly \
  --policy-type Custom \
  --user-name <your-ram-user-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

## Permission Verification

To verify that your account has the required permissions:

```bash
# Test ListCategories permission
aliyun agentexplorer list-categories --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Test SearchSkills permission
aliyun agentexplorer search-skills --keyword "test" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills

# Test GetSkillContent permission
aliyun agentexplorer get-skill-content --skill-name "example-skill" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-find-skills
```

If any command returns a permission error (e.g., `403 Forbidden`, `NoPermission`), you need to apply the RAM policy above.

## Common Permission Errors

### Error: "User not authorized to operate on the specified resource"

**Cause**: Missing one or more required permissions.

**Solution**: Apply the complete RAM policy shown above.

### Error: "The specified action is not found"

**Cause**: AgentExplorer service may not be available in your region or account type.

**Solution**: Verify that you're using a supported account type and region.

## Security Best Practices

1. **Read-only access**: These permissions only allow reading public data, no write operations
2. **Minimal scope**: Only grants access to AgentExplorer APIs, not other services
3. **No resource restrictions needed**: Skills catalog is public, no need for resource-level filtering
4. **Suitable for automation**: Safe to use in CI/CD pipelines or automated scripts
5. **No sensitive data**: Skills content is public documentation, no confidential information

## Permission Escalation

This skill does **not** require any additional permissions beyond the minimal set listed above. If you encounter permission errors after applying this policy, it may indicate:

- Account-level restrictions (contact your administrator)
- Service availability issues (check Alibaba Cloud service status)
- Incorrect policy attachment (verify policy is attached to correct user/role)

## Related Documentation

- [Alibaba Cloud RAM User Guide](https://www.alibabacloud.com/help/ram)
- [RAM Policy Syntax](https://www.alibabacloud.com/help/ram/user-guide/policy-structure-and-syntax)
- [AgentExplorer Service Documentation](https://www.alibabacloud.com/help/agentexplorer)
