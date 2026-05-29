# Acceptance Criteria: alibabacloud-pai-dlc-job

**Scenario**: PAI-DLC Deep Learning Job Management
**Purpose**: Skill Testing Acceptance Criteria

> **Note on snippets in this file:** Sections 1-3 below show product names,
> command names, and parameter names as **pattern placeholders** (e.g.,
> `aliyun pai-dlc <command>`). These are fragments for mismatch detection,
> not complete executable commands. The Section 4 "User-Agent" rule (and the
> SKILL.md core workflow) require every API-invoking command to end with
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`; full executable examples carry it.

---

# Correct CLI Command Patterns

## 1. Product — Verify Product Name Exists

CORRECT
```bash
aliyun pai-dlc <command>
```

INCORRECT
```bash
aliyun pai <command>        # Error: product name should be pai-dlc
aliyun dlc <command>        # Error: product name should be pai-dlc
aliyun PAI-DLC <command>    # Error: case-sensitive, should use lowercase
```

## 2. Command — Verify Command Name Format

CORRECT (Plugin mode, lowercase with hyphens)
```bash
aliyun pai-dlc create-job
aliyun pai-dlc list-jobs
aliyun pai-dlc get-job
aliyun pai-dlc get-pod-logs
aliyun pai-dlc list-ecs-specs
aliyun pai-dlc get-web-terminal
aliyun pai-dlc stop-job
aliyun pai-dlc update-job
aliyun pai-dlc get-token
aliyun pai-dlc get-job-events
aliyun pai-dlc get-pod-events
aliyun pai-dlc get-job-sanity-check-result
aliyun pai-dlc list-job-sanity-check-results
```

INCORRECT (Traditional API format)
```bash
aliyun pai-dlc CreateJob       # Error: should use create-job
aliyun pai-dlc ListJobs        # Error: should use list-jobs
aliyun pai-dlc GetJob          # Error: should use get-job
aliyun pai-dlc GetPodLogs      # Error: should use get-pod-logs
```

## 3. Parameters — Verify Parameter Name Format

CORRECT (Lowercase with hyphens)
```bash
--job-id
--pod-id
--display-name
--job-type
--job-specs
--user-command
--workspace-id
--resource-id
--page-number
--page-size
--start-time
--end-time
--max-lines
--user-agent
```

INCORRECT (CamelCase or underscore)
```bash
--JobId            # Error: should use --job-id
--jobId            # Error: should use --job-id
--job_id           # Error: should use --job-id
--displayName      # Error: should use --display-name
--DisplayName      # Error: should use --display-name
```

## 4. User-Agent — Must Include Identifier

CORRECT
```bash
aliyun pai-dlc list-jobs --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

INCORRECT
```bash
aliyun pai-dlc list-jobs --region cn-hangzhou   # Error: missing --user-agent
```

## 5. JobSpecs Format — Verify JSON Structure

CORRECT - Method 1: EcsSpec (Public Resources)
```bash
--job-specs '[{"Type":"Worker","PodCount":1,"Image":"registry.cn-hangzhou.aliyuncs.com/pai-dlc/pytorch:1.12","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]'
```

CORRECT - Method 2: ResourceConfig (Dedicated Resource Group)
```bash
--job-specs '[{"Type":"Worker","PodCount":1,"Image":"registry.cn-hangzhou.aliyuncs.com/pai-dlc/pytorch:1.12","ResourceConfig":{"CPU":"4","Memory":"16Gi","GPU":"1"}}]'
```

INCORRECT
```bash
# Error: Not a valid JSON array
--job-specs '{"Type":"Worker"}'

# Error: Missing required fields
--job-specs '[{"Type":"Worker"}]'

# Error: Incorrect field name case
--job-specs '[{"type":"Worker","podCount":1}]'

# Error: EcsSpec and ResourceConfig set simultaneously (mutually exclusive!)
--job-specs '[{"Type":"Worker","PodCount":1,"Image":"...","EcsSpec":"ecs.gn6i-c4g1.xlarge","ResourceConfig":{"CPU":"4"}}]'
```

## 6. Job Status — Verify Case & Spelling (NOT an exhaustive enum)

> **Authoritative enum source:** `aliyun pai-dlc list-jobs --help`. This section
> only verifies case-sensitivity and spelling conventions — do NOT treat the
> samples below as the complete list of legal `--status` values.

CORRECT (representative samples — server accepts more, e.g. `Bidding`,
`EnvPreparing`, `SanityChecking`, `SucceededReserving`, `FailedReserving`)
```bash
--status Creating
--status Running
--status Succeeded
--status Failed
```

INCORRECT
```bash
--status creating     # Error: first letter should be uppercase
--status RUNNING      # Error: should use Running
--status success      # Error: should use Succeeded
```

## 7. Job Type — Verify Job Types

CORRECT
```bash
--job-type TFJob
--job-type PyTorchJob
--job-type XGBoostJob
--job-type OneFlowJob
--job-type ElasticBatchJob
```

INCORRECT
```bash
--job-type tensorflow    # Error: should use TFJob
--job-type pytorch       # Error: should use PyTorchJob
--job-type tf-job        # Error: should use TFJob
```

---

# Credential Patterns

## 1. Credential Verification — Must Use Secure Method

CORRECT
```bash
# Only check configuration status
aliyun configure list
```

INCORRECT
```bash
# Error: Prohibited from printing credential values
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET

# Error: Prohibited from using plaintext credentials in command line
aliyun configure set --access-key-id LTAI5tXXXX --access-key-secret 8dXXXX
```

---

# Complete Command Examples

## Create Job

CORRECT - EcsSpec (Public Resources)
```bash
aliyun pai-dlc create-job \
  --region cn-hangzhou \
  --display-name "my-training-job" \
  --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"registry.cn-hangzhou.aliyuncs.com/pai-dlc/pytorch-training:1.12-gpu-py38-cu113-ubuntu20.04","EcsSpec":"ecs.gn6i-c4g1.xlarge"}]' \
  --user-command "python train.py" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

CORRECT - ResourceConfig (Dedicated Resource Group)
```bash
aliyun pai-dlc create-job \
  --region cn-hangzhou \
  --resource-id <resource-group-id> \
  --display-name "my-training-job" \
  --job-type PyTorchJob \
  --job-specs '[{"Type":"Worker","PodCount":1,"Image":"registry.cn-hangzhou.aliyuncs.com/pai-dlc/pytorch-training:1.12-gpu-py38-cu113-ubuntu20.04","ResourceConfig":{"CPU":"4","Memory":"16Gi","GPU":"1","GPUType":"NVIDIA-V100"}}]' \
  --user-command "python train.py" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## List Jobs

CORRECT
```bash
aliyun pai-dlc list-jobs \
  --region cn-hangzhou \
  --status Running \
  --page-number 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## Get Logs

CORRECT
```bash
aliyun pai-dlc get-pod-logs \
  --region cn-hangzhou \
  --job-id dlc12345678 \
  --pod-id dlc12345678-worker-0 \
  --max-lines 500 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## Stop Job

CORRECT
```bash
# Stop job
aliyun pai-dlc stop-job \
  --region cn-hangzhou \
  --job-id dlc12345678 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

---

# Testing Checklist

- [ ] All commands use plugin mode format (lowercase with hyphens)
- [ ] All commands include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`
- [ ] No hardcoded user-specific parameters (RegionId, JobId, etc. need user confirmation)
- [ ] Credential operations only use `aliyun configure list` for checking
- [ ] JobSpecs use correct JSON array format
- [ ] Enum values use correct case
- [ ] All required parameters provided

---

# AIWorkSpace Resource Discovery Command Standards

This section covers the 8 AIWorkSpace 2021-02-04 query APIs needed before creating a DLC job. All commands MUST be invoked through the `aliyun-cli-aiworkspace` plugin, and subcommands MUST use the lowercase + hyphen format.

## 8. AIWorkSpace Plugin Query Commands — Verify Subcommand Spelling

CORRECT (lowercase + hyphen subcommands exposed by the plugin)
```bash
aliyun aiworkspace list-workspaces --region cn-hangzhou --page-number 1 --page-size 20
aliyun aiworkspace list-images --region cn-hangzhou --workspace-id <WORKSPACE_ID>
aliyun aiworkspace get-image --region cn-hangzhou --image-id <IMAGE_ID>
aliyun aiworkspace list-datasets --region cn-hangzhou --workspace-id <WORKSPACE_ID>
aliyun aiworkspace get-dataset --region cn-hangzhou --dataset-id <DATASET_ID>
aliyun aiworkspace list-code-sources --region cn-hangzhou --workspace-id <WORKSPACE_ID>
aliyun aiworkspace get-code-source --region cn-hangzhou --code-source-id <CODE_SOURCE_ID>
```

INCORRECT — ROA Generic Fallback Invocation (Red Line, Forbidden)
```bash
# Forbidden: invoking with the HTTP method + path-pattern ROA generic form
aliyun aiworkspace ListImages --version 2021-02-04 --method GET --pathPattern /api/v1/images --header Content-Type=application/json

# Forbidden: the same ROA fallback is also disallowed on the PAI-DLC side
aliyun pai-dlc CreateJob --version 2020-12-30 --method POST --pathPattern /api/v1/jobs --body '{...}'
```

INCORRECT — Wrong Product Name
```bash
# Error: resource discovery APIs belong to the aiworkspace product, not pai-dlc
aliyun pai-dlc list-images --workspace-id <id>
aliyun pai-dlc list-datasets --workspace-id <id>
aliyun pai-dlc list-workspaces
```

INCORRECT — Does Not Conform to lowercase + hyphen Convention
```bash
# Error: missing hyphen
aliyun aiworkspace listimages --workspace-id <id>
aliyun aiworkspace listdatasets --workspace-id <id>

# Error: using camelCase / PascalCase / underscore naming
aliyun aiworkspace ListImages --workspace-id <id>
aliyun aiworkspace List-Images --workspace-id <id>
aliyun aiworkspace list_images --workspace-id <id>
```

## 9. AIWorkSpace Command Parameters — Use kebab-case

CORRECT
```bash
--workspace-id
--image-id
--dataset-id
--code-source-id
--page-number
--page-size
--workspace-ids       # list-workspaces only, multiple IDs separated by commas
--display-name        # filter parameter for list-code-sources
--data-source-types   # filter parameter for list-datasets (NAS / OSS)
```

INCORRECT
```bash
--WorkspaceId            # Error: should use --workspace-id
--imageId                # Error: should use --image-id
--code_source_id         # Error: should use --code-source-id
```

## 10. Resource Discovery -> CreateJob Value Mapping

CORRECT — Look up first, then construct; use plugin return values as CreateJob parameters
```bash
# Look up WorkspaceId
WORKSPACE_ID=$(aliyun aiworkspace list-workspaces --region cn-hangzhou \
  --cli-query 'Workspaces[0].WorkspaceId')

# QuotaId (`--resource-id`) is manually provided by the user

# Look up ImageUri
IMAGE_URI=$(aliyun aiworkspace list-images --region cn-hangzhou --workspace-id $WORKSPACE_ID \
  --cli-query 'Images[0].ImageUri')
```

INCORRECT — Querying ImageUri from the pai-dlc product (wrong product)
```bash
# Do not query images under the pai-dlc product; ImageUri can only come from AIWorkSpace.ListImages
aliyun pai-dlc list-images --workspace-id $WORKSPACE_ID
```

---

# Red Line: ROA Generic Fallback Invocations Are Forbidden

> **Per the user's decision for this task**: Within this skill, using the HTTP method + path-pattern ROA generic fallback invocation is strictly forbidden.

## Scope

This red line applies to all of the following:

- The 7 AIWorkSpace resource discovery APIs (`ListImages` / `GetImage` / `ListDatasets` / `GetDataset` / `ListCodeSources` / `GetCodeSource` / `ListWorkspaces`). `--resource-id` (QuotaId) is manually provided by the user.
- All PAI-DLC job APIs (`CreateJob` / `ListJobs` / ...).

## Violation Examples (Must Never Appear in Correct Examples)

```bash
# Using the ROA generic form to assemble any AIWorkSpace / PAI-DLC API
aliyun aiworkspace ListImages --version 2021-02-04 --method GET --pathPattern /api/v1/images
aliyun aiworkspace GetDataset --version 2021-02-04 --method GET --pathPattern /api/v1/datasets/{DatasetId}
aliyun pai-dlc CreateJob --version 2020-12-30 --method POST --pathPattern /api/v1/jobs --body '{...}'
```

## Correct Approach

- The skill MUST rely solely on the lowercase + hyphen subcommands exposed by the plugin.
- If a particular plugin subcommand is unavailable (`unknown command`), run `aliyun plugin update --name aliyun-cli-pai-dlc` or `aliyun plugin install --names aliyun-cli-aiworkspace` to reinstall/upgrade the plugin. If it remains unavailable, stop and ask the user to intervene; **do NOT construct ROA invocations on your own**.
