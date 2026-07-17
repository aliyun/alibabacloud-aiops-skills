---
name: alibabacloud-dataworks-data-agent
description: >
  Interact with DataWorks Data Agent for conversational data analysis,
  session lifecycle management, and artifact download. Use this Skill when users
  want to chat with a Data Agent for data querying, create or resume Agent
  sessions, list session history, download analysis artifacts, check
  token usage, or cancel an active session.
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.4.5 with dataworks-public plugin >= 0.5.9.
  Credentials managed by aliyun CLI profiles.
metadata:
  domain: aiops
  owner: dataworks-team
  contact: dataworks-agent@alibaba-inc.com
---

# DataWorks Data Agent

Interact with DataWorks Data Agent via `aliyun dataworks-public` CLI.

## Prerequisites

- aliyun CLI >= 3.4.5: `aliyun version`
- dataworks-public plugin >= 0.5.9: `aliyun plugin list | grep dataworks`
- If plugin outdated: `aliyun plugin update aliyun-cli-dataworks-public`
- Verify profile: `aliyun configure list | grep <profile>`

## API Reference

| Action | Key Params |
|---|---|
| `create-agent-session` | `{"Meta":{"Agent":{"AgentName":"dataworks_data_agent"}},"ClientToken":"<uuid-v4>"}` |
| `prompt-agent-session` | `{"SessionId":"<id>","Prompt":[{"Type":"text","Text":"..."}]}` |
| `load-agent-session` | `{"SessionId":"<id>"}` |
| `list-agent-sessions` | `{"AgentName":"dataworks_data_agent","MaxResults":20}` |
| `list-agent-session-artifacts` | `{"SessionId":"<id>"}` |
| `get-agent-session-artifact-meta` | `{"SessionId":"<id>","ArtifactPath":"<path>"}` |
| `get-agent-session-token-usage` | `{"SessionId":"<id>"}` |
| `cancel-agent-session` | `{"SessionId":"<id>"}` |

## Usage

```bash
aliyun dataworks-public <action> --profile <profile> --region <region> --params '<JSON>' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

### Workflow

```bash
# 1. Create session (extract SessionId from $.JsonRpcResponse.Result.SessionId)
#    ClientToken ensures idempotency — retry with same token won't create duplicates
aliyun dataworks-public create-agent-session --profile default --region cn-shanghai \
  --params '{"Meta":{"Agent":{"AgentName":"dataworks_data_agent"}},"ClientToken":"<uuid-v4>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 2. Send prompt (reuse SessionId from step 1)
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Prompt":[{"Type":"text","Text":"your question"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 3. List artifacts
aliyun dataworks-public list-agent-session-artifacts --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 4. Download artifact (path must come from list result)
aliyun dataworks-public get-agent-session-artifact-meta --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","ArtifactPath":"<path>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 5. Load history
aliyun dataworks-public load-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 6. Check token usage
aliyun dataworks-public get-agent-session-token-usage --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 7. Cancel session
aliyun dataworks-public cancel-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

### Context & File Attachment

```bash
# With dataset context
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<id>","Prompt":[{"Type":"text","Text":"query"}],"Meta":{"Context":"{\"datasetUuid\":\"xxx\"}"}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# With file attachment
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<id>","Prompt":[{"Type":"text","Text":"analyze"},{"Type":"file","Name":"data.csv","Uri":"file:///path/to/data.csv"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

## Guidelines

- **Unclear intent** (MANDATORY): When the user's request is vague (e.g., "help me handle this") without specifying a clear action target (data analysis / session management), you MUST ask the user to clarify before calling any API. Do NOT guess or infer the intent — ask what they want to do and what specific data/target they need. Only proceed after the user provides clear instructions. Your final response MUST contain a direct question to the user (e.g., "What would you like to do?"). Do NOT end the task by writing a note or file about the vagueness — you MUST ask the user interactively.
- **Session reuse**: If the user mentions a previous conversation, check `list-agent-sessions` for non-RELEASED sessions and reuse the SessionId.
- **No active session** (MANDATORY): If the user states they haven't created a session, see Security Constraint #7.
- **Create session failure**: If `create-agent-session` returns empty or fails to return a SessionId after 2 attempts, fall back to `list-agent-sessions` to find an existing non-RELEASED session and reuse its SessionId. Do NOT retry create more than 2 times — the 3rd attempt is forbidden. Do NOT use RELEASED sessions for `prompt-agent-session` — they will return empty responses. If `list-agent-sessions` also returns only RELEASED sessions, report to the user: "Unable to create session and no active sessions available. Please retry later or check service status." and terminate the workflow immediately.
- **Empty response**: If `prompt-agent-session` returns a response with no content (empty `response` field or only `RequestId` without `agent_message_chunk`), you MUST: (1) Report to the user that the API returned an empty response — do not treat it as success. (2) AUTOMATICALLY retry with a more specific query (e.g., add time range or specific API name) — do NOT ask the user whether to retry, just do it. (3) If retry also returns empty, report the failure and suggest checking backend service status or session validity. Do NOT stop midway and ask the user for confirmation — the Agent should handle the retry autonomously. (4) If retry also returns empty, do NOT continue to list-agent-session-artifacts or any subsequent steps — terminate the workflow with the failure report.
- **Artifact paths**: Always call `list-agent-session-artifacts` first to get real paths before downloading. If `list-agent-session-artifacts` returns empty, report "no artifacts found" — do NOT call `get-agent-session-artifact-meta`.
- **Profile issues**: If the CLI returns an authentication error (not an empty response), inform the user and suggest `aliyun configure list` to verify profile configuration.

## Security Constraints

1. **Endpoint**: Only `*.aliyuncs.com` domains or localhost.
2. **Credentials**: Never read or display AccessKey/Secret/SecurityToken. Never read `~/.aliyun/config.json` or credential files with ANY method — including `cat`, `read_file`, `grep`, `python` scripts, `open()`, or shell commands. Suggest `aliyun configure list` instead. Never hardcode credentials in scripts or output files.
3. **Scope**: Only call the 8 Data Agent APIs listed above. Do NOT call other DataWorks OpenAPI (e.g., ListProjects, ListInstances, GetInstance, ListDags, etc.) — the Data Agent handles data analysis internally via `prompt-agent-session`. Your job is to create a session and send the user's query to the Data Agent, NOT to query DataWorks resources directly.
4. **File paths**: Only pass user data files. Never pass `/etc/`, `/proc/`, `~/.ssh/`, `~/.kube/`, `~/.aliyun/`.
5. **No env var modification**: Do NOT modify/unset environment variables (e.g., `ALIBABA_CLOUD_CLI_MOCK`) to bypass errors.
6. **No fake output**: When API fails, report the real error. Never simulate/fake output with echo or scripts.
7. **No active session**: If the user states they haven't created a session, you MUST immediately stop — do NOT call any API (including `list-agent-sessions`, `get-agent-session-token-usage`, `cancel-agent-session`), do NOT read config files, do NOT create scripts. Report "No active session" and suggest `create-agent-session`. RELEASED sessions are NOT active.

## Observability

All `aliyun dataworks-public` CLI calls must include the `--user-agent` flag for tracing:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/{session-id}
```

- **Session ID**: Generate a UUID v4 once per workflow and reuse it for all API calls within that workflow (e.g., `python3 -c "import uuid; print(uuid.uuid4())"`)
- **UA template**: `AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<uuid>`
- All API calls (create, prompt, list, load, token, cancel, download) must carry the same session-id within a single workflow
- Do NOT reuse session-id across separate user conversations

## References

- [API Reference](references/api-reference.md)
- [Examples](references/examples.md)
- [RAM Policies](references/ram-policies.md)
