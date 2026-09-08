# Node Exec / Cloud Assistant (F7)

Cloud-Assistant-style remote command execution for Lingjun nodes. Two submit APIs (`run-command`, `stop-invocation`) and one query API (`describe-invocations`).

> [BLOCK] **Boundary** - File delivery (`send-file` / `describe-send-file-results`) is out of scope for this skill.

## F7.1 `run-command` - execute a shell script

### CLI

```bash
safe_aliyun aliyun eflo-controller run-command \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --node-id-list <NodeId> [<NodeId2> ...] \
  --command-content '<bash-script>' \
  [--name <human-name>] [--description <text>] \
  [--timeout 60] [--working-dir /home] [--username root] \
  [--client-token <uuid>] \
  [--content-encoding PlainText|Base64] \
  [--enable-parameter true --parameters '{"k":"v"}'] \
  [--repeat-mode Once|Period|NextRebootOnly|EveryReboot --frequency <expr>] \
  [--termination-mode Process|ProcessTree] \
  [--launcher <bash-path>]
```

### Parameters

| Flag | Required | Default | Notes |
|---|---|---|---|
| `--node-id-list` | [OK] | - | space-separated; <=50 per call |
| `--command-content` | [OK] | - | Bash text. With `--enable-parameter true`, `{{name}}` placeholders are substituted by `--parameters`. |
| `--client-token` | [BLOCK] | (none) | UUID, **strongly recommended** for idempotency |
| `--timeout` | [BLOCK] | `60` (seconds) | per-node hard kill |
| `--working-dir` | [BLOCK] | `/home` (Linux) | - |
| `--username` | [BLOCK] | `root` (Linux) | non-root must already exist on the node |
| `--content-encoding` | [BLOCK] | `PlainText` | `Base64` for binary-safe content |
| `--enable-parameter` | [BLOCK] | `false` | enables `{{var}}` substitution |
| `--parameters` | conditional | `{}` | required when `--enable-parameter true` |
| `--repeat-mode` | [BLOCK] | `Once` | `Once`/`Period`/`NextRebootOnly`/`EveryReboot` |
| `--frequency` | conditional | - | required when `--repeat-mode Period`; Cron / Rate / At |
| `--termination-mode` | [BLOCK] | `Process` | `Process` kills the shell only, `ProcessTree` kills children too |

### Response

```json
{ "InvokeId": "t-uf6...", "RequestId": "..." }
```

### Polling

```bash
safe_aliyun aliyun eflo-controller describe-invocations \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --invoke-id <InvokeId> [--node-id <NodeId>] \
  --include-output true --content-encoding PlainText
```

Field: `Invocations[0].InvokeNodes[*].InvocationStatus`  in  {`Pending`, `Scheduled`, `Running`, `Success`, `Failed`, `Stopped`, `Stopping`, `PartialFailed`, `Timeout`}. Per-node `Output` is the captured stdout/stderr (`PlainText` / `Base64` per encoding flag).

### Stop in-flight

```bash
safe_aliyun aliyun eflo-controller stop-invocation \
  --endpoint eflo-controller.<region>.aliyuncs.com --region <region> \
  --invoke-id <InvokeId> [--node-id-list <NodeId> ...]
```

---

## Workflow (run-command)

1. List nodes -> HITL pick `--node-id-list`.
2. Compose `--command-content`; redact secrets.
3. Generate `--client-token` UUID.
4. Show the confirmation table (with the **first 200 chars** of `command-content` only) + the closing prompt (see `render.confirm_prompt` in `lib/core/i18n.sh`) in one message.
5. User replies the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`) -> submit via `safe_mutate_oneshot` -> record `InvokeId`.
6. Poll `describe-invocations` every 10s until terminal.
7. Report per-node `InvocationStatus` + truncated `Output`.

## Common errors

| Code | Cause | Fix |
|---|---|---|
| `InvocationContentTooLarge` | command body > 24 KB Base64 | shorten the script or split into multiple invocations |
| `Invocation.NodeOffline` | node disconnected from cloud-assistant | retry after `describe-node` shows healthy |
| `Invocation.UserNotExist` | non-root user not present | ensure user exists on node |
