# Recovery notifications

Load only when the user wants an explicit notification that a previously
firing alert has returned to normal. Recovery is off by default and is an
optional part of the [alert-rule configuration](../create-update-alert-rule.md).

Set this field inside the rule's `configuration`:

```json
{"sendResolved": true}
```

SLS sends a recovery notification when the previous evaluation fired for an
alert instance and the current evaluation no longer satisfies its trigger
condition. A rule that has never fired has nothing to recover. This setting is
separate from no-data alerts, notification repeat intervals, and rule status.

For grouped evaluation, stable grouping labels are important because they
identify independent alert instances. Changing grouping fields or identity
labels can create a new fingerprint rather than recover the old alert; read
[labels and annotations](../labels-annotations.md) before changing them.

Custom templates should handle both states:

```text
{% if alert.status == "resolved" %}
Recovered at {{ alert.resolve_time | format_date }}
{% else %}
Firing since {{ alert.fire_time | format_date }}
{% endif %}
```

`alert.status` is `firing` or `resolved`. `alert.resolve_time` is zero while
firing and contains the recovery time for a resolved event. Read
[template data](../../notifications/templates/variables.md) for other variables.

To verify recovery, inspect a firing event followed by a resolved event for
the same alert instance. Creating these events or sending notifications requires
user authorization. See the
[official recovery guide](https://help.aliyun.com/zh/sls/recovery-notifications).
