# Confirmation Gate — HARD STOP (Create / Update / Delete)

**[CRITICAL — HIGHEST PRIORITY RULE]** Authoritative rules for the `create-resource-group` / `update-resource-group` / `delete-resource-group` confirmation gate. Referenced by `SKILL.md` §6.

## Hard-block declaration

> 🚨 **Never assume authorization. This applies equally to CREATE, UPDATE, and DELETE.**

The agent is **ABSOLUTELY FORBIDDEN** from executing `create-resource-group`, `update-resource-group`, or `delete-resource-group` in the same turn as the user's original request. Before any of these invocations, the agent MUST assume itself **unauthorized** and proceed only after the user explicitly authorizes via the literal token `CONFIRM-CREATE <RESOURCE_GROUP_NAME>` (for create) or `CONFIRM <RESOURCE_GROUP_NAME>` / `CONFIRM <RESOURCE_GROUP_ID>` (for update / delete) in the current conversation.

> 🚫 **Environment-agnostic.**

Regardless of whether the current context is automated testing, CI pipeline, sandbox, eval environment, dry-run demo, or the user has agreed multiple times in conversation history — the agent MUST **re-wait** and **re-validate** the current turn's `CONFIRM-CREATE <RG_NAME>` (for create) or `CONFIRM <RG_NAME>` / `CONFIRM <RG_ID>` (for update / delete) token before each `create-resource-group` / `update-resource-group` / `delete-resource-group` call. Historical tokens, implicit authorization, verbal assent — none count.

## Banned self-authorization phrasing

The phrases below — or close paraphrases — appearing anywhere in the agent's thinking, output, or tool invocations are treated as **self-forged authorization = severe over-reach**, equal to mutating without a CONFIRM token:

- "Since the current environment is an automated-testing context, I will continue executing the real operation."
- "Because this is an eval / CI scenario, I will skip the CONFIRM wait."
- "To speed up the test flow, I will batch-execute all updates."
- "The user has already agreed multiple times in earlier turns, so no fresh CONFIRM is needed this turn."
- "The dry-run has passed, so I can directly execute the real update."
- "Create is a non-destructive operation, so I can skip the CONFIRM-CREATE wait."
- "The user asked me to create, so that is implicit authorization to execute."
- "I will go ahead and create since the parameters are valid."
- Any "the environment is special → therefore the gate is relaxed" self-justifying logic.
- Any "create is safe / non-destructive → therefore no confirmation needed" self-justifying logic.

These are not mitigating clauses — they are **triggers**. Once seen, the agent MUST immediately stop the workflow and emit a `🛑 Precondition Not Met` block (with `Failed precondition` reading *"Self-authorization phrasing detected; gate not passed"*), then exit.

## Same-turn execution prohibition

> 🚫 The verbatim prompt and the mutating CLI MUST be in different turns.

After asking the user verbatim for `CONFIRM-CREATE <RG_NAME>` or `CONFIRM <RG_NAME>`, the agent MUST immediately end the current turn and wait for the user to reply in the **next** turn. **STRICTLY FORBIDDEN** to emit the verbatim prompt and call `create-resource-group` / `update-resource-group` / `delete-resource-group` in the same message / same turn — even with intervening thinking, other tools, or self-dialogue. Same-turn execution = 0 wait = equivalent to never having asked.

- Decision rule: from the verbatim prompt being printed until the next real user message, everything (thinking, Bash calls, other tool calls, self-talk) belongs to the **same turn**. Any `aliyun paistudio create-resource-group` / `update-resource-group` / `delete-resource-group` call in that window = violation.
- The token MUST appear in the **user's next reply**, not in the agent's continuation message. The agent MUST NOT "pretend" the user has replied, and MUST NOT have a Bash call answer on the user's behalf.

## Token literal requirements

- Must come from a **real user** in their **next turn**, as the **literal string** `CONFIRM-CREATE <RESOURCE_GROUP_NAME>` (for create) or `CONFIRM <RESOURCE_GROUP_NAME>` / `CONFIRM <RESOURCE_GROUP_ID>` (for update / delete), with the placeholder substituted with the real name or ID; name preferred.
- The following do NOT unlock: `yes` / `go` / `confirm` / `ok` / `proceed` / wrong case / RG name or ID typo / missing space / using `CONFIRM` for create or `CONFIRM-CREATE` for update/delete.

## Forging tokens — strictly forbidden

The agent MUST NOT:

- Use `echo "CONFIRM-CREATE <RG_NAME>"` / `echo "CONFIRM <RG_NAME>"` / `echo "CONFIRM <RG_ID>"` / `printf` / programmatic construction in thinking, Bash, or any tool call to fake having received a token.
- Interpret "the user said yes in the previous turn" as a token for the current turn.
- Skip the wait and proceed directly.
- "Fill in a CONFIRM for the user and continue" — equivalent to forging authorization = severe over-reach.

## Mandatory dry-run before Update / Delete

Before asking for the confirmation token for `update-resource-group` or `delete-resource-group`, the agent **MUST** first execute the command with `--cli-dry-run` and show the output to the user. This is non-negotiable — **no dry-run, no confirmation prompt, no execution**. The sequence is:

1. Run `<command> ... --cli-dry-run` to preview the resolved request payload.
2. Show the dry-run output to the user.
3. Ask for the confirmation token.
4. **STOP. END THE TURN.**

Skipping the `--cli-dry-run` step is a **critical workflow violation**, equivalent to executing without confirmation.

## Gate procedure

Each `create-resource-group` / `update-resource-group` / `delete-resource-group` operation requires:

1. **Print the resolved plan** — must be a literal `📋 Resolved Plan` block, **not** a meta-statement like "now printing Resolved Plan".
   - **Create**: print all resolved parameters (Region, Name, ResourceType, Version, UserVpc if applicable).
   - **Update / Delete**: run `--cli-dry-run` first (see above), then print target resource ID, action, full diff of fields being changed, blast radius — all 7 required fields per `SKILL.md` §5 *Branch 3*, including the dry-run output.
2. **Ask the user verbatim**:
   - **Create**:
     ```
     Please explicitly confirm whether to execute the above create operation. Type "CONFIRM-CREATE <RESOURCE_GROUP_NAME>" to continue; any other input cancels.
     ```
   - **Update / Delete**:
     ```
     Please explicitly confirm whether to execute the above <update|delete> operation. Type "CONFIRM <RESOURCE_GROUP_NAME>" (or the actual ResourceGroupId) to proceed; any other input cancels.
     ```

   The placeholder MUST be substituted with the real name (preferred) or ID. Verbatim placeholders (with angle brackets retained) and wildcards (`CONFIRM ALL`, `CONFIRM <RG>`, `CONFIRM batch`) are forged prompts and forbidden.
3. **End the turn and wait for the user's NEXT message**. The verbatim prompt is the **last** content the agent emits in this turn — no Bash, no further tool calls, no continuation messages until the user replies.
4. **Only proceed** if the user's next message contains the exact literal token: `CONFIRM-CREATE <real RG name>` (for create) or `CONFIRM <real RG name>` / `CONFIRM <real RG ID>` (for update / delete). Any other reply is cancellation. Using the wrong token type (e.g. `CONFIRM` for create, or `CONFIRM-CREATE` for update/delete) is also cancellation.
5. **Idempotency window**: a confirmation token is valid for the immediately following CLI call only. Re-running, retrying, or batching multiple resources / multiple steps under one token is forbidden — each mutating call needs its own freshly-issued plan + token.

## Failure to obtain a valid token

If a valid token is not received, the agent MUST immediately stop the workflow and emit a `🛑 Precondition Not Met` block (with `Failed precondition` reading *"Did not receive the literal `CONFIRM-CREATE <RESOURCE_GROUP_NAME>` (for create) or `CONFIRM <RESOURCE_GROUP_NAME>` / `CONFIRM <RESOURCE_GROUP_ID>` (for update/delete) token; cannot execute mutating CLI"*), then exit. **STRICTLY FORBIDDEN** to silently retry, fall back, or degrade to read-only.

## Multi-task — one mutating operation per turn

When the user requests multiple operations in a single message, the agent MUST decompose the request into individual tasks and process each sequentially. **ONE mutating operation per turn.** Each task follows its own workflow in full — no shortcuts.

- Each mutating CLI needs its own `📋 Resolved Plan` block + its own confirmation token in a separate turn.
- The agent MUST NOT execute or prepare the second task until the first one is fully confirmed and executed.
- The agent MUST NOT print multiple confirmation prompts in one turn.
- The user's multi-step request is a TODO list, not a blanket execution authorization.

**Example — user sends: "Create RG test-rg in cn-wulanchabu (ECS v2.0), rename rg-old to rg-new, delete rg-empty":**

| Turn | Actor | Action |
| --- | --- | --- |
| 1 | Agent | Decompose into 3 tasks. Start task 1: follow Step 6.3 (validate params, print plan). Ask `CONFIRM-CREATE test-rg`. **STOP.** |
| 2 | User | `CONFIRM-CREATE test-rg` |
| 3 | Agent | Execute `create-resource-group` for test-rg. Start task 2: follow Step 6.4 (existence check, compute diff, **run `update-resource-group --cli-dry-run`**, show output, print plan). Ask `CONFIRM rg-old`. **STOP.** |
| 4 | User | `CONFIRM rg-old` |
| 5 | Agent | Execute `update-resource-group`. Start task 3: follow Step 6.7 (existence check, MG-count check, **run `delete-resource-group --cli-dry-run`**, show output, print plan). Ask `CONFIRM rg-empty`. **STOP.** |
| 6 | User | `CONFIRM rg-empty` |
| 7 | Agent | Execute `delete-resource-group`. All tasks complete. |

**Common violations in multi-task mode (ALL are critical failures):**
- Executing `create-resource-group` without waiting for `CONFIRM-CREATE` because "it's just a create"
- Skipping `--cli-dry-run` for update/delete because "there are more tasks to do"
- Executing multiple mutating commands in one turn
- Skipping the confirmation gate because "the user already asked for all of them"
- Printing multiple confirmation prompts in one turn

## Read-only operations

- Read-only steps (`list-*`, `get-*`) do NOT require confirmation.
