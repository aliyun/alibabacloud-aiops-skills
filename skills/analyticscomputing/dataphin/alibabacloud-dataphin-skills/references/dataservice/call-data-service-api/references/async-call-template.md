# 异步调用模板（零依赖，无需 SDK）

大数据量查询（通常 > 30 秒）走异步：网关先返回 `jobId`，再轮询状态、分批取结果、关闭任务。

## 1. 首选：脚本一条命令

```bash
python3 scripts/call-data-service-api.py async-call \
  --api-id 10083 --method LIST --params-file query.json \
  --poll-interval 1 --timeout 600
```

脚本已内置完整流程（提交 → 轮询 → 合并分页 → `closeJob`），无需自己管理 `jobId`。

## 2. 异步调用协议

```
1. POST /{verb}/{apiId}?appKey=..&env=..        → 提交请求
2. 响应含 jobId？
   ├─ 无 → 网关直接返回同步结果（数据量小时）
   └─ 有 → 进入轮询
3. POST /getJobStatus?appKey=..&env=..&fetchSize=1000&jobId=..
   ├─ status=1 RUNNING   → 继续轮询
   ├─ status=2 SUCCESS   → 转步骤 4
   ├─ status=3 FAILED    → /getJobExecutionLog 取错误日志
   └─ 4 CANCELLED / 5 EXPIRED / 6-7 CLOSED_* → 结束
4. POST /getJobResult?...&jobId=..              → 反复调用直到 results 为空，逐批合并
5. POST /closeJob?...&jobId=..                  → 释放资源（务必执行）
```

| 端点 | 用途 |
|------|------|
| `/getJobStatus` | 查询任务状态 |
| `/getJobResult` | 分批拉取结果（需循环至空批次） |
| `/getJobExecutionLog` | 失败时取执行日志 |
| `/closeJob` | 关闭任务（正常/异常都要调） |
| `/cancelJob` | 取消运行中的任务 |

> 这些端点的 query 参数固定为 `appKey` / `env` / `fetchSize` / `jobId`，签名方式与业务调用完全相同（见 [Python 调用模板 §1](./python-client-template.md)）。

## 3. 嵌入自有工程时的实现

```python
import json
import time

SUCCESS_CODE = "DPN-OLTP-COMMON-000"


def async_call(gw, api_id, method, params, poll_interval=1.0, timeout=300):
    """异步调用并轮询结果。gw 为 python-client-template.md 中的 DataphinGateway 实例。"""
    resp = gw.call(api_id, method, params)
    job_id = resp.get("jobId")
    if not job_id:
        return resp  # 网关直接返回同步结果

    def job(endpoint):
        path = (f"{endpoint}?appKey={gw.app_key}&env={gw.env}"
                f"&fetchSize=1000&jobId={job_id}")
        return gw.post(path, {})  # 与业务调用同一套签名逻辑

    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            time.sleep(poll_interval)
            status_resp = job("/getJobStatus")
            if status_resp.get("code") != SUCCESS_CODE:
                continue  # 生产代码应限制重试次数
            status = status_resp.get("result", {}).get("status")
            if status == 1:                       # RUNNING
                continue
            if status == 2:                       # SUCCESS
                merged = None
                while True:                       # 分批拉取直到空批次
                    batch = job("/getJobResult")
                    if merged is None:
                        merged = batch
                        if batch.get("code") != SUCCESS_CODE or not batch.get("results"):
                            return merged
                        continue
                    if batch.get("code") != SUCCESS_CODE or not batch.get("results"):
                        return merged
                    merged["results"].extend(batch["results"])
            if status == 3:                       # FAILED
                log = job("/getJobExecutionLog")
                raise RuntimeError(f"异步任务失败: {json.dumps(log, ensure_ascii=False)}")
            return resp                           # CANCELLED / EXPIRED / CLOSED_*
        raise TimeoutError(f"异步任务超时({timeout}s)，jobId={job_id}")
    finally:
        job("/closeJob")                          # 无论成功失败都要关闭
```

## 4. 使用要点

1. **何时用异步**：大数据量查询、耗时操作（通常 > 30 秒）；小数据量网关会直接同步返回
2. **轮询间隔**：建议 1-3 秒；过密会给网关造成压力
3. **超时**：默认 300s，大数据量可设 600-1800s（脚本 `--timeout`）
4. **务必关闭任务**：`closeJob` 放在 `finally`，否则任务会占用服务端资源直到过期
5. **分页合并**：`getJobResult` 必须循环调用至空批次，只调一次会丢数据
6. **失败排查**：`status=3` 时先看 `/getJobExecutionLog`，里面是引擎侧真实错误
7. **Impala 引擎**：轮询超时按引擎实际耗时放宽，`fetchSize` 固定 1000
