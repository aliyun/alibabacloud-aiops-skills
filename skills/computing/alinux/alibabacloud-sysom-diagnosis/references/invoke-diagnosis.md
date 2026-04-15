# InvokeDiagnosis（契约、CLI 与前置）

> **本文件**说明 **InvokeDiagnosis** 契约、**本机/远程**约定与 **CLI 选项**。Agent 主路径为 `memory … --deep-diagnosis`。各诊断专有 `params` 见 [diagnoses/](./diagnoses/)。

**权限与开通**：远程路径在发 OpenAPI 前会**内建**与 **`osops precheck` 相同的环境检查**；亦可单独运行 precheck 自检。三要素与场景矩阵见 [openapi-permission-guide.md](../shared/references/openapi-permission-guide.md)。

**本地优先**：未明确要远程时，先跑本机 quick（见 [memory-routing.md](./memory-routing.md)）。下表「诊断目标」仅适用于远程深度诊断。

## 诊断目标（远程深度诊断前必做，所有 `service_name` 相同）

**在每次发起远程深度诊断之前**（`memory … --deep-diagnosis`），Agent 须先请用户确认诊断范围：

| 用户选择 | 命令行 | 说明 |
|----------|--------|------|
| **A — 本机** | 不传 `--region`/`--instance`，CLI 从元数据补全 | Agent 勿自行 curl 元数据填参数 |
| **B — 远程实例** | 用户提供 `--region` 与 `--instance` | 禁止用本机元数据冒充远程实例 |

失败重试、换诊断类型时，**仍遵循上表**：本机继续省略两参数；远程继续用用户提供的 region/instance。

## 请求体结构（InvokeDiagnosis）

| 字段 | 说明 |
|------|------|
| `service_name` | 字符串，诊断类型，与 OpenAPI **`diagnosis_item_config.items`** 的键一致。 |
| `channel` | 字符串，当前一般为 **`ecs`**（与 CLI `--channel ecs` 一致）。 |
| `params` | **字符串**：内容为 **JSON** 文本；反序列化后为对象，通常需 **`region`**、**`instance`** 以定位 ECS；**各诊断特有字段**见 [diagnoses/](./diagnoses/) 下对应 `service_name` 专文。 |

经 OpenAPI **`invoke_diagnosis`** 转发时，服务端会把 **`uid`** 合并进 **`params`**（来自请求上下文），一般无需在 `params` 里重复手填。

**前置条件**：目标 ECS 须运行中、已装云助手；须在 **SysOM / ECS 控制台** 对目标实例完成 **诊断授权**（勿使用已废弃的 OpenAPI 授权接口）；账号侧需 **AliyunServiceRoleForSysom** 等服务关联角色（细则见阿里云 SysOM 产品说明）。

## CLI 与内部 Invoke（原 `diagnosis invoke`）

**对外**：`./shared/scripts/osops memory <子命令> --deep-diagnosis …`，选项如下：

| 选项 | 说明 |
|------|------|
| `--region` / `--instance` | 合并进 `params`；见下节 **元数据补全**。 |
| `--timeout` | 轮询 **GetDiagnosisResult** 的总等待秒数，默认 `300`；长任务需加大。 |
| `--poll-interval` | 轮询间隔秒数，默认 `1`。 |
| `--verbose-envelope` | 成功时保留完整 **`agent.summary`**；默认紧凑（省 token），业务载荷见 **`data.remote`**。 |

**结果**：成功时见 `data.routing`、`data.remote`（`remote.result`）、`agent.findings`。

**失败时**：`error.code`/`error.message` 为标准业务码；环境类失败可能返回与 precheck 同构的信封；业务失败时 `data` 含 `remediation` 等引导。


### 本机元数据补全

未传 `--region`/`--instance` 时，CLI 会请求 ECS 元数据（`100.100.100.200`）补全。若 `error.code` 为 `Sysom.InvalidParameter`、`instance not found in ecs`，常见原因是 **AK 所属账号与实例不匹配**（含跨账号）。precheck 通过仅表示凭证可调接口，不保证实例对齐。

元数据详见 [metadata-api.md](../shared/references/metadata-api.md)。

## 按诊断类型的参数

见 [diagnoses/README.md](./diagnoses/README.md) 及对应 `*.md` 专文。

## 相关入口

- [SKILL.md](../SKILL.md) — 能力总览表
- [openapi-permission-guide.md](../shared/references/openapi-permission-guide.md) — 权限与 precheck
