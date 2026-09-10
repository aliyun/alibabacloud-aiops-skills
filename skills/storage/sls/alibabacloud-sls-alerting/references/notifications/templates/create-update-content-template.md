# Create or update a content template

Select the channels requested by the user, or those used by an action policy
when connecting to one. A standalone template can be created before any policy
or alert exists. For updates, read the current template and preserve other channels.

- [Channel content](channel-content.md):
  subject, title, body, and structured-message settings.
- [Syntax](syntax.md): interpolation, conditions, loops, and formatting.
- [Variables](variables.md): available alert and query-result data.
- [Verification](verify-content-template.md): validate the
  record structure, syntax, and variable references before writing.

## Record fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `template_id` | string | Stable template ID selected by action-policy actions. |
| `template_name` | string | Human-readable template name. |
| `is_default` | boolean | Built-in/default marker; set to `false` for a custom template. |
| `templates` | object | Map of channel name to channel-specific template configuration. |

## Simple example

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

Save this decoded object as `SLS_RESOURCE_VALUE_FILE`; use the
[common create command](../api/resource-records.md#create) with
`resource_name = sls.alert.content_template`.

Outer ID/tag map to `template_id` / `template_name`. For updates use
[record replacement](../api/resource-records.md#update-an-existing-record), then read
back and compare the intended channels. Reference the saved template ID from
each relevant action's `template_id`.
