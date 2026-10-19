---
name: alibabacloud-wuying-console
description: Query and manage Alibaba Cloud WUYING resources from a local agent through the official Aliyun CLI product plugins. Use for cloud computers, cloud browsers, application delivery groups, office sites, users, policies, images, terminals, sessions, reports, and local WUYING CLI setup or troubleshooting. Also use for OAuth management command discovery, API version selection, and required-parameter lookup for 无影控制台、云电脑、云浏览器、应用交付组. Do not use for browser-only console navigation or unrelated Alibaba Cloud products.
---

# Alibaba Cloud WUYING Console

Operate WUYING through the official `aliyun` CLI and configured official WUYING product plugins. Treat each plugin's live command schema as authoritative. This skill adds cross-product discovery, safety, and agent-friendly execution rules without forking Aliyun CLI or maintaining a scenario-to-Action map.

This Skill supports only Aliyun CLI OAuth profiles and OAuth-compatible control-plane APIs. Client-session APIs and credentials are out of scope.

"Execute real calls" or "never simulate/mock" does not authorize an authentication
bypass. If OAuth preflight denies a request, executing that real check and
reporting `request_sent: false` is the correct grounded outcome, not a simulated
cloud result. Do not turn task urgency into permission to use STS/AK, direct CLI,
SDK or HTTP calls after denial.

## First decision: scope and safety

Classify the user's intent before environment remediation, installation, or
resource discovery. For any state-changing request, read
[safety.md](references/safety.md) first. An unresolved wildcard or account-wide
destructive request must stop with an explicit refusal to bypass confirmation;
do not upgrade/install software, log in, or enumerate resources to advance it.
Offer a separately scoped read-only inventory instead, without executing it.
For other tasks, authorization to operate on cloud resources is not authorization
to install software or change authentication. Obtain specific authorization for
each required environment change before performing it.

## Execution prerequisites

Before any business API request, require a compatible official plugin and a valid
OAuth profile from the environment check. `blocked` and `needs_auth` are execution
gates, not warnings. A valid AccessKey or StsToken profile does not satisfy the
OAuth requirement; never fall back to it. Software installation authorization is
separate from cloud-operation authorization. A request to skip confirmation does
not authorize unresolved, wildcard, or account-wide destructive targets.

For cloud tasks, proceed only when `checks.valid_oauth_profile` is the literal
boolean `true` and the requested product is in `checks.ready_products`. Missing,
false, or `"not_checked"` authentication evidence blocks every business request,
including reads. After any authorized install or upgrade, rerun the environment
check and apply both gates again; plugin readiness alone is not authentication.
If remediation is not explicitly authorized, report the blocker and ask only for
that authorization. A request to query or change a resource is not permission to
install software. The local-only exception applies to a task whose goal is local
metadata/maintenance, not to continuing a blocked cloud query by relabeling its
preparation as local-only work.

Every business request must use `scripts/run_wuying.py` as the execution entry
point. It rechecks the active OAuth profile, official plugin readiness, and the
explicit allowed API version before delegating unchanged arguments to the
official CLI. Never bypass a blocked result by running the command directly,
switching credentials, or editing the gate. Local help/discovery does not use
this entry point. It does not grant mutation approval or replace the safety gate.

The configured product scope is `ecd`, `appstream-center`, `eds-user`, `wyota`, and `wss`. A product is executable only when its official plugin is installed and reported as ready by the environment check.

## Prerequisites

| Dependency | Minimum | Purpose |
|---|---:|---|
| Python | 3.10 | Run the bundled environment, catalog, and search helpers |
| Aliyun CLI | 3.5.0 | Authenticate and execute official product-plugin commands |
| Official WUYING plugins | See [products.json](references/products.json) | Provide the live OpenAPI command schemas |

The bundled scripts use only the Python standard library. They have no third-party
package dependency; see [scripts/requirements.txt](scripts/requirements.txt).

## Observability

At the start of one user workflow, generate one cryptographically random
32-character lowercase hexadecimal session ID, load the published Skill version
from the manifest, and reuse both values for every cloud API command in that
workflow:

```bash
export SKILL_SESSION_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
export SKILL_VERSION="$(python3 -c 'import json; print(json.load(open("references/manifest.json"))["version"])')"
```

Do not regenerate the session ID between discovery, execution, verification,
retries, or follow-up questions in the same workflow. Every `aliyun` command
that calls a WUYING cloud API MUST include:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-wuying-console/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"
```

Local utility and metadata commands such as `aliyun version`, `aliyun configure`,
`aliyun plugin`, `aliyun ... --help`, and `aliyun ... --help-all` do not call a
business API and do not require this flag.

## Start Every Task

1. Apply the scope/safety decision above, then create and retain `SKILL_SESSION_ID` as described in Observability for an eligible workflow.
2. Run `python3 scripts/check_environment.py` from this skill directory.
3. If Aliyun CLI is missing or older than 3.5.0, stop and request authorization before installing or upgrading it. Use an official CLI installation path such as `brew install aliyun-cli` on macOS. For an existing installation, use `aliyun upgrade`, then rerun the environment check.
4. If the result is `blocked`, stop cloud execution and follow the returned remediation. Do not install software, start OAuth login, or change profiles without user authorization. For a task limited to local inspection, command discovery, or catalog maintenance, continue only those local steps whose dependencies are actually available; the local-only rules below apply.
5. If the result is `partial`, continue only when the requested operation belongs to a product in `ready_products`. If it requires an `unavailable_products` entry, explain which official plugin is missing and request authorization before installing it.
6. If `updates_available` is non-empty, tell the user which installed plugins have newer stable versions. Do not update automatically. A compatible installed version may continue to run unless the requested command is absent or the user authorizes the update.
7. If the result is `needs_auth`, explain that OAuth authentication is missing and follow [authentication.md](references/authentication.md). Do not call any business API. Authentication is not required for local metadata inspection; this does not authorize a login or an authentication-mode change.
8. Convert the business intent into a short English search phrase and search the generated catalog:

   ```bash
   python3 scripts/search_command_catalog.py "<business keywords>"
   ```

   The catalog mirrors every command exposed by the configured plugin versions; it is not a hand-maintained scenario map or API allowlist. Search again with alternative business terms when the first result is weak.
9. Before composing arguments, inspect the live schema for the chosen command:

   ```bash
   aliyun <product> <command> --api-version <version> --help
   ```

10. Use the product and `preferred_api_version` listed for that command in the catalog. The catalog contains only OAuth-compatible versions. Always pass `--api-version` explicitly because plugin defaults can expose a different command set.

## Orchestration Logic

This is a schema-driven workflow, not a list of hard-coded console scenarios:

1. **Triage, then prepare**: reject unresolved destructive scope first; only then verify CLI, authentication, plugin availability, and updates.
2. **Discover**: search the generated cross-product command catalog.
3. **Resolve**: inspect live help and query authoritative resources for required IDs.
4. **Gate**: classify risk and obtain confirmation for mutations or destructive actions.
5. **Execute**: delegate the smallest matching OpenAPI command through `scripts/run_wuying.py` with explicit API version,
   `--cli-ai-mode`, and the workflow User-Agent.
6. **Verify**: inspect the response and, after mutations, query the resulting state.

If product/API existence, resource identity, or permission cannot be established,
stop and return a focused remediation; do not fall through to another product.
For unresolved routing or parameter constraints, first gather evidence and use
the bounded exploration rules below when eligible instead of stopping immediately.

### Local-only discovery and catalog maintenance

CLI help, bundled catalog search, and catalog generation do not require OAuth
credentials. An authentication gate blocks cloud execution, not these local
operations. A missing binary or plugin still prevents its live help: obtain
specific installation authorization or report that gap. Never describe a bundled
catalog snapshot as live-help verification or invent unavailable parameter schemas.

When the user asks for command syntax, API versions, or parameter templates,
include the requested commands, versions, and verified required parameters in
the final answer itself, not only in a saved report or a list of artifact paths.
If single-line templates were requested, show each complete template on one
line. Label templates as unexecuted; distinguish live-help facts from unresolved
gaps and never replace missing required parameters with guessed values.

Treat `missing_products` as a coverage boundary, not evidence that another
product implements the missing capability. Similar keywords do not establish
equivalent resource types or contracts. When the requested capability depends
on unavailable metadata, either obtain specific authorization to install the
official plugin and verify live help, or state the product's exact missing
dependency and the unverified commands/parameters in the final answer itself.
Do not present another product's keyword matches as the answer without verifying
that its documented resource type and operation match the request.

Use the bundled generator, not a replacement script that synthesizes commands.
When all configured plugins are missing, `--allow-missing` may produce an empty,
explicitly incomplete catalog with every missing product recorded. Zero generated
commands means no installed metadata, not no supported APIs or no cloud resources.
If output files must stay outside the installed Skill, use generator `--output`
and search `--catalog` with the same output path. Report `catalog_complete`,
`missing_products`, versions, and command counts from the actual generator result.

## Resolve the Operation

- Match the user's intent to catalog commands using the official command name and description across all configured products. Do not maintain or infer a fixed user-phrase-to-Action mapping.
- Inspect live help for the strongest candidates when names or descriptions are similar. Compare required parameters and response meaning before choosing. For unresolved contract constraints, gather evidence and use bounded exploration below when eligible; ask a focused question only when user intent or preference is genuinely missing, not as a substitute for available checks.
- Use the catalog's `preferred_api_version`, which is the latest OAuth-compatible version for the exact command. Never select a newer version excluded by the product's `oauth_api_versions` configuration.
- Read live help immediately before execution because plugin upgrades can change parameters after this catalog was generated.
- Use exact parameter names and types from live help. Do not invent parameters from console labels or memory.
- This Skill does not support client-session contracts. Never ask the user for `client-id`, `login-token`, or `session-id`, and never place those values in a command template. If an operation has no OAuth-compatible catalog entry, report that the operation is unsupported by this Skill and stop.
- Never guess `RegionId`, resource IDs, account IDs, names, or selection order. Query authoritative resources first, present ambiguous matches, and validate the chosen ID against the query result.
- Add `--cli-ai-mode` and the required workflow `--user-agent` to every cloud API
  execution command so the CLI records agent-mode usage and the calls are
  correlated under one Skill session.
- Parse the default JSON API response. Do not pass `--output json`: in Aliyun CLI 3.5.0, `--output` configures table columns rather than selecting JSON. Add `--cli-output json` when machine-readable local CLI errors are needed.
- Paginate when the API indicates more results. Do not report the first page as the full result.

### Verify the official API contract before execution

Before the first business API call for each exact Product + API Version + Action
in a workflow, read its official documentation in [OpenAPI Explorer](https://api.aliyun.com/)
or [Alibaba Cloud Help Center](https://help.aliyun.com/). Use the API Action from
live CLI help to find the matching page; do not substitute another version or a
similarly named API. Reuse the checked contract for pagination and repeated calls
in that workflow unless the version, plugin, or relevant evidence changes.

Check the documented endpoint/region requirements, fixed values, allowed values,
parameter dependencies, and usage limits against live CLI help and official
metadata. Apply explicit requirements, not just example values. Keep the source
link and relevant constraint in workflow context. If documentation is unavailable
or sources conflict, seek additional official metadata or relevant console-source
evidence, then use bounded exploration below when eligible. Respect the documented
compatibility exceptions; do not immediately pause solely because a constraint
is unclear, and do not probe alternative values with real mutations.

Keep CLI routing/signing region (`--region`) separate from business parameters
such as `RegionId` and `ResourceRegionId`. If an API requires a fixed routing
region, pass it explicitly instead of inheriting the profile's default. When
`RegionId` is also exposed as a business parameter, use its exact flag from live
help and satisfy that constraint too. Resource-region fields must retain the
authoritatively queried target region; never rewrite them to match the endpoint.

Verified narrow rule for `ecd/2020-09-30`:
[CreateCenterPolicy](https://help.aliyun.com/zh/wuying-workspace/developer-reference/api-ecd-2020-09-30-createcenterpolicy),
[ModifyCenterPolicy](https://help.aliyun.com/zh/wuying-workspace/developer-reference/api-ecd-2020-09-30-modifycenterpolicy),
and [CloneCenterPolicy](https://help.aliyun.com/zh/wuying-workspace/developer-reference/api-ecd-2020-09-30-clonecenterpolicy)
explicitly require `RegionId=cn-shanghai`; route these calls to Shanghai and pass
the documented business value. Do not extend this rule to every Action containing
`CenterPolicy`: verify each contract independently.

Skill routing exception for `ecd/2021-06-02` `ListSecureSkillIdentities`:
explicitly pass `--region cn-shanghai` for mainland China calls, regardless of
the profile's default region or the desktops' resource regions. Keep the Action
as `list-secure-skill-identities`; do not substitute `ListSecureSkillDesktops`.
This is a routing/signing-region constraint only. The current command schema
does not expose a business `RegionId` parameter, so do not invent a
`--biz-region-id` argument. Read the remaining parameters from live CLI help.

### Bounded exploration for unresolved constraints

- Probe only an API already verified as read-only, within the user's authorized
  account, region scope, and resource type. A read-like Action name alone does not
  prove safety. Unknown-risk operations are not eligible.
- Derive each candidate region or parameter value from official documentation,
  metadata, or relevant console implementation. Explain the hypothesis and its
  source; do not invent identifiers, bypass schema validation, or override an
  explicit fixed value. A routing-region probe must not rewrite resource-region
  fields or expand the requested resource scope.
- Allow at most three exploratory API requests for the same Product + Version +
  Action and unresolved constraint in one workflow. Each request must test a
  distinct evidence-backed hypothesis; do not reset the budget by rephrasing.
  Normal pagination after establishing the contract is not an exploratory request.
- Retain candidate arguments, evidence, outcome, error code, and `RequestId`
  when returned, with secrets redacted. A successful empty response does not
  establish that the account has no resources when routing or filters remain
  uncertain. State which scope was actually checked.
- For mutations or destructive operations, investigate with authoritative reads,
  local `--cli-dry-run`, or an explicitly documented server-side no-side-effect
  validation mode. Local dry run proves request construction only, not server
  acceptance. Never try candidate values by submitting real changes; execute
  only after resolving the contract and passing the existing confirmation gate.
- Stop exploration on authentication/authorization failures or safety boundaries;
  do not change profiles or seek an access bypass. If no supported candidate
  remains, the three-request budget is exhausted, or the next step could make an
  uncertain change, report the evidence and unresolved constraint without claiming
  success. Continue independently resolvable parts of the task when safe.

### ModifyUserEntitlement compatibility exception

For `ecd modify-user-entitlement --api-version 2020-09-30`, use a non-empty
`EndUserId` list and exactly one non-empty operation list: `AuthorizeDesktopId`
for grants or `RevokeDesktopId` for revocations. Omit the other list; do not add
empty or unrelated IDs to satisfy help that marks both lists as required.

Observed behavior in defect 87702715: a request containing both lists returned
success while leaving the requested revocation unapplied. Treat combined calls
as unsupported by this Skill. If the CLI rejects a single-operation request,
stop and report the schema incompatibility rather than combining operations.

When the user requests both grants and revocations, present two separate steps
with their exact users, desktops, and execution order for confirmation. These
calls are not atomic. Execute and verify each step against authoritative desktop
authorization data before proceeding. If a step fails or its effect cannot be
verified, stop and report completed, failed, and unverified changes separately;
do not claim overall success or automatically roll back.

## Apply the Safety Gate

Read [safety.md](references/safety.md) before any non-read operation.

- `read`: execute when required parameters are known.
- `mutation`: show the exact command intent, region, targets, and important changes; obtain explicit user confirmation immediately before execution.
- `destructive`: explain irreversible or disruptive effects and obtain explicit confirmation immediately before execution. Do not broaden the target set.
- Treat unknown or newly added command patterns as `mutation` until their live help proves they are read-only.
- Use `--cli-dry-run` to validate a prepared request when useful. A successful dry run is not evidence that the server-side operation succeeded.
- Never add `--yes` before the user has confirmed. Never use it to bypass an approval boundary.
- For an unresolved wildcard or account-wide destructive request, explicitly reject bypassing confirmation before planning execution. Do not install software or submit cloud mutations to advance it. A general "do everything" or "do not ask" instruction is not confirmation of an exact target set.

## Execute and Report

1. Run the smallest command that satisfies the request.
   A business API command must follow this shape:

   ```bash
   python3 scripts/run_wuying.py -- aliyun <product> <command> \
     --api-version <version> \
     <command-parameters> \
     --cli-ai-mode \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-wuying-console/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"
   ```
   The wrapper returns `request_sent: false` when OAuth/plugin/version preflight
   fails. Treat that as terminal for this request, not as permission to invoke
   bare `aliyun` or reconfigure credentials. Command templates may show the
   underlying official CLI syntax, but actual business execution uses the wrapper.
2. Inspect the process exit status and the API response. A zero exit from request preparation alone is not an API success.
3. For mutations, query the affected resource afterward when a read API exists and report the observed state separately from the accepted request.
4. Base summaries only on returned fields. Do not infer region, status, resource type, or ownership from an ID.
5. Make the final answer self-contained even after a follow-up closes the task.
   Retain the requested findings, scope, blockers and execution/non-execution
   status from earlier turns; do not replace them with an acknowledgement or
   artifact paths alone. For an environment-wide check, name every configured
   product and its observed readiness, plus the authentication and update-check
   outcomes. Distinguish missing plugins from up-to-date installed plugins.
   For a verification request, the final answer must pair the user's expected
   values with actual observations (or explicitly unknown/unverified values),
   identify the target and scope, and state the comparison verdict. A blocked
   workflow still needs this expectation-versus-observation summary; do not put
   it only in an artifact or replace it with setup instructions.
6. On failure, preserve the error code and `RequestId`, redact secrets, and follow [troubleshooting.md](references/troubleshooting.md). Do not repeatedly retry a mutation unless the API documents idempotency or the resulting state has been checked.

## Maintain the Catalog

The configured product scope is maintained in [products.json](references/products.json). Adding a product changes discovery scope; it does not add scenario-specific routing rules.

The environment check queries the official stable plugin index with `aliyun plugin list-remote`. It reports newer versions in `updates_available` and remediation but never upgrades automatically. If the remote index is unavailable, update status is reported as unavailable without blocking compatible installed plugins. Use `--skip-update-check` only for an intentional offline check.

Regenerate the catalog after upgrading Aliyun CLI or any configured product plugin. The generator validates every plugin version but exposes only the versions listed in each product's `oauth_api_versions` configuration:

```bash
python3 scripts/generate_command_catalog.py
```

Use `--allow-missing` only when intentionally producing a partial local catalog. The resulting catalog records missing configured products, so the Agent can distinguish “no matching command” from “the official product plugin is unavailable”.

Review the reported product versions and command counts, then validate the skill. The generator and search helper only read local CLI metadata and the generated catalog; they do not call business APIs.

For official metadata plugins, the generator reads the installed package's
`manifest.json` and `metadata.index.json` and verifies the indexed data file's
SHA256, product identity and API versions. This avoids Help-rendering differences
between CLI releases while retaining the plugin's exact command names. An invalid
package is an error, not permission to substitute traditional built-in APIs.
For older official binary plugins without JSON Help, the generator accepts their
actual command listing only after each listed API's local help confirms the
exact command path and requested API version. It records this source separately
as `cli_verified_text_help`; it never derives command names from PascalCase APIs.

## References

- Authentication and credential handling: [authentication.md](references/authentication.md)
- Least-privilege authorization guidance: [ram-policies.md](references/ram-policies.md)
- Execution and confirmation rules: [safety.md](references/safety.md)
- Errors and common compatibility issues: [troubleshooting.md](references/troubleshooting.md)
- Validated implementation baseline: [compatibility.md](references/compatibility.md)
