# Async Tasks: Receipt + On-Demand Query (DescribeTask)

Only a few Lingjun APIs are asynchronous; the rest return synchronously. This skill adopts a "**submit receipt + on-demand query**" model for async tasks (no automatic polling — simple and reliable). This document describes the async API set, the receipt contract, and how to query with `describe-task`.

## Async API Set

| API | Returns | Typical Duration (measured) | Abnormal Threshold |
|---|---|---|---|
| `CreateCluster` | `{ClusterId, TaskId, RequestId}` | ~1 minute without nodes; a few minutes with nodes | 30 minutes |
| `UpdateNodeGroup` (some fields only) | `{TaskId, RequestId}` | A few minutes | 10 minutes |

⚠️ **`UpdateNodeGroup` async vs sync is field-level**:
- **Async** fields (return TaskId): `--login-password` / `--biz-key-pair-name` / `--file-system-mount-enabled`
- **Sync** fields (return RequestId only): `--new-node-group-name` / `--image-id` / `--biz-ram-role-name` / `--user-data`

**Note**: `DeleteNode` is a synchronous API and does **not** return a TaskId — do not mistake it for an async one.

## Fully Synchronous APIs (no polling needed)

| API | Returns |
|---|---|
| `DeleteCluster` | `{RequestId}` (effective immediately; after deletion `describe-cluster` should return `RESOURCE_NOT_FOUND`) |
| `CreateNodeGroup` | `{NodeGroupId, RequestId}` |
| `DeleteNodeGroup` | `{RequestId}` |
| `TagResources` / `UntagResources` / `ChangeResourceGroup` | `{RequestId}` |
| All `List*` / `Describe*` | Business data + `RequestId` |

## describe-task Usage

```bash
aliyun eflo-controller describe-task \
  --endpoint eflo-controller.<region>.aliyuncs.com \
  --region <region> \
  --task-id <task-id>
```

**Response fields**:

```json
{
  "TaskId": "task-xxx",
  "TaskType": "CreateCluster",
  "TaskState": "running",
  "CreateTime": "2026-05-30T12:00:00Z",
  "UpdateTime": "2026-05-30T12:05:00Z",
  "Message": "...",
  "Steps": [...],
  "NodeIds": [...],
  "ClusterId": "i-xxx",
  "ClusterName": "...",
  "RequestId": "..."
}
```

## TaskState Enum

| TaskState | Meaning | Terminal? |
|---|---|---|
| `init` | Task created, not started | ❌ In progress |
| `pending` | Awaiting scheduling | ❌ In progress |
| `running` | Executing | ❌ In progress |
| `execution_success` | ✅ Succeeded | ✅ Terminal |
| `execution_fail` | ❌ Failed | ✅ Terminal |

## Receipt + On-Demand Query Contract (default interaction mode)

1. **Submit receipt**: right after an async API submit succeeds, print the receipt in the reply body (markdown table; zh sessions use Chinese column names): Operation / ClusterId (if any) / TaskId / RequestId / estimated duration; close by telling the user they can say "查一下任务进度" at any time.
2. **No automatic polling**: after the receipt the conversation may end; no background/foreground polling is started.
3. **On-demand query**: when the user asks about progress, run `query <region> task <task-id>` and print stdout verbatim; after a terminal state, add the resource-level verification below.
4. **Poll only on explicit wait request**: only when the user explicitly asks to "wait until it finishes / watch the progress", use `poll_task <region> <tid>` (with `export LJ_TASK_LABEL="<operation name>"` prefixed) to poll continuously until a terminal state.
5. **Timeout reference**: quote the typical measured duration as the estimate (create: ~1 min without nodes, a few minutes with); if an on-demand query finds the task past the abnormal threshold (create: 30 minutes) and still non-terminal, report the current state and suggest opening a ticket. Never write the abnormal threshold into the receipt as the estimated duration.

## ⚠️ DescribeTask HTTP 200 Business-Error Trap

`DescribeTask` may return **HTTP 200** + `ErrorCodeInfo.Success=false` on certain internal errors — you **cannot** judge success by the HTTP status code alone.

```json
HTTP/1.1 200 OK
{
  "ErrorCodeInfo": {
    "Success": false,
    "HttpStatusCode": 200,
    "ErrorCode": "",
    "ErrorMessage": "<raw exception message>"
  }
}
```

Correct check:

```bash
RESULT=$(aliyun eflo-controller describe-task ...)
SUCCESS=$(echo "$RESULT" | jq -r '.ErrorCodeInfo.Success // "true"')

if [ "$SUCCESS" = "false" ]; then
  echo "❌ DescribeTask internal error"
  echo "$RESULT" | jq '.ErrorCodeInfo'
  exit 1
fi
```

## Success Verification (API level)

After an async API reaches the terminal state `execution_success`, perform **one extra resource-state verification** to count it as a real success:

| API | Post-terminal verification |
|---|---|
| `CreateCluster` | `describe-cluster` returns `OperatingState=Running` |
| `DeleteCluster` (synchronous) | Right after a successful submit, `describe-cluster` should return `RESOURCE_NOT_FOUND` |
| `UpdateNodeGroup` | The `describe-node-group` fields match the expected values |

## Idempotency of Repeated Calls

| API | Idempotency behavior |
|---|---|
| `DeleteNode` | ✅ A second call on an already-`Releasing` node returns HTTP 200 |
| `CreateCluster` | ❌ No built-in ClientToken; repeated calls create multiple tasks — the caller must deduplicate |
| `DeleteCluster` | Repeated call while Deleting / already deleted returns `OperationConflict` or `RESOURCE_NOT_FOUND` |
| `CreateNodeGroup` | ❌ Duplicate `NodeGroupName` returns HTTP 417 `IntegrityError` |
| `UpdateNodeGroup` | ❌ The async branch has no ClientToken; repeated calls create multiple tasks |

## 📖 References

- [DescribeTask error codes](error-codes.md#114-describetask)
- [eflo-controller OpenAPI](https://api.aliyun.com/api/eflo-controller/2022-12-15)
