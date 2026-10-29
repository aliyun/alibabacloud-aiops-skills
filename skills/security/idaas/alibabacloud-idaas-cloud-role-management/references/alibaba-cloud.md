# Alibaba Cloud roles

Verify `aliyun sts get-caller-identity --profile PROFILE` with bounded subprocess
execution. AccountId must equal the selected cloud account owner, independently
of the EIAM administrator. Read the connected provider using IMS GetOIDCProvider;
do not create or update it in the user-role workflow.

Inspect RAM GetRole, ListPoliciesForRole (all pages), GetPolicy and GetPolicyVersion.
Read all attached policy types and default versions. RAM managed policies are
shared resources; never change their default version to repair this role.
Inspect any additional permission boundary mechanism supported by the deployment.

Dynamic config field: AlibabaCloudAccountRoleConfig, with RoleName and
TrustConfig.AssumeRolePolicyDocument / RoleSessionDuration. Require matching
provider principal, OIDC issuer and audience conditions. Copy the generated
document only after comparing it to the approved constraints; do not use the
documentation's account-root trust examples for OIDC.

For an absent cloud role, RAM CreateRole takes RoleName,
AssumeRolePolicyDocument and MaxSessionDuration. For a planned trust repair,
RAM UpdateRole takes the new policy document; preserve unrelated statements.
Create a new dedicated custom policy only if its name and complete document were
approved. An existing same-name policy must match exactly or stop. Attach with
AttachPolicyToRole using the actual PolicyType and PolicyName. Re-read GetRole,
ListPoliciesForRole and GetPolicyVersion after writes. Do not grant PassRole,
administrator policy or the EIAM system-management policy as a shortcut.

Regional read-only requests require per-action authorization metadata. A regional
CLI endpoint does not constrain granted permissions. Enumerate approved read APIs
and verify which resources/region conditions they support. Some list APIs expose
account-wide metadata; explain any inability to enforce the requested boundary
before proposing a policy. No global ECS read-only template is bundled.

Official API reference:
https://help.aliyun.com/en/ram/developer-reference/api-ram-2015-05-01-createrole
