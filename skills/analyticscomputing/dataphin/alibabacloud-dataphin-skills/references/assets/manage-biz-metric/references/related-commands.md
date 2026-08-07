# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（业务指标定义 CRUD）。

| 命令 | 用途 | 必填参数 |
|------|------|---------|
| `create-biz-metric` | 创建业务指标定义 | `--tenant-id`、`--biz-metric-name` |
| `update-biz-metric` | 更新业务指标定义 | `--tenant-id`、`--biz-metric-name` |
| `get-biz-metric-by-name` | 按名称查询业务指标详情 | `--tenant-id`、`--biz-metric-name`、`--draft` |
| `delete-biz-metric` | 删除业务指标定义（不可回滚） | `--tenant-id`、`--biz-metric-name` |

## 关键可选参数

| 参数 | 适用命令 | 说明 |
|------|---------|------|
| `--display-name` | create/update | 展示名 |
| `--description` | create/update | 指标描述 |
| `--labels` | create/update | 资产标签列表，格式：`--labels value1 value2` |
| `--catalog-ids` | create/update | 归属目录 ID 列表，格式：`--catalog-ids value1 value2` |
| `--biz-owner-name` | create/update | 业务负责人账号用户名，非展示昵称 |
| `--metric-definition` | create/update | 指标口径；引用其他业务指标时用半角中括号包裹 |
| `--related-biz-metrics` | create/update | 相关业务指标列表 |
| `--associated-tech-metric-full-names` | create/update | 关联技术指标全名数组 |
| `--metric-relation-diagram-switch-open` | create/update | 指标关系图开关 |
| `--metric-relation-diagram-expression` | create/update | 指标关系图表达式 |
| `--operate-instruction-enabled` | create/update | 是否开启操作说明 |
| `--operate-instruction-content` | create/update | 操作说明内容 |
| `--view-scope` | create/update | 可见范围对象 |
| `--custom-attribute` | create/update | 自定义属性数组 |
| `--new-name` | update | 更新后的业务指标名称 |

## OpenAPI 字段映射

| CLI 参数 | API 参数名 | 备注 |
|---|---|---|
| `--biz-metric-name` | `CreateBizMetricCommand.Name` / `UpdateBizMetricCommand.Name` / `BizMetricByNameQuery.Name` / `DeleteBizMetricCommand.Name` | 租户内唯一；get/delete/update 均按名称定位 |
| `--display-name` | `DisplayName` | 展示名 |
| `--metric-definition` | `MetricDefinition` | 指标口径 |
| `--catalog-ids` | `CatalogIds` | 归属目录 ID 列表，CLI list 参数用空格分隔多个值 |
| `--biz-owner-name` | `BizOwnerName` | 负责人账号用户名 |
| `--related-biz-metrics` | `RelatedBizMetrics` | 相关业务指标列表，CLI list 参数用空格分隔多个值 |
| `--associated-tech-metric-full-names` | `AssociatedTechMetricFullNames` | 技术指标全名列表，CLI list 参数用空格分隔多个值 |
| `--draft` | `BizMetricByNameQuery.Draft` | `true` 查询草稿态，`false` 查询已发布态 |

## 指标口径与关系图规则

- `--metric-definition` 可填写业务口径文本或计算表达式。
- 引用其他业务指标时，指标名称必须用半角中括号 `[ ]` 包裹。
- 指标关系图表达式仅支持 `+`、`-`、`*`、`/`、`()`、`%`、`∑`。
- 开启 `--metric-relation-diagram-switch-open true` 前，至少需要配置一个 `--related-biz-metrics`，否则服务端可能自动关闭关系图。
- 一个技术指标只能被一个业务指标关联，不能重复关联。

## 能力边界

`dataphin-public` 当前只开放业务指标定义的 create/update/get/delete 命令，未开放 `list-biz-metrics`、`publish-biz-metric`、`online-biz-metric`、`offline-biz-metric`。业务指标发布/上架/下架属于资产上架管理链路，不得伪造不存在的 CLI 命令。

> [Agent 自主发现] 页面或内部资产上架接口中的 `metaBizIndex.metricDefinition`、`shelveDirectoryIds`、`saveAndOnShelve`、`shelveType` 等字段只用于理解业务流程，不可直接作为 OpenAPI CLI 参数。
