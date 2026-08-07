# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（标准落标映射）。

| 命令 | 用途 | 必填参数 | 读/写 |
|------|------|---------|------|
| `get-asset-mapping-relations` | 按资产查映射关系 | `--tenant-id`、`--guid`、`--asset-type`（COLUMN/INDEX）、`--relation-type`（VALID/INVALID） | 读 |
| `get-belong-asset-mapping` | 按归属资产（表）查映射 | `--tenant-id`、`--belong-guid` | 读 |
| `create-standard-mapping` | 批量创建映射（有效/无效） | `--tenant-id`、`--standard-id`、`--asset-guid-list` | 写 |
| `update-standard-mapping-to-invalid` | 映射置为无效 | `--tenant-id`、`--standard-id` | 写 |
| `delete-standard-valid-mapping` | 删除有效映射 | `--tenant-id`、`--standard-id` | 写 |
| `delete-standard-invalid-mapping` | 删除无效映射 | `--tenant-id`、`--standard-id` | 写 |

## 关键可选参数

| 命令 | 可选参数 | 说明 |
|------|---------|------|
| `create-standard-mapping` | `--relation-type`（默认 VALID）、`--invalid-mapping-relation-operation-type`（默认 SET_INVALID_TO_VALID） | 映射类型、无效映射冲突策略（SET_INVALID_TO_VALID 转有效 / KEEP_INVALID_AND_SKIP 跳过） |
| `get-belong-asset-mapping` | `--relation-type` | 不传则不按类型过滤 |
| `update-standard-mapping-to-invalid` / `delete-standard-*-mapping` | `--guid-list`、`--belong-guid-list` | 按资产 GUID 或归属资产 GUID 圈范围，单次上限各 1000 |

## 响应结构要点（api-meta 2023-06-30 实测）

- `create-standard-mapping` → `Data.SuccessCount`（int64）+ `Data.FailedGuidList[]`（失败资产 GUID）
- `get-asset-mapping-relations` → `MappingRelationList[]`：`Guid` / `Name` / `AssetType`（COLUMN/INDEX）/ `StandardId` / `StandardName` / `StandardCode` / `StandardSetId` / `StandardSetName` / `StandardSetDirectory` / `ModifyTime`

## 扩展命令（同域，本 skill 未直接编排）

- `create-standard-relations` / `delete-standard-relations`（标准与标准之间的关联关系，非落标映射）
- `list-standards` / `get-standard` / `publish-standard`（标准生命周期，见 `manage-data-standard` skill）
