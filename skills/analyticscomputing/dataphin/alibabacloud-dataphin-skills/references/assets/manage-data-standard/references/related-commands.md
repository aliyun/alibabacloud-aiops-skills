# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（数据标准生命周期）。

| 命令 | 用途 | 必填参数 |
|------|------|---------|
| `list-standards` | 分页查询标准列表 | `--tenant-id`、`--standard-stage`（DEV/PROD） |
| `get-standard` | 获取标准详情 | `--tenant-id`、`--standard-id` |
| `create-standard` | 创建数据标准 | `--tenant-id`、`--standard-set-reference`、`--standard-template-reference` |
| `update-standard` | 更新（修订）标准 | `--tenant-id`、`--standard-id`、`--standard-set-reference`、`--standard-template-reference`、`--standard-status` |
| `publish-standard` | 提交审批并发布 | `--tenant-id`、`--standard-id`、`--comment` |
| `offline-standard` | 下线标准 | `--tenant-id`、`--standard-id`、`--comment` |
| `delete-standard` | 删除标准（不可回滚） | `--tenant-id`、`--standard-id` |

## 关键可选参数

| 命令 | 可选参数 | 说明 |
|------|---------|------|
| `list-standards` | `--keyword`、`--page-no`、`--page-size`、`--standard-set-id-list`、`--standard-status-list`、`--standard-template-id-list`、`--standard-type-list` | 关键字/分页/多维过滤 |
| `get-standard` | `--need-relation`、`--nullable`、`--standard-stage`、`--version` | 是否返回关联标准/码表、指定阶段与版本 |
| `create-standard` / `update-standard` | `--description`、`--effective-time-config`、`--need-generate-standard-code`、`--owner`、`--standard-general-monitor-config` | 描述、生效时间、编码规则、负责人、监控配置 |
| `publish-standard` | `--auto-publish-after-approval`（默认 true）、`--reviewer-id-list`、`--standard-stage`、`--version` | 审批与发布控制 |

## 扩展命令（同域，本 skill 未直接编排）

- `standard-set` 系列：`create-standard-set` / `update-standard-set` / `get-standard-set` / `delete-standard-set`
- `standard-template` 系列：`create-standard-template` / `update-standard-template` / `get-standard-template`
- `standard-lookup-table`（码表）、`standard-word-root`（词根）、`standard-mapping`（映射）、`standard-relations`（关联关系）
- `get-standard-statistics` — 按标准类型统计目录下标准数目

## create-standard 入参结构（实测要点，勿踩坑）

创建标准时，属性值用【扁平结构】承载，**不是**嵌套的 `AttributeWithValueList[].{Attribute, Value}`（用嵌套会被服务端拒绝并只回笼统 `DPN.Commons.InternalError`，易误判为服务端故障）。正确写法：

```bash
aliyun dataphin-public create-standard --tenant-id <租户> \
  --standard-set-reference '{"Id":<标准集ID>}' \
  --standard-template-reference '{"Id":<模板ID>,"Version":1,"AttributeValueList":[
     {"AttributeId":<属性Id>,"Value":"<值>"}, ... ]}' \
  --effective-time-config '{"Type":"FOREVER"}' \
  --owner <负责人ID>
```

关键要点：
- `--standard-set-reference` / `--standard-template-reference` 均用 **`{"Id":...}`**（非 `StandardSetId`）。
- 属性值：`AttributeValueList` 元素**仅 `{AttributeId, Value}`**；服务端忽略元素内的 `ValueConfig`/`ConstraintType` 等其他字段。
- **`--effective-time-config` 必传**（如 `{"Type":"FOREVER"}`），缺失即失败。
- 属性 `AttributeId` 从 `get-standard-template` 取，且**必须加 `--nullable=false`**，否则该读命令默认路径也报 `InternalError`（服务端 bug）。
- 需填齐模板的**全部必填属性**（`Required=true`），否则报对应属性「值为空」。
- ⚠ **RANGE 类型属性（如「值域」）无法经 OpenAPI 创建**（已实测定性）：其约束类型（LIST/MIN_MAX/CUSTOMIZED）是**纯实例级、`constraintChangeable=true`**，只有内部 web API 的嵌套结构 `attribute.valueConfig.valueRange.valueConstraint` 能承载；OpenAPI 扁平 `AttributeValueList` 元素只有 `{AttributeId, Value}` 无此字段，服务端会报 `RequiredAttributeNotFoundConstraintType / 未指定范围值类型`。且**模板层无法固化** range 约束（`update-standard-template` 设 LIST 后被服务端重置回 NONE）。若模板含 RANGE 必填属性，唯一可行做法是用 `update-standard-template` 把该属性改为 `Required=false`（或换一个无 RANGE 必填的模板），create 无需传 range 即可跑通。

## 完整生命周期（已实测跑通）

`create-standard`（DRAFT/DEV）→ `publish-standard --comment ... --auto-publish-after-approval true`（转 PROD/ACTIVE）→ `offline-standard --comment ...`（回 DEV/DRAFT）→ `delete-standard`（删净）。查询状态用 `get-standard --standard-id <id> --standard-stage DEV|PROD --nullable=false`。

⚠ `update-standard-template` 坑：`get-standard-template` 返回的属性 `valueLength` 常为 `null`，但 update 要求**非空**（否则报 `valueLength cannot be null`），原样回写会失败，需先给每个属性补默认值（如 STRING 属性 256、RANGE 属性 -1）；且 update 后模板版本号自增、无法回退。
