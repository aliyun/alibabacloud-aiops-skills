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

## Webhook delivery constraints

For a custom Webhook notification, use a publicly reachable endpoint. SLS
treats a request that takes more than five seconds or returns a status other
than exactly HTTP 200 as failed; failures can cause retries. `POST` is the
recommended method unless the receiver requires another supported method.

Keep tokenized URLs, signing secrets, and authorization headers out of chat
and displayed output. DingTalk and Lark integrations can use a signing secret;
bot keyword, signature, and IP restrictions must agree with the provider's
security settings. DingTalk, WeCom, and Lark bots allow 20 messages per minute
per bot. See the
[official notification error reference](https://help.aliyun.com/zh/sls/error-codes)
before a high-volume rollout.

WeCom notifications that mention everyone or specified members must use plain
text rather than Markdown. Its bot payload also has a documented 4096-byte
limit. Keep templates compact and use a query/detail URL for larger evidence.

Multiple `fire(...)` calls in the selected action-policy branch request
simultaneous channels. Each channel is delivered and verified independently.
Sending a notification requires explicit user intent.

See [users](../objects/users.md), [webhook integrations](../objects/webhooks/manage-webhook-integrations.md),
[action policies](manage-action-policies.md),
[content templates](../templates/manage-content-templates.md), and the
[official channel guide](https://help.aliyun.com/zh/sls/notification-methods).
