# ResourceRecord operations

## Scope and envelope

Use this file after selecting a resource and operation through
[notification management](../manage-notifications.md). It supplies the common API envelope
and commands. Use the ResourceRecord route in
[region configuration](../../regions.md#region).
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
[on-call selection](../objects/on-call.md); this workflow does not author their schedules.

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

Type-specific files show the decoded inner object. Save that object as
`SLS_RESOURCE_VALUE_FILE`; `jq -c .` supplies the string contents to `--value`.
If `jq` is unavailable, use a Python script instead.
The CLI performs outer JSON encoding. Do not use `jq @json` on an already
serialized string, or send the whole outer record as `--value`.
Keep template text and DSL in the file so shell expansion does not consume
`${...}`, quotes, or backslashes.

## Command mapping

| Intent | CLI command | API action / boundary |
| --- | --- | --- |
| List | `list-resource-record` | `ListResourceRecord`; offset/size pagination |
| Read one | `get-resource-record` | `GetResourceRecord` |
| Create | `create-resource-record` | `CreateResourceRecord` |
| Update | `update-resource-record` | `UpdateResourceRecord`; one record selected by `--record-id` |
| Delete | `delete-resource-record` | `DeleteResourceRecord`; accepts a comma-separated ID list |

Create returns response data including the record `id`. Update and delete
define no response fields; check exit status and readback rather than
requiring a JSON response. Failures return error information. Preserve the
exit code and error text when capturing output.

## Read and reuse

Use `--resource-name` for the selected namespace. List with
`list-resource-record`; read an exact record with `get-resource-record
--record-id <id>`.

For listing, start with `--offset 0` and choose `--size` from 1–200. The response
contains `items`, `count` (records in this page), and `total` (matching records).
Advance the offset by the returned `count` and keep the same filters for
subsequent pages. Finish when the offset reaches `total`. If a page returns
zero records before that point, report the incomplete listing rather than
looping at the same offset. Optional filters are
`--ids` (exact IDs), `--tag`, and `--search`. Include
`--include-system-records true` to find built-in records such as `sls.builtin.cn`.
A get returns the outer record shown above; decode its `value` for use.

## Local validation before a write

Run the standalone [validator](../../../scripts/validate_resource.py)
(Python 3.7+, standard library only). Set `SLS_SKILL_DIR` to the absolute
directory containing this skill's `SKILL.md`:

```bash
python3 "$SLS_SKILL_DIR/scripts/validate_resource.py" --input-kind value \
  --purpose custom-write --resource-name "$SLS_RESOURCE_NAME" "$SLS_RESOURCE_VALUE_FILE"
```

`value` checks a decoded object; `record` also checks single JSON encoding and
outer ID/tag equality. Record mode accepts a record or a `{"record": {...}}`
get-response wrapper. Use `--purpose custom-write` (the default) before any write;
use `--purpose read` for service responses, including built-in records. Read mode
still checks types, identity, and encoding, but accepts built-in markers and
service policy labels. It does not authorize editing built-in resources.

Exit `0` means local checks passed, `1` means invalid input, and `2` means invalid
CLI arguments. Warnings do not fail validation. `--json` returns errors, warnings,
and derived ID/tag without printing the payload. Unknown fields are retained.
The script does not parse DSL, resolve dependencies, render templates, test
permissions/reachability, or prove service acceptance.

Unknown resource types produce a warning: only the value's object shape and,
in record mode, the generic envelope and JSON encoding are checked. Unknown
Webhook types retain ID/name/type and identity-mapping checks but skip other
Webhook fields. Unknown template locales also produce a warning; required
fields and value types are still checked. A locale must be a nonempty string.
Confirm the corresponding schema before writing; a warning does not establish
service support.

Use `--cli-dry-run` on create or update to inspect request construction
without sending it; this does not validate service semantics. Remove the flag
for an authorized write.

## Create

Prepare the inner value and mapped ID/tag. Prefer caller-selected IDs so
dependent rules can refer to stable identifiers.

```bash
aliyun sls create-resource-record \
  --user-agent "$SLS_ALERT_USER_AGENT" \
  --region cn-shanghai \
  --resource-name "$SLS_RESOURCE_NAME" \
  --id "$SLS_RECORD_ID" --tag "$SLS_RECORD_TAG" \
  --value "$(jq -c . "$SLS_RESOURCE_VALUE_FILE")" \
  --cli-dry-run
```

Ensure the ID is available and dependencies exist. Create new records with
`create-resource-record`; change existing records with `update-resource-record`.

## Update an existing record

Read the exact record, decode `value`, preserve unrelated fields, apply the
requested change, and validate the complete intended record.

Use the create parameters with `update-resource-record` and add
`--record-id "$SLS_RECORD_ID"`. `--record-id` selects the record in the request
path; `--id` remains in the body. Set both from the inner object's mapped ID.

## Delete

Use `delete-resource-record` with the same namespace and `--ids`, a
comma-separated list of up to 200 exact record IDs. Check known policy, group,
and rule references; checking one Project cannot establish that a globally
shared resource is unused. Do not delete built-in records or the namespace.

See the
[official resource schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-alert-resource-data)
for the ResourceRecord envelope.
