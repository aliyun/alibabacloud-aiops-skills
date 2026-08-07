# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（命令名以 `aliyun dataphin-public --help` 实际输出为准）。

## 核心命令

| 命令 | 用途 | 关键必填参数 |
|------|------|-------------|
| `create-standard` | 创建数据标准（METADATA / QUALITY） | `--tenant-id`、`--standard-template-reference`、`--standard-set-reference` |

## 配套查询 / 生命周期命令

| 命令 | 用途 | 关键必填参数 |
|------|------|-------------|
| `get-standard` | 获取标准详情（创建后验证） | `--tenant-id`、`--standard-id` |
| `list-standards` | 分页查询标准列表（注意复数） | `--tenant-id`、`--standard-stage`（DEV/PROD，隐藏必填） |
| `update-standard` | 更新已建标准的监控配置 | `--tenant-id`、`--standard-id`、`--standard-status` |
| `offline-standard` | 下线标准 | `--tenant-id`、`--standard-id` |
| `publish-standard` | 发布标准 | `--tenant-id`、`--standard-id` |

## 依赖的前置资源命令

| 命令 | 用途 |
|------|------|
| `create-standard-template` / `get-standard-template` | 标准模板（`--standard-template-reference` 的来源） |
| `create-standard-set` / `get-standard-set` | 标准集（`--standard-set-reference` 的来源） |

> 参数取值请以 `aliyun dataphin-public <cmd> --help` 为准。
