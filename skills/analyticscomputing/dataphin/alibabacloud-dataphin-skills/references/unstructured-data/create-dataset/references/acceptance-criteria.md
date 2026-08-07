# 验收标准 · create-dataset

## 前置验收

- [ ] `aliyun version` >= 3.4.8
- [ ] `aliyun dataphin-public create-dataset --help` 无报错（插件含 v6.2.0+ 命令集）
- [ ] `aliyun configure list` 显示有效 profile

## 流程验收

- [ ] Step 1：设计稿（名称 + 五个不可变字段 + 表 schema）已产出并经用户确认
- [ ] Step 2：`list-datasets` 查重完成（命中一致配置则复用，不重复建）
- [ ] Step 3：`create-dataset` 先 `--cli-dry-run`，HITL 确认后正式执行返回 `Code: OK` + `DatasetId`
- [ ] Step 4：`get-dataset` 回读，五字段/VersionList/TableSchema 与设计稿逐项一致
- [ ] （按需）`update-dataset` 携带回读的 `FileId`，`Success=true` 后再次回读核对

## 硬约束验收（违反即 bug）

- [ ] 五个不可变字段一次定型，未在 UpdateCommand 中尝试修改
- [ ] 表名匹配 `^[a-z][a-z0-9_]{0,63}$`；Milvus 时主键(INT64/VARCHAR)+向量字段齐备
- [ ] 向量列 Dimension 与下游 Embedding 算子 vectorDimension 一致；URL 语义列带 `Url:true`
- [ ] `delete-dataset` 前已自查下游引用且逐次人工确认
- [ ] 大整数 ID 以字符串呈现
- [ ] 每个 `aliyun` API 命令带 `--user-agent AlibabaCloud-Agent-Skills/create-dataset/{session-id}`（session-id 继承父层）
