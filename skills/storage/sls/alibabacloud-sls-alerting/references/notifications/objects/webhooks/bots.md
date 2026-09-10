# Configure a bot integration

Use a reusable Webhook integration for a bot destination. Obtain an approved
bot URL and any required signing secret before preparing the record.

| Provider | Integration `type` | Signing field |
| --- | --- | --- |
| DingTalk | `dingtalk` | `secret` when signature validation is enabled |
| WeCom | `wechat` | No signing secret field is specified here |
| Lark | `lark` | `secret` when signature validation is enabled |
| Slack | `slack` | No signing secret field is specified here |

These integrations use `method: POST` and an empty `headers` array. Omit
`secret` when it is not configured. Preserve unrelated fields on updates.
Use the [shared record fields](manage-webhook-integrations.md#shared-record-fields) and management
operations to save the integration.

An [action](../../action-policies/actions.md) references it using
`type="webhook_integration"`, its matching `integration_type`, and `webhook_id`.
The action type is distinct from the integration's own `type`.
Check [provider delivery constraints](../../action-policies/channels.md#webhook-delivery-constraints)
for rate limits, keyword/signature/IP rules, and content requirements.
