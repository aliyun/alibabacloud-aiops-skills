# Related Commands: alibabacloud-flink-ai-ops

Unified entry point: `SKILL_SESSION_ID=<32-hex> SKILL_VERSION=<manifest-version> python3 scripts/flink_ai_ops_cli.py <command> -w <workspace> -n <namespace> -r <region_id> [args]`.

## Command Parameters

All business commands require a confirmed workspace ID (`-w/--workspace`), namespace (`-n/--namespace`), and region ID (`-r/--region_id`). These flags have no defaults.

`chat_ai_agent`, `trigger_patrol`, and `update_patrol_config` all use the mutually exclusive and mandatory `--body_json <object>` or `--body_file <path>` to pass the official JSON object; no shortcut options for message, scope, or configuration fields are provided.

| Command | Business parameters |
| --- | --- |
| `chat_ai_agent` | `(--body_json JSON \| --body_file PATH) [--confirm] [--timeout 300] [--compact]` |
| `get_patrol_config` | No extra business parameters |
| `update_patrol_config` | `(--body_json JSON \| --body_file PATH) [--confirm]` |
| `trigger_patrol` | `(--body_json JSON \| --body_file PATH) --confirm [--wait] [--timeout 300] [--poll_interval 5]` |
| `list_patrol_reports` | `[--start_date MS] [--end_date MS] [--status STATUS] [--scope_type TYPE] [--trigger_type TYPE] [--page N] [--size N]` |
| `get_patrol_report_detail` | `(--report_id ID \| --date DATE) [--timezone TZ]` |
| `wait_patrol_report` | `--report_id ID [--timeout 300] [--poll_interval 5]` |

- In `list_patrol_reports`, `start_date/end_date` are millisecond timestamps and `page` starts at 1; the API defaults to 20 per page with a maximum of 200. `--status` filters by `PENDING/IN_PROGRESS/COMPLETED/FAILED`, scope by `ALL/TAGS/DEPLOYMENTS`, and trigger type by `CRON/MANUAL/INNER_API`. `COMPLETING` in report responses is a processing intermediate state to keep waiting on; it does not extend the filter values above. Never mistake the API's report status for the job's `RUNNING`.
- In `get_patrol_report_detail`, exactly one of `report_id/date` is required; the date is `YYYY-MM-DD`, `today`, or `yesterday`. The API's date query defaults to UTC; for "today" in Chinese local time, explicitly provide `--timezone Asia/Shanghai`. `timezone` works with `date` and does not change the report ID semantics.
- `chat_ai_agent` keeps the full events and aggregated text by default; `--compact` only removes plain-text event fragments confirmed duplicated by the aggregated `text`, keeping the event count, order, identifiers, indices, and full tool, approval, error, and unknown fields — it changes neither collection, execution, nor exit code; the same applies to partial results on failure, and content is kept when duplication cannot be safely confirmed.
- Timeout parameters are in seconds: `--connect_timeout` defaults to 10; `--read_timeout` defaults to Chat 300 and patrol 60; `--timeout` limits a whole Chat collection round or patrol wait, defaulting to 300; `--poll_interval` defaults to 5.

## API Mapping

| Command | Official API |
| --- | --- |
| `chat_ai_agent` | [ChatAiAgent](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-chataiagent) |
| `get_patrol_config` | [GetPatrolConfig](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-getpatrolconfig) |
| `update_patrol_config` | [UpdatePatrolConfig](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-updatepatrolconfig) |
| `trigger_patrol` | [TriggerPatrol](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-triggerpatrol) |
| `list_patrol_reports` | [ListPatrolReports](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-listpatrolreports) |
| `get_patrol_report_detail` | [GetPatrolReportDetail](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-getpatrolreportdetail) |
| `wait_patrol_report` | Local bounded orchestration: queries the list to locate the real `reportId` and reads the detail after a terminal success; not a new API |

## Retry and Idempotency

The SDK client disables automatic retries; the wrapper retries retryable transient read (GET) errors at most once. Chat, Trigger, and PATCH are never replayed; a failed write may leave the result uncertain — keep the received events, verify read-only against the actual resource, report, or configuration, and never retry blindly. This version has no session-state query command.
