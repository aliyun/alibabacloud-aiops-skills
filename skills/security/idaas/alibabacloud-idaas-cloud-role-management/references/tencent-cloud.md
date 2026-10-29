# Tencent Cloud roles

Verify tccli sts GetCallerIdentity using the selected profile. Compare the owner
UIN, not a subaccount UIN, with the requested target. Verify mainland/global site
from authorized account/profile context; ask if ambiguous. Use supported official
endpoints for that site without guessing from the number or user location.

Inspect CAM GetRole, ListAttachedRolePolicies (all pages), GetPolicy and
GetPolicyVersion where required. Read the connected OIDC config without changing
it. Read TencentCloudAccountRoleConfig.RoleName and TrustConfig fields
AssumeRolePolicyDocument and RoleSessionDuration. Validate trust principal,
issuer, audience and duration against the plan.

Check `tccli cam ACTION help` for current schemas and use structured request JSON
for nested documents. CreateRole takes RoleName and PolicyDocument (trust), with
supported session-duration/description options. Normalize a scalar action to an
array only if required, preserving semantics. For approved business policies,
CreatePolicy creates a dedicated policy; AttachRolePolicy binds its actual
PolicyId to the role identifier accepted by the current schema. Read back the
policy content/default version and attachments. Never infer PolicyId from a name
or overwrite a shared policy. For an approved trust repair use the deployment's
supported UpdateRoleTrustPolicy schema; missing capability blocks repair.

An OIDC provider missing from this already connected account is an onboarding
configuration failure. Do not retrieve arbitrary URLs or create an alternative
provider to bypass the failure. Do not change issuer/JWKS globally for this role.

Official role workflow:
https://cloud.tencent.com/document/product/598/19381
