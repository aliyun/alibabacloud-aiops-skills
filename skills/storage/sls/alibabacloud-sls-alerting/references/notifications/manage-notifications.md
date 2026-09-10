# Manage alert notifications

Notification resources control who receives alerts, how they are processed and
sent, and what the messages contain. They can be reused by multiple rules.

- [Notification objects](objects/manage-notification-objects.md): people, groups, or integrations
  that receive messages. Choose an object type to manage destinations or members.
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
