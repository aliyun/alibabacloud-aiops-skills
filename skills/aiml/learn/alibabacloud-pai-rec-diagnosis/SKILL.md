---
name: alibabacloud-pai-rec-diagnosis
description: |
  Alibaba Cloud PAI-Rec Engine Diagnostic and Configuration Validation Skill.
  Use for diagnosing PAI-Rec engine interface issues and validating engine configurations.
  Triggers: "PAI-Rec", "engine diagnosis", "engine config validation", "pairec", "recommendation engine".
---

# PAI-Rec Engine Diagnosis and Configuration Validation

This skill provides comprehensive diagnostic and validation capabilities for Alibaba Cloud PAI-Rec (Programmable Recommendation System) engines, including interface troubleshooting and configuration analysis.

## Scenario Description

PAI-Rec is Alibaba Cloud's programmable recommendation system that provides intelligent recommendation capabilities. This skill helps users:

1. **Diagnose PAI-Rec Engine Interface Issues**: When engine API returns errors or unexpected results, trace the request through EAS service logs and engine configurations to identify root causes.

2. **Validate Engine Configurations**: Analyze engine configuration files for potential issues, inconsistencies, or misconfigurations before deployment.

**Architecture**: PAI-EAS Service + PAI-Rec Engine + Engine Configuration Management

### Key Components
- **PAI-EAS Service**: Elastic Algorithm Service hosting the recommendation engine
- **PAI-Rec Engine**: The recommendation engine processing requests
- **Engine Configuration**: Configuration files defining engine behavior
- **Service Logs**: EAS service logs containing request traces

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

For detailed RAM policies required by this skill, see [references/ram-policies.md](references/ram-policies.md).

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, service names, instance IDs,
> environment names, config names, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

### Required Parameters

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `service-name` | Required | PAI-EAS service name | N/A |
| `cluster-id` | Required | EAS cluster/region ID | N/A |
| `instance-id` | Required | PAI-Rec instance ID | N/A |
| `request-id` | Required (for diagnosis) | Request ID from engine API response | N/A |
| `config-name` | Optional | Engine configuration name | N/A |
| `environment` | Optional | Engine environment (Prod/Pre) | N/A |
| `engine-config-id` | Optional | Specific engine config version ID | N/A |
| `region` | Optional | Alibaba Cloud region | N/A |

---

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis"
> ```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

### Workflow 1: PAI-Rec Engine Interface Diagnosis

This workflow helps diagnose issues when a PAI-Rec engine API returns errors or unexpected results.

**Input Example:**
```
Service Name: embedding_recall
API Response:
{
    "code": 299,
    "msg": "items size not enough",
    "request_id": "941b4e14-d1c5-489f-a184-b2b17f8b4fdb",
    "size": 0,
    "experiment_id": "",
    "items": []
}
```

#### Step 1: Retrieve EAS Service Information

Get the service details to find the EAS service ID and configuration:

```bash
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name>
```

**What to extract:**
- `Resource`: EAS service resource ID (e.g., `eas-r-1v4qb1yan3qmnjwxqe`)
- `ServiceConfig.envs`: Environment variables containing:
  - `REGION`: The region
  - `INSTANCE_ID`: PAI-Rec instance ID
  - `CONFIG_NAME`: Engine configuration name
  - `PAIREC_ENVIRONMENT`: Environment (product/prepub)

#### Step 2: Extract Request ID from API Response

Parse the API response JSON to get the `request_id` field. This will be used to search service logs.

#### Step 3: Query EAS Service Logs

Use the request ID as the **sole** filter to search service logs. Do NOT pass `--start-time` / `--end-time` when searching PAI-Rec business logs:

```bash
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  --keyword <request-id> \
  --page-size 500
```

**[CRITICAL] Known CLI pitfall — keyword-only lookup is required for business logs:**
- When only `--keyword` is supplied (no time range), the CLI returns the full PAI-Rec application trace (`controller.go` / `feed.go` / `recall.go` / `rank_service.go` etc.) matching the request_id.
- As soon as `--start-time` / `--end-time` are added — even if the window covers the real log timestamp — the CLI silently drops business logs and only returns infrastructure noise (`/bin/sh` wrapper heartbeats, `502 Bad Gateway` retries, `postgres.go dbstat`).
- Therefore: for request-level diagnosis, always omit the time range and rely on `--keyword <request-id>` alone.

**Notes:**
- `--keyword`: Use the full `request_id` extracted from the API response (case-sensitive exact match).
- `--page-size`: Raise to 500 to capture the entire trace in a single page; total matched entries for one request is usually < 30.
- `--start-time` / `--end-time`: Only use these for broad time-window scans **without** `--keyword` (e.g., when investigating non-request-specific issues). Required format is `yyyy-MM-dd HH:mm:ss` in UTC (space separator, no `T` / no `Z`). ISO-8601 forms like `2025-04-28T00:00:00Z` will be rejected with `InvalidParameter`.

#### Step 4: List Engine Configurations

Map the environment and list matching configurations:

**Environment Mapping:**
- `product` → `Prod`
- `prepub` → `Pre`

```bash
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id> \
  --environment <Prod|Pre> \
  --status Released \
  --name <config-name>
```

**What to extract:**
- Find the configuration with `Status: Released`
- Get `EngineConfigId` and `Version`

#### Step 5: Get Engine Configuration Details

```bash
aliyun pairecservice get-engine-config \
  --instance-id <instance-id> \
  --engine-config-id <engine-config-id>
```

**What to extract:**
- `ConfigValue`: The actual engine configuration (JSON/YAML)

#### Step 5.5 (Optional): Static Config Sanity Check

Optionally run `scripts/validate.py` against the retrieved `ConfigValue` to quickly
rule out structural / reference / naming errors in the engine configuration
before diving into the log trace. See Workflow 2 § Step 3 and
[references/config-validation.md](references/config-validation.md) for usage,
exit codes, and the full rule list.

```bash
printf '%s' "$CONFIG_VALUE" | python3 scripts/validate.py --stdin
```

**When to run:** when the log trace points at a specific configuration element
(e.g. a `RecallConfs` / `FilterConfs` / `SceneConfs` entry), or when the
configuration is being diagnosed for the first time in this skill session.

**When to skip:** when the log trace already shows a decisive non-config root
cause (e.g. a `scene_id` not present in `SceneConfs`, a 5xx from an upstream
EAS dependency, a missing feature table). `validate.py` is a static checker and
cannot detect request-time mismatches between client input and configuration.

**[MUST] Scoping rule for the final report:**
- `validate.py` findings may enter the final diagnosis ONLY when they are
  directly tied to the log evidence for the current `request_id`
  (e.g. the log blames a `RecallConf` name that `validate.py` flags as
  duplicated or dangling).
- Findings unrelated to the current `request_id` trace MUST NOT be added to the
  final conclusion. They remain an internal sanity-check signal only. This
  preserves the evidence-only reporting rule in Step 6.

#### Step 6: Comprehensive Analysis

Analyze the following components together:
1. **API Response**: Error code, message, and returned data
2. **Service Logs**: Trace logs for the request_id showing processing flow
3. **Engine Configuration**: Settings that may affect the behavior

**Common Issues to Check:**
- Configuration mismatches (e.g., recall settings, filtering rules)
- Resource limitations (e.g., insufficient items, timeout settings)
- Data source issues (e.g., table access, feature availability)
- Environment inconsistencies (e.g., prod config in prepub environment)

**[MUST] Evidence-only reporting rule:**

The final diagnosis delivered to the user MUST be grounded strictly in what the EAS service logs and the engine configuration directly show. Apply the following constraints:

- **Report only what is observed.** Quote the exact log line (file:line, level, message) and the exact config fragment that proves each claim.
- **State the direct causal chain** from log evidence to the API response, and stop there.
- **Do NOT add** any of the following unless the user explicitly asks:
  - Speculative root causes not visible in logs/config (e.g., "client probably sent wrong X")
  - Fix recommendations or remediation steps
  - Conditional "if X then Y" scenarios
  - Tangential best-practice advice (security, fallback design, naming, etc.)
  - Guesses about upstream systems, client code, or data sources not covered by the logs/config
- **If the evidence is insufficient** to reach a conclusion, state explicitly what additional data (specific log lines, other config versions, other environments) is needed, instead of guessing.
- **Recommendations are opt-in only.** Provide fixes/suggestions only when the user explicitly requests them in a follow-up.

---

### Workflow 2: PAI-Rec Engine Configuration Validation

This workflow validates engine configurations for potential issues.

**Input:** Configuration name and environment (Prod/Pre)

#### Step 1: List Configuration Versions

If user doesn't provide `engine-config-id`, list available versions:

```bash
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id> \
  --environment <Prod|Pre> \
  --name <config-name>
```

**Display to user:**
- `Version`: Version number
- `Status`: Configuration status (Released/Draft/Archived)
- `GmtCreateTime`: Creation timestamp
- `EngineConfigId`: Version ID

Ask user to select a version or provide the `engine-config-id`.

#### Step 2: Retrieve Configuration Details

```bash
aliyun pairecservice get-engine-config \
  --instance-id <instance-id> \
  --engine-config-id <engine-config-id>
```

#### Step 3: Run Schema + Rule Validation

**[MUST]** Feed the extracted `ConfigValue` JSON into `scripts/validate.py`. The script
enforces JSON Schema (`references/schema.json`) + reference-consistency rules and exits
with status 0 on pass, 1 on failure.

```bash
# From stdin (recommended when ConfigValue is already in memory)
printf '%s' "$CONFIG_VALUE" | python3 scripts/validate.py --stdin

# From a saved JSON file
python3 scripts/validate.py /tmp/engine-config.json

# From an inline JSON string
python3 scripts/validate.py '{"RunMode":"product","RecallConfs":[...]}'
```

Requires `jsonschema` (`pip install jsonschema`); if missing the script falls back to
rule-only validation without Schema checks.

**What the script checks (summary):**

1. **Structure** — JSON well-formedness, required fields, types (`RunMode`,
   `RecallConfs`, `FilterConfs`, `SortConfs`, `AlgoConfs`, `SceneConfs`, `RankConf`,
   `FeatureConfs`, `UserFeatureConfs`, `DebugConfs`, `FeatureLogConfs`,
   `CallBackConfs`, `PipelineConfs`, etc.)
2. **Enum values** — `RecallType` / `FilterType` / `SortType` / `RunMode` /
   `DebugConfs.OutputType` / `GeneralRankConfs.ActionConfs[].ActionType`
3. **Reference consistency** — `SceneConfs.RecallNames` → `RecallConfs`;
   `FilterNames` → `FilterConfs`; `SortNames` → `SortConfs`;
   `RankConf.RankAlgoList` → `AlgoConfs`; any `DaoConf.AdapterType` +
   `*Name` → the corresponding `*Confs` (Hologres / Redis / MySQL / TableStore /
   FeatureStore / …)
4. **Business rules**
   - `User2ItemExposureFilter` with `WriteLog=true` + FeatureStore adapter: must set
     `TimeInterval > 0`
   - `PriorityAdjustCountFilter` in `accumulator` mode: `Count` must be strictly
     increasing (use `Type="fix"` for independent per-recall caps)
   - `PipelineConfs.*.Name` must be globally unique
   - `DebugConfs.Rate` must be an integer in `[0, 100]`
5. **Duplicate name detection** within `RecallConfs`, `FilterConfs`, `SortConfs`,
   `AlgoConfs`

Detailed usage, exit codes, example outputs and the full rule list live in
[references/config-validation.md](references/config-validation.md).

#### Step 4: Evidence-Grounded Report

Report to the user based strictly on the script's output plus any additional
inspection of `ConfigValue`:

- ✅ Checks passed (Schema clean, references resolved, no rule violations)
- ⚠️  Warnings reported by the script (severity=warning) or inconsistencies
  observed in `ConfigValue` (e.g. naming collisions between `RankScore` variables
  and model output fields, env/region mismatches)
- ❌ Errors reported by the script (severity=error) or missing required fields
- Missing-evidence notes — what extra data (other config versions, model
  signatures, etc.) would be needed to turn a warning into a confirmed error

Do not add speculative fixes or best-practice tangents; suggestions are provided
only when the user explicitly asks for them.

---

## Success Verification Method

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

**Quick Verification:**

1. **For Diagnosis Workflow:**
   - Service information retrieved successfully
   - Logs found containing the request_id
   - Configuration loaded correctly
   - Root cause identified

2. **For Validation Workflow:**
   - Configuration retrieved successfully
   - All validation checks executed
   - Issues clearly reported
   - Recommendations provided (if applicable)

---

## Cleanup

This skill performs read-only operations and does not create any resources that require cleanup.

---

## Best Practices

1. **Always capture request_id**: When reporting API issues, include the full response with request_id for accurate log correlation.

2. **Log queries — keyword only, no time range**: For request-level diagnosis, pass `--keyword <request_id>` to `aliyun eas describe-service-log` and leave `--start-time` / `--end-time` unset. Combining keyword with a time range filters out business logs due to a CLI quirk (see Workflow 1, Step 3). Only use time ranges for broad non-request scans, and only with the `yyyy-MM-dd HH:mm:ss` UTC format (no `T` / no `Z`).

3. **Environment awareness**: Always verify that configurations match the target environment (Prod vs Pre).

4. **Version control**: When validating configurations, check multiple versions if issues persist across deployments.

5. **Log retention**: EAS service logs are retained for limited periods; diagnose issues promptly after occurrence.

6. **Configuration backup**: Before applying changes based on validation results, ensure current configurations are backed up.

7. **Cross-reference**: Compare working configurations with problematic ones to identify differences.

8. **Service status**: Check EAS service status before diagnosing; service-level issues may mask configuration problems.

9. **Evidence-only conclusions**: Ground every statement in the diagnosis on a specific log line or config fragment. Do not speculate, do not propose fixes, and do not volunteer best-practice advice unless the user explicitly asks. If the evidence is insufficient, say what is missing rather than inferring.

10. **Structured analysis**: Follow the systematic workflow rather than jumping to conclusions based on error messages alone.

11. **Document findings**: Keep track of recurring issues and their resolutions for faster future diagnosis.

---

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [RAM Policies](references/ram-policies.md) | Required RAM permissions for PAI-Rec and EAS APIs |
| [Related Commands](references/related-commands.md) | Complete CLI command reference |
| [Verification Method](references/verification-method.md) | Detailed verification procedures |
| [CLI Installation Guide](references/cli-installation-guide.md) | Alibaba Cloud CLI installation instructions |
| [Configuration Examples](references/configuration-examples.md) | Sample engine configurations and common patterns |
| [Config Validation](references/config-validation.md) | `scripts/validate.py` usage, exit codes, rule catalogue |
| [Troubleshooting Guide](references/troubleshooting-guide.md) | Common issues and solutions |
