# Branch Discipline — Three Exclusive Branches

Authoritative rules for §5 *Pre-execution discipline*. Referenced by `SKILL.md` §5.

## Branch decision (top-down rule of thumb)

| # | Branch | Trigger | Required output |
|---|---|---|---|
| 1 | **⚠️ Input Conflict** — ask the user to refile | User-supplied inputs contradict a design rule (e.g. ECS v2.0 + UserVpc, missing required field). The skill could submit a *different* request, but MUST NOT silently rewrite the user's intent. | `⚠️ Input Conflict` block + question listing 3 concrete options. **No CLI call.** |
| 2 | **🛑 Precondition Not Met** — explicit skip | Live-state check fails (RG does not exist, MGs still attached for delete, etc.). | `🛑 Precondition Not Met` block. **No mutating CLI call.** |
| 3 | **📋 Resolved Plan** — happy path | All inputs valid and live state allows the action. | `📋 Resolved Plan` block before submission; for create wait for `CONFIRM-CREATE <real RG name>` token; for update/delete wait for `CONFIRM <real RG name>` token (name-priority; ID also acceptable). |

**Picking the branch**:

- Reason cites a **user input that contradicts a design rule** → Branch 1. Never silently strip / coerce the conflicting input.
- Reason cites a **state observation** (`TotalCount=0`, `TotalCount=3`, `NotFound`) → Branch 2.
- Otherwise → Branch 3.

Read-only `list-*` / `get-*` calls are exempt — execute directly, no branch block required.

## Execution lock — no mutating CLI before the branch block is fully printed

After the §5 branch decision, the agent MUST emit the corresponding structured block (`📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict`) as a **standalone, user-visible message segment** with all required fields present.

- Before the branch block is fully printed, **STRICTLY FORBIDDEN** to call `create-resource-group` / `update-resource-group` / `delete-resource-group` / `delete-resource-group-machine-group` / `delete-machine-group` (also no `--cli-dry-run` form).
- The branch block MUST NOT be folded into a later result summary, MUST NOT live only in thinking, MUST NOT be replaced by a "branch X identified" summary that omits fields.
- If the branch block is incomplete or missing fields, any subsequent mutating CLI = **violation** (equivalent to skipping the branch decision entirely).
- If the agent started printing a branch block but was interrupted / the user re-asked, the agent MUST re-run the §5 decision + re-print the full block; do not continue mutating with stale context.

## Literal-match self-check — last gate before any mutating CLI

Before invoking any mutating CLI, the agent MUST run a **literal-match self-check**: scan the conversation history to confirm a complete, standalone user-visible message segment exists with one of the literal headers `📋 Resolved Plan` / `🛑 Precondition Not Met` / `⚠️ Input Conflict` (must be a user-visible paragraph, not thinking, not a comment, not a quoted reference).

- If the self-check fails (missing literal emoji + title header / found but missing required fields / only in thinking), the agent MUST immediately backtrack, emit the corresponding branch block, and re-enter the gate. **STRICTLY FORBIDDEN** to proceed.
- **STRICTLY FORBIDDEN** to skip the self-check or bypass completion with reasons like *"already confirmed in thinking"*, *"a short summary has been emitted"*, *"context already implies equivalent Resolved Plan info"*, *"discussed in prior turns"*.
- The **only** condition that passes self-check: a literal-matching structured block exists in the current turn or the previous turn (when the current turn is the response to a CONFIRM token). Anything else = fail.
- If self-check fails but mutating CLI was already called = **P0 over-reach event**: stop subsequent steps, mark the violation in the response, and apologize to the user.

## Required block shapes

All three blocks must be **distinct, labeled message sections** — not folded into a later result summary.

### 📋 Resolved Plan (Branch 3) — required fields

`Action` · `Region` · `ResourceGroupId` (or `(new)` for create) · `Field diff` (update only) · `Preconditions verified` (one bullet per relevant check from §5 parameter table) · `Blast radius` (one sentence) · `Resolved command` (the exact `aliyun paistudio …` invocation, including `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-resource-group-management/{session-id}"`).

After printing:

- For **create**, ask verbatim (**the agent MUST NOT call `create-resource-group` in this turn — same-turn execution is ABSOLUTELY FORBIDDEN**):

  ```
  Please explicitly confirm whether to execute the above create operation. Type "CONFIRM-CREATE <RESOURCE_GROUP_NAME>" to continue; any other input cancels.
  ```

  And **end the turn** waiting for the user's next message. Do NOT call `create-resource-group` until the user replies with the exact `CONFIRM-CREATE <real RG name>` token in a **separate message**.

- For **update / delete**, first run the command with `--cli-dry-run` and show the output to the user (**mandatory — skipping = critical violation**), then ask verbatim:

  ```
  Please explicitly confirm whether to execute the above <update|delete> operation. Type "CONFIRM <RESOURCE_GROUP_NAME>" (or the actual ResourceGroupId) to proceed; any other input cancels.
  ```

  And **end the turn** waiting for the user's next message.

### 🛑 Precondition Not Met (Branch 2) — required fields

`Intended action` · `Skipped steps` (one bullet per step in the would-be workflow + reason) · `Failed precondition` (Check / Result / verbatim CLI evidence) · `Why this matters` (one sentence) · `Next steps for the user` (numbered).

After printing: exit. **Do NOT prompt for CONFIRM** — no mutation will be issued.

### ⚠️ Input Conflict (Branch 1) — required fields

`Conflicting input` (what the user supplied) · `Design rule violated` (one-line cite of the rule from the §5 parameter table or VPC matrix) · `Concrete options for the user` (numbered, **exactly 3 concrete options** — never 1, never 2, never "etc." / "or similar". Each option MUST be a self-contained, complete restatement the user can pick verbatim) · explicit question asking the user to pick `1` / `2` / `3` or restate.

After printing: **wait for the user's explicit re-submission.**

## Block-shape compliance — no meta-statements, no shortcut substitutes

> 🛑 The structured block must be **literally printed**, not declared.

Phrases like "now printing Resolved Plan", "first print Resolved Plan (§5 Branch 3)", "I will print the Resolved Plan block" are **meta-descriptions**, not blocks. The agent MUST emit a single user-visible message that begins with the literal `📋 Resolved Plan` header and lists all 7 required fields line-by-line. Any field missing or merged into prose = block not emitted = subsequent mutating CLI is a violation.

> 🛑 The token placeholder MUST be substituted.

In the verbatim prompt, `<RESOURCE_GROUP_NAME>` / `<RESOURCE_GROUP_ID>` are **placeholders**. When printing, the agent MUST substitute the real RG name or ID (e.g., user said `test-rg` → the prompt MUST contain literal `CONFIRM test-rg`). **STRICTLY FORBIDDEN** to keep placeholders verbatim (`CONFIRM <RESOURCE_GROUP_ID>`), use wildcards (`CONFIRM ALL` / `CONFIRM *` / `CONFIRM <RG>` / `CONFIRM the resource group`), or have one token cover multiple RGs.

> 🛑 Name-priority for the token.

When the user references the RG by name (e.g., `test-rg`, `rg-lj-test`, `Lingjun-RG prod-1`), the agent MUST fill in the RG **name** in the verbatim prompt (e.g., `CONFIRM test-rg`), not the internal ID (e.g., `CONFIRM lingjpev4a3zjfxl`). Use ID only when the original request only provided ID, or when the name is ambiguous (multiple RGs with the same name) — and explicitly explain the disambiguation.

## Multi-step / batch operation rules

> See also `SKILL.md` §6 *Multi-Task Handling* for the top-level decompose-then-confirm discipline and a turn-by-turn example table.

> 🔁 Multi-step workflow — ONE mutating operation per turn.

When the user requests multiple operations in a single message, the agent MUST decompose the request into individual tasks and process each task sequentially. Each task follows its own Step 6.x workflow in full — **no step may be skipped, shortened, or combined just because the task is part of a batch.** Each mutating CLI (create / update / delete) requires its own `📋 Resolved Plan` block + its own confirmation token (`CONFIRM-CREATE` for create, `CONFIRM` for update/delete) in a separate turn. The agent MUST NOT execute or prepare the second task until the first one is fully confirmed and executed.

> 🔁 Batch formula — `N RG × M operations = N × M independent Resolved Plans + N × M independent tokens`.

Example: "rebind VPC for 13 ResourceGroups" with workflow *unbind then rebind* requires **13 × 2 = 26** independent `📋 Resolved Plan` blocks (one for each RG's unbind and rebind) and **26** independent `CONFIRM <RG_NAME>` tokens (one wait before each mutating call).

- **STRICTLY FORBIDDEN** to emit one "batch plan" covering multiple RGs.
- **STRICTLY FORBIDDEN** to use a single `CONFIRM ALL` / `CONFIRM batch` / "confirm all" token to unlock multiple mutating calls. Idempotency window is **one token, one call**.
- **STRICTLY FORBIDDEN** to execute multiple mutating commands in one turn.
- **STRICTLY FORBIDDEN** to print multiple confirmation prompts in one turn.
- If the user proactively says "I agree to all" / "batch confirm" / "one CONFIRM for all", the agent MUST refuse and explain: each RG's each mutating call requires its own `📋 Resolved Plan` block + its own `CONFIRM-CREATE <real RG name>` (for create) or `CONFIRM <real RG name or ID>` (for update/delete) token. This lets the user explicitly review every state change's diff and blast radius.
- If the user asks to "skip intermediate blocks" or "only confirm the last step" to speed up, the agent MUST also refuse — this is not a performance-optimization knob, it is a compliance baseline.

**The user's multi-step request is a TODO list, not a blanket execution authorization.** Each task follows its own Step 6.x workflow in full — no shortcuts.

## Branch 1 (Input Conflict) — silent-rewrite prohibition

Branch 1 is the **only** legitimate path for handling conflicts. Once in Branch 1, the agent MUST NOT:

1. **Silently fix / drop any conflicting field** — including: removing `--user-vpc` and proceeding to create ECS v2.0; switching `--biz-version` from `2.0` to `1.0` and proceeding; filling a missing required field with a "reasonable default" and proceeding. These are over-reaching rewrites of user intent = forged authorization.
2. **Use any internal tool to substitute the Input Conflict text block** — including `ask_user_question` / `AskUserQuestion`, IDE pop-ups, multi-choice widgets, or markdown collapse blocks (`<details>`). The conflict response MUST be the literal `⚠️ Input Conflict` text block with all template fields and 3 concrete options.
3. **Degrade to a verbal hint / suggestion** — e.g., "I noticed you supplied VPC but chose ECS v2.0 — should I just create the no-VPC version for you?" That is bypassing the template via inducement = silent rewrite. Forbidden.
4. **Submit any CLI request before the user's explicit refill instruction** ("pick 1" / "pick 2" / "pick 3" / explicit parameter rewrite) — even the `--cli-dry-run` form is forbidden, let alone real `create-resource-group` / `update-resource-group` / `delete-resource-group`. Until the user replies, the agent is **frozen**, no mutating CLI allowed.

Any violation above = **unauthorized execution of operations the user did not authorize**, equivalent to mutating without a CONFIRM token.

## Worked examples

See `SKILL.md` §5 for the canonical three-branch decision discipline summary, and the inline worked examples there for all three branches and the Lingjun refusal pattern.
