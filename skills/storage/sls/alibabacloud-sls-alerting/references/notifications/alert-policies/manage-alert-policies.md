# Manage alert policies

An alert policy routes and groups alerts, applies inhibition or silence, and
selects an [action policy](../action-policies/manage-action-policies.md). Most ordinary rules can
reuse `sls.builtin.dynamic`; custom policy authoring is needed only for requested
routing or noise-reduction behavior.

- To create or change a policy, follow [create or update](create-update-alert-policy.md).
- To list or inspect policies, use [record reads](../api/resource-records.md#read-and-reuse)
  with `resource_name = sls.alert.alert_policy`. Resolve names to exact IDs and decode `value`.
- To delete a policy, check known dependents, then use
  [record deletion](../api/resource-records.md#delete) for its exact ID.

The record's ID and display tag map to `policy_id` and `policy_name`.
Check known rules that select the policy before deletion or changing its action
target. DSL-only records may not show graphical nodes in the console.
