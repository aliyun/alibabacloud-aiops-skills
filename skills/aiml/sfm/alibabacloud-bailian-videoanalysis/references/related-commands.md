# Related Commands: alibabacloud-bailian-videoanalysis

## Available Python Scripts

All scripts are located in the `scripts/` directory:

| Script                                            | Purpose                                                  | Required Parameters            | Optional Parameters                                |
|---------------------------------------------------|----------------------------------------------------------|--------------------------------|----------------------------------------------------|
| `check_env.py`                                    | Check environment configuration (packages + credentials) | None                           | None                                               |
| `quanmiao_submit_videoAnalysis_task.py`           | Submit video analysis task to Bailian                    | `--workspace_id`, `--file_url` | None                                               |
| `quanmiao_get_videoAnalysis_task_result.py`       | Get video analysis task result                           | `--workspace_id`, `--task_id`  | None                                               |

## Aliyun CLI Commands

**Important:** All `aliyun` CLI commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-bailian-videoanalysis`.

| Command                                                           | Purpose                                     |
|-------------------------------------------------------------------|---------------------------------------------|
| `aliyun version`                                                  | Verify CLI version (>= 3.3.1)               |
| `aliyun configure list`                                           | Check credential status (NEVER print AK/SK) |
| `aliyun configure set --auto-plugin-install true`                 | Enable automatic plugin installation        |
| `aliyun modelstudio list-workspaces`                              | List Bailian workspaces                     |
| `aliyun ossutil ls`                                               | List OSS buckets                            |
| `aliyun ossutil cp <local-file> oss://<bucket>/<key>`             | Upload file to OSS                          |
| `aliyun ossutil sign oss://<bucket>/<key> --expires-duration 2h`  | Generate temporary URL                      |
| `aliyun ossutil rm oss://<bucket>/<key>`                          | Delete uploaded OSS object (cleanup)        |

## Execution Order

```
1. check_env.py (environment validation)
       ↓
2. aliyun modelstudio list-workspaces (get workspace_id)
       ↓
3a. [If local file] aliyun ossutil cp + sign (upload & get URL)
3b. [If URL provided] Skip upload, use URL directly
       ↓
4. quanmiao_submit_videoAnalysis_task.py (submit task)
       ↓
5. quanmiao_get_videoAnalysis_task_result.py (poll loop)
       ↓
6. Summarize (no script call, use Step 5 result directly)
```
