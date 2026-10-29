# API Parameters and Verified Pitfalls (Kubernetes OIDC Federation)

> Sources: EIAM2 source-code inspection (idaas-eiam2-application / idaas-commons / idaas-eiam2-common-control)
> + live create/read-back/cleanup verification on test instance `idaas_zcwh4tvaqai3c53dee2qxrqlha` (2026-10).
> Chinese version (with full test records): `api-and-pitfalls.zh-CN.md`.

## 1. CreateFederatedCredentialProvider (OIDC Provider)

Call pattern: `--force --method POST --yes` + flattened dot-notation parameters (JSON strings are rejected).

| Parameter | Required | Notes |
|---|---|---|
| `FederatedCredentialProviderType` | ✅ | `oidc` |
| `FederatedCredentialProviderName` | ✅ | `[a-z0-9_-]{1,64}` |
| `NetworkAccessEndpointId` | ✅ (OIDC-specific) | Shared endpoint `inae_public`; optional for PKCS#7 but mandatory for OIDC |
| `OidcProviderConfig.JwksSource` | ✅ | `static` / `dynamic_from_issuer` / `dynamic_from_jwks_uri` (console terms: Static Fill-in / Issuer Address Resolution / JWKS URI Resolution) |
| `OidcProviderConfig.Issuer` | ✅ | HTTPS URL, verbatim from cluster discovery. **Immutable after creation** (Update forces the stored value) |
| `OidcProviderConfig.Audiences.1..5` | ✅ | 1–5 values. **ANY-match semantics**: the token passes when its aud array intersects the configured Audiences (jose4j setExpectedAudience). Configure only the primary aud (issuer-equal value preferred, else first token aud element); copying the full list widens the trust surface |
| `OidcProviderConfig.StaticJwks` | static ✅ | Standard JWKS JSON string (`{"keys":[...]}`, validated non-empty server-side) |
| `OidcProviderConfig.JwksUri` | dynamic_from_jwks_uri ✅ | HTTPS URL (validator enforces https:// + URL validity) |
| `OidcProviderConfig.TrustCondition` | ❌ | DSL expression (see §4) |

`DynamicJwks` / `JwksLastObtainedTime` are server-internal fields, not accepted from the API.

**iss verification is strict equality** (setExpectedIssuer): the token's iss must exactly equal the configured Issuer.

**UpdateFederatedCredentialProvider has full-overwrite semantics (production-verified 2026-10)**:
- `--FederatedCredentialProviderName` **required** even when unchanged (omission → `MissingFederatedCredentialProviderName`)
- `--NetworkAccessEndpointId` **required** (omission → `MissingParameter.NetworkAccessEndpoint`)
- Include all OidcProviderConfig fields (JwksSource/Issuer/Audiences/StaticJwks); Issuer is force-preserved from DB but must still be passed
- Same call pattern as Create; prefer `scripts/rotate_static_jwks.py` (reads back and refills everything automatically)

### 1.1 JWKS Source Mode Runtime Behavior (source: FederatedCredentialProviderFacadeImpl / JwksRemoteServiceImpl)

| Behavior | Static Fill-in (static) | Issuer Address Resolution (dynamic_from_issuer) | JWKS URI Resolution (dynamic_from_jwks_uri) |
|---|---|---|---|
| JWKS origin | Entered at creation (StaticJwks) | IDaaS fetches `{issuer}/.well-known/openid-configuration` → `jwks_uri` → JWKS | IDaaS fetches the configured JwksUri |
| On create/update | No network; format validation only | **Synchronous fetch**; failure → OBTAIN_JWKS_ERROR, request rolls back (authoritative reachability signal) | Same |
| Periodic refresh | ❌ none | ✅ SchedulerX2 job `DYNAMIC_OBTAINING_JWKS` refreshes enabled providers; writes JwksLastObtainedTime on success | ✅ same |
| Key-rotation follow | ❌ manual Update of StaticJwks | ✅ automatic (within refresh interval) | ✅ automatic |
| kid miss at auth | Raises InvalidJwtException immediately (**no on-miss refetch**) | Same (hot path reads DB cache only, no network) | Same |
| Periodic fetch failure | — | Warn log only; keeps old JWKS; no retry/backoff | Same |
| Manual refresh API | ❌ rejected (JWKS_SOURCE_NOT_REFRESHABLE) | ✅ refreshOidcProviderJwks | ✅ |
| Network egress | — | NetworkAccessEndpointId resolved to egress proxy for OkHttpClient; falls back to PUBLIC_NAE | Same |
| Fit | Self-managed clusters (private issuer) — only option | Managed clusters (ACK/EKS/GKE public issuer URL) — preferred, rotation-free | Independent public JWKS URL |

## 2. CreateApplicationFederatedCredential (Kubernetes Structured Mode)

Call pattern: same `--force --method POST --yes` + dot notation.

| Parameter | Required | Notes |
|---|---|---|
| `ApplicationFederatedCredentialType` | ✅ | `oidc` |
| `ApplicationFederatedCredentialName` | ✅ | ≤64 chars; must equal SDK `applicationFederatedCredentialName` |
| `ApplicationId` / `FederatedCredentialProviderId` | ✅ | M2M client app / provider IDs |
| `VerificationMode` | ✅ | `structured` (**no standalone "kubernetes" enum**; freedom = handwritten DSL, structured = server-compiled) |
| `OidcVerificationConfig.Profile` | structured ✅ | `kubernetes` (OidcProfileEnum: generic / kubernetes / gcp_vm / azure_vm) |
| `OidcVerificationConfig.KubernetesConfig.Namespace` | ✅ | K8s namespace |
| `OidcVerificationConfig.KubernetesConfig.ServiceAccountName` | ✅ | Field name is **ServiceAccountName** (not ServiceAccount) |
| `OidcVerificationConfig.KubernetesConfig.PodNamePrefix` | ❌ | Pod-name prefix filter |
| `VerificationCondition` / `AttributeMappings` | 🚫 forbidden | Server-compiled in structured mode; passing them is rejected |

Server-compiled output (verified by read-back):
```
And(Equals(jwt.claims.'kubernetes.io'.namespace, "<ns>"), Equals(jwt.claims.'kubernetes.io'.serviceaccount.name, "<sa>"))
# with podNamePrefix: adds StartsWith(jwt.claims.'kubernetes.io'.pod.name, "<prefix>")
```

## 3. Token Endpoint (id-token-bearer → M2M Token)

`POST https://<DefaultEndpoint>/api/v2/iauths_system/oauth2/token`, `application/x-www-form-urlencoded`:

| Parameter | Value |
|---|---|
| `grant_type` | `client_credentials` |
| `client_id` | `app_xxx` (M2M client) |
| `client_assertion_type` | `urn:cloud:idaas:params:oauth:client-assertion-type:id-token-bearer` (source constant OIDC_BEARER) |
| `client_assertion` | Pod SA JWT **verbatim** (header.payload.signature; no PEM/normalization) |
| `application_federated_credential_name` | Credential name |
| `scope` | PAM flow: `urn:cloud:idaas:pam\|cloud_account_role:obtain_access_credential`; custom RS: `<RSIdentifier>\|<ScopeValue>` (slash counts verbatim; `.all` wildcard) |

Federated assertion allowlist (FederatedCredentialAuthnConstants.PERMITTED_ASSERTION_TYPE): `pkcs7-bearer`, `id-token-bearer`, `x509-jwt-bearer`, `eds:session-token-bearer`. **Standard `urn:ietf:params:oauth:client-assertion-type:jwt-bearer` is NOT allowed** (classic client auth only).

Error states: 400 `invalid_request "not been authorized by resource server"` (RS not authorized) → 400 `invalid_scope` (RS ok, scope not) → federation failures (JWKS/issuer mismatch, aud miss, ns/sa mismatch, expired token) → 200 when all set. Success access_token is a JWT with sub/aud/scope/iat/exp.

## 4. DSL Expression Syntax (TrustCondition / freedom-mode VerificationCondition)

JWT claim paths (FederatedCredentialClaimPaths): `jwt.sub`, `jwt.jti`, `jwt.claims.'kubernetes.io'.namespace`, `jwt.claims.'kubernetes.io'.serviceaccount.name`, `jwt.claims.'kubernetes.io'.pod.name`; other claims via `jwt.claims.<name>` (quote names containing `-`/`.`).

Functions: `Equals(path, "value")`, `StartsWith`, `EndsWith`, `Contains`, `ToLower`, `And(...)`, `Or(...)`, `Append(...)`.

Example (provider-level subject restriction):
```
Equals(jwt.sub, "system:serviceaccount:prod:my-app-sa")
```
No `jwt.issuer`/`jwt.aud` paths exist — issuer/audience are verified at the provider layer (Issuer/Audiences fields).

## 5. PAM Feature Permission Authorization

- PAM system application fixed ID `iap_pam` (ApplicationCreationType=system_init; excluded from ListApplications; query via GetApplication). RS identifier `urn:cloud:idaas:pam`.
- Two stages: A. `AuthorizeResourceServerToClient(iap_pam)` (idempotent); B. `ListResourceServerScopes --ResourceServerScopeType all` (**returns 0 without `all`** — PAM scopes are application_delegated/delegated) → take ress_id of `cloud_account_role:obtain_access_credential` → `AuthorizeResourceServerScopesToClient --force --method POST --ResourceServerScopeIds.1 <ress_id>` (scope value as ID → InvalidParameter.ResourceServerScopeIds).
- system_init apps are write-protected (CreateResourceServerScope blocked; unnecessary).
- **Data permissions have no OpenAPI**: console Permission Center > Data Permission Management rule linking app↔cloud role; cloud account/role onboarding at Assets > Cloud Identity (see idaas-cloud-identity-setup skill).

## 6. SDK Configuration (client-config.json) and Runtime

- Path precedence: JVM `-Dcloud_idaas_config_path` > env `CLOUD_IDAAS_CONFIG_PATH` > `~/.cloud_idaas/client-config.json` (classpath: prefix supported).
- KUBERNETES deploy environment token path precedence: `oidcTokenFilePath` field > `oidcTokenFilePathEnvVarName` env target > default `/var/run/secrets/kubernetes.io/serviceaccount/token` (native K8s default SA path hits the default).
- `authnConfiguration`: identityType=CLIENT, authnMethod=OIDC, clientDeployEnvironment=**KUBERNETES**, applicationFederatedCredentialName=credential name.
- httpConfiguration connect/readTimeout must be within 2000–60000 ms (SDK ValidatorUtil).
- FileOidcTokenProvider re-reads the token file 10 minutes before expiry (compatible with kubelet projected-token rotation).
- Java onboarding: `IDaaSCredentialProviderFactory.init()` → `IDaaSPamAklessCredentialFactory.getAlibabaCloudCredentialsProvider("<role_arn>")` → `getCredentials()` (STS triple).

## 7. Cluster-Side Command Quick Reference

```bash
kubectl get --raw /.well-known/openid-configuration   # discovery: paste the whole JSON back; the skill parses issuer/jwks_uri
kubectl get --raw /openid/v1/jwks                     # export static JWKS (paste back whole)
kubectl create token <sa> -n <namespace> --duration=1h   # sign a token for an SA (no pod needed)
kubectl exec -n <ns> <pod> -- cat /var/run/secrets/kubernetes.io/serviceaccount/token   # or read the pod-mounted token
```

Prerequisites: K8s ≥1.21 (Bound ServiceAccount Token); API Server configured with `--service-account-issuer`. Projected tokens are short-lived (~1h) — verify promptly.

⚠️ **User-facing commands must be zero-dependency and unique**: ACK nodes/CloudShell may lack python3/jq (verified 2026-10) — only kubectl (plus POSIX grep/awk when unavoidable); all JSON/JWT parsing happens skill-side (discovery JSON pasted whole; tokens parsed by `parse_sa_token.py`, never jwt.io). One command per artifact; no equivalent alternatives (parsing is the skill's job; choices add cognitive load — user feedback 2026-10).

### 7.1 issuer / audience Distribution Differences (⚠️ exact string matching, never interchangeable)

Distributions configure `--service-account-issuer` / `--api-audiences` differently (all verified):

| Cluster | issuer | Default token aud | Origin |
|---|---|---|---|
| Self-managed lightweight distro (verified sample) | `https://kubernetes.default.svc.cluster.local` | `[issuer-equal, <distro-identifier>]` (dual aud; ANY-match means configuring the primary aud alone suffices) | Distro explicitly sets `--api-audiences=<issuer FQDN>,<distro-identifier>` (visible in API Server startup logs) |
| ACK | `https://oidc-ack-<region>.oss-<region>.aliyuncs.com/<clusterid>` (public OSS) | `["https://kubernetes.default.svc"]` (single, **short name**) | ACK sets the issuer to an OSS URL for RRSA public discovery and pins `--api-audiences` to the K8s legacy default for workload compatibility |
| ACK RRSA projected token | same | `sts.aliyuncs.com` (custom audience) | workload-side serviceAccountTokenRequest |
| kubeadm self-managed (defaults) | FQDN `https://kubernetes.default.svc.cluster.local` (source-pinned: manifests.go `fmt.Sprintf("https://kubernetes.default.svc.%s", DNSDomain)`, DNSDomain defaults to `cluster.local`, verified on release-1.30) | with `--api-audiences` unset, inherits the first issuer value → **FQDN long name** | kubeadm/upstream default chain |

**⚠️ The in-cluster discovery `jwks_uri` on ACK is a broken value (user-verified 2026-10)**: `kubectl get --raw /.well-known/openid-configuration` returns `"jwks_uri":"https://:6443/openid/v1/jwks"` (empty host); the public OSS discovery's jwks_uri is the valid one (`…/<clusterid>/keys`). Impact: never configure JWKS URI Resolution from the in-cluster value (creation would fail); Issuer Address Resolution is unaffected (IDaaS fetches the public discovery — verified). In-cluster JWKS export always uses `kubectl get --raw /openid/v1/jwks` (direct API Server path).

**Stored-JWKS read-back differs by API (verified 2026-10)**: `GetFederatedCredentialProvider` does **not** return JWKS for dynamic providers (StaticJwks empty); `ListFederatedCredentialProviders` **does** return DynamicJwks + JwksLastObtainedTime, enabling kid comparison. Reuse detection therefore always uses List; when comparison is impossible, `REUSE_KID_STALE=unknown(no_cluster_jwks|<jwks_source>)` — **unknown ≠ fresh**; never present it as verified.

Two look-alike values: `https://kubernetes.default.svc` (K8s legacy default audience, short Service DNS name) ≠ `https://kubernetes.default.svc.cluster.local` (FQDN). IDaaS matches Audiences against token aud by **exact string**; mixing them fails federation.

**The look-alike pair appears in the aud field, not the issuer**: the short name is upstream `LegacyAPIAudiences` (pre-1.21 historical default audience), pinned by ACK/EKS for compatibility; issuers never use the short name — self-managed clusters (kubeadm/kind and lightweight distros) default to the FQDN issuer, managed vendors (ACK/EKS/GKE) default to a public URL (so federation peers can fetch JWKS).

**Mental model**: short name = historical default + managed-vendor compatibility choice; FQDN = the modern kubeadm default chain (FQDN issuer → aud inherits issuer when `--api-audiences` unset). The decision chain has many branches (explicit audience / vendor pinning / version differences): **never guess either field — copy the issuer verbatim from discovery; derive aud by parsing the actual token**.

**Rule: Audiences must come from the actual parsed SA token; never infer from the issuer** (issuer-equality on some self-managed clusters is coincidence; ACK differs entirely). Corollaries: tokens with different audiences in one cluster (default vs RRSA) need different providers or multiple Audiences; an existing provider whose Audiences miss the primary aud is **not reusable** — create a new one.

aud decision chain (rules of thumb; the actual token always wins):
1. **Explicit audience** (projected volume `audience:` / `kubectl create token --audience`) → aud = requested value (RRSA `sts.aliyuncs.com`, IRSA `sts.amazonaws.com`)
2. **Default mounted token** → aud = apiserver `--api-audiences`: managed vendors pin the short name; the verified lightweight distro pins `[issuer FQDN, <identifier>]`; unset (typical kubeadm) inherits the first issuer value → FQDN (⚠️ based on upstream-code understanding, not re-verified from source this round)
3. One-liner: **short name ≈ managed-vendor compatibility choice; FQDN ≈ self-managed default following the issuer**

## 8. Source File Index (Workspace Inspection Basis)

| Content | Path |
|---|---|
| OidcVerificationConfig / KubernetesConfig DTO | idaas-eiam2-application/core/.../federatedcredential/params/OidcVerificationConfigDomain.java, KubernetesConfigDomain.java |
| Credential validator | idaas-eiam2-application/core/.../federatedcredential/validator/ApplicationFederatedCredentialValidator.java |
| VerificationMode / OidcProfile enums | idaas-eiam2-application/domain/.../enums/federatedcredential/VerificationModeEnum.java, OidcProfileEnum.java |
| Provider DTO / validator | idaas-eiam2-application/core/.../federatedcredential/params/OidcProviderConfigParam.java, validator/FederatedCredentialProviderValidator.java |
| JwksSource enum | idaas-commons/.../federatedcredential/enums/OidcProviderJwksSourceTypeEnum.java |
| Assertion URN constants | idaas-commons/.../urn/UrnOauthClientAssertionType.java (OIDC_BEARER), constants/FederatedCredentialAuthnConstants.java (allowlist) |
| Claim paths / DSL compiler | idaas-eiam2-application/facade/.../federatedcredential/compiler/FederatedCredentialClaimPaths.java, VerificationDslBuilder.java |
| aud ANY-match / iss strict verification | idaas-commons/.../federatedcredential/util/FederatedCredentialAuthnUtil.java, FederatedCredentialAuthnJwtUtil.java (jose4j setExpectedAudience/setExpectedIssuer) |
| Dynamic JWKS fetch/refresh | idaas-eiam2-application/facade/.../FederatedCredentialProviderFacadeImpl.java (setDynamicJwks / dynamicObtainingJwks / refreshOidcProviderJwks), remote/.../JwksRemoteServiceImpl.java |
| Token endpoint entry | idaas-eiam2-common-control/web/.../api/v2/controller/oauth2/AuthorizationServerOauth2Controller.java |

## 9. Verification Records (test instance idaas_zcwh4tvaqai3c53dee2qxrqlha, 2026-10)

- API parameter round: static provider + M2M client + structured kubernetes credential (compiled condition matched source) + PAM auto_done; all cleaned up.
- Self-managed single-node K8s E2E (ECS-hosted, private FQDN issuer, dual aud, Static Fill-in): id-token-bearer → **HTTP 200**. `kubectl create token` (TokenRequest, no pod binding) carries full `kubernetes.io` claims and passes structured verification — no test pod needed. Note: newer lightweight-distro releases require cgroup v2.
- ACK managed cluster E2E (public OSS issuer, single short-name aud, Static Fill-in): fresh three resources + PAM auto_done + id-token-bearer → **HTTP 200**. The provider pins whatever issuer/JWKS/aud the cluster reports — the skill is issuer-shape agnostic. ACK rotated its SA signing key within a month (kid differs from the September provider) — the static-rotation warning is a real operational risk. The pre-existing `aliyun-ack` provider (aud=sts.aliyuncs.com, RRSA) is NOT reusable for default tokens.
- Issuer Address Resolution: created against the ACK OSS issuer; read-back confirmed synchronous fetch (JwksLastObtainedTime = creation time, DynamicJwks populated). Public discovery jwks_uri = `…/<clusterid>/keys`.
- rotate_static_jwks.py: live-verified (auto-refill of Name/NAE/Issuer/Audiences; same-kid warning branch; read-back preserved fields).
- All test resources cleaned up. Not covered: EKS/GKE (same standard OIDC SA token mechanics; expected to work), JWKS URI Resolution creation, generic/gcp_vm/azure_vm profiles, in-pod SDK STS closure (needs console data permissions).
