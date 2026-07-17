# RAM Permissions

This skill can call AgentLoop SearchContext endpoints with either AK/SK signing or ContextStore API Key auth.

Required RAM permissions:

For AK/SK mode, the configured identity must be allowed to call AgentLoop `SearchContext` for the target AgentSpace and ContextStore. API Key mode uses the direct mem0-compatible HTTP endpoint with `Authorization: Token ...`; it is authenticated by the receiving ContextStore service, not by RAM.

## Data Flow

When recall is enabled, `scripts/search_context.js` sends the following data to the configured AgentLoop SearchContext endpoint:

- `query`: the task, error, case, service, or goal text provided by the agent
- AK/SK mode: `context_type` (`experience` only in the current rollout), `limit`, `threshold`, `filter`, and `formatted`
- API Key mode: `top_k`, `threshold`, and `filters` for `/v2/memories/search`

The CLI requires `--confirm-outbound` or `AGENTLOOP_CONFIRM_OUTBOUND=true` before transmitting query data. Without confirmation, it exits before reading credential variables.

After confirmation, the CLI reads `AGENTLOOP_ACCESS_KEY` / `AGENTLOOP_ACCESS_SECRET` or `AGENTLOOP_BEARER_API_KEY` only from `~/.agentloop/recall.env`, the nearest project `.agentloop/recall.env`, or process environment variables. Secrets must not be passed as command-line arguments.

Use HTTPS endpoints for real credentials. Plain HTTP is accepted only for localhost tests and local adapters.
