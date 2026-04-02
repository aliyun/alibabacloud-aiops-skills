# RAM Policies for DMS Database Query

This document lists the RAM (Resource Access Management) permissions required for the DMS database query workflow.

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| DMS | dms:GetUserActiveTenant | * | Get tenant ID |
| DMS | dms:SearchDatabase | * | Search databases by keyword |
| DMS | dms:ExecuteScript | * | Execute SQL scripts |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:GetUserActiveTenant",
        "dms:SearchDatabase",
        "dms:ExecuteScript"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal Permission Policy

For production environments, consider restricting permissions to specific resources:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:GetUserActiveTenant"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dms:SearchDatabase"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "dms:TenantId": "${your-tenant-id}"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "dms:ExecuteScript"
      ],
      "Resource": "acs:dms:*:*:database/${database-id}",
      "Condition": {
        "StringEquals": {
          "dms:SqlType": ["SELECT"]
        }
      }
    }
  ]
}
```

## Permission Descriptions

### dms:GetUserActiveTenant

- **Purpose**: Retrieve the tenant ID (Tid) for the current user
- **Required**: Yes (prerequisite for all other DMS API calls)
- **Resource**: `*` (tenant-level operation)

### dms:SearchDatabase

- **Purpose**: Search for databases by keyword
- **Required**: Yes (to find the target database)
- **Resource**: `*` (searches across all accessible databases)

### dms:ExecuteScript

- **Purpose**: Execute SQL scripts on a database
- **Required**: Yes (core functionality)
- **Resource**: Can be restricted to specific database IDs
- **Note**: This permission allows execution of SELECT, DML, and DDL statements. Consider restricting to read-only queries in production.

## Best Practices

1. **Least Privilege**: Only grant `dms:ExecuteScript` on specific databases that users need to access
2. **Read-Only Access**: For reporting/analytics users, consider creating a separate policy that only allows SELECT queries
3. **Audit Logging**: Enable DMS audit logging to track all SQL executions
4. **Regular Review**: Periodically review and revoke unnecessary permissions

## Related Documentation

- [Alibaba Cloud RAM Documentation](https://help.aliyun.com/zh/ram/)
- [DMS Permission Management](https://help.aliyun.com/zh/dms/user-guide/permission-management)
