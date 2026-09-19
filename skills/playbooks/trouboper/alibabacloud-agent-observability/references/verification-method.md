# Success Verification Method

Prerequisites: Completed SKILL.md §2/4 pre-check (CLI >= 3.3.3, `aliyun configure list` valid, SLS / CMS plugins installed; **binding rules**: `--region` required, `--project` (eBPF source) and `--workspace` (LoongSuit source) **at least one**; supports CLI arguments or environment variables `AGENT_OBS_REGION` / `AGENT_OBS_SLS_PROJECT` / `AGENT_OBS_CMS_WORKSPACE` / `AGENT_OBS_SERVICE_NAME`, CLI takes priority), and has run Step 0.5's `scripts/preflight.py` (seven checks; unbound side set to `skipped`, which is a valid configuration). Value sources: agent application name / region / time range / **SLS Project name and CMS 2.0 workspace name** / **target trace trace_id** obtained via clarification from the user (**can only be obtained from the user**, the skill has no auto-discovery mechanism). **Shell variables in this document are the verifier's own operational convenience**, not requirements for end users — when facing end users, never mention parameter names/variable names. Each step below has clear success criteria; if any step fails, check stderr first (missing binding → ask user for names to fill in; permissions → ram-policies.md; project/workspace does not exist → verify bindings).

## Step 0 — Binding and Target Trace Confirmation (Obtain from User)

Bindings and target trace can only be provided by the user (the skill has no auto-discovery mechanism):

- **CMS 2.0 workspace name**: workspace list in the Cloud Monitor 2.0 console (→ `--workspace`)
- **SLS Project name**: project list in the Log Service console, the one storing the `ebpf-event` logstore (→ `--project`)
- **Target trace trace_id**: trace ID obtained by the user from application logs / console / platform links (→ `--trace-id`); when the user cannot provide it, present Step 1's `totals.trace_ids` (top 50) for them to choose, **the skill does not select on behalf**

**Success criteria**: Both names are verbatim from the console, trace_id is explicitly specified by the user, **not guessed or concatenated based on naming patterns** (wrong names cause queries to silently return 0 rows, which is then misjudged as "no data in the window"). Getting only one binding is still runnable (automatically narrows to that source).
**Failure mode**: User cannot provide → explain the console navigation path in text for them to find it, **do not guess, do not concatenate**; when both are missing, the script exits with code 2 and lists all missing items at once.

Commands below uniformly use a shell variable to hold the binding and target, `<sls-project>` / `<cms-workspace>` / `<trace-id>` are from user clarification:

```bash
BIND="--region cn-hangzhou --project <sls-project> --workspace <cms-workspace> --service-name <agent-app-name>"
TID="<trace-id>"
```

`--service-name` is optional but **strongly recommended**: it **only takes effect on the LoongSuit side** (CMS SPL `serviceName = '<app-name>'` predicate). ebpf-event index has no `service.name` nor `__tag__:__service_name__`, so eBPF side always sets `service_filter_unavailable: true` with a note (not an error); to narrow eBPF side, use `--agent-type` / `--comm` / `--container-id`. When `--service-name` is omitted, results cover all applications under the binding, and output notes declare "not narrowed to a single application".

Scripts validate bindings at startup (`--region` required; `--project` / `--workspace` **at least one**, when both are missing, lists all missing items and terminates), default `--mode both` — **when only one side is bound, automatically narrows to the bound source and outputs `mode_narrowed`**, the absent side marks `bound=false` + `gap` in `sources.<name>` (connectivity gap, no silent degradation). Output's `mode` / `binding` / `sources` fields indicate query scope and binding status on both sides (eBPF side's `binding` also contains `service_name` / `applied` / `service_filter_unavailable` / `fetch_truncated`). Each step below gives success criteria for both scope and single-source (loongsuit/ebpf).

> **Output format rules**: Scripts have only two output formats — `--format json` (default, stable machine contract) and `--format yaml` (isomorphic YAML), **markdown is no longer an option**. **Script stdout is not the observation report** — the observation report is always a self-contained HTML (see Step 5 below). Field-level success criteria are based on json output; commands below omit `--format` which defaults to json.

> This document verifies capabilities script by script; the daily analysis entry point follows SKILL.md §8's "trace_overview overview (optional) → user confirms target trace_id → trace_chain chain reconstruction" flow, no need to run overview first.
>
> **Window discipline**: All queries must first go through SKILL.md §8 Step 0 clarification, confirming a specific slice with **span ≤ maximum window limit** (`AGENT_OBS_MAX_WINDOW_HOURS`, default 4h; the limit is the `to − from` span, not "can only query the most recent 4h"). Commands below uniformly use an explicit historical 4h slice example `--from 1787148000 --to 1787162400` (2026-08-19 22:00 ~ 2026-08-20 02:00, span 14400s = 4h); replace with your confirmed slice during actual verification. Explicit slices have precise spans and past slices hit permanent cache, making verification reproducible.

## Step 1 — Dual-Source Connectivity and Overview Aggregation (Optional; Verify Target Trace is in Window)

```bash
SKILL_SESSION_ID=$(openssl rand -hex 16) python3 scripts/trace_overview.py $BIND --from 1787148000 --to 1787162400
```

**Success criteria (both default)**: Output contains both trace side (`traces analyzed: N`>0, `genai spans`, `by operation`, `services (cross-Agent view)`, `totals.trace_ids`) and event side (`events: N`>0, `by event`, `errors by type`) sections; when one side is 0, mark it honestly, do not error-degrade.
**Success criteria (single-source troubleshooting)**: trace side same as above; event side same as above.
**Success criteria (drift comparison, optional)**: Adding `--compare-hours <N>` appends a `drift` section (`totals/chat latency/react/by model/by tool` each with `{base, current, delta_pct}`, trace side only); metrics with baseline 0 having `delta_pct=None` is normal.
**Success criteria (target verification)**: User's `$TID` appears in `totals.trace_ids` (top 50); when not present, shift the slice and try again, **do not enlarge the span**.
**Performance note**: Overview's trace detail fetching time grows with window span and trace volume, so span must be ≤ maximum window limit (default 4h); when enumeration hits the cap, output shows `enumeration_truncated: true` (sample scope, stderr also prompts) — this is normal protection, not an error; first confirm `$BIND` includes `--service-name` (if not, enumeration covers all applications under the binding), then add `--agent` or narrow the slice and rerun, or explicitly raise `--max-traces` (default 200). `--compare-hours <N>` is **double the query volume** (current slice + baseline slice shifted back N hours), both slices must each be ≤ limit.
**Failure mode**: Required binding parameters missing → stderr lists all missing items, fill them in and rerun; both sides N=0 → first verify whether `--service-name` matches the console "Application Name" exactly (exact match, wrong name causes LoongSuit side 0 rows; removing this parameter and rerunning distinguishes "wrong name" from "genuinely no data in the slice"), then consider **shifting the slice** (change `--from/--to` to point to the time period when data actually exists, span unchanged) or verifying bindings, **do not try to find data by enlarging the span**; LoongSuit side is 0 but you're certain the slice has data → first do the **unfiltered control probe** from Step 2 failure mode (overview and content search share the same enumeration path); `LogStoreNotExist`/`no 'ebpf-event' logstore` → eBPF source connectivity gap, verify project binding or confirm eBPF collector is installed; CMS / SLS permission errors → ram-policies.md. eBPF side `genai_index_coverage` all-zero is a data-side fact (collector only emits runtime facts), report honestly, not a script failure.

## Step 1b — Content-Based Span Locating (Optional; span_search.py)

```bash
# Discipline: --match should only be executed within a slice confirmed in Step 0 with span ≤ limit; scripts do not validate windows, wide spans won't be rejected, just extremely slow
python3 scripts/span_search.py $BIND --match "<keyword>" --from 1787148000 --to 1787162400
```

**Success criteria**: Each row in `hits[]` contains `trace_id` / `span_id` / `op` / `agent` / `service` / `field` (e.g., `input.user`, `input.tool`) / `snippet`; a hit is an anchor — `trace_id` feeds into Step 3's `--trace-id`, `span_id` feeds into Step 4's `--span-id`. Each span records at most one hit per side, total count constrained by `--limit` (default 50).
**Failure mode**: 0 hits but Step 1 has data → first check if output has `enumeration_fallback: no-entry-span` (application has no entry-layer instrumentation, enumeration has fallen back to `kind=LLM`); still 0 → do an **unfiltered control probe** — use CMS SPL to run the same slice without the `gen_ai.span.kind` predicate (`aliyun cms get-entity-store-data ... --query ".trace_set with (domain='apm', name='apm.trace.common') | project traceId, spanName | limit 10"`), if there are spans without the predicate but 0 with it, the problem is in the enumeration condition, not binding, timezone, or date; `--workspace` missing → exit 2 (ebpf-event has no message payloads, content search only has the LoongSuit path).

## Cache and Window Behavior Verification

```bash
# Run the same command twice to compare timing (explicit past slices don't push to grid, and window end >5min is immutable permanent cache, rerun must hit cache;
# cache statistics can be checked by running preflight.py separately, its output contains a cache section)
time python3 scripts/trace_chain.py $BIND --trace-id $TID --from 1787148000 --to 1787162400 --format json > /tmp/r1.json
time python3 scripts/trace_chain.py $BIND --trace-id $TID --from 1787148000 --to 1787162400 --format json > /tmp/r2.json
ls -l ${AGENT_OBS_CACHE_DIR:-/tmp/agent_obs_cache}/ | tail -3
# Bypass cache for comparison
time python3 scripts/trace_chain.py $BIND --trace-id $TID --from 1787148000 --to 1787162400 --no-cache --format json > /tmp/r3.json
```

**Success criteria**: Second run is noticeably faster than the first (hits cache, no more CLI calls; corresponding entries appear in cache directory); `--no-cache` run restores full timing; all three runs have identical `steps` count and `patterns`.
**Failure mode**: Second run shows no speedup → check if `--from/--to` is exactly the same in both commands, or if `AGENT_OBS_NO_CACHE` was accidentally set (if validating with relative `--hours`, may also have crossed a 300s grid boundary); data inconsistency → belongs to window boundary behavior, verify if `window` is the same in both runs.

## Step 3 — Chain Reconstruction

```bash
python3 scripts/trace_chain.py $BIND --trace-id $TID --from 1787148000 --to 1787162400
```

**Success criteria (both default)**: Output contains `loongsuit` and `ebpf` sections (**both sources anchored on same `--trace-id`**; loongsuit tree + ebpf exchange timeline); when one side has no data for the target, that section shows `present=false` + reason (connectivity gap discovery, not an error); **only errors when both are missing**.
**Success criteria (loongsuit single source)**: Output tree-shaped `steps` (enter→invoke_agent→react→chat/tool hierarchy correct, non-GenAI spans collapsed), `max react round`, `failed`, `tool loops` statistics; cross-Agent chains show multiple services with notes; contains `context growth` section (per-chat input_tokens sequence within the trace, growth summary and ballooning flag; `present=false` when fewer than 2 chats is normal); `latency` section contains trace self-baseline percentiles.
**Success criteria (ebpf single source)**: Output exchange timeline (request/response paired by `http.exchange.id`, including method/url_path/server/status/latency_ms/process), `patterns` (failed_exchanges / status_5xx / repeated_calls / unpaired), `processes`; `window_narrowed` **is always null** with `window_narrowed_note` (anchor fields are not indexed, cannot probe boundaries server-side, this is by design).
**Success criteria (all scopes)**: LoongSuit side output contains `window_narrowed` — detail fetching has automatically narrowed to **trace boundary ± `--margin`** (default 300s, boundary probed by `where traceId in ('<id>')` lightweight projection); when the trace spans the full window, it's null (no narrowing, normal); top-level `trace_id` is a single value equal to `$TID`.
**Failure mode**: `no ebpf rows found` → ebpf side only single-source absent (under both, marks `present=false`, not an error; single-source ebpf mode is the error); `no spans found` → this trace does not exist in this slice (correct approach is **shifting the slice**: use `--from/--to` to move the slice to the time period when the trace actually occurred, span unchanged, or first verify with Step 1's `totals.trace_ids`); `exchanges_truncated` → output truncated by `--event-limit` (increase it); `fetch_truncated: true` → eBPF rows exceed per-logstore 2000-row cap (`sls_event.EBPF_FETCH_CAP`), **at this point all counts are samples not full counts**, narrow the slice or add `--container-id`/`--agent-type` filtering; LoongSuit side suspects a single react round exceeds margin causing missed spans → increase `--margin` (the script automatically falls back to full window for traces it can't fetch and marks `fallback_full_window`).

## Step 4 — Evidence Extraction

```bash
# LoongSuit side (--trace-id direct branch can cover traces without ENTRY spans, bypassing enumeration)
python3 scripts/decision_evidence.py $BIND --span-id <any spanId from Step3> --from 1787148000 --to 1787162400
python3 scripts/decision_evidence.py $BIND --trace-id $TID --span-id <spanId> --from 1787148000 --to 1787162400
# eBPF side (--event-id passes event.id)
python3 scripts/decision_evidence.py $BIND --mode ebpf --event-id <any event_id from Step3> --from 1787148000 --to 1787162400
```

**Success criteria (LoongSuit side)**: Output target summary, ancestor chain (at least 1 level), siblings count, react rounds count; chat/tool spans should have messages or arguments/result respectively; `entry_task` is the enter span's entry message (null when the trace has no enter span, which is normal); `session_id` is an attribute echo.
**Success criteria (eBPF side)**: Output target runtime facts (event_name/ts/event_sequence, http method/path/server/status code, process pid/comm/cmdline, container/host/k8s, agent_type), three-ring context (`context.same_exchange` / `same_process` / `same_trace`, where `same_exchange` should contain the paired other half); `messages` and `entry_task` **are always null** with notes explaining the reason (ebpf-event has no message payloads); `trace_id` and `trace_id_from` indicate whether the trace_id came from its own traceparent or was propagated via `http.exchange.id`.
**Failure mode**: `span/event not found` → use the full ID from Step 3 output (`--format json` view) (not the truncated display), or **shift the slice** (move `--from/--to` to the time period when the span/event actually occurred, span unchanged).

## Step 5 — Report Output (HTML, Template Injection)

Write analysis conclusions as an annotation spec (title + notes keyed by spanId, see
the rendering contract), along with trace facts, and pass to `scripts/report_render.py`
to inject into the `report-template.html` template. Scenario organization see
the scenario playbooks.

```bash
python3 scripts/report_render.py --facts chain=reports/facts/chain.json \
  [--spec reports/facts/notes.json] --out reports/html/<scenario>.html
```

**Success criteria**: HTML file is written and **self-contained** (rendering summary `self_contained`:
`external_assets=0`, `script_blocks=1`); the artifact is in **template injection form** — `window.TRACE_DATA = {…}`
has been replaced with trace data, `<title>` is the report title; template sections (trace info / trace analysis / performance
analysis / LLM calls / TOOL calls / execution trace / Gantt chart / node details) are all rendered
client-side from spans, showing "no data available" when data is missing; Agent annotations (`spec.notes[spanId]`) land on the corresponding node's
note field (anchoring is evidence); amounts never appear (spec layer monetary semantic text is rejected by R4);
`--out -` sends HTML to stdout, rendering summary to stderr.

**Failure mode**: `report self-check failed: …` → **spec structure issue, not a data issue**
(common: R1 facts is not trace_chain output, R2 notes keys are not in the trace, R3 text exceeds
`--text-limit`, R4 spec contains monetary amounts); fix the spec according to the named rule. `refused: the
artifact is not self-contained` → **template is polluted** (external resources or multiple script blocks), check the
template file. The renderer makes **zero cloud calls**, so any cloud-side errors are unrelated to it. Output directory is auto-created.

## Step 6 — Final Output (Two Fixed Components)

The skill's final deliverable must contain both components:

1. **Analysis summary answering the user's question**: Use natural language to directly answer the user's original question, providing **conclusive judgments + key evidence identifiers** (trace_id/span_id/event.id), 3–8 paragraphs. Do not repeat script output verbatim, distill insights.
2. **Agent trace observation report (HTML)**: The file path of the HTML report rendered in Step 5 (e.g., `reports/html/<scenario>.html`), which the user can open offline to view complete trace facts.

**Success criteria**: Output presents the summary first, then the report path; evidence cited in the summary (trace_id/span_id/event.id) is consistent with locatable nodes in the report; the summary does not repeat script stdout verbatim, but distills conclusions (e.g., "The trace stalled at the execute_tool stage, the last chat's finish_reasons contains tool_calls but there is no subsequent execute_tool span, evidence span_id=xxx"); the report path points to an actually existing HTML file.

**Failure mode**: Only outputting the report path without analysis summary → user doesn't know what to look for in the report; only outputting the summary without the report → loses the complete fact layer; summary repeating large blocks of script stdout JSON → insights not distilled, violates output specification.

## Read-Only Compliance Self-Check

```bash
# Only match command construction lines (not comments/docstrings), to avoid false positives from "aliyun sls" in documentation
grep -rn --include="*.py" '"aliyun", "sls"' scripts/ | grep -v -e "get-logs" -e "list-log-stores" && echo "VIOLATION" || echo "OK: only get-logs / list-log-stores"
grep -rn --include="*.py" '"aliyun", "cms"' scripts/   # The only place, action constrained by CMS_ACTION_WHITELIST
grep -rn --include="*.py" "CMS_ACTION_WHITELIST" scripts/cms_trace.py   # Confirm CMS read-only whitelist exists
grep -rn --include="*.py" "SPL_DENY" scripts/cms_trace.py               # Confirm SPL pipe command blacklist exists
grep -rn --include="*.py" "user_agent()" scripts/obs_core.py scripts/sls_event.py scripts/cms_trace.py scripts/preflight.py   # Confirm UA injection exists
grep -rn --include="*.py" "arms" scripts/ && echo "VIOLATION: ARMS dependency should have been removed" || echo "OK: no ARMS dependency"
```

**Success criteria**: No other `aliyun sls` subcommands in scripts besides `get-logs` and `list-log-stores` (both read-only); CMS calls limited to whitelisted `get-entity-store-data` / `list-workspaces`, and the seven SPL pipe commands that initiate external or model calls (`http-call` / `llm-call` / `agentic-call` / `embedding` / `entity-call` / `prom-call` / `graph-call`) are intercepted by `SPL_DENY`; write verb interception and UA injection have not been bypassed; **no ARMS dependency remnants**.
