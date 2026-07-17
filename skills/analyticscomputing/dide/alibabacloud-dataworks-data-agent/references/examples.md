# DataWorks Data Agent Examples

## Example 1: First Data Analysis

User: *"Analyze data quality of the orders table for the last 7 days"*

```bash
# 1. Create session (extract SessionId from $.JsonRpcResponse.Result.SessionId)
aliyun dataworks-public create-agent-session --profile default --region cn-shanghai \
  --params '{"Meta":{"Agent":{"AgentName":"dataworks_data_agent"}}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 2. Send prompt
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Prompt":[{"Type":"text","Text":"Analyze data quality of orders table for the last 7 days"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 3. List artifacts
aliyun dataworks-public list-agent-session-artifacts --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","MaxResults":50}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>

# 4. Download artifact (path must come from step 3)
aliyun dataworks-public get-agent-session-artifact-meta --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","ArtifactPath":"<path>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 2: Multi-turn Conversation (Session Reuse)

User follow-up: *"Give fix suggestions for the anomalies"*

```bash
# Reuse the same SessionId from Example 1
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Prompt":[{"Type":"text","Text":"Give fix suggestions for the anomalies"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

To find a previous session to reuse:

```bash
aliyun dataworks-public list-agent-sessions --profile default --region cn-shanghai \
  --params '{"AgentName":"dataworks_data_agent","MaxResults":20}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
# Find a non-RELEASED session and reuse its SessionId
```

---

## Example 3: Load Session History

User: *"Restore the context from my last conversation"*

```bash
aliyun dataworks-public load-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Meta":{"BeginLogOffset":0,"IsReload":true}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 4: Check Token Usage

User: *"How many tokens did this conversation consume?"*

```bash
aliyun dataworks-public get-agent-session-token-usage --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 5: Cancel Session

User: *"Terminate the current conversation"*

```bash
aliyun dataworks-public cancel-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 6: File Attachment Analysis

User: *"Analyze the sales data in this CSV file"*

```bash
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Prompt":[{"Type":"text","Text":"Analyze the sales data trends in this file"},{"Type":"file","Name":"sales_data.csv","Uri":"file:///path/to/sales_data.csv"}]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 7: With Dataset Context

User: *"Query data from my dataset"*

```bash
aliyun dataworks-public prompt-agent-session --profile default --region cn-shanghai \
  --params '{"SessionId":"<session-id>","Prompt":[{"Type":"text","Text":"Show recent records"}],"Meta":{"Context":"{\"datasetUuid\":\"xxx\"}"}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-data-agent/<session-id>
```

---

## Example 8: No Active Session

User: *"Check token usage for my session" (but user hasn't created one)*

Agent should:

1. Recognize the user hasn't created a session
2. Report: "No active session"
3. Suggest: `aliyun dataworks-public create-agent-session --params '{"Meta":{"Agent":{"AgentName":"dataworks_data_agent"}}}'`
4. Do NOT call `get-agent-session-token-usage` or `cancel-agent-session` without a valid SessionId
5. Do NOT search `list-agent-sessions` when the user explicitly states no session exists

---

## Example 9: Empty SSE Response Recovery

User: *"The response was empty, help me check why"*

Agent should:

1. Report the empty response to the user (do not treat as success)
2. AUTOMATICALLY retry with a more specific query (e.g., add time range or specific API name) — do NOT ask the user whether to retry
3. If retry also returns empty, report the failure and suggest checking backend service status or session validity
