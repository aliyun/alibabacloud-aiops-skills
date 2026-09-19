# Managed Agents Recipe: Prompt Versioning and Rollback

> This recipe covers the Agent versioning mechanism on Bailian Managed Agents, version canarying, and rollback practice. Examples uniformly use REST/curl. All key API shapes and evaluation numbers are field-tested (2026-09, Bailian cn-beijing region).

## Overview

This recipe demonstrates the full lifecycle of server-side prompt versioning: build v1, evaluate against a labeled test set, release v2, detect a regression, then pull production traffic back to the old behavior — a rollback. The core idea is stripping the "prompt" out of application code and turning it into a server-side versionable resource, so it goes through review and promotion independently of code.

Mechanisms involved: `POST /agents/{id}` (every update bumps the version), the Session-to-Agent-version binding (which **supports explicitly pinning a historical version**), and `GET /agents/{id}/versions` to list historical versions.

## Scenario

A product-support system uses an LLM to route tickets to the right team. The PM wants more API-related tickets to flow to the platform team.

In the past, changing one routing-prompt line required "PR + CI + deploy", and rollback went through the same pipeline. With Managed Agents, the prompt lives server-side: every `POST /agents/{id}` produces a new, immutable version; a Session locks a snapshot of some Agent version at creation (the latest by default, or an explicitly pinned one). If the new version performs worse, rollback is "publish a new version equivalent to the old one" — Sessions created afterwards pick it up immediately, no deployment needed.

After this recipe you will have:

- created an Agent that returns `version: 1`;
- scored a version against a labeled test set;
- released v2 and watched the version number auto-increment;
- **pinned a historical version for comparison without touching the Agent's current version**;
- pulled a regressed Agent back to v1 behavior, with zero deployment along the way.

## Environment-variable conventions

The curl examples in this recipe uniformly use:

```bash
BASE="https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
API_KEY="<your DashScope API Key>"
AGENT_ID="agent_xxx"     # fill in after creating the Agent
```

> Auth uses `Authorization: Bearer $API_KEY`; one key covers all resources in the workspace. The only region currently is `cn-beijing`. For the model ID use a field-tested one: `qwen3.8-max` / `qwen3.7-max` / `qwen3.7-plus` (this recipe uses `qwen3.7-plus`, sufficient for classification; generic IDs like `qwen3-max` are rejected).

> The Agent in this recipe is a pure-LLM classifier (no tool calls) and **needs no Environment** — a Session runs fine without `environment_id` (field-tested). Only Agents that run bash or read/write files need a sandbox; see 01 and 02.

## Step 1: Create the Agent (v1)

The system prompt has the Agent classify every ticket into "team + priority" and reply with a single line of JSON:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ticket-triage",
    "model": { "id": "qwen3.7-plus" },
    "system": "You are a support-ticket triage agent for a usage-billed API product.\nRead the ticket and respond with ONLY a single line of raw JSON (no code fences, no prose):\n{\"team\": \"<billing|auth|api-platform|dashboard>\", \"priority\": \"<P1|P2|P3>\"}\nRoute based on the customer'\''s actual problem, not surface keywords."
  }'
```

The response carries `version: 1`. Every subsequent `POST /agents/{id}` (note: **the update verb is POST, not PATCH — field-tested, PATCH returns 405**; the body requires both `name` and the current `version`) produces a new version under the same `id`, with the version number auto-incrementing; that version number is the handle for all later pinning and rollback. Fill the response's `id` into `AGENT_ID`.

## Step 2: Load the labeled test set

The evaluation fixture is the 4 tickets below (the field-tested set, one per team; T3 is deliberately written as "a billing problem that mentions API usage" to set up the later regression):

```json
[
  { "id": "T1", "expected": "api-platform",
    "subject": "Error 429 Too Many Requests on POST /v1/chat",
    "body": "Hi, since this morning every request to POST /v1/chat returns HTTP 429 Too Many Requests even though our traffic pattern is unchanged. Did something change on the server side? Our request volume is the same as last week." },
  { "id": "T2", "expected": "auth",
    "subject": "OAuth token expired, cannot refresh",
    "body": "Our integration suddenly stopped working. The access token expired and the refresh call returns invalid_grant. We did not change any credentials on our side. Please help." },
  { "id": "T3", "expected": "billing",
    "subject": "Invoice amount does not match dashboard usage",
    "body": "My latest invoice shows API usage charges of $412 for July, but the usage report on the dashboard only adds up to $380. I checked every day of the month and the numbers do not reconcile. I need a corrected invoice." },
  { "id": "T4", "expected": "dashboard",
    "subject": "Usage chart on the dashboard is blank",
    "body": "When I open the analytics dashboard, the usage chart section renders as an empty white area in both Chrome and Safari. The rest of the dashboard works fine. This started after your latest UI update." }
]
```

This test set is independent of the Agent — keep it in your own evaluation script or data file (each item: ticket text + expected team).

## Step 3: Score v1 (establish the baseline)

Run v1 once per ticket to get the baseline. The per-ticket evaluation flow (triage, from here on):

1. Create a Session (`agent` passes the Agent ID);
2. Send a `message` event carrying the ticket content;
3. Poll the event history until the Session returns to idle;
4. Collect the `assistant` output text, parse the JSON, compare against ground truth;
5. Delete the Session (delete right after evaluating, leave no trace).

### Session-to-Agent-version binding semantics (important, field-tested)

The `agent` field has **two accepted forms**, deciding which version the Session locks:

| Form of `agent` | Version locked |
|---|---|
| `"agent_xxx"` (string) | The **latest** version at the moment of creation |
| `{ "id": "agent_xxx", "version": N }` (object) | **The explicitly pinned version N**; if absent → `404 "Agent not found"` |
| `{ "id": "agent_xxx" }` (object without version) | Same as the string form — locks the latest |

- A Session uses this snapshot for its entire lifetime; later Agent version bumps do not affect an existing Session;
- Adding a top-level `version` field (a sibling of `agent`) **does nothing** — it is silently ignored, and the latest is still locked.

Two practical conventions follow:

- **To evaluate any historical version**, just pass the object form `{id, version: N}` — no need to first make it "the current latest" (this is the counter-intuitive part: many assume evaluating a historical version requires rolling back first; it does not);
- **Default production traffic** uses the string form and locks the latest version, so "which version production runs" = "whoever controls the Agent's latest-version state".

### The REST implementation of triage

First create the Session (`agent` passes the Agent ID string, locking a snapshot of the current latest version; a pure-LLM Agent needs no `environment_id`):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "'"$AGENT_ID"'",
    "title": "triage-eval"
  }'
```

> Note (current behavior): Session creation has **no initial-input field** (no `initial_events`); you must "create the Session first, then send a `message` event" in two steps.

With `SESSION_ID` from the response, send the ticket (concatenate `Subject: ...` and the body into text):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/sessions/$SESSION_ID/events" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": [
      { "type": "message", "role": "user",
        "content": [ { "type": "text", "text": "Subject: ...\n\n<ticket body>" } ] }
    ]
  }'
```

Poll the event history, take the last event, until the Session returns to idle:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "$BASE/sessions/$SESSION_ID/events?order=desc&limit=1" \
  -H "Authorization: Bearer $API_KEY"
```

> Parsing detail (field-tested): the `session_status` / `stop_reason` to check live in the **`content[0].data`** of `session_status`-type events (`{"stop_reason": {"type": "end_turn"}, "session_status": "idle"}`), not at the event's top level; a top-level `type` of `session_status` marks the end of the turn. A 60-second timeout is recommended. Each triage took about 8-11 seconds in field tests.

From the `assistant` message, concatenate the `content` text, `json.loads` the `{"team", "priority"}`, compare with the expected team; finally delete the Session:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X DELETE "$BASE/sessions/$SESSION_ID" \
  -H "Authorization: Bearer $API_KEY"
```

> The SSE live stream (`GET /sessions/{id}/events/stream`, request header `Accept: text/event-stream`) can replace polling — accumulate streamed text by `sequence_number`; polling is simply easier in an evaluation script. Archive (`POST /sessions/{id}/archive`) or delete, one of the two: DELETE is cleaner inside an evaluation loop.

The score logic: run triage once per ticket, tally "hits / total" per team.

**v1 field-tested result (4-item set, qwen3.7-plus):**

| Team | Hits/total |
|---|---|
| api-platform | 1/1 |
| auth | 1/1 |
| billing | 1/1 (T3 mentions API usage, still correctly routed to billing) |
| dashboard | 1/1 |

## Step 4: Release v2

The PM wants a new routing rule: any ticket mentioning API usage, rate limits, quotas, or request volume routes to the platform team. Update the system prompt with `POST /agents/{id}` (`name` + current `version` required), which produces v2.

The new system prompt = v1's content, plus:

```
ROUTING RULE: If the ticket text mentions API usage, rate limits, quotas, or request volume, route to api-platform. Apply this rule before any other consideration; do not second-guess it based on the rest of the ticket.
```

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ticket-triage",
    "version": 1,
    "system": "You are a support-ticket triage agent for a usage-billed API product.\nRead the ticket and respond with ONLY a single line of raw JSON (no code fences, no prose):\n{\"team\": \"<billing|auth|api-platform|dashboard>\", \"priority\": \"<P1|P2|P3>\"}\nRoute based on the customer'\''s actual problem, not surface keywords.\n\nROUTING RULE: If the ticket text mentions API usage, rate limits, quotas, or request volume, route to api-platform. Apply this rule before any other consideration; do not second-guess it based on the rest of the ticket."
  }'
```

The response's `version` becomes `2`.

## Interlude: where did code review go?

One API call changed the Agent, with no review in between — fine for a demo, not for production. `POST /agents/{id}` has no built-in approval flow; any key in the workspace can call it. And a Session created via the string form locks the then-latest version, **which means the first Session created after a version bump already uses the new prompt**. This is exactly the same situation as feature flags, or any "config managed via API rather than code".

**The recommended pattern for restoring review:**

- Make "which version production should run" a change-controlled artifact — for example, explicitly record the target version number in your own deployment config;
- Anyone can build v2 / v3 / v10; those versions just sit on the server, carrying no production traffic;
- "Promotion" = updating that "which version production uses" config, and that config update goes through normal code review. The advanced variant: on the production side, create Sessions with the `{id, version}` object to pin the controlled version number directly — not even depending on "the Agent's latest version".

> Ground rule: default traffic (string form) binds "the latest-version snapshot at creation time", so "which version production runs" should land in **your release control over the Agent's latest version** — who may update the Agent, and when a given config becomes the current latest. Building versions is cheap; the SDLC stays intact.

## Step 5: Score v2

Run v2 through the same evaluation. Two ways:

- **The default way**: v2 is now the latest version, so create Sessions with the string form (locks v2);
- **Comparison evaluation**: leave the Agent's versions completely untouched — pass the object form, pinning `{id, version: 1}` and `{id, version: 2}` respectively, and compare any two historical versions' behavior at any time.

Field-tested result (default form, v2 as latest): the new rule is too broad — T3 is a **billing** ticket for a usage-billed API product whose body mentions "API usage charges", and the ROUTING RULE grabbed it for the platform team:

**v2 field-tested result:**

| Team | Hits/total |
|---|---|
| api-platform | 1/1 |
| auth | 1/1 |
| billing | 0/1 (**regression!** T3 routed to api-platform) |
| dashboard | 1/1 |

## Step 6: Roll back

`billing` regressed. The good news: v1's config is still fully retained server-side; rollback needs no code redeployment.

**Rollback = publish a new version equivalent to v1.** Default traffic (string form) binds "the latest at creation time", so to bring production behavior back to v1, POST the v1 system prompt verbatim once more with `POST /agents/{id}`, producing v3 (the version number keeps incrementing; the config is equivalent to v1):

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ticket-triage",
    "version": 2,
    "system": "You are a support-ticket triage agent for a usage-billed API product.\nRead the ticket and respond with ONLY a single line of raw JSON (no code fences, no prose):\n{\"team\": \"<billing|auth|api-platform|dashboard>\", \"priority\": \"<P1|P2|P3>\"}\nRoute based on the customer'\''s actual problem, not surface keywords."
  }'
```

If you only want to inspect a historical version's config to decide what to roll back to, use `GET /agents/{id}/versions` (see the end).

Re-run the failed T3 on the v3 "back to the v1 prompt" (field-tested): `billing` routing is correct again.

Since all versions are retained server-side:

- v2 can still be iterated on and fixed (build v4 from v2 as the blueprint, or pin `{id, version: 2}` for evaluation);
- production can stay on v3 for now, or run a small canary — part of the requests pass `{id, version: N}` to trial a new version, the rest go through the default latest;
- once fixed, build a new version and walk the same evaluation → promotion flow.

## Cleanup

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -X POST "$BASE/agents/$AGENT_ID/archive" \
  -H "Authorization: Bearer $API_KEY"
```

> Use archive, not delete: **Agents do not support DELETE (field-tested, returns 405)**; archiving keeps the audit record, tears down the container, and stops billing; the version history is the point of its existence. The evaluation Sessions were already DELETEd in-loop.

## Summary

The mechanism itself is small — build a version, update to bump, pin production to a version, switch back when needed — but once the prompt becomes "a versioned server-side resource", it can be evaluated and promoted independently of application code. Key points:

- **Which version production should run must be a controlled artifact**: treat it as the gate for prompt changes, subject to normal review;
- **For high-risk Agents, canary the new version on small traffic first, then full rollout** (combined with explicit `{id, version}` pinning for traffic splitting);
- **Understand the version-binding semantics**: the string form locks the latest; the object form `{id, version}` locks the specified version (404 if absent); a top-level `version` field does nothing; established Sessions are unaffected by later bumps;
- **Evaluating a historical version requires no prior rollback** — the object form pins any version for direct comparison; rollback exists to restore old behavior for **default traffic**.

## Next: list all versions

View all historical versions of an Agent:

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 30 -s "$BASE/agents/$AGENT_ID/versions" \
  -H "Authorization: Bearer $API_KEY"
```

Field-tested response shape (versions ordered newest to oldest):

```json
{
  "data": [
    {
      "agent_id": "agent_xxx",
      "version": 3,
      "created_at": "2026-09-01T22:24:55+08:00",
      "config": {
        "name": "ticket-triage",
        "model": { "id": "qwen3.7-plus" },
        "system": "<full system prompt of that version>",
        "tools": [], "mcpServers": [], "skills": [],
        "metadata": {}, "status": "...",
        "workspaceId": "...", "userId": "...",
        "gmtCreate": "...", "gmtModified": "...", "id": "...", "version": 3
      }
    }
  ],
  "next_page": null,
  "request_id": "..."
}
```

Note that `config` is a **verbatim dump of the internal storage format**: fields are camelCase (`mcpServers`, `workspaceId`, `gmtCreate`), unlike the creation API's snake_case; every version carries the full `system` and `created_at`, usable for auditing, comparing historical prompts, and deciding which version to promote to production.
