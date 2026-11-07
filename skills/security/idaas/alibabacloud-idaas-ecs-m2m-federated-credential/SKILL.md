---
name: alibabacloud-idaas-ecs-m2m-federated-credential
description: "Configure Alibaba Cloud IDaaS EIAM federation for ECS without AccessKeys (AK): create PKCS#7 federated credential providers, create or select M2M client applications, bind application federated credentials to ECS instances or cloud accounts, authorize PAM scopes, and guide ECS signature and client_assertion token exchange with pkcs7-bearer. Use when users ask for machine identity authentication, read-only IDaaS/ECS inventory, or missing federation parameters. Triggers: ECS authentication without AK, PKCS#7 federation, federated credential providers, M2M client applications, application federated credentials, ECS-to-EIAM/IDaaS access tokens, read-only IDaaS/ECS instance queries"
---

# IDaaS ECS M2M Federation (PKCS#7, Without AK)

Implement the verified end-to-end flow: **ECS instance identity signature (PKCS#7 + IMDSv2) → signature verification by an EIAM federated credential provider → application federated credential verification → M2M token issuance using client_credentials**.

All scripts are in `scripts/`. They use **Python 3 with the standard library only**, calling the `aliyun` CLI through subprocess (credentials must already be configured). Run scripts from the workspace root: `python3 scripts/<script>.py`.

Respond in the user's language unless they request otherwise.

For exact API versions, required request parameters, CLI option mappings, and response fields, read [OpenAPI contracts](references/openapi-contracts.md). Each listed RPC Action is independent; the OAuth token endpoint is a separate instance HTTP API.

## Execute Scoped Read-Only Requests

Preserve the API, region, page number, page size, and filters explicitly supplied
by the user. Initialize the session and read the manifest before the first cloud
call. Execute only the requested read operation using the configured credential
chain and the session user-agent; do not start parameter collection, creation,
authorization, or cleanup for an inventory-only request.

For a bounded `ListInstances` query, call the CLI directly with the requested
pagination values:

```bash
aliyun eiam list-instances --region <region> --page-number <page_number> --page-size <page_size> --user-agent "$UA"
```

`UA` must contain the manifest version and current session ID in the format below.
Do not substitute `list_instances.py` for this bounded request: that script is
intended for complete federation discovery and retrieves all pages with its own
page size. Do not silently change a requested first page of 10 into pages of 50.
Report the returned `TotalCount` and only the requested page's items. No instance,
application, Provider, or ECS ID is needed for `ListInstances`. Request only
missing parameters required by the selected API. On failure, preserve the actual
error code and request ID; permission guidance must identify the failed read
Action without demanding write permissions. A failed query is never an empty list.
Honor an explicit no-retry instruction.

For full federation configuration, retain the prerequisite checks, complete paged
discovery scripts, parameter collection, creation, verification, and owned-resource
cleanup described below.

Preserve explicitly requested authentication and trust modes. Never replace `oidc+oauth2/m2m` with `oidc`, change the selected account or region, or switch credential verification mode to work around a rejected request. If the requested operation cannot be completed, preserve its error and report the blocked prerequisite before proposing a different plan.

## Phase 0: Prerequisites (Credential Validation and Permission Guidance)

1. **CLI installation**: Run `aliyun version`. If the CLI is not installed, guide the user through installation using `assets/cli-installation-guide.md`. Use the pinned release and SHA256 verification in that guide; do not execute remote install scripts or use unverified latest packages. Check the installed product-plugin help for the documented typed object/array options; update the CLI/plugins from the vendor if required options are missing. Use the verified request format in `references/api-and-pitfalls.md`, rather than guessing compatibility from the CLI version alone.
   Before a product's first request, check `aliyun plugin list`. Install a missing required plugin using the vendor's default index: `aliyun plugin install --names aliyun-cli-eiam` for EIAM, `aliyun-cli-sts` for identity validation, or `aliyun-cli-ecs` when ECS inventory is requested. Complete installation before running API helpers. Do not change global automatic-install settings.
2. **Credential validation** (the aliyun CLI has no separate login state; access depends on configured credentials): Run `aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-idaas-ecs-m2m-federated-credential/<version>/<session_id>` to validate access:
   - Success → credentials are valid. **Record the returned AccountId** as the default for the subsequent "current cloud account" option.
   - Failure → distinguish between missing configuration (ask the user to run `aliyun configure` in their terminal, keep credential entry in the user's terminal; do not request or print AccessKeys in the conversation) and expired STS credentials or invalid AK credentials (reconfigure or rotate them).
3. **Permission guidance (proactively show this after validation succeeds and before asking questions)**:
   > This skill requires the following RAM permissions:
   > - **Required**: only the EIAM Actions needed by the selected workflow; use the minimal custom policy in `references/ram-policies.md`. Include cleanup Actions only when that cleanup is authorized. Do not recommend FullAccess as the default remedy for a single denied Action.
   > - **Optional**: ECS read-only access, `AliyunECSReadOnlyAccess` (only used to list instances for selection in specific-instance mode; if unavailable, fall back to manual instance ID input without blocking the flow).
   > - **Not required**: Cloud Assistant RunCommand or RAM write operations.
   > See `references/ram-policies.md` for the mapping from actions to steps.
4. **If `Forbidden.RAM` occurs**: Use `references/ram-policies.md` to identify the missing action and affected step. Identify the exact denied Action and propose only its required authorization using the minimal policy. Do not demand a FullAccess policy; discuss a broader system policy only if the user explicitly asks. Wait for authorization before retrying, and honor an explicit stop or no-retry instruction. Except for the built-in fallback in list_ecs, **do not silently skip failed steps**.
5. **Input pre-validation (before any API call)**:
   - Validate that the region is in the EIAM supported list: `cn-hangzhou`, `cn-beijing`, `cn-hongkong`, `ap-southeast-1`, `ap-southeast-5`, `ap-northeast-2`, `eu-central-1`. Reject unsupported regions immediately and present the supported list for the user to re-select.
   - Validate name formats: provider names must match `[a-z0-9_-]{1,64}`; application and credential names must be ≤64 characters. If a provider name contains uppercase letters or invalid characters, suggest a corrected lowercase version (e.g. `My-Trust` → `my-trust`) and confirm with the user before proceeding. Preserve application and credential name casing; their length must be 1–64 characters.
   - Validate the IDaaS instance ID against `idaas_[a-z0-9]+` before constructing trust conditions or calling APIs.
   - Validate AccountId is a numeric string of appropriate length (typically 16 digits for Alibaba Cloud account IDs).
   - Pre-validation failures must be reported to the user immediately with a specific correction suggestion; **do not defer to API-level errors**.

When a cloud operation fails, the final user-facing reply must name the failed
Action, error category, actual error code, actual RequestId, and the next safe
step. Include these concise diagnostics even when a detailed report or execution
log is saved to a file; a file link alone is insufficient. If the response has no
RequestId, state that it was not returned rather than inventing one. Preserve the
first failed write result and any explicit stop or no-retry instruction.
This also applies when ending a turn to await the user's decision: include the
diagnostic summary in that same last message together with the question. Do not
follow a complete error report with a separate "waiting for your reply" message
that drops the Action, category, code, RequestId, and safe next step. After a
stop answer, retain those diagnostics in the closing reply without retrying.

## Session Initialization and Observability

### Session ID Generation
At the start of every skill invocation, generate a **32-character lowercase hexadecimal session ID** and export it as `SKILL_SESSION_ID` for every script process (e.g. `export SKILL_SESSION_ID=$(python3 -c "import secrets; print(secrets.token_hex(16))")`). This session ID uniquely identifies one end-to-end execution of this skill and must be included in every `--user-agent` value throughout the session.

### Manifest Read Gate
Before the first cloud API call, read `references/manifest.json` to obtain the current skill version. If the file is missing or the `version` field is empty, **abort with an error** and instruct the user to restore it. The version from `references/manifest.json` is used in the user-agent string.

### User-Agent Format
Every `aliyun` cloud API command must include:
```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-idaas-ecs-m2m-federated-credential/<version>/<session_id>
```
Where `<version>` is read from `references/manifest.json` and `<session_id>` is the generated 32-character hex string. The Python scripts in this skill call `aliyun` through subprocess; they append this flag automatically, including ECS queries.

For direct CLI examples below, bind shell variable `UA` to this complete value
after reading the manifest and generating the session ID. Never send an empty
`--user-agent` value.

### Preserve Command Results
Keep the original command's stdout, stderr, and exit code together. A pipeline
such as `python3 scripts/list_ecs.py ... | tee ...; echo $?` reports the exit
code of `tee`, not the script. Prefer a direct invocation and the execution
tool's actual exit code. If file capture is needed, redirect stdout and stderr
to separate files and capture `$?` immediately after that same command, before
any other shell command; do not rerun an operation just to obtain its log.

For large read-only CLI responses, capture the complete original stdout directly
to an output file before displaying a bounded summary. Do not reconstruct JSON
from a truncated tool preview. Parse the saved file to confirm it is complete
and report the actual pagination metadata (for ECS DescribeInstances:
TotalCount, PageNumber, PageSize, and RequestId) from that response. Retain the
original response file and stderr even if parsing fails; report the failure
instead of inventing missing fields. Do not apply shell wrappers to a request
whose explicit invocation contract requires a single unwrapped CLI command.

### Skill Switch Isolation
- Do not change shared CLI defaults, credential profiles, or other skills' configuration. Installing missing required vendor plugins is a prerequisite, not permission to change global automatic-install settings.
- All temporary files (signature files, intermediate outputs) must include the session ID in their filename (e.g. `/tmp/sig_<session_id>.pem`) and be deleted after use.
- If the user switches to a different skill mid-conversation, this skill's session state is considered stale; generate a new session ID on the next invocation.

## Interaction Rules (Required for User Experience)

- Collect all parameters marked **[Ask]** below using the execution environment's question tool (such as **AskUserQuestion**), or a plain-language question if unavailable. **Do not assume answers on the user's behalf**.
- If a question tool is deferred, discover it and then invoke the returned question tool with the actual question. Tool discovery, a todo item, and a proposed question in a log do not deliver a question to the user. Wait for the answer before continuing the dependent step; use a plain-language question only when no question tool is available.
- Provide a **suggested default** for every name question, marking the option "(Recommended)". The user can always supply a custom value through **Other**.
- For list selections (IDaaS instances, M2M applications, or ECS instances), first show the complete list in a table in the **message body**, including ID, name, and description. Include only the most representative ≤3 entries plus Other in AskUserQuestion options (maximum 4 options).
- **Combine independent questions** into a single AskUserQuestion call (within the question tool's supported limit) to reduce interaction rounds.
- Check for **name conflicts** using List APIs before creation. If a name conflicts, append `-2` or `-3` to the suggested name and explain this in the message body; shorten the base if needed to stay within 64 characters. No extra question round is needed.
- Use parameters the user has already supplied (such as instance IDs, names, or scope) directly. **Do not ask again**.

## Phase 1: Collect Parameters in Three Rounds

### Round 1 [Ask]: Region and ECS Owner Account
- Q1 Region: `cn-hangzhou` (Recommended) / `cn-beijing` / `ap-southeast-1` / `eu-central-1` + Other.
  (Supported EIAM regions: cn-hangzhou, cn-beijing, cn-hongkong, ap-southeast-1, ap-southeast-5, ap-northeast-2, eu-central-1.)
- Q2 ECS owner account: `Current account <AccountId>` (Recommended) / another account (ask the user to enter that account's numeric ID through Other).

Then run `scripts/list_instances.py <region>` to retrieve the instance list. For programmatic selection or auditing, append `--json` to return every paginated instance with its complete metadata and untruncated description; the default output remains a human-readable table. Do not infer instance eligibility from a truncated display label.

### Round 2 [Ask]: IDaaS Instance, Provider Name, and Signature Validity
- Q1 Instance: Select from the list (show the complete table first; include ≤3 representative options plus Other for manual instance ID input).
- Q2 Federated credential provider name: Suggest `ecs-pkcs7-trust` (**lowercase letters, digits, `_`, and `-` only; ≤64 characters**) + Other.
- Q3 Signature validity: `3600 seconds` (Recommended) / `900 seconds` (more secure) / `86400 seconds` + Other.

Then run the following **in parallel**:
- `scripts/list_m2m_apps.py <region> <instance_id>` (for the "select an existing application" option in Round 3).
- If the current account was selected in Round 1: `scripts/list_ecs.py <region>` (for specific-instance mode; if it reports `NO_PERMISSION` with exit code 2, ask the user to provide instance IDs manually).

### Round 3 [Ask]: Client Application, Credential Name, and Verification Mode
- Q1 M2M client application:
  - `Create an application named ecs-m2m-client` (Recommended); the name can be changed through Other.
  - `Use existing application <app_id> (<name>)`; include ≤2 entries from list_m2m_apps plus Other (show the complete table in the message body).
- Q2 Application federated credential name: Suggest `ecs-afc` (≤64 characters) + Other.
- Q3 Credential verification mode:
  - `Specific ECS instances`: Only selected instances can obtain tokens. This is the strictest option. If an ECS list is available, follow up with **[Ask]** to select one or more instances using multiSelect, up to 10. Otherwise, ask the user to enter comma-separated instance IDs.
  - `Cloud account`: Trust **all** ECS instances in that account (recommended for unified account governance).

## Phase 2: Create Resources (Sequentially; Stop on Failure and Suggest a Fix)

When the user requires PAM, check candidate instances before creating resources with `aliyun eiam check-instance-module-status --region <region> --instance-id <iid> --module-key urn:alibaba:idaas:license:module:pam`. An explicit `Module.ModuleStatus=enabled` is required for that selection. M2M entitlement is validated by application creation and the subsequent `M2MClientStatus` readback; `m2m` is not a verified module key, and a successful application list does not prove creation entitlement. Keep successful resource IDs from every attempted instance for authorized teardown.

PAM module state belongs to a specific region and InstanceId, not the whole
account. If preparation switches to another candidate after a quota or license
rejection, query that candidate's module state again before using its PAM branch.
Never reuse another instance's enabled or disabled result. A disabled-PAM path
also requires a successful explicit check on the instance that owns the newly
created resources; an earlier candidate's result cannot justify skipping its
authorization.

Use only actual IDs returned by queries or supplied by the user. Never copy resource
IDs from examples or evaluation files. Record each successful creation immediately,
including its region, IDaaS instance, resource ID, name, and whether this invocation
created it. A reused application is not owned by this invocation. If a later step
fails, report the partial resource list and stop; do not retry creation blindly.

After creation, perform three independent readbacks using direct CLI calls:

1. **Provider readback**: `aliyun eiam get-federated-credential-provider --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"` — verify TrustCondition contains the correct AccountId and the Pkcs7ProviderConfig audience matches the IDaaS instance ID.
2. **Application readback**: `aliyun eiam get-application --region <r> --instance-id <iid> --application-id <app_id> --user-agent "$UA"` — verify `M2MClientStatus=enabled`, confirm `ClientId` matches the value used in subsequent steps, and check `SsoType=oidc+oauth2/m2m`. This is a mandatory verification step; a zero exit code from the creation script alone does not prove the application is correctly configured.
3. **Credential association readback**: `aliyun eiam list-application-federated-credentials-for-provider --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"` — verify the credential name, application ID, verification mode, and trust condition (instance IDs or cloud account) match the request. Do not add `--application-id` to this API call.

A zero CLI exit status alone does not prove the configuration is correct. Report each readback result including the actual field values.


```bash
# 1. Federated credential provider (account condition: owner-account-id + aud=IDaaS instance ID)
scripts/create_trust_source.py <region> <instance_id> <provider_name> <account_id> [validity]
#    → Record FCP_ID=fcp_xxx

# 2. M2M client application (only when creating a new application; skip when using an existing one)
scripts/create_m2m_client.py <region> <instance_id> <app_name>
#    → Record APP_ID=app_xxx and confirm M2M_STATUS=enabled

# 3. Application federated credential
scripts/create_federated_credential.py <region> <instance_id> <app_id> <fcp_id> <cred_name> <instance|account> <comma_separated_instance_ids|cloud_account_id>
#    → Record AFC_ID=afc_xxx

# 4. PAM feature permission authorization (run by default; fully automated in two stages, verified in 2026-10)
scripts/authorize_pam_scope.py <region> <instance_id> <app_id>
#    Stage A, RS level: AuthorizeResourceServerToClient(iap_pam) (idempotent)
#    Stage B, scope level: ListResourceServerScopes(--resource-server-scope-type all ← required!)
#                → Find the ress_id for cloud_account_role:obtain_access_credential
#                → AuthorizeResourceServerScopesToClient (JSON array of scope IDs)
#    → PAM_AUTH=auto_done: Automatic authorization completed; use token scope
#      urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential
#    → PAM_AUTH=module_disabled: PAM is not enabled; skip if only an M2M token is needed
#    → PAM_AUTH=scope_not_found: Fall back to the console (Permission Center > Feature Permission Management)
#    Reminder: STS exchange also requires a data permission authorization rule in the console
#    linking the application to the target cloud role (Data Permission Management).
```

## Phase 3: Summary and Verification Guidance

Token exchange is an instance-scoped HTTP integration, not a POP RPC Action. Its
required form fields and JSON responses are specified in
`references/oauth-token.openapi.yaml`. Do not register the URL as a fictitious
EIAM RPC Action or merge it with an RPC identifier.

HTTP API metadata for this step:

| Metadata | Contract |
|---|---|
| Product and version | IDaaS EIAM instance HTTP API, v2 |
| Method and path | POST, `/api/v2/iauths_system/oauth2/token` |
| Endpoint | Actual `Instance.DefaultEndpoint.Endpoint` returned by GetInstance |
| Content type | `application/x-www-form-urlencoded` |
| Required parameters | `grant_type=client_credentials`; actual `client_id`; `client_assertion_type=urn:cloud:idaas:params:oauth:client-assertion-type:pkcs7-bearer`; actual `client_assertion`; actual `application_federated_credential_name`; actual authorized `scope` |
| Success response fields | HTTP 200 JSON with nonempty `access_token`; optional `token_type`, `expires_in` |
| Rejection response fields | Actual HTTP status and OAuth JSON `error`, `error_description`; authentication rejection is 400 or 401, not a network/WAF failure |

Complete token input means all six form fields and the discovered endpoint are
available. Resource discovery and the token HTTP call have separate contracts;
missing a signature or scope must not make an otherwise complete read-only RPC
request require federation setup parameters.

1. **Summary table**: List the IDs, names, key settings, and verification conditions of the provider, application, and application federated credential.
2. Retrieve the instance endpoint: `aliyun eiam get-instance --region <r> --instance-id <iid> --cli-query 'Instance.DefaultEndpoint.Endpoint' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-idaas-ecs-m2m-federated-credential/<version>/<session_id>`
3. **Give the user the signature command**: Run `scripts/gen_ecs_sign_command.py <instance_id>` and send the generated one-line command to the user. Ask them to run it on ECS and paste back the signature. Remind them to do this promptly: signature validity equals the value configured on the provider.
4. Save the returned signature in a temporary file (delete it with `rm` after use). **[Ask]** which **scope** to request, in the format `<ResourceServerIdentifier>|<ScopeValue>`. For the PAM-to-STS flow, use the fixed scope `urn:cloud:idaas:pam|cloud_account_role:obtain_access_credential` (Phase 2, step 4 authorization must be completed first).
5. Run `scripts/test_m2m_token.py <endpoint> <client_id> <cred_name> <scope> <sig_file>` and report the result accurately (token summary or error). Preserve the script's actual status in the final reply as `HTTP_STATUS=<actual integer>`. For an OAuth rejection also include the actual `error` and `error_description`, the script exit code, and whether a token was issued. Do not invent an HTTP status for network failures or replace the status field with a success/failure label.

## Critical Constraints and Verified Pitfalls

1. **Use the typed plugin interface**. The provider script passes `--pkcs7-provider-config` as one JSON object with canonical API field names; the CLI serializes it into flat request parameters and selects POST from metadata. Scope authorization passes `--resource-server-scope-ids` as a JSON array. The complete helper requests are checked with the native CLI dry-run parser. Legacy override flags and dotted CLI options are not part of this interface.
2. **ECS signature requests must include the IMDSv2 token header** (first call `PUT /latest/api/token`). The audience must be URI-encoded JSON: `{"aud":"<IDaaS_INSTANCE_ID>","signingTime":<seconds>}`. The aud value must be the IDaaS instance ID. The generator script already implements this.
3. **Use the ResourceServer identifier exactly as registered in scope**. Unusual forms such as the single-slash `api:/xxx` are valid; **never "normalize" them to `api://`**. `.all` is a wildcard granting all scopes of that RS. A nonexistent ResourceServer causes `Invalid audience: <identifier>`; omitting scope causes `scope required` (scope is required).
4. **Use a single-line base64 body for client_assertion**, removing the `-----BEGIN/END PKCS7-----` delimiters and line breaks. This format has been verified; the test script normalizes it automatically.
5. The token endpoint is fixed: `https://<DefaultEndpoint>/api/v2/iauths_system/oauth2/token`. Query the endpoint using GetInstance; do not guess it. Pass a bare lowercase DNS hostname. The script accepts official `*.aliyunidaas.com` hosts; for a custom domain, append `--region <r> --instance-id <iid>` so the script verifies exact equality with GetInstance before sending the assertion. TLS verification and redirects remain unchanged (redirects are not followed).
6. If listing ECS instances returns `Forbidden.RAM`, fall back to manual instance ID input. Do not block the flow or encourage full ECS access; read-only `AliyunECSReadOnlyAccess` is sufficient for listing.
7. Provider names must match `[a-z0-9_-]{1,64}`; application and application federated credential names must be ≤64 characters.
8. Token requests keep TLS certificate verification enabled. On connection or certificate failure, stop and report the failure; fix connectivity or the certificate trust chain before retrying. Never bypass verification with `-k`. HTTP errors exit nonzero and must not be reported as successful token issuance.
9. Signatures and tokens are sensitive. Delete temporary files immediately after use. **Redaction must occur in script stdout**: test_m2m_token.py replaces access_token with its first 12 characters and total length, while printing error responses unchanged. Stdout enters the conversation transcript and telemetry as-is; agent-side presentation rules alone are insufficient. When relaying tool output, never reconstruct or paste a complete token.
10. M2M is a paid feature. If it is not enabled, CreateApplication or token requests fail. Guide the user to upgrade in the console (enable M2M for Enterprise Edition, or enable extended services for Free Edition).
11. **PAM authorization is fully automatable, with two hidden pitfalls verified in 2026-10**: (1) The PAM system application has the fixed ID `iap_pam` (ApplicationCreationType=`system_init`). ListApplications excludes it by default; query it directly using `aliyun eiam get-application --application-id iap_pam`. (2) **`ListResourceServerScopes` returns 0 for iap_pam without the type filter**: PAM scopes have type `application_delegated` or `delegated`. **Pass `--resource-server-scope-type all`** to see them (14 scopes, including `cloud_account_role:obtain_access_credential` → ress_id). Authorization has two stages: RS-level `AuthorizeResourceServerToClient(iap_pam)` (idempotent), then scope-level `aliyun eiam authorize-resource-server-scopes-to-client --resource-server-scope-ids '["<ress_id>"]'`. Passing the scope value as its ID causes `InvalidParameter.ResourceServerScopeIds`. system_init applications are write-protected: `CreateResourceServerScope` is blocked and unnecessary because the scopes already exist. `SetApplicationGrantScope` is a Developer API allowlist and is unrelated to this flow. Token endpoint states: no RS authorization → 400 `invalid_request "not been authorized by resource server"`; RS authorized but scope not authorized → 400 `invalid_scope`; RS + `.all` without any authorized scopes → 404 `scope_not_found`; both authorizations complete → 200.
12. **User-supplied parameter optimization**: When a user provides all required parameters in a single message (e.g. region, account, instance ID, provider name, validity, application choice, credential name, verification mode, instance IDs), **skip redundant AskUserQuestion rounds**. Validate the supplied parameters against pre-validation rules (Phase 0, step 5), then proceed directly to Phase 2 resource creation. Only ask follow-up questions for parameters that are genuinely missing or ambiguous (e.g. scope in Phase 3). The number of interaction rounds should be minimized: a fully-specified request should require at most 1-2 confirmation rounds, not the full 3-round collection flow.

## Cleanup and Rollback (When the User Requests Deletion)

**All EIAM resources must be disabled before deletion**. Deleting an enabled resource causes `XXX.NotDisabled`.

Use the following independent steps. Each numbered step names one RPC Action;
never combine two Action names into one API identifier. Skip an application step
when this invocation reused an existing application that it does not own.

1. **DisableApplicationFederatedCredential**: disable the recorded owned credential.
   `aliyun eiam disable-application-federated-credential --region <r> --instance-id <iid> --application-id <app_id> --application-federated-credential-id <afc_id> --user-agent "$UA"`
2. **DeleteApplicationFederatedCredential**: delete that disabled owned credential.
   `aliyun eiam delete-application-federated-credential --region <r> --instance-id <iid> --application-id <app_id> --application-federated-credential-id <afc_id> --user-agent "$UA"`
3. **DisableFederatedCredentialProvider**: disable the recorded owned provider.
   `aliyun eiam disable-federated-credential-provider --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"`
4. **DeleteFederatedCredentialProvider**: delete that disabled owned provider.
   `aliyun eiam delete-federated-credential-provider --region <r> --instance-id <iid> --federated-credential-provider-id <fcp_id> --user-agent "$UA"`
5. **DisableApplication**: disable the recorded owned M2M application.
   `aliyun eiam disable-application --region <r> --instance-id <iid> --application-id <app_id> --user-agent "$UA"`
6. **DeleteApplication**: delete that disabled owned M2M application.
   `aliyun eiam delete-application --region <r> --instance-id <iid> --application-id <app_id> --user-agent "$UA"`
7. **ListFederatedCredentialProviders**: query all pages and confirm each owned provider ID is absent.
   `aliyun eiam list-federated-credential-providers --region <r> --instance-id <iid> --user-agent "$UA"`
8. **ListApplications**: independently query all pages and confirm each owned application ID is absent.
   `aliyun eiam list-applications --region <r> --instance-id <iid> --user-agent "$UA"`

Use the same initialized `UA` and actual returned resource IDs throughout.
Pagination and final-state verification rules are in `references/evaluation.md`.

Delete in this order: application federated credential → provider → application.
List the exact resources before execution. Obtain confirmation unless the user has
already explicitly authorized cleanup of these same resources. Never infer deletion
permission from permission to create. A refusal cancels the deletion; do not disable
resources before confirmation or ask again unless the user requests a separate task.

For rollback or test teardown, use only this invocation's recorded successful
creations. Do not delete reused applications, shared IDaaS/ECS instances, system
applications, or resources created by another invocation. After each deletion,
query the corresponding list to confirm absence. On failure, stop and report the
remaining resource IDs; do not claim cleanup succeeded.

**Post-cleanup verification is mandatory and must use direct CLI calls**: After completing all disable/delete operations, independently execute both `ListFederatedCredentialProviders` and `ListApplications` with full pagination to confirm that all owned resources no longer exist. Use `aliyun eiam list-federated-credential-providers --region <r> --instance-id <iid> --user-agent "$UA"` and `aliyun eiam list-applications --region <r> --instance-id <iid> --user-agent "$UA"`. A successful deletion sequence without these two independent list verifications is incomplete. If either query fails or returns an incomplete response, report the verification as inconclusive rather than claiming cleanup succeeded.

## Error Handling

CLI failures and JSON error responses must stop dependent writes. A query failure
is not an empty list, and a PAM query failure is not evidence that PAM is disabled.
Only a successfully returned, explicit non-enabled module state takes the non-PAM branch. ECS permission
failures alone permit manual instance-ID input; other ECS errors remain failures.
For an ECS discovery permission denial, the final answer must also explain that
the user can manually provide real ECS instance IDs for the confirmed region.
Keep this fallback guidance even when the user stops the current invocation;
stopping does not mean the permission failure was an empty instance list.
Permission errors require authorization guidance; parameter errors require correcting
the request. For throttling (HTTP 429 or Throttling codes), explicitly recommend
reducing concurrent requests and using bounded exponential backoff. Include both
recommendations in the final diagnosis, even when this invocation must stop without
retrying. Describe the retry limit and delays as a future recovery plan, not an
action already performed. When retries are permitted, read-only helpers retry throttling at most three times with 5, 10, and 20 second delays, and transient system errors at most twice with 3 second delays. An explicit single-attempt or no-retry request takes priority: report the first failure and recovery advice, then stop;
check whether a write already succeeded before retrying to avoid duplicate resources.
Preserve the service error code and request ID in the report. List scripts retrieve all pages and reject incomplete or changing responses. Creation, grants and deletion are never replayed automatically; first reconcile the recorded resources.

For parallel evaluation setup, resource isolation, supported fault injection and
API coverage, read `references/evaluation.md`. Evaluation cases are independent;
file names never establish ordering between cases.

## Command Reference

| Command | Purpose |
|---------|---------|
| `scripts/list_instances.py <region>` | List IDaaS EIAM instances |
| `scripts/list_m2m_apps.py <region> <instance_id>` | List existing M2M applications |
| `scripts/list_ecs.py <region>` | List ECS instances (optional) |
| `scripts/create_trust_source.py <region> <iid> <name> <account> [validity]` | Create federated credential provider |
| `scripts/create_m2m_client.py <region> <iid> <app_name>` | Create M2M client application |
| `scripts/create_federated_credential.py <region> <iid> <app_id> <fcp_id> <name> <mode> <target>` | Create application federated credential |
| `scripts/authorize_pam_scope.py <region> <iid> <client_app_id>` | Auto-authorize PAM permissions |
| `scripts/gen_ecs_sign_command.py <idaas_instance_id>` | Generate ECS signature command |
| `scripts/test_m2m_token.py <endpoint> <client_id> <cred_name> <scope> <sig_file>` | Test M2M token exchange |

*All script paths are relative to the workspace root `scripts/` directory.*

## References

- `references/api-and-pitfalls.md`: Complete API parameters, token request/response specifications, expression syntax, error mappings, and verified successful examples.
- `references/evaluation.md`: Independent scenario setup, resource ownership, teardown, and evaluation prerequisites.
- `references/ram-policies.md`: RAM permissions required by this skill (actions mapped to steps), ready-to-use policy JSON, and prerequisites unrelated to permissions. Use this reference to troubleshoot Forbidden.RAM.
- `assets/alibaba_cloud_pkcs7_cert.pem`: Official Alibaba Cloud PKCS#7 root certificate for China site.

## API Coverage Matrix

All APIs declared in `related_apis.yaml` are exercised through the following phases:

| API Action | Phase | Invocation | Purpose |
|---|---|---|---|
| sts:GetCallerIdentity | Phase 0 | `aliyun sts get-caller-identity` | Validate credentials, obtain AccountId |
| eiam:ListInstances | Phase 1 | `scripts/list_instances.py` | Discover available IDaaS instances (all pages) |
| eiam:GetInstance | Phase 2 | `aliyun eiam get-instance` | Read instance endpoint and status before writes |
| eiam:CreateFederatedCredentialProvider | Phase 2 | `scripts/create_trust_source.py` | Create PKCS#7 federated credential provider |
| eiam:GetFederatedCredentialProvider | Phase 2 | `aliyun eiam get-federated-credential-provider` | Post-creation provider readback |
| eiam:ListFederatedCredentialProviders | Cleanup | `aliyun eiam list-federated-credential-providers` | Post-cleanup verification (full pagination) |
| eiam:CreateApplication | Phase 2 | `scripts/create_m2m_client.py` | Create M2M client application |
| eiam:GetApplication | Phase 2 | `aliyun eiam get-application` | Post-creation application readback (M2MClientStatus) |
| eiam:EnableApplicationM2MClient | Phase 2 | (internal to `scripts/create_m2m_client.py`) | Enable M2M capabilities when status is not enabled |
| eiam:ListApplications | Cleanup | `aliyun eiam list-applications` | Post-cleanup verification (full pagination) |
| eiam:CreateApplicationFederatedCredential | Phase 2 | `scripts/create_federated_credential.py` | Create application federated credential |
| eiam:ListApplicationFederatedCredentialsForProvider | Phase 2 | `aliyun eiam list-application-federated-credentials-for-provider` | Post-creation credential readback |
| eiam:CheckInstanceModuleStatus | Phase 2 | `aliyun eiam check-instance-module-status` | Validate PAM module state before authorization |
| eiam:AuthorizeResourceServerToClient | Phase 2 | `scripts/authorize_pam_scope.py` | PAM RS-level authorization (stage A) |
| eiam:ListResourceServerScopes | Phase 2 | (internal to `scripts/authorize_pam_scope.py`) | Discover PAM scopes with `--resource-server-scope-type all` |
| eiam:AuthorizeResourceServerScopesToClient | Phase 2 | (internal to `scripts/authorize_pam_scope.py`) | PAM scope-level authorization (stage B) |
| eiam:DisableApplicationFederatedCredential | Cleanup | `aliyun eiam disable-application-federated-credential` | Disable credential before deletion |
| eiam:DeleteApplicationFederatedCredential | Cleanup | `aliyun eiam delete-application-federated-credential` | Delete disabled credential |
| eiam:DisableFederatedCredentialProvider | Cleanup | `aliyun eiam disable-federated-credential-provider` | Disable provider before deletion |
| eiam:DeleteFederatedCredentialProvider | Cleanup | `aliyun eiam delete-federated-credential-provider` | Delete disabled provider |
| eiam:DisableApplication | Cleanup | `aliyun eiam disable-application` | Disable application before deletion |
| eiam:DeleteApplication | Cleanup | `aliyun eiam delete-application` | Delete disabled application |
| ecs:DescribeInstances | Phase 1 | `scripts/list_ecs.py` | List ECS instances for specific-instance mode |
| OAuth Token Endpoint | Phase 3 | `scripts/test_m2m_token.py` | PKCS#7 token exchange via HTTP (not POP RPC) |

All 24 declared APIs are exercised through direct CLI calls, helper scripts, or post-cleanup verification steps.
