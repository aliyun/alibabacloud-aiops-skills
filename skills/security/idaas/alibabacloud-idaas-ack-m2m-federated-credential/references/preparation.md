# Preparation and troubleshooting

| Prerequisite | Readiness check | Official guidance |
| --- | --- | --- |
| Authenticated Alibaba Cloud CLI 3.5.1+ and Python 3.9+ on the agent, compatible kubectl in the execution terminal, and Python 3.9+ in the verification container | Check `aliyun version`, `kubectl version --client`, and `python3 --version` where each tool runs. Verify the selected CLI identity with STS `GetCallerIdentity` and follow the owning-account or RAM-principal path in the Skill. If the user runs kubectl, check connectivity from their [Workbench terminal](workbench.md). | [CLI authentication](https://help.aliyun.com/zh/cli/configure-credentials), [connect to ACK](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/access-clusters/) |
| Existing running ACK managed cluster, Kubernetes >=1.22, with RRSA OIDC enabled | Confirm the region and cluster ID and check the ACK-managed RAM OIDC provider. The expected audience is `sts.aliyuncs.com`. Check for an active `ack-pod-identity-webhook` when using webhook mode. | [Enable RRSA](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services#title-ymn-qe1-39y), [install the injection webhook](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services#step-cvk-g5g-gan) |
| EIAM Enterprise instance with machine identity management enabled | `GetInstance` must return a running instance with a resolved Alibaba Cloud default endpoint. `GetInstanceLicense` must return `Edition=enterprise`, `LicenseStatus=valid` and `InstanceLicenseDetail.M2mApplicationLicenseStatus=enabled`. This is the supported starting point for the workflow. | [EIAM instance management](https://help.aliyun.com/zh/idaas/eiam/user-guide/instance-management), [machine identity management and billing](https://help.aliyun.com/zh/idaas/eiam/product-overview/pricing), [license API](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-getinstancelicense) |
| A selected, ready Pod, its ServiceAccount and the correct kubectl context | Read the Pod's actual ServiceAccount, check the RRSA injection metadata and projection, and run the token-claim probe in the chosen container. The selected container must be ready and contain Python 3. Choose a designated test Pod if the workload image has no Python. | [RRSA workload configuration](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services), [ACK RBAC](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/grant-rbac-permissions-to-ram-users-or-ram-roles) |
| Runtime network access | The Pod can reach the EIAM instance's default token endpoint. STS verification additionally uses the regional EIAM Developer API and STS public HTTPS endpoints. | [M2M token exchange](https://help.aliyun.com/zh/idaas/eiam/user-guide/m2m-client-token-invocation-example), [ACK to EIAM](https://help.aliyun.com/en/idaas/eiam/use-cases/ack-get-sts-token-without-static-credentials) |
| PAM feature or a business scope | For the default PAM-scoped M2M flow, make sure PAM is available and select the exact built-in feature scope. If using an existing business resource server, provide the exact scope already granted to the selected Client. | [M2M client integration](https://help.aliyun.com/zh/idaas/implementing-m2m-integration-for-oidc-m2m-applications-using-the-client-credentials-grant-type) |
| Optional STS target | An enabled PAM cloud role managed in the selected EIAM instance and an approved least-privilege test target. | [Prepare PAM cloud assets](https://help.aliyun.com/zh/idaas/eiam/user-guide/cloud-identity-management) |

## Select how to connect

Offer three execution choices in the user's language: **Skill runs on this machine**, **User runs in ACK Workbench**, and **User runs in their own terminal**. Include the actor in the label when combining execution and network choices, for example **Skill runs on this machine via the public API Server**. Use the cluster session in Workbench. For direct access from either terminal, offer the available **public API Server** and **private API Server** endpoints as choices. Confirm the execution environment can reach the selected endpoint before testing RBAC.

For agent-run access, inspect the files selected by `KUBECONFIG` or the default `~/.kube/config` in that terminal. A kubeconfig stores cluster connection settings and credentials or a credential reference. A context is its named combination of cluster, user and default namespace. Get the current context and list context names locally. Inspect only the endpoint and context metadata needed to match the selected ACK cluster and access path. Use a single verified match or offer multiple verified matches by name. [Kubernetes kubeconfig and contexts](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)

~~~bash
kubectl config current-context
kubectl config get-contexts -o name
~~~

If no matching context is available, offer to obtain a temporary kubeconfig from ACK with the selected cloud CLI identity, use an existing local kubeconfig file the user selects, or switch to a user-run path. The temporary option requires `cs:DescribeClusterUserKubeconfig` on the cluster. Ask for a file location only when the user chooses an existing file that the agent cannot locate. Read the context choices from that file. For a temporary kubeconfig, set `PrivateIpAddress` to match the chosen endpoint, use a short `TemporaryDurationMinutes`, and store the returned config in a private session-local file. Keep the credentials out of chat and command output. Verify connectivity and permissions against the selected context. [ACK temporary kubeconfig API](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-describeclusteruserkubeconfig)

## Kubernetes access by login identity

- **Owning Alibaba Cloud account.** Use the kubeconfig issued to the primary account for the selected cluster. ACK grants this account cluster access by default, so the operator can proceed without a separate Kubernetes RBAC grant. [ACK authorization overview](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/authorization-overview/)
- **RAM user or RAM role.** Check the identity in the actual execution context, such as the user's Workbench session or the role used to obtain the runner's temporary kubeconfig. RAM policy governs cloud OpenAPI calls such as `cs:DescribeClusterUserKubeconfig`. Kubernetes RBAC on the selected cluster governs kubectl. A successful kubeconfig request or an administrator's successful connection leaves the operator's RBAC pending until checked.

### Grant and verify ACK RBAC

Give these steps to the user when explaining Kubernetes access. Use the cluster and identity the user selected when they are known.

1. Identify the RAM user or role that will run `kubectl`, the target cluster, and the workload path. Reuse existing permissions when they pass the applicable checks.
2. Have the owning account or a cluster administrator create the custom rules below. In **ACK console > Authorization Management**, select **RAM Users** or **RAM Roles**, find the kubectl identity, and use **Manage Permissions > Add Permissions > Custom** with the target cluster and namespace for the namespaced rules. Bind the separate Namespace resource rules at cluster scope to the same identity. When the Skill will create a namespace, agree on both bindings in advance so the administrator can apply the namespaced binding once the namespace exists. [ACK custom RBAC roles and binding](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/customize-an-rbac-role#ec41636691f42)
3. Verify access in the intended terminal with the same identity and context. Check list permissions only for the selectors the user needs. Before the Pod probe, verify the named Namespace, ServiceAccount and Pod reads and the required `pods/exec` verb. Before creating resources, check the corresponding `create` permissions at the scope where they will be used. [ACK RBAC grant steps](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/grant-rbac-permissions-to-ram-users-or-ram-roles#h3-auth-operation)

### Choose permissions for the workload path

| Workload path | Cluster-scoped rules | Namespace-scoped rules |
| --- | --- | --- |
| Reuse an existing namespace and ready Pod | Allow `get` on `namespaces` with `resourceNames` set to the selected namespace. Add a separate `list namespaces` rule only when needed for discovery. | Allow `get` on the selected `serviceaccounts` and `pods`. For `pods/exec`, scope `get` and `create` to the selected Pod by name for kubectl transport compatibility. Add separate `list` rules for workload discovery when needed. |
| Create a Pod in an existing namespace | Use the same Namespace access. | Add `create pods` and the `get/list/watch` access used by the readiness command. Add `create serviceaccounts` when creating a dedicated ServiceAccount. The Skill's explicit token projection requires only the create, readiness and verification permissions. |
| Skill creates a new test namespace and workload | Allow the named Namespace read and a separate `create namespaces` rule. | The administrator sets up the RoleBinding after namespace creation. Verify access to create and check a dedicated ServiceAccount and Pod, including readiness and exec, before the workload writes. |

Use a ClusterRoleBinding for cluster-scoped Namespace rules and a RoleBinding in the selected namespace for workload rules. Kubernetes RBAC can restrict named reads and `pods/exec` by resource name. Top-level `create` grants apply at their binding scope. If an administrator prefers to retain namespace creation, have them create it and use the existing-namespace path. [Kubernetes RBAC resource and subresource rules](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#referring-to-resources)

In an isolated test cluster, a user may choose the ACK **Operations** preset (`cs:ops`) when reusing a namespace or **Administrator** (`cs:admin`) when the Skill creates a namespace. Operations includes cluster-wide workload access, including Secrets. Administrator includes cluster-wide Kubernetes administration. Verify the same access checks if the user selects a preset. [ACK preset role descriptions](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/grant-rbac-permissions-to-ram-users-or-ram-roles#f23afb6c64f60), [Operations preset rules](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/best-practices-of-authorization#title-qa1-6sb-0mn)

Enabling RRSA and installing its webhook require cloud RAM permissions. Use the same RBAC guidance for public access, private access and Workbench. [RAM permission selection](ram-policies.md#select-permissions-before-running)

| Action | Check before using the permission |
| --- | --- |
| Create a Pod | `kubectl --context "$CONTEXT" -n "$NS" auth can-i create pods` |
| Create a ServiceAccount | `kubectl --context "$CONTEXT" -n "$NS" auth can-i create serviceaccounts` |

When the names are known, check the actual reads and the required exec permission from the intended terminal. Set `CONTEXT`, `NS`, `SA` and `POD` to the confirmed values. Use the already selected context in Workbench.

~~~bash
kubectl --context "$CONTEXT" --request-timeout=10s get namespace "$NS" -o name
kubectl --context "$CONTEXT" --request-timeout=10s -n "$NS" get serviceaccount "$SA" -o name
kubectl --context "$CONTEXT" --request-timeout=10s -n "$NS" get pod "$POD" -o name
kubectl --context "$CONTEXT" --request-timeout=10s -n "$NS" auth can-i create "pods/$POD" --subresource=exec
~~~

Check `get` on the exec subresource when required by the client transport. Confirm actual exec during the selected Pod's probe. For `Unauthorized`, check the selected kubeconfig, credential identity and expiration. For `Forbidden`, identify the missing RBAC verb and resource scope. If the helper reports a combined authentication or RBAC error, use the direct check to distinguish them. A timeout or TLS error calls for a connection check from that terminal. Repeat the failed operation with the same identity after the issue is resolved. [kubectl auth can-i](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/)

### Create a new test namespace

Use the selected agent-run connection for this path. Confirm the target cluster, namespace, dedicated ServiceAccount, Pod, and image with the user. Check the agent's ability to create namespaces and read the exact namespace name.

~~~bash
kubectl --context "$CONTEXT" --request-timeout=10s auth can-i create namespaces
kubectl --context "$CONTEXT" --request-timeout=10s get namespace "$NS" -o name
~~~

Proceed when the permission check returns `yes` and the exact namespace read returns `NotFound`. Create it with `kubectl --context "$CONTEXT" create namespace "$NS"` and verify the returned name. Have the administrator apply the agreed namespace binding if the selected identity still needs it. Verify the workload permissions from the same context and confirm that the Pod and ServiceAccount names are free. Create both with the approved [workload commands](workbench.md#select-and-prepare-the-workload). An `AlreadyExists` response at any creation step requires a new name and confirmation before continuing.

## Public API Server access

Ask which environment will run kubectl, for example the local agent host or the evaluation runner. In **ACK > Cluster Information > Basic Information > Network**, identify the selected cluster's public API Server endpoint and the load balancer serving it. Use the public kubeconfig for the selected identity, preferably a temporary one, and verify its `server` host and port locally. Share only the endpoint and context name with the user. The usual listener is TCP 6443. The same kubectl workload commands apply once that endpoint is reachable. [Connect to an ACK cluster](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/access-clusters/) and [get kubeconfig](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/obtain-the-kubeconfig-file-of-a-cluster-and-use-kubectl-to-connect-to-the-cluster/)

| Public endpoint type | Connection and allowlist location |
| --- | --- |
| CLB with an EIP | The public kubeconfig points to the CLB's public EIP. Find the ACL attached to that CLB's TCP 6443 listener. Tell the customer the CLB and ACL IDs, if available. Public and private endpoints can share this listener, so preserve the ACK management and VPC or vSwitch ranges required by the existing policy. [ACK CLB access control](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/configure-network-acls-for-the-api-server-of-an-ack-cluster) |
| Public NLB | Use the public hostname in the kubeconfig and verify that it resolves and matches the API Server TLS certificate. Find the security group attached to the **public NLB**, and report the NLB and security group IDs, if available. Check the effective inbound security group policy for the listener. Select this resource by its actual association with the public endpoint. [ACK NLB connection guide](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/connect-to-the-cluster-api-server-through-nlb) and [NLB security groups](https://help.aliyun.com/zh/slb/network-load-balancer/user-guide/add-an-nlb-instance-to-a-security-group/) |

Test with the public kubeconfig from the actual execution environment. Check TCP to the selected endpoint, then run `kubectl --context "$CONTEXT" --request-timeout=10s get --raw=/version` and read the selected namespace. Report the network and TLS result, the authenticated resource read, and any Kubernetes RBAC error separately. A TCP timeout leaves the network cause unresolved. A successful local read establishes local access. A runner needs its own check.

If access already works, tell the customer that no additional allowlist entry is needed for that execution environment. If an allowlist change is needed, ask for the verified source IP or approved CIDR for traffic from the actual execution environment to the ACK endpoint. HTTP IP echo results are hints and may differ by destination, proxy or network path. Keep public access limited to the approved sources, use TLS verification and Kubernetes authentication, and follow the customer's approval process for network changes. Report the verified connection source, public endpoint, load balancer type and ID, ACL or security group ID, and any remaining uncertainty. AgentHub runner access and Pod-to-EIAM or STS connectivity require their own evidence.

## Check and prepare ACK RRSA

Use the confirmed ACK region and cluster ID. Keep the same authenticated CLI profile and session throughout. Run the add-on check below for webhook mode. In the examples, `ACK_SKILL_USER_AGENT` is the User-Agent built from the session ID and manifest version in the Skill.

~~~bash
aliyun cs describe-cluster-detail --cluster-id "$CLUSTER_ID" --region "$ACK_REGION" \
  --user-agent "$ACK_SKILL_USER_AGENT"
aliyun cs get-cluster-addon-instance --cluster-id "$CLUSTER_ID" \
  --instance-name ack-pod-identity-webhook --region "$ACK_REGION" \
  --user-agent "$ACK_SKILL_USER_AGENT"
~~~

- Check that cluster details match the selected region and ID and report a running ACK managed cluster on Kubernetes 1.22 or later. An absent RRSA configuration or `enabled=false` means RRSA needs enabling. A reported enabled state with a missing OIDC provider name needs investigation. In webhook mode, also check the webhook status.
- Treat `AddonNotFound` as a missing webhook. An existing `active` webhook is ready. For an existing webhook in any other state, report that state and wait for an in-progress install or diagnose the problem. For any other API error, report the error and request ID and keep that check unresolved.
- Before a write, show the target cluster, the missing operations, and the applicable [RAM permissions](ram-policies.md#optional-ack-rrsa-preparation). Explain that enabling RRSA updates the cluster and caps newly issued ServiceAccount tokens at 12 hours. Get explicit authorization for each operation to be performed. If the user declines or chooses manual setup, share the relevant console steps below and stop before federation configuration if a prerequisite is still pending.

### Enable RRSA after approval

Recheck the target and current state immediately before the write. If RRSA is already enabled, continue with the selected token source. For a confirmed missing RRSA configuration, use the [ModifyCluster API](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-modifycluster).

~~~bash
aliyun cs modify-cluster --cluster-id "$CLUSTER_ID" --region "$ACK_REGION" \
  --enable-rrsa true --user-agent "$ACK_SKILL_USER_AGENT"
~~~

Wait for `DescribeClusterDetail` to report `state=running`, `rrsa_config.enabled=true` and an OIDC provider name before treating RRSA as ready. If the request times out or the outcome is unclear, read back cluster state before considering another write.

### Install the webhook after approval

Once RRSA is enabled and the cluster has returned to Running, recheck the webhook. For `AddonNotFound`, call [ListAddons](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-listaddons) with the target cluster ID. Use the version returned for the exact component when its `supported_actions` includes `Install`. If the component or an installable version is unavailable, report that and share the console steps.

~~~bash
aliyun cs list-addons --cluster-id "$CLUSTER_ID" --region "$ACK_REGION" \
  --user-agent "$ACK_SKILL_USER_AGENT"
~~~

Build the JSON array with the selected version and call the [InstallClusterAddons API](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/developer-reference/api-cs-2015-12-15-installclusteraddons).

~~~bash
ACK_ADDON_BODY=$(python3 -c 'import json, sys; print(json.dumps([{"name": "ack-pod-identity-webhook", "version": sys.argv[1]}]))' "$ACK_ADDON_VERSION")
aliyun cs install-cluster-addons --cluster-id "$CLUSTER_ID" --region "$ACK_REGION" \
  --biz-body "$ACK_ADDON_BODY" \
  --user-agent "$ACK_SKILL_USER_AGENT"
~~~

Record the returned task and request IDs when present. Poll `GetClusterAddonInstance` until the exact component reports `state=active` or a failure. Check the current state before any retry. If polling times out, report the last observed state and keep the step pending. Run full preflight once both cluster prerequisites and the selected EIAM instance and workload are ready.

### Manual console steps

- To enable RRSA, open the target ACK cluster's Basic Information tab and find RRSA OIDC under Security and Auditing. [Enable RRSA](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services#title-ymn-qe1-39y)
- To install the webhook, open Operations > Add-ons, go to Security, and install `ack-pod-identity-webhook`. [Install the injection webhook](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/use-rrsa-to-authorize-pods-to-access-different-cloud-services#step-cvk-g5g-gan)

## Pod has no RRSA Token

1. Check the selected cluster reports `rrsa_config.enabled=true` and the webhook is active.
2. Check the selected namespace label `pod-identity.alibabacloud.com/injection=on` and ServiceAccount annotation `pod-identity.alibabacloud.com/role-name`. The RRSA injection role's trust should reference the cluster's ACK RAM OIDC provider, the same issuer, `sts.aliyuncs.com`, and the exact subject `system:serviceaccount:NAMESPACE:SERVICE_ACCOUNT`.
3. Check that the Pod actually uses that ServiceAccount. After fixing the namespace or ServiceAccount, create a new Pod using the approved workload process so the admission webhook can run. Verify the projected `rrsa-oidc-token` volume and the selected container's `ALIBABA_CLOUD_OIDC_TOKEN_FILE`.
4. Run `preflight` again. It checks file readability, issuer, audience, expiration, and namespace, ServiceAccount, and Pod claims in the container. It never prints the raw Token.

For access problems check the selected context, network route, cloud RAM policy, and workload RBAC separately. No cloud permissions need to be attached to an RRSA role used only for injection. Make changes to namespace labels, ServiceAccounts, RAM roles, or workloads through the customer's approved environment setup.
