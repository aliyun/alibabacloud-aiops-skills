# Labels and annotations

Load when the user needs routing, noise-reduction, assignment, or additional
notification context. Both are optional additions to the ordinary
[alert-rule workflow](create-update-alert-rule.md).

- Labels are identifying attributes used in alert deduplication, routing, and
  assignment. Prefer stable values such as environment and team.
- Annotations are descriptive attributes used in templates and assignment.
  Put changing measurements or explanatory text here instead of identity labels.

Labels written directly in the rule are static strings. If the value must vary
per host, service, or another result field, use [group evaluation](group-evaluation.md);
its grouping fields become dynamic alert labels.

The rule API stores arrays of key/value objects:

```json
{
  "labels": [
    {"key": "env", "value": "production"},
    {"key": "team", "value": "payments"}
  ],
  "annotations": [
    {"key": "title", "value": "${alert_name}"},
    {"key": "desc", "value": "Matching result rows: ${__pass_count__}"}
  ]
}
```

Place these fields inside `configuration`, preserving unrelated entries.
Generated alert events expose maps to templates, for example
`alert.annotations.desc` in the new template syntax. Do not replace the API
arrays with event-format maps.

`autoAnnotation: true` adds result context. When a result field has several
values, automatic annotation can select the first; do not describe that value
as an aggregate over all rows. Group-evaluation fields can become labels.
Record `tag`, rule category `tags`, and alert `labels` are separate fields.

SLS calculates the alert fingerprint from the owning Alibaba Cloud account ID
(`aliuid`), owning Project, rule ID (`alert_id`), and all alert labels.
Annotations are not part of the fingerprint. Changing or adding a label can
therefore change deduplication identity; changing an annotation does not.

See the [official labels and annotations guide](https://help.aliyun.com/zh/sls/labels-and-annotations)
for substitution variables and automatic-annotation behavior, and the
[fingerprint guide](https://help.aliyun.com/zh/sls/deduplicate-alerts-based-on-fingerprints)
for deduplication identity.
