# Pre-Reply Compliance Red Lines (R1–R7)

Authoritative pre-reply gate for the `pai-resource-group-management` skill. Referenced by `SKILL.md` §6.

Before generating **every** final user-facing reply, the agent MUST cross-check the **non-negotiable** red lines below. Any failure → interrupt the reply, fall back to the corresponding branch block or refusal path, and only resume after fixing. R1–R7 are AND-related, not OR.

This list complements `SKILL.md` §6 *Exit Checklist*:

- **Exit Checklist** focuses on **flow order** (branch → CONFIRM → CLI → disable).
- **This compliance gate** focuses on **non-negotiable red lines** (what MUST NOT happen).

Both run **simultaneously**, neither replaces the other.

## R1 — MachineGroup deletion always refused

**Self-check**: For all MG deletion / release requests (with or without CONFIRM token), did the agent strictly refuse and direct the user to the PAI Console (Resource Pool → Machine Group → Unsubscribe/Release)?

**Failure action**: Emit explicit refusal + Console path. **NEVER** call `delete-resource-group-machine-group` / `delete-machine-group`.

## R2 — AI-mode closure

**Self-check**: Has the current turn issued `aliyun configure ai-mode disable` as the **last** `aliyun` CLI (after all `paistudio` calls, before the natural-language reply)?

**Failure action**: Immediately issue `aliyun configure ai-mode disable`, then generate the reply. Mark the turn as a P0 workflow defect.

## R3 — CONFIRM token cross-turn

**Self-check**: For every `update-resource-group` / `delete-resource-group` call, did a literal `CONFIRM <real RG name>` (or `CONFIRM <real RG ID>`) token arrive in an **independent turn**? Does each mutating call correspond to a **unique single** legitimate token from the previous user turn?

**Failure action**: If missing or same-turn execution: stop subsequent steps, run `aliyun configure ai-mode disable`, report P0 over-reach to the user.

## R4 — Structured branch block literal-present

**Self-check**: In conversation history, before each mutating CLI call, does a standalone segment exist with literal `📋 Resolved Plan` header (with all 7 required fields)? For each refusal scenario, does a segment with literal `🛑 Precondition Not Met` or `⚠️ Input Conflict` header exist?

**Failure action**: Immediately emit the missing literal block (do NOT accept thinking / summary / meta-description as substitute), then continue.

## R5 — Plugin & channel purity

**Self-check**: Were all mutating operations this turn conducted through `aliyun paistudio …`? Are there any traces of SDK / curl / MCP / `resourcemanager` / `pai` / `aiworkspace` or other alternative channels? Was `aliyun plugin list | grep paistudio` verified before invocation?

**Failure action**: If alternative channels found: stop, report over-reach, run `aliyun configure ai-mode disable`. If plugin not verified: add the verification step before the corresponding branch.

## R6 — Lingjun VPC forbidden-string compliance

**Self-check**: For Lingjun VPC modification request replies, is the literal string `aliyun paistudio update-resource-group` and `--user-vpc` command fragment **completely absent** (including counter-example code blocks, inline code, SDK fragments)?

**Failure action**: Rewrite the reply as plain natural-language refusal + escalation path; remove all command fragments.

## R7 — Parameter minimization

**Self-check**: For all `update-resource-group` calls, does the command-line parameter set strictly equal "the set of fields actually changing this turn"? Are there any extra fields not requested by the user (e.g., `--name` was carried when only description was changed)?

**Failure action**: Rewrite the command line to remove unchanged fields, re-enter §5 Branch 3 + CONFIRM gate.

## Why this gate exists

Past incidents show that an agent following the §5 / §6 flow correctly may still ship a reply that:

- Calls `paistudio` correctly but skips the AI-mode disable.
- Issues the verbatim CONFIRM prompt then immediately runs the mutating CLI in the same turn.
- Adds `--name` to a description-only update because "it's harmless".
- Emits `🛑 Precondition Not Met` with the right structure but mentions `aliyun paistudio update-resource-group` in the explanation, implying a viable path.

Each of these passes flow-order checks but breaks a non-negotiable red line. R1–R7 catches them.
