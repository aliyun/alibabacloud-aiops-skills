# Risk Levels, Approval, Snapshot & Rollback

## Risk levels

| Level | Examples | Approval |
|---|---|---|
| R0 read | list/get, machine-group list-machines, query, status/alarm query | auto |
| R1 local | render config, validate schema, normalize diff | auto |
| R2 reversible write | Project/Logstore/index/machine-group/pipeline-config creation, logtail-pipeline-config update, logtail-pipeline-config apply-to-machine-group, index create/update, host/ACK/k8s install, `kubectl apply` CR | user authorization; diff recommended |
| R3 high impact | logtail-pipeline-config remove-from-machine-group, index delete, batch changes | user authorization; state impact/scope |
| R4 destructive | project delete/log-store/logtail-pipeline-config/machine-group, `kubectl delete` CR | user authorization; identify exact resources |

## Authorization and change review

- Installation, collection changes and resource changes require user authorization.
- Showing changes as a diff is recommended. For config/index changes, show
  `config_update_diff` and `index_update_diff` together. `normalize_diff.py` supports
  `--kind config`, `--kind index` and `--kind auto` for other resource objects.
- State affected bindings, machines and resource scope for high-impact changes.
- Identify exact resources and deletion impact for destructive changes.
- `mode=plan` performs no cloud writes. Do not execute declined or deferred changes.

## Snapshot (before any write)

Snapshots preserve the pre-change values needed for recovery; a diff makes added,
removed and overwritten settings visible for review.

- Cloud resources: save the full `<group> get` object (project/logstore/index/machine-group/pipeline-config), plus binding relations from `machine-group get-applied-configs` / `logtail-pipeline-config get-applied-machine-groups`, and any ETag/lastModifyTime.
- Store snapshots in the task object (`task-model.yaml` -> `execution.snapshot`).
- Do NOT snapshot secrets.

## Rollback

- Use only the pre-execution snapshot or a declared inverse operation. Never rebuild a prior config from memory.
- Update rollback: re-apply the snapshot object via the corresponding `update-*` (full body).
- New resource rollback does NOT default to deletion; deleting a newly created resource is still R4 and needs explicit confirmation.
- Binding rollback: `apply` <-> `remove` are inverses; confirm before removing.
- After rollback, re-run the relevant U-checks to confirm the restored state.

## Cleanup order (config created by this skill)

1. `logtail-pipeline-config remove-from-machine-group` (R3)
2. `logtail-pipeline-config delete` (R4)
3. Optional `index delete` / `logstore delete` / `project delete` only with explicit user confirmation (R3/R4), and only if not shared by other configs (check `logtail-pipeline-config get-applied-machine-groups` / other configs first).
