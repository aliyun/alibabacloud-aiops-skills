# Manage alert notifications

Notification resources control who receives alerts, how they are processed and
sent, and what the messages contain. They can be reused by multiple rules.

## Notification objects

- [Users](objects/users.md): individual recipients with email addresses or telephone
  numbers. Manage their destinations and notification switches. These are SLS
  users, not RAM identities.
- [User groups](objects/user-groups.md): reusable sets of users. Manage membership
  when several people should receive the same notifications.
- [Webhook integrations](objects/webhooks/manage-webhook-integrations.md): bot or HTTP destinations, such as DingTalk,
  WeCom, Lark, Slack, or a custom service. Manage the endpoint and required
  authentication settings.
- [On-call groups](objects/on-call.md): select existing groups of scheduled recipients.

## Policies and content

- [Alert policies](alert-policies/manage-alert-policies.md): route and group alerts, apply
  inhibition or silence, and select action policies.
- [Action policies](action-policies/manage-action-policies.md): choose channels, recipients,
  and templates, with conditional actions and optional escalation.
- [Content templates](templates/manage-content-templates.md): define the message content and format.

An alert policy selects an action policy; its actions reference notification
objects and templates. To connect these resources to a rule, follow
[rule notification setup](../rules/notifications/connect.md).
Reuse suitable resources. Creating a new object or template is not required
merely because a rule needs notifications.
