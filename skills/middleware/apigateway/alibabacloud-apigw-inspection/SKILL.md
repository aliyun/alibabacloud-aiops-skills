---
name: alibabacloud-apigw-inspection
description: |
  Perform instance inspection on Alibaba Cloud Cloud-Native API Gateway, AI Gateway, and API Gateway, and query Cloud Monitor metric data. Use when the user needs to view monitoring metrics of gateway instances (such as CPU usage, memory usage, connections, network IO, bandwidth, rate limiting, etc.), obtain metric data for a specific point in time or time range, or evaluate resource utilization.
  Trigger scenarios include: "check if the Cloud-Native API Gateway has enough resources", "view monitoring data of the AI Gateway instance", "inspect this API Gateway instance", "how is the gateway performing", "check if the gateway has any anomalies", "check gateway health status", etc.
---

# Cloud-Native API Gateway / AI Gateway / API Gateway Instance Inspection

## Scenario Description

Perform health inspection on Alibaba Cloud gateway instances, retrieve monitoring metric data, and generate inspection reports.

**Architecture**: `Cloud Monitor (CMS) + API Gateway (cloudapi) + Cloud-Native API Gateway / AI Gateway (apig)`

**Supported Product Types**:
| Product Type | Instance ID Format | Query Command |
|---------|-----------|----------|
| Cloud-Native API Gateway | gw-xxxxxxx | `aliyun apig list-gateways` |
| AI Gateway | gw-xxxxxxx | `aliyun apig list-gateways` |
| API Gateway (Dedicated) | apigateway-xx-xxxxxxx | `aliyun cloudapi describe-instances` |

> **Note**: API Gateway shared instances (VPC_SHARED) do not support inspection. Only dedicated instances (VPC_DEDICATED) are supported.

---

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> follow the upgrade/installation instructions below.

**Upgrade / Install Aliyun CLI** (choose one based on your platform):

- **macOS (Homebrew)**:
  ```bash
  brew install aliyun-cli        # fresh install
  brew upgrade aliyun-cli        # upgrade existing
  ```
- **Linux / macOS (binary)**:
  ```bash
  curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
  ```
- **Windows (PowerShell)**:
  ```powershell
  Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
  Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
  ```

After upgrade, verify with `aliyun version`.
For more platforms and detailed instructions, see `references/cli-installation-guide.md`.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once
for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

---

## Environment Variables

No additional environment variables required. Credentials are configured via `aliyun configure`.

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

## RAM Permission Policy

This skill only involves read-only operations and requires the following minimum RAM permissions:

| Product | RAM Action | Description |
|------|-----------|------|
| API Gateway | apigateway:DescribeInstances | List API Gateway instances |
| API Gateway | apigateway:DescribeInstanceDropPacket | View dropped packet count |
| API Gateway | apigateway:DescribeInstanceDropConnections | View dropped connection count |
| API Gateway | apigateway:DescribeInstanceSlbConnect | View concurrent connection count |
| API Gateway | apigateway:DescribeInstanceTraffic | View traffic information |
| API Gateway | apigateway:DescribeInstanceQps | View QPS data |
| Cloud-Native API Gateway / AI Gateway | apig:ListGateways | Query gateway list |
| Cloud Monitor | cms:QueryMetricData | Query monitoring data |

Full policy document: [references/ram-policies.md](references/ram-policies.md)

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
|-------|---------|------|-------|
| Product Type | Required | Cloud-Native API Gateway / AI Gateway / API Gateway | None |
| RegionId | Required | Region where the instance is located | None |
| Instance ID | Required | Unique identifier of the gateway instance | None |
| Time Range | Optional | Query time point or time range | Current time |

**Available Region Check**:
- [AI Gateway Available Regions](https://help.aliyun.com/zh/api-gateway/ai-gateway/product-overview/supported-regions)
- [Cloud-Native API Gateway Available Regions](https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/product-overview/regions)
- [API Gateway Available Regions](https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/developer-reference/api-cloudapi-2016-07-14-endpoint)

---

## Core Workflow

### Step 1: Collect Required Information

Before starting queries, the following information must be confirmed (proactively ask the user if not provided). Using default configurations is prohibited:

1. **Cloud Product Type** — Which cloud product the user wants to query.(Cloud-Native API Gateway / AI Gateway / API Gateway).
2. **Region (RegionId)** — The region where the instance is located.
3. **Instance ID** — The unique identifier of the instance.
4. **Time Range** — The time point or time range for the query.

### Step 2: Query Instance Information

> **[MUST] API Invocation Requirement:**
> The gateway list MUST be queried by calling the **Apig ListGateways** API via CLI plugin mode.
> This is a mandatory step — skipping the gateway list query is NOT allowed.
>
> **[MUST] Plugin Mode Only:**
> All commands in this skill MUST be executed using CLI plugin mode. Traditional API format (PascalCase action names) is NOT allowed.
> If the plugin is not installed, run `aliyun plugin install --names apig` to install it, then retry.

#### 2.1 Cloud-Native API Gateway / AI Gateway

**API Mapping**: Product `Apig` | Action `ListGateways` | Version `2019-01-01`

```bash
aliyun apig list-gateways --region ${region_id} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

Note: The `gatewayType` in the response indicates the instance type: `API` (Cloud-Native API Gateway), `AI` (AI Gateway)

#### 2.2 API Gateway

```bash
aliyun cloudapi describe-instances --api-version 2016-07-14 --region ${region_id} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

Note: The `InstanceType` in the response indicates the instance type. Only `VPC_DEDICATED` (dedicated) instances are supported. `VPC_SHARED` shared instances do not support inspection.

### Step 3: Retrieve Monitoring Metric Data

#### 3.1 Cloud-Native API Gateway / AI Gateway

> **[MUST] API Invocation Requirement:**
> Monitoring metrics MUST be queried using the **Cms DescribeMetricData** API via CLI plugin mode
>
> **CRITICAL — PROHIBITED APIs:**
> - **DO NOT USE** `DescribeMetricList` (`aliyun cms describe-metric-list`) — returns a different response format and is NOT accepted
> - **DO NOT USE** `DescribeMetricMetaList` (`aliyun cms describe-metric-meta-list`) — DO NOT call this API to discover or list available metrics
>
> **ALL metric names are already provided below. No metric discovery is needed:**
> - For **Cloud-Native API Gateway** instances: select metric names from the **Supported Metrics for Cloud-Native API Gateway** table below
> - For **AI Gateway** instances: select metric names from the **Supported Metrics for AI Gateway** table below
> - Use the exact `Metric Name` values from the corresponding table directly as the `--metric-name` parameter

**API Mapping**: Product `Cms` | Action `DescribeMetricData` | Version `2019-01-01` | Namespace `acs_cnapigateway`

```bash
aliyun cms describe-metric-data \
--namespace acs_cnapigateway \
--region ${region} \
--api-version 2019-01-01 \
--metric-name ${metric-name} \
--period 60 \
--start-time ${start-time} \
--end-time ${end-time} \
--dimensions '[{"instanceId": "${instanceId}"}]' \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

**Notes**:
- `start-time / end-time` use Unix millisecond timestamps
- `instanceId` must be passed in dimensions
- **MUST query ALL of the following metric categories**: CPU Usage, Memory Usage, Connections, Network IO, Rate Limiting
- Only check CPU, memory, connections, network IO, rate limiting, and bandwidth

**Supported Metrics for Cloud-Native API Gateway**:
| Metric Name | Display Name | Dimensions | Metric Period | Unit |
|---|---|---|---|---|
| EnvoyClientActiveConnection | Current active connections (gateway to client) | userId,regionId,instanceId | 60300 | count |
| EnvoyClientDestroyConnection | Destroyed connections per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| EnvoyClientDestroySSL | SSL handshake failures per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| EnvoyClientNewConnection | New connections per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| EnvoyClientNewSSL | SSL handshakes per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| EnvoyClientReuseSSL | SSL handshake reuse per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| EnvoyCpuUsageRate | Gateway CPU usage | userId,instanceId | 60300 | % |
| EnvoyFsReadBytes | Disk read load | userId,instanceId | 60300 | B/s |
| EnvoyFsWriteBytes | Disk write load | userId,instanceId | 60300 | B/s |
| EnvoyMemoryUsage | Memory load | userId,instanceId | 60300 | MiB |
| EnvoyMemoryUsageRate | Gateway memory usage | userId,instanceId | 60300 | % |
| EnvoyNetworkInBytes | Inbound network IO load | userId,instanceId | 60300 | B/s |
| EnvoyNetworkOutBytes | Outbound network IO load | userId,instanceId | 60300 | B/s |
| EnvoyRateLimitRequests | Rate-limited requests | userId,instanceId | 60300 | count/s |
| EnvoyUpstreamActiveConnection | Current active connections (gateway to backend) | userId,instanceId | 60300 | count |
| EnvoyUpstreamDestroyConnection | Destroyed connections per second (gateway to backend) | userId,instanceId | 60300 | count/s |
| EnvoyUpstreamNewConnection | New connections per second (gateway to backend) | userId,instanceId | 60300 | count/s |
| Ipv4EipRateIn | Public IPv4 inbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv4EipRateOut | Public IPv4 outbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv6GatewayRateIn | Public IPv6 inbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv6GatewayRateOut | Public IPv6 outbound bandwidth | userId,instanceId | 60300 | bit/s |
| SlbInstanceTrafficRX | Private network inbound bandwidth | userId,instanceId | 60300 | bit/s |
| SlbInstanceTrafficTX | Private network outbound bandwidth | userId,instanceId | 60300 | bit/s |

**Supported Metrics for AI Gateway**:
| Metric Name | Display Name | Dimensions | Metric Period | Unit |
|---|---|---|---|---|
| AIGatewayEnvoyClientActiveConnection | Current active connections (gateway to client) | userId,regionId,instanceId | 60300 | count |
| AIGatewayEnvoyClientDestroyConnection | Destroyed connections per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyClientDestroySSL | SSL handshake failures per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyClientNewConnection | New connections per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyClientNewSSL | SSL handshakes per second (gateway to client) | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyCpuUsageRate | Gateway CPU usage | userId,regionId,instanceId | 60300 | % |
| AIGatewayEnvoyFsReadBytes | Disk read load | userId,regionId,instanceId | 60300 | B/s |
| AIGatewayEnvoyFsWriteBytes | Disk write load | userId,regionId,instanceId | 60300 | B/s |
| AIGatewayEnvoyMemoryUsage | Memory load | userId,regionId,instanceId | 60300 | MiB |
| AIGatewayEnvoyMemoryUsageRate | Gateway memory usage | userId,regionId,instanceId | 60300 | % |
| AIGatewayEnvoyNetworkInBytes | Inbound network IO load | userId,regionId,instanceId | 60300 | B/s |
| AIGatewayEnvoyNetworkOutBytes | Outbound network IO load | userId,regionId,instanceId | 60300 | B/s |
| AIGatewayEnvoyRateLimitRequests | Rate-limited requests | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyUpstreamActiveConnection | Current active connections (gateway to backend) | userId,regionId,instanceId | 60300 | count |
| AIGatewayEnvoyUpstreamDestroyConnection | Destroyed connections per second (gateway to backend) | userId,regionId,instanceId | 60300 | count/s |
| AIGatewayEnvoyUpstreamNewConnection | New connections per second (gateway to backend) | userId,regionId,instanceId | 60300 | count/s |
| Ipv4EipRateIn | Public IPv4 inbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv4EipRateOut | Public IPv4 outbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv6GatewayRateIn | Public IPv6 inbound bandwidth | userId,instanceId | 60300 | bit/s |
| Ipv6GatewayRateOut | Public IPv6 outbound bandwidth | userId,instanceId | 60300 | bit/s |
| SlbInstanceTrafficRX | Private network inbound bandwidth | userId,instanceId | 60300 | bit/s |
| SlbInstanceTrafficTX | Private network outbound bandwidth | userId,instanceId | 60300 | bit/s |

#### 3.2 API Gateway Dedicated Instances

> **[MUST] API Invocation Requirement:**
> For API Gateway dedicated instances, you MUST use the **CloudAPI dedicated APIs** via CLI plugin mode to query monitoring data.
> **DO NOT use Cloud Monitor (CMS) for API Gateway dedicated instances.** CMS is only for Cloud-Native API Gateway / AI Gateway (Step 3.1).
>
> **The following 5 API calls are ALL mandatory:**
>
> | # | API | Product | Action | Version | Notes |
> |---|-----|---------|--------|---------|-------|
> | 1 | Dropped packets | `cloudapi` | `DescribeInstanceDropPacket` | `2016-07-14` | |
> | 2 | Dropped connections | `cloudapi` | `DescribeInstanceDropConnections` | `2016-07-14` | |
> | 3 | SLB connections | `cloudapi` | `DescribeInstanceSlbConnect` | `2016-07-14` | |
> | 4 | Traffic | `cloudapi` | `DescribeInstanceTraffic` | `2016-07-14` | Query RELEASE, PRE, TEST separately |
> | 5 | QPS | `cloudapi` | `DescribeInstanceQps` | `2016-07-14` | Query RELEASE, PRE, TEST separately |
>
> **CRITICAL: Traffic and QPS must each be queried 3 times** — once for each environment (RELEASE, PRE, TEST).
> This means a total of **7 API calls** (5 base APIs, but Traffic and QPS each × 3 environments).

**Note**: For API Gateway, skip 3.1 and execute this step directly. Time format uses ISO8601 UTC (YYYY-MM-DDThh:mm:ssZ)

```bash
# 1. Dropped packets
aliyun cloudapi describe-instance-drop-packet \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --sbc-name Maximum \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# 2. Dropped connections
aliyun cloudapi describe-instance-drop-connections \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --sbc-name Maximum \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# 3. SLB connections
aliyun cloudapi describe-instance-slb-connect \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --sbc-name Maximum \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# 4. Traffic — MUST query RELEASE, PRE, and TEST environments separately (3 calls)
aliyun cloudapi describe-instance-traffic \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name RELEASE \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

aliyun cloudapi describe-instance-traffic \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name PRE \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

aliyun cloudapi describe-instance-traffic \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name TEST \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

# 5. QPS — MUST query RELEASE, PRE, and TEST environments separately (3 calls)
aliyun cloudapi describe-instance-qps \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name RELEASE \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

aliyun cloudapi describe-instance-qps \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name PRE \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}

aliyun cloudapi describe-instance-qps \
--start-time ${start-time} --end-time ${end-time} \
--instance-id ${instanceId} --stage-name TEST \
--api-version 2016-07-14 --region ${region} \
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-apigw-inspection/{session-id}
```

### Step 4: Generate Inspection Report

#### 4.1 Anomaly Check Rules

| Metric | Normal | Warning | Critical |
|------|------|------|------|
| CPU Usage | < 70% | 70%-85% | > 85% |
| Memory Usage | < 75% | 75%-90% | > 90% |
| Connections | < 70% of max | 70%-85% | > 85% |
| Network IO | < 70% of bandwidth | 70%-85% | > 85% |
| Rate Limiting | No triggers | > 0 occurrences | Continuously increasing |

**Spike Detection**: Alert when the increase within a period exceeds the threshold (CPU > 30%, Memory > 25%, Connections > 50%, Network IO > 40%)

#### 4.2 Report Structure

The inspection report should include the following sections:
1. **Basic Information** — Product type, instance ID, region, inspection time
2. **Inspection Results Overview** — Table format showing the status of each metric
3. **Detailed Analysis** — Peak values, trends, and analysis for each metric
4. **Risk Assessment** — List of high/medium risk items
5. **Optimization Recommendations** — Recommendations based on actual issues (omit if all metrics are normal)
6. **Conclusion** — Summary of inspection results

**Important**: All data must come from actual API responses. Fabricating data is strictly prohibited.

---

## Success Verification

For verification methods, see [references/verification-method.md](references/verification-method.md)

---

## Cleanup

This skill only involves read-only operations. No resource cleanup is required.

---

## Command List

For the full command list, see [references/related-commands.md](references/related-commands.md)

---

## Best Practices

1. **Plugin Mode Only**: All commands MUST be executed using `aliyun` CLI plugin mode. Traditional API format (PascalCase action names) is NOT allowed. If a required plugin is not installed, run `aliyun plugin install --names <plugin-name>` to install it first.
2. **Confirm Parameters**: All user-customizable parameters must be confirmed before execution
3. **Check Region**: Ensure the region is within the available regions for the corresponding product
4. **Check Instance Type**: API Gateway only supports dedicated instance inspection
5. **Time Format**: Cloud Monitor uses millisecond timestamps; API Gateway uses ISO8601 UTC
6. **Data Accuracy**: Report data must come from actual API responses
7. **Risk Classification**: Strictly follow threshold standards for risk assessment

---

## Reference Links

| Document | Path |
|------|------|
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| RAM Permission Policy | [references/ram-policies.md](references/ram-policies.md) |
| Related Commands | [references/related-commands.md](references/related-commands.md) |
| Verification Method | [references/verification-method.md](references/verification-method.md) |
| Acceptance Criteria | [references/acceptance-criteria.md](references/acceptance-criteria.md) |
| AI Gateway Available Regions | https://help.aliyun.com/zh/api-gateway/ai-gateway/product-overview/supported-regions |
| Cloud-Native API Gateway Available Regions | https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/product-overview/regions |
| API Gateway Available Regions | https://help.aliyun.com/zh/api-gateway/traditional-api-gateway/developer-reference/api-cloudapi-2016-07-14-endpoint |
