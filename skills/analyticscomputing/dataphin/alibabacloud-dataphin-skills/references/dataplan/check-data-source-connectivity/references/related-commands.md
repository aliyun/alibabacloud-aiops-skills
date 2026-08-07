# 相关命令

> 本 skill 涉及的 `aliyun dataphin-public` 命令清单。

| 命令 | 用途 |
|------|------|
| `aliyun dataphin-public check-data-source-connectivity --type <T> --config-item-list '{...}' ...` | 按 Type + ConfigItemList 探测连通性（不创建数据源） |
| `aliyun dataphin-public check-data-source-connectivity-by-id --data-source-id <N>` | 对已存在的数据源按 ID 探测连通性 |
| `aliyun dataphin-public check-data-source-connectivity --help` | 查看参数详情 |

## 上下游相关命令

| 命令 | 关系 |
|------|------|
| `aliyun dataphin-public create-data-source` | Check 通过后再建源，见同套件子 skill `create-data-source`（经套件入口路由加载） |
| `aliyun dataphin-public list-data-source-with-config` | 列出现有数据源及 ConfigItemList，可获取 `check-data-source-connectivity-by-id` 所需的数据源 ID |
| `aliyun dataphin-public update-data-source-config` | 探测失败修正配置后更新已建数据源 |
