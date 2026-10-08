# Skill usage troubleshooting

Use this guide when a command or bundled script fails. For missing chart data,
incorrect values or controls that do not respond, follow
[dashboard diagnosis](workflows/diagnose.md).

## Setup and command failures

| Problem | Check or next step |
| --- | --- |
| Script not found | Resolve scripts relative to the skill directory, not the current project. Use the entrypoint's `--help` to confirm the command |
| Python or package missing | Use Python 3.10+ and follow [Python dependencies](cli-installation-guide.md#python-dependencies), including the optional packages for metric StoreView queries and subscriptions |
| `aliyun` or an SLS command is unavailable | Check CLI version >= 3.3.22, the SLS plugin and the command help; follow [installation and upgrade](cli-installation-guide.md) |
| User-Agent missing or invalid | Follow [Observability](../SKILL.md#observability-required-for-cloud-operations). Export `ALIBABACLOUD_SLS_DASHBOARD_USERAGENT` in the command environment, using this skill's manifest version and conversation session ID |
| Manifest missing or invalid | Restore the skill's packaged [manifest](manifest.json). Do not invent a version |
| Unexpected command argument | Use `python3 scripts/sls.py COMMAND --help` or `python3 scripts/dashboard.py COMMAND --help`. Subscription actions use `dashboard.py subscription ACTION --help` |

Offline build and validation do not require cloud credentials or a User-Agent.

## Connection and access failures

Check the profile, region, project and resource name. Use
[connection options](datasources/api.md#connection-options) to select the profile
and endpoint consistently. For connection failures, check endpoint reachability
from the current host.

For authentication or permission errors, check that the selected profile is usable
and the caller has the [RAM permissions](ram-policies.md) for the requested operation
and source Project. Dashboard
access does not grant datasource access. Do not print credentials or ask
users to paste secrets; use the configured authentication method.

For a missing resource, verify its exact name and location before changing the
configuration. Keep a StoreView's own name rather than querying a member store.

## Configuration and write failures

- **Invalid Plan or chart:** inspect the reported field path, then use the
  [Plan guide](model/plan.md) or the matching [chart reference](charts/charts.md).
- **Baseline conflict:** fetch the current dashboard, review the changes and
  reconcile through the [edit workflow](workflows/edit.md) before updating.
- **Write request failure or timeout:** inspect the target before retrying.
  A failed response does not prove the write failed. Follow
  [publish verification](workflows/publish.md).
- **Subscription failure:** check existing reports, channels, schedule and
  source Projects in the [subscription workflow](integrations/subscriptions.md).
  A saved report does not establish successful notification delivery.

Report the failing operation, error code and checks performed. Keep credentials
and private notification URLs out of troubleshooting output.
