# AI Observability Module

> Global conventions (credentials, Observability / User-Agent, output format, error codes, command prefix) - see [../SKILL.md](../SKILL.md).
> RAM permissions - see [ram-policies.md](ram-policies.md).
> Run `aliyun cms2 apm <subcommand> --help` for full flag lists and examples.

## Scope

Guided workflow to onboard AI applications (LLM-based services, AI Agents, custom instrumented apps) into AgentLoop application observability. Uses `aliyun cms2` CLI to initialize APM infrastructure, retrieve access credentials, and generate framework-specific configuration.

**In-Scope**: Initialize APM infra, retrieve LicenseKey/Endpoint, register app services, generate startup configuration for all supported AI frameworks.

**Out-of-Scope**: Model fine-tuning or training observability; GPU monitoring (see `cloud-acs-ecs-gpu` addon); general CloudMonitor (CMS) management; `default-cms-*` or other non-`agentloop-*` workspaces; alerts, RUM, Prometheus rules, and other non-onboarding CMS features.

---

## Workspace Mandatory Rules

> **CRITICAL** - AgentLoop AI onboarding requires an explicit AgentLoop workspace from the user.

1. **Always ask user to provide `workspace`**: Never auto-build workspace as `default-cms-{AccountId}-{regionId}`.
2. **Workspace format is `agentloop-{32-char-code}`**: If missing, run `aliyun cms2 workspace list -o json` and reuse the first `agentloop-[0-9a-f]{32}` match. On quota 403/400, reuse existing `agentloop-*` workspace and continue.
3. **Do NOT proceed without a valid workspace**: All APM commands require the user-provided or discovered `agentloop-*` workspace.

---

## Execution Safety Protocol

Follow the same Two-Phase Execution Protocol as [apm.md - Execution Safety Protocol](apm.md#execution-safety-protocol).

**Operations that do NOT require confirmation** (execute directly):
- Read-only commands: `get`, `list`, `--help`
- AgentLoop platform resource creation: `apm configuration create`, `apm service create`
- Retrieving credentials: `apm configuration get`
- Fetching addon templates: `integration addon get`

**Operations that REQUIRE confirmation** (must use Two-Phase Protocol):
- Deleting service records: `apm service delete`
- Modifying user application startup scripts or Dockerfiles

---

## Supported Frameworks

| Framework | Addon Name | Protocols | Underlying Agent |
|-----------|-----------|-----------|-----------------|
| **Dify** | `ai-dify` | opentelemetry | Dify console built-in OTel configuration |
| **LangChain/LangGraph** | `ai-langchain-langgraph` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **DashScope** | `ai-dashscope` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **AgentScope** | `ai-agentscope` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **OpenAI** | `ai-openai` | arms, arms4cs, opentelemetry | Python aliyun-bootstrap |
| **Coze** | `ai-coze` | arms-ecs, arms-ack, opentelemetry | Golang (arms-ecs: instgo, arms-ack: ack-onepilot) |
| **OpenClaw** | `ai-openclaw` | opentelemetry | dedicated installer script |
| **CoPaw** | `ai-copaw` | opentelemetry | dedicated installer script |
| **Hermes** | `ai-hermes` | opentelemetry | dedicated installer script |
| **custom instrumentation** | `ai-custom-instrumentation` | agent-extension, manual | ARMS agent extension / manual OTel SDK |

**Protocol legend**:
- `arms` - proprietary Python agent (general environment), serviceType = `TRACE`
- `arms4cs` - proprietary Python agent (container environment), serviceType = `TRACE`
- `arms-ecs` / `arms-ack` - proprietary agent (by deployment environment), serviceType = `TRACE`
- `opentelemetry` - OpenTelemetry protocol, serviceType = `XTRACE`
- `agent-extension` / `manual` - custom instrumentation, serviceType = `TRACE`

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

### Step 1 - Gather Parameters

Collect from user:

| Parameter | How to obtain |
|-----------|---------------|
| `workspace` | **Ask user explicitly**, or discover via `aliyun cms2 workspace list` (first `agentloop-[0-9a-f]{32}` match). On quota 403/400, reuse existing `agentloop-*` workspace. Format: `agentloop-{32-char-code}`. Do NOT auto-derive. |
| `regionId` | Ask user (e.g., `cn-hangzhou`, `ap-southeast-1`), or derive from cluster metadata / kubeconfig context when applicable |
| `appName` | Ask user - the application/service name |
| `framework` | Ask user - which AI framework (Dify, LangChain, etc.) |
| `network` | Ask user - `public` or `VPC` (not needed for Dify console config) |
| `protocol` | Present available protocols from [Supported Frameworks](#supported-frameworks) and ask user to choose |

### Step 2 - Initialize APM Infrastructure

```bash
aliyun sts get-caller-identity --force -o json

# Use user-provided workspace (format: agentloop-{32-char-code})
# workspace={userProvidedWorkspace}

# Initialize (idempotent)
aliyun cms2 apm configuration create --workspace {workspace} --region {regionId}
```

### Step 3 - Get Credentials

```bash
aliyun cms2 apm configuration get --workspace {workspace} --region {regionId} -o json
```

Extract from response:
- `entryPointInfo.authToken` -> `{LicenseKey}`
- `entryPointInfo.publicDomain` -> `{publicEndpoint}`
- `entryPointInfo.privateDomain` -> `{vpcEndpoint}`
- `entryPointInfo.project` -> `{project}`

### Step 4 - Register Application Service

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

### Step 5 - Generate Configuration

Route to the appropriate path based on user's selected `protocol` and `framework`.

#### Path A - Reuse apm.md Existing Flows (proprietary agent)

For protocols that correspond to existing apm.md onboarding flows, do NOT call `integration addon get`. Instead, follow the linked apm.md section directly with Step 3 credentials.

| Protocol | Framework | Follow |
|----------|-----------|--------|
| `arms` | LangChain/LangGraph, DashScope, AgentScope, OpenAI | [apm.md - Python - Aliyun Agent (aliyun-bootstrap)](apm.md#python--aliyun-agent-aliyun-bootstrap) |
| `arms4cs` | LangChain/LangGraph, DashScope, AgentScope, OpenAI | [apm.md - Python - ack-onepilot (K8s)](apm.md#python--ack-onepilot-k8s) |
| `arms-ecs` | Coze | [apm.md - Golang - instgo compile (ECS / Host)](apm.md#golang--instgo-compile-ecs--host) |
| `arms-ack` | Coze | [apm.md - Golang - ack-onepilot (K8s)](apm.md#golang--ack-onepilot-k8s) |

#### Path B - Addon Dynamic Fetch

For all other protocols (`opentelemetry`, `agent-extension`, `manual`), and for frameworks without proprietary agent support (Dify, OpenClaw, CoPaw, Hermes), use `integration addon get` to fetch the configuration template at runtime.

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

### Step 6 - Post-Onboarding Verification

```bash
aliyun cms2 apm service list --workspace {workspace} --service-name {appName} --region {regionId} -o json
```

**Expected**: service appears with correct `serviceType` and `serviceName`. After restarting the application with the generated configuration, data should appear in AgentLoop console within 2-3 minutes.

---

## Framework-Specific Notes

### Dify

- Dify >= 1.6.0 has built-in OTel tracing. Configure LicenseKey and Endpoint in Dify console > Monitoring > Trace application performance > AgentLoop. No agent installation is required.
- Only the `opentelemetry` protocol is supported. Fetch configuration parameters from the addon template and enter them in the Dify console.
- No `aliyun-instrument` or other agent installation step is required.

### Coze

- Underlying runtime is Golang. Protocol names differ from other frameworks: `arms-ecs` / `arms-ack` (not `arms`/`arms4cs`).
- `arms-ecs` -> Reuse [apm.md Golang - instgo](apm.md#golang--instgo-compile-ecs--host)
- `arms-ack` -> Reuse [apm.md Golang - ack-onepilot](apm.md#golang--ack-onepilot-k8s)
- `opentelemetry` -> Fetch Go OTel Agent configuration from the addon template.

### OpenClaw / CoPaw / Hermes

- Each framework provides a dedicated installer script (`curl -fsSL ... | bash`) that installs the corresponding observability plugin.
- Pass parameters via `--x-arms-license-key`, `--serviceName`, and `--endpoint`.
- Only the `opentelemetry` protocol is supported. Render output from the addon template.

### LangChain/LangGraph / DashScope / AgentScope / OpenAI

- `arms` / `arms4cs` protocols -> Reuse [apm.md Python - Aliyun Agent](apm.md#python--aliyun-agent-aliyun-bootstrap); auto-instruments LLM calls, tool use, and agent traces.
- `opentelemetry` protocol -> Fetch OTel SDK configuration from the addon template.

### custom instrumentation

- `agent-extension`: Based on the ARMS agent extension (`loongsuite-util-genai`). Requires the proprietary Python agent to be installed first.
- `manual`: Manual OTel SDK instrumentation without depending on the ARMS agent.
- Both protocols provide concrete code examples via the addon template.

---

## Offboarding / Uninstall

Offboarding is the reverse of onboarding: **remove agent configuration from the application first, then clean up AgentLoop platform resources**.

| Step | Action | Command / Procedure |
|------|--------|---------------------|
| 1 | Remove agent from application | Reverse of Step 5: remove the agent wrapper, environment variables, disable tracing in the Dify console, or uninstall the plugin script (framework-specific) |
| 2 | Restart application | Restart without agent params |
| 3 | Verify agent stopped | Confirm no new data appears in AgentLoop console after 3-5 minutes |
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
