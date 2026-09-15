# RAM Policies for Flink Python Job Submission

## Required Permissions

The following RAM permissions are required for the Flink Python Job Submission skill.

### RealtimeCompute (stream)

| RAM Action | Operation Type | Purpose |
|---|---|---|
| stream:DescribeVvpInstances | List | Detect workspace storage mode and bound OSS bucket, and retrieve the exact VVP console URL from `ClusterState.Url` |
| stream:CreateDeployment | Write | Create Python deployment, including its `flinkConf` Other Configuration |
| stream:GetDeployment | Read | Get deployment details |
| stream:UpdateDeployment | Write | Update Python deployment configuration |
| stream:ListEngineVersionMetadata | List | Read the workspace-recommended stable VVR engine version |
| stream:ListSavepoints | List | Check for completed checkpoint/savepoint state before choosing a default startup strategy |
| stream:StartJobWithParams | Write | Start job instance |
| stream:StopJob | Write | Stop running job |
| stream:GetLatestJobStartLog | Read | Get JM startup log |
| stream:FlinkApiProxy | Read | Proxy to Flink REST API (logs/metrics) |
| stream:ListDeployments | List | List deployments |

### OSS (user-managed storage only)

| RAM Action | Operation Type | Purpose |
|---|---|---|
| oss:PutObject | Write | Upload artifacts to OSS |
| oss:GetObject | Read | Verify uploaded artifacts |
| oss:ListObjects | List | List objects in bucket |
| oss:ListBuckets | List | Discover OSS buckets |

Fully managed artifact upload uses the signed-in VVP File Management page and does not use customer OSS permissions. The signed-in identity must have upload, supported in-place replacement, and read access in the target project space.

`flinkConf` is part of the `CreateDeployment` request body. Supplying it during
creation needs no separate UpdateDeployment API and adds no RAM action beyond
`stream:CreateDeployment`.

Changing an existing deployment uses `UpdateDeployment` and requires
`stream:UpdateDeployment`. The read-before-merge and verification calls also
require `stream:GetDeployment`.

`stream:ListEngineVersionMetadata` is required only when neither the user nor
the selected existing deployment supplies the engine version for a new
deployment.

`stream:ListSavepoints` is required when `start-job` is called without an
explicit restore strategy. A permission or API failure must block the start;
it must never be interpreted as proof that no restorable state exists.

The project-local deployment registry is a local Markdown file and requires no
Alibaba Cloud RAM permission.

---

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted
