# Job Lifecycle Management

Operational rules for `update-job` / `stop-job` / `get-web-terminal` /
`get-token` — focused on **what `--help` cannot tell you**: status windows,
silent-no-op cases, and the high-risk `stop-job` confirmation protocol.

For the full parameter list of any subcommand, run
`aliyun pai-dlc <cmd> --help`.

## 1. Status-to-Operation Compatibility

| Operation | Allowed Job Status | Caveat |
|-----------|--------------------|--------|
| `update-job --accessibility` | Any | Takes effect immediately |
| `update-job --description` | Any | Metadata only |
| `update-job --priority` | `Creating` / `Queuing` / `EnvPreparing` | **AND** job uses quota (`--resource-id`); once `Running`, cannot be modified |
| `update-job --job-specs` (PodCount) | Elastic-enabled jobs only | Restricted to supported phases |
| `stop-job` | `Running` / `Queuing` only | Irreversible — three-step protocol below |
| `get-web-terminal` | `Running` only | Pod must be alive |
| `get-token` | Any | Read-only sharing |

> **`update-job` does NOT expose `--display-name`** — to rename a job,
> recreate it.

## 2. `update-job --priority` Pre-check Protocol

Always probe both `Status` and `ResourceId` before issuing a priority update;
otherwise the API returns `200 OK` while silently dropping the change.

```bash
aliyun pai-dlc get-job \
  --region <region> --job-id <job-id> \
  --cli-query '{Status: Status, ResourceId: ResourceId}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

Proceed **only if both** hold:

- `Status` ∈ `Creating` / `Queuing` / `EnvPreparing`
- `ResourceId` is non-empty (quota-based job, e.g. `quotaXXXX`)

After issuing the update, expect a 10–60 second propagation delay before
`get-job` reflects the new `Priority`.

## 3. `stop-job` — Three-Step Protocol (HIGH RISK)

Stopping a `Running` job discards in-memory progress unless the user's script
checkpoints. **Never call `stop-job` without explicit user confirmation.**

### Step 1 — Pre-check

```bash
aliyun pai-dlc get-job \
  --region <region> --job-id <job-id> \
  --cli-query '{Status: Status, Name: DisplayName}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Step 2 — Confirm with the user

Present `Status` + `DisplayName`. Use this prompt template:

```
Job <job-id> ("<DisplayName>") is currently <Status>.
Stopping a Running job cannot be undone and will discard any in-memory progress.
Are you sure you want to stop this job? [yes/no]
```

Do NOT proceed without an explicit `yes`.

### Step 3 — Execute, then verify

```bash
aliyun pai-dlc stop-job --region <region> --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Verify (expected: "Stopped")
aliyun pai-dlc get-job --region <region> --job-id <job-id> \
  --cli-query "Status" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## 4. `get-web-terminal`

Requires the Pod to be alive; the URL is short-lived. Typical pattern:

```bash
POD_ID=$(aliyun pai-dlc get-job --region <region> --job-id <job-id> \
  --cli-query "Pods[0].PodId" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job)

aliyun pai-dlc get-web-terminal --region <region> --job-id <job-id> \
  --pod-id "$POD_ID" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## 5. `get-token` — Read-Only Sharing

Generates a token recipients can use to view the job (logs / events /
metrics) without RAM access. The token is read-only delegation; it cannot
modify the job. **Never share via insecure channels** — logs may contain
sensitive data.

## Common Pitfalls

- ❌ `stop-job` on a `Stopped` / `Succeeded` / `Failed` job — API rejects with
  `BadRequest` (terminal state). Always pre-check.
- ❌ `get-web-terminal` after the Job exits `Running` — Pod gone, URL
  unreachable.
- ⚠ `update-job --priority` on a public-resource (`EcsSpec`) job → silent
  no-op. Only quota-based jobs (`--resource-id`) honor it.
- ⚠ `update-job --priority` once job is `Running` or later → silent no-op,
  cannot be modified.
- ⚠ Display name is **not updatable** — pick the right name at `create-job`.
