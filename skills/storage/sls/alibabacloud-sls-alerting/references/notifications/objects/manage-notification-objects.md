# Manage notification objects

A notification object identifies a person, group, or integration that can
receive an alert. An [action policy](../action-policies/manage-action-policies.md) selects the object and
delivery channel; a [content template](../templates/manage-content-templates.md) defines the message.
Creating an object alone does not connect it to a rule or send a notification.

## Choose the object type

- [Users](users.md): individual recipients with email addresses or telephone
  numbers. Manage their destinations and notification switches. These are SLS
  users, not RAM identities.
- [User groups](user-groups.md): reusable sets of users. Manage membership
  when several people should receive the same notifications.
- [Webhook integrations](webhooks/manage-webhook-integrations.md): bot or HTTP destinations, such as DingTalk,
  WeCom, Lark, Slack, or a custom service. Manage the endpoint and required
  authentication settings.
- [On-call groups](on-call.md): scheduled recipients. This skill
  supports selecting an existing group; rotation, calendar, and override
  authoring are outside its coverage.

Follow the selected type's document for its settings and management operations.
To use it in an alert, continue with [action policies](../action-policies/manage-action-policies.md), or
the [notification workflow](../../rules/notifications/connect.md) for the complete setup.
