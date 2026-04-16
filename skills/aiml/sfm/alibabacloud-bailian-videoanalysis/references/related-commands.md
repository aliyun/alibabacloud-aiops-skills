# Related Commands: alibabacloud-bailian-videoanalysis

## Available Python Scripts

All scripts are located in the `scripts/` directory:

| Script | Purpose | Required Parameters | Optional Parameters |
|--------|---------|--------------------|--------------------|
| `check_env.py` | Check environment configuration (packages + credentials) | None | None |
| `list_workspace.py` | Query available Bailian workspaces | None | None |
| `quanmiao_upload_file_to_oss_and_get_file_url.py` | Upload file to OSS and get temporary URL | `--localFilePath` | `--ossBucket`, `--ossObjectKey`, `--expireSeconds` |
| `quanmiao_submit_videoAnalysis_task.py` | Submit video analysis task to Bailian | `--workspace_id`, `--file_url` | None |
| `quanmiao_get_videoAnalysis_task_result.py` | Get video analysis task result | `--workspace_id`, `--task_id` | None |

## Aliyun CLI Commands

| Command | Purpose |
|---------|---------|
| `aliyun version` | Verify CLI version (>= 3.3.1) |
| `aliyun configure list` | Check credential status (NEVER print AK/SK) |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| `aliyun oss rm oss://<bucket>/<key> --user-agent AlibabaCloud-Agent-Skills` | Delete uploaded OSS object (cleanup) |

## Execution Order

```
1. check_env.py
       ↓
2. list_workspace.py
       ↓
3. quanmiao_upload_file_to_oss_and_get_file_url.py
       ↓
4. quanmiao_submit_videoAnalysis_task.py
       ↓
5. quanmiao_get_videoAnalysis_task_result.py  (poll loop)
       ↓
6. Summarize (no script call, use Step 5 result directly)
```
