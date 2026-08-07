# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（主题域生命周期）。

| 命令 | 用途 | 必填参数 |
|------|------|---------|
| `list-data-domains` | 查询主题域列表 | `--tenant-id` |
| `get-data-domain-info` | 获取主题域详情 | `--tenant-id`、`--data-domain-id` |
| `create-data-domain` | 创建主题域 | `--tenant-id`、`--biz-unit-id`、`--data-domain-name`、`--display-name`、`--abbreviation` |
| `update-data-domain` | 更新主题域 | `--tenant-id`、`--biz-unit-id`、`--data-domain-id`、`--data-domain-name`、`--display-name`、`--abbreviation` |
| `delete-data-domain` | 删除主题域（不可回滚） | `--tenant-id`、`--biz-unit-id`、`--data-domain-id` |

## 关键可选参数

| 命令 | 可选参数 | 说明 |
|------|---------|------|
| `list-data-domains` | `--biz-unit-id-list`、`--keyword`、`--parent-id-list` | 按数据板块 / 关键词（名称/编码/描述）/ 上级主题域过滤；均为 list 型，多值空格分隔 |
| `create-data-domain` | `--description`、`--parent-id` | 描述；上级主题域 ID（构建层级树） |
| `update-data-domain` | `--description`、`--parent-id` | 同上 |

## 前置依赖（数据板块 / BizUnit）

主题域挂在数据板块（业务单元 BizUnit）之下，`--biz-unit-id` 为硬前置。若尚无数据板块或不知其 ID：

- 数据板块创建/查询属于「数据规划」域能力，不在本 skill 编排范围内
- 本 skill 执行前需先确定目标 `--biz-unit-id`（询问用户或由上游 skill 传入）

## 字段映射（与产品页面对应）

| CLI 参数 | 页面字段 | 备注 |
|---|---|---|
| `--data-domain-name` | 主题域编码（英文名） | 唯一标识 |
| `--display-name` | 主题域名称（中文名/展示名） | — |
| `--abbreviation` | 缩写 | 逻辑表命名前缀拼接用 |
| `--parent-id` | 上级主题域 | 不传即顶级 |
| `--biz-unit-id` | 所属数据板块 | 归属容器 |
