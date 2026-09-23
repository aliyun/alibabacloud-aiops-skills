---
name: alibabacloud-csas-device-health-monitor
description: >
  Read-only health and risk monitoring for endpoint devices enrolled in Alibaba Cloud SASE (CSAS).
  Diagnose a device or scan a fleet for CPU or memory pressure, battery health, disk saturation, and online
  status. Use when users report a slow, hot, laggy, or draining endpoint, or ask about sustained CPU or memory
  use, battery health, disk capacity, online status, or devices
  with recent performance risks. It does not count inventory, assess idle devices, check client versions, or
  lock, recall, delete, or otherwise modify devices. Triggers: "CSAS device health", "slow endpoint", "CPU or memory pressure",
  "battery health", "disk saturation", "endpoint online status".
---

# CSAS Device Health Monitor

This skill performs only read-only CSAS API calls. A fleet scan may write a local resume file; it never alters CSAS devices.

## Prerequisites

- Aliyun CLI version 3.3.3 or later and `jq` 1.6 or later are required. Check with `aliyun version` and `jq --version`.
- For first installation or a major CLI upgrade, use `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`. For routine updates on CLI 3.3.5 or later, use `aliyun upgrade`.
- Before the first CSAS call, the script checks for `aliyun-cli-csas` and, if needed, installs it non-interactively with `aliyun plugin install --name aliyun-cli-csas < /dev/null`. This prepares only a local CLI dependency; it does not modify global CLI configuration or any CSAS cloud resource.
- Verify only credential status with `aliyun configure list`. Do not read, print, enter, or embed credential values. If no valid profile is available, stop and have the user configure their identity outside this session.

## Permissions and Confirmation

Read `references/ram-policies.md` before running the workflow. If a permission failure occurs, read that file, use the `ram-permission-diagnose` skill to request the listed permission, then pause until the user confirms it was granted.

Before a cloud call, confirm the device selector, region/profile context, lookback window, thresholds, scan limit, and any local resume path with the user.

## Observability

Before the first cloud API invocation, read `references/manifest.json` from this skill root and use only its non-empty `version`. Stop on a missing or invalid manifest. Generate a fresh random 32-character lowercase hexadecimal session ID for this skill, reuse it only while this skill is active, and generate a distinct ID after switching skills. Never reuse or copy a documented ID.

Every actual cloud API command, including commands called by `scripts/device-health.sh`, must append exactly:

```bash
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-csas-device-health-monitor/{session-id} skill-version/{skill-version}"
```

The script reads the current manifest and creates the session ID itself. Do not use deprecated AI-mode configuration or an exported global user-agent variable.

## Workflow

1. Run `scripts/device-health.sh --profile <profile> --region <region> list-devices --limit 20 --sort-by UpdateTime` to discover candidate devices. Use this script rather than a manually assembled `aliyun csas` command, so every cloud call receives the required user agent.
2. Run `scripts/device-health.sh --profile <profile> --region <region> device-report --device <DeviceTag-or-hostname> --days 7` for a complete point-in-time report plus CPU and memory trends. Any exact CSAS DeviceTag is accepted, including non-UUID mobile tags; an exact hostname is resolved only when no matching tag exists.
3. Run `scripts/device-health.sh --profile <profile> --region <region> workload-trend --device <selector> --metric cpu --days 7` when only one workload needs analysis. Provide `--from` and `--to` instead of `--days` for an exact epoch window, and use `--max-gap-seconds` to control when sampled workload points no longer count as consecutive.
4. Run `scripts/device-health.sh --profile <profile> --region <region> health-scan --days 7 --limit 100 --resume-file .device-health-state/scan.json` for a bounded synchronous fleet scan. Split larger fleets into caller-managed runs.

All commands emit one JSON result on stdout and progress or errors on stderr. A workload sample above its threshold is an `observation`; two consecutive high samples within the permitted gap are a `warning`. Device reports show both `device_status` (the CSAS terminal state) and `collection_status` (snapshot reporting recency); do not present either as a substitute for the other. Fleet scans place only warnings and critical findings in `flagged`; observations are not fleet alerts. CSAS workload points are approximately ten-minute samples, so no result claims an exact duration. Android, iOS, Harmony, stale, and otherwise incomplete telemetry is `insufficient_data`, not healthy. A zero battery value without valid collection-time and capacity evidence is reported as `insufficient_data` while preserving the static snapshot evidence. Use the user's language for explanations, but in every final health summary retain these exact bilingual metric labels: `Disk (磁盘)`, `Battery (电池)`, `CPU`, `Memory (内存)`, and `Collection status (上报状态)`. Always cover those five dimensions; name `insufficient_data` only for telemetry that is actually unavailable.

## References

- `references/api-contract.md` describes supported calls and output behavior.
- `references/cli-installation-guide.md` provides CLI installation and upgrade steps.
- `references/state-files.md` specifies the local scan resume format.
- `references/acceptance-criteria.md` lists expected and prohibited behavior.
- `references/operational-limits.md` covers rate limiting and partial results.
- `references/live-test-guide.md` describes isolated, current-account read-only integration tests.
