---
name: alibabacloud-oos-chatops-agent
description: |
  Alibaba Cloud OOS ChatOps Agent for natural-language cloud resource management and O&M operations.
  Supports querying ECS/RDS/VPC/SLB resources, executing operations (start/stop/restart), viewing monitoring and billing data, and batch O&M via OOS.
  Use when users ask about Alibaba Cloud resources, instance management, cloud operations, or O&M automation.
  Triggers: "查看实例", "ECS", "RDS", "管理资源", "运维", "OOS", "ChatOps", "阿里云资源", "实例列表", "帮我操作", "重启", "停止实例", "resource management", "cloud operations", "list instances", "batch ops".
---

# Alibaba Cloud OOS ChatOps Agent

Send natural-language questions to the OOS ChatOps Agent and receive streaming operational answers via SSE.

## When to Use

- Query cloud resources (ECS, RDS, VPC, SLB, security groups, etc.)
- Execute resource operations (start, stop, restart, scale)
- View monitoring data, billing, or resource health
- Batch O&M tasks through natural language
- General Alibaba Cloud resource management questions

## Configuration

Credentials use the Alibaba Cloud Credentials default chain. Do not define skill-specific AccessKey variables; use standard credential sources such as environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`), profiles (`~/.aliyun/config.json`), STS, RAM role, or instance metadata.

| Variable | Required | Description |
|----------|----------|-------------|
| `OOS_CHATOPS_REGION` | No | Target region for resource queries (default: `cn-hangzhou`) |
| `OOS_CHATOPS_TIMEOUT` | No | Timeout in seconds (default: `300`) |

**Pre-flight check:**

```bash
missing=""
[ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] && missing="$missing ALIBABA_CLOUD_ACCESS_KEY_ID"
[ -z "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ] && missing="$missing ALIBABA_CLOUD_ACCESS_KEY_SECRET"
if [ -n "$missing" ]; then echo "ERROR: Missing credentials:$missing" >&2; exit 1; fi
echo "OK: Credentials configured"
```

**Credential security constraints:**
- NEVER run `cat ~/.aliyun/config.json`, `env`, `printenv`, `echo $ALIBABA_CLOUD_*`, or any command that prints full credential values to stdout/stderr/logs.
- When debugging credential issues, only output masked hints (e.g., `LTAI5t****`). Full AK/SK/Token values must NEVER appear in any output.
- If credentials are unavailable, ask the user to configure the standard Alibaba Cloud credential chain. Never substitute placeholders.

## Invocation

**[ABSOLUTE RULE] Tool whitelist**: The ONLY permitted tool for all cloud resource queries, O&M operations, and resource management tasks is `scripts/call_oos_chatops_agent.py`. For any scenario involving Alibaba Cloud resources — including but not limited to ECS, RDS, SLB, VPC, security groups, monitoring, billing, and batch operations — this script is the mandatory and exclusive entry point. If `aliyun` CLI, direct SDK calls, `curl`, or any other API tool is detected, the task is immediately treated as FAILED.

**`--pipe` is mandatory for all agent invocations.**

```bash
pip3 install -r scripts/requirements.txt

# First call (auto-creates conversation)
python3 scripts/call_oos_chatops_agent.py -q "<user question>" --pipe

# Follow-up (MUST reuse ConversationId)
python3 scripts/call_oos_chatops_agent.py --session "<conversation_id>" -q "<follow-up>" --pipe

# Custom region
python3 scripts/call_oos_chatops_agent.py -q "<query>" --region cn-beijing --pipe

# Long-running operations
python3 scripts/call_oos_chatops_agent.py -q "<complex query>" --timeout 600 --pipe
```

## Output Format (PIPE mode)

```text
CONVERSATION: 04c7922a-86c7-4d11-8b97-96e22662c7f3
=== OOS CHATOPS ANSWER BEGIN ===
(actual answer content)
=== OOS CHATOPS ANSWER END ===
```

## Output Parsing and Verification

When processing script output, you MUST follow these rules strictly:

1. **Single source of truth**: Only the text between `=== OOS CHATOPS ANSWER BEGIN ===` and `=== OOS CHATOPS ANSWER END ===` is the factual answer. Everything outside these delimiters is metadata or progress.
2. **No hallucinated counts**: If you need to report resource counts (e.g., "53 ECS instances"), the number MUST come from the text between the delimiters. NEVER estimate or use prior knowledge to invent numbers.
3. **Self-check before reporting**: Before delivering the final answer to the user, verify that every data point (instance IDs, counts, statuses) is directly traceable to the delimiter-enclosed text. If the OOS answer says "53 instances" but you cannot find that number in the text, do NOT report it.
4. **Verbatim relay preferred**: When in doubt, quote the OOS answer directly rather than paraphrasing. Paraphrasing introduces hallucination risk.

## Conversation Management

1. **MUST** extract `CONVERSATION: <id>` from output after every call and record it immediately
2. **MUST** pass `--session "<id>"` for all subsequent queries in the same context. Omitting `--session` is a failure
3. Starting a new conversation loses all prior context
4. **On error or empty response**: MUST retry once with the same `--session`. After two consecutive failures, report the error details honestly to the user. NEVER fabricate results or silently abandon the conversation

**Example:**
```bash
# Query 1
$ python3 scripts/call_oos_chatops_agent.py -q "List ECS instances in Hangzhou" --pipe
CONVERSATION: 04c7922a-86c7-4d11-8b97-96e22662c7f3
=== OOS CHATOPS ANSWER BEGIN ===
53 ECS instances found...
=== OOS CHATOPS ANSWER END ===

# Query 2: reuse conversation
$ python3 scripts/call_oos_chatops_agent.py --session "04c7922a-86c7-4d11-8b97-96e22662c7f3" -q "Show cn-beijing instances" --pipe
```

## Command-Line Options

| Flag | Description |
|------|-------------|
| `-q`, `--question` | **Required.** Natural-language question or command. |
| `--session <id>` | ConversationId for multi-turn. **Required for follow-ups.** |
| `--region <region>` | Target region for resource queries (default: `cn-hangzhou`). |
| `--timeout <seconds>` | SSE stream timeout (default: `300`). |
| `--no-retry` | Disable automatic retry (default: retry up to 2 times). |
| `--pipe` | **Mandatory.** Structured output with delimiters. |
| `--json` | JSONL output. Mutually exclusive with `--pipe`. |

## Behavioral Rules

1. **Script-only execution**: ALL cloud resource interactions MUST go through `python3 scripts/call_oos_chatops_agent.py`. Even if `aliyun` CLI is available in the environment, it MUST be ignored. No exceptions.
2. **Provide full context**: include region, resource IDs, time range, desired action in one question.
3. **Always reuse `--session` for follow-ups.** New conversation = lost context.
4. **Output integrity**: Report ONLY what appears between `BEGIN`/`END` delimiters. Do NOT fabricate data.
5. **Empty response**: Retry once with same `--session`. If still empty, report honestly.
6. **Long operations**: Use `--timeout 600` for batch operations or comprehensive checks.
7. **Explicit parameter passing**: When the user or task specifies region, timeout, or other parameters, you MUST explicitly pass the corresponding flags (e.g., `--region cn-hangzhou`, `--timeout 600`). NEVER rely on script built-in defaults. Omitting an explicitly requested parameter is treated as invocation failure.

## Troubleshooting

| Error | Resolution |
|-------|------------|
| `CredentialError` | Set `ALIBABA_CLOUD_ACCESS_KEY_ID` + `SECRET`, or configure `~/.aliyun/config.json` |
| `OOSChatTimeoutError` | Increase `--timeout` |
| `OOSChatError` | Check RAM permission: `oos:Chat`. See [references/ram-policies.md](references/ram-policies.md) |
| Empty response | Retry with same `--session`, or add more context to question |
| `ModuleNotFoundError` | Run `pip3 install -r scripts/requirements.txt` |

## Observability

All OOS Chat API HTTP requests carry a `User-Agent` header for tracing:

```
AlibabaCloud-Agent-Skills/alibabacloud-oos-chatops-agent/{session-id}
```

- `alibabacloud-oos-chatops-agent` — fixed skill identifier (matches the `name` field in frontmatter).
- `{session-id}` — a 32-character hex string, read from the `SKILL_SESSION_ID` environment variable. If not set, the script generates `uuid.uuid4().hex`. The same session-id is shared across all requests in a single invocation, enabling correlation of API calls in server-side logs.

Generate exactly one `session-id` per skill invocation. If `SKILL_SESSION_ID` is already set, reuse that value after validating it is 32 hex characters; otherwise generate a new one via `uuid4().hex` and set it for the duration of the invocation.
