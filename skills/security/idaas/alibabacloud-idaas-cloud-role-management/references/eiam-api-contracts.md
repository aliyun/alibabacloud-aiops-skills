# EIAM role operation contracts

Product: `eiam`; API version: `2021-12-01`. These contracts describe the
operations actually used by this Skill. They supplement CLI command metadata;
they do not grant permissions or prove that a profile can access a resource.
Use the original server response and RequestId as execution evidence.

| API | Required request fields | Response fields used by this workflow |
| --- | --- | --- |
| GetInstance | InstanceId | Instance, RequestId |
| ListCloudAccounts | InstanceId | CloudAccounts, NextToken, TotalCount, RequestId |
| GetCloudAccount | InstanceId, CloudAccountId | CloudAccount, RequestId |
| ListCloudAccountRoles | InstanceId, CloudAccountId | CloudAccountRoles, NextToken, TotalCount, RequestId |
| GetCloudAccountRole | InstanceId, CloudAccountId, CloudAccountRoleId | CloudAccountRole, RequestId |
| CreateCloudAccountRole | InstanceId, CloudAccountId, CloudAccountRoleName, ClientToken | CloudAccountRole, RequestId |
| GetCloudAccountRoleConfig | InstanceId, CloudAccountId, CloudAccountRoleId | CloudAccountRoleConfig, RequestId |
| CheckCloudAccountRoleConfig | InstanceId, CloudAccountId, CloudAccountRoleId | CloudAccountRoleHealthCheckResult, RequestId |

For list operations, MaxResults and NextToken control pagination. Optional
filters never substitute for reading all actual matching pages. Do not invent
NextToken or depend on TotalCount alone when a real next page is present.

Read `CloudAccountRoleUsageType` from the actual role object. Business roles must
have usage `user`. A role with usage `system` is inspection-only. Fresh health
requires `CloudAccountRoleHealth == healthy`, result `success` and a
`LastCheckTime` at or after the current check request start time.

The auxiliary GetCloudAccountRoleConfig and CheckCloudAccountRoleConfig contracts
were verified with real service responses through official CLI 3.5.2 forced RPC.
The public product plugin may not list them in local metadata. Use only the
bounded transport builder with all three exact IDs; never infer a role ID from
its name or use a cached success response as an API substitute.

These are separate operations: local `role_tools.py validate` checks the request
shape, `check` verifies an existing immutable sealed artifact, and `seal` creates
a new artifact only when no original exists. None is an EIAM API.
