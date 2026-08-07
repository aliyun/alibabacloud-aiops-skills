# 验收标准 · create-unstructured-workflow

## 前置验收

- [ ] `aliyun version` >= 3.4.8
- [ ] `aliyun dataphin-public create-work-flow-by-json --help` 无报错（插件含 v6.2.0+ 命令集）
- [ ] `aliyun configure list` 显示有效 profile
- [ ] 目标项目为 BASIC 模式

## 流程验收（六步）

- [ ] Step 1：模态识别正确，格式兼容预检有结论（不兼容时给出转码/换链路建议）
- [ ] Step 2：设计稿完整（算子链 + 连线字段契约 + 数据集五不可变字段 + 表 schema + 提示词全文），且**已暂停等用户确认**
- [ ] Step 3：`list-datasets` 先搜索复用；新建时入参经用户确认；无论新建/复用均 `get-dataset` 回读成功
- [ ] Step 4：结构自检清单全过（id/hop 一致、字段契约、环境值无占位串、向量维度对齐）
- [ ] Step 5：默认 `TaskType=3 + Submit=false`；先 `--cli-dry-run`；用户确认后正式执行返回 `Code: OK` + `Data.PipelineId`
- [ ] Step 6：输出验证指引（界面回显 4 步 + 试跑 + 清理入口）

## 硬约束验收（违反即 bug）

- [ ] LLM/评分/去重类算子上游为 `xxx_url` 时已插入桥接（text_chunking 大 chunkSize / python_executor）
- [ ] 环境值全部来自 `get-dataset` 回读，无编造（含 modelId 来自实际环境）
- [ ] 提示词按业务语境定制，非跨场景照搬
- [ ] 所有写操作执行前已 HITL 确认；`delete-dataset` 逐次人工确认且先自查下游引用
- [ ] 大整数 ID 以字符串呈现
- [ ] 每个 `aliyun` API 命令带 `--user-agent AlibabaCloud-Agent-Skills/create-unstructured-workflow/{session-id}`（session-id 继承父层）
