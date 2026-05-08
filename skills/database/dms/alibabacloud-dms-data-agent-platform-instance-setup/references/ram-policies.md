# RAM Policies for Create Dify Instance

This document lists the RAM (Resource Access Management) permissions required for the create-dify-instance skill.

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| DMS | dms:CreateDifyInstance | * | Create a Dify instance |
| DMS | dms:ListInstances | * | List registered instances (Advanced Mode only) |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:CreateDifyInstance",
        "dms:ListInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimal Permission Policy

For production environments, `dms:ListInstances` is only required in Advanced Mode when the user does not know the existing instance ID. If you only use Simple Mode, it can be omitted:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dms:CreateDifyInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Descriptions

### dms:CreateDifyInstance

- **Purpose**: Provision a Dify instance, including Workspace, database (PostgreSQL), KV store (Redis), and vector database (AnalyticDB)
- **Required**: Yes (core functionality)
- **Resource**: `*`
- **Note**: Covers both `DryRun=true` (validation) and `DryRun=false` (actual provisioning)

### dms:ListInstances

- **Purpose**: List instances already registered in DMS, used to look up `DbResourceId`, `KvStoreResourceId`, or `VectordbResourceId` when the user selects `UseExistingInstance` in Advanced Mode
- **Required**: Only in Advanced Mode when the user does not know the existing instance ID
- **Resource**: `*`

## Best Practices

1. **Least Privilege**: If only Simple Mode is used, remove `dms:ListInstances` from the policy
2. **Separate Roles**: Consider using a dedicated RAM role for provisioning rather than granting permissions to a personal AccessKey
3. **Audit Logging**: Enable ActionTrail to record all `CreateDifyInstance` calls for traceability
4. **Key Rotation**: Rotate the AccessKey used for `ACCESS_KEY_ID` / `ACCESS_KEY_SECRET` regularly

## Related Documentation

- [Alibaba Cloud RAM Documentation](https://help.aliyun.com/zh/ram/)
- [DMS Permission Management](https://help.aliyun.com/zh/dms/user-guide/permission-management)
- [DMS CreateDifyInstance API](https://api.aliyun.com/api/dms-enterprise/2018-11-01/CreateDifyInstance)
- [DMS ListInstances API](https://api.aliyun.com/api/dms-enterprise/2018-11-01/ListInstances)
