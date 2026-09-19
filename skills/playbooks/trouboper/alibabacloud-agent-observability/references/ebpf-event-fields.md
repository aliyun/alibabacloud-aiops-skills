# eBPF Field Dictionary (SLS ebpf-event)

The eBPF side obtains AI system runtime facts (general model interaction +
process/file/network) from the `ebpf-event` logstore in an **SLS Project**. Field semantics align with the official specification [agent-event/agent-event-webtracking/ebpf-event Common Field Reference](https://help.aliyun.com/zh/document_detail/3049427.html).
This document records the **measured caliber** (2026-09-13, project `agentloop-ef42743ae9b83d77f199318578c66080`,
region `cn-hangzhou`), not documentation speculation.

## 1. Data Location and Access Method

- Collection: eBPF probe, writing to the `ebpf-event` logstore in an SLS project
- Access: `aliyun sls get-logs` (**read-only**; this skill only uses raw retrieval, **not server-side SQL** — reason see section 3)
- Binding: `--project` (can only be provided by the user; the skill has no auto-discovery mechanism)

## 2. Declared Index Fields (43 fields, server-side queryable)

All index keys returned by `aliyun sls get-index` in practice. **This is the only field set that can be referenced by server-side queries**:

| Group | Fields | Type |
|---|---|---|
| Event Identity | `event.id` / `event.name` | text |
| Time | `time_unix_nano` / `observed_time_unix_nano` | long |
| Host/Container | `host.id` / `host.name` / `host.ip` / `container.id` / `__tag__:__hostname__` / `__source__` | text |
| Error | `error.type` / `error.message` | text |
| Agent | `gen_ai.agent.id` / `gen_ai.agent.name` / `gen_ai.agent.type` | text |
| Session Hierarchy | `gen_ai.session.id` / `gen_ai.turn.id` / `gen_ai.turn.start` / `gen_ai.turn.end` / `gen_ai.step.id` | text |
| Model | `gen_ai.provider.name` / `gen_ai.request.model` / `gen_ai.response.model` / `gen_ai.response.id` / `gen_ai.response.finish_reasons` | text |
| Token | `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` / `gen_ai.usage.total_tokens` / `gen_ai.usage.cache_read.input_tokens` / `gen_ai.usage.cache_creation.input_tokens` | long |
| Tool | `gen_ai.tool.name` / `gen_ai.tool.call.id` / `gen_ai.tool.call.exec.id` / `gen_ai.tool.call.duration` (long) / `gen_ai.tool.call.arguments` (json) / `gen_ai.tool.call.result` (json) / `gen_ai.tool.definitions` (json) | text/json/long |
| Messages | `gen_ai.input.messages` (json) / `gen_ai.input.messages_delta` (json) / `gen_ai.output.messages` (json) / `gen_ai.system_instructions` (json) | json |
| Other | `gen_ai.skill.name` / `gen_ai.user.id` | text |

There are also **line-level (full-text) indexes**.

## 3. Actual Population Status (Key: Does Not Match Index Declarations)

Measured over 30 days, this logstore has **only 6 rows**, with `event.name` being only `http.request` / `http.response`;
searching `gen_ai.session.id: *` returns **0 rows**. That is:

- **The entire set of `gen_ai.*` index fields in section 2 has never been populated in that environment**. `trace_overview.py --mode ebpf`'s
  `genai_index_coverage` counts per key; all zeros means the collector only produces runtime facts, not GenAI attributes — **this is a gap discovery, not a script bug**.
- Therefore the eBPF side **does not provide Session/Turn/Step insights**; that portion must go through the LoongSuit side
  (the LoongSuit field dictionary).

## 4. Fields Present in Measured Rows But Not Indexed (Runtime Fact Body)

These fields exist in real rows but are **not in the section 2 index set**, so doing `group by` on them will be rejected by SLS
(measured: `group by "agent.type"` directly errors). Therefore this skill always uses **raw retrieval + client-side aggregation** for the eBPF side:

| Group | Fields | Description |
|---|---|---|
| Agent | `agent.type` | Measured values like `qwenpaw` |
| Process | `pid` / `comm` / `cmdline` | Process fact body |
| Event Order | `event.sequence` | Ordering tie-break within the same exchange |
| HTTP Pairing | `http.exchange.id` | **The unique key for pairing request and response** |
| HTTP Request | `http.request.method` / `url.path` / `url.scheme` / `server.address` / `user_agent.original` / `http.request.header.traceparent` | |
| HTTP Response | `http.response.status_code` / `http.response.body.content` / `http.response.body.size` / `http.response.header.*` / `is_sse` | |
| k8s | `__tag__:_cluster_id_` / `__tag__:_node_name_` / `__tag__:_node_ip_` | |

## 5. Correlation Keys

- **`http.request.header.traceparent`**: W3C format `00-<32hex trace_id>-<16hex parent_span_id>-<flags>`.
  This is the **only key** for linking the eBPF side to the LoongSuit side, supporting two-level correlation:
  - **trace-level**: `trace_id` <-> LoongSuit `traceId` (coarse-grained; can only say "these network calls are in this trace")
  - **span-level (precise)**: the third segment `parent_span_id` is **the id of the span that initiated the call**; when it equals the LoongSuit
    `spanId`, it can locate "which external calls this span itself initiated". The `runtime_calls` section output by `decision_evidence.py`
    (`--mode both --span-id <id>`) uses this correlation.
  > **Measured finding**: This header **only appears on `http.request` rows**; `http.response` rows do not have it. So
  > `sls_event.link_by_exchange()` uses `http.exchange.id` to propagate the `trace_id` and
  > `parent_span_id` parsed from the request side to the paired response row (labeled `trace_id_from: "exchange"`); otherwise all response rows
  > would fall into "ungrouped".
  > Also, this header **is not in the full-text index**; measured bare 32-hex term server-side retrieval returns 0 rows, so `--trace-id`
  > can only be **client-side filtered**, not pushed down.
  >
  > **Match rate is measured, not assumed**: `runtime_calls.match.span_match_rate` gives
  > the span-level hit proportion. **A low match rate means the probe did not carry this span's id; it does not mean the call does not exist** — in that case,
  > the `trace_only` section still lists calls from the same trace, but they cannot be attributed to a specific span.
- **Cannot use application-layer request id for correlation**: neither side has `gen_ai.request.id` (`gen_ai.request.*` measured
  only has `.model`), so the path of aligning `http.exchange.id` with some `gen_ai.*` attribute **does not exist**; do not attempt it.
- **`http.exchange.id`**: pairs request <-> response, used for calculating per-exchange latency and status codes.
- `pid` (+`comm`/`cmdline`) = process; `container.id` = container; `host.*` = host; `__tag__:_cluster_id_` =
  k8s cluster.

## 6. Narrowing (Application Narrowing)

**The index has no `service.name`, nor `__tag__:__service_name__`**. Therefore:

- `--service-name` **cannot take effect** on the eBPF side; the script always outputs `service_filter_unavailable: true` with a
  note (the LoongSuit side is still narrowed).
- eBPF side alternatives: `--container-id` / `--host` / `--event-name` (indexed, **server-side** filtering),
  `--agent-type` / `--comm` / `--trace-id` (not indexed, **client-side** filtering), `--match`
  (scans `url.path` / `cmdline` / `user_agent.original`, client-side).

## 7. Sampling Cap

Single raw retrieval per logstore has a cap of `sls_event.EBPF_FETCH_CAP = 2000` rows (each `get-logs` returns <=100 rows,
paginated with `--offset`). When the cap is hit, output carries `fetch_truncated: true` — **at this point all counts are sampled, not full**; the report
must declare this. Narrowing the slice or adding `--container-id`/`--agent-type` filters is the correct approach; do not widen the window span.

## 8. Other Logstores in the Same Project (Not Included in This Phase)

Measured: this project has 9 logstores total, of which `agent-trajectory` (1084 rows in 30 days) is a materialized trajectory store
(containing `trajectory_id` / `session_id` / `turn_id` / `trace_id` / `step_count` / `tool_calls` /
`model_calls` / `source_kind=otel_trace`). **Not included in this phase**; must not infer current caliber from it.
