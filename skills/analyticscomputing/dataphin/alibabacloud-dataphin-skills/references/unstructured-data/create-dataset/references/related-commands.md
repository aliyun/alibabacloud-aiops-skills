# 相关命令索引 · create-dataset

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` | 按关键词/类型/场景分页查询（查重复用；`IncludeVersionList=true` 带版本详情） | 读 |
| `create-dataset` | 创建数据集（CreateCommand 含 VersionConfig / TableSchema） | 写 |
| `get-dataset` | 回读 DatasetDTO + 完整 VersionList（验证 + 下游环境值来源） | 读 |
| `update-dataset` | 更新数据集（UpdateCommand.Id 与 FileId 必填） | 写 |
| `delete-dataset` | 删除数据集（高危：无回收站、不自查下游引用） | 写 |

## 命令速查（插件 >= 0.7.0 展平参数格式；旧版嵌套参数在新插件下被静默忽略，以 --help 为准）

```bash
# 查重 / 搜索
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<关键词>" --include-version-list true --page 1 --page-size 10

# 创建（VersionConfig 骨架见 dataset-parameters.md §四；先 --cli-dry-run，HITL 确认后正式执行；一次仅建 1 个版本）
aliyun dataphin-public create-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --name "<名>" --type HYBRID --content-type TEXT --dir-name / --scenario OFFLINE \
  --storage-type OSS --metadata-storage-type POSTGRESQL --version V1 \
  --version-config "$(cat version-config-v1.json)"

# 回读验证（若报 DPN.Filter.NoPermission，用上方 list-datasets 兜底）
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>"

# 更新/追加版本（--id/--file-id 必填，FileId 从回读取）
aliyun dataphin-public update-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --id "<DatasetId>" --file-id "<FileId>" --version V2 --version-config "$(cat version-config-v2.json)"

# 删除（高危，逐次人工确认）
aliyun dataphin-public delete-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>"
```

> 所有 API 命令实际执行时必须追加 `--profile <有效 profile 名>`（认证信息统一来自阿里云 CLI 配置）与 `--user-agent AlibabaCloud-Agent-Skills/create-dataset/{session-id}`（session-id 继承父 skill）。
> 注意：`create-dataset`/`update-dataset` 的 `--project-id` 是 String；`get-dataset`/`delete-dataset` 是 Long；`list-datasets` 的 ProjectId 在 body 内。
