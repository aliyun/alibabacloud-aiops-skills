# Exit Checklist — Mandatory Final-CLI Discipline

Detailed exit checklist for the `pai-resource-group-management` skill. The compact summary lives in `SKILL.md` §6 *Exit Checklist*; this file is the authoritative full version.

## Why this exists

`aliyun configure ai-mode enable` tags every subsequent `aliyun` CLI invocation with the AI-Mode user-agent so RAM audit trails can distinguish agent calls from human calls. Failing to disable AI-mode at every exit point pollutes the user's CLI profile across **subsequent unrelated invocations**, producing false attribution in the audit log. Treating the disable as the literal last CLI of the turn is the only reliable way to avoid that pollution — checks in summary text, in thinking, or in retries do not count.

## When this checklist runs

Run top-down at **every** exit point — including all of:

- ✅ Successful mutating completion (create / update / delete returned 200).
- ✅ Mid-flow failure (CLI returned `Forbidden.RAM`, `NotFound`, `InvalidParameter`, etc.).
- ✅ Refusal (Lingjun VPC change, MachineGroup deletion, ACS variant create, etc.).
- ✅ User cancellation (CONFIRM token mismatch, user replied "no" / "cancel").
- ✅ `🛑 Precondition Not Met` block printed (Branch 2 exit).
- ✅ `⚠️ Input Conflict` block printed and turn ended waiting for user re-fill (Branch 1 exit). Note: AI-mode **stays enabled** while waiting on Branch 1 — the disable runs on the next turn after the user re-submits and that turn exits.
- ✅ Read-only inspection complete (no mutation, no confirmation gate, but AI-mode was enabled at the start → must be disabled at the end).
- ✅ Tool call error / unexpected exception bubbled up.

## The 7-point exit checklist (verbatim)

> 1. ✅ §5 branch block has been printed as a standalone, visible message segment (`📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict`) — required fields all present. Meta-statements ("now outputting Resolved Plan") do NOT count.
> 2. ✅ For mutating ops: a literal `CONFIRM <actual RG name>` or `CONFIRM <actual RG ID>` token from the real user was received in the **previous user turn** (not the same turn as the verbatim prompt), and the mutating CLI was issued exactly once against that token. Token with `<>` brackets retained / `CONFIRM ALL` / `CONFIRM batch` / placeholder verbatim are all treated as no valid token received.
> 3. ✅ For batch / multi-step ops: `N RG × M operations` produced exactly `N × M` separate `📋 Resolved Plan` blocks and `N × M` separate `CONFIRM` tokens — no batch-wide single token was used.
> 4. ✅ No agent self-bypass phrasing appeared in this turn (e.g., "Since the current environment is an automated test context...", "eval/CI scenario skip CONFIRM", "user has agreed multiple times", "dry-run passed so proceed directly", etc.). If any such phrase appears, treat the turn as a P0 violation, abort all mutating CLI, run `aliyun configure ai-mode disable`, and report.
> 5. ✅ For Lingjun VPC modify requests: refusal text contains **no** `aliyun paistudio update-resource-group` command string, **no** `--user-vpc` command fragment — only natural-language refusal + escalation path.
> 6. ✅ `aliyun configure ai-mode disable` has been issued **as the final CLI command of the turn** — strictly after every other `aliyun paistudio …` call and strictly before the natural-language response text.
> 7. ✅ No `aliyun paistudio …` mutating CLI was issued after `aliyun configure ai-mode disable` (if so, re-disable at the very end and flag the violation).

## Banned self-bypass phrasing (full list)

If any of these phrases — or their close paraphrase — appears anywhere in the agent's thinking, output, Bash command, or tool invocation in the current turn, treat as a **P0 violation** and abort all mutating CLI:

- "Since the current environment is an automated test context, I will proceed with actual operations"
- "Since this is an eval/CI scenario, skip the CONFIRM wait"
- "To speed up the test flow, merge-execute all updates"
- "The user has agreed multiple times earlier, no need to re-CONFIRM this turn"
- "dry-run passed, can proceed directly with the real update"
- "I will fill in a CONFIRM for the user and continue"
- "Since this is sandbox / staging, the gate can be relaxed"
- Any "special environment → therefore relax the gate" self-justifying reasoning

## Recovery from a missed `disable`

If a previous turn ended without `aliyun configure ai-mode disable`, the **first** action of the next turn — before reading user request, before any planning, before any other tool — MUST be:

```bash
aliyun configure ai-mode disable
```

Then re-enable per the standard §6 enable block if the new turn is itself going to invoke `paistudio` actions.

## Final-step self-prompt (recommended)

Append the following line at the end of every multi-step plan, as a checklist line the agent renders to itself before sending the reply:

```
Final Step (MANDATORY): aliyun configure ai-mode disable
```
