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
  --display-name "verify-job" \
  --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"<ImageUri>","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]' \
  --user-command "python -c 'print(123)'" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query "JobId" --output text)
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

aliyun pai-dlc get-job-metrics --region <region> --job-id <job-id> \
  --metric-type GpuCoreUsage \
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
  --cli-query 'JobId' --output text)
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

---

## 3. JobTemplate CRUD (E2E)

Verifies the full lifecycle of all 6 JobTemplate APIs.

> **Plugin gate:** `aliyun-cli-pai-dlc` ≥ 0.3.1.
> **Constraints format:** `'{\"JobSpecs[0].Image\":\"locked\",...}'` (semantics
> in SKILL.md §7.7).

### 3.1 Pre-flight

```bash
aliyun pai-dlc create-job-template --help >/dev/null 2>&1 \
  || aliyun plugin update --name aliyun-cli-pai-dlc
aliyun plugin list | grep aliyun-cli-pai-dlc
```

### 3.2 Create

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

**Expect:** `TemplateId` matches `tpl[0-9a-z]+`; `Version=1`,
`DefaultVersion=1`.

### 3.3 List & Get

```bash
aliyun pai-dlc list-job-templates --region <region> \
  --workspace-id $WORKSPACE_ID --template-id $TEMPLATE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'JobTemplates[*].{Id:TemplateId,Name:TemplateName,Default:DefaultVersion}'

aliyun pai-dlc get-job-template --region <region> --template-id $TEMPLATE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Id:TemplateId,Default:DefaultVersion,Total:TotalCount,Versions:Versions[*].Version}'
```

**Expect:** list returns the new template; `TotalCount=1`, `Versions=[1]`.

### 3.4 Update — Two Modes

```bash
# 3.4.1 Metadata only (no new version)
aliyun pai-dlc update-job-template --region <region> --template-id $TEMPLATE_ID \
  --description "Updated description" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{VersionCreated:VersionCreated,DefaultVersion:DefaultVersion}'

# 3.4.2 New content → new version
NEW_CONTENT=$(echo "$TEMPLATE_CONTENT" | python3 -c "import sys,json;c=json.load(sys.stdin);c['UserCommand']='python train.py';print(json.dumps(c))")

aliyun pai-dlc update-job-template --region <region> --template-id $TEMPLATE_ID \
  --content "$NEW_CONTENT" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Version:Version,VersionCreated:VersionCreated,DefaultVersion:DefaultVersion}'
```

**Expect:** 3.4.1 → `VersionCreated=false`. 3.4.2 → `Version=2`,
`VersionCreated=true`, `DefaultVersion=1` (still).

### 3.5 Switch Default Version

```bash
aliyun pai-dlc set-job-template-default-version \
  --region <region> --template-id $TEMPLATE_ID --biz-version 2 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc get-job-template --region <region> --template-id $TEMPLATE_ID \
  --biz-version all \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Default:DefaultVersion,Total:TotalCount}'
```

**Expect:** `DefaultVersion=2`, `TotalCount=2`.

### 3.6 Launch Job from Template

```bash
JOB_ID=$(aliyun pai-dlc create-job \
  --region <region> --workspace-id $WORKSPACE_ID \
  --display-name "from-template-$(date +%s)" --template-id $TEMPLATE_ID \
  --user-command 'python train.py --epochs 1' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query 'JobId' --output text)

aliyun pai-dlc get-job --region <region> --job-id $JOB_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job \
  --cli-query '{Status:Status,JobSpecsImage:JobSpecs[0].Image}'
```

**Expect:** valid `JobId`; `JobSpecs[0].Image` matches the template (not
overridden by `create-job` since not passed).

> Without `--constraints`, field "lock" is agent-side only. Use
> `--constraints` for server-side enforcement.

### 3.7 JobTemplate Checklist

- [ ] Plugin ≥ 0.3.1 verified
- [ ] §3.2 `TemplateId` non-empty, `Version=1`
- [ ] §3.3 list / get fields match creation
- [ ] §3.4.1 `VersionCreated=false`; §3.4.2 `Version=2`, `VersionCreated=true`
- [ ] §3.5 `DefaultVersion` switched to 2
- [ ] §3.6 template fields retained on launch
- [ ] No ROA calls anywhere in the flow
