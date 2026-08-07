# 相关命令索引 · create-unstructured-workflow

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` | 按关键词搜索数据集（复用判定；`IncludeVersionList=true` 带版本详情） | 读 |
| `create-dataset` | 创建数据集（表 schema 按链路末端算子输出设计） | 写 |
| `get-dataset` | 回读 DatasetDTO + VersionList（工作流环境值唯一来源） | 读 |
| `update-dataset` | 更新数据集（`FileId` 必填，先 get-dataset 回读取） | 写 |
| `create-work-flow-by-json` | JSON 脚本模式创建非结构化工作流（仅 BASIC 项目，Env=PROD） | 写 |
| `delete-dataset` | 删除测试数据集（高危：先自查下游引用，逐次人工确认） | 写 |

## 命令速查（插件 >= 0.7.0 展平参数格式；旧版嵌套参数在新插件下被静默忽略，以 --help 为准）

```bash
# 搜索数据集
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<关键词>" --include-version-list true --page 1 --page-size 10

# 创建数据集（VersionConfig 骨架见 dataset-parameters.md；一次仅建 1 个版本，V2+ 用 update-dataset 追加）
aliyun dataphin-public create-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --name "<名>" --type HYBRID --content-type TEXT --dir-name / --scenario OFFLINE \
  --storage-type OSS --metadata-storage-type POSTGRESQL --version V1 \
  --version-config "$(cat version-config-v1.json)"

# 回读数据集（若报 DPN.Filter.NoPermission，用上方 list-datasets 兜底）
aliyun dataphin-public get-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>"

# 创建工作流（WorkFlowJson 规范见 workflow-json-spec.md；先 --cli-dry-run；--directory 仅传已存在目录）
aliyun dataphin-public create-work-flow-by-json --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --env PROD --task-name "<名>" --task-type 3 --submit false \
  --work-flow-json "$(jq -c . workflow.json)"

# 删除数据集（高危）
aliyun dataphin-public delete-dataset --op-tenant-id "$TENANT_ID" \
  --project-id "$PROJECT_ID" --id "<DatasetId>"
```

> 所有 API 命令实际执行时必须追加 `--profile <有效 profile 名>`（认证信息统一来自阿里云 CLI 配置）与 `--user-agent AlibabaCloud-Agent-Skills/create-unstructured-workflow/{session-id}`（session-id 继承父 skill）。
