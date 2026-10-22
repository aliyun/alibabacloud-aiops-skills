# Get Session: duration and usage

Use this reference to interpret response fields from the [Get Session API](https://docs.agent.bailian.aliyun.com/zh/api/managed-agents/session/get) (`GET /sessions/{session_id}`), analyze cache usage, and estimate token costs.

Source: product clarifications provided by the user on 2026-09-20, supplementing accounting definitions not fully explained in the existing API documentation. The examples below are illustrative data, not results of new live tests performed by this skill.

## Field definitions

`stats` describes session duration, and `usage` describes cumulative usage across recorded model calls within the session. Neither represents a single request.

| Field | Type | Meaning |
| --- | --- | --- |
| `stats` | object | Session duration statistics. |
| `stats.active_seconds` | number | Cumulative time in seconds that the session has spent in the `running` state, excluding time in the `idle` state; not model inference time alone. |
| `stats.duration_seconds` | number | Total elapsed time in seconds from session creation to the statistics cutoff, including both running and idle time. |
| `usage` | object | Cumulative token usage across recorded model calls within the session. |
| `usage.input_tokens` | integer | Cumulative input tokens, including ordinary input, cache reads, and cache creation. |
| `usage.output_tokens` | integer | Cumulative output tokens. |
| `usage.cache_read_input_tokens` | integer | Cumulative input tokens served from cache. |
| `usage.cache_creation_input_tokens` | integer | Cumulative input tokens used to create new explicit caches. |

**Duration cutoff rules**: when the session is not running, the cutoff is the timestamp of the last activity event. While the session is running, the current running interval is included, subject to limits based on the last activity event timestamp and the system grace period. Therefore, `duration_seconds` is not always the query time minus the creation time. Do not infer a specific value for the system grace period from this description.

## Token accounting

The following relationships use **DashScope / Qwen accounting conventions**:

```text
总输入 tokens = 普通 tokens + 缓存读取 tokens + 缓存创建 tokens
普通 tokens = input_tokens − cache_read_input_tokens − cache_creation_input_tokens
总 tokens = input_tokens + output_tokens
```

Cache reads and cache creation are already included in total input tokens; do not add them again. Session usage accumulates tokens across model calls, rather than counting tokens in the deduplicated final conversation.

## Example 1: implicit cache hits

Assuming explicit caching is not enabled for this session, the following data shows cumulative implicit cache hits:

```json
{
  "stats": {
    "active_seconds": 38.738,
    "duration_seconds": 246.296
  },
  "usage": {
    "input_tokens": 88422,
    "output_tokens": 897,
    "cache_read_input_tokens": 74240,
    "cache_creation_input_tokens": 0
  }
}
```

| Metric | Result |
| --- | --- |
| Cumulative running time | 38.738 seconds |
| Total elapsed time | 246.296 seconds |
| Total input tokens | 88,422 |
| Cache read tokens | 74,240 |
| Cache creation tokens | 0 |
| Ordinary input tokens | 88,422 − 74,240 − 0 = **14,182** |
| Output tokens | 897 |
| Total tokens | 88,422 + 897 = **89,319** |

Implicit caching usually does not report cache creation separately. A cache creation count of 0 does not rule out explicit caching that only reads an existing cache; check the request configuration to distinguish these cases.

## Example 2: explicit cache creation and hits

```json
{
  "stats": {
    "active_seconds": 974.883,
    "duration_seconds": 975.246
  },
  "usage": {
    "input_tokens": 329173,
    "output_tokens": 15984,
    "cache_read_input_tokens": 281341,
    "cache_creation_input_tokens": 47748
  }
}
```

| Metric | Result |
| --- | --- |
| Cumulative running time | 974.883 seconds |
| Total elapsed time | 975.246 seconds |
| Total input tokens | 329,173 |
| Cache read tokens | 281,341 |
| Cache creation tokens | 47,748 |
| Ordinary input tokens | 329,173 − 281,341 − 47,748 = **84** |
| Output tokens | 15,984 |
| Total tokens | 329,173 + 15,984 = **345,157** |

A cumulative creation count greater than 0 means explicit cache creation occurred within the reporting scope; a cumulative read count greater than 0 means cache hits also occurred. These may come from different model calls.

## Billing notes

```text
输入费用 = 普通 tokens × 普通输入单价
         + 缓存读取 tokens × 缓存读取单价
         + 缓存创建 tokens × 缓存创建单价

Token 总费用 = 输入费用 + 输出 tokens × 输出单价
```

- If unit prices are quoted per million tokens, divide the calculated amount by 1,000,000.
- Cache read prices depend on the model and whether caching is explicit or implicit.
- If the session uses different models or pricing tiers, calculate the cost of each call separately and then sum the costs; do not apply a single unit price to the entire session's cumulative usage.
- `stats` contains duration statistics and is not directly used in the formulas above, which calculate token costs only.

See the [Bailian cache billing documentation](https://docs.bailian.console.aliyun.com/zh/model-studio/context-cache) for detailed rules. Verify current unit prices for the relevant model and caching method when preparing an actual quote.
