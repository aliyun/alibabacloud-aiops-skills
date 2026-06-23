---
name: alibabacloud-pts-pilot
description: Router skill for Alibaba Cloud PTS (Performance Testing Service) operations. Resolves the user's PTS intent and delegates execution to the appropriate sub-skill. Itself does NOT execute any CLI / API / business logic. Triggers "PTS", "压测", "性能测试", "stress testing", "performance testing", "JMeter", "load testing", "压测调优".
---

# alibabacloud-pts-pilot — PTS Operations Router

> **[MUST] Role Declaration — What I Do**
> I am a **router-only** skill. My ONLY job:
> 1. **Parse** user intent → **Match** to a sub-skill → **Call the Skill tool** to delegate.
> 2. That's it. I never execute CLI, shell, or API commands myself.
>
> **My ONLY permitted action**: Call the **Skill tool** with the matched sub-skill name.
> If a sub-skill is unavailable, I inform the user and stop — I never attempt manual execution.

---

## Family Layout & Installation

This skill ships as a **parent-child bundle** in a single ZIP named after the parent (`alibabacloud-pts-pilot.zip`). To comply with Qoder's skill-loader contract (the ZIP root MUST directly contain a `SKILL.md`), the parent's `SKILL.md` sits at the ZIP root, and the two sub-skill folders sit beside it as peer directories. Qoder's recursive scan then registers all three `SKILL.md` files under a flat namespace.

```
alibabacloud-pts-pilot.zip
├── SKILL.md                    ← parent router (this file) — at ZIP root, required by Qoder
├── references/
│   └── routing-rules.md
├── alibabacloud-pts-task/               ← sub-skill (CRUD worker), peer of parent SKILL.md
│   ├── SKILL.md
│   └── references/             (acceptance-criteria, cli-installation-guide,
│                                 pts-scene-json-reference, ram-policies,
│                                 related-apis, verification-method)
└── alibabacloud-pts-reporter/           ← sub-skill (read-only PTS report analyzer), peer of parent SKILL.md
    ├── SKILL.md
    └── references/             (cli-installation-guide, ram-policies,
                                  report-analysis-knowledge-base)
```

**Installation (manual import):**
1. In Qoder, use "Import Skill ZIP" and point it at `alibabacloud-pts-pilot.zip`. Qoder will load the parent `SKILL.md` (this file) as the `alibabacloud-pts-pilot` skill.
2. After import, Qoder's recursive scan will also discover `alibabacloud-pts-task/SKILL.md` and `alibabacloud-pts-reporter/SKILL.md` as independent skills registered by their own `name:` field.
3. Trigger the parent by any PTS-related phrase (see frontmatter `Triggers`); the router will pick the correct sub-skill and hand off via the `Skill` tool.

> **Why this layout?** Qoder's loader requires `SKILL.md` at the ZIP root; it will reject ZIPs whose root contains only folders. Nesting sub-skills under an extra wrapper folder (e.g. `alibabacloud-pts-pilot/alibabacloud-pts-pilot/SKILL.md`) breaks this contract. Keeping the parent `SKILL.md` at the root while placing sub-skill folders as peers is the only layout that satisfies both the Qoder loader and the "one bundle, named after the parent" distribution requirement.

> **Integrity check after unzip**: the ZIP root must contain `SKILL.md` (parent) plus two sibling folders (`alibabacloud-pts-task/`, `alibabacloud-pts-reporter/`) each holding their own `SKILL.md`. Do not rename the folders — sub-skill `name:` fields must stay aligned with the delegation strings used in the Sub-Skill Registry below.

---

## Sub-Skill Registry

| Sub-Skill | Status | Intent Signature | Positive Triggers (examples) | Negative Triggers (DO NOT route here) | Handoff |
|-----------|--------|------------------|------------------------------|---------------------------------------|---------|
| **alibabacloud-pts-task** | ✅ Active | CRUD actions on PTS scenarios: create / query / start / stop / report / delete, JMeter upload & run | "create scenario", "start stress-test", "stop stress-test", "view report", "delete scenario", "upload JMeter script", "list PTS scenes", "start scene" | Pure knowledge Q&A ("what is PTS"), tuning advice ("how to tune parameters") | Invoke Skill tool with `alibabacloud-pts-task`, pass resolved `{intent, RegionId, SceneId?, sceneConfig?}` |
| **alibabacloud-pts-reporter** | ✅ Active | Read-only report analysis — interpret PTS report metrics, identify report-observable bottleneck patterns | "analyze stress-test report", "interpret report", "stress-test result analysis", "explain metrics", "PTS report analysis" | CRUD operations (create/start/stop), instance-level cloud product diagnosis | Invoke Skill tool with `alibabacloud-pts-reporter`, pass resolved `{RegionId, HistoryReportId, SceneId?, TopN?}` (HistoryReportId required) |
| **alibabacloud-find-skills** | ✅ Active | Search / discover / install Alibaba Cloud agent skills; also triggered when user wants product-level diagnosis tools that this router cannot provide | "search alicloud skill", "any skill for PTS management", "find alicloud skills", "browse skill marketplace", "help me find a skill", "any skill for RDS/ECS/Redis diagnosis", "after bottleneck found, find product skill", "any tool for diagnosing RDS", "find database diagnostic tool", "deep-diagnose product after bottleneck" | PTS CRUD / report analysis / any concrete execution | Invoke Skill tool with `alibabacloud-find-skills`, pass user's search intent as-is |

> **Registry column semantics**
> - **Status**: ✅ Active = ready to delegate · 🚧 Planned = reserved slot, not yet implemented
> - **Intent Signature**: one-line semantic fingerprint used for matching
> - **Positive / Negative Triggers**: concrete phrases that MUST / MUST NOT route here
> - **Handoff**: exact delegation mechanism + minimum required context to pass in

---

## Sub-Skill Contracts

Every active sub-skill declares an explicit **Input / Output Contract**. The router passes whatever the user explicitly provided — it does NOT need to gather every field or construct complex objects (like `sceneConfig`). Let the sub-skill handle missing details. MUST surface Output fields to the user.

### `alibabacloud-pts-task` (✅ Active)

| Direction | Field | Required | Notes |
|-----------|-------|----------|-------|
| **Input** | `intent` | ✅ | One of: `create` / `query` / `start` / `stop` / `report` / `delete` / `jmeter_upload` / `jmeter_run` |
| **Input** | `RegionId` | ✅ (default: `cn-shanghai`) | Defaults to `cn-shanghai` when unspecified; never ask the user |
| **Input** | `SceneId` | conditional | Required for `query`/`start`/`stop`/`report`/`delete` |
| **Input** | `sceneConfig` | optional | Sub-skill will construct this from user's natural-language params (URL, concurrency, duration, etc.). Router NEVER needs to build or ask for JSON config. |
| **Output** | `SceneId` | — | Echoed for all CRUD actions |
| **Output** | `ReportId` / `JobId` | — | Echoed for `start` / `jmeter_run` |
| **Output** | `status` | — | One of: `success` / `failed` / `user_cancelled` |

### `alibabacloud-pts-reporter` (✅ Active)

| Direction | Field | Required | Notes |
|-----------|-------|----------|-------|
| **Input** | `RegionId` | ✅ (default: `cn-shanghai`) | Defaults to `cn-shanghai` when unspecified |
| **Input** | `HistoryReportId` | optional | When not provided, delegate to reporter directly; it will query the latest report on its own |
| **Input** | `SceneId` | optional | Enables baseline data pull |
| **Input** | `TopN` | optional | Max recommendations; default `5` |
| **Output** | `recommendations[]` | — | Each item: `{area, severity, evidence, suggestion}`, ranked by severity; bottleneck analysis and tuning suggestions based on PTS report data |

### `alibabacloud-find-skills` (✅ Active)

| Direction | Field | Required | Notes |
|-----------|-------|----------|-------|
| **Input** | `searchIntent` | ✅ | User's search phrase or intent (e.g., "any PTS-related skill") |
| **Input** | `categoryCode` | optional | Filter by category if user specifies |
| **Output** | `skills[]` | — | Matched skills with name, description, install command |
| **Output** | `installCommand` | — | `npx clawhub install <skill-name>` when user wants to install |

---

## Routing Protocol

Follow these **five steps** for every invocation. Never skip a step.

1. **Parse** — Extract the user's intent and explicit parameters (`RegionId`, `SceneId`, `HistoryReportId`, etc.).
   > 💡 **Smart Defaults — Minimize questions, delegate fast**
   > - `RegionId` unspecified → default to `cn-shanghai`, never ask the user
   > - `HistoryReportId` unspecified → delegate to reporter directly; it will query the latest report on its own
   > - `sceneConfig` / URL / concurrency / duration details → pass user's raw message to sub-skill; let it construct the config; never ask
   > - `SceneId` unspecified AND intent requires it → this is the **ONLY** case where you may ask the user
   > - Sub-skill unavailable → route to `alibabacloud-find-skills` to search and guide installation
   > 
   > ⚠️ **No-Ask Red Line**: Except for missing SceneId, you MUST NOT ask the user for any other information. Do NOT mention or reference missing parameters (like HistoryReportId) to the user. Delegate immediately and silently let the sub-skill handle it.
2. **Match** — Score user intent against each row's *Intent Signature + Positive Triggers + Negative Triggers*. Pick the highest match with `Status = ✅ Active`. Ties → prefer more specific.
   > ⚠️ **Priority Rule**: If user message contains the word "skill" (e.g., "any...skill", "search skill", "find a skill"), **always** match to `alibabacloud-find-skills` first, even if the message also mentions PTS / stress-testing keywords. The word "skill" is the strongest signal for find-skills routing.
   > ⚠️ **Product-Diagnosis Rule**: If user wants to diagnose/analyze a specific cloud product (RDS, ECS, Redis, SLB, etc.) that is NOT PTS itself, match to `alibabacloud-find-skills` — because this router has no sub-skill for product-level instance diagnosis.
3. **Announce [MUST — ATOMIC]** — Immediately output exactly one line to the user:
   > "This matches **{sub-skill-name}** ({intent}). Delegating to it now."
   Do NOT insert any other tool calls, file reads, or searches between this announcement and Step 4.
4. **Handoff [MUST — ATOMIC]** — Immediately after Step 3, invoke the **Skill tool** (the tool literally named `Skill` in your tools list) with `{sub-skill-name}` and the resolved Input Contract fields.
   > **CRITICAL**: Simply call the `Skill` tool with the sub-skill name — the platform handles resolution. If the Skill tool call fails, report the error to the user and stop.
5. **Summarize** — After the sub-skill returns, do **NOT** directly pass through the raw output. Extract key metrics and status information from the result, then format and present them to the user using the templates defined in **Result Summarization** below.

---

## Fallback Behavior

| Situation | Action |
|-----------|--------|
| User request is a knowledge / conceptual question about PTS **without mentioning "skill"** and **without asking about non-PTS product diagnosis** | Answer inline without delegation. Do NOT invoke any sub-skill. |
| User wants to diagnose/analyze a non-PTS product (RDS, ECS, Redis, SLB, etc.) or asks "have tools for X" | Route to `alibabacloud-find-skills` via Skill tool — this router has no sub-skill for product-level diagnosis. |
| User mentions searching/finding skills or asks for **skill for a specific product** (e.g., "RDS skill", "ECS skill") | Route to `alibabacloud-find-skills` via Skill tool. This takes priority over inline Q&A. |
| No row matches | Ask the user a single clarifying question using the **Positive Triggers** of all Active sub-skills as concrete examples. |
| User explicitly names a sub-skill | Route directly via Skill tool, skip Match scoring. |
| Sub-skill invocation fails / skill not found | Route to `alibabacloud-find-skills` to search for the corresponding skill and guide the user to install it. **NEVER** fall back to executing CLI commands yourself. |

> ⚠️ **Router-Only Invariant** — My ONLY tool is the **Skill tool** for delegation.
> If Skill tool is unavailable or fails, I report the error and stop. I never fall back to CLI/shell/web search.

---

## Result Summarization

After a sub-skill completes execution, the router MUST summarize its output before presenting to the user. Do NOT transparently relay raw sub-skill responses.

### General Summary Template

All summarized results follow this structure:

```
📋 **PTS Operation Summary**

| Field | Value |
|-------|-------|
| Operation | {intent} |
| Status | {status: success/failed/user_cancelled} |
| SceneId | {SceneId} |
| ... | ... |

{Key metrics in table or list format if available}

{1-3 suggested next actions if applicable}
```

### `alibabacloud-pts-task` Result Summarization

Summarize differently based on intent:

| Intent | Key Fields to Extract |
|--------|----------------------|
| **create** | SceneId, SceneName, target URL, concurrency, duration |
| **start** | SceneId, start status, PlanId / JobId |
| **stop** | SceneId, stop status |
| **report** | Key performance metrics: QPS, RT mean / P99, success rate, concurrency, total request count |
| **delete** | SceneId, deletion status |
| **jmeter_upload** / **jmeter_run** | JMeter SceneId, execution status |

For **report** intent, append a performance metrics table:

```
📊 **Key Performance Metrics**

| Metric | Value |
|--------|-------|
| QPS | {value} |
| RT Mean | {value} ms |
| RT P99 | {value} ms |
| Success Rate | {value}% |
| Concurrency | {value} |
| Total Requests | {value} |
```

### `alibabacloud-pts-reporter` Result Summarization

Extract and present:

1. **Report Key Metrics** — QPS, RT Mean / P99, Success Rate, Concurrency, Total Requests (from PTS report).
2. **Report-Observable Bottlenecks (Top N)** — Each recommendation includes:
   - Problem area (`area`)
   - Severity (`severity`)
   - Evidence summary (`evidence`)
   - Tuning suggestion (`suggestion`)

3. **Priority Action List** — At the end, append a priority-ranked action list:

```
🎯 **Priority Action List**

1. [severity: High] {area} — {suggestion}
2. [severity: Medium] {area} — {suggestion}
3. ...
```

4. **[MUST] Proactive Follow-Up — Product-Level Deep Diagnosis** — After presenting the action list, proactively ask:

```
💡 **Next Step: Product-Level Deep Diagnosis**

The report analysis has identified the bottleneck areas above. If you need instance-level
diagnosis and tuning for specific cloud products, please tell me which product component
you want to dive into (e.g., ECS / RDS / Redis / SLB / PolarDB).

I will search for the corresponding diagnostic Skill and guide you through installation.
```

**Routing flow after user selection:**
- Use the user's chosen product keyword as `searchIntent`, route to `alibabacloud-find-skills`
- After find-skills returns matched skill list, present recommendations to the user with install commands
- After installation, prompt the user that they can now use that skill for instance-level diagnosis

> **Note:** This follow-up is triggered ONLY when the reporter returns bottlenecks with severity=High/Medium. If the report conclusion is "no significant issues", skip this step.

---

## Extension Points — How to Add a New Sub-Skill

When a new sub-skill (e.g., `alibabacloud-pts-reporter`) becomes Active, update **exactly these three places**:

1. **This file — Registry table**: flip `Status` from 🚧 to ✅; refine Positive/Negative Triggers based on real intent drift.
2. **This file — Sub-Skill Contracts section**: finalize the Input/Output Contract (remove "— contract draft").
3. **`references/routing-rules.md`**: add worked examples (Positive / Negative / Edge cases) for the new sub-skill.

> **DO NOT**:
> - Add any `aliyun` CLI command here (router stays CLI-free).
> - Duplicate sub-skill internals (RAM policy, workflow steps, JSON schema) — these belong inside the sub-skill's own `references/`.
> - Overlap triggers with existing rows without updating Negative Triggers on both sides.

---

## References

- [`references/routing-rules.md`](references/routing-rules.md) — Detailed intent-matching examples & edge cases (load on demand when routing is uncertain).

## Checklist (self-verification before handoff)

- [ ] Intent identified and mapped to **exactly one** Active sub-skill, or fallback path taken.
- [ ] Required Input Contract fields gathered (or clarifying question asked).
- [ ] Announcement line sent to user before Skill tool invocation.
- [ ] After handoff, Output Contract surfaced back to user.
- [ ] Router body did not execute any CLI / OpenAPI / business logic.
- [ ] After handoff, summarized output presented to user using Result Summarization templates.
