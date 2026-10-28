# SAML IdP troubleshooting

## Metadata cannot be resolved

- Verify the URL returns XML directly without interactive login or HTML redirects.
- Verify public DNS, TLS trust, and IDaaS backend reachability.
- Use an IDaaS network access endpoint for private services.
- A successful browser or local fetch does not prove IDaaS can reach the URL.
- Download the metadata and use `--metadata-file` when URL hosting is unavailable.

## SP Metadata download returns HTML

- Keep the original target instance, IdP ID and SP Metadata URL from `show`; do not recreate the IdP to retry a download.
- Report HTML/WAF as a download failure. A successful `GetIdentityProvider` only supplies endpoint fields; it does not prove raw XML delivery.
- If the user can download the original XML from that exact URL, accept the file or XML text as a separate recovery step. Before presenting it, validate it as SAML SP metadata and compare both its SP Entity ID and ACS URL with the same target's authenticated `show` result. Do not change the document to make it match.
- An XML from another instance or IdP is not a substitute. A working production Metadata URL only proves that particular document can be fetched; it cannot satisfy a newly created IdP's handoff.
- Until matching original XML is available and delivered, explicitly leave raw XML handoff incomplete. No RAM, WAF, or network-security changes are part of this recovery.
- To validate a user-provided original file, run `sp-metadata --instance-id <same-instance> --idp-id <same-idp> --output-mode raw --raw-input-file <original.xml> --output-file outputs/sp-metadata.xml --output-format markdown`. This re-reads the target and verifies both Entity ID and ACS before returning the original XML. It does not repair sandbox connectivity or accept XML from another IdP.

## Certificate fingerprint mismatch

- Compute SHA-256 over base64-decoded certificate DER, not PEM text, base64 text or the public key alone.
- Compare against the original input from the current conversation. A saved “original” file can itself contain a transcription error. If it cannot be restored reliably, ask for the original again and stop writes.
- Never turn a mismatch into an accepted test warning, remove the expected-fingerprint argument, or switch to another certificate. A prior supplied constraint is retained in `outputs/metadata-constraints.json`; preserve it through failures and HITL rounds.
- Do not confuse an artifact mismatch with a runtime-only issue: read the exact target's configured certificate and compute its DER fingerprint before diagnosing a stale artifact. An incorrectly configured staged IdP should remain disabled pending explicit remediation authorization.

## Metadata parses but creation fails

- Confirm the type is `urn:alibaba:idaas:idp:standard:saml2`.
- Confirm creation uses `--method POST --force`; do not send `SamlConfig` as JSON.
- Serialize each certificate as `SamlConfig.Certificates.N.Content`; omitting `.Content` causes `InvalidSamlConfig.Certificates.N`.
- Ensure the SSO URL is valid, binding is `HTTP-REDIRECT` or `HTTP-POST`, clock skew is `0..360`, and one or two public certificates are present.
- Preserve the service error code and Request ID.
- `ResourceDuplicated.IdentityProviderExternalId`: the Entity ID is already registered in this instance. A different display name or ClientToken does not avoid this constraint. Query providers without `Direction=inbound` (the API uses values such as `pull`), identify the owner, and stop rather than changing their resource or rewriting customer Metadata.
- `QuotaExceeded` for `IdentityProvider`: inspect the existing count and preserve the reported limit. Do not retry unchanged requests until capacity is available. Cleanup requires explicit authorization for identified test resources; otherwise ask for a different instance or a quota increase.

## Signature verification fails

- Confirm the imported certificate belongs to the external IdP signing key, not the IDaaS SP certificate or a TLS server certificate.
- During certificate rollover, configure both active certificates when possible.
- Check whether the IdP signs the Response, Assertion, or both; EIAM validates with the imported IdP certificate.
- Check that the signature algorithm and canonicalization are supported and that XML was not modified in transit.
- `WantResponseSigned=true` requires a direct XML signature on the `<samlp:Response>` root. An Assertion-only signature is insufficient and produces `Saml2ResponseShouldBeSigned`.
- `WantAssertionsSigned=true` independently requires the `<saml:Assertion>` to be signed.

## The IdP rejects AuthnRequest

- Match `RequireRequestSigned` to the external IdP policy.
- If signed requests are required, register the IDaaS SP signing certificate at the external IdP.
- Match the binding and IDaaS SP Entity ID/ACS information exactly.

## Local/test IdP signing hints

- Keycloak: enable signing for SAML documents and assertions in the client signature settings, then export refreshed IdP metadata.
- SimpleSAMLphp: configure the hosted IdP signing certificate/private key and enable Response/Assertion signing according to the selected IDaaS requirements.
- AD FS: verify the relying-party trust uses the current token-signing certificate and a compatible issuance transform rule.
- Custom IdP: place a direct `<ds:Signature>` under `<samlp:Response>` when Response signing is required; signing only `<saml:Assertion>` does not satisfy that policy.

## Login returns but the user is not signed in

- Inspect NameID and attribute mapping separately from SAML transport success.
- Confirm the user is assigned/authorized in both systems.
- Check `InResponseTo`, Destination, Recipient, Audience, Conditions, and clock skew.
- Do not increase clock skew beyond 360 seconds; correct system time instead.

## Redirects to a portal without a SAML response

The external IdP may have authenticated the user but denied the SP application because of missing assignment or policy. Inspect the browser network trace for a POST to the IDaaS ACS URL. If no `SAMLResponse` is posted, troubleshoot the external IdP before IDaaS assertion validation.
