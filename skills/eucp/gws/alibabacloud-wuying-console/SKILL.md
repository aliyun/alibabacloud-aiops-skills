---
name: alibabacloud-wuying-console
description: Query and manage Alibaba Cloud WUYING resources from a local agent through the official Aliyun CLI product plugins. Use for cloud computers, cloud browsers, application delivery groups, office sites, users, policies, images, terminals, sessions, reports, and local WUYING CLI setup or troubleshooting. Do not use for browser-only console navigation or unrelated Alibaba Cloud products.
---

# Alibaba Cloud WUYING Console

Operate WUYING through the official `aliyun` CLI and configured official WUYING product plugins. Treat each plugin's live command schema as authoritative. This skill adds cross-product discovery, safety, and agent-friendly execution rules without forking Aliyun CLI or maintaining a scenario-to-Action map.

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

1. Create and retain `SKILL_SESSION_ID` as described in Observability.
2. Run `python3 scripts/check_environment.py` from this skill directory.
3. If Aliyun CLI is missing or older than 3.5.0, stop and request authorization before installing or upgrading it. Use an official CLI installation path such as `brew install aliyun-cli` on macOS. For an existing installation, use `aliyun upgrade`, then rerun the environment check.
4. If the result is `blocked`, stop and follow the returned remediation. Do not install software, start OAuth login, or change profiles without user authorization.
5. If the result is `partial`, continue only when the requested operation belongs to a product in `ready_products`. If it requires an `unavailable_products` entry, explain which official plugin is missing and request authorization before installing it.
6. If `updates_available` is non-empty, tell the user which installed plugins have newer stable versions. Do not update automatically. A compatible installed version may continue to run unless the requested command is absent or the user authorizes the update.
7. If the result is `needs_auth`, explain that local authentication is missing and follow [authentication.md](references/authentication.md).
8. Convert the business intent into a short English search phrase and search the generated catalog:

   ```bash
   python3 scripts/search_command_catalog.py "<business keywords>"
   ```

   The catalog mirrors every command exposed by the configured plugin versions; it is not a hand-maintained scenario map or API allowlist. Search again with alternative business terms when the first result is weak.
9. Before composing arguments, inspect the live schema for the chosen command:

   ```bash
   aliyun <product> <command> --api-version <version> --help
   ```

10. Use the product and version listed for that command in the catalog. Always pass `--api-version` explicitly because plugin defaults can expose a different command set.

## Orchestration Logic

This is a schema-driven workflow, not a list of hard-coded console scenarios:

1. **Prepare**: verify CLI, authentication, plugin availability, and updates.
2. **Discover**: search the generated cross-product command catalog.
3. **Resolve**: inspect live help and query authoritative resources for required IDs.
4. **Gate**: classify risk and obtain confirmation for mutations or destructive actions.
5. **Execute**: call the smallest matching OpenAPI command with explicit API version,
   `--cli-ai-mode`, and the workflow User-Agent.
6. **Verify**: inspect the response and, after mutations, query the resulting state.

If any stage cannot establish an authoritative product, command, parameter, target,
or permission, stop at that stage and return a focused remediation instead of
guessing or falling through to a different product.

## Resolve the Operation

- Match the user's intent to catalog commands using the official command name and description across all configured products. Do not maintain or infer a fixed user-phrase-to-Action mapping.
- Inspect live help for the strongest candidates when names or descriptions are similar. Compare required parameters and response meaning before choosing. If the official schemas still leave a material ambiguity, ask a focused question before acting.
- Prefer the latest API version listed for the exact command, unless the user requires an older contract.
- Read live help immediately before execution because plugin upgrades can change parameters after this catalog was generated.
- Use exact parameter names and types from live help. Do not invent parameters from console labels or memory.
- Never guess `RegionId`, resource IDs, account IDs, names, or selection order. Query authoritative resources first, present ambiguous matches, and validate the chosen ID against the query result.
- Add `--cli-ai-mode` and the required workflow `--user-agent` to every cloud API
  execution command so the CLI records agent-mode usage and the calls are
  correlated under one Skill session.
- Parse the default JSON API response. Do not pass `--output json`: in Aliyun CLI 3.5.0, `--output` configures table columns rather than selecting JSON. Add `--cli-output json` when machine-readable local CLI errors are needed.
- Paginate when the API indicates more results. Do not report the first page as the full result.

## Apply the Safety Gate

Read [safety.md](references/safety.md) before any non-read operation.

- `read`: execute when required parameters are known.
- `mutation`: show the exact command intent, region, targets, and important changes; obtain explicit user confirmation immediately before execution.
- `destructive`: explain irreversible or disruptive effects and obtain explicit confirmation immediately before execution. Do not broaden the target set.
- Treat unknown or newly added command patterns as `mutation` until their live help proves they are read-only.
- Use `--cli-dry-run` to validate a prepared request when useful. A successful dry run is not evidence that the server-side operation succeeded.
- Never add `--yes` before the user has confirmed. Never use it to bypass an approval boundary.

## Execute and Report

1. Run the smallest command that satisfies the request.
   A business API command must follow this shape:

   ```bash
   aliyun <product> <command> \
     --api-version <version> \
     <command-parameters> \
     --cli-ai-mode \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-wuying-console/${SKILL_SESSION_ID} skill-version/${SKILL_VERSION}"
   ```
2. Inspect the process exit status and the API response. A zero exit from request preparation alone is not an API success.
3. For mutations, query the affected resource afterward when a read API exists and report the observed state separately from the accepted request.
4. Base summaries only on returned fields. Do not infer region, status, resource type, or ownership from an ID.
5. On failure, preserve the error code and `RequestId`, redact secrets, and follow [troubleshooting.md](references/troubleshooting.md). Do not repeatedly retry a mutation unless the API documents idempotency or the resulting state has been checked.

## Maintain the Catalog

The configured product scope is maintained in [products.json](references/products.json). Adding a product changes discovery scope; it does not add scenario-specific routing rules.

The environment check queries the official stable plugin index with `aliyun plugin list-remote`. It reports newer versions in `updates_available` and remediation but never upgrades automatically. If the remote index is unavailable, update status is reported as unavailable without blocking compatible installed plugins. Use `--skip-update-check` only for an intentional offline check.

Regenerate the catalog after upgrading Aliyun CLI or any configured product plugin:

```bash
python3 scripts/generate_command_catalog.py
```

Use `--allow-missing` only when intentionally producing a partial local catalog. The resulting catalog records missing configured products, so the Agent can distinguish “no matching command” from “the official product plugin is unavailable”.

Review the reported product versions and command counts, then validate the skill. The generator and search helper only read local CLI metadata and the generated catalog; they do not call business APIs.

## References

- Authentication and credential handling: [authentication.md](references/authentication.md)
- Least-privilege authorization guidance: [ram-policies.md](references/ram-policies.md)
- Execution and confirmation rules: [safety.md](references/safety.md)
- Errors and common compatibility issues: [troubleshooting.md](references/troubleshooting.md)
- Validated implementation baseline: [compatibility.md](references/compatibility.md)
