# 相关命令索引 · update-dataset-schema

| 命令 | 用途 | 类型 |
|------|------|------|
| `list-datasets` | 定位数据集 + 回读版本表结构/元数据源/FileId（`--include-version-list true`） | 读 |
| `get-dataset` | 回读单数据集详情（NoPermission 时用 list-datasets 兜底） | 读 |
| `execute-ad-hoc-task` | DATABASE_SQL 直连元数据 PG 执行 ALTER DDL | 写（高危） |
| `get-ad-hoc-task-log` | 确认 DDL 执行 `TaskStatus: SUCCESS` | 读 |
| `get-ad-hoc-task-result` | 反查 information_schema 确认列生效 | 读 |
| `update-dataset` | 重新提交完整 TableSchema（等价界面"重新加载表结构"；`--id/--file-id` 必填） | 写 |

## 命令速查（插件 >= 0.7.0 展平参数格式；以 --help 为准）

```bash
# 1. 回读现状
aliyun dataphin-public list-datasets --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --keyword "<数据集名>" --include-version-list true --page 1 --page-size 10

# 2. 执行 ALTER（HITL 确认后；data-source-id/schema 用回读的 MetadataStorageConfig 值）
aliyun dataphin-public execute-ad-hoc-task --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --operator-type DATABASE_SQL --data-source-id "<元数据源ID>" --data-source-schema "<schema>" \
  --code "ALTER TABLE <表名> ADD COLUMN <列名> <类型>;"

# 3. 确认 DDL 成功（sub-task-id 从 0 开始）
aliyun dataphin-public get-ad-hoc-task-log --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --task-id "<TaskId>" --sub-task-id 0 --offset 0

# 4. 重新提交完整表结构（TableSchema = 回读原值 + 新列，与物理表一致）
aliyun dataphin-public update-dataset --op-tenant-id "$TENANT_ID" --project-id "$PROJECT_ID" \
  --id "<DatasetId>" --file-id "<FileId>" --version "<版本>" \
  --version-config "$(cat version-config-updated.json)"

# 5. 回读验证（同步骤 1，核对列清单）
```

> 所有 API 命令实际执行时必须追加 `--profile <有效 profile 名>`（认证统一走阿里云 CLI 配置）与 `--user-agent AlibabaCloud-Agent-Skills/update-dataset-schema/{session-id}`（session-id 继承父 skill）。
