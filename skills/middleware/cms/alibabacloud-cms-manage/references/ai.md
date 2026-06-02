# AI Observability Module

> Global conventions (credentials, output format, error codes, command prefix, distributions) — see [../SKILL.md](../SKILL.md).
> Run `aliyun cms2 apm <subcommand> --help` for full flag lists and examples.

## Scope

Guided workflow to onboard AI applications (LLM-based services, AI Agents, custom instrumented apps) into CMS Application Monitoring. Uses `aliyun cms2` CLI to initialize APM infrastructure, retrieve access credentials, and generate framework-specific configuration.

**In-Scope**: Initialize APM infra, retrieve LicenseKey/Endpoint, register app services, generate startup configuration for all supported AI frameworks.

**Out-of-Scope**: Model fine-tuning or training observability; GPU monitoring (see `cloud-acs-ecs-gpu` addon).

---

## Execution Safety Rules

Follow the same Two-Phase Execution Protocol as [apm.md — Execution Safety Rules](apm.md#execution-safety-rules).

**Operations that do NOT require confirmation** (execute directly):
- Read-only commands: `get`, `list`, `--help`
- CMS backend resource creation: `apm configuration create`, `apm service create`
- Retrieving credentials: `apm configuration get`
- Fetching addon templates: `integration addon get`

**Operations that REQUIRE confirmation** (must use Two-Phase Protocol):
- Deleting service records: `apm service delete`
- Modifying user application startup scripts or Dockerfiles

---

## Supported Frameworks

| Framework | Addon Name | Protocols | Underlying Agent |
|-----------|-----------|-----------|-----------------|
| **Dify** | `ai-dify` | opentelemetry | Dify 控制台内置 OTel 配置 |
| **LangChain/LangGraph** | `ai-langchain-langgraph` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **DashScope** | `ai-dashscope` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **AgentScope** | `ai-agentscope` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **OpenAI** | `ai-openai` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **Coze** | `ai-coze` | arms-ecs, arms-ack, opentelemetry | Golang（arms-ecs: instgo, arms-ack: ack-onepilot） |
| **OpenClaw** | `ai-openclaw` | opentelemetry | 专用 installer 脚本 |
| **CoPaw** | `ai-copaw` | opentelemetry | 专用 installer 脚本 |
| **Hermes** | `ai-hermes` | opentelemetry | 专用 installer 脚本 |
| **自定义埋点** | `ai-custom-instrumentation` | agent-extension, manual | ARMS 探针扩展 / 手动 OTel SDK |

**Protocol legend**:
- `arms` — 自研 Python Agent (通用环境), serviceType = `TRACE`
- `arms4cs` — 自研 Python Agent (容器环境), serviceType = `TRACE`
- `arms-ecs` / `arms-ack` — 自研探针 (按部署环境区分), serviceType = `TRACE`
- `opentelemetry` — OpenTelemetry 协议, serviceType = `XTRACE`
- `agent-extension` / `manual` — 自定义埋点, serviceType = `TRACE`

---

## CLI Commands Reference

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `apm configuration create` | Initialize APM infrastructure (idempotent) | `--workspace`, `--region` |
| `apm configuration get` | Get LicenseKey, Endpoint, project | `--workspace`, `--region` |
| `apm service create` | Register application service | `--workspace`, `--region`, `--body` |
| `apm service list` | List/filter registered services | `--workspace`, `--region`, `--service-name` |
| `apm service delete` | Delete a service record | `--workspace`, `--region`, `--service-id` |
| `integration addon get` | Fetch addon template + schema | `--addon-name`, `--env-type Client` |

---

## Onboarding Workflow

### Step 1 — Gather Parameters

Collect from user:

| Parameter | How to obtain |
|-----------|---------------|
| `regionId` | Ask user (e.g., `cn-hangzhou`, `ap-southeast-1`) |
| `appName` | Ask user — the application/service name |
| `framework` | Ask user — which AI framework (Dify, LangChain, etc.) |
| `network` | Ask user — `public` or `VPC` (not needed for Dify console config) |
| `protocol` | Present available protocols from [Supported Frameworks](#supported-frameworks) and ask user to choose |

### Step 2 — Initialize APM Infrastructure

```bash
aliyun sts get-caller-identity -o json

# Build workspace name
workspace=default-cms-{AccountId}-{regionId}

# Initialize (idempotent)
aliyun cms2 apm configuration create --workspace {workspace} --region {regionId}
```

### Step 3 — Get Credentials

```bash
aliyun cms2 apm configuration get --workspace {workspace} --region {regionId} -o json
```

Extract from response:
- `entryPointInfo.authToken` → `{LicenseKey}`
- `entryPointInfo.publicDomain` → `{publicEndpoint}`
- `entryPointInfo.privateDomain` → `{vpcEndpoint}`
- `entryPointInfo.project` → `{project}`

### Step 4 — Register Application Service

```bash
aliyun cms2 apm service create --workspace {workspace} --region {regionId} \
  --body '{
    "serviceName": "{appName}",
    "serviceType": "{serviceType}",
    "attributes": [
      {"key": "language", "value": "{language}"}
    ]
  }'
```

**serviceType mapping**: see [Protocol legend](#supported-frameworks).

**language attribute**: based on the framework's underlying agent (e.g., `python` for LangChain/LangGraph/DashScope/AgentScope/OpenAI); refer to addon template for framework-specific values; omit if unknown.

### Step 5 — Generate Configuration

Route to the appropriate path based on user's selected `protocol` and `framework`.

#### Path A — Reuse apm.md Existing Flows (自研探针)

For protocols that correspond to existing apm.md onboarding flows, do NOT call `integration addon get`. Instead, follow the linked apm.md section directly with Step 3 credentials.

| Protocol | Framework | Follow |
|----------|-----------|--------|
| `arms` | LangChain/LangGraph, DashScope, AgentScope, OpenAI | [apm.md — Python — Aliyun Agent (aliyun-bootstrap)](apm.md#python--aliyun-agent-aliyun-bootstrap) |
| `arms4cs` | LangChain/LangGraph, DashScope, AgentScope, OpenAI | [apm.md — Python — ack-onepilot (K8s)](apm.md#python--ack-onepilot-k8s) |
| `arms-ecs` | Coze | [apm.md — Golang — instgo compile (ECS / Host)](apm.md#golang--instgo-compile-ecs--host) |
| `arms-ack` | Coze | [apm.md — Golang — ack-onepilot (K8s)](apm.md#golang--ack-onepilot-k8s) |

#### Path B — Addon Dynamic Fetch

For all other protocols (`opentelemetry`, `agent-extension`, `manual`), and for frameworks without 自研探针 support (Dify, OpenClaw, CoPaw, Hermes), use `integration addon get` to fetch the configuration template at runtime.

1. Fetch addon card:

```bash
aliyun cms2 integration addon get --addon-name {addonName} --env-type Client -o json
```

2. Extract the target protocol template:

```bash
aliyun cms2 integration addon get --addon-name {addonName} --env-type Client -o json \
  | jq -r '.data.codeTemplate.codes[] | select(.name=="{protocol}") | .codeTemplate'
```

3. Render variables with Step 3 credentials:

| Template Variable | Value Source |
|-------------------|--------------|
| `{{region}}` | `{regionId}` |
| `{{LicenseKey}}` | `entryPointInfo.authToken` |
| `{{workspace}}` / `{{$context$.workspace}}` | `{workspace}` |
| `{{Project}}` | `entryPointInfo.project` |
| `{{PubDomain}}` / `{{PubAddr}}` | `entryPointInfo.publicDomain` |
| `{{VpcDomain}}` / `{{InnerAddr}}` | `entryPointInfo.privateDomain` |
| `{{serviceName}}` | `{appName}` |
| `{{version}}` | Ask user (default: `1.0.0`) |
| `{{environment}}` | Ask user (default: `production`) |
| `{{connectionType}}` | `inner` (VPC) or `public` |
| `{{exportMethod}}` | Must be selected from `schema.props.dataSource` |

4. **Interactive parameter confirmation rules**:
   - For branch/select parameters (`connectionType`, `exportMethod`, `instrumentType`, `source`), ask the user to choose explicitly with concrete options from schema `dataSource`. Do NOT auto-select or silently use defaults.
   - For `{{version}}` and `{{environment}}`, always ask user to confirm with suggested defaults.
   - If schema and template disagree on allowed values, **schema wins**.
   - Only ask for parameters that are actually referenced by the selected template branch.

5. Present rendered steps to user.

### Step 6 — Post-Onboarding Verification

```bash
aliyun cms2 apm service list --workspace {workspace} --service-name {appName} --region {regionId} -o json
```

**Expected**: service appears with correct `serviceType` and `serviceName`. After restarting the application with the generated configuration, data should appear in CMS 2.0 console within 2-3 minutes.

---

## Framework-Specific Notes

### Dify

- Dify >= 1.6.0 内置 OTel 追踪能力，在 Dify 控制台 > 监测 > 追踪应用性能 > 云监控 中配置 LicenseKey 和 Endpoint 即可，无需安装任何探针
- 仅 `opentelemetry` 协议，通过 addon 模板获取配置参数填入 Dify 控制台
- 不需要 `aliyun-instrument` 或任何 agent 安装步骤

### Coze

- 底层为 Golang 应用，协议名称与其他框架不同：`arms-ecs` / `arms-ack`（而非 `arms`/`arms4cs`）
- `arms-ecs` → 复用 [apm.md Golang — instgo](apm.md#golang--instgo-compile-ecs--host)
- `arms-ack` → 复用 [apm.md Golang — ack-onepilot](apm.md#golang--ack-onepilot-k8s)
- `opentelemetry` → 通过 addon 模板获取 Go OTel Agent 配置

### OpenClaw / CoPaw / Hermes

- 各有专用 installer 脚本（`curl -fsSL ... | bash`），脚本自动安装对应可观测插件
- 参数通过 `--x-arms-license-key`、`--serviceName`、`--endpoint` 传入
- 仅 `opentelemetry` 协议，按 addon 模板输出即可

### LangChain/LangGraph / DashScope / AgentScope / OpenAI

- `arms` / `arms4cs` 协议 → 复用 [apm.md Python — Aliyun Agent](apm.md#python--aliyun-agent-aliyun-bootstrap)，auto-instruments LLM calls, tool use, agent traces
- `opentelemetry` 协议 → 通过 addon 模板获取 OTel SDK 配置

### 自定义埋点

- `agent-extension`: 基于 ARMS 探针扩展（`loongsuite-util-genai`），需先接入 Python 自研探针
- `manual`: 手动 OTel SDK 埋点，不依赖 ARMS 探针
- 两种协议均通过 addon 模板获取具体代码示例

---

## Offboarding / Uninstall

Offboarding is the reverse of onboarding: **remove agent configuration from the application first, then clean up CMS-side resources**.

| Step | Action | Command / Procedure |
|------|--------|---------------------|
| 1 | Remove agent from application | Reverse of Step 5: remove agent wrapper、环境变量、Dify 控制台禁用追踪、或 uninstall 插件脚本（视框架而定） |
| 2 | Restart application | Restart without agent params |
| 3 | Verify agent stopped | Confirm no new data appears in CMS console after 3-5 minutes |
| 4 | Delete service record (**requires user confirmation**) | `aliyun cms2 apm service delete --workspace {workspace} --service-id {serviceId} --region {regionId}` |

---

## Error Handling & Fallback

| Error | Cause | Resolution |
|-------|-------|------------|
| `addon not found` | Addon name incorrect or not yet available in region | Verify addon name from [Supported Frameworks](#supported-frameworks); for Python-based frameworks fallback to [apm.md Python section](apm.md#python--aliyun-agent-aliyun-bootstrap) |
| `workspace not found` | APM infrastructure not initialized | Run `apm configuration create` first (Step 2) |
| `service already exists` | Duplicate serviceName | Use `apm service list` to check, then update or delete existing service |
| `InvalidJSON` | Malformed `--body` | Validate with `jq . <<<'<value>'` before passing to CLI |
| Template variable unresolved | `{{var}}` in rendered output | Check variable mapping table in Step 5; ensure all credentials from Step 3 are substituted |
