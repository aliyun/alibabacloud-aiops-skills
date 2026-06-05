# Async Tasks in ACK CLI

Most ACK write operations are **asynchronous**: the `aliyun cs <verb> ...`
command returns within seconds with a task envelope, but the actual work
(provisioning, scaling, upgrading, addon install) continues in the
ACK control plane for minutes to hours. To know whether the work succeeded
you must poll the task.

This document explains the lifecycle, response shapes, polling strategy,
and how to interpret failures — read this whenever the user is doing
anything that mutates ACK state.

## Which operations return a task

| Operation | Async? | Typical duration |
| --------- | ------ | ---------------- |
| `create-cluster` | ✅ | 8–20 min |
| `delete-cluster` | ✅ | 3–10 min |
| `upgrade-cluster` (control plane) | ✅ | 10–30 min |
| `pause-task` / `resume-task` / `cancel-task` (act on the `task_id` returned by `upgrade-cluster` and other writes) | ✅ | seconds |
| `modify-cluster-node-pool` (set absolute `desired_size` — the way to "scale to N") | ✅ | 2–8 min per node added/removed |
| `scale-cluster-node-pool --count N` (delta — adds N nodes) | ✅ | 2–8 min per added node |
| `upgrade-cluster-nodepool` | ✅ | minutes per node, rolling |
| `create-cluster-node-pool` | ✅ | 3–8 min |
| `delete-cluster-nodepool` | ✅ | 2–5 min |
| `install-cluster-addons` | ✅ | 30 s – 5 min |
| `upgrade-cluster-addons` | ✅ | 30 s – 5 min |
| `un-install-cluster-addons` | ✅ | 30 s – 3 min |
| `migrate-cluster` (where applicable) | ✅ | tens of minutes |
| `describe-*` / read APIs | ❌ — synchronous | — |

If you're not sure, check the response: an immediate `task_id` field means it's
async.

## Response envelope

Async commands return a JSON envelope similar to:

```json
{
  "cluster_id": "ce914461c0fb4901ae8908be4a10a7a1",
  "request_id": "DDA4DB1A-A7E3-1455-A6FB-77F58F01A43E",
  "task_id":    "T-69ce1022aa09ae010300000b"
}
```

Keep all three:

- `task_id` — pass to `describe-task-info` to track progress.
- `request_id` — quote this when filing a support ticket; it correlates the
  call to ACK control-plane logs.
- `cluster_id` (or `nodepool_id`, `addon` name, etc.) — the resource the task
  is acting on. For `create-cluster`, the cluster ID is reserved immediately,
  but the cluster only becomes usable after the task succeeds.

## Polling: `describe-task-info`

```bash
aliyun cs describe-task-info --task-id T-69ce1022aa09ae010300000b --region cn-hangzhou
```

Pass `--region` matching the cluster's region. Task IDs are region-scoped,
so calling without `--region` routes to the default endpoint and adds an
extra hop. (See SKILL.md §6 Rule B.)

The response carries (field names may vary slightly by task kind):

```json
{
  "task_id":     "T-69ce1022aa09ae010300000b",
  "task_type":   "cluster_create",
  "state":       "running",
  "created":     "2026-06-01T10:00:00Z",
  "updated":     "2026-06-01T10:03:00Z",
  "current_stage": "init_master",
  "task_result": [
    {"name":"prepare_vpc","data":"{\"vpc_id\":\"vpc-bp1xxx\"}"},
    {"name":"init_master","data":"..."}
  ],
  "error": null
}
```

States you'll see (terminology varies slightly across task kinds — code defensively):

| `state` | Meaning |
| ------- | ------- |
| `running` / `pending` | Still in progress — keep polling |
| `success` / `succeeded` | Done, no errors — operation complete |
| `failed` / `fail` / `error` | Terminal failure — inspect `error.code` / `error.message` |
| `paused` | Upgrade tasks only — paused via `pause-task` (acts on `task_id`) |
| `canceled` / `cancelled` | Canceled via `cancel-task` (acts on `task_id`) |

Treat any success/failed/canceled spelling as terminal — stop polling. The
bundled `wait-for-task.sh` collapses all three failure spellings into a single
"failure" exit code.

## Polling strategy

Polling has real cost (token spend in agent contexts, API rate limits, user
attention). Choose interval based on the operation:

| Operation kind | Suggested interval | Suggested timeout |
| -------------- | ------------------ | ----------------- |
| Cluster create / delete | 30 s | 30 min |
| Cluster upgrade (control plane) | 30 s | 60 min |
| Node pool create / scale / upgrade | 15 s | 20 min |
| Addon install / upgrade / uninstall | 10 s | 10 min |

**Always confirm with the user before starting a long busy-wait loop.** A
typical interaction:

> "ACK returned task `T-...` for the cluster creation in cn-hangzhou.
> Creation usually takes 10–15 minutes. Want me to poll until it finishes
> (about 30s intervals), or just hand back the task ID so you can check
> later with `aliyun cs describe-task-info --task-id T-... --region cn-hangzhou`?"

For automation contexts where polling is desired, use the bundled
`./scripts/wait-for-task.sh` — it polls with sensible defaults and prints
the final state.

## Interpreting failures

When `state` becomes `failed`, the `error` field carries a structured code
plus message. The most common failure causes:

| `error.code` (representative) | Likely cause | What to suggest |
| ----------------------------- | ------------ | --------------- |
| `QuotaExceeded.*` | Account/region quota hit (instances, vCPUs, EIPs) | Open Quota Center, request increase, or pick a smaller spec |
| `InvalidVSwitchId.IpNotEnough` | Pod/node vSwitch out of IPs | Add a vSwitch in another AZ, or expand the existing one |
| `InvalidParameter.Format` | JSON-string-inside-JSON escaping in `addons.config` | Rebuild the body with `jq | tojson` (see SKILL §5) |
| `Forbidden.RAM` / `NoPermission` | RAM identity missing the required Action(s) on `cs` or a dependent product (VPC / ECS) | Attach a RAM policy that grants the missing Action — consult ACK RAM documentation |
| `ImagePullBackOff` (in addon install task data) | Cluster nodes can't reach the addon registry | Check egress / NAT, verify ACR-EE/ACR mirror config |
| `ErrorClusterNotFound` / `ErrorNodePoolNotFound` | Wrong region or stale ID | Re-check `--region` and the resource ID |

When reporting back to the user, **lead with the actionable cause**, not the raw
`error.code`. For example: "ACK couldn't pull `logtail-ds` image — your nodes
can't reach `registry.cn-hangzhou.aliyuncs.com`. Check the cluster's NAT/egress
or configure an ACR mirror."

## Subtasks and partial-failure tasks

Some tasks (notably `install-cluster-addons` with multiple addons in one
request) report per-component subtasks under `task_result`. A top-level
`success` doesn't always mean every subtask succeeded — check
`task_result[*].data` for per-addon status when troubleshooting "the install
returned success but the addon isn't running."

For node-pool upgrades, `task_result` lists each node's drain/cordon/upgrade
status. If one node hangs, the whole task can stay `running` for a long time
— inspect `task_result` to find the stuck node and investigate (PDBs,
unkillable pods, taints).

## When NOT to poll

- The user just wants to fire-and-forget (e.g., they'll check the console
  later) — return the `task_id` and stop.
- The operation is quick (< 1 min) and the user is interactive — one
  `describe-task-info` after a brief delay is enough.
- You're in a script with a separate orchestrator that already tracks
  ACK state externally.

The polling helper exists to save the user keystrokes, not to be the
default behaviour for every async call.
