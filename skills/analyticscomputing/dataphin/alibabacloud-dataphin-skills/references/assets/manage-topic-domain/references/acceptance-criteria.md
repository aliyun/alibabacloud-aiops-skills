# 验收标准

## 正确模式

### 1. 产品名与命令格式正确
- 使用 `dataphin-public` 而非旧 `dataphin` 二进制
- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`（kebab-case）
- 查询列表用复数命令 `list-data-domains`，非 `list-data-domain`
- 获取详情用 `get-data-domain-info`（带 `-info` 后缀），非 `get-data-domain`

### 2. 参数确认与 HITL
- 所有用户自定义参数执行前需用户确认
- 写操作（create / update / delete）执行前必须 HITL 二次确认
- 不硬编码 tenant-id / biz-unit-id / data-domain-id 等
- 大整数 ID 一律字符串传参（引号包住）

### 3. 必填参数完整
- create/update/delete 必带 `--biz-unit-id`（所属数据板块，硬前置）
- `create-data-domain` 必带 `--data-domain-name` + `--display-name` + `--abbreviation`
- `update-data-domain` 必带 `--data-domain-id` + create 的全部必填字段
- `delete-data-domain` / `get-data-domain-info` 必带 `--data-domain-id`

### 4. 端到端校验两步法（主题域无发布流程）
- 同步响应 `Code: OK`
- `list-data-domains`（按 `--biz-unit-id-list` + `--keyword` 过滤）/ `get-data-domain-info` 反查命中
- ⚠ 主题域**无异步发布状态**，不需要轮询 PublishStatus / Stage

### 5. Observability
- 所有调用 API 的 `aliyun` 命令携带 `--user-agent AlibabaCloud-Agent-Skills/manage-topic-domain/{session-id}`
- session-id 继承父 skill，不重新生成

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant / biz-unit / data-domain ID
- ❌ 使用 `dataphin` 旧 CLI 二进制命令
- ❌ 未带 `--user-agent` 调用 aliyun API 命令
- ❌ create/update/delete 漏传 `--biz-unit-id`
- ❌ update 只传要改的字段（漏传 create 必填项会报参数缺失）
- ❌ delete-data-domain 未经确认直接执行（不可回滚）
- ❌ 误以为主题域有发布流程去调 publish/offline（不存在此类命令）
