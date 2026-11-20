# Notification channels

Load this file when selecting a channel or validating its prerequisites.
Channel choice belongs in an action policy; the selected
content template must also define that channel's content.

## Channel selection

| Channel family | Resolve first | Important constraints |
| --- | --- | --- |
| Email | Enabled user, user group, or on-call group with an email address | Mail filtering can prevent receipt even after SLS accepts the action. |
| SMS | Enabled recipient with a telephone number and `sms_enabled: true` | SMS can incur charges; a configured switch without a number is not deliverable. |
| Voice | Enabled recipient with a telephone number and `voice_enabled: true` | Only mainland China numbers with country code `86` are supported; voice can incur charges. |
| Webhook integration | Existing `sls.alert.action_webhook` record and matching `integration_type` | Prefer reusable integrations for DingTalk, WeCom, Lark, Slack, and custom Webhooks over legacy inline URLs. |
| Message Center | At least one verified recipient in Alibaba Cloud Message Center | Recipient management is outside SLS user records; the service sends through its configured email/SMS combination. |
| EventBridge | Existing custom event bus in the selected region and required read access | Use a JSON content template when downstream EventBridge rules inspect event `data`. |
| Function Compute | Existing non-HTTP function and required read access | The supported function name starts with `sls-ops-`; use a custom Webhook for HTTP functions. |

Use the documented action-DSL examples for recipient-backed channels and
reusable Webhook integrations. For Message Center, EventBridge, or Function
Compute, export and preserve a known-good action-policy record instead of
inventing `fire(...)` arguments from console labels.

To enable quota checks for email, SMS, voice, or Message Center actions, use
`check_quota="true"`; see the
[action DSL reference](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data).

For Webhook HTTP requirements, provider limits, and formatting, see
[integration delivery constraints](../objects/webhooks/manage-webhook-integrations.md#delivery-constraints).

Multiple `fire(...)` calls in the selected action-policy branch request
simultaneous channels. Each channel is delivered and verified independently.
Sending a notification requires explicit user intent.

See the [official channel guide](https://help.aliyun.com/zh/sls/notification-methods).
