# Versioned User-Agent for Alibaba Cloud calls

The skill version is the top-level `version` string in [../manifest.json](../manifest.json), not the CLI/SDK version. The skill name comes from SKILL.md frontmatter. Never hardcode a session ID or copy one from another skill.

At the start of each invocation of this skill, generate a fresh random 32-character lowercase hexadecimal session ID with `secrets.token_hex(16)`. Generate it once per invocation, not per HTTP request. Reuse it across requests, retries, polling, SSE reconnects, subprocesses, and transport fallback in that invocation. Every other skill invocation generates its own ID; do not reuse an inherited generic UA or another skill's ID. A new run must regenerate it.

## Initialize once

Resolve `SKILL_ROOT` to this installed skill's absolute directory (not the customer's current directory), then run:

```bash
export BAILIAN_MANAGED_AGENT_SKILL_UA="$(python3 "$SKILL_ROOT/scripts/user_agent.py")"
test -n "$BAILIAN_MANAGED_AGENT_SKILL_UA" || exit 1
```

Keep this value in the execution context and explicitly pass it to subprocesses if shell environments do not persist. It contains no credentials. Customer code generated for later execution must ship the helper and manifest/name metadata or equivalent runtime initialization; generate a fresh ID on each application run, not at code-generation time.

The required declaration, with placeholders substituted at runtime, is exactly:

```bash
--user-agent "AlibabaCloud-Agent-Skills/{frontmatter-name}/{session-id} skill-version/{skill-version}"
```

## curl / REST

All cloud API curl examples in this skill require the initialization above. The flag expands to the complete declaration, including the space before `skill-version`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 \
  --header "Authorization: Bearer $DASHSCOPE_API_KEY" \
  "$CMA_BASE/agents?limit=20"
```

Keep the same header on upload, download, polling, and event-stream requests. Do not send credentials to a public echo service to test UA propagation. Validate request headers locally with a recording transport or inspect the HTTP client's prepared request.

## CLI

The exported variable above is storage for our wrapper; it is **not** a claim that `bl` automatically reads it. Before any cloud call, verify the installed CLI's documented custom User-Agent/header mechanism using help or its source. If a version supports a custom-UA argument, pass the complete generated value explicitly to every cloud command. Do not assume `bl --user-agent` exists just because curl supports it.

If the CLI cannot forward the UA, follow the bounded update rule in [cli-api-routing.md](cli-api-routing.md), then re-check. If still unavailable, perform the authorized operation through REST with the header. Do not issue a CLI cloud request with missing attribution, patch the installed CLI, or bypass a pending plan/approval gate. Local version/help/validation operations have no cloud request to annotate.

## SDK and HTTP clients

Set the actual outbound `User-Agent` header at the request/transport layer, after SDK default headers are applied. Setting an unrelated environment variable is insufficient. Verify the installed SDK's supported transport hook first. If unsupported, use REST with a configurable HTTP client instead of inventing an SDK parameter.

- Python HTTPX: a synchronous `request` event hook assigns `request.headers['User-Agent'] = ua`; `AsyncClient` needs an async hook. For DashScope, pass that HTTPX client through the verified `http_client` option, confirming the installed version accepts the transport. See [../integration/code-python.md](../integration/code-python.md).
- Java OkHttp: a shared interceptor sets `.header("User-Agent", ua)` on every request. The SSE client must inherit it. See [../integration/code-java.md](../integration/code-java.md).
- Other SDKs: use their verified custom-header/transport mechanism and test the final outbound header; REST is the fallback if the mechanism cannot be verified.

## Terraform (only if explicitly selected)

This skill does not ship Terraform configurations. If explicitly requested, the Alibaba Cloud provider documents `TF_APPEND_USER_AGENT` (since v1.145.0) and `configuration_source` for appending custom attribution. Use the same per-run value:

```bash
export TF_APPEND_USER_AGENT="$BAILIAN_MANAGED_AGENT_SKILL_UA"
```

Pass it to the process running `terraform plan` / `apply`, including remote runners; verify the provider version and effective header locally. Preserve the provider's native tokens and the complete skill component. Do not also set `configuration_source` to a conflicting value. Other providers require separate verification; exporting arbitrary `TF_VAR_*` variables does not set headers.

Source: [Alibaba Cloud provider: custom User-Agent](https://registry.terraform.io/providers/aliyun/alicloud/latest/docs).
