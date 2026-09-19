# HTML Report Rendering Contract (TRACE_DATA Template Injection)

The **sole deliverable form** of observation reports is self-contained HTML, rendered by `scripts/report_render.py`: it maps
`trace_chain.py`'s trace facts into a **single `TRACE_DATA` object**, injects it into the bundled page template
`report-template.html`.

Division of labor red line: **scripts provide facts, the Agent provides annotations, the template provides presentation**. The renderer contains no keyword mapping tables,
severity thresholds, or scoring — plain-language attribution classification and recommended actions are determined by the Agent per the attribution taxonomy; **every number in the report comes from chain facts**;
the Agent only provides text annotations (title and per-span notes), not hand-copied numbers.

## 1. Rendering Pipeline

```
--facts chain=<trace_chain.py output>(required)
  -> chain_root validation (both mode feeds into loongsuit segment; ebpf-only is directly rejected)
  -> optional --spec annotations (Agent text)
  -> check_report self-check (R1-R4, thrown all at once before rendering)
  -> build_trace_data maps to {meta, summary, spans}
  -> redact_tree structural redaction (title also goes through redact())
  -> js_data_literal script-safe JSON encoding
  -> inject into template (replaces TRACE_DATA assignment block + <title>)
  -> self_containment_scan measured self-containment guard (fails = rejected)
  -> HTML artifact + rendering summary
```

This script makes **zero cloud calls, does not accept binding parameters, and depends only on `obs_core`**.

## 2. TRACE_DATA Data Contract

The template's data entry point is `window.TRACE_DATA = {meta, summary, spans}`; the template contains all rendering
logic (8 sections: Trace Info / Trace Analysis / Performance Analysis / LLM Calls / TOOL Calls / Execution Trace
Tree / Gantt Timeline / Node Details); missing data shows "No data available" rather than being fabricated.

| Section | Source | Description |
|---|---|---|
| `meta` | chain top-level + enter/invoke_agent/chat spans | traceId / sessionId (span attribute echo) / agent / model / query (entry message) / startTime / endTime / status / env / user; `title` prepended before rendering |
| `summary` | **always `{}`** | Every summary number is derived by the template from spans; **never hand-filled** |
| `spans[]` | Mapped from `chain.steps[]` item by item | See table below |

Span mapping (`build_trace_data`):

| TRACE_DATA Field | From chain step | Description |
|---|---|---|
| `id` / `parentId` | `spanId` / `parentSpanId` | Parent not in chain = null (root node) |
| `kind` | `op` via `KIND_BY_OP` | enter/invoke_agent->agent, react->react, chat->llm, execute_tool->tool; unknown op falls to agent |
| `name` | op + model/tool/round | e.g., `LLM . qwen-max`, `execute_tool . read_file` |
| `startMs` / `durationMs` | Offset relative to trace start / `duration_ms` | Gantt chart coordinates |
| `round` | react itself or nearest react ancestor | Turn attribution |
| `status` | `error` | `ok` / `error` |
| `promptTokens` / `completionTokens` / `cachedTokens` / `totalTokens` / `ttftMs` | Token and TTFT fields | Only written when non-empty |
| `input` / `output` / `inputChars` / `outputChars` | Message text and size | Template truncates for display |
| `note` | **spec.notes[spanId]**, failed span fallback to `statusMessage` | Agent annotation takes priority; fact as fallback |

**Anchoring discipline**: `--facts` must contain `chain=` (`trace_chain.py` output). Both-mode facts
must carry the loongsuit segment (the template renders the GenAI span tree; the eBPF side has no GenAI spans; standalone ebpf
facts are directly rejected with a prompt to bind `--workspace`).

## 3. Annotation Spec (Agent Authoring Layer)

`--spec` is **optional** JSON, carrying only the Agent's qualitative text:

```json
{
  "schema_version": "obs-trace-report-v1",
  "title": "Task Review: Logistics Complaint Order Query",
  "notes": {"<spanId>": "First-token wait is high, needs review"}
}
```

- **Text only, no numbers**: all numeric values are derived by the template from facts; Agent hand-copied numbers have no landing point
- `notes` keyed by spanId, rendered as notes on that span node (failed spans without annotation fall back to
  `statusMessage` fact)
- `title` defaults to `Agent Trace Observation Report . <trace_id>`, injected into `<title>` and `meta.title`
- Per-item qualitative conclusion evidence identifiers are carried by the spanId itself (template nodes are evidence anchors); cross-source conclusions reference `event.id`/`http.exchange.id` in the note text

## 4. Self-Check Rules (R1-R4)

Before rendering, all errors are accumulated and thrown at once as
`report self-check failed: ...` (`ObsError` -> stderr + exit 2):

| # | Rule | Level |
|---|---|---|
| R1 | Chain facts must carry non-empty `steps[]` (missing `--facts chain=` is the same) | Fatal |
| R2 | `schema_version` (when provided) must be `"obs-trace-report-v1"`; every key in `notes` must be a real spanId in the chain | Fatal |
| R3 | `title` and each note exceeding `--text-limit` (default 4000) -> error with identification | Fatal |
| R4 | Monetary-semantic text in spec (`price/pricing/cost/fee/billing/currency` and their Chinese equivalents) -> always rejected; neither source has price data; amounts can only be written as "missing" | Fatal |

R4 is the mechanical enforcement point of the "consumption uses token caliber only" decision; it does not rely on human memory. The old
`report_check` R1-R16 (block enumeration, `value_ref` parsing, `session_flow` swimlanes) has been retired along with
the 14-block rendering model.

## 5. Template Injection Contract

Template: `report-template.html` (`--template` can override, for testing). The template
**contract** is two anchor points; missing either triggers `ObsError` (exit 2):

1. **`window.TRACE_DATA = ...` assignment block** — `inject()` uses regex
   `window\.TRACE_DATA\s*=` to locate the **assignment** (not a bare name: the template header comment also mentions this name),
   replacing up to the first `\n};` (the template's built-in example data object). Anchoring on the assignment is anti-regression: files where only
   a comment mentions TRACE_DATA must be rejected (TC14 pins this)
2. **`<title>...</title>` element** — replaced with the report title (`html.escape` escaped)

**Template discipline** (sanitization requirements, delivered as part of the distribution package): zero external resources (CDN/fonts/images/scripts),
zero sensitive information (tokens / empIds / personal names / tracking variables), exactly one `<script>` block (the template's
built-in rendering logic). The template is **both an input surface and a distribution surface**; contaminated templates are rejected by the guard in the next section,
and no report is produced.

## 6. Redaction and Script-Safe Encoding

Reports are distributed artifacts; telemetry content is attacker-controllable in hijack scenarios, so this layer is the
skill's only XSS surface.

- **Order: `redact` -> encoding**. Redaction must see the original text; encoding ensures strings cannot escape the script block
- `TRACE_DATA` is written via `js_data_literal`: JSON (`ensure_ascii=False`, compact separators)
  then all `<` / `>` / `&` and U+2028/U+2029 are escaped to `\uXXXX` — **no string can
  close the template's `<script>` block or inject tags**; this single chokepoint covers body content, attribute positions, and
  `<title>` (the latter additionally goes through `html.escape`)
- **Structural redaction** (`REDACT_PATTERNS`, replaced with `[redacted:<class>]`):

| class | Match Pattern |
|---|---|
| `private_key_block` | `-----BEGIN ... PRIVATE KEY-----` (to END or line end) |
| `bearer_token` | `bearer` / `token` + 16+ character token string |
| `aliyun_access_key` | `LTAI` + 12-24 characters |
| `aws_access_key` | `AKIA` / `ASIA` + 16 characters |
| `secret_assignment` | `password` / `secret` / `api_key` / `access_key` = value |

- **Boundary declaration**: This is **structural regex**, not semantic PII detection. The responsibility for what content the Agent chooses to quote lies with the Agent. The rendering summary reports `redaction.hits[]` and this boundary
- **Assertion caliber** (see `tests/cases/TC13.md`): `<svg onload=` and `javascript:` — these
  **bare substrings do appear in the artifact**, within `\u003c`-escaped JSON literals — the report truthfully
  shows what is in the telemetry. Asserting they do not exist would cause a **correct** renderer to falsely fail, so tests only
  assert that **live forms** (unescaped tag structures) do not exist

## 7. Self-Containment Measured Guard

Self-containment is not a declaration; it is **measured against the final artifact** (`self_containment_scan`):

- `external_assets`: count of `(src|href) = "//..."` pattern external references in the artifact; **must be 0**
- `script_blocks`: count of `<script` blocks; **must be exactly 1** (the template's built-in renderer; the renderer itself
  does not add any scripts)
- Violation triggers `ObsError` rejecting rendering — **when the template is contaminated, prefer not producing a report**; this is a hard anti-regression boundary

The rendering summary faithfully records `self_contained{external_assets: 0, script_blocks: 1,
inline_js: 1}`, asserted by TC13. Interactions within the template (section collapsing, node selection) are all driven by that single
script block, with no external dependencies.

## 8. Output Contract and Artifact Paths

- `--out PATH`: HTML written to file (directory auto-created), rendering summary to stdout (`--format`)
- `--out -`: HTML written to **stdout**, rendering summary moved to **stderr** — the only way for tests to assert HTML
  content; this is an **intentional inversion**, declared in `--out` help
- Rendering summary fields: `schema_version` / `trace_id` / `title` / `bytes` / `sha256` /
  `facts.pool` / `redaction{applied, hits, boundary}` / `notes_applied` /
  `self_contained` / `template` / `self_check{rules_evaluated: 4, errors: 0}`
- `reports/facts/*.json` — each script's `--format json` output (fact layer);
  `reports/html/*.html` — rendered artifacts; both covered by `.gitignore`'s `reports/*`
