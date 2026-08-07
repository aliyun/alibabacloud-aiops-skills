# 相关命令

## 命令总览

| 命令 | OpenAPI Action | 用途 | 类型 |
|------|----------------|------|------|
| `create-security-level` | `CreateSecurityLevel` | 新建数据分级 | 写 |
| `get-security-level` | `GetSecurityLevel` | 按分级 index 获取数据分级详情 | 读 |
| `update-security-level` | `UpdateSecurityLevel` | 更新数据分级名称、顺序或描述 | 写 |
| `delete-security-level` | `DeleteSecurityLevel` | 删除数据分级 | 写 |
| `create-security-classify-catalog` | `CreateSecurityClassifyCatalog` | 新建数据分类目录 | 写 |
| `update-security-classify-catalog` | `UpdateSecurityClassifyCatalog` | 更新数据分类目录 | 写 |
| `delete-security-classify-catalog` | `DeleteSecurityClassifyCatalog` | 删除数据分类目录 | 写 |
| `create-security-classify` | `CreateSecurityClassify` | 新建数据分类并绑定分级 | 写 |
| `get-security-classify` | `GetSecurityClassify` | 获取数据分类详情 | 读 |
| `update-security-classify` | `UpdateSecurityClassify` | 更新分类名称、路径、分级、条件或状态 | 写 |
| `delete-security-classify` | `DeleteSecurityClassify` | 删除数据分类 | 写 |
| `create-security-identify-result` | `CreateSecurityIdentifyResult` | 给具体表字段创建安全识别结果 | 写 |
| `list-security-identify-results` | `ListSecurityIdentifyResults` | 分页查询字段识别结果 | 读 |
| `get-security-identify-result` | `GetSecurityIdentifyResult` | 获取单个识别结果详情 | 读 |
| `list-security-identify-records` | `ListSecurityIdentifyRecords` | 查询指定表字段的识别记录 | 读 |
| `update-security-identify-result-status` | `UpdateSecurityIdentifyResultStatus` | 批量启停识别结果 | 写 |
| `delete-security-identify-results` | `DeleteSecurityIdentifyResults` | 批量删除识别结果 | 写 |

> `get-security-secret-key` 属于密钥管理，不纳入本 Skill 主链路。

## 核心参数

| 参数 | 命令 | 类型 | 说明 |
|---|---|---|---|
| `--tenant-id` | 全部 OpenAPI 命令 | number/string | 租户 ID，建议用引号传大整数 |
| `--security-level-name` | level create/update/delete | string | 分级名称，如 C4-绝密、L3 |
| `--abbreviation` | level/classify create/update | string | 简称，如 C4、ID_CARD |
| `--index` | level create/update/get/delete | number | 分级顺序或敏感程度，需以租户配置为准 |
| `--directory-name` | classify catalog create/update | string | 分类目录名称 |
| `--parent-path` | classify/catalog create/update/delete | string | 父目录路径，根目录为 `/` |
| `--visible-type` | catalog create/update | string | `PUBLIC` 或 `PRIVATE` |
| `--security-classify-name` | classify create/update/delete | string | 分类名称，如 身份证号、手机号 |
| `--security-classify-id` | classify get/update/delete | number | 分类 ID |
| `--level-name` | classify create/update | string | 绑定的数据分级名称 |
| `--feature-name-list` | classify create/update | list(string) | 引用识别特征名称 |
| `--advanced-condition-list` | classify create/update | list(object) | 高级匹配条件；每个元素建议传 JSON 对象 |
| `--priority` | classify create/update | number | 分类优先级，默认 5 |
| `--status` | classify create/update | string | `ENABLE` 或 `DISABLE` |
| `--table-catalog` | identify result create / identify record list | string | 表 Catalog；不同表来源含义不同 |
| `--table-name` / `--field-name` | identify result create / identify record list | string | 目标表名和字段名 |
| `--classify-id` | identify result create / result list | number | 分类 ID |
| `--conflict-strategy` | identify result create | string | `COVER_UNLOCKED` 或 `COVER_ALL` |
| `--enable` | identify result create / status update | boolean | 是否生效 |
| `--identify-result-id-list` | status update / delete results | list(number) | 识别结果 ID 列表 |
| `--keyword` | list results | string | 按表 catalog、表名、中文名、字段名搜索 |
| `--page-no` / `--page-size` | list results / records | number | 分页参数 |
| `--is-datasource-table` | result create / records list | boolean | true 表示数据源表；false 表示 Dataphin 表 |
| `--datasource-name` / `--datasource-env` | 数据源表场景 | string | 数据源名称与环境标识 |

## 正确参数示例

### 创建分级

```bash
aliyun dataphin-public create-security-level --tenant-id "$TENANT_ID" \
  --security-level-name "C4-绝密" \
  --abbreviation C4 \
  --index 4 \
  --description "高度敏感数据" \
  --user-agent "$UA" --format json
```

### 创建分类

```bash
aliyun dataphin-public create-security-classify --tenant-id "$TENANT_ID" \
  --security-classify-name "身份证号" \
  --abbreviation ID_CARD \
  --parent-path "/" \
  --level-name "C4-绝密" \
  --priority 5 \
  --status ENABLE \
  --user-agent "$UA" --format json
```

### 给字段创建识别结果

```bash
aliyun dataphin-public create-security-identify-result --tenant-id "$TENANT_ID" \
  --table-catalog "<项目英文名或板块英文名或数据源 schema>" \
  --table-name "ods_user" \
  --field-name "id_card" \
  --classify-id "<分类ID>" \
  --enable true \
  --conflict-strategy COVER_UNLOCKED \
  --user-agent "$UA" --format json
```

### 查询字段标签

```bash
aliyun dataphin-public list-security-identify-results --tenant-id "$TENANT_ID" \
  --keyword "id_card" \
  --page-no 1 --page-size 10 \
  --user-agent "$UA" --format json
```

### 启停识别结果

```bash
aliyun dataphin-public update-security-identify-result-status --tenant-id "$TENANT_ID" \
  --enable false \
  --identify-result-id-list "<识别结果ID>" \
  --user-agent "$UA" --format json
```

## 参数陷阱

| 陷阱 | 错误示例 | 正确示例 |
|---|---|---|
| 把创建分级当成字段打标 | 只执行 `create-security-level` | 字段打标必须执行 `create-security-identify-result` |
| 把分类条件当成立即打标 | 只执行 `create-security-classify --advanced-condition-list ...` | 字段手动打标必须执行 `create-security-identify-result` |
| 伪造高级条件对象 | 直接传 `{"Property":"FIELD_NAME"...}` | 仅在已有明确特征条件上下文时传高级条件，否则不传 |
| 覆盖策略过宽 | `--conflict-strategy COVER_ALL` 未确认 | 默认 `COVER_UNLOCKED`，仅覆盖未锁定标签 |
| 表来源口径混淆 | 数据源表仍按项目英文名填 `table-catalog` | 数据源表填 db/schema，Dataphin 物理表填项目英文名，逻辑表填板块英文名 |
| 删除顺序错误 | 先删分级 | 先停用/删除识别结果，再删分类，最后删分级 |
| 忘记 user-agent | 只执行业务参数 | 每条 OpenAPI CLI 都加 `--user-agent "$UA"` |

## 业务边界

- 公共 OpenAPI 直接覆盖分级、分类目录、分类和识别结果；内部 REST 只作业务语义参考。
- 自动识别规则、扫描任务、特征生成、批量 Excel 导入等属于更复杂的数据安全识别流水线，本 Skill 只沉淀公开 OpenAPI 已覆盖的分级分类与识别结果主链路。
- 分类分级与脱敏策略是上下游关系：分类分级提供敏感字段标签，脱敏规则决定查询时如何掩码、替换或加密。
- `COVER_ALL` 可能覆盖线上锁定标签，影响资产目录展示、审批规则和脱敏联动；生产环境必须二次确认。
