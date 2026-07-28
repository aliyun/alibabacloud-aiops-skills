---
name: alibabacloud-rocketmq-inspection
description: Read-only batch health inspection for Alibaba Cloud RocketMQ instances (4.x classic and 5.x serverless). Pulls metrics from CMS namespace acs_rocketmq and management APIs via aliyun CLI plugin mode, emits a scored Markdown report. Triggers include "RocketMQ inspection", "MQ health check", "consumer lag", "consumer delay", "message backlog", "DLQ", "RocketMQ inspect".
---

# Alibaba Cloud RocketMQ Inspection

A read-only inspection skill for Alibaba Cloud RocketMQ. Pulls cloud-monitoring metrics, resource quotas, and consumer-group runtime state across one or many instances, then renders a scored Markdown report.

Use this skill when the user asks to:

- Run a health check / inspection on RocketMQ instance(s).
- Investigate consumer lag, consumption delay, message backlog, throttling, or DLQ growth.
- Audit resource-quota usage (Group count, Topic count, retention) against the per-instance and per-region limits.
- Deep-dive into a single consumer group when the summary flags it.

## Read-only constraint (hard)

This skill MUST only call `Describe* / List* / Get* / *Status / *Info` APIs. Any `Create / Delete / Update / Modify / Set / Put / Reset / Send` style call is forbidden — these would mutate cloud resources or message state and violate the skill's contract.

When adding new API calls, verify the HTTP method is GET via `aliyun <product> <command> --help` before merging.

Only local writes are allowed: the Markdown report (current directory), intermediate JSON (`/tmp/rocketmq-inspection-{pid}/`), and the user threshold file on first run.

RAM permissions required to operate the skill are documented in [references/ram-policies.md](references/ram-policies.md).

## Prerequisites

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> download the installer first, then run it locally:
> ```bash
> curl -fsSL -o /tmp/aliyun-cli-setup.sh https://aliyuncli.alicdn.com/setup.sh
> bash /tmp/aliyun-cli-setup.sh
> ```
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

Run once per host (or after AccessKey rotation / RAM policy changes):

```bash
bash <skill_root>/scripts/preflight.sh
```

Preflight verifies the `aliyun` CLI, credentials (`sts get-caller-identity`), `jq`, and the four CLI plugins this skill uses (`aliyun-cli-cms`, `aliyun-cli-sts`, `aliyun-cli-ons`, `aliyun-cli-rocketmq`). Missing plugins are auto-installed into `~/.aliyun/plugins/` via `--auto-plugin-install true`.

All CLI calls in this skill are in **plugin mode** — kebab-case commands and parameters. The PascalCase OpenAPI-passthrough form is not used.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once
for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id}
```

Concrete examples from this skill's scripts:

```bash
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} cms describe-metric-list --namespace acs_rocketmq --metric-name InstanceApiCallTps --period 60 --start-time ... --end-time ... --dimensions ...
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} ons ons-group-list --instance-id <id> --region cn-hangzhou
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} rocketmq get-consumer-group-lag --instance-id <id> --consumer-group-id <gid> --region cn-hangzhou
aliyun --user-agent AlibabaCloud-Agent-Skills/alibabacloud-rocketmq-inspection/{session-id} sts get-caller-identity
```

**Script execution:**

```bash
SKILL_SESSION_ID={session-id} bash <skill_root>/scripts/inspect.sh ...
SKILL_SESSION_ID={session-id} bash <skill_root>/scripts/diagnose_group.sh ...
SKILL_SESSION_ID={session-id} bash <skill_root>/scripts/preflight.sh
```

## Invocation

```bash
bash <skill_root>/scripts/inspect.sh \
  [--instances <id1,id2,...>] \
  [--config <yaml>] \
  [--all] \
  [--version 4|5|both] \
  [--window 24h] \
  [--region cn-hangzhou|all]
```

**Instance selection (priority high → low)**:
1. `--instances` — explicit comma-separated IDs. Version (4 vs 5) is auto-detected from the ID prefix.
2. `--config <yaml>` — see `assets/instances.example.yaml` for the schema.
3. `--all` — discover instances via management API in the selected region(s).

**`--region all`** scans 22 mainstream AliCloud regions. Regions without RocketMQ service silently skip.

**Time window** (`--window`) accepts `Ns`, `Nm`, `Nh`, `Nd` suffixes. Default `24h`. CMS retains 60s-granularity data for 31 days, so values up to `30d` work.

**Ghost instances**: An ID that appears in CMS but returns `Instance.NotFound` from `get-instance` / `ons-instance-base-info` is recorded in the report's "Skipped instances" section and not pulled further. This avoids wasting calls on released instances whose 31-day metric skeleton is still cached.

## Threshold configuration

The threshold file lives at `<skill_root>/thresholds.yaml`. On first run, `inspect.sh` copies `assets/thresholds.default.yaml` to that path and prints the location. Edit it to match your business tolerance — changes apply on the next run, no restart needed.

Defaults are conservative (e.g. any throttle event trips `warn`). See [references/thresholds.md](references/thresholds.md) for the full table and the health-score algorithm.

## Output

Two report types, both written to the current working directory:

- `./rocketmq-inspection-{YYYYMMDD-HHmm}.md` — main inspection
- `./group-diagnose-{groupId}-{YYYYMMDD-HHmm}.md` — single-group deep dive (see below)

Report layout:

1. Region quota — instance count per region vs the 1000-per-region cap
2. Skipped instances — ghosts
3. Summary — health score per instance with top issues
4. Per-instance detail — 5 collapsible metric sections, resource quota (incl. message retention), Group health, Consumer runtime state (incl. 5.x `inflightCount` against the 2500 cap), Topic load (internal `%RETRY%` / `%DLQ%` / `%SYS%` topics filtered)
5. Failed metric fetches, if any

Health score: every instance starts at 100, deducts 5 per warn match and 15 per critical, floored at 0. Tiers: ≥80 healthy, 60–79 watch, <60 critical.

Intermediate raw JSON (one file per metric per instance) is kept under `/tmp/rocketmq-inspection-{pid}/` for ad-hoc inspection.

## Single-group deep diagnosis

When the main report flags a specific group (high lag, latency, inflight, or DLQ), run:

```bash
bash <skill_root>/scripts/diagnose_group.sh \
  <instanceId> <groupId> [--region cn-hangzhou]
```

The diagnose report contains:
- Group config (consume model, delivery order, retry policy)
- Live client connections (ID / IP / language / version) — empty list usually explains a "lag with no progress" symptom
- Lag broken down by Topic (`readyCount` / `inflightCount` / `deliveryDuration` / `lastConsumeTimestamp`)
- An automated conclusion suggesting the most likely cause

4.x and 5.x instances are auto-detected and routed to the appropriate API set.

## Metrics covered

32 cloud-monitoring metrics under namespace `acs_rocketmq`, grouped as:

- **Instance dimension** (22): API TPS / utilization / send-receive TPS / online-clients / connections / throttling / public bandwidth / drop / storage
- **Group dimension** (7): ConsumerLag / LagLatency / Ready / DLQ / throttling
- **Topic dimension** (3): send / receive / send-throttle

Plus three quota probes (Group count, Topic count, retention) via management APIs and per-group Consumer runtime state.

The full metric catalogue (49 metrics in `acs_rocketmq`, of which 32 are enabled here) and what's intentionally excluded (fine-grained Group×Topic dimensions, migration-task metrics) is in [references/metrics.md](references/metrics.md).

## Common pitfalls

The aliyun CLI has several non-obvious behaviours that have bitten this skill during development — timezone interpretation on naked time strings, `Dimensions` JSON shape, `Datapoints` being a stringified JSON, the 50 QPS account cap, plugin-mode parameter name differences. They are catalogued in [references/cli-pitfalls.md](references/cli-pitfalls.md). Read it before extending the skill.

## Performance notes

- Single instance, 24h window: ~30s (32 metric calls + quota + per-group consumer status)
- Full account multi-region (3 instances, 22 regions probed): 2–5 min
- CMS `describe-metric-list` is capped at 50 QPS per account; the skill serialises calls with `sleep 0.05` for a ~30 QPS ceiling

## Out of scope

- Scheduling — wrap with the `loop` skill if recurring runs are needed
- Alerting — no DingTalk / email / webhook push
- Cross-run trend diffs
- AccessKey / RAM management — relies on `aliyun configure`
- Any cloud-side write operation
