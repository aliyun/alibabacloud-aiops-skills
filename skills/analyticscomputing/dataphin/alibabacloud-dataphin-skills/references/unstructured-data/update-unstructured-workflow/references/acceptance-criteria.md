# 验收标准 · update-unstructured-workflow

## 前置验收

- [ ] `aliyun version` >= 3.4.8
- [ ] `aliyun dataphin-public update-pipeline --help` 显示展平参数（`--node-info` / `--pipeline-config` / `--schedule-config`）
- [ ] `aliyun configure list` 显示有效 profile
- [ ] 目标工作流所属项目为 BASIC 模式

## 流程验收（五步 + 验证）

- [ ] Step 1：定位键（PipelineId/FileId/NodeId）来自用户或创建回执，未猜测
- [ ] Step 2：`get-pipeline-by-id` 回读成功，基线 JSON 已落盘保存
- [ ] Step 3：变更设计稿（diff 摘要 + 风险提示）输出完整，且**已暂停等用户确认**
- [ ] Step 4：就地最小 diff 编辑；更新自检清单全过（stepId 未变 / hop 无悬空 / 字段契约 / 环境值成组）
- [ ] Step 5：默认 `--submit false`；先 `--cli-dry-run`；用户确认后正式执行返回 `Code: OK`
- [ ] Step 6：回读 diff 确认变更生效且未变更部分与基线一致；输出界面回显指引

## 硬约束验收（违反即 bug）

- [ ] 修改建立在回读结果之上（禁止凭记忆重建 JSON）；未变更 step/hop 原样回传
- [ ] 已有 step 的 `id` / `pluginConfig.stepId` 未被改动；删 step 时关联 hops 已清理
- [ ] 切数据集版本时环境值成组替换且来自 `get-dataset` 回读
- [ ] `--schedule-config` 不改调度时原样回传回读值，未自行构造
- [ ] 基线 JSON 保留至验证完成（唯一回滚手段）
- [ ] 所有写操作执行前已 HITL 确认
- [ ] 大整数 ID 以字符串呈现
- [ ] 每个 `aliyun` API 命令带 `--user-agent AlibabaCloud-Agent-Skills/update-unstructured-workflow/{session-id}`（session-id 继承父层）
