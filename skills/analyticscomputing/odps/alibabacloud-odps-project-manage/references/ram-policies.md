# RAM Policies

Required RAM (Resource Access Management) permissions for MaxCompute Project Management operations.

## Required Permissions

This Skill execution requires the following RAM permissions in `{Product}:{Action}` format:

- `odps:CreateProject` — Create MaxCompute project
- `odps:GetProject` — Query project details
- `odps:ListProjects` — List all projects
- `odps:ListQuotas` — List compute quotas (REQUIRED for project creation)

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| MaxCompute | `odps:CreateProject` | `*` | Create MaxCompute project |
| MaxCompute | `odps:GetProject` | `*` or specific project | Get project details |
| MaxCompute | `odps:ListProjects` | `*` | List all projects |
| MaxCompute | `odps:ListQuotas` | `*` | List compute quotas (required for creation) |

---

## RAM Policy Document

### Full Access Policy

Use this policy for users who need complete project management capabilities:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:CreateProject",
        "odps:GetProject",
        "odps:ListProjects",
        "odps:ListQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Policy

Use this policy for users who only need to view project information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:GetProject",
        "odps:ListProjects"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create-Only Policy

Use this policy for automation that only needs to create projects:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:CreateProject",
        "odps:GetProject",
        "odps:ListProjects",
        "odps:ListQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Resource Scope Examples

### Restrict to Specific Project

To restrict permissions to a specific project:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:GetProject"
      ],
      "Resource": "acs:odps:*:*:projects/<project-name>"
    }
  ]
}
```

### Restrict by Project Name Prefix

To allow operations on projects with a specific prefix:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:GetProject",
        "odps:ListProjects"
      ],
      "Resource": "acs:odps:*:*:projects/test_*"
    }
  ]
}
```

---

## Permission Verification

Before running the skill, verify permissions using:

```bash
# Check current user identity
aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage

# List attached policies (requires RAM read permission)
aliyun ram list-policies-for-user --user-name <username> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

---

## Pre-configured System Policies

Alibaba Cloud provides pre-configured policies that include MaxCompute permissions:

| Policy Name | Description |
|-------------|-------------|
| `AliyunODPSFullAccess` | Full access to MaxCompute resources |
| `AliyunODPSReadOnlyAccess` | Read-only access to MaxCompute resources |

To attach a system policy:

```bash
aliyun ram attach-policy-to-user \
  --policy-type System \
  --policy-name AliyunODPSFullAccess \
  --user-name <username> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-odps-project-manage
```

---

## Best Practices

1. **Least Privilege**: Grant only the minimum permissions required for the task
2. **Resource Scoping**: When possible, restrict resources to specific projects rather than using `*`
3. **Separate Policies**: Use different policies for different environments (dev, staging, prod)
4. **Audit Regularly**: Review and audit RAM policies periodically
5. **Use Roles**: For cross-account or service access, use RAM roles instead of long-term credentials
