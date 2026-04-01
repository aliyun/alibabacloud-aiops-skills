# 根因分析报告模板

本模板用于生成告警诊断后的根因分析报告。

---

## 报告模板

```
=====================================
       阿里云告警根因分析报告
=====================================

【告警信息】
- 告警内容：{alert_content}
- 告警来源：{alert_source}
- 告警时间：{alert_time}
- 告警级别：{alert_level}

【意图分类】
- 分类结果：{intent_type}
  - 网络连通性问题 → NIS可达性分析
  - ECS实例问题 → ECS实例诊断
- 匹配关键字：{matched_keywords}

【诊断对象】
- 资源ID：{resource_id}
- 资源名称：{resource_name}
- 地域：{region_id}
- VPC：{vpc_id}
- 安全组：{security_group_ids}

=====================================
         诊断结果
=====================================

【根因判定】
- 根因类型：{root_cause_type}
- 根因描述：{root_cause_description}
- 错误码：{error_code}（如适用）

【详细分析】

1. 云平台侧检查
   - 实例状态：{instance_status}
   - 系统事件：{system_events}
   - 安全组规则：{security_group_analysis}
   - 网络配置：{network_config}
   - 监控指标：
     * CPU使用率：{cpu_utilization}%
     * 内存使用率：{memory_utilization}%
     * 磁盘使用率：{disk_utilization}%

2. 网络路径分析（NIS）（如适用）
   - 正向路径：{forward_reachable}
   - 反向路径：{reverse_reachable}
   - 阻断点：{blocking_point}
   - 阻断原因：{blocking_reason}
   - 网络拓扑：
     {topology_diagram}

3. GuestOS内部诊断（如执行）
   - 系统负载：{system_load}
   - 磁盘状态：{disk_status}
   - 网络状态：{network_status}
   - 系统日志：{system_logs}

【问题总结】
{issues_summary}

=====================================
         处置建议
=====================================

【立即处理】
{immediate_actions}

【后续优化】
{optimization_suggestions}

【风险提示】
{risk_warnings}

=====================================
         附录
=====================================

【诊断时间线】
{diagnosis_timeline}

【相关资源】
{related_resources}

【参考文档】
- 阿里云ECS文档：https://help.aliyun.com/product/25365.html
- 阿里云NIS文档：https://help.aliyun.com/product/134713.html
- 阿里云安全组最佳实践：https://help.aliyun.com/document_detail/25475.html

=====================================
       报告生成时间：{report_time}
=====================================
```

---

## 字段说明

### 告警信息字段

| 字段 | 说明 | 示例 |
|-----|------|-----|
| alert_content | 原始告警内容 | "ECS i-xxx 端口22连接超时" |
| alert_source | 告警来源系统 | CMS, ARMS, SLS |
| alert_time | 告警发生时间 | 2024-01-15 10:30:00 |
| alert_level | 告警级别 | Critical, Warning, Info |

### 诊断对象字段

| 字段 | 说明 | 示例 |
|-----|------|-----|
| resource_id | 资源ID | i-bp1abc123 |
| resource_name | 资源名称 | web-server-01 |
| region_id | 地域 | cn-shanghai |
| vpc_id | VPC ID | vpc-xxx |
| security_group_ids | 安全组列表 | sg-xxx, sg-yyy |

### 根因类型枚举

| 类型 | 说明 |
|-----|------|
| SECURITY_GROUP_BLOCK | 安全组规则阻断 |
| ROUTE_TABLE_DROP | 路由表丢包 |
| INSTANCE_STOPPED | 实例已停止 |
| INSTANCE_EXPIRED | 实例已过期 |
| INSTANCE_LOCKED | 实例已锁定 |
| HIGH_CPU_USAGE | CPU使用率过高 |
| HIGH_MEMORY_USAGE | 内存使用率过高 |
| DISK_FULL | 磁盘空间不足 |
| NETWORK_UNREACHABLE | 网络不可达 |
| SERVICE_NOT_RUNNING | 服务未运行 |
| SYSTEM_EVENT | 系统事件影响 |
| IPTABLES_BLOCK | iptables规则阻断 |
| PORT_NOT_LISTENING | 端口未监听 |

---

## 示例报告

```
=====================================
       阿里云告警根因分析报告
=====================================

【告警信息】
- 告警内容：ECS实例 i-uf61cqjmlzllh516wtlp 访问不通
- 告警来源：CMS
- 告警时间：2024-03-23 14:30:00
- 告警级别：Critical

【意图分类】
- 分类结果：ECS实例问题 → ECS实例诊断
- 匹配关键字：ECS实例, 访问不通

【诊断对象】
- 资源ID：i-uf61cqjmlzllh516wtlp
- 资源名称：app-a
- 地域：cn-shanghai
- VPC：vpc-uf64633l39g37rkv7liqx
- 安全组：sg-uf6e9mj0yddrvnz21v74

=====================================
         诊断结果
=====================================

【根因判定】
- 根因类型：SECURITY_GROUP_BLOCK
- 根因描述：安全组存在优先级1的Drop ALL规则，阻断了所有入站流量
- 错误码：nra.securitygroup.rule.deny

【详细分析】

1. 云平台侧检查
   - 实例状态：Running ✅
   - 系统事件：无
   - 安全组规则：存在异常 ❌
     * 发现规则 sgr-uf614ksdpw3quyqlkifs
     * 协议: ALL, 端口: -1/-1
     * 源: 0.0.0.0/0, 策略: Drop, 优先级: 1
   - 网络配置：正常
   - 监控指标：
     * CPU使用率：0.27%
     * 内存使用率：45%
     * 磁盘使用率：32%

【问题总结】
1. 安全组 sg-uf6e9mj0yddrvnz21v74 存在一条优先级最高(1)的
   Drop ALL入方向规则，导致所有入站流量被阻断。

=====================================
         处置建议
=====================================

【立即处理】
1. 删除阻断规则：
   aliyun ecs RevokeSecurityGroup \
     --SecurityGroupId sg-uf6e9mj0yddrvnz21v74 \
     --RegionId cn-shanghai \
     --SecurityGroupRuleId.1 sgr-uf614ksdpw3quyqlkifs

【后续优化】
1. 审核安全组规则变更流程，避免误添加Drop规则
2. 配置安全组规则变更告警

【风险提示】
- 删除规则后入站流量将恢复，请确认这是预期行为

=====================================
       报告生成时间：2024-03-23 14:35:00
=====================================
```

---

## 使用说明

1. 诊断完成后，根据诊断结果填充模板字段
2. 根因类型应从枚举值中选择
3. 处置建议应包含具体可执行的命令
4. 风险提示应提醒用户操作可能带来的影响
