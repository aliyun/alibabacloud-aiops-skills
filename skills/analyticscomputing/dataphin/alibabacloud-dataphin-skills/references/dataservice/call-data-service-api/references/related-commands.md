# API 调用参考（call-data-service-api）

> 本 Skill **不依赖任何 SDK**：调用走附带脚本 [`scripts/call-data-service-api.py`](../scripts/call-data-service-api.py)（纯标准库，内置 HMAC-SHA256 签名）；元信息查询走 `aliyun` CLI。

## CLI 信息查询命令

| 命令 | 用途 | 权限要求 |
|------|------|---------|
| `get-data-service-api-document --op-tenant-id <t> --id <apiId>` | 查询 API 文档（路径、参数、方法） | 项目成员 |
| `get-data-service-app --op-tenant-id <t> --app-id <appId>` | 查询应用详情（含 AppKey/AppSecret） | 应用成员 |
| `list-data-service-apps --op-tenant-id <t> --list-query ...` | 列出所有应用（查看 AppId） | 租户成员 |
| `list-authorized-data-service-api-details --op-tenant-id <t> --list-query AppKeyStr=<appKey> ...` | 查应用**已授权 API** + 授权字段（逆查 apiId 首选；用 `AppKeyStr` 字符串） | 应用成员 |
| `list-data-service-published-apis --op-tenant-id <t> --project-id <p>` | 查看已发布 API 列表 | 项目成员 |
| `apply-data-service-app --op-tenant-id <t> --project-id <p> --apply-command ...` | 申请应用权限（需审批） | 租户成员 |
| `get-data-service-api-groups --op-tenant-id <t> --project-id <p>` | 查看 API 分组列表 | 项目成员 |

> **权限说明**：`get-data-service-app` 要求当前用户是应用成员（`IsMember: true`），否则返回 `NoAuthorized`。

## 调用脚本用法

`scripts/call-data-service-api.py`（Python >= 3.9，零第三方依赖）：

| 子命令 | 用途 | 模式 |
|------|------|------|
| `call --api-id <id> --method <M> --params '<json>'` | 调用 API | 同步 |
| `async-call --api-id <id> --method <M> --params-file <f>` | 调用 API（自动轮询 jobId、合并分页、关闭任务） | 异步 |
| `sse --api-id <id> --method <M> --params '<json>'` | 逐帧输出数据 | 流式(SSE) |

| 选项 | 说明 |
|------|------|
| `--method` | `LIST` / `GET` / `CREATE` / `UPDATE` / `DELETE`（决定路径动词） |
| `--stage` | `RELEASE`（生产）/ `PRE`（开发），默认 RELEASE |
| `--env` | `PROD` / `PRE`，默认 PROD |
| `--scheme` / `--port` | 默认 `HTTP` / 80（内置网关仅支持 HTTP） |
| `--ignore-ssl` | HTTPS 自签证书时跳过校验 |
| `--poll-interval` / `--timeout` | 仅 `async-call`：轮询间隔（默认 1s）与超时（默认 300s） |
| `--quiet` | 仅输出结果 JSON |

凭证与网关地址由环境变量提供：`DATAPHIN_APP_KEY` / `DATAPHIN_APP_SECRET` / `DATAPHIN_GATEWAY_HOST`。
退出码：0 成功，1 业务失败或网络/签名错误，2 缺少环境变量或参数错误。

## 异步调用端点

| 端点 | 用途 |
|------|------|
| `/getJobStatus` | 查询任务状态（1 RUNNING / 2 SUCCESS / 3 FAILED / 4 CANCELLED / 5 EXPIRED / 6-7 CLOSED_*） |
| `/getJobResult` | 分批拉取结果（循环至 `results` 为空） |
| `/getJobExecutionLog` | 失败时取执行日志 |
| `/closeJob` / `/cancelJob` | 关闭 / 取消任务 |

query 参数固定为 `appKey` / `env` / `fetchSize` / `jobId`，详见 [异步调用模板](./async-call-template.md)。

## 请求参数结构速查

调用参数即 HTTP JSON body，无客户端配置对象：

| 场景 | body 结构 |
|------|----------|
| 查询（LIST/GET） | QueryParam：`conditions` / `returnFields` / `pageStart` / `pageSize` / ... |
| DML（CREATE/UPDATE/DELETE） | ManipulationParam：`conditions`（单条）或 `batchConditions`（批量） |

字段完整说明见 [Python 调用模板 §4](./python-client-template.md)。

## 响应格式

```json
{
  "code": "DPN-OLTP-COMMON-000",
  "message": "success",
  "results": [{ "field1": "value1", "field2": "value2" }],
  "totalNum": 100,
  "sessionId": "...",
  "executeContext": { "requestId": "...", "executeTime": 113 }
}
```

| 字段 | 说明 |
|------|------|
| `code` | 业务码，`"DPN-OLTP-COMMON-000"` 表示成功 |
| `message` | 错误信息 |
| `results` | 业务数据列表 |
| `totalNum` | 数据总数（需设置 `returnTotalNum: true`） |
| `executeContext.requestId` | 请求追踪 ID |

## get-data-service-api-document 关键返回字段

| 字段 | 含义 | 用途 |
|------|------|------|
| `GroupId` / `GroupName` | API 分组 | 构造调用路径 |
| `Name` | API 名称 | 构造调用路径 |
| `RequestMethod` | HTTP 方法：0=GET, 1=POST | 确定请求方法 |
| `Protocol` | 协议类型 | HTTP/HTTPS |
| `PublicParamList` | 公共参数 | 内置网关的 appkey/appsecret |
| `RequestParamList` | 业务请求参数 | 构造请求参数 |
| `ResponseParamList` | 响应参数 | 解析返回数据 |
| `IsPagedQuery` | 是否分页 | 仅辅助；**不能单独定 methodType**（`get` 也可能为 `true`），methodType 按 API 操作类型定 |
| `CacheTime` | 缓存时间 | 缓存策略参考 |
