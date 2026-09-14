# 异步调用（零依赖脚本）

复用 [`call-data-service-api.py`](../scripts/call-data-service-api.py) 的 `async-call`，不再安装 SDK 或手动实现轮询客户端。

## 使用方式

在本 Skill 目录运行；所有变量来自已确认的业务参数，`query.json` 保存对应 API 的请求 JSON。

```bash
SKILL_SESSION_ID="$SESSION_ID" python3 scripts/call-data-service-api.py async-call \
  --api-id "$API_ID" --method "$METHOD" --params-file query.json \
  --stage "$STAGE" --env "$DATA_ENV" --scheme "$SCHEME" --port "$PORT"
```

默认轮询间隔 1 秒、超时 300 秒，可用 `--poll-interval` 和 `--timeout` 调整，二者单位均为秒。原有 SDK 配置中的轮询间隔以毫秒表示，迁移时需换算。凭证及网关地址仍从 `DATAPHIN_APP_KEY`、`DATAPHIN_APP_SECRET`、`DATAPHIN_GATEWAY_HOST` 读取。

## 调用流程

1. POST 到 `/{methodType}/{apiId}?appKey={appKey}&env={env}`，提交业务 JSON。
2. 没有 jobId 时直接返回同步响应；有 jobId 时开始轮询 `/getJobStatus`。
3. RUNNING 继续等待；SUCCESS 循环读取 `/getJobResult`，合并分页，直到 results 为空。
4. FAILED 获取 `/getJobExecutionLog` 并报错；超时抛出超时错误。
5. `finally` 尝试 `/closeJob`；关闭失败记录诊断，不覆盖原始异常。

| 端点 | 用途 |
|------|------|
| `/getJobStatus` | 查询状态：1 RUNNING / 2 SUCCESS / 3 FAILED / 4 CANCELLED / 5 EXPIRED / 6 CLOSED_BY_SUCCESS / 7 CLOSED_BY_FAILED |
| `/getJobResult` | 分批读取结果，fetchSize 默认 1000 |
| `/getJobExecutionLog` | 读取失败日志 |
| `/closeJob` | 结束轮询后尝试关闭任务 |

任务请求的 query 参数为 `appKey`、`env`、`fetchSize`、`jobId`；路径与查询串保持原样签名。脚本不新增取消任务的子命令；保留历史状态处理行为。

## 响应与工程内复用

业务成功码仍为 `DPN-OLTP-COMMON-000`。LIST 检查 `results`，GET 检查 `result`；授权字段、stage/env 和业务 JSON 按当前 API 文档确定。

工程内先按 [Python 调用模板](./python-client-template.md) 加载同一个 Gateway，再调用 `gateway.async_call(api_id, method, params, poll_interval=1.0, timeout=300)`。
