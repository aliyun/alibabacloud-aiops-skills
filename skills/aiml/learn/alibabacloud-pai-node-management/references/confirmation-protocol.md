# Two-Step Confirmation Gate for `operate-node`

Node operations (`Cordon` / `Uncordon` / `Drain`) are state-mutating. The agent MUST halt at the `operate-node` step and wait for an explicit user token before executing.

## Protocol

1. **[MUST] Pre-operation status query**: call

   ```bash
   aliyun paistudio list-nodes --region "${REGION_ID}" \
     --resource-group-ids "${RG_ID}" \
     --node-names "${NODE_ID}" --page-number 1 --page-size 1
   ```

   > Append the per-command `--user-agent` flag specified in SKILL.md §0 to every actual invocation; it is omitted from the sample for readability.

   And put the node's current `Status` / `MachineGroupId` / `ResourceGroupId` into the confirmation prompt explicitly.

   > **Absolutely no skipping the pre-op query**: even if the user has already claimed *"the node is currently Running / already Cordoned / I just checked"*, the agent MUST query again — user self-report is not an audit-trustworthy source, and node state may have changed between turns. Skipping the query and going straight to the prompt is a violation. If the query returns 0 nodes (typo / wrong RG) or >1 nodes (anomaly), STOP and ask the user to disambiguate; do NOT proceed by guessing.

2. **[MUST] Print the confirmation prompt**, then **end the turn** — do NOT continue in the same turn. The prompt MUST include the literal sentence `"Please reply with \`CONFIRM-NODE-OP <NODE_ID>\` to proceed"` (where `<NODE_ID>` is the real node identifier). The user reply MUST literally match that token; do not accept softer wording such as `confirm` / `yes` / `proceed` / `go` / `ok`.

   ```
   ⚠️ I am about to perform the following node operation:
   • Operation: <Cordon|Uncordon|Drain>
   • Target node: <NODE_ID>
   • ResourceGroup: <RG_ID>
   • MachineGroup: <MG_ID>
   • Current status: <STATUS>   ← from the pre-op list-nodes call above
   • Resolved parameters: <Cordon/Uncordon/DrainParameters JSON>
   • Impact: <what will happen; for Drain, explicitly warn workloads will be evicted without an upfront pod inventory>

   Please reply with CONFIRM-NODE-OP <NODE_ID> to proceed, or CANCEL to abort.
   Any other reply (yes / ok / proceed / confirm / go ahead) will NOT unlock execution and the prompt will be re-printed.
   ```

3. **[MUST] Wait for the literal token** `CONFIRM-NODE-OP <NODE_ID>` (with the correct node ID) in a subsequent user message.
   - `yes` / `ok` / `confirm` / `go ahead` / `do it` / `proceed` → re-prompt with the template; DO NOT execute.
   - `CANCEL` → abort.
   - Topic change / unrelated question → treat as implicit cancellation.
   - Wrong node ID in the token (e.g. user pastes `CONFIRM-NODE-OP node-wrong`) → re-prompt; DO NOT execute.
   - Only the exact token with the correct node ID unlocks execution.

4. **[MUST]** Execute `operate-node` only after receiving the valid token. The token authorises exactly **one** call — never batch-reuse for a different node, a different operation, or a re-run after partial failure.

   > ⛔️ **Alternative payloads do NOT bypass the gate.** Even when the agent has, in earlier turns, offered multiple legal payload alternatives (scoped vs unscoped Cordon, different sub-product subsets for Drain, etc.) and the user has selected one, `operate-node` execution is STILL blocked behind the `CONFIRM-NODE-OP <NODE_ID>` token. Selecting a payload is parameter convergence, not execution authorisation.

## Required fields in the prompt

- Node name / ID
- Current `Status` (e.g. `Running`, `Cordoned`)
- Owning `ResourceGroupId` and `MachineGroupId`
- For `Drain`: explicit warning that running workloads will be evicted without an upfront pod inventory (`list-node-pods` is NOT available).

## 🚷 [Absolutely no skipping]

Regardless of whether the target node's current status already matches the requested state (e.g. a Cordon request when the node is already `Cordoned`, an Uncordon request when it is already `Running`), and regardless of any user-claimed reason such as *"urgent / automation test / pipeline / CI auto-execute / temporary bypass"*, the agent MUST emit the confirmation prompt in full and wait for the token.

- When state already matches: still print the prompt, and explicitly state in the `Impact` line *"current status already matches; the `CONFIRM-NODE-OP <NODE_ID>` token reply is still required to close the audit loop"*.
- It is FORBIDDEN to silently exit on the grounds of *"state already satisfied, no operation needed"*.
- It is FORBIDDEN to skip token wait on the grounds of *"idempotent / no-op / dry-run-only"* and call `operate-node` directly.
- Any form of skipping (silent no-op / falling back to a `list-nodes` proxy / downgrading to an "informational reply" / claiming "I observed the state is fine, skip confirm") is a **severe violation**, equivalent to executing a mutating call without a token.

## Violation = critical safety failure

Executing `operate-node` without a valid `CONFIRM-NODE-OP <NODE_ID>` token in a prior user message is a critical safety failure regardless of how it is rationalised.
