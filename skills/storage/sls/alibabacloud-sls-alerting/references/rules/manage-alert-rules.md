# Manage alert rules

An alert rule runs queries on a schedule, evaluates their results, and selects
how triggered alerts enter notification processing. A rule belongs to a Project.

- To create a rule or change its settings, follow [create or update a rule](create-update-alert-rule.md).
- To find, inspect, disable, enable, or delete a rule, use the operations below.
- To temporarily mute a rule or cancel its mute, follow [mute or unmute a rule](mute-alert-rule.md).

Use the stable rule ID for operations. Resolve a supplied display name to a
unique ID by listing and inspecting matches; do not substitute the display name.

Rule mutations succeed with exit `0` and no output; failures return a nonzero
exit code and error information.

## List and inspect

Commands use `aliyun sls` and the owning `--project`.

| Operation | Command | Parameters |
| --- | --- | --- |
| List | `list-alerts` | `--offset`, `--size` (at most 200); optional `--logstore` filter |
| Inspect | `get-alert` | `--alert-name` with the stable rule ID |

List responses contain `results`, `count`, and `total`. Advance the zero-based
`--offset` by the returned `count` to retrieve further pages.

The rule's `status` is `ENABLED` or `DISABLED`; values are case-sensitive.

## Enable, disable, or delete

Use `enable-alert`, `disable-alert`, or `delete-alert` with the same
`--project` and `--alert-name` as `get-alert`. These operations take no rule body.
Confirm the resulting status, or absence after deletion.

Rule deletion does not include shared users, policies, or templates.
