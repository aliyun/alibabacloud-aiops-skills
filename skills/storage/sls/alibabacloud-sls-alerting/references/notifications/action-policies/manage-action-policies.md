# Manage action policies

An action policy defines how to notify: channels, recipients, templates,
conditional selection, and optional escalation. Rules or alert policies select
it; actions reference [notification objects](../objects/manage-notification-objects.md) and
[templates](../templates/manage-content-templates.md).

- To create or change a policy, follow [create or update](create-update-action-policy.md).
- To list or inspect policies, use [record reads](../api/resource-records.md#read-and-reuse)
  with `resource_name = sls.alert.action_policy`. Resolve names to exact IDs and decode `value`.
- To delete a policy, check known dependents, then use
  [record deletion](../api/resource-records.md#delete) for its exact ID.

The record's ID and display tag map to `action_policy_id` and `action_policy_name`.
Prefer reusing a suitable policy. Check rules and alert policies that select it
before changing a shared policy or deleting it.
