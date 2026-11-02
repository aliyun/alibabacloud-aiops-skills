---
name: alibabacloud-idaas-create-saml-idp
description: Create, update, inspect, validate, and troubleshoot a standard inbound SAML 2.0 identity provider in Alibaba Cloud IDaaS EIAM by using Alibaba Cloud CLI. Use when a user wants to connect an external SAML IdP to IDaaS, import or parse IdP metadata from a URL or XML file, configure Entity ID, SSO URL, binding, certificates and Response/Assertion/AuthnRequest signing, obtain IDaaS SP metadata, create or enable the identity source, run the built-in status check, inspect existing IdPs, or diagnose SAML identity-source failures. Also use to read and interpret SAML 2.0 identity-provider metadata for connecting an external IdP to Alibaba Cloud IDaaS EIAM before creation.
---

# Create an IDaaS SAML identity provider

Treat the external system as the SAML IdP and IDaaS as the SP. Guide the user through metadata parsing, configuration, verification, and handoff instead of reproducing the console form.

Metadata-only reading and interpretation is also in scope, before creating an IdP. If no Metadata URL, XML or public certificate is supplied, ask for the actual input; do not invent sample metadata or write a replacement parser and present it as the user's connection configuration. Instance selection and cloud writes can wait until the user requests them.

Use `scripts/idaas_saml_idp.py` for all Alibaba Cloud CLI calls and metadata parsing. Read [references/openapi.md](references/openapi.md) when exact fields or serialization behavior are needed. Read [references/troubleshooting.md](references/troubleshooting.md) when metadata validation or login fails.

## Safety rules

- Run `doctor`, `instances`, `list`, `show`, `resolve`, and `plan` without confirmation because they are read-only.
- Before `create`, `update`, or `enable`, show a concise preview and obtain explicit user confirmation in the current conversation.
- Pass `--confirm CREATE`, `--confirm UPDATE`, or `--confirm ENABLE` only after that confirmation.
- Pass `--accept-warnings` only after showing every warning and receiving explicit acceptance.
- Import only IdP public signing certificates. Never request, read, transmit, or store the external IdP private key.
- Keep request signing and credential loading inside Alibaba Cloud CLI. For `CreateIdentityProvider`, use the script's `--method POST --force` compatibility path; do not read AK/SK directly or implement request signing.
- Do not use `--cli-dry-run` with production metadata unless the user accepts that full public certificates and endpoint details will be printed.
- Create a new IdP with authentication enabled by default. The creation preview must explicitly show that authentication will be enabled, so the user's create confirmation covers both creation and the initial authentication status. Use `--authn-status disabled` only when the user requests a staged rollout; do not call `enable` again when creation already returned `enabled`.
- After every successful create, immediately ask the user to choose one of the two fixed SP information modes: separate fields or raw Metadata XML. Run `sp-metadata` in the selected mode and present the result using the fixed format below. This handoff is mandatory and must not depend on status-check API support.
- Reject localhost, loopback, URL fragments, embedded credentials, and non-HTTPS metadata/SSO URLs unless the user explicitly identifies a disposable local test and accepts the limitation.
- Do not delete an IdP. Update one only after showing the complete replacement configuration and obtaining explicit confirmation.
- Use `create --state-file outputs/create-state.json` for one onboarding operation. Keep this file, the Entity ID, and ClientToken across tool errors and conversation/HITL rounds. A completed state returns its original IdP ID without another create call; a pending or locked state stops for `list`/`show` reconciliation. Never start a fresh state file to get past an uncertain outcome or quota error. Separate deliberately new onboarding operations need separate state files.
- On a continued conversation/HITL round, use the original operation's absolute workspace and `creationStateFile` returned by create, even if the execution environment offers a new current directory. A missing relative `outputs/` in a new directory does not prove no IdP was created. Inspect earlier write results and the original absolute state path before generating a UUID or parsing a replacement working copy. If the earlier outcome cannot be recovered, stop and reconcile the existing target; do not treat visible providers as unrelated merely because a newly generated Entity ID differs.
- SAML Entity IDs must be unique within an instance; a unique display name does not isolate duplicate Metadata. Before creating, inspect existing providers and stop on a conflicting Entity ID. Do not change customer Metadata or reuse/delete another provider to bypass a conflict. `list` deliberately omits the Direction filter: `inbound` is not the API's direction value and can hide existing SAML providers.

## Workflow

### 1. Check the environment and choose an instance

Run:

```bash
python3 scripts/idaas_saml_idp.py doctor --profile <profile>
python3 scripts/idaas_saml_idp.py instances --profile <profile>
```

After the environment check, always list the instances returned by `instances`. The user is not expected to know or retrieve an Instance ID before this step. Present the result using this fixed Markdown table and do not omit the complete Instance ID:

```text
| No. | Instance name | Instance ID | Status | Version | SSO domain |
|---:|---|---|---|---|---|
| 1 | <description> | `<instanceId>` | RUNNING | EIAM 2.0 | <ssoDomain> |
```

After the table, ask the user to reply with the **number**. Also accept a complete Instance ID, exact instance name, or SSO domain when the user provides one. Resolve the chosen row to its Instance ID internally; never ask the user to look it up elsewhere or type it again.

Clearly mark non-running instances. Do not recommend or automatically select an instance merely because its name appears suitable. Use `instances --running-only` only when the user explicitly requests active instances only, and state when filtering is applied. Never infer an ambiguous instance.

Do not use inline visualizations or `:codex-followup` directives for instance selection. Use the fixed table and ordinary conversation.

After the user chooses an instance, collect the IdP display name and Metadata source. If the user already supplied either value, preserve it and ask only for the missing information.

### 2. Collect the metadata source

Prefer one source in this order:

1. IdP Metadata URL: `--metadata-url <https-url>`
2. downloaded IdP metadata XML: `--metadata-file <local-path>`
3. manual fields: `--entity-id`, `--sso-url`, and one or two `--certificate-file` values

Require an identity-provider display name. Do not ask the user to copy Entity ID, SSO URL, and certificates when metadata is available. Metadata contains public certificates, never the private key.

Preserve the supplied metadata bytes and public certificate; do not regenerate a certificate, substitute a bundled lab asset, or silently repair a fingerprint discrepancy. When the user supplies an expected certificate fingerprint, pass `--expected-certificate-sha256 <fingerprint>` on `resolve`, `plan`, `create`, and `update` (repeat for two certificates). A mismatch must stop before cloud write and be resolved from the original source. The fingerprint is a constraint, not a value to copy into a computed result.

A rejected certificate remains rejected after a settings, warning, CREATE or UPDATE confirmation. Those confirmations do not waive the fingerprint constraint. Do not switch to native CLI, an SDK or another script to submit a certificate rejected by this workflow. Recover the original input, recompute and verify the fingerprint, then present the corrected plan for confirmation. If recovery is impossible, stop the write and request the original input. The local constraint file is a workflow guard; it cannot prevent arbitrary commands outside the script.

Keep an unmodified copy of metadata received in the current conversation before editing a working copy. If a saved copy has a different fingerprint, compare it against that original input. If the original cannot be recovered reliably, ask the user to provide it again and stop the write. A certificate found in the Skill directory, an example, or another IdP is not a recovery source, even when its fingerprint matches the expected value. Do not replace the input to make a fingerprint check pass.

`outputs/metadata-constraints.json`, creation state and the handoff journal are script-owned state, not templates to fill in. Do not initialize them with handwritten JSON or edit a malformed file to let an operation continue. The first valid script invocation creates its own schema. Preserve an existing malformed file and report the error for reconciliation; do not delete it or switch workspaces to bypass it.

Run commands from a writable operation workspace. CLI calls retain a supplied fingerprint constraint in `outputs/metadata-constraints.json`, scoped to the target instance and source file/URL in this working directory. The constraint is saved before resolution, including when resolution fails; subsequent calls cannot drop or replace it by omitting the flag. Preserve that file and the working directory across tool/HITL rounds. Do not delete/edit it, move the source, or switch directories to bypass a mismatch. A deliberately new operation, including a user-approved certificate rotation, needs its own original input and operation workspace; never reset a failed operation's constraints automatically.

### 3. Resolve and preflight

Run `resolve` with the selected source:

```bash
python3 scripts/idaas_saml_idp.py resolve \
  --profile <profile> --instance-id <instance-id> \
  --metadata-url <metadata-url>
```

For a file, replace `--metadata-url` with `--metadata-file`. Add `--network-access-endpoint-id <id>` only when IDaaS must reach a private Metadata URL.

`resolve` saves its actual computed JSON to `outputs/metadata-resolution.json` by default, independently of shell redirection. Use `--output-file <path>` only when another artifact path is explicitly needed. The saved result contains the actual Entity ID, SSO URL and computed certificate fingerprints; do not hand-write a replacement artifact.

Explain the resolved Entity ID, SSO services, bindings, signing-certificate fingerprints, `WantAuthnRequestsSigned`, and warnings. The script may fetch a Metadata URL locally only for diagnosis if the official IDaaS resolver fails; that fallback does not prove IDaaS backend reachability. Treat its warning as blocking unless the user fixes connectivity or explicitly accepts it.

### 4. Confirm optional settings

Always show the effective settings, including defaults, in one group. For example:

```text
Optional settings (recommended):
- SSO Binding: HTTP-REDIRECT
- Require IDaaS to sign AuthnRequest: disabled
- Require the external IdP to sign Response: enabled
- Require the external IdP to sign Assertion: enabled
- Maximum clock skew: 180 seconds
- Signing certificates: 1 (show the SHA-256 fingerprint)
- Network access endpoint: none
- Authentication status after creation: enabled

Reply "Continue with the recommended settings", or specify the settings to change.
```

Follow these rules:

- Prefer `HTTP-REDIRECT` when metadata advertises it; otherwise use `HTTP-POST`.
- Derive AuthnRequest signing from metadata `WantAuthnRequestsSigned` when present. Otherwise recommend disabled and tell the user to enable it only if the IdP requires signed requests.
- Default both `WantResponseSigned` and `WantAssertionsSigned` to enabled. These control what IDaaS accepts from the external IdP; they are different from `RequireRequestSigned`, which controls IDaaS outbound AuthnRequests.
- Allow either inbound signature requirement to be disabled only when the user explicitly chooses the interoperability/security tradeoff. Prefer keeping at least one signed object and never describe disabling both as production-safe.
- Default maximum clock skew to 180 seconds. Accept only `0..360`; do not use clock skew to conceal a persistently incorrect system clock.
- Import signing certificates from metadata, deduplicate them, and accept at most two because EIAM supports at most two. If more are present, stop and ask which active/rollover certificates to use.
- Allow the user to change binding, request-signing requirement, clock skew, selected certificates, network access endpoint, and initial authentication status.
- Default the initial authentication status to `enabled`. Use `disabled` only when the user explicitly asks to create first and enable later.
- Accept “Continue with the recommended settings” as one confirmation without asking about every item separately.

### 5. Produce a creation plan

Run `plan` with the final values. It emits a preview containing certificate fingerprints rather than certificate bodies.

```bash
python3 scripts/idaas_saml_idp.py plan \
  --profile <profile> --instance-id <instance-id> --name <name> \
  --metadata-file <path> --binding HTTP-REDIRECT \
  --no-require-request-signed --want-response-signed \
  --want-assertions-signed --max-clock-skew 180 \
  --authn-status enabled
```

Show the instance, source, Entity ID, SSO URL, binding, all three signing settings, clock skew, certificate count/fingerprints, warnings, and the initial authentication status. Make `enabled` visually explicit because creation makes the identity source available immediately. Also show `externalIdpRequirements`; this prevents a user from discovering the signing contract only after login fails.

### 6. Create after confirmation and immediately hand off SP metadata

After explicit confirmation, rerun the same parameters with `create --confirm CREATE --state-file outputs/create-state.json`. If warnings exist, show them and require separate acceptance before adding `--accept-warnings`. Report the returned identity-provider ID, request ID, and authentication status. On a later round, inspect the existing state/result before generating any new identity or issuing a create command. The service may validate or normalize the display name; report the stored name if observed, but do not treat name normalization as a SAML configuration failure.

Before a new POST, `create` performs a fresh complete `ListIdentityProviders` check and rejects an existing Entity ID. When the user supplies the instance's quota, pass `--idp-quota <limit>` to also stop if the inventory is full; do not assume every instance has the same limit. Successful output includes `creationPreflight` with the target and real list request IDs. Reusing a completed creation state does not issue another list or create. Both create and update return a `writeReceipt` tying the actual submitted certificate fingerprints to the target and write request ID; retain this alongside the state and subsequent same-target readback. It is evidence of the submitted configuration, not a substitute for a successful response or readback.

Immediately after every successful creation, regardless of whether the status-check API is supported, use this exact choice prompt and wait for the user's selection. Do not choose a mode on the user's behalf unless they already specified one:

```text
Choose how to receive the IDaaS SP information:
1. Separate fields: SP Metadata URL, SP Entity ID, and ACS URL
2. Raw data: complete SP Metadata XML

Reply with 1 or 2.
```

For option 1, run:

```bash
python3 scripts/idaas_saml_idp.py sp-metadata \
  --profile <profile> --instance-id <instance-id> --idp-id <idp-id> \
  --output-mode fields --output-format markdown
```

Present the result using exactly this structure:

```text
## IDaaS SP information (separate fields)

- SP Metadata URL:
  <spMetadataUrl>
- SP Entity ID:
  <spEntityId>
- ACS URL:
  <spAcsUrl>
```

For option 2, run:

```bash
python3 scripts/idaas_saml_idp.py sp-metadata \
  --profile <profile> --instance-id <instance-id> --idp-id <idp-id> \
  --output-mode raw --output-file outputs/sp-metadata.xml --output-format markdown
```

Present the result using exactly this structure, with the XML in an `xml` code block:

````text
## IDaaS SP Metadata (raw XML)

- Metadata source URL: <spMetadataUrl>

```xml
<rawMetadataXml>
```
````

The creation handoff is incomplete until the selected format has been delivered. If the first read is temporarily unavailable, preserve and report the created IdP ID, retry the read briefly, and do not retry creation.

An HTML/WAF response is an incomplete raw XML handoff. Keep the exact target IdP ID and Metadata URL in the final response. A user may download the original XML from that exact URL and provide it for a later handoff; first verify its SP Entity ID and ACS URL against `show` for the same target. Do not use XML from a different IdP or report a URL/fields-only result as raw XML delivery. See [download recovery](references/troubleshooting.md#sp-metadata-download-returns-html) for the remaining checks.

For that recovery, save the user-provided original XML text/file without reconstructing it, then run the same target's `sp-metadata --output-mode raw --raw-input-file <provided-file> --output-file outputs/sp-metadata.xml --output-format markdown`. This performs a fresh authenticated target read and rejects an Entity ID or ACS mismatch, HTML and oversized input. The result labels the source `user-supplied-file`; it does not claim the sandbox downloaded it. Without matching original XML, leave delivery incomplete and request the file instead of repeating downloads.

The output file contains only validated downloaded XML. Present its complete contents in the raw format above, without reconstructing XML from SP fields. A file path or Metadata URL alone does not complete a request for raw XML.

For raw mode, an HTTP 200 response alone is not success. The downloader validates a SAML SP descriptor, its ACS endpoint, and the SP Entity ID returned by IDaaS. It tries the normal download and at most one system-curl fallback, including when the first response is HTML instead of metadata. If both fail, report the download error, existing IdP ID, and Metadata URL, and leave the raw handoff explicitly incomplete. Stop repeated downloads until connectivity changes; do not recreate the IdP, synthesize XML, or silently switch the requested output mode.

The last assistant answer must itself contain the selected SP handoff, even if the same information appeared earlier or is stored in files. Use the rendered Markdown above: all three labeled endpoint values for fields mode, or the complete validated XML for raw mode. An action summary saying “SP information delivered” is not the handoff.

Prepare this handoff after the last check or write, rather than replacing it with an action summary. For fields, run `sp-metadata --output-mode fields --output-format markdown` after the check and include its three endpoint values in the final answer. After a staged enable, include the returned `spHandoffMarkdown` verbatim: it repeats the same target's validated handoff without another download. In raw mode, if that block is unavailable, use `sp-metadata --output-mode raw --raw-input-file <previously-validated-file> --output-format markdown` for the same target and include the complete output. Preserve the selected output mode; do not ask the user to choose it again.

### 7. Run the official status check

Run:

```bash
python3 scripts/idaas_saml_idp.py check \
  --profile <profile> --instance-id <instance-id> --idp-id <idp-id>
```

Translate every failed check item into an actionable explanation. If the service returns `UnsupportedAction`, treat the script's result as a non-blocking capability warning: continue to `show`/`sp-metadata` and advise console verification. Use `check --skip-check` only when the user explicitly chooses to skip an unsupported or unavailable check. A successful configuration check does not prove browser SSO, account matching, NameID mapping, or authorization succeeds.

### 8. Complete external IdP setup and test login

Tell the user to configure the SP Metadata URL, SP Entity ID, and ACS URL at the external IdP, grant users access, and then perform a real SP-initiated login test. Before testing, explicitly verify that the external IdP signs Response and Assertion according to the selected requirements and emits a NameID/attributes compatible with IDaaS account mapping.

A default creation is already enabled and needs no separate `enable` call. If the user explicitly created it with `--authn-status disabled`, explain that enabling exposes the identity source to authentication, obtain explicit confirmation, and then run `enable --confirm ENABLE`.

For a staged rollout, do not declare completion after creating the disabled IdP. After the requested SP handoff and status-check outcome are available, read back the exact created IdP, show the enable preview, request explicit enable confirmation, and only then enable it. If a certificate mismatch or incomplete SP handoff blocks this sequence, preserve `disabled`, request the missing original input/XML, and report the remaining enable step; do not treat a blocked stage as completed.

### 9. Update an existing SAML IdP when required

Use `update` to replace the complete SAML connection configuration, including certificates and signing requirements. Always run `show`, resolve the desired metadata again, display the full update preview, and obtain explicit confirmation before `update --confirm UPDATE`. The command intentionally requires a complete metadata source so a partial update cannot silently erase certificates or endpoints. Run status check and `sp-metadata` again afterward.

## Failure handling

- Preserve the original CLI error code and request ID, but redact sensitive credential fields.
- If creation times out, list existing IdPs before retrying; compare name, Entity ID, and stored `ClientToken` to avoid duplicates.
- If metadata resolution fails, diagnose DNS, TLS, XML validity, EntityDescriptor structure, SSO bindings, signing certificates, and IDaaS network reachability before creation.
- If the status check fails, do not claim that the configuration is ready for login. Because the default creation status is enabled, clearly report the failure and advise the user not to test or roll out login until the failed checks are corrected.
- If login reports `Saml2ResponseShouldBeSigned` or an Assertion signature equivalent, compare the error with `WantResponseSigned`/`WantAssertionsSigned` and fix the external IdP signing behavior; weaken the IDaaS requirement only for an explicitly accepted test scenario.
- Distinguish metadata parsing, IDaaS status checking, and real browser SSO verification.

### Persisted staged handoff

`resolve` retains its nested metadata and also emits computed `entityId`, selected
`ssoUrl`, and normalized `certificateSha256s`. For a single certificate it emits
`certificateSha256`. Save actual stdout; do not invent these values.

`check` emits `instanceId`, `identityProviderId`, `outcome`, `serviceError`, and
`readbackVerified`. On UnsupportedAction it performs a fresh same-target `show`
and preserves the original error. Failed readback stays unverified. A failed or
unfinished job is not a successful status check.

When `sp-metadata` reads a disabled target, it records the staged handoff in
`outputs/sp-handoff-state.json`, scoped by profile, region, instance and IdP.
An attempted raw handoff remains pending after a WAF/download failure; switching
to fields cannot clear it. `enable` rejects a recorded incomplete handoff even
with `--confirm ENABLE`. It requires actual check evidence and revalidates the
saved original XML against fresh official Entity ID and ACS before enabling a
raw handoff. Preserve the journal and working directory across commands; never
remove or edit it to bypass a blocked enable. It is a workflow guard, not an
access-control boundary against arbitrary CLI calls or local file editing.

For raw delivery, explicitly use `--output-mode raw --output-file
outputs/sp-metadata.xml`. If download fails, ask a separate question requesting
only the same target's original SP XML. Keep disabled; do not combine this
question with ENABLE or request the already verified IdP signing certificate.
Use `--raw-input-file` to validate supplied originals, then deliver the complete
XML and record the actual check outcome before a separate enable preview and
confirmation. Do not state completion while waiting for original XML.

For updates, explicitly pass the user's selected `--output-mode fields` or
`--output-mode raw`; the default fields mode does not satisfy a raw XML request.
