# 验收标准

## create-maxcompute-data-source

### 基础验收

- [ ] CLI 版本 >= 3.4.8（`aliyun version`）
- [ ] dataphin-public 插件可用（`aliyun dataphin-public --help`）
- [ ] Profile 有效（`aliyun configure list`）

### 功能验收

#### 连通性预检
- [ ] `check-data-source-connectivity` 传入正确 MaxCompute 配置，返回 `ConnectStatus: true`
- [ ] 传入错误配置时，返回 `ConnectStatus: false`

#### Basic 项目创建
- [ ] `create-data-source` 仅传 `ProdDataSourceCreate`，返回 `Code: OK` 和 `ProdDataSourceId`
- [ ] `list-data-source-with-config` 按名称反查命中
- [ ] `check-data-source-connectivity-by-id` 返回 `ConnectStatus: true`

#### DEV-PROD 项目创建
- [ ] Step 1：创建生产环境数据源成功，返回 `ProdDataSourceId`
- [ ] Step 2：创建开发环境数据源成功，`ProdDataSourceId` 正确关联
- [ ] 列表反查同时出现 PROD 和 DEV 两条记录

#### 清理
- [ ] `delete-data-source` Mode=DEV_PROD 成功删除
- [ ] 删除后 `list-data-source-with-config` 反查不再命中

### Observability 验收
- [ ] 所有 `aliyun` API 命令均携带 `--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-data-source/{session-id}`
- [ ] session-id 继承自父 skill `alibabacloud-dataphin-skills`
