# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单（命令名以 `aliyun dataphin-public --help` 实际输出为准）。

## 核心命令

| 命令 | 用途 | 关键必填参数 |
|------|------|-------------|
| `update-standard` | 更新数据标准（METADATA / QUALITY） | `--tenant-id`、`--standard-id`、`--standard-status`、`--standard-template-reference`、`--standard-set-reference` |

## 配套查询 / 生命周期命令

| 命令 | 用途 | 关键必填参数 |
|------|------|-------------|
| `get-standard` | 更新前拉全量配置、更新后验证 | `--tenant-id`、`--standard-id` |
| `list-standards` | 分页查询标准列表（注意复数），定位 `--standard-id` | `--tenant-id`、`--standard-stage`（DEV/PROD，隐藏必填） |
| `create-standard` | 新建标准 | `--tenant-id`、`--standard-template-reference`、`--standard-set-reference` |
| `offline-standard` | 下线标准 | `--tenant-id`、`--standard-id`、`--comment` |
| `publish-standard` | 发布标准 | `--tenant-id`、`--standard-id` |

## 依赖的前置资源命令

| 命令 | 用途 |
|------|------|
| `get-standard-template` | 校验 `--standard-template-reference` 引用的模板 |
| `get-standard-set` | 校验 `--standard-set-reference` 引用的标准集 |

> 参数取值请以 `aliyun dataphin-public <cmd> --help` 为准。
