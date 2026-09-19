# PB-1 Behavior Insight Playbook (Two-Perspective Analysis)

Goal: Answer two categories of questions about Agent behavior — the **reason** behind decisions (why this call was made at this point) and the **chain** of behavior (whether this step is on the critical path or an expensive detour).

Division of labor: `scripts/` only performs quantitative aggregation and evidence extraction; **all qualitative judgments are made by the Agent executing this playbook**, and every conclusion must cite evidence. The Agent analyzes directly from the script's standard output (`--format json` is the default and stable machine contract; `--format yaml` outputs isomorphic YAML; **script stdout is not an observation report**), and does not ad-hoc generate shell/python scripts for secondary data processing. When a required analysis view is missing, extend the script output first, then analyze based on the new output.

Scope discipline: The time dimension of this playbook is **on-demand <=4h slices**, and the analysis unit is **a single user-specified trace (trace_id)**; the skill does not perform trace sampling or per-trace summary rankings (when the user cannot provide a trace_id, use `trace_overview`'s `totals.trace_ids` to let them pick — the skill does not choose on their behalf); no full-day 24h aggregation or weekly/monthly long-span operational analysis (for a different time period, **shift the slice** — span unchanged). All comparison baselines are limited to trace self-baseline and adjacent slice only; there is no long-history baseline. The report deliverable is a **self-contained HTML** injected into the `report-template.html` template (`report_render.py`), organized by business scenario.

## Data Sources (Dual Source, Not Either/Or)

LoongSuit and eBPF are **two complementary perspectives of the same Agent trajectory** and must be analyzed together: `--region` is required; `--workspace` (CMS 2.0 workspace) and `--project` (SLS project) require **at least one**, passed as command-line arguments (**no binding-type environment variables**). The script defaults to `--mode both` for dual-source joint queries, with both sources **anchored to the same `--trace-id`** (the eBPF side parses trace_id from `http.request.header.traceparent`); when only one side is bound, it automatically narrows to that source and marks the other as a gap. Single-source `--mode loongsuit|ebpf` is for troubleshooting/review only.

**Binding values (must be obtained from the user)**: Clarify five business facts with the user — agent application name / region / trace time range / **SLS Project name and CMS 2.0 workspace name (at least one)** / **target trace_id**; the skill has no auto-discovery mechanism. If the user cannot provide these, explain the console navigation path in text — **do not guess or compose resource names**. See the clarification script and SKILL.md section 8 Step 0.

The **agent application name** obtained through clarification is passed via `--service-name` (strongly recommended); it **only takes effect on the LoongSuit side** (CMS `serviceName` predicate). The ebpf-event index has no `service.name`; the eBPF side uses `--agent-type`/`--comm`/`--container-id` for narrowing instead. When analyzing, first read the narrowing status in `binding`: `applied: false` with no application name = results are mixed across all applications under that binding, and any "this application's error rate/latency" conclusion is invalid; `service_filter_unavailable: true` = LoongSuit side is narrowed but eBPF side cannot be narrowed — the two sides have different calibers and must be labeled with their source separately.

| Scope | Data Source | Record Granularity | Evidence Identifier |
|---|---|---|---|
| `loongsuit` | CMS 2.0 workspace trajectory (UModel `GetEntityStoreData`, including cross-Agent traces) | Single operation span | `trace_id` + `span_id` |
| `ebpf` | SLS `ebpf-event` (raw retrieval + client-side aggregation) | Single runtime fact (process/network/HTTP; **no Session/Turn/Step hierarchy**) | `event.id` + `http.exchange.id` |

Field dictionaries: LoongSuit side the LoongSuit field dictionary; eBPF side the eBPF field dictionary.

Unique material per source (complementary roles):
- loongsuit: `reasoning` parts in `gen_ai.input.messages` (model chain-of-thought), span duration/TTFT, cross-Agent `serviceName` view -> **preferred for decision context, latency breakdown, and trace structure**
- ebpf: process facts (pid/comm/cmdline), container/host/k8s attribution, network and HTTP facts (method/url.path/server.address/status_code), per-exchange latency paired by `http.exchange.id`, `trace_id` (can jump to LoongSuit for verification) -> **preferred for runtime behavior and external dependencies**; it **has no message payloads and no turn/step hierarchy**, so content retrieval and turn localization must go through the LoongSuit side
- Coverage differences: In practice, some environments' ebpf-event only contains `http.request`/`http.response` runtime facts, with all `gen_ai.*` index fields empty (`genai_index_coverage` all zeros). One source missing for a target = **gap discovery**, explicitly labeled; do not assert the trace does not exist based on single-source absence.

## Steps

### 1. Panoramic Scan (optional; find window context for the target trace)

```bash
python3 scripts/trace_overview.py <binding> <slice> [--service-name <name>]
```

- LoongSuit side records: error rate, react average/max rounds, repeated_tool_calls (loop candidates), model/tool composition, TTFT coverage, services (cross-Agent view), `steps_from_span_kind`, `totals.trace_ids` (top 50)
- eBPF side records: rows/exchanges, by_event distribution, process/container/host/cluster composition, network dimensions (by_url_path/by_server/by_method/by_http_status), exchange latency (latency pairs/avg/p95 + unpaired count), errors_by_type, `genai_index_coverage`
- both default: two segments output side by side, not mixed; a segment with 0 is recorded as-is (coverage difference, not degradation)
- **Purpose**: Verify whether the user's target trace_id falls within the slice (`totals.trace_ids`); provide slice context for trace-level conclusions (error rate, call volume composition); entry point for drift comparison (`--compare-hours`)

### 2. Target Trace Confirmation (user-specified, skill does not choose)

**The analysis unit is a single user-specified trace**: `--trace-id` is provided by the user (from the application's own logs / console / platform link), or selected by the user themselves from `trace_overview`'s `totals.trace_ids` — the skill does not make "which trace is most worth examining" sampling judgments or per-trace rankings.

- When locating spans by content, use `python3 scripts/span_search.py <binding> <slice> --match "<text>"` (**LoongSuit side only**: parses span's `gen_ai.input.messages` and `gen_ai.output.messages`, scans all message roles, labels hits as `field=input.<role>`/`output.<role>`; user's original words typically land in `input.user`, injected payloads typically land in `input.tool`). Hits include `trace_id`/`span_id`/`op`, which can be fed directly to `trace_chain.py --trace-id` and `decision_evidence.py --span-id`. **Discipline: `--match` only executes within the slice confirmed in Step 0** — first confirm with the user the **specific time period** when the trace occurred, and keep the slice span <= the maximum window limit (`AGENT_OBS_MAX_WINDOW_HOURS`, default 4h; the limit is `to - from` span, any historical 4h slice is valid), pinned with explicit `--from/--to`; do not run keyword searches with wide spans like `--hours 168` (client-side scanning of messages per span, linearly long-running). **Scripts no longer block**: no script reads that variable or rejects wide spans; exceeding the limit will only be extremely slow, not exit 2 — the only evidence is the Step 0 clarification record
- **First action when nothing is found but the user is confident data exists**: Run an **unfiltered comparison probe** in the same slice — use CMS SPL without the `gen_ai.span.kind` predicate (`aliyun cms get-entity-store-data --api-version 2024-03-30 --workspace <w> --from <ts> --to <ts> --query ".trace_set with (domain='apm', name='apm.trace.common') | project traceId, spanName | limit 10" --region <r> --user-agent <ua>`). Spans exist but zero with predicate => the problem is in the enumeration condition (the application may only instrument LLM/STEP/TOOL, output will carry `enumeration_fallback: no-entry-span`), **not** a binding/timezone/date error. In practice, skipping this probe and directly suspecting the binding has led to misdiagnosis
- When the target trace is visible from only one source: retain as-is and label the coverage difference (gap discovery)

### 3. Chain Reconstruction

```bash
python3 scripts/trace_chain.py <binding> <slice> --trace-id <trace-id>
```

- **All modes anchor on `--trace-id`**; both default: both sources use the same anchor to build their respective chains; when one side has no data for the trace, that segment has `present=false` (gap discovery, not an error); both missing triggers an error
- LoongSuit side: locate suspicious nodes from `steps` (parent-child tree, non-GenAI framework spans are collapsed) and `patterns` — error spans, spans in tool_loops, later react rounds, chats with abnormally high tokens; `services` > 1 indicates cross-Agent; the `latency` section is latency breakdown (each chat's duration/ttft/decode/tokens/throughput + **trace self-baseline** percentiles); read it directly for latency issues; read `steps` react `round` and chat sequence for turn structure
- eBPF side: locate suspicious runtime behavior from `exchanges` timeline and `patterns` — `failed_exchanges`, `status_5xx`, `repeated_calls` (same method+url_path+server repeated, external dependency jitter or retry storm), `unpaired` (request sent but no response, possibly timeout or process killed); `processes` provides process attribution, which can determine whether consecutive behavior is within the same process

### 4. Evidence Extraction (for each suspicious node)

```bash
# LoongSuit side (traces without ENTRY can use --trace-id directly, skipping enumeration)
python3 scripts/decision_evidence.py <binding> <slice> --span-id <spanId>
python3 scripts/decision_evidence.py <binding> <slice> --trace-id <id> --span-id <spanId>
# eBPF side (event.id)
python3 scripts/decision_evidence.py <binding> <slice> --mode ebpf --event-id <event.id>
```

- LoongSuit evidence: target span's input/output messages, tool arguments/result, ancestor chain, sibling steps, react turn sequence, trace original task (`entry_task`, taken from the enter span's entry message)
- eBPF evidence: target row's runtime facts (event_name/ts, http method/path/server/status_code/body size, process pid/comm/cmdline, container/host/k8s, agent_type), three-ring context (`context.same_exchange` / `same_process` / `same_trace`), `trace_id` and `trace_id_from`; `messages` and `entry_task` are **always null** (ebpf-event has no message payloads — this is not a script deficiency)

### 5. Two-Perspective Analysis

The correspondence between analysis subsections and business scenarios (scenario organization see the scenario playbooks):

| Analysis Subsection | Scenarios |
|---|---|
| Perspective 1: Decision Reason | PB-S1 / PB-S2 |
| Perspective 2: Behavior Chain | PB-S1 |
| Latency Analysis | PB-S3 |
| Hang / No-Result Analysis | PB-S2 |
| Drift Comparison Analysis | PB-S3 / PB-S6 (adjacent slice comparison) |
| Context Growth Analysis | PB-S4 |
| Security & Hijack Analysis | PB-S2 forensics entry (Scenario 7 security audit is reserved) |
| Multi-Agent Trace Analysis | PB-S5 |
| Data Gap & Hallucination Risk Analysis | PB-S2 / PB-S6 |
| Registry Consistency Audit | PB-S6 |

**Perspective 1: Decision Reason (why this call was made at this point)**
- LoongSuit side: read the target span's parent chain — parent react's round and finish_reason, previous round chat's output messages (the model's reasoning conclusion at that point); read input messages / tool arguments to see the context carried by the call
- eBPF side: read the three-ring context — the paired other half of the same `http.exchange.id` (request<->response), the process neighborhood of the same `pid` within +/-60s (what it was doing before and after), all runtime rows of the same `trace_id`; ebpf-event **has no message payloads**, so "what context the model based its decision on" can only come from the LoongSuit side — use `trace_id` to jump over and see the complete parent chain
- Judgment: Is this call a reasonable next step in task decomposition, a response to the previous step's result, or an unjustified leap?

**Perspective 2: Behavior Chain (critical step or detour)**
- Critical step criteria: output is consumed by subsequent steps (subsequent messages reference its content), it is on the path to the final answer, failure would cause task failure
- Detour criteria: same (tool, arguments) repeated (loop), result not referenced subsequently, no strategy change after failure before retrying, probing unrelated to `entry_task` (e.g., probing aws cli during an Alibaba Cloud inspection)
- Cost accounting: tokens and duration proportion consumed by detour steps (LoongSuit: steps' tokens/duration_ms; eBPF: exchange latency and request count — ebpf-event **has no token counts**, tokens can only come from the LoongSuit side)

**Latency Analysis (LoongSuit side, read the `latency` section directly)**
- Target round time = read the corresponding chat row in `latency.chats`: `duration_ms = ttft_ms (first token/prefill) + decode_ms (decoding)`; compare with `latency.baseline` (**trace self-baseline**: TTFT median/p95 of the chat sequence within the trace, decode_tps median, input_tokens distribution) for qualitative assessment
- TTFT significantly higher than baseline -> prefill-side causes: context too large (compare that row's input_tokens with baseline max), prefix cache cold start (first round after long idle does full prefill, subsequent calls within minutes show significantly lower TTFT — this is the evidence), model-side queuing; decode_tps significantly lower than baseline -> decoding-side / model throughput issue
- Evidence references `latency.chats` row's spanId/traceId; `cache_read_tokens` is always 0 and unusable (see field dictionary section 5.10); cache effect is evidenced by TTFT distribution comparison
- eBPF side has no TTFT: only per-exchange latency paired by `http.exchange.id` (`totals.latency_pairs`/`avg_latency_ms`, unpaired counted in `patterns.unpaired`), which is external HTTP dependency latency, not model latency; model-side latency conclusions are based on the LoongSuit side with caliber noted

**Hang / No-Result Analysis (LoongSuit side, read `steps` and `patterns` for determination)**
- Hang signature: **the last chat's `finish_reasons` contains `tool_calls` and there is no `execute_tool` span after it** — the model issued a tool call intent but the execution span never closed/was never exported (a hung tool's execute_tool is never persisted), manifesting as no result on the user side; find the last chat in `steps` by time order, check its finish_reasons and subsequent spans to determine
- "Did not reach completion" signature: the last react has no `finish_reason` (normal completion should carry a stop-type reason)
- **Distinguishing "hang" from "application did not instrument entry layer"**: a trace without an enter span (and `trace_overview`/`span_search` output carries `enumeration_fallback: no-entry-span`) indicates the application simply does not report ENTRY/AGENT spans — this is a **gap**, not hang evidence; in this case, hang can only be determined by the above chat/execute_tool signature
- Timeline evidence: find large gaps along the `steps` timeline — intra-round tool silence vs. post-hang interval; if a gap is immediately followed by the user resending the same request (compare adjacent enter spans' input messages, if the trace has enter), that forms a "retry after hang" evidence chain
- Hang vs. still-running determination looks at window age qualitatively: window long ended with no subsequent spans = hang; window close to current time = possibly still running
- When needing to see the model's last decided tool call at the hang point, use `decision_evidence.py --trace-id <id> --span-id <chat spanId>` (`--trace-id` direct access covers traces without enter span) to read its output messages
- eBPF side corresponding signal: exchange has only request without paired response (`patterns.unpaired` non-empty) — external call sent but no response received, possibly timeout or process killed; when both sources are visible, cross-validate with the LoongSuit side's hang signature

**Drift Comparison Analysis (LoongSuit side, `trace_overview.py --compare-hours <N>`)**
- Purpose: regression caused by silent changes on the provider/platform side — looks "normal" in a single window, only exposed when compared with the immediately preceding window; the `drift` section provides `{base, current, delta_pct}` for error_rate / chat latency (avg+p95) / TTFT / react rounds / model and tool call volumes
- **Window discipline**: `--compare-hours <N>` is **double the query volume** (current slice + baseline slice shifted back N hours), and both slices **individually** must be <= the maximum window limit (default 4h) — the limit is per-window, not per-invocation
- Qualitative judgment: delta is significant (e.g., TTFT or latency +50% or more, error_rate goes from 0 to non-zero, react rounds increase) and **traffic structure has not changed** (corroborated by sessions/traces delta) -> regression hypothesis holds; if only call volume changed while per-unit metrics stayed the same -> more likely traffic change than regression
- Trace-level review: whether the regression falls on the model side (TTFT) or tool side (by_tool errors), confirm using `trace_chain.py --trace-id <user-specified suspicious trace>`'s `latency` / `tool_analysis` sections
- Metrics where the baseline window is 0 have `delta_pct=None`, label as-is, do not convert
- LoongSuit side only; under `--mode ebpf` the script notes drift is loongsuit-side only

**Context Growth Analysis (LoongSuit side, read trace_chain's `context_growth` section)**
- Purpose: context bloat and cost in long-running tasks — `series` is the per-chat input_tokens sequence within the trace, `input_tokens.growth_pct/monotonic_frac` is the growth summary, `total.input_tokens` is the cumulative cost
- `ballooning_candidate=true` (growth rate >=100% and monotonic fraction >=0.8 and >=5 chats) = ballooning candidate; but **flags are based on growth rate, not absolute volume**: very large existing volume + low growth rate will not trigger; cost risk is assessed qualitatively from `total` and `ttft_ms.first/last` trend (last TTFT significantly higher than first with input_tokens increasing in sync -> context pressure)
- Flat sequence (growth_pct~0) = context compression exists or calls are independent; when combined with "long task failure", consider the compression-loss-of-information hypothesis
- eBPF side has no per-call context sequence (ebpf-event has no messages and no turn/step hierarchy); this view is LoongSuit side only; cross-reference with hang signature to determine whether long task failure is a hang or context pressure

**Security & Hijack Analysis (content retrieval -> forensics)**
- Entry: `span_search.py --match "<injection characteristic text>" --from <ts> --to <ts>` (e.g., "ignore previous instructions", unauthorized instruction fragments; **LoongSuit side only**, ebpf-event has no message payloads). The slice must first be confirmed with the user (the specific time period when the attack occurred) and **span <= maximum window limit** (default 4h); do not scan directly with wide spans like 168h — the script will not reject it, it will just be extremely slow
- Forensics chain: hit span (`hits[].trace_id`/`span_id`) -> `decision_evidence.py --span-id <hit span>` to read input/output messages and tool arguments -> determine whether the target was hijacked (subsequent calls deviate from `entry_task`, sensitive path reads / external address exfiltration / credential-type parameters appear)
- Tool-side signal: sensitive tools (file read, HTTP exfiltration) appear in `trace_overview.by_tool` with parameters pointing to sensitive resources; outbound calls unrelated to `entry_task` are high-weight evidence
- Boundary: when the payload only stays in the tool result and is not consumed by the model (not entering input/output messages), `--match` will not hit; whether it constitutes an attack is a qualitative conclusion and must cite messages/arguments fragments from the forensics chain

**Multi-Agent Trace Analysis (single trace across services)**
- Signal: `trace_overview.services` > 1 or `trace_chain.services` > 1 = the trace spans Agent runtimes; a sub-agent's enter hanging under the main chain's dispatch-type tool is the handoff boundary
- Failure localization: read which service/layer `patterns.failed_spans` falls on — main chain failure or sub-chain failure; after sub-chain failure, whether the main chain rerouted/degraded/completed directly (read subsequent react's finish_reason along the `steps` tree)
- Composite error attribution: when there are multiple failed spans, determine causality by parent-child relationship — downstream failure caused by upstream failure counts as the same root cause; parallel failures without parent-child relationship are considered independently caused
- Handoff quality (message completeness, context passing sufficiency) **has no structured metric**: compare the sub-agent enter's input messages with the main chain dispatch's arguments qualitatively to judge whether passing was sufficient; label gaps as-is
- **Scope boundary**: the above refers to handoffs **within a single trace**; cross-trace relay handoffs (the last step of one trace as input to the next) are out of scope for this phase — no cross-trace splicing

**Data Gap & Hallucination Risk Analysis**
- Signal: same data tool repeatedly fails with same parameters (`trace_overview.repeated_tool_calls` / `trace_chain.patterns.tool_loops`) + model still gives a specific answer after data failure (read last chat's output)
- Risk pattern: model gives specific values/factual answers after data failure = hallucination candidate; use `decision_evidence.py` to read the last chat's output messages, cite alongside the data tool's failure records
- Boundary (must be declared): hallucination determination requires comparing output with actual data source values; telemetry can only flag suspicious patterns; when the data tool returns **dirty data rather than errors**, there is no failure signal at all — only output spot-checks can detect it

**Registry Consistency Audit (inventory vs. registry)**
- Purpose: unregistered tools/models and shadow deployments are hidden security gaps; compare `trace_overview`'s `by_tool` / `by_model` / `services` inventories item by item against the customer registry
- Classification: registry has it, inventory has it = normal; inventory has it, registry does not = unregistered/experiment candidate (combine with service name to judge shadow deployment); registry has it, inventory does not = unused (within the window)
- Coverage boundary: inventory comes from `kind=ENTRY` enumeration; when there are no ENTRY spans in the slice, it automatically falls back to `kind=LLM` and labels `enumeration_fallback: no-entry-span` (applications that don't instrument the entry layer are still covered, but this must be declared in the conclusion); traces with neither ENTRY nor LLM spans (e.g., hung executions stuck at the tool stage) remain outside the overview — audit conclusions must declare the window and enumeration caliber; when necessary, use `trace_chain.py --trace-id` for supplementary checks on suspicious traces (`--trace-id` direct access is not affected by enumeration fallback)

### 6. Evidence Rules (mandatory)

- Every qualitative conclusion must be accompanied by an evidence identifier: LoongSuit side `trace_id` + `span_id`; eBPF side `event.id` + `http.exchange.id`; quoted content must come from the script output's messages/arguments/result fragments
- No fabrication: when evidence is insufficient, write "insufficient evidence" and state what is missing (e.g., outside the window, truncated, fetch_truncated)
- Truncation (default list 200 / detail 2000 characters) may lose information; when longer context is needed, re-extract with `--detail-limit`; on the eBPF side, when data volume exceeds 2000 rows per store, output carries a `fetch_truncated` label — narrow the window and re-pull as needed
- eBPF side latency/caliber limitations: no TTFT, no token counts; latency relies on `http.exchange.id` request->response pairing; when model-side latency or tokens are needed, use `trace_id` to jump to the LoongSuit side
- Dual-source cross-validation: model latency and content-type conclusions can only reference the LoongSuit side (span Duration/TTFT/messages); runtime behavior and external dependency conclusions reference the eBPF side (exchange/process/network); the two sources are cross-checked by **`trace_id`** (eBPF rows parse from `http.request.header.traceparent`); caliber differences are explicitly labeled; single-source absence is labeled as a "gap" — do not assert non-existence based on this
- Analysis output is written as annotation spec `{schema_version: "obs-trace-report-v1", title?, notes: {spanId: text}}`, together with trace facts handed to `scripts/report_render.py` for template injection rendering as self-contained HTML (see the rendering contract); scenario-based organization see the scenario playbooks; plain-language attribution classification and recommended actions are determined by the Agent per the attribution taxonomy, **no mapping is done in code**
