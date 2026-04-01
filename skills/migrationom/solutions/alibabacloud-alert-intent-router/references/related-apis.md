# API 参考

> **重要**: 所有 CLI 命令必须添加 User-Agent 头:
> ```bash
> --header "User-Agent: AlibabaCloud-Agent-Skills"
> ```

## NIS 网络智能服务 — 版本: 2021-12-16

| CLI 命令 | API Action | 说明 |
|---------|-----------|------|
| `aliyun nis create-and-analyze-network-path --header "User-Agent: AlibabaCloud-Agent-Skills"` | CreateAndAnalyzeNetworkPath | 创建网络可达性分析任务 |
| `aliyun nis get-network-reachable-analysis --header "User-Agent: AlibabaCloud-Agent-Skills"` | GetNetworkReachableAnalysis | 查询分析任务结果 |

### CreateAndAnalyzeNetworkPath 参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| `--source-id` | string | 是 | 源资源ID |
| `--source-type` | string | 是 | 源类型: ecs, internetIp, vsw, vpn, vbr |
| `--target-id` | string | 是 | 目的资源ID |
| `--target-type` | string | 是 | 目的类型: ecs, internetIp, vsw, vpn, vbr, clb |
| `--protocol` | string | 否 | 协议: tcp, udp, icmp |
| `--source-ip-address` | string | 否 | 源IP（vpn/vbr 云下私网IP必填） |
| `--target-ip-address` | string | 否 | 目的IP（vpn/vbr 云下私网IP必填） |
| `--source-port` | int | 否 | 源端口 |
| `--target-port` | int | 否 | 目的端口（tcp/udp必填） |
| `--region` | string | 否 | 地域ID |

### GetNetworkReachableAnalysis 参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| `--network-reachable-analysis-id` | string | 是 | 分析任务ID |
| `--region` | string | 否 | 地域ID |

### 返回结果关键字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| NetworkReachableAnalysisStatus | string | 任务状态: init, finish, error, timeout |
| Reachable | boolean | 路径是否可达 |
| NetworkReachableAnalysisResult | string | JSON格式的拓扑、ACL、安全组、路由数据 |

---

## ECS 云服务器 — 版本: 2014-05-26

| CLI 命令 | API Action | 说明 |
|---------|-----------|------|
| `aliyun ecs DescribeInstances --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeInstances | 查询实例列表 |
| `aliyun ecs DescribeInstanceAttribute --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeInstanceAttribute | 查询实例属性 |
| `aliyun ecs DescribeInstanceHistoryEvents --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeInstanceHistoryEvents | 查询系统事件 |
| `aliyun ecs DescribeSecurityGroupAttribute --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeSecurityGroupAttribute | 查询安全组规则 |
| `aliyun ecs RunCommand --header "User-Agent: AlibabaCloud-Agent-Skills"` | RunCommand | 执行云助手命令 |
| `aliyun ecs DescribeInvocationResults --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeInvocationResults | 查询命令结果 |

### DescribeInstances 常用参数

| 参数 | 类型 | 说明 |
|-----|------|------|
| `--InstanceIds` | string | 实例ID列表 JSON，如 '["i-xxx"]' |
| `--InstanceName` | string | 实例名称 |
| `--PrivateIpAddresses` | string | 私网IP列表 JSON |
| `--RegionId` | string | 地域ID |

### RunCommand 参数

| 参数 | 类型 | 说明 |
|-----|------|------|
| `--InstanceId.1` | string | 目标实例ID |
| `--Type` | string | RunShellScript 或 RunPowerShellScript |
| `--CommandContent` | string | Base64编码的命令内容 |
| `--Timeout` | int | 超时时间（秒） |

---

## CMS 云监控 — 版本: 2019-01-01

| CLI 命令 | API Action | 说明 |
|---------|-----------|------|
| `aliyun cms DescribeMetricData --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeMetricData | 查询监控指标数据 |
| `aliyun cms DescribeMetricLast --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeMetricLast | 查询最新监控数据 |

### DescribeMetricData/Last 参数

| 参数 | 类型 | 必填 | 说明 |
|-----|------|-----|------|
| `--MetricName` | string | 是 | 指标名称 |
| `--Namespace` | string | 是 | 服务命名空间 |
| `--Dimensions` | string | 否 | 资源过滤，如 '[{"instanceId":"i-xxx"}]' |
| `--StartTime` | string | 否 | 开始时间 |
| `--EndTime` | string | 否 | 结束时间 |
| `--Period` | string | 否 | 统计周期: 15, 60, 900, 3600 |

### 常用监控指标

| 资源类型 | Namespace | 指标 |
|---------|-----------|-----|
| ECS | acs_ecs_dashboard | CPUUtilization, memory_usedutilization, diskusage_utilization |
| EIP | acs_vpc_eip | out_ratelimit_drop_speed, net_out.rate_percentage |
| NAT | acs_nat_gateway | ErrorPortAllocationCount, DropTotalPps |
| CLB | acs_slb_dashboard | UnhealthyServerCount, UpstreamCode5xx |

---

## VPC 专有网络

| CLI 命令 | API Action | 说明 |
|---------|-----------|------|
| `aliyun vpc DescribeVpcs --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeVpcs | 查询VPC信息 |
| `aliyun vpc DescribeEipAddresses --header "User-Agent: AlibabaCloud-Agent-Skills"` | DescribeEipAddresses | 查询EIP绑定 |
