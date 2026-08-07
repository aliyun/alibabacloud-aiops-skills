# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public update-standard [flags]`，不用 PascalCase `UpdateStandard`

### 2. 命令名正确
- 查询列表命令是 `list-standards`（**复数**），不是 `list-standard`
- 生命周期命令：`get-standard` / `create-standard` / `offline-standard` / `publish-standard`

### 3. 更新必填参数齐全
- `--standard-id` + `--standard-status` 必填（比 create 多这两项）
- `--standard-status` 为合法枚举（`EFFECTIVE` / `DRAFT` / `OFFLINED` 等），不确定先 `get-standard` 回填

### 3.1 标准属性值位置正确（实测高频坑）
- 属性值写在 `--standard-template-reference.AttributeValueList`（元素 `{"AttributeId":<属性 Id>,"Value":"..."}`），**不放 `--standard-general-monitor-config`**
- `AttributeId` 来自 `get-standard-template` 的 `TemplateInfo.AttributesConfig.AttributeList[].Id`
- `AttributeValueList` 无逐元素增删改语义：**整体覆盖**，改一个属性也要带上其余属性值
- 报 `RequiredAttributeValueIsBlank` 时不得在 monitor-config 内换字段名重试

### 4. Id 增改删语义正确
- 新增：子元素**不传 Id**
- 更新：子元素**传现有 Id**
- 删除：请求中**省略该 Id**
- 更新前先 `get-standard` 拉全量，避免漏列已有 Id 误删

### 5. 类型分支正确
- `Type=METADATA`：无需 `RuleSubType / QualityRuleTemplate / RuleConfigList / RuleValidateConfigList`
- `Type=QUALITY` + `RuleSubType=CUSTOMIZED`：三项必填
- 切换 METADATA → QUALITY 必须补齐 `RuleSubType` 及对应必填项

### 6. RuleValidateConfigList 校验树正确
- 「父 RELATION（AND/OR） + 子 EXPRESSION」结构；子节点 `ParentId` 指向父 `Id`
- `EXPRESSION` 叶子必填 `Metric` / `MetricName` / `Value`；每个节点 `Id` 唯一

### 7. 参数确认
- `--standard-id` / `--standard-status` / 监控配置执行前需用户确认
- 不硬编码 tenant-id / standard-id / 模板 Id

### 8. 可观测性
- 每条 aliyun 命令携带 `--user-agent AlibabaCloud-Agent-Skills/update-standard/{session-id}`
- session-id 继承自父套件，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant / standard / 模板 ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 命令名写成 `list-standard`（应为 `list-standards`）
- ❌ 缺少必填 `--standard-id` / `--standard-status`
- ❌ 更新前不 `get-standard` 拉全量，漏列已有 Id 导致误删监控配置
- ❌ `Type=QUALITY`+`CUSTOMIZED` 时漏填 QualityRuleTemplate / RuleConfigList / RuleValidateConfigList
- ❌ 两个 EXPRESSION 平铺（缺少 RELATION 父节点串联「且/或」）
- ❌ 静默更新标准（未经用户确认参数）
