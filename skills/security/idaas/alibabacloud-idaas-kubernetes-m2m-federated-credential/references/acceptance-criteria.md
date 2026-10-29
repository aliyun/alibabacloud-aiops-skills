# Acceptance Criteria: alibabacloud-idaas-kubernetes-m2m-federated-credential

**Scenario**: IDaaS EIAM Kubernetes M2M Federated Credential (OIDC, Without AK)
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — `eiam` (IDaaS/EIAM product subcommand)

#### ✅ CORRECT
```bash
aliyun eiam list-instances --region cn-hangzhou
aliyun eiam create-federated-credential-provider --region cn-hangzhou --instance-id <iid> ...
aliyun eiam get-instance --region cn-hangzhou --instance-id <iid>
```

#### ❌ INCORRECT
```bash
aliyun idaas list-instances          # Wrong product name; correct is `eiam`
aliyun eiam listInstances            # Neither documented PascalCase nor kebab-case API spelling
```

## 2. Command — documented API and plugin spellings

#### ✅ CORRECT
```bash
aliyun eiam create-federated-credential-provider --region cn-hangzhou --instance-id <iid> --federated-credential-provider-name k8s-oidc-trust --force --method POST
aliyun eiam disable-application-federated-credential --region cn-hangzhou --instance-id <iid> --application-id <app_id> --application-federated-credential-id <afc_id>
aliyun eiam delete-federated-credential-provider --region cn-hangzhou --instance-id <iid> --federated-credential-provider-id <fcp_id>
```

#### ❌ INCORRECT
```bash
aliyun eiam createFederatedCredentialProvider ...    # Undocumented mixed-case spelling
aliyun eiam create_federated_credential_provider ...  # Undocumented snake_case spelling
```

> **Note:** Some EIAM APIs (Create/Update FederatedCredentialProvider, CreateApplicationFederatedCredential) require `--force --method POST` with flattened dot-notation parameters for nested config fields. This is a documented exception for APIs that need nested JSON structures passed as dot-separated parameters.

Both PascalCase API commands (used by bundled scripts) and kebab-case plugin commands are supported by the installed CLI. Check `aliyun eiam <command> --help` for the matching parameter spelling; do not reject a valid bundled script call merely for using PascalCase.

## 3. Parameters — EIAM-specific parameter patterns

#### ✅ CORRECT — OIDC provider creation with dot-notation
```bash
aliyun eiam create-federated-credential-provider \
  --region cn-hangzhou \
  --instance-id instance_xxx \
  --FederatedCredentialProviderName k8s-oidc-trust \
  --FederatedCredentialProviderType oidc \
  --NetworkAccessEndpointId inae_public \
  --OidcProviderConfig.JwksSource dynamic_from_issuer \
  --OidcProviderConfig.Issuer "https://kubernetes.example.com" \
  --OidcProviderConfig.Audiences.1 "https://kubernetes.default.svc" \
  --force --method POST
```

#### ❌ INCORRECT — JSON string for nested config
```bash
aliyun eiam create-federated-credential-provider \
  --OidcProviderConfig '{"JwksSource":"dynamic_from_issuer",...}'   # Causes InvalidXxxConfig
```

#### ❌ INCORRECT — Missing `--force --method POST`
```bash
aliyun eiam create-federated-credential-provider \
  --OidcProviderConfig.JwksSource dynamic_from_issuer   # Rejected by CLI validation without --force
```

## 4. User-Agent — per-command observability

#### ✅ CORRECT
```bash
aliyun eiam list-instances --region cn-hangzhou --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/abc123def456 skill-version/0.6.0"
```

#### ❌ INCORRECT
```bash
# Missing skill-version/ prefix
aliyun eiam list-instances --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/0.6.0/abc123"

# Missing double quotes (UA value contains a space)
aliyun eiam list-instances --user-agent AlibabaCloud-Agent-Skills/alibabacloud-idaas-kubernetes-m2m-federated-credential/abc123 skill-version/0.6.0

# Missing alibabacloud- prefix on skill name
aliyun eiam list-instances --user-agent "AlibabaCloud-Agent-Skills/idaas-kubernetes-m2m-federated-credential/abc123 skill-version/0.6.0"
```

## 5. Credential verification — local check first

#### ✅ CORRECT
```bash
# Step 1: Local check (no API call)
aliyun configure list

# Step 2: Server-side validation (after local check passes)
aliyun sts get-caller-identity --user-agent "..."
```

#### ❌ INCORRECT
```bash
# Skipping local check and going straight to API call
aliyun sts get-caller-identity     # Missing aliyun configure list first

# Printing credentials
echo $ALIBABA_CLOUD_ACCESS_KEY_ID  # FORBIDDEN
```

## 6. JWKS Source Mode Selection

#### ✅ CORRECT
- Public issuer (ACK/EKS/GKE managed clusters): `dynamic_from_issuer` (Issuer Address Resolution) — auto-refreshes JWKS
- Private issuer (self-managed clusters): `static` (Static Fill-in) — requires manual JWKS export and rotation
- Independent public JWKS URL: `dynamic_from_jwks_uri` — must be HTTPS, use public discovery URL not in-cluster value

#### ❌ INCORRECT
- Using `dynamic_from_jwks_uri` with the in-cluster discovery `jwks_uri` (e.g., `https://:6443/openid/v1/jwks` — broken on ACK, empty host)
- Using `dynamic_from_issuer` for a private/unreachable issuer (creation will fail with OBTAIN_JWKS_ERROR)
- Expecting `static` mode to auto-rotate JWKS after cluster key rotation (it never does; manual update required)

## 7. Token Assertion Type

#### ✅ CORRECT
```
client_assertion_type = urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer
client_assertion = <SA JWT verbatim, three dot-separated segments>
```

#### ❌ INCORRECT
```
client_assertion_type = urn:ietf:params:oauth:client-assertion-type:jwt-bearer   # Not in allowlist
client_assertion = -----BEGIN CERTIFICATE-----\n<jwt>   # PEM wrapping is for PKCS#7, not OIDC
```

## 8. Kubernetes Verification Mode

#### ✅ CORRECT
```
ApplicationFederatedCredentialType = oidc
VerificationMode = structured
OidcVerificationConfig.Profile = kubernetes
OidcVerificationConfig.KubernetesConfig.Namespace = <ns>
OidcVerificationConfig.KubernetesConfig.ServiceAccountName = <sa>
```

#### ❌ INCORRECT
```
VerificationMode = kubernetes    # No standalone "kubernetes" mode; must use structured + Profile=kubernetes
# Passing VerificationCondition/AttributeMappings in structured mode   # Server-compiled; causes conflicts
```

## 9. Audience Configuration

#### ✅ CORRECT
- Configure only one primary audience (`AUD_PRIMARY` from parse_sa_token.py)
- ANY-match semantics: token passes if its aud array intersects configured Audiences
- Distinguish `https://kubernetes.default.svc` (ACK/EKS short name) vs `https://kubernetes.default.svc.cluster.local` (self-managed FQDN) — exact string match, never interchangeable

#### ❌ INCORRECT
- Copying the token's full aud list (over-configuration that widens trust surface)
- Inferring audience from the issuer URL instead of parsing the actual token
- Reusing another cluster's audience configuration

## 10. Resource Deletion Order

#### ✅ CORRECT
```
1. Disable application federated credential → Delete application federated credential
2. Disable federated credential provider → Delete federated credential provider
3. Disable application → Delete application
```

#### ❌ INCORRECT
```
# Deleting without disabling first → causes XXX.NotDisabled error
aliyun eiam delete-application --region ... --application-id <app_id>   # Must disable first
# Wrong deletion order (deleting app before credential) → orphaned resources
```

## 11. UpdateFederatedCredentialProvider — Full-Overwrite Semantics

#### ✅ CORRECT
```bash
# Include ALL fields even when unchanged
scripts/rotate_static_jwks.py <region> <instance_id> <fcp_id> <new_jwks_file>
# Reads back and refills Name/NAE/Issuer/Audiences, replaces StaticJwks only
```

#### ❌ INCORRECT
```bash
# Omitting required fields on update
aliyun eiam update-federated-credential-provider \
  --StaticJwks '{"keys":[...]}' \
  # Missing FederatedCredentialProviderName → MissingFederatedCredentialProviderName error
  # Missing NetworkAccessEndpointId → MissingParameter.NetworkAccessEndpoint error
```
