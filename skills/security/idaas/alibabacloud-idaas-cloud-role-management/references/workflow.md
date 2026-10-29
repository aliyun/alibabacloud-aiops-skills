# Discovery, writes and verification

Use the CLI's current help for exact request schemas. The EIAM operation inventory
across all branches is GetInstance, GetCloudAccount, ListCloudAccounts,
ListCloudAccountRoles, GetCloudAccountRole, CreateCloudAccountRole,
GetCloudAccountRoleConfig and CheckCloudAccountRoleConfig. This is a union of
capabilities, not a mandatory sequence or prerequisite for every request. Select
only the operations reachable on the chosen branch; an input-only request has no
cloud operations, a system inspection stops after classification, and a terminal
error stops all later calls. Creation APIs are required only when the approved
branch actually creates an absent resource. Missing dynamic-config/health APIs
block provisioning or health verification, not an unrelated read-only inspection.
List pages until the API's NextToken/total count is exhausted; repeated tokens,
failed pages, ambiguous matches or missing fields mean discovery_incomplete.

Creation request fields confirmed in public CLI: InstanceId, CloudAccountId,
CloudAccountRoleName and ClientToken; Description is optional. Default user role
type is vendor-specific. Do not force the stale CLI's Alibaba-only `role` enum on
AWS or Tencent. Do not invent optional ProjectIds where the deployment lacks it.
The role list/read-back field is `CloudAccountRoleUsageType`: require `user`
for a business role and reserve `system` plus creation type `system_init` for
the account's automatic system role. Do not treat a missing or differently named
field as proof of ownership or resource absence. Preserve a newly created record
when local response validation fails and resume by its exact recorded ID.

Preserve raw JSON from bounded subprocess execution. Avoid command substitution,
shell pipelines and string-concatenated shell commands. Never dump configure
files or environment variables. Use explicit named profiles for every call;
default profile selection must not silently change between security domains.

Before EIAM discovery, verify the explicit EIAM profile with STS GetCallerIdentity
and compare its AccountId with the known instance owner, even for an inspection
that stops at system-role classification. Do not substitute setup-script evidence
for this current caller check. Target-cloud identity is required before cloud
resource reads or writes; a protected system-role stop need not query that cloud.

For role configuration or full verification, discovery must include all EIAM
matching roles, the connected account's current provider and system role health,
and all cloud policies/trust. This full discovery does not apply after a terminal
error or after a read-only system classification stop. Register reuses a
cloud role unchanged and records existing permission scope; it is not evidence
that newly requested permissions have been applied. Reuse requires equivalence;
repair requires an exact approved trust difference. A permission difference
requiring replacement of shared policies is outside the approved operation.

For a new record, full dynamic trust is available only after creation. The
pre-creation plan must bind the verified account provider, issuer and audience,
role name and duration. After record creation, validate the returned trust policy
contains no unexpected principal, wildcard, action or condition change. If the
constraints cannot be established before creation, stop for configuration support
rather than approving an unrestricted future trust policy. An out-of-scope
response leaves the record partial; do not delete it automatically.

Some vendor configurations omit `RoleSessionDuration`. Do not invent a generated
value or change an existing system role's duration on that basis. For a new
business role, set the explicit duration from the approved plan through the
vendor's supported creation field, then verify its cloud read-back value.

User-role policy attachments may be absent from EIAM generated configuration.
This means business permissions are supplied separately, not permission to copy
the account's system-management policy. Health checks validate federation; cloud
policy content, attachments, inline policies and boundaries require independent
verification. A role not yet assigned is not usable by an arbitrary portal user.

Official schema references:

- https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-createcloudaccountrole
- https://help.aliyun.com/en/idaas/eiam/developer-reference/api-eiam-2021-12-01-listcloudaccountroles
- https://help.aliyun.com/en/idaas/eiam/developer-reference/api-eiam-2021-12-01-getcloudaccountrole
