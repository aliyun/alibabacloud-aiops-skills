---
name: alibabacloud-network-reachability-analysis
description: >
  Perform Alibaba Cloud NIS (Network Intelligence Service) network path reachability analysis
  with forward/reverse path diagnosis, topology visualization, and resource monitoring.
  Use when analyzing network connectivity, diagnosing unreachable paths, checking security groups
  or route tables, or visualizing network topology between cloud resources.
  Triggers: "reachability analysis", "network path analysis", "NIS analysis", "connectivity diagnosis",
  "path reachable", "network troubleshooting",
  "可达性分析", "网络路径分析", "NIS分析", "连通性诊断", "路径可达", "网络排障".
---

# NIS Network Reachability Analysis / NIS 网络可达性分析

> **Language / 语言**: Respond in the same language the user uses.
> If the user speaks Chinese, use the Chinese (zh-CN) prompts below.
> If the user speaks English, use the English (en) prompts below.

Guides an agent through interactive network reachability analysis using Alibaba Cloud NIS.
Covers forward/reverse path analysis, topology visualization (Mermaid), and monitoring diagnostics
for resources along the path.

**Architecture**: `NIS (CreateAndAnalyzeNetworkPath + GetNetworkReachableAnalysis) + CloudMonitor (DescribeMetricData)`

> ⚠️ **CRITICAL / 关键**: **READ-ONLY OPERATIONS ONLY**
> 
> This skill performs **read-only** network diagnostics. **DO NOT** create, modify, or delete any cloud resources.
> 
> 本技能仅执行**只读**网络诊断操作。**严禁**创建、修改或删除任何云资源。
> 
> Allowed: `CreateAndAnalyzeNetworkPath`, `GetNetworkReachableAnalysis`, `DescribeMetricData`, `Describe*` APIs
> 
> 允许：分析任务创建与查询、监控数据查询、Describe* 类查询 API
> 
> Forbidden: `Create*` (except `CreateAndAnalyzeNetworkPath`), `Modify*`, `Delete*`, `Start*`, `Stop*`, `Run*` APIs
> 
> 禁止：创建类 API（除 `CreateAndAnalyzeNetworkPath` 外）、修改、删除、启停、执行类 API

## Installation

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version
aliyun configure set --auto-plugin-install true
```

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
> aliyun configure list --user-agent AlibabaCloud-Agent-Skills
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile


## RAM Permissions

See [references/ram-policies.md](references/ram-policies.md) for the full RAM policy.

Required actions: `nis:CreateAndAnalyzeNetworkPath`, `nis:GetNetworkReachableAnalysis`, `cms:DescribeMetricData`.

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance IDs, IP addresses,
> protocol, ports, resource types, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

Collect the following parameters interactively:

| Parameter | Required | Description (EN) | 说明 (ZH) | Default |
|-----------|----------|-------------------|-----------|---------|
| RegionId | Yes | Region of the analysis task | 分析任务所在地域 | — |
| SourceType | Yes | `ecs`, `vsw`, `internetIp`, `vpn`, `vbr` | 源端类型 | — |
| SourceId | Yes | Source resource ID (or public IP if `internetIp`) | 源资源 ID（公网 IP 类型直接填 IP） | — |
| SourceIpAddress | Conditional | On-Premise IP, **required** for `vpn`/`vbr` | 云下私网 IP，`vpn`/`vbr` 时**必填** | — |
| TargetType | Yes | `ecs`, `vsw`, `internetIp`, `vpn`, `vbr`, `clb` | 目的端类型 | — |
| TargetId | Yes | Target resource ID (or public IP if `internetIp`) | 目的资源 ID（公网 IP 类型直接填 IP） | — |
| TargetIpAddress | Conditional | On-Premise IP, **required** for `vpn`/`vbr` | 云下私网 IP，`vpn`/`vbr` 时**必填** | — |
| Protocol | Yes | `tcp`, `udp`, or `icmp` | 协议类型 | — |
| TargetPort | Conditional | Required for `tcp`/`udp` | `tcp`/`udp` 时必填 | — |
| SourcePort | Optional | Source port | 源端口 | — |

### Interactive Collection Logic / 交互收集逻辑

Use the prompts matching the user's language:

**Step 1 — Ask resource types / 询问资源类型**

| EN | ZH |
|----|-----|
| "What is the **source resource type**? (ecs / vsw / internetIp / vpn / vbr)" | "请问**源端资源类型**是什么？（ecs / vsw / internetIp / vpn / vbr）" |
| "What is the **target resource type**? (ecs / vsw / internetIp / vpn / vbr / clb)" | "请问**目的端资源类型**是什么？（ecs / vsw / internetIp / vpn / vbr / clb）" |

**Step 2 — Type-specific prompts / 按类型提示**

| Condition | EN Prompt | ZH Prompt |
|-----------|-----------|-----------|
| `internetIp` | "For public IP analysis, please provide the **public IP address** directly as the ID." | "分析公网路径时，请直接提供**公网 IP 地址**作为 ID 传入。" |
| `vpn` / `vbr` | "For hybrid cloud analysis, besides the resource ID, please also provide the **On-Premise IP** (private IP on your side)." | "连接云下环境时，除了资源 ID，请务必提供您的**云下私网 IP (On-Premise IP)** 以确保分析准确。" |

**Step 3 — Protocol & ports / 协议和端口**

| EN | ZH |
|----|-----|
| "What protocol? (tcp / udp / icmp) And what is the target port?" | "请问使用什么协议？（tcp / udp / icmp）目的端口是多少？" |

## Core Workflow

### Step 1: Forward Path Analysis / 正向路径分析

```bash
aliyun nis create-and-analyze-network-path \
  --source-id <SourceId> \
  --source-type <SourceType> \
  --target-id <TargetId> \
  --target-type <TargetType> \
  --protocol <Protocol> \
  --target-port <TargetPort> \
  --source-ip-address <SourceIpAddress> \
  --target-ip-address <TargetIpAddress> \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

> Omit `--source-ip-address` / `--target-ip-address` if SourceType/TargetType is not `vpn` or `vbr`.
> Omit `--target-port` if Protocol is `icmp`.

Record the returned `NetworkReachableAnalysisId`.

> ⚠️ **MANDATORY / 强制**: **ALWAYS perform reverse path analysis after forward analysis completes.**
> 
> **MUST** execute Step 3 (Reverse Path Analysis) immediately after Step 2 finishes. Do NOT skip or omit reverse path check.
> 
> **必须**在正向分析完成后立即执行 Step 3（反向路径分析）。严禁跳过或省略反向路径检查。

### Step 2: Poll for Forward Result / 轮询正向结果

```bash
aliyun nis get-network-reachable-analysis \
  --network-reachable-analysis-id <ForwardAnalysisId> \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

Repeat until `NetworkReachableAnalysisStatus` is `finish`. Extract `Reachable`, `NetworkReachableAnalysisResult`.

### Step 3: Reverse Path Analysis / 反向路径分析

Swap source and target / 交换源和目的:
- Forward `SourceId/Type` → Reverse `TargetId/Type`
- Forward `TargetId/Type` → Reverse `SourceId/Type`
- Forward `SourceIpAddress` → Reverse `TargetIpAddress`
- Forward `TargetIpAddress` → Reverse `SourceIpAddress`

**Port handling / 端口处理**:
- Reverse `--source-port` = Forward `TargetPort` (server listening port / 服务端监听端口)
- Reverse `--target-port` = Random ephemeral port in range **49152 ~ 65535** (client ephemeral port / 客户端随机端口)

> Since the client initiates the connection with a dynamically assigned ephemeral port, the reverse path (server → client) should use a random port in the ephemeral range (49152-65535) as the target port to simulate real return traffic.
>
> 由于客户端发起连接时使用动态分配的临时端口，反向路径（服务端→客户端）的目的端口应使用临时端口范围（49152-65535）内的随机值来模拟真实回程流量。

```bash
aliyun nis create-and-analyze-network-path \
  --source-id <OriginalTargetId> \
  --source-type <OriginalTargetType> \
  --target-id <OriginalSourceId> \
  --target-type <OriginalSourceType> \
  --protocol <Protocol> \
  --source-port <OriginalTargetPort> \
  --target-port <RandomPort_49152_to_65535> \
  --source-ip-address <OriginalTargetIpAddress> \
  --target-ip-address <OriginalSourceIpAddress> \
  --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills
```

> Omit `--source-ip-address` / `--target-ip-address` if SourceType/TargetType is not `vpn` or `vbr`.
> 若源/目的类型不是 `vpn` 或 `vbr`，可省略 `--source-ip-address` / `--target-ip-address`。

### Step 4: Poll for Reverse Result / 轮询反向结果

Same as Step 2, using the reverse `NetworkReachableAnalysisId`.

### Step 5: Result Interpretation / 结果解读

> **CRITICAL / 关键**: Always use `topologyData.positive` from the **actively initiated** analysis task.
> **IGNORE** `topologyData.reverse` in any response — it is unreliable.
> 
> 始终使用**主动发起**的分析任务返回的 `topologyData.positive`。
> **忽略**任何响应中的 `topologyData.reverse`——它不可靠。

For each direction (forward/reverse) / 对正向和反向分别：

1. Check `Reachable` field. If `true`, path is connected. / 检查 `Reachable` 字段，`true` 表示可达。
2. If `false`, analyze from `NetworkReachableAnalysisResult`: / 若为 `false`，分析以下字段定位阻断点：
   - `errorCode` — root cause code / 根因错误码
   - `securityGroupData` — security group rules blocking traffic / 安全组拦截规则
   - `routeData` — route table entries causing drops / 路由表丢包条目

### Step 6: Topology Visualization / 拓扑可视化 (Mermaid)

Generate a Mermaid diagram from `topologyData.positive`:

```
graph LR
```

- **Nodes**: Extract `nodeType` and `bizInsId` from `nodeList`
- **Links**: Build directional edges from `linkList`

Example:
```mermaid
graph LR
    ECS_i-src["ECS: i-bp1xxx"] --> VRouter_vrt-1["VRouter: vrt-xxx"]
    VRouter_vrt-1 --> VSW_vsw-1["VSW: vsw-xxx"]
    VSW_vsw-1 --> ENI_eni-1["ENI: eni-xxx"]
    ENI_eni-1 --> ECS_i-dst["ECS: i-bp2xxx"]
```

### Step 7: Resource Monitoring Diagnostics / 途经资源监控诊断

For resource IDs found in `topologyData`, if they match the prefixes below, query monitoring data for the **last 1 hour**:
对 `topologyData` 中途经的资源 ID，若匹配以下前缀，查询**最近 1 小时**监控数据：

| Prefix | Namespace | Metrics |
|--------|-----------|---------|
| `ecs-` | `acs_ecs_dashboard` | `CPUUtilization`, `ConnectionUtilization`, `DiskReadWriteIOPSUtilization`, `BurstCredit`, `DiskIOQueueSize` |
| `eip-` | `acs_vpc_eip` | `out_ratelimit_drop_speed`, `net_out.rate_percentage`, `net_rxPkgs.rate` |
| `nat-` | `acs_nat_gateway` | `ErrorPortAllocationCount`, `SessionLimitDropConnection`, `SessionActiveConnectionWaterLever`, `SessionNewConnectionWaterLever`, `BWRateOutToOutside`, `DropTotalPps` |
| `clb-` | `acs_slb_dashboard` | `UnhealthyServerCount`, `UpstreamCode5xx`, `InstanceQpsUtilization`, `InstanceMaxConnectionUtilization`, `UpstreamRt`, `StatusCode4xx` |
| `vbr-` | `acs_physical_connection` | `VbrHealthyCheckLossPercent`, `VbrHealthyCheckLatency`, `PkgsRateLimitDropOutFromVpcToVbr`, `RateOutFromVpcToIDC` |

Query command (CMS uses **PascalCase API-style**, not plugin mode):

```bash
aliyun cms DescribeMetricData \
  --Namespace <Namespace> \
  --MetricName <MetricName> \
  --Dimensions '[{"instanceId":"<ResourceId>"}]' \
  --StartTime <1HourAgoTimestamp> \
  --EndTime <NowTimestamp> \
  --Period 60 \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Rate limit**: 10 calls/second per account. Batch queries across multiple metrics should be paced accordingly.

## Cleanup / 清理

NIS reachability analysis is **read-only** — no cloud resources are created or modified.
No cleanup is required.
NIS 可达性分析为**只读操作**——不会创建或修改任何云资源，无需清理。

## Constraints / 使用限制

1. **IPv4 only / 仅支持 IPv4** — Only IPv4 path analysis is supported.
2. **Unidirectional / 单向分析** — Each analysis is one-way; reverse path requires a separate task with swapped source/target.
3. **CMS quota / CMS 配额** — `DescribeMetricData` shares 1,000,000 free calls/month with other CMS query APIs.
4. **CMS rate limit / CMS 频控** — 10 calls/second per account (including RAM users).

## Best Practices / 最佳实践

1. Always perform both forward and reverse analysis to confirm bidirectional connectivity. / 始终执行正向+反向分析以确认双向连通性。
2. When path is unreachable, check security group rules and route tables first. / 路径不可达时，优先检查安全组规则和路由表。
3. For `vpn`/`vbr` scenarios, always provide On-Premise IP. / `vpn`/`vbr` 场景务必提供云下私网 IP。
4. Use Mermaid topology diagrams to visualize traffic paths. / 使用 Mermaid 拓扑图帮助用户可视化流量路径。
5. Query monitoring data only for resources on the actual path. / 仅查询实际路径上的资源监控数据以减少 API 调用。
6. Present monitoring anomalies alongside reachability results. / 将监控异常与可达性结果一并呈现，提供完整诊断。

## References / 参考文件

| Reference | Contents (EN) | 内容 (ZH) |
|-----------|---------------|-----------|
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions | 所需 RAM 权限策略 |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification commands | 逐步验证命令 |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect CLI patterns | 正确/错误 CLI 模式对照 |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide | 阿里云 CLI 安装指南 |
