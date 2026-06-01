# RAM 权限清单

本 Skill 执行所需的 RAM 权限（只读，无写权限）：

## 云防火墙查询权限

`yundun-cloudfw:DescribeAssetList` — 查询互联网防火墙防护资产列表及防护状态

`yundun-cloudfw:DescribePolicyAdvancedConfig` — 查询互联网防火墙全局严格模式配置

`yundun-cloudfw:DescribeControlPolicy` — 查询互联网防火墙 ACL 规则列表

`yundun-cloudfw:DescribeVpcFirewallList` — 查询 VPC 边界防火墙实例列表

`yundun-cloudfw:DescribeVpcFirewallControlPolicy` — 查询 VPC 边界防火墙 ACL 规则列表

`yundun-cloudfw:DescribeNatFirewallList` — 查询 NAT 边界防火墙实例列表

`yundun-cloudfw:DescribeNatFirewallControlPolicy` — 查询 NAT 边界防火墙 ACL 规则列表

`yundun-cloudfw:DescribeTrafficLog` — 查询流量日志（需已开通日志分析功能）

## 说明

以上权限均包含在阿里云托管策略 `AliyunYundunCloudFirewallReadOnlyAccess` 中，
推荐直接为诊断用 RAM 用户授予此托管策略，无需逐条配置。
