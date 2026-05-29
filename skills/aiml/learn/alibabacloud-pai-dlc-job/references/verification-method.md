# PAI-DLC Operation Verification Methods

End-to-end and per-command verification scripts. These are **runnable
flows**, not parameter docs — for flag-level details run
`aliyun pai-dlc <cmd> --help`. The job status enum, common errors, and red
lines live in [related-apis.md](related-apis.md) (single source of truth).

Every API call MUST include
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`. Replace
`<region>` / `<job-id>` / `<pod-id>` / `<workspace-id>` placeholders before
running.

---

## 1. Per-Command Quick Verify

### 1.1 Create Job

```bash
JOB_ID=$(aliyun pai-dlc create-job \
  --region <region> \
  --workspace-id <workspace-id> \
  --display-name "verify-job" \
  --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"<ImageUri>","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]' \
  --user-command "python -c 'print(123)'" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query "JobId")
```

**Expect:** `JobId` matches `dlc[0-9a-z]+`; status shortly enters
`Creating` / `Queuing` / `Running`.

### 1.2 List / Get / Events / Logs / Metrics

```bash
aliyun pai-dlc list-jobs --region <region> --status Running --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-job --region <region> --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-pod-logs --region <region> --job-id <job-id> --pod-id <pod-id> \
  --max-lines 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-job-events --region <region> --job-id <job-id> \
  --max-events-num 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-pod-events --region <region> --job-id <job-id> --pod-id <pod-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

**Expect:** all return non-empty data once the job is past `EnvPreparing`.
Logs contain stdout/stderr; events sorted by time.

### 1.3 Update / Stop

```bash
# Priority update (pre-check status & quota first; see SKILL.md §7.8)
aliyun pai-dlc update-job --region <region> --job-id <job-id> --priority 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Stop (HIGH-RISK — follow pre-check + user-confirmation protocol in SKILL.md §7.8)
aliyun pai-dlc stop-job --region <region> --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### 1.4 Health Check (only when `Settings.EnableSanityCheck=true`)

```bash
aliyun pai-dlc list-job-sanity-check-results \
  --region <region> --job-id <job-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-job-sanity-check-result \
  --region <region> --job-id <job-id> --sanity-check-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### 1.5 Debug Helpers

```bash
# Verbose logging
aliyun pai-dlc <cmd> --region <region> --log-level=debug \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Dry-run (no API call)
aliyun pai-dlc <cmd> --region <region> --cli-dry-run \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

---

## 2. Resource Discovery → CreateJob (E2E)

Verifies the full **discover → fill → create → verify → cleanup** workflow
using AIWorkSpace resource discovery. Mirrors the §7.6 flow in `SKILL.md`.

### 2.1 Pre-flight

```bash
aliyun aiworkspace --help >/dev/null 2>&1 \
  || aliyun plugin install --names aliyun-cli-aiworkspace
```

### 2.2 Discover Resources

```bash
WORKSPACE_ID=$(aliyun aiworkspace list-workspaces \
  --region <region> --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Workspaces[0].WorkspaceId')

IMAGE_URI=$(aliyun aiworkspace list-images \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Images[0].ImageUri')

DATASET_ID=$(aliyun aiworkspace list-datasets \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Datasets[0].DatasetId')

CODE_SOURCE_ID=$(aliyun aiworkspace list-code-sources \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'CodeSources[0].CodeSourceId')
```

**Expect:** all four variables non-empty. Optional resources can be omitted
in step 2.3 if absent.

### 2.3 Create Job with Discovered Resources

> ⚠ When passing `--resource-id` (dedicated quota), use `ResourceConfig` —
> NOT `EcsSpec`. For pay-as-you-go, use `EcsSpec` and omit `--resource-id`.

```bash
JOB_SPECS=$(cat <<EOF
[{
  "Type": "Worker",
  "PodCount": 1,
  "Image": "$IMAGE_URI",
  "ResourceConfig": {"CPU": "4", "Memory": "16Gi", "GPU": "1", "SharedMemory": "8Gi"}
}]
EOF
)

JOB_ID=$(aliyun pai-dlc create-job \
  --region <region> \
  --workspace-id $WORKSPACE_ID \
  --resource-id $QUOTA_ID \
  --display-name "e2e-discovery-verify" \
  --job-type PyTorchJob \
  --job-specs "$JOB_SPECS" \
  --data-sources "[{\"DataSourceId\":\"$DATASET_ID\",\"MountPath\":\"/mnt/data\"}]" \
  --code-source "{\"CodeSourceId\":\"$CODE_SOURCE_ID\",\"MountPath\":\"/mnt/code\"}" \
  --user-command "python -c 'print(123)'" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'JobId')
```

### 2.4 Verify

```bash
aliyun pai-dlc get-job --region <region> --job-id $JOB_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Status:Status,WorkspaceId:WorkspaceId,ResourceId:ResourceId}'
```

**Expect:** `Status` ∈ `Creating` / `Queuing` / `EnvPreparing` / `Running` /
`Succeeded`. `WorkspaceId` / `ResourceId` match discovery values.

### 2.5 Discovery Checklist

- [ ] `aliyun aiworkspace list-workspaces --help` returns exit 0
- [ ] All four discovery variables non-empty
- [ ] §2.3 returns valid `JobId` (`dlc[0-9a-z]+`)
- [ ] §2.4 status in expected enum
- [ ] No ROA calls anywhere in the flow
- [ ] `EcsSpec` ⇄ `ResourceConfig` mutual exclusion respected
