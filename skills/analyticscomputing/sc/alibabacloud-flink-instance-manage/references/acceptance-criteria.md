# Operation Completion Checklist

Use this checklist to decide whether an instance/namespace operation is actually complete.

## 1) Entrypoint

Run resource operations only through:

```bash
python scripts/instance_ops.py <command> ...
```

Do not replace with raw `aliyun foasconsole` commands.

## 2) Confirmation flags

- `create` requires `--confirm`
- `create_namespace` requires `--confirm`

If `--confirm` is missing, fix the command before execution.

## 3) Read-back verification

A create operation is complete only when:

1. create response is successful (or idempotent equivalent), and
2. follow-up read-back confirms target state.

Create response without read-back is not complete.

## 4) Retry and fallback

- Max attempts for one command: 2 (initial + one corrected retry)
- No blind retries
- No automatic operation switching without explicit user approval

## 5) Lifecycle chain consistency

For `create` + `create_namespace` in one flow:

- namespace must target the same `InstanceId` returned by `create`
- if instance is not `RUNNING`, wait/poll the same instance first
- do not switch to a different instance without explicit user approval
- final `completed` status requires both create commands to return `success: true`

## 6) Security baseline

- No AK/SK hardcoding in commands or scripts
- Use default credential chain (CLI profile or RAM role)
- No secret values in normal response content

## 7) Response completeness

Final response should include:

- `operation`
- `create_result`
- `verify_result`
- `status` (`completed` / `failed` / `not_ready`)
- `next_action` when not completed

## 8) No partial-success closure for lifecycle flow

For lifecycle tasks that require instance + namespace create:

- if `create_namespace` fails, do not mark overall status as `completed`
- use `failed` or `not_ready` with explicit next action

## 9) Flink AI Service

| Scenario | Expected behavior | Failure case |
|---|---|---|
| Query status or free quota | Run the read-only command in the user's specified region and report the returned DTO fields | Treat missing quota as zero or silently switch regions |
| Activate, deactivate, or change closure protection | Pass `--confirm` after user confirmation and use an explicit boolean for closure protection | Automatically disable closure protection when it blocks deactivation |
| Verify a change | Check the returned `Success` and verify the target state with a follow-up query | Report an accepted request or transitional state as complete |
| Write request times out or returns an ambiguous result | Record the `request_id` if available and query the current state first | Retry the write before checking the current state |
