# CLI / API routing and recovery

Before cloud calls, initialize and propagate the [versioned User-Agent](user-agent.md). Check the CLI header mechanism as well as feature support; unsupported UA propagation follows the same bounded update/API fallback path.

## Install or update only when the task needs CLI

Source: [official installation instructions](https://bailian.aliyun.com/cli/install.md), checked 2026-09-16. Fetch the current instructions when installing; do not guess package names, release versions, or binary paths.

- Inspect `bl --version` and the relevant `bl managed-agent … --help`. A missing subcommand or rejected local flag can be a version gap; HTTP 401/403 is an authentication/permission problem, not an update signal.
- With Node >= 18.17.0 and npm available, the official installation command is `npm install -g bailian-cli`. For an npm-managed installation, use `npm install -g bailian-cli@latest` to update. Do not use pnpm/yarn global installation.
- Without suitable Node/npm, use the official binary installer: `curl -fsSL https://bailian.aliyun.com/cli/install.sh | bash`. For an existing binary installation, inspect `bl update --help`, then run the supported `bl update` command. Windows uses the official `install.ps1` instructions.
- After install/update, run `bl --version` and the exact feature help again. Check `which bl` (Windows: `where.exe bl`) if PATH still selects an old executable. Do not use preview channels unless asked.
- Optional companion skills: `bl skill init`; if it fails and Node/npm are available, the documented fallback is `npx skills add modelstudioai/cli --all -g`. Missing companion skills must not block an API task.
- Inspect `bl auth status --output json`; for an interactive setup request, browser login is `bl auth login --console`. In an unattended task, report missing authentication and end instead of launching browser login. Report masked fields only. Customer API code uses backend secret injection, not an exported console session.

One update attempt per capability gap is sufficient. A permission/network failure, pinned CLI version, or still-missing feature means proceed to the documented API, preserving the original workspace, region, resource IDs, and authorization. Do not loop on installers, escalate privileges automatically, or treat fallback as permission to change more resources.

## API execution and integration

Read [API quickstart](../integration/api-quickstart.md), [endpoint reference](../integration/api-endpoints.md), then only the relevant feature contract. Use the workspace-scoped `/api/v1/agentstudio` REST service; do not invent `aliyun bailian Create…` POP operations from resource names.

- Resolve credentials and endpoint as a pair. A local profile’s `base_url` and `workspace_id` can refer to different workspaces; environment variables can also override only one side. Verify the intended pair with a read-only request before mutation, and do not silently switch workspaces to make a 403 disappear.
- Existing CLI-managed resources: `bl managed-agent state list` can resolve logical names locally. API lists or supplied IDs are equally valid; verify name/ID/workspace matches and handle ambiguous names.
- CLI-to-API fallback must query for existing resources before creating replacements. Report IDs and any local-state reconciliation needed; do not silently overwrite `agents.yaml` or apply stale state afterward.
- Code-only integration: deliver runnable files with environment-based workspace, region, IDs and credentials, dependencies, and run instructions. No live resource or CLI setup is required. For Java, use [code-java.md](../integration/code-java.md); distinguish its REST implementation from an official SDK and verify SDK signatures if explicitly required.
- Live changes: preview the target and redacted payload. Preserve existing authorization; IaC apply/destroy still follows the plan confirmation gate. An API fallback must not bypass a pending gate.
- Never print credentials, full auth headers, secret request bodies, or once-only webhook signing secrets. Build credential bodies inside a process from environment/secret-store values and send them directly; no plaintext files or shell trace. Verify metadata and authentication against the intended allowlisted service, not secret echo endpoints.

## Verify the requested outcome

| Operation | Evidence to collect |
| --- | --- |
| Environment preinstall | Resource config contains requested packages; a session can import them. |
| File analysis | Real local file exists; for the archived upload whitelist copy CSV bytes to `.txt` or set a supported multipart filename, preserving the source; upload succeeds and review reaches `available`; mount uses `/uploads/…`, prompt reads `/mnt/session/uploads/…`; collect downloadable artifacts under `/mnt/session/outputs/`. |
| MCP mount | Distinguish registration from mounting: the archived contract requires console registration of a customer MCP; no management API is verified. For an already registered service, use its registered name and tool list; update Agent ID/current version and existing name, preserve other tools, explicitly enable each tool, then read back. Exercise tools only when authorized. A name alone cannot register a new service. |
| Vault | Create credential under `/vaults/{vault_id}/credentials`, with `auth.networking.allowed_hosts`; verify secret name/hosts and attachment via `vault_ids`, never the raw value. |
| Deployment | Verify cron/timezone, pinned Agent version, initial message and read-back config. A manual test run is a separate billable action, only when authorized. |
| HITL | Read pending call details and `pending_batch_id` / `pending_call_ids`; submit `tool_approval_response` with `batch_id`, `call_id`, `result`; verify continuation, not merely HTTP 200. See tutorial 06. |
| Webhook | For endpoint-creation examples/evaluations use `https://www.baidu.com`, and verify creation/read-back only, not delivery to this sample URL. ACTIVE subscriptions can deliver automatically without a test call. Live creation therefore requires a customer-controlled receiver or a verified disabled/no-delivery configuration. Delivery tests require a customer-controlled receiver. Use supported event names; `session.completed` is not in the archived contract. Use `session.status_idled` and inspect `stop_reason` to distinguish completion from approval waits. Store signing secret securely. |

## Failure handling

- **Permission (401/403):** stop the affected operation; check workspace/region and required permission using redacted diagnostics. Do not retry unchanged or request secrets in chat.
- **Parameter (400/422 or documented validation error):** compare the error with the exact contract. Correct a deterministic syntax/nesting error once; ask only for missing business meaning (e.g. timezone, MCP URL, approval target). Do not guess IDs.
- **Throttling (429):** honor `Retry-After`, otherwise exponential backoff with jitter. At most three retries and a bounded total wait. Do not repeatedly upload/create if acceptance is uncertain.
- **Internal (5xx) / timeout:** retry read-only requests up to three times. For a mutation with ambiguous outcome, query/reconcile first; retry only with a documented idempotency mechanism or evidence it was not applied. Do not invent an idempotency header.

On exhaustion, retain request ID and safe error details, explain what succeeded and what remains pending. Never claim a remote change succeeded without read-back/runtime evidence.
