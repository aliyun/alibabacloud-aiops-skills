# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-pipeline-by-id` | 回读管道任务完整配置（pipeline-id / file-id / node-id 三选一） | 读 |
| `list-files` | 只知道任务名时按名称反查 fileId | 读 |
| `update-pipeline` | 全量回写管道配置并提交（同步） | 写 |
| `update-pipeline-by-async` | 异步更新管道配置（配置体量大 / 同步超时时） | 写 |
| `get-pipeline-async-result` | 查询异步更新执行结果 | 读 |
