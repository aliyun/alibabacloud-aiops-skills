# RAM Permissions Required by This Skill

> Applies to the RAM user or role whose credentials are used to run `idaas-kubernetes-m2m-federated-credential` (the credentials configured through `aliyun configure`).
> Chinese version: `ram-policies.zh-CN.md`.

## 1. Permission Details (Actions Mapped to Steps)

### 1.1 STS (No Explicit Authorization Required)

`sts:GetCallerIdentity` — **Phase 0 prerequisites**: validate credentials and retrieve the current AccountId. Available to any RAM identity by default.

### 1.2 EIAM (Core Permissions)

`eiam:ListInstances` — **Phase 1 Round 2**: `list_instances.py` lists EIAM instances in the selected region. Required.

`eiam:GetInstance` — **Phase 3**: query `DefaultEndpoint.Endpoint` to construct the token endpoint. Required.

`eiam:ListFederatedCredentialProviders` — **Phase 1 Round 2**: `list_oidc_trust_sources.py` lists OIDC providers for reuse detection; name conflict checks. Required.

`eiam:CreateFederatedCredentialProvider` — **Phase 2 step 1**: create the OIDC provider (Static Fill-in / Issuer Address Resolution / JWKS URI Resolution; `create_oidc_trust_source.py`). Conditional: not needed when reusing an existing provider.

`eiam:UpdateFederatedCredentialProvider` — **Key rotation**: update StaticJwks after a cluster SA signing key rotation (`rotate_static_jwks.py`). Optional (rotation maintenance).

`eiam:ListApplications` — **Phase 1 Round 3**: `list_m2m_apps.py` lists existing M2M applications; application name conflict checks. Required.

`eiam:CreateApplication` — **Phase 2 step 2**: create the M2M client (`create_m2m_client.py`). Conditional: not needed when using an existing application.

`eiam:GetApplication` — **Phase 2 steps 2/4**: check `M2MClientStatus`; query the PAM system application `iap_pam` directly. Required.

`eiam:EnableApplicationM2MClient` — **Phase 2 step 2**: enable M2M client capability when not already enabled. Conditional (new applications only).

`eiam:CreateApplicationFederatedCredential` — **Phase 2 step 3**: create the kubernetes structured-mode credential (`create_k8s_credential.py`). Required.

`eiam:ListApplicationFederatedCredentials` — **After Phase 2 step 3**: read back the compiled VerificationCondition (optional verification). Optional.

`eiam:CheckInstanceModuleStatus` — **Phase 2 step 4**: check whether PAM is enabled. Required for the PAM flow.

`eiam:AuthorizeResourceServerToClient` — **Phase 2 step 4 stage A**: RS-level authorization (Client → iap_pam), idempotent. Required for the PAM flow.

`eiam:ListResourceServerScopes` — **Phase 2 step 4 stage B**: find the ress_id of the PAM scope (must pass `--ResourceServerScopeType all`). Required for the PAM flow.

`eiam:AuthorizeResourceServerScopesToClient` — **Phase 2 step 4 stage B**: scope-level authorization. Required for the PAM flow.

### 1.3 EIAM Cleanup/Rollback (Only When the User Explicitly Requests Deletion)

`eiam:DisableApplicationFederatedCredential`, `eiam:DeleteApplicationFederatedCredential` — disable then delete the credential. Optional (rollback).

`eiam:DisableFederatedCredentialProvider`, `eiam:DeleteFederatedCredentialProvider` — disable then delete the provider. Optional (rollback).

`eiam:DisableApplication`, `eiam:DeleteApplication` — disable then delete the M2M application. Optional (rollback).

## 2. Permissions Explicitly Not Required

| Permission | Why not needed |
|------|-------------|
| Any ECS permission | This skill targets Kubernetes; SA tokens are obtained **by the user on the cluster side** (or via the agent's own kubectl, governed by cluster RBAC, not RAM). |
| RAM permission for the token endpoint | `POST /api/v2/iauths_system/oauth2/token` is the IDaaS instance OAuth endpoint, authenticated via the federated credential (id-token-bearer assertion), not RAM. |
| Any RAM permission | The base flow does not touch RAM. STS-flow cloud role onboarding/trust policies are instance-side configuration (console or the idaas-cloud-identity-setup skill). |
| API for data permission rules | Permission Center > Data Permission Management (application↔cloud-role rules) has **no OpenAPI**; the skill provides console guidance only. |

## 3. Authorization Policies (Paste into the RAM Console)

### Option A: Minimal Custom Policy (Recommended) — create + verify + PAM authorization

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eiam:ListInstances",
        "eiam:GetInstance",
        "eiam:ListFederatedCredentialProviders",
        "eiam:CreateFederatedCredentialProvider",
        "eiam:UpdateFederatedCredentialProvider",
        "eiam:ListApplications",
        "eiam:GetApplication",
        "eiam:CreateApplication",
        "eiam:EnableApplicationM2MClient",
        "eiam:CreateApplicationFederatedCredential",
        "eiam:ListApplicationFederatedCredentials",
        "eiam:CheckInstanceModuleStatus",
        "eiam:AuthorizeResourceServerToClient",
        "eiam:ListResourceServerScopes",
        "eiam:AuthorizeResourceServerScopesToClient"
      ],
      "Resource": "*"
    }
  ]
}
```

### Option B: Option A + Cleanup/Rollback

Append to the Action list:

```json
"eiam:DisableApplicationFederatedCredential",
"eiam:DeleteApplicationFederatedCredential",
"eiam:DisableFederatedCredentialProvider",
"eiam:DeleteFederatedCredentialProvider",
"eiam:DisableApplication",
"eiam:DeleteApplication"
```

### Option C: System Policy (Coarse-Grained)

- `AliyunEIAMFullAccess` — the only system policy this skill needs.

## 4. Other Prerequisites (Not RAM Permissions)

1. **M2M paid feature enabled** on the instance (Enterprise Edition: upgrade to enable M2M and purchase application quota; Free Edition: enable extended services). Otherwise CreateApplication (m2m type) or token requests fail.
2. **PAM flow**: Privileged Access Management enabled (`CheckInstanceModuleStatus` probes this; `PAM_AUTH=module_disabled` does not block).
3. **Cluster side**: Kubernetes >= 1.21 (Bound ServiceAccount Token); API Server configured with `--service-account-issuer`; kubeconfig permissions for `get --raw` / `create token` / `exec`.
4. **Network**: the machine running the skill must reach `eiam.<region>.aliyuncs.com` (OpenAPI) and `https://<instance DefaultEndpoint>` (public token endpoint); **business pods** must reach the EIAM instance public endpoint (SDK runtime).
5. **STS flow extras (console only, no OpenAPI)**: Assets > Cloud Identity has onboarded the target cloud account and role; Permission Center > Data Permission Management has an authorization rule linking the M2M client to the target cloud role.
