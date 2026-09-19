# Plain-Language Attribution Taxonomy (For Agent Analysis)

**This table is where the discipline of "code does not perform semantic analysis" lands**: mapping knowledge is here for the Agent to read,
**not in Python**. `scripts/report_render.py` only renders the labels the Agent provides; it contains no keyword-to-category mapping tables, severity thresholds, or scoring (see
the acceptance criteria section 6).

The Agent's input is always the script's **raw facts**; the output is plain language + mandatory evidence citations +
explicit uncertainty.

---

## 1. Plain-Language Attribution Taxonomy

Five categories of plain-language attribution. **The "fact signature" is "what is observable"; the "plain-language label" is "what is shown to people"; the "boundary" column explains when determination is impossible**.

| Plain-Language Label | Observable Fact Signature | Mandatory Evidence | Boundary / Undeterminable Cases |
|---|---|---|---|
| **Parameter Error** | `error.type` looks like `ValidationError` / `InvalidArgument` / `SchemaError`; `statusMessage` contains field name or type mismatch; `tool_arguments` is missing required keys or has wrong value types; same `(tool, arguments)` retried without change | `trace_id`+`span_id`, `ev.target.tool_arguments` verbatim | Parameters **look** correct but the server still reports an error -> attribute to "External Service", not Parameter Error. Whether parameters "should" be filled this way requires business semantics; telemetry cannot determine this |
| **External Service Timeout** | eBPF side `http.status_code >= 500` or `error.type` looks like `Timeout`/`ConnectionError`; `exchange` latency far higher than same-slice same-type calls; `unpaired` requests (only request, no response) | `event.id`+`http.exchange.id`; LoongSuit side corresponding `span_id` | Slow does not equal timeout: check whether a response came back. `unpaired` may also be a collection boundary truncation; must combine with `fetch_truncated` to judge |
| **Model Hallucination** | Data tool **repeatedly fails** (`tool_loops` / `repeated_tool_calls`) but the round is still `complete`; the last round's `output.messages` gives specific values/conclusions without a successful data source | `trace_id`+`span_id`, last round chat's `output_messages`, failed tool's `span_id` | **Telemetry can only flag suspicious patterns, not determine hallucination** — determination requires comparison with actual values. Dirty data (not errors) produces no failure signal; this path is completely invisible |
| **Insufficient Permissions** | `error.type` looks like `Forbidden`/`Unauthorized`/`PermissionDenied`; `status_code` 401/403; same tool succeeds in other traces but fails in this one | `trace_id`+`span_id`, `statusMessage` | 403 may also be a resource-not-found disguised as forbidden; in cross-account AssumeRole scenarios, permission attribution requires separate investigation; telemetry cannot determine this |
| **Context Loss** | Last chat's `finish_reasons` contains `tool_calls` and there is no `execute_tool` span after it (determined by `steps` time order); large gaps on the `steps` timeline; `context_growth.input_tokens.growth_pct` is abnormal or the sequence is broken | `trace_id`+`span_id`, last chat's `finish_reasons`, `steps` timestamps | **Hang vs. still-running** can only be determined by window age; `enumeration_fallback="no-entry-span"` means the application did not instrument the entry layer (enumeration fell back to `kind=LLM`); this is not context loss |

**Discipline**:

- A single failure may match multiple category signatures -> **label all that apply**, do not force-choose one
- When the signature is insufficient, write "insufficient evidence" and state what is missing; **do not guess**
- Every label written into the report must anchor to a span in the trace: `spec.notes` keys are spanIds (`report_render` R2 enforced; keys not in the trace facts will be rejected)

## 2. Recommended Action Mapping

**Recommended actions are rewritten by the Agent and written into the report; they are not script output**. The table below provides candidates, not templates:

| Fact Pattern | Recommended Action Candidate |
|---|---|
| Parameter error + same-parameter unchanged retry | Check the tool's input parameter schema and the caller's assembly logic; consider whether parameters should change before retrying |
| External service timeout + `unpaired` requests | Verify whether the downstream service was available during the slice period; consider whether timeout and degradation strategies are needed |
| Model hallucination candidate (conclusions given despite data failure) | Have the model explicitly declare gaps when data is missing instead of filling in; verify against actual values |
| Insufficient permissions (401/403) | Verify the tool's required permissions and the calling identity; in cross-account scenarios, verify the assumed role's authorization |
| Context loss / hang | Verify whether the declared tool at the hang point actually executed; check whether the entry layer instrumentation is missing |
| Context bloat (`ballooning_candidate`) | Check whether context compression or segmentation is needed |
| Unregistered tool/model | Cross-reference with the customer registry; confirm whether it is a shadow deployment or experimental branch |

**Must distinguish** "Agent application-side improvements" from "observability capability improvements" — the latter are instrumentation/collection issues, not application problems.

## 3. Structural Redaction (Boundary Declaration)

Pattern list see the rendering contract section 6. This section only declares boundaries:

- Redaction is **structural regex**, not semantic PII detection. It can block private key blocks, AK patterns,
  `password=...` and similar things with **fixed shapes**
- **It cannot block**: person names in natural language, phone numbers, business-sensitive content. The responsibility for what content the Agent chooses to write into the spec's title and `notes` text, and what verbatim text is quoted in conversation, lies with the Agent
- The rendering summary reports `redaction.hits[]`; `applied: false` means no patterns matched; it does not mean the content is safe
- Credential values never enter the output (`preflight.py` always labels `credential_masked: true`); this is unrelated to this section but shares the same origin

## 4. Token Consumption Caliber (Proxy Cost)

Scenario 4 (PB-S4, Consumption Analysis) uses token caliber only. **Monetary amounts are permanently missing**; rationale and boundaries:

| Fact | Explanation |
|---|---|
| `gen_ai.usage.input_tokens` / `.output_tokens` / `.total_tokens` | Only populated on LoongSuit side's `chat` and `invoke_agent` spans |
| `gen_ai.usage.cache_read.input_tokens` | **Always 0 in practice**; does not mean there is no prefix cache reuse. To judge cache effectiveness, look at TTFT distribution, not this field (existing declaration see `trace_chain.py:290`) |
| Tool/retrieval step tokens | **Do not consume tokens**: tokens only land on `chat` and `invoke_agent` span types. Tool calls and retrieval steps have no tokens; this is zero, not a gap |
| eBPF side tokens | **"Unmeasurable" rather than "measured as zero"**: `gen_ai.usage.*` is declared in the ebpf-event index but has never been populated (see `genai_index_coverage`). `trace_overview.py` eBPF side's note always states "a zero token count on this side means UNMEASURABLE, not measured-zero"; token totals always read from the LoongSuit side |
| Unit price / monetary amount | **Neither source has price/cost/billing fields; this skill does not call billing APIs**. Report caliber always writes "missing"; no values given |

**You may state that monetary amounts are unavailable, but must not give monetary values**: `report_render.py` R4 mechanically rejects any monetary-semantic keys and text in the spec (`price` / `cost` / `fee` / `billing` / `currency` and their Chinese equivalents trigger rejection); writing "missing" for amounts is unaffected.

**No daily / weekly / monthly caliber**: this phase's time dimension is on-demand <=4h slices; no full-day or weekly/monthly aggregation. Any "comparison" can only be **adjacent slice** comparison; the wording is fixed as "compared to the previous slice" (`delta_pct: null` renders as "no baseline", never `0%`).
