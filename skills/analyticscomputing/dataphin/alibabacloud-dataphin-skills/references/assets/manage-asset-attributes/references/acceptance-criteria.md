# 验收标准

## 正确模式

### 1. 产品名 / 命令格式
- 使用 `dataphin-public`（非旧 `dataphin` 二进制）
- 插件模式命令为 kebab-case：`get-asset-type-attribute-codes` / `update-asset-attributes`
- 命令未收录时改走 OpenAPI SDK 兜底（API 版本 `2023-06-30`，RPC 风格）

### 2. 写入前置
- 先 `GetAssetTypeAttributeCodes` 拿到合法 `AttributeCode` 与枚举 `Value`
- 覆盖写前用 `GetAssetAttributes` 读出原值另存（覆盖不可自动回滚）

### 3. 端到端校验三步法
1. 同步返回 `Success=true` 且 `Data.FailCount=0`
2. 逐条核对 `Data.ResultList[i].Success=true`
3. `GetAssetAttributes` 回读被写 GUID，`Values` 与写入一致

### 4. 参数确认
- 所有用户自定义参数（租户、GUID、AttributeCode、Values）执行前需用户确认
- 不硬编码 tenant-id / GUID / 资源名

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/GUID
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 未经 HITL 确认直接批量写入 / 清空属性
- ❌ 单次 `AssetAttributeUpdateList` 超 50 条
- ❌ 依赖服务端拦截非法 AttributeCode / 超长文本（实测会静默成功）
