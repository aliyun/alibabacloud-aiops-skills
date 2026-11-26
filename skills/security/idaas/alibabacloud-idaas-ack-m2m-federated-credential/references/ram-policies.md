# RAM and Kubernetes permissions

Use a RAM user or role scoped to the intended account, ACK clusters, EIAM instance and dependent resource ARNs where the API permits. Grant the complete set of named Actions once for the approved resources. A known ACK cluster ID allows direct preflight. The discovery permissions support the region and cluster picker. See [ACK RAM authorization](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-ram), [EIAM OpenAPI reference](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-overview/), and [RAM OIDC provider readback](https://help.aliyun.com/zh/ram/developer-reference/api-ims-2019-08-15-getoidcprovider).

## Select permissions before running

On a permission failure, report the failed Action or Kubernetes verb, resource scope, and first error and request ID when available. Use the table below to identify the missing access. Offer `ram-permission-diagnose` if available for RAM failures. Stop the affected operation and resume when the user confirms the required access is in place.

For a RAM user or role, present the complete custom policy in one request before the first ACK or EIAM call. Include the entire workflow so the user can start with M2M and later verify STS without another permission request. Identify the cloud CLI principal and resolve the resource scope with the user or the RAM administrator. Ask for separate execution confirmation before writes. The target owning account needs no additional RAM grant. When the workflow reaches Kubernetes operations, identify the actual Kubernetes operator and check existing access before requesting RBAC.

For RAM, an administrator creates or updates a custom policy in **RAM console > Permission Management > Policies** and attaches it to the selected CLI user or role. Use the resource types documented for the individual Actions. For Kubernetes, an ACK administrator grants the listed verbs to the actual kubectl identity on the selected cluster and namespace. [Create a custom policy](https://help.aliyun.com/zh/ram/create-a-custom-policy), [grant permissions to a RAM user](https://help.aliyun.com/zh/ram/user-guide/grant-permissions-to-the-ram-user), and [ACK RBAC grant steps](preparation.md#kubernetes-access-by-login-identity)

| User's operation | Cloud RAM permissions | Kubernetes RBAC for the kubeconfig identity |
| --- | --- | --- |
| Find a region or cluster | `cs:DescribeRegions` and, for the regional list, `cs:DescribeClustersForRegion`. Provide a known cluster ID to skip these lookups. | None for the cloud lists. |
| Select an EIAM instance | `eiam:ListInstances` in the selected EIAM region. Provide a known EIAM region and instance ID to skip the list. | None. |
| Check RRSA and injection webhook readiness | `cs:DescribeClusterDetail` on the selected cluster. Add `cs:GetClusterAddonInstance` for webhook mode. | None. |
| Obtain a temporary kubeconfig from ACK | `cs:DescribeClusterUserKubeconfig` on the selected cluster. Include when requesting a temporary kubeconfig. | Check the resulting Kubernetes identity before using the configuration. |
| Prepare missing RRSA prerequisites after approval | Readiness Actions plus `cs:ModifyCluster` to enable RRSA, or `cs:ListAddons` and `cs:InstallClusterAddons` to install the missing webhook. | None for these ACK OpenAPI calls. |
| List resources to select a workload | The cloud discovery Actions apply if choosing the ACK cluster. | `list` on namespaces, then `list` on ServiceAccounts and Pods in the selected namespace. Supply exact names to skip these lists. |
| Prepare a user-approved test workload | Explicit token projection uses Kubernetes permissions. | `create` on namespaces for the agent-run new-namespace path, and on ServiceAccounts and Pods for new objects. The `kubectl wait` example uses `get`, `list` and `watch` on Pods. |
| Preflight an exact cluster and workload | `cs:DescribeClusterDetail`, `ram:GetOIDCProvider`, `eiam:GetInstance`, `eiam:GetInstanceLicense`, and `eiam:ListFederatedCredentialProviders`. Add `cs:GetClusterAddonInstance` for webhook mode. | `get` on the target namespace, ServiceAccount and Pod. The in-Pod check uses `pods/exec` on the selected Pod. The verb is `get` or `create` depending on the client transport. |
| Configure federation | Federation read Actions and `eiam:CreateApplicationFederatedCredential`. Add `eiam:CreateFederatedCredentialProvider` or `eiam:CreateApplication` only for the resources being created. | The helper repeats the preflight reads and Pod check. |
| Verify with the default PAM scope | Add the PAM feature permission Actions for the selected M2M Client. If using a caller-supplied business scope, use the scope that is already authorized. | The same in-Pod access used for preflight. |
| Obtain STS for an existing PAM role | Add the PAM role selection and data permission Actions for the selected role and its rule. | The same in-Pod access used for preflight. |
| Clean up owned resources | Add the confirmed cleanup Actions and the supporting EIAM read Actions for the affected resources. | None for the EIAM cleanup operations. |

Use the [ACK RBAC grant and verification steps](preparation.md#kubernetes-access-by-login-identity) to check the grants for the actual kubeconfig identity.

### Custom policy JSON for M2M federation

This policy covers the complete Skill, including discovery, temporary kubeconfig, RRSA and webhook preparation, both token sources, federation, linking an existing PAM role, STS verification, and cleanup of resources the Skill created. Present all statements in the initial request even when the user starts with M2M only. Granting the policy allows the CLI identity to perform these Actions. The Skill still asks separately before each planned write.

Replace the placeholders throughout the JSON with the approved values.

- `ACCOUNT_ID` is the Alibaba Cloud account ID.
- `ACK_CLUSTER_ARN` is `acs:cs:ACK_REGION:ACCOUNT_ID:cluster/CLUSTER_ID`. If multiple clusters are approved, provide their exact ARNs in both ACK statements.
- `RRSA_PROVIDER_ARN` is the selected cluster's `rrsa_config.oidc_arn`. If RRSA is still disabled, use the ACK-generated provider ARN `acs:ram::ACCOUNT_ID:oidc-provider/ack-rrsa-CLUSTER_ID` in the same request and verify it after enabling RRSA. For multiple clusters, include the corresponding provider ARNs. The OpenAPI name is `ims:GetOIDCProvider` and the RAM Action is `ram:GetOIDCProvider`.
- `EIAM_INSTANCE_ARN` is `acs:eiam:EIAM_REGION:ACCOUNT_ID:instance/INSTANCE_ID`. Replace it in both resource entries. The suffix `/*` covers resources inside that approved instance, including IDs created during the run. For multiple approved instances, include both entries for each.

Use known selections or ask for the approved cluster and EIAM instance IDs in the authorization message so that the administrator can finish the policy at once. The ACK catalog Actions that lack resource-level authorization use `Resource: "*"`. EIAM instance discovery is scoped to the selected account. `sts:GetCallerIdentity` normally works without an explicit grant. [ACK RAM authorization](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-ram), [EIAM RAM authorization](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-ram), [ACK-generated RRSA provider](https://help.aliyun.com/en/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services), and [GetOIDCProvider authorization](https://help.aliyun.com/zh/ram/developer-reference/api-ims-2019-08-15-getoidcprovider).

~~~json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeRegions",
        "cs:DescribeClustersForRegion",
        "cs:ListAddons"
      ],
      "Resource": [
        "*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeClusterDetail",
        "cs:GetClusterAddonInstance",
        "cs:DescribeClusterUserKubeconfig",
        "cs:ModifyCluster"
      ],
      "Resource": [
        "ACK_CLUSTER_ARN"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cs:InstallClusterAddons"
      ],
      "Resource": [
        "ACK_CLUSTER_ARN"
      ],
      "Condition": {
        "ForAllValues:StringEquals": {
          "cs:AddonNames": [
            "ack-pod-identity-webhook"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ram:GetOIDCProvider"
      ],
      "Resource": [
        "RRSA_PROVIDER_ARN"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "eiam:ListInstances"
      ],
      "Resource": [
        "acs:eiam:*:ACCOUNT_ID:instance/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "eiam:GetInstance",
        "eiam:GetInstanceLicense",
        "eiam:ListFederatedCredentialProviders",
        "eiam:GetFederatedCredentialProvider",
        "eiam:CreateFederatedCredentialProvider",
        "eiam:ListApplications",
        "eiam:GetApplication",
        "eiam:CreateApplication",
        "eiam:ListApplicationFederatedCredentials",
        "eiam:CreateApplicationFederatedCredential",
        "eiam:GetApplicationFederatedCredential",
        "eiam:ListResourceServerScopes",
        "eiam:AuthorizeResourceServerToClient",
        "eiam:AuthorizeResourceServerScopesToClient",
        "eiam:ListCloudAccounts",
        "eiam:ListCloudAccountRoles",
        "eiam:GetCloudAccountRole",
        "eiam:CreateAuthorizationRule",
        "eiam:GetAuthorizationRule",
        "eiam:CreateAuthorizationResource",
        "eiam:AddApplicationToAuthorizationRule",
        "eiam:ListAuthorizationResources",
        "eiam:ListAuthorizationRulesForApplication",
        "eiam:ListApplicationsForAuthorizationRule",
        "eiam:RemoveApplicationFromAuthorizationRule",
        "eiam:DeleteAuthorizationResource",
        "eiam:DisableAuthorizationRule",
        "eiam:DeleteAuthorizationRule",
        "eiam:DisableApplicationFederatedCredential",
        "eiam:DeleteApplicationFederatedCredential",
        "eiam:ListApplicationFederatedCredentialsForProvider",
        "eiam:DisableFederatedCredentialProvider",
        "eiam:DeleteFederatedCredentialProvider",
        "eiam:DisableApplication",
        "eiam:DeleteApplication"
      ],
      "Resource": [
        "EIAM_INSTANCE_ARN",
        "EIAM_INSTANCE_ARN/*"
      ]
    }
  ]
}
~~~

Have the RAM administrator open **Permission Management > Policies > Create Policy > Script Editor**, paste the completed JSON, and save it. Under **Identity Management > Users** or **Roles**, select the CLI identity and attach the custom policy. Use that same identity for discovery and the subsequent checks. [Create a custom policy](https://help.aliyun.com/zh/ram/create-a-custom-policy) and [grant permissions to a RAM user](https://help.aliyun.com/zh/ram/user-guide/grant-permissions-to-the-ram-user).

## Required permissions

The `required_permissions` inventory groups the exact RAM Actions by operation.

### Discover and preflight

- `sts:GetCallerIdentity`
- `cs:DescribeRegions`
- `cs:DescribeClustersForRegion`
- `cs:DescribeClusterDetail`
- `cs:GetClusterAddonInstance`
- `cs:DescribeClusterUserKubeconfig`
- `ram:GetOIDCProvider`
- `eiam:ListInstances`
- `eiam:GetInstance`
- `eiam:GetInstanceLicense`
- `eiam:ListFederatedCredentialProviders`

### Optional ACK RRSA preparation

- `cs:ModifyCluster`
- `cs:ListAddons`
- `cs:InstallClusterAddons`

Scope the two write Actions to `acs:cs:{regionId}:{accountId}:cluster/{ClusterId}` for the confirmed cluster. Use the `cs:AddonNames` condition for `ack-pod-identity-webhook` on the installation grant. The `cs:ListAddons` request filters by cluster ID and its RAM Action uses resource `*`. Run the preparation Actions only for the approved steps. [ModifyCluster authorization](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-modifycluster) and [InstallClusterAddons authorization](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-installclusteraddons)

### Federation configuration

- `eiam:GetFederatedCredentialProvider`
- `eiam:CreateFederatedCredentialProvider`
- `eiam:ListApplications`
- `eiam:GetApplication`
- `eiam:CreateApplication`
- `eiam:ListApplicationFederatedCredentials`
- `eiam:CreateApplicationFederatedCredential`
- `eiam:GetApplicationFederatedCredential`

### PAM feature permission

- `eiam:ListResourceServerScopes`
- `eiam:AuthorizeResourceServerToClient`
- `eiam:AuthorizeResourceServerScopesToClient`

### Optional PAM role selection and data permission

- `eiam:ListCloudAccounts`
- `eiam:ListCloudAccountRoles`
- `eiam:GetCloudAccountRole`
- `eiam:CreateAuthorizationRule`
- `eiam:GetAuthorizationRule`
- `eiam:CreateAuthorizationResource`
- `eiam:AddApplicationToAuthorizationRule`
- `eiam:ListAuthorizationResources`
- `eiam:ListAuthorizationRulesForApplication`

### Confirmed cleanup

Include the federation read Actions for the owned objects being removed. Application deletion also requires `eiam:ListAuthorizationRulesForApplication` to check for remaining rule bindings. Cleaning up an owned PAM rule requires `eiam:GetAuthorizationRule` and `eiam:ListAuthorizationResources` as well as the applicable rule cleanup Actions.

- `eiam:ListApplicationsForAuthorizationRule`
- `eiam:RemoveApplicationFromAuthorizationRule`
- `eiam:DeleteAuthorizationResource`
- `eiam:DisableAuthorizationRule`
- `eiam:DeleteAuthorizationRule`
- `eiam:DisableApplicationFederatedCredential`
- `eiam:DeleteApplicationFederatedCredential`
- `eiam:ListApplicationFederatedCredentialsForProvider`
- `eiam:DisableFederatedCredentialProvider`
- `eiam:DeleteFederatedCredentialProvider`
- `eiam:DisableApplication`
- `eiam:DeleteApplication`

`sts:GetCallerIdentity` verifies both the configured operator and the issued STS identity. It normally does not require an explicit RAM grant. Scope EIAM rule, application, provider and credential Actions to their selected parent instance with the resource types documented for each Action. The PAM resource-server and scope operations require the operator to manage feature permissions for the selected application.

The helper uses an existing kubeconfig context. The ACK API for preparing a temporary kubeconfig is `cs:DescribeClusterUserKubeconfig`. Kubernetes RBAC applies to the operator using kubectl. Discovery uses `list` on namespaces, ServiceAccounts and Pods. Providing exact names skips the listing permissions and preflight uses `get` on the selected objects. For namespace-scoped identities, grant `get` on the exact namespace through a ClusterRole binding that restricts the namespace resource name. In-Pod verification additionally requires permission on `pods/exec` for the selected Pod. Match the verb to the client transport, or grant `get` and `create` to support both. These operator permissions are separate from the workload's ServiceAccount and the PAM target role. See [ACK custom Kubernetes RBAC](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/customize-an-rbac-role).

The verification runtime uses the mounted RRSA token and then the EIAM bearer token. It does not use the operator's CLI identity or require static keys. For STS, the PAM data permission must name the selected role, and its existing RAM policy defines which business resource calls are permitted. See [ACK RBAC](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/authorization-overview/) and [M2M token invocation](https://help.aliyun.com/zh/idaas/eiam/user-guide/m2m-client-token-invocation-example).
