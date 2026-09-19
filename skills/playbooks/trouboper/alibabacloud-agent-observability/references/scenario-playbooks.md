# Scenario-Based Observation Playbook (PB-S1 ... PB-S6)

Organize existing script outputs by **business scenario**: each scenario specifies the audience, analysis unit, which scripts to run,
which fact paths to reference, which sections of the template report the conclusions land in, and **fixed data gaps**. Qualitative
analysis is always done by the Agent (see the attribution taxonomy); rendering always goes through
`scripts/report_render.py` injecting into the `report-template.html` template
(see the rendering contract).

## 0. Scope Discipline

- **Time dimension**: on-demand **<=4h slices**. No full-day 24h aggregation, no weekly/monthly, no cross-day
  long-span operational analysis. Need a different time period? **Shift the slice** (`--from/--to` moved to the target period,
  **span unchanged**) — do not widen the span.
- **Analysis unit**: **a single user-specified trace (trace_id)**. The skill does not perform trace sampling or
  per-trace summary rankings; when the user cannot provide a trace_id, use `trace_overview.py`'s
  `totals.trace_ids` (top 50) for the user to pick — the skill does not choose on their behalf.
- **All comparison baselines are limited to two types**: trace self-baseline (`chain.latency.baseline`, chat
  sequence self-percentiles within the trace) and adjacent slice (`trace_overview.py --compare-hours`'s `drift` section);
  there is no long-history baseline. When the baseline is 0 or missing, write "no baseline" — **never** write `0%`.
- **Consumption uses token caliber only**: neither source has price/cost/billing fields; this skill does not call
  billing APIs. Monetary amounts are always `missing`; if the Agent authoring layer produces monetary-semantic text,
  `report_render` R4 will mechanically reject it.
- Scenario 7 (Security & Compliance Audit) and Scenario 8 (Trend Weekly/Monthly Reports) are **reserved extensions**, not implemented in this phase.

## 0.1 How to Use Example Prompts

Each scenario includes an **example prompt** — something a user would actually say. A good prompt carries five
business facts (application name / region / time range / CMS workspace or SLS Project / target
trace_id), allowing the skill to proceed directly to Step 0.5 preflight; **missing any one triggers the clarification flow**
(the clarification script) to obtain it from the user, rather than guessing names or composing resource names.

Resource names in examples (`agent-prod-ws`, `cn-hangzhou`, `order-assistant`, etc.) are **placeholders**;
actual values must be copied verbatim from what the user provides. Specifying the **audience** in the prompt
("for the customer service manager" / "for the architecture team") is very useful — it determines the level of
de-terminologization in the report.

Common command skeleton (binding and slice parameters see SKILL.md section 6; `span_search` is only run when
content-based span localization is needed):

```bash
python3 scripts/trace_overview.py     <binding> <slice> --format json > reports/facts/overview.json
python3 scripts/span_search.py       <binding> <slice> --match <keyword> --format json > reports/facts/search.json
python3 scripts/trace_chain.py       <binding> <slice> --trace-id <id> --format json > reports/facts/chain.json
python3 scripts/decision_evidence.py <binding> <slice> --span-id <sid> --format json > reports/facts/ev.json
python3 scripts/report_render.py --facts chain=reports/facts/chain.json \
    [--spec reports/facts/notes.json] --out reports/html/<scenario>.html
```

`--facts` only needs `chain=trace_chain.py` output (the rendering fact layer); `--spec` is
the Agent-authored annotation layer `{schema_version: "obs-trace-report-v1", title?, notes: {spanId: text}}`,
where `notes` keys must be real spanIds existing in the chain (R2 enforced), and the text renders as that node's
note field — **this is where the Agent's analysis conclusions are written**, with evidence anchoring naturally satisfied.

**Report Landing Quick Reference** (template sections, all auto-rendered from spans — Agent does not copy numbers):

| Template Section | Content |
|---|---|
| `#sec-info` Trace Info | trace_id / service / time / total token cards |
| `#sec-link` Trace Analysis | Step composition and service distribution summary |
| `#sec-perf` Performance Analysis | Duration and TTFT breakdown |
| `#sec-llm` LLM Call Analysis | Per-model aggregation table (count / tokens / latency / TTFT / output speed) |
| `#sec-tool` TOOL Call Analysis | Per-tool aggregation table (count / duration / errors) |
| `#sec-trace` Execution Trace | Span tree (with note annotations) |
| `#sec-gantt` Gantt Chart | Timeline view |
| `#sec-detail` Node Details | Per-span table |

---

## PB-S1 Single Task Execution Review (What Happened)

- **Audience**: Customer service manager / Product manager / Business operations
- **Analysis unit**: Specified trace (single or multi-turn). Turn structure is read from `chain.steps[]`'s react
  round and chat sequence; there is no longer a separate turn health section
- **Trigger phrasings**: "What did this task do", "Why is this trace so long", "Give me a review of this execution"

**Example Prompt**

> Help me review what the `qwenpaw` Agent application did in today's execution around 14:20.
> Region `cn-hangzhou`, CMS 2.0 workspace `agent-prod-ws`, trace id is
> `1787048349629qdvjowi0000c2a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`. The report is for the customer service manager,
> who doesn't understand trace terminology — focus on explaining how many steps the task took, what each step did,
> whether it took any detours, and whether the user's original request was ultimately fulfilled. Annotate analysis
> conclusions directly on the corresponding step nodes.

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_chain.py --trace-id <id>` | `chain.span_count`, `chain.steps[]` (spanId/op/spanName/service/agent/duration_ms/error/depth/round), `chain.latency.chats[]` and `chain.context_growth.series[]`, `chain.op_duration_split.{duration_ms,leaf_ops,container_ops}`, `chain.total_duration_ms`, `chain.total_tokens`, `chain.total_input_tokens`, `chain.total_output_tokens`, `chain.avg_ttft_ms`, `chain.chat_count`, `chain.tool_count` |
| `decision_evidence.py --span-id <sid>` | `ev.entry_task` (entry message), `ev.target.input_messages`, `ev.target.output_messages` |

**Report Landing**: `#sec-info` (total duration / TTFT / total tokens / input / output / LLM count /
Tool count, auto-calculated by template), `#sec-trace` execution trace tree (main structural view, step types color-coded),
`#sec-perf` + `#sec-gantt` (duration and timeline), `#sec-llm` / `#sec-tool` aggregation tables,
`#sec-detail` per-span table. **Agent annotations** (`spec.notes[spanId]`) are placed on: key decision points
(why this call was made), detour steps (output not consumed subsequently), risk signals (reasoning path too long /
context bloat / repeated reads **merged into one**, not split individually).

**Qualitative Analysis Guidance**: The "why" of key decision points follows `behavior-insight-playbook.md` Perspective 1
(parent react's `finish_reason` + previous round output), mapped to plain language per
`attribution-taxonomy.md` section 1. Critical step vs. detour is determined by Perspective 2 (whether output is consumed subsequently,
whether it is on the path to the final answer). User's original request vs. final response comparison reads
`ev.entry_task` and the last chat's output.

**Fixed Data Gaps**: eBPF side has no message payloads (`messages` / `entry_task` always null); decision
context can only come from the LoongSuit side; `messages` is truncated at 2000 characters by default — use
`--detail-limit` for longer content. Tree node cards are **span-level facts** (model / tokens / first-token wait / tool
arguments truncated to 200 characters); to see a specific node's full conversation, run `decision_evidence.py
--span-id` separately for comparison — do not expect to expand it in the tree.

**Evidence Requirements**: Each conclusion lands on a specific node, and the annotation anchors to that spanId (naturally satisfied);
when stating in conversation, append `trace_id` + `span_id`.

---

## PB-S2 Failure & Anomaly Diagnosis (Why It Got It Wrong)

- **Audience**: Operations / Customer service / Developer liaisons
- **Analysis unit**: Specified trace
- **Trigger phrasings**: "Why did it get it wrong", "Which step went wrong", "What is the root cause of this error"

**Example Prompt**

> In CMS workspace `agent-prod-ws` in `cn-hangzhou`, the `order-assistant` application
> had user complaints about incorrect answers today between 10:00-12:00, trace id
> `1787048349ab12cd34ef56ab78cd90ef12ab34cd56ef78ab34cd56ef78ab34cd5`. Help me locate
> which step had the problem, what input the previous step gave it, then explain the cause in plain language
> (was it wrong parameters, a broken external service, or the model making up data), and tell me what to
> investigate next. The report is for the operations team, who don't understand technical details. This prompt
> didn't provide an SLS Project, so only the LoongSuit side is bound — the runtime facts half should be
> marked as a gap in the report, not treated as "no problem".

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_chain.py --trace-id <id>` | `chain.patterns.failed_spans[{spanId,spanName,statusMessage}]`, `chain.patterns.tool_loops[{tool,arguments,times}]` (retry candidates), `chain.steps[]` (hang signature analysis) |
| `trace_overview.py` | `overview.totals.{errors,error_rate}`, `overview.by_operation[].errors` |
| `decision_evidence.py --span-id <failed span>` | `ev.target.statusMessage`, `ev.target.finish_reasons`, `ev.target.tool_arguments`, `ev.ancestor_chain[]` (causes); `--trace-id` can reach traces without ENTRY directly |

**Report Landing**: `#sec-trace` execution trace tree (failed nodes marked with error indicators, failed subtrees visible at a glance),
`#sec-detail` per-span table, `#sec-tool` error column. **Agent annotations** placed on the failed node and its
direct predecessor node: one-sentence root cause + plain-language attribution + what to investigate next.

**Hang Signature Analysis** (turn health section removed; Agent reads `chain.steps[]` to determine):
**The last chat's `finish_reasons` contains `tool_calls` and there is no `execute_tool` span after it**
= hang candidate — the model issued a tool call intent but there is no execution record; combine with window age to determine
whether it is still running or truly hung. Similarly, the "did not reach completion" signature is the last react having no `finish_reason`.

**Qualitative Analysis Guidance**: Plain-language attribution categories (**parameter error / external service timeout / model hallucination / insufficient permissions /
context loss**) and recommended actions **are determined by the Agent per `attribution-taxonomy.md` sections 1-2**;
scripts only provide raw facts (`error.type` / `statusMessage` / `finish_reasons` /
`statusCode` / retry candidates). **No mapping tables in code**.

Three-tier error determination caliber see `acceptance-criteria.md` section 9: `statusCode=2` ->
`finish_reasons` contains error -> `otel.status_code=ERROR`. Quoted error counts must state the caliber.

**Fixed Data Gaps**: **There is no retry field** — retries can only be inferred from identical `(tool, arguments)`
repeated execution (`tool_loops` / `repeated_tool_calls`); this must be stated as inference, not measurement.
Hang vs. still-running can only be determined by window age.

**Evidence Requirements**: Root cause conclusion annotations must anchor to the failed spanId; when stating in conversation, append
`trace_id` + `span_id`.

---

## PB-S3 Performance & Duration Analysis (Why So Slow)

- **Audience**: Product / Operations (evaluating user experience)
- **Analysis unit**: Specified trace
- **Trigger phrasings**: "Why so slow", "Which step is slow", "How much slower than normal"

**Example Prompt**

> The `support-bot` (region `cn-hangzhou`, CMS workspace `agent-prod-ws`) execution yesterday at 16:00
> — users reported waiting over 40 seconds for a response, trace id
> `1787048349ff11aa22bb33cc44dd55ee66ff77aa88bb99cc00dd11ee22ff33aa4455`.
> Help me identify the one or two slowest steps and compare them against **this trace's own normal level**
> to see how much they differ — is it the first-token wait getting longer or decoding getting slower. For the product team
> to decide whether to optimize the experience. If the trace can't be found in this slice,
> shift the slice to find it — **do not widen the time span**.

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_chain.py` | `chain.latency.chats[{spanId,duration_ms,ttft_ms,decode_ms,decode_tps,input_tokens}]`, `chain.latency.baseline.{ttft_ms{median,p95,max},decode_tps{median,min},input_tokens{median,max}}` (**trace self-baseline**, chat sequence self-percentiles within the trace), `chain.steps[].duration_ms` |
| `trace_overview.py` | `overview.loongsuit.by_operation[].{avg_ms,p95_ms}` (cross-trace baseline within the slice), `overview.drift.chat_latency.{avg_ms,p95_ms}` (adjacent slice comparison, `--compare-hours`) |

**Report Landing**: `#sec-perf` (performance analysis, template auto-generates duration and TTFT breakdown from spans),
`#sec-gantt` (Gantt chart, slow steps visible at a glance on the timeline), `#sec-llm` table (per-model
`avg_duration_ms` / `avg_ttft_ms` / `avg_output_tps`). **Agent annotations** placed on the slowest
step: whether slowness is in prefill or decoding, whether it is a spike or progressively worsening.

**Qualitative Analysis Guidance**: `duration_ms = ttft_ms + decode_ms`. TTFT far above trace self-baseline ->
prefill-side causes (context too large / prefix cache cold start / model queuing); `decode_tps` far below self-baseline
-> decoding or model throughput. See `behavior-insight-playbook.md` "Latency Analysis".

**Fixed Data Gaps**: eBPF side **has no TTFT field**; latency only covers pairable exchanges
(`latency_pairs`, unpaired counted in `unpaired`); some models do not report
`gen_ai.response.time_to_first_token`, so `baseline.ttft_ms.coverage` is often incomplete.
`cache_read_tokens` is always 0 in practice; to judge prefix cache effect, look at TTFT distribution rather than this field.

**Evidence Requirements**: Reference `latency.chats` row's `spanId` / `traceId`.

---

## PB-S4 Consumption Analysis (Token Caliber, Proxy Cost)

- **Audience**: Management / Finance and operations liaisons
- **Analysis unit**: Specified trace (supplemented by current slice composition facts)
- **Trigger phrasings**: "How much did this task consume", "Where did the tokens go", "Why was this one especially expensive"

**Example Prompt**

> Help me look at the consumption composition of trace
> `1787048399aa11bb22cc33dd44ee55ff66aa77bb88cc99dd00ee11ff22aa33bb44` in the `cn-hangzhou` / CMS workspace `agent-prod-ws`
> `knowledge-agent` application's 09:00-13:00 slice today: which model consumed the most, what proportion
> input vs. output tokens were, and whether tool retries caused noticeably elevated consumption. For management. **We don't have model unit price data, don't give amounts** — just write "missing" for the amount column,
> I want the token caliber. Also note that tool calls themselves don't consume tokens, don't
> force a "model/tool/retrieval" three-way pie chart.

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_overview.py` | `overview.token_composition.by_source_field.{input,output,cache_read,total}_tokens`, `overview.token_composition.by_span_role.{chat,invoke_agent}`, `overview.token_composition.coverage`, `overview.token_composition.pricing.available`, `overview.by_model[]` |
| `trace_chain.py` | `chain.context_growth.{series[],input_tokens{growth_pct,monotonic_frac},total{input_tokens,output_tokens},ballooning_candidate}`, `chain.llm_analysis.rows[]`, `chain.total_*` |

**Report Landing**: `#sec-info` (total token / input / output cards, auto-calculated by template),
`#sec-llm` (per-model aggregation table: count / tokens / latency), `#sec-trace` tree node token
fields. **Agent annotations** placed on abnormal consumption nodes (retry amplification / context bloat). **Amounts are always
`missing`** — `report_render` R4 mechanically rejects monetary-semantic text in the Agent authoring layer.

**Qualitative Analysis Guidance**: "This trace had elevated consumption due to N retries" is determined by the Agent combining
`chain.patterns.tool_loops` and `overview.repeated_tool_calls`. Context bloat
(`ballooning_candidate`) follows `behavior-insight-playbook.md` "Context Growth Analysis".

**Fixed Data Gaps** (must be listed in every S4 report):

1. **Amount = missing**: neither source has price/billing fields; this skill does not call billing APIs.
   `token_composition.pricing.available` is always `false`. You may state that the amount is **unavailable**,
   but **must not give a monetary value** (`report_render` R4 mechanically rejects).
2. **Tool and retrieval steps do not consume tokens**: tokens only land on `chat` and `invoke_agent` span types,
   so a "model calls vs. tool calls vs. retrieval" three-way pie chart **cannot be produced**.
3. **`cache_read_tokens` is always 0**: not instrumented in practice; does not mean there is no cache reuse.
4. **eBPF side tokens are "unmeasurable"** rather than "measured as zero".
5. **No daily / weekly caliber**: this phase does not do full-day or weekly/monthly aggregation.

**Evidence Requirements**: Token numbers come from the template's auto-aggregation of spans; the Agent does not hand-copy them;
abnormal consumption conclusions anchor to specific chat spanIds.

---

## PB-S5 Multi-Agent Collaboration & Multi-Turn Tracing

- **Audience**: Product managers / Architecture understanding personnel
- **Analysis unit**: Specified trace (**within a single trace** cross-Agent handoff; cross-trace relay handoff
  is out of scope for this phase and must be explicitly declared)
- **Trigger phrasings**: "How do these Agents divide the work", "Where did the handoff fail", "Who is responsible for this failure"

**Example Prompt**

> `research-orchestrator` (region `cn-hangzhou`, CMS workspace `agent-prod-ws`)
> calls sub-agents for retrieval. Yesterday's 11:30 execution failed, trace id
> `1787048411cc22dd33ee44ff55aa66bb77cc88dd99ee00ff11aa22bb33cc44dd55`. Help me
> draw the call relationship between the main Agent and sub-Agents, clearly mark whether the failure occurred in the main chain or sub-chain,
> which handoff boundary had the problem, and whether the input the sub-Agent received matches the parameters the main Agent sent.
> For the architecture team. Handoff quality itself has no structured metrics, so that part should be written as
> qualitative judgment with uncertainty clearly marked.

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_overview.py` | `overview.services[]` (>1 means cross-Agent), `overview.by_operation[]` |
| `trace_chain.py` | `chain.services[]`, `chain.steps[].{parentSpanId,service,agent,depth}` (collaboration hierarchy derived from `parentSpanId`), `chain.patterns.failed_spans[]` (locate main chain vs. sub-chain) |
| `decision_evidence.py` | `ev.ancestor_chain[]` (upstream/downstream of handoff boundary), `ev.target.{input_messages,tool_arguments}` (handoff parameter comparison) |

**Report Landing**: `#sec-trace` execution trace tree (**each sub-Agent's `enter` branch forms its own
subtree**, responsibility visible by which subtree it falls on — a tree is easier to identify than a relationship diagram), `#sec-detail` per-span table
(cross-service rows), `#sec-link` service distribution. **Agent annotations** placed on handoff boundary nodes (sub-Agent `enter` points) and responsibility attribution nodes.

**Qualitative Analysis Guidance**: A sub-Agent's `enter` hanging under the main chain's dispatch tool is the handoff boundary; failure
localization looks at where `patterns.failed_spans` falls — main chain or sub-chain; composite errors attributed by parent-child relationship. See
`behavior-insight-playbook.md` "Multi-Agent Trace Analysis".

**Fixed Data Gaps**: **Handoff quality (message completeness, context passing sufficiency) has no structured metrics**;
it can only be qualitatively assessed by comparing the sub-Agent `enter`'s input messages with the main chain dispatch's parameters. `services > 1`
only indicates cross-service, not that the handoff succeeded. **Cross-trace relay handoffs (the last step of one trace as input to the next)
are out of scope for this phase** — when the user raises this, state it explicitly; no cross-trace splicing.

**Evidence Requirements**: Responsibility attribution conclusions anchor to the failed spanId; when stating in conversation, append `trace_id` +
`span_id`.

---

## PB-S6 Tool Call Quality Analysis

- **Audience**: Operations (evaluating tool/plugin reliability)
- **Analysis unit**: Specified trace (in-trace tool behavior) + current slice (window-level tool facts)
- **Trigger phrasings**: "Which tool is most unstable", "Is the tool failure rate high", "Which tool is slowest"

**Example Prompt**

> The `cn-hangzhou` / CMS workspace `agent-prod-ws` `tool-gateway` application's 08:00-12:00 slice today —
> help me look at each tool's call status: success rate, average duration, how slow the slowest
> 5% are, rank them by health, and tell me which tool is most unstable and needs priority investigation. For the operations team.
> Also compare with the previous 4-hour slice to see if things have worsened. **Note: I only want this slice, no 7-day
> trend** — this skill does not do cross-day aggregation; the trend part is replaced by adjacent slice comparison, and the report should
> clearly state this is a slice-level comparison, not a long-term trend. If an HTML report is needed, give me a representative trace's
> trace_id; I'll cross-reference the window-level conclusions.

**Prerequisite Scripts and Fact Paths**

| Script | Key Fact Paths |
|---|---|
| `trace_overview.py` | `overview.by_tool[{tool,calls,errors,avg_ms,p95_ms,error_rate}]`, `overview.repeated_tool_calls[{tool,arguments,times}]`, `overview.drift.by_tool[{tool,calls,errors}]` (adjacent slice comparison) |
| `trace_chain.py` | `chain.tool_analysis.rows[{tool,count,avg_duration_ms,total_duration_ms,error_count,error_rate}]`, `chain.patterns.tool_loops[{tool,arguments,times,spanIds}]` |

**Report Landing**: Window-level facts (`by_tool` ranking, slice comparison) are delivered **in conversation**; the HTML report
renders the user-specified trace — `#sec-tool` produces the trace's tool aggregation table, `#sec-trace` tree
shows failed tool nodes. **Agent annotations** placed on the trace's most unstable tool call node (it is an instance of the window-level ranking). The template does not produce a window-level ranking page; for per-tool drill-down, shift the slice or change the trace_id to produce another report.

**Qualitative Analysis Guidance**: Rankings and ratios are arithmetic; "which tool needs investigation" is the Agent's judgment. Unregistered
tools/models are checked against the customer registry per `behavior-insight-playbook.md` "Registry Consistency Audit"
(`tests/fixtures/registry_allowlist.json` is the test baseline; production uses the customer-provided list).

**Fixed Data Gaps** (must be listed in every S6 report):

1. **7-day success rate trend is out of scope**: the window span discipline of <=4h means `by_day` can never span a day;
   this phase is not multi-window driven. The degraded form = **single-slice ranking + adjacent slice comparison**
   (`trace_overview.py --compare-hours`).
2. **No parameter error rate breakdown**: only span-level `errors` and `error_rate` are available; cannot distinguish "parameter
   error" from "server error"; need to examine `decision_evidence.py`'s `tool_arguments` and
   `statusMessage` case by case.
3. **`repeated_tool_calls` is a loop/retry candidate**, not a measured retry count.

**Evidence Requirements**: Ranking numbers come from `overview.by_tool` (script output, Agent does not hand-copy); in-trace
conclusions anchor to specific `execute_tool` spanIds.
