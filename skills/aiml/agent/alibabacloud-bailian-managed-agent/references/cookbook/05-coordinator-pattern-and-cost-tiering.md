# 05 · Web Research with Built-in Tools and Model Cost Tiering

> **Evidence scope:** on 2026-10-09, live cn-beijing tests using the local environment-variable API key passed both standalone built-in `web_search` / `web_fetch` and a `qwen3.8-max` coordinator delegating to a `qwen3.7-plus` worker using those tools. The [official tool configuration](https://help.aliyun.com/zh/model-studio/managed-agents-builtin-tools) was also checked. This verifies the execution path and model/thread attribution; no matched single-model control or monetary cost benchmark was run. Earlier large-task comparisons inherited from 04 used its historical MCP setup.

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
web_search → web_fetch xN (built-in tools)
   |              |              |
   +-- distilled findings and source URLs returned in the worker's final message ------+
   v
Coordinator synthesizes -> final answer
```

The cost story rests entirely on two structural properties:

1. **Reading stays with the worker.** Search results and fetched pages enter the worker's context; the coordinator should receive only distilled findings and source URLs. Verify this by grouping events by thread: the built-in variant should show `tool_call` / `tool_call_output` for `web_search` and `web_fetch` on worker threads, with orchestration and synthesis on the primary thread. The same separation was observed in 04's historical MCP run, where the search events were `mcp_call` / `mcp_call_output`. A worker that copies entire pages into its result defeats this design.
2. **Attribute model usage by model ID.** Select each Agent's model with `model.id` and use that model's applicable rates. Coordinator and workers with different IDs give two model groups for cost attribution. The model configuration may also carry options such as `enable_thinking`; `{ "id": "..." }` is the minimal selection shape, not the complete schema.

Independent workers can run concurrently (in 04's field test the case picker and pricing modeler were spawned simultaneously). This can shorten wall-clock time, but delegation, follow-up, and synthesis add overhead; measure latency instead of assuming an improvement.

## Configure a two-model team

Use field-tested tiers for model IDs: flagship coordinator `qwen3.8-max`, cheap worker `qwen3.7-plus` (there is an even cheaper `qwen3.6-flash` tier). Generic legacy IDs like `qwen3-max` are rejected with `400`; defer to the official list for specifics.

### The worker: cheap model + built-in search and page reading

Enable both tools explicitly in one `builtin_toolkit`. No search MCP activation or `mcp_servers` entry is needed for this flow:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_worker",
    "model": { "id": "qwen3.7-plus" },
    "tools": [
      { "type": "builtin_toolkit",
        "default_config": { "enabled": false },
        "configs": [
          { "name": "web_search", "enabled": true },
          { "name": "web_fetch", "enabled": true }
        ] }
    ],
    "system": "You are a search worker researching one focused sub-question for a coordinator. Use web_search to locate sources and web_fetch to read promising pages. Prefer primary sources, try alternative queries when evidence is weak, and cross-check important claims. Include concise findings, source URLs, and supporting facts in your final assistant message; a submission receipt alone is insufficient. Do not return full page text. If no definite answer emerges, state what remains uncertain."
  }'
```

Every worker instance researches one focused sub-question in its own Session thread — the giant web pages it reads enter nobody else's context.

### Search, read, and verify before adding a coordinator

For a single research question, use the worker directly. A useful sequence is: `web_search` locates candidate sources → `web_fetch` reads the relevant pages → the Agent checks the claim against the source and answers with URLs. A search snippet alone is not a substitute for reading the page when the claim depends on its details.

Use the [shared smoke-test setup](index.md#shared-smoke-test-setup), then run from the repository root:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py --scenarios web
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute \
  --scenarios web --output /tmp/ma-web-check
```

`web_test` in [cookbook_smoke.py](../../scripts/cookbook_smoke.py) requests a search for Memory Store documentation and retrieval of a specified official page. The recorded run contained successful calls to both tools and an answer citing the creation-time mounting constraint. The test uses the script's `qwen3.8-max` Agent; it verifies the web-tool path, not the worker/coordinator cost split shown here. Memory Store is only the research topic in this check; no memory mount is needed to search or read the page.

Configuration names require underscores: `web_search` / `web_fetch`, not `websearch` / `webfetch`. Browser clicks and forms require `browser_use` through an activated MCP service; obtain its service and tool names from the account catalog. Browser execution was not verified in this test workspace.

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

### Verify the built-in worker/coordinator path

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --scenarios web_team --output /tmp/ma-web-team-check
```

`web_team_test` creates the two-model team above with only the worker in the coordinator's roster. The 2026-10-09 run created one worker thread; both `web_search` and `web_fetch` completed on that thread, and the coordinator synthesized the findings. No `mcp_call` was used. Inspect `builtin-web-team-events.json` and `web_team_evidence` for the thread split and usage grouped by model.

The run also exposed handoff overhead: the worker issued four `submit_result` calls, but its first final message contained only a submission receipt. The coordinator used `send_to_agent` to request the full report. A successful tool receipt alone therefore does not prove the coordinator has usable findings; require the worker's final message to include concise facts and source URLs, and check the actual result.

This small sample recorded five model requests for `qwen3.8-max` and eight for `qwen3.7-plus`, with respective raw `input_tokens` totals of 15,698 and 52,715 and `output_tokens` totals of 1,329 and 4,484. These are observations of one run, not a spending limit or proof of savings. Account for cache fields and tool charges when converting usage to cost.

> **Roster version semantics** (04 §3.4, three controlled experiments): a member without `version` takes the worker's latest version at every delegation — editing a worker needs no coordinator change; for a frozen, reproducible team configuration, pin the `version` explicitly.

> **The coordinator knows only what you tell it.** The server does not leak workers' system prompts or tool details to the coordinator; everything it knows about worker behavior comes from the description you write in its own prompt. If the two descriptions diverge, delegation quality drifts — that alignment responsibility is yours; the server does not enforce it for you.

### Cost guardrails

Sessions have no budget / spend-cap field (none observed in field tests; the reference map marks this as a capability gap); guardrails land on three layers:

- **Deployment-layer throttling**: constrain trigger frequency (a cron schedule is itself a throttle), preventing the same task from being pulled up repeatedly. Note that field tests show **concurrent triggers do not error** (two consecutive `/run` calls each create a run and complete in parallel) — the concurrency cap is yours to control on the triggering side (field-tested in 02);
- **Prompt-constrained fan-out**: write the worker-count cap, the task granularity per brief, and the no-more-spawns conditions into the coordinator's system prompt. These are soft instructions, not an enforced spend cap; retries and follow-up delegations still add usage;
- **Post-hoc reconciliation**: after each run, tally usage by model dimension and compare against the expected band; when anomalies amplify, go back and tighten the granularity constraints in the prompt (method in the next section).

## Measure the bill

To audit whether this architecture really saves money, two data paths exist:

**Path one: per-call grouping over the event stream (post-hoc, no extra infrastructure).** Every model call produces one `model_request_end` event whose payload carries `model`, `input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`, and whose top level carries `thread_id` (seen in 04's field tests). Bucketing by `thread_id` gives "coordinator-thread spend vs each worker-thread spend"; bucketing by `data.model` gives "the flagship column vs the cheap column" — two bills read straight out of the event stream.

**Path two: time window x model ID.** In workspace-level usage data, slice by run time window and model ID: the team run yields two rows (flagship + cheap), the single-flagship control run only the flagship row. Operating order: run the team, note the window; run the control, note the window; pull each. Usage and pricing calibers defer to Bailian's official billing documentation.

### Designing a fair controlled experiment

To answer "what would it cost without this pattern", the realistic alternative is **a single flagship agent with the same built-in `web_search` / `web_fetch` configuration** (only the model ID changes). One subtlety decides whether this comparison is fair or useless: **strictness must match**. Left to judge for itself, the flagship will be frugal — reading a single source per fact and calling it done is cheap, but that is a lower-strictness product, not the same job at a different price. The control's prompt must explicitly demand what the team already does: every fact independently verified at least twice, re-fetch and flag when two sources disagree, and two source URLs per fact in the answer.

Count web-tool calls as well as model tokens. Tool charges are separate from model inference; use the applicable [billing rules linked from the tool guide](https://help.aliyun.com/zh/model-studio/managed-agents-builtin-tools). Switching the old MCP setup to built-ins changes the tool-cost component, so remeasure both arms rather than carrying over an old total-cost ratio.

### Counterfactual estimation

To see "what if all reading were billed at flagship rates", take the team run's token counts, uniformly apply the flagship rate, and compare with the real split (reading billed at cheap rates). Cache-related rate multipliers (write / read) defer to the official billing documentation — `cache_read_input_tokens` / `cache_creation_input_tokens` in `model_request_end` are exactly the raw fields for this kind of accounting.

The hypothesis to test is that most reading tokens move to the cheaper worker rate while answer quality is preserved. Matched strictness makes the comparison meaningful; it does not guarantee equal token counts or a cheaper total. Measure actual token volume, delegation overhead, and tool charges in each arm. The historical MCP observations are motivation for this experiment, not measurements of the revised built-in configuration.

## Four honest warnings

1. **Hold the comparison at matched strictness.** An unconstrained single flagship reads less and is indeed cheaper, but it is a different product. Compare the two sides only with the verification standard fixed.
2. **Delegation has a floor price.** Every worker thread carries a fixed setup overhead. Splitting the same job into more, narrower briefs raises the bill instead — brief granularity has an optimum.
3. **The verification standard covers only what you put into it.** In the historical comparison, both sides verified 20 facts, but the park list itself could come from the model's memory — so the selected parks might not even satisfy the requested top-ten criterion. The facts were audited; **the problem decomposition was not**. When the premise matters, spend one extra delegation and have a worker verify it first.
4. **The coordinator knows only what you tell it.** See above — the accuracy of your description of worker behavior directly decides delegation quality, and with it whether this economics cashes out.

## When the split does not pay off

- **Narrow questions**: too little reading, no arbitrage room;
- **The coordinator answered from its own knowledge** (no delegation happened): you paid a flagship round trip for nothing. The event stream gives a clear signal: a run with **no `thread_created` at all** — instantly recognizable in 04 §4.4's bucketed rendering;
- **The raw material itself needs flagship-grade judgment** (subtle document analysis rather than fact-finding): a cheap reader may distill away exactly what mattered.

## Summary

- **Cost tiering lands as model-ID tiering**: the flagship coordinator only plans and synthesizes, never touching raw pages; cheap workers do all the reading in parallel threads;
- **Keep raw reading in worker contexts**: verify built-in web `tool_call` events by thread and require concise worker results;
- **Two measurement paths**: group `model_request_end` by `thread_id` / model (event layer); time window x model ID (usage layer). Controlled experiments must match strictness, or you are comparing two different products;
- **Three guardrail layers**: Deployment throttling, prompt-constrained fan-out, post-hoc reconciliation.

For resources created manually, follow 04 §7. The smoke script cleans up its own recorded resources as described in the [shared test lifecycle](index.md#shared-smoke-test-setup).
