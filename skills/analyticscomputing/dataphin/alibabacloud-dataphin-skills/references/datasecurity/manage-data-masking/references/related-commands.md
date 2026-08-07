# 相关命令与内部接口边界

## 公开 CLI 可用命令

当前 `manage-data-masking` 只能使用公开 `dataphin-public` 命令完成字段标签前置检查，不能直接创建脱敏规则。

| 命令 | OpenAPI | 用途 | 类型 |
|---|---|---|---|
| `list-security-identify-results` | `ListSecurityIdentifyResults` | 按表名、字段名、分类等查询字段安全识别结果 | 读 |
| `get-security-identify-result` | `GetSecurityIdentifyResult` | 按识别结果 ID 查询字段标签详情 | 读 |
| `list-security-identify-records` | `ListSecurityIdentifyRecords` | 查询指定表字段的识别记录与分类状态 | 读 |
| `get-security-classify` | `GetSecurityClassify` | 回读分类与分级绑定信息 | 读 |

## 当前未暴露的脱敏规则能力

以下能力在页面内部 REST 中存在业务语义，但未出现在当前公开命令集与版本感知 OpenAPI 索引中。

| 内部 REST 语义 | 业务用途 | 外部 Skill 处理方式 |
|---|---|---|
| `/api/datasecurity/desensitization/addDesensitizeRule` | 创建动态脱敏规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/updateDesensitizeRule` | 编辑动态脱敏规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/desensitizeRule/close` | 停用脱敏规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/desensitizeRule/open` | 启用脱敏规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/queryPagedDesensitizeRule` | 查询脱敏规则列表 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/getDesensitizeRule` | 获取脱敏规则详情 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/getDesensitizeRuleByClassifyId` | 查询分类绑定的脱敏规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/addDesensitizeWhiteListRule` | 创建脱敏白名单规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/desensitizeWhiteListRule/close` | 停用脱敏白名单规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/deleteDesensitizeWhiteListRule` | 删除脱敏白名单规则 | 仅作为语义参考，不执行 |
| `/api/datasecurity/desensitization/updateDesensitizeSettings` | 更新默认脱敏配置 | 仅作为语义参考，不执行 |
| `/api/datasecurity/encrypt/validateEncryptRange` | 校验 FPE 加密区间 | 仅作为语义参考，不执行 |

## 参数清单

| 参数 | 来源 | 说明 |
|---|---|---|
| `tenant-id` | 用户确认 | 租户 ID，大整数建议字符串传 |
| `table-catalog` | 用户确认 / 资产回读 | 逻辑表填板块英文名，物理表填项目英文名，数据源表填 db/schema |
| `table-name` | 用户确认 | 目标表名 |
| `field-name` | 用户确认 | 目标字段名 |
| `classify-id` | 公开识别结果回读 | 脱敏规则通常绑定数据分类 |
| `classify-name` | 公开分类回读 | 便于用户确认业务语义 |
| `algorithm-code` | 用户确认 | 掩码、哈希、加密、空值、保留格式等算法编码 |
| `scene` | 用户确认 | `TEMP_QUERY`、`WRITE_DEV` 等生效场景 |
| `rule-scopes` | 用户确认 | 业务板块、项目、平台、账号、表范围等 |
| `white-list-account` | 用户确认 | 白名单账号，高风险 |
| `effective-date-range` | 用户确认 | 白名单生效时间窗口 |

## 正确公开检查示例

```bash
TENANT_ID="<租户 ID>"
SESSION_ID="<inherited from alibabacloud-dataphin-skills>"
UA="AlibabaCloud-Agent-Skills/manage-data-masking/$SESSION_ID"

aliyun dataphin-public list-security-identify-results --tenant-id "$TENANT_ID" \
  --keyword "phone" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

aliyun dataphin-public list-security-identify-records --tenant-id "$TENANT_ID" \
  --table-catalog "<catalog>" \
  --table-name "ods_user" \
  --field-name "phone" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json

aliyun dataphin-public get-security-classify --tenant-id "$TENANT_ID" \
  --security-classify-id "<分类ID>" \
  --user-agent "$UA" --format json
```

## 常见错误

| 错误做法 | 风险 | 正确做法 |
|---|---|---|
| 只创建分类分级就宣称已脱敏 | 查询结果仍可能是明文 | 明确分类分级只是前置标签 |
| 伪造 `create-desensitize-rule` 命令 | 当前 CLI 无此命令，会误导用户 | 核对版本感知 OpenAPI 索引与公开命令集 |
| 默认全业务板块、全项目生效 | 影响范围过大 | 逐项确认 `ruleScopes` |
| 白名单默认长期有效 | 例外权限失控 | 确认账号、场景、起止日期 |
| 修改默认脱敏配置不恢复 | 租户级全局影响 | 记录旧值并恢复；当前公开 CLI 不执行 |

## 业务边界

- 本 Skill 不直接执行内部 REST，也不绕过公开 OpenAPI 权限边界。
- 若字段未分类分级，应提示先完成字段分类分级，再继续脱敏需求交付。
- 若未来公开 OpenAPI 增加脱敏规则命令，应更新本文件、RAM 策略和 L2/L3 测试报告后再允许写操作。
