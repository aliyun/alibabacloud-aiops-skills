# Manage content templates

A content template renders alert data into each channel's message text and
format. An action policy selects the template; the template does not select
recipients or enable a channel.

Use [ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.alert.content_template`. Prefer built-in `sls.builtin.cn` when
suitable; do not recreate or overwrite it. Action policies may share references to a template.

## Create or update

Select the channels requested by the user, or those used by an action policy
when connecting to one. A standalone template can be created before any policy
or alert exists. Updates replace the template value, so a diff can reveal unintended
changes to other channels.

For custom expressions, read [syntax](syntax.md) and [variables](variables.md).

### Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `template_id` | string | Stable template ID selected by action-policy actions. |
| `template_name` | string | Human-readable template name. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom template. |
| `templates` | object | Map of channel name to channel-specific template configuration. |

### Simple example

Illustrative custom email template:

```json
{
  "template_id": "example-template",
  "template_name": "Example English notification",
  "is_default": false,
  "templates": {
    "email": {
      "locale": "en-US",
      "subject": "SLS alert: {{ alert.alert_name }}",
      "content": "Rule {{ alert.alert_name }} in {{ alert.project }} is {{ alert.status }}."
    }
  }
}
```

The shared [ResourceRecord operations](../api/resource-records.md) save template values.
Reference the saved ID from each relevant action's `template_id`.

## Channel content

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
| `locale` | string | `zh-CN` or `en-US`; confirm service support before using another locale. |
| `content` | string | Notification body. An empty string asks SLS to use its default content for that channel. |
| `subject` | string | Email/EventBridge subject; template expressions are allowed. |
| `title` | string | Chat-channel title; template expressions are allowed. |
| `send_type` | string | Whether Webhook/FC sends each alert separately or sends a merged alert collection. Preserve a service-returned value on update. |
| `limit` | integer | Maximum alerts included from one merged group. Preserve an existing value unless the requirement specifies a limit. |

Use `single` for per-alert delivery. Preserve existing `batch` or `merged` values
instead of translating them. Keep an existing `limit: 0` unless its behavior is
verified; do not assume it means unlimited or zero delivered alerts. See the
[resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
for channel parameters.

## Template verification

The [resource validator](../api/resource-records.md#local-validation) can check a complete
value with `--input-kind value --purpose custom-write`; `--purpose read` is for inspecting
service-returned objects. [Template syntax](syntax.md) and [template data](variables.md)
describe expressions, control flow and standard variables. Query schemas or samples
provide the types of custom result fields.

Missing optional values, empty arrays and firing/resolved branches can affect the rendered
content. JSON notification bodies also depend on escaping of substituted values.

### Optional service rendering

A documented service preview can show rendered content and errors when available;
a JSON parser can check rendered JSON bodies. Actual delivery stays within the requested
notification scope and is not a fallback for an unavailable preview.
