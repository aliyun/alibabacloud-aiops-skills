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
| `ExtraInfo` | `--extra-info` | JSON string | No | The script requires a JSON object and always merges `{"mode":"readonly"}` into it |

The deployed request contract uses console source names. Prefer the exact matching product route; use `yaochi-console` only for RDS, an unknown product, or genuinely generic consultation. Do not shorten or invent a route.

The current DAS plugin does not expose image input, so the bundled script does not accept image keys.

## Readonly Contract

`ExtraInfo.mode == "readonly"` asks the service to filter write tools and block write APIs, and to omit the `humanConfirm` tool. The script always sends this mode and rejects any other `mode` value. Classification on the service side is based on API names, and some auxiliary tools are passed through, so describe readonly as the request contract rather than a universal guarantee. If a `humanConfirm` UI call still arrives, the script reports `[ReadonlyViolation]`, makes no confirmation call, and exits nonzero.

Resource changes and confirmation execution are outside this public release. No local write-command fallback is provided.

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
| UI calls | `UiFunctionCall`, `ui_function_call` | `humanConfirm` is treated as a readonly violation and never approved |
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
