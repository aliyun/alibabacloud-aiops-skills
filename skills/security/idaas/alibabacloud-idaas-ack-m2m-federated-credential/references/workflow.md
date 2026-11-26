# ACK federation execution

Run the helper from the skill root. Use a private writable directory for state, for example an existing private session directory outside the repository. Keep shell variables in the current terminal and never include credential material.

Use [the user-run Kubernetes workflow](workbench.md) if the user executes the kubectl commands. The examples below use the agent's local kubeconfig.

~~~bash
export ALIBABA_CLOUD_PROFILE=approved-cli-profile
export ACK_SKILL_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
python3 scripts/ack.py discover
python3 scripts/ack.py discover --ack-region "$ACK_REGION"
python3 scripts/ack.py workloads --context "$CONTEXT"
python3 scripts/ack.py workloads --context "$CONTEXT" --namespace "$NS"

scope_args=(--ack-region "$ACK_REGION" --cluster-id "$CLUSTER_ID" \
  --eiam-region "$EIAM_REGION" --instance-id "$INSTANCE_ID" --namespace "$NS" --service-account "$SA")
pod_args=(--context "$CONTEXT" --pod "$POD" --container "$CONTAINER")
python3 scripts/ack.py preflight "${scope_args[@]}" "${pod_args[@]}"
~~~

The helper also accepts `--cli-profile` before the subcommand. It sets the Alibaba Cloud CLI credential environment variable for that process. In Alibaba Cloud CLI 3.5.1 the global `--profile` flag can also be passed to ACK list operations as the API's cluster subtype filter. Use `ALIBABA_CLOUD_PROFILE` instead. If a region list is empty, validate a known ID with `preflight`. Keep permission errors distinct from a successful empty list.

For a [new Pod with an explicit ServiceAccount token projection](workbench.md#create-a-pod-with-an-explicit-token-projection), add `--token-source projected` to the Pod arguments for preflight, configure and verify. Keep the default webhook mode for existing injected Pods.

### Select an EIAM instance

Use the [official EIAM service endpoint guide](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-endpoint) to show region choices. Once the region is selected, run the read-only [ListInstances API](https://help.aliyun.com/zh/idaas/eiam/developer-reference/api-eiam-2021-12-01-listinstances) using the selected CLI profile and Skill User-Agent.

~~~bash
aliyun eiam list-instances --region "$EIAM_REGION" --page-number 1 --page-size 20 \
  --user-agent "$ACK_SKILL_USER_AGENT"
~~~

Read all pages until the collected `Instances` match `TotalCount`. Report a failed or incomplete listing separately from an empty result. Show running instances by `Description` and `InstanceId`, ask the user to choose, and check the selected instance's license during preflight. Offer a different region if the selected region has no running instance. For a missing `eiam:ListInstances` grant, give the updated RAM policy or have the user choose the instance from the [EIAM console](https://idaas.console.aliyun.com/).

### Resource names

- For a new M2M Client, `--app-name` is the application display name. Enter a nonblank, printable name. Capitalization and spaces are allowed, as in `Finance M2M Client`.
- For a new trust source or application federated credential, the helper requires 1-64 lowercase ASCII letters, digits, hyphens, or underscores, starting with a letter or digit. Example names are `finance-ack-trust` and `finance-ack-rrsa`. [Trust source naming](https://help.aliyun.com/en/idaas/eiam/user-guide/federated-credential-provider-management) and [credential naming](https://help.aliyun.com/en/idaas/eiam/user-guide/create-application-federated-credential).

After approval, choose the applicable create or reuse arguments. Pass `--provider-id` in place of `--provider-name` to reuse a matching provider. Pass `--app-id` in place of `--app-name` to reuse an enabled M2M Client. The helper lists resources for conflict checks, then reads exact IDs. An optional `--pod-prefix` limits the credential to Pod names with that prefix. Production customers should use a dedicated namespace and ServiceAccount.

~~~bash
python3 scripts/ack.py configure "${scope_args[@]}" "${pod_args[@]}" \
  --provider-name "$PROVIDER_NAME" --app-name "$APP_NAME" \
  --credential-name "$CREDENTIAL_NAME" --pam-feature --state "$STATE" --confirmed
python3 scripts/ack.py verify "${scope_args[@]}" "${pod_args[@]}" --state "$STATE"
~~~

For an existing authorized business ResourceServer, configure without `--pam-feature` and run `verify --scope "$RESOURCE_SERVER_SCOPE"` with the exact `ResourceServerIdentifier|ScopeValue`. The helper does not create a business server or modify its grants.

The new provider uses the shared network endpoint `inae_public` and `dynamic_from_issuer`. The same provider can serve multiple applications when issuer, audience and use match. `CreateFederatedCredentialProvider` and `CreateApplicationFederatedCredential` use flattened nested parameters and an explicit POST when the CLI metadata does not accept nested flags directly. The profile is `kubernetes` inside `structured` mode, with fields `Namespace` and `ServiceAccountName`. EIAM compiles the verification condition.

For the default M2M check, authorize the M2M Client at the PAM ResourceServer level, then the specific `cloud_account_role:obtain_access_credential` scope by its ID. Query the built-in `iap_pam` application directly and call `ListResourceServerScopes` with type `all`. `SetApplicationGrantScope` controls a different allowlist.

## Optional STS

~~~bash
python3 scripts/ack.py roles --eiam-region "$EIAM_REGION" --instance-id "$INSTANCE_ID"
python3 scripts/ack.py roles --eiam-region "$EIAM_REGION" --instance-id "$INSTANCE_ID" \
  --cloud-account-id "$CLOUD_ACCOUNT_ID"
python3 scripts/ack.py grant "${scope_args[@]}" --state "$STATE" --rule-name "$RULE_NAME" \
  --cloud-account-id "$CLOUD_ACCOUNT_ID" --cloud-role-id "$CLOUD_ROLE_ID" \
  --expected-role-arn "$ROLE_ARN" --confirmed
python3 scripts/ack.py verify "${scope_args[@]}" "${pod_args[@]}" --state "$STATE" --sts
~~~

Offer the managed Alibaba Cloud accounts as choices first. After the user selects an account, offer its enabled user roles by name and ARN. Confirm the selected role, M2M application, and single-role rule before the grant. Create it with project `iprj_system_default` and `AuthorizationResourceScope=custom`. Omit `AuthorizationRuleScenarioLabel` for a direct `cloud_account_role` attachment. `privileged_cloud_account` expects a cloud permission template and rejects a direct role. Before M2M Token issuance the PAM feature grant is sufficient. Before STS issuance the M2M application must also belong to the data permission rule for the role.

The in-Pod verifier uses the mounted RRSA Token with `client_credentials` and `urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer`. It uses only the resolved EIAM default endpoint from the selected instance, disables HTTP redirects, and validates the account and role in the STS `GetCallerIdentity` response. Verification output contains no reusable credentials. For application integration, follow the official [ACK SDK example](https://help.aliyun.com/en/idaas/eiam/use-cases/ack-get-sts-token-without-static-credentials). Set `oidcTokenFilePathEnvVarName` to `ALIBABA_CLOUD_OIDC_TOKEN_FILE` and use the exact verified credential name.

## Failure handling and resource ownership

Inspect the state after a failed invocation. A known ID is recorded immediately, before any dependent write. Re-run with the same session and selections for recorded saves. If a create result is unknown, the pending entry gives the exact name and Action. Reconcile it with cloud state and the API request before retrying or cleaning up. Investigate expired client login, scoped permission errors, invalid references, issuer/JWKS retrieval, and Pod token failures separately.

After the user confirms the specific owned IDs:

~~~bash
python3 scripts/ack.py cleanup "${scope_args[@]}" --state "$STATE" --confirmed
~~~

Cleanup checks the rule's owned links and assets, removes them, then disables and deletes the rule, application federated credential, owned trust source, and owned application. It checks for remaining dependencies and verifies absence. It never deletes an existing cluster, workload, cloud role, or reused provider/client. If configuration granted a feature scope to a reused app, verify any desired revocation separately with the app owner.
