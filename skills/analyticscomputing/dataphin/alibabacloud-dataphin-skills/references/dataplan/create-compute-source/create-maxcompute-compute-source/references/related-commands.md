# 相关命令索引

## create-maxcompute-compute-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `check-compute-source-connectivity` | 创建前预检连通性（传 `--type` + `--config-list`） | 读 |
| `create-compute-source` | 创建计算源（扁平 flag，CLI 序列化为 CreateCommand） | 写 |
| `list-compute-sources` | 按类型/关键字查询计算源列表（**命令名为复数**） | 读 |
| `get-compute-source` | 按 `--compute-source-id` 查询计算源详情（不回显 ConfigList） | 读 |
| `check-compute-source-connectivity-by-id` | 按已有计算源 Id 校验连通性 | 读 |
| `delete-compute-source` | 按 `--compute-source-id` 删除计算源 | 写 |

## 关键参数速查（实测自 `aliyun dataphin-public <cmd> --help`）

| 命令 | 必填参数 |
|------|----------|
| `create-compute-source` | `--op-tenant-id` `--compute-source-name` `--type` `--config-list`（`--description` 可选） |
| `check-compute-source-connectivity` | `--op-tenant-id` `--type` `--config-list` |
| `list-compute-sources` | `--op-tenant-id`（`--type` `--keyword` `--page-no` `--page-size` `--bind-project` 可选） |
| `get-compute-source` | `--op-tenant-id` `--compute-source-id` |
| `check-compute-source-connectivity-by-id` | `--op-tenant-id` `--compute-source-id` |
| `delete-compute-source` | `--op-tenant-id` `--compute-source-id` |

> 注：`--op-tenant-id` 亦可写 `--tenant-id`（别名）；profile 已配置时可省略。
# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public --help` | 查看全部命令 |

> TODO: 根据 skill 实际流程补充具体命令。
