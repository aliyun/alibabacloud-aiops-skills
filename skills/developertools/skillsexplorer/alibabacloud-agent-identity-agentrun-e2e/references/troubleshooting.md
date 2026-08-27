# Troubleshooting: Field-Verified Failure Signatures

Every entry below was hit and root-caused during the field verification run
(2026-08). Match the signature first, apply the fix, then retest.

## Inbound (Runtime endpoint)

| Signature | Root cause | Fix |
|---|---|---|
| `401 ERR_UNAUTHORIZED: Agent Identity enabled but no ID token provided` | Request lacks the OIDC ID Token | Add `Authorization: Bearer <id-token>` |
| `401 ID token validation failed` | IdP signing key drift or wrong issuer | Re-check the IdP discovery URL; re-sign a fresh token |
| `404 {"detail":"Not Found"}` at `.../invocations` | Wrong path — the app serves OpenAI routes | Use `.../invocations/openai/v1/chat/completions` |
| `404 NOT_FOUND` (platform style) at `/openai/v1/...` directly under `endpoints/Default/` | Path misses the `/invocations` prefix | Full path: `endpoints/Default/invocations/openai/v1/chat/completions` |

## MCP tool loading / calls

| Signature | Root cause | Fix |
|---|---|---|
| `tool_resource() got an unexpected keyword argument 'oauth_scopes'` | agentrun-sdk 0.0.52 removed the parameter | Sample code must not pass it; no OAUTH_SCOPES env either |
| `403 ... -ram.agentrun-data...` with RAM signature, no WAT forwarded | Request carried no WAT (SDK has no built-in forwarding) | The sample must forward WAT manually — see the sample's main.py (Config headers + SDK context) |
| `MCP initialize timed out after 30s` (normal endpoint) | Server answered `200 {"error":"Authorization header is missing"}` — a non-JSON-RPC body the MCP client waits on forever | The call lacked the platform credential/RAM auth — check the runtime instance actually received FC-injected credentials; also the classic mask for OTHER errors: unwrap the ExceptionGroup (sub-exception) before diagnosing |
| `McpError('This request requires more information.')` | The OAuth2 access token expired (1 h TTL) or first use — the Hook demands authorization | Hand the authorization URL to the user IMMEDIATELY (links expire in minutes); after they click, retry |
| `500 missing X-AgentRun-Mcp-Tool-Arn` when calling a tool endpoint directly | The tool was created via the CreateTool API — data-plane route never activated | Recreate the tool through the AgentRun console; API-created tools also self-vanish |
| `StructuredTool does not support sync invocation` | langchain sync invoke on an async tool function | Make local tools plain `def`, and wrap decorated impls behind a clean-signature function |

## Local tool credentials (@requires_*)

| Signature | Root cause | Fix |
|---|---|---|
| Tool reports missing api_key / empty credential, no other error | agent-identity SDK defaulted to cn-beijing | Runtime env MUST set `AGENT_IDENTITY_REGION_ID=<region>` |
| OSS tool `403 AccessDenied ... bucket acl` | The runtime's auto-created workload-identity role lacks OSS permissions | `05_attach_role_policy.sh` (AliyunOSSReadOnlyAccess on the agentrole-*) |
| `Missmatch.ResourceOAuth2ReturnURL` on an OAuth2-annotated local tool | Tool passed a callback_url the workload identity's whitelist doesn't contain (AgentRun-managed identities have an EMPTY, non-editable whitelist) | Do not pass callback_url at all — the platform handles callbacks; route the on_auth_url link to the user instead |
| `AuthorizationFail.AkProxy: not allowed to do action:CreateRole` (or any RAM write) | CLI logged in via OAuth mode — temporary credentials cannot do RAM writes | Reconfigure the CLI in AK mode (`aliyun configure`); see `ram-policies.md` section 3 |
| Resource created in cn-beijing unexpectedly | agent-identity CLI/SDK default region | `AGENT_IDENTITY_REGION_ID=cn-hangzhou` in the environment of the creating process |

## Cedar / authorization

| Signature | Root cause | Fix |
|---|---|---|
| Every tool call 403 with permission control ON, no policies bound | GA behavior: policy control enabled + empty policy set = deny all | Create + bind a policy set, or disable permission control for a pure smoke run |
| Tool list shows everything despite policies | Policy set not bound to the tool | Bind the set to the tool in the AgentIdentity console (binding is console-side) |
| Authorization URL flow "completes" but the next call asks again | The request_uri link expired before the user clicked | Generate a fresh link and click immediately |

## Packaging

See `packaging.md` — four distinct pip failures (platform tags, resolver
explosion, sdist-only deps, crcmod) each have a dedicated fix there.

## Toolchain (aliyun CLI)

| Signature | Root cause | Fix |
|---|---|---|
| `Plugin 'aliyun-cli-<x>' is required for command ... but not installed` followed by `ERROR: failed to read user input: EOF` | A plugin-mode (kebab-case) command ran without its plugin, and the CLI's install prompt cannot be answered in a non-interactive shell | Re-run `scripts/00_detect_env.sh` — it sets `auto-plugin-install` and pre-installs the plugins. Manual: `aliyun plugin install --names aliyun-cli-sts aliyun-cli-ram` |
| `'get-caller-identity' is not a valid api` / unknown command | CLI older than 3.3.3, which has no plugin mode | `brew upgrade aliyun-cli`, or install the latest from https://github.com/aliyun/aliyun-cli/releases |
| `required flags missing: --policy-type, --policy-name, --role-name` | Plugin mode also renames flags to kebab-case; PascalCase flags such as `--PolicyType` are not recognised | Use the kebab-case flags |

## Platform quirks worth knowing

- OAuth-issued CLI credentials (OAuth login mode) are rejected for RAM write
  operations with `AkProxy` errors — AK mode is the working configuration.
- The console MCP-creation page pre-fills `"transportType": "sse"` in its
  JSON example; streamable-http endpoints need the verified block from
  `console-guides.md`.
- Deploying a Runtime auto-creates a workload identity (`agentrun-<id>`,
  role `agentrole-xxxxx`). Manual creation is unnecessary and its OAuth2
  return-URL whitelist is not editable (`WorkloadIdentityPlatformMismatch`).
