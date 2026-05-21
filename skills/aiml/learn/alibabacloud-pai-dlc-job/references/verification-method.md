# PAI-DLC Operation Verification Methods

Quick verification commands for each operation. Every command MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`.

---

## Basic Operations Quick Verify

All commands below use `<region>` placeholder. Replace `<region>`, `<job-id>`, `<pod-id>`, `<workspace-id>` etc. with actual values before running.

### 1. Create Job

```bash
JOB_ID=$(aliyun pai-dlc create-job \
  --region <region> \
  --display-name "verify-job" \
  --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"<ImageUri>","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]' \
  --user-command "python -c 'print(123)'" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query "JobId" --output text)
```

**Expect:** Valid `JobId` (format `dlcXXXXXXXX`), status in `Creating|Queuing|Running`.

### 2. List / Get / Events / Logs / Metrics

```bash
# List jobs by status
aliyun pai-dlc list-jobs --region <region> --status Running --page-size 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get job detail
aliyun pai-dlc get-job --region <region> --job-id <job-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get pod logs (job must be Running or completed)
aliyun pai-dlc get-pod-logs --region <region> --job-id <job-id> --pod-id <pod-id> --max-lines 100 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get job/pod events
aliyun pai-dlc get-job-events --region <region> --job-id <job-id> --max-events-num 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
aliyun pai-dlc get-pod-events --region <region> --job-id <job-id> --pod-id <pod-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get GPU metrics (job must be Running)
aliyun pai-dlc get-job-metrics --region <region> --job-id <job-id> --metric-type GpuCoreUsage --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

**Expect:** All return valid data arrays. Logs contain stdout/stderr. Events sorted by time.

### 3. Update / Stop

```bash
# Update priority (Running jobs only)
aliyun pai-dlc update-job --region <region> --job-id <job-id> --priority 5 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Stop (Running → Stopping → Stopped)
aliyun pai-dlc stop-job --region <region> --job-id <job-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

**Expect:** Stop returns success, status transitions to `Stopped`.

### 4. Health Check (only when `EnableSanityCheck` is enabled)

```bash
aliyun pai-dlc list-job-sanity-check-results --region <region> --job-id <job-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
aliyun pai-dlc get-job-sanity-check-result --region <region> --job-id <job-id> --sanity-check-number 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

---

## Job Status Troubleshooting

Status lifecycle: `Creating → Queuing → (Bidding) → EnvPreparing → SanityChecking → Running → (Restarting) → Stopping → Succeeded/Failed/Stopped`

| Status | Cause | Debug |
|--------|-------|-------|
| Queuing | Insufficient resources | Check `ReasonMessage` via `get-job` |
| EnvPreparing | Image pulling | Check pod events |
| Failed | Execution error | Check job events + pod logs |
| Stopping/Restarting | Transitional | Wait for stable state |

```bash
# Debug: enable verbose logging
aliyun pai-dlc <command> --region <region> --log-level=debug --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Dry-run (no actual execution)
aliyun pai-dlc <command> --region <region> --cli-dry-run --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Common Errors

| Error | Fix |
|-------|-----|
| `NotFound` | Verify JobId is correct |
| `InvalidParameter` | Check parameter format via `--help` |
| `Forbidden.RAM` | Add RAM permissions (see ram-policies.md) |
| `Throttling` | Reduce request frequency |
| `ServiceUnavailable` | Retry later |

---

## Resource Discovery → CreateJob End-to-End

Verifies the full "query → fill → create → verify → cleanup" workflow using AIWorkSpace resource discovery APIs.

### Pre-flight

```bash
aliyun aiworkspace --help >/dev/null 2>&1 || aliyun plugin install --names aliyun-cli-aiworkspace
```

### Step 1: Discover Resources

```bash
WORKSPACE_ID=$(aliyun aiworkspace list-workspaces \
  --region <region> --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Workspaces[0].WorkspaceId' --output text)

IMAGE_URI=$(aliyun aiworkspace list-images \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Images[0].ImageUri' --output text)

DATASET_ID=$(aliyun aiworkspace list-datasets \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'Datasets[0].DatasetId' --output text)

CODE_SOURCE_ID=$(aliyun aiworkspace list-code-sources \
  --region <region> --workspace-id $WORKSPACE_ID --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'CodeSources[0].CodeSourceId' --output text)
```

**Expect:** All five variables non-empty. `ImageUri` is full image address. If any optional resource is absent, omit the corresponding field in Step 2.

### Step 2: Create Job with Discovered Resources

> ⚠️ When using `--resource-id` (dedicated quota), use `ResourceConfig` NOT `EcsSpec`. For pay-as-you-go, use `EcsSpec` without `--resource-id`.

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
  --cli-query 'JobId' --output text)
```

**Expect:** Valid `JobId` (`dlcXXXXXXXX`).

### Step 3: Verify

```bash
# Verify status
aliyun pai-dlc get-job --region <region> --job-id $JOB_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Status:Status,WorkspaceId:WorkspaceId,ResourceId:ResourceId}'
```

**Expect:** Status → `Running` or `Succeeded`. `WorkspaceId`/`ResourceId` match discovery values.

### Resource Discovery Checklist

- [ ] `aliyun aiworkspace list-workspaces --help` returns exit 0
- [ ] All five variables (WorkspaceId, QuotaId, ImageUri, DatasetId, CodeSourceId) non-empty
- [ ] Step 2 returns valid `JobId`
- [ ] Step 3 status is `Creating|Queuing|EnvPreparing|Running|Succeeded`
- [ ] No ROA calls appear in the workflow
- [ ] EcsSpec/ResourceConfig mutual exclusion respected

---

## JobTemplate CRUD End-to-End

Verifies the full lifecycle of 5 JobTemplate APIs (CreateJobTemplate / GetJobTemplate / ListJobTemplates / UpdateJobTemplate / SetJobTemplateDefaultVersion).

> **Plugin:** `aliyun-cli-pai-dlc` >= 0.3.1. Verify: `aliyun pai-dlc create-job-template --help`.
> **Constraints format:** `--constraints '{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"locked\",\"JobType\":\"locked\"}'`.

### Pre-flight

```bash
aliyun pai-dlc create-job-template --help >/dev/null 2>&1 || aliyun plugin update --name aliyun-cli-pai-dlc
aliyun plugin list | grep aliyun-cli-pai-dlc
```

### Step 1: Create Template

```bash
TEMPLATE_CONTENT=$(cat <<'EOF'
{
  "JobType": "PyTorchJob",
  "JobSpecs": [{"Type": "Worker", "PodCount": 1, "Image": "<ImageUri-from-list-images>", "EcsSpec": "ecs.gn6i-c4g1.xlarge"}],
  "UserCommand": "python -c 'print(123)'"
}
EOF
)

CREATE_RESP=$(aliyun pai-dlc create-job-template \
  --region <region> --workspace-id $WORKSPACE_ID \
  --template-name "e2e-verify-$(date +%s)" \
  --content "$TEMPLATE_CONTENT" \
  --description "Template for CRUD verification" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job)
TEMPLATE_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['TemplateId'])")
```

**Expect:** Non-empty `TemplateId` (`tplxxxxxxxxxx`), `Version=1`, `DefaultVersion=1`.

### Step 2: List & Detail

```bash
# List
aliyun pai-dlc list-job-templates --region <region> --workspace-id $WORKSPACE_ID --template-id $TEMPLATE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'JobTemplates[*].{Id:TemplateId,Name:TemplateName,Default:DefaultVersion}'

# Detail (default version)
aliyun pai-dlc get-job-template --region <region> --template-id $TEMPLATE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Id:TemplateId,Default:DefaultVersion,Total:TotalCount,Versions:Versions[*].Version}'
```

**Expect:** List returns 1 record with `DefaultVersion=1`. Detail: `TotalCount=1`, `Versions=[1]`, Content matches input.

### Step 3: Update (New Version)

```bash
# 3.1 Metadata only (no new version)
aliyun pai-dlc update-job-template --region <region> --template-id $TEMPLATE_ID \
  --description "Updated description" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{VersionCreated:VersionCreated,DefaultVersion:DefaultVersion}'

# 3.2 Content → new version
NEW_CONTENT=$(echo "$TEMPLATE_CONTENT" | python3 -c "import sys,json;c=json.load(sys.stdin);c['UserCommand']='python train.py';print(json.dumps(c))")
aliyun pai-dlc update-job-template --region <region> --template-id $TEMPLATE_ID \
  --content "$NEW_CONTENT" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Version:Version,VersionCreated:VersionCreated,DefaultVersion:DefaultVersion}'
```

**Expect:** 3.1: `VersionCreated=false`, `DefaultVersion=1`. 3.2: `Version=2`, `VersionCreated=true`, `DefaultVersion=1`.

### Step 4: Switch Default Version

```bash
aliyun pai-dlc set-job-template-default-version \
  --region <region> \
  --template-id $TEMPLATE_ID --biz-version 2 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{DefaultVersion:DefaultVersion}'

# Verify
aliyun pai-dlc get-job-template --region <region> --template-id $TEMPLATE_ID --biz-version all \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Default:DefaultVersion,Total:TotalCount}'
```

**Expect:** `DefaultVersion=2`, `TotalCount=2`.

### Step 5: Create Job from Template

```bash
JOB_ID=$(aliyun pai-dlc create-job \
  --region <region> --workspace-id $WORKSPACE_ID \
  --display-name "from-template-$(date +%s)" --template-id $TEMPLATE_ID \
  --user-command 'python train.py --epochs 1' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job --cli-query 'JobId' --output text)

aliyun pai-dlc get-job --region <region> --job-id $JOB_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Status:Status,JobSpecsImage:JobSpecs[0].Image}'
```

**Expect:** Valid `JobId`. `JobSpecs[0].Image` matches template ImageUri (not overridden in create-job).

> Note: Without `--constraints`, field lock is agent-side only. Use `--constraints` for server-side enforcement.

### JobTemplate Checklist

- [ ] `aliyun pai-dlc create-job-template --help` returns exit 0; plugin >= 0.3.1
- [ ] Step 1: non-empty `TemplateId`, `Version=1`, `DefaultVersion=1`
- [ ] Step 2: list/detail fields match creation params
- [ ] Step 3.1: `VersionCreated=false`; Step 3.2: `Version=2`, `VersionCreated=true`
- [ ] Step 4: `DefaultVersion` switched to `2`
- [ ] Step 5: template fields retained unless overridden
- [ ] No ROA calls anywhere in the workflow
