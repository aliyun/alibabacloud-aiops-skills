# Webhook integrations

A Webhook integration stores a bot or HTTP destination and its connection
settings. An action policy selects the integration to deliver notifications.

## Manage Webhook integrations

Use [ResourceRecord operations](../../api/resource-records.md) with
`resource_name = sls.alert.action_webhook`; ID/tag map to `id` / `name`.

For creation or a destination change, choose the integration kind:

- [Bot integrations](#bot-integrations): provider type and signing settings.
- [Custom HTTP](#custom-http): method, headers, and receiver requirements.

## Shared record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `id` | string | Stable integration ID referenced by `webhook_id`. |
| `name` | string | Human-readable integration name. |
| `type` | string | Integration kind; select it from the bot or custom HTTP guide above. |
| `url` | string | Intended destination URL. Treat embedded tokens as secrets. |
| `method` | string | `GET`, `POST`, `PUT`, `DELETE`, or `OPTIONS`; bot integrations use `POST`. |
| `headers` | array of objects | Request headers. |
| `headers[].key` | string | HTTP header name. |
| `headers[].value` | string | HTTP header value; it can be sensitive. |
| `secret` | string | Optional signing secret; see the selected integration's authentication requirements. |

Keep tokenized URLs, authorization headers, and signing secrets out of chat and
command output. Redact for display only;
do not accidentally write redacted values back during an update. Configuration
creation does not authorize sending an HTTP request to the destination.

Before deletion or destination changes, identify known policy references.
See the
[official resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
for supported integration types and additional constraints.

## Bot integrations

Obtain the bot URL and any required signing secret before preparing the record.

| Provider | Integration `type` | Signing field |
| --- | --- | --- |
| DingTalk | `dingtalk` | `secret` when signature validation is enabled |
| WeCom | `wechat` | — |
| Lark | `lark` | `secret` when signature validation is enabled |
| Slack | `slack` | — |

These integrations use `method: POST` and an empty `headers` array. Omit
`secret` when it is not configured.

## Custom HTTP

Use `type: custom` with the receiver's URL, method, and headers:

```json
{
  "id": "example-webhook",
  "name": "Example webhook",
  "type": "custom",
  "url": "https://example.com/sls-alerts",
  "method": "POST",
  "headers": [{"key": "Content-Type", "value": "application/json"}]
}
```

## Select the integration in an action

Set `type="webhook_integration"`, `integration_type` to the integration's own
`type`, and `webhook_id` to its record ID. For the custom example, these are
`integration_type="custom"` and `webhook_id="example-webhook"`.

## Delivery constraints

For a custom Webhook notification, use a publicly reachable endpoint. SLS
treats a request that takes more than five seconds or returns a status other
than exactly HTTP 200 as failed; failures can cause retries. `POST` is the
recommended method unless the receiver requires another supported method.

Bot keyword, signature, and IP restrictions must agree with the provider's
security settings. DingTalk, WeCom, and Lark bots allow 20 messages per minute
per bot. See the
[official notification error reference](https://help.aliyun.com/zh/sls/error-codes)
before a high-volume rollout.

WeCom notifications that mention everyone or specified members must use plain
text rather than Markdown. Its bot payload also has a documented 4096-byte
limit. Keep templates compact and use a query/detail URL for larger evidence.
