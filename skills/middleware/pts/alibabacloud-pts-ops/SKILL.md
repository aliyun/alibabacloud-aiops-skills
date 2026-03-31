---
name: alibabacloud-pts-ops
description: |
  Alibaba Cloud PTS (Performance Testing Service) scenario-based skill for creating and managing stress testing scenarios.
  Supports both PTS native HTTP/HTTPS stress testing and JMeter-based stress testing.
  Triggers: "PTS", "压测", "性能测试", "stress testing", "performance testing", "JMeter", "load testing", "创建压测场景"
required_permissions:
  - pts:CreatePtsScene
  - pts:GetPtsScene
  - pts:ListPtsScene
  - pts:StartPtsScene
  - pts:StopPtsScene
  - pts:DeletePtsScene
  - pts:StartDebugPtsScene
  - pts:GetPtsReportDetails
  - pts:GetPtsSceneBaseLine
  - pts:GetPtsSceneRunningData
  - pts:GetPtsSceneRunningStatus
  - pts:SaveOpenJMeterScene
  - pts:GetOpenJMeterScene
  - pts:ListOpenJMeterScenes
  - pts:StartTestingJMeterScene
  - pts:StopTestingJMeterScene
  - pts:RemoveOpenJMeterScene
  - pts:GetJMeterReportDetails
---

# Alibaba Cloud PTS Stress Testing Scenario Management

This skill enables you to create and manage stress testing scenarios using Alibaba Cloud PTS (Performance Testing Service). It supports both PTS native HTTP/HTTPS stress testing and JMeter-based stress testing.

## Scenario Description

PTS (Performance Testing Service) is Alibaba Cloud's fully managed performance testing platform that helps you validate the performance, capacity, and stability of your applications. This skill covers:

1. **PTS Native Stress Testing** - Create HTTP/HTTPS stress testing scenarios with configurable APIs, serial links, and load models
2. **JMeter Stress Testing** - Upload and run JMeter scripts with distributed load generation

### Architecture

```
User → Aliyun CLI → PTS Service → Target Application
                         ↓
                   Stress Testing Report
```

## Pre-check

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
# Verify CLI version
aliyun version

# Enable auto plugin installation
aliyun configure set --auto-plugin-install true
```

## Timeout Settings

All CLI commands should include timeout parameters to avoid hanging:

```bash
# Recommended timeout settings for PTS operations
--read-timeout 60 --connect-timeout 10
```

- **read-timeout**: 60 seconds (stress testing operations may take longer)
- **connect-timeout**: 10 seconds

## Environment Variables

No additional environment variables required beyond CLI authentication.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, scene names, target URLs,
> concurrency, duration, JMX files, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

### User-Customizable Parameters

| Parameter Name | Required | Description | Default Value |
|---------------|----------|-------------|---------------|
| RegionId | No | Region for PTS service | cn-hangzhou |
| Scene Name | Yes | Name of the stress testing scenario | - |
| Target URL | Yes | URL to stress test | - |
| HTTP Method | Yes | GET, POST, PUT, DELETE, etc. | GET |
| Concurrency | Yes | Number of concurrent users | - |
| Duration | Yes | Test duration in seconds | - |
| JMX File | Yes (JMeter) | Path to JMeter script file | - |
| Mode | No | CONCURRENCY or TPS | CONCURRENCY |

## Authentication

This skill relies on the Aliyun CLI's default credential chain. Ensure your CLI is already authenticated before use.

Verify current authentication:

```bash
aliyun configure get
```

If CLI is not yet configured, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for setup instructions.

## RAM Policy

Users must have appropriate PTS permissions. See [references/ram-policies.md](references/ram-policies.md) for detailed policies.

## Idempotency

PTS APIs do not support `ClientToken`-based idempotency. **Scene names are not unique** — multiple
PTS or JMeter scenarios may share the same `SceneName`. Never treat “same name” as one resource;
always use **`SceneId`** (returned by the API) as the stable identifier.

To prevent duplicate resources or unintended side-effects when retrying after timeouts or errors,
**always** use the **check-then-act** pattern before every write operation:

| Operation | Check Before Acting | If Already Exists / Running |
|-----------|--------------------|-----------------------------|
| **Create PTS scene** (`save-pts-scene`) | Do **not** dedupe by name. After success, record `SceneId`. | If the prior call outcome is unknown, use `list-pts-scene` **with the user** to disambiguate before retrying; do **not** blindly retry save (each retry may create another scene). |
| **Create JMeter scene** (`save-open-jmeter-scene`) | Same as PTS — names may duplicate; use `SceneId` only. | Same pattern with `list-open-jmeter-scenes` + user disambiguation before retry. |
| **Start PTS test** (`start-pts-scene`) | `get-pts-scene-running-status` — check status | If `RUNNING` or `SYNCING`, skip; do NOT start again |
| **Start JMeter test** (`start-testing-jmeter-scene`) | `get-open-jmeter-scene` — check status | If already running, skip; do NOT start again |
| **Delete PTS scene** (`delete-pts-scene`) | Confirm target **`SceneId`** still exists (e.g. `list-pts-scene` / `get-pts-scene`) | If that `SceneId` is gone, treat as success (already deleted) |
| **Delete JMeter scene** (`remove-open-jmeter-scene`) | Confirm target **`SceneId`** still exists | If that `SceneId` is gone, treat as success (already deleted) |

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, scene names, target URLs,
> concurrency, duration, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

### Workflow 1: Create and Run PTS Native Stress Testing

#### Task 1.1: Create PTS Scenario

> **Note:** Use `save-pts-scene` instead of `create-pts-scene`. The `--scene` parameter accepts a JSON object directly (not wrapped in a `Scene` field).

> **Idempotency:** `SceneName` may duplicate across scenarios. Do **not** skip creation or pick a
> scene based on name alone. After `save-pts-scene` succeeds, record the returned **`SceneId`** for
> all later steps. If the command fails or times out with unknown outcome, use `list-pts-scene`
> together with the user to identify the intended `SceneId` before retrying — avoid blind retries
> that create extra scenes.

```bash
aliyun pts save-pts-scene \
  --scene '{
    "SceneName": "<SCENE_NAME>",
    "RelationList": [
      {
        "RelationName": "serial-link-1",
        "ApiList": [
          {
            "ApiName": "api-1",
            "Url": "<TARGET_URL>",
            "Method": "<HTTP_METHOD>",
            "TimeoutInSecond": 10,
            "RedirectCountLimit": 10,
            "HeaderList": [
              {
                "HeaderName": "User-Agent",
                "HeaderValue": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              }
            ],
            "CheckPointList": [
              {
                "CheckPoint": "",
                "CheckType": "STATUS_CODE",
                "Operator": "eq",
                "ExpectValue": "200"
              }
            ]
          }
        ]
      }
    ],
    "LoadConfig": {
      "TestMode": "concurrency_mode",
      "MaxRunningTime": <DURATION_MINUTES>,
      "AutoStep": false,
      "Configuration": {
        "AllConcurrencyBegin": <CONCURRENCY>,
        "AllConcurrencyLimit": <CONCURRENCY>
      }
    },
    "AdvanceSetting": {
      "LogRate": 1,
      "ConnectionTimeoutInSecond": 5
    }
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameter Notes:**
- `MaxRunningTime`: Duration in **minutes** (not seconds), range [1-1440]
- `TestMode`: Use `concurrency_mode` for concurrent user testing or `tps_mode` for RPS testing
- `TimeoutInSecond`: Request timeout in seconds (recommended: 10)
- `RedirectCountLimit`: Maximum redirects allowed (use `10` for normal, `0` to disable)
- `HeaderList`: HTTP headers, **User-Agent is recommended** for better compatibility
- `CheckPointList`: Assertions for response validation (STATUS_CODE, BODY_JSON, etc.)
- `AdvanceSetting.LogRate`: Log sampling rate (1-100)
- `AdvanceSetting.ConnectionTimeoutInSecond`: Connection timeout (recommended: 5)

> For complete JSON structure with all fields (POST requests, file parameters, global variables, etc.), see [references/pts-scene-json-reference.md](references/pts-scene-json-reference.md)

#### Task 1.2: Start Stress Testing

> **[MUST] Pre-flight Safety Checks** — Starting a stress test sends significant traffic to the
> target system. ALL of the following checks MUST pass before executing `start-pts-scene`:
>
> 1. **Idempotency guard** — Run `get-pts-scene-running-status --scene-id <SCENE_ID>`.
>    If the status is `RUNNING` or `SYNCING`, the test is already in progress — skip the start
>    command and proceed to monitoring. Do NOT start a duplicate test.
> 2. **Retrieve and verify scene configuration** — Run `get-pts-scene --scene-id <SCENE_ID>` and
>    confirm the response contains a valid `SceneName`, at least one `RelationList` entry with a
>    non-empty `Url`, and a valid `LoadConfig` (non-zero `MaxRunningTime` and concurrency).
>    If any field is missing or empty, abort and notify the user.
> 3. **Display test summary and require explicit user confirmation** — Present the following to
>    the user and wait for explicit approval (e.g., "yes" / "确认"):
>    - Target URL(s)
>    - Concurrency level
>    - Test duration
>    - Test mode (concurrency / TPS)
>
>    Do NOT proceed without the user's explicit "go-ahead" confirmation.

```bash
# Idempotency guard: Skip if test is already running
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
# ↑ If status is RUNNING or SYNCING, skip start-pts-scene and go to monitoring.

# Pre-flight check: Verify scene configuration is complete
aliyun pts get-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# Start stress testing (only after all checks pass and user confirms)
aliyun pts start-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 1.3: Monitor Testing Status

```bash
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 1.4: Get Testing Report

```bash
aliyun pts get-pts-report-details \
  --scene-id <SCENE_ID> \
  --plan-id <PLAN_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Workflow 2: Create and Run JMeter Stress Testing

#### Task 2.1: Create JMeter Scenario

> **Idempotency:** `SceneName` may duplicate across JMeter scenarios. Do **not** dedupe by name.
> After `save-open-jmeter-scene` succeeds, record the returned **`SceneId`**. On uncertain
> failure, use `list-open-jmeter-scenes` with the user to disambiguate before retrying.

```bash
aliyun pts save-open-jmeter-scene \
  --open-jmeter-scene '{
    "SceneName": "<SCENE_NAME>",
    "TestFile": "<JMX_FILENAME>",
    "Duration": <DURATION>,
    "Concurrency": <CONCURRENCY>,
    "Mode": "CONCURRENCY"
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 2.2: Start JMeter Testing

> **[MUST] Pre-flight Safety Checks** — Starting a JMeter stress test sends significant traffic
> to the target system. ALL of the following checks MUST pass before executing
> `start-testing-jmeter-scene`:
>
> 1. **Idempotency guard** — Run `get-open-jmeter-scene --scene-id <SCENE_ID>` and check the
>    scene status. If the test is already running, skip the start command and proceed to
>    monitoring. Do NOT start a duplicate test.
> 2. **Verify scene configuration** — From the same response, confirm it contains a valid
>    `SceneName`, a non-empty `TestFile`, and non-zero `Duration` and `Concurrency`.
>    If any field is missing or empty, abort and notify the user.
> 3. **Display test summary and require explicit user confirmation** — Present the following to
>    the user and wait for explicit approval (e.g., "yes" / "确认"):
>    - Scene name and JMX file
>    - Concurrency level
>    - Test duration
>
>    Do NOT proceed without the user's explicit "go-ahead" confirmation.

```bash
# Idempotency guard + pre-flight check: Verify scene config and check if already running
aliyun pts get-open-jmeter-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
# ↑ If already running, skip start command. If config is incomplete, abort.

# Start JMeter testing (only after all checks pass and user confirms)
aliyun pts start-testing-jmeter-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 2.3: Get JMeter Report

```bash
aliyun pts get-jmeter-report-details \
  --report-id <REPORT_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Workflow 3: Manage Scenarios

#### Task 3.1: List All PTS Scenarios

```bash
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 3.2: List All JMeter Scenarios

```bash
aliyun pts list-open-jmeter-scenes \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 3.3: Get Scenario Details

```bash
# PTS scenario
aliyun pts get-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# JMeter scenario
aliyun pts get-open-jmeter-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 3.4: Debug Scenario (PTS only)

```bash
aliyun pts start-debug-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Task 3.5: Stop Running Test

```bash
# Stop PTS test
aliyun pts stop-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# Stop JMeter test
aliyun pts stop-testing-jmeter-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Success Verification Method

> **IMPORTANT:** `start-pts-scene` may return `Success: true` even when the stress test fails to actually launch (e.g., due to target site protection or missing configuration). Always verify actual execution status.

After each operation, verify success using the verification commands in [references/verification-method.md](references/verification-method.md).

**Verify scenario creation:**
```bash
# Use list-pts-scene instead of get-pts-scene (more reliable)
aliyun pts list-pts-scene \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Verify stress test is actually running:**
```bash
# Check running status first
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# Then verify with running data (requires plan-id from start-pts-scene)
aliyun pts get-pts-scene-running-data \
  --scene-id <SCENE_ID> \
  --plan-id <PLAN_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Key indicators of successful execution:**
- `Status`: Should be "RUNNING" or "SYNCING" (not "STOPPED" immediately)
- `AliveAgents`: Should be > 0
- `Concurrency`: Should match configured value
- `TotalRequestCount`: Should be increasing

## Cleanup

Delete scenarios when no longer needed.

> **[MUST] Pre-delete Safety Checks** — Before deleting any scenario, ALL of the following
> checks MUST pass:
>
> 1. **Idempotency guard** — Using the target **`SceneId`** (not name), verify it still exists
>    (e.g. `list-pts-scene` / `list-open-jmeter-scenes` or `get-*`). If that `SceneId` is absent,
>    treat deletion as already done and skip the delete command.
> 2. **Check if the scenario is currently running** — Run
>    `get-pts-scene-running-status --scene-id <SCENE_ID>` (PTS) or check JMeter scene status.
>    If the scenario status is `RUNNING` or `SYNCING`, you MUST stop it first using
>    `stop-pts-scene` / `stop-testing-jmeter-scene` and wait for it to fully stop before deleting.
>    Do NOT delete a running scenario.
> 3. **Require explicit user confirmation** — Display the scene name and ID to the user and
>    ask for explicit deletion confirmation (e.g., "yes" / "确认删除"). Do NOT proceed without
>    the user's explicit approval.

```bash
# Pre-delete check: Verify scenario is not running
aliyun pts get-pts-scene-running-status \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete PTS scenario (only after confirming it is not running and user approves)
aliyun pts delete-pts-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete JMeter scenario (only after confirming it is not running and user approves)
aliyun pts remove-open-jmeter-scene \
  --scene-id <SCENE_ID> \
  --user-agent AlibabaCloud-Agent-Skills
```

## API and Command Tables

See [references/related-apis.md](references/related-apis.md) for complete API and CLI command reference.

## Best Practices

1. **Use complete scene configuration** - Always include `TimeoutInSecond`, `HeaderList` (with User-Agent), `CheckPointList`, and `AdvanceSetting` for reliable test execution
2. **Always confirm parameters** - Verify target URLs, concurrency settings, and duration with the user before execution
3. **Start with low concurrency** - Begin with low concurrency and gradually increase to identify performance thresholds
4. **Verify actual execution** - Don't trust `Success: true` from `start-pts-scene`; always check `get-pts-scene-running-data` with `--plan-id`
5. **Use debug mode first** - For PTS scenarios, use `start-debug-pts-scene` to validate configuration before full tests
6. **Monitor during tests** - Regularly check running status during stress tests
7. **Review reports thoroughly** - Analyze response times, error rates, and throughput in reports
8. **Clean up after testing** - Delete test scenarios to avoid unnecessary costs
9. **Use appropriate test duration** - Longer tests provide more accurate results but consume more resources
10. **Include warmup period** - Allow time for systems to warm up before measuring peak performance

## Reference Links

| Reference | Description |
|-----------|-------------|
| [cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration |
| [related-apis.md](references/related-apis.md) | Complete API and CLI command reference |
| [ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [verification-method.md](references/verification-method.md) | Verification steps for each operation |
| [pts-scene-json-reference.md](references/pts-scene-json-reference.md) | Complete PTS scene JSON structure reference |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for skill validation |
