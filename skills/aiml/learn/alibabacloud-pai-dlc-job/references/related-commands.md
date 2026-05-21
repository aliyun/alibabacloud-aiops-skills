# Related CLI Commands

Flat list of every `aliyun` CLI command used by this skill.

All API-invoking commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`.
Client-side helpers (`version`, `configure`, `plugin`, `--help`) do not invoke remote
APIs and therefore do not require the flag.

## Client-Side Helpers (no API call)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| (CLI itself) | `aliyun version` | Print Aliyun CLI version (must be >= 3.3.1) |
| (CLI itself) | `aliyun configure list` | Show currently configured profiles (no AK/SK values) |
| (CLI itself) | `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| (CLI itself) | `aliyun plugin list` | List installed plugins |
| (CLI itself) | `aliyun plugin install --names aliyun-cli-pai-dlc` | Install pai-dlc plugin |
| (CLI itself) | `aliyun plugin install --names aliyun-cli-pai-dlc --version 0.3.1` | Pin pai-dlc plugin version |
| (CLI itself) | `aliyun plugin install --names aliyun-cli-aiworkspace` | Install aiworkspace plugin |
| (CLI itself) | `aliyun plugin update --name aliyun-cli-pai-dlc` | Upgrade pai-dlc plugin to latest |
| (CLI itself) | `aliyun pai-dlc --help` | Probe whether pai-dlc plugin is installed |
| (CLI itself) | `aliyun aiworkspace --help` | Probe whether aiworkspace plugin is installed |
| (CLI itself) | `aliyun pai-dlc <subcommand> --help` | Show parameters for any pai-dlc subcommand |

## PAI-DLC Job APIs (`pai-dlc` plugin, API version 2020-12-03)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| pai-dlc | `aliyun pai-dlc create-job` | Create a distributed training job |
| pai-dlc | `aliyun pai-dlc list-jobs` | List jobs with optional `--status` filter |
| pai-dlc | `aliyun pai-dlc get-job` | Get full job detail by `--job-id` |
| pai-dlc | `aliyun pai-dlc update-job` | Update mutable fields (priority, name, etc.) |
| pai-dlc | `aliyun pai-dlc stop-job` | Stop a Running / Queuing job (high-risk) |
| pai-dlc | `aliyun pai-dlc get-pod-logs` | Fetch container logs (limit with `--max-lines`) |
| pai-dlc | `aliyun pai-dlc get-pod-events` | Fetch pod-level Kubernetes events |
| pai-dlc | `aliyun pai-dlc get-job-events` | Fetch job-level system events |
| pai-dlc | `aliyun pai-dlc get-job-metrics` | Fetch metric data (`GpuCoreUsage`, `MemoryUsage`, etc.) |
| pai-dlc | `aliyun pai-dlc list-job-sanity-check-results` | List GPU sanity check results |
| pai-dlc | `aliyun pai-dlc get-job-sanity-check-result` | Get one sanity check result by `--sanity-check-number` |
| pai-dlc | `aliyun pai-dlc get-web-terminal` | Get a Web Terminal URL for a running pod |
| pai-dlc | `aliyun pai-dlc get-token` | Get a sharing token for a job (read-only delegation) |
| pai-dlc | `aliyun pai-dlc list-ecs-specs` | List available ECS instance types (`--accelerator-type GPU` etc.) |

## PAI-DLC TensorBoard APIs (`pai-dlc` plugin)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| pai-dlc | `aliyun pai-dlc create-tensorboard` | Create a TensorBoard instance from a job or dataset |
| pai-dlc | `aliyun pai-dlc get-tensorboard` | Get TensorBoard instance detail |
| pai-dlc | `aliyun pai-dlc list-tensorboards` | List TensorBoard instances (filterable by `--job-id`) |
| pai-dlc | `aliyun pai-dlc start-tensorboard` | Start a stopped TensorBoard instance |
| pai-dlc | `aliyun pai-dlc stop-tensorboard` | Stop a running TensorBoard instance |
| pai-dlc | `aliyun pai-dlc update-tensorboard` | Update TensorBoard visibility / name / timeout |
| pai-dlc | `aliyun pai-dlc get-tensorboard-shared-url` | Generate a shareable TensorBoard link |
| pai-dlc | `aliyun pai-dlc get-dashboard` | Get DLC job dashboard URL (RayJob only) |
| pai-dlc | `aliyun pai-dlc get-ray-dashboard` | Get Ray dashboard URL with optional sharing |

## PAI-DLC JobTemplate APIs (`pai-dlc` plugin >= 0.3.1)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| pai-dlc | `aliyun pai-dlc create-job-template` | Create a reusable job template (Version=1) |
| pai-dlc | `aliyun pai-dlc get-job-template` | Get template detail; `--biz-version all` returns all versions |
| pai-dlc | `aliyun pai-dlc list-job-templates` | List templates in a workspace |
| pai-dlc | `aliyun pai-dlc update-job-template` | Update template (metadata-only or new content version) |
| pai-dlc | `aliyun pai-dlc set-job-template-default-version` | Switch the default version of a template |

## AIWorkSpace Resource Discovery (`aiworkspace` plugin, API version 2021-02-04)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| aiworkspace | `aliyun aiworkspace list-workspaces` | List available workspaces (yields `--workspace-id`) |
| aiworkspace | `aliyun aiworkspace list-images` | List images filterable by `--labels system.chipType=GPU` etc. (yields `Image`) |
| aiworkspace | `aliyun aiworkspace get-image` | Get a single image's full metadata |
| aiworkspace | `aliyun aiworkspace list-datasets` | List datasets in a workspace (yields `DataSourceId`) |
| aiworkspace | `aliyun aiworkspace get-dataset` | Get a single dataset's full metadata |
| aiworkspace | `aliyun aiworkspace list-code-sources` | List code sources in a workspace (yields `CodeSourceId`) |
| aiworkspace | `aliyun aiworkspace get-code-source` | Get a single code source's full metadata |

## Common Flags Used Across This Skill

| Flag | Used For | Example |
|------|----------|---------|
| `--region` | Target region (REQUIRED for every API call) | `--region cn-hangzhou` |
| `--workspace-id` | Target PAI Workspace | `--workspace-id 161278` |
| `--resource-id` | Dedicated Quota ID (when using `ResourceConfig`) | `--resource-id quotaXXX` |
| `--cli-query` | Server-side JMESPath projection on response | `--cli-query "Pods[0].PodId"` |
| `--page-size` / `--page-number` | Pagination | `--page-size 20 --page-number 1` |
| `--max-lines` | Limit log line count | `--max-lines 100` |
| `--max-events-num` | Limit event count | `--max-events-num 50` |
| `--download-to-file` | Stream large logs to disk | `--download-to-file true` |
| `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job` | REQUIRED on every API-invoking command | (see examples above) |

## Forbidden Patterns (Red Lines)

- **NEVER** use `--pathPattern` / `--method GET` / `--method POST` / `--method PUT` /
  `--method DELETE` (ROA generic fallback) — install/upgrade the proper plugin instead.
- **NEVER** invoke an `aliyun pai-dlc list-images` / `list-workspaces` /
  `list-datasets` / `list-code-sources` (these subcommands belong to the `aiworkspace`
  product, not `pai-dlc`).
- **NEVER** invoke an `aliyun aiworkspace create-job-template` / `list-job-templates`
  (these subcommands belong to the `pai-dlc` product, not `aiworkspace`).
- **NEVER** read or print AK/SK values; never run `aliyun configure set` with literal
  credential values.
