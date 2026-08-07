# 验收标准

## 功能验收

- [ ] 能用 `create-security-level` 创建数据分级，并用 `get-security-level --index` 回读名称、简称和描述。
- [ ] 能用 `create-security-classify-catalog` 创建分类目录，并能更新或删除临时目录。
- [ ] 能用 `create-security-classify` 创建分类，绑定指定 `level-name`，并用 `get-security-classify` 回读分类详情。
- [ ] 能用 `update-security-classify` 调整分类分级、状态、优先级或高级条件，并回读确认。
- [ ] 能用 `create-security-identify-result` 给具体表字段生成安全识别结果。
- [ ] 能用 `list-security-identify-results` 按 keyword / classifyId / project / datasource 过滤识别结果。
- [ ] 能用 `get-security-identify-result` 查询单个识别结果详情。
- [ ] 能用 `list-security-identify-records` 查询指定表字段的识别记录。
- [ ] 能用 `update-security-identify-result-status` 批量启停识别结果，并二次回读验证状态变化。
- [ ] 能分别核对识别结果 `Status` 与识别记录中的 `ClassifyStatus`，避免把标签启用误判为分类也启用。
- [ ] 能用 `delete-security-identify-results`、`delete-security-classify`、`delete-security-level` 按安全顺序清理临时对象。

## 安全验收

- [ ] 写操作前必须展示租户、分级、分类、表、字段、分类 ID、覆盖策略和影响范围，并获得用户明确确认。
- [ ] `--conflict-strategy` 默认使用 `COVER_UNLOCKED`；使用 `COVER_ALL` 前必须提示会覆盖线上全部打标。
- [ ] 删除分级前确认没有分类绑定；删除分类前确认没有识别结果、识别规则或脱敏联动依赖。
- [ ] 所有 OpenAPI CLI 命令必须携带 `--user-agent AlibabaCloud-Agent-Skills/manage-data-classification/{session-id}`。
- [ ] 不读取、不回显、不写入 AK/SK 等凭证。

## 业务语义验收

- [ ] 清楚区分数据分级、数据分类、识别结果三层对象。
- [ ] 用户说“把字段标记为机密”时，最终必须落到 `create-security-identify-result`，不能只创建分级或分类。
- [ ] 能说明分类分级与脱敏规则、权限审批、资产目录展示的联动边界。
- [ ] 能说明 `table-catalog` 在数据源表、Dataphin 物理表、逻辑表中的不同含义。
- [ ] 不伪造内部 `/api/datasecurity/...` REST 为外部命令入口。
