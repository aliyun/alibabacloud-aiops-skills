# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 查询详情命令为 `get-biz-metric-by-name`，不是 `get-biz-metric` 或 `list-biz-metrics`
- 不输出不存在的 `publish-biz-metric` / `online-biz-metric` / `offline-biz-metric` 命令

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id、catalog-id、业务指标名称、负责人等业务参数
- 大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- create/update/delete 必带 `--tenant-id`、`--biz-metric-name`
- get 必带 `--tenant-id`、`--biz-metric-name`、`--draft`
- update 改名时使用 `--new-name`，不要把新旧名称混淆
- 删除前必须先 get 回读并确认目标唯一、无下游引用

### 4. 业务字段结构正确
- 业务指标名称租户内唯一，且仅使用允许字符
- `--metric-definition` 清晰表达业务口径；引用其他业务指标时用半角中括号 `[ ]` 包裹
- `--catalog-ids`、`--labels`、`--related-biz-metrics`、`--associated-tech-metric-full-names` 等 list 参数使用 CLI 原生空格分隔多值格式，如 `--catalog-ids value1 value2`
- `--view-scope`、`--custom-attribute` 等对象/数组参数使用 OpenAPI 期望结构，不照搬内部 REST camelCase 字段
- 开启指标关系图前先配置相关业务指标，否则关系图开关可能自动关闭

### 5. 端到端校验
- create 返回成功后，需 `get-biz-metric-by-name --draft true` 回读字段
- update 返回成功后，需回读确认展示名、描述、口径、目录等字段变化
- get 时区分草稿态 `--draft true` 与已发布态 `--draft false`
- delete 后需反查目标不存在或返回空/明确错误
- 遇到发布/上架/下架诉求，需说明不在本 OpenAPI 命令边界内

### 6. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-biz-metric/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/catalog/metric ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ 将资产上架内部字段 `metaBizIndex`、`shelveDirectoryIds`、`saveAndOnShelve` 当作 CLI 参数
- ❌ 编造 `list-biz-metrics`、`publish-biz-metric`、`online-biz-metric`、`offline-biz-metric` 等不存在命令
- ❌ 创建前不查重，导致同名业务指标冲突
- ❌ 删除前不确认下游报表、指标关系图、相关指标或技术指标绑定依赖
- ❌ update 只传少量字段却期望其它可选字段自动保留，未先 get 回读现值
