# LoongSuit Field Dictionary (CMS 2.0 UModel)

The LoongSuit side obtains Agent trajectory data (including cross-Agent call traces) from **CMS 2.0 workspaces** via **UModel `GetEntityStoreData`** (SPL umodel mode): native Session / Turn / Step and framework state. Field semantics align with the official specification [LLM Trace Field Definition](https://help.aliyun.com/zh/document_detail/3046157.html) (OTel GenAI semantic convention extension). This document also records measured deviations (2026-09-13, workspace `default-cms-1543428740671114-cn-hangzhou`). When the specification is upgraded, re-measure first before updating this document.

## 1. Data Location and Access Method

- Probe: LoongSuit pilot / language framework probe (OTel GenAI instrumentation); data lands in CMS 2.0 workspaces
  (`--workspace`; console label: **Cloud Monitor 2.0 Workspace**)
- Access: via CMS 2.0 UModel; **does not read SLS directly or call ARMS** (ARMS dependency has been completely removed):
  ```bash
  aliyun cms get-entity-store-data --api-version 2024-03-30 \
    --workspace <workspace name> --from <unix seconds> --to <unix seconds> --query <SPL> \
    --region <region> --user-agent <UA>
  ```
- SPL syntax, dataset name (`.trace_set with (domain='apm', name='apm.trace.common')`), and pipe command denylist
  see the CMS UModel query reference
- `--workspace` is a **real query parameter**; time parameters are **unix seconds** (note: different from the millisecond caliber of the ARMS era; no conversion needed)

## 2. Response Structure (Measured)

`GetEntityStoreData` returns `{header: [...], data: [[...], ...]}`; `data` is a row array, positionally corresponding to `header`.
Projected span row fields:

| Field | Description |
|---|---|
| `traceId` / `spanId` / `parentSpanId` | Lineage triplet; root span parent is `""` or sentinel `0000000000000001` |
| `spanName` | Span name (e.g., `chat kilo-auto/free`, `react step`, `execute_tool Bash`) |
| `startTime` / `endTime` / `duration` | **Nanoseconds** (different from the old ARMS millisecond caliber; no conversion needed) |
| `serviceName` | Reporting application name (basis for cross-Agent view; can be server-side filtered) |
| `kind` | OTel SpanKind numeric value |
| `statusCode` / `statusMessage` | OTel status: `0`=UNSET, `1`=OK, **`2`=ERROR** (measured distribution 15198/9/115). Filtering must use `cast(statusCode as bigint) = 2` |
| `attributes` | JSON string, i.e., OTel attributes (including all `gen_ai.*`) |
| `resources` | JSON string, resource labels (measured to contain `service.name` / `acs.cms.workspace` / `telemetry.sdk.language` / `ipv4`) |
| `events` / `traceState` | Framework internal fields; not used by the skill |

**The returned rows are already in the downstream-shared span-row shape**, so `cms_trace.cms_span_to_row()` is essentially a pass-through (only adds a derived `error` boolean); no key name mapping is needed. Three-tier error determination: `statusCode=2` -> `gen_ai.response.finish_reasons` contains `error` -> `otel.status_code` in attributes.

> **Measured finding: `gen_ai.step.id` has never been populated** (0 non-empty rows within a 30-day window). The step hierarchy can only be derived from `gen_ai.span.kind=STEP` (9716 spans measured) + parent-child lineage. Script output labels `step_id_source: "span.kind+lineage"`; **step ids are not fabricated**. Other hierarchy fields are available: `gen_ai.session.id` 36098 rows, `gen_ai.turn.id` 29352 rows.

## 3. Official Field Specification (doc 3046157)

### 3.1 Common Attributes and Resources

| Attribute | Meaning | Requirement Level |
|---|---|---|
| `gen_ai.session.id` | Session ID | Conditionally Required |
| `gen_ai.user.id` | End-user identifier | Conditionally Required |
| `gen_ai.span.kind` | Operation type (see 3.2) | Required |
| `gen_ai.operation.name` | Operation secondary type (see 3.2) | Required |
| `gen_ai.framework` | Framework type (langchain/llama_index...) | Conditionally Required |

Resources: `service.name` (application name, Required), `acs.cms.workspace`, `acs.arms.service.id`, `ali.trace.source`, `acs.arms.service.feature=genai_app` (AI application identifier, Required).

`service.name` is the **application name** in the console's "AI Applications" list, and also the narrowing key on the LoongSuit side: the script pushes the clarified `--service-name` as a CMS SPL `serviceName = '<application name>'` predicate to the server side (exact equality). The same semantics **do not have a corresponding column** on the eBPF side (the ebpf-event index has neither `service.name` nor `__tag__:__service_name__`; see the eBPF field dictionary), so `--service-name` cannot take effect on that side and always labels `service_filter_unavailable`; **there is no `gen_ai.service.name` in the GenAI attributes**.

### 3.2 span.kind <-> operation.name Mapping

| gen_ai.span.kind | gen_ai.operation.name | Semantics |
|---|---|---|
| ENTRY | `-` (not defined in spec; measured probes report `enter`) | Application call entry |
| AGENT | `invoke_agent` / `create_agent` | Agent invocation |
| STEP | `react` | ReAct round (Reasoning-Acting iteration) |
| LLM | `chat` / `generate_content` / `text_completion` | Model invocation |
| TOOL | `execute_tool` | Tool invocation |
| CHAIN | (workflow/task) | Chain (LangChain) |
| RETRIEVER | `retrieval` | Document retrieval |
| EMBEDDING | `embeddings` | Embedding |
| TASK | `run_task` | Internal custom method |
| RERANKER | - | Reranking |

The skill's agent behavior analysis focuses on the first five (enter/invoke_agent/react/chat/execute_tool); other types, if they appear in ARMS details, are passed through as ordinary nodes.

> All enumeration queries use `gen_ai.span.kind` as the condition, not `gen_ai.operation.name`: ENTRY's operation.name is `-` in the field definition (the community has no semantic specification for this span type yet; the value may change in the future); span.kind is the stable key.

### 3.3 Key Attributes by Type

**ENTRY (`enter`)**: `gen_ai.session.id`, `gen_ai.user.id`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.response.time_to_first_token` (streaming first packet, ns)

**AGENT (`invoke_agent`)**: `gen_ai.agent.id/name/description`, `gen_ai.conversation.id`, `gen_ai.usage.{input,output,total}_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_creation.input_tokens`, `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions`, `gen_ai.response.time_to_first_token`

**STEP (`react`)**: `gen_ai.react.round` (round number, auto-incrementing from 1), `gen_ai.react.finish_reason` (reason for ending this round, e.g., `tool_calls`/`stop`/`error`)

**LLM (`chat`)**: `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.request.{max_tokens,temperature,top_p,top_k,frequency_penalty,presence_penalty,stop_sequences,seed}`, `gen_ai.response.{id,model,finish_reasons}`, `gen_ai.response.time_to_first_token` (ns), `gen_ai.response.reasoning_time` (ms), `gen_ai.usage.*` (same as AGENT), `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.tool.definitions`, `gen_ai.latency.time_in_model_{prefill,decode,inference}`

**TOOL (`execute_tool`)**: `gen_ai.tool.name`, `gen_ai.tool.type` (function/extension/datastore), `gen_ai.tool.call.id`, `gen_ai.tool.description`, `gen_ai.tool.call.arguments` (JSON string), `gen_ai.tool.call.result` (JSON string), `gen_ai.skill.{id,name,description,version}` (for Skill-type tools)

**messages format** (`gen_ai.input.messages` / `gen_ai.output.messages`): `[{"role": "user|assistant|system|tool", "parts": [{"type": "text|reasoning|tool_call|tool_call_response", "content": "..."}]}]`; the `reasoning` part carries the model chain-of-thought and is the data foundation for "observable reasoning process". Message content collection is controlled by the probe switch `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` (enabled by default).

## 4. Typical Hierarchy

```
enter (ENTRY)
+-- invoke_agent (AGENT)          <- usage aggregated values, including cache_read
    +-- react round=1..N (STEP)
        +-- chat {model} (LLM)    <- tokens/TTFT/finish_reasons
        +-- execute_tool {tool} (TOOL) x N
```

Cross-Agent calls: sub-agent spans carry **different `service.name`**, hanging under the parent chain; `services` deduplicated > 1 indicates a cross-Agent trace.

## 5. Measured Deviations and Pitfalls (qwenpaw environment; must follow)

1. **Three-tier error determination**: `ResultCode` is always -1 and unreliable. Determination order: tag `error.type`/`error.message` exists -> `gen_ai.response.finish_reasons` contains `"error"` -> OTel status ERROR (the script normalizes `otel.status_code=ERROR`/statusMessage in TagEntryList to `statusCode="2"`). Measured error spans' statusMessage carries the exception class name (e.g., `CancelledError`, `RemoteProtocolError`).
2. **Details contain non-GenAI framework spans**: no `gen_ai.operation.name`, 0ms leaf/intermediate nodes. `trace_chain.build_tree` collapses them (children inherit depth), `decision_evidence` ancestor chain/sibling filters; do not include them in GenAI statistics during analysis.
3. **TTFT coverage is incomplete**: some models do not report `gen_ai.response.time_to_first_token` (measured: `qwen3.6-plus` has it, `Peach-07-17-DogFooding` does not); TTFT statistics must tolerate null values and note coverage.
4. **session.id coverage**: enter/invoke_agent/react spans stably carry `gen_ai.session.id`; chat/execute_tool may lack it depending on probe version. It is a span container attribute; trace aggregation does not depend on it (traceId lineage is the fallback); the skill only displays it as an attribute.
5. **Search returns span-level entries**: multiple rows per trace; client-side deduplication by TraceID; pagination `--page-size <=100`; enumeration upper limit `--max-traces` (default 200; when reached, output carries `enumeration_truncated` sampling marker).
6. **Detail API occasionally missing spans**: when a parent node is missing, hang as root fallback; no error.
7. **Root span parent sentinel**: both `""` and `0000000000000001` are treated as root.
8. **Agent name case variants** may coexist (measured: `Default`/`default`); be aware when filtering by agent.
9. **Tag filter syntax**: `--tags Key=gen_ai.span.kind Value=ENTRY` (multiple `--tags` can be repeated); at the field level `gen_ai.session.id` can also be used as a tag key, but the skill's analysis anchor is traceId, not session.id-based retrieval.
10. **`gen_ai.usage.cache_read.input_tokens` is under-reported**: measured value is always 0, even when TTFT differences clearly indicate prefix reuse (same-trace subsequent calls within minutes show TTFT dropping to 1/4). **Do not use this attribute to judge prefix cache hits**; use TTFT distribution comparison across multiple calls with the same context (the `latency` section in `trace_chain` outputs with this caliber and includes notes).
11. **Applications exist that do not instrument the entry layer at all**: measured in the same workspace, qwenpaw in a 4h slice of 50 traces had `kind=ENTRY` 0, `kind=AGENT` 0, only LLM/STEP/TOOL, with `gen_ai.session.id` directly on those spans. Enumerating by ENTRY alone would make such applications invisible on the enumeration path, so `cms_trace.search_agent_traces` falls back to `kind=LLM` when ENTRY returns empty results, and labels `enumeration_fallback="no-entry-span"` in the output — this marker is simultaneously evidence of the "application did not instrument entry layer" gap; direct access via `--trace-id` is not affected by enumeration.

## 6. Data Retrieval Conventions Within the Skill

| Action | API | Key Parameters |
|---|---|---|
| Enumerate traces | `cms get-entity-store-data --api-version 2024-03-30` | SPL `.trace_set with (domain='apm', name='apm.trace.common') \| where json_extract_scalar(attributes, '$["gen_ai.span.kind"]') = 'ENTRY'` (`kind=ENTRY` enumeration; empty result falls back to `kind=LLM`), `\| where serviceName = '<application name>'`, `--from/--to` (unix **seconds**), `--workspace`, `\| limit <offset>, <count>` |
| Fetch details | `cms get-entity-store-data --api-version 2024-03-30` | SPL `\| where traceId in ('<id>', ...)` (<=50 ids per batch), `\| project traceId, spanId, parentSpanId, spanName, serviceName, startTime, duration, statusCode, statusMessage, attributes, resources` |

Read-only whitelist see `cms_trace.CMS_ACTION_WHITELIST` (`get-entity-store-data` / `list-workspaces`); every SPL query passes through `cms_trace.SPL_DENY` before going out (blocking `http-call` / `llm-call` / `agentic-call` / `embedding` / `entity-call` / `prom-call` / `graph-call`); all calls inject UA `AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}`. SPL syntax details see the CMS UModel query reference.
