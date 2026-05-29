---
name: alibabacloud-cms-manage
description: |
  Entry skill for the aliyun CLI distribution of CloudMonitor (CMS).
  Use when the user mentions aliyun cms2, CloudMonitor, CMS commands,
  or any CMS module operation such as Integration Policy/Center, APM, RUM,
  Prometheus Service, Recording rule, alert rule, alert template, alert history,
  event hub, SLS event, PromQL, cloud resource, service observability,
  monitoring onboarding, metric query, etc.
license: Apache-2.0
compatibility: aliyun-cli>=3.3.15
metadata:
  domain: aiops
  owner: cms
  contact: cms@alibaba-inc.com
---

# CMS CLI — `aliyun cms2`

## Prerequisite Check

1. **Check `aliyun` exists** — `which aliyun` (macOS/Linux) or `where aliyun` (Windows).
   - Not found → ask the user to install the aliyun CLI first: <https://help.aliyun.com/document_detail/121541.html>. Stop and wait.

2. **Check CLI version** — run `aliyun version`. Minimum required: **3.3.15** (see `compatibility` in frontmatter).

   > ⚠️ Compare version segments as **integers** (semver): 3.3.4 < 3.3.15 because 4 < 15.
   > Shell verification: `printf '%s\n' "3.3.15" "$(aliyun version)" | sort -V | head -1`
   > If the output equals the current version, the requirement is NOT met.

   - Version OK → go to step 3.
   - Version too old or unrecognized →
     1. Run `aliyun upgrade --help` to test whether the `upgrade` subcommand exists.
        - Available → run `aliyun upgrade -y` to update to the latest version automatically, then re-check `aliyun version`.
     2. If `upgrade` not available → run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash`, then re-check `aliyun version`.
     3. If upgrade succeeded → go to step 3.
     4. If upgrade failed → ask the user to upgrade manually: <https://help.aliyun.com/zh/cli/update-cli>. Stop and exit.

3. **Check `cms2` plugin** — run `aliyun cms2 --help`.
   - Help output OK → continue to **Credentials**.
   - `unknown command` / missing → **stop immediately**, output the error report below (append CLI version, OS, and error message), and make **no further CLI calls**.

---

## Credentials

`aliyun cms2` reuses the aliyun CLI credential system (`aliyun configure`).
Use `--profile <name>` to switch profiles.

## AI-Mode

Execute the following before and after business commands:

```bash
# Before — enable AI-Mode and set User-Agent
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cms-manage"
aliyun plugin update

# ... execute business commands (aliyun cms2 ...) ...

# After — disable AI-Mode
aliyun configure ai-mode disable
```

## Global Conventions

**Hard constraint**: fallback to `aliyun cms`, other API versions, or any workaround is strictly prohibited.

> **Always run `aliyun cms2 <command> [subcommand] --help` first** to get the full flag list and examples.

- **Prefer `-o text`** (default) to reduce token consumption for list/get; use `-o json` only when indented JSON is needed.
- **Before onboarding concrete resource IDs**, verify them with `entity query --source CloudResource`; do not rely on ID shape alone.
- **`entity query` default time range**: when the user does not specify `--from`/`--to`, default to the last 7 days (`--from` = now − 7d, `--to` = now, both as Unix seconds).

## Error Handling

Error codes and actions are listed in `aliyun cms2 --help`. Additional tips:

- `InvalidJSON` usually means malformed `--body`; validate with `jq . <<<'<value>'` before passing to the CLI.
- `--body and stdin are mutually exclusive; specify only one` — means both `--body` (or `--file`) and stdin data were provided. Fix: keep only one input source. In agent/CI environments where stdin may be a pipe, append `< /dev/null` to the command to ensure stdin is empty.

## Module Routing

| User Intent Keywords | Commands | Module |
|---------------------|----------|--------|
| onboarding, monitoring addon, policy, integration, addon release, metric metadata | `integration` `metric-meta` | [references/integration.md](references/integration.md) |
| alert, rule, alert rule, alert template, alert history, patch, create rule, manage rule | `alert rule` `alert template` `alert history` | [references/alerting.md](references/alerting.md) |
| APM measureCode, group/filter/groupBy, baseUnit/displayUnit | `alert rule` (APM type) | [references/apm-metrics.md](references/apm-metrics.md) |
| UModel metricSet, K8s pod metric, entity-based alert | `alert rule` (UModel type) | [references/umodel-metrics.md](references/umodel-metrics.md) |
| notification, contact, robot, webhook, notification recipients, dingTalk, bots, lark, weChat work | `notification-channel contact` `notification-channel robot` `notification-channel webhook` | [references/alerting.md](references/alerting.md) |
| event, event-hub, alert event, SLS event, incident | `event-hub` | [references/event-hub.md](references/event-hub.md) |
| Grafana, dashboard | `grafana` | references/grafana.md *(planned)* |
| APM, application monitoring, agent install, Java agent, Golang agent, Python agent, Node.js agent, PHP agent, .NET agent, ack-onepilot, OpenTelemetry onboarding, K8s/ACK/ACS container onboarding, ECS host onboarding, LicenseKey, proprietary agent, instgo, aliyun-bootstrap, probe setup, apm onboarding | `apm service` `apm configuration` | [references/apm.md](references/apm.md) |
| AI observability, Dify, LangChain, LangGraph, DashScope, AgentScope, OpenAI, Coze, OpenClaw, CoPaw, Hermes, LLM monitoring, AI tracing, AI agent monitoring, custom instrumentation | `apm service` `apm configuration` `integration addon` | [references/ai.md](references/ai.md) |
| RUM, Real User Monitoring, User Experience Monitoring, frontend monitoring, web monitoring, H5, mobile app monitoring, Android crash, iOS crash, JS error, page performance, miniapp monitoring, create RUM app, RUM SDK, pid, serviceId, endpoint | `rum service` `rum configuration` | [references/rum.md](references/rum.md) |

Commands not listed above — see `aliyun cms2 --help`.
