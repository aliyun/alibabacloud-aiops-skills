# 文档入口（sysom-diagnosis）

避免在 **permission** 与 **诊断契约** 之间来回重复叙述：按主题 **只读一处**。

| 需求 | 文档 |
|------|------|
| **precheck、AK/RAM Role、三要素、场景 A-K、凭证/开通类问题** | [openapi-permission-guide.md](./openapi-permission-guide.md) |
| **RAM 最小权限、Action 映射、策略模板（可直接用于自定义策略）** | [ram-policies.md](./ram-policies.md) |
| **诊断本机/远程（必做）、InvokeDiagnosis 请求体、`region`/`instance`、元数据补全；对客 CLI 为 `memory … --deep-diagnosis`（维护者 OpenAPI 直调见同文）** | [invoke-diagnosis.md](./invoke-diagnosis.md) |
| **深度诊断业务错误**（如 `InvalidParameter`、`instance not found`） | [invoke-diagnosis.md](./invoke-diagnosis.md) 与本节下说明；以 CLI 输出 **`error`** / **`data.diagnosis_target`** / **`data.read_next`** / **`data.remediation`** 为准 |
| **ECS 元数据 URL、常用 curl、IMDS** | [metadata-api.md](./metadata-api.md) |
| **各 `service_name` 的 `params` 字段** | [diagnoses/README.md](./diagnoses/README.md) → 对应 `*.md` |
| **内存域快速排查入口归纳** | [memory-routing.md](./memory-routing.md) |
| **技能能力总览表** | [SKILL.md](../SKILL.md) |

Agent 应优先根据 **`precheck` JSON** 的 `data.guidance`（及 `data.remediation`）处理 **凭证与开通**；**深度诊断**（`memory … --deep-diagnosis`）返回的业务错误对照 [invoke-diagnosis.md](./invoke-diagnosis.md) 与 **`error` / `data`**。**不要在对话中收集 AccessKey/Secret**；认证失败时引导用户在终端执行 **`configure`**：在 **`sysom-diagnosis/`**（技能根）执行 **`./scripts/osops.sh configure`**。若当前 Bash 无 PTY、无法交互输入，见 **`data.guidance.credential_policy`**。
