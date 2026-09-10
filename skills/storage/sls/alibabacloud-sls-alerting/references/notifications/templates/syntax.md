# Notification-template syntax

Read only for custom rendering. For record fields, use
[create or update a template](create-update-content-template.md#record-fields); otherwise reuse
`sls.builtin.cn` without loading a template-language manual.

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
message, and custom webhook body have different formatting requirements;
follow [template verification](verify-content-template.md#template-verification) for the
destination format and outer resource JSON.
Read [template data](variables.md) only when choosing result or metadata
variables, and [notification channels](../action-policies/channels.md) for
destination-specific constraints.

Do not confuse rule-annotation `${...}` substitution with this syntax. The
service supports old/new template compatibility, but property representations
can differ; avoid mixing styles in a new template. Rendering success is
separate from delivery authorization and delivery success.

For filters, escaping, or more complex control flow, consult the
[official new-template syntax](https://help.aliyun.com/zh/sls/syntax-for-new-alert-templates).
