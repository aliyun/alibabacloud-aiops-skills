# EIAM SAML IdP OpenAPI reference

## Core operations

| Operation | Purpose | Mutating |
|---|---|---|
| `ListEiamInstances` | List visible EIAM instances | No |
| `ListIdentityProviders` | List identity providers | No |
| `GetIdentityProvider` | Read one identity provider and SP handoff data | No |
| `ExecIdentityProviderMetadataUrlResolution` | Resolve a SAML Metadata URL through IDaaS | No |
| `CreateIdentityProvider` | Create a SAML identity provider | Yes |
| `CreateIdentityProviderStatusCheckJob` | Start built-in configuration checks | Creates a diagnostic job |
| `GetIdentityProviderStatusCheckJob` | Poll status-check results | No |
| `EnableIdentityProviderAuthn` | Make the identity source available | Yes |

API product/version: `eiam` / `2021-12-01`.

## SAML creation model

- Identity provider type: `urn:alibaba:idaas:idp:standard:saml2`
- Required SAML fields:
  - `SamlConfig.IdPEntityId` (may be an HTTPS URL or URN)
  - `SamlConfig.IdPSsoUrl`
  - `SamlConfig.Certificates.N.Content`
  - `SamlConfig.BindingMethod`: `HTTP-REDIRECT` or `HTTP-POST`
  - `SamlConfig.RequireRequestSigned`
  - `SamlConfig.WantResponseSigned`
  - `SamlConfig.WantAssertionsSigned`
  - `SamlConfig.MaxClockSkew`: `0..360` seconds
- Optional private connectivity: `NetworkAccessEndpointId`

Create with `AuthnConfig.AuthnStatus=enabled` by default. Use `disabled` only for a user-requested staged rollout. The creation preview and confirmation must disclose the selected initial status.

After creation, ask the user to choose either separate SP fields or the raw SP Metadata XML. For separate fields, call `GetIdentityProvider` and present the SP Metadata URL, SP Entity ID, and ACS URL. For raw XML, read the service-returned SP Metadata URL and return the complete XML. This handoff is required even when the status-check API is unsupported.

`Certificates` is an array of objects, not strings. Each PEM-encoded public X.509 certificate must use the `.Content` suffix. EIAM accepts at most two. Never send a private key.

## Metadata resolution

Call `ExecIdentityProviderMetadataUrlResolution` with `InstanceId` and `SamlMetadataUrl`. Normalize the returned `IdentityProviderMetadata.SamlMetadataConfiguration`, whose effective fields are Entity ID, SSO URL, and certificate content. The API resolver does not replace the need to choose binding, request-signing behavior, and clock skew explicitly.

For a downloaded XML file, parse the SAML 2.0 `EntityDescriptor` locally:

- `entityID`
- `IDPSSODescriptor/SingleSignOnService` Binding and Location
- signing or unspecified `KeyDescriptor/X509Certificate`
- optional `WantAuthnRequestsSigned`

## Alibaba Cloud CLI flat-object compatibility

`CreateIdentityProvider` and `UpdateIdentityProvider` publish `SamlConfig` as a top-level object in CLI metadata, while the EIAM RPC service requires flat parameters such as `SamlConfig.IdPSsoUrl` and `SamlConfig.Certificates.1.Content`. JSON object serialization is rejected by the service.

Invoke creation with:

```text
--method POST --force
```

`--force` bypasses incomplete local parameter registration and forwards the required flat keys. Alibaba Cloud CLI still owns credential resolution and request signing, including STS and role-based profiles. Do not read `~/.aliyun/config.json` or implement V1 HMAC signing.

## Metadata and SP handoff are different

The imported XML describes the external IdP. After creation, the external IdP still needs the IDaaS SP Entity ID, ACS URL, and—when signed AuthnRequests are required—the IDaaS SP signing certificate. Obtain these from the created identity provider details/console and do not confuse them with the imported IdP values.

## Status check

Poll the job returned by `CreateIdentityProviderStatusCheckJob` through `GetIdentityProviderStatusCheckJob`. Inspect each major/minor check item and error reason. Some instance versions/regions return `UnsupportedAction`; report that as an unsupported capability rather than a failed SAML configuration, then continue with `GetIdentityProvider` and console verification. Passing proves only configuration/connectivity checks; it does not prove user assignment, account matching, NameID mapping, or end-to-end SSO.
