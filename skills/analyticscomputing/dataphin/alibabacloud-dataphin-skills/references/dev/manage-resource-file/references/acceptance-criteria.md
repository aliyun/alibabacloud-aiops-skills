# 验收标准

## 正确模式

### 1. 产品名正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制

### 2. 命令格式正确
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`

### 3. 参数确认
- 所有用户自定义参数执行前需用户确认
- 不硬编码 tenant-id / project-id / resource-id 等
- `--resource-name` / `--resource-type` 未提供时必须主动询问用户
- `--compute-engine-type` 未明确时按 UDF/非 UDF 区分：UDF 必须询问引擎，非 UDF 用 `NONE`

### 4. 存储类型分支正确
- StorageType=oss：使用 `ossutil cp` 且带 `--sts-token`（临时 SecurityToken）
- StorageType=ceph：先 `mc alias set` 再 `mc cp`，无 SecurityToken
- 不混用 ossutil / mc

### 5. 凭证处理安全
- 临时凭证只写入 shell 变量供工具使用
- 禁止 `echo` / 日志打印 AccessId / AccessKey / SecurityToken
- 凭证过期后重新调用 `get-file-storage-credential`

### 6. 更新先回读
- `update-resource` 前先 `get-resource` 回读最新版本信息
- 在回读结果上更新，避免覆盖式更新丢字段

### 7. 端到端校验三步法
- 同步 Code:OK
- 创建/更新后 `get-resource` 反查确认资源存在
- 更新后 `get-resource-by-version` 核对版本/文件地址变化

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project/resource ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ oss 上传遗漏 `--sts-token`
- ❌ ceph 上传跳过 `mc alias set`
- ❌ `echo` 打印临时凭证
- ❌ `update-resource` 未先 `get-resource` 直接覆盖
- ❌ UDF 资源未指定 `--compute-engine-type`，或非 UDF 指定引擎
