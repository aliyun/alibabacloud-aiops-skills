# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（数据标准码表生命周期）。

| 命令 | 用途 | 必填参数 | 读/写 |
|------|------|---------|------|
| `create-standard-lookup-table` | 创建码表 | `--tenant-id`、`--standard-lookup-table-name`、`--code` | 写 |
| `get-standard-lookup-table` | 查询码表详情 | `--tenant-id`、`--standard-lookup-table-id` | 读 |
| `update-standard-lookup-table` | 更新码表（码值整体覆盖） | `--tenant-id`、`--id`、`--standard-lookup-table-name`、`--code` | 写 |
| `delete-standard-lookup-table` | 删除码表（不可回滚） | `--tenant-id`、`--standard-lookup-table-id` | 写 |

## 关键可选参数

| 命令 | 可选参数 | 说明 |
|------|---------|------|
| `create-standard-lookup-table` / `update-standard-lookup-table` | `--description`、`--directory-reference`、`--lookup-table-value-list`、`--owner` | 描述、归属目录、码值列表、负责人 |
| `get-standard-lookup-table` | `--nullable`（默认 true） | false 时码表不存在抛异常，便于程序化判断 |

## 复杂参数结构（api-meta 2023-06-30 实测）

- `--lookup-table-value-list` 元素（每个元素一个 JSON 对象，多个空格分隔）：
  `{"Value":"杭州","Name":"Hangzhou","EnglishName":"HZ","Description":"..."}`
  - `Value`（必填，码表内唯一，≤64 字符）、`Name`（必填，≤64 字符）、`EnglishName` / `Description` 可选
- `--directory-reference`：`{"Directory":"/dir1/dir2"}`（目录路径，`/` 分隔多级）
- `create` 响应 `Data` = 码表 Id（int64，按字符串记录）

## 扩展命令（同域，本 skill 未直接编排）

- `standard-word-root` 系列：`create-standard-word-root` / `get-standard-word-root` / `update-standard-word-root` / `delete-standard-word-root`（词根）
- 标准侧引用：`get-standard --need-relation true` 可返回标准关联的码表
