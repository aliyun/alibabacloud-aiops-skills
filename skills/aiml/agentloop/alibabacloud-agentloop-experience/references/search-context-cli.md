# SearchContext CLI

## Command

```bash
node scripts/search_context.js search \
  --query "current task description" \
  --context-type experience \
  --confirm-outbound \
  --limit 5 \
  --threshold 0.6 \
  --filter-json '{}'
```

## Arguments

Required:

- `--query`: recall query text. Keep it concise and grounded in the current task, error, system, case, or user request.
- `--context-type`: currently only `experience` is supported for prior task-solving examples. `memory` is reserved for a future rollout and should not be used.
- `--confirm-outbound`: explicit per-request confirmation that query data may be sent to the configured endpoint.

Optional:

- `--limit`: maximum result count, default `5`.
- `--threshold`: recall threshold, default `0.6`.
- `--filter-json`: JSON object string with extra filters, default `{}`.
- `--help`: print JSON help, supported both as `node scripts/search_context.js --help` and `node scripts/search_context.js search --help`.

Secrets must never be passed as CLI arguments.
Without `--confirm-outbound` or `AGENTLOOP_CONFIRM_OUTBOUND=true`, the CLI returns an error before reading credential variables or calling the endpoint.

## Configuration

Copy `assets/recall.env.example` to one of:

- `~/.agentloop/recall.env`
- `<project>/.agentloop/recall.env`

The project-level file must be ignored by git:

```gitignore
.agentloop/recall.env
```

Configuration is loaded in this order, with later sources overriding earlier sources:

1. User config: `~/.agentloop/recall.env`
2. Project config: the nearest `.agentloop/recall.env` found by walking from the current directory upward
3. Current process environment variables

Supported variables:

- `AGENTLOOP_ENABLE_RECALL`: `true` or `false`. When not `true`, the CLI returns an empty successful result and does not call the endpoint.
- `AGENTLOOP_RECALL_ENDPOINT`: AgentLoop Recall or SearchContext HTTP endpoint.
- `AGENTLOOP_CONFIRM_OUTBOUND`: optional automation setting. When `true`, permits outbound recall without passing `--confirm-outbound`; set only after user or operator approval.
- `AGENTLOOP_ACCESS_KEY`: Alibaba Cloud access key for AK/SK signed requests.
- `AGENTLOOP_ACCESS_SECRET`: Alibaba Cloud access secret for AK/SK signed requests.
- `AGENTLOOP_BEARER_API_KEY`: ContextStore API Key copied from the Memory/Experience store API Key tab. The CLI sends it as `Authorization: Token ...`.

## HTTP Request

When enabled with AK/SK, the CLI sends a `POST` request to `AGENTLOOP_RECALL_ENDPOINT` with JSON:

```json
{
  "query": "current task description",
  "context_type": "experience",
  "limit": 5,
  "threshold": 0.6,
  "filter": {},
  "formatted": true
}
```

The CLI supports two auth modes:

- AK/SK: set `AGENTLOOP_ACCESS_KEY` and `AGENTLOOP_ACCESS_SECRET`. The CLI sends Alibaba Cloud ROA signed headers, including `Date`, `Content-MD5`, `x-acs-signature-*`, and `Authorization: acs ...`.
- API Key: set `AGENTLOOP_BEARER_API_KEY`. The CLI sends a plain HTTP request following the console Memory store integration example: `Authorization: Token ...`.

API Key mode calls the mem0-compatible direct search endpoint. If `AGENTLOOP_RECALL_ENDPOINT` is a ContextStore path such as `/agentspace/{workspace}/contextstore/{store}/context/search`, the CLI uses the same origin but posts to `/v2/memories/search` with JSON:

```json
{
  "query": "current task description",
  "top_k": 5,
  "threshold": 0.6,
  "filters": {}
}
```

When both modes are configured, a complete AK/SK pair takes priority. If either AK or SK is missing, the CLI falls back to API Key auth when `AGENTLOOP_BEARER_API_KEY` is set.

Use HTTPS endpoints for real credentials. The CLI rejects plain HTTP endpoints unless the host is `localhost`, `127.0.0.1`, or `::1`.

## Output

Success:

```json
{
  "request_id": "...",
  "error": null,
  "results": [
    {
      "title": "...",
      "summary": "...",
      "content": "...",
      "metadata": {}
    }
  ]
}
```

Recall disabled:

```json
{
  "request_id": "...",
  "error": null,
  "results": []
}
```

Failure:

```json
{
  "request_id": "...",
  "error": "missing AGENTLOOP_RECALL_ENDPOINT",
  "results": []
}
```

The CLI never prints `AGENTLOOP_ACCESS_SECRET`. It normalizes common response shapes by accepting `results`, `data.results`, or `data.items`.
