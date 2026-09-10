# Use an existing on-call group

An on-call group selects recipients according to a duty schedule. Use it when
the alert should reach the current on-call recipient rather than a fixed group.

An on-call group is a different resource (`sls.alert.oncall_group`). Reuse an
existing `oncall_id` in the action policy's `oncall_groups` list when requested.
This guide supports on-call group reuse but does not create rotations,
calendars, or overrides.

Use [record reads](../api/resource-records.md#read-and-reuse) with
`resource_name = sls.alert.oncall_group` to locate and inspect an existing group.
Then reference its `oncall_id` through an [action policy](../action-policies/manage-action-policies.md).
Do not treat a user group's member list as an on-call schedule.
