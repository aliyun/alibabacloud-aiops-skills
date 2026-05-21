# Job Lifecycle Management

Detailed flow for `update-job`, `stop-job`, `get-web-terminal`, and
`get-token`. The Stop operation is **high-risk** and requires a
pre-check + explicit user confirmation before execution.

## Status-to-Operation Compatibility

| Operation | Allowed Job Status |
|-----------|--------------------|
| `update-job` (mutable fields) | Any status, but only `display-name`, `description`, `priority`, `accessibility`, `job-specs.PodCount` can be modified |
| `stop-job` | `Running` or `Queuing` only |
| `get-web-terminal` | `Running` only (Pod must be alive) |
| `get-token` | Any status (read-only sharing) |

## 1. `update-job` (Low-Risk)

Only mutable fields. No user confirmation required for safe updates such as
priority adjustments.

```bash
# Example: bump priority from 1 to 5
aliyun pai-dlc update-job \
  --region <region> \
  --job-id <job-id> \
  --priority 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## 2. `stop-job` (High-Risk)

Stop is irreversible — a running job's training progress is lost unless the
script has its own checkpointing. Always run the three-step protocol below.

### Step 1: Pre-check Job Status

```bash
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <job-id> \
  --cli-query '{Status: Status, Name: DisplayName}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Step 2: Confirm with User

Present the status + name to the user. Do NOT proceed without an explicit `yes`.
Recommended prompt template:

```
Job <job-id> ("<DisplayName>") is currently <Status>.
Stopping a Running job cannot be undone and will discard any in-memory progress.
Are you sure you want to stop this job? [yes/no]
```

### Step 3: Execute Stop (only after user replies `yes`)

```bash
aliyun pai-dlc stop-job \
  --region <region> \
  --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Step 4: Verify Stopped

```bash
aliyun pai-dlc get-job \
  --region <region> \
  --job-id <job-id> \
  --cli-query "Status" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
# Expected: "Stopped"
```

## 3. `get-web-terminal` (Live Pod Only)

```bash
# Requires the Job to be Running and the target Pod to be alive.
POD_ID=$(aliyun pai-dlc get-job --region <region> --job-id <job-id> \
  --cli-query "Pods[0].PodId" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job)

aliyun pai-dlc get-web-terminal \
  --region <region> \
  --job-id <job-id> \
  --pod-id "$POD_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

The response contains a short-lived URL. Open it in a browser to attach an
interactive shell.

## 4. `get-token` (Read-Only Sharing)

```bash
# Generate a sharing token valid for 7 days (604800 seconds)
aliyun pai-dlc get-token \
  --region <region> \
  --target-id <job-id> \
  --target-type job \
  --expire-time 604800 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

Recipients can use the token to view the job (and its logs / events / metrics)
without RAM access. The token grants read-only delegation; it cannot modify the
job.

## Resource Cleanup Template

End-to-end script to stop a job after training completes.

```bash
JOB_ID=<job-id>
REGION=<region>

# Step 1: Pre-check status
aliyun pai-dlc get-job --region $REGION --job-id $JOB_ID \
  --cli-query '{Status: Status, Name: DisplayName}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Step 2: Confirm with user (prompt template above), then proceed only on "yes"

# Step 3: Stop if still running
aliyun pai-dlc stop-job --region $REGION --job-id $JOB_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Step 4: Verify stopped
aliyun pai-dlc get-job --region $REGION --job-id $JOB_ID \
  --cli-query "Status" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
# Expected: "Stopped"
```

## Common Pitfalls

- ❌ Calling `stop-job` on a `Stopped` / `Succeeded` / `Failed` job — the API
  rejects with `BadRequest` because the Job is already in a terminal state. This
  is benign (no cost leak) but confusing in scripts; check status before calling.
- ❌ Calling `get-web-terminal` after the Job exits Running — the Pod is gone
  and the terminal URL will be unreachable.
- ❌ Sharing a `get-token` URL via insecure channels — the token allows full
  read access to logs that may include sensitive data.
- ⚠ Use `update-job --priority` only between 1 and 9; values outside this range
  are silently rejected by the scheduler.
