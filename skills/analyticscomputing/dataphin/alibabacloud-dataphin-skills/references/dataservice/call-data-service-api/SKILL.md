---
name: call-data-service-api
description: |
  使用附带的零依赖 Python 脚本调用 Dataphin 已发布的数据服务 API。脚本内置 HMAC-SHA256 签名，仅用标准库，无需安装 SDK。
  触发场景：调用数据服务 API / SDK 调用 / Python 调用 / AppKey 调用 / 异步调用 API。
---

# 数据服务 API 调用

## 1. Scenario Description

应用开发者使用附带的零依赖 Python 脚本调用已发布并授权的 API，支持同步、异步和流式（SSE）三种调用模式。脚本内置 HMAC-SHA256 签名认证，用户无需手动拼接签名串。

**业务流程：**
```
确认调用信息 → 检查脚本 → 同步调用 API → （可选）异步调用 → 验证调用成功
```

**资源拓扑：**
```
数据服务网关
├── 阿里云 API 网关模式（推荐脚本调用）
│   ├── 脚本内置 HMAC-SHA256 签名
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

**与 S1/S2 的衔接：**
- S1 产出 `ApiId` + API 路径（通过 `get-data-service-api-document` 查询）
- S2 产出 `AppKey` / `AppSecret`，本 Skill 消费这些凭证发起调用

**与 S1/S2 的本质差异：**

| 维度 | 管理面（S1/S2/S4） | 调用面（本 Skill） |
|------|-------------------|-------------------|
| 凭证 | RAM AccessKey/Secret | **App AppKey/AppSecret** |
| 工具 | `aliyun` CLI | **Python 标准库调用脚本** |
| 网关 | 阿里云 OpenAPI 网关 | **数据服务网关** |
| 环境 | 无区分 | **Dev / Prod（stage 参数）** |

## 2. Installation

**Python ≥ 3.9，仅使用标准库，无需安装 SDK 或第三方包。**

| 用途 | 入口 |
|------|------|
| 同步、异步和 SSE 调用 | `scripts/call-data-service-api.py` |
| 嵌入 Python 工程 | [Python 调用模板](./references/python-client-template.md)，复用同一脚本 |
| 查询应用及 API 元信息 | `aliyun` CLI，见 [CLI 安装指引](./references/cli-installation-guide.md) |

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
# 检查 Python 环境（脚本要求 >= 3.9）
python3 --version

# 确认应用凭证已获取（来自 S2 manage-app-and-bindauth 产出）
# appKey: 应用 AppKey
# appSecret: 应用 AppSecret
# host: 数据服务网关地址（从控制台"网络配置"获取）
```

**凭证不可打印**：任何时候不得将 AppKey/AppSecret 输出到终端或日志。

**认证方式说明：**

本 Skill **不使用 RAM 凭证**，使用数据服务应用凭证（AppKey/AppSecret），脚本内置签名认证。

| 网关类型 | 认证方式 | 脚本支持 | 适用场景 |
|---------|---------|---------|---------|
| **阿里云 API 网关** | HMAC-SHA256 签名（脚本自动处理） | ✅ 内置签名 | 公共云独立部署 |
| **内置网关** | appkey/appsecret 作为请求参数 | 需手动构造 | 私有云独立部署 / VPC 环境 |

> **如何判断当前网关类型**：登录 Dataphin 控制台 → 数据服务 → 服务管理 → 网络配置。

## 5. App Authentication

> **本 Skill 不使用 RAM 认证**，改用数据服务应用认证。

### 认证方式一：脚本自动签名（阿里云 API 网关）——推荐

`scripts/call-data-service-api.py` 统一完成 nonce/timestamp、签名串与请求头构造。凭证从环境变量读取；签名规则及工程内复用方式见 [Python 调用模板](./references/python-client-template.md)。App 认证要求见 [App 认证参考](../../ram-policies.md)。

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
| `SignatureDoesNotMatch` | 签名不匹配（手动签名时） | 使用附带脚本；排查签名头是否包含签名自身、path 是否被改写、JSON 请求是否错误添加 Content-MD5 |
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

版本 `{version}`（Shell 变量 `SKILL_VERSION`）来自套件 `references/manifest.json` 的 `version` 字段，与 session-id 一同继承[父技能 §7](../../../SKILL.md#7-observability)。直接加载本子技能时先完成父层初始化；所有 CLI / SDK 调用使用父技能名称与同一版本，跨 Shell 调用须重新注入这些值。

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

前置发现所用 CLI API 命令附带 `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{session-id} skill-version/{version}"`。

脚本读取 `SKILL_SESSION_ID`，并由公共 helper 从 manifest 读取版本，通过普通 `user-agent` 请求头标记：

```
user-agent: AlibabaCloud-Agent-Skills/alibabacloud-dataphin-skills/{SESSION_ID} skill-version/{version}
```

每次执行脚本时用 `SKILL_SESSION_ID="$SESSION_ID" python3 ...` 内联传入父层的 32 字符会话 ID。不要把标记放进 `x-ca-*` 头，避免改变签名头集合。

## 8. Core Workflow

### 步骤 0：脚本前置检查

在本 Skill 目录确认 Python 和附带脚本可用：

```bash
python3 --version
python3 scripts/call-data-service-api.py --help
```

脚本不依赖 SDK、`requests` 或其他第三方包。调用凭证由环境变量传入，值不得打印。

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

在发起调用前，按 §6 确认 AppKey/AppSecret、host、apiId、methodType、stage、env、协议和端口。凭证在会话外配置；业务变量沿用用户确认的取值：

```bash
: "${DATAPHIN_APP_KEY:?未设置}" "${DATAPHIN_APP_SECRET:?未设置}" "${DATAPHIN_GATEWAY_HOST:?未设置}"
: "${API_ID:?未确认}" "${METHOD:?未确认}" "${STAGE:?未确认}" "${DATA_ENV:?未确认}"
: "${SCHEME:?未确认}" "${PORT:?未确认}" "${SESSION_ID:?未继承父层会话 ID}"
```

`METHOD` 使用大写 `LIST/GET/CREATE/UPDATE/DELETE`，脚本映射成路径中的小写动词。`STAGE` 为 `RELEASE/PRE`，`DATA_ENV` 为 `PROD/PRE`；协议、端口选项见 [命令参考](./references/related-commands.md)。

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

| API 操作类型 / 命名 | methodType | 网关路径 |
|---|---|---|
| 列表查询（`List*` / `Bulk*` / 分页） | `list` | `/list/{apiId}` |
| 单条查询（`Get*`，按主键精确取一条） | `get` | `/get/{apiId}` |
| 新增（`Create*`） | `create` | `/create/{apiId}` |
| 更新（`Update*`） | `update` | `/update/{apiId}` |
| 删除（`Delete*`） | `delete` | `/delete/{apiId}` |

> **⚠️ `IsPagedQuery=true` 不等于 `list`**：`get` 类 API 也可能 `IsPagedQuery=true`（实测 `GetCustomer`）。猜错 methodType → `403 ... not bind app {appKey}`，换正确动词重试。

### 步骤 2：准备业务请求参数

按 API 文档和授权字段准备 `query.json`：查询使用 QueryParam（`conditions`、`returnFields`、分页等）；DML 使用 ManipulationParam（单条 `conditions` 或批量 `batchConditions`）。完整字段表见 [Python 调用模板](./references/python-client-template.md)。

### 步骤 3：同步调用

```bash
SKILL_SESSION_ID="$SESSION_ID" python3 scripts/call-data-service-api.py call \
  --api-id "$API_ID" --method "$METHOD" --params-file query.json \
  --stage "$STAGE" --env "$DATA_ENV" --scheme "$SCHEME" --port "$PORT"
```

脚本输出原始业务 JSON：`LIST` 读取 `results` 数组，`GET` 读取 `result` 对象；DML 按目标 API 的响应定义处理。`--params` 也可传 JSON 字符串，与 `--params-file` 二选一。

### 步骤 4：异步调用

```bash
SKILL_SESSION_ID="$SESSION_ID" python3 scripts/call-data-service-api.py async-call \
  --api-id "$API_ID" --method "$METHOD" --params-file query.json \
  --stage "$STAGE" --env "$DATA_ENV" --scheme "$SCHEME" --port "$PORT"
```

脚本处理提交、jobId 轮询、分页合并和 `closeJob`；无 jobId 时直接返回同步响应。轮询超时与间隔用 `--timeout`、`--poll-interval` 控制，见 [异步调用说明](./references/async-call-template.md)。

### 步骤 5：SSE 与工程内复用

```bash
SKILL_SESSION_ID="$SESSION_ID" python3 scripts/call-data-service-api.py sse \
  --api-id "$API_ID" --method "$METHOD" --params-file query.json \
  --stage "$STAGE" --env "$DATA_ENV" --scheme "$SCHEME" --port "$PORT"
```

SSE 逐帧输出 JSON。工程内调用通过标准库加载同一脚本的 `Gateway`，见 [Python 调用模板](./references/python-client-template.md)，不另写签名客户端。

### 步骤 6：验证调用成功

验证标准：
- 响应 HTTP 状态码为 200
- 响应 `code` 字段为 `"DPN-OLTP-COMMON-000"`（不是 `"0"`）
- 返回数据含预期业务字段

返回校验按 methodType 区分：`LIST` 检查 `results` 列表中的授权业务字段，`GET` 检查 `result` 对象，DML 检查目标 API 定义的响应字段。脚本同步/异步命令退出码为 0 才表示其检查通过；退出码说明见 [命令参考](./references/related-commands.md)。

## 9. Success Verification

采用三步验证法：

1. **HTTP 状态检查**：响应状态码为 200
2. **业务码检查**：`code == "DPN-OLTP-COMMON-000"` 表示业务成功（注意：不是 `"0"`）
3. **数据完整性**：按操作类型检查 `results`（LIST）或 `result`（GET），DML 按 API 文档验证

## 10. Cleanup

本 Skill 无需清理资源。API 调用不创建持久化资源，无需回滚操作。

> **注意**：脚本的 `async-call` 在轮询结束、失败或超时后通过 `finally` 尝试调用 `closeJob` 关闭任务，无需手动清理。

## 11. Command Tables

本 Skill 使用附带脚本调用数据服务网关，同时使用少量 CLI 命令获取调用所需的元信息。

### CLI 信息查询命令

| 命令 | 用途 | 必要性 |
|------|------|--------|
| `get-data-service-api-document` | 查询 API 文档（路径、参数、方法） | 推荐 |
| `get-data-service-app` | 查询应用详情（含 AppKey/AppSecret） | 需应用成员 |
| `list-data-service-apps` | 列出所有应用 | 可选 |
| `list-data-service-published-apis` | 查看已发布 API 列表 | 可选 |

### 调用脚本子命令

| 子命令 | 用途 |
|--------|------|
| `call` | 同步查询或 DML |
| `async-call` | 异步调用、轮询与分页合并 |
| `sse` | 流式调用 |

完整参数、退出码和请求字段见 [命令参考](./references/related-commands.md)。

## 12. Best Practices

- **统一使用附带脚本**：签名逻辑集中维护，直接调用与工程内复用使用同一实现
- **环境变量存储凭证**：不要硬编码 AppKey/AppSecret，使用 `DATAPHIN_APP_KEY` / `DATAPHIN_APP_SECRET` 环境变量
- **API 调用路径**：正确格式为 `/{methodType}/{apiId}?appKey=xxx&env=xxx`，不是 `/api/<GroupId>/<ApiName>`
- **methodType 大小写**：脚本的 `--method` 参数使用大写（`LIST`/`GET`/`CREATE`/`UPDATE`/`DELETE`）
- **scheme 选择**：内置网关仅支持 HTTP；阿里云 API 网关支持 HTTPS
- **业务成功码**：`DPN-OLTP-COMMON-000`（不是 `0`）
- **异步调用**：大数据量查询使用 `async-call`，脚本自动轮询并合并分页结果
- **Impala API**：如底层是 Impala 引擎，通过 `--timeout`（秒）和 `--poll-interval`（秒）设置合理的轮询超时和间隔
- **大整数 ID**：API 返回的 19 位 snowflake ID 在 Python 中按字符串处理
- **IN 类型参数**：使用列表传递值，如 `{"age": [10, 20, 30]}`
- **分页稳定性**：使用 ORDER BY 主键或联合主键，避免分页时数据重复或丢失
