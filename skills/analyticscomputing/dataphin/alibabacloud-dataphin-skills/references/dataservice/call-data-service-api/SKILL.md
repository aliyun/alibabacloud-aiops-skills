---
name: call-data-service-api
description: |
  调用 Dataphin 数据服务已发布的 API。使用附带脚本（Python 标准库，零依赖）完成 HMAC-SHA256 签名，无需下载官方 SDK。
  触发场景：调用数据服务 API / SDK 调用 / Python 调用 / AppKey 调用 / 异步调用 API。
---

# 数据服务 API 调用

## 1. Scenario Description

应用开发者调用 Dataphin 数据服务已发布并授权的 API，支持同步、异步和流式（SSE）三种调用模式。调用脚本内置 HMAC-SHA256 签名认证，**不依赖官方 SDK，也不需要任何第三方库**。

**业务流程：**
```
确认调用信息 → 同步调用 API → （可选）异步调用 → 验证调用成功
```

**资源拓扑：**
```
数据服务网关
├── 阿里云 API 网关模式（推荐脚本调用）
│   ├── HMAC-SHA256 签名（脚本内置）
│   └── AppKey/AppSecret → 脚本自动处理
├── 内置网关模式
│   ├── 参数认证（appkey/appsecret 请求参数）
│   └── AppKey/AppSecret → 请求参数
├── 同步调用（即时返回）
├── 异步调用
│   ├── 提交任务 → jobId
│   ├── 脚本自动轮询状态
│   └── 获取结果
└── 流式调用（SSE）
    └── 实时返回数据片段
```

**前置条件：**
- 至少一个 API 已发布到目标环境（S1 `create-and-publish-api` 产出）
- 应用已创建并获授权（S2 `manage-app-and-bindauth` 产出）
- 已获取 AppKey 和 AppSecret
- 已确认网关地址和 API 调用路径
- Python >= 3.9（仅需标准库）

**与 S1/S2 的衔接：**
- S1 产出 `ApiId` + API 路径（通过 `get-data-service-api-document` 查询）
- S2 产出 `AppKey` / `AppSecret`，本 Skill 消费这些凭证发起调用

**与 S1/S2 的本质差异：**

| 维度 | 管理面（S1/S2/S4） | 调用面（本 Skill） |
|------|-------------------|-------------------|
| 凭证 | RAM AccessKey/Secret | **App AppKey/AppSecret** |
| 工具 | `aliyun` CLI | **本 Skill 调用脚本（HTTP + 签名）** |
| 网关 | 阿里云 OpenAPI 网关 | **数据服务网关** |
| 环境 | 无区分 | **Dev / Prod（stage 参数）** |

## 2. Installation

**无需安装任何 SDK 或第三方库。**

| 用途 | 要求 | 说明 |
|-----|------|------|
| **API 调用（本 Skill 核心）** | Python ≥ 3.9 | 直接用 `scripts/call-data-service-api.py`，纯标准库 |
| 元信息查询（apiId/AppKey 等） | aliyun CLI ≥ 3.4.8 + dataphin 插件 | 见 [CLI 安装指引](./references/cli-installation-guide.md) |
| 嵌入自有工程（可选） | `requests` 或标准库 | 见 [Python 调用模板](./references/python-client-template.md) |

> 官方 Python/Java SDK 亦可用（控制台「数据服务 → 应用管理 → 调用说明 → SDK 下载」），但**不是本 Skill 的前置条件**；脚本签名逻辑与官方 SDK v5.5.0 逐字节一致。

## 3. Environment Variables

| 变量 | 说明 | 必须 |
|------|------|------|
| DATAPHIN_APP_KEY | 应用 AppKey | 是 |
| DATAPHIN_APP_SECRET | 应用 AppSecret | 是 |
| DATAPHIN_GATEWAY_HOST | 数据服务网关地址 | 是 |

> **安全提示**：不要将 AppKey/AppSecret 硬编码在代码中，务必使用环境变量。

## 4. Authentication

### Pre-check: Credentials Required

```bash
# 检查 Python 环境（脚本要求 >= 3.9，无需第三方库）
python3 --version

# 确认应用凭证已获取（来自 S2 manage-app-and-bindauth 产出）
# appKey: 应用 AppKey
# appSecret: 应用 AppSecret
# host: 数据服务网关地址（从控制台"网络配置"获取）
```

**凭证不可打印**：任何时候不得将 AppKey/AppSecret 输出到终端或日志。

**认证方式说明：**

本 Skill **不使用 RAM 凭证**，使用数据服务应用凭证（AppKey/AppSecret），签名由调用脚本内置完成。

| 网关类型 | 认证方式 | 脚本支持 | 适用场景 |
|---------|---------|---------|---------|
| **阿里云 API 网关** | HMAC-SHA256 签名（脚本自动处理） | ✅ 内置签名 | 公共云独立部署 |
| **内置网关** | appkey/appsecret 作为请求参数 | 需手动构造 | 私有云独立部署 / VPC 环境 |

> **如何判断当前网关类型**：登录 Dataphin 控制台 → 数据服务 → 服务管理 → 网络配置。

## 5. App Authentication

> **本 Skill 不使用 RAM 认证**，改用数据服务应用认证。

### 认证方式一：脚本自动签名（阿里云 API 网关）——推荐

`scripts/call-data-service-api.py` 内置 HMAC-SHA256 签名，用户只需提供 AppKey/AppSecret，脚本自动完成全部签名流程（nonce/timestamp 生成、签名串构造、签名计算、Header 设置）。签名串规范见 [Python 调用模板 §1](./references/python-client-template.md)，App 认证说明见 [App 认证参考](../../ram-policies.md)。

### 认证方式二：参数认证（内置网关）

| 项目 | 说明 |
|------|------|
| 凭证类型 | App AppKey / AppSecret |
| 传输方式 | 请求参数（Query 或 Body） |

内置网关模式下，appkey 和 appsecret 作为 API 的公共参数传入。详见 [App 认证参考](../../ram-policies.md)。

### AppKey/AppSecret 获取

AppKey/AppSecret 由 S2 `manage-app-and-bindauth` 创建应用时获取。也可通过以下 CLI 命令查询：

```bash
# 查看应用详情（需要是应用成员，或 SuperAdmin 权限）
aliyun dataphin-public get-data-service-app \
  --op-tenant-id <tenantId> --app-id <appId> \
  --profile <profile> --endpoint <endpoint>

# 列出所有应用（查看 AppId，需应用成员才能获取 AppKey/AppSecret）
aliyun dataphin-public list-data-service-apps \
  --op-tenant-id <tenantId> \
  --list-query PageNo=1 PageSize=20 \
  --profile <profile> --endpoint <endpoint>
```

### 常见认证错误

| 错误码 | 原因 | 解决方案 |
|--------|------|---------|
| `AppKeyNotFound` | AppKey 无效 | 检查 AppKey 是否正确，是否来自 S2 |
| `SignatureDoesNotMatch` | 签名不匹配（自行实现签名时） | 用附带脚本可避免；自研时对照 [签名规范](./references/python-client-template.md) 检查：`x-ca-signature-headers` 不含 `x-ca-signature` 自身、path 与签名串完全一致、JSON 请求不带 `content-md5` |
| `TimestampExpired` | 时间戳偏差过大 | 确保客户端时间与服务器偏差 < 15 分钟 |
| `The request api path not bind app` | 应用未授权该 API | 回到 S2 完成授权流程 |
| `InvalidAppKey` | AppKey/AppSecret 参数错误（内置网关） | 检查 appkey/appsecret 参数值 |

### Permission Failure Handling

若遇到权限错误（HTTP 403 或错误码含 `AppUnauthorized`/`Forbidden`），请：
1. 确认应用已通过 S2 `manage-app-and-bindauth` 获得目标 API 的授权
2. 确认 stage 参数与 API 发布环境匹配（RELEASE = 生产，PRE = 开发）
3. 确认当前用户是应用成员（`IsMember: true`）
4. 联系项目管理员授权

详见 [App 认证参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

| 参数 | 含义 | 获取方式 | 必填 |
|------|------|---------|------|
| appKey | 应用 AppKey | S2 创建应用时获取；或 SuperAdmin 用 `get-data-service-app` 查询 | 是 |
| appSecret | 应用 AppSecret | 同上 | 是 |
| host | 数据服务网关地址 | 控制台「网络配置」或管理员提供 | 是 |
| apiId | API 唯一标识（整数） | `list-data-service-published-apis` 或 API 列表页面 | 是 |
| methodType | API 操作类型 | `get-data-service-api-document` 查询（LIST/GET/CREATE/UPDATE/DELETE）| 是 |
| stage | 环境 | RELEASE（生产）/ PRE（开发），默认 RELEASE | 是 |
| env | 数据环境 | PROD（生产数据）/ PRE（开发数据），默认 PROD | 是 |
| 业务参数 | API 定义的请求参数 | `get-data-service-api-document` 的 `RequestParamList` | 视 API |

**host 获取说明：**
> 网关地址从 Dataphin 控制台获取：数据服务 → 服务管理 → 网络配置。独立部署环境常见命名为 `dataphin-dataservice.<租户基础域名>`（反代 canonical 常落 `dataphin-os-gateway.*`）。该网关**与管理面 OpenAPI 端点 `dataphin-openapi.*` 不是同一域名**，也不在任何 OpenAPI 返回里。若无法直接拿到，可按命名规律**探测确认**（`curl POST /list/{apiId}` 返回 `DPN-OLTP-*` 即命中），详见 [调用前置发现 §网关 host 发现](./references/pre-call-discovery.md#网关-host-发现p1)。VPC/私有化部署中该域名可能不对外暴露公网地址，需联系运维确认。

> **⚠️ 参数获取暗坑（逆向参数时必看）**：
> - **应用名不唯一**：同租户可能多个同名应用，必须用 **AppKey** 唯一确定，不靠名字。
> - **AppKey 是字符串**（如 `"200000326"`），比较用 `str()`。
> - `list-authorized-data-service-api-details` 用 **`AppKeyStr`**（字符串），`AppKey`（整型）已弃用。
> - `returnFields` 只能取**已授权字段**（步骤 C 产出），传未授权字段会报错。
> 完整清单见 [调用前置发现 §暗坑清单](./references/pre-call-discovery.md#暗坑清单p2-速查)。

**API 调用路径构造：**正确格式为 `/{methodType}/{apiId}?appKey={appKey}&env={env}`，**不是** `/api/<GroupId>/<ApiName>`。methodType 有 5 种：`list`（列表查询）、`get`（单条查询）、`create`/`update`/`delete`（DML）。

> **⚠️ methodType 由 API 发布时的操作类型决定，不能仅凭 `IsPagedQuery` 推断**：`IsPagedQuery` 只表示「是否分页」，`list` 与 `get` 都可能为 `true`（实测 `GetCustomer` 的 `IsPagedQuery=true` 但它是 `get`）。应按 API 的**操作语义/命名**判断（`Get*`/单条 → `get`；`List*`/`Bulk*`/列表 → `list`；`Create*`→`create`；`Update*`→`update`；`Delete*`→`delete`）。**methodType 猜错 → 网关返回 `403 The request api path /xxx/{apiId} not bind app {appKey}`**，据此换正确动词重试。

示例：`http://<YOUR_GATEWAY_ENDPOINT>/list/10083?appKey=200000008&env=PROD`

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

调用脚本通过标准 `user-agent` 请求头标记（脚本读取环境变量 `SKILL_SESSION_ID` 自动注入）：
```
user-agent: AlibabaCloud-Agent-Skills/call-data-service-api/{SESSION_ID}
```

> **⚠️ 不要用 `X-Ca-User-Agent` 之类的 `x-ca-*` 头承载可观测标记**：`x-ca-*` 前缀会被纳入签名串，多一个头就要同步进 `x-ca-signature-headers`，否则触发 `SignatureDoesNotMatch`。用普通 `user-agent`（不参与签名）最稳妥。

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 0：环境前置检查

在执行任何调用之前，确认 Python 版本与凭证环境变量就绪。**无需下载或安装 SDK。**

```bash
# 1. Python >= 3.9（脚本仅用标准库，无需 pip install）
python3 --version

# 2. 确认脚本存在（相对于本 Skill 目录）
ls ./scripts/call-data-service-api.py

# 3. 确认凭证环境变量（值不打印）
: "${DATAPHIN_APP_KEY:?未设置}" "${DATAPHIN_APP_SECRET:?未设置}" "${DATAPHIN_GATEWAY_HOST:?未设置}"
```

### 步骤 0.5：零参数发现（仅有「应用名 + API 名」时）

若用户只给了**应用名 + 要调的 API 名**（例：*让应用「客户管理」查询客户列表*），而没有直接给 `appKey`/`appSecret`/`apiId`/`host`，先走一条管理面反查链补齐四要素——**否则会卡在找参数上**（这是本 Skill 最常见的耗时点）：

| 反查步 | 命令 | 产出 |
|--------|------|------|
| A 应用名→AppId | `list-data-service-apps` | AppId（⚠️ **同名应用用 AppKey 去重**） |
| B AppId→凭证 | `get-data-service-app` | AppKey / AppSecret（⚠️ AppKey 为**字符串**） |
| C 已授权 API→apiId | `list-authorized-data-service-api-details`（用 `AppKeyStr`） | apiId + **授权 returnFields** |
| D apiId→文档 | `get-data-service-api-document` | methodType（⚠️按操作类型定，**不能仅凭 `IsPagedQuery`**）+ 请求参数 |

`host`（网关地址）需单独确认，见 §6 host 获取说明。

> 完整可照抄命令、同名去重/AppKeyStr/字段授权等**暗坑清单**、以及**网关 host 命名规律 + 探测法**，详见 [调用前置发现](./references/pre-call-discovery.md)。

### 步骤 1：确认调用信息

在发起调用前，确认以下信息已就绪并导出为环境变量（凭证不打印）：

```bash
export DATAPHIN_APP_KEY=<来自 S2>
export DATAPHIN_APP_SECRET=<来自 S2>
export DATAPHIN_GATEWAY_HOST=<控制台「网络配置」获取>
export SKILL_SESSION_ID=<父 Skill 生成的 session-id>   # 可观测标记，可选
# 调用时还需：apiId（整数）、method（LIST/GET/CREATE/UPDATE/DELETE）、
#             stage（RELEASE=生产 / PRE=开发）、env（PROD / PRE）
```

### 步骤 1.5：查询 API 文档（如路径未知）

```bash
# 通过 CLI 查询 API 文档，获取 IsPagedQuery、请求方法、参数列表
aliyun dataphin-public get-data-service-api-document \
  --op-tenant-id <tenantId> --id <apiId> \
  --profile <profile> --endpoint <endpoint>

# 关键返回字段：
#   IsPagedQuery    → 是否分页（仅辅助，不能单独用来定 methodType，见下）
#   RequestParamList → 业务请求参数（应走 conditions 字段）
#   ResponseParamList → 响应参数
#   PublicParamList → 公共参数（appkey/appsecret，仅内置网关需要）
```

API 调用 URL 构造规则：`/{methodType}/{apiId}?appKey={appKey}&env={env}`

**methodType 由 API 操作类型决定（5 选 1），按操作语义/命名判断——不要只看 `IsPagedQuery`：**

| API 操作类型 / 命名 | method | 网关路径 |
|---|---|---|
| 列表查询（`List*` / `Bulk*` / 分页） | `LIST` | `/list/{apiId}` |
| 单条查询（`Get*`，按主键精确取一条） | `GET` | `/get/{apiId}` |
| 新增（`Create*`） | `CREATE` | `/create/{apiId}` |
| 更新（`Update*`） | `UPDATE` | `/update/{apiId}` |
| 删除（`Delete*`） | `DELETE` | `/delete/{apiId}` |

> **⚠️ `IsPagedQuery=true` 不等于 `list`**：`get` 类 API 也可能 `IsPagedQuery=true`（实测 `GetCustomer`）。猜错 methodType → `403 ... not bind app {appKey}`，换正确动词重试。

### 步骤 2：同步调用 API（推荐）

用附带脚本 `scripts/call-data-service-api.py` 调用，脚本内置 HMAC-SHA256 签名，无需 SDK、无需第三方库。完整说明见 [Python 调用模板](./references/python-client-template.md)。

```bash
# LIST 同步调用（--method 决定路径动词，须大写）
python3 scripts/call-data-service-api.py call \
  --api-id 10083 --method LIST \
  --params '{"conditions":{},"returnFields":[],"pageStart":0,"pageSize":10,"keepColumnCase":true}' \
  --stage RELEASE --env PROD

# GET 单条查询（结果在 result 字段，不是 results）
python3 scripts/call-data-service-api.py call --api-id 10084 --method GET \
  --params '{"conditions":{"id":1}}'

# 私有化自签 HTTPS：加 --scheme HTTPS --ignore-ssl
```

成功时脚本输出 `code == "DPN-OLTP-COMMON-000"` 的 JSON 并以退出码 0 结束；业务失败退出码 1，缺少环境变量/参数错误退出码 2。

> **结果字段随 method 不同**：`LIST` → `results`（数组）；`GET` → `result`（单个对象）。

### 步骤 3：异步调用（大数据量）

```bash
# 自动完成：提交 → 轮询 jobId → 合并分页结果 → closeJob
python3 scripts/call-data-service-api.py async-call \
  --api-id 10083 --method LIST --params-file query.json \
  --poll-interval 1 --timeout 600
```

详见 [异步调用模板](./references/async-call-template.md)。

### 步骤 4：流式调用（SSE）与 DML

```bash
# 流式调用：逐帧输出 JSON
python3 scripts/call-data-service-api.py sse --api-id 10085 --method GET --params '{}'

# DML：--method 换 CREATE/UPDATE/DELETE，参数为 ManipulationParam
python3 scripts/call-data-service-api.py call --api-id 10083 --method CREATE \
  --params '{"conditions":{"id":1,"name":"test"}}'
# 批量操作用 batchConditions，详见 references/python-client-template.md
```

### 步骤 5：嵌入自有工程（可选）

如需在已有 Python 工程内调用（而非命令行），可照抄 [Python 调用模板](./references/python-client-template.md) 的 `requests` 版最小客户端（约 60 行）。签名规范见该文档 §1。

### 步骤 6：验证调用成功

验证标准：
- 脚本退出码为 0
- 响应 `code` 字段为 `"DPN-OLTP-COMMON-000"`（不是 `"0"`）
- 返回数据含预期业务字段（`LIST` 看 `results`，`GET` 看 `result`）

## 9. Success Verification

采用三步验证法：

1. **HTTP 状态检查**：响应状态码为 200
2. **业务码检查**：`code == "DPN-OLTP-COMMON-000"` 表示业务成功（注意：不是 `"0"`）
3. **数据完整性**：返回 `results` 列表包含预期业务字段

## 10. Cleanup

本 Skill 无需清理资源。API 调用不创建持久化资源，无需回滚操作。

> **注意**：`async-call` 在异步任务完成/失败后会自动调用 `closeJob` 关闭任务（放在 `finally` 中），无需手动清理。

## 11. Command Tables

本 Skill 用附带脚本调用数据服务网关，同时用少量 CLI 命令获取调用所需的元信息。

### CLI 信息查询命令

| 命令 | 用途 | 必要性 |
|------|------|--------|
| `get-data-service-api-document` | 查询 API 文档（路径、参数、方法） | 推荐 |
| `get-data-service-app` | 查询应用详情（含 AppKey/AppSecret） | 需应用成员 |
| `list-data-service-apps` | 列出所有应用 | 可选 |
| `list-data-service-published-apis` | 查看已发布 API 列表 | 可选 |

### 调用脚本子命令

| 子命令 | 用途 | 模式 |
|------|------|------|
| `call --api-id <id> --method <M> --params '<json>'` | 调用 API | 同步 |
| `async-call --api-id <id> --method <M> --params-file <f>` | 调用 API（自动轮询、合并分页、关闭任务） | 异步 |
| `sse --api-id <id> --method <M> --params '<json>'` | 逐帧输出数据 | 流式(SSE) |

选项与请求参数详见 [API 调用参考](./references/related-commands.md) 及 [Python 调用模板](./references/python-client-template.md)。

## 12. Best Practices

- **零依赖调用**：用 `scripts/call-data-service-api.py`（纯标准库），无需安装 SDK 或 `requests`，签名与官方 SDK v5.5.0 逐字节一致
- **环境变量存储凭证**：不要硬编码 AppKey/AppSecret，使用 `DATAPHIN_APP_KEY` / `DATAPHIN_APP_SECRET` 环境变量，且不打印
- **API 调用路径**：正确格式为 `/{methodType}/{apiId}?appKey=xxx&env=xxx`，不是 `/api/<GroupId>/<ApiName>`
- **method 大写**：`--method` 使用大写（`LIST`/`GET`/`CREATE`/`UPDATE`/`DELETE`），它决定网关路径动词
- **scheme 选择**：内置网关仅支持 HTTP；阿里云 API 网关支持 HTTPS（自签证书用 `--ignore-ssl`）
- **业务成功码**：`DPN-OLTP-COMMON-000`（不是 `0`）
- **异步调用**：大数据量查询用 `async-call`，脚本自动轮询并合并分页结果、关闭任务
- **签名自研需谨慎**：`x-ca-signature-headers` 不含 `x-ca-signature` 自身、path 与签名串完全一致、JSON 请求不带 `content-md5`、`content-type` 不带 `; charset`（详见 [签名规范](./references/python-client-template.md)）
- **可观测标记走 `user-agent`**：不要用 `x-ca-*` 头承载，避免影响签名
- **大整数 ID**：API 返回的 19 位 snowflake ID 在 Python 中按字符串处理
- **IN 类型参数**：使用列表传递值，如 `{"age": [10, 20, 30]}`
- **分页稳定性**：使用 ORDER BY 主键或联合主键，避免分页时数据重复或丢失
