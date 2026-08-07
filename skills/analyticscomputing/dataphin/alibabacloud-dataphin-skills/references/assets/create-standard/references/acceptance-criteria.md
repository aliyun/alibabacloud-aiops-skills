# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public create-standard [flags]`，不用 PascalCase `CreateStandard`

### 2. 命令名正确
- 查询列表命令是 `list-standards`（**复数**），不是 `list-standard`
- 生命周期命令：`get-standard` / `update-standard` / `offline-standard` / `publish-standard`

### 3. 类型分支正确
- `Type=METADATA`：无需 `RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList`
- `Type=QUALITY` + `RuleSubType=CUSTOMIZED`：三项（QualityRuleTemplate / RuleConfigList / RuleValidateConfigList）必填
- `Type=QUALITY` + `RuleSubType=BY_ATTRIBUTE`：依赖 AttributeId / AttributeMonitorConfig

### 4. RuleValidateConfigList 校验树正确
- 「父 RELATION（AND/OR） + 子 EXPRESSION」结构；子节点 `ParentId` 指向父 `Id`
- `EXPRESSION` 叶子必填 `Metric` / `MetricName` / `Value`
- 每个节点 `Id` 业务侧生成且唯一

### 5. 标准属性值位置正确（实测高频坑）
- 属性值写在 `--standard-template-reference.AttributeValueList`，元素为 `{"AttributeId":<属性 Id>,"Value":"..."}`
- **不把属性值放进 `--standard-general-monitor-config`**（无论叫 `AttributeValues` / `StandardAttributeList` / `AttributeList` 都无效）
- `AttributeId` 来自 `get-standard-template` 的 `TemplateInfo.AttributesConfig.AttributeList[].Id`，不凭属性编码猜
- `Required=true` 的属性全部给值；报 `RequiredAttributeValueIsBlank` 时不得在 monitor-config 内换字段名重试

### 6. JSON 参数正确
- `--standard-general-monitor-config` 传 JSON 字符串（外单内双）
- `--standard-set-reference` 传 `{"Id":<int>}`；`--standard-template-reference` 传 `{"Id":<int>,"AttributeValueList":[...]}`

### 7. 参数确认
- 模板 Id / 标准集 Id / 属性值 / 监控配置执行前需用户确认
- 不硬编码 tenant-id / 模板 Id / 标准集 Id

### 8. 可观测性
- 每条 aliyun 命令携带 `--user-agent AlibabaCloud-Agent-Skills/create-standard/{session-id}`
- session-id 继承自父套件，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant / 模板 / 标准集 ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 命令名写成 `list-standard`（应为 `list-standards`）
- ❌ `Type=QUALITY`+`CUSTOMIZED` 时漏填 QualityRuleTemplate / RuleConfigList / RuleValidateConfigList
- ❌ 两个 EXPRESSION 平铺（缺少 RELATION 父节点串联「且/或」）
- ❌ `list-standards` 缺少 `--standard-stage`（DEV/PROD）
- ❌ 静默创建标准（未经用户确认参数）
