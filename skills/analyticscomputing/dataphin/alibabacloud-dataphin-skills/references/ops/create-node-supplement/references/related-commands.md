# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public list-nodes` | 查询节点元数据（必须传 `--node-biz-type` / `--node-sub-biz-type-list` / `--schedule-type`） |
| `aliyun dataphin-public create-node-supplement` | 发起节点补数据 |
| `aliyun dataphin-public get-operation-submit-status` | 海量模式下由 jobId 取真正 SupplementId（`ExternalBizId`） |
| `aliyun dataphin-public get-supplement-dagrun` | 查询补数据 dagrun 列表（按业务日期） |
| `aliyun dataphin-public get-supplement-dagrun-instance` | 查询 dagrun 下各节点实例状态 |
| `aliyun dataphin-public list-node-down-stream` | 创建前查询下游节点做参考 |
| `aliyun dataphin-public --help` | 查看全部命令 |
