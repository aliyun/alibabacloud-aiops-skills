# Configure a custom HTTP destination

Use `type: custom` for an approved HTTP receiver. Set its URL, required method,
and headers in the integration; keep authentication material out of display.
See [shared fields](manage-webhook-integrations.md#shared-record-fields)
for the full record shape and [delivery constraints](../../action-policies/channels.md#webhook-delivery-constraints)
for reachability, timeout, and response requirements.

## Simple example

Illustrative custom integration; the example domain is not a delivery target:

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

Save this decoded object as `SLS_RESOURCE_VALUE_FILE`; use the
[common create command](../../api/resource-records.md#create) with
`resource_name = sls.alert.action_webhook`.

Use the outer record ID to reference this integration in an action policy.
For example, its action has `type="webhook_integration"`,
`integration_type="custom"`, and `webhook_id="example-webhook"`; the action
type is not the same field as the integration's own `type`.
