# Python 调用模板（零依赖）

调用和签名统一复用附带的 [`call-data-service-api.py`](../scripts/call-data-service-api.py)。无需 SDK、requests 或第三方包。

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

## 2. 在工程内复用 Gateway

将附带脚本放到工程的 `scripts/call-data-service-api.py`，以下示例保存为工程根目录的 `invoke_api.py`。凭证在会话外配置；业务变量沿用用户确认的参数。使用 `SKILL_SESSION_ID="$SESSION_ID" python3 invoke_api.py` 继承会话标记。

```python
import importlib.util
import json
import os
from pathlib import Path

script_path = Path(__file__).resolve().parent / "scripts" / "call-data-service-api.py"
spec = importlib.util.spec_from_file_location("dataphin_gateway", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

gateway = module.Gateway(
    host=os.environ["DATAPHIN_GATEWAY_HOST"],
    app_key=os.environ["DATAPHIN_APP_KEY"],
    app_secret=os.environ["DATAPHIN_APP_SECRET"],
    stage=os.environ["STAGE"], env=os.environ["DATA_ENV"],
    scheme=os.environ["SCHEME"], port=int(os.environ["PORT"]),
)
api_id, method = os.environ["API_ID"], os.environ["METHOD"]
with open("query.json", encoding="utf-8") as stream:
    params = json.load(stream)
result = gateway.call(api_id, method, params)
if result.get("code") != module.SUCCESS_CODE:
    raise RuntimeError("数据服务返回业务错误，请检查响应 code 和 message")
# LIST: result["results"]；GET: result["result"]；DML: 按 API 响应定义处理。
```

异步入口为 `gateway.async_call(api_id, method, params, poll_interval=1.0, timeout=300)`；SSE 入口为 `gateway.sse(api_id, method, params)`，迭代处理返回对象。直接复用脚本，不复制 `_headers` 或另外实现签名。

## 3. 调用参数

命令行 `--method` 为大写 LIST/GET/CREATE/UPDATE/DELETE，映射为路径小写动词。环境、协议、端口及退出码见 [命令参考](./related-commands.md)。路径保持 `/{methodType}/{apiId}?appKey={appKey}&env={env}`，methodType 不能仅由 IsPagedQuery 推断。

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
