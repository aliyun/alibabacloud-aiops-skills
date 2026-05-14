# RAM Permission Configuration

## Recommended: Use System Policy

Grant the RAM user or role the system policy `AliyunDMSFullAccess` for full DMS operation permissions related to Dify instance provisioning.

## Least Privilege

For least privilege control, grant the following permissions:

### Core DMS Permissions

- `dms:CreateDifyInstance` — Provision a Dify instance, including Workspace, database (PostgreSQL), KV store (Redis), and vector database (AnalyticDB). Covers both `DryRun=true` (validation) and `DryRun=false` (actual provisioning).
- `dms:ListInstances` — List instances already registered in DMS, used to look up `DbResourceId`, `KvStoreResourceId`, or `VectordbResourceId` when the user selects `UseExistingInstance` in Advanced Mode.

### Required Permissions by Operation Mode

| Operation Mode | Required Actions |
|---------------|-----------------|
| Simple Mode (all new resources) | dms:CreateDifyInstance |
| Simple Mode (dry-run validation) | dms:CreateDifyInstance |
| Advanced Mode (provide existing instance IDs) | dms:CreateDifyInstance |
| Advanced Mode (look up existing instance IDs) | dms:CreateDifyInstance, dms:ListInstances |

### Additional Permissions for Querying Cloud Instances

When using Advanced Mode and reusing existing cloud database instances, the following read-only permissions may also be required to look up source instance metadata:

- `rds:DescribeDBInstances` — Query RDS PostgreSQL instance list (used as Dify metadata database)
- `r-kvstore:DescribeInstances` — Query Redis/Tair instance list (used as Dify KV store)
- `gpdb:DescribeDBInstances` — Query AnalyticDB for PostgreSQL instance list (used as Dify vector database)

Or directly grant the corresponding product system read-only policies: `AliyunRDSReadOnlyAccess`, `AliyunKvstoreReadOnlyAccess`, `AliyunGPDBReadOnlyAccess`.

## Best Practices

1. **Mode-Based Minimization**: If only Simple Mode is used, `dms:ListInstances` can be omitted.
2. **Separate Roles**: Use a dedicated RAM role for provisioning rather than granting permissions to a personal AccessKey.
3. **Audit Logging**: Enable ActionTrail to record all `CreateDifyInstance` calls for traceability.
4. **Key Rotation**: Rotate the AccessKey used for `ACCESS_KEY_ID` / `ACCESS_KEY_SECRET` regularly.

## Related Documentation

- [Alibaba Cloud RAM Documentation](https://help.aliyun.com/zh/ram/)
- [DMS Permission Management](https://help.aliyun.com/zh/dms/user-guide/permission-management)
- [DMS CreateDifyInstance API](https://api.aliyun.com/api/dms-enterprise/2018-11-01/CreateDifyInstance)
- [DMS ListInstances API](https://api.aliyun.com/api/dms-enterprise/2018-11-01/ListInstances)
