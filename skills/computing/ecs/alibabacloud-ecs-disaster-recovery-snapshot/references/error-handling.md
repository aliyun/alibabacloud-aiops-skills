# Error Handling — ECS Snapshot-Based Disaster Recovery

## General Retry Strategy

| Error Type | Action | Max Retries | Delay |
| --- | --- | --- | --- |
| `InternalError`, `ServiceUnavailable`, `Throttling` | Auto-retry | 3 | 15 seconds |
| `OperationConflict` | Auto-retry | 3 | 15 seconds |
| `InvalidInstanceId.NotFound`, `InvalidDiskId.NotFound` | Stop immediately | — | — |
| `QuotaExceeded.*` | Stop, guide user to quota center | — | — |
| `IncorrectDiskStatus`, `IncorrectInstanceStatus` | Stop, explain status issue | — | — |
| Other unknown errors | Stop, show full error, suggest docs/ticket | — | — |

---

## Scenario A — Step 3: Snapshot Creation

### a) API request failure (create-snapshot returns error)

**Retryable errors** (`InternalError`, `ServiceUnavailable`, `Throttling`, `OperationConflict`):
- Inform user of the error reason
- Wait **15 seconds** then auto-retry, max **3 retries**
- Example message: "Snapshot creation encountered a server error (InternalError). Will auto-retry in 15 seconds (attempt 1/3)."

**Non-retryable errors** (`InvalidInstanceId.NotFound`, `InvalidDiskId.NotFound`, `QuotaExceeded`, `IncorrectDiskStatus`):
- Stop immediately
- Explain the specific error cause
- Give actionable suggestion (e.g., check instance ID, check disk status, request quota increase)

### b) Snapshot creation stuck (polling timeout)

If snapshot is not completed after **5 minutes** from submission:
- Proactively inform user of current snapshot progress
- Use `AskUserQuestion` with options:
  - `Continue waiting` — Continue polling, report progress every 60 seconds
  - `Check in console` — Direct user to ECS Console → Storage & Snapshots → Snapshots
  - `Abort this operation` — Terminate workflow, preserve created snapshot resources

### c) Snapshot status abnormal

If snapshot status becomes `failed` or `error`:
- Stop immediately
- Inform user that snapshot creation failed
- Suggest checking console for details

---

## Scenario A — Step 4: Image Creation

### a) create-image submission failure

**Retryable errors** (`InternalError`, `ServiceUnavailable`):
- Wait 15 seconds then retry, max 3 times

**`InvalidSnapshotId.NotReady`**:
- Snapshot not yet ready — wait for snapshot completion then re-submit

**Non-retryable errors**:
- Stop immediately and explain error

### b) Image creation stuck (polling timeout)

If image is not ready after **5 minutes** from submission:
- Inform user of current image creation progress
- Use `AskUserQuestion` with options:
  - `Continue waiting` — Continue polling, report every 60 seconds
  - `Check in console` — Direct user to ECS Console → Instances & Images → Images
  - `Abort this operation` — Terminate workflow, preserve created snapshots and image

### c) Image status abnormal

If image status becomes `UnAvailable`:
- Stop immediately
- Inform user that image creation failed
- Suggest checking console or recreating

---

## Scenario A — Step 6: Instance Creation (run-instances)

### Error diagnosis table

| Error Code | Root Cause | Actionable Suggestion |
| --- | --- | --- |
| `QuotaExceeded.Instance` | Instance quota insufficient | Direct user to [Quota Center](https://quotas.console.aliyun.com/) |
| `OperationDenied.NoStock` / `Throttling.Resource` | No stock in target AZ | `AskUserQuestion`: change AZ / change similar spec / retry later |
| `InvalidParameter.*` | Parameter error | Parse which parameter is invalid, suggest correction |
| `InvalidSecurityGroupId.NotFound` | Security group not found | Check resource ID correctness |
| `InvalidVSwitchId.NotFound` | VSwitch not found | Check VSwitch ID correctness |
| `InternalError` / `ServiceUnavailable` | Server-side failure | Wait 15s, retry max 3 times |
| `InvalidImageId.NotFound` | Image not ready or missing | Check image status is Available |
| `InvalidDataDiskSize.*` | Data disk params mismatch | Verify `--data-disk` Size/Category/SnapshotId match source |
| Other | Unknown | Show full error code and message, suggest [ECS API docs](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview) or ticket |

### Instance created but status abnormal

If instance status is not `Running` after waiting (e.g., `Stopped`, `Pending` timeout):
- Inform user of actual status
- Suggest checking instance details in console

---

## Scenario B — Step 3: Snapshot Creation

Same handling as Scenario A Step 3 (see above).

---

## Scenario B — Steps 4-5: Disk Creation & Attachment

### create-disk failure

| Error Code | Action |
| --- | --- |
| `InternalError`, `ServiceUnavailable` | Wait 15s, retry max 3 times |
| `InvalidSnapshotId.NotFound` | Check snapshot is completed and Available |
| `QuotaExceeded.Disk` | Direct user to [Quota Center](https://quotas.console.aliyun.com/) |
| Other | Show full error and suggest |

### attach-disk failure

| Error Code | Action |
| --- | --- |
| `InstanceNotFound` | Check target instance ID correctness |
| `IncorrectInstanceStatus` | Instance may be starting up — wait 15s, retry |
| `DiskCategoryNotSupported` | Target instance doesn't support this disk type — `AskUserQuestion` for alternative |
| Retryable errors | Wait 15s, retry max 3 times |

---

## Common Patterns

### Polling pattern for snapshot/image status

```bash
# Poll every 30 seconds, timeout after 5 minutes
START_TIME=$(date +%s)
while true; do
  STATUS=$(aliyun ecs describe-snapshots ...)
  if [[ "$STATUS" == "accomplished" ]]; then break; fi
  if [[ "$STATUS" == "failed" ]]; then # handle failure; fi
  
  ELAPSED=$(( $(date +%s) - START_TIME ))
  if [[ $ELAPSED -gt 300 ]]; then
    # Timeout — ask user what to do
    break
  fi
  sleep 30
done
```

### User-facing progress messages

- "Snapshot creating... Current progress: 45% (waited 2 minutes)"
- "Image creating... Status: Creating (waited 3 minutes)"
- "Instance starting... Current status: Pending"
