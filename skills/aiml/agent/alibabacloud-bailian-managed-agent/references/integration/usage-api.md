# Managed Agent Usage: summaries and trends

Source: the complete Usage API contract supplied by the user on **2026-11-11**. The dated live probes below independently verify a subset in one **cn-beijing** workspace. The public documentation index did not establish a matching Usage operation page during this check; do not invent an official page URL or infer availability in other workspaces.

Use this API for workspace/Agent consumption, per-model and per-tool breakdowns, Session lifetime usage, and hourly/daily/monthly dashboards. For the older `GET /sessions/{id}` fields and token-cost examples, use [Session stats and usage](session-stats-and-usage.md). General Bailian model quota/Token Plan commands are a separate capability; `bl usage summary` is not evidence of support for these MA endpoints.

## Choose the scope

Both endpoints are **read-only queries using POST**, relative to the workspace-scoped `/api/v1/agentstudio` base URL, with `Authorization: Bearer …` and `Content-Type: application/json`. Initialize and propagate the [versioned User-Agent](../workflows/user-agent.md). Resolve the API key and endpoint as a pair; gateway identity determines the account/workspace. Body identity fields cannot switch workspaces.

| Endpoint / dimension | Required body fields | Optional fields | Omit |
| --- | --- | --- | --- |
| `/usage/summary`, `workspace` | `dimension`, `time_range` | `granularity` | Agent/Session filters; all pagination fields |
| `/usage/summary`, `agent` | `dimension`, `agent_id`, `time_range` | `agent_version`, `granularity` | `session_id`; all pagination fields |
| `/usage/summary`, `session` | `dimension`, `session_id` | None | Agent filters, `time_range`, `granularity`, pagination |
| `/usage/trend`, `workspace` | `dimension`, `time_range` | `granularity`, `page_size`, `page_token` | Agent/Session filters |
| `/usage/trend`, `agent` | `dimension`, `agent_id`, `time_range` | `agent_version`, `granularity`, `page_size`, `page_token` | `session_id` |

There is **no Session trend** and no Session time-window filter. Dimensions are lowercase and case-sensitive. IDs must be nonblank single strings. Agent versions are **strings**, even when Session metadata exposes a numeric version: convert `2` to `"2"`. Omission or `agent_version: null` merges all versions; empty/blank versions are invalid. Other strings match exactly without trimming (`" 2 "` does not mean `"2"`).

`time_range`, `granularity`, `page_size` and `page_token` reject explicit null. On the first trend request, **omit `page_token`** rather than passing null or an empty string. Body fields belong directly at the JSON root, not under `input` or `parameters`.

## Requests

Use the configured workspace, not the example IDs. The following summary returns the full aligned period and all model/tool detail groups:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 \
  -X POST "$AGENTSTUDIO_URL/usage/summary" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "dimension": "workspace",
    "time_range": {
      "start_time": "2026-11-02T10:15:30+08:00",
      "end_time": "2026-11-02T14:00:01+08:00"
    },
    "granularity": "hour"
  }'
```

For an Agent, change `dimension` to `agent`, add `agent_id`, and optionally add `"agent_version": "2"`. To query a Session, replace the entire body with:

```json
{"dimension": "session", "session_id": "sesn_xxx"}
```

For trends, change the path to `/usage/trend`, use the workspace/Agent body, and optionally add `"page_size": 1` to exercise pagination. Resource-list `limit/page/next_page` conventions do **not** apply here.

## Time range and granularity

`time_range.start_time` and `end_time` must be timezone-aware, second-precision RFC 3339; `Z` and numeric offsets are accepted. Nonzero seconds are valid. Unix timestamps, missing timezone and fractional seconds are invalid. End must be strictly later than start.

If `granularity` is omitted, use the **original** requested interval:

| Original interval | Actual granularity |
| --- | --- |
| At most 72 hours | `hour` |
| Over 72 hours, with end no later than start plus three calendar months in Beijing time | `day` |
| Longer | `month` |

Explicit `hour`, `day` or `month` overrides automatic selection; `minute` is unsupported. The service floors the start and ceils the end to complete Beijing-time buckets: hour boundaries, midnight, or the first day of the month. An end already on a boundary stays unchanged. All intervals are **[start, end)** and response times use `+08:00`.

For example, `10:15:30–14:00:01` with `hour` covers **10:00–15:00**, not only the exact requested seconds. Read `data.query_range` rather than relabeling results with the original boundaries. `query_range` is absent for Session summaries; Session usage covers its whole recorded lifetime.

## Response and accounting

Success uses `{"request_id": "…", "data": {...}}`. Summary data has `usage`, `data_updated_at`, and (workspace/Agent only) `query_range`. Trend data has `query_range`, `data_updated_at`, `granularity`, `points`, `has_more`, `next_page_token`. Each point has `start_time`, `end_time`, and `usage`.

Every `usage` contains `total`, `models[]` grouped by `model_name`, and `tools[]` grouped by **both** `source` and `tool_name`. Metrics are **objects**, e.g. `{"value": 1000, "unit": "tokens"}`, not plain numbers. Preserve unknown model/tool names and sources as null; do not drop their rows. Details have no guaranteed array order; trend points are ascending.

| `usage.total` metric | Unit / interpretation |
| --- | --- |
| `input_tokens`, `output_tokens`, `total_tokens` | `tokens`; total = input + output, or null when either is unknown |
| `cache_read_tokens`, `cache_creation_tokens` | `tokens`; already included in input, never add them again |
| `cache_hit_ratio` | `ratio`; cache reads / input, rounded to 8 decimal places; null for zero/unknown input or unknown cache reads |
| `model_call_count` | `count`; recorded model-request **end** events, including failed calls |
| `tool_call_count` | `count`; tool-call **starts**, including failed and unfinished calls |
| `builtin_tool_call_count`, `mcp_tool_call_count`, `custom_tool_call_count` | `count`; tool source breakdown |
| `turns` | `count`; `role=user` events |
| `steps` | `count`; one per model-request end and per tool-call start |
| `interrupt_error_count` | `count`; errors outside model/tool call failures |
| `model_failed_count`, `tool_failed_count` | `count`; model failures and confirmed tool failures |
| `runtime_ms` | `ms`; cumulative **settled running segments**, excluding unsettled segments |

Model detail `usage` contains the five token counters, `cache_hit_ratio`, `call_count`, `failed_count`. Tool detail `usage` contains only `call_count` and `failed_count`; tool sources are `builtin`, `mcp`, `custom` or null. Tool detail has no token or runtime metric. Integer-valued metrics are int64/null; ratios are numeric/null. Preserve int64 precision in clients that cannot represent all int64 values as native numbers.

`total`, `models` and `tools` are views of the same scope: do not sum total and detail together. Across buckets, recompute cache ratio from summed cache reads and inputs; do not sum or average ratios. Compare summary and trend only with matching filters, grain and returned range, complete pages, and a settled observation window.

The old Session GET fields use scalar `usage.cache_read_input_tokens` / `cache_creation_input_tokens`; Usage API uses nested `cache_read_tokens.value` / `cache_creation_tokens.value`. `runtime_ms` is not Session elapsed duration or a guaranteed live value of `stats.active_seconds * 1000`: the latter can include a current running interval. Completed-session equality in one sample does not establish equality during execution. This API supplies consumption, not monetary billing or real-time progress.

## Pagination, unknown data and freshness

- `page_size` is **1–100**, default 100, and counts complete time buckets, not detail rows. Return each bucket with all its model/tool groups.
- Continue only with the previous `next_page_token` passed unchanged as `page_token`. Keep identity, dimension, Agent/version, **original** boundaries, actual granularity and `page_size` fixed. Equivalent timezone spellings of the same absolute times are allowed; changing raw boundaries is not, even if they align to the same range.
- Each cursor lasts **15 minutes from generation**; retrying it does not extend expiry. HTTP 410 means discard the partial collection and restart without a cursor. Detect repeated cursors and enforce a page/deadline budget; a budget-limited collection is incomplete.
- `query_range` spans the **entire query** and stays the same across pages. `data_updated_at` refers to the current page; page values can differ.
- Cursors do not freeze a snapshot. Updates/backfills into already-read buckets may be missed on continuation. To refresh, start again from page one; short-lived caching can still delay visibility.
- No matching records: summary retains all metric objects and units with **null values**, `models=[]`, `tools=[]`, `data_updated_at=null`; workspace/Agent keep `query_range`. Trend returns `points=[]`, `has_more=false`, `next_page_token=null` while retaining range/grain.
- **Null is unknown, zero is a known zero.** A missing trend bucket is not automatically a zero bucket. Existing recorded buckets with zero/null metrics still appear. Show gaps/unknowns distinctly in dashboards; do not silently zero-fill.
- An existing Session without recorded usage returns HTTP 200 with unknown metrics. Session ownership is checked first; a missing/out-of-scope Session returns 404. An empty result alone does not prove the Session is missing.
- `data_updated_at` is the newest known source-record update represented in that response, not the request time or a completeness watermark. Recent calls can be absent; keep freshness visible in reports.

## Error handling

Business errors use `{"type":"error","error":{"code":"…","message":"…"},"request_id":"…"}`. Gateway authentication/routing errors instead put `code` and `message` at the root. Parse both, retain request IDs, and never log bearer keys.

| HTTP / code | Handling |
| --- | --- |
| 400 `invalid_parameter` | Fix dimension/field combination, type, timestamp or page-size validation. Explicit null cursor is in this category. |
| 400 `invalid_page_token` | Empty/blank/malformed cursor, or cursor bound to different query/identity. Omit it initially; preserve conditions when continuing. |
| 400 `query_limit_exceeded` | More than **100,000 combined model/tool detail rows** (totals excluded): summary limit is per entire query, trend limit per current page. Narrow summary scope/range; reduce trend page size or use a finer grain. There is no silent truncation or Top N fallback. |
| 401 `InvalidApiKey`; 403 `Endpoint.AccessDenied` | Resolve key/endpoint/workspace permissions; do not retry unchanged or silently switch workspace. |
| 404 `not_found` | Session absent or outside authenticated scope. |
| 410 `page_token_expired` | Restart pagination from scratch. |
| 429 `rate_limit` | Both endpoints share an account/workspace limiter. Reduce concurrency and use bounded backoff; do not load-test it by default. |
| 503 `service_unavailable`; 500 `internal_error` | Bounded retries for these read-only POST queries; preserve request IDs and report incomplete results on exhaustion. |

## Reproduce the read-only probes

[scripts/usage_smoke.py](../../scripts/usage_smoke.py) uses only Python's standard library. It previews by default and accesses credentials only with `--execute`. Supply an existing Agent and Session and a settled historical window with at least two recorded days to exercise pagination. Optional `--empty-session-id` tests an existing Session known to have no activity. No resources are created, mutated or deleted, and no Agent messages are sent.

```bash
python3 "$SKILL_ROOT/scripts/usage_smoke.py" \
  --start-time '2026-11-01T00:00:00+08:00' \
  --end-time '2026-11-11T00:00:00+08:00' \
  --agent-id "$AGENT_ID" --agent-version "$AGENT_VERSION" \
  --session-id "$SESSION_ID"
```

Add `--execute` for an authorized live test; use `AGENTSTUDIO_URL` + `DASHSCOPE_API_KEY`, or explicitly select a paired CLI JSON profile with `--bl-config /path/to/config.json`. Reuse this invocation's `BAILIAN_MANAGED_AGENT_SKILL_UA`; a standalone invocation generates a fresh UA. `--output /path/to/new-result.json` preserves safe metrics/checks/request IDs; existing files are not overwritten. The harness stops on authentication failure, throttling or service failure instead of amplifying them, and reports a page-budget stop as incomplete. Its fixed calendar-boundary probes use August–November 2026; the main aggregation window is configurable.

## Live evidence — 2026-11-11, one cn-beijing workspace

The final run completed **53 read-only API requests and 41 checks: 41 passed, 0 failed, 0 skipped**. Its summary request ID was `6fe5e93a-8609-990b-99ff-1910847be101`. These counts describe contract probes, including expected 400/404 responses, not model execution or throughput tests.

The historical range **2026-11-01 00:00 through 2026-11-11 00:00 (+08:00)** returned 519,041 input + 12,966 output = **532,007 tokens**, 54 model calls, 44 tool calls, 17 turns, 98 steps, and **494,698 ms** settled runtime. Two model groups and eleven tool groups were present. The latest represented source update was **2026-11-10 14:17:27 +08:00**.

- Daily trends with `page_size=1` yielded **three nonempty buckets across three pages**; every known additive total matched the summary. Missing days were omitted.
- Workspace, Agent, explicit-version Agent and Session queries succeeded. A completed Session returned **32,167 tokens**, 3 model calls, 3 tool calls, and **85,635 ms**; the previously read Session GET reported matching token counts and 85.635 active seconds for that completed sample.
- Cursor retry and equivalent UTC boundaries succeeded. Changed `page_size` or a one-second change to the original start returned `invalid_page_token`, despite unchanged aligned day boundaries.
- Second-precision and exact-boundary hour alignment, natural day/month alignment, and automatic-grain boundaries at 72 hours and three calendar months were checked.
- All-version/null version behavior, exact untrimmed version matching, no matching version, an existing empty Session, invalid combinations, unsupported minute/fractional seconds/missing timezone, invalid page sizes/cursors, and missing Session behavior were checked.
- **Observed cursor distinction:** null returns `invalid_parameter`; empty/whitespace/malformed strings return `invalid_page_token`. Both are HTTP 400. The first test harness incorrectly grouped blank strings with null; its expectations were corrected to the documented invalid-cursor category.

Scope limits: this is existing-record read-only validation, not generation-to-statistics ingestion testing. Cursor expiry after 15 minutes, the 100,000-detail limit, cross-workspace denial, forced throttling/service failures, active-session settlement, SDK/CLI support and other regions were **not** live-tested. Their behavior above comes from the supplied contract. Request IDs and pass counts are retained in the local run output; do not describe these untested branches as verified.
