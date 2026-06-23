# Routing Rules — alibabacloud-pts-pilot

> **Purpose:** Concrete intent-matching examples that extend `SKILL.md` → *Sub-Skill Registry*.
> Load on demand when the router is uncertain which sub-skill to delegate to.

---

## 1. `alibabacloud-pts-task` — PTS CRUD Worker (✅ Active)

### ✅ Positive examples — route here

| User utterance | Resolved intent | Required fields to collect |
|----------------|-----------------|----------------------------|
| "Help me create a PTS stress-test scenario targeting https://api.example.com" | `create` | Delegate directly with `RegionId` (default cn-shanghai) + user's raw message; sub-skill builds sceneConfig |
| "Start the stress-test for SceneId scene-abc" | `start` | `RegionId`, `SceneId=scene-abc` |
| "Stop the running stress-test scene-abc" | `stop` | `RegionId`, `SceneId=scene-abc` |
| "Check the stress-test report for scene-abc" | `report` | `RegionId`, `SceneId=scene-abc` (or `ReportId`) |
| "List all PTS scenarios under my account" | `query` (list) | `RegionId` |
| "Delete scenario scene-abc" | `delete` | `RegionId`, `SceneId=scene-abc` |
| "Upload this JMeter script xxx.jmx to PTS and run" | `jmeter_upload` + `jmeter_run` | `RegionId`, script path, scene name |
| "list PTS scenes in cn-shanghai" | `query` (list) | `RegionId=cn-shanghai` |
| "start scene scene-xyz" | `start` | `RegionId`, `SceneId=scene-xyz` |

### ❌ Negative examples — DO NOT route here

| User utterance | Why NOT | Correct action |
|----------------|---------|----------------|
| "What is PTS? How is it different from JMeter?" | Conceptual Q&A, no execution intent | Answer inline in router |
| "My stress-test QPS is only 500, how to optimize?" | Tuning advice belongs to report analyzer when grounded in a report | Ask user for `HistoryReportId`, then route to `alibabacloud-pts-reporter` |
| "I want to stress-test" (only, no verb) | Too vague — missing intent verb | Ask clarifying question using Positive examples |

### Edge cases

- **Mixed intent** — "Create scenario and start immediately"
  → Route to `alibabacloud-pts-task` with `intent=create`, ask it to chain `start` after success. Pass both in one handoff.
- **Region missing** — "Start scene-abc"
  → Default to `cn-shanghai`, never ask the user, delegate directly.
- **SceneId format uncertain** — user supplies an ID without confirming source
  → Do NOT validate format in router; delegate as-is, sub-skill will surface any error.

---

## 2. `alibabacloud-pts-reporter` — PTS Report Analyzer (✅ Active)

### ✅ Positive examples — route here

| User utterance | Resolved intent | Required fields to collect |
|----------------|-----------------|----------------------------|
| "Last stress-test report report-123 shows bottleneck where?" | `report_analysis` | `RegionId`, `HistoryReportId=report-123` |
| "Analyze the latest stress-test result of scene-abc" | `report_analysis` | `RegionId`, `SceneId=scene-abc` (reporter will resolve the latest report) |
| "RT P99 is very high in the report, what's the cause?" | `report_analysis` | `RegionId`, `HistoryReportId` |
| "Why does the QPS curve show a staircase drop in this stress-test?" | `report_analysis` | `RegionId`, `HistoryReportId` |

### ❌ Negative examples

| User utterance | Why NOT | Correct action |
|----------------|---------|----------------|
| "create/start/stop scenario" | CRUD actions belong to `alibabacloud-pts-task` | Route to `alibabacloud-pts-task` |
| "What is stress-test TPS?" | Conceptual Q&A, answer inline | Router answers directly |
| "Give tuning advice based on instance i-xxx" | Instance-level diagnosis is NOT yet supported by `alibabacloud-pts-reporter` | Do NOT route to reporter; inform user that only report analysis is supported currently; product-level diagnosis skill needed |

### Edge cases

- **Missing `HistoryReportId`** — "Help me optimize my stress-test"
  → Delegate to reporter directly; it will query the latest report on its own. Never ask the user.
- **User pastes a report screenshot/text only** — Delegate to reporter directly; let it handle the content.
- **After report analysis, user wants deep product diagnosis** (e.g. "I want to tune RDS" / "deep-analyze ECS") — This is the proactive follow-up flow; use the product keyword as `searchIntent` and route to `alibabacloud-find-skills` to search for the corresponding diagnostic skill and guide installation.
- **User asks for instance-level diagnosis but no corresponding skill exists** — Router should first route to `alibabacloud-find-skills` to search; if no match found, inform user that no skill is currently available.

---

## 3. `alibabacloud-find-skills` — Skill Search & Discovery (✅ Active)

### ✅ Positive examples — route here

| User utterance | Resolved intent | Required fields to collect |
|----------------|-----------------|----------------------------|
| "Any skill for PTS management" | `search` | searchIntent="PTS management" |
| "Search alicloud-related skills" | `search` | searchIntent=user's raw message |
| "find alicloud skills for database" | `search` | searchIntent="database" |
| "Browse skill marketplace categories" | `browse_categories` | (none) |
| "Help me install alibabacloud-ecs-ops skill" | `install` | skillName="alibabacloud-ecs-ops" |
| "PTS stress-test found RDS bottleneck, any RDS diagnostic tool?" | `search` | searchIntent="RDS diagnosis" |
| "Report shows database is slow, help me find diagnostic tools" | `search` | searchIntent="database diagnosis" |
| "Want to deep-analyze ECS CPU issue, anything available?" | `search` | searchIntent="ECS CPU diagnosis" |

### ❌ Negative examples

| User utterance | Why NOT | Correct action |
|----------------|---------|----------------|
| "Create a PTS stress-test scenario" | Concrete execution intent | Route to `alibabacloud-pts-task` |
| "Analyze the stress-test report" | Report analysis intent | Route to `alibabacloud-pts-reporter` |
| "What is PTS" | Conceptual Q&A | Router answers inline |

---

## 4. Ambiguity Resolution Playbook

When two or more sub-skills seem to match:

1. **Check verbs** — Execution verbs (create/start/stop/delete/query) → `alibabacloud-pts-task`. Analytical verbs (analyze/interpret/why) + `HistoryReportId`/`SceneId` → `alibabacloud-pts-reporter`.
2. **Check object specificity** — A `HistoryReportId` or `SceneId` with analytical verb → `alibabacloud-pts-reporter`. A `SceneId` with action verb → `alibabacloud-pts-task`.
3. **Check tense** — Past-tense result analysis (e.g. “the stress test just now…why…”) → `alibabacloud-pts-reporter`. Present/future action → `alibabacloud-pts-task`.
4. **InstanceId-only with analytical intent** — User mentions `InstanceId` with analysis intent → route to `alibabacloud-find-skills` to search for the product's diagnostic skill and guide installation. If no match, inform user no skill is currently available.
5. **Last resort** — Ask one clarifying question listing the Positive triggers of each candidate.

---

## 5. Router Anti-Patterns (DO NOT)

| Anti-pattern | Why it's wrong |
|--------------|----------------|
| Router runs `aliyun pts describe-scenes` to "help pick" | Breaks Router-Only invariant; sub-skill enforces pre-checks |
| Router reads AK/SK or calls `aliyun configure list` | Credential gate is the sub-skill's job |
| Router loads `pts-scene-json-reference.md` to validate user config | JSON schema lives inside `alibabacloud-pts-task/references/` |
| Router asks 5 clarifying questions before handoff | Ask **one** question max; let sub-skill handle the rest via Parameter Confirmation |
| Router routes to 🚧 Planned sub-skill silently | MUST surface Planned status + offer Active alternatives (applies only when a sub-skill is still Planned; currently both are ✅ Active) |

---

## 6. Future Sub-Skills — Reserved Intent Space

To prevent trigger collision when new workers are added, the following intent spaces are **reserved**:

| Reserved name (draft) | Intent space | Distinguishing verbs |
|-----------------------|--------------|----------------------|
| `alibabacloud-pts-schedule` | Scheduled / recurring stress runs | "scheduled stress-test", "daily execution" |
| `alibabacloud-pts-compare` | Cross-report comparison | "compare two stress-tests", "performance regression" |
| `alibabacloud-pts-alarm` | Alarm rules on stress metrics | "stress-test alarm", "threshold alert" |

When activating any of these, repeat the 3-step Extension flow from `SKILL.md`.
