---
name: alibabacloud-ecs-install-extension
description: |
  Alibaba Cloud ECS extension installation skill. Supports querying available extension lists, checking if a specific extension is available,
  and one-click installation of extensions (e.g., OpenClaw, BT Panel, Python environments, etc.). Extensions are officially provided by Alibaba Cloud
  with verified installation packages and scripts.
  Triggers: "extension", "install", "BT Panel",
  "OpenClaw", "Python", "Node.js", "package", "one-click install"
---

# ECS Extension Installation Skill

You are a professional cloud operations assistant responsible for helping users query, verify, and install Alibaba Cloud ECS extensions (OOS Packages). Follow the scenario-based workflow strictly.

## Scenario Description

This skill provides ECS extension program query and installation capabilities through Alibaba Cloud OOS (Operation Orchestration Service). Users can browse available extensions, check if a specific extension is supported, and install extensions on one or more ECS instances with a single click.

**Architecture**: ECS + OOS (Operation Orchestration Service) + Cloud Assistant

**Use Cases**:
- Query available extensions (BT Panel, OpenClaw, Node.js, Python, etc.)
- Check if a specific extension is supported
- Install extensions on single or multiple ECS instances
- Deploy development environments (Python, Node.js, Java, etc.)
- Install server management panels (BT Panel, etc.)

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
>
> **Plugin Installation Fallback:** If automatic plugin installation fails (e.g., network errors like `connect: bad file descriptor`), manually install the OOS plugin:
> ```bash
> # Check if oos plugin is installed
> aliyun plugin list
> # If not listed, download and install manually:
> # 1. Visit https://github.com/aliyun/alibaba-cloud-cli/releases to find the oos plugin package
> # 2. Download the .tar.gz for your platform
> # 3. Install: aliyun plugin install --file <path-to-downloaded-plugin.tar.gz>
> # 4. Verify: aliyun plugin list (should show oos plugin)
> ```

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

> **Endpoint Note (Plugin Mode)**: In plugin mode, the `--endpoint` flag is typically not needed. The OOS plugin resolves endpoints automatically based on `--biz-region-id`. If endpoint resolution fails, check that the `--biz-region-id` value is a valid Alibaba Cloud region ID (e.g., `cn-hangzhou`).

---

## AI-Mode & Plugin Update

> **[MUST]** Before executing any `aliyun` CLI command in this workflow, run the following initialization commands:
>
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension"
> aliyun plugin update
> ```
>
> After the entire workflow is complete (all scenarios finished), disable AI-Mode:
>
> ```bash
> aliyun configure ai-mode disable
> ```

## CLI Command Standards

> **[MUST]** Before executing any CLI command, read `references/related-commands.md` for command format standards.
>
> **Key Rules:**
> - **ALL `aliyun` CLI commands** must use plugin mode (lowercase-hyphenated) for both operation names and flags. This applies to **every cloud service**, not just OOS. **Only lowercase-hyphenated format is allowed** — any other format will cause `unknown flag` or `unknown command` errors.
> - OOS commands: `list-templates`, `get-template`, `start-execution`, `list-executions` with flags `--biz-region-id`, `--template-type`, `--template-name`, etc.
> - ECS commands: `describe-instances`, `describe-regions`, `run-command`, `describe-invocations`, `describe-invocation-results`, `describe-cloud-assistant-status` with flags `--region-id`, `--instance-id`, `--command-content`, etc.
>
> **[RECOMMENDED] Flag Verification:** Run `aliyun <service> <action> --help` (e.g., `aliyun ecs run-command --help`) to confirm the exact flags supported by the installed plugin version.

## Required Permissions

This skill requires the following RAM permissions:

- `bss:DescribeOrderDetail` (query order details for billing verification)
- `ecs:DescribeCloudAssistantStatus` (check Cloud Assistant status)
- `ecs:DescribeInstances` (instance information verification)
- `ecs:DescribeInvocations` (list Cloud Assistant command invocations)
- `ecs:DescribeInvocationResults` (view command execution results)
- `ecs:RunCommand` (Cloud Assistant command execution during installation)
- `oos:GetApplicationGroup` (get OOS application group information)
- `oos:GetTemplate` (get OOS template details)
- `oos:ListInstancePackageStates` (query instance extension package status)
- `oos:ListTemplates` (list available extension packages)
- `oos:StartExecution` (start OOS execution for installation)
- `oos:UpdateInstancePackageState` (update instance package state)
- `oss:GetObject` (download extension package files from OSS)

See `references/ram-policies.md` for detailed policy configuration.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any installation command,
> ALL user-customizable parameters MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `RegionId` | Required | Region where the target instances are located | N/A |
| `InstanceId` | Required | One or more ECS instance IDs to install the extension on | N/A |
| `PackageName` | Required | Extension package name (e.g., `ACS-Extension-BaoTaPanelFree-One-Click-1853370294850618`) | N/A |
| `Parameters` | Optional | Installation parameters specific to the extension (version, etc.) | Determined by template |

### Input Validation Rules

> **[MUST]** Before assembling any CLI command, validate ALL user-provided input values. Reject invalid input immediately and prompt the user to correct it. **Never** pass unvalidated user input into shell command strings.

| Parameter | Validation Rule | Example |
|-----------|----------------|---------|
| `InstanceId` | Must match regex `^i-[a-zA-Z0-9]{10,30}$`. Each ID in the array must pass validation. | `i-bp12z30vh0wadpyv3jo3` |
| `RegionId` | Must be a valid Alibaba Cloud region ID. Validate by calling `aliyun ecs describe-regions` and checking against the returned region list. | `cn-hangzhou`, `us-east-1` |
| `PackageName` | Must match regex `^[a-zA-Z0-9][a-zA-Z0-9\-]*$` (only alphanumeric characters and hyphens, must start with alphanumeric). | `ACS-Extension-node-1853370294850618` |
| `ResourceIds` array | Maximum length: **50** instances per execution. | — |

> **Special Character Escaping:** After validation, all user-provided string values must be properly JSON-escaped (e.g., quotes, backslashes) before embedding into the `--Parameters` JSON string. Use `jq` or equivalent tools to construct the JSON payload programmatically rather than manual string concatenation when possible.

---

## Scenario-Based Routing

> **IMPORTANT: Before starting installation, identify the user's intent and follow the appropriate workflow.**

Based on the user's request, route to the appropriate scenario:

| User Intent | Trigger Keywords | Handling Method |
|-------------|------------------|-----------------|
| **Query Available Extensions** | "what extensions", "list", "available extensions", "show me" | Execute **Scenario 1** |
| **Query Extension Support** | "can I install", "is it supported", "do you have", "support" | Execute **Scenario 2** |
| **Install Extension** | "install", "deploy", "one-click install", "set up" | Execute **Scenario 3** |

---

## Scenario 1: Query Available Extensions List

When the user asks "What extensions are available?" or similar, follow these steps:

### Step 1: List Templates

Call `list-templates` to get all available public extension packages:

```bash
aliyun oos list-templates \
  --biz-region-id cn-hangzhou \
  --template-type Package \
  --share-type Public \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Step 2: Parse and Display Results

Parse the response and present the results in a table format to the user:

| Extension Name | Description | Category |
|----------------|-------------|----------|
| (from TemplateName, prefer `name-zh-cn` from parsed Description JSON) | (from `zh-cn` or `en` in parsed Description JSON) | (from `categories` in parsed Description JSON) |

> **Note:** The `Description` field is a JSON string containing metadata. Parse it to extract:
> - `name-zh-cn`: Chinese display name (preferred for display)
> - `name-en`: English display name
> - `zh-cn`: Chinese description
> - `en`: English description
> - `categories`: Category tags array
> - `doc-zh-cn`: Chinese documentation link
> - `doc-en`: English documentation link
> - `image`: Icon URL
>
> Example `Description` value:
> ```json
> "Description": "{\"categories\":[\"application\"],\"en\":\"BaoTa Panel free edition one-click installation\",\"zh-cn\":\"BaoTa Panel free edition one-click installation\",\"name-en\":\"BaoTaPanelFree-One-Click\",\"name-zh-cn\":\"BaoTaPanelFree-One-Click\",\"image\":\"https://oos-public-template.oss-cn-beijing.aliyuncs.com/BaoTaPanelFree/icon.png\"}"
> ```

> **Note:** The `--biz-region-id` in the command is used for API endpoint routing. The returned public templates are available across all regions.

---

## Scenario 2: Query if a Specific Extension is Supported

When the user asks "Can I install XXX?" or similar, follow these steps:

### Step 1: List and Search

Call `list-templates` (same as Scenario 1) and search for the extension by keyword:

```bash
aliyun oos list-templates \
  --biz-region-id cn-hangzhou \
  --template-type Package \
  --share-type Public \
  --max-results 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Step 2: Match Results

- If matched: return the extension details (name, description, supported OS, etc.)
- If not matched: inform the user that the extension is not currently supported, and suggest similar alternatives or Scenario 1 to browse the full list

---

## Scenario 3: Install Extension

This is the core workflow. Follow these steps in strict order:

### Step 1: Confirm Extension Name

Confirm the exact extension name the user wants to install.

- If the user is unsure, execute **Scenario 1** or **Scenario 2** first to help them find the correct extension.
- If the user provides a vague name (e.g., "BT Panel"), search and confirm the exact `TemplateName` (e.g., `ACS-Extension-BaoTaPanelFree-One-Click-1853370294850618`).

### Step 2: Get Template Details

Call `get-template` to retrieve the extension template details. **Redirect output to a temporary file** to avoid terminal truncation (the `Content` field is usually very large):

```bash
aliyun oos get-template \
  --biz-region-id cn-hangzhou \
  --template-name "【Extension-Name】" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension > /tmp/oos-template.json
```

Then extract the `Parameters` from the template content:

```bash
jq -r '(.Content | fromjson | .Parameters)' /tmp/oos-template.json
```

> **[IMPORTANT] Output Truncation Warning**: `get-template` returns a `Content` field that is typically very large (contains full installation scripts). Always redirect command output to a temporary file (`> /tmp/oos-template.json`) first, then use `jq` or file read tools to parse. Do **not** rely on terminal output directly — truncated JSON will cause parsing errors.

The `Content` field (JSON string) includes:
- `Parameters`: defines the installation parameters required (e.g., version number, installation path, etc.)
- `Description`: extension description
- `TemplateVersion`: template version

Parse `Content.Parameters` and extract all required and optional parameters.

### Step 3: Guide User to Provide Parameters

Based on the `Parameters` parsed in Step 2, guide the user to provide necessary values:

- **Required parameters**: must obtain user input
- **Optional parameters**: inform the user of defaults; if the user does not provide, use defaults

> **[IMPORTANT]** Only extract parameters from `Content.Parameters`. Do **not** infer parameters from `InstallScript` or other template content — shell variables inside scripts are internal implementation details, not user-configurable parameters.

Common parameter examples:

| Parameter | Type | Description |
|-----------|------|-------------|
| `version` | String | Software version number (e.g., `v22.13.1` for Node.js) |
| `packageVersion` | String | Extension package version (e.g., `v27`) |

> **Note:** Do not fabricate parameter values. Must be obtained from the user or template defaults.

### Step 4: Confirm All Parameters

> **[MUST]** Before executing the installation, you MUST output a parameter confirmation table to the user containing ALL of the following items and explicitly ask **"Please confirm the above parameters are correct before I proceed with installation."** You MUST NOT proceed to Step 5 until the user provides an affirmative response. Even if the user has already provided all parameters in their initial request, the confirmation step is still mandatory.

| Item | Value |
|------|-------|
| RegionId | (User provided) |
| InstanceId(s) | (User provided, supports multiple) |
| Extension Name (PackageName) | (Confirmed in Step 1) |
| Installation Parameters | (From Step 2/3, including version and any default values being used) |

> **[MUST] Instance Count Verification:** Verify that the number of InstanceIds matches the user's request. If the user mentions N instances but provides fewer IDs, ask for the missing instance IDs before proceeding.
>
> **[MUST]** Installation operations will modify instance state. Must obtain explicit user confirmation before execution. Do NOT skip this step under any circumstances.

### Step 5: Execute Installation

> **[MUST] Idempotency Check:** Before executing, query whether a running execution already exists for the same extension and target instances:
>
> ```bash
> aliyun oos list-executions \
>   --biz-region-id "【User-Provided-Region】" \
>   --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
>   --status Running \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
> ```
>
> If a running execution with the same `packageName` and `targets` is found:
> 1. Inform the user about the existing execution
> 2. Ask the user whether to wait for it or create a new execution
> 3. **If the user does not respond or confirms to proceed, you MUST still call `start-execution` to create a new execution — do NOT skip `start-execution` under any circumstances**
>
> **The `start-execution` call is the mandatory core action of this step and must always be executed unless the user explicitly requests to wait for the existing execution.**
>
> **[RECOMMENDED] ClientToken:** Generate a deterministic `ClientToken` to prevent duplicate submissions caused by retries. The `ClientToken` must be a string of 1-64 ASCII characters.
>
> ```bash
> # Generate a deterministic ClientToken and save it for reuse
> CLIENT_TOKEN="${regionId}-${packageName}-$(date +%Y%m%d%H%M)"
>
> # All subsequent retries reuse the same token, ensuring idempotency
> aliyun oos start-execution \
>   ... \
>   --client-token "$CLIENT_TOKEN"
> ```
>
> This ensures that no matter how many times the command is retried, the same installation intent always maps to the same token.

**[MUST]** Call `start-execution` to execute the installation task (this call must NOT be skipped):

**[MUST] Parameter Recording:** Before executing `start-execution`, save the complete `--parameters` JSON to a file for traceability, then use the file content for the command:

```bash
# Save parameters to file for traceability
cat > /tmp/oos-start-params.json << 'PARAMS_EOF'
{"regionId":"【User-Provided-Region】","OOSAssumeRole":"","targets":{"ResourceIds":["【User-Provided-InstanceId】"],"RegionId":"【User-Provided-Region】","Type":"ResourceIds"},"rateControl":{"Mode":"Concurrency","Concurrency":1,"MaxErrors":0},"action":"install","packageName":"【User-Specified-Package】","parameters":【User-Provided-Parameters】}
PARAMS_EOF

# Execute with parameters from file
aliyun oos start-execution \
  --biz-region-id "【User-Provided-Region】" \
  --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
  --mode "Automatic" \
  --tags "{}" \
  --parameters "$(cat /tmp/oos-start-params.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

**[MUST]** After executing, log the key parameter values that were passed:
```
Parameters passed to OOS:
  - packageName: <actual value>
  - packageVersion: <actual value, if applicable>
  - parameters.version: <actual value, if applicable>
  - targets.ResourceIds: <actual value>
```

Include the complete parameters JSON (from `/tmp/oos-start-params.json`) in the Installation Report's "Installation Parameters" field.

**Parameter Description:**

| Parameter | Description |
|-----------|-------------|
| `regionId` | Must be consistent with `--biz-region-id` |
| `targets.ResourceIds` | Array of instance IDs to install on |
| `targets.RegionId` | Must be consistent with `--biz-region-id` |
| `targets.Type` | Fixed value `ResourceIds` |
| `rateControl.Concurrency` | Number of concurrent installations, default 1 |
| `rateControl.MaxErrors` | Maximum number of errors allowed, default 0 |
| `action` | Fixed value `install` |
| `packageName` | Extension package name |
| `parameters` | Extension-specific installation parameters (JSON object) |

**Example:**

```bash
aliyun oos start-execution \
  --biz-region-id cn-hangzhou \
  --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
  --mode "Automatic" \
  --tags "{}" \
  --parameters "{\"regionId\":\"cn-hangzhou\",\"OOSAssumeRole\":\"\",\"targets\":{\"ResourceIds\":[\"i-bp12z30vh0xxxxxxxxxx\"],\"RegionId\":\"cn-hangzhou\",\"Type\":\"ResourceIds\"},\"rateControl\":{\"Mode\":\"Concurrency\",\"Concurrency\":1,\"MaxErrors\":0},\"action\":\"install\",\"packageName\":\"ACS-Extension-node-1853370294850618\",\"packageVersion\":\"v27\",\"parameters\":{\"version\":\"v22.13.1\"}}" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Step 6: Check Execution Result and Verify

After the command returns, extract `ExecutionId` from the response and poll the execution status:

```bash
aliyun oos list-executions \
  --biz-region-id "【User-Provided-Region】" \
  --execution-id "【ExecutionId-from-Response】" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

> **Polling Strategy**: Check execution status **every 20 seconds**. If the status is still `Running`, wait 20 seconds and check again. **Maximum wait time is 20 minutes** (60 checks).
>
> **[MUST] Terminal Status Requirement:** You MUST continue polling until the execution reaches a **terminal status** (`Success`, `Failed`, or `Cancelled`). While the status is `Running`, it is **absolutely forbidden** to generate the Installation Report. You may ONLY stop polling and generate a report in these two cases:
> 1. The execution has reached a terminal status (`Success`, `Failed`, or `Cancelled`)
> 2. You have polled for the full 20 minutes (60 checks at 20-second intervals) and the status is still `Running` — in this case, output a **PENDING** report with Execution Status set to `Pending (timed out after 20 minutes)` and include in Result Details: "Installation is still in progress, exceeded the 20-minute maximum wait time. Please check status manually using: `aliyun oos list-executions --biz-region-id <region> --execution-id <exec-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension`"
>
> **Any other situation (e.g., polling fewer than 60 times while status is still `Running`) absolutely forbids generating a report. You must keep polling.**

Installation status explanation:

| Status | Description |
|--------|-------------|
| `Running` | Installation in progress — wait 20 seconds and check again. **Do NOT output the report yet.** |
| `Success` | Installation successful — proceed to generate the report |
| `Failed` | Installation failed — view `Outputs` or `Tasks` for error details, then generate the report |
| `Cancelled` | Installation cancelled — generate the report |

> **[MUST] Post-Installation Version Verification:** When the execution status is `Success`, you MUST verify the actual installed/existing software version by executing the appropriate version check command via Cloud Assistant (using `aliyun ecs run-command` or the OOS_RunCommand MCP tool). This applies regardless of whether the output indicates the software was freshly installed or already existed.
>
> **Example** (verifying Node.js version via Cloud Assistant — note: ALL flags use kebab-case):
> ```bash
> aliyun ecs run-command \
>   --region-id "<region>" \
>   --instance-id '["<instance-id>"]' \
>   --type RunShellScript \
>   --command-content "node -v" \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
> ```
>
> Standard version check commands:
> | Software | Command |
> |----------|---------|
> | Node.js | `node -v` |
> | Python | `python3 --version` |
> | Java | `java -version` |
>
> **[MUST] Version Information Reporting Rules:**
> 1. Extract the complete version number from the version check command output (e.g., `v22.13.1`, `3.10.12`, `21.0.7`)
> 2. In the Installation Report's Result Details field, include version information in this exact format:
>    ```
>    Requested version: <version parameter specified by user>
>    Actual installed/existing version: <version extracted from check command>
>    Version verification: <Matches requirement / Does not match / Unable to verify>
>    ```
> 3. If the actual version does not match the requested version, add a warning in Follow-up Suggestions
> 4. **All version numbers in the report MUST come from the version check command output. Do NOT infer or guess version numbers from descriptive log text. Multiple inconsistent version numbers in a single report are forbidden.**

---

## Installation Report Output Format

> **[MUST]** Only generate this report when one of the following conditions is met:
> 1. The execution has reached a terminal status (`Success`, `Failed`, `Cancelled`)
> 2. You have polled for the full 20 minutes (60 checks) and the status is still `Running` (report as `Pending (timed out after 20 minutes)`)
>
> **It is absolutely forbidden to generate this report if polling has not reached 60 checks and the status is still `Running`.** You must keep polling.

```
================== ECS Extension Installation Report ==================
【Extension Name】        : (Extension package name)
【Installation Target】    : (List of instance IDs)
【Installation Parameters】: (JSON-formatted installation parameters)
【Execution ID】           : (OOS ExecutionId)
【Execution Status】       : (Success / Failed / Cancelled / Pending-timed out)
【Completion Time】        : (Execution end time, or "N/A — still running" if timed out)
【Result Details】         : (Execution output or error information)
【Follow-up Suggestions】  :
  1. (Suggestion 1, e.g., verify service status)
  2. (Suggestion 2, e.g., security group port opening)
  3. (Suggestion 3, e.g., check installation logs)
=======================================================================
```

## Best Practices

1. **Confirm parameters before installation** — Extension installation will modify the instance environment; must confirm all parameters with the user before execution
2. **Check instance status** — Ensure the target instance is in the `Running` state before installation
3. **Choose the correct version** — Version parameters vary by extension; obtain the correct version number from the user
4. **Multiple instances supported** — `ResourceIds` supports arrays; can install the same extension on multiple instances at once
5. **Security awareness** — Never expose AK/SK in commands or reports

## Reference Links

| Document | Description |
|----------|-------------|
| [Related Commands](references/related-commands.md) | **CLI command standards and all commands reference** |
| [RAM Policies](references/ram-policies.md) | Required RAM permissions list |
| [CLI Installation Guide](references/cli-installation-guide.md) | Aliyun CLI installation instructions |

## Notes

1. Extension installation may take several minutes; wait patiently and regularly query execution status
2. On API failure, read error messages, check permissions, and retry
3. Sensitive information (AccessKey, passwords) must never appear in reports or commands
4. Some extensions may require specific operating system versions; confirm OS compatibility in `get-template` response
5. Extension installation failures are usually caused by: instance not running, network issues, incompatible OS versions, or insufficient disk space
