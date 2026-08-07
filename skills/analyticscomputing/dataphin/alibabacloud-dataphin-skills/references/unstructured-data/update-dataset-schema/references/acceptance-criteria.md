# 验收标准 · update-dataset-schema

## 前置验收

- [ ] `aliyun version` >= 3.4.8；`aliyun dataphin-public update-dataset --help` 无报错
- [ ] `aliyun configure list` 显示有效 profile
- [ ] 目标数据集元数据存储为 POSTGRESQL（Milvus 不适用本流程）

## 流程验收（三段式）

- [ ] Step 1：回读拿到 MetadataStorageConfig（DataSourceId/ProdSchema/TableName/TableSchema）与 FileId；变更设计稿（现状 vs 目标列 diff + ALTER SQL + 完整新 TableSchema）经用户确认
- [ ] Step 1：已自查下游工作流引用（界面确认或用户求证）；删列/改类型逐条人工确认
- [ ] Step 2：`execute-ad-hoc-task`（DATABASE_SQL + data-source-id + data-source-schema）执行成功，`get-ad-hoc-task-log` 返回 `TaskStatus: SUCCESS`
- [ ] Step 3：`update-dataset` 携带**完整列清单**（回读原值 + 新列）返回 `Code: OK`
- [ ] Step 4：回读目标版本 TableSchema 与物理表逐列一致

## 硬约束验收（违反即 bug）

- [ ] 未尝试"在线编辑"表结构（不存在该入口）；顺序为先 DDL 后提交 schema
- [ ] update-dataset 提交的是完整列清单，非仅新增列
- [ ] 已被工作流引用的列未删未改（只加不减）
- [ ] 大整数 ID 以字符串呈现；写操作前 HITL 确认
- [ ] 每个 `aliyun` API 命令带 `--profile` 与 `--user-agent AlibabaCloud-Agent-Skills/update-dataset-schema/{session-id}`（session-id 继承父层）
