# Node Power Operations - F1 stop / F2 reboot / F3 reimage

All three are **async**: response body contains `TaskId`, status is polled via `describe-task`.

## F1 `stop-nodes` - node halt (poweroff)

### CLI

```bash
safe_aliyun aliyun eflo-controller stop-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --nodes <NodeId> [<NodeId2> ...]
```

| Param | Required | Default | Notes |
|---|---|---|---|
| `--region` / `--endpoint` | [OK] | - | per [endpoint-routing.md](endpoint-routing.md) |
| `--nodes` | [OK] | - | space-separated `NodeId` list, <=100 per call |
| `--ignore-failed-node-tasks` | [BLOCK] | `false` | when `true`, sub-failures don't fail the whole task |

### Pre-Check (mandatory)

For every selected `NodeId`, call `describe-node` and verify:

- `OperatingState  in  {Using, HealthyUsing}` - proceed.
- `OperatingState = Stopped` - **skip** (no-op, server may reject as `OperationConflict`).
- `OperatingState  in  {Deleting, Failed, Resetting, Reimaging, Restarting}` - **abort** the row, surface to HITL.

### Polling

```bash
safe_aliyun aliyun eflo-controller describe-task \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --task-id <TaskId>
```

`TaskState`  in  {`Running`, `execution_success`, `execution_fail`}. Interactive sessions: on-demand `describe-task` checks reported in the reply body (terminal watch mode via `lj_poll.sh` only on explicit user request); typical duration 5-15 min.

### Verify

```bash
safe_aliyun aliyun eflo-controller describe-node \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId>
# expect: .OperatingState == "Stopped"
```

---

## F2 `reboot-nodes` - OS reboot, state preserved

### CLI

```bash
safe_aliyun aliyun eflo-controller reboot-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> --nodes <NodeId> [<NodeId2> ...]
```

| Param | Required | Default | Notes |
|---|---|---|---|
| `--cluster-id` | optional but recommended | - | server permits omitting; supplying it is faster (fewer cross-cluster lookups) |
| `--nodes` | [OK] | - | <=100 per call |
| `--ignore-failed-node-tasks` | [BLOCK] | `false` | - |

### Pre-Check

`OperatingState  in  {Using, HealthyUsing}` - proceed. `Stopped` - server returns `InvalidNodeStatus`; **must not** retry. Use `start` flow (currently provided implicitly by `reboot-nodes` from `Stopped`? - no, `reboot-nodes` requires running state; route to console for cold-start).

### Verify

`describe-node` `LastBootTime` (or analogous timestamp field) must be later than the pre-call value.

---

## F3 `reimage-nodes` - OS re-install - IRREVERSIBLE

> [STOP] Wipes the system disk on every selected node; **data disks are left untouched by default** (zh canonical wording comes from `render.danger_reimage` / `render.danger_reimage_tail` in `lib/core/i18n.sh`; do NOT claim all on-node data is wiped). The skill **does not** verify backups - that is the user's responsibility.

### CLI

```bash
safe_aliyun aliyun eflo-controller reimage-nodes \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --cluster-id <cid> \
  --nodes Hostname=<h> ImageId=<i> NodeId=<n> [LoginPassword='***'] \
         [Hostname=<h2> ImageId=<i2> NodeId=<n2> [LoginPassword='***']] \
  [--user-data <bash>] [--ignore-failed-node-tasks true|false]
```

### Per-node sub-fields

| Sub-field | Required | Source | Notes |
|---|---|---|---|
| `NodeId` | [OK] | `list-cluster-nodes` HITL pick | - |
| `Hostname` | [OK] | user input or carry over from `describe-node.Hostname` | Linux hostname rules (`[a-z0-9-]+`) |
| `ImageId` | [OK] | `list-images` HITL pick | **`forbidden_inference`** - must come from list output, never from chat history |
| `LoginPassword` |  optional | user input | omit -> node keeps its existing password; **`forbidden_inference`**; rendered as `***` everywhere; when supplied must satisfy Lingjun complexity (8-30 chars, 3 of 4 char classes) |

### Top-level optional

- `--user-data <text>` - bash script run on first boot after reimage.
- `--ignore-failed-node-tasks` - `false` by default.

### Confirmation (mandatory, single step)

The danger box and the parameter confirmation table are shown in **one message**, ending with the closing prompt (see `render.confirm_prompt` in `lib/core/i18n.sh`). Only the explicit language-matched confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`) triggers submission; vague replies (`Yes`, `OK`, blank, a new question, the other language's word) -> [paused] Not Executed.

### Pre-Check

Per node:

- `OperatingState = Stopped` (preferred; reimage from stopped is the standard path)
- `OperatingState = Using` - also accepted; the platform will halt the node first.
- Any other state - abort.

### Polling

On-demand `describe-task` checks reported in the reply body (terminal watch mode via `lj_poll.sh` only on explicit user request); typical 30-45 min total.

### Verify (per node)

```bash
safe_aliyun aliyun eflo-controller describe-node \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id <NodeId>
# expect: .ImageId == requested ImageId
#         .OperatingState == "Using"
```

If `TaskState=execution_success` but `describe-node.ImageId` does **not** match the requested target -> emit a [WARN] partial-success report and surface to HITL.
