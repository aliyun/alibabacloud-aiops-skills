# Tencent Cloud adapter

Verify `tccli sts GetCallerIdentity --profile PROFILE`; compare the full owner
account UIN with account_id. A subaccount UIN is not the owner UIN. Use verified
site context: mainland uses tencentcloudapi.com endpoints; international uses
the provider's supported international endpoints. Verify current CLI support.

Prefer existing profiles, official `tccli auth login --browser no --profile
PROFILE`, or authorized corporate SSO. Keep the initiating CLI session alive.
If terminal input is required, enter the result locally, never in chat.

Create the EIAM account with a complete CloudAccountProviderName using the
required idaas-eiam- prefix. Read TencentCloudAccountRoleConfig: RoleName,
TrustConfig.AssumeRolePolicyDocument, TrustConfig.RoleSessionDuration, and
PolicyConfigs[].PolicyDocument. Never infer values from another vendor's role.

OIDC creation needs the current issuer JWKS: fetch OpenID Discovery from the
verified generated issuer, validate jwks_uri belongs to the intended identity
service, and retrieve its keys. Do not follow arbitrary untrusted URLs.
Normalize a single CAM trust-policy action string to a one-element array when
the API requires an array; preserve policy semantics.

Inspect CAM DescribeOIDCConfig, GetRole, GetPolicy and ListAttachedRolePolicies.
Create missing resources with CreateOIDCConfig, CreateRole, CreatePolicy and
AttachRolePolicy. Approved repairs may use UpdateOIDCConfig, supported role
update APIs, CreatePolicyVersion and SetDefaultPolicyVersion. Check exact schema
with `tccli cam ACTION help --detail`; use structured JSON for complex input.

Compare provider name, issuer, audience, JWKS, role duration, policy default
version and attachments. Read all relevant pages. An access-denied or network
failure does not justify creation. If no safe in-place repair exists, report
the conflict rather than deleting and recreating a shared resource.
