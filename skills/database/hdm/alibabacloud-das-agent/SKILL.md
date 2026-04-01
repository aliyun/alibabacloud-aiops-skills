---
name: alibabacloud-das-agent
description: >
  Diagnose and manage Alibaba Cloud databases through natural language. Use when
  users need to troubleshoot database performance issues (high CPU, slow queries,
  abnormal connections, lock waits), check instance status, analyze disk space,
  optimize SQL, run health inspections, or detect security baseline violations.
  Supports RDS (MySQL/PostgreSQL/SQL Server), PolarDB, MongoDB, Redis (Tair),
  and Lindorm. Trigger this skill even for casual descriptions like "my database
  is slow", "can't connect to the database", "help me check this SQL", or
  "database disk is almost full". Also suitable for consulting Alibaba Cloud-specific
  database features (e.g., PolarDB Serverless, DAS autonomy capabilities) and
  comparing product differences (RDS vs PolarDB). Do NOT use this skill for
  general SQL tutorials, non-Alibaba Cloud databases, or local database administration.
license: Apache-2.0
compatibility: >
  Requires uv (Python package manager) and HTTPS access to das.cn-shanghai.aliyuncs.com.
  Requires Alibaba Cloud credentials to be available through the default credential chain
  (AliyunHDMFullAccess permission). DAS Agent ID is optional.
metadata:
  async: true
  timeout: 1800
  required_permissions:
    - "das:Chat"
---

# DAS Agent Chat

Send natural language questions to the Alibaba Cloud DAS (Database Autonomy Service) Agent and receive diagnostic results.

## Pricing and Free Tier

**This is a paid service with a free tier for trial usage.**

- **Free Tier**: When `ALIBABA_CLOUD_DAS_AGENT_ID` is not set, the script omits the `AgentId` parameter and the API will use a **default Agent ID** which comes with a limited free quota for trial purposes.
- **Paid Usage**: For production workloads or higher usage volumes, purchase a DAS Agent subscription and set your own `ALIBABA_CLOUD_DAS_AGENT_ID` to bind your dedicated agent and quota.

> **Recommendation**: Start with the free tier (default Agent ID) to evaluate the service. Once you decide to adopt it for production, purchase a subscription and configure your own Agent ID.

## Environment Variables

The script requires Alibaba Cloud credentials resolvable via the [default credential chain](https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-python-access-credentials). The DAS Agent ID is **optional** — if not provided, the `AgentId` parameter will be omitted and the API will use a default Agent ID with limited free quota.

```bash
# Optional: Set your own Agent ID after purchasing DAS Agent service
export ALIBABA_CLOUD_DAS_AGENT_ID="<agent_id>"               # Obtain from DAS console (optional)
```

The Alibaba Cloud Credentials SDK automatically resolves credentials from multiple sources (environment variables, configuration files, ECS RAM roles, etc.). Refer to the [official credential configuration documentation](https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-python-access-credentials) for setup instructions.

If you have purchased a DAS Agent subscription, create and manage your Agent ID at: https://das.console.aliyun.com/

## Troubleshooting

### Credential Resolution Failed

If the script exits with a credential-related error, it means the Alibaba Cloud Credentials SDK could not resolve a usable credential from its default provider chain.

Supported credential sources:

- Environment variables (see [official documentation](https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-python-access-credentials))
- Local profile files: `~/.aliyun/config.json` or `~/.alibabacloud/credentials.ini`
- ECS RAM Role metadata when running on an Alibaba Cloud ECS instance

Common cases:

- Credential environment variables are empty or missing — configure them according to the official documentation.
- Errors mentioning `~/.aliyun/config.json` or `~/.alibabacloud/credentials.ini`
  The SDK attempted local profile-based credentials, but the files were missing or invalid. Create/fix the default profile if you want to use local profiles.
- Errors mentioning `100.100.100.200`
  The SDK attempted ECS metadata. This is expected on ECS, but usually a local-machine misconfiguration elsewhere.

For local development, if you are not using ECS RAM Role credentials, you can explicitly disable ECS metadata lookup:

```bash
export ALIBABA_CLOUD_ECS_METADATA_DISABLED=true
```

This avoids confusing `100.100.100.200` metadata connection errors on non-ECS machines and makes missing-credential failures easier to read.

## Invocation

Run from the `scripts/` directory of this skill:

```bash
cd scripts

# Pipe mode (RECOMMENDED for agents) — clean output: progress to stderr, answer clearly delimited on stdout
uv run call_das_agent.py --question "<user's question>" --pipe

# Default mode (CLI chat UI) — real-time streaming with tool details
uv run call_das_agent.py --question "<user's question>"

# JSON mode — machine-readable JSONL, one JSON object per line on stdout
uv run call_das_agent.py --question "<user's question>" --json

# Multi-turn conversation — reuse the server-assigned session ID to maintain context
uv run call_das_agent.py --question "List my instances" --pipe  # Returns session_id on first line
# Extract session_id (line starting with "SESSION:"), then reuse it:
uv run call_das_agent.py --question "Check the first one" --session "<session_id_from_above>" --pipe
```

**Always use `--pipe` when invoking as an agent.** It routes all progress/tool-call noise to stderr and writes only the DAS answer to stdout, wrapped in clear delimiters — making the real response impossible to miss.

Prefer `--json` when you need to parse the response programmatically. For JSON event types and output mode details, see [references/api-reference.md](references/api-reference.md).

## Behavioral Notes

DAS Agent internally orchestrates multiple API calls and tool invocations to answer a single question. This has important implications:

1. **Long-running tasks**: Complex diagnostics (multi-instance inspection, comprehensive health checks, batch SQL analysis) can take several minutes up to 30 minutes, because DAS Agent sequentially calls monitoring APIs, runs diagnostics, and synthesizes results. Inform the user before starting and provide periodic progress updates.

2. **Instance enrollment**: The target database instance must be enrolled under the DAS Agent. If you see error code `-1810006`, it means the agent is not associated with any instance — guide the user to the [DAS console settings](https://das.console.aliyun.com/?aes_debug=#/das-agent?currentView=settings) to associate instances.

3. **Include instance ID in questions**: DAS Agent resolves instances by ID (e.g., `rm-bp1xxx`, `pc-2zeyyy`). Always include the specific instance ID in the question for accurate results. If the user hasn't provided one, ask them or first query the instance list.

4. **Parallel execution**: When diagnosing multiple instances, launch multiple script processes in parallel — each invocation is independent and stateless (unless sharing a session ID).

5. **Multi-turn conversations — always reuse the session ID when questions are related**: If the user's questions are sequential or contextually connected (follow-up diagnostics, drill-down analysis, referencing a previous result, comparing findings), you **must** pass `--session <session_id>` on every subsequent call. Starting a new session mid-conversation forces the DAS Agent to re-run all prior context from scratch, wastes time, and produces lower-quality answers.

   **Decision rule**: Default to reusing the session ID. Only start a new session when the user explicitly switches to a completely unrelated topic or asks to "start over".

   The session ID is **server-assigned** and returned as the very first line of every `--pipe` invocation:
   ```
   SESSION: <uuid>
   ```
   Extract it immediately after each call and carry it forward. In `--json` mode it appears as `{"type": "session", "session_id": "..."}` on the first line.

   Examples of when reuse is **mandatory**:
   - "List my instances" → "Check CPU on the first one" → "Why is it high?"
   - "Run a health check on rm-bp1xxx" → "Show me the top slow queries"
   - "What locks are held?" → "Kill that session"

   The DAS Agent retains the full conversation history server-side, so follow-up questions can be short and natural — no need to repeat instance IDs or prior context.

## Output

For output mode comparison and format details, see [references/api-reference.md](references/api-reference.md).

**After running the script, relay the complete stdout to the user verbatim.** Do not summarize, paraphrase, or omit any part of the script's stdout. The DAS Agent's actual diagnostic answer is embedded in the output — the user must see it in full.

For detailed API signature and SSE event documentation, see [references/api-reference.md](references/api-reference.md).
