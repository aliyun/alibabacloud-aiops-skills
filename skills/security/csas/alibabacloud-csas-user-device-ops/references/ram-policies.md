# RAM Permission List

Required RAM permissions for this skill. The RAM Action prefix for SASE is `csas`.

## Quick Setup: System Policy

For quickest setup, attach the Alibaba Cloud system policy `AliyunCSASFullAccess` to the RAM user or role. This covers all CSAS operations (read + write) used by this skill.

```
PolicyName: AliyunCSASFullAccess
PolicyType: System
```

If the principal of least privilege is required, use the minimal custom policy below instead.

## Read-Only Permissions

| Action | Description | Used By |
|---|---|---|
| `csas:ListUserDevices` | List/query terminal devices | Direct CLI, inactive-analysis, cleanup-inactive |
| `csas:ListUsers` | List/query user accounts | Direct CLI |
| `csas:ListUserApplications` | Query user application authorization | Direct CLI |
| `csas:ListUserGroups` | Query user groups | Direct CLI |
| `csas:GetUserDevice` | Get single device detail | Direct CLI |
| `csas:GetActiveIdpConfig` | Get active IDP configuration | Direct CLI |

## Write Permissions

| Action | Description | Used By |
|---|---|---|
| `csas:UpdateUserDevicesStatus` | Lock/unlock/mark devices | cleanup-inactive.sh only |

## Minimal Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "csas:ListUserDevices",
        "csas:ListUsers",
        "csas:ListUserApplications",
        "csas:ListUserGroups",
        "csas:GetUserDevice",
        "csas:GetActiveIdpConfig",
        "csas:UpdateUserDevicesStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

## Read-Only Policy (no device lock capability)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "csas:ListUserDevices",
        "csas:ListUsers",
        "csas:ListUserApplications",
        "csas:ListUserGroups",
        "csas:GetUserDevice",
        "csas:GetActiveIdpConfig"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read this file (`references/ram-policies.md`) to get the full list of permissions required by this skill
> 2. Guide the user through requesting the necessary permissions from their RAM administrator
> 3. Pause and wait until the user confirms that the required permissions have been granted
> 4. Retry the failed operation after confirmation
