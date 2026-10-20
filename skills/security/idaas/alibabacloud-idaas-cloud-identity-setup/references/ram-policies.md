# Required permissions

Grant only the actions needed by the selected mode and provider. This is an
operation inventory, not a ready-to-attach administrator policy. Resolve exact
resource ARNs against the deployed API authorization metadata and restrict
instance, role, policy, and provider resources to the approved plan. Resource
wildcards needed by a list API do not justify wildcard Actions.

## EIAM administrator: discovery and verification

`eiam:ListInstances` — Discover accessible instances, including all pages.

`eiam:GetInstance` — Validate the exact requested instance for target-only verification.
An instance-scoped grant does not authorize account-wide ListInstances. Failed
listing is not evidence that an instance or account record is absent.

`eiam:ListCloudAccounts` — Find account records in accessible instances.

`eiam:GetCloudAccount` — Read the selected account and health.

`eiam:ListCloudAccountRoles` — Find automatic system roles and read health.

`eiam:GetCloudAccountRole` — Read the system role and health.

`eiam:GetCloudAccountRoleConfig` — Obtain generated provider-specific configuration.

`eiam:CheckCloudAccountRoleConfig` — Run EIAM configuration checking; may update health metadata.

## New onboarding only

`eiam:CreateCloudAccount` — Create the account record and its automatic system role.

Authorize this action on the target instance's cloud-account creation ARN:
`acs:eiam:REGION:OWNER_ACCOUNT:instance/INSTANCE_ID/cloudaccount/*`.
The instance ARN alone does not authorize this action. Keep the owner and
instance explicit; use the official action/resource mapping for every operation.
Source: https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-createcloudaccount

## Unsupported operations

Cross-instance account transfer and old-record cleanup are outside this skill.
Normal onboarding must not request EIAM role disable/delete or account delete
permissions. Read-only discovery detects ownership conflicts and blocks writes.

## Alibaba Cloud target account: inspect/create

OIDC APIs are called through IMS, but their authorization prefix is **ram**.

`ram:GetOIDCProvider` — Compare OIDC provider configuration.

`ram:CreateOIDCProvider` — Create a missing provider.

`ram:GetRole` — Compare system role trust and duration.

`ram:CreateRole` — Create the generated system role.

`ram:GetPolicy` — Read generated custom-policy metadata.

`ram:GetPolicyVersion` — Compare its default version document.

`ram:CreatePolicy` — Create a missing generated custom policy.

`ram:ListPoliciesForRole` — Read attachments.

`ram:AttachPolicyToRole` — Attach only the generated policy.

## Read-policy resource ARN formats

Use each operation's authorization resource template, not the ARN returned by
GetRole. The returned role ARN uses an empty region for identity/AssumeRole;
GetRole and ListPoliciesForRole authorize against the Resource template
`acs:ram:{authorization_region}:ACCOUNT_ID:role/EXACT_ROLE_NAME`.
GetPolicy and GetPolicyVersion use the Resource template
`acs:ram:{authorization_region}:ACCOUNT_ID:policy/EXACT_CUSTOM_POLICY_NAME`.
For these authorization templates, substitute the literal asterisk (`*`) ONLY
for the `authorization_region` segment. These are Resource ARN templates, not
Action declarations. The Action array must contain only the specific operations
listed above; never use a wildcard Action. Preserve the exact account and resource
names; do not replace them with wildcard accounts or names. An empty-region
Resource can cause ImplicitDeny despite containing the right Action.

Sources: [GetRole authorization](https://www.alibabacloud.com/help/en/ram/developer-reference/api-ram-2015-05-01-getrole),
[ListPoliciesForRole authorization](https://help.aliyun.com/zh/ram/developer-reference/api-ram-2015-05-01-listpoliciesforrole),
and [GetPolicyVersion authorization](https://help.aliyun.com/zh/ram/developer-reference/api-ram-2015-05-01-getpolicyversion).

A resource-format correction is still a policy change. Present the exact
before/after scope and obtain any required approval before applying it. A denied
read must terminate the current workflow; do not substitute an administrator
profile, skip the comparison, or claim a healthy configuration.

## Alibaba Cloud target account: approved repair only

`ram:UpdateRole` — Repair approved trust policy or duration differences.

`ram:CreatePolicyVersion` — Create the approved replacement policy version.

`ram:SetDefaultPolicyVersion` — Select the approved policy version.

Provider repair permissions depend on the exact difference (audience,
fingerprint, or issuance limit); do not pregrant all provider mutations.
Consult the current IMS authorization table and add only the exact required
Action to the reviewed plan before requesting repair authorization. Do not
perform provider repair until that additional action is recorded.

## Other providers

Alibaba Cloud RAM does not authorize AWS IAM or Tencent Cloud CAM. Obtain a
separate target-account identity and the precise IAM/CAM permissions for the
chosen commands in the corresponding provider reference. No cloud resource
delete permissions are needed for normal onboarding.

## Sources and version boundary

- [ListInstances authorization](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-listinstances)
- [IMS authorization table](https://help.aliyun.com/en/ram/developer-reference/api-ims-2019-08-15-ram)
- EIAM account/role operation names: EIAM 2021-12-01 OpenAPI definitions.

Older internal filenames such as ObtainCloudAccountRoleConfig and
VerifyCloudAccountRoleTrustConfig are not public permission Action names.
Verify the deployed authorization definitions before generating a customer's
policy; documentation or permission inventory alone does not prove access.
