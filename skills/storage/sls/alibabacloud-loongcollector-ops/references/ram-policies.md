# RAM Policies (per workflow, least privilege)

Use the user's own identity. Grant only what a workflow needs. Do not default to `AliyunLogFullAccess`. Actions use the `log:` prefix; resources are `acs:log:<region>:<account>:project/<project>/...`.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

On `Unauthorized`/`AccessDenied`: stop the affected operation, report `[Error: permission]`, the exact missing Action, and request ID, then pause for permission diagnosis. Ask once in that turn and end the turn. Retry only after the user explicitly confirms authorization is complete — then retry the identical failed command the same turn and emit `[RECOVERED: permission_granted]` in the user-facing text. If the user says authorization is incomplete/rejected/cancelled, or the ask limit is reached, emit `[BLOCKED: PERMISSION_REQUIRED]` as the sole content of that turn (no tools, no English long sentence). Never switch account/profile or widen scope.

## Layer: ReadOnly (default)

Used by `lens.query`, `troubleshoot.basic`, and all Observe steps.

```
log:GetProject, log:ListProject
log:GetLogStore, log:ListLogStores
log:GetIndex
log:GetMachineGroup, log:ListMachineGroup, log:ListMachines
log:GetConfig, log:ListConfig            # pipeline config get/list
log:GetAppliedConfigs, log:GetAppliedMachineGroups
log:GetLogStoreLogs                       # GetLogsV2 (business + Lens run logs)
```

## Layer: Operator (explicit user authorization)

Used by `config.create`, `config.modify`, `onboarding.cloud`, `machine_group.manage` (create/update/bind).

```
log:CreateProject, log:UpdateProject
log:CreateLogStore, log:UpdateLogStore
log:CreateIndex, log:UpdateIndex
log:CreateMachineGroup, log:UpdateMachineGroup
log:CreateConfig, log:UpdateConfig        # Create/UpdateLogtailPipelineConfig
log:ApplyConfigToMachineGroup
```

## Layer: Destructive (temporary authorization, second confirmation)

Used by cleanup / delete / unbind (R3/R4).

```
log:RemoveConfigFromMachineGroup
log:DeleteConfig
log:DeleteIndex
log:DeleteMachineGroup
log:DeleteLogStore
log:DeleteProject
```

## Workflow -> Actions quick map

| Workflow | ReadOnly | Operator | Destructive |
|---|---|---|---|
| lens.query / troubleshoot.basic | all ReadOnly | — | — |
| config.create | Get/List config, group, logstore | CreateConfig, ApplyConfigToMachineGroup, (CreateIndex/UpdateIndex) | — |
| config.modify | GetConfig, GetIndex, ListMachines | UpdateConfig, UpdateIndex | — |
| onboarding.cloud | all ReadOnly | Create/Update Project/LogStore/Index/MachineGroup/Config + Apply | — |
| machine_group.manage | Get/List group, ListMachines | Create/Update MachineGroup, Apply | Remove/Delete (R3/R4) |
| cleanup | GetAppliedMachineGroups | — | Remove/Delete config/index/logstore/project |

> Note: exact Action names should be confirmed against current SLS RAM documentation at authorization time; `log:GetLogStoreLogs` covers GetLogsV2. Resource-level scoping to the specific project/logstore is recommended over `*`.
