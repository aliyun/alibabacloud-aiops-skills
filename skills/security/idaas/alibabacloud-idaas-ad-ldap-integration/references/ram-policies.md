# RAM permissions

Use a dedicated RAM identity and grant only the actions needed for the current workflow. Never request or default to `eiam:*`, `ecs:*`, `AliyunEiamFullAccess`, or `AliyunECSFullAccess`. An account administrator must review and grant permissions; this Skill MUST NOT create or attach RAM policies automatically.

## Required permissions

| RAM action | Required operation |
|---|---|
| `eiam:GetInstance`, `eiam:ListNetworkAccessEndpoints` | Discover the authorized instance and available endpoints. |
| `eiam:GetNetworkAccessEndpoint` | Read the current IDaaS endpoint egress ranges. |
| `eiam:CreateIdentityProvider` | Create an AD/OpenLDAP identity provider after explicit confirmation. |
| `eiam:GetIdentityProvider` | Read identity-provider connection and basic configuration. |
| `eiam:GetIdentityProviderUdPullConfiguration` | Read inbound synchronization scope and schedule. |
| `eiam:GetIdentityProviderAuthnConfiguration` | Read delegated-authentication configuration through the verified private API via the SDK fallback. |
| `eiam:GetIdentityProviderUserProfileMapping` | Read the complete user-profile mapping through the verified API via the SDK fallback. |
| `eiam:SetIdentityProviderUserProfileMapping` | Overwrite the user-profile mapping after complete read-back and authorization. |
| `eiam:SetIdentityProviderUdPullConfiguration` | Change inbound synchronization scope, schedule, or protection thresholds after explicit confirmation. |
| `eiam:SetIdentityProviderAuthnConfiguration` | Change delegated-authentication configuration after explicit confirmation. |
| `eiam:EnableIdentityProviderUdPull`, `eiam:DisableIdentityProviderUdPull` | Enable or disable inbound synchronization after explicit confirmation. |
| `eiam:EnableIdentityProviderAuthn`, `eiam:DisableIdentityProviderAuthn` | Enable or disable delegated authentication after explicit confirmation. |
| `eiam:ListSynchronizationJobs`, `eiam:GetSynchronizationJob` | Read synchronization history and task status. |
| `eiam:RunSynchronizationJob` | Start a synchronization job after explicit confirmation. |
| `eiam:ListIdentityProviders` | List identity providers for discovery and verification. |
| `eiam:ListOrganizationalUnits`, `eiam:ListUsers`, `eiam:GetUser` | Verify synchronized organizations, accounts, and memberships. |
| `eiam:BindUserAuthnSourceMapping` | Bind an existing account only when the user explicitly selects that conflict-resolution path. |
| `ecs:AuthorizeSecurityGroup` | Optionally add the exact IDaaS egress CIDRs to a directory-server security group after explicit confirmation. |

Mapping APIs are absent from plugin mode but can be called as verified OpenAPIs through the SDK fallback. The API names are `GetIdentityProviderUserProfileMapping` and `SetIdentityProviderUserProfileMapping`; verify their current RAM action definitions before requesting permissions. A missing plugin command is not a reason to grant broad permissions or require console-only operation. See [mapping API usage](identity-provider-mapping-api.md).

For any permission-denial code (including `Forbidden.RAM` and `Forbidden.NoPermission`), preserve the actual code and RequestId, identify only the denied action, and stop dependent operations. Recommend only that action for the requested operation; do not append an unrelated read-only permission bundle. Do not invent a resource ARN from its name or URL: use the action's verified current RAM resource definition, or state that resource scoping remains to be verified. Do not create or attach policies, retry a deterministic denial, expand to wildcard actions or FullAccess, or call a simulation result a production incident.
