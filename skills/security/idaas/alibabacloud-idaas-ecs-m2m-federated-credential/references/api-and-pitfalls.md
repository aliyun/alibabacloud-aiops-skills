# API Parameters and Verified Pitfalls

Plugin requests validated in 2026-11 with aliyun CLI v3.5.1 and EIAM API version 2021-12-01.

Platform lifecycle runs also executed the typed requests with CLI v3.3.23 and
EIAM plugin v0.9.9. Check the installed plugin's request options rather than
treating the locally validated CLI version as a minimum requirement. First-use
plugin installation may emit status lines before JSON in older CLI builds;
helpers accept only the known installation lines for the requested product.

The instance HTTP token API has an independent [OpenAPI 3 contract](oauth-token.openapi.yaml). POP RPC dependencies remain in the root `related_apis.yaml`; the HTTP endpoint is not an EIAM RPC Action.

## 1. API Overview

| API | Purpose | Key parameters |
|-----|---------|----------------|
| `ListInstances` | List EIAM instances | PageNumber/PageSize; the response includes DefaultEndpoint.Endpoint |
| `GetInstance` | Retrieve the instance endpoint | `--cli-query 'Instance.DefaultEndpoint.Endpoint'` |
| `CreateFederatedCredentialProvider` | Create a federated credential provider | See §2 (typed JSON configuration) |
| `GetFederatedCredentialProvider` | Query a provider | FederatedCredentialProviderId |
| `ListFederatedCredentialProviders` | List providers and check for name conflicts | Required: InstanceId; optional: MaxResults, NextToken |
| `CreateApplication` | Create an M2M client application | SsoType=`oidc+oauth2/m2m`, ApplicationSourceType=`urn:alibaba:idaas:app:source:standard` |
| `GetApplication` | Query an application and its M2M status | Response field: Application.M2MClientStatus |
| `EnableApplicationM2MClient` | Enable M2M client capabilities | ApplicationId+InstanceId |
| `ListApplications` | List applications to find existing M2M applications | Required: InstanceId; optional: PageNumber/PageSize; filter by SsoType==oidc+oauth2/m2m |
| `CreateApplicationFederatedCredential` | Create an application federated credential | See §4 |
| `ListApplicationFederatedCredentialsForProvider` | List application federated credentials by provider | FederatedCredentialProviderId |
| `DisableApplicationFederatedCredential` | Disable a case-owned credential | Required: InstanceId, ApplicationId, ApplicationFederatedCredentialId |
| `DeleteApplicationFederatedCredential` | Delete that disabled credential | Required: InstanceId, ApplicationId, ApplicationFederatedCredentialId |
| `DisableFederatedCredentialProvider` | Disable a case-owned provider | Required: InstanceId, FederatedCredentialProviderId |
| `DeleteFederatedCredentialProvider` | Delete that disabled provider | Required: InstanceId, FederatedCredentialProviderId |
| `DisableApplication` | Disable a case-owned client application | Required: InstanceId, ApplicationId |
| `DeleteApplication` | Delete that disabled application | Required: InstanceId, ApplicationId |

Every row above is one RPC Action of product `eiam`, version `2021-12-01`,
declared separately in `related_apis.yaml`. `--region` selects the service endpoint.
List responses expose the collection and RequestId; application lists use
Applications/TotalCount, while provider lists use FederatedCredentialProviders
and token pagination. Disable/Delete responses expose RequestId; a successful
write response alone does not prove the final state, so query again after cleanup.
The required parameters for each independent Action in the table were rechecked
with vendor CLI 3.5.1 API help. Exact option mappings and response fields are listed
separately for each Action in the OpenAPI contracts document linked directly from SKILL.md. Query response schemas with `aliyun eiam <plugin-command> --help --cli-section response`.
Do not combine two Action names into one API identifier.

ECS `describe-instances` requires the plugin option `--biz-region-id` for the API parameter `RegionId`; use `--region` separately to select the endpoint. Confirm the option names with the installed CLI metadata rather than deriving them from PascalCase.

For provider-to-credential readback, use the provider-scoped Action exactly:

```bash
aliyun eiam list-application-federated-credentials-for-provider --region <region> --instance-id <instance_id> --federated-credential-provider-id <provider_id> --user-agent "$UA"
```

This Action does not accept `--application-id`. Do not substitute the separate
application-scoped list Action when verifying the provider association. Filter
its returned associations by the actual application and credential IDs locally.

## 2. Verified Parameters for CreateFederatedCredentialProvider (PKCS#7)

Use the production helper, which builds one typed JSON object for the plugin option `--pkcs7-provider-config`:

```bash
python3 scripts/create_trust_source.py <region> <instance_id> <provider_name> <account_id> [validity_seconds]
```

The object uses the API's wire field names: `TrustAnchorSource`, `CmsVerificationMode`, `SignatureEffectiveTime` (integer), `SigningTimeValueExpression`, `TrustCondition`, and `Certificates` (array of objects containing `Content`). The CLI maps this object to flat RPC request keys, including `Pkcs7ProviderConfig.Certificates.1.Content`. The helper inserts the bundled certificate and the actual selected account/audience values without shell interpolation. POST is selected by API metadata.

- The official certificate is bundled at `assets/alibaba_cloud_pkcs7_cert.pem` (SHA256 fingerprint `09025956e3895bfd...1941`). It is the root certificate for the China site supplied by the console's "Get Cloud Provider Certificate" action.
- `SigningTimeValueExpression` is fixed; do not change it.
- In `TrustCondition`, `aud` must equal the IDaaS instance ID (the same constraint used by the console).
- For trust across accounts, set `owner-account-id` to the other account's ID.

### Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `unknown flag --force` or `--method` | A legacy CLI override was supplied to the typed plugin command | Use the current helper and metadata-selected HTTP method |
| `unknown flag --pkcs7-provider-config.*` | Dotted wire parameters were used as plugin options | Pass one JSON object to `--pkcs7-provider-config` |
| Invalid PKCS#7 configuration | Missing or incorrect typed configuration values | Inspect the plugin request help and validate the account, audience, certificate and validity |

## 3. Obtain the Signature on ECS (IMDSv2)

```bash
# Generate the complete one-line command for the actual selected IDaaS instance.
python3 scripts/gen_ecs_sign_command.py <IDAAS_INSTANCE_ID>
```

- The generated command keeps the metadata value inside a subshell, prints only
  the PKCS#7 response, and stops on an empty token or failed request. It avoids
  putting a literal credential assignment/header value in the displayed template.
- Hardened instances (IMDSv2) reject requests without the `X-aliyun-ecs-metadata-token` header.
- Generate signingTime **at execution time**. Signature validity is controlled by the provider's `SignatureEffectiveTime` (default: 3600 seconds). Obtain a new signature after expiration.
- The response is PEM (`-----BEGIN PKCS7-----`…). Before sending it to the token endpoint, **remove the delimiters and line breaks, leaving a single-line base64 body** (verified to work).
- Key signature payload fields: `instance-id`, `owner-account-id`, `region-id`, `private-ipv4`, and `audience` (a JSON string containing aud and signingTime).

## 4. CreateApplicationFederatedCredential (PKCS#7)

```bash
aliyun eiam create-application-federated-credential --region <r> \
  --instance-id <iid> --application-id <app_id> \
  --federated-credential-provider-id <fcp_id> \
  --application-federated-credential-type pkcs7 \
  --application-federated-credential-name <name> \
  --verification-mode freedom \
  --verification-condition "<expression>"
```

Use the plugin scalar options above; the CLI selects POST from metadata. Keep the script's local name and trust-condition validation, and never replay a failed creation automatically.

### Verification Condition Expressions (freedom Mode)

| Mode | Expression |
|------|------------|
| Single ECS instance | `Equals(pkcs7.payload.jsonData.'instance-id', "i-bp1xxxx")` |
| Multiple ECS instances (≤10) | `Or(Equals(pkcs7.payload.jsonData.'instance-id', "i-a"),Equals(pkcs7.payload.jsonData.'instance-id', "i-b"))` |
| Cloud account | `Equals(pkcs7.payload.jsonData.'owner-account-id', "<account_id>")` |

Other available fields include `region-id`, `private-ipv4` (with `IpMatch("172.16.0.0/24", ...)`), `zone-id`, `mac`, and `serial-number`. See the official documentation on using federated credential expressions.

## 5. Token Endpoint Specification

This is an instance-local OAuth HTTP endpoint, not a POP Action. Its metadata is
defined here rather than registering a fictitious RPC Action in `related_apis.yaml`.
The hostname comes from `GetInstance`; all six form parameters below are required
by this skill's PKCS#7 client-credentials flow.

```
POST https://<DefaultEndpoint>/api/v2/iauths_system/oauth2/token
Content-Type: application/x-www-form-urlencoded
```

| Parameter | Value |
|-----------|-------|
| grant_type | `client_credentials` |
| client_id | M2M client application ID (app_xxx) |
| client_assertion_type | `urn:cloud:idaas:params:oauth:client-assertion-type:pkcs7-bearer` |
| client_assertion | Single-line base64 PKCS#7 signature |
| scope | `<ResourceServerIdentifier>\|<ScopeValue>`; `.all` matches all scopes; **required** |
| application_federated_credential_name | Application federated credential **name**, not ID |

### Successful Response (Verified Example, HTTP 200)

```json
{
  "token_type": "Bearer",
  "access_token": "eyJraWQi...(JWT, RS256)",
  "expires_in": 1200,
  "expires_at": 1792061324,
  "scope": "sls:mcp2 sls:mcp1"
}
```

Key JWT payload fields: `sub`/`client_id` = application ID; `aud` = ResourceServer identifier; `scope` = scopes actually granted (`.all` expands to a list of specific scopes); `iss` = `https://<endpoint>/api/v2/iauths_system/oauth2`; `_idaas_iid` = instance ID. Observed token validity: 1200 seconds.

### Error Mapping

| HTTP | error | Meaning and action |
|------|-------|--------------------|
| 400 | `invalid_request` + `Invalid audience: <identifier_from_scope>` | The ResourceServer does not exist or its identifier is incorrect. **Use single or double slashes exactly as registered.** |
| 400 | `invalid_scope` + `scope required` | Scope is required and cannot be omitted. |
| 400 | Assertion or signature errors | Check signature expiration, aud=instance ID, single-line base64 assertion format, credential name, and whether the trust condition includes this ECS instance. |
| 401 | Client authentication failure | Check client_id, M2MClientStatus=enabled, and whether the application federated credential is associated with this application and provider. |

## 6. Environment Pitfalls

- **CLI installation**: Direct access to GitHub Releases may fail on internal networks or in sandboxes (DNS or certificate errors). Use only the pinned, SHA256-verified release documented in `assets/cli-installation-guide.md`; if its official sources are inaccessible, stop installation instead of switching to latest or skipping verification.
- **aliyun configure is interactive**: An agent cannot supply interactive input in this environment. Ask the user to run it in their terminal, keep secret entry in the user's terminal and out of the conversation.
- **SSL behind a proxy**: If curl/requests reports certificate errors, use `--cacert "$REQUESTS_CA_BUNDLE"`. If that file is outdated, combine certificates into a new file using `cat /etc/ssl/certs/ca-certificates.crt <proxy_CA>`. Do not bypass TLS verification with `-k`; stop until trust is configured.
- **RAM permissions**: EIAM requires read/write access; listing ECS instances requires only read access. Cloud Assistant RunCommand (`ecs:RunCommand`) is usually unavailable. **By default, ask the user to run the command on ECS and paste back the signature**; do not depend on RunCommand.
- **Paid M2M feature**: Application creation or token requests fail if M2M is not enabled on the instance. Guide the user to upgrade in the console.

## 7. PAM Flow Without AK (Scope Authorization and STS Exchange)

### 7.1 Feature Permission Authorization (Verified in 2026-10: Fully Automatable, with Two Hidden Pitfalls)

**Pitfall 1: The PAM system application has the fixed ID `iap_pam`.**
- Query it directly using `GetApplication --application-id iap_pam` (ApplicationName=Privileged Access Management, ResourceServerIdentifier=`urn:cloud:idaas:pam`, RS enabled).
- ListApplications excludes it by default because ApplicationCreationType=`system_init` is filtered out. Use `--application-creation-type system_init` to list all system applications (12 observed: iap_pam, iap_admin_portal, iap_access_request, iap_cloud_idaas_cli, iap_config_portal, STS RS applications for cloud accounts, etc.). The filter value is `system_init`, not `system`.

**Pitfall 2: `ListResourceServerScopes` returns 0 for iap_pam with the default query.**
- The 14 PAM scopes have type `application_delegated` or `delegated`. Ordinary M2M server scopes have type `application` and are visible by default.
- **Pass `--resource-server-scope-type all`** to return the complete list, including:
  `cloud_account_role:obtain_access_credential` → `ress_xxx` (the ID varies by instance and must be queried dynamically).
- Without this filter, TotalCount=0, which can easily be mistaken for "scope does not exist" or "authorization is only available in the console" (this led to an incorrect conclusion in v0.3.x).

**Two-step automatic authorization**:

```bash
# A. RS level (idempotent)
aliyun eiam authorize-resource-server-to-client --region <r> --instance-id <iid> \
  --client-application-id <client_app_id> --resource-server-application-id iap_pam

# B. Scope level (requires actual ress_id values in a JSON array)
aliyun eiam list-resource-server-scopes --region <r> --instance-id <iid> \
  --application-id iap_pam --max-results 50 --resource-server-scope-type all
#   → Find ResourceServerScopeId where ResourceServerScopeValue == cloud_account_role:obtain_access_credential
aliyun eiam authorize-resource-server-scopes-to-client --region <r> --instance-id <iid> \
  --client-application-id <client_app_id> --resource-server-application-id iap_pam \
  --resource-server-scope-ids '["<ress_id>"]'
```

**Additional verified notes**:
- Passing the scope **value** as its ID to `AuthorizeResourceServerScopesToClient` causes `InvalidParameter.ResourceServerScopeIds`; the ID must be ress_xxx.
- `CreateResourceServerScope(iap_pam)` causes `UnsupportedAction.RestrictApplicationCreationType`. system_init applications are write-protected; scope creation is unnecessary because the scopes already exist.
- `SetApplicationGrantScope` is a Developer API allowlist. It silently discards PAM scope values and is unrelated to this flow.
- Equivalent console path (manual fallback): Permission Center → Feature Permission Management → Privileged Access Management → authorize the client → select the scope.
- **Data permissions** (application ↔ target cloud role) still require console configuration: Permission Center → Data Permission Management → Authorization Rules. The cloud role must already be managed and available under Asset Management.
- Token endpoint states indicate authorization progress:

| Authorization state | Token request result |
|---------------------|----------------------|
| RS not authorized | 400 `invalid_request`: "Client [...] has not been authorized by resource server [urn:cloud:idaas:pam]" |
| RS authorized + explicit scope | 400 `invalid_scope`: "Invalid scope: cloud_account_role:obtain_access_credential" |
| RS authorized + `.all` | 404 `scope_not_found`: "The current audience does not have an authorized scope" |
| RS and scope both authorized | 200, token issued |

- Data permissions (application ↔ target cloud role) also require console configuration: Permission Center → Data Permission Management → Authorization Rules. The cloud role must be managed and available under Asset Management → Cloud Identities / Cloud Roles (corresponding OpenAPIs: `CreateCloudAccount` / `CreateCloudAccountRole` / `ListCloudAccounts` / `ListCloudAccountRoles`).

### 7.2 STS Exchange (eiam-developerapi OpenAPI)

Use the fixed token request scope: `urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential`.

```bash
aliyun eiam-developerapi GET /v2/<idaas_instance_id>/cloudAccountRoles/_/actions/obtainAccessCredential \
  --region <region> \
  --cloudAccountRoleExternalId 'acs:ram::<account_id>:role/<role_name>' \
  --header "Authorization=Bearer <M2M_TOKEN>" \
  --header "Content-Type=application/json" \
  --version 2022-02-25
```

- Product code: `eiam-developerapi`; version: `2022-02-25`; RESTful API; endpoint: `eiam-developerapi.<region>.aliyuncs.com`.
- Optional parameter `durationSeconds` specifies STS credential validity.
- Returns AccessKeyId / AccessKeySecret / SecurityToken (the three components of RAM STS credentials).
- The official SDK (IDaaS Akless Alibabacloud Adapter) calls this API internally. The scope field in `~/.cloud_idaas/client-config.json` uses the same fixed value shown above.

## 8. End-to-End Sequence (Reference)

```
ECS ──1. IMDSv2 token + audience──▶ 100.100.100.200 ──▶ PKCS#7 signature
ECS ──2. HTTPS token exchange (pkcs7-bearer assertion)──▶ EIAM
EIAM: 3. Provider verifies the signature (official root certificate + owner-account-id + aud + signingTime validity)
      4. Verify the application federated credential (instance-id or account expression)
      5. Verify the client application's scope authorization ──▶ issue M2M token (JWT)
(Optional) 6. Exchange the token for RAM STS credentials using AssumeRoleWithOIDC
             (requires a RAM OIDC IdP with Issuer set to the iss value).
```
