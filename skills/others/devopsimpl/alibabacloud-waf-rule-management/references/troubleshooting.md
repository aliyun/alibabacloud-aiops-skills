# WAF Skill 常见问题排查

> 本文件包含 CLI 工具安装、SLS 查询、认证等常见问题的解决方案。
> 
> 仅在遇到问题时由 Agent 按需读取。

---

## 1. 命令未找到：`aliyun: command not found`

**解决**：
```bash
brew install aliyun-cli
```

---

## 2. 命令未找到：`aliyunlog: command not found`

**解决**：
```bash
pip3 install aliyun-log-cli
```

---

## 3. SLS 查询返回空结果

**排查步骤**：

1. 确认 traceid/查询条件是否正确
2. 确认时间范围是否覆盖请求发生时间（建议查最近 7 天）
3. 确认 Region 是否正确（国内 `cn-hangzhou`，海外 `ap-southeast-1`）
4. 确认 AK/SK 有访问 SLS 的权限
5. 确认 Project/Logstore 名称拼写正确

---

## 4. 认证失败

**排查步骤**：

1. 执行 `aliyun sts get-caller-identity` 验证 AK/SK 有效性
2. 确认该账号有访问对应 Project/Logstore 的权限
3. 检查 RAM 权限策略是否正确配置（参见 [ram-policies.md](ram-policies.md)）

---

## 5. SLS 查询报错：`ParameterInvalid: Column 'xxx' cannot be resolved`

**原因**：select 语句中使用了不存在的字段（如 `waf_hit`）。

**解决**：移除不存在的字段后重试。详见 SKILL.md 第 1.4 节的关键字段说明。

---

## 6. WAF API 报错：`Defense.Control.DefenseWhitelistBypassTagInvalid`

**原因**：白名单规则缺少 `tags` 字段。

**解决**：添加 `"tags":["regular_rule"]` 等合法标签。详见 [api_reference.md](api_reference.md) 第 7.1 节。

---

## 7. WAF API 报错：`Defense.Control.DefenseRuleConditionValueInvalid`

**原因**：conditions 字段错误，如使用了 `"value"` 而非 `"values"`。

**解决**：检查 conditions 数组中每个对象的字段名，确保使用复数形式 `"values"`。

---

## 8. WAF API 报错：`InvalidBindResources`

**原因**：数组参数格式错误，使用了 JSON 数组或缺少索引。

**解决**：改用 flat format：`--BindResources.1 'xxx'`。详见 [cli_traps.md](cli_traps.md)。

---

## 9. 规则下发后未生效

**排查步骤**：

1. 确认规则状态 `status=1`（启用）
2. 等待 10-30 秒生效延迟
3. 使用规则不生效诊断流程（SKILL.md 第 3 章）
4. 检查防护对象是否正确绑定模版
5. 检查是否有白名单冲突

---

## 10. 规则所在模板未绑定到防护对象

**问题表现**：规则已创建且状态正常（status=1），但流量未被拦截或放行。

**原因分析**：
- WAF 3.0 的规则组织在模板（Template）中
- 模板必须绑定到防护对象（Resource）才会生效
- 如果规则所在模板未绑定到目标防护对象，规则不会生效

**诊断步骤**：

1. **查询规则所在模板**：
   ```bash
   aliyun waf-openapi describe-defense-rules \
     --version 2021-10-01 --force --region cn-hangzhou \
     --profile <profile-name> \
     --user-agent AlibabaCloud-Agent-Skills \
     --InstanceId '<instance_id>' \
     --RuleType 'custom_acl'
   ```
   从返回结果中找到目标规则，记录 `TemplateId`

2. **查询防护对象绑定的模板**：
   ```bash
   aliyun waf-openapi describe-defense-resource-templates \
     --version 2021-10-01 --force --region cn-hangzhou \
     --profile <profile-name> \
     --user-agent AlibabaCloud-Agent-Skills \
     --InstanceId '<instance_id>' --Resource '<resource>'
   ```
   查看返回的 `Templates` 数组

3. **对比判断**：
   - 如果规则的 `TemplateId` 不在已绑定模板列表中，则确认是此问题

**解决方案**：

**方法1：将规则所在模板绑定到防护对象**
- 控制台操作：
  1. 进入 `防护配置` → `防护对象`
  2. 找到目标防护对象（如 `i-bp1ivk5aoljy431axxa8-80-ecs`）
  3. 点击"绑定模板"或"管理模板"
  4. 选择包含目标规则的模板
  5. 保存绑定

**方法2：在已绑定的模板中重新创建规则**
- 控制台操作：
  1. 进入 `防护配置` → `自定义防护` → `自定义规则`
  2. 确保在已绑定模板的上下文中创建规则
  3. 或编辑现有规则，移动到已绑定模板中

**注意事项**：
- 模板绑定后约 30 秒生效
- 一个防护对象可以绑定多个模板
- 白名单模板优先级高于自定义规则模板

---

## 11. 规则匹配条件与实际请求不符

**问题表现**：规则配置了特定的 URI、IP 或其他条件，但实际请求不满足这些条件，导致规则不生效。

**常见场景**：

**场景1：URI 路径不匹配**
- 规则配置：URI **包含** `/chenhang`
- 实际请求：`request_path: "/"`
- 结果：路径不匹配，规则不生效

**场景2：IP 地址不匹配**
- 规则配置：源IP **包含** `192.168.1.0/24`
- 实际请求：`real_client_ip: 10.0.0.1`
- 结果：IP 不在指定网段，规则不生效

**诊断步骤**：

1. **查询规则配置**：
   ```bash
   aliyun waf-openapi describe-defense-rules \
     --version 2021-10-01 --force --region cn-hangzhou \
     --profile <profile-name> \
     --user-agent AlibabaCloud-Agent-Skills \
     --InstanceId '<instance_id>' \
     --Query '{"ruleId":<rule_id>}'
   ```
   查看 `Config` 字段中的 `conditions` 数组

2. **查询实际流量日志**：
   ```bash
   aliyunlog log get_log \
     --project="wafnew-project-<account_id>-cn-hangzhou" \
     --logstore="wafnew-logstore" \
     --query="request_traceid:<traceid>" \
     --from_time="7 days ago" --to_time="now" \
     --region-endpoint="cn-hangzhou.log.aliyuncs.com"
   ```
   查看 `request_path`、`real_client_ip`、`host` 等字段

3. **对比分析**：
   - 检查规则条件中的 key（如 URL、IP）
   - 检查规则条件中的 opValue（如 contain、eq、ne）
   - 检查规则条件中的 values（如 `/chenhang`、`192.168.1.0/24`）
   - 与实际请求的对应字段进行对比

**解决方案**：

根据实际需求调整规则匹配条件：
- 如果要拦截所有访问根路径的请求：URI **等于** `/`
- 如果要拦截包含特定路径的请求：URI **包含** `/特定路径`
- 如果要拦截特定IP：源IP **包含** `IP地址`
- 如果要拦截非特定IP：源IP **不等于** `IP地址`

---

## 12. WAF 控制台路径错误（WAF 2.0 vs 3.0）

**问题描述**：用户或 AI 提供了错误的控制台配置路径。

**错误示例**：
- ❌ `防护配置` → `访问控制` → `白名单`（这是 WAF 2.0 的路径）

**正确路径（WAF 3.0）**：
- ✅ `防护配置` → `自定义防护` → `白名单`
- ✅ `防护配置` → `自定义防护` → `自定义规则`
- ✅ `防护配置` → `自定义防护` → `IP 黑名单`

**如何识别 WAF 版本**：
- WAF 3.0 API 版本：`2021-10-01`
- WAF 3.0 产品名称：`waf-openapi`
- 如果用户未明确说明，默认按 WAF 3.0 处理

**解决**：确保使用 WAF 3.0 的正确控制台路径进行配置指导。

---

## 13. IP 访问控制配置不完整

**问题描述**：用户想实现"只允许特定 IP 访问"，但只配置了白名单，没有配置阻断规则。

**错误做法**：
- 只配置白名单允许某 IP 访问，但未配置其他 IP 的拦截规则
- 这样其他 IP 仍然可以访问（除非基础防护默认拦截）

**正确做法（两种方案）**：

**方案一：自定义规则（推荐）**
- 创建自定义规则：IP **不属于** 指定网段 → **拦截**
- 一条规则即可实现"只允许特定 IP 访问"
- 使用 `custom_acl` DefenseScene，`ne` 操作符

**方案二：白名单 + 基础防护**
- 配置白名单允许特定 IP
- 确保基础防护（`waf_group` 或 `waf_base`）已开启
- 基础防护会默认拦截未匹配的请求

**解决**：在配置指导中明确说明需要配置的完整规则集，确保逻辑完整。

