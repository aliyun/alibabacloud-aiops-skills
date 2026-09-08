Lingjun node-group update = modifying the default configuration of a node group (single action: `update-node-group`).

> [BLOCK] **Boundary (MANDATORY)** - Moving a node between groups (`change-node-group`) is a **different concept** from the "group update" covered here and does **not** belong to this skill; route it to `alibabacloud-lingjun-cluster-scaling`.

---

## `update-node-group` - modify NodeGroup default configuration

### Semantics

Modifies the "default configuration" of a **node group**. These defaults only apply to nodes **provisioned in the future** under this group (e.g. inherited as defaults during `extend-cluster`); they have **no effect on existing nodes**.

> [WARN] **CLI doc-hallucination hard rule (MANDATORY)** -
> `aliyun eflo-controller update-node-group --help` marks `--new-node-group-name` as Optional, **but the server requires it**. Even when the user only wants to change `--image-id` / `--login-password` / `--user-data`, omitting `--new-node-group-name` immediately returns `MissingParameter.NewNodeGroupName`.
>
> Standard practice: first run `describe-node-group --node-group-id <gid>` to read the current `NodeGroupName`; if the user does not want a rename, pass the same value back to `--new-node-group-name`. **The Agent must never omit this parameter on its own.**

### Required

- `--region` / `--endpoint`
- `--node-group-id <gid>`
- `--new-node-group-name <name>` (must be passed even when not renaming)

### Business-optional (at least one required for a meaningful change)

- `--image-id <m-xxx>` - `forbidden_inference`; must be HITL-selected from `list-images`
- `--login-password '***'` - sensitive field, always redact
- `--user-data <base64>` - Cloud-Init script (<=16KB Base64)
- `--biz-key-pair-name <kp>`
- `--biz-ram-role-name <role>`
- `--file-system-mount-enabled true|false`
- `--system-disk PerformanceLevel=<PL0|PL1|...>` - the system disk **only supports changing the performance level**; Category and Size have no parameters and cannot be changed (CLI 3.3.10 dry-run verified: Size/Category report unknown field)

### Workflow (synchronous)

1. `describe-node-group --node-group-id <gid>` -> read the current `NodeGroupName` and all default fields
2. HITL: the user checks off which fields to modify; unmodified fields keep their original values (but `--new-node-group-name` must always be passed)
3. Parameter confirmation table (dump the full field table) + user replies with the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`, same step); after confirmation, submit via `safe_mutate_oneshot`
4. Submit `update-node-group`
5. Verify: run `describe-node-group` again and assert field-by-field that the new values took effect

### Example invocation

```bash
safe_aliyun aliyun eflo-controller update-node-group \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-group-id ng-xxx \
  --new-node-group-name <existing-or-new-name> \
  --image-id m-xxx \
  --login-password '***'
```

### Common errors

| Symptom | Root cause | Remedy |
|---|---|---|
| `MissingParameter.NewNodeGroupName` | CLI doc-hallucination: `--new-node-group-name` not passed | Read the current name from `describe-node-group` and resend |
| `InvalidImageId.NotFound` | Custom image cross-region / deleted | Re-run HITL via `list-images` |
| `OperationConflict` | Another task is running on this group | HITL choose parallel / wait; **never** silently retry |

---

## Verification Cheat Sheet

| Capability | Verification API | Pass criteria |
|---|---|---|
| update-node-group | `describe-node-group` | Every modified field returns value == new value |
