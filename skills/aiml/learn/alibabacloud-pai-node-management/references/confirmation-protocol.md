# Two-Step Confirmation Gate for `operate-node`

Node operations (`Cordon` / `Uncordon` / `Drain`) are state-mutating. The agent MUST halt at the `operate-node` step and wait for an explicit user token before executing.

## Protocol

1. **[MUST] Pre-operation status query**: call

   ```bash
   aliyun paistudio list-nodes --region "${REGION_ID}" \
     --resource-group-ids "${RG_ID}" \
     --node-names "${NODE_ID}" --page-number 1 --page-size 1
   ```

   并把节点的当前 `Status` / `MachineGroupId` / `ResourceGroupId` 显式写进确认提示。

   > **绝对禁止跳过 pre-op 查询**：即使用户在请求中已声称 *"节点现在是 Running / 已 Cordon / 我刚查过"*，Agent 也 **MUST** 自己查一次——用户自述不是审计可信源，且节点状态在两次对话之间可能已变。无查询直接进入确认提示视为违规。若查询返回 0 节点（节点名拼错 / RG 不对）或 >1 节点（异常），STOP 并要求用户澄清，**不允许** 凭猜测继续。

2. **[MUST] Print the confirmation prompt**, then **end the turn** — do NOT continue in the same turn. The prompt MUST include the literal sentence `"Please reply with \`CONFIRM-NODE-OP <NODE_ID>\` to proceed"`（其中 `<NODE_ID>` 替换为真实节点名）—— **强制要求用户回复该字面令牌**，不允许用 `confirm` / `yes` / `proceed` / `go` / `好的` / `是` 等弱化措辞替代。

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
   Any other reply (yes / ok / 好 / proceed / confirm / go ahead) will NOT unlock execution and the prompt will be re-printed.
   ```

3. **[MUST] Wait for the literal token** `CONFIRM-NODE-OP <NODE_ID>` (with the correct node ID) in a subsequent user message.
   - `yes` / `ok` / `确认` / `go ahead` / `do it` / `proceed` / `好的` → re-prompt with the template; DO NOT execute.
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

## 🚷【绝对禁止跳过】

无论目标节点当前状态是否已符合预期（例如 Cordon 请求时节点已是 `Cordoned`、Uncordon 请求时节点已是 `Running`），也无论用户是否声明 *"紧急 / 自动化测试 / 流水线 / CI 自动执行 / 临时绕过"* 等任何理由，Agent 都 **MUST** 完整输出上述确认提示并等待令牌。

- 若状态已满足：仍需输出提示，并在 `Impact` 段明确说明 *"当前状态已符合，但仍需您回复 `CONFIRM-NODE-OP <NODE_ID>` 以完成审计闭环"*。
- **严禁** 以 *"状态已满足，无需操作"* 为由静默退出而不打印确认提示。
- **严禁** 以 *"幂等 / no-op / dry-run-only"* 为由跳过令牌等待，直接调用 `operate-node`。
- 任何形式的跳过（静默 no-op / 改走 `list-nodes` 替代 / 降级为"信息性回复" / 声称"已观察到状态符合，跳过确认"）均视为 **严重违规**，等同于无令牌执行 mutating 调用。

## Violation = critical safety failure

Executing `operate-node` without a valid `CONFIRM-NODE-OP <NODE_ID>` token in a prior user message is a critical safety failure regardless of how it is rationalised.
