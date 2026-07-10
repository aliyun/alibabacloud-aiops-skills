# Application Monitoring (APM) Module

> Global conventions (credentials, Observability / User-Agent, output format, error codes, command prefix) - see [../SKILL.md](../SKILL.md).
> RAM permissions - see [ram-policies.md](ram-policies.md).
> Run `aliyun cms2 apm <subcommand> --help` for full flag lists and examples.

## Scope

Guided workflow to onboard server-side applications into AgentLoop application observability. Uses `aliyun cms2` CLI to initialize APM infrastructure and retrieve access credentials, then generates configuration for the user's specific language and deployment method.

**In-Scope**: Initialize APM infra, retrieve LicenseKey/Endpoint, register app services, generate startup configuration for all supported languages, **auto-modify K8s Deployment YAML** (with user confirmation) via `aliyun cs` + `kubectl`.

**Out-of-Scope (this version)**: Automatic modification of ECS host startup scripts / Dockerfile; agent binary downloads; general CloudMonitor (CMS) management; `default-cms-*` or other non-`agentloop-*` workspaces; alerts, RUM, Prometheus rules, and other non-onboarding CMS features.

---

## Workspace Mandatory Rules

> **CRITICAL** - AgentLoop onboarding requires an explicit AgentLoop workspace from the user. The following rules are **absolute and non-negotiable**.

1. **Always ask user to provide `workspace`**: Never auto-build workspace as `default-cms-{userId}-{regionId}` or any other derived format.
2. **Workspace format is `agentloop-{32-char-code}`**: Prefix `agentloop-` followed by exactly 32 characters (e.g. `agentloop-2694ecf8****************1f84542d`). If missing or invalid, run `aliyun cms2 workspace list -o json` and reuse the first matching `agentloop-[0-9a-f]{32}` workspace; if none match, stop and prompt: **Please provide a valid AgentLoop workspace in the format `agentloop-{32-char-code}`.**
3. **Quota fallback**: if workspace creation hits **403/400** quota errors, list existing workspaces, reuse a matching `agentloop-*` workspace, log the reuse reason, and continue - do not abort or fall back to `default-cms-*`.
4. **Do NOT proceed without a valid workspace**: All `apm configuration` / `apm service` commands require `--workspace`; do not guess or fabricate a value.
5. **Region must be obtained separately**: `regionId` is NOT encoded in the workspace name. Derive it from cluster metadata or kubeconfig context in container flows; ask the user in non-container flows.

---

## Container Onboarding Mandatory Rules

> **CRITICAL** - When the user selects container (ACK/ACS/K8s) onboarding, the following rules are **absolute and non-negotiable**. Violating any of them is a workflow error.

1. **Do NOT ask user for `regionId`**: In container onboarding, `regionId` must be derived automatically from cluster metadata or kubeconfig context. Never prompt the user for region. If derivation fails, use `aliyun cs describe-clusters` output to extract `region_id` from cluster info.
2. **Do NOT run any `integration addon list` or `integration addon get` commands**: Container onboarding uses ack-onepilot component check + workload label patching. Addon discovery is exclusively for non-container (ECS/host) OpenTelemetry scenarios.
3. **Do NOT mention "Addon" to the user**: When asking the user to select onboarding type, use the prompt "Please select the onboarding type?" (not "Please select the onboarding protocol type? (Addon type)" or any variant containing "Addon").
4. **Do NOT ask user for `network` type**: Container onboarding uses ack-onepilot label injection - there is no agent download URL or endpoint configuration, so public/VPC distinction is irrelevant. Skip the network question entirely.

**Trigger recognition**: User mentions any of the following -> treat as container onboarding: K8s, ACK, ACS, container, container service, Kubernetes, cluster.

**Container onboarding flow summary** (no addon, no regionId prompt, no network prompt):
1. Determine it's container onboarding (user says ACK/ACS/K8s)
2. Ask user for: `workspace` (format: `agentloop-{32-char-code}`), `appName`, `language`; collect `clusterId` (from user input or derive from context)
3. Derive `regionId` from cluster info or kubeconfig context (NOT from workspace name; NOT by asking user in container flow); skip `network` (irrelevant for ack-onepilot)
4. Validate `workspace` matches `agentloop-{32-char-code}`; if not, stop and ask user to provide a valid AgentLoop workspace
5. Check ack-onepilot component -> Install if missing (with Two-Phase confirmation)
6. Patch Deployment with labels (with Two-Phase confirmation)

> **Language limitation**: Node.js and PHP do NOT support ack-onepilot. For these languages on K8s, guide the user to use OpenTelemetry env vars or manual SDK startup instead of ack-onepilot labels.

---

## Execution Safety Protocol

**Two-Phase Execution Protocol** - applies to operations that **modify the user's application or cluster** (e.g., patching Deployments, installing components, modifying startup scripts):

1. **Phase A (Plan)**: Present the complete execution plan including exact commands, target resources, and expected impact. End your turn immediately after presenting the plan.
2. **Phase B (Execute)**: Only proceed after the user's NEXT message contains explicit approval ("yes", "confirm", "proceed", "go ahead").

**Mandatory Rules**:
- Do NOT combine Phase A and Phase B in the same response.
- Do NOT interpret silence or unrelated messages as approval.
- If user says "no", "cancel", or asks to modify -> return to Phase A with adjustments.

**Operations that do NOT require confirmation** (execute directly):
- Read-only commands: `get`, `list`, `--help`, `describe`, `describe-clusters`
- AgentLoop platform resource creation: `apm configuration create`, `apm service create` (these are AgentLoop platform infrastructure, not user application changes)
- Retrieving credentials: `apm configuration get`

**Operations that REQUIRE confirmation** (must use Two-Phase Protocol):
- Installing cluster components: `install-cluster-addons` (ack-onepilot)
- Patching K8s Deployments: `kubectl patch deployment`
- Modifying user application startup scripts or Dockerfiles
- Any `kubectl apply` / `kubectl delete` on user workloads
- Deleting service records: `apm service delete` (destructive - removes historical monitoring data association)

> **Always offer manual alternative**: When presenting Phase A, also mention the manual way to achieve the same result (console URL, kubectl edit, manual file editing). Let the user choose between automated execution and self-service.

**Plan output format** (use Markdown list, avoid box-drawing characters):
```markdown
### Execution Plan

- Target: [what will be changed]
- Commands:
 - `command 1`
 - `command 2`
- Impact: [blast radius / what gets created or modified]
- Rollback: [yes/no, how]

Please confirm execution (`yes` / `no`).
```

---

## Supported Languages and Methods

| Language / Component | proprietary agent | ack-onepilot (K8s) | OpenTelemetry | eBPF |
|----------|:-:|:-:|:-:|:-:|
| **Java** | AliyunJavaAgent | Yes | OTel Java Agent | - |
| **Golang** | instgo compile | Yes | OTel Go Agent / SDK | - |
| **Python** | aliyun-bootstrap | Yes | opentelemetry-instrument | - |
| **Node.js** | @loongsuite/cms_node_sdk | - | OTel Node SDK | - |
| **PHP** | - | - | OTel PHP extension | - |
| **.NET** | - | - | OTel .NET Auto-Instrument | OBI (DaemonSet) |
| **Nginx** | - | - | ngx_otel_module | - |
| **Kong** | - | - | Kong OTel Plugin | - |
| **APISIX** | - | - | APISIX OTel Plugin | - |

---

## CLI Commands Reference

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `apm configuration create` | Initialize APM backend infrastructure | `--workspace`, `--region` |
| `apm configuration get` | Retrieve authToken, endpoints, project | `--workspace`, `--region` |
| `apm service create` | Register application service | `--workspace`, `--body` (JSON or @file) |
| `apm service list` | List/verify existing services | `--workspace`, `--service-name`, `--service-type` |
| `apm service get` | Get service details | `--workspace`, `--service-id` |
| `apm service delete` | Remove a service | `--workspace`, `--service-id` |

> **Important**: `apm service create --body` requires `< /dev/null` when piping in some shell environments to avoid stdin conflicts.

---

## Onboarding Workflow (6 Steps)

### Step 1 - Gather Parameters

| Parameter | Required | How to Obtain |
|-----------|----------|---------------|
| `regionId` | Conditional | **Container onboarding:** Automatically derive from clusterId via `aliyun cs describe-clusters` response (`region_id` field), NEVER ask user. **Non-container onboarding:** Always ask user to confirm. |
| `userId` (AccountId) | Yes | `aliyun sts get-caller-identity` -> `.AccountId`, or ask user |
| `workspace` | Yes | **User must provide explicitly**, or discover via `aliyun cms2 workspace list` (first `agentloop-[0-9a-f]{32}` match). Format: `agentloop-{32-char-code}`. On quota 403/400, reuse existing `agentloop-*` workspace and continue. Do NOT auto-derive `default-cms-{userId}-{regionId}`. |
| `appName` | Yes | Always ask user to confirm application name |
| `language` | Yes | java / golang / python / nodejs / php / dotnet |
| `method` | Yes | proprietary agent / otel / ack-onepilot (prompt: "Please select the onboarding type?") |
| `network` | Conditional | **Container onboarding:** Do NOT ask - ack-onepilot handles connectivity internally, network type is irrelevant. **Non-container onboarding:** Always ask user (public or VPC, affects download URL and endpoint). |

### Step 2 - Initialize APM Infrastructure

```bash
aliyun cms2 apm configuration create --workspace {workspace} --region {regionId}
```

Idempotent - if already initialized, returns successfully. Use `apm configuration get` to check status.

### Step 3 - Retrieve Access Credentials

```bash
aliyun cms2 apm configuration get --workspace {workspace} --region {regionId} -o json
```

**Example real response** (status=Running means ready):
```json
{
 "success": true,
 "data": {
 "entryPointInfo": {
 "authToken": "awy7aw18hz@2694ecf80a44b70",
 "privateDomain": "proj-xtrace-d1265ec453407aba9ef476c91f84542d-cn-hangzhou.cn-hangzhou-intranet.log.aliyuncs.com",
 "project": "proj-xtrace-d1265ec453407aba9ef476c91f84542d-cn-hangzhou",
 "publicDomain": "proj-xtrace-d1265ec453407aba9ef476c91f84542d-cn-hangzhou.cn-hangzhou.log.aliyuncs.com"
 },
 "feeType": "arms=serverless;xtrace=serverless",
 "regionId": "cn-hangzhou",
 "requestId": "D9A655EE-3A76-5B16-88AA-60BE3B4D7A03",
 "settings": {
 "arms_switch": "enable",
 "trace_aggregate": "enable",
 "xtrace_switch": "enable"
 },
 "status": "Running",
 "type": "apm",
 "workspace": "agentloop-2694ecf8****************1f84542d"
 }
}
```

The `status` field indicates the observability instance lifecycle state:

| Status | Meaning | Action |
|--------|---------|--------|
| `Created` | Provisioning in progress; resources are initializing asynchronously | Proceed to next step |
| `Running` | Fully operational | Proceed to next step |
| `Failed` | Initialization failed; the system will auto-retry | Proceed to next step (retry is automatic) |
| `Pending` | Awaiting activation; does **not** auto-recover | User must verify: 1) workspace exists, 2) the SLS project mapped to the workspace exists, 3) required logstores (`{workspace}__entity`, `{workspace}__topo`) exist under that project |

Extract these variables for subsequent steps:

| Field Path | Variable | Description |
|-----------|----------|-------------|
| `entryPointInfo.authToken` | **LicenseKey** | Agent authentication token (sensitive) |
| `entryPointInfo.publicDomain` | **publicEndpoint** | Public network data reporting endpoint |
| `entryPointInfo.privateDomain` | **vpcEndpoint** | VPC internal data reporting endpoint |
| `entryPointInfo.project` | **project** | SLS project name, used in OTel header `x-arms-project` |

> **Security**: `authToken` is a credential for data reporting. Remind the user not to log or expose it.

### Step 4 - Register Application Service

```bash
aliyun cms2 apm service create --workspace {workspace} --region {regionId} \
 --body @service.json < /dev/null
```

Where `service.json`:
```json
{
 "serviceName": "{appName}",
 "serviceType": "TRACE",
 "attributes": "{\"language\":\"java\"}"
}
```

**serviceType mapping**:
- proprietary agent (AliyunJavaAgent / instgo / aliyun-bootstrap / cms_node_sdk) -> `TRACE`
- OpenTelemetry / eBPF -> `XTRACE`

**`attributes.language` reference**:

| Language | `attributes` value | serviceType |
|----------|-------------------|-------------|
| Java | omit or `{"language":"java"}` | TRACE or XTRACE |
| Golang | `{"language":"golang"}` | TRACE or XTRACE |
| Python | `{"language":"python"}` | TRACE or XTRACE |
| Node.js | `{"language":"nodejs"}` | TRACE or XTRACE |
| .NET | `{"language":"dotnet"}` | XTRACE |
| PHP | `{"language":"php"}` | XTRACE |
| Gateway (Nginx/Kong/APISIX) | omit | XTRACE |

**Example real response**:
```json
{
 "success": true,
 "data": {
 "pid": "awy7aw18hz@9269550ea2c2be0",
 "requestId": "B47F0659-143E-5E90-B446-29729C1ABC3A",
 "serviceId": "awy7aw18hz@645ab0bc177a46e87c7f1"
 }
}
```

### Step 5 - Generate Configuration Output

Route to the appropriate section below based on `language` + `method`, substitute the credential variables, and present to user for manual application.

> **K8s users**: After generating configuration, proceed to [Step 6 - K8s Deployment Modification](#k8s-deployment-modification-step-6) to apply changes to the cluster.

#### Addon Usage Decision Table

| Scenario | `integration addon get` | Rationale |
|----------|:-:|-----------|
| Container / ACK / ACS / K8s onboarding | **Forbidden** | Use ack-onepilot component check + label patching directly |
| ECS/host - Java AliyunJavaAgent (proprietary agent) | Not used | Only non-addon exception; use manual install section |
| ECS/host - other proprietary agent (Go/Python) | **Use** | Fetch addon template (e.g. `apm-golang` -> `arms-ecs` protocol) |
| ECS/host - OpenTelemetry (all languages) | **Use** | Standard addon Dynamic Fetch flow |
| ack-onepilot component operations | **Forbidden** | `ack-onepilot` is a cluster component, not an addon name |

> **User-facing prompt rule**: When asking the user to select onboarding type/protocol, always use "Please select the onboarding type?" as the question text. Do NOT use "Please select the onboarding protocol type? (Addon type)" or any phrasing that mentions "Addon" - this term is an internal implementation detail that is meaningless to users.

> **Manual onboarding strategy**: By default, display the required startup parameters (e.g. `-javaagent`, `-Darms.*`, `OTEL_*` env vars) and guide the user to apply them manually. Also inform the user: if authorized, the agent can directly locate the target process startup script, auto-add parameters, and execute the restart. Explicit user authorization is required before performing any write or restart actions.
>
> **Manual alternative for all automated steps**: If the user prefers manual operation, provide:
> - The exact commands/config to copy-paste
> - The target file paths to edit
> - The AgentLoop console URL for GUI-based operation: `https://cmsnext.console.aliyun.com/`

---

## Common Configuration Templates

### OTel Environment Variables (Shared)

All OpenTelemetry-based integrations use the same export configuration. Substitute variables from Step 3.
Prefer runtime `addon get` templates (see [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch)); use this section as fallback when addon templates are unavailable.

**HTTP protocol** (recommended):
```bash
export OTEL_SERVICE_NAME={appName}
export OTEL_RESOURCE_ATTRIBUTES=service.name={appName},acs.cms.workspace={workspace},service.version={version},deployment.environment={env}
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://{endpoint}/opentelemetry/v1/traces
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://{endpoint}/opentelemetry/v1/metrics
export OTEL_EXPORTER_OTLP_HEADERS="x-arms-license-key={LicenseKey},x-arms-project={project},x-cms-workspace={workspace}"
export OTEL_LOGS_EXPORTER=none
```

**gRPC protocol**:
```bash
export OTEL_SERVICE_NAME={appName}
export OTEL_RESOURCE_ATTRIBUTES=service.name={appName},acs.cms.workspace={workspace},service.version={version},deployment.environment={env}
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=https://{endpoint}:10010
export OTEL_EXPORTER_OTLP_HEADERS="x-arms-license-key={LicenseKey},x-arms-project={project},x-cms-workspace={workspace}"
export OTEL_LOGS_EXPORTER=none
```

> `{endpoint}` = `{publicEndpoint}` (public network) or `{vpcEndpoint}` (VPC internal).

**Language-specific overrides**: Some languages use different endpoint path prefixes (e.g. `/apm/trace/opentelemetry/v1/traces` for Golang/Node.js). See per-language sections below.

### ack-onepilot Labels (Shared)

All ack-onepilot onboarding uses these labels at `spec.template.metadata.labels`:

```yaml
armsPilotAutoEnable: "on"
armsPilotCreateAppName: "{appName}"
armsPilotAppWorkspace: "{workspace}"
```

Additional labels by language:

| Language | Extra Label | Notes |
|----------|-------------|-------|
| Java | `one-agent.jdk.version: "OpenJDK18"` | Optional, match app JDK version |
| Golang | `aliyun.com/app-language: golang` | Required for non-Java |
| Python | `aliyun.com/app-language: python` | Required for non-Java |

> **Prerequisite**: ack-onepilot component must be installed and running. See [ack-onepilot Installation](#prerequisites-install-ack-onepilot-component).

### Agent Download URL Pattern

| Network | URL Pattern |
|---------|-------------|
| Public | `http://arms-apm-{regionId}.oss-{regionId}.aliyuncs.com/<path>` |
| VPC | `http://arms-apm-{regionId}.oss-{regionId}-internal.aliyuncs.com/<path>` |

---

## OpenTelemetry Onboarding (Dynamic Fetch)

> **STOP - CONTAINER EXCLUSION**: This entire section applies **ONLY to non-container (ECS/host) scenarios**. For container/ACK/ACS onboarding, skip directly to ack-onepilot component check + label patching. See [Addon Usage Decision Table](#addon-usage-decision-table).

For non-container onboarding, fetch the latest install guide at runtime instead of using static snippets.

1. Select addon by target language/component:

| Target | Addon Name |
|--------|------------|
| Java | `apm-java-batch` |
| Golang | `apm-golang` |
| Python | `apm-python` |
| Node.js | `apm-nodejs-batch` |
| PHP | `apm-php-batch` |
| .NET | `apm-dotnet-batch` |
| Nginx | `apm-nginx` |
| Kong | `apm-kong` |
| APISIX | `apm-apisix` |

2. Fetch addon card:

```bash
aliyun cms2 integration addon get --addon-name {addonName} --env-type Client -o json
```

3. Extract the target protocol template:

```bash
aliyun cms2 integration addon get --addon-name {addonName} --env-type Client -o json \
 | jq -r '.data.codeTemplate.codes[] | select(.name=="opentelemetry") | .codeTemplate'
```

4. Render variables with Step 3 credentials and runtime context:

| Template Variable | Value Source |
|-------------------|--------------|
| `{{region}}` | `{regionId}` |
| `{{LicenseKey}}` | `entryPointInfo.authToken` |
| `{{workspace}}` / `{{$context$.workspace}}` | `{workspace}` |
| `{{Project}}` | `entryPointInfo.project` |
| `{{PubDomain}}` / `{{PubAddr}}` | `entryPointInfo.publicDomain` |
| `{{VpcDomain}}` / `{{InnerAddr}}` | `entryPointInfo.privateDomain` |
| `{{serviceName}}` | `{appName}` |
| `{{version}}` | Ask user (see interactive rules below) |
| `{{environment}}` | Ask user (see interactive rules below) |
| `{{connectionType}}` | `inner` (VPC) or `public` |
| `{{exportMethod}}` | Must be selected from `schema.props.dataSource` |

5. **Interactive parameter confirmation rules**:
 - For branch/select parameters (`connectionType`, `exportMethod`, `instrumentType`, `source`), ask the user to choose explicitly with concrete options from schema `dataSource`. Do NOT auto-select or silently use defaults.
 - For `{{version}}` and `{{environment}}`, always ask user to confirm with suggested defaults: `version` -> `1.0.0`, `2.0.0`, or custom; `environment` -> `production`, `staging`, `development`, or custom.
 - If schema and template disagree on allowed values, **schema wins**. Hidden branches not in schema are unavailable.
 - If schema is missing or invalid, switch to manual guidance mode (show raw template + ask user to confirm each field).
 - Only ask for parameters that are actually referenced by the selected template branch.

6. Present rendered steps to user. If the addon template is unavailable, fallback to the per-language documentation linked in each section below.

---

## Java - AliyunJavaAgent (Manual Install)

### 1. Download Agent

```bash
wget -T 30 -t 3 "http://arms-apm-{regionId}.oss-{regionId}[-internal].aliyuncs.com/AliyunJavaAgent.zip" -O AliyunJavaAgent.zip
unzip AliyunJavaAgent.zip -d /opt/
```

### 2. Startup Configuration

**Spring Boot / JAR**:
```bash
java -javaagent:/opt/AliyunJavaAgent/aliyun-java-agent.jar \
 -Darms.licenseKey={LicenseKey} \
 -Darms.appName={appName} \
 -Darms.workspace={workspace} \
 -jar app.jar
```

**Tomcat** - add to `{TOMCAT_HOME}/bin/setenv.sh`:
```bash
JAVA_OPTS="$JAVA_OPTS -javaagent:/opt/AliyunJavaAgent/aliyun-java-agent.jar -Darms.licenseKey={LicenseKey} -Darms.appName={appName} -Darms.workspace={workspace}"
```

**Jetty** - add to `{JETTY_HOME}/start.ini`:
```
--exec
-javaagent:/opt/AliyunJavaAgent/aliyun-java-agent.jar
-Darms.licenseKey={LicenseKey}
-Darms.appName={appName}
-Darms.workspace={workspace}
```

**Multi-instance**: add `-Darms.agentId=001` to differentiate JVM processes on the same host.

Reference: [Manually install Java agent](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/manually-install-agent-for-java-applications).

---

## Java - OpenTelemetry Agent

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-java-batch`.

```bash
aliyun cms2 integration addon get --addon-name apm-java-batch --env-type Client -o json
```

Fallback: [Report Java application data via OpenTelemetry](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-java-application-data).

---

## Java - ack-onepilot (K8s)

### Prerequisites: Install ack-onepilot Component

Before adding labels, verify that the **ack-onepilot** component is installed and running in the target cluster.

> **Caution**: Do NOT use `aliyun cs describe-cluster-addons-version` to check installation status - it returns all **available** addons (including uninstalled ones), not only installed ones.

**Check** - use `kubectl` to verify actual resources:

```bash
kubectl get ns ack-onepilot
kubectl get pods -n ack-onepilot
```

If the namespace does not exist or no pods are Running, the component is **not installed**.

**Install** - **WARNING: CONFIRMATION REQUIRED - Phase A**: Inform the user that ack-onepilot is not installed and present the installation plan. STOP and end your turn. Do NOT proceed until user explicitly confirms.

```markdown
### Execution Plan - Install ack-onepilot

- Target: Cluster `[{clusterId}]`
- Commands:
 - `aliyun cs install-cluster-addons --cluster-id {clusterId} --biz-body name=ack-onepilot config="" version=""`
- Precondition: ack-onepilot is not installed (`kubectl get ns ack-onepilot` returns NotFound)
- Impact: deploys DaemonSet in `ack-onepilot` namespace; agent pods run on worker nodes
- Rollback: `kubectl delete ns ack-onepilot` (or uninstall via console)

Please confirm installation (`yes` / `no`).
```

**Phase B** (after user confirms): Obtain `clusterId` via `aliyun cs describe-clusters`, then execute:

```bash
aliyun cs install-cluster-addons --cluster-id {clusterId} --biz-body name=ack-onepilot config="" version=""
```

After installation, verify pods are Running:

```bash
kubectl get pods -n ack-onepilot
```

> **Permission requirement**: RAM account must have `cs:InstallClusterAddons` permission. If 403 Forbidden, fall back to manual installation via [Container Service Console](https://cs.console.aliyun.com/) -> Cluster -> Operations > Component Management -> Search `ack-onepilot` -> Install.
>
> **Manual alternative**: If the user cannot or prefers not to use CLI for component installation, guide them to the console path above. The result is identical.

**Requirements**: ack-onepilot >= 5.1.0; Worker node RAM role needs `AliyunARMSFullAccess` and `AliyunTracingAnalysisFullAccess`.

### Add Labels

Apply [ack-onepilot labels from Common Configuration](#ack-onepilot-labels-shared) to the Deployment. Java does not require the `aliyun.com/app-language` label.

Reference: [Onboard Java applications via ack-onepilot](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/install-the-arms-agent-for-java-applications-deployed-in-ack-and-acs-clusters-by-using-the-ack-onepilot-component).

---

## Golang - Onboarding (via `apm-golang` addon)

All Golang onboarding methods (proprietary agent instgo and OpenTelemetry) use the same addon for template rendering:

```bash
aliyun cms2 integration addon get --addon-name apm-golang --env-type Client -o json
```

Select the protocol template by method:

| Method | Protocol Name in Addon | Notes |
|--------|----------------------|-------|
| proprietary agent (ECS/host) | `arms-ecs` | instgo compile-time instrumentation |
| OpenTelemetry (Auto) | `opentelemetry` | Standard OTel Dynamic Fetch flow |
| OpenTelemetry (Manual SDK) | `opentelemetry` | Prefer SDK instructions in template if available |

> For ACK/K8s container onboarding, do NOT use this addon flow. Follow [Golang - ack-onepilot (K8s)](#golang--ack-onepilot-k8s) directly.

Extract a specific protocol template:

```bash
aliyun cms2 integration addon get --addon-name apm-golang --env-type Client -o json \
 | jq -r '.data.codeTemplate.codes[] | select(.name=="{protocolName}") | .codeTemplate'
```

Fallback: [Manually install Golang agent](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/manually-install-the-golang-agent) | [Report Go application data via OpenTelemetry](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-go-application-data).

---

## Golang - ack-onepilot (K8s)

### Prerequisites: Install ack-onepilot Component

Follow the same installation and confirmation workflow as [Java - ack-onepilot (K8s)](#java--ack-onepilot-k8s):
- Check installation status with `kubectl get ns ack-onepilot` and `kubectl get pods -n ack-onepilot`
- If missing, use **Two-Phase confirmation** before installation
- In container onboarding, do not ask user for `regionId`
- Install command (after user confirms):
 `aliyun cs install-cluster-addons --cluster-id {clusterId} --biz-body name=ack-onepilot config="" version=""`
- Verify all ack-onepilot pods are `Running` before continuing
- Do NOT run `integration addon list/get` to search for `ack-onepilot`

### Add Labels to Deployment

Apply [ack-onepilot labels from Common Configuration](#ack-onepilot-labels-shared) with `aliyun.com/app-language: golang`.

**Important**: Golang applications require compiling with `instgo` before deploying to K8s. The ack-onepilot component handles agent injection, but the binary must already be instrumented at compile time.

Reference: [Onboard Go applications via ack-onepilot](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/install-arms-agent-for-golang-applications-deployed-in-ack-and-acs).

---

## Python - Aliyun Agent (aliyun-bootstrap)

```bash
pip3 install aliyun-bootstrap
aliyun-bootstrap -a install

export ARMS_APP_NAME={appName}
export ARMS_WORKSPACE={workspace}
export ARMS_REGION_ID={regionId}
export ARMS_LICENSE_KEY={LicenseKey}

aliyun-instrument python app.py
```

**Special cases**:
- **uvicorn**: `from aliyun.opentelemetry.instrumentation.auto_instrumentation import sitecustomize` as first import, or `aliyun-instrument gunicorn -k uvicorn.workers.UvicornWorker ...`
- **uWSGI**: see [uWSGI integration docs](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/manually-install-the-python-agent)
- **gevent**: set `GEVENT_ENABLE=true`
- **AI frameworks** (LangChain/LangGraph, DashScope, AgentScope, OpenAI and others): Some AI frameworks reuse this Python agent via the `arms`/`arms4cs` protocols. See [references/ai.md](ai.md) for the full AI observability onboarding guide.

**Docker**:
```dockerfile
ENV ARMS_APP_NAME={appName}
ENV ARMS_REGION_ID={regionId}
ENV ARMS_LICENSE_KEY={LicenseKey}
ENV ARMS_WORKSPACE={workspace}
RUN pip3 install aliyun-bootstrap && ARMS_REGION_ID={regionId} aliyun-bootstrap -a install
CMD ["aliyun-instrument", "python", "app.py"]
```

Reference: [Manually install Python agent](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/manually-install-the-python-agent).

---

## Python - OpenTelemetry

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-python`.

```bash
aliyun cms2 integration addon get --addon-name apm-python --env-type Client -o json
```

Fallback: [Report Python application data via OpenTelemetry](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-python-application-data).

---

## Python - ack-onepilot (K8s)

### Prerequisites: Install ack-onepilot Component

Follow the same installation and confirmation workflow as [Java - ack-onepilot (K8s)](#java--ack-onepilot-k8s):
- Check installation status with `kubectl get ns ack-onepilot` and `kubectl get pods -n ack-onepilot`
- If missing, use **Two-Phase confirmation** before installation
- In container onboarding, do not ask user for `regionId`
- Install command (after user confirms):
 `aliyun cs install-cluster-addons --cluster-id {clusterId} --biz-body name=ack-onepilot config="" version=""`
- Verify all ack-onepilot pods are `Running` before continuing
- Do NOT run `integration addon list/get` to search for `ack-onepilot`

### Add Labels to Deployment

Apply [ack-onepilot labels from Common Configuration](#ack-onepilot-labels-shared) with `aliyun.com/app-language: python`.

For ack-onepilot >= 5.1.0, the Python agent is auto-injected - no Dockerfile modification needed.

Reference: [Onboard Python applications via ack-onepilot](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/install-arms-agent-for-python-applications-deployed-in-ack-and-acs).

---

## Node.js - proprietary Node SDK (proprietary agent)

### Prerequisites

- Node.js v16+ (Active or Maintenance LTS versions only)
- Supported frameworks: Express, Koa, HTTP/HTTPS, MySQL, PostgreSQL, MongoDB, Redis, Kafka, gRPC, Socket.IO

### 1. Install

```bash
npm install @loongsuite/cms_node_sdk
```

### 2. Start Application

**CommonJS mode**:
```bash
export ARMS_LICENSE={LicenseKey}
export CMS_SERVICE_NAME={appName}
export ARMS_REGION_ID={regionId}
export ARMS_WORKSPACE={workspace}
node -r @loongsuite/cms_node_sdk/register app.js
```

**ESModule mode**:
```bash
export ARMS_LICENSE={LicenseKey}
export CMS_SERVICE_NAME={appName}
export ARMS_REGION_ID={regionId}
export ARMS_WORKSPACE={workspace}
node --experimental-loader=@loongsuite/cms_node_sdk/import-hooks -r @loongsuite/cms_node_sdk/register index.js
```

### 3. Manual Instrumentation (Optional)

Create `instrumentation.js`:

**CommonJS**:
```javascript
const { NodeSDK } = require('@loongsuite/cms_node_sdk');

const sdk = new NodeSDK({
 serviceName: "{appName}",
 licenseKey: "{LicenseKey}",
 regionId: "{regionId}",
 workspace: "{workspace}",
});

sdk.start();
module.exports = sdk;
```

**ESModule**:
```javascript
import { NodeSDK } from '@loongsuite/cms_node_sdk';

const sdk = new NodeSDK({
 serviceName: "{appName}",
 licenseKey: "{LicenseKey}",
 regionId: "{regionId}",
 workspace: "{workspace}",
});

sdk.start();
export { sdk };
```

Run with:
```bash
node --require ./instrumentation.js app.js
```

---

## Node.js - OpenTelemetry

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-nodejs-batch`.

```bash
aliyun cms2 integration addon get --addon-name apm-nodejs-batch --env-type Client -o json
```

Fallback: [Node.js OpenTelemetry onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-node-js-application-data).

---

## PHP - OpenTelemetry

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-php-batch`.

```bash
aliyun cms2 integration addon get --addon-name apm-php-batch --env-type Client -o json
```

Fallback: [PHP OpenTelemetry onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-php-application-data).

---

## .NET - OpenTelemetry (Auto-Instrument)

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-dotnet-batch`.

```bash
aliyun cms2 integration addon get --addon-name apm-dotnet-batch --env-type Client -o json
```

Fallback: [.NET OpenTelemetry onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-net-application-data).

---

## .NET - OpenTelemetry (Manual SDK)

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-dotnet-batch`.

```bash
aliyun cms2 integration addon get --addon-name apm-dotnet-batch --env-type Client -o json
```

Prefer codeTemplate content that includes manual SDK instructions when available in the current addon version.

Fallback: [.NET OpenTelemetry onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/use-opentelemetry-to-report-net-application-data).

---

## .NET - eBPF (OBI DaemonSet)

Use addon template runtime fetch from `apm-dotnet-batch` with OBI protocol card.

```bash
aliyun cms2 integration addon get --addon-name apm-dotnet-batch --env-type Client -o json \
 | jq -r '.data.codeTemplate.codes[] | select(.name=="obi") | .codeTemplate'
```

Fallback: [eBPF ECS onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/access-observable-through-opentelemetry-ebpf-obi-on-ecs) | [eBPF ACK onboarding guide](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/access-observable-through-opentelemetry-ebpf-obi-on-ack).

---

## Nginx - OpenTelemetry (ngx_otel_module)

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-nginx`.

```bash
aliyun cms2 integration addon get --addon-name apm-nginx --env-type Client -o json
```

Fallback: complete onboarding via [AgentLoop console > Integration Center](https://agentloop.console.aliyun.com/).

---

## Kong - OpenTelemetry Plugin

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-kong`.

```bash
aliyun cms2 integration addon get --addon-name apm-kong --env-type Client -o json
```

Fallback: complete onboarding via [AgentLoop console > Integration Center](https://agentloop.console.aliyun.com/).

---

## APISIX - OpenTelemetry Plugin

Use [OpenTelemetry Onboarding (Dynamic Fetch)](#opentelemetry-onboarding-dynamic-fetch) with addon `apm-apisix`.

```bash
aliyun cms2 integration addon get --addon-name apm-apisix --env-type Client -o json
```

Fallback: complete onboarding via [AgentLoop console > Integration Center](https://agentloop.console.aliyun.com/).

---

## Post-Onboarding Verification

```bash
# Verify the service was registered
aliyun cms2 apm service list --workspace {workspace} --service-name {appName} --region {regionId} -o json
```

**Expected**: service appears with correct `serviceType` and `serviceName`. After restarting the application, data should appear in AgentLoop console within 2-3 minutes.

---

## Offboarding / Uninstall

Offboarding is the reverse of onboarding. The general principle: **remove agent configuration from the application first, then clean up AgentLoop platform resources**.

### Generic Uninstall Steps

| Step | Action | Command / Procedure |
|------|--------|---------------------|
| 1 | Remove agent from application | Reverse of Step 5: remove `-javaagent`, `OTEL_*` env vars, `aliyun-instrument` wrapper, or ack-onepilot labels |
| 2 | Restart application | Restart without agent params; for K8s, removing labels triggers rolling update automatically |
| 3 | Verify agent stopped | Confirm no new data appears in AgentLoop console after 3-5 minutes |
| 4 | Delete service record (optional, **requires user confirmation**) | `aliyun cms2 apm service delete --workspace {workspace} --service-id {serviceId} --region {regionId}` |

### Uninstall by Method

| Method | What to Remove |
|--------|----------------|
| **proprietary agent (JVM)** | Remove `-javaagent:/opt/AliyunJavaAgent/...` and all `-Darms.*` from startup command; optionally `rm -rf /opt/AliyunJavaAgent` |
| **proprietary agent (Golang)** | Re-compile without `instgo` (`go build` instead of `./instgo go build`); remove `ARMS_*` env vars |
| **proprietary agent (Python)** | Remove `aliyun-instrument` wrapper from CMD; `pip3 uninstall aliyun-bootstrap`; remove `ARMS_*` env vars |
| **proprietary agent (Node.js)** | Remove `-r @loongsuite/cms_node_sdk/register` from startup; `npm uninstall @loongsuite/cms_node_sdk`; remove `ARMS_*`/`CMS_*` env vars |
| **OpenTelemetry** | Remove `-javaagent:opentelemetry-javaagent.jar` or `opentelemetry-instrument` wrapper; remove all `OTEL_*` env vars |
| **ack-onepilot** | Remove labels (`armsPilotAutoEnable`, `armsPilotCreateAppName`, `armsPilotAppWorkspace`, `aliyun.com/app-language`) from Deployment |
| **eBPF (OBI)** | `kubectl delete daemonset obi -n {namespace}` + delete ConfigMap and RBAC |
| **Gateway plugins** | Remove `opentelemetry` plugin config from Nginx/Kong/APISIX |

### ack-onepilot Component Uninstall (Cluster-wide)

Only when removing APM from the entire cluster:

```bash
aliyun cs un-install-cluster-addons --cluster-id {clusterId} --biz-body name=ack-onepilot
```

> **Caution - CONFIRMATION REQUIRED**: This affects ALL monitored applications in the cluster. Use Two-Phase Protocol.

> **Manual alternative**: Container Service Console -> Cluster -> Operations > Component Management -> Search `ack-onepilot` -> Uninstall.

---

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `ServiceObservability not exists` (404) | APM not initialized for this workspace | Run `apm configuration create` first |
| `The workspace does not belong to you` (401) | Workspace not owned by current account, or wrong workspace provided | Ask user to confirm the `agentloop-` AgentLoop workspace name; verify AccountId via `aliyun sts get-caller-identity` |
| `CredentialNotConfigured` | Missing AK/SK | Run `aliyun configure` to set up the default credential profile (see [../SKILL.md - Credentials](../SKILL.md#credentials)) |
| `--body and stdin are mutually exclusive` | Shell stdin conflict with `--body` | Append `< /dev/null` to the command, or use `--body @file.json` |

---

## Agent Download URLs by Region

See [Agent Download URL Pattern](#agent-download-url-pattern) in Common Configuration. Region list:

| Region | regionId |
|--------|----------|
| East China 1 (Hangzhou) | `cn-hangzhou` |
| East China 2 (Shanghai) | `cn-shanghai` |
| North China 2 (Beijing) | `cn-beijing` |
| South China 1 (Shenzhen) | `cn-shenzhen` |
| China (Hong Kong) | `cn-hongkong` |
| Singapore | `ap-southeast-1` |
| US (Silicon Valley) | `us-west-1` |
| Europe (Frankfurt) | `eu-central-1` |

Full region list: [Manual Agent Installation](https://help.aliyun.com/zh/cms/cloudmonitor-2-0/manually-install-agent-for-java-applications)

---

## K8s Deployment Modification (Step 6)

After generating the configuration (Step 5), if the user's application runs on Kubernetes, patch the Deployment YAML to inject the onboarding labels/env vars - with explicit user confirmation before applying.

> **Scope**: For **ack-onepilot** method, this step is **required** - label patching IS the onboarding mechanism. For other methods (manual startup / OTel env vars), this step is optional (user may prefer to modify their own manifests).

> **Safety rule**: ALL cluster write operations - including installing components (e.g. ack-onepilot) and patching Deployments - require **explicit user confirmation** before execution. Show the user what will be changed and wait for approval.

> **Manual alternative**: If the user prefers not to use automated patching, provide the label/env YAML snippet and instruct them to:
> 1. Edit Deployment YAML manually: `kubectl edit deployment {name} -n {namespace}`
> 2. Or apply via console: Container Service Console -> Workloads -> Deployments -> Edit YAML
> 3. Or use a GitOps workflow: commit the label changes to their deployment manifest repository

### Prerequisites

- `kubectl` CLI is available locally
- AK/SK has ACK cluster read permissions (`cs:DescribeClusters`, `cs:DescribeClusterUserKubeconfig`)
- For ack-onepilot method: verify component is installed first. See [ack-onepilot Prerequisites](#prerequisites-install-ack-onepilot-component) for check and installation steps
- In container onboarding, do not ask user for `regionId`; derive it automatically from cluster metadata or kubeconfig context when needed

### Workflow

1. **Discover clusters and obtain kubeconfig**:

 ```bash
 # List ACK clusters to find clusterId (only needed when clusterId is unknown)
 aliyun cs describe-clusters --region {regionId}

 # Get kubeconfig for the target cluster (saved to ~/.kube/config by default)
 aliyun cs describe-cluster-user-kubeconfig --cluster-id {clusterId} --temporary-duration-minutes 480
 ```

 If the user's cluster is not ACK (self-managed K8s), ask for the kubeconfig file path (default `~/.kube/config`).

 Verify access:
 ```bash
 kubectl cluster-info
 ```

2. **Search for Deployment across namespaces**:

 ```bash
 kubectl get deployment --all-namespaces -o wide
 ```

 Filter results by user-provided deployment name or `{appName}`. If multiple matches are found, present the list (name + namespace + replicas) and ask the user to confirm the target. If no match is found, ask the user for the exact deployment name or namespace. Note: deployment name and `appName` are independent - do NOT use deployment name as `appName` without explicit user confirmation.

3. **Read current Deployment**:

 ```bash
 kubectl get deployment {deploymentName} -n {namespace} -o yaml
 ```

4. **WARNING: CONFIRMATION REQUIRED - Phase A**: Show patch to user and STOP. End your turn here. Do NOT apply the patch in the same response.

 Present the following to the user:

 ```markdown
 ### Execution Plan - Patch K8s Deployment

 - Target: `{namespace}/{deploymentName}`
 - Current replicas: `{replicas}`
 - Action: add APM onboarding labels/env
 - Patch JSON:
 ```json
 {full patch content}
 ```
 - Impact: triggers Deployment rolling update; pods will be recreated
 - Rollback: `kubectl rollout undo deployment/{deploymentName} -n {namespace}`

 Please confirm execution (`yes` / `no`).
 ```

 **STOP HERE. End your turn. Wait for user's next message.**

5. **Phase B - Apply patch** (ONLY after user's next message contains explicit approval):

 **ack-onepilot method** - patch labels:

 ```bash
 # Java (no app-language label needed):
 kubectl patch deployment {deploymentName} -n {namespace} \
 --type=strategic -p '{"spec":{"template":{"metadata":{"labels":{"armsPilotAutoEnable":"on","armsPilotCreateAppName":"{appName}","armsPilotAppWorkspace":"{workspace}"}}}}}'

 # Non-Java (add aliyun.com/app-language):
 kubectl patch deployment {deploymentName} -n {namespace} \
 --type=strategic -p '{"spec":{"template":{"metadata":{"labels":{"aliyun.com/app-language":"{language}","armsPilotAutoEnable":"on","armsPilotCreateAppName":"{appName}","armsPilotAppWorkspace":"{workspace}"}}}}}'
 ```

 **OpenTelemetry method** - add `OTEL_*` env vars to container spec (see [OTel env vars](#otel-environment-variables-shared)).

6. **Verify rollout**:

 ```bash
 kubectl rollout status deployment/{deploymentName} -n {namespace} --timeout=120s
 ```

### Safety Checklist

Before executing any K8s write operation (component installation or Deployment patch):
- [ ] Presented complete execution plan (Phase A) in a dedicated response
- [ ] **Ended turn after Phase A** - did NOT continue to execution in the same response
- [ ] User's NEXT message contains explicit approval ("yes"/"confirm"/"proceed"/"go ahead")
- [ ] For component installation (e.g. ack-onepilot): informed user the component is missing, got Phase A confirmation
- [ ] Searched across all namespaces first, then confirmed deployment name and namespace with user
- [ ] Showed the complete patch JSON/YAML to user in Phase A
- [ ] Verified current replica count to understand blast radius
- [ ] After patching (Phase B), verified rollout status
- [ ] If rollout fails, guided user to rollback: `kubectl rollout undo deployment/{name}`

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Agent not reporting | Verify LicenseKey, workspace, endpoint; check network (ports 80/443 outbound) |
| App not in console | Confirm workspace matches; wait 2-3 min for data propagation |
| K8s pod not monitored | ack-onepilot >= 5.1.0 installed; labels on `spec.template.metadata.labels` (not top-level) |
| OTel data missing | Check `x-arms-license-key` and `x-cms-workspace` headers |
| Different workspace LicenseKey mismatch | Each workspace has its own LicenseKey - do NOT reuse across workspaces |