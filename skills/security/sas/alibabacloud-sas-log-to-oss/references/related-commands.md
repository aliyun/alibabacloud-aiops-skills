# Related CLI Commands

Complete list of all commands used by this skill.

## Python SDK Script Commands

| Command | Description | Required Parameters | Optional Parameters |
|---------|-------------|---------------------|---------------------|
| `list-logstores` | List all LogStores under an SLS Project | `--project` | `--endpoint` |
| `create-export` | Create a single OSS export task | `--project`, `--logstore`, `--name`, `--bucket` | `--display-name`, `--description`, `--oss-endpoint`, `--prefix`, `--suffix`, `--role-name`, `--path-format`, `--timezone`, `--content-type`, `--compression`, `--buffer-interval`, `--buffer-size`, `--delay-seconds`, `--from-time`, `--to-time`, `--columns`, `--delimiter`, `--header`, `--enable-tag` |
| `batch-create` | Batch create export tasks for all (or specified) LogStores | `--project`, `--bucket` | `--logstores`, plus all optional parameters from `create-export` |
| `list-exports` | List all OSS export tasks | `--project` | `--logstore`, `--endpoint` |
| `get-export` | View details of a specific export task | `--project`, `--name` | `--endpoint` |
| `stop-export` | Stop an export task | `--project`, `--name` | `--endpoint` |
| `start-export` | Start an export task | `--project`, `--name` | `--endpoint` |
| `delete-export` | Delete an export task | `--project`, `--name` | `--force`, `--endpoint` |

## Aliyun CLI Equivalent Commands

> **Note**: The `aliyun sls` CLI plugin MUST be invoked in **plugin mode** with lowercase-hyphenated command names (e.g., `aliyun sls get-oss-export`). Do NOT use PascalCase API names (e.g., `GetOSSExport`) as CLI subcommands. The Python script (`scripts/sls_oss_export.py`) is the PRIMARY execution method; use the CLI only when the user explicitly requests it or as a fallback when the script cannot run. Always include `--user-agent` as specified in SKILL.md Section 6.

| Script Command | Aliyun CLI Command | Key Parameters |
|----------------|-------------------|----------------|
| `list-logstores` | `aliyun sls list-log-stores` | `--project`, `--offset`, `--size` |
| `create-export` | `aliyun sls create-oss-export` | `--project`, `--body` (JSON config) |
| `list-exports` | `aliyun sls list-oss-exports` | `--project`, `--offset`, `--size` |
| `get-export` | `aliyun sls get-oss-export` | `--project`, `--name` |
| `start-export` | `aliyun sls start-oss-export` | `--project`, `--name` |
| `stop-export` | `aliyun sls stop-oss-export` | `--project`, `--name` |
| `delete-export` | `aliyun sls delete-oss-export` | `--project`, `--name` |

## SLS API Reference Table

| Operation | SLS API | SDK Method | RAM Action |
|-----------|---------|-----------|-----------|
| List LogStores | ListLogStores | `client.list_log_stores(project, request)` | `sls:ListLogStores` |
| Create export task | CreateOSSExport | `client.create_ossexport(project, request)` | `sls:CreateOSSExport` |
| List export tasks | ListOSSExports | `client.list_ossexports(project, request)` | `sls:ListOSSExports` |
| Get export task | GetOSSExport | `client.get_ossexport(project, name)` | `sls:GetOSSExport` |
| Update export task | UpdateOSSExport | `client.update_ossexport(project, name, request)` | `sls:UpdateOSSExport` |
| Start export task | StartOSSExport | `client.start_ossexport(project, name)` | `sls:StartOSSExport` |
| Stop export task | StopOSSExport | `client.stop_ossexport(project, name)` | `sls:StopOSSExport` |
| Delete export task | DeleteOSSExport | `client.delete_ossexport(project, name)` | `sls:DeleteOSSExport` |

## Common Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--endpoint` | `cn-hangzhou.log.aliyuncs.com` | SLS API endpoint |
| `--oss-endpoint` | `https://oss-cn-hangzhou-internal.aliyuncs.com` | OSS internal endpoint |
| `--role-name` | `aliyunlogdefaultrole` | RAM role name |
| `--prefix` | `sls-export/` | OSS file prefix |
| `--suffix` | `.json` | OSS file suffix |
| `--content-type` | `json` | Storage format: json, csv, parquet, orc |
| `--compression` | `snappy` | Compression: snappy, gzip, zstd, none |
| `--buffer-interval` | `300` | Buffer interval, seconds (300-900) |
| `--buffer-size` | `256` | Buffer size, MB (5-256) |
| `--delay-seconds` | `0` | Delivery delay, seconds |
| `--from-time` | `1` | Start time: 1=from first log, or Unix timestamp |
| `--to-time` | `0` | End time: 0=run forever, or Unix timestamp |
| `--path-format` | `%Y/%m/%d/%H/%M` | OSS partition format |
| `--timezone` | `+0800` | Timezone |
