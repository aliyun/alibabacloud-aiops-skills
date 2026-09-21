---
name: lhm-sch-deploy
description: LHM schedule migration deployment (write → DataWorks): trigger deployment, poll progress, fetch results, and generate reports. Completes end-to-end deployment through three LHM APIs (SubmitStart to trigger → SubmitInstanceList to poll until ALL_SUCCESS → TaskWriterWorkflowList to fetch per-workflow results), and outputs structured JSON + Markdown reports. Use when the user mentions "部署", "deploy", "提交到 DataWorks" (submit to DataWorks), "发布工作流" (publish workflows), "触发 LHM 部署" (trigger LHM deployment), "查看部署状态" (check deployment status), "deploy 阶段" (deploy stage), or "部署报告" (deployment report). Not applicable to: the schedule exploration/conversion stages (use lhm-scheduler-cli), SQL conversion (use sql-trans), or DDL migration (use ddl-trans). Known limitations: depends on the LHM platform APIs and does not support offline deployment; result-package download (write_verify_report) is not yet integrated — currently only workflow-level results are obtained via the API.
---

# LHM Schedule Migration Deployment Skill

This skill triggers and monitors LHM schedule migration deployment tasks, automatically polls until deployment completes, and generates detailed deployment reports.

## Prerequisites

**The environment and credentials have already been prepared by [lhm-sch-env](../lhm-sch-env/SKILL.md) at session start; this skill performs no environment validation whatsoever.**
Simply run the deployment command — do not run validation scripts, do not re-confirm credentials, and do not prompt the user about configuration.

> ⛔ **The one exception — the `aliyun-cli-lhm` plugin (hard stop)**: the deployment command reaches the service through `aliyun lhm <command>`, so the plugin (>= 0.1.1, i.e. `~/.aliyun/plugins/aliyun-cli-lhm/manifest.json` exists) must be present. If it is not, **stop immediately**: report the environment error verbatim and terminate. Do **not** prompt the user for a deployment parameter, do **not** run `uv tool install` or `lhm-sch-deploy` — this CLI shells out to `aliyun lhm`, so a successful install is never proof that the flow can proceed — and never report a deployment or upload result that did not come from a real call.

Only when a command actually reports an environment-class error should it be handed to [lhm-sch-env](../lhm-sch-env/SKILL.md).

For reference: credentials are resolved by the aliyun CLI default credential chain (`aliyun configure` / environment variables / RAM Role / `~/.alibabacloud/credentials`) at call time — this skill neither reads nor stores any AK/SK, and the startup banner no longer prints a credential source. The CLI is installed as a uv global tool: `bash install.sh` to install, `bash uninstall.sh` to uninstall.

## Usage

### Basic Usage

```bash
lhm-sch-deploy --task-id <YOUR_TASK_ID>
```

### Full Parameters

```bash
lhm-sch-deploy \
  --task-id <TASK_ID> \
  --config config/deploy_config.json \
  --output-dir <session dir>/output/deploy/result \
  --endpoint lhm-pre.cn-hangzhou.aliyuncs.com \
  --region cn-hangzhou \
  --poll-interval 15 \
  --timeout 1800
```

### Parameter Descriptions

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--task-id` | Migration task ID (optional; when missing, resolved in order from session config / environment variable / config file) | - |
| `--config` | Config file path (relative to the current working directory) | `config/deploy_config.json` |
| `--output-dir` | Output directory | `<session dir>/output/deploy/result/<timestamp>/` |
| `--endpoint` | LHM service endpoint, attached to every `aliyun lhm` call as a fixed parameter (resolved in order: session config `lhm.endpoint` > config file `lhm.endpoint` > `LHM_ENDPOINT` environment variable > default) | `lhm-pre.cn-hangzhou.aliyuncs.com` |
| `--region` | Region, attached to every `aliyun lhm` call as a fixed parameter (resolved in order: session config `lhm.region_id` > config file `lhm.region_id` > `REGION_ID` environment variable > default) | `cn-hangzhou` |
| `--poll-interval` | Polling interval (seconds) | 15 |
| `--timeout` | Timeout (seconds) | 1800 |
| `--skip-start` | Skip the trigger step and poll the existing instance directly | false |

### Output Directory Structure

The CLI is installed as a global tool with the code directory separated from the runtime directory. By default it outputs to `<session dir>/output/deploy/result/<timestamp>/` under the **session temp directory** (same root as the session config `session.json`). The session temp directory (abbreviated `<session dir>` below) is a per-session dedicated `/tmp/lhm-sch-session-<uid>/s-<timestamp>-<random>/`, which the CLI locates automatically via the pointer file `current` (or `$LHM_SESSION_FILE`):

```
<session dir>/output/deploy/result/20260115_143022/
├── deploy_result_summary.json       # structured report data
├── workflow_list.json               # raw workflow list data
├── deploy_report.md                 # detailed Markdown report
├── package.zip                      # raw result package
└── package/                         # extracted result package
    ├── write_verify_report.json     # read-back verification report
    ├── workflow.json                # workflow configuration
    ├── nodeSpec.json               # node specifications
    ├── nodeRelationSpec.json       # node dependencies
    ├── trigger.json                # trigger configuration
    └── script/                     # script files
```

**Output path precedence**: CLI `--output-dir` > config file `output_dir` > default session temp directory (`<session dir>/output/deploy/result/<timestamp>/`)

## Config File

The config file (by default `config/deploy_config.json` in the current working directory; overridable with `--config`) persists commonly used parameters:

```json
{
  "task_id": "your-task-id",
  "lhm": {
    "endpoint": "lhm-pre.cn-hangzhou.aliyuncs.com",
    "region_id": "cn-hangzhou"
  },
  "poll_interval_seconds": 15,
  "timeout_seconds": 1800
}
```

> The optional field `output_dir` can override the output location; when unset, output defaults to the session temp directory `<session dir>/output/deploy/result/`.

A config file can be created by copying the template `config/deploy_config.template.json`.

## Workflow

The deployment script executes in the following 6 phases:
### Phase 1: Trigger Deployment

Calls the `GetBwmMigrationWorkflowSubmitStart` API to trigger the deployment task.

- **Input**: task_id
- **Output**: trigger success/failure status
- **Skip**: use `--skip-start` to skip this step (reconnection scenarios)

### Phase 2: Poll and Wait

Calls the `GetBwmMigrationSubmitInstanceList` API to poll the deployment instance status.

- **Strategy**: take the first record in the returned list (the latest instance)
- **Termination conditions**: `ALL_SUCCESS` (success) / `FAILED|CANCELLED|TERMINATED` (failure) / timeout
- **Polling interval**: 15 seconds by default
- **Fault tolerance**: abort after 3 consecutive API failures

**Instance status descriptions**:

| Status | Meaning |
|--------|---------|
| `ALL_SUCCESS` | All successful (terminal) |
| `RUNNING` | Running |
| `SUBMITTING` | Submitting |
| `WAITING` | Waiting |
| `INIT` | Initializing |
| `PARTIAL_SUCCESS` | Partially successful |
| `FAILED` | Failed (terminal) |
| `CANCELLED` | Cancelled (terminal) |
| `TERMINATED` | Terminated (terminal) |

### Phase 3: Fetch Workflow Results

Calls the `GetBwmMigrationTaskWriterWorkflowList` API to fetch the deployment result of each workflow (with automatic pagination).

- **Input**: instance_id (obtained from Phase 2)
- **Output**: workflow list, including name, status, node count, schedule configuration, etc.

### Phase 4: Generate the Base Report

Generates the structured JSON report and the console Markdown summary table.

**Output files**:
- `deploy_result_summary.json` - complete structured report data
- `workflow_list.json` - raw workflow list data

### Phase 5: Download the Result Package

Downloads the deployment result zip package via a presigned URL and extracts it.

**Output**:
- `package.zip` - raw result package
- `package/` - extracted directory, containing:
  - `write_verify_report.json` - read-back verification report
  - `workflow.json` - detailed workflow configuration
  - `nodeSpec.json` - node specifications
  - `nodeRelationSpec.json` - node dependencies
  - `trigger.json` - trigger configuration
  - `script/` - script files

### Phase 6: Generate the Detailed Report

Generates the complete Markdown report based on the result package.

**Output files**:
- `deploy_report.md` - includes read-back verification results, workflow details, node dependencies, script previews, etc.

## Exit Codes

| Exit code | Meaning | Scenario |
|-----------|---------|----------|
| 0 | Success | Deployment completed and all workflows succeeded |
| 1 | Config/credential error | Missing task_id, credentials not resolved by the aliyun CLI, network error |
| 2 | Polling timeout | Not completed within the timeout period |
| 3 | Deployment failed | Instance status is a terminal state such as FAILED/CANCELLED |

## Reconnection After Disconnection

If the connection drops during deployment, use the `--skip-start` parameter to skip the trigger step and poll the existing instance directly:

```bash
lhm-sch-deploy --task-id <TASK_ID> --skip-start
```

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LHM 调度迁移部署
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  任务ID:  task_abc123
  端点:    lhm-pre.cn-hangzhou.aliyuncs.com
  输出目录: /tmp/lhm-sch-session-501/output/deploy/result/20260115_143022

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1/4] 触发部署...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ 部署已触发

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [2/4] 等待部署完成...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  任务ID: task_abc123
  轮询间隔: 15s / 超时: 1800s
  [00:00] ⏳ 状态: 提交中
  [00:15] ⏳ 状态: 运行中
  [00:30] ⏳ 状态: 运行中
  [00:45] ✅ 状态: 全部成功

  ✅ 部署完成！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [3/4] 获取工作流部署结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  实例ID: instance_xyz789
  共 3 个工作流，3 个成功，0 个失败，合计 9 个节点

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [4/4] 生成报告...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📄 /tmp/lhm-sch-session-501/output/deploy/result/20260115_143022/deploy_result_summary.json
  📄 /tmp/lhm-sch-session-501/output/deploy/result/20260115_143022/workflow_list.json


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  部署结果汇总
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务ID: task_abc123
状态:   ✅ 全部成功
时间:   2026-01-15 14:30:22

| 工作流名称                 | 目标工作流                 | 状态       |   节点数 | 调度                 |
|---------------------------|---------------------------|------------|---------|---------------------|
| daily_etl_job             | daily_etl_job             | ✅ 成功    |       5 | 0 0 2 * * ?         |
| hourly_sync_task          | hourly_sync_task          | ✅ 成功    |       3 | 0 0 * * * ?         |
| weekly_report_gen         | weekly_report_gen         | ✅ 成功    |       1 | 0 0 8 ? * MON       |

结果文件已保存至: /tmp/lhm-sch-session-501/output/deploy/result/20260115_143022
```

## Troubleshooting

### 1. Credential Error

**Error**: the `aliyun lhm` call reports a credential/authentication error (invalid or missing credentials). Credentials are resolved by the aliyun CLI default credential chain, not by this skill.

**Solution**: this is an environment-class issue; hand it to [lhm-sch-env](../lhm-sch-env/SKILL.md). Ensure the default credential chain is configured (`aliyun configure`, environment variables, or RAM Role) and that RAM permissions include LHM. For handling common accompanying warnings (overly broad permissions, malformed JSON, unreplaced placeholders), see the "Common Warnings" table in lhm-sch-env.

### 2. Missing task_id

**Error**: `未指定 task_id` (task_id not specified)

**Solution** (from highest to lowest precedence):
- Specify on the command line: `--task-id <YOUR_TASK_ID>`
- Complete the stage 3 conversion first: after `convert-start` succeeds, `convert_task_id` is automatically written back into the session config, and this CLI uses it directly
- Environment variable: `export TASK_ID=<ID>`
- Or set the `task_id` field in the config file

> If this error persists after stage 3 completes, common causes are: the session config was cleaned up
> by `--cleanup`, or the source/target data source was changed mid-flow causing the old task_id to be
> discarded.

### 3. Polling Timeout

**Error**: `部署等待超时（1800s）` (deployment wait timed out, 1800s)

**Solution**:
- Increase the timeout: `--timeout 3600`
- Or use `--skip-start` to resume polling

### 4. Deployment Failed

**Error**: `部署终止: FAILED` (deployment terminated: FAILED)

**Solution**:
- Inspect the instance's `detail` field to understand the failure reason
- Check the task logs in the LHM console
- Fix the issue and trigger the deployment again

## Relationship with Other Skills

This skill is the final step of the schedule migration flow:

1. **migration-sdm-lhm-scheduler** - reads the source scheduler configuration
2. **migration-sdm-sql-trans** - SQL syntax conversion
3. **migration-sdm-lhm-deploy** (this skill) - deployment to DataWorks

## Technical Details

### Code Structure

```
lhm-sch-deploy/
├── pyproject.toml                 # uv install entry (hatchling build + local SDK sources)
├── install.sh / uninstall.sh      # uv tool install / uninstall
├── config/                        # default config template
└── scripts/lhm_deploy_cli/
    ├── cli.py                     # command-line entry and phase orchestration
    ├── client.py                  # LHM SDK client and API wrappers
    ├── report.py                  # result package download/parsing + report generation
    └── ui.py                      # terminal output and status mapping
```

### SDK Wrappers

The SDK client is wrapped in `scripts/lhm_deploy_cli/client.py`, providing the following functions:

- `create_client(endpoint, region_id)` - create the LHM SDK client
- `start_submit(client, task_id)` - trigger deployment
- `list_submit_instances(client, task_id)` - query the instance list
- `get_result_package_url(client, instance_id)` - get the presigned download URL of the result package
- `list_writer_workflows(client, instance_id)` - query workflow results
- `fetch_all_workflows(client, instance_id)` - fetch all workflows with automatic pagination

The SDK body is bundled inside `lhm-sch-workflowmigration/sdk/alibabacloud_lhm20250116_inner/` and included via `[tool.uv.sources]` in `pyproject.toml` in editable mode, with no intrusive `sys.path` manipulation.

### Status Mapping

The CLI maps the English statuses returned by the API to localized display labels (defined in `ui.py`):

```python
STATUS_CN = {
    "ALL_SUCCESS": ("✅", "全部成功"),
    "SUCCESS": ("✅", "成功"),
    "RUNNING": ("🔄", "进行中"),
    "SUBMITTING": ("📤", "提交中"),
    "WAITING": ("⏳", "等待中"),
    "FAILED": ("❌", "失败"),
    "CANCELLED": ("🚫", "已取消"),
}
```

## License

This skill is part of the migration-sdm project.
