# Flink AI Ops RAM Permissions

The skill calls the development console OpenAPI (`ververica`, version `2022-07-18`) through the Python SDK. The published actions use the `stream:` prefix and resource scope `*`. See the [official RAM authorization table](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-ram).

## Commands and RAM Actions

| Command | Official API | Published RAM action | Behavior |
| --- | --- | --- | --- |
| `chat_ai_agent` | [ChatAiAgent](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-chataiagent) | `stream:ChatAiAgent` | Conversation may execute write tools |
| `get_patrol_config` | [GetPatrolConfig](https://help.aliyun.com/en/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-getpatrolconfig) | `stream:GetPatrolConfig` | Read-only |
| `update_patrol_config` | [UpdatePatrolConfig](https://help.aliyun.com/en/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-updatepatrolconfig) | Unpublished | Update configuration (PATCH) |
| `trigger_patrol` | [TriggerPatrol](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-triggerpatrol) | Unpublished | Trigger a manual patrol |
| `list_patrol_reports` | [ListPatrolReports](https://help.aliyun.com/en/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-listpatrolreports) | `stream:ListPatrolReports` | Read-only |
| `get_patrol_report_detail` | [GetPatrolReportDetail](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-ververica-2022-07-18-getpatrolreportdetail) | `stream:GetPatrolReportDetail` | Read-only |

The individual patrol API pages show no authorization details. The RAM authorization table supplies the three read actions above. For the two unpublished write actions, have an administrator check the RAM console or confirm with Alibaba Cloud Support.

`wait_patrol_report` and `trigger_patrol --wait` use the report list and detail read actions for polling. `update_patrol_config` reads the current configuration to generate a preview and reads it again to verify a submitted update.

## Example Read-Only Patrol Policy

Grant the read actions required by the intended workflow. Grant `stream:ChatAiAgent` separately when needed. Conversation tools are subject to cloud-side permissions, while the local `--confirm` controls submission of approval decisions.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "stream:GetPatrolConfig",
        "stream:ListPatrolReports",
        "stream:GetPatrolReportDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

## Handling Permission Errors

On a permission error such as `Forbidden.RAM` or `Forbidden`, give the administrator the original error code, redacted message, and actual `request_id` so they can verify the API and permission. The target workspace needs access to Flink AI features for the assistant and patrol.
