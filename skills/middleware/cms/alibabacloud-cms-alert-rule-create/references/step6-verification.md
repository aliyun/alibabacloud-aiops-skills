# Step 6: 验证

## 目的
检查告警状态并提供最佳实践建议。

---

## 状态确认

### CMS 1.0

```bash
aliyun cms describe-metric-rule-list --rule-id "<rule-id>"
```

**预期结果：**
- `AlertState` = "OK" 或 "ALARM"

---

## 常用管理命令

### CMS 1.0

```bash
# 列出规则
aliyun cms describe-metric-rule-list --namespace <ns>

# 启用规则
aliyun cms enable-metric-rules --ids '["<id>"]'

# 禁用规则
aliyun cms disable-metric-rules --ids '["<id>"]'

# 删除规则
aliyun cms delete-metric-rules --ids '["<id>"]'
```

---

## 最佳实践建议

### 1. 恢复通知
建议启用"恢复通知"开关。

### 2. 多级别告警
建议同时配置 Warn 和 Critical 阈值。

### 3. 静默期
建议生产环境设置 5-10 分钟静默期，避免告警风暴。

---

## 示例场景

### 场景：CMS 1.0 资源告警

**用户**："帮我监控 ECS CPU，超过 85% 时告警"

**技能路径**：
1. ✅ 识别为 **CMS 1.0 告警**（`step0`）
2. ✅ 获取 Namespace=`acs_ecs_dashboard`，确认实例范围（`step1`）
3. ✅ 从指标库提取 `CPUUtilization`（`step2`）
4. ✅ 配置阈值 85%（`step3`）
5. ✅ 查询 CMS 联系人组（`step4`）
6. ✅ 预览配置并执行（`step5`）
7. ✅ 验证状态（`step6`）

---

## 完成
告警创建完成！
