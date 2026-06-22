---
name: alibabacloud-kafka-capacity-assessment
description: |
  Performs capacity assessment on Alibaba Cloud Kafka instances to determine whether throttling is occurring and recommends instance upgrades when capacity is running high.
  Triggers when users describe issues such as consumer lag buildup, producer send failures, throughput throttling, or connection anomalies on a Kafka instance.
  Trigger phrases: "kafka capacity assessment", "kafka throttling", "kafka consumer lag", "kafka performance bottleneck", "kafka throughput insufficient", "kafka connection limit", "kafka disk full", "kafka anomaly".
  Do NOT use for: Kafka instance creation, Topic/partition management and configuration, message send/receive code debugging, or fault diagnosis unrelated to capacity.
---

# Kafka Instance Capacity Assessment

Based on the incident information provided by the user, this skill queries CloudMonitor metrics and instance metadata to determine whether a Kafka instance has reached a capacity bottleneck, and provides upgrade recommendations accordingly.

**Architecture**: Kafka Instance (v2/v3 Series) + CloudMonitor (CMS) + Aliyun CLI

---

## Pre-check: Aliyun CLI >= 3.3.3 required

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

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

**Script / Terraform execution:** When running Python SDK scripts or Terraform commands or bash scripts, inject the session-id via inline environment variable so the code can read it at runtime:

```bash
# Python SDK script
SKILL_SESSION_ID={session-id} python3 scripts/deploy.py

# Terraform
SKILL_SESSION_ID={session-id} terraform apply
```

Scripts and Terraform configs should read `SKILL_SESSION_ID` from the environment (default to empty string if absent). See `references/how-to-implement-by-common-sdk.md` for SDK patterns.

---

## RAM Policy

This skill requires the following RAM permissions:

| API | Permission Action | Description |
|:---|:---|:---|
| `GetInstanceList` | `alikafka:GetInstanceList` | Retrieve the Kafka instance list and instance metadata |
| `DescribeMetricList` | `cms:DescribeMetricList` | Query CloudMonitor metric data |

For the full permission list, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|:---|:---|:---|:---|
| Instance Region | Required | Region ID where the instance resides, e.g. `cn-hangzhou` | None |
| Instance ID | Required | Kafka instance ID, e.g. `alikafka_post-cn-xxxxx` | None |
| Incident Time / Time Range | Optional | Minute-level precision is preferred | Last 1 hour from current time |
| Symptoms | Optional | Consumer lag / producer failure / connection anomaly, etc. | None (full assessment if omitted) |

---

## Core Workflow (SOP)

### Hard Rules

1. **This skill performs read-only operations only.** If a bottleneck is identified, inform the user which metrics need to be scaled up via the console. **Calling any write OpenAPI or executing CLI commands to upgrade the instance on behalf of the user is strictly prohibited.**
2. **v2 and v3 instances use different CloudMonitor metrics.** Always query according to the specifications below. **Using v2 MetricNames on a v3 instance, or vice versa, is strictly prohibited.**

### Step 1: Collect Incident Context

Gather parameters from the user (see the Parameter Confirmation section above). For any required parameter not yet provided, prompt for it individually.

Key symptoms to watch for:
- Message backlog / increasing consumer lag
- Producer send failures / reduced send throughput
- Reduced consumer consumption rate
- Clients unable to connect to the broker
- Messages deleted before the committed retention period expires
- Instance throughput throttled

### Step 2: Identify Instance Series, Edition, and Specification Family

```bash
aliyun alikafka get-instance-list --biz-region-id <RegionId> --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/{session-id}
```
> In Aliyun CLI Plugin Mode, the region must be passed via both `--biz-region-id` and `--region`.

Extract the following key fields from the response:
- `Series`: Identifies the instance series (`v2` or `v3`)
- **v2 series**: Refer to [Kafka v2 Instance Specification Reference](references/kafka-v2-spec-and-capacity.md) Section 1 to determine the edition and specification family
- **v3 series**: Refer to [Kafka v3 Instance Specification Reference](references/kafka-v3-spec-and-capacity.md) Section 1 to determine the edition (v3 has no specification family distinction)

If the user has provided an instance ID, filter by it:
```bash
aliyun alikafka get-instance-list --biz-region-id <RegionId> --region <RegionId> --instance-id <InstanceId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/{session-id}
```

Filter by series:
```bash
aliyun alikafka get-instance-list --biz-region-id <RegionId> --region <RegionId> --series v2 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/{session-id}
```

### Step 3: Infer Metrics Likely Approaching Their Limits

Based on the symptoms described by the user and the capacity bottleneck guidance in the knowledge base, infer the likely bottleneck:

| Symptom | Probable Bottleneck Metric |
|:---|:---|
| Messages deleted before retention period expires | Disk space at capacity |
| Message backlog | Network throughput throttled, or produce/consume request rate throttled |
| Producer send throughput degraded | Produce traffic throttled or produce request rate throttled |
| Consumer consumption rate degraded | Consume traffic throttled or consume request rate throttled |
| Clients unable to connect to broker | Connection count at limit (necessary but not sufficient — verify with metrics) |

### Step 4: Query CloudMonitor Metric Data

#### 4.1 Determine Query Parameters

Based on the `Series` value confirmed in Step 2, determine the Namespace and MetricName:
- **Namespace**: Fixed value — `acs_kafka`
- **v2 instance MetricNames**: See [Kafka v2 Instance Specification and Capacity Policy](references/kafka-v2-spec-and-capacity.md) Section 5
- **v3 instance MetricNames**: See [Kafka v3 Instance Specification, Elastic Strategy, and Capacity Policy](references/kafka-v3-spec-and-capacity.md) Section 6

#### 4.2 Construct the Query Command

```bash
aliyun cms describe-metric-list \
  --namespace acs_kafka \
  --metric-name <MetricName> \
  --period 60 \
  --start-time "<start time YYYY-MM-DD HH:mm:ss>" \
  --end-time "<end time YYYY-MM-DD HH:mm:ss>" \
  --dimensions '[{"instanceId":"<InstanceId>"}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-kafka-capacity-assessment/{session-id}
```

**Parameter notes:**
- `--period`: Aggregation interval in seconds; valid values: 15 / 60 / 900 / 3600. Recommended: 60
- `--start-time` / `--end-time`: Time range; the interval must not exceed 31 days; the range is left-open, right-closed. **If the user does not specify a time range, default to the last 1 hour** (`--end-time` = current time, `--start-time` = current time - 1 hour), and note this in the diagnostic report
- `--dimensions`: JSON string specifying the instance ID

#### 4.3 Query the Applicable Metrics by Instance Series

**Metrics for v2 instances** (select based on the inferred bottleneck from Step 3):

| MetricName | Description | Bottleneck Threshold |
|:---|:---|:---|
| `InstanceMessageInputRatioV2` | Produce traffic as a percentage of instance specification limit | Approaching 100% indicates a bottleneck |
| `InstanceMessageOutputRatioV2` | Consume traffic as a percentage of instance specification limit | Approaching 100% indicates a bottleneck |
| `PartitionInstanceRatioV2` | Partition count as a percentage of instance specification limit | Approaching 100% indicates a bottleneck |
| `instance_disk_capacity` | Instance disk utilization | **> 80%** indicates near-full; Kafka dynamic cleanup begins |
| `InstanceMaxConnection` | Maximum connections per node (public + private network) | Compare against formula-calculated limit |
| `InstanceMaxInternetConnection` | Maximum connections per node (public network only) | Compare against formula-calculated limit |
| `instance_reqs_input` | Produce request rate (requests/sec) | Compare against formula-calculated limit |
| `instance_reqs_output` | Consume request rate (requests/sec) | Compare against formula-calculated limit |

**Metrics for v3 instances** (select based on the inferred bottleneck from Step 3):

| MetricName | Description | Bottleneck Threshold |
|:---|:---|:---|
| `InstanceMessageInputRatioV3` | Produce traffic as a percentage of the elastic ceiling | > 100% means the elastic ceiling is exceeded and throttling is occurring; (0%, 100%] means reserved capacity is exceeded, incurring elastic overage charges |
| `InstanceMessageOutputRatioV3` | Consume traffic as a percentage of the elastic ceiling | Same as above |
| `InstanceMaxConnectionRatioV3` | Connection utilization per node (public + private network) | Approaching 100% indicates a bottleneck |
| `InstanceMaxInternetConnectionRatioV3` | Connection utilization per node (public network only) | Approaching 100% indicates a bottleneck |
| `InstanceThrottleTimeP99InputV3` | Produce throttle duration | **> 0 indicates active throttling** |
| `InstanceThrottleTimeP99OutputV3` | Consume throttle duration | **> 0 indicates active throttling** |

### Step 5: Analyze Findings and Generate Diagnostic Report

#### 5.1 Analysis

Combine the following inputs for a comprehensive assessment:
1. Instance metadata (Step 2) → obtain the **specification limits** for each metric
2. CloudMonitor data (Step 4) → obtain the **actual usage** of each metric during the incident window
3. When investigating a historical incident, prioritize **ratio-based metrics** (e.g., `InstanceMessageInputRatioV2`, `instance_disk_capacity`, `InstanceMessageInputRatioV3`) or **anomaly-based metrics** (e.g., `InstanceThrottleTimeP99InputV3`). Fall back to **absolute-value capacity metrics** only if the preferred metrics return no data.

**v2 instance capacity limit calculation:**
> See [Kafka v2 Instance Specification and Capacity Policy](references/kafka-v2-spec-and-capacity.md) Section 3

**v3 instance capacity limit calculation:**
> See [Kafka v3 Instance Specification, Elastic Strategy, and Capacity Policy](references/kafka-v3-spec-and-capacity.md) Sections 2–4

#### 5.2 Generate Diagnostic Report

Output the following structured report to the user:

```markdown
## Kafka Instance Capacity Assessment Report

### Basic Information
- Instance ID:
- Region:
- Instance Series: v2 / v3
- Edition:
- Specification:
- Incident Time:

### Incident Summary
- User-Reported Symptoms:
- Anomalous Metrics:

### Monitoring Data Analysis
| Metric Name | Observed Value | Specification Limit | Utilization / Threshold Exceeded | Conclusion |
|:---|:---|:---|:---|:---|
| ... | ... | ... | ... | ... |

### Diagnostic Conclusion
- Root Cause:
- Metrics at or Exceeding Limit:

### Upgrade Recommendations
- Metrics to scale up and recommended target values:
- How to proceed: Navigate to Alibaba Cloud Console > Cloud Message Queue for Apache Kafka > Instance Details > Upgrade
```

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for verification steps.

---

## Cleanup

This skill performs read-only query operations only and **does not create or modify any resources**. No cleanup is required.

---

## Command Tables

For a complete list of CLI commands used by this skill, see [references/related-commands.md](references/related-commands.md).

---

## Best Practices

1. Prefer ratio/percentage metrics for bottleneck detection to avoid inconsistencies caused by historical data recorded under a different specification tier
2. For v3 instances, distinguish between "reserved capacity" and "elastic ceiling": exceeding reserved capacity only incurs elastic overage charges; throttling occurs only when the elastic ceiling is exceeded
3. CloudMonitor data has an approximate 1-minute propagation delay; account for this time offset when querying
4. For v2 instances, when disk utilization exceeds 80%, Kafka begins dynamic log cleanup, which may cause messages to be deleted before the configured retention period
5. Applicable only to standard instances listed in official Alibaba Cloud documentation; not applicable to non-standard instances or self-managed Kafka clusters
6. Calling any write-operation API is prohibited; only read-only queries are permitted
7. v2 and v3 instances use different CloudMonitor MetricNames; mixing them is strictly prohibited

---

## Reference Links

| Document | Description |
|:---|:---|
| [Knowledge Base Notes and Freshness Advisory](references/README.md) | Last-updated timestamp, data staleness risks, and links to official documentation |
| [Kafka v2 Instance Specification and Capacity Policy](references/kafka-v2-spec-and-capacity.md) | v2 instance specification tables, partition limits, connection count / request rate formulas, disk cleanup policy, CloudMonitor metrics, and bottleneck troubleshooting guide |
| [Kafka v3 Instance Specification, Elastic Strategy, and Capacity Policy](references/kafka-v3-spec-and-capacity.md) | v3 instance elastic strategy, elastic ceiling calculation, connection count / request rate formulas, CloudMonitor metrics, and bottleneck troubleshooting guide |
| [CLI Installation Guide](references/cli-installation-guide.md) | Complete guide for installing and configuring Aliyun CLI |
| [RAM Policies](references/ram-policies.md) | Full list of RAM permissions required by this skill |
| [Related Commands](references/related-commands.md) | All CLI commands used by this skill |
| [Verification Method](references/verification-method.md) | Steps for verifying capacity assessment results |
| [Acceptance Criteria](references/acceptance-criteria.md) | Acceptance criteria and test scenarios for this skill |
