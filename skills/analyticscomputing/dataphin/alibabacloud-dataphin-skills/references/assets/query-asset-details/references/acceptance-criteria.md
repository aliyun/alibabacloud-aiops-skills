# 验收标准

## 正确模式

### 1. 产品名 / 命令格式
- 使用 `dataphin-public`（非旧 `dataphin` 二进制）
- 插件模式命令为 kebab-case：`get-asset-attributes` / `get-catalog-asset-details`
- 命令未收录时改走 OpenAPI SDK 兜底（API 版本 `2023-06-30`，RPC 风格）

### 2. GetAssetAttributes 校验
- `Success=true`；命中资产 `AttributeList` 含预期 `AttributeCode`
- 传 `AttributeCodeList` 时仅返回指定属性
- 不存在 GUID 不报错且不出现在结果中（须核对返回的 GUID 集）

### 3. GetCatalogAssetDetails 校验
- `Success=true`；`Directories[].DirectoryChain` 存在
- `DirectoryChain` 按 `Level` 升序，末节点为叶子（其 DirectoryId == 外层 DirectoryId）
- 空描述兼容 `null`（TopicDescription）与 `""`（DirectoryDescription）

### 4. 参数确认
- 所有用户自定义参数（租户、GUID）执行前需用户确认
- 不硬编码 tenant-id / GUID

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/GUID
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 凭 `Success=true` 断定 GUID 有效（不存在也返回 true）
- ❌ 单次 `GuidList` 超 50 条
