# Define notification actions

Each `fire(...)` action combines a channel with its recipients, template, and
sending period. Resolve [notification objects](../objects/manage-notification-objects.md) and
[content templates](../templates/manage-content-templates.md) before filling their IDs.

## Channel arguments

| DSL argument | Value kind | Meaning |
| --- | --- | --- |
| `type` | string | Notification channel, e.g. `email`, `sms`, `voice`, or `webhook_integration`. |
| `users` | list of strings | User IDs. |
| `groups` | list of strings | User group IDs. |
| `oncall_groups` | list of strings | On-call group IDs. |
| `receiver_type` | string | `static` for direct recipients. Dynamic recipients require callback configuration. |
| `external_url` | string | Dynamic-recipient callback URL; leave empty for static recipients. |
| `external_headers` | object | Headers for a dynamic-recipient callback; use `{}` for static recipients. |
| `template_id` | string | Existing content-template ID, such as `sls.builtin.cn`. |
| `period` | string | Sending period, such as `any`, `workday`, or `worktime`. |
| `check_quota` | string | Whether the channel asks SLS to enforce its notification quota; official DSL examples pass `"true"` where supported. |
| `integration_type` | string | Webhook integration kind when `type="webhook_integration"`. |
| `webhook_id` | string | Existing webhook ResourceRecord ID. |

Read [notification channels](channels.md) before selecting a
channel with recipient, provider, formatting, or delivery constraints.
