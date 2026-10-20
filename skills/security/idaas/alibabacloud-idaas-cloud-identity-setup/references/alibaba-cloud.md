# Alibaba Cloud adapter

Verify identity with `aliyun sts get-caller-identity --profile PROFILE`.
Require full AccountId to match the target account before resource inspection.
Use existing authorized RAM user/role profiles or official CLI OAuth; do not ask
for credentials or callback codes in chat. Recheck identity after login.

Use IMS for OIDC providers and RAM for roles, policies, and attachments.
Read AlibabaCloudAccountRoleConfig from EIAM: role name, session duration,
TrustConfig and PolicyConfigs. Use CloudAccountProviderName from the account.
Derive issuer and audience from the generated trust configuration; never copy
another instance's settings.

Inspect providers with GetOIDCProvider, roles with GetRole, policies with
GetPolicy/GetPolicyVersion, and attachments with ListPoliciesForRole. Compare
JSON policies semantically, audiences as sets, and configured session duration.
Create missing objects using CreateOIDCProvider, CreateRole, CreatePolicy and
AttachPolicyToRole. Only explicit not-found errors prove absence.

For approved repair, use UpdateRole or versioned policy updates. Provider repair
requires the exact additional IMS/RAM action recorded in the reviewed plan.
Derive current certificate fingerprints from the verified issuer TLS chain;
do not reuse cached fingerprints or temporary files shared with other runs.

If EIAM reports no registered OIDC provider, recheck provider name, issuer,
client IDs and fingerprints instead of recreating roles or the EIAM account.
