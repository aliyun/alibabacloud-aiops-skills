# GetYaoChiAgent API Reference

## API and CLI Mapping

| Item | Value |
|---|---|
| Product | Database Autonomy Service (DAS) |
| API version | `2020-01-16` |
| Action | `GetYaoChiAgent` |
| Request | `POST /agent` |
| CLI plugin | `aliyun-cli-das` |
| CLI command | `aliyun das get-yao-chi-agent` |
| Default endpoint | `das.cn-shanghai.aliyuncs.com` |
| RAM action | `hdm:GetYaoChiAgent` |
| Resource scope | `*` |

Official documentation: [GetYaoChiAgent](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-getyaochiagent)

## Request Parameters

| OpenAPI | CLI | Type | Required | Notes |
|---|---|---|---|---|
| `Query` | `--query` | string | Yes | Natural-language request; include product, region, resource ID, and time range when relevant |
| `SessionId` | `--session-id` | UUID string | No | Omit on the first turn; reuse the returned value for related follow-ups |
| `Source` | `--source` | string | No | Select the matching known-product route; RDS and generic consultation use `yaochi-console` |
| `ExtraInfo` | `--extra-info` | JSON string | No | The script requires a JSON object and passes explicit `{"mode":"readonly"}` through unchanged |

Pass the canonical console routes below to the helper. It validates the route locally with `--cli-dry-run` before any agent request. Plugins that accept console names retain them; when the plugin explicitly rejects a source enum, the helper probes an explicit equivalent short name (`yaochi`, `polardb`, `tair`, `mongodb`, `lindorm`, `polarx`, or `dbs`). Only a successful local probe selects that alias. The canonical route still controls operation approval. Follow-ups use the same canonical route and returned SessionID; do not update plugins during a conversation. Unmapped routes, including `polardb-pg-console`, must be accepted as-is or fail with a compatibility error; they never fall back to a different product. Do not shorten or invent routes manually.

The current DAS plugin does not expose image input, so the bundled script does not accept image keys.

## Readonly Contract

The helper uses the standard session when no mode is supplied. Explicit
`ExtraInfo.mode == "readonly"` asks the service to filter write tools for
read-only requests. It is not a universal guarantee about every auxiliary
tool. In either mode, a confirmation card without a matching approved plan
does not receive a callback. The approved operation path omits the mode
and is limited to the exact local and server-side allowlists.

Only the operations listed in [the operation contract](related-commands.md#confirming-an-operation) may receive approval. No local write fallback is provided.

## Supported Source Routes

| Source | Route |
|---|---|
| `yaochi-console` | Cross-product intent routing |
| `polardb-console` | PolarDB MySQL |
| `polardb-pg-console` | PolarDB PostgreSQL |
| `tair-console` | Tair / Redis |
| `mongodb-console` | MongoDB |
| `lindorm-console` | Lindorm |
| `polarx-console` | PolarDB-X |
| `dbs-console` | DBS |
| `gpdb-console` | AnalyticDB PostgreSQL |
| `adbmysql-console` | AnalyticDB MySQL |
| `clickhouse-console` | ClickHouse |
| `selectdb-console` | SelectDB |
| `dts-console` | DTS |

Prefer the matching source for known-product queries: PolarDB MySQL -> `polardb-console`, PolarDB PostgreSQL -> `polardb-pg-console`, Tair/Redis -> `tair-console`. RDS has no registered dedicated source in the current route set, so it remains on `yaochi-console`; do not invent `rds-console`.

## Account / Source Concurrency

The service contract permits **2 concurrent requests per cloud account and source**. All conversations and callers sharing that account/source share the allowance, including separate evaluation sandboxes. Regions and SessionIDs do not partition this budget. Related follow-ups keep the same source; they are sequential and reuse only their actual returned SessionID.

Schedule known products on their corresponding source and limit each account/source group to 2 active calls. Cross-product inventory uses independent product queries with the exact routes above. On `Throttling.UserConcurrentLimit`, wait for capacity on that account/source rather than repeatedly retrying or switching to an unrelated route. The Bash wrapper does not implement a distributed account-wide semaphore; its process-local state cannot coordinate independent sandboxes.

## Response Events

The DAS plugin can expose the stream in any of these forms:

```text
{"data":{"Content":"...","SessionId":"..."}}
data: {"Content":"...","SessionId":"..."}
{"content":"...","session_id":"..."}
done
```

Field casing varies between the public OpenAPI schema, plugin wrapper, and backend JSON Lines. The script accepts both forms.

| Logical field | Possible names | Handling |
|---|---|---|
| Answer delta | `Content`, `content` | Concatenate to stdout in arrival order |
| Reasoning delta | `ReasoningContent`, `reasoning_content` | Only write to stderr with `--debug` |
| Conversation ID | `SessionId`, `session_id`, `sessionId` | Write as `[SessionID] ...` on stderr |
| Tool calls | `FunctionCall`, `function_call` | Debug progress only |
| UI calls | `UiFunctionCall`, `ui_function_call` | Readonly: violation, no callback. Operation: check against the exact approved plan before sending a decision |
| Sub-agent calls | `SubAgentCall`, `sub_agent_call` | Debug progress only |
| Request ID | `RequestId`, `requestId` | Include in structured errors when available |
| Heartbeat | `heartbeat` | Ignore when no content is present |

Completion can be the bare line `done`, SSE data `[DONE]`, a JSON done marker, or a normal EOF after at least one valid response event. For normal EOF, success also requires aliyun CLI exit code 0; an empty stream, parser error, or nonzero CLI exit is not completion.

## Command Shape

```bash
aliyun das get-yao-chi-agent \
  --query "<natural-language query>" \
  --source yaochi-console \
  --extra-info '{"mode":"readonly"}' \
  --endpoint das.cn-shanghai.aliyuncs.com \
  --read-timeout 180 \
  --connect-timeout 30 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-apsaradb-agent/<fresh-session> skill-version/<skill-version>"
```

Use `scripts/call_apsaradb_agent.sh` instead of assembling this command manually.

## Secrets

Passwords, tokens, AccessKeys, credentials, private keys, and other secrets must not enter `Query`, `ExtraInfo`, local command arguments, logs, or artifacts. The script rejects queries and metadata that appear to contain such values. Perform secret-bearing changes and connection tests only through the Alibaba Cloud console or another secure secret-entry channel.

## CreateYaoChiAgentConfirm

Use the official DAS `create-yao-chi-agent-confirm` plugin command in the helper.
The callback uses the pending card's `ConfirmationId` and originating stream
`SessionId`, with the same profile, endpoint, and versioned User-Agent as the
query. The boolean `Approved` records the decision. Do not send `ToolArgs`.
The response must echo the ID and decision; it does not prove the operation
succeeded. Read the original stream to its terminal event and verify the
resource state with a separate readonly request.

[Official DAS OpenAPI catalog](https://api.aliyun.com/document/DAS)
