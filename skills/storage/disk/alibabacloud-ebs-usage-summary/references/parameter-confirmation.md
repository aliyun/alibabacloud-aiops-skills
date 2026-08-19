# Parameter Confirmation Gate — Full Rule Set

Detailed rules for the mandatory gate summarised in SKILL.md · Parameter Confirmation. Read this file whenever you need to decide **whether to wait for the user** or **how to phrase a clarification question**.

## 1. The Checklist (always required)

Before executing **any** `aliyun ebs ...` command, output a parameter checklist containing every user-customizable parameter you are about to use:

- **Metric queries**: region, disk / device-type / device-category / instance filter, metric name, start time, end time, period, time aggregation, cross-disk aggregation, group-by labels
- **Resource overview**: region, report type, application name / report ID, page size / page number

Rules:

1. **Never silently use defaults.** Documented defaults (`--period 5`, `--report-type present`, `--app-name default`) must still appear in the checklist.
2. If the user later replies with modifications, regenerate the checklist and re-enter this gate — re-confirmation is required after **every** parameter change.
3. Skipping the checklist output entirely is a workflow failure, regardless of which branch below is taken.

## 2. Two Branches

| Branch | Behaviour |
|--------|-----------|
| **A — Interactive Confirmation** (default for ambiguous inputs) | Ask the user to confirm or modify the checklist (e.g. *"Please confirm the parameters above. Reply 'confirm' to proceed, or tell me which fields to modify."*) and **WAIT for an explicit confirmation reply** before issuing any CLI command. |
| **B — Unattended Auto-Proceed** (fully-specified input / explicit auto-run signal) | Print the checklist as a *notification* (e.g. *"Parameters auto-locked based on your request. Starting execution. Interrupt to adjust."*), then **proceed directly without waiting**. This exists to prevent deadlock in automated evaluations, batch pipelines, and other no-human-in-the-loop runs. |

## 3. Bypass Decision Rule

Use **Branch B** when **ANY** of the following is true:

- **B1 · Fully-Specified Input**: All required parameters for the matched Scenario are unambiguously derivable from the user's prompt (or from documented defaults for optional parameters). For `describe-metric-data`: region + a filter (disk / device type / device category / instance) + metric name are all present or unambiguous. For the resource overview commands: the region is present (other parameters may fall back to documented defaults).
- **B2 · Explicit Auto-Run Signal**: The prompt contains any of `auto-execute`, `no-confirm`, `skip-confirm`, `auto`, `non-interactive`, `unattended`, or an equivalent instruction.
- **B3 · No-Human-Loop Environment**: The runtime is an automated evaluation / batch / CI pipeline where no follow-up user reply is possible (detect via absence of any prior interactive turn, or an env signal such as `EVAL_MODE=1`). **B3 only removes the obligation to *wait* for a reply — it never removes the obligation to *ask* the clarification question required by §4.**

Use **Branch A** when **ANY** of the following is true:

- **A1 · Ambiguity**: A required parameter is missing, has multiple plausible values, or the user's intent maps to more than one Scenario.
- **A2 · Destructive or Wide-Scope Risk**: The query would scan an excessively wide time window (> 30 days), or would aggregate across all disks of a region without any filter.
- **A3 · Re-Entry After Failure**: This gate is being re-entered after a Hard Stop (repeated command failures) or after a time-range error. Failures always require a human decision; Branch B is **FORBIDDEN** on re-entry.

**Conflict resolution:** when both a Branch B trigger and a Branch A trigger fire, **Branch A wins** (safety-first) — with one narrow carve-out: if the only Branch B trigger is **B3** and the only Branch A trigger is **A1**, emit the explicit clarification question, then proceed on stated assumptions instead of blocking forever. In every other A-vs-B conflict, Branch A blocks execution as normal.

## 4. [MUST] Ambiguity Clarification is NEVER Skippable

**Whenever a required parameter is missing or ambiguous (rule A1), you MUST explicitly ask the user a clarification question — this obligation holds even in unattended / automated-evaluation runs.**

The clarification question is a **separate, explicit, user-facing question**, not merely a row in the parameter checklist. It MUST:

1. **Name every missing or inferred parameter** (e.g. *"Which region should I query? Which disk ID (or ECS instance ID) should I target?"*).
2. **State the value you would assume** for each, and why (e.g. *"If unspecified, I will assume the CLI default profile region and filter by `DeviceType=system` rather than a specific disk ID."*).
3. **Invite correction** (e.g. *"Tell me the correct region / disk ID and I will re-run."*).

Then, depending on the environment:

- **Human-in-the-loop run** → **WAIT** for the user's answer before any CLI command (Branch A).
- **Unattended / automated-evaluation run** → after emitting the clarification question and stated assumptions, **proceed** with those assumptions so the run does not deadlock (Branch B), and repeat the open questions in the final answer.

**FORBIDDEN**: jumping straight to *"Parameters auto-locked, starting execution"* when a required parameter was never supplied by the user. Auto-locking is only legitimate under B1 (fully-specified input) — never as a way to dodge an unanswered question.

## 5. Re-Entry Gate on Failure

Any **2 consecutive** `aliyun ebs describe-metric-data` (or resource overview command) failures — timeout, non-zero exit, gateway 5xx — MUST trigger a **Hard Stop** and re-enter this gate:

1. Stop issuing commands.
2. Surface the failure to the user verbatim, together with the exact commands already attempted and the adjustments already applied.
3. Propose the next option (narrower window, larger period, different filter) and **wait for the user's decision**.

On re-entry, **Branch B is FORBIDDEN** (rule A3): take Branch A and wait for an explicit user decision.

**A 3rd silent retry without a user-facing Hard Stop message is FORBIDDEN** and is treated as a workflow failure — it is also checked after the fact by the retry-discipline audit performed during success verification.
