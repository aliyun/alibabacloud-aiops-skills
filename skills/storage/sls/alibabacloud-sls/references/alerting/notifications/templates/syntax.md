# Notification-template syntax

Prefer the new syntax: `{{ expression }}` renders values, `{% ... %}` controls
flow, and `{# ... #}` adds non-rendered comments. Alert properties are under
`alert`. This is a rendering language, not arbitrary Python execution.

```text
Rule: {{ alert.alert_name }}
Project: {{ alert.project }}
{% if alert.severity >= 8 %}Urgent{% else %}Informational{% endif %}
{% for key, value in alert.labels.items() %}
{{ key }}: {{ value }}
{% endfor %}
```

Embed template text in the channel's `content` string using JSON encoding.
Use documented alert fields and known query-result fields; available event
samples can help check their values and types. An email body, chat
message, and custom webhook body have different formatting requirements.
[Template checks](manage-content-templates.md#template-verification) cover the
destination format and outer resource JSON.
See [template data](variables.md) for result and metadata variables, and
[notification channels](../action-policies/channels.md) for formatting constraints.

Do not confuse rule-annotation `${...}` substitution with this syntax. The
service supports old/new template compatibility, but property representations
can differ; avoid mixing styles in a new template.

For filters, escaping, or more complex control flow, consult the
[official new-template syntax](https://help.aliyun.com/zh/sls/syntax-for-new-alert-templates).
