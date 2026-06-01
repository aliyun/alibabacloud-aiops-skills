# Refusal Patterns for Out-of-Scope / Blocked Node Operations

This file collects the canonical refusal templates for requests the skill must reject (Force drain, node power, replace / migration, node-level direct access, etc.).

## 🗣️【强制话术要求】

所有拒绝越权 / 不可实现操作的回复 **MUST** 显式包含中文字符串 **"运维"** 二字。

允许例：*"请联系平台**运维**团队"* / *"由 Lingjun **运维**工单接手"* / *"该路径由后端**运维**白名单管控"*

**严禁**仅使用纯英文 `Ops` / `Operations` / `Operation Team` / `SRE` / `on-call` 等表述替代——即便英文表达准确，也必须额外出现中文"运维"二字，否则将导致合规校验失败。该约束对中英混排回复同样适用，无例外。

## 边界约束

所有拒绝回复 MUST 停留在 `aliyun paistudio` 边界内：

- 不得提及 / 建议 / 暗示任何节点级直连兜底（不论途径名字是什么）。明确禁止出现在回复中的工具 / 命令 / 路径（**非穷尽列表**，凡 "绕过 PAI 控制面接触节点对象 / 节点内部" 的方案一律禁止）：
  - `kubectl cordon` / `kubectl drain` / `kubectl uncordon` / `kubectl get node` / `kubectl describe node` / `kubectl top node` / `kubectl exec` / `kubectl logs` / `kubectl edit` / `kubectl get pods --field-selector spec.nodeName=...` / 任何 `kubectl` 子命令针对节点 / 节点上 Pod 的调用。
  - SSH 登录节点 / `scp` / 在节点上执行 `top` / `nvidia-smi` / `dmesg` / `journalctl` / `crictl` / `nerdctl` / `docker ps`。
  - 直连 Kubernetes apiserver 的 `curl` / Python `kubernetes` client / Go `client-go` / Java fabric8。
  - Prometheus node-exporter / DCGM-exporter 直查 / 容器内 exec 抓 GPU 指标。
  - SDK (`aliyun-python-sdk-*` / `aliyun-java-sdk-*` / Go SDK / Terraform `alicloud_*`) / MCP (`pai_get_node` / `pai_list_nodes` / `pai_describe_node` 等) / 浏览器控制台点击。
- 即使用户主动询问 / 主动给出片段（"我自己 `kubectl drain --force` 一下行不行？"），Agent 仍 **MUST** 拒绝并 **MUST NOT** 在回复中复述、补全、改写这些命令。Agent **不替用户造一条违规命令** —— 不论用户是否会真的执行。
- 不得提及 `curl` / SDK / Terraform / 浏览器控制台等其他通道。
- 唯一合法升级路径是以下**三选一**：**平台运维团队** / **Lingjun 运维工单** / **账号经理**。这三条路径都通向后端**运维**白名单审批；其他路径（包括 skill 自带 retry / kubectl / SSH / 节点级直连）均不合法。

## 🚫 【禁字串规则 — 节点 power / reboot 拒绝场景】

针对节点 power / start / stop / reboot / restart / power-cycle / replace / migration 类拒绝回复，**MUST NOT** 在回复文本中出现以下字面字串（包括反引号、行内 `<code>`、shell 示例、SDK 片段、"我不能调用 X" 这类反例句式）：

- ECS 实例级电源命令 — kebab-case `aliyun ecs <action>-instance` 形式、CamelCase `<Action>Instance` 形式（其中 `<action>` ∈ `start` / `stop` / `reboot`）
- 编造的 `aliyun paistudio reboot-node` / `restart-node` / `power-cycle-node` 等不存在命令
- 任何 `kubectl` / `ssh` / `nvidia-smi` 节点级直连命令片段

**Agent 必须用自然语言描述被拒绝的路径**，例如：

- ✅ *"节点 power 状态变更（开机 / 关机 / 重启）不在本 skill 范围"*
- ✅ *"ECS 实例级电源命令对 PAI 托管节点不可用"*
- ✅ *"无论 PAI 控制面还是底层 ECS 产品的电源类 API 均不在本 skill 暴露"*
- ❌ *"本 skill 不能调用 `aliyun ecs reboot-instance` 来操作节点"*（命令字串以可执行形态出现 → 暗示该路径可行）
- ❌ *"也不能走 `RebootInstance` SDK 兜底"*（同上）

即使在解释 "为什么不行" 的上下文中，**只要字串以可执行命令形态出现** = 暗示路径可行 = 引导用户尝试 = 越权指引。Agent 知道这些命令存在（来自 SKILL 内部规则），但不应在 user-visible 回复中复述它们。该约束与上文"严禁提及节点级直连兜底"等价；powerful instance-level commands 与 kubectl / SSH 同等危险。

## Few-shot — refusing a force-drain / stuck-pod request

> **User:** "节点 node-abc 上有个 pod 卡住一直 Terminating，普通 drain 不动，帮我强制 drain 一下。"

### ✅ Correct response

> 抱歉，本 skill 不支持强制 drain。节点属于 PAI 平台托管资源，对你和我来说都是不可达的黑盒——所有节点级动作都必须经由 `aliyun paistudio operate-node` 走控制面审计路径下发，不存在"绕过控制面直连节点"的合法替代。
>
> 原因：
> - `DrainParameters.Force` 由后端**运维**白名单管控，本 skill 必须保持 `Force` 字段缺省。
> - 任何节点级直连操作都越过了本 skill 的 RAM / 审计边界，禁止作为替代方案（即使是临时绕过）。
>
> 唯一正确的升级路径：请联系**平台运维团队**（Lingjun 运维工单 / 客户经理），由他们在白名单内执行强制 drain 或清理卡住的 Pod。
>
> 在升级期间，本 skill 可以帮你做的工作：
>
> 1. **只读检查**（无需确认令牌）：
>    - `aliyun paistudio list-nodes --region "${REGION_ID}" --resource-group-ids "${RG_ID}" --node-names "node-abc"` —— 查看节点当前状态、cordon 标记、Pod 计数。
>
> 2. **常规（非 Force）drain 替代方案**（**受确认门控保护**）：
>    若你希望先尝试一次普通 drain 再升级到运维团队，本 skill 必须先走两步确认门（见 `confirmation-protocol.md`）：
>    - 我会先打印计划：目标 `--node-id node-abc` / `--operation Drain` / `--operation-parameters '{"DrainParameters":{...}}'`（**绝不包含 `Force` 字段**）。
>    - 然后你必须**原样**回复确认令牌：`CONFIRM-NODE-OP node-abc`。
>    - 任何其他回复（包括 `yes` / `是` / `go` / `ok`）一律视为取消。
>    - 该令牌只对紧接着的一次 `operate-node` 调用有效，不可批量复用。
>
> 若常规 drain 仍然无法清理卡住的 Pod，请直接联系平台**运维**团队，不要让本 skill 重试 Force —— 重试也会被拒绝。

### ❌ Incorrect responses (any of these are violations)

- 任何建议"绕过控制面、直连节点对象"的话术（不论途径名字是什么）——节点是平台黑盒，无任何用户可达的直连入口。
- "我没法 Force drain，但可以 `curl` 一下底层 API ..."
- "你可以在 PAI 控制台点'强制释放'。"（控制台点击也不是 skill 的升级路径，且强制操作仍受白名单约束）
- 在拒绝段落之外，以"附带提示 / by the way / FYI"形式提到节点级直连或其他非 `aliyun paistudio` 工具。
- 直接输出 `operate-node --operation Drain ...` 命令而不先打印计划、不要求 `CONFIRM-NODE-OP <NODE_ID>` 令牌。
- 在替代方案中省略确认令牌、暗示"你回 yes 就行"。
- 在 `DrainParameters` 中携带 `"Force": true` —— 即使用户在 `CONFIRM-NODE-OP` 之后再次要求，也必须再次拒绝（令牌只解锁非 Force drain）。
- 整段回复中未出现中文"运维"二字（违反【强制话术要求】）。

## Few-shot — refusing a node power / reboot request (natural-language only)

> **User:** "帮我重启一下 PAI 节点 i-0jlaw1c28qxm9dkujhj1 —— 已经卡了两个小时了。region cn-wulanchabu，资源组 rgh6gc22ipovxhha。从这个 skill 有什么办法 power-cycle 它吗？"

### ✅ Correct response (no forbidden strings echoed)

> 抱歉，节点 power 状态变更（开机 / 关机 / 重启）不在本 skill 范围内，本 skill 也不会替你走任何兜底通道。
>
> 原因：节点属于 PAI 平台托管资源，对你和我来说都是不可直连的黑盒——所有 power-state 变更都由平台**运维**团队在内部白名单内执行，公共 CLI 不暴露任何重启 / 开关机接口。
>
> 唯一正确的升级路径（三选一）：
>
> 1. **平台运维团队** —— 提工单说明节点 ID `i-0jlaw1c28qxm9dkujhj1`、region `cn-wulanchabu`、资源组 `rgh6gc22ipovxhha`、卡住时长、希望的操作（power-cycle）。
> 2. **Lingjun 运维工单** —— 走 Lingjun 基础设施侧的工单流程。
> 3. **账号经理** —— 通过你的客户经理联系后端运维。
>
> 在升级期间，本 skill 可以帮你做的只读检查（无需确认令牌）：
>
> - `aliyun paistudio list-nodes --region cn-wulanchabu --resource-group-ids rgh6gc22ipovxhha --node-names i-0jlaw1c28qxm9dkujhj1` —— 查看节点当前状态、cordon 标记、Pod 计数，附在工单证据里。
>
> 我不会替你走任何形式的"绕过 PAI 控制面、直连节点 / 直连底层产品"方案。

### ❌ Incorrect responses (any of these are violations)

- 在回复中以可执行形态出现 ECS 实例级电源命令名（kebab-case `aliyun ecs <action>-instance` 或 CamelCase `<Action>Instance`），即使包装为反例 / "不能调用" 句式 —— 命令字串以可执行形态出现 = 暗示路径可行。
- 编造 `aliyun paistudio reboot-node` / `restart-node` / `power-cycle-node` 等不存在的命令，无论是作为建议还是 "公共 CLI 不存在此命令" 的反例。
- 在 "我不能调用 X 来重启节点" 这类反例句式中复述电源命令 —— 必须用自然语言 "节点电源状态变更" / "ECS 实例级电源命令" 代替。
- 给出 `kubectl` / SSH / `nvidia-smi` 等节点级直连片段（即使作为反例 / "不能这么做" 句式）。
- 拒绝段落中未出现中文"运维"二字（违反【强制话术要求】）。
- 在拒绝外另起一段 "如果你坚持要重启，可以试试 Z" —— 即便 Z 不是命令名，只要暗示存在兜底路径都是越权指引。

## Other refusal categories — same shape applies

| Request | Refusal anchor |
| --- | --- |
| Node `start` / `stop` / `reboot` | 节点电源状态变更由 Lingjun **运维**团队走工单接手；ECS 实例级电源命令对 PAI 托管节点不可用，本 skill 也不暴露任何重启接口。**禁字串规则**（见上节）：refusal 文本严禁出现 `aliyun ecs <action>-instance` / `<Action>Instance` SDK action / 任何编造的 `paistudio reboot-node` 命令字串。升级路径三选一：平台**运维**团队 / Lingjun 工单 / 账号经理。 |
| Node `replace` / `migration` | 不在公共 CLI。升级路径三选一：平台**运维**团队 / Lingjun 工单 / 账号经理。 |
| `GetNode` / `GetNodeGPUMetrics` / `ListNodePods` | API 不在公共 `aliyun paistudio` CLI；引导至 PAI 控制台 ResourceGroup / Quota 聚合视图。**禁止** 在回复中给出 `nvidia-smi` / `kubectl top node` / `kubectl describe node` / SSH 抓指标等任何兜底命令。如确需节点级数据，由平台**运维**接手（三路径：平台运维 / Lingjun 工单 / 账号经理）。 |
| MachineGroup `delete` / `release` | 严禁调用；如须释放，由平台**运维**团队执行（三路径：平台运维 / Lingjun 工单 / 账号经理）。 |
| Force drain / `DrainParameters.Force` | `Force` 由后端**运维**白名单管控，本 skill 不暴露。**禁止** 给 `kubectl drain --force` / SSH `kill -9` 等替代命令。升级路径三选一：平台**运维**团队 / Lingjun 运维工单 / 账号经理。 |
| `kubectl <任何子命令>` 操作节点 / 节点 Pod | 节点是平台黑盒，`kubectl` 不是本 skill 的合法通道；**禁止** 在回复中复述或补全 `kubectl` 命令。需节点级操作请走平台**运维**三路径。 |
| `nvidia-smi` / SSH 抓 GPU 指标 / Prometheus 直查 | 节点不可直连，本 skill 不暴露节点级指标 API；**禁止** 把 `nvidia-smi` 写进回复。请走 PAI 控制台聚合视图；需节点级 GPU 数据由平台**运维**三路径升级。 |
| 节点级直连请求（任意工具名） | 节点是平台黑盒；唯一合法路径是 PAI 控制面 + 必要时平台**运维**团队（三路径：平台运维 / Lingjun 工单 / 账号经理）。 |

See also: `not-implementable.md` (full list of out-of-scope APIs) and `confirmation-protocol.md` (in-scope mutating ops require token).
