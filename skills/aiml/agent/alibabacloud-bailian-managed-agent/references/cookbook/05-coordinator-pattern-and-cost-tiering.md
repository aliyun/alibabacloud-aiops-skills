# The Coordinator Pattern — Big Models Plan, Small Models Execute

> This recipe covers the **cost tiering** of the multiagent coordinator pattern: have the flagship model do only planning and synthesis, hand the token-heavy execution to cheap models, and measure the split honestly. The full multi-agent chain — configuration shape, orchestration tools, thread observation, client-side rendering — was field-tested and expanded in 04; this recipe does not repeat it. The curl and API behaviors below follow the shapes 04 verified, focusing on "why this architecture makes sense on the bill, how to compute it, and when it does not pay off".

```bash
export BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
export API_KEY="<your DashScope API Key>"
```

## Scenario: reading is the bulk of the bill

Most agent workloads contain two very different kinds of work: **a little planning and judgment, and a lot of mechanical reading and execution**. Web research is the extreme case: verifying twenty facts means pulling hundreds of thousands of tokens of web pages past the model. At flagship rates, that reading bill dominates — but reading itself does not need flagship judgment.

The coordinator pattern splits the two loads: the flagship coordinator plans the research, decomposes sub-questions, and synthesizes the answer, **never touching a raw web page**; cheap workers do all the reading in their own parallel threads, returning only distilled findings. The same reading tokens, billed at cheap instead of flagship rates — that is the whole point of cost tiering.

The same economics apply to any workload where "a cheap model can do the token-heavy leg": document review, log analysis, codebase scanning.

## Architecture: reading stays in worker threads, billed at cheap rates

```
User question
   |
   v
Flagship coordinator (qwen3.8-max, no tools of its own)
   |  create_agent / list_agents / wait_for_agents (platform auto-injected, see 04)
   |--------------|--------------|--------->  parallel sub-questions
   v              v              v
worker A       worker B       worker C ... (qwen3.7-plus, each in its own Session thread)
bailian_web_search xN (MCP marketplace WebSearch service)
   |              |              |
   +-- distilled findings returned (final assistant text auto-returned / submit_result) --+
   v
Coordinator synthesizes -> final answer
```

The cost story rests entirely on two structural properties:

1. **Reading does not cross over.** The megabytes of search results and web pages a worker reads exist only in its own thread context; the coordinator receives small messages (the sub-question delegated out) and distilled summaries (the findings coming back). This is directly verifiable in the event stream (seen in 04's field tests): dense `mcp_call` / `mcp_call_output` on worker threads, and only orchestration tool calls plus final synthesis on the coordinator's primary thread — **the bulky raw content never appears in any event on the primary thread**.
2. **Rates are decided by the model ID.** A Bailian agent's `model` field takes just `{ id }`; capability and price tier are decided by the ID itself. Coordinator and workers with different IDs split the bill into two columns naturally — the model ID is also the easiest dimension for cost attribution.

Parallelism is an incidental gain: workers run in independent threads, so wall-clock time is also shorter (in 04's field test the case picker and the pricing modeler were spawned simultaneously).

## Configure a two-model team

Use field-tested tiers for model IDs: flagship coordinator `qwen3.8-max`, cheap worker `qwen3.7-plus` (there is an even cheaper `qwen3.6-flash` tier). Generic legacy IDs like `qwen3-max` are rejected with `400`; defer to the official list for specifics.

### The worker: cheap model + search MCP

Web search is not a builtin tool (`builtin_toolkit` has 7 tools total, no `web_search` / `web_fetch`); the only sanctioned route is mounting the MCP marketplace `WebSearch` service, tool name `bailian_web_search`:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_worker",
    "model": { "id": "qwen3.7-plus" },
    "mcp_servers": [ { "type": "official", "name": "WebSearch" } ],
    "tools": [
      { "type": "mcp_toolkit", "mcp_server_name": "WebSearch",
        "default_config": { "enabled": true },
        "configs": [ { "name": "bailian_web_search", "enabled": true } ] }
    ],
    "system": "You are a search worker researching one focused sub-question for a coordinator. Use the search tools to find the answer, and be thorough: try multiple query phrasings, follow promising links, cross-check across sources. Report the specific answers you found with supporting evidence (URLs, quotations); if no definite answer emerges, say clearly what you did find and what remains uncertain."
  }'
```

Every worker instance researches one focused sub-question in its own Session thread — the giant web pages it reads enter nobody else's context.

### The coordinator: flagship model, no tools of its own, just a roster

The coordinator gets no `tools` — it has no direct channel to the world beyond its roster. What makes it a coordinator is the `multiagent` field: the server auto-injects `create_agent` / `list_agents` / `wait_for_agents` (the worker side gets `submit_result`); you define none of these tools:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_coordinator",
    "model": { "id": "qwen3.8-max" },
    "multiagent": {
      "type": "coordinator",
      "agents": [
        { "type": "agent", "id": "<the search_worker agent id>" }
      ]
    },
    "system": "You are coordinating a team of search workers to answer a hard web-research question. Your workers have web search; you do not. Break the question into focused sub-questions, delegate them to workers via create_agent, and run several in parallel on independent sub-questions. After spawning, always call wait_for_agents before drawing any conclusion. When a worker reports, judge whether it answered the sub-question; if evidence is thin, delegate once more with different phrasing. Once evidence suffices, synthesize the workers'\'' findings into a single final answer to the original question."
  }'
```

From here it is 04's standard chain: create the Environment (§3.3), create a Session mounting the coordinator, POST one `message` event. A coverage-style question looks typically like: "For the ten largest national parks in the contiguous US, find the current standard private-vehicle entrance fee and whether a peak-season reservation is required, verifying every fact against that park's official nps.gov page — no third-party summaries". Coverage tasks are exactly where this pattern shines: the reading is mandatory (nobody can answer from memory); the only questions are at what rate the reading is billed and whether it runs in parallel. The fan-out scale is the coordinator's own call — **whether you write a cap into its prompt is the steering wheel of your cost**.

> **Roster version semantics** (04 §3.4, three controlled experiments): a member without `version` takes the worker's latest version at every delegation — editing a worker needs no coordinator change; for a frozen, reproducible team configuration, pin the `version` explicitly.

> **The coordinator knows only what you tell it.** The server does not leak workers' system prompts or tool details to the coordinator; everything it knows about worker behavior comes from the description you write in its own prompt. If the two descriptions diverge, delegation quality drifts — that alignment responsibility is yours; the server does not enforce it for you.

### Cost guardrails

Sessions have no budget / spend-cap field (none observed in field tests; the reference map marks this as a capability gap); guardrails land on three layers:

- **Deployment-layer throttling**: constrain trigger frequency (a cron schedule is itself a throttle), preventing the same task from being pulled up repeatedly. Note that field tests show **concurrent triggers do not error** (two consecutive `/run` calls each create a run and complete in parallel) — the concurrency cap is yours to control on the triggering side (field-tested in 02);
- **Prompt-constrained fan-out**: write the worker-count cap, the task granularity per brief, and the no-more-spawns conditions into the coordinator's system prompt — how many workers the coordinator spawns is entirely its own judgment; the prompt is your only steering wheel;
- **Post-hoc reconciliation**: after each run, tally usage by model dimension and compare against the expected band; when anomalies amplify, go back and tighten the granularity constraints in the prompt (method in the next section).

## Measure the bill

To audit whether this architecture really saves money, two data paths exist:

**Path one: per-call grouping over the event stream (post-hoc, no extra infrastructure).** Every model call produces one `model_request_end` event whose payload carries `model`, `input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`, and whose top level carries `thread_id` (seen in 04's field tests). Bucketing by `thread_id` gives "coordinator-thread spend vs each worker-thread spend"; bucketing by `data.model` gives "the flagship column vs the cheap column" — two bills read straight out of the event stream.

**Path two: time window x model ID.** In workspace-level usage data, slice by run time window and model ID: the team run yields two rows (flagship + cheap), the single-flagship control run only the flagship row. Operating order: run the team, note the window; run the control, note the window; pull each. Usage and pricing calibers defer to Bailian's official billing documentation.

### Designing a fair controlled experiment

To answer "what would it cost without this pattern", the realistic alternative is **a single flagship agent mounting the same search MCP** (tool config identical to the worker's; only the model ID changes to flagship). One subtlety decides whether this comparison is fair or useless: **strictness must match**. Left to judge for itself, the flagship will be frugal — reading a single source per fact and calling it done is cheap, but that is a lower-strictness product, not the same job at a different price. The control's prompt must explicitly demand what the team already does: every fact independently verified at least twice, re-fetch and flag when two sources disagree, and two source URLs per fact in the answer.

### Counterfactual estimation

To see "what if all reading were billed at flagship rates", take the team run's token counts, uniformly apply the flagship rate, and compare with the real split (reading billed at cheap rates). Cache-related rate multipliers (write / read) defer to the official billing documentation — `cache_read_input_tokens` / `cache_creation_input_tokens` in `model_request_end` are exactly the raw fields for this kind of accounting.

The structurally stable conclusion: **the two runs read almost the same amount (that is the point of matched strictness); the difference is at what rate the reading is billed** — the team's overwhelming majority of input tokens land in the worker (cheap) rate column. Token volumes differ run to run; treat single-run ratios as samples. What is stable is the structure, not the specific number.

## Four honest warnings

1. **Hold the comparison at matched strictness.** An unconstrained single flagship reads less and is indeed cheaper, but it is a different product. Compare the two sides only with the verification standard fixed.
2. **Delegation has a floor price.** Every worker thread carries a fixed setup overhead. Splitting the same job into more, narrower briefs raises the bill instead — brief granularity has an optimum.
3. **The verification standard covers only what you put into it.** Both sides verified 20 facts, but the park list itself may come from the model's memory — putting Kings Canyon, 12th by area, into the top ten, say. The facts were audited; **the problem decomposition was not**. When the premise matters, spend one extra delegation and have a worker verify it first.
4. **The coordinator knows only what you tell it.** See above — the accuracy of your description of worker behavior directly decides delegation quality, and with it whether this economics cashes out.

## When the split does not pay off

- **Narrow questions**: too little reading, no arbitrage room;
- **The coordinator answered from its own knowledge** (no delegation happened): you paid a flagship round trip for nothing. The event stream gives a clear signal: a run with **no `thread_created` at all** — instantly recognizable in 04 §4.4's bucketed rendering;
- **The raw material itself needs flagship-grade judgment** (subtle document analysis rather than fact-finding): a cheap reader may distill away exactly what mattered.

## Summary

- **Cost tiering lands as model-ID tiering**: the flagship coordinator only plans and synthesizes, never touching raw pages; cheap workers do all the reading in parallel threads;
- **Reading does not cross over** is an architectural property, directly verifiable in the event stream (dense `mcp_call` on worker threads; only orchestration and synthesis on the primary thread);
- **Two measurement paths**: group `model_request_end` by `thread_id` / model (event layer); time window x model ID (usage layer). Controlled experiments must match strictness, or you are comparing two different products;
- **Three guardrail layers**: Deployment throttling, prompt-constrained fan-out, post-hoc reconciliation.

Cleanup after the run is the same as 04 §7: archive the Session / Environment / Agents one by one (archiving keeps the audit record and stops billing).
