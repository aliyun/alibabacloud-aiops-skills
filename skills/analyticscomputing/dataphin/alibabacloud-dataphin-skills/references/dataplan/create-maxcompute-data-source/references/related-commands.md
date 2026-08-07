# 相关命令索引

## create-maxcompute-data-source

| 命令 | 用途 | 类型 |
|------|------|------|
| `check-data-source-connectivity` | 创建前预检连通性（传 Type + ConfigItemList） | 读 |
| `create-data-source` | 创建数据源（MaxCompute 类型） | 写 |
| `list-data-source-with-config` | 按类型/名称搜索数据源（含配置项） | 读 |
| `check-data-source-connectivity-by-id` | 按已有数据源 ID 检查连通性 | 读 |
| `delete-data-source` | 删除数据源（支持 DEV / DEV_PROD 模式） | 写 |
| `update-data-source-basic-info` | 编辑数据源基本信息（名称/描述） | 写 |
| `update-data-source-config` | 编辑数据源连接配置项 | 写 |
| `get-data-source-dependencies` | 查询数据源变更影响的任务 | 读 |

### MaxCompute ConfigItemList 配置项

| Key | 必填 | 说明 |
|-----|------|------|
| `maxcompute.endpoint` | 是 | MaxCompute 服务 Endpoint（如 `http://service.cn-hangzhou.maxcompute.aliyun.com/api`） |
| `maxcompute.project` | 是 | MaxCompute 项目名称 |
| `maxcompute.access.id` | 是 | MaxCompute 访问 AccessKey ID |
| `maxcompute.access.key` | 是 | MaxCompute 访问 AccessKey Secret |
| `deploy.type` | 否 | 部署类型（MaxCompute 场景服务端自动回填 `RDS`，可省略） |

### DeleteCommand.Mode 枚举

| 值 | 说明 |
|----|------|
| `DEV` | 仅删除开发环境数据源 |
| `DEV_PROD` | 同时删除开发和生产环境数据源 |
