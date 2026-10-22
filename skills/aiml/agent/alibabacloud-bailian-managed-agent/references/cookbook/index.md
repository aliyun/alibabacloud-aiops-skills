# Scenario Cookbook Index

> Source of these recipes: **REST / curl field tests** on the Bailian cn-beijing region (2026-09), with **05 / 09 / 10 / 11 retested online on 2026-10-09**, plus application integration guidance. **Recipes 01-11 are documented**. Built-in web checks live in 05, memory in 09, multimodal input in 10, and streaming/file interaction in 11. Each recipe distinguishes tested components from untested combinations; browser MCP and current Webhook delivery remain prerequisite-dependent.
> Division of labor with [../tutorials/index.md](../tutorials/index.md):
> **tutorials are organized by capability / action verb** (how to mount files, how to configure schedules, how to handle approvals) — one capability per tutorial, covered in depth;
> **the cookbook is organized by business scenario** (Yunling Tea's morning-brief bot, Shibei E-commerce's reconciliation notifier) — one recipe chains several capabilities into a complete pipeline.
> "How do I use this feature" → tutorials; "how does my business scenario land end to end / give me a complete example" → the cookbook.

## Scenario → recipe mapping

Match on the **business intent** in the user's description (not the action verb). When one intent hits multiple recipes, lead with the lower difficulty.

| Intent signal from the user | Recipe | Scenario protagonist | Capabilities chained | Difficulty |
| --- | --- | --- | --- | --- |
| "Give me a complete from-zero-to-running example" / "have the Agent analyze my data into a report" / "first time — show me the full picture" | [01-get-started-data-analysis-agent.md](01-get-started-data-analysis-agent.md) | An order ledger with dirty data mixed in | Agent / Environment / file upload & mounting / Session / SSE event stream / artifact retrieval / archiving | Beginner |
| "Going to production — what am I missing" / wanting "scheduled runs + web search + config injection + human confirmation on incidents" all at once | [02-production-four-building-blocks.md](02-production-four-building-blocks.md) | Yunling Tea · morning-brief bot | MCP marketplace toolsets / config injection (environment variables + Vault wiring) / Deployment (manual + cron + `initial_events`) / HITL / resource lifecycle / data residency | Advanced |
| "The prompt edit broke it — how do I roll back" / "don't want a release cycle just to change one prompt line" / "want canary rollouts and evaluation for prompts" | [03-prompt-versioning-and-rollback.md](03-prompt-versioning-and-rollback.md) | A ticket-routing system | Agent version auto-increment / Sessions pinning historical versions / golden-set evaluation / regression detection / rollback / `GET /agents/{id}/versions` | Advanced |
| "One Agent can't do it — I need multiple roles dividing the work" / "multi-step deliverables like custom proposals and complex reports" | [04-multi-agent-custom-proposals.md](04-multi-agent-custom-proposals.md) | Northstar · sales proposal | `multiagent` coordinator + roster / platform-injected orchestration tools / Session Threads API / a dashboard rendered by `thread_id` split | Expert |
| "Research online with built-in tools" / "multi-agent is too expensive" / "how to mix flagship and cheap models" | [05-coordinator-pattern-and-cost-tiering.md](05-coordinator-pattern-and-cost-tiering.md) | Web research, from one question to high-volume reading | built-in web_search / web_fetch / coordinator-worker model tiering / cost guardrails / controlled experiments | Advanced / Expert |
| "Notify me when the task finishes" / "tired of polling" / "alert me when runs fail" | [06-webhook-event-notifications.md](06-webhook-event-notifications.md) | Shibei E-commerce · reconciliation notifier | Webhook resources (`wep_`) / 32 named events / receiver-side implementation / HMAC signature verification / at-least-once and reordering / retry semantics | Advanced |
| "We already have an MCP Server / an internal SOP — can we hook it up" | [07-custom-mcp-and-skills.md](07-custom-mcp-and-skills.md) | Luming Publishing · manuscript-review assistant | custom MCP (`type: customer`) registration and mounting / custom Skill packaging, upload, and versioning / runtime event-stream verification | Advanced |
| "How do I hand secrets to the Agent / is it safe" / "keep API keys out of code and logs" / "the compliance review needs the secret chain explained" / "passing config into sessions" | [08-vault-secret-injection-and-egress-gateway.md](08-vault-secret-injection-and-egress-gateway.md) | A weather assistant · external API calls | Vault placeholder injection / `allowed_hosts` egress allowlist / egress gateway Authorization replacement / session environment variables vs. Vault selection / TLS pitfalls | Advanced |
| "Next session should pick up my project notes" | [09-working-memory-handoff.md](09-working-memory-handoff.md) | Project handoff | MA Memory Store / explicit write-back / cross-session readback | Advanced |
| "Have the Agent answer a question about an image" / "how to send multimodal input" | [10-multimodal-input.md](10-multimodal-input.md) | Image-question service | image upload and review / file_id image blocks / model-route verification | Advanced |
| "Build a conversation client" / "stream answers and show Thinking" / "let users add or remove attachments" | [11-client-integration-practice.md](11-client-integration-practice.md) | Web or mobile conversation client | backend event adapter / Delta assembly / Thinking and turn states / recovery / runtime file interactions | Advanced |

## Capability → which recipe has the end-to-end practice (reverse lookup)

tutorials explain "how to configure this feature"; here you see "what it looks like inside a complete pipeline".

| Capability | Feature tutorial | End-to-end practice |
| --- | --- | --- |
| Builtin toolsets and per-tool `configs[]` enablement | [../tutorials/01-ai-native-quickstart.md](../tutorials/01-ai-native-quickstart.md) | 01 Step 1, the two traps at the top of 04 |
| File upload & mounting, artifact retrieval | [../tutorials/03-mount-files.md](../tutorials/03-mount-files.md) | 01 Step 3 / Step 6, 04 §3.1-3.2 (9 files) |
| Deployment scheduling and triggering | [../tutorials/04-scheduled-deployment.md](../tutorials/04-scheduled-deployment.md) | 02 Step 5 (including the version-drift trap, pause / archive) |
| Sandbox environment and dependencies | [../tutorials/05-environment-packages.md](../tutorials/05-environment-packages.md) | 01 Step 2, 04 §3.3 |
| Human approval (HITL / `requires_action`) | [../tutorials/06-tool-approval.md](../tutorials/06-tool-approval.md) | 02 Step 6 (polling option A / post-hoc Deployment query option B) |
| Multi-agent fleets and thread observation | [../tutorials/07-multiagent-coordinator.md](../tutorials/07-multiagent-coordinator.md) | 04 §4 (including Session Threads API and dashboard rendering), 05 (cost tiering) |
| MCP integration (marketplace / custom) | _(no feature tutorial yet — the recipes are authoritative)_ | 02 Step 3 (marketplace `official`), 07 §1 (custom `customer`) |
| Session environment variables (`environment_variables` plaintext injection) | _(no feature tutorial yet — the recipes are authoritative)_ | 02 Step 4.1, 08 Step 6 |
| Vault secret store (placeholders + egress gateway) | _(no feature tutorial yet — the recipes are authoritative)_ | 02 Step 1-2 (wiring), all of 08 (security-model deep dive) |
| Agent versioning and rollback | _(no feature tutorial yet — the recipes are authoritative)_ | all of 03 |
| Webhook event notifications | _(no feature tutorial yet — the recipes are authoritative)_ | all of 06 |
| MA working memory / cross-session handoff | [Memory distinction](../product/status.md) | 09 |
| Built-in web search / page reading | [Current tool rules](../product/concepts.md#tool-and-mcp) | 05; browser interaction still uses MCP |
| Multimodal image input | [Event contracts](../integration/api-quickstart.md) | 10; use the tested file_id image path |
| Delta / Thinking / client recovery | [Event contracts](../integration/api-quickstart.md) | 11; backend-to-UI integration |
| Runtime file add/remove | [File tutorial](../tutorials/03-mount-files.md) | 11; attachment interactions in an existing conversation |
| Custom Skill packaging and upload | _(no feature tutorial yet — the recipes are authoritative)_ | 07 §2 |

## Suggested reading order

- **First contact**: run 01 through the full chain → then jump by intent. 01 is the common prerequisite for every other recipe (environment-variable conventions, resource concepts, and how to read the event stream all live there).
- **Going to production**: 01 → 02 (the four building blocks) → 06 (completion notifications) → 08 (secret safety, when external API credentials are involved). 02 solves "running on schedule", 04's SSE solves "a human watching", 06 solves "notify me when it's done", 08 solves "handing secrets out safely".
- **Multi-agent**: 04 first (the complete chain and observation surface) → then 05 (cost tiering; 05 does not repeat 04's configuration shape).
- **Hooking up your own assets**: 07 reads standalone, but its mounting semantics build on 01's `tools` / `configs[]` foundation.
- **Building a client**: 01 → 11 (streaming, recovery, and attachment interactions); add 10 for image input and 09 for cross-session working notes.

## Shared smoke-test setup

Recipes 05 and 09-11 use [cookbook_smoke.py](../../scripts/cookbook_smoke.py). Run from the repository root; no SDK is required:

```bash
python3 -m venv /tmp/ma-cookbook-env
/tmp/ma-cookbook-env/bin/pip install httpx
```

Each recipe supplies its own `--scenarios` selection. Without `--execute`, the script only previews scope and does not load credentials. With `--execute`, it creates temporary synthetic resources, calls models/tools, and cleans up only IDs recorded from its own creation responses. Its shared fixture includes an Agent, Environment, and Memory Store even when a selected scenario does not use memory.

The recipe commands use `DASHSCOPE_API_KEY` already injected into the local environment. Set its matching workspace endpoint before running:

```bash
export CMA_BASE="https://<workspace_id>.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
```

Alternatively, supply `BAILIAN_WORKSPACE_ID` for the cn-beijing default endpoint. To deliberately use a bl JSON profile instead, add `--bl-config "$HOME/.bailian/config.json"`; this selects **that file's `api_key` and `base_url` together**, overriding the environment key. Updating `DASHSCOPE_API_KEY` does not update a saved profile. Check the actual endpoint rather than assuming separately stored workspace fields agree. The script performs a read-only `/agents` authentication check before creating anything; do not mix credentials and endpoints from different environments. Keys are not passed as arguments, printed, or saved in output. Requests carry this skill's freshly generated per-invocation User-Agent; mutations are not automatically retried.

| Scenario | Recipe context |
| --- | --- |
| `web` | 05: built-in search and page reading |
| `web_team` | 05: built-in web worker, coordinator, and model/thread usage evidence |
| `memory` | 09: working-memory handoff |
| `image` | 10: image input |
| `delta`, `recovery`, `files` | 11: Delta assembly, intentional disconnect/recovery, and runtime file interactions, tested separately |
| `approval`, `deployment` | 02 and tutorials 06 / 04: approval and manual Deployment |
| `multiagent` | 04: delegation and thread evidence |
| `vault` | 08: placeholder injection |

Results go to `live-results.jsonl` and resource IDs to `ledger.json` in the output directory. Use a fresh directory per run. To retry cleanup, use the same authentication options with `--execute --cleanup-only --output` pointing to that run's existing directory. Agent, Deployment, and Memory Store are archived with history retained; Session, Environment, uploaded File, Vault credentials, and Vault are deleted. Do not claim all historical records are physically removed.

The script creates no recurring schedule or Webhook. Its Deployment check triggers one manual run; its Vault check uses dummy values and does not establish real external-service authentication. Browser interaction needs an activated MCP service; current Webhook delivery/signature verification needs a controlled public receiver. Neither was verified in these smoke checks; 06 retains its separate historical Webhook evidence.

## Rules when presenting these recipes

1. **The companies in these recipes are fictional** (Yunling Tea / Northstar / Shibei E-commerce / Luming Publishing). Replace them with the customer's own business nouns when presenting; never cite them as customer cases.
2. **Precedence of sources**: field-test conclusions here (tagged with test date and region) **outrank** the whitepaper snapshot in `product/whitepaper-source.md`. On conflict, the field test wins, and the finding flows back into `product/` and `integration/` (rules in the "Directory map" of [../../SKILL.md](../../SKILL.md): fact dictionary and usage layers, one-way backflow of field-test conclusions).
3. **These are scenario recipes, not the fact dictionary.** Look up field names, endpoints, quotas, and error codes in [../integration/api-endpoints.md](../integration/api-endpoints.md) and [../product/concepts.md](../product/concepts.md); numbers in the recipes (token counts, durations, evaluation scores) are single-run field samples, not SLA promises.
4. **Advance one step at a time**, each step with a directly runnable curl and the response you should see; when the user's environment differs from the recipe (another region, pre-existing resources), state the differences first, then adapt.
5. Recipe examples uniformly use REST / curl. When the user wants the same thing via CLI → use skill `bailian-managed-agent`'s agents.yaml pipeline; both paths drive the same resources.

## Related files

- Find tutorials by capability → [../tutorials/index.md](../tutorials/index.md)
- Concepts and object relationships → [../product/concepts.md](../product/concepts.md)
- Full endpoint table and request bodies → [../integration/api-endpoints.md](../integration/api-endpoints.md)
- Requirements → solution methodology → [../workflows/solution-design.md](../workflows/solution-design.md)
