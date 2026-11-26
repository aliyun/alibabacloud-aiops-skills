# Acceptance Criteria: alibabacloud-idaas-ack-m2m-federated-credential

**Scenario**: ACK RRSA + IDaaS EIAM OIDC Federation for M2M workloads
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

The skill wraps all `aliyun` CLI calls inside `scripts/ack.py`. The helper constructs commands as `aliyun <product> <Action> [params] --user-agent <UA>`. Below are the correct product, action, and parameter patterns.

## 1. STS - Security Token Service

#### CORRECT
```
aliyun sts GetCallerIdentity --region <region>
```
- Product: `sts`
- Action: `GetCallerIdentity`
- Key parameters: `--region`
- Returns: `AccountId`, `Arn`, `IdentityType`, `RequestId`

#### INCORRECT
```
aliyun sts get-caller-identity       # plugin-mode alias not used by this skill
aliyun sts GetCallerIdentity          # missing --region
```

## 2. CS - Container Service for Kubernetes

#### CORRECT
```
aliyun cs DescribeRegions --clusterType ManagedKubernetes --region <region>
aliyun cs DescribeClustersForRegion --region_id <region> --page_number 1 --page_size 50 --region <region>
aliyun cs DescribeClusterDetail --ClusterId <cluster-id> --region <region>
aliyun cs GetClusterAddonInstance --cluster_id <cluster-id> --instance_name ack-pod-identity-webhook --region <region>
```
- Product: `cs`
- Key parameters: `--ClusterId` (format: `c` + 32 hex chars), `--clusterType`, `--region_id`, `--page_number`, `--page_size`, `--instance_name`
- `DescribeRegions` returns `regions[]` with `regionId`
- `DescribeClustersForRegion` returns `page_info.total_count` and `clusters[]`
- `DescribeClusterDetail` returns `cluster_id`, `cluster_type`, `current_version`, `rrsa_config`, `state`, `profile`
- `GetClusterAddonInstance` returns `name`, `state`

#### INCORRECT
```
aliyun cs describe-regions                            # wrong product alias
aliyun cs DescribeClusterDetail --cluster-id c123     # cluster ID must be c + 32 hex
aliyun cs DescribeClustersForRegion --region cn-hangzhou  # parameter is --region_id not --region
```

## 3. IMS - Identity Management Service

#### CORRECT
```
aliyun ims GetOIDCProvider --OIDCProviderName <name> --region <region>
```
- Product: `ims`
- Key parameters: `--OIDCProviderName`
- Returns: `OIDCProvider.IssuerUrl`, `OIDCProvider.ClientIds`

#### INCORRECT
```
aliyun ram GetOIDCProvider --OIDCProviderName <name>   # RAM Action is GetOIDCProvider but CLI product is ims
aliyun ims get-oidc-provider                            # plugin-mode not used
```

## 4. EIAM - IDaaS EIAM

### Instance and License

#### CORRECT
```
aliyun eiam GetInstance --InstanceId <id> --region <region>
aliyun eiam GetInstanceLicense --InstanceId <id> --region <region>
```
- Instance ID format: `idaas_` + 6-64 lowercase alphanumeric chars
- `GetInstance` returns `Instance.InstanceId`, `Instance.Status`, `Instance.DefaultEndpoint.Endpoint`
- `GetInstanceLicense` returns `License.Edition`, `License.LicenseStatus`, `License.InstanceLicenseDetail.M2mApplicationLicenseStatus`

### Trust Source (FederatedCredentialProvider)

#### CORRECT
```
aliyun eiam ListFederatedCredentialProviders --InstanceId <id> --FederatedCredentialProviderType oidc --region <region>
aliyun eiam GetFederatedCredentialProvider --InstanceId <id> --FederatedCredentialProviderId <id> --region <region>
aliyun eiam CreateFederatedCredentialProvider --InstanceId <id> --force --method POST \
  --FederatedCredentialProviderName <name> --FederatedCredentialProviderType oidc \
  --NetworkAccessEndpointId inae_public \
  --OidcProviderConfig.Issuer <issuer-url> --OidcProviderConfig.Audiences.1 sts.aliyuncs.com \
  --OidcProviderConfig.JwksSource dynamic_from_issuer --yes --region <region>
```
- Provider ID format: `fcp_` + 6-64 lowercase alphanumeric chars
- Provider name format: 1-64 lowercase letters, digits, hyphens, underscores (start with letter/digit)
- `CreateFederatedCredentialProvider` uses `--force --method POST` for flattened nested parameters

#### INCORRECT
```
aliyun eiam CreateFederatedCredentialProvider --OidcProviderConfig Issuer=<url>   # wrong nested param format
aliyun eiam CreateFederatedCredentialProvider --OidcProviderConfig.Issuer <url>    # missing --force --method POST
```

### Application (M2M Client)

#### CORRECT
```
aliyun eiam ListApplications --InstanceId <id> --SsoType oidc+oauth2/m2m --PageNumber 1 --PageSize 100 --region <region>
aliyun eiam GetApplication --InstanceId <id> --ApplicationId <id> --region <region>
aliyun eiam CreateApplication --InstanceId <id> --ApplicationName <name> \
  --ApplicationSourceType urn:alibaba:idaas:app:source:standard \
  --SsoType oidc+oauth2/m2m --yes --region <region>
```
- Application ID format: `app_` + 6-64 lowercase alphanumeric chars
- Application name: nonblank, printable (capitalization and spaces allowed)
- `ListApplications` uses `--PageNumber`/`--PageSize` pagination (not NextToken)

#### INCORRECT
```
aliyun eiam ListApplications --NextToken <token>    # ListApplications uses page-based pagination
aliyun eiam CreateApplication --SsoType m2m          # correct value is oidc+oauth2/m2m
```

### Application Federated Credential

#### CORRECT
```
aliyun eiam ListApplicationFederatedCredentials --InstanceId <id> --ApplicationId <id> --region <region>
aliyun eiam CreateApplicationFederatedCredential --InstanceId <id> --ApplicationId <id> \
  --force --method POST \
  --FederatedCredentialProviderId <provider-id> \
  --ApplicationFederatedCredentialType oidc \
  --ApplicationFederatedCredentialName <name> \
  --VerificationMode structured \
  --OidcVerificationConfig.Profile kubernetes \
  --OidcVerificationConfig.KubernetesConfig.Namespace <ns> \
  --OidcVerificationConfig.KubernetesConfig.ServiceAccountName <sa> \
  --yes --region <region>
aliyun eiam GetApplicationFederatedCredential --InstanceId <id> --ApplicationId <id> \
  --ApplicationFederatedCredentialId <cred-id> --region <region>
```
- Credential name format: same as provider name (1-64 lowercase, digits, hyphens, underscores)
- `--VerificationMode` must be `structured`
- `--OidcVerificationConfig.Profile` must be `kubernetes`

#### INCORRECT
```
aliyun eiam CreateApplicationFederatedCredential --VerificationMode kubernetes  # mode is structured, profile is kubernetes
aliyun eiam CreateApplicationFederatedCredential --OidcVerificationConfig.Profile=structured  # reversed
```

### PAM Feature Permission

#### CORRECT
```
aliyun eiam ListResourceServerScopes --InstanceId <id> --ApplicationId iap_pam \
  --ResourceServerScopeType all --region <region>
aliyun eiam AuthorizeResourceServerToClient --InstanceId <id> \
  --ClientApplicationId <app-id> --ResourceServerApplicationId iap_pam --yes --region <region>
aliyun eiam AuthorizeResourceServerScopesToClient --InstanceId <id> \
  --ClientApplicationId <app-id> --ResourceServerApplicationId iap_pam \
  --force --method POST --ResourceServerScopeIds.1 <scope-id> --yes --region <region>
```
- PAM application ID is always `iap_pam` (built-in)
- PAM scope value is `cloud_account_role:obtain_access_credential`
- `AuthorizeResourceServerScopesToClient` uses `--force --method POST`

#### INCORRECT
```
aliyun eiam AuthorizeResourceServerScopesToClient --ResourceServerScopeIds <scope-id>  # must use .1 indexed format
aliyun eiam SetApplicationGrantScope --ApplicationId iap_pam                            # wrong API for PAM scope
```

### PAM Role Selection and Data Permission

#### CORRECT
```
aliyun eiam ListCloudAccounts --InstanceId <id> --region <region>
aliyun eiam ListCloudAccountRoles --InstanceId <id> --CloudAccountId <id> --region <region>
aliyun eiam GetCloudAccountRole --InstanceId <id> --CloudAccountId <id> --CloudAccountRoleId <id> --region <region>
aliyun eiam CreateAuthorizationRule --InstanceId <id> --ProjectId iprj_system_default \
  --AuthorizationRuleName <name> --AuthorizationResourceScope custom \
  --ClientToken ack-rule-<session-id> --yes --region <region>
aliyun eiam GetAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> --region <region>
aliyun eiam CreateAuthorizationResource --InstanceId <id> --AuthorizationRuleId <id> \
  --AuthorizationResourceEntityType cloud_account_role \
  --AuthorizationResourceEntityId <role-id> --ClientToken ack-resource-<session-id> --yes --region <region>
aliyun eiam AddApplicationToAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> \
  --ApplicationId <app-id> --ValidityType permanent --ClientToken ack-attachment-<session-id> --yes --region <region>
aliyun eiam ListAuthorizationResources --InstanceId <id> --AuthorizationRuleId <id> --region <region>
aliyun eiam ListAuthorizationRulesForApplication --InstanceId <id> --ApplicationId <id> --region <region>
```
- Cloud account ID format: `ca_` + 6-64 lowercase alphanumeric chars
- Cloud role ID format: `carole_` + 6-64 lowercase alphanumeric chars
- Role ARN format: `acs:ram::<8-20 digits>:role/<1-64 chars>`
- Rule must use `--ProjectId iprj_system_default` and `--AuthorizationResourceScope custom`
- `ClientToken` uses `ack-` prefix + session ID for idempotency

#### INCORRECT
```
aliyun eiam CreateAuthorizationRule --AuthorizationRuleScenarioLabel privileged_cloud_account  # wrong for direct role
aliyun eiam CreateAuthorizationResource --AuthorizationResourceEntityType cloud_account          # must be cloud_account_role
```

### Cleanup Operations

#### CORRECT
```
aliyun eiam ListApplicationsForAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> --region <region>
aliyun eiam RemoveApplicationFromAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> \
  --ApplicationId <id> --yes --region <region>
aliyun eiam DeleteAuthorizationResource --InstanceId <id> --AuthorizationRuleId <id> \
  --AuthorizationResourceId <id> --yes --region <region>
aliyun eiam DisableAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> --ClientToken ack-disable-<session> --yes --region <region>
aliyun eiam DeleteAuthorizationRule --InstanceId <id> --AuthorizationRuleId <id> --yes --region <region>
aliyun eiam DisableApplicationFederatedCredential --InstanceId <id> --ApplicationId <id> \
  --ApplicationFederatedCredentialId <id> --yes --region <region>
aliyun eiam DeleteApplicationFederatedCredential --InstanceId <id> --ApplicationId <id> \
  --ApplicationFederatedCredentialId <id> --yes --region <region>
aliyun eiam ListApplicationFederatedCredentialsForProvider --InstanceId <id> \
  --FederatedCredentialProviderId <id> --region <region>
aliyun eiam DisableFederatedCredentialProvider --InstanceId <id> --FederatedCredentialProviderId <id> --yes --region <region>
aliyun eiam DeleteFederatedCredentialProvider --InstanceId <id> --FederatedCredentialProviderId <id> --yes --region <region>
aliyun eiam DisableApplication --InstanceId <id> --ApplicationId <id> --yes --region <region>
aliyun eiam DeleteApplication --InstanceId <id> --ApplicationId <id> --yes --region <region>
```
- Cleanup order: rule links -> rule -> credential -> provider -> application
- Resources must be disabled before deletion
- Reused resources (owned=false) are preserved

#### INCORRECT
```
aliyun eiam DeleteAuthorizationRule --AuthorizationRuleId <id>           # must disable first
aliyun eiam DeleteApplication --ApplicationId <id>                        # must remove dependents first
aliyun eiam DeleteFederatedCredentialProvider --FederatedCredentialProviderId <id>  # must check dependents first
```

---

# Correct Parameter Formats

| Parameter | Pattern | Example |
|-----------|---------|---------|
| Region | `[a-z][a-z0-9-]{1,31}` | `cn-hangzhou`, `ap-southeast-1` |
| Cluster ID | `c[0-9a-f]{32}` | `c1234567890abcdef1234567890abcdef` |
| EIAM Instance ID | `idaas_[a-z0-9]{6,64}` | `idaas_abc123` |
| Provider ID | `fcp_[a-z0-9]{6,64}` | `fcp_abc123` |
| Application ID | `app_[a-z0-9]{6,64}` | `app_abc123` |
| Cloud Account ID | `ca_[a-z0-9]{6,64}` | `ca_abc123` |
| Cloud Role ID | `carole_[a-z0-9]{6,64}` | `carole_abc123` |
| Provider/Credential Name | `[a-z0-9][a-z0-9_-]{0,63}` | `finance-ack-trust` |
| Application Name | nonblank printable string | `Finance M2M Client` |
| Kubernetes Name | `[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?` | `default`, `my-namespace` |
| Role ARN | `acs:ram::<8-20 digits>:role/<1-64 chars>` | `acs:ram::123456789012:role/my-role` |
| PAM Scope | `identifier\|permission` | `urn:cloud:idaas:pam\|cloud_account_role:obtain_access_credential` |
| Session ID | `[a-z0-9]{8,32}` | random 32-char hex |

---

# Correct Helper Script Patterns

## Subcommand Invocation

#### CORRECT
```bash
python3 scripts/ack.py discover
python3 scripts/ack.py discover --ack-region cn-hangzhou
python3 scripts/ack.py workloads --context my-context
python3 scripts/ack.py preflight --ack-region cn-hangzhou --cluster-id c<32hex> \
  --eiam-region cn-shanghai --instance-id idaas_abc123 \
  --namespace default --service-account my-sa \
  --context my-context --pod my-pod --container my-container
python3 scripts/ack.py configure [scope-args] [pod-args] \
  --provider-name my-trust --app-name "My App" \
  --credential-name my-cred --pam-feature --state /tmp/state.json --confirmed
python3 scripts/ack.py verify [scope-args] [pod-args] --state /tmp/state.json
python3 scripts/ack.py verify [scope-args] [pod-args] --state /tmp/state.json --sts
python3 scripts/ack.py roles --eiam-region cn-shanghai --instance-id idaas_abc123
python3 scripts/ack.py grant [scope-args] --state /tmp/state.json \
  --cloud-account-id ca_abc123 --cloud-role-id carole_abc123 --rule-name my-rule --confirmed
python3 scripts/ack.py cleanup [scope-args] --state /tmp/state.json --confirmed
```

#### INCORRECT
```bash
python3 scripts/ack.py configure --provider-name x --app-name y  # missing --credential-name, --state, --confirmed
python3 scripts/ack.py verify --sts                                 # missing scope args, state, pod args
python3 scripts/ack.py cleanup --state /tmp/s.json                  # missing --confirmed and scope args
python3 scripts/ack.py grant --cloud-role-id carole_abc123          # missing --cloud-account-id, --rule-name
```

## Reuse Patterns

#### CORRECT - Reuse existing trust source
```bash
python3 scripts/ack.py configure [scope-args] [pod-args] \
  --provider-id fcp_existing123 --app-name "New App" \
  --credential-name new-cred --state /tmp/state.json --confirmed
```

#### CORRECT - Reuse existing M2M application
```bash
python3 scripts/ack.py configure [scope-args] [pod-args] \
  --provider-name new-trust --app-id app_existing123 \
  --credential-name new-cred --state /tmp/state.json --confirmed
```

#### INCORRECT - Mix create and reuse for same resource type
```bash
python3 scripts/ack.py configure --provider-name x --provider-id fcp_y  # mutually exclusive
python3 scripts/ack.py configure --app-name x --app-id app_y            # mutually exclusive
```

---

# Correct In-Pod Verification Patterns

The verification probe (`scripts/pod_verify.py`) runs inside the selected Pod via `kubectl exec`. It validates:

1. **RRSA token claims**: issuer matches ACK OIDC provider, audience is `sts.aliyuncs.com`, subject matches namespace/SA, token not expired
2. **M2M token exchange**: POST to EIAM token endpoint with `client_credentials` grant and OIDC assertion, verify `access_token` returned
3. **STS credential** (optional): Obtain STS via PAM Developer API, verify `GetCallerIdentity` returns the target role ARN
4. **Redirect rejection**: HTTP redirects are disabled to prevent assertion forwarding

#### INCORRECT
- Using the operator's CLI identity for in-Pod verification (probe uses mounted RRSA token)
- Sending tokens to non-EIAM endpoints
- Following HTTP redirects during token exchange
- Using static AK/SK for STS verification
