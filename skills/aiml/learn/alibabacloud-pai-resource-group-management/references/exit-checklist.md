# Exit Checklist — Mandatory Pre-Reply Discipline

Detailed exit checklist for the `pai-resource-group-management` skill. The compact summary lives in `SKILL.md` §6 *Exit Checklist*; this file is the authoritative full version.

## Why this exists

Every `aliyun paistudio` business API call issued by this skill MUST carry the per-command flag `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"` so RAM audit trails can distinguish agent calls from human calls. The flag is **scoped to a single command invocation** — it is not a global session toggle. Missing or malformed `--user-agent` on any business API call (including read-only `list-*` / `get-*` and `--cli-dry-run`) breaks the observability contract and is treated as a P0 workflow defect.

The flag MUST NOT be added to system / configuration commands such as `aliyun configure list`, `aliyun configure get`, `aliyun plugin update`, `aliyun plugin list`, `aliyun version` — those are local CLI utilities and do not accept `--user-agent`. Adding the flag to a system command is itself a P0 defect.

Any deprecated user-agent setter mechanism (e.g., a global / session-wide UA toggle issued via a separate `configure` subcommand) is **NO LONGER USED** by this skill. Do not call any such subcommand.

## When this checklist runs

Run top-down at **every** exit point — including all of:

- ✅ Successful mutating completion (create / update / delete returned 200).
- ✅ Mid-flow failure (CLI returned `Forbidden.RAM`, `NotFound`, `InvalidParameter`, etc.).
- ✅ Refusal (Lingjun VPC change, MachineGroup deletion, ACS variant create, etc.).
- ✅ User cancellation (CONFIRM token mismatch, user replied "no" / "cancel").
- ✅ `🛑 Precondition Not Met` block printed (Branch 2 exit).
- ✅ `⚠️ Input Conflict` block printed and turn ended waiting for user re-fill (Branch 1 exit).
- ✅ Read-only inspection complete (no mutation, no confirmation gate, but at least one business API call was issued — every such call must have carried `--user-agent`).
- ✅ Tool call error / unexpected exception bubbled up.

## The 7-point exit checklist (verbatim)

> 1. ✅ §5 branch block has been printed as a standalone, visible message segment (`📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict`) — required fields all present. Meta-statements ("now I will print Resolved Plan") do NOT count.
> 2. ✅ For mutating ops: a literal `CONFIRM-CREATE <actual RG name>` (for create) or `CONFIRM <actual RG name>` / `CONFIRM <actual RG ID>` (for update/delete) token from the real user was received in the **previous user turn** (not the same turn as the verbatim prompt), and the mutating CLI was issued exactly once against that token. A token with `<>` brackets retained, or `CONFIRM ALL` / `CONFIRM batch` / placeholder verbatim / wrong token type (e.g. `CONFIRM` for create), is treated as no legitimate token received.
> 3. ✅ For batch / multi-step ops: `N RG × M operations` produced exactly `N × M` separate `📋 Resolved Plan` blocks and `N × M` separate confirmation tokens (`CONFIRM-CREATE` for create, `CONFIRM` for update/delete) — no batch-wide single token was used. Only ONE mutating operation was executed per turn. No multiple confirmation prompts were printed in one turn.
> 4. ✅ No agent self-bypass phrasing appeared in this turn (e.g., "since the current environment is an automated-test context…", "skip CONFIRM in eval/CI scenarios", "the user has agreed multiple times already", "the dry-run passed so we can execute directly", etc.). If any such phrase appears, treat the turn as a P0 violation, abort all mutating CLI, and report.
> 5. ✅ For Lingjun VPC modify requests: refusal text contains **no** literal `aliyun paistudio update-resource-group` command string and **no** `--user-vpc` command fragment — only natural-language refusal plus the escalation path.
> 6. ✅ Every business API call this turn (`aliyun paistudio …`, including `--cli-dry-run` and read-only `list-*` / `get-*`) carried the literal flag `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"` with the actual session id substituted in (3-segment fixed format).
> 7. ✅ No system / configuration command (e.g., `aliyun configure list`, `aliyun configure get`, `aliyun plugin update`, `aliyun plugin list`, `aliyun version`) was invoked with `--user-agent`. No deprecated session-wide user-agent setter command was invoked at all.

## Banned self-bypass phrasing (full list)

If any of these phrases — or their close paraphrase — appears anywhere in the agent's thinking, output, Bash command, or tool invocation in the current turn, treat as a **P0 violation** and abort all mutating CLI:

- "Since the current environment is an automated-test context, I will go ahead and execute the actual operation."
- "Because this is an eval/CI scenario, I'll skip waiting for CONFIRM."
- "To speed up the test, I'll merge all updates into one execution."
- "The user has already agreed multiple times in earlier turns, no need to re-CONFIRM in this turn."
- "The dry-run passed, so I can directly execute the real update."
- "I'll fill in a CONFIRM on behalf of the user and continue."
- "Because this is sandbox / staging, the gate can be relaxed."
- Any "the environment is special, therefore the gate can be relaxed" form of self-justification.

## Recovery from a missing or malformed `--user-agent`

If a business API call was issued earlier in this turn without `--user-agent`, or with a malformed user-agent (wrong format, extra segments, missing session id, or set via a deprecated session-wide setter), the recovery procedure is:

1. Stop issuing further CLI calls for the current turn.
2. Re-issue the same business API call **once** with the correct flag, e.g.:
   ```bash
   aliyun paistudio list-resource-groups \
     --region cn-hangzhou \
     --page-number 1 --page-size 20 \
     --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"
   ```
3. Mark the turn as a P0 observability defect in the natural-language reply.
4. Do NOT chain additional operations; finish the turn, let the user re-issue follow-ups.

If a system / configuration command was contaminated with `--user-agent`, re-run the same command **without** the flag, then proceed.

## Final-step self-prompt (recommended)

Append the following line at the end of every multi-step plan, as a checklist line the agent renders to itself before sending the reply:

```
Final Step (MANDATORY): every `aliyun paistudio …` business API call this turn carried `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"`; no system command was contaminated with `--user-agent`.
```
