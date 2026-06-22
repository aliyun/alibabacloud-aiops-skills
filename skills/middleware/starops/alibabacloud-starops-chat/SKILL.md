---
name: alibabacloud-starops-chat
description: |
  Alibaba Cloud STAROps Agent AIOps diagnostic skill. Use this skill to help users diagnose service errors, analyze root causes, query workspace/service topology, inspect APM metrics, and troubleshoot incidents through the STAROps Agent.
  Triggers: "排查根因", "根因分析", "服务报错", "服务异常", "APM 服务", "workspace 服务", "STAROps", "AIOps 诊断", "链路追踪", "告警分析".
---

# Alibaba Cloud STAROps Agent

Call the Alibaba Cloud STAROps Agent through STAROps OpenAPI and receive a streaming diagnostic answer.

## Scenario Description

Use this skill when the user wants to:

- Diagnose service errors or exceptions (root cause analysis)
- Query workspace topology, service lists, or service metrics
- Analyze APM traces, error rates, latency, or request volume
- Triage alerts or investigate incidents
- Ask questions about their STAROps workspace or services

## Configuration

The script reads STAROps connection values from environment variables and optional JSON config files. Environment variables and command-line flags override config file values.

Config files are loaded in this order:

1. User config: `~/.starops/config.json`
2. Project config: `./.starops/config.json` (overrides user config)
3. Explicit config: `--config <path>` or `STAROPS_AGENT_CONFIG` (overrides user/project config)

The three required values (`employeeId`, `workspace`, `uid`) may come from either environment variables or config files.

| Variable | Required | Description |
|----------|----------|-------------|
| `STAROPS_AGENT_EMPLOYEE` | Yes, unless config provides `employeeId` | Digital Employee ID in STAROps (from console → Digital Employee list → ID column) |
| `STAROPS_AGENT_WORKSPACE` | Yes, unless config provides `workspace` | Workspace identifier |
| `STAROPS_AGENT_UID` | Yes, unless config provides `uid` | Alibaba Cloud account UID that owns the workspace |
| `STAROPS_AGENT_ENDPOINT` | No | API endpoint (default: `starops.cn-beijing.aliyuncs.com`) |
| `STAROPS_AGENT_PROJECT` | No | Optional STAROps project variable forwarded with each request. Overridden by `--project` |
| `STAROPS_AGENT_TIMEOUT` | No | Default value for `--timeout` (CreateChat stream total timeout in seconds; default `1800`) |
| `STAROPS_AGENT_IDLE_TIMEOUT` | No | Default value for `--idle-timeout` (max seconds to wait for the next SSE event; default `60`) |
| `STAROPS_AGENT_CONFIG` | No | Path to an explicit JSON config file loaded after user/project config |

Minimal config file example:

```json
{
  "employeeId": "<your-digital-employee-id>",
  "workspace": "<your-workspace-name>",
  "uid": "<your-alibaba-cloud-account-uid>"
}
```

Optional fields:

```json
{
  "endpoint": "starops.cn-beijing.aliyuncs.com",
  "project": "optional-project",
  "timeout": 1800,
  "idleTimeout": 60
}
```

Config files use the exact key names shown above. Do not use alternate aliases such as `employee`, `digitalEmployeeId`, `workspaceName`, or `accountUid`.

**Pre-flight check — run this before invoking the script to confirm environment or config values are available:**

```bash
missing=""
[ -z "$STAROPS_AGENT_EMPLOYEE" ] && missing="$missing STAROPS_AGENT_EMPLOYEE"
[ -z "$STAROPS_AGENT_WORKSPACE" ] && missing="$missing STAROPS_AGENT_WORKSPACE"
[ -z "$STAROPS_AGENT_UID" ] && missing="$missing STAROPS_AGENT_UID"
config_file_found=""
[ -f ".starops/config.json" ] && config_file_found=1
[ -f "$HOME/.starops/config.json" ] && config_file_found=1
[ -n "$STAROPS_AGENT_CONFIG" ] && [ -f "$STAROPS_AGENT_CONFIG" ] && config_file_found=1
if [ -n "$missing" ] && [ -z "$config_file_found" ]; then
  echo "ERROR: Missing required environment variables:$missing and no STAROps config file was found" >&2
  exit 1
fi
echo "OK: STAROps configuration is available from environment variables or config file"
```

If any required value is still unavailable, ask the user to provide it. Never substitute placeholder strings like `example-employee`.

The STAROps console link uses the same digital employee ID as `assistantId`.

Credentials use the Alibaba Cloud Credentials default chain. Do not define skill-specific AccessKey variables; use standard Alibaba Cloud credential sources such as environment credentials (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`), profiles, STS, RAM role, or instance metadata.

## Invocation

**IMPORTANT: The `--pipe` flag is MANDATORY for all invocations.** It ensures structured output with THREAD ID, STAROPS_URL, and delimited answer blocks that downstream agents can reliably parse. Never omit `--pipe`.

Install dependencies and run from this skill's root directory:

```bash
pip3 install -r scripts/requirements.txt

# First call - creates a new thread automatically
python3 scripts/call_starops_agent.py --question "<complete user context>" --pipe

# First call with an explicit config file
python3 scripts/call_starops_agent.py --config ".starops/config.json" --question "<complete user context>" --pipe

# Follow-up calls - MUST reuse the thread ID from previous response
python3 scripts/call_starops_agent.py --thread "<thread_id>" --question "<follow-up question>" --pipe
```

**Thread Management:**
- Extract thread ID from output
- Use the printed `STAROPS_URL` when the user needs to inspect the same thread in the STAROps console
- Always pass `--thread "<id>"` for related follow-up questions to preserve context

Example workflow:
```bash
# Query 1: Creates new thread
$ python3 scripts/call_starops_agent.py --question "Query TOP 5 error applications" --pipe
THREAD: thread-abc123-xyz
STAROPS_URL: https://starops.console.aliyun.com/chat?threadId=thread-abc123-xyz&assistantId=apsara-ops
=== STAROPS ANSWER BEGIN ===
...

# Query 2: MUST reuse thread for context
$ python3 scripts/call_starops_agent.py --thread "thread-abc123-xyz" --question "Deep dive into notification app errors" --pipe
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| `--question <text>` | **Required.** Natural-language question to send to STAROps Agent. |
| `--thread <id>` | Existing STAROps thread ID. **Required for follow-up questions** to preserve investigation context. |
| `--pipe` | **Mandatory for agent invocations.** Emit structured output with `THREAD`, `STAROPS_URL`, and `=== STAROPS ANSWER BEGIN/END ===` delimiters for reliable parsing. |
| `--json` | Emit machine-readable JSONL events. Mutually exclusive with `--pipe`. **Do not use for agent invocations** — `--pipe` is the supported agent format. |
| `--config <path>` | Optional JSON config file. Loaded after `~/.starops/config.json` and `./.starops/config.json`. |
| `--project <name>` | Optional STAROps project variable. Overrides `STAROPS_AGENT_PROJECT`. |
| `--timeout <seconds>` | Total CreateChat stream timeout in seconds. Overrides `STAROPS_AGENT_TIMEOUT` (default `1800`). |
| `--idle-timeout <seconds>` | Maximum seconds to wait for the next SSE event before failing. Overrides `STAROPS_AGENT_IDLE_TIMEOUT` (default `60`). |

## Behavioral Notes

1. STAROps Agent calls are long-running by design. A single `CreateChat` stream may start multiple internal diagnostic steps and take minutes; the default timeout is 30 minutes.
2. Provide complete context in one question: cloud account or workspace context, time range, service or application names, alert text, SLS project/logstore, UModel object, region, and what decision the user needs.
3. **CRITICAL: Always reuse `--thread` for follow-ups in the same investigation. Starting a new thread discards all prior context and findings.**
4. Use this skill for Agent reasoning and diagnosis, not direct resource management. For direct ECS, OSS, RDS, SLS, or RAM mutations, use the corresponding official CLI, SDK, or specialized skill.
5. **MANDATORY: Always pass `--pipe`.** Tool-call status and streaming diagnosis-report chunks are written to stderr, while stdout keeps the reusable thread ID and final answer easy to parse. Omitting `--pipe` will produce unstructured output that cannot be reliably evaluated.
6. If no SSE event arrives for a while, the script fails with a clear idle-timeout error instead of silently waiting for the full task timeout. Increase `--idle-timeout` only when the investigation is expected to be quiet for long periods.
7. **Output integrity rule**: Your final report MUST be based on the actual content returned between `=== STAROPS ANSWER BEGIN ===` and `=== STAROPS ANSWER END ===`. Specifically:
   - Quote or paraphrase concrete data points from the STAROps response (HTTP status codes, service names, error paths, metrics).
   - Do NOT infer or fabricate diagnostic conclusions that are not supported by the STAROps output.
   - If the STAROps answer is empty (`(No assistant answer was returned.)`), incomplete, or only contains generic text, retry once using the same `--thread`. If the retry still yields no actionable data, report honestly: "STAROps did not return actionable diagnostic data. Confirm that the workspace contains relevant services and data for the requested time range."
   - Never substitute your own prior knowledge for missing STAROps evidence. For example, do not claim "database connection pool exhaustion" if STAROps did not mention it.

## Observability

All STAROps OpenAPI HTTP requests must use this User-Agent template declaration:

```text
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

For this skill, the concrete template is:

```text
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-starops-chat/{session-id}
```

Generate exactly one `session-id` per skill invocation as a 32-char hex value. If `SKILL_SESSION_ID` is already set, reuse that value after validating it is 32 hex characters; otherwise generate `uuid4().hex`, set `SKILL_SESSION_ID`, and reuse it for all outbound calls. The same `session-id` must be consistent across CLI/SDK/Terraform and direct HTTP requests made during the invocation, including both `CreateThread` and `CreateChat`; do not generate a new `session-id` per request. The Python script sets the HTTP `User-Agent` header to `AlibabaCloud-Agent-Skills/alibabacloud-starops-chat/{session-id}`.

## Troubleshooting

When the script exits with an error, check the following in order:

1. **HTTP 401 Unauthorized** — The credential chain did not resolve to a valid identity with STAROps permissions. Verify that `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (or STS / RAM role) are set and that the identity has `starops:CreateThread` and `starops:CreateChat` permissions. See [references/ram-policies.md](references/ram-policies.md).
2. **HTTP 404 Not Found** — The Digital Employee ID (`STAROPS_AGENT_EMPLOYEE`) or workspace (`STAROPS_AGENT_WORKSPACE`) does not exist, or the UID (`STAROPS_AGENT_UID`) does not match the owning account. Double-check all three environment variables.
3. **ConfigError: Missing required STAROps configuration values** — One or more of `employeeId`, `workspace`, or `uid` is missing from both environment variables and config files.
4. **CredentialError** — The Alibaba Cloud Credentials SDK could not find any valid credential source. Ensure at least one credential provider is configured (environment variables, `~/.aliyun/config.json`, STS, RAM role, or instance metadata).
5. **Idle timeout** — No SSE event was received within `--idle-timeout` seconds (default 60). The STAROps Agent may be stalled. Retry with the same `--thread` if a THREAD line was printed, or increase `--idle-timeout` for investigations expected to be quiet.
6. **Stream interruption / network error** — The HTTPS connection was reset or timed out. Retry the same request with `--thread` to resume context.
7. **ModuleNotFoundError** — Python dependency not installed. Run `pip3 install -r scripts/requirements.txt` before invoking the script.

## API Surface

This skill directly calls STAROps OpenAPI:

- `CreateThread`: `POST /digitalEmployee/{employeeId}/thread`
- `CreateChat`: `POST /chat`

See [references/api-reference.md](references/api-reference.md) and [references/ram-policies.md](references/ram-policies.md).
