# Risk Levels, Approval, Snapshot & Rollback

## Risk levels

| Level | Examples | Approval |
|---|---|---|
| R0 read | list/get, list-machines, get-logs-v2, status/alarm query | auto |
| R1 local | render config, validate schema, normalize diff | auto |
| R2 reversible write | create-project/log-store/index/machine-group/pipeline-config, update-logtail-pipeline-config, apply-config-to-machine-group, create/update-index, host/ACK/k8s install, `kubectl apply` CR | show normalized diff, one confirmation |
| R3 high impact | remove-config-from-machine-group, delete-index, batch changes | confirm after stating impact/scope |
| R4 destructive | delete-project/log-store/logtail-pipeline-config/machine-group, `kubectl delete` CR | second confirmation, restate exact resources |

If the host client offers HITL, R2-R4 may use it; still keep this confirmation protocol because HITL is not universal.

## Approval protocol

- R2: execute `normalize_diff.py` for every target resource/relation, present the normalized result (`config_update_diff` + `index_update_diff` together when fields change) and exact commands; one confirmation.
- R3: state affected bindings/machines/scope explicitly before confirming.
- R4: restate the exact resource names and that deletion is irreversible; require a distinct second confirmation.
- `mode=plan`: never call write commands regardless of level.
- Only an explicit affirmative answer from the user authorizes R2+; the original request, a plan table, and “the task explicitly requires” are never implicit approval.
- Ask at most one confirmation question per assistant turn. Create-and-bind (R2) and unbind (R3) are **two** gates: finish the first confirmation and its writes before using the fixed unbind approval subject from `SKILL.md`. Never merge them.
- Install (`install.deploy`) and collection are **two** gates. First use the environment-specific install subject from `SKILL.md` (ECS / self-host / ACK / self-k8s). After the stage gate passes, use the fixed create-and-bind approval subject when a CR or API config must be created. Skip the second gate on pure `[Idempotent-Skip]` reuse of default collection.
- First confirmation emits `[AWAITING: R2_CONFIRMATION] ask=1` with the question and ends the turn; nothing you write yourself counts as the answer. No create/update/apply/remove/install (including `--cli-dry-run` or `kubectl apply`) until the matching explicit affirmative reply.
- **Deferred replies (hard stop):** A user message that states neither approval nor rejection — blank, "later", "not decided yet", or any equivalent — is a deferral. First ask uses `ask=1`. After each deferral, restate the waiting resources in one line and re-ask the identical confirmation subject **exactly once** with `[AWAITING: R2_CONFIRMATION] ask=2` then `ask=3` (never a duplicated question); never soft-close without re-asking. When `ask=3` has also gone unanswered, emit `[BLOCKED: R2_CONFIRMATION_TIMEOUT]` as the first and only output bytes of that turn — no reasoning, no tool calls, no English long sentence, no prefix or suffix around the tag.
- Rejection/cancellation: emit `[CANCELLED: R2_CONFIRMATION_REJECTED]` as the sole content of that turn and stop every planned write. Do not append `User rejected the proposed plan…` or any other English prose.
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
