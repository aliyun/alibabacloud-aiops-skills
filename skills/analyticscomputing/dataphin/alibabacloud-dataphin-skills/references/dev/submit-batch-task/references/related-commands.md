# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public create-batch-task` | 创建离线任务文件，得 FileId（--env DEV） |
| `aliyun dataphin-public get-batch-task-info` | 读 TaskInfo.DagId 推导租户根节点 |
| `aliyun dataphin-public submit-batch-task` | 提交代码/调度/上游，得 NodeId + SubmitId |
| `aliyun dataphin-public publish-object-list` | 发布待发布记录上线运维区（submit 后必做） |
| `aliyun dataphin-public get-physical-node` | 验证节点上线（.NodeInfo，Status=normal） |
| `aliyun dataphin-public get-node-up-down-stream` | 验证上游（参数 --id，返回 .NodeDagInfo.UpStreamNodeList） |
| `aliyun dataphin-public get-physical-node-content` | 验证代码内容（.Data.CodeContent） |
| `aliyun dataphin-public list-submit-records` | 查询待发布记录 |
| `aliyun dataphin-public --help` | 查看全部命令 |
