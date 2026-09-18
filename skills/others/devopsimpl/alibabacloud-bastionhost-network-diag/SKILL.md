---
name: alibabacloud-bastionhost-network-diag
description: >
  Diagnose client timeouts or anomalies when accessing Alibaba Cloud Bastion Host — quickly root-cause public network connectivity, Bastion Host configuration,
  Cloud Firewall blocking, and other causes. Use when users report: connection timeout to Bastion Host, abnormal Bastion Host access,
  SSH/RDP cannot connect to Bastion Host, Bastion Host web page inaccessible, Bastion Host public network access failure, Bastion Host whitelist issues,
  Bastion Host blocked by Cloud Firewall, even if the user does not explicitly mention "Bastion Host" or "bastionhost".
  Applicable to Basic Edition, Enterprise Dual-Engine Edition, and National Cryptography Edition Bastion Host V3.2.
compatibility: >
  Requires Alibaba Cloud CLI (aliyun-cli) and read-only permissions on yundun-bastionhost and cloudfw products.
metadata:
  domain: aiops
  owner: bastionhost-team
  contact: bastionhost-team@alibaba-inc.com
allowed-tools: Bash Read
---

# Bastion Host Client Access Anomaly Diagnosis

Diagnose the root causes of client connection timeouts or anomalies to Bastion Host, covering public network connectivity, instance configuration, Cloud Firewall blocking, and other key dimensions.

## Strict Constraints

- **Only perform read-only queries; strictly prohibit any write, modify, or delete operations**
- All Alibaba Cloud API calls must use `aliyun-cli` commands
- After the user explicitly authorizes automatic execution, the Agent may automatically execute the read-only `aliyun-cli` query commands listed in this Skill
- Before executing each command, display the command to be executed and explain its purpose
- If `aliyun-cli` is unavailable, credentials are not configured, or permissions are insufficient, stop automatic execution and inform the user of manual troubleshooting steps
- In uncertain situations, prioritize asking the user for additional information; do not perform write operations on your own
- **Never expose or persist credentials**: do not copy, back up, move, print, `cat`, or read the aliyun CLI config/credential file (`~/.aliyun/config.json`) or any file containing an AccessKey, AccessKeySecret, or STS token, and never write credentials to any file. Credentials are pre-configured by the runtime environment; do not modify or back them up.
- **Run every `aliyun-cli` command as a SINGLE LINE** without backslash (`\`) line continuations, so that the command and all of its parameters appear on one physical line.

## Output Language Requirements

- **All final user-facing responses must match the language of the user's query.** Do not switch languages between the query and the final response.
- The final response must explicitly include standard Alibaba Cloud diagnostic terminology for each scenario (see below).
- Do not rely only on attached files or output artifacts; the chat response itself must contain the required diagnostic terms.
- **Every diagnosis report must begin with an explicit instance identity line stating the Instance ID and Region** (use the user's language, e.g. Chinese "实例 ID" and "地域"). This still holds when the diagnosis continues after the user supplies a corrected region or instance ID, so the identified instance and its region are always present in the final response.
- **The scenario-required diagnostic terminology (see table below) must appear in the chat text of EVERY final response, not only inside the report file.** This still holds for any follow-up final response produced after the user supplies additional information (such as a client public IP, a port, or a request to re-check a specific source IP): the follow-up response must restate the applicable scenario terminology instead of only answering the narrow follow-up. In particular, when the instance is located in mainland China and the client is overseas, the cross-border reminder (at least one of "cross-border" / "VPN" / "Global Accelerator" / "GA") must be repeated in that follow-up final response as well.

### Required Diagnostic Terminology by Scenario

| Scenario | Required diagnostic terminology (must appear in the final response) |
|----------|---------------------------------------------------------------------|
| Cloud Firewall blocked / intercepted | At least 2 terms meaning "intercept/block", "Cloud Firewall", or the API field names `TrafficLog` / `RuleResult` |
| Cloud Firewall no block / not intercepted | At least 1 term meaning "no interception", "not blocked", "no block record found", or the API field name `DataList` |
| Private domain name | At least 2 terms meaning "private network", "internal network", "troubleshooting guidance", "automatic diagnosis not supported", "security group", or `ping` |
| No instance found in region | At least 2 terms meaning "instance ID", "region", "supplement", or "provide" |
| Cross-border access (instance located in mainland China while the client is overseas) | At least 1 term meaning "cross-border", "VPN", "Global Accelerator", or "GA" |

Use the standard Alibaba Cloud diagnostic terminology that a user would expect in a diagnostic report.

## User-Agent Compliance

Before the first Alibaba Cloud API call:

1. Read `references/manifest.json` and extract the `version` field.
   - If the file does not exist or `version` is missing, stop and inform the user that the Skill manifest is missing and automatic execution cannot proceed.
2. Generate a unique session ID once and export it as an environment variable so that all subsequent scripts share the same session ID:
   ```bash
   export SESSION_ID=$(openssl rand -hex 16)
   ```
3. Construct the `--user-agent` value exactly as:
   ```
   AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}
   ```
4. Append `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"` to every `aliyun-cli` command.

## Pre-Diagnosis Information Collection

Collect the required information in the following order. Ask the user for anything that is missing:

### 0. Access Address Type Gate (MUST RUN BEFORE ANY aliyun-cli COMMAND)

**Before calling ANY cloud API, first inspect the Bastion Host access address the user has ALREADY provided:**

- If the user has provided an access address AND it is a **private domain name** (does NOT contain the `-public` keyword, e.g. `xxxxxxxx.bastionhost.aliyuncs.com`) → **do NOT call ANY `aliyun-cli` command** (no `describe-instances`, no `describe-instance-attribute`, no `cloudfw` API). Jump directly to [Private Domain Name Scenario Handling](#private-domain-name-scenario-handling). This holds **EVEN IF the user also provides an instance ID** — never query a private-domain instance.
- If the access address is a **public domain name** (contains `-public`), OR the user has **not provided any access address yet** (region-only or instance-only query) → continue to Section 1.

### 1. Obtain the Bastion Host Instance ID (MANDATORY FIRST STEP - PUBLIC-DOMAIN / ADDRESS-UNKNOWN PATH ONLY)

**This mandatory first step applies ONLY after the Section 0 gate confirms the access address is NOT a private domain name.**

**This `describe-instances` call is ALWAYS the first data-plane command of the public-domain diagnosis, EVEN IF the user already provides the instance ID.** It verifies that the instance exists in the region and returns the authoritative `InternetEndpoint`, `IntranetEndpoint`, and `RegionId`. Do NOT call `describe-instance-attribute` or any `cloudfw` API before `describe-instances`.

**If the user has provided a region, query Bastion Host instances in that region; otherwise, query the `cn-hangzhou` region by default.**

After the user authorizes automatic execution, call directly as a single line (replace `<region>` with the user-provided region or `cn-hangzhou`):

```bash
aliyun yundun-bastionhost describe-instances --biz-region-id <region> --region <region> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Judgment**:
- If `Instances` is non-empty, extract `InstanceId` (e.g., `bastionhost-cn-xxxxxx03`) and proceed to the next step
- If `Instances` is an empty array, it means no Bastion Host was found in the queried region. **The response must explicitly ask the user to provide or supplement the instance ID and region.** Do not proceed with diagnosis until the user supplies a valid instance ID or region.

At the same time, extract the following fields from the response for later use:
- `InternetEndpoint`: Public domain name (e.g., `xxxxxxxx-public.bastionhost.aliyuncs.com`)
- `IntranetEndpoint`: Private domain name (e.g., `xxxxxxxx.bastionhost.aliyuncs.com`)
- `RegionId`: Region where the Bastion Host is located

### 2. Confirm the Access Address Type

Ask the user for the Bastion Host access address and port currently in use:

- **Public domain name** feature: The domain name contains the `-public` keyword (e.g., `xxx-public.bastionhost.aliyuncs.com`)
- **Private domain name** feature: The domain name does not contain `-public`
- Also collect the port actually used by the user (e.g., the `-p` parameter in the SSH command, RDP port, HTTPS port) for subsequent custom port checks

## Scenario Branch Judgment

Determine the scenario based on the collected access address:

| Access Address Type | Handling |
|---------------------|----------|
| Public domain name (contains `-public`) | Continue to [Public Domain Name Diagnosis Process](#public-domain-name-diagnosis-process) |
| Private domain name (does not contain `-public`) | Jump to [Private Domain Name Scenario Handling](#private-domain-name-scenario-handling) |

## Public Domain Name Diagnosis Process

### Step 1: Query Bastion Host Instance Attributes

Query the detailed Bastion Host configuration based on the instance ID. After the user authorizes automatic execution, call directly:

```bash
aliyun yundun-bastionhost describe-instance-attribute --instance-id <instance-id> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

Retain the full response content for subsequent analysis.

**Item-by-item checks**:

#### 1.1 Public Network Switch Check

Check the public network access switch status from the response:
- Public network switch **closed** → Inform the user that the public network access switch needs to be enabled; otherwise, public network connection is impossible
- Public network switch **open** → Continue to the next step

#### 1.2 Whitelist Check

Check whether an access whitelist is configured:
- **Whitelist not enabled** → This item passes
- **Whitelist enabled** → Display the current whitelist configuration and prompt the user to verify whether the client IP is within the whitelist range
  - If the user confirms the IP is not in the whitelist → Inform the user that the client IP needs to be added to the whitelist

#### 1.3 Custom Port Check

The standard ports for Bastion Host are: SSH `60022`, RDP `63389`, HTTPS `443`.

- **You must prioritize comparing the port actually used by the user with the port configured for the instance**:
  - Identify the port actually used by the user from the access command or address entered (e.g., the `-p` parameter in the SSH command)
  - Compare the `CustomPort` for the corresponding protocol in the response with the port actually used by the user
    - **Inconsistent** → Determined as failed. Inform the user that the ports do not match; they should access using the port configured for the instance, or modify the port in the console
    - **Consistent** → This item passes
- Next, check whether `CustomPort` is not equal to `StandardPort`:
  - If a custom port is configured, prompt the user that the current instance uses a custom port rather than the standard port

### Step 2: Cloud Firewall Diagnosis

#### 2.1 Collect the Client Public IP

After entering the Cloud Firewall diagnosis process, collect the client's public IP from the user:
- Prompt the user to enter "IP" in the browser search box to query their public IP

#### 2.2 Check the Protection Status of the Bastion Host Ingress IP

Check whether the Bastion Host public ingress IP is added to Cloud Firewall protection. After the user authorizes automatic execution, call directly:

```bash
aliyun cloudfw describe-asset-list --current-page 1 --page-size 10 --search-item <instance-id> --resource-type BastionHostIngressIP --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Note**: `--resource-type` is fixed to `BastionHostIngressIP`.

**Judgment**:

| Response Scenario | Meaning | Handling |
|-------------------|---------|----------|
| `Assets` is an empty array `[]` | Cloud Firewall not activated | Skip the Cloud Firewall investigation and continue to output the diagnosis result |
| `ProtectStatus` = `closed` | Cloud Firewall activated but Bastion Host ingress IP not added to protection | Inform the user that it is currently not protected by Cloud Firewall and skip subsequent Cloud Firewall diagnosis |
| `ProtectStatus` = `open` | Cloud Firewall activated and Bastion Host ingress IP added to protection | Continue to execute the Cloud Firewall traffic log query |

Extract the Bastion Host public ingress IP from the `InternetAddress` field in the response and retain it for the next step.

### Step 3: Cloud Firewall Traffic Log Query

#### 3.1 Query Cloud Firewall Drop Records

**Only execute when the Bastion Host ingress IP has Cloud Firewall protection enabled.**

Query whether there are Cloud Firewall drop records. After the user authorizes automatic execution, call directly:

```bash
aliyun cloudfw describe-traffic-log --start-time <start-timestamp> --end-time <end-timestamp> --source-code yundun --direction in --rule-result 2 --src-ip <client-ip> --dst-ip <bastionhost-public-ip> --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-bastionhost-network-diag/${SESSION_ID} skill-version/${VERSION}"
```

**Parameter Description**:
- `--source-code`: Fixed to `yundun`
- `--direction`: Fixed to `in` (inbound)
- `--rule-result`: Fixed to `2` (indicates Cloud Firewall drop)
- `--src-ip`: Client public IP
- `--dst-ip`: Bastion Host public ingress IP extracted in Step 2

**Important**: Run this as a SINGLE-LINE command exactly as shown above. Do NOT split it across multiple lines with backslash (`\`) continuations, and do NOT omit any of the three fixed parameters `--source-code yundun`, `--direction in`, and `--rule-result 2`. Every parameter must appear on the same physical line as `aliyun cloudfw describe-traffic-log`.

**Time Range Handling** (`start-time` / `end-time` are Unix timestamps in seconds):

- User provided a specific anomaly time → `start-time` is 1 hour before the anomaly time; `end-time` is 1 hour after the anomaly time
- User mentioned "just now" → `start-time` is current time minus 1 hour; `end-time` is current time plus 1 hour
- User mentioned "today" → `start-time` is the timestamp of 00:00 today; `end-time` is the current time
- User did not provide a time → Default `start-time` is 00:00 today; `end-time` is the current time
- **Only data within the last 7 days can be queried**. If the time range exceeds this, `ErrorTimeError` will be returned. Inform the user accordingly

**Judgment**:

| Response Scenario | Meaning |
|-------------------|---------|
| Returns `ErrorTimeError` | Query time exceeds the 7-day range; narrow the time range and query again |
| `DataList` is an empty array | No Cloud Firewall drops or blocks in the current query time range; Cloud Firewall did not block |
| `DataList` is non-empty | Cloud Firewall drop records exist. Analyze `RuleName`, `DstPort`, `Proto`, and other fields item by item to locate the blocking reason |

**When interception records are found**:
- Extract the `RuleName` (rule name) and `DstPort` (destination port) of the interception rule
- Inform the user which Cloud Firewall rule intercepted the traffic and recommend checking and adjusting the corresponding rule

### Step 4: Cross-Border Access Reminder

Extract `RegionId` from the instance attributes and determine whether cross-border access is possible:
- If the Bastion Host is located in a Chinese mainland region (e.g., `cn-hangzhou`, `cn-shanghai`, etc.), prompt the user: If the current operation is cross-border O&M, there may be cross-border network instability; it is recommended to access via VPN or Global Accelerator (GA)

## Private Domain Name Scenario Handling

Automatic diagnosis for private domain name scenarios is currently not supported. **After identifying a private domain name, do NOT execute any `aliyun-cli` commands (including `yundun-bastionhost describe-instances`, `describe-instance-attribute`, and all `cloudfw` APIs).** Even if the user provides an instance ID, do not query it. Provide guidance separately according to the access protocol:

**HTTPS Access Anomaly**:
Inform the user that private domain HTTPS access is not supported for automatic diagnosis. Refer the user to the official document [Enable O&M over a Private Network](https://help.aliyun.com/zh/bh/bastionhost/user-guide/enable-o-m-over-a-private-network) for configuration and troubleshooting, and provide the document link.

**SSH / RDP Access Anomaly**:
1. Inform the user that private domain SSH/RDP access is not supported for automatic diagnosis. Prompt the user to check network connectivity by running `ping <Bastion Host private domain name>`
2. Provide guidance based on the network topology:
   - **Same VPC access** → Check whether the security group allows traffic on Bastion Host ports (SSH 60022, RDP 63389)
   - **Cross-VPC access** → The network needs to be connected via VPC peering or CEN (Cloud Enterprise Network)
   - **On-premises IDC access** → The network needs to be connected via VBR (Express Connect)

The final chat response must contain the required diagnostic terminology listed in [Output Language Requirements](#output-language-requirements): at least 2 terms meaning "private network", "internal network", "troubleshooting guidance", "automatic diagnosis not supported", "security group", or `ping`. Do not put these terms only in an attached report file; include them directly in the reply to the user.

## Diagnostic Result Output

After completing all investigation steps, output a structured diagnostic report:

```
**Diagnosis Result**
**Instance ID: <instance-id> | Region: <region-id> | Client IP: <client-ip> (display only when client IP has been collected) | Diagnosis Time: <current-datetime>**

| **Diagnosis Item** | **Diagnosis Result** | **Details** |
|--------------------|----------------------|-------------|
| Public network switch check | Pass / Fail | Public network switch is enabled / not enabled |
| Console whitelist check | Pass / Fail | Whitelist not enabled / client IP not in whitelist |
| Custom port check | Pass / Fail | User's actual port is consistent / inconsistent with the instance-configured port; the instance-configured port is XXXXX; please use the correct port to access |
| Cloud Firewall check | Pass / Fail / Not configured | Cloud Firewall did not block / Cloud Firewall blocked by rule XXX / Cloud Firewall not activated |
| Bastion Host region check | Pass | The current Bastion Host region is XX; if operating cross-border, VPN/GA acceleration is recommended |
```

**Root Cause Summary**: Below the table, summarize the diagnosis conclusion and recommended actions in one paragraph in the same language as the user's query. The summary must follow the terminology requirements in [Output Language Requirements](#output-language-requirements):
- When Cloud Firewall interception is found, the summary must clearly state that Cloud Firewall intercepted or blocked the traffic and include the rule name.
- When no interception is found, the summary must clearly state that Cloud Firewall did not block the traffic.
- When the queried region has no instances, the response must ask the user to supplement or provide the instance ID and region.

## Reference Documents

- Detailed Bastion Host API examples and response formats → Read `references/api-examples.md`
- RAM permission list → Read `references/ram-policies.md`
