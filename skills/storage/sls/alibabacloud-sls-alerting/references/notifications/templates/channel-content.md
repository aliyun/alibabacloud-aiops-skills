# Define channel message content

Choose the fields for each selected channel; preserve channels outside the requested change.

| Channel entry | Parameters | Meaning |
| --- | --- | --- |
| `templates.sms` | `locale`, `content` | SMS language and body. |
| `templates.voice` | `locale`, `content` | Voice language and body. |
| `templates.email` | `locale`, `subject`, `content` | Email language, subject, and body. |
| `templates.dingtalk` | `locale`, `title`, `content` | DingTalk language, title, and body. |
| `templates.wechat` | `locale`, `title`, `content` | WeCom language, title, and body. |
| `templates.lark` | `locale`, `title`, `content` | Lark language, title, and body. |
| `templates.slack` | `locale`, `title`, `content` | Slack language, title, and body. |
| `templates.webhook` | `locale`, `send_type`, `limit`, `content` | Custom-webhook language, per-alert/merged mode, merged-item limit, and body. |
| `templates.fc` | `locale`, `send_type`, `limit`, `content` | Function Compute language, per-alert/merged mode, merged-item limit, and body. |
| `templates.event_bridge` | `locale`, `subject`, `content` | EventBridge language, subject, and body. |
| `templates.message_center` | `locale`, `content` | Message Center language and body. |

Channel parameter meanings:

| Parameter | JSON type | Meaning |
| --- | --- | --- |
| `locale` | string | Documented values: `zh-CN`, `en-US`. Other nonempty values produce a local warning; confirm service support. |
| `content` | string | Notification body. An empty string asks SLS to use its default content for that channel. |
| `subject` | string | Email/EventBridge subject; template expressions are allowed. |
| `title` | string | Chat-channel title; template expressions are allowed. |
| `send_type` | string | Whether Webhook/FC sends each alert separately or sends a merged alert collection. Preserve a service-returned value on update. |
| `limit` | integer | Maximum alerts included from one merged group. Preserve an existing value unless the requirement specifies a limit. |

The public resource schema describes `single` and `batch` for `send_type`, while
its FC example uses `merged`. Use `single` for the simple per-alert case. Preserve
existing `batch` or `merged` values instead of translating them. The
[official resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
shows `limit: 0` but does not explain its special meaning; do not interpret it
as either unlimited or zero delivered alerts without verifying that behavior.
