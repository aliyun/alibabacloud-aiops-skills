# `operate-node --operation-parameters` Schema & Validation

Backend shape (`OperateNodeBaseRequest.OperationParameters` in [pkg/pai-resource-service/model/node/node.go](file:///Users/shining/Projects/pai-mono/pkg/pai-resource-service/model/node/node.go)):

```json
{
  "DrainParameters":    { "PodNames": ["..."], "PodFromSubProducts": ["DLC"] },
  "CordonParameters":   { "QuotaId": "", "WorkspaceId": "", "Comment": "" },
  "UncordonParameters": { "QuotaId": "", "WorkspaceId": "" }
}
```

Only the sub-object matching the chosen `--operation` is read; omit the others.

## CordonParameters / UncordonParameters

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `QuotaId` | string | paired with `WorkspaceId` | Scope. MUST be set together with `WorkspaceId`. |
| `WorkspaceId` | string | paired with `QuotaId` | Scope. MUST be set together with `QuotaId`. |
| `Comment` | string | optional (Cordon only) | Free-text reason recorded in audit event. |

**Pairing rule** (backend-enforced): `QuotaId` and `WorkspaceId` MUST be provided **together** or **both omitted**. One-without-the-other is rejected with `"both quota id and workspace id should be provided"`.

> 📝 **【强制前置说明 — agent 回复 MUST 显式展开此规则】** 若用户请求只含 `QuotaId` 或 `WorkspaceId` 之一（或在自然语言里只提了 quota 名 / workspace 名而省略另一半），Agent 的 **文本回复** MUST 完整包含以下三段内容，缺一不可：
>
> 1. **自然语言展开配对规则**：明确写出 *"`CordonParameters` / `UncordonParameters` 中的 `QuotaId` 与 `WorkspaceId` 必须配对——两者同时给出（scoped）或两者同时缺省（unscoped），只给一边后端会以 `"both quota id and workspace id should be provided"` 拒绝"*。**不允许**只 link 到本文件 / 只在脚注 / 只在参考目录里一笔带过。
> 2. **给出一个合法完整 payload 备选示例**（既可补齐另一半的 scoped 版，也可两个都去掉的 unscoped 版，二选一或都列），让用户选定一种再继续。示例必须是可直接复制粘贴执行的 JSON，不是占位符。
> 3. **明确告知**："在你选定补齐方式之前，我不会进入 Resolved Plan、不会拼 JSON、不会调 `operate-node`、不会让后端报错"。
>
> 选定备选 ≠ 授权执行：即使用户回复"用第一个备选"或在第二轮把另一半补齐，Agent **MUST** 继续走完 `CONFIRM-NODE-OP <NODE_ID>` 令牌门 (`confirmation-protocol.md`) 才能真正调用 `operate-node`——前置说明 + 备选确认 是 **预备步骤**，不是 **执行授权**。

> ⛔️ **【备选 payload 不等于执行授权】** 即使 Agent 在前置说明中给出多种合法 payload（scoped / unscoped / 不同 Comment / 不同 Sub-product 组合），且用户选定其中一种回复，**`operate-node` 调用依然 MUST 卡在 `CONFIRM-NODE-OP <NODE_ID>` 令牌之后**。备选 payload 只是收敛参数，令牌才解锁执行。任何"用户选了备选 A，所以我直接执行 A"的快捷路径均视为越权。

## DrainParameters

| Field | Type | Required | Semantics |
| --- | --- | --- | --- |
| `PodNames` | `[]string` | optional | Restrict eviction to listed pod names. Empty = all eligible pods. |
| `PodFromSubProducts` | `[]string` | optional | Restrict by sub-product. Allowed: `DLC` / `DSW` / `EAS` / `Tensorboard`. Other values → `"invalid production type"`. |

> 🚫 **`Force` is NOT exposed by this skill — 后端运维白名单管控.**
>
> `DrainParameters.Force` 由 PAI 后端的**运维**白名单（operator allowlist）控制，本 skill **不暴露**该字段、**不接受**用户传入该字段、**不会**在任何 payload 中写出 `"Force": true`。即使用户在 `CONFIRM-NODE-OP` 令牌之后再次要求 Force drain，Agent **MUST** 再次拒绝（令牌只解锁非 Force drain）。
>
> 当用户请求 Force drain（包括 "强制 drain" / "清掉卡住的 Terminating Pod" / "drain --force" / "驱逐失败再强制一次" 等任何变体），Agent 的回复 MUST 明确说明：
>
> 1. **本 skill 不暴露 Force 字段**——非技术原因；这是后端**运维**白名单边界，不是参数缺失。
> 2. **唯一升级路径是以下三选一**（不存在 skill 内 / `kubectl drain --force` / SSH `kill -9` / 节点级直连等任何替代）：
>    - **平台运维团队**（直接联系）
>    - **Lingjun 运维工单**（提交工单走白名单审批）
>    - **账号经理**（由其代为升级到运维侧）
> 3. **此期间本 skill 能做的只读检查 + 常规（非 Force）drain 备选** 仍受 `CONFIRM-NODE-OP <NODE_ID>` 令牌门控（见 `refusal-patterns.md` 中的 few-shot）。
>
> Agent **MUST NOT** 在拒绝段落之外（包括 by-the-way / FYI / 附带提示等任何形式）暗示用户可以自行 `kubectl drain --force` / SSH 进节点清 Pod / 走 `curl` 内部 API 等任何"绕过 skill 边界"的方案。

## CLI examples

```bash
# Cordon — scoped (Quota+Workspace together)
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Cordon \
  --operation-parameters '{"CordonParameters":{"QuotaId":"${QUOTA_ID}","WorkspaceId":"${WORKSPACE_ID}","Comment":"maintenance"}}'

# Cordon — unscoped (omit BOTH)
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Cordon \
  --operation-parameters '{"CordonParameters":{"Comment":"maintenance"}}'

# Uncordon — scoped
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Uncordon \
  --operation-parameters '{"UncordonParameters":{"QuotaId":"${QUOTA_ID}","WorkspaceId":"${WORKSPACE_ID}"}}'

# Drain — evict eligible pods, then cordon
aliyun paistudio operate-node \
  --region "${REGION_ID}" --node-id "${NODE_ID}" --operation Drain \
  --operation-parameters '{"DrainParameters":{"PodFromSubProducts":["DLC","DSW"]}}'
```

**Permission**: `pai:UpdateResourceGroup` on the node's ResourceGroup **OR** `pai:UpdateQuota` on the root Quota (backend OR).
