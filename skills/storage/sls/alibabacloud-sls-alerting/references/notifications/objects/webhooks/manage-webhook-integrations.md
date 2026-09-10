# Webhook integrations

A Webhook integration stores a bot or HTTP destination and its connection
settings. An action policy selects the integration to deliver notifications.

## Manage Webhook integrations

For list, read, create, update, or delete operations, use
[ResourceRecord operations](../../api/resource-records.md) with
`resource_name = sls.alert.action_webhook`. Outer ID/tag map to `id` / `name`
in the value below.

For creation or a destination change, choose the integration kind:

- [Bot integrations](bots.md): provider type and signing settings.
- [Custom HTTP](custom-http.md): method, headers, and receiver requirements.

## Shared record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `id` | string | Stable integration ID referenced by `webhook_id`. |
| `name` | string | Human-readable integration name. |
| `type` | string | Integration kind; select it from the bot or custom HTTP guide above. |
| `url` | string | Approved destination URL. Treat embedded tokens as secrets. |
| `method` | string | HTTP method required by the receiver. |
| `headers` | array of objects | Request headers. |
| `headers[].key` | string | HTTP header name. |
| `headers[].value` | string | HTTP header value; it can be sensitive. |
| `secret` | string | Optional signing secret; see the selected integration's authentication requirements. |

Keep tokenized URLs, authorization headers, and signing secrets out of chat,
command output, and dry-run reports. Redact for display only;
do not accidentally write redacted values back during an update. Configuration
creation does not authorize sending an HTTP request to the destination.

For timeout, HTTP status, public-network, provider-rate-limit, and formatting
constraints, read [notification channels](../../action-policies/channels.md).

Before deletion or destination changes, identify known policy references.
See the
[official resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
for supported integration types and additional constraints.
