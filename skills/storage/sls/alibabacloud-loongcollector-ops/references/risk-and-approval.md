# Risk Levels, Approval, Snapshot & Rollback

## Risk levels

| Level | Examples | Approval |
|---|---|---|
| R0 read | list/get, list-machines, get-logs-v2, status/alarm query | auto |
| R1 local | render config, validate schema, normalize diff | auto |
| R2 reversible write | create-project/log-store/index/machine-group/pipeline-config, update-logtail-pipeline-config, apply-config-to-machine-group, create/update-index | show normalized diff, one confirmation |
| R3 high impact | remove-config-from-machine-group, delete-index, batch changes | confirm after stating impact/scope |
| R4 destructive | delete-project/log-store/logtail-pipeline-config/machine-group | second confirmation, restate exact resources |

If the host client offers HITL, R2-R4 may use it; still keep this confirmation protocol because HITL is not universal.

## Approval protocol

- R2: execute `normalize_diff.py` for every target resource/relation, present the normalized result (`config_update_diff` + `index_update_diff` together when fields change) and exact commands; one confirmation.
- R3: state affected bindings/machines/scope explicitly before confirming.
- R4: restate the exact resource names and that deletion is irreversible; require a distinct second confirmation.
- `mode=plan`: never call write commands regardless of level.
- Only an explicit affirmative answer from the user authorizes R2+; the original request is never implicit approval.
- Ask at most one confirmation question per assistant turn. Emit `[AWAITING: R2_CONFIRMATION]` together with the question and end the turn; nothing you write yourself counts as the answer.
- **Deferred replies (hard stop):** A user message that states neither approval nor rejection — blank, "later", "not decided yet", or any equivalent — is a deferral. Maintain `deferral_counter` starting at `0` and increment it once per such message. After each deferral, re-ask the identical Chinese confirmation subject in the same turn; never soft-close without re-asking. When the third ask has also gone unanswered, emit `[BLOCKED: R2_CONFIRMATION_TIMEOUT]` as the first and only output bytes of that turn — no reasoning, no tool calls, no prefix or suffix around the tag.
- Rejection/cancellation: emit `[CANCELLED: R2_CONFIRMATION_REJECTED]` as the sole content of that turn and stop every planned write.
- Automation, urgency, and complete parameters never waive this gate; execute no R2+ command while the answer is outstanding.

## Snapshot (before any write)

- Cloud resources: save the full `get-*` object (project/logstore/index/machine-group/pipeline-config), plus binding relations from `get-applied-configs` / `get-applied-machine-groups`, and any ETag/lastModifyTime.
- Store snapshots in the task object (`task-model.yaml` -> `execution.snapshot`).
- Do NOT snapshot secrets.

## Rollback

- Use only the pre-execution snapshot or a declared inverse operation. Never rebuild a prior config from memory.
- Update rollback: re-apply the snapshot object via the corresponding `update-*` (full body).
- New resource rollback does NOT default to deletion; deleting a newly created resource is still R4 and needs explicit confirmation.
- Binding rollback: `apply` <-> `remove` are inverses; confirm before removing.
- After rollback, re-run the relevant U-checks to confirm the restored state.

## Cleanup order (config created by this skill)

1. `remove-config-from-machine-group` (R3)
2. `delete-logtail-pipeline-config` (R4)
3. Optional `delete-index` / `delete-log-store` / `delete-project` only with explicit user confirmation (R3/R4), and only if not shared by other configs (check `get-applied-machine-groups` / other configs first).
