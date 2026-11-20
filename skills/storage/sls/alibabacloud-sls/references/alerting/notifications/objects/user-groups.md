# Notification user groups

A user group collects existing notification users so an action policy can
address the group and membership can be maintained in one place.

## Manage user groups

Use [ResourceRecord operations](../api/resource-records.md) with
`resource_name = sls.common.user_group`; ID/tag map to `user_group_id` / `user_group_name`.

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

Resolve member IDs through [Users](users.md). When changing membership, preserve every member
not included in the requested change. Referencing a group does not guarantee
that all members have the selected delivery channel enabled.

Deleting a group is separate from deleting its users. Action policies and on-call
configuration may still reference the group.
