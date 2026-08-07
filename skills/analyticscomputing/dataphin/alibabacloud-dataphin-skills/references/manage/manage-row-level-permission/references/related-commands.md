# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（行级权限管理）。

| 命令 | 用途 | 必填参数 |
|------|------|---------|
| `create-row-permission` | 创建行级权限 | `--tenant-id`、`--row-permission-name`、`--mapping-columns` |
| `update-row-permission` | 更新行级权限 | `--tenant-id`、`--row-permission-id`、`--row-permission-name`、`--mapping-columns` |
| `delete-row-permission` | 删除行级权限（不可回滚） | `--tenant-id`、`--row-permission-id` |
| `list-row-permission` | 分页查询行级权限 | `--tenant-id`、`--page-num`、`--page-size` |
| `get-row-permission-by-table-guids` | 按表 GUID 查询行级权限 | `--tenant-id`、`--table-guids` |
| `get-account-by-row-permission-id` | 查询某行级权限规则下授权账号 | `--tenant-id`、`--row-permission-id`、`--rule-ids` |
| `list-row-permission-by-user-id` | 查询指定用户行级权限 | `--tenant-id`、`--operator`、`--page-num`、`--page-size` |

## 参数格式

| 参数 | 类型 | 格式 |
|------|------|------|
| `--mapping-columns` | list(object) | 每个数组元素单独传一个 JSON 对象字符串，如 `--mapping-columns '{"ColumnName":"id","ColumnType":"NUMBER","ColumnId":"col1"}'` |
| `--rules` | list(object) | 每个规则单独传一个 JSON 对象字符串 |
| `--tables` | list(object) | 每个关联表单独传一个 JSON 对象字符串 |
| `--table-guids` | list(string) | CLI 原生 list 格式：`--table-guids guid1 guid2` |
| `--rule-ids` | list(number/string) | CLI 原生 list 格式：`--rule-ids 1001 1002` |

## OpenAPI 字段映射

| CLI 参数 | API 参数名 | 备注 |
|---|---|---|
| `--row-permission-name` | `RowPermissionName` | 行级权限名称 |
| `--row-permission-desc` | `RowPermissionDesc` | 行级权限描述 |
| `--row-permission-id` | `RowPermissionId` | create 不返回，需要 list 反查 |
| `--mapping-columns` | `MappingColumns` | 映射/管控字段列表 |
| `--rules` | `Rules` | 规则列表，包含 ScopeType / Expressions / UserMappingList |
| `--tables` | `Tables` | 关联表资源列表，需包含表、项目、数据源、业务板块等元数据 |
| `--table-guids` | `TableGuids` | 表 GUID 列表 |
| `--rule-ids` | `RuleIds` | 规则 ID 列表 |
| `--operator` | `Operator` | 指定用户/操作人 |

## 常见结构

### MappingColumns

```json
{
  "ColumnName": "id",
  "ColumnType": "NUMBER",
  "ColumnDesc": "",
  "ColumnId": "<column-id>"
}
```

### Rule（全部列）

```json
{
  "RuleName": "all",
  "ScopeType": "ALL_COLUMN",
  "Expressions": [],
  "UserMappingList": [],
  "Status": 1,
  "IsDelete": false
}
```

### Rule（按字段值过滤）

```json
{
  "RuleName": "east_region",
  "ScopeType": "SELECT_COLUMN",
  "Expressions": [
    {
      "Parent": "null",
      "Type": "RELATION",
      "Operator": "OR",
      "SubConditions": [
        {
          "Type": "EXPRESSION",
          "SubConditions": [],
          "ColumnId": "<column-id>",
          "Parent": "-999",
          "Operator": "IN",
          "Values": ["华东", "华南"]
        }
      ]
    }
  ],
  "UserMappingList": [],
  "Status": 1,
  "IsDelete": false
}
```

## 生命周期注意事项

- `create-row-permission` 返回成功布尔值，不返回 `rowPermissionId`，必须 `list-row-permission --keyword` 反查。
- `update-row-permission` 是覆盖式更新，需完整回填 `MappingColumns`、`Rules`、`Tables`。
- 行级权限申请/审批/运行时过滤不是本 7 个 OpenAPI 命令直接完成，需另走授权申请链路。
- 页面内部接口是 camelCase 字段，OpenAPI JSON 对象建议使用 PascalCase 字段。
