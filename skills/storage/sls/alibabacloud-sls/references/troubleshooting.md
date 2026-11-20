# Troubleshooting

Use the symptom and operation context to find relevant explanations and methods.

## Environment and access

| Symptom | Context and possible checks | Details |
| --- | --- | --- |
| Command `aliyun` is unavailable | Executable location and whether its directory is on `PATH`. | [Installation](cli-installation-guide.md) |
| An expected command or option is missing | Installed CLI/plugin versions and the command's available options. | [Version requirements](../SKILL.md#requirements), [updates](cli-installation-guide.md#version-checks-and-updates) |
| `unknown profile <name>` or `no credentials available` | Selected profile and authentication configuration; `aliyun configure list` lists available profiles. | [Profile configuration](profile-configuration.md) |
| `InvalidAccessKeyId.NotFound` or `SignatureDoesNotMatch` | Selected profile, credential provider status, and signing configuration. | [Profile configuration](profile-configuration.md) |
| `SignatureVersionNotSupported` | Some regions may not support v1 signing. Enable v4 with `--cli-sign-version v4 --region <region-id>`. V4 signing requires the correct target region; an endpoint override does not replace it. | [Region and endpoint configuration](regions.md) |
| `InvalidSecurityToken.Expired` | Temporary credential expiry and renewal through the issuing mechanism. | [Profile configuration](profile-configuration.md) |
| `Unauthorized` or a RAM permission error | The action and resource used by the operation, and their authorization scope. | [Capability permissions](#capability-specific-troubleshooting) |
| `ProjectNotExist` | Project name, selected account, and owning region; cross-region discovery can help locate a Project. | [Region and endpoint configuration](regions.md) |
| Connection failure or an unexpected endpoint | Target address, public/internal network reachability, and proxy settings. | [Region and endpoint configuration](regions.md) |

## CLI error output

Follow [General conventions](../SKILL.md#general-conventions) for command success
and failure diagnostics. Preserve available diagnostic details when reporting
the failure. Local errors may have no HTTP status or request ID; missing details
alone do not establish an infrastructure failure or justify a retry.

## Capability-specific troubleshooting

| Capability | Context | Troubleshooting | Permissions |
| --- | --- | --- | --- |
| Log collection | Installation, collection configuration, missing data and machine-group heartbeat. | [Collection troubleshooting](loongcollector/troubleshooting.md), [installation and configuration](loongcollector/entry.md) | [Collection permissions](loongcollector/ram-policies.md) |
| Query | Matching, indexes, syntax, time ranges and result precision. | [Query troubleshooting](query/troubleshooting.md) | [Query permissions](query/ram-policies.md) |
| Index | Index existence, configuration fields and index operations. | [Index troubleshooting](index/troubleshooting.md) | [Index permissions](index/ram-policies.md) |
| Alerting | Rule and notification configuration, triggering and delivery. | [Alerting troubleshooting](alerting/troubleshooting.md) | [Alerting permissions](alerting/ram-policies.md) |
| Dashboard | Python tools, configuration, persistence, subscriptions and display. | [Dashboard troubleshooting](dashboard/troubleshooting.md) | [Dashboard permissions](dashboard/ram-policies.md) |
