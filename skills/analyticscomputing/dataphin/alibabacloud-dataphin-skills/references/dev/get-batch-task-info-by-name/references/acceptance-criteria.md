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
