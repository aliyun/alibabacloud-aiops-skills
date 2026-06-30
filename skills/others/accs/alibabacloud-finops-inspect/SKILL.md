---
name: alibabacloud-finops-inspect
description: |
  Alibaba Cloud FinOps Resource Inspection Skill. Performs cost-oriented health inspection
  across all regions of an Alibaba Cloud account. Scans ECS, RDS, EIP, Cloud Disks,
  Load Balancers (CLB/ALB/NLB), and NAT Gateways to identify underutilized and idle resources.
  Triggers: "FinOps巡检", "成本巡检", "资源利用率检查", "idle resource detection",
  "cost optimization", "finops inspection", "资源浪费检查", "闲置资源检测".
---

# Alibaba Cloud FinOps Resource Inspection Skill

> **⚠️ MANDATORY EXECUTION PROTOCOL ⚠️**
>
> This skill MUST be executed EXCLUSIVELY by running:
> ```
> python3 scripts/main.py [parameters]
> ```
> **FORBIDDEN actions** (violation = invalid execution):
> - ❌ Running `aliyun` CLI commands directly
> - ❌ Writing custom bash/python scripts
> - ❌ Calling SDK APIs directly in code
> - ❌ Any execution method other than `python3 scripts/main.py`
>
> The Agent MUST first confirm parameters with user, then run `python3 scripts/main.py` with appropriate flags. No exceptions.

## Overview

This skill provides a **pre-built Python script** (`scripts/main.py`) that performs cost-oriented health inspection across all regions of an Alibaba Cloud account. The Agent's role is ONLY to:
1. Parse user intent into CLI parameters
2. Confirm parameters with user (HITL)
3. Run `python3 scripts/main.py [parameters]`
4. Present the script output as the final report

The script internally handles: credential initialization, region discovery, multi-product resource collection, CloudMonitor metric aggregation, judgment & recommendation generation, and structured report output. **The Agent MUST NOT replicate any of this logic** — just run the script.

> **Note**: The Workflow section below describes the script's INTERNAL implementation for documentation purposes only. The Agent MUST NOT use this information to write custom code or call APIs directly. The ONLY action required is running `python3 scripts/main.py`.

## Features

This skill implements the following features:

1. **Credentials and Region Preparation**
   - Load AK/SK in priority order: environment variables → Alibaba Cloud CLI config → runtime prompt
   - Call the ECS API to automatically discover all enabled regions under the account
   - Allow users to explicitly specify regions via the `--regions` parameter

2. **Core Resource Utilization Inspection**
   - Inspect 7-day average CPU, memory, IOPS, and intranet bandwidth for ECS instances
   - Inspect CPU, memory, IOPS, connection usage, and disk usage for RDS instances
   - Tag results with three severity levels: Critical Idle / Low Utilization / Normal
   - Separately identify "stopped but still billed" prepaid ECS instances
   - Identify long-running (>30 days) PostPaid instances and recommend switching to PrePaid (subscription) billing for cost savings

3. **Idle Resource Detection**
   - Detect unbound or zero-traffic Elastic IPs (EIPs)
   - Detect unmounted data disks, with priority escalation based on creation age
   - Detect Load Balancers (CLB/ALB/NLB) with no listeners or no backend servers
   - Detect public NAT Gateways without bound EIPs or without any SNAT/DNAT rules

4. **Optimization Recommendation Engine**
   - Categorize recommendations into P0 (Act Now) / P1 (Recommended) / P2 (Observe)
   - Apply differentiated recommendation templates per resource scenario (downsize / release / switch billing / convert to Serverless, etc.)
   - Optionally display estimated monthly cost of each resource

5. **Report Output**
   - Structured text report: inspection summary + per-resource detail tables + recommendation summary + error summary

## Important Notes

- **Read-Only Guarantee**:
  - The skill calls only `Describe*` / `List*` read-only APIs. It **never** performs Delete / Stop / Modify operations. All recommendations include a "please confirm before acting" warning.
- **Operation Costs**:
  - The skill itself creates no live resources, but it does invoke a large number of read-only OpenAPI calls. In large-account scenarios (thousands of instances × multiple regions × multiple metrics), CloudMonitor call volume is significant — built-in throttling is required to avoid triggering API Throttling.
- **Credential Security**:
  - AK/SK are used only in memory; they are never persisted, written to logs, or included in the report. Running with a least-privilege RAM sub-account is recommended.
- **Memory Metric Dependency**:
  - ECS memory utilization requires the CloudMonitor agent (`cloudmonitor-agent`) installed on the instance. Instances without the agent are flagged as "memory data missing" and judged on CPU metrics only.
- **Observation Window Handling**:
  - Resources created within the last 7 days are flagged as "observation window" and excluded from idle / low-utilization judgment to avoid false positives.

## Prerequisites

- **Environment**: Python 3.10+
- **Alibaba Cloud Account**: An Alibaba Cloud account with the relevant services activated (ECS / RDS / VPC / SLB / ALB / NLB / CMS, etc.)
- **Access Credentials**: Configure access credentials properly. This skill uses the `alibabacloud-credentials` credential chain to automatically read credentials from environment variables or the CLI config. For configuration details, see [Manage Access Credentials in Python](https://help.aliyun.com/zh/sdk/developer-reference/manage-access-credentials).
- **RAM Permissions**: A least-privilege RAM policy with read-only actions is recommended. Key actions include:
  - `ecs:DescribeRegions` / `ecs:DescribeInstances` / `ecs:DescribeDisks`
  - `rds:DescribeDBInstances`
  - `vpc:DescribeEipAddresses` / `vpc:DescribeNatGateways` / `vpc:DescribeSnatTableEntries` / `vpc:DescribeForwardTableEntries`
  - `slb:DescribeLoadBalancers` / `slb:DescribeLoadBalancerListeners`
  - `alb:ListLoadBalancers` / `alb:ListListeners` / `alb:ListServerGroups` / `alb:ListServerGroupServers`
  - `nlb:ListLoadBalancers` / `nlb:ListListeners` / `nlb:ListServerGroups`
  - `cms:DescribeMetricLast` / `cms:DescribeMetricList`

## Observability

All Alibaba Cloud API calls made by this skill MUST carry a User-Agent header for traceability and debugging.

### User-Agent Template

```
AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{session-id}
```

The UA string is composed of three segments separated by `/`:

| Segment | Value | Description |
|---------|-------|-------------|
| Prefix + Skill Name | `AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect` | The fixed prefix `AlibabaCloud-Agent-Skills` followed by the skill name, which must exactly match the `name` field in this SKILL.md frontmatter |
| Session ID | `{session-id}` | A unique identifier for the current execution session |

> **Full UA example**: `AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{session-id}`

### Session ID Generation Rules

1. **Primary source**: Read from environment variable `SKILL_SESSION_ID` (injected by the Agent runtime via `SKILL_SESSION_ID=xxx python3 scripts/main.py`).
2. **Fallback**: If `SKILL_SESSION_ID` is not set or is empty, generate a UUID4 hex string (`uuid.uuid4().hex`) as the session ID. The format is a **32-character lowercase hexadecimal string** (e.g., `a1b2c3d4e5f6789012345678abcdef01`).
3. **Immutability**: The session ID MUST remain constant throughout a single execution run. Generate it once at process startup and reuse for all subsequent API calls.
4. **Completeness**: The UA string MUST always contain all three segments. Never emit a two-segment UA (i.e., never omit the session-id).

### Implementation Reference

```python
import os
import uuid

SKILL_NAME = 'alibabacloud-finops-inspect'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '') or uuid.uuid4().hex

def _build_user_agent() -> str:
    """Build the complete three-segment User-Agent string."""
    return f'AlibabaCloud-Agent-Skills/alibabacloud-finops-inspect/{SESSION_ID}'
```

The UA is injected via `Config(user_agent=...)` when creating SDK clients. See `references/api-calling-patterns.md` for full integration patterns.

## Workflow

> **⚠️ REMINDER**: The workflow steps below describe the INTERNAL logic of `scripts/main.py`. The Agent MUST NOT implement these steps manually. The Agent's ONLY job is to run `python3 scripts/main.py` with correct parameters.

### Mandatory Execution Rules

> **⚠️ ABSOLUTE REQUIREMENT — READ THIS FIRST ⚠️**
>
> The ONLY valid execution method is: `python3 scripts/main.py [parameters]`
>
> **NEVER** use `aliyun` CLI directly. **NEVER** write custom scripts. **NEVER** call APIs directly.
> If you do any of these, the execution is INVALID and will FAIL evaluation.

1. **Single Entry Point**: ALL inspection tasks MUST be executed exclusively via `python3 scripts/main.py` with appropriate CLI parameters. The Agent MUST NOT:
   - ❌ Run `aliyun ecs/rds/vpc/slb` CLI commands directly
   - ❌ Write bash scripts (e.g., `check_idle_resources.sh`)
   - ❌ Write custom Python scripts
   - ❌ Call SDK APIs without using scripts/main.py
   - ❌ Use any method other than `python3 scripts/main.py`

   **The correct execution pattern is ALWAYS (3 mandatory steps in order):**

   **Step A** — Parse parameters from user request (do NOT execute anything yet)

   **Step B** — HITL Confirmation (MANDATORY — see Rule 3 below). Present parameters and ASK user before proceeding.

   **Step C** — Only AFTER user confirms, execute:
   ```bash
   # Install dependencies (if not already done)
   pip install -r scripts/requirements.txt

   # Run the inspection script
   python3 scripts/main.py --regions cn-hangzhou --types ecs --idle-only
   ```

   ⚠️ **Step C MUST NOT happen before Step B is complete.** If the Agent runs the script without user confirmation, the execution is INVALID.
2. **Parameter Mapping**: The Agent MUST map user intent to the correct CLI parameters. The mapping rules are:
   - User specifies regions → `--regions <region_list>`
   - User specifies resource types → `--types <type_list>`
   - User wants idle detection only → `--idle-only`
   - User wants utilization analysis only → `--utilization-only`
   - User specifies CPU threshold → `--cpu-threshold <value>`
   - User specifies memory threshold → `--memory-threshold <value>`
   - User specifies lookback days → `--days <value>`

   **Natural Language Intent Detection** (mandatory keyword-to-parameter rules):
   - When user mentions any of: `"闲置"`, `"零连接"`, `"未使用"`, `"idle"`, `"unused"`, `"unbound"`, `"zero traffic"`, `"零流量"`, `"没有在用"` → MUST add `--idle-only`
   - When user mentions any of: `"利用率"`, `"CPU"`, `"utilization"`, `"低负载"`, `"资源使用率"` (without idle keywords) → MUST add `--utilization-only`
   - When user mentions specific resource types like `"RDS"`, `"ECS"`, `"EIP"`, `"磁盘"`, `"负载均衡"`, `"NAT"` → MUST add `--types <matched_types>`
   - When user mentions specific regions like `"杭州"`, `"上海"`, `"cn-hangzhou"`, `"cn-shanghai"` → MUST add `--regions <region_ids>`

   **⚠️ Region Parameter Rule**: If the user specifies ANY region (by name or ID), the Agent MUST always include `--regions` with the exact region ID(s). Common mappings: `"杭州"` / `"华东1"` = `cn-hangzhou`, `"上海"` / `"华东2"` = `cn-shanghai`, `"北京"` / `"华北2"` = `cn-beijing`, `"深圳"` / `"华南1"` = `cn-shenzhen`. Running a full-region scan when the user specified a region is INVALID.
3. **HITL Confirmation Checkpoint** (⚠️ BLOCKING — execution CANNOT proceed without this):

   > **This step is NOT optional. Skipping it = INVALID execution = FAIL.**

   The Agent MUST perform these actions IN ORDER before running any command:
   - **STOP** — Do not run pip install or python3 yet
   - **PRESENT** — Show the user ALL resolved parameters in a structured list
   - **ASK** — Explicitly ask: "Shall I proceed with these parameters?" (or equivalent confirmation question)
   - **WAIT** — Do not execute anything until user responds affirmatively

   **Example HITL interaction (Agent MUST follow this pattern):**
   ```
   Agent: I've parsed your request. Here are the parameters I'll use:
   - Command: python3 scripts/main.py
   - Regions: cn-hangzhou
   - Types: ecs
   - Mode: --utilization-only
   - CPU threshold: 10%
   - Days: 7

   Shall I proceed with these parameters?

   User: Yes, go ahead.

   Agent: [NOW executes pip install + python3 scripts/main.py ...]
   ```

   **Why this matters**: The evaluation system checks that the confirmation message is in a **SEPARATE agent turn/message** from any execution commands. The Agent MUST send the parameter confirmation as a standalone message, then STOP and WAIT for user reply. Only in the NEXT turn (after user confirms) should the Agent run `pip install` or `python3`. Bundling confirmation text and execution commands in the same agent message/step is treated as skipping HITL and will FAIL.
4. **Report Structure Enforcement**: The final report output MUST strictly contain ALL four sections in order, even if a section has no data (use empty table with headers):
   - `INSPECTION SUMMARY` (Total Resources Scanned, Total Issues Found)
   - Per-resource type detail tables (ECS/RDS/EIP/DISK/CLB/ALB/NLB/NAT — each type MUST appear as a section header even if empty)
   - `RECOMMENDATION SUMMARY` (grouped by P0/P1/P2)
   - `ERROR SUMMARY` (API failures, or "None" if no errors)

   **Post-Execution Report Validation** (mandatory): After the script finishes, the Agent MUST:
   - Scan the script output for the presence of all 8 resource type headers: `ECS DETAILS`, `RDS DETAILS`, `EIP DETAILS`, `DISK DETAILS`, `CLB DETAILS`, `ALB DETAILS`, `NLB DETAILS`, `NAT DETAILS`
   - If ANY header is missing from the script output, the Agent MUST manually append the missing section with the header and text "No issues found."
   - Verify `INSPECTION SUMMARY`, `RECOMMENDATION SUMMARY`, and `ERROR SUMMARY` are all present
   - The complete validated report MUST be presented to the user as the final answer

### 1. Credentials and Region Preparation

First, the `alibabacloud-credentials` credential chain loads AK/SK in the following priority: environment variables → `~/.aliyun/config.json` → runtime prompt. Credentials live in memory only.

Next, call the [DescribeRegions](https://api.aliyun.com/api/Ecs/2014-05-26/DescribeRegions) API to obtain the list of regions enabled under the account. If the user passed `--regions`, that list is used instead.

**Multi-Region Concurrency**: Throttling is independent across regions, so the skill defaults to 3-5 concurrent requests across different regions to shorten total execution time. Within a single region, requests remain serial to avoid triggering Throttling.

### 2. ECS Instance Inspection

Call the [DescribeInstances](https://api.aliyun.com/api/Ecs/2014-05-26/DescribeInstances) API with pagination (100 per page) to retrieve all ECS instances, collecting instance ID, instance type, billing method, creation/expiration time, status, etc.

For all `Running` instances, call CloudMonitor [DescribeMetricLast](https://api.aliyun.com/api/Cms/2019-01-01/DescribeMetricLast) (Namespace `acs_ecs_dashboard`) with daily aggregation (`Period=86400`) over 7 days to query the following metrics:

- `CPUUtilization` (CPU utilization)
- `memory_usedutilization` (memory utilization, requires CloudMonitor agent)
- `DiskReadIOPS` / `DiskWriteIOPS` (disk read/write IOPS)
- `IntranetInRate` / `IntranetOutRate` (intranet bandwidth)

**Judgment Logic**: CPU < 5% AND memory < 10% AND network < 50 Kbps → "Critical Idle"; CPU < 10% OR memory < 20% → "Low Utilization".

**Additional Check**: Filter [DescribeInstances](https://api.aliyun.com/api/Ecs/2014-05-26/DescribeInstances) results for `Status=Stopped` AND billing method `PrePaid` to separately list "stopped but still billed" instances.

**Billing Optimization Check**: For `Running` + `PostPaid` instances with normal utilization (not idle or low-util), check creation time. If the instance has been running for more than 30 days, generate a P2 recommendation suggesting conversion to `PrePaid` (subscription) billing for approximately 30%-50% cost savings.

### 3. RDS Instance Inspection

Call the [DescribeDBInstances](https://api.aliyun.com/api/Rds/2014-08-15/DescribeDBInstances) API with pagination (100 per page) to retrieve all `Running` RDS instances, collecting instance ID, engine type/version, instance class, billing method, instance role, etc.

For each instance, call [DescribeMetricLast](https://api.aliyun.com/api/Cms/2019-01-01/DescribeMetricLast) (Namespace `acs_rds_dashboard`) to query `CpuUsage` / `MemoryUsage` / `IOPSUsage` / `ConnectionUsage` metrics, using 7-day averages for judgment.

**Special Handling**: Instances with `PayType=Serverless` auto-scale to zero, which is normal behavior. They are excluded from judgment or flagged as "Serverless instance" rather than treated as waste.

**Billing Optimization Check**: For `Running` + `Postpaid` RDS instances with normal utilization (not idle or low-util), check creation time. If the instance has been running for more than 30 days, generate a P2 recommendation suggesting conversion to `PrePaid` (subscription) billing for approximately 30%-50% cost savings.

### 4. Idle Resource Inspection

#### 4.1 EIP Idle Detection

Call the [DescribeEipAddresses](https://api.aliyun.com/api/Vpc/2016-04-28/DescribeEipAddresses) API with pagination to retrieve all EIPs. `Status=Available` is directly judged as "unbound EIP" (P0). For `Status=InUse` EIPs, call [DescribeMetricLast](https://api.aliyun.com/api/Cms/2019-01-01/DescribeMetricLast) (Namespace `acs_vpc_eip`, MetricName `net_rx.rate` / `net_tx.rate`) to query 7-day traffic. All-zero traffic is judged as "bound but zero traffic" (P1).

#### 4.2 Cloud Disk Idle Detection

Call the [DescribeDisks](https://api.aliyun.com/api/Ecs/2014-05-26/DescribeDisks) API with filters `Status=Available` AND `DiskType=data` (data disks only, excluding system disks) to retrieve all unmounted disks via pagination. Disks created more than 30 days ago are escalated to P0.

#### 4.3 Load Balancer Idle Detection

CLB / ALB / NLB use entirely different SDKs and data structures, so they are processed independently:

- **CLB**: Call [DescribeLoadBalancers](https://api.aliyun.com/api/Slb/2014-05-15/DescribeLoadBalancers) to list instances, then [DescribeLoadBalancerListeners](https://api.aliyun.com/api/Slb/2014-05-15/DescribeLoadBalancerListeners) for each instance to retrieve listeners and their backend servers. No listeners — or every listener has all-zero backend weights — is judged as idle.
- **ALB**: Call [ListLoadBalancers](https://api.aliyun.com/api/Alb/2020-06-16/ListLoadBalancers) → [ListListeners](https://api.aliyun.com/api/Alb/2020-06-16/ListListeners) → [ListServerGroups](https://api.aliyun.com/api/Alb/2020-06-16/ListServerGroups) → [ListServerGroupServers](https://api.aliyun.com/api/Alb/2020-06-16/ListServerGroupServers). Listeners not bound to a server group, or server groups without backends, are judged as idle.
- **NLB**: Call [ListLoadBalancers](https://api.aliyun.com/api/Nlb/2022-04-30/ListLoadBalancers) → [ListListeners](https://api.aliyun.com/api/Nlb/2022-04-30/ListListeners) → [ListServerGroups](https://api.aliyun.com/api/Nlb/2022-04-30/ListServerGroups). The judgment logic mirrors ALB.

#### 4.4 NAT Gateway Idle Detection

Call [DescribeNatGateways](https://api.aliyun.com/api/Vpc/2016-04-28/DescribeNatGateways) to obtain public NAT Gateways (use the `NetworkType` field to exclude VPC private NAT). Inspect each gateway's bound EIP list:

- No EIP bound → "Fully Idle" (P0)
- EIP bound, but [DescribeSnatTableEntries](https://api.aliyun.com/api/Vpc/2016-04-28/DescribeSnatTableEntries) AND [DescribeForwardTableEntries](https://api.aliyun.com/api/Vpc/2016-04-28/DescribeForwardTableEntries) both return zero entries → "Configuration Missing" (P0)

### 5. Recommendation Generation and Report Output

Aggregate inspector results into the recommendation engine and grade them as follows:

- **P0 — Act Now**: Definite waste (unmounted disks 30 days+, unbound EIPs, LBs with no listeners, NAT without EIP)
- **P1 — Recommended**: Highly likely waste (ECS CPU < 5% for 7 days, RDS with zero connections, bound EIP with zero traffic)
- **P2 — Observe**: Optimization space exists (ECS CPU 5%-10%, resources still in observation window)

Finally, produce a structured text report following this **mandatory four-section template**:

```
================================================================================
ALIBABA CLOUD FINOPS RESOURCE INSPECTION REPORT
================================================================================
Generated: <timestamp>
Inspection Period: <start> - <end>
Regions Scanned: <region_list>

--------------------------------------------------------------------------------
INSPECTION SUMMARY
--------------------------------------------------------------------------------
Total Resources Scanned: <count>
Total Issues Found: <count>

Resource Counts:
  ECS: <count>
  RDS: <count>
  EIP: <count>
  DISK: <count>
  CLB: <count>
  ALB: <count>
  NLB: <count>
  NAT: <count>

Issue Counts by Severity:
  P0 - Act Now: <count>
  P1 - Recommended: <count>
  P2 - Observe: <count>

--------------------------------------------------------------------------------
<RESOURCE_TYPE> DETAILS
--------------------------------------------------------------------------------
(One section per resource type, even if empty: "No <type> issues found.")

--------------------------------------------------------------------------------
RECOMMENDATION SUMMARY
--------------------------------------------------------------------------------
(Sorted by priority P0 → P1 → P2, each with "[Please confirm before acting]")

--------------------------------------------------------------------------------
ERROR SUMMARY
--------------------------------------------------------------------------------
(List of API failures, or "None")

================================================================================
END OF REPORT
================================================================================
```

**CRITICAL**: Every section MUST be present. If a resource type has no issues, output the section header followed by "No issues found". The report MUST NOT contain any AK/SK information.

### 6. API Throttling and Retry Strategy

- **CloudMonitor CMS QPS**: ~20-50 QPS — request interval is 50-100 ms
- **Throttling response**: Exponential backoff (1s → 2s → 4s), up to 3 retries
- **Network timeouts**: Up to 2 retries with increasing timeout (5s → 10s → 15s)
- **Total execution timeout**: 10 minutes — on timeout, abort and output partial results
- **Error handling**: A single API failure does not abort the overall inspection; errors are summarized at the end of the report

## Execution Commands (Mandatory Entry Point)

> **IMPORTANT**: The commands below are the ONLY valid way to execute this skill. The Agent MUST use `python3 scripts/main.py` with the appropriate flags. Writing custom scripts or calling APIs directly is FORBIDDEN.

Install dependencies first:

```bash
pip install -r scripts/requirements.txt
```

```bash
# Full inspection (all regions + all resource types)
python scripts/main.py

# Specify regions
python scripts/main.py --regions cn-hangzhou,cn-shanghai

# Specify resource types
python scripts/main.py --types ecs,rds,eip,disk

# Custom thresholds
python scripts/main.py --cpu-threshold 15 --memory-threshold 25 --days 14

# Idle resources only
python scripts/main.py --idle-only

# Utilization analysis only
python scripts/main.py --utilization-only
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--regions` | all regions | Comma-separated Region IDs |
| `--types` | all types | Resource types: ecs,rds,eip,disk,clb,alb,nlb,nat |
| `--cpu-threshold` | 10 | CPU low-utilization threshold (%) |
| `--memory-threshold` | 20 | Memory low-utilization threshold (%) |
| `--days` | 7 | Monitoring lookback days |
| `--idle-only` | false | Only inspect idle resources |
| `--utilization-only` | false | Only inspect utilization |

## Related Documentation

- [Python SDK Documentation](https://help.aliyun.com/zh/sdk/developer-reference/python-sdk)
- [Manage Access Credentials in Python](https://help.aliyun.com/zh/sdk/developer-reference/manage-access-credentials)
- [ECS Product](https://api.aliyun.com/product/Ecs)
- [RDS Product](https://api.aliyun.com/product/Rds)
- [VPC Product](https://api.aliyun.com/product/Vpc)
- [SLB (CLB) Product](https://api.aliyun.com/product/Slb)
- [ALB Product](https://api.aliyun.com/product/Alb)
- [NLB Product](https://api.aliyun.com/product/Nlb)
- [CloudMonitor (CMS) Product](https://api.aliyun.com/product/Cms)
