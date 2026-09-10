# Notification user groups

A user group collects existing notification users so an action policy can
address the group and membership can be maintained in one place.

## Manage user groups

For list, read, create, update, or delete operations, use
[ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.common.user_group`. Outer ID/tag map to
`user_group_id` / `user_group_name` in the value below.

## `value` parameters

| Field | JSON type | Meaning |
| --- | --- | --- |
| `user_group_id` | string | Stable group ID. Action policies refer to this value. |
| `user_group_name` | string | Human-readable group name. |
| `enabled` | boolean | Enables or disables the notification group. |
| `members` | array of strings | Existing SLS notification-user IDs. These are not names, email addresses, or RAM users. |

## Simple example

```json
{
  "user_group_id": "example-team",
  "user_group_name": "Example team",
  "enabled": true,
  "members": ["example-user"]
}
```

Save this decoded object as `SLS_RESOURCE_VALUE_FILE`; use the
[common create command](../api/resource-records.md#create) with the namespace above.

Resolve member IDs through [Users](users.md); do not substitute display names,
RAM users, or email addresses. When changing membership, preserve every member
not included in the requested change. Referencing a group does not guarantee
that all members have the selected delivery channel enabled.

Deleting a group is separate from deleting its users. Inspect known action
policy and on-call references before deletion. Use the
[ResourceRecord update workflow](../api/resource-records.md#update-an-existing-record)
for membership changes; they are not alert-rule updates.
