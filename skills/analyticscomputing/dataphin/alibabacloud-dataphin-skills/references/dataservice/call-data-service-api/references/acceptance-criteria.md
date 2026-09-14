# 验收标准：数据服务 API 调用

## 调用方式

- Python >= 3.9，脚本及工程内复用只依赖标准库；不需要 SDK 或 requests。
- `call`、`async-call`、`sse` 和各参数帮助可用，参数及默认值与历史脚本一致。
- AppKey/AppSecret 从环境变量读取；会话标记由 `SKILL_SESSION_ID` 注入普通 user-agent。
- 签名头清单不包含 x-ca-signature 或 x-ca-signature-headers；JSON 请求不添加 Content-MD5；path 和 query 原样参与签名。
- 模板复用同一 Gateway，不包含另一套手动签名客户端。

## 业务规则保留

- 应用查找、AppKey 字符串处理、AppKeyStr、已授权 returnFields、网关发现流程保持有效。
- methodType 不仅由 IsPagedQuery 推断；LIST/GET/CREATE/UPDATE/DELETE 的路径映射不变。
- stage 为 RELEASE/PRE，env 为 PROD/PRE；QueryParam 和 ManipulationParam 字段保留。
- 同步调用检查 HTTP 200 和业务码 DPN-OLTP-COMMON-000；LIST 读 results，GET 读 result，DML 按 API 文档验证。
- 异步调用保留无 jobId 的同步返回、轮询、分页合并和 finally 关闭任务；SSE 逐帧输出 JSON。
- 权限错误和业务确认流程沿用当前技能说明，不改变 API 授权及发布行为。

## 离线验证

运行 `python3 -B tests/test_client.py`，使用虚构凭证和模拟连接验证签名、同步/异步/SSE，不连接云端。离线通过不代表真实环境调用已经通过。
