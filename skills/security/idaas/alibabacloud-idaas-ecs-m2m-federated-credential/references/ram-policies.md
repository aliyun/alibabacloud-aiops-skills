# RAM Permissions Required by This Skill

> Applies to the RAM user or role whose credentials are used to run `idaas-ecs-m2m-federated-credential` (the credentials configured through `aliyun configure`).
> Kept in sync with the scripts and workflow; cleanup permissions are needed only for explicitly authorized deletion.

## 1. Permission Details (Actions Mapped to Steps)

### 1.1 STS (No Explicit Authorization Required)

| Action | Step | Requirement |
|--------|------|-------------|
| `sts:GetCallerIdentity` | **Phase 0 prerequisites**: Validate credentials and retrieve the current AccountId as the default for "ECS owner account = current account" in Round 1. | Available to any RAM identity by default; no authorization required. |

### 1.2 EIAM (Core Permissions, Required)

| Action | Step | Requirement |
|--------|------|-------------|
| `eiam:ListInstances` | **Phase 1, Rounds 1/2**: `list_instances.py` lists EIAM instances in the selected region for the user to choose a target. | Required |
| `eiam:GetInstance` | **Phase 3 verification guidance**: Query `DefaultEndpoint.Endpoint` to construct the token endpoint `https://<endpoint>/api/v2/iauths_system/oauth2/token`. | Required |
| `eiam:ListFederatedCredentialProviders` | **Before Phase 2, step 1**: Check for provider name conflicts (append a suffix on conflict); verify cleanup results. | Required |
| `eiam:CreateFederatedCredentialProvider` | **Phase 2, step 1**: Create an ECS PKCS#7 federated credential provider (`create_trust_source.py`). | Required |
| `eiam:GetFederatedCredentialProvider` | **After Phase 2, step 1**: Read back and verify provider configuration. | Required for verification |
| `eiam:ListApplications` | **Phase 1, Round 3**: `list_m2m_apps.py` lists existing M2M applications for selection; also checks for application name conflicts. | Required |
| `eiam:CreateApplication` | **Phase 2, step 2**: Create an application when the user selects "Create an M2M client" (`create_m2m_client.py`). | Conditional; not needed when using an existing application. |
| `eiam:GetApplication` | **Phase 2, step 2**: Check that `M2MClientStatus` is enabled after creation. | Conditional, as above. |
| `eiam:EnableApplicationM2MClient` | **Phase 2, step 2**: Enable M2M client capabilities if not already enabled. | Conditional, as above. |
| `eiam:CreateApplicationFederatedCredential` | **Phase 2, step 3**: Create an application federated credential associating the provider with the client application (`create_federated_credential.py`). | Required |
| `eiam:CheckInstanceModuleStatus` | **Phase 2, step 4**: Check whether PAM is enabled (`authorize_pam_scope.py`) to determine whether to show PAM authorization guidance. | Required for the PAM flow. |
| `eiam:GetApplication` (iap_pam) | **Phase 2, step 4**: Query the PAM system application directly (fixed ID: `iap_pam`) and confirm RS status. | Required for the PAM flow. |
| `eiam:AuthorizeResourceServerToClient` | **Phase 2, step 4**: Automatically authorize at the RS level (Client → iap_pam), idempotently; scope-level authorization follows through AuthorizeResourceServerScopesToClient. | Required for the PAM flow. |
| `eiam:ListResourceServerScopes` | **Phase 2, step 4**: Resolve the actual PAM scope ID with ResourceServerScopeType=all. | Required for the PAM flow. |
| `eiam:AuthorizeResourceServerScopesToClient` | **Phase 2, step 4**: Authorize the resolved PAM scope to the client. | Required for the PAM flow. |
| `eiam:ListApplicationFederatedCredentialsForProvider` | **Phase 3 summary**: Verify application federated credential associations by provider. | Required for verification |

### 1.3 EIAM Cleanup and Rollback (Only When the User Explicitly Requests Deletion)

| Action | Step | Requirement |
|--------|------|-------------|
| `eiam:DisableApplicationFederatedCredential` | Disable the owned application federated credential before deletion. | Optional, for rollback. |
| `eiam:DeleteApplicationFederatedCredential` | Delete that disabled owned credential. | Optional, for rollback. |
| `eiam:DisableFederatedCredentialProvider` | Disable the owned provider before deletion. | Optional, for rollback. |
| `eiam:DeleteFederatedCredentialProvider` | Delete that disabled owned provider. | Optional, for rollback. |
| `eiam:DisableApplication` | Disable the owned M2M application before deletion. | Optional, for rollback. |
| `eiam:DeleteApplication` | Delete that disabled owned M2M application. | Optional, for rollback. |

### 1.4 ECS (Optional; Only Affects Instance Selection)

| Action | Step | Requirement |
|--------|------|-------------|
| `ecs:DescribeInstances` | **Phase 1, Round 3**: `list_ecs.py` lists ECS instances in the region for specific-instance mode (≤10 selected instances). | Optional. If unavailable, ask the user to enter instance IDs manually; **do not block the flow**. |

## 2. Permissions Explicitly Not Required

| Permission | Why it is not required |
|------------|------------------------|
| `ecs:RunCommand` / `ecs:InvokeCommand` (Cloud Assistant) | **The user runs the PKCS#7 signature command on ECS** and pastes back the result. The skill does not execute it remotely. |
| RAM permissions for token exchange | The IDaaS instance OAuth endpoint (specified in `oauth-token.openapi.yaml`) is an HTTP authentication API. It uses **federated credential authentication** (a PKCS#7 assertion), rather than RAM authentication. |
| Any RAM permission | The basic flow does not involve RAM. A later extension, "M2M token → AssumeRoleWithOIDC → STS", requires a RAM OIDC IdP and role trust policy. These are configured outside the instance and are outside this skill's scope. |

## 3. Authorization Policies (Ready to Paste into the RAM Console)

### Option A: Minimal Custom Policy (Recommended), for Creation and Verification Only

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
        "eiam:GetFederatedCredentialProvider",
        "eiam:CreateFederatedCredentialProvider",
        "eiam:ListApplications",
        "eiam:GetApplication",
        "eiam:CreateApplication",
        "eiam:EnableApplicationM2MClient",
        "eiam:CreateApplicationFederatedCredential",
        "eiam:ListApplicationFederatedCredentialsForProvider",
        "eiam:CheckInstanceModuleStatus",
        "eiam:AuthorizeResourceServerToClient",
        "eiam:ListResourceServerScopes",
        "eiam:AuthorizeResourceServerScopesToClient"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstances"],
      "Resource": "*"
    }
  ]
}
```

### Option B: Option A Plus Cleanup and Rollback (When Deletion Support Is Needed)

Append the following to the Action array of the first Statement in Option A:

```json
"eiam:DisableApplicationFederatedCredential",
"eiam:DeleteApplicationFederatedCredential",
"eiam:DisableFederatedCredentialProvider",
"eiam:DeleteFederatedCredentialProvider",
"eiam:DisableApplication",
"eiam:DeleteApplication"
```

### Existing System Policies (For User-Requested Comparison Only)

The minimal policies above are the default recommendation. The following names
may help a user understand an existing authorization; they are not required to
resolve a single denied Action and must not be requested as a blanket fix.

- `AliyunEIAMFullAccess` (all EIAM read/write operations, including deletion).
- `AliyunECSReadOnlyAccess` (only used to list ECS instances for selection).

## 4. Other Prerequisites (Unrelated to RAM Permissions)

1. **The paid M2M feature must be enabled on the instance**. Enterprise Edition requires an upgrade to enable M2M management and a purchased M2M application quota; Free Edition requires extended services. Otherwise, `CreateApplication` (m2m type) or token requests fail.
2. **The M2M server (ResourceServer) referenced by scope must already exist and authorize the client**. A token request with `scope=<ResourceServerIdentifier>|<ScopeValue>` requires the ResourceServer to be registered in the same instance and the client application to be authorized for the scope (`AuthorizeResourceServerScopesToClient`; the PAM path is automated by this skill; custom resource servers must be prepared separately).
3. **ECS**: The target instance must be able to access the metadata service at `100.100.100.200` (available by default). For hardened instances (IMDSv2), the generated signature command already includes the metadata token; no additional configuration is needed.
4. **Network**: The machine running the skill must be able to reach `eiam.<region>.aliyuncs.com` (OpenAPI) and `https://<instance_DefaultEndpoint>` (the public token endpoint).
