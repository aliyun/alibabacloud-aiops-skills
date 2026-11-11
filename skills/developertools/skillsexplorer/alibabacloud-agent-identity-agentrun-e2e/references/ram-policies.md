# RAM Permissions Required by This Skill

Every cloud call this skill makes is listed in `related_apis.yaml`. This
document maps those calls to the RAM actions the operator's identity needs,
and describes the one role the skill grants a policy to.

The `agentidentity:` prefix is confirmed by the system policies
`AliyunAgentIdentityFullAccess` (`agentidentity:*`) and
`AliyunAgentIdentityReadOnlyAccess` (`agentidentity:Get*`, `agentidentity:List*`).

## 1. Identity running the skill

The operator authenticates through the aliyun CLI profile (`aliyun configure`,
AK mode). That identity needs the actions below.

| Phase / script | API | RAM action | Auth level |
|---|---|---|---|
| 1 — credential check | Sts `GetCallerIdentity` | none required | — |
| 2.1 — identity provider | AgentIdentity `GetIdentityProvider` | `agentidentity:GetIdentityProvider` | resource |
| 2.1 — identity provider | AgentIdentity `CreateIdentityProvider` | `agentidentity:CreateIdentityProvider` | resource |
| 2.2 — OAuth2 callback backfill | Ims `UpdateApplication` | `ram:UpdateApplication` | resource (Application) |
| 2.2 — backfill verification | Ims `GetApplication` | `ram:GetApplication` | resource (Application) |
| 2.2 — scope availability check | Ims `ListPredefinedScopes` | none required | — |
| 2.5 — API-key provider | AgentIdentity `GetAPIKeyCredentialProvider` | `agentidentity:GetAPIKeyCredentialProvider` | resource |
| 2.5 — API-key provider | AgentIdentity `CreateAPIKeyCredentialProvider` | `agentidentity:CreateAPIKeyCredentialProvider` | resource |
| 2.6 — existing bucket check | Oss `GetBucketInfo` | `oss:GetBucketInfo` | resource (Bucket) |
| 2.6 — existing object check | Oss `HeadObject` | `oss:GetObject` | resource (Object) |
| 2.6 — OSS test fixture | Oss `PutBucket` | `oss:PutBucket` | resource (Bucket) |
| 2.6 — OSS test fixture | Oss `PutObject` | `oss:PutObject` | resource (Object) |
| 2.6 — OSS read-back | Oss `GetObject` | `oss:GetObject` | resource (Object) |
| 3.5 — locate runtime identity | AgentIdentity `ListWorkloadIdentities` | `agentidentity:ListWorkloadIdentities` | resource |
| 3.5 — existing role permission check | Ram `ListPoliciesForRole` | `ram:ListPoliciesForRole` | resource (Role) |
| 3.5 — grant OSS read to the role | Ram `AttachPolicyToRole` | `ram:AttachPolicyToRole` | resource (Policy, Role) |
| 4 — existing policy set check | AgentIdentity `GetPolicySet` | `agentidentity:GetPolicySet` | resource |
| 4 — existing policy check | AgentIdentity `ListPolicies` | `agentidentity:ListPolicies` | resource |
| 4 — Cedar policy set | AgentIdentity `CreatePolicySet` | `agentidentity:CreatePolicySet` | resource |
| 4 — Cedar policy | AgentIdentity `CreatePolicy` | `agentidentity:CreatePolicy` | resource |
| 6 — binding check before policy cleanup | AgentIdentity `ListPolicySetAttachedGateways` | `agentidentity:ListPolicySetAttachedGateways` | resource |
| 6 — cleanup | AgentIdentity `DeletePolicy` | `agentidentity:DeletePolicy` | resource |
| 6 — cleanup | AgentIdentity `DeletePolicySet` | `agentidentity:DeletePolicySet` | resource |
| 6 — cleanup | Oss `DeleteObject` | `oss:DeleteObject` | resource (Object) |
| 6 — cleanup | Oss `DeleteBucket` | `oss:DeleteBucket` | resource (Bucket) |
| 6 — restore a reused role, only if this run added the policy | Ram `DetachPolicyFromRole` | `ram:DetachPolicyFromRole` | resource (Policy, Role) |

Console-only steps (RAM OAuth application, AgentIdentity OAuth2 credential
provider, model service, MCP tool registration, policy-set binding, Runtime
creation) are performed by the user in the browser with their own console
permissions; they are not covered by this policy.

## 2. Policy example for the operator

Sufficient for everything the scripts do. The OSS actions are scoped to bucket
names matching `e2e-test-*`; update the bucket ARNs if `E2E_OSS_BUCKET` is overridden.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentidentity:GetIdentityProvider",
        "agentidentity:CreateIdentityProvider",
        "agentidentity:GetAPIKeyCredentialProvider",
        "agentidentity:CreateAPIKeyCredentialProvider",
        "agentidentity:ListWorkloadIdentities",
        "agentidentity:GetPolicySet",
        "agentidentity:ListPolicies",
        "agentidentity:ListPolicySetAttachedGateways",
        "agentidentity:CreatePolicySet",
        "agentidentity:CreatePolicy",
        "agentidentity:DeletePolicy",
        "agentidentity:DeletePolicySet"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ram:GetApplication",
        "ram:UpdateApplication",
        "ram:ListPoliciesForRole",
        "ram:AttachPolicyToRole",
        "ram:DetachPolicyFromRole"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutBucket",
        "oss:GetBucketInfo",
        "oss:DeleteBucket"
      ],
      "Resource": "acs:oss:*:*:e2e-test-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:GetObject",
        "oss:DeleteObject"
      ],
      "Resource": "acs:oss:*:*:e2e-test-*/*"
    }
  ]
}
```

The system policies `AliyunAgentIdentityFullAccess`, `AliyunRAMFullAccess`,
and `AliyunOSSFullAccess` grant broader permissions than this example.
Prefer the custom policy above for shared accounts.

## 3. CLI credential mode

Configure the CLI in AK mode (`aliyun configure`) for this workflow. If an
OAuth profile returns `AuthorizationFail.AkProxy` for a required RAM operation,
check the action named in the error and the profile permissions.

## 4. The role the skill grants a policy to

Deploying the Runtime with AgentIdentity credential configuration auto-creates
a platform-managed workload identity
(`agentrun-<runtime-id>`) backed by a role (`agentrole-xxxxx`). The gateway
issues that identity's Workload Access Token, and the sample's local OSS tool
reads the test file with credentials exchanged for it.

`05_attach_role_policy.sh` therefore attaches the system policy
**`AliyunOSSReadOnlyAccess`** to that role. This is the only permission the
skill grants to any identity other than the operator's own, and it is required
for the Group C verification case to pass.

Do not create or edit that workload identity by hand: it is platform-managed
(`WorkloadIdentityPlatformMismatch`), and deleting the Runtime removes it.
