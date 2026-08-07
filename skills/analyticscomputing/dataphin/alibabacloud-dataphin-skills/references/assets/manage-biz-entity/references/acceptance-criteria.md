# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 查询列表用复数命令 `list-biz-entities`，非 `list-biz-entity`
- 获取详情用 `get-biz-entity-info`（带 `-info` 后缀），按版本查询用 `get-biz-entity-info-by-version`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / online / offline / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id / biz-unit-id / data-domain-id / biz-entity-id 等
- 大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- create/update 必带 `--biz-unit-id` 与 `--data-domain-id`
- online/offline/delete 必带 `--biz-unit-id`、`--biz-entity-id`、`--type`
- online/offline 必带 `--comment`，上线命令也要传备注
- `--type BIZ_OBJECT` 时必须传 `--biz-object`，不得传 `--biz-process`
- `--type BIZ_PROCESS` 时必须传 `--biz-process`，不得传 `--biz-object`

### 4. JSON 字段结构正确
- `--biz-object` / `--biz-process` 使用 OpenAPI PascalCase 字段
- 业务对象字段：`Name`、`DisplayName`、`Type`、`OwnerUserId`、`Description`、`ParentId`、`RefBizEntityIdList`
- 业务活动字段：`Name`、`DisplayName`、`Type`、`OwnerUserId`、`Description`、`RefBizEntityIdList`、`BizEventEntityIdList`、`PreBizProcessIdList`
- `BizObject.Type` 使用 `NORMAL` / `ENUM` / `VIRTUAL` / `HIERARCHY`
- `BizProcess.Type` 使用 `BIZ_EVENT` / `BIZ_SNAPSHOT` / `BIZ_PROCESS`

### 5. 端到端校验
- create/update 同步响应 `Code: OK` 后，需 `list-biz-entities` 或 `get-biz-entity-info` 反查字段
- online/offline 可能存在异步状态变化，需轮询 list/get 确认状态字段变化
- delete 后需反查目标不存在或返回空
- delete 前必须确认无维度逻辑表、事实逻辑表、汇总逻辑表、指标或其它业务实体依赖

### 6. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-biz-entity/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant / biz-unit / data-domain / biz-entity ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ create/update 漏传 `--biz-unit-id` 或 `--data-domain-id`
- ❌ `--type BIZ_OBJECT` 却传 `--biz-process`，或 `--type BIZ_PROCESS` 却传 `--biz-object`
- ❌ 使用内部 REST 字段 `cn` / `owner` / `bizObjectType=1` 作为 OpenAPI 入参
- ❌ update 只传要改的字段，导致 `RefBizEntityIdList` 等关联列表被清空
- ❌ 未上线就把业务实体用于下游维度/事实/指标建模
- ❌ 业务实体存在下游依赖时直接删除
