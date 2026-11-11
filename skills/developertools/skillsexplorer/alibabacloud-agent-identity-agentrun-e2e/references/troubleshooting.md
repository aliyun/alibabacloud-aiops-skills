# Troubleshooting: Failure Signatures

Match the signature first. Inspect the full error and nested exceptions,
apply the appropriate fix, then retest.

## Inbound (Runtime endpoint)

| Signature | Root cause | Fix |
|---|---|---|
| `401 ERR_UNAUTHORIZED: Agent Identity enabled but no ID token provided` | Request lacks the OIDC ID Token | Add `Authorization: Bearer <id-token>` |
| `401 ID token validation failed` | Token validation failed | Check token expiration, issuer, audience, and the IdP discovery URL; obtain a new token |
| `404 {"detail":"Not Found"}` at `.../invocations` | Wrong path — the app serves OpenAI routes | Use `.../invocations/openai/v1/chat/completions` |
| `404 NOT_FOUND` (platform style) at `/openai/v1/...` directly under `endpoints/Default/` | Path misses the `/invocations` prefix | Full path: `endpoints/Default/invocations/openai/v1/chat/completions` |

## MCP tool loading / calls

| Signature | Root cause | Fix |
|---|---|---|
| `tool_resource() got an unexpected keyword argument 'oauth_scopes'` | The installed SDK does not accept this argument | Use the official sample and pinned dependencies without adding `oauth_scopes` |
| `403 ... -ram.agentrun-data...` with RAM signature, no WAT forwarded | Request carried no WAT | Verify that the unmodified official `main.py` is deployed and that the inbound WAT is present; the sample forwards it through Config headers and the SDK context |
| `MCP initialize timed out after 30s` | The MCP handshake did not complete | Inspect the server response and nested ExceptionGroup; check the endpoint, transport, and Runtime credentials |
| `McpError('This request requires more information.')` | User authorization is required | Provide the authorization URL promptly (links expire in minutes); after authorization completes, retry |
| `500 missing X-AgentRun-Mcp-Tool-Arn` when calling a tool endpoint directly | The tool route may not be active | Check the tool status and use the console registration flow described in this Skill; confirm any failed test tool is cleaned up |
| `StructuredTool does not support sync invocation` | A synchronous invocation reached an async tool function | Check the nested error, deployed official sample files, and dependency versions; rebuild the unmodified sample with the Skill's constraints if they differ |

## Local tool credentials (@requires_*)

| Signature | Root cause | Fix |
|---|---|---|
| Tool reports missing api_key / empty credential, no other error | Provider or region mismatch | Check the provider name and set `AGENT_IDENTITY_REGION_ID=<region>` to the deployment region |
| OSS tool `403 AccessDenied ... bucket acl` | The runtime's auto-created workload-identity role lacks OSS permissions | `05_attach_role_policy.sh` (AliyunOSSReadOnlyAccess on the agentrole-*) |
| `Missmatch.ResourceOAuth2ReturnURL` on an OAuth2-annotated local tool | A supplied callback_url is not in the workload identity's whitelist | Check the deployed official sample and OAuth2 provider configuration; the sample omits callback_url and provides authorization links through on_auth_url |
| `AuthorizationFail.AkProxy: not allowed to do action:CreateRole` | The current CLI profile is not authorized for the named RAM operation | Check the profile and required permissions; use AK mode for this workflow; see `ram-policies.md` section 3 |
| Resource created in an unexpected region | Saved deployment region or console region differs from the intended region | Check saved `AGENTRUN_REGION` and the console region; `AGENT_IDENTITY_REGION_ID` controls the Runtime local tools' credential requests, not these scripts' resource-creation region |

## Cedar / authorization

| Signature | Root cause | Fix |
|---|---|---|
| Every tool call 403 with permission control ON, no policies bound | Permission control is enabled with no permitting policy | Create and bind a policy set, or disable permission control for a connectivity check |
| Tool list shows everything despite policies | The binding, Hooks, or configuration used by the current request may differ from the intended setup | Check the ENFORCE binding and PRE_LIST_TOOLS, POST_LIST_TOOLS, PRE_CALL_TOOL Hooks; verify the current request's actual tool-loading logs before changing the binding |
| Authorization URL flow "completes" but the next call asks again | The link may have expired, or the provider or identity may differ | Check the provider and identity; generate a fresh link if needed |

## Packaging

See `packaging.md` — four distinct pip failures (platform tags, resolver
explosion, sdist-only deps, crcmod) each have a dedicated fix there.

## Toolchain (aliyun CLI)

| Signature | Root cause | Fix |
|---|---|---|
| `Plugin 'aliyun-cli-<x>' is required for command ... but not installed` followed by `ERROR: failed to read user input: EOF` | A plugin-mode (kebab-case) command ran without its plugin, and the CLI's install prompt cannot be answered in a non-interactive shell | Re-run `scripts/00_detect_env.sh` — it sets `auto-plugin-install` and pre-installs the plugins. Manual: `aliyun plugin install --names aliyun-cli-sts aliyun-cli-ram` |
| `'get-caller-identity' is not a valid api` / unknown command | CLI older than 3.3.3, which has no plugin mode | `brew upgrade aliyun-cli`, or install the latest from https://github.com/aliyun/aliyun-cli/releases |
| `required flags missing: --policy-type, --policy-name, --role-name` | Plugin mode also renames flags to kebab-case; PascalCase flags such as `--PolicyType` are not recognised | Use the kebab-case flags |

## Platform notes

- If OAuth CLI credentials return an `AkProxy` error for a RAM operation,
  check the action permissions; use AK mode for this workflow.
- The console MCP-creation page pre-fills `"transportType": "sse"` in its
  JSON example; streamable-http endpoints need the verified block from
  `console-guides.md`.
- Deploying a Runtime with AgentIdentity credential configuration auto-creates
  a workload identity (`agentrun-<id>`,
  role `agentrole-xxxxx`). Manual creation is unnecessary and its OAuth2
  return-URL whitelist is not editable (`WorkloadIdentityPlatformMismatch`).
