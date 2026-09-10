---
name: alibabacloud-sls-alerting
description: "Manage Alibaba Cloud SLS alerts and notifications. Use when configuring SLS alert rules, managing notification resources, or investigating alert events."
---

# Alibaba Cloud SLS Alerting

## Prerequisites

Complete these checks before executing commands; explanation-only requests do
not require CLI setup.

### Install Aliyun CLI

Run `aliyun version` to verify version >= `3.3.22`. If missing or outdated, follow
the [CLI installation guide](references/cli-installation-guide.md).

### Update Plugins

Check `aliyun sls version` and the requested command's help. When an update is
needed, update the SLS plugin:

```bash
aliyun plugin update --name sls
```

### Profile selection

Use the CLI's configured profile by default; add `--profile` only when the user
specifies a profile.

## Observability (MUST follow for every aliyun api command)

Before the first cloud call, read this skill's [manifest](references/manifest.json)
and use its top-level non-empty string `version` as `{skill-version}`. Stop and
report an invalid or missing file/version; never guess it.

Generate a fresh random 32-character lowercase hexadecimal `{session-id}` for
this skill in the conversation; reuse it for operations, pagination, and retries.
When switching skills, read the selected skill's manifest and use its own session
ID and version, including when returning to this skill.

Every cloud API command and request-only dry run **MUST** include this flag.
Local `configure`, `plugin`, `version`, and help commands are exempt:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sls-alerting/{session-id} skill-version/{skill-version}"
```

Set `SLS_ALERT_USER_AGENT` to the resolved value and pass it double-quoted.
Do not send literal placeholders, credentials, or personal identifiers.

## Select the operation

Rules define when to raise alerts. Notification resources determine how those
alerts are handled and sent. Event diagnosis explains an alert that occurred.
Read the matching management or diagnosis entry, then follow only the references
needed for the requested operation.

- [Manage alert rules](references/rules/manage-alert-rules.md): find, inspect, create,
  update, disable, enable, or delete rules.
- [Manage alert notifications](references/notifications/manage-notifications.md): manage
  notification objects, alert policies, action policies, and content templates.
- [Diagnose alert events](references/diagnosis/diagnose.md): explain trigger
  causes, frequency, and duration, or query alert history.

## Skill usage troubleshooting

For problems running commands or bundled scripts, use
[skill usage troubleshooting](references/troubleshooting.md).
Rule behavior and alert outcomes belong to the functional branches above.

## Shared operation boundaries

- Read before replacement updates and preserve unrelated fields.
- Execute changes covered by the user's request and existing authorization.
- Read back writes and compare intended fields. Configuration success does not
  prove evaluation or delivery success.
- **NEVER** run `aliyun configure get`.
- **NEVER** extract or print AccessKey IDs, AccessKey secrets, or STS tokens
  from configuration files, environment variables, or command output. Never ask
  users to paste credentials. Let the CLI use its configured authentication.

## Reference Documents

These references support all operation branches; consult them when needed.

- [CLI installation guide](references/cli-installation-guide.md): installation,
  authentication modes, and profiles.
- [Region and endpoint configuration](references/regions.md): route rule and
  ResourceRecord operations to the appropriate endpoint.
- [Related APIs](references/related-apis.md): API parameters and responses.
- [RAM policies](references/ram-policies.md): caller permissions and resource scopes.
