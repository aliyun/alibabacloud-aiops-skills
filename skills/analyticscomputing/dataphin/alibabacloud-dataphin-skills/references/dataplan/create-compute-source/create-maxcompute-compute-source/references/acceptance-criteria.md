# 验收标准

## create-maxcompute-compute-source

### 基础验收

- [ ] CLI 版本 >= 3.4.8（`aliyun version`）
- [ ] dataphin-public 插件可用（`aliyun dataphin-public --help`）
- [ ] Profile 有效（`aliyun configure list`）

### 功能验收

#### 连通性预检
- [ ] `check-compute-source-connectivity` 传入正确 MaxCompute 配置（`--type MAX_COMPUTE` + `--config-list`），返回 `Success: true` 且 `Connected: true`
- [ ] 传入错误配置时，返回 `Connected: false` 并给出 `Reason`

#### 创建计算源
- [ ] `create-compute-source` 用扁平 flag（`--compute-source-name` / `--type MAX_COMPUTE` / `--config-list`），返回 `Code: OK` 与 `CreateResult.Id`
- [ ] `list-compute-sources --type MAX_COMPUTE --keyword <name>` 按名称反查命中
- [ ] `check-compute-source-connectivity-by-id --compute-source-id <Id>` 连通校验通过

#### 类型枚举正确性
- [ ] `--type` 使用 `MAX_COMPUTE`（大写下划线），非驼峰 `MaxCompute`

#### 清理
- [ ] `delete-compute-source --compute-source-id <Id>` 成功删除（未绑定项目时）
- [ ] 删除后 `list-compute-sources` 反查不再命中

### Observability 验收
- [ ] 所有 `aliyun` API 命令均携带 `--user-agent AlibabaCloud-Agent-Skills/create-maxcompute-compute-source/{session-id}`
- [ ] session-id 继承自父 skill `alibabacloud-dataphin-skills`
# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / project-id / 资源名等

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
