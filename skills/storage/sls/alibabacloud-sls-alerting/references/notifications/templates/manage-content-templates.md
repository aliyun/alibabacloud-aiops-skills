# Manage content templates

A content template renders alert data into each channel's message text and
format. An action policy selects the template; the template does not select
recipients or enable a channel.

- Read or reuse: use [record reads](../api/resource-records.md#read-and-reuse)
  with `resource_name = sls.alert.content_template`. Prefer built-in `sls.builtin.cn`
  when suitable; do not recreate or overwrite it.
- Create or change message content: follow [create or update](create-update-content-template.md).
- Delete: inspect known action-policy references, then use
  [record deletion](../api/resource-records.md#delete) for the exact ID.

The outer ID/tag map to `template_id` / `template_name` in the decoded value.
