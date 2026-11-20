# CLI execution

This page covers commands, parameter mapping, request construction, and
response handling. For configuration fields and update rules, use
[alert rule configuration](rules/create-update-alert-rule.md) or
[ResourceRecord configuration](notifications/api/resource-records.md).

- [Alert rules](#alert-rules)
- [Notification resources](#notification-resources)

Use the configured profile unless the user specifies one, select the appropriate
[region and endpoint](../regions.md), and include the
[User-Agent](../../SKILL.md#observability) on API calls.

You can use `--cli-dry-run` to preview a request.

## Alert rules

### Target

Use the stable rule ID, not its display name: rule operations use `--alert`.
Set `SLS_PROJECT` to
the owning Project, `SLS_ALERT_ID` to the ID, and `SLS_ALERT_FILE` to the prepared
rule document for the examples below.

A rule document for local
validation includes `name`, `displayName`, `schedule`, `configuration`, and an
optional `description`. Use enable/disable operations to change the enabled state.

### List and inspect rules

`alert list` and `alert get` inspect rules. List responses contain `results`, `count`
and `total`; the next zero-based offset is the current offset plus the returned `count`.

### Create or update a rule

A [local validator](rules/verify-alert-rule.md) can check the complete document.

Use `--from-file` with a complete writable JSON document:

```bash
aliyun sls alert create \
  --project "$SLS_PROJECT" \
  --alert "$SLS_ALERT_ID" --from-file "$SLS_ALERT_FILE"
```

The create name can be in the file or `--alert`; if supplied in both they must match.
For updates, replace `alert create` with `alert update` and keep `--alert` to select
the existing rule.

File input uses the file for all body fields; it does not merge them with body flags.
When an update must retain a writable field that file input cannot preserve, prepare a
request with `displayName`, `schedule`, `configuration`, optional `description`, and
any other writable fields to retain; use `--raw-body-file` in the update command.
For a JSON object missing `name`, the CLI adds the `--alert` value; an existing `name`
is retained. The command-line `--alert` still selects the update target.

Manage the rule's enabled state with `alert enable` and `alert disable`.
`schedule.runImmediately` controls evaluation immediately after creation.

### Enable, disable, or delete a rule

Use `alert enable`, `alert disable` or `alert delete` for the selected rule.

### Mute or unmute a rule

Set `SLS_MUTE_UNTIL` to the requested end time, such as `now+1h`, `now+1h30m`,
or a future Unix timestamp in seconds.

```bash
aliyun sls alert mute \
  --project "$SLS_PROJECT" --alert "$SLS_ALERT_ID" \
  --until "$SLS_MUTE_UNTIL"
```

To cancel the mute, use `alert unmute` with the same Project and rule ID.

Both commands preserve other rule settings; [mute semantics](rules/manage-alert-rules.md#mute-or-unmute)
describe the affected field and notification behavior.

## Notification resources

Select the namespace and derive the ID/tag using the
[ResourceRecord mapping](notifications/api/resource-records.md#scope-and-envelope).
Set `SLS_RESOURCE_NAME`, `SLS_RECORD_ID`, and `SLS_RECORD_TAG` to those values.

Type-specific files show the inner object. Save it as `SLS_RESOURCE_VALUE_FILE`;
`jq -c .` supplies that object as JSON text to `--value`, rather than the outer record.
Keep template text and DSL in the file so shell expansion does not consume
`${...}`, quotes, or backslashes.

Create returns response data including the record `id`. Update and delete
define no response fields, so a JSON body is not required for success. The CLI exit
status distinguishes success from failure; failures return error information.

### Read resource records

Use `--resource` for the selected namespace. List with
`resource-record list`; read an exact record with `resource-record get
--record-id <id>`.

The list response contains `items`, `count` (records in this page), and `total`
(matching records).
The next offset is the current offset plus `count`, with filters unchanged.
Reaching `total` covers the matching records; a zero-record page before that point
indicates an incomplete listing. `--include-system-records true` includes built-ins
such as `sls.builtin.cn` in list/get operations.
A get returns the [outer record](notifications/api/resource-records.md#scope-and-envelope);
decode its `value` for use.

### Create a resource record

[Local validation](notifications/api/resource-records.md#local-validation) can check the
inner value and mapped ID/tag.

```bash
aliyun sls resource-record create \
  --region cn-shanghai \
  --resource "$SLS_RESOURCE_NAME" \
  --record-id "$SLS_RECORD_ID" --tag "$SLS_RECORD_TAG" \
  --value "$(jq -c . "$SLS_RESOURCE_VALUE_FILE")"
```

### Update a resource record

The [ResourceRecord update](notifications/api/resource-records.md#update-an-existing-record)
replaces the inner value. Use the create parameters with
`resource-record update`. `--record-id "$SLS_RECORD_ID"` selects the existing
record; derive it from the inner object's mapped ID.

### Delete resource records

Use `resource-record delete` with the same namespace and `--record-ids`, a
comma-separated list of up to 200 exact record IDs. Shared-resource dependencies are
described under [record deletion](notifications/api/resource-records.md#delete).
