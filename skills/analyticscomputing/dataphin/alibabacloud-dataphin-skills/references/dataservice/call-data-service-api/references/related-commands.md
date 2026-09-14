# API 调用参考（call-data-service-api）

> 本 Skill 使用附带脚本调用数据服务网关，仅依赖 Python 标准库；元信息查询仍走下列管理面 CLI。

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

## 查询参数（QueryParam）字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `conditions` | dict | 视 API | 查询条件，key=字段名 value=值（IN 类型用列表） |
| `returnFields` | list | 否 | 返回字段列表，空列表返回所有有权限字段 |
| `orderBys` | list | 否 | 排序字段，如 `[{"field": "id", "order": "ASC"}]` |
| `pageStart` | int | 否 | 分页起始位置（仅 LIST 类型生效） |
| `pageSize` | int | 否 | 每页条数（仅 LIST 类型生效） |
| `useModelCache` | bool | 否 | 是否使用模型缓存 |
| `useResultCache` | bool | 否 | 是否使用结果缓存 |
| `keepColumnCase` | bool | 否 | 是否保持字段大小写（建议 True） |
| `returnTotalNum` | bool | 否 | 是否返回总数（有性能损耗） |
| `apiVersion` | str | 否 | API 版本号（仅开发环境支持） |
| `accountType` | str | 否 | 代理账号类型 |
| `delegationUid` | str | 否 | 代理账号 ID |

## DML 操作参数（ManipulationParam）字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `conditions` | dict | 视 API | 单条操作的条件，key=字段名 value=值 |
| `batchConditions` | list | 视 API | 批量操作的条件列表，每个元素为 dict |

> **注意**：如果数据量是"单条"，不要将 conditions 放进 batchConditions。

## API 路径与返回值

脚本按 `--method` 映射到 `/{methodType}/{apiId}?appKey={appKey}&env={env}`；LIST/GET/CREATE/UPDATE/DELETE 对应 list/get/create/update/delete。LIST 的结果在 `results`，GET 的结果在 `result`；DML 按目标 API 文档处理。

签名头规范及工程内复用见 [Python 调用模板](./python-client-template.md)。
