# Identity-provider mapping OpenAPIs

Use this reference when the CLI plugin lacks mapping commands. These APIs were present in the original Skill; the read path was verified against an isolated AD IDP on 2026-10-22. This is not evidence that the write path or a full synchronization succeeded.

The write contract below was also exercised on an isolated OpenLDAP IDP on 2026-10-22: all five returned mapping items were preserved, only the display-name source changed from `idpUser.cn` to the verified `idpUser.displayName`, and the complete read-back matched. The `user.username` source remained `idpUser.uid`. This verifies that particular mapping write/read-back, not arbitrary fields, organization/group mappings, or successful synchronization/login.

## Read first

### Verified API metadata (2026-10-23)

The authoritative definitions were re-read from `cloudspec-model/EIAM_pop_Eiam_2021-12-01@master`, `operations/GetIdentityProviderUserProfileMapping.cspec` and `operations/GetIdentityProviderAuthnConfiguration.cspec`. Both are private POP Eiam APIs, version `2021-12-01`, supporting GET/POST. Caller-supplied required business parameters are `InstanceId` and `IdentityProviderId` (nonblank strings, maximum 64 characters each); `RegionId` is resolved from the host. Caller identity, RequestId and authentication metadata are system parameters, not extra business inputs to ask the administrator for.

The following official online documents were opened and their request/response tables expanded on 2026-10-23. Both display API version `2021-12-01` and update time `2025-03-31 18:01`; they agree with the definitions above:

- [GetIdentityProviderUserProfileMapping](https://apiworkbench.aliyun-inc.com/document/Eiam/2021-12-01/GetIdentityProviderUserProfileMapping).
- [GetIdentityProviderAuthnConfiguration](https://apiworkbench.aliyun-inc.com/document/Eiam/2021-12-01/GetIdentityProviderAuthnConfiguration?ampEnv=online).

Both document the required string parameters `InstanceId` and `IdentityProviderId`, each at most 64 characters. Their read actions are respectively `eiam:GetIdentityProviderUserProfileMapping` and `eiam:GetIdentityProviderAuthnConfiguration`, scoped to `acs:eiam:{#regionId}:{#accountId}:instance/{#InstanceId}/identityprovider/{#IdentityProviderId}`. This describes the authorization contract; it does not authorize granting a new role or widening the caller's permissions.

| API | Relevant response paths |
|---|---|
| GetIdentityProviderUserProfileMapping | `RequestId`, `UserProfileMapping.InstanceId`, `.IdentityProviderId`, `.UserMappingIdentityName`, `.IdentityProviderProfileMappingAttributes[]` with `TargetField`, `SourceValueExpression`, `ExpressionMappingType`, optional `TargetFieldDescription` |
| GetIdentityProviderAuthnConfiguration | `RequestId`, `AuthnConfiguration.BindingConfig`, `.LdapAuthnConfig` with `AutoUpdatePasswordStatus`, `UserObjectClass`, `UserLoginIdentifier`; `.AutoCreateUserConfig`, `.AutoUpdateUserConfig` |

The authentication document expands `BindingConfig` into `MappingBindingStatus`, `AutoMatchUserStatus`, and `AutoMatchUserProfileExpressions[]` (the same four mapping item fields shown above). `AutoCreateUserConfig` contains `AutoCreateUserStatus` and `TargetOrganizationalUnitIds[]`; `AutoUpdateUserConfig` contains `AutoUpdateUserStatus`. Example values such as `enabled`, `person,top`, and `mail` in the document are examples, not values to impose on the current identity provider. Read and preserve its actual configuration.

`related_apis.yaml` registers these API identities using the repository's existing gateway schema. On 2026-10-23, selecting the mapping API through AgentHub's native **Dependency API → Add API** catalog generated commit `34e4b21` with `popCode: "Eiam"`. The old lowercase `eiam` entry remained alongside it, demonstrating that the registry treated the identifiers as different. All 18 entries were then normalized to the native `Eiam` identifier and the duplicate removed; API names and version were preserved. This is an observed registration format, not an invented metadata extension. The table and official links document the verified contract for readers; successful metadata retrieval and IC coverage still require a new platform report. Do not invent unsupported YAML keys to suppress an information-completeness failure.

### SDK read fallback

Use `scripts/eiam_read.py` when a verified read API has no plugin command. Its fixed dependencies are declared in [scripts/requirements.txt](../scripts/requirements.txt): `alibabacloud-tea-openapi==0.4.6`, `alibabacloud-credentials==1.0.12`, and `alibabacloud-tea-util==0.3.15`. Check imports first; do not install during a no-install task. It uses the SDK default credential provider chain. Version `alibabacloud-credentials==1.0.12` includes the official `CLIProfileCredentialsProvider` in that chain (verified in its installed source), so an existing sandbox CLI profile may be resolved by the SDK itself. Do not manually read, print, export or translate credential files. A working CLI still does not prove that a particular SDK provider invocation will succeed; if it is unavailable, report the sanitized failure and use the console or ask the operator to configure an approved provider.

```bash
python3 scripts/eiam_read.py \
  --action GetIdentityProviderUserProfileMapping \
  --region <REGION_ID> --endpoint <VERIFIED_EIAM_ENDPOINT> \
  --instance-id <INSTANCE_ID> --idp-id <IDP_ID> \
  --user-agent "$USER_AGENT"
```

The helper permits only the following verified read actions; it cannot write configuration or trigger synchronization. Use it for public reads too when the installed CLI has no EIAM plugin. Every invocation requires the verified instance, region, endpoint and current session User-Agent, plus the action-specific scope below. It calls HTTPS RPC POST version `2021-12-01`, with case-sensitive OpenAPI query fields, bounded timeouts, one attempt, default TLS validation, and recursive output redaction. Errors expose only type/code/request ID/status. Do not retry credentials or parameter variants blindly.

| Action | Required scope argument | Verified business query beyond `InstanceId` |
|---|---|---|
| `GetIdentityProvider`, `GetIdentityProviderUdPullConfiguration`, the two private GETs above | `--idp-id` | `IdentityProviderId` |
| `GetNetworkAccessEndpoint` | `--network-access-endpoint-id` | `NetworkAccessEndpointId` |
| `ListSynchronizationJobs` | `--idp-id` | `TargetType=identity_provider`, `TargetIds.1`, `PageNumber`, `PageSize=100` |
| `GetSynchronizationJob` | `--synchronization-job-id` | `SynchronizationJobId` |
| `ListOrganizationalUnits` | `--parent-id` | `ParentId`, `PageNumber`, `PageSize=100` |
| `ListUsers` | `--organizational-unit-id` | `OrganizationalUnitId`, `PageNumber`, `PageSize=100` |
| `GetUser` | `--user-id` | `UserId` |

For each list scope increment `--page-number` until the actual `TotalCount` is covered, and recursively query each returned organizational-unit ID when a complete subtree is requested. `ListUsers` is scoped to one organization; do not assume it recursively includes descendants. Do not pass JSON arrays for flat RPC parameters. These public query shapes were independently exercised against the existing 05/06 LDAP fixtures; that evidence is limited to reads, not new onboarding or full login.

Redact sensitive keys before displaying any API response. The result is under `UserProfileMapping`, with `IdentityProviderProfileMappingAttributes[]`. The observed items contain `TargetField`, `SourceValueExpression`, and `ExpressionMappingType`. Examples observed in read-back are `idpUser.cn` with type `field`, and `"86"` with type `expression`. Do not turn bare LDAP attribute names into expressions by guesswork.

## Authentication read (same SDK path)

`GetIdentityProviderAuthnConfiguration` was independently read successfully against the same isolated instance/IDP on 2026-10-22 through the previous transport. Use the helper above with `--action GetIdentityProviderAuthnConfiguration` and the same verified identifiers, endpoint and session User-Agent. Do not infer that only the SET API exists from plugin help, and do not call a SET to discover configuration. The response is under `AuthnConfiguration`; enabled switches still do not prove login. Historical API success does not establish that SDK credentials or a new invocation work; record the actual result.

## Overwrite write contract (mapping only)

The current authoritative POP definition was read on 2026-10-22 from `cloudspec-model/EIAM_pop_Eiam_2021-12-01@master`, `operations/SetIdentityProviderUserProfileMapping.cspec`. It confirms the private API `SetIdentityProviderUserProfileMapping` supports GET/POST and flat array parameters. Use POST for writes, with:

- `InstanceId`, `IdentityProviderId`, `UserMappingIdentityName`.
- `IdentityProviderProfileMappingAttributes.N.TargetField`.
- `IdentityProviderProfileMappingAttributes.N.SourceValueExpression`.
- `IdentityProviderProfileMappingAttributes.N.ExpressionMappingType`.

Each array item requires all three fields and additionally permits `TargetFieldDescription`. `InstanceId` and `IdentityProviderId` are required; `UserMappingIdentityName` is optional in the API schema and means the identity-matching field, not the source attribute. Preserve its actual current setting rather than inventing one. Array indices start at 1. The array name is plural `IdentityProviderProfileMappingAttributes`; do not substitute a name suggested by a generic missing-parameter error. Recheck the authoritative definition if the API rejects the documented contract; historical instructions and successful GET alone do not establish a successful SET.

The bundled helper intentionally supports reads only. For an authorized mapping write, use the console or construct a separate SDK POST using the verified contract above, the default credential provider and session User-Agent; flatten each item into indexed query keys rather than passing a JSON array. Do not claim that the read helper performs writes.

Preserve the full old mapping, including optional fields and identity matching configuration. Show the full intended replacement and explain username/primary-key mismatch, deletion/recreation, and downstream authorization risks. Obtain authorization, write the complete configuration, then read back and compare every item. Do not trigger a synchronization merely because the mapping write succeeded. Organization/group mappings and the other S6 gates must be verified separately; this user-profile response does not establish them.

Authoritative portals: https://api.aliyun.com/product/Eiam and https://apiworkbench.aliyun-inc.com .
