# Parameter Confirmation Templates

> Every mutating CLI **must** go through the `safe_mutate` two-phase commit + the unified confirmation word (session-language dependent: zh session uses the zh confirmation word defined below, en session "confirm") before submission. This file gives the confirmation-table skeleton for each action.

---

## General rules

1. Every confirmation table must be built from real HITL-collected values; it is **strictly forbidden** to let the LLM auto-fill any `forbidden_inference` field.
2. Sensitive parameters (`LoginPassword` / AK etc.) are rendered as `******`; the real value lives only inside the single quotes of the CLI.
3. **Parameter-name localization (MANDATORY in zh sessions)**: in zh sessions (`LJ_LANG=zh`):
   - **Confirmation table**: parameter names are rendered per the mapping table below as **pure Chinese** (Chinese name only, **no** English parenthetical - write the pure Chinese name, not the Chinese-name-plus-English form).
   - **Result displays** (submission receipt, polling progress, diagnostic report including table header columns, error reports): keep the Chinese-name-plus-original format so users can reconcile with API fields.
   - Parameter **values** (IDs / enums / timestamps) are never translated; **single exception**: node state (`OperatingState`) in zh sessions must be translated to Chinese per the authoritative table [node-state-i18n.md](node-state-i18n.md) (e.g. `Using` renders as its zh literal from that table); states not listed in the table stay English; script/jq decision logic still compares the raw English values - translation happens only at the rendering layer. En sessions keep the original parameter names and English states. A Chinese display mixing in untranslated parameter names is a rendering violation and must be regenerated.
4. **Exclusion rules**: derived parameters (`Endpoint`, derived from Region) and optional parameters kept at their default value (e.g. `IgnoreFailedNodeTasks=false`) **do not enter the confirmation table** - `Endpoint` appears only inside the full-CLI line of the confirmation table; an optional parameter is shown only when the user explicitly sets a non-default value.
5. The user-facing confirmation word **follows the session language**: zh session (`LJ_LANG=zh`) uses the zh confirmation word given in the code block below, en session (`LJ_LANG=en`) uses **"confirm"**:
   - After Phase 1 renders the confirmation table, the prompt follows the session language: zh sessions ask the user to reply the zh confirmation word to submit; en sessions: "If everything checks out, reply \"confirm\" to submit; to modify parameters or abort, just let me know." (zh canonical wording lives in SKILL.md).
   - Internal terms such as hash / token / Phase are **forbidden** in user-facing output; after receiving the confirmation word the Agent executes the submission internally.
   - The `reimage-nodes` confirmation table must include the [WARN] system-disk wipe, irreversible warning line; the user's confirmation word counts as acknowledgement of that risk.
   - Any input other than the confirmation word of the current session language (`yes` / `OK` / empty enter / near-miss spellings / the confirmation word of the other language, etc.) is **not** accepted -> abort immediately and produce a [PAUSE] Not Executed report.

```bash
zh confirmation word: 「确认」
en confirmation word: confirm
```

---

## Parameter-name Chinese mapping table (MANDATORY in zh sessions)

This table is the single authoritative translation source; free improvisation is forbidden (same source as the node-ops skill table). **The confirmation table uses only the "Chinese name" column** (no English parenthetical); result displays such as the diagnostic report use the Chinese-name-plus-original format:

```bash
| Original | Chinese | Original | Chinese |
|---|---|---|---|
| Action | `操作` | Region | `地域` |
| ClusterId | `集群 ID` | ClusterName | `集群名` |
| NodeId | `节点 ID` | HyperNodeId | `超节点 ID` |
| Hostname | `主机名` | MachineType | `机型` |
| OperatingState | `当前状态` | Targets | `目标节点` |
| ResourceType / Type | `资源类型` | DiagnosticType | `诊断类型` |
| DiagnosticId | `诊断任务 ID` | AiJobLogInfo | `AI 作业日志信息` |
| ImageId | `镜像 ID` | LoginPassword | `登录密码` |
| UserData | `自定义数据` | IgnoreFailedNodeTasks | `忽略失败节点任务` |
| Reason | `报修原因` | IssueCategory | `故障类别` |
| StartTime | `开始时间` | EndTime | `结束时间` |
| Description | `故障描述` | RequestId | `请求 ID` |
| Reversible | `可逆性` | CLI | `完整 CLI` |
| Status | `任务状态` | DiagResult / Verdict | `诊断结论` |
| CreationTime | `提交时间` | FinishedTime | `完成时间` |
| Duration | `总耗时` | CheckItem | `检查项` |
| ErrorCode | `错误码` | ErrorMessage | `错误信息` |
| FaultDescription | `故障描述` | Suggestion | `修复建议` |
| Nodes / NodeIds | `节点列表` | Polling | `轮询方式` |
| ReportId | `报障 ID` | CreateTime / FinishTime | `报障创建时间 / 完成时间` |
```

---

## Confirmation-table templates

The templates below show the en-session layout. In zh sessions every field label is rendered as pure Chinese per the mapping table above (e.g. `Region` renders as its zh label from that table), and the footer prompt uses the zh wording with the confirmation-word token.

## 1. create-diagnostic-task confirmation table

```
🛑 About to submit a diagnostic task (mutating)

┌────────────────────────────────────────────────────────────────┐
│ Region              : cn-hangzhou                                │
│ Cluster ID          : <cid>                                      │
│ Diagnostic Type     : BasicCheck                                 │
│ Target Nodes (1)    :                                            │
│   - Type=Node  NodeId=e01-cn-xxx  Hostname=node-001              │
│ AI Job Log Info     : — (only required for CheckByAiJobLogs)   │
└────────────────────────────────────────────────────────────────┘

Full CLI: aliyun eflo-controller create-diagnostic-task --endpoint ... --region ...

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

---

## 2. reboot-nodes confirmation table

```
🛑 About to reboot nodes (reversible mutating)

┌────────────────────────────────────────────────────────────────┐
│ Action              : reboot-nodes                               │
│ Region              : cn-hangzhou                                │
│ Cluster ID          : <cid>                                      │
│ Target Nodes (1)    :                                            │
│   - NodeId=e01-cn-xxx  Hostname=node-001  MachineType=efg1.nvga1│
│ Reversibility       : ✅ back to Using ~5–10 min after reboot    │
└────────────────────────────────────────────────────────────────┘

⚠️ Impact: AI Jobs running on the node(s) will be interrupted.

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

---

## 3. reimage-nodes confirmation table (destructive, with system-disk wipe warning)

```
🛑 About to reimage nodes (⚠️ system disk wiped, irreversible)

┌────────────────────────────────────────────────────────────────┐
│ Action              : reimage-nodes                              │
│ Region              : cn-hangzhou                                │
│ Cluster ID          : <cid>                                      │
│ Target Nodes (1)    :                                            │
│   - NodeId=e01-cn-xxx  Hostname=node-001                        │
│     ImageId=<imgid>  ← forbidden_inference (HITL-selected)       │
│     LoginPassword=******                                         │
│ User Data           : —                                          │
│ Reversibility       : ❌ system-disk data permanently erased     │
└────────────────────────────────────────────────────────────────┘

⚠️⚠️⚠️ DESTRUCTIVE: all user-space directories, ephemeral images, and checkpoints
   on the system disk are lost. Mounted data disks / NAS / OSS are unaffected.

Reply "confirm" to submit ("confirm" counts as acknowledgement of the wipe risk above); any other input cancels.
```

---

## 4. stop-nodes confirmation table (no ClusterId)

```
🛑 About to stop nodes (reversible mutating)

┌────────────────────────────────────────────────────────────────┐
│ Action              : stop-nodes (note: CLI has no --cluster-id) │
│ Region              : cn-hangzhou                                │
│ Target Nodes (2)    :                                            │
│   - NodeId=e01-cn-xxx  Hostname=node-001                        │
│   - NodeId=e01-cn-yyy  Hostname=node-002                        │
│ Reversibility       : ✅ (restart requires console start-nodes) │
└────────────────────────────────────────────────────────────────┘

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

---

## 5. report-node-status confirmation table

```
🛑 About to report node anomaly (the platform creates a fault report and spawns deep diagnosis)

┌────────────────────────────────────────────────────────────────┐
│ Action              : report-node-status                       │
│ Region              : cn-hangzhou                              │
│ NodeId              : e01-cn-xxx  Hostname=node-001            │
│ Diagnosis Type      : COMPREHENSIVE                            │
│ Fault Description   : "GPU0 reported HBM ECC=128"              │
└────────────────────────────────────────────────────────────────┘

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```
