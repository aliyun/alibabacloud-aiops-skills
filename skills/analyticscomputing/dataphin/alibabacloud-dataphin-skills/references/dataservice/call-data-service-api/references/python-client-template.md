# Python 调用模板（零依赖，无需 SDK）

> 首选：直接用本 Skill 附带脚本 [`scripts/call-data-service-api.py`](../scripts/call-data-service-api.py)，
> 无需安装任何 SDK / 三方库。本文给出**签名规范**与**最小可用客户端**，供需要嵌入自有工程时照抄。

## 1. 签名规范（HMAC-SHA256，阿里云 API 网关规范）

数据服务网关调用 = **POST** + JSON body + 以下签名头。签名串按顺序拼接：

```
POST\n
{accept}\n
{content-md5}\n          ← JSON body 留空；仅 application/octet-stream 才计算
{content-type}\n
{date}\n
{按字典序的 x-ca-* 头，每行 "k:v\n"}
{path}                   ← 原样，含 query string，不排序不归一化
```

签名值 = `base64(HMAC-SHA256(string_to_sign, appSecret))`，放入 `x-ca-signature`。

| Header | 值 | 是否参与签名 |
|--------|-----|------|
| `accept` | `application/json`（SSE 为 `text/event-stream`） | ✅ |
| `content-type` | `application/json` | ✅ |
| `content-md5` | JSON body 时为空串 | ✅（空值） |
| `date` | 当前时间字符串（内容不限，两端一致即可） | ✅ |
| `x-ca-key` | AppKey | ✅ |
| `x-ca-nonce` | UUID4 | ✅ |
| `x-ca-timestamp` | 毫秒时间戳 | ✅ |
| `x-ca-stage` | `RELEASE` / `PRE` | ✅ |
| `x-ca-signature-method` | `HmacSHA256` | ✅ |
| `x-ca-signature-headers` | 上述 5 个 `x-ca-*` 键名，逗号分隔、字典序 | ❌ |
| `x-ca-signature` | 签名值 | ❌ |
| `user-agent` | 可观测标记（见 SKILL.md §7） | ❌ |

> **⚠️ 三个必踩的坑**
> 1. **`x-ca-signature-headers` 不能包含 `x-ca-signature` 自身**：先算清单、再算签名、最后塞签名值，顺序写反 → `SignatureDoesNotMatch`。
> 2. **签名的 path 必须与实际请求行完全一致**：query 直接拼在 path 里，不要用 `requests` 的 `params=`（可能重排/重编码）。
> 3. **JSON body 不参与签名**，不要给 JSON 请求加 `content-md5`；`content-type` 不要带 `; charset=UTF-8`。

## 2. 最小可用客户端（requests 版，约 60 行）

```python
#!/usr/bin/env python3
"""Dataphin 数据服务 API 调用 — requests 版最小客户端"""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime

import requests

SUCCESS_CODE = "DPN-OLTP-COMMON-000"


class DataphinGateway:
    def __init__(self, host, app_key, app_secret, stage="RELEASE", env="PROD",
                 scheme="http", port=80):
        self.base = f"{scheme}://{host}:{port}"
        self.app_key, self.app_secret = str(app_key), app_secret
        self.stage, self.env = stage, env

    def _headers(self, path, accept="application/json"):
        headers = {
            "accept": accept,
            "content-type": "application/json",
            "date": str(datetime.now()),
            "x-ca-key": self.app_key,
            "x-ca-nonce": str(uuid.uuid4()),
            "x-ca-signature-method": "HmacSHA256",
            "x-ca-stage": self.stage,
            "x-ca-timestamp": str(int(time.time() * 1000)),
        }
        ca_keys = sorted(k for k in headers if k.startswith("x-ca-"))
        string_to_sign = (
            f"POST\n{headers['accept']}\n\n{headers['content-type']}\n{headers['date']}\n"
            + "".join(f"{k}:{headers[k]}\n" for k in ca_keys)
            + path
        )
        # 顺序关键：先 signature-headers，再 signature
        headers["x-ca-signature-headers"] = ",".join(ca_keys)
        headers["x-ca-signature"] = base64.b64encode(hmac.new(
            self.app_secret.encode(), string_to_sign.encode(), hashlib.sha256
        ).digest()).decode()
        return headers

    def post(self, path, params, accept="application/json"):
        # ⚠️ query 已拼在 path 里，不要再用 params= 传（会与签名串不一致）
        resp = requests.post(self.base + path, headers=self._headers(path, accept),
                             data=json.dumps(params), timeout=30, verify=False)
        resp.raise_for_status()
        return resp.json()

    def call(self, api_id, method, params):
        """method: LIST / GET / CREATE / UPDATE / DELETE（决定路径动词）"""
        path = f"/{method.lower()}/{api_id}?appKey={self.app_key}&env={self.env}"
        return self.post(path, params)


if __name__ == "__main__":
    gw = DataphinGateway(
        host=os.environ["DATAPHIN_GATEWAY_HOST"],
        app_key=os.environ["DATAPHIN_APP_KEY"],
        app_secret=os.environ["DATAPHIN_APP_SECRET"],
    )
    result = gw.call(10083, "LIST", {
        "conditions": {}, "returnFields": [], "pageStart": 0, "pageSize": 10,
        "keepColumnCase": True,
    })
    if result.get("code") == SUCCESS_CODE:
        # ⚠️ 结果字段随 methodType 不同：LIST → results（数组）；GET → result（单对象）
        print(f"调用成功，返回 {len(result.get('results', []))} 条数据")
    else:
        print(f"调用失败: code={result.get('code')}, message={result.get('message')}")
```

> 环境无 `requests` 时不必安装：脚本 `scripts/call-data-service-api.py` 用 `http.client` 实现，纯标准库。

## 3. DML 与流式调用

```python
# DML：method 换成 CREATE / UPDATE / DELETE，参数结构为 ManipulationParam
gw.call(10083, "CREATE", {"conditions": {"id": 1, "name": "test"}})
gw.call(10083, "DELETE", {"batchConditions": [{"id": 1}, {"id": 2}]})  # 批量
# ⚠️ 单条操作用 conditions，不要塞进 batchConditions

# 流式（SSE）：accept 改为 text/event-stream，按 \n\n 切帧、取 data: 前缀行
# 直接用脚本：python3 scripts/call-data-service-api.py sse --api-id 10085 --method GET --params '{}'
```

## 4. 查询参数（QueryParam）字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `conditions` | dict | 视 API | 查询条件，key=字段名 value=值 |
| `returnFields` | list | 否 | 返回字段列表，空列表返回所有**已授权**字段 |
| `orderBys` | list | 否 | 排序字段，如 `[{"field": "id", "order": "ASC"}]` |
| `pageStart` | int | 否 | 分页起始位置（仅 LIST 类型生效） |
| `pageSize` | int | 否 | 每页条数（仅 LIST 类型生效） |
| `useModelCache` | bool | 否 | 是否使用模型缓存 |
| `useResultCache` | bool | 否 | 是否使用结果缓存 |
| `keepColumnCase` | bool | 否 | 是否保持字段大小写（建议 True） |
| `returnTotalNum` | bool | 否 | 是否返回总数（有性能损耗） |
| `apiVersion` | str | 否 | API 版本号（仅开发环境支持） |
| `accountType` | str | 否 | 代理账号类型（USER_ID/ACCOUNT_NAME/SOURCE_USER_ID） |
| `delegationUid` | str | 否 | 代理账号 ID（使用代理模式时需配置） |

## 5. 使用要点

1. **优先用脚本**：`scripts/call-data-service-api.py` 已覆盖同步/异步/SSE，签名与官方 SDK 逐字节一致
2. **环境变量**：`DATAPHIN_APP_KEY` / `DATAPHIN_APP_SECRET` / `DATAPHIN_GATEWAY_HOST`，不硬编码、不打印
3. **method 大写**：路径动词由它决定（`LIST`→`/list/{apiId}`），猜错 → `403 ... not bind app`
4. **scheme 选择**：内置网关仅支持 HTTP；阿里云 API 网关支持 HTTPS（自签证书用 `--ignore-ssl`）
5. **stage 参数**：`RELEASE` = 生产，`PRE` = 开发；与 API 发布环境不匹配会 403
6. **Python 版本**：>= 3.9（脚本仅用标准库）
7. **时间偏差**：客户端与服务端偏差 > 15 分钟 → `TimestampExpired`
8. **IN 类型参数**：使用列表传值，如 `{"age": [10, 20, 30]}`
9. **大整数 ID**：19 位 snowflake ID 在 Python 中按字符串处理
