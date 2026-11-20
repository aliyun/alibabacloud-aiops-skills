# Scheduled SQL outcomes: `scheduled_sql_alert`

Use to investigate a Scheduled SQL instance's execution outcome, failure and
scheduling delay. One record is emitted after each instance finishes; this is
not a periodic heartbeat and the topic name does not mean an alert notification
was sent.

| Field | Meaning |
| --- | --- |
| `project`, `job_name`, `schedule_id`, `instance_id` | Owning Project, job, schedule and execution identity |
| `job_type` | `ScheduledSQL` |
| `create_time`, `schedule_time`, `trigger_time` | Instance creation, planned schedule and execution start, in Unix seconds |
| `__time__` | Execution end, in Unix seconds |
| `status` | `FAILED` or `SUCCEEDED` |
| `error_code`, `error_message` | Failure category and detail |
| `fallbehind` | Trigger time minus scheduled time, in seconds |
| `succeed_lines` | Rows written on success; zero for a failed instance |

Example filter:

```text
__topic__: scheduled_sql_alert and project: "example-project" and job_name: "example-job"
```

Distinguish scheduling delay from execution duration. Since the event timestamp
is the finish time, choose a query window that includes completion of the
suspected execution. No completed-instance record does not prove that the
job never started. Check task state and scheduling evidence as needed.

For location and management, see [service logs](../service-logs.md).
Source: [Service log types — Scheduled SQL](https://help.aliyun.com/zh/sls/log-types).
