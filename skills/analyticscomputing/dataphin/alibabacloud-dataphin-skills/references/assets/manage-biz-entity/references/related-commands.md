# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（业务实体生命周期）。

| 命令 | 用途 | 必填参数 |
|------|------|---------|
| `list-biz-entities` | 查询业务实体列表 | `--tenant-id` |
| `get-biz-entity-info` | 获取业务实体详情 | `--tenant-id`、`--type`、`--biz-entity-id` |
| `get-biz-entity-info-by-version` | 查询指定版本详情 | `--tenant-id`、`--type`、`--biz-entity-id`、`--version-id` |
| `create-biz-entity` | 创建业务实体 | `--tenant-id`、`--biz-unit-id`、`--data-domain-id`、`--type`、按类型传 `--biz-object` 或 `--biz-process` |
| `update-biz-entity` | 更新业务实体 | `--tenant-id`、`--biz-unit-id`、`--data-domain-id`、`--biz-entity-id`、`--type`、按类型传 `--biz-object` 或 `--biz-process` |
| `online-biz-entity` | 上线业务实体 | `--tenant-id`、`--biz-unit-id`、`--biz-entity-id`、`--type`、`--comment` |
| `offline-biz-entity` | 下线业务实体 | `--tenant-id`、`--biz-unit-id`、`--biz-entity-id`、`--type`、`--comment` |
| `delete-biz-entity` | 删除业务实体（不可回滚） | `--tenant-id`、`--biz-unit-id`、`--biz-entity-id`、`--type` |

## 关键可选参数

| 命令 | 可选参数 | 说明 |
|------|---------|------|
| `list-biz-entities` | `--keyword`、`--page`、`--page-size`、`--filter-criteria` | 按关键字、分页、过滤条件查询；`--filter-criteria` 支持 BizUnit/DataDomain/SubType/Owner/Status 等过滤 |
| `create-biz-entity` | `--biz-object` / `--biz-process` 内的 `Description`、`OwnerUserId`、关联列表 | 创建业务对象或业务活动的业务字段 |
| `update-biz-entity` | `--biz-object` / `--biz-process` 内的关联列表 | update 会清空未回填的 `RefBizEntityIdList`，更新前必须回读现值 |

## 前置依赖（数据板块 / 主题域）

业务实体同时归属数据板块（BizUnit）与主题域（DataDomain）：

- `--biz-unit-id`：所属数据板块，create/update/online/offline/delete 必带
- `--data-domain-id`：所属主题域，create/update 必带
- 若不知道主题域 ID，可先使用 `manage-topic-domain` 的 `list-data-domains` / `get-data-domain-info` 反查

## 类型分支

| 大类 `--type` | JSON 参数 | 细分类型字段 | 适用场景 |
|---|---|---|---|
| `BIZ_OBJECT` | `--biz-object` | `Type=NORMAL / ENUM / VIRTUAL / HIERARCHY` | 客户、商品、门店等对象类实体，支撑维度建模 |
| `BIZ_PROCESS` | `--biz-process` | `Type=BIZ_EVENT / BIZ_SNAPSHOT / BIZ_PROCESS` | 下单、支付、发货等活动类实体，支撑事实建模和指标建模 |

## OpenAPI JSON 字段映射

| OpenAPI 字段 | 页面/业务字段 | 备注 |
|---|---|---|
| `Name` | 编码 / 英文名 | 64 字符以内，仅允许字母、数字、下划线 |
| `DisplayName` | 展示名 / 中文名 | 64 字符以内，允许汉字、字母、数字、下划线、中划线 |
| `Description` | 描述 | 128 字符以内 |
| `OwnerUserId` | 负责人用户 ID | 传用户 ID，非花名 |
| `Type` | 细分类型 | 在 `BizObject` 与 `BizProcess` 内含义不同，见上表 |
| `ParentId` | 继承实体 | 仅普通业务对象支持，且只能继承已上线业务对象 |
| `RefBizEntityIdList` | 关联业务实体 | 仅允许关联已上线业务实体；update 不传会清空原值 |
| `BizEventEntityIdList` | 流程包含的业务事件 | 仅 `BizProcess.Type=BIZ_PROCESS` 时使用 |
| `PreBizProcessIdList` | 前序业务流程 | 仅 `BizProcess.Type=BIZ_PROCESS` 时使用 |

## 过滤条件示例

```json
{
  "BizUnitIdList": ["<biz-unit-id>"],
  "DataDomainIdList": ["<data-domain-id>"],
  "SubTypeList": ["NORMAL", "BIZ_EVENT"],
  "OwnerUserIdList": ["<owner-user-id>"],
  "HasTableRef": false
}
```

> [Agent 自主发现] 不要把页面内部 REST 字段直接用于 OpenAPI。OpenAPI 使用 `DisplayName` / `OwnerUserId` / `Type=NORMAL`，而不是内部接口中的 `cn` / `owner` / `bizObjectType=1`。
