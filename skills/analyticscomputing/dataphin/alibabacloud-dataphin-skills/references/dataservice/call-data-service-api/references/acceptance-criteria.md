# 验收标准（call-data-service-api）

## 功能验收

| 步骤 | 验收标准 |
|------|---------|
| 环境前置检查 | Python >= 3.9；脚本存在；AppKey/AppSecret/host 环境变量已设置 |
| 确认调用信息 | AppKey/AppSecret/host/apiId/method 均已获取 |
| 同步调用 | 脚本退出码 0，响应 code == "DPN-OLTP-COMMON-000"，含 results/result 字段 |
| 异步调用 | `async-call` 返回结果，脚本自动完成轮询、分页合并和 closeJob |
| 流式调用 | `sse` 逐帧输出数据 |
| 验证调用成功 | 响应业务字段符合预期 |

## 非功能验收

- [ ] SKILL.md 行数 ≤ 400
- [ ] **零依赖**：调用脚本仅用 Python 标准库，无需安装 SDK 或 requests
- [ ] 整个 Skill 目录体积 < 10 MB（不含任何 SDK 二进制）
- [ ] 调用脚本可直接运行（仅需配置环境变量）
- [ ] 可观测标记走普通 `user-agent`，不使用 `x-ca-*` 头
- [ ] AppKey/AppSecret 不硬编码、不打印，使用环境变量
- [ ] session-id 继承自父层（`SKILL_SESSION_ID`）
- [ ] 签名逻辑与官方 SDK v5.5.0 逐字节一致（已用官方 SDK 交叉校验）
- [ ] 异步调用说明脚本自动轮询、分页合并和任务关闭
- [ ] 认证错误有明确排查指引（含 SignatureDoesNotMatch 三大坑）
- [ ] Python 版本要求 >= 3.9 已说明
