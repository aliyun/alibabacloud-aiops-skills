# Executor authorization and business permissions

These are distinct: the executor needs permission to provision the requested role;
the business role receives only the approved workload permissions. Never copy an
executor or system role's permission policy to the new role. Default credentials
or an authenticated profile do not establish authorization for every action.

EIAM discovery: eiam:GetInstance, eiam:ListCloudAccounts, eiam:GetCloudAccount,
eiam:ListCloudAccountRoles, eiam:GetCloudAccountRole. Creation/checking additionally
needs eiam:CreateCloudAccountRole, eiam:GetCloudAccountRoleConfig and
eiam:CheckCloudAccountRoleConfig when exposed and authorized in that deployment.
Check action/resource support in official metadata. Private auxiliary operations
are a deployment prerequisite, not generally available customer permissions.

Alibaba target reads: sts:GetCallerIdentity, ram:GetRole,
ram:ListPoliciesForRole, ram:GetPolicy, ram:GetPolicyVersion, ram:GetOIDCProvider.
Planned writes only: ram:CreateRole, ram:CreatePolicy, ram:AttachPolicyToRole;
ram:UpdateRole only for an approved change. Scope role/policy resources to the
exact owner and names.

Resource ARN syntax is separate from the Action list above. Construct the RAM
role authorization resource from colon-separated fields: `acs`, service `ram`,
region `*`, the verified account ID, then `role/` plus the exact role name.
The region wildcard is a Resource field, never an Action permission. Identity
ARNs can have an empty region and must not be copied blindly as authorization
resources. Some list actions require Resource "*"; explain that granularity
instead of inventing a scoped ARN. The Action field must always contain only
individually named operations from the approved plan.

AWS target reads: sts:GetCallerIdentity, iam:GetRole,
iam:ListAttachedRolePolicies, iam:ListRolePolicies, iam:GetRolePolicy,
iam:GetPolicy, iam:GetPolicyVersion, iam:GetOpenIDConnectProvider.
Planned writes: iam:CreateRole, iam:AttachRolePolicy, iam:PutRolePolicy,
iam:CreatePolicy, iam:UpdateAssumeRolePolicy, iam:UpdateRole, each only if used
and approved. Use exact partition-aware role and policy ARNs.

Tencent target reads: sts:GetCallerIdentity, cam:GetRole,
cam:ListAttachedRolePolicies, cam:ListPolicies, cam:GetPolicy, cam:GetPolicyVersion,
cam:DescribeOIDCConfig. Planned writes: cam:CreateRole, cam:CreatePolicy,
cam:AttachRolePolicy, cam:UpdateRoleTrustPolicy, with schema and current action
support verified before use. Only request the subset for the concrete plan.

No executor action to delete, migrate, assign users/groups, modify shared OIDC
providers or remove a permissions boundary is part of this skill. Do not request
wildcard action policies or administrator access to resolve a narrow denial.

Business permissions require exact documents, existing policy versions or named
resources, verified service authorization semantics, and an explicit approval.
The local validator rejects wildcard actions as a conservative first-version
policy; it cannot certify resource/condition enforcement or effective access.
