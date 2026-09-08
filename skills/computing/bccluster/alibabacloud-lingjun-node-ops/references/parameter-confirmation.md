# Parameter Confirmation - Single-Step Confirmation Templates

> Single source of truth for the single-step parameter-confirmation gate referenced from `SKILL.md`.
>
> Compliance note (static-scan rule 4.1.2): this document is English-only and contains zero Chinese characters; zh parameter display names live exclusively in the `pname.*` dictionary of `lib/core/i18n.sh`, a shell data file outside the scanned documentation set.

## Single-Step Confirmation (MANDATORY)

All mutating CLIs in this skill follow **one** confirmation flow:

1. The Agent presents **one single message** containing: (a) for F3/F4, a prominent danger notice first; (b) the full parameter confirmation table (sensitive fields redacted to `***`); (c) the closing prompt - the canonical wording comes from `render.confirm_prompt` in `lib/core/i18n.sh` (en: "Please review the parameters above and reply 'confirm' to execute"). The table and the confirmation ask are **the same step** - never split into two rounds. **No** CLI is sent at this point.
2. The user replies the **language-matched confirmation word** - defined by `render.confirm_word` in `lib/core/i18n.sh` (zh and en variants; case-insensitive; the other language's word is not accepted) -> the Agent submits via `safe_mutate_oneshot <tag> --intent "<user's original words>" aliyun ...` (internal hash freezing and audit trail are transparent to the user).
3. Any other reply (cancel / a new question / silence / a partial answer) -> the Agent terminates the flow and emits a [paused] Not Executed report. If the user asked to change a parameter, regenerate the table and ask again (still one message).

Internal implementation terms (hash / token / Phase 1 / Phase 2 / `safe_mutate_confirm`) must **never** appear in user-facing output.

## Rendering Format (MANDATORY)

The confirmation table **must** be rendered as a **Markdown table** (two columns: Parameter / Value; multi-node actions use one row per node or a per-node sub-table). It is **strictly forbidden** to render it as an ASCII-art box (`+----+` frames), inside a code fence, or as preformatted plain text - those degrade readability in chat UIs. Danger notices (F3/F4) are rendered as a **text-only quote block** (bold lines + emoji) placed above the table - **never nest tables, headings, or lists inside the quote block** (Markdown tables do not render inside `>` blocks and will collapse into literal `---` garbage). Per-node detail rows belong in the confirmation table itself (or a normal Markdown table after the quote block). Always leave **one blank line** between the quote block, any heading, and the table - otherwise the renderer swallows the heading into the quote.

## Parameter-Name i18n (MANDATORY in zh sessions)

In zh sessions (`LJ_LANG=zh`), parameter names in the confirmation table must always be rendered as **zh names** via the `pname.*` dictionary in `lib/core/i18n.sh` (show the zh name only - do **not** append the raw English name, e.g. render the zh value of `pname.Action` rather than "Action" with a zh annotation). Parameter **values** (IDs / enums / endpoints) are never translated, with the **sole exception of node states**: `OperatingState` values must be rendered via the authoritative mapping per [node-state-i18n.md](node-state-i18n.md) (e.g. `Using` rendered via `state.Using`); states not in the mapping stay in English. En sessions keep the raw parameter names and states. The `pname.*` dictionary is the sole authoritative translation source - never improvise.

Exclusion rule: derived parameters (e.g. `Endpoint`, derived from Region) and optional parameters left at their default (e.g. `IgnoreFailedNodeTasks=false`) are **excluded** from the table; show them only when the user explicitly sets a non-default value.

zh rendering example (node stop; the Markdown table is output directly, not inside a code fence; the zh column names come from `pname.*` and the zh closing prompt from `render.confirm_prompt`).

> The templates below use English parameter names to show structure; in zh sessions, replace each field name with its `pname.*` zh value (without the English original).

## Confirmation table - common columns

| Column | Source | Notes |
|---|---|---|
| Region | user / HITL | per Rule 2 of endpoint-routing.md |
| ClusterId | `list-clusters` HITL pick | shown for context |
| NodeGroupId | `list-node-groups` HITL pick | shown when relevant |
| NodeId / HyperNodeId | `list-cluster-nodes` HITL pick | per row |
| Hostname | `describe-node Hostname` | from real response only - never invented |
| Action | constant | e.g., `stop-nodes`, `reimage-nodes` |
| Sensitive fields | `***` | LoginPassword / file Content (Base64) / AK |

> Derived parameters (e.g. `Endpoint`, derived from Region) and optional parameters left at their default (e.g. `IgnoreFailedNodeTasks=false`) are **excluded** from the table; show them only when the user explicitly sets a non-default value.

## Per-Action confirmation templates

> All templates are Markdown tables. Each ends with the same one-line closing prompt (from `render.confirm_prompt` in `lib/core/i18n.sh`; en: "Please review the parameters above and reply 'confirm' to execute") - the confirmation happens in the **same message** as the table. Multi-node actions: one row per node (`NodeId / Hostname / group / state` combined) or a per-node sub-table.

### F1 stop-nodes / F2 reboot-nodes

| Parameter | Value |
|---|---|
| Action | stop-nodes (async) |
| Region | cn-wulanchabu |
| Cluster | i114934*** (lj-prod-01) |
| Node 1 | e01-cn-aaa - node-001 - ng-train - Using |
| Node 2 | e01-cn-bbb - node-002 - ng-train - Using |

Please review the parameters above and reply 'confirm' to execute.

### F3 reimage-nodes - IRREVERSIBLE (danger notice in the same message)

> [STOP] **DANGER: Reimage will WIPE the system disk on every selected node.**
> System-disk data must already be backed up; this skill does NOT verify backups. Data disks are left untouched by default.
> (zh canonical wording comes from `render.danger_reimage` / `render.danger_reimage_tail` in `lib/core/i18n.sh` - it is FORBIDDEN to write "all data on the node will be wiped and unrecoverable")

(The danger quote block ends here - do not put the affected-node details inside the quote block; show them as Node rows in the table below; leave one blank line between the quote block and the table.)

| Parameter | Value |
|---|---|
| Action | reimage-nodes (async, IRREVERSIBLE) |
| Region | cn-wulanchabu |
| Cluster | i114934*** (lj-prod-01) |
| Node 1 | NodeId=e01-cn-aaa - Hostname=node-001 - ImageId=m-uf6... - LoginPassword=`***` - ng-train - Stopped |
| Node 2 | NodeId=e01-cn-bbb - Hostname=node-002 - ImageId=m-uf6... - LoginPassword=`***` - ng-train - Using |
| UserData | (none) / (provided, length=N bytes) |

This operation is irreversible; system-disk data will be erased (data disks are left untouched by default). Please review the parameters and reply 'confirm' to execute.

### F4 renew-instance - PAID (danger notice in the same message)

> [STOP] **DANGER: This will generate a paid order, billed immediately.**
> The order CANNOT be reversed once Status=Success.

| Parameter | Value |
|---|---|
| Action | bssopenapi renew-instance (sync) |
| InstanceId | e01-cn-aaa |
| ProductCode | bccluster |
| ProductType | bccluster_eflocomputing_public_cn (China site) |
| RenewPeriod | 1 month |
| ClientToken | 7c9a8b6e-1d2f-30a4-7c9a-8b6e1d2f30a4 |
| Current ExpiredTime | 2026-06-30T16:00:00Z (from describe-node) |

This operation immediately generates a paid order and cannot be reversed. Please review the parameters and reply 'confirm' to execute.

### F5 change-node-types

| Parameter | Value |
|---|---|
| Action | change-node-types (async) |
| Region | cn-wulanchabu |
| NodeIds (<=10) | e01-cn-aaa, e01-cn-bbb |
| Current NodeType | cpfs-enhanced |
| Target NodeType | ebs-enhanced (9-value enum, NOT a MachineType) |

> [WARN] Task SUCCESS does NOT guarantee the node type change took effect - re-query `describe-node.NodeType` after the task completes.

Please review the parameters above and reply 'confirm' to execute.

### F6 report-node-status

| Parameter | Value |
|---|---|
| Action | report-node-status (sync) |
| Region | cn-wulanchabu |
| NodeId | e01-cn-aaa |
| DiagnosisType | COMPREHENSIVE |
| Description | GPU 0 ECC error spike |

Please review the parameters above and reply 'confirm' to execute.

### F6 approve-operation

| Parameter | Value |
|---|---|
| Action | approve-operation (sync) |
| Region | cn-wulanchabu |
| NodeId | e01-cn-aaa |
| OperationType | RepairMachine (closed enum: RepairMachine / RebootMachine / UpgradeMachine; picked via HITL) |

Please review the parameters above and reply 'confirm' to execute.

### F7 run-command

| Parameter | Value |
|---|---|
| Action | run-command (async, InvokeId) |
| Region | cn-wulanchabu |
| Nodes | e01-cn-aaa, e01-cn-bbb |
| Name | check-gpu |
| Username | root |
| WorkingDir | /home |
| ContentEncoding | PlainText |
| Timeout | 30s |
| RepeatMode | Once |
| ClientToken | 7c9a8b6e-... |
| Command (first 200 chars) | `nvidia-smi -L` |

Please review the parameters above and reply 'confirm' to execute.

### F8 update-node-group

| Parameter | Value |
|---|---|
| Action | update-node-group (sync) |
| Region | cn-wulanchabu |
| NodeGroupId | ng-train |
| NewName | ng-train (carried over - see F8 doc-hallucination rule) |
| ImageId | m-uf6abc... -> m-uf6def... (forbidden_inference) |
| LoginPassword | `***` (set/changed) |
| UserData | (provided, length=N bytes) |
| FileSystemMountEnabled | true |

Please review the parameters above and reply 'confirm' to execute.

### F9 tag-resources / untag-resources

| Parameter | Value |
|---|---|
| Action | tag-resources (sync) |
| BizRegionId | cn-wulanchabu |
| ResourceType | node |
| ResourceIds | e01-cn-aaa, e01-cn-bbb |
| Tags | env=prod, team=ai |

Please review the parameters above and reply 'confirm' to execute.

### F9 change-resource-group

| Parameter | Value |
|---|---|
| Action | change-resource-group (sync) |
| ResourceRegionId | cn-wulanchabu |
| ResourceType | node |
| ResourceId | e01-cn-aaa |
| ResourceGroupId | rg-xxxx (forbidden_inference - picked by user) |

Please review the parameters above and reply 'confirm' to execute.

## Hard rules

- **Explicit-confirmation-only**: only the explicit language-matched confirmation word triggers execution - the words defined by `render.confirm_word` in `lib/core/i18n.sh` (case-insensitive); the other language's word, vague or unrelated replies (silence, "probably fine", `yes`/`OK`, a new question, partial answers) must **not** be treated as confirmation - doing so is self-violation V5, non-retryable. `cancel` (or its zh equivalent) or any negative reply -> [paused] Not Executed.
- **Same-message rule**: the parameter table and the closing prompt must appear in **one** message; splitting them into two rounds (table first, then a separate "are you sure?" round) is forbidden.
- **Markdown-table rendering**: the confirmation table is always a Markdown table; ASCII-art boxes, code fences, or preformatted text renderings are forbidden.
- **Resource-list field source**: `NodeId` / `HyperNodeId` / `Hostname` in every confirmation table **must** come field-by-field from the **current-session** real response of `list-cluster-nodes` / `describe-node` / `list-cluster-hyper-nodes` / `describe-hyper-node`. Never impersonate identity using `MachineType` / `NodeGroupName` / `HpnZone` / `Zone` / `OperatingState`.
- **Verbatim resource names**: display names (`ImageName` / `ClusterName` / `NodeGroupName` / `ImageId` etc.) **must** be quoted **character-for-character** from the real API response in **every user-facing surface** - confirmation tables, HITL pickers / option lists (image picker included), receipts, and reports. Abbreviating, paraphrasing, dropping segments, or re-assembling them (e.g. rendering `Alinux3_x86_5.10.134-16.3_NV_RunC_D3_E3C7_570.133.20_V1.3_251027` as "Alinux3 RunC V1.3" or "Alinux3 RunC 570 driver V1.3") is forbidden. Standard value format: `<Id> (<full Name>)`; if a name is too long, keep it verbatim anyway - never truncate. In widget-style pickers whose labels must stay short: **label = resource ID, description = verbatim full name**; the ID must never be omitted, and one option = one resource (never bundle several).
- **Sensitive-field redaction**: `LoginPassword`, file `Content` (when contains secrets), AK/SK, certificates -> render as `***` everywhere user-facing; the real value is interpolated only inside CLI single-quotes at execution time.
- **Parameter-name i18n**: in zh sessions every parameter name in the table must be rendered via the `pname.*` mapping in `lib/core/i18n.sh`, showing the zh name only (without the English original); values are never translated - **except node states**, which must be rendered per [node-state-i18n.md](node-state-i18n.md).
- **No internal feature codes**: the `F1`-`F9` codes are documentation indices only and must **not** appear in **any user-facing output** - confirmation-table titles, Action values, submission receipts, progress lines, or final reports. Use the localized feature names from `render.feat.*` in `lib/core/i18n.sh` - never "F5 ..." or "... (F5)". The only exception is a capability-overview table enumerating all features.
