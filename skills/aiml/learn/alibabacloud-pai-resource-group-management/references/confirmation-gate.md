# Mandatory Two-Step Confirmation Gate (Update / Delete)

Authoritative rules for the `update-resource-group` / `delete-resource-group` confirmation gate. Referenced by `SKILL.md` §6.

## Hard-block declaration

> 🚨 **Never assume authorization.**

Before any `update-resource-group` / `delete-resource-group` invocation, the agent MUST assume itself **unauthorized** and proceed only after the user explicitly authorizes via the literal token `CONFIRM <RESOURCE_GROUP_NAME>` (or `CONFIRM <RESOURCE_GROUP_ID>`) in the current conversation.

> 🚫 **Environment-agnostic.**

Regardless of whether the current context is automated testing, CI pipeline, sandbox, eval environment, dry-run demo, or the user has agreed multiple times in conversation history — the agent MUST **re-wait** and **re-validate** the current turn's `CONFIRM <RG_NAME>` (or `CONFIRM <RG_ID>`) token before each `update-resource-group` / `delete-resource-group` call. Historical tokens, implicit authorization, verbal assent — none count.

## Banned self-authorization phrasing

The phrases below — or close paraphrases — appearing anywhere in the agent's thinking, output, or tool invocations are treated as **self-forged authorization = severe over-reach**, equal to mutating without a CONFIRM token:

- "Since the current environment is an automated test context, I will proceed with actual operations"
- "Since this is an eval/CI scenario, skip the CONFIRM wait"
- "To speed up the test flow, merge-execute all updates"
- "The user has agreed multiple times earlier, no need to re-CONFIRM this turn"
- "dry-run passed, can proceed directly with the real update"
- Any "special environment → therefore relax the gate" self-justifying logic

These are not mitigating clauses — they are **triggers**. Once seen, the agent MUST immediately stop the workflow, emit a `🛑 Precondition Not Met` block (with `Failed precondition` reading *"Self-authorization phrasing detected, gate check failed"*), call `aliyun configure ai-mode disable`, and exit.

## Same-turn execution prohibition

> 🚫 The verbatim prompt and the mutating CLI MUST be in different turns.

After asking the user verbatim for `CONFIRM <RG_NAME>`, the agent MUST immediately end the current turn and wait for the user to reply in the **next** turn. **STRICTLY FORBIDDEN** to emit the verbatim prompt and call `update-resource-group` / `delete-resource-group` in the same message / same turn — even with intervening thinking, other tools, or self-dialogue. Same-turn execution = 0 wait = equivalent to never having asked.

- Decision rule: from the verbatim prompt being printed until the next real user message, everything (thinking, Bash calls, other tool calls, self-talk) belongs to the **same turn**. Any `aliyun paistudio update-resource-group` / `delete-resource-group` call in that window = violation.
- The token MUST appear in the **user's next reply**, not in the agent's continuation message. The agent MUST NOT "pretend" the user has replied, and MUST NOT have a Bash call answer on the user's behalf.

## Token literal requirements

- Must be from a **real user** in their **next turn**, as the **literal string** `CONFIRM <RESOURCE_GROUP_NAME>` or `CONFIRM <RESOURCE_GROUP_ID>` (placeholder substituted with the real name or ID; name preferred).
- The following do NOT unlock: `yes` / `go` / `confirm` / `ok` / `proceed` / wrong case / RG name or ID typo / missing space.

## Forging tokens — strictly forbidden

The agent MUST NOT:

- Use `echo "CONFIRM <RG_NAME>"` / `echo "CONFIRM <RG_ID>"` / `printf` / programmatic construction in thinking, Bash, or any tool call to fake having received a token.
- Interpret "user said yes in the previous turn" as a token for the current turn.
- Skip the wait and proceed directly.
- "Fill in a CONFIRM for the user and continue" — equivalent to forging authorization = severe over-reach.

## Five-step gate procedure

Each `update-resource-group` / `delete-resource-group` operation requires:

1. **Print the resolved plan** (target resource ID, action, full diff of fields being changed, blast radius) — must be a literal `📋 Resolved Plan` block with all 7 required fields (Action, Region, ResourceGroupId, Field diff, Preconditions verified, Blast radius, Resolved command), **not** a meta-statement like "now output the Resolved Plan". Always include a `--cli-dry-run` preview when the CLI supports it.
2. **Ask the user verbatim**:

   ```
   Please explicitly confirm whether to execute the above <update|delete> operation. Enter "CONFIRM <RESOURCE_GROUP_NAME>" (or the actual resource group ID) to proceed; any other input cancels.
   ```

   The placeholder MUST be substituted with the real name (preferred) or ID. Verbatim placeholders (`CONFIRM <RESOURCE_GROUP_ID>` with brackets) and wildcards (`CONFIRM ALL`, `CONFIRM <RG>`, `CONFIRM batch`) are forged prompts and forbidden.
3. **End the turn and wait for the user's NEXT message**. The verbatim prompt is the **last** content the agent emits in this turn — no Bash, no further tool calls, no continuation messages until the user replies.
4. **Only proceed** if the user's next message contains the exact literal token `CONFIRM <real RG name>` or `CONFIRM <real RG ID>` (matching whatever placeholder was filled in step 2 — both forms acceptable, name preferred). Any other reply is cancellation.
5. **Idempotency window**: a confirmation token is valid for the immediately following CLI call only. Re-running, retrying, or batching multiple resources / multiple steps under one token is forbidden — each mutating call needs its own freshly-issued plan + token.

## Failure to obtain a valid token

If a valid token is not received, the agent MUST immediately stop the workflow, emit a `🛑 Precondition Not Met` block (with `Failed precondition` reading *"No literal `CONFIRM <RESOURCE_GROUP_NAME>` or `CONFIRM <RESOURCE_GROUP_ID>` token received, cannot execute mutating CLI"*), then call `aliyun configure ai-mode disable` and exit. **STRICTLY FORBIDDEN** to silently retry, fall back, or degrade to read-only.

## Read-only and create operations

- Read-only steps (`list-*`, `get-*`) do NOT require confirmation.
- `create-resource-group` does NOT require this gate, but the agent MUST still emit a `📋 Resolved Plan` block summarizing the resolved parameters before submission.
