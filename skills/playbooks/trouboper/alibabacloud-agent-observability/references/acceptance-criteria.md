# Acceptance Criteria: alibabacloud-agent-observability

**Scenario**: Enterprise Agent application observability (CMS 2.0 workspace trace LoongSuit + SLS ebpf-event eBPF dual data source read-only observation and analysis; analysis unit is a single user-specified trace trace_id)
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — CMS / SLS Plugin Mode

#### ✅ CORRECT
```bash
# LoongSuit side (CMS 2.0 UModel, time parameters in unix seconds; --api-version 2024-03-30 is mandatory)
aliyun cms get-entity-store-data --api-version 2024-03-30 --workspace <workspace-name> --from 1787000000 --to 1787086400 --query ".trace_set with (domain='apm', name='apm.trace.common') | where json_extract_scalar(attributes, '\$[\"gen_ai.span.kind\"]') = 'ENTRY' | project traceId, spanId, spanName, serviceName, startTime, duration | limit 0, 100" --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}
aliyun cms list-workspaces --api-version 2024-03-30 --biz-region cn-hangzhou --workspace-name-list <workspace-name> --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}
# eBPF side (SLS raw search; ebpf-event runtime fields are not indexed, no server-side SQL aggregation)
aliyun sls get-logs --project agentloop-xxx --logstore ebpf-event --from 1787000000 --to 1787086400 --query "*" --line 100 --offset 0 --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}
aliyun sls list-log-stores --project agentloop-xxx --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}
```

#### ❌ INCORRECT
```bash
aliyun cms GetEntityStoreData ...    # Legacy API style, forbidden; must use plugin mode with lowercase hyphens
aliyun cms get-entity-store-data ... # Missing --api-version 2024-03-30: CMS 2.0 API is not in the default 2019-01-01 version, will report "not available in the current API version"
aliyun sls GetLogs ...               # Legacy API style, forbidden
aliyun log get-logs ...              # Wrong product name
aliyun sls get-logs ... --query "* | select count(*) group by \"agent.type\""   # ebpf-event runtime fields are not indexed, server-side aggregation will be rejected; must use raw search + client-side aggregation
# SPL pipe commands that initiate external/model calls (blocked by cms_trace.SPL_DENY):
#   | http-call ...  | llm-call ...  | agentic-call ...  | embedding ...
#   | entity-call ...  | prom-call ...  | graph-call ...
aliyun cms cms_natural_language_query ...   # Requires CreateThread/CreateChat write permissions, this skill does not use it
```

## 2. Read-Only Constraints

#### ✅ CORRECT
LoongSuit side allows only `cms get-entity-store-data` and `cms list-workspaces` (`cms_trace.CMS_ACTION_WHITELIST` whitelist), and every SPL query is checked against `cms_trace.SPL_DENY` before being sent (blocking seven pipe commands that initiate external or model calls: `http-call` / `llm-call` / `agentic-call` / `embedding` / `entity-call` / `prom-call` / `graph-call`); eBPF side allows only `sls get-logs` (raw search) and `sls list-log-stores` (listing, for logstore discovery). `sls_event.run_get_logs` uses regex interception for write verbs (insert/update/delete/drop/create/alter/truncate/merge/replace).

#### ❌ INCORRECT
Any `aliyun cms|sls` write/modify/delete API; CMS query APIs outside the whitelist; SPL using external-call pipe commands; bypassing `sls_event`/`cms_trace` to directly construct CLI calls; **any ARMS or AgentLoop calls** (both dependencies have been completely removed).

## 3. Observability UA

#### ✅ CORRECT
Every cloud API command must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-observability/skill-version/{version}/{session-id}`; scripts inject via `SKILL_SESSION_ID`, and `obs_core.user_agent()` assembles the UA uniformly (shared by CMS / SLS calls). Local commands (`version` / `plugin list` / `configure list`) do not use this flag.

#### ❌ INCORRECT
`aliyun configure ai-mode enable` (deprecated); `export ALIBABA_CLOUD_USER_AGENT=...` (does not survive across bash sessions); omitting `--user-agent`.

## 4. Credential Security

#### ✅ CORRECT
Use `aliyun configure list` to check profile status.

#### ❌ INCORRECT
`echo $ALIBABA_CLOUD_ACCESS_KEY_ID` / `echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET`; `env | grep -i access` / `env | grep -i secret` / `printenv` (dumps credential values to transcript); `cat ~/.aliyun/config.json` / `cat ~/.alibabacloud/credentials` (plaintext `access_key_secret` and `sts_token`); any command whose output contains credential **values**; printing/echoing AK/SK; requesting AK/SK in conversation; `aliyun configure set` with plaintext credentials.

## 5. Query Patterns (Tested Constraints)

#### ✅ CORRECT
```bash
# LoongSuit side: CMS SPL umodel mode (four tested constraints, see the CMS UModel query reference for details)
# ① Must start with a directive (bare index queries are rejected: "index query is not supported in umodel mode")
--query ".trace_set with (domain='apm', name='apm.trace.common') | ..."
# ② Attribute keys containing dots → JSONPath must use bracket notation (dot notation parses as nested path, tested to return all null)
| where json_extract_scalar(attributes, '$["gen_ai.session.id"]') = '<sid>'
# ③ Aggregation only supports alias-equals form (count(*) as c / count(*) by f / count() by f all fail)
| stats c = count(*) by serviceName
# ④ statusCode type is inconsistent → must cast (= 2 and = '2' both fail)
| where cast(statusCode as bigint) = 2
# Time parameters are unix seconds
--from 1787000000 --to 1787086400
```
```bash
# eBPF side: SLS raw search (runtime fields are not indexed, no server-side SQL aggregation)
--query '*' --line 100 --offset 200 --reverse false
# Only indexed fields can be filtered server-side:
--query '"container.id": "<cid>"'   --query '"event.name": "http.request"'
```

#### ❌ INCORRECT
```bash
--query "* | select ... group by \"agent.type\""   # ebpf-event runtime fields are not indexed, server-side aggregation is rejected
--query '5e1733a5a663fea7e76b9f8718ab9e9c'         # traceparent is not in the full-text index, tested bare-word search returns 0 rows (--trace-id can only be filtered client-side)
--query 'gen_ai.session.id: x'                     # Unquoted dot-field full-text search gets tokenized, won't match
--line 1000                                        # Raw search single-request limit is 100, exceeding is invalid (must paginate)
| stats count(*) as c by serviceName               # SPL does not accept 'as' alias (must use c = count(*))
| where statusCode = 2                             # Type mismatch error (must use cast(statusCode as bigint) = 2)
json_extract_scalar(attributes, '$.gen_ai.session.id')   # Dot notation parses as nested path, returns all null
aliyun cms get-entity-store-data ...(without --api-version 2024-03-30)   # CMS 2.0 API is not in the default version
```

## 6. Trace Enumeration and Anchoring Rules

#### ✅ CORRECT
**The analysis unit is a single user-specified trace (trace_id)**; there is no trace sampling: ① Enumeration is only for overview (`trace_overview.py`) and content-based locating (`span_search.py`) — LoongSuit side enumerates traces by `gen_ai.span.kind=ENTRY` (CMS SPL predicate; when the slice has no ENTRY spans, falls back to `kind=LLM` and marks `enumeration_fallback: no-entry-span`); ② The analysis anchor is `--trace-id`, **required for `trace_chain.py` in all modes** — LoongSuit side uses `where traceId in ('<id>')` predicate for initial trace boundary probing (startTime/duration lightweight projection), then fetches details within boundary ± `--margin` narrow window (empty narrow window falls back to full window and marks `fallback_full_window`); `decision_evidence.py`'s `--trace-id` direct branch can cover traces without ENTRY spans (bypassing enumeration); ③ `gen_ai.session.id` is only a span container attribute echo (carried by enter/invoke_agent), not an analysis unit; ④ eBPF side has **no session layer**, groups by `trace_id` parsed from `http.request.header.traceparent`, response rows inherit trace_id via `http.exchange.id` from request rows (`sls_event.link_by_exchange`), rows without traceparent go into `ungrouped.rows`. `trace_overview.totals.trace_ids` (top 50) is a window fact for users to pick their target trace; **the skill does not select on behalf of the user**.

#### ❌ INCORRECT
Enumerating by `gen_ai.operation.name=enter` (ENTRY's operation.name is not defined in spec, and apps without entry-layer instrumentation will return nothing); asserting "no data / wrong binding" when predicate enumeration returns 0 without first doing an **unfiltered control probe** (removing the `gen_ai.span.kind` predicate for the same slice); grouping and counting LLM/tool calls by span's session.id (spans missing session.id will be undercounted, should anchor by trace_id); the skill selecting "the most interesting trace" or doing per-trace ranking (traces are user-specified); eBPF side not doing `sls_event.link_by_exchange` and treating response rows as "ungrouped" (traceparent is only on request rows, response rows must inherit trace_id via `http.exchange.id`); eBPF side using server-side SQL aggregation on runtime fields (`agent.type`/`pid`/`comm` etc. are not indexed, will be rejected); treating `--trace-id` as a server-side predicate pushdown (this header is not in the full-text index, tested bare-word search returns 0 rows, can only be filtered client-side).

## 7. Dual-Source Binding and Query Scope

#### ✅ CORRECT
**Binding rules**: `--region` is required; `--project` (eBPF source) / `--workspace` (LoongSuit source) **at least one**, provided via CLI arguments or environment variables (`AGENT_OBS_REGION` / `AGENT_OBS_SLS_PROJECT` / `AGENT_OBS_CMS_WORKSPACE` / `AGENT_OBS_SERVICE_NAME`, CLI takes priority), `Config.resolve` validates at startup, listing all missing items and terminating when both are absent. **Binding only one side is a valid configuration**: `sls_event.resolve_mode` returns `(mode, narrowed)` and automatically narrows to the bound source, the absent side is marked `bound=false` + `gap` in `sources.<name>`, and `mode_narrowed` is output — **no silent degradation**; explicitly specifying `--mode` pointing to an unbound source raises an error. `--mode` accepts `both` (default) / `loongsuit` / `ebpf`; legacy values `trace`/`event`/`auto` raise an error with a rename mapping. Any scope including ebpf triggers `list-log-stores` to probe for `ebpf-event`.

**Clarify five business facts with the user**: ① Agent application name (→ `--service-name`) ② Region (→ `--region`) ③ Time range of the trace (→ `--from/--to` slice) ④ **SLS Project name and CMS 2.0 workspace name (at least one)** (→ `--project` / `--workspace`) ⑤ **Target trace trace_id** (→ `--trace-id`, the skill does not sample traces). **Only ask the user**: check conversation history/context first, ask the user directly if not available; **the skill has no auto-discovery mechanism**, if the user cannot provide these names, explain the console navigation path in text so they can find it themselves, **do not guess or concatenate resource names**; when the user cannot provide a trace_id, present `trace_overview`'s `totals.trace_ids` for them to choose. **Clarify agent application name in the same batch** (`--service-name`, optional but **strongly recommended**): it **only takes effect on the LoongSuit side** (CMS SPL `serviceName = '<app-name>'` predicate); ebpf-event index has no `service.name` nor `__tag__:__service_name__`, so eBPF side always sets `service_filter_unavailable: true`, use `--agent-type` / `--comm` / `--container-id` / `--host` / `--event-name` to narrow instead (first three are not indexed, can only be filtered client-side). Values must be copied verbatim from the console (exact match). When omitted, execution proceeds normally but output notes declare "not narrowed to a single application". The script output's `binding` / `mode` / `sources` fields faithfully reflect the query scope, binding on both sides, and narrowing status; **dual-source results are aligned by `trace_id`** (eBPF rows parsed from `http.request.header.traceparent`).

**Step 0.5 Preflight (mandatory)**: After clarifying bindings and before issuing any queries, run `scripts/preflight.py --region <region> [--project ...] [--workspace ...]`, seven checks (`cli_version` / `plugins` / `credentials` / `bindings` / `sls_project` / `ebpf_logstore` / `cms_workspace`). Unbound sides have their corresponding check set to `skipped` (valid configuration, not a failure); `credentials` only outputs the credential **type** (AK/STS/RamRoleArn/...), **credential values never enter the output**; `--strict` with any `fail` results in exit code 2. **Preflight does not check data** (no time window parameters), data existence is surfaced by analysis scripts' `totals` / `genai_index_coverage`.

#### ❌ INCORRECT
Treating loongsuit/ebpf as mutually exclusive data sources (drawing conclusions from querying only one side); both absent but running silently empty instead of erroring; hardcoding logstore names without probing; silently continuing when ebpf logstore probe fails (should error and record as a connectivity gap); asserting traces don't exist based on single-source absence (should mark "other source absent = connectivity gap discovered"); **treating preflight's `skipped` as a failure** (unbound side set to skipped is valid configuration); **ignoring `mode_narrowed`** (when only one side is bound, output explains narrowing from both to which side); **not asking the user for SLS Project / CMS workspace names and instead guessing or concatenating** (e.g., fabricating based on `agentloop-<encoding>` pattern); **skipping preflight and issuing queries directly**; **using server-side SQL aggregation on ebpf-event** (runtime fields are not indexed, will be rejected; must use raw search + client-side aggregation); **treating all-zero `genai_index_coverage` as a script bug** (it's a data-side fact — the collector only emits runtime facts); repeatedly asking the user for known bindings at the start of every session (should check conversation history first); **asking the user to set binding parameters** (the Agent should pass them inline in commands or set environment variables); **using parameter names/variable names instead of business names when asking**; **sending help documentation links to the user** instead of explaining the console location (menu > tab > column name); **guessing or rewriting agent application names** (must copy console verbatim — wrong names cause 0 rows on LoongSuit side, then falsely report "connectivity gap"); **not doing a control probe without `--service-name` when LoongSuit side returns 0 rows** before asserting no data; **treating eBPF side numbers as single-application scope when `service_filter_unavailable: true`** (eBPF side can never be narrowed, should be explicitly marked); **issuing any query without confirming specific start/end times with the user, or when the confirmed slice span exceeds the maximum window limit (`AGENT_OBS_MAX_WINDOW_HOURS`, default 4h)** — the limit applies to all steps, both sources (LoongSuit spans and eBPF rows) equally, not just `--match`, e.g., `span_search.py --hours 168 --match "<keyword>"` (anti-pattern: first clarify the specific time period of the trace, use `--from/--to` to pin a ≤4h slice, then execute the query).

## 8. --match Semantics (span_search.py, content-based span locating)

#### ✅ CORRECT
`span_search.py`'s `--match` is a **case-insensitive substring search**, **LoongSuit side only** (ebpf-event has no message payloads, content search is meaningless; `--workspace` missing triggers `ObsError`): after enumerating traces within the window (ENTRY→LLM fallback, `--max-traces` cap, default 200), client-side scans each span's `gen_ai.input.messages` **and** `gen_ai.output.messages` across **all roles**, hits output flat `hits[]`: `{trace_id, span_id, op, agent, service, field: "input.<role>"|"output.<role>", start, snippet}` — injection-type content typically hits with `field=input.tool` (tool results entering context), user's original words usually land in `input.user`. Each span records at most one hit per side (`--limit`, default 50, earliest first). **A hit is an anchor**: `trace_id` feeds into `trace_chain.py --trace-id`, `span_id` feeds into `decision_evidence.py --span-id`. **Window constraints rely on clarification discipline, not script guardrails**: `--match` should only be executed within a slice confirmed in Step 0 with span ≤ `AGENT_OBS_MAX_WINDOW_HOURS` (default 4h); **no script reads this variable or rejects wide spans**, exceeding the limit will just be very slow, not exit 2.

#### ❌ INCORRECT
Matching only the first-round input fragment and claiming "deep text doesn't exist / trace doesn't exist"; searching only the eBPF side for message content (no message payloads, scripts won't even accept it); treating hits as full text (output is truncated context snippets); using unescaped match text directly in SQL literals (single quotes must be escaped); running `--match` with excessive span without confirming a specific time period (e.g., `span_search.py --hours 168 --match "<keyword>"` — **won't be rejected by the script, just extremely slow**, relies on Step 0 clarification record for self-discipline); covering wide time range needs by **enlarging a single span** (should split into multiple ≤-limit slices and query each).

## 9. Error Determination Rules (LoongSuit Side Tested Constraints)

#### ✅ CORRECT
Three-level determination: `statusCode = 2` (OTel ERROR) → `gen_ai.response.finish_reasons` contains `"error"` → attributes' `otel.status_code` is ERROR (`statusMessage` carries the exception class name). `cms_trace.cms_span_to_row` preserves the original `statusCode` and derives the `error` boolean. Tested statusCode distribution: `0`=UNSET (15198) / `1`=OK (9) / `2`=ERROR (115).

#### ❌ INCORRECT
Treating `statusCode` `0` (UNSET) / `1` (OK) as errors (only `2` is OTel ERROR); filtering statusCode in SPL with `statusCode = 2` or `statusCode = '2'` (tested both fail due to type mismatch, must write `cast(statusCode as bigint) = 2`); counting non-GenAI framework spans (no gen_ai.operation.name) in GenAI statistics (should be collapsed/filtered); applying the same error rules to the eBPF side (eBPF side errors come from `error.type`/`error.message` or `http.response.status_code >= 500`).

---

# Correct Script Patterns

## 1. Shared Layer Reuse

#### ✅ CORRECT
```python
import obs_core as c
import sls_event as e
import cms_trace as a
cfg = c.Config.resolve(args)
mode = e.resolve_mode(cfg, args)
raw, facets, truncated, narrowing = e.fetch_ebpf_rows(cfg, f, t)   # eBPF side raw search + client-side aggregation
rows, truncated = e.run_ebpf_search(cfg, query, f, t, max_rows=2000)  # eBPF raw search (paginated)
spans = a.fetch_traces_spans(cfg, trace_ids, f, t)         # loongsuit side details
value = c.to_int(row.get("tokens"))     # Defend against string "null"
```

#### ❌ INCORRECT
Each script calling aliyun via subprocess independently; `int(row["tokens"] or 0)` (crashes on `"null"`); event raw search not assuming single-request 100-row limit.

## 2. Analysis and Evidence

#### ✅ CORRECT
Qualitative conclusions reference script output's messages/arguments/result fragments + evidence identifiers (LoongSuit side: trace_id/span_id; eBPF side: event.id + http.exchange.id); insufficient evidence marked as "missing"; error counts state the methodology (LoongSuit: span error determination three-level rules `statusCode=2`; eBPF: `error.type` non-empty or `http.response.status_code >= 500`); eBPF side TTFT and token counts marked as "missing", not fabricated (ebpf-event does not have these two field types).

#### ❌ INCORRECT
Qualitative conclusions without evidence identifiers; guessing full content from truncated text; fabricating data to fill gaps; fabricating TTFT/token counts/messages on eBPF side (ebpf-event does not have these fields).

## 3. Parameter Confirmation

#### ✅ CORRECT
`--region` is required; `--project` / `--workspace` **at least one**, missing causes script error listing all missing items; **no environment variable channel**. Value sources: clarify with the user — agent application name / region / trace time range / **SLS Project name and CMS 2.0 workspace name (at least one)** / **target trace trace_id** — five items, check conversation history first, ask user directly if not available; names **can only be obtained from the user** (no auto-discovery mechanism), the Agent passes them inline in commands; agent application name obtained in the same batch is passed via `--service-name` (strongly recommended, **LoongSuit side narrowing only**); time window/filter parameters come from user confirmation — must clarify to **specific start/end times** and **span ≤ maximum window limit** (`AGENT_OBS_MAX_WINDOW_HOURS`, default 4h), passed via explicit `--from/--to` (precise span, past slices hit permanent cache). Wide time range needs should be split into multiple ≤-limit slices queried individually, with coverage stated in conclusions. After binding confirmation, run `scripts/preflight.py` for seven configuration checks before issuing queries.

#### ❌ INCORRECT
Hardcoding user's project/region/workspace/application name; **not asking the user for SLS Project / CMS workspace names and instead guessing or concatenating binding names** (e.g., fabricating based on `agentloop-<encoding>` pattern); **skipping `preflight.py` and issuing queries directly**; assuming default time window and executing large-scale queries without confirmation; assuming default values when required bindings are missing; **going through without `--service-name`** and treating cross-application mixed numbers as single-application conclusions; **any query exceeding span limits** (not just `--match`, includes overview/search/chain/evidence, both sources equally); when a trace is not found, trying to find it by **enlarging the span** (should shift the slice: move `--from/--to` to the time period when the trace actually occurred, span unchanged); **the skill selecting a trace to drill into** (traces are user-specified, when unavailable present `totals.trace_ids` for user to choose).

## 4. Caching and Window Behavior (P0 Performance Optimization)

#### ✅ CORRECT
All GetLogs / ListLogStores / CMS queries go through unified caching in `sls_event`/`cms_trace` (SLS key = sha256 of project+logstore+region+query+from+to+line+offset+reverse; CMS key = api+region+workspace+params); entries whose window end exceeds 5 minutes (`CACHE_STABLE_AGE`) are marked `stable` for permanent caching, recent window entries expire per `AGENT_OBS_CACHE_TTL` (default 1800s); atomic writes (tmp + `os.replace`); cache read/write failures silently degrade to normal API calls. Relative windows (`--hours`) have their end aligned upward to a 300s grid, start pushed forward by one additional grid (`resolve_window`); **all scripts default to 4h span, from a single source `obs_core.DEFAULT_HOURS`**, and **there is no span limit validation code** (the limit is Agent clarification discipline). `trace_chain`'s LoongSuit side detail fetching automatically narrows to **trace boundary ± `--margin`** (first using `where traceId in ('<id>')` predicate for lightweight startTime/duration boundary projection), if no spans are found after narrowing, automatically falls back to full window and sets `fallback_full_window`; **eBPF side cannot narrow** (`window_narrowed` is always null, anchor fields are not indexed), paginated fetching exceeding the cap sets `fetch_truncated` (at which point counts are samples).

#### ❌ INCORRECT
Bypassing the shared layer to issue queries independently (cache invalidated and read-only interception lost); applying grid alignment to explicit `--from/--to` windows (only relative windows are aligned); assuming event details single-request `--line 1000` (single-request limit is 100, must paginate); still issuing CLI calls on cache hit; treating `--no-cache` as default.

## 5. Implementation Responsibility Division (CLI/Code vs Agent vs Human-Computer Interaction)

#### ✅ CORRECT
All data access and quantitative aggregation goes through existing scripts (whitelist/read-only interception/caching/UA auto-inheritance); qualitative analysis (Step 4) and report annotation writing (Step 5) are done by the Agent executing the skill; scope clarification/target trace confirmation via human-computer interaction — **the maximum window limit has no script backstop**, the only execution basis is Step 0's clarification record; scripts only surface volume markers (`enumeration_truncated` / `fetch_truncated`), do not validate window span. When analysis reveals an analysis-view gap, analyze the root cause of the temporary operation, abstract commonalities, build the capability into the script's standard output, then proceed with analysis.

#### ❌ INCORRECT
Implementing semantic analysis via CLI/code (e.g., writing a script to keyword-score messages as conclusions); generating temporary shell/python scripts during analysis to post-process script output; treating data-plane gaps (event has no TTFT, ResultCode always -1) as script bugs to "fix" or fabricating data to fill; treating the absence of the external `ram-permission-diagnose` skill as an execution failure (should degrade to manual comparison against ram-policies.md).

## 6. Report Rendering (report_render.py)

#### ✅ CORRECT
Rendering is **template injection**, not document assembly: trace facts (`--facts chain=trace_chain.py output`) are mapped to a single `window.TRACE_DATA = {meta, summary, spans}` (summary is always `{}`, all aggregation is derived client-side from spans by the template, the Agent does not copy numbers), undergoes structural redaction (`redact_tree`: five regex patterns for `private_key_block`/`bearer_token`/`aliyun_access_key`/`aws_access_key`/`secret_assignment`) and **script block safe encoding** (`js_data_literal`: `<`/`>`/`&` escaped to `\u003c`/`\u003e`/`\u0026`, U+2028/U+2029 also escaped, no string can escape the `<script>` block), then replaces the example TRACE_DATA assignment and `<title>` in the template `report-template.html`; **4 structural self-checks before rendering**: R1 chain facts must contain non-empty `steps[]`, R2 `schema_version == "obs-trace-report-v1"` and spec.notes keys must be real spanIds in the trace, R3 title/notes text ≤ `--text-limit` (default 4000), R4 Agent-authored layer (spec) monetary semantic text is always rejected (neither source has price data, amounts can only be "missing"). **Self-containment is tested, not asserted**: `self_containment_scan` counts external-linked resources (`src=`/`href=` with `//` references, must be 0) and `<script` block count (must be exactly 1, the template's built-in renderer) on the final artifact, refusing to render if not met — a polluted template cannot produce a report. **Annotation is evidence**: the Agent's analysis conclusions go into `spec.notes[spanId]`, rendered as the node's note field, anchoring is naturally established; failed spans without annotations fall back to `statusMessage` as factual baseline. Layman attribution categories and suggested actions are determined by the Agent per the attribution taxonomy, the renderer must not contain keyword mapping tables, thresholds, or scoring. `--out -` is an intentional inversion (HTML→stdout, summary→stderr), used to allow tests to assert HTML content.

#### ❌ INCORRECT
Injecting telemetry content directly into the template without redaction/encoding (in hijack scenarios, tool results are attacker-controllable); modifying `js_data_literal` to remove `<`/`>`/`&` escaping (strings could then close the `<script>` block and inject code); bypassing `--spec` to directly modify numbers in facts files (report numbers can only come from trace facts' TRACE_DATA mapping, spec only carries text); writing monetary amounts or unit prices in spec/notes (R4 mechanically rejects); adding external CDN/font/scripts to the template or a second `<script>` block (self-containment guard directly refuses rendering); treating `report self-check failed` as a data issue (it's a spec structure issue); using `:target` + `href` for interaction; fabricating values for metrics without data support (show "no data available" when data is missing); writing keyword→attribution-category mapping tables, severity thresholds, or scoring in Python (violates §6); treating the example TRACE_DATA position in the template file as a place to hand-copy numbers (that assignment is entirely replaced, hand-copied content is all lost).
