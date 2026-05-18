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

## Environment Variables

The script reads the following environment variables. They are typically **pre-configured by the execution platform** — verify they are set before running; do **not** overwrite them with placeholder values.

| Variable | Required | Description | How to obtain |
|----------|----------|-------------|---------------|
| `STAROPS_AGENT_EMPLOYEE` | Yes | Digital employee name in STAROps | STAROps console → Digital Employee list → name column |
| `STAROPS_AGENT_WORKSPACE` | Yes | Workspace identifier | STAROps console → Workspace settings → workspace name |
| `STAROPS_AGENT_UID` | Yes | Alibaba Cloud account UID that owns the workspace | Alibaba Cloud console → Account Management → Account ID |
| `STAROPS_AGENT_ENDPOINT` | No | API endpoint (default: `starops.<region>.aliyuncs.com`) | Use default unless a private or custom endpoint is required |
| `STAROPS_AGENT_REGION` | No | Region (default: `cn-beijing`) | STAROps is centrally deployed; use `cn-beijing` for all regions |

### Environment Setup

If the variables are not pre-configured by the platform, set them manually before running the script:

```bash
export STAROPS_AGENT_EMPLOYEE="<your-digital-employee-name>"
export STAROPS_AGENT_WORKSPACE="<your-workspace-name>"
export STAROPS_AGENT_UID="<your-alibaba-cloud-account-uid>"
```

**Credentials** — The script uses the Alibaba Cloud Credentials SDK default chain. Configure one of the following (in priority order):

1. **STS token** — Recommended for CI/sandbox. The platform injects STS credentials via `~/.aliyun/config.json` or environment.
2. **RAM role** — For ECS/container workloads with instance metadata.
3. **CLI profile** — Run `aliyun configure` to create a profile in `~/.aliyun/config.json`.
4. **Environment variables** — Set `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (least preferred; avoid in production).

Do not define skill-specific AccessKey variables; the credential SDK handles resolution automatically.

**Pre-flight check — run this before invoking the script to confirm the variables are set:**

```bash
missing=""
[ -z "$STAROPS_AGENT_EMPLOYEE" ] && missing="$missing STAROPS_AGENT_EMPLOYEE"
[ -z "$STAROPS_AGENT_WORKSPACE" ] && missing="$missing STAROPS_AGENT_WORKSPACE"
[ -z "$STAROPS_AGENT_UID" ] && missing="$missing STAROPS_AGENT_UID"
if [ -n "$missing" ]; then echo "ERROR: Missing required environment variables:$missing" >&2; exit 1; fi
echo "OK: EMPLOYEE=$STAROPS_AGENT_EMPLOYEE WORKSPACE=$STAROPS_AGENT_WORKSPACE UID=$STAROPS_AGENT_UID"
```

If any required variable is empty, **stop and ask the user** to provide the value. Never substitute placeholder strings like `example-employee`.

The STAROps console link uses the same digital employee ID as `assistantId`.

## Invocation

**IMPORTANT: The `--pipe` flag is MANDATORY for all invocations.** It ensures structured output with THREAD ID, STAROPS_URL, and delimited answer blocks that downstream agents can reliably parse. Never omit `--pipe`.

Install dependencies and run from this skill's root directory:

```bash
pip3 install -r scripts/requirements.txt

# First call - creates a new thread automatically
python3 scripts/call_starops_agent.py --question "<complete user context>" --pipe

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
   - If the STAROps answer is empty (`(No assistant answer was returned.)`), incomplete, or only contains generic text, retry once using the same `--thread`. If the retry still yields no actionable data, report honestly: "STAROps 未返回有效诊断数据，请确认 workspace 中是否存在相关服务和时间范围内的数据。"
   - Never substitute your own prior knowledge for missing STAROps evidence. For example, do not claim "database connection pool exhaustion" if STAROps did not mention it.

## Troubleshooting

When the script exits with an error, check the following in order:

1. **HTTP 401 Unauthorized** — The credential chain did not resolve to a valid identity with STAROps permissions. Verify that the Alibaba Cloud Credentials default chain can resolve a valid credential (STS token, RAM role, CLI profile, or instance metadata) and that the identity has `cms:CreateThread` and `cms:CreateChat` permissions. See [references/ram-policies.md](references/ram-policies.md).
2. **HTTP 404 Not Found** — The digital employee name (`STAROPS_AGENT_EMPLOYEE`) or workspace (`STAROPS_AGENT_WORKSPACE`) does not exist, or the UID (`STAROPS_AGENT_UID`) does not match the owning account. Double-check all three environment variables.
3. **ConfigError: Missing required STAROps environment variables** — One or more of `STAROPS_AGENT_EMPLOYEE`, `STAROPS_AGENT_WORKSPACE`, `STAROPS_AGENT_UID` is empty or unset.
4. **CredentialError** — The Alibaba Cloud Credentials SDK could not find any valid credential source. Ensure at least one credential provider is configured (environment variables, `~/.aliyun/config.json`, STS, RAM role, or instance metadata).
5. **Idle timeout** — No SSE event was received within `--idle-timeout` seconds (default 60). The STAROps Agent may be stalled. Retry with the same `--thread` if a THREAD line was printed, or increase `--idle-timeout` for investigations expected to be quiet.
6. **Stream interruption / network error** — The HTTPS connection was reset or timed out. Retry the same request with `--thread` to resume context.
7. **ModuleNotFoundError** — Python dependency not installed. Run `pip3 install -r scripts/requirements.txt` before invoking the script.

## API Surface

This skill directly calls STAROps OpenAPI:

- `CreateThread`: `POST /digitalEmployee/{name}/thread`
- `CreateChat`: `POST /chat`

See [references/api-reference.md](references/api-reference.md) and [references/ram-policies.md](references/ram-policies.md).
