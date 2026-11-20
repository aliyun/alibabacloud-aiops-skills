# ResourceRecord operations

## Scope and envelope

These notification objects share an API envelope and ID mapping.
[Notification management](../manage-notifications.md) describes their roles;
[CLI execution](../../cli-execution.md#notification-resources) covers request parameters.
ResourceRecords use the route in [region configuration](../../../regions.md#region).
Records can be reused by rules across Projects.

| Kind | Fixed `resource_name` | `record.id` comes from | `record.tag` comes from |
| --- | --- | --- | --- |
| [User](../objects/users.md) | `sls.common.user` | `user_id` | `user_name` |
| [User group](../objects/user-groups.md) | `sls.common.user_group` | `user_group_id` | `user_group_name` |
| [Webhook integration](../objects/webhooks/manage-webhook-integrations.md) | `sls.alert.action_webhook` | `id` | `name` |
| [Action policy](../action-policies/manage-action-policies.md) | `sls.alert.action_policy` | `action_policy_id` | `action_policy_name` |
| [Alert policy](../alert-policies/manage-alert-policies.md) | `sls.alert.alert_policy` | `policy_id` | `policy_name` |
| [Content template](../templates/manage-content-templates.md) | `sls.alert.content_template` | `template_id` | `template_name` |

Existing on-call groups use `sls.alert.oncall_group`, with `oncall_id` and
`oncall_name` as ID and tag. Use list/get to inspect and reuse them through
[on-call selection](../objects/on-call.md).

For create and update, derive `id` and `tag` from the inner object's
fields using the table above. Store the complete inner object in `value` as a
JSON string.

The fixed `resource_name`, record `tag`, and an alert rule's `labels`/`tags` are
different concepts. `createTime` and `lastModifyTime` are response metadata,
not desired-state inputs.

Example outer record:

```json
{
  "id": "example-team",
  "tag": "Example team",
  "value": "{\"user_group_id\":\"example-team\",\"user_group_name\":\"Example team\",\"enabled\":true,\"members\":[\"example-user\"]}"
}
```

Type-specific examples show the decoded inner object.

## Read and reuse

`list` finds records within a namespace; `get` reads an exact record ID. Responses use
the outer envelope above, with JSON text in `value`. Built-ins such as `sls.builtin.cn`
are included through the system-record option; see
[record reads](../../cli-execution.md#read-resource-records) for filters and pagination.

## Local validation

The [validator](../../../../scripts/alerting/validate_resource.py) checks an inner value or outer record:

```bash
python3 "scripts/alerting/validate_resource.py" --input-kind value \
  --purpose custom-write --resource-name "$SLS_RESOURCE_NAME" --input "$SLS_RESOURCE_VALUE_FILE"
```

Use `--input-kind value` for a decoded object, or `record` for an outer record
or `{"record": {...}}` get-response wrapper. Use `--purpose custom-write`
(the default) for a proposed custom value and `--purpose read` for service responses,
including built-in records. Keep built-in records unchanged.

[Validation reports](../../validation-results.md) include errors, warnings, and
derived ID/tag. Warnings use exit code 0 by default; `--strict` changes it to 1.
The resource schema, dependencies,
policy DSL and template expressions provide context for interpreting reported issues.

## Create

The [create command](../../cli-execution.md#create-a-resource-record) accepts an inner value
and its mapped ID/tag. Caller-selected IDs provide stable references for dependent rules.

## Update an existing record

The [update command](../../cli-execution.md#update-a-resource-record) replaces the inner value.
Comparing the desired value with the current record helps preserve unrelated fields.
The selected record ID and the body's mapped ID identify the same object.

## Delete

Records can be referenced by policies, groups and rules across Projects, so one Project's
references do not establish whether a record is unused. [Record deletion](../../cli-execution.md#delete-resource-records)
targets exact custom record IDs; built-in records and the namespace remain unchanged.

See the
[official resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
for the ResourceRecord envelope.
