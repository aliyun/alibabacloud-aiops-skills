---
name: alibabacloud-network-mtr-diagnosis
description: >
  Public network MTR diagnosis tool. Supports both manual guidance and Cloud Assistant automation modes.
  Manual mode guides users to run MTR tools locally (macOS/Linux/Android/Windows) and analyze result screenshots.
  Automated mode remotely executes mtr/ping/curl diagnostics on ECS instances via Alibaba Cloud Cloud Assistant.
  Applicable to public network access failures, high latency, packet loss, SLB health check failures, NAT outbound packet loss, etc.
  Use this skill when users encounter network connectivity issues, need to troubleshoot public network link quality, or analyze MTR screenshots.
license: Apache-2.0
metadata:
  domain: aiops
  owner: network-team
  contact: network-team@alibaba-inc.com
---

# Public Network MTR Diagnosis

## Use Cases

| Scenario | Typical Issues |
|----------|---------------|
| **Public network access failure** | Connection refused, timeout, intermittent disconnection |
| **High or unstable latency** | Large jitter, latency spikes during specific time periods |
| **Packet loss** | Persistent packet loss, intermittent packet loss |
| **SLB/CLB health check failure** | Backend ECS health check fails, link troubleshooting needed |
| **Cross-region public network access** | Poor link quality between ECS instances across regions |
| **NAT Gateway outbound issues** | Packet loss / high latency when ECS behind NAT accesses external targets |
| **EIP bandwidth throttling** | Packet loss at fixed bandwidth threshold |

## Prerequisites

This Skill supports two modes:

**Manual mode**: No dependencies. Guides users to run MTR tools locally and provide result screenshots for analysis.

**Automated mode (Cloud Assistant)**:
- **Python 3.7+** (required) — scripts use standard library only, no third-party dependencies
- **aliyun CLI** (required): macOS `brew install aliyun-cli`; Linux download from [aliyuncli.alicdn.com](https://aliyuncli.alicdn.com)
- **Alibaba Cloud credentials**: Relies on aliyun CLI's default credential chain — environment variables (`ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET`), CLI profile (`~/.aliyun/config.json`), or ECS RAM Role
- **ECS Cloud Assistant agent**: The target ECS instance must have Cloud Assistant agent installed and running
- **Network access**: ISP identification relies on ipinfo.io API (free, no token required). Automatically falls back to backbone prefix matching when unreachable

### aliyun CLI Configuration

Before using the automated mode, ensure the aliyun CLI is properly configured:

#### Plugin Update

Run `aliyun plugin update` to ensure the ECS plugin is up-to-date. All CLI commands in this Skill use plugin mode (lowercase-hyphenated format, e.g., `run-command`, `describe-instances`).

> For permission details, see [ram-policies.md](references/ram-policies.md). run-command is an execution-level operation and requires user confirmation on each invocation.

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-mtr-diagnosis/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-mtr-diagnosis/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` command invocation.

> For RAM permissions details, see [references/ram-policies.md](references/ram-policies.md).

## Core Principles

> **Bidirectional MTR is mandatory**: Unidirectional testing is incomplete. Forward and reverse paths may differ (asymmetric routing). Always guide both client→server and server→client testing. **Exception**: When the target is an uncontrollable public address (e.g., public DNS such as 8.8.8.8 or 223.5.5.5, or any host you cannot log into), reverse MTR from the target back to the source may be impossible. In such cases, perform forward MTR from the source to the target. **You MUST explicitly tell the user**: "由于目标 [target] 是不可控公网地址，无法从目标侧发起反向 MTR，本次分析基于正向 MTR 结果；建议从其他 vantage point（如另一台不同运营商或地域的云服务器）补充反向测试以验证回程路径。" Record this limitation and the suggestion in the final report.
>
> **TCP MTR for supplementary verification**: When intermediate hops in ICMP MTR show high packet loss but the final destination is normal, or when ICMP is blocked by a firewall, use `mtr --tcp -P <port>` for TCP mode verification.
>
> **Cloud Assistant is mandatory for ECS operations**: When the user provides an ECS instance, ALL operations — including checking tool availability (`which mtr`), installing packages, running MTR, and collecting results — MUST be executed **remotely on the ECS** via Cloud Assistant scripts. **NEVER** run diagnostic commands (e.g. `which mtr`, `mtr --version`, `ping`, `mtr`) on the local machine or agent environment. The diagnosis targets the remote ECS's network, not the local environment.
>
> **User confirmation required before installing software**: You MUST NOT install any software (including `mtr`) on the ECS without first explicitly informing the user and receiving their approval. When `check-mtr` returns `installed: false`, you MUST STOP and ask the user for permission. **Never** auto-run `apt-get install`, `yum install`, or any installation command without user consent.

## Mode Selection (MUST determine first)

Before starting any diagnosis, you MUST determine which mode to use based on the user's situation:

| User's Situation | Mode | Action |
|-----------------|------|--------|
| User provides an ECS instance ID (e.g., `i-bp1xxx`) | **Automated Mode** | Use Cloud Assistant scripts to diagnose remotely on the ECS |
| User says "no ECS", "no cloud server", "local machine", "home computer", "Mac/Windows/Linux desktop" | **Manual Mode** | ⛔ STOP. Do NOT run any commands. Only provide text guidance for the user to run MTR on THEIR machine. |
| User has an ECS but Cloud Assistant is unavailable | **Manual Mode (fallback)** | Guide user to SSH into ECS and run MTR manually |

> **CRITICAL for Manual Mode**: When the user does NOT have an ECS, you MUST NOT:
> - Run `which mtr`, `mtr`, `ping`, or any diagnostic command on your own machine/agent environment
> - Install packages (`apt-get install`, `yum install`) on your own machine
> - Use aliyun CLI to call any cloud API
>
> **Even if the user says "帮我跑一下" (help me run it), "execute for me", or similar — you MUST NOT run commands locally.** The user's request to "run diagnostics" means guiding them to run it on THEIR machine, not yours. Your agent environment is a Linux cloud server whose network path is completely irrelevant to the user's home network. Running commands here would produce meaningless results for a completely different network.
>
> Instead, you MUST **guide the user** to perform these steps on their own machine. Start by providing the installation command for their OS (e.g., `brew install mtr` for macOS), then the MTR execution commands, and explain how to share results for your analysis. Your role is an **instructor**, not an executor.

## Diagnosis Workflow — Manual Mode

### Step 1: Determine Target Address and Test Direction

Ask the user:
- Target address: IP address (e.g., 8.8.8.8) or domain name (e.g., www.example.com)
- Test direction: From where to where (e.g., from local machine to ECS, from ECS to external)
- Protocol/port: If a specific port is needed (e.g., TCP/80, TCP/443)

### Step 2: Guide User to Use MTR Tool

Recommend the appropriate MTR tool based on the user's operating system:

#### Linux / ECS Server

```bash
# Installation
yum install -y mtr        # CentOS / RHEL / Alibaba Cloud Linux
apt-get install -y mtr     # Ubuntu / Debian

# ICMP MTR (standard mode)
mtr -r -c 100 -n <target_IP_or_domain>

# TCP MTR (specific port, use when ICMP is blocked)
mtr --tcp -P 80 -r -c 100 <target_IP>
mtr --tcp -P 443 -r -c 100 <target_IP>
```

#### macOS Users

**Option 1: Terminal mtr (Recommended)**

```bash
brew install mtr
sudo mtr -r -c 100 -n <target_IP_or_domain>
# TCP mode
sudo mtr --tcp -P 443 -r -c 100 <target_IP>
```

**Option 2: Best NetTools (App Store)**

1. Open the App Store, search for and download "Best NetTools"
2. Select the "Traceroute" or "MTR" function
3. Enter the target address and start the test
4. Wait 30-60 seconds to collect sufficient data, then take a screenshot of the results

#### Android Users

**Recommended tool: Network Multimeter (download from app store)**

1. Open the app store, search for and download "Network Multimeter"
2. Find the "MTR" or "Traceroute" function
3. Enter the target address and start the test
4. Wait 30-60 seconds, then take a screenshot of the results

#### Windows Users

**Recommended tool: WinMTR (free and open source)**

Download: https://github.com/White-Tiger/WinMTR/releases

1. Download and install WinMTR
2. Enter the target address in the Host field
3. Click "Start" to begin the test
4. Wait 30-60 seconds, then click "Export TEXT" to export or take a screenshot

### Step 3: Bidirectional MTR Testing

**You MUST explain the importance of bidirectional MTR testing to the user.** Cover these points:

1. **Why bidirectional testing matters**: Internet routing is often asymmetric — the forward path (client→server) and reverse path (server→client) may traverse completely different routers and ISPs. A problem on one path won't appear on the other. Without both directions, you cannot determine which direction has the issue.
2. **How asymmetric routing affects diagnosis**: For example, forward traffic may go through China Telecom backbone while reverse traffic goes through China Unicom. If only the Unicom return path has packet loss, a unidirectional forward test would miss the problem entirely.
3. **Guide the user to perform reverse testing**: Tell the user to run MTR from their own machine to the target (forward), and if possible, run MTR from the target back to their machine (reverse). If the target is a server they control, provide the reverse MTR command. If reverse testing is not possible (e.g., target is Google DNS 8.8.8.8 which won't initiate connections), explain this limitation and suggest testing from another vantage point.

Provide concrete commands for both directions:
```bash
# Forward: from your Mac to target
sudo mtr -r -c 100 -n 8.8.8.8

# Reverse: if you have a server at the target side, run from there back to your public IP
sudo mtr -r -c 100 -n <your_public_IP>
```

### Step 4: Analyze MTR Results

#### 1. Identify Key Metrics

Review the following data for each hop:
- **Hostname/IP**: Node address (can identify ISP)
- **Loss%**: Packet loss rate (>5% warrants attention, >20% severe)
- **Avg**: Average latency
- **Wrst**: Worst latency (large gap from Avg indicates jitter)

#### 2. Determine Problem Location

| Symptom | Possible Cause | Recommendation |
|---------|---------------|----------------|
| Loss% suddenly increases at a hop and persists thereafter | Link issue at or after that node | Identify the specific ISP or node |
| Latency suddenly jumps significantly (>50ms) | Route detour or node congestion | Check for international links or cross-ISP routing |
| High packet loss at the last hop | Target server issue | Contact the target side for investigation |
| Packet loss at an intermediate hop but recovers afterwards | ICMP rate limiting at that node, not real packet loss | Focus on the final destination packet loss rate |
| High packet loss across all hops | Local network issue | Check local network connection |
| High ICMP packet loss but normal TCP MTR | ICMP filtered by firewall | Use TCP MTR results as the reference |

#### 3. Output Diagnosis Conclusion

Based on the analysis, provide:
1. **Problem location**: Which specific hop has the issue
2. **Impact scope**: Localized or widespread
3. **Probable cause**: ISP link, international gateway, target server, etc.
4. **Direction determination**: Forward or reverse issue (requires bidirectional MTR comparison)
5. **Recommended actions**

## Diagnosis Workflow — Automated Mode (Cloud Assistant)

Remotely execute MTR diagnostics on ECS via Alibaba Cloud Cloud Assistant, no SSH login required.

> **CRITICAL — All operations target the remote ECS, NOT the local machine:**
> Every step in this workflow (environment check, tool detection, package installation, MTR execution, result analysis) must be performed on the **remote ECS instance** through Cloud Assistant. **Never** run `which mtr`, `mtr --version`, `ping`, `mtr`, or any diagnostic command locally — the local environment is irrelevant to the ECS network diagnosis.

> **CRITICAL — Never install software without user consent:**
> When `check-mtr` reports that mtr is not installed, you MUST STOP and explicitly ask the user: "mtr 工具尚未安装在 ECS 上，是否允许我安装？" **Do NOT proceed** with installation until the user explicitly agrees. Auto-installing without consent is strictly prohibited.

> **IMPORTANT**: All scripts in this Skill reside in the skill's `scripts/` directory. Before running any command, set the `SKILL_DIR` variable to the absolute path of this skill's root directory (provided in the task's Skill path), and use it as prefix for all script paths:
> ```bash
> SKILL_DIR="<absolute_skill_path>"   # e.g. the path given in the task's "Skill path" field
> ```
>
> **You MUST use these scripts** (`mtr_ecs.py`, `mtr_analyze.py`, `mtr_common.py`) for all Cloud Assistant operations. Do NOT call aliyun CLI directly for ECS operations — the scripts handle credential chains, retry logic, observability (`--user-agent`), and structured output automatically.

### Step 0: Environment Check and Input Parsing

```bash
PYTHON=$(bash "$SKILL_DIR/scripts/detect_python.sh") || exit 1
DIAG_DIR="/tmp/mtr_diag_$(date +%s)" && mkdir -p "$DIAG_DIR"
$PYTHON "$SKILL_DIR/scripts/mtr_common.py" check-env
$PYTHON "$SKILL_DIR/scripts/mtr_common.py" parse-input --input "<all_user_provided_info>" > "$DIAG_DIR/input.json"
```

Extracts instance ID, region, target IP/domain, protocol/port. Outputs environment readiness status.

### Step 1: Check Cloud Assistant Status

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_ecs.py" check-agent --instance-id <instance_ID> --region <region>
```

Confirms Cloud Assistant agent is installed and running. If not installed, prompts the user to install or falls back to manual mode.

### Step 1.5: Check Whether mtr Tool Is Installed

> **Do NOT run `which mtr` or `mtr --version` locally.** Use the script below to check mtr on the **remote ECS** via Cloud Assistant:

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_ecs.py" check-mtr --instance-id <instance_ID> --region <region>
```

Returns `installed: true/false` and the package manager type.

- If `installed: true`, proceed directly to Step 2
- If `installed: false`, **STOP immediately** and ask the user for permission before doing anything else:
  > "该 ECS 实例上未安装 mtr 工具，需要安装后才能执行诊断。是否允许我在 ECS 上安装 mtr？"
  
  **Do NOT run any install command until the user explicitly agrees.** After receiving explicit user approval:
  ```bash
  $PYTHON "$SKILL_DIR/scripts/mtr_ecs.py" install-mtr --instance-id <instance_ID> --region <region>
  ```
  If the user declines, fall back to manual mode (guide user to SSH in and install manually)

> **⛔ COMPLIANCE — HARD STOP**: Installing software on ECS without user consent is strictly prohibited. When mtr is not installed, you MUST ask the user and WAIT for their response before proceeding. This is a non-negotiable compliance requirement.

### Step 2: Forward MTR (ECS → Target)

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_ecs.py" run-mtr --instance-id <instance_ID> --region <region> --target <target_IP> --count 100 > "$DIAG_DIR/forward_mtr.json"
```

To test a specific port, add `--tcp-port <port>`, which will execute both ICMP MTR and TCP MTR simultaneously.

### Step 3: Reverse MTR (ECS → Client)

When the target is a server you control, determine the client's public IP (`<client_IP>`) and run reverse MTR from the ECS back to the client:

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_ecs.py" run-mtr --instance-id <instance_ID> --region <region> --target <client_IP> --count 100 > "$DIAG_DIR/reverse_mtr.json"
```

If `<client_IP>` cannot be determined (e.g., the user's local public IP is unknown or NATed), or if the target is an uncontrollable public address (e.g., Google DNS 8.8.8.8, Alibaba Cloud DNS 223.5.5.5), **skip reverse MTR** and proceed to analyze the forward MTR data only. **You MUST do both of the following**:
1. **Explain to the user**: "由于目标 [target] 是不可控公网地址，无法从目标侧发起反向 MTR，本次分析基于正向 MTR 结果。"
2. **Suggest an alternative**: "建议从其他 vantage point（如另一台不同运营商或地域的云服务器）补充反向测试，以验证回程路径是否存在丢包或高延迟。"
Record both the limitation and the suggestion in the final report.

### Step 4: Analyze MTR Results

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_analyze.py" analyze --forward "$DIAG_DIR/forward_mtr.json" --reverse "$DIAG_DIR/reverse_mtr.json"
```

### Step 5: Generate Diagnosis Report

```bash
$PYTHON "$SKILL_DIR/scripts/mtr_analyze.py" report --dir "$DIAG_DIR"
```

Outputs: conclusion, severity, forward/reverse analysis, ICMP/TCP comparison, ISP path, recommended actions.

## Analysis Examples

### Example 1: Normal Link

```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    192.168.1.1             0.0%   100   1.2   1.5   0.8   3.2
2    10.10.10.1              0.0%   100   5.3   5.8   4.9   8.1
3    202.96.128.86           0.0%   100   8.2   9.1   7.5   15.2
4    202.97.1.1              0.0%   100   12.5  13.2  11.8  18.5
5    8.8.8.8                 0.0%   100   15.3  16.1  14.2  22.1
```

**Conclusion**: Link is normal — no packet loss, latency increases reasonably per hop. Traverses China Telecom backbone (202.96/202.97).

### Example 2: Persistent Packet Loss at Intermediate Node

```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    192.168.1.1             0.0%   100   1.2   1.5   0.8   3.2
2    10.10.10.1              0.0%   100   5.3   5.8   4.9   8.1
3    202.96.128.86           30.0%  100   8.2   9.1   7.5   15.2
4    202.97.1.1              30.0%  100   200.5 210.2 195.3 350.1
5    8.8.8.8                 30.0%  100   205.3 215.8 200.1 380.5
```

**Conclusion**: Persistent 30% packet loss starting from hop 3 (202.96.128.86, China Telecom backbone) with significantly increased latency. This is a backbone network issue.

### Example 3: ICMP Rate Limiting (False Packet Loss)

```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    192.168.1.1             0.0%   100   1.2   1.5   0.8   3.2
2    10.10.10.1              50.0%  100   5.3   5.8   4.9   8.1
3    202.96.128.86           0.0%   100   8.2   9.1   7.5   15.2
4    8.8.8.8                 0.0%   100   15.3  16.1  14.2  22.1
```

**Conclusion**: Hop 2 shows 50% packet loss but all subsequent hops fully recover. This is ICMP rate limiting (the node deprioritizes ICMP probe packets), not real packet loss.

### Example 4: ICMP Blocked, TCP MTR Normal

**ICMP MTR:**
```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    172.16.0.1              0.0%   100   0.3   0.4   0.2   1.2
2    10.54.0.1               0.0%   100   1.2   1.5   0.8   3.1
3    ???                     100.0  100   0.0   0.0   0.0   0.0
4    47.95.x.x               100.0  100   0.0   0.0   0.0   0.0
```

**TCP MTR (port 443):**
```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    172.16.0.1              0.0%   100   0.3   0.4   0.2   1.2
2    10.54.0.1               0.0%   100   1.2   1.5   0.8   3.1
3    ???                     100.0  100   0.0   0.0   0.0   0.0
4    47.95.x.x               0.0%   100   5.3   5.8   4.9   8.1
```

**Conclusion**: ICMP is blocked by the target security group (100% loss at final hop), but TCP port 443 is reachable with normal latency. TCP MTR should be used as the reference — the service link is normal.

### Example 5: Asymmetric Routing

**Forward (Client → ECS):**
```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    192.168.1.1             0.0%   100   1.2   1.5   0.8   3.2
2    202.96.128.86           0.0%   100   5.3   5.8   4.9   8.1
3    202.97.33.1             0.0%   100   28.5  29.1  27.2  35.1
4    47.95.x.x               0.0%   100   30.2  31.5  29.8  38.2
```

**Reverse (ECS → Client):**
```
Hop  Hostname                Loss%  Sent  Last  Avg   Best  Wrst
1    172.16.0.1              0.0%   100   0.3   0.4   0.2   1.2
2    219.158.5.1             15.0%  100   8.5   9.2   7.8   25.3
3    219.158.33.1            15.0%  100   35.2  38.5  32.1  85.6
4    192.168.1.100           15.0%  100   40.1  42.3  38.5  90.2
```

**Conclusion**: Asymmetric routing detected. Forward path goes through China Telecom (202.97) with no packet loss; reverse path goes through China Unicom (219.158) with 15% persistent packet loss starting from hop 2. The issue is on the reverse (return) China Unicom link.

## Advanced Analysis

### Identifying ISP Nodes

Common ISP identifiers:
- **China Telecom**: 202.96.x.x, 202.97.x.x (backbone / international gateway)
- **China Unicom**: 219.158.x.x (backbone / international gateway), 221.4.x.x, 125.33.x.x
- **China Mobile**: 221.183.x.x, 223.120.x.x, 111.13.x.x

> Note: `219.158.x.x` belongs to **China Unicom** backbone, not China Telecom.

### Identifying Route Detours

A latency jump exceeding 50ms at a certain hop may indicate:
- Route detour (normal route disrupted, using backup path)
- International link (transoceanic hop)
- Node congestion

### Multi-Period Comparison

It is recommended to test during different time periods (peak / off-peak):
- Issues only during peak hours: Link congestion
- Issues throughout the day: Link quality or equipment failure

## Alibaba Cloud Scenario-Specific Guides

### SLB/CLB Health Check Failure

Troubleshooting steps:
1. Run MTR to the SLB VIP to check whether the link is normal
2. Run TCP MTR to the backend ECS health check port (`mtr --tcp -P <port> <backend_IP>`)
3. If ICMP is normal but TCP shows packet loss, check whether the security group / firewall allows the health check port
4. Use automated mode to execute reverse MTR on the backend ECS to troubleshoot the return path

### Cross-Region Public Network Access

Troubleshooting steps:
1. Run MTR from the source region ECS to the target region ECS's EIP
2. Run MTR from the target region ECS to the source region ECS's EIP
3. Compare bidirectional MTR results to identify abnormal cross-region / cross-ISP nodes
4. Check whether traffic passes through international gateways (e.g., 202.97.x.x China Telecom international gateway)

### NAT Gateway Outbound Packet Loss

Troubleshooting steps:
1. Run MTR from the ECS behind NAT to the external target
2. Check whether the first hop is the NAT Gateway and whether packet loss starts from the NAT Gateway
3. If the NAT Gateway hop is normal but subsequent hops show packet loss, it is an ISP link issue
4. If packet loss starts at the NAT Gateway hop, check the NAT Gateway bandwidth and connection count

### EIP Bandwidth Throttling Detection

Characteristic patterns:
- Normal MTR latency but packet loss rate at a fixed ratio (e.g., consistently ~X%)
- `Wrst` latency much higher than `Avg`, with periodic spikes
- Occurs when bandwidth reaches the EIP throttling threshold

Troubleshooting steps:
1. Compare the EIP bandwidth specification with actual traffic
2. Test during low-traffic periods to confirm packet loss disappears
3. Upgrade EIP bandwidth or optimize traffic

## Fallback Strategy

| Unavailable Resource | Fallback |
|---------------------|----------|
| `aliyun` CLI not installed | Manual mode only |
| Alibaba Cloud credentials missing | Manual mode only |
| Cloud Assistant agent not installed | Prompt installation, fall back to manual mode (guide user to SSH in) |
| mtr not installed on ECS | Explicitly inform user and install after consent; fall back to manual mode if user declines |
| Insufficient ECS permissions | Prompt to check RAM permissions, fall back to manual mode |
| Python < 3.7 | Prompt to upgrade Python |

## References

- MTR metrics detailed description: [references/reference.md](references/reference.md)
- RAM permission configuration: [references/ram-policies.md](references/ram-policies.md)
