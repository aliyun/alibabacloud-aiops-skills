---
name: alibabacloud-dataworks-datastudio-develop
description: |
  DataWorks data development Skill. Create, configure, validate, deploy, update, move, and rename nodes and workflows.
  Manage components, file resources, and UDF functions. Covers 150+ node types: Shell, SQL, Python, DI, Flink, EMR, etc.
  Supports scheduled and manual workflow orchestration via aliyun CLI or Python SDK.
  WARNING: Supports mutating operations (Move, Rename) requiring explicit user confirmation. Delete operations are NOT supported by this skill.
  Triggers: DataWorks, data development nodes, workflows, FlowSpec, scheduling tasks, data integration, ETL pipelines, .spec.json.
  Also triggers for Alibaba Cloud data development, scheduling node configuration, FlowSpec format, or DI task orchestration.
---

# DataWorks Data Development

## ❗ 5-SECOND SUMMARY — Read This First

> **Credentials**: Run `aliyun configure list` first. The CLI is almost always pre-configured (STS token). Do NOT search for credential files — just check the CLI config.
>
> **Install plugin first**: Run `aliyun plugin install --names dataworks-public`. All commands use plugin mode (kebab-case): `aliyun dataworks-public create-node ...`
>
> **APIs**: `create-workflow-definition` → `create-node` (per node) → `create-pipeline-run` (deploy). For updates: `update-node` → `create-pipeline-run`. **NEVER use** `deploy-file`, `submit-file`, `create-file`, `create-business`.
>
> **FlowSpec**: Copy the exact JSON from the "Quick Start" section below. Do NOT guess the format. `version` is `"2.0.0"`, `kind` is `"CycleWorkflow"` or `"Node"`. Common wrong values: `apiVersion`, `type`, `Workflow`, `metadata` — all wrong.
>
> **Publish after update**: `update-node` → `create-pipeline-run(type=Online)` → poll `get-pipeline-run` → `exec-pipeline-run-stage`. `deploy-file` does NOT work.

## ⚡ MANDATORY: Read Before Any API Call

**These absolute rules are NOT optional — violating ANY ONE means the task WILL FAIL:**

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Aliyun CLI Setup (execute before first use)**:
```bash
# Plugin install (required)
aliyun plugin install --names dataworks-public
# Plugin update (run periodically)
aliyun plugin update --names dataworks-public
# AI-Mode: available commands are enable/disable/set-user-agent
# This skill DISABLES AI-Mode (exact parameter control required)
aliyun configure ai-mode disable
# Do NOT run: aliyun configure ai-mode enable
# Set user-agent for tracking
aliyun configure ai-mode set-user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

Per-command UA flag (business commands only): every `aliyun dataworks-public` invocation must append `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop`.

0. **FIRST THING: Check CLI credentials.** Before ANY `aliyun` command, run `aliyun configure list`. The CLI is typically pre-configured with valid STS token credentials — **do NOT search for credential files** (e.g., testconfig.json) before checking. If `aliyun configure list` shows a valid profile, use it directly. If multiple profiles exist, run `aliyun configure switch --profile <name>` to select the correct one. Priority: prefer a profile whose name contains `dataworks` (case-insensitive); otherwise use `default`. **Do NOT skip this step. Do NOT run any `aliyun dataworks-public` command before switching.** NEVER read/echo/print AK/SK values.
1. **Install plugin before first use.** Run `aliyun plugin install --names dataworks-public`. If already installed, run `aliyun plugin update --names dataworks-public` to ensure latest version. The plugin provides kebab-case commands (`create-node`, `create-workflow-definition`, etc.) which are the required invocation form.
2. **ONLY use plugin mode (kebab-case).** Every DataWorks API call must look like: `aliyun dataworks-public create-node --project-id ... --spec '...'`. Never use PascalCase RPC (`CreateNode`, `CreateWorkflowDefinition`) — always use plugin mode.
3. **ONLY use these commands for create:** `create-workflow-definition` → `create-node` (per node, with `--container-id`) → `create-pipeline-run` (to deploy).
4. **ONLY use these commands for update:** `update-node` (incremental, `kind:Node`) → `create-pipeline-run` (to deploy). Never use `import-workflow-definition`, `deploy-file`, or `submit-file` for updates or publishing.
4a. **ONLY use these commands for deploy/publish:** `create-pipeline-run --type Online --object-ids <ID>` → `get-pipeline-run --id <PipelineRunId>` (poll) → `exec-pipeline-run-stage --id <PipelineRunId> --code <StageCode>` (advance). **NEVER use** `deploy-file`, `submit-file`, `list-deployment-packages`, or `get-deployment-package` — these are all legacy APIs that will fail. ⚠️ `--object-ids` is **space-separated bare IDs** (e.g. `--object-ids 7567482277219412494`), NOT a JSON array string. Wrapping it as `'["ID"]'` will produce `未找到发布对象: [["ID"]]` because the CLI passes the literal bracket text as the ID.

5. **If `create-workflow-definition` or `create-node` returns an error, FIX THE SPEC — do NOT fall back to legacy APIs.** Error 58014884415 / `0x5083000000000005` ("Spec JSON parse failed") means your FlowSpec JSON format is wrong (e.g., used `"kind":"Workflow"` instead of `"kind":"CycleWorkflow"`, or `"apiVersion"` instead of `"version"`, or used a flat `{"type":"SHELL","content":"..."}` structure instead of the `{"version":"2.0.0","kind":"Node","spec":{"nodes":[...]}}` structure). **Stop guessing and copy the exact Spec from the Quick Start below, then modify only the values you need.**
6. **Run CLI commands directly — do NOT create wrapper scripts.** Never create `.sh` scripts to batch API calls. Run each `aliyun` command directly in the shell. Wrapper scripts add complexity and obscure errors.
7. **Saving files locally is NOT completion.** The task is only done when the API returns a success response (e.g., `{"Id": "..."}` from `create-workflow-definition`/`create-node`). Writing JSON files to disk without calling the API means the workflow/node was NOT created. Never claim success without a real API response.
8. **NEVER simulate, mock, or fabricate API responses.** If credentials are missing, the CLI is misconfigured, or an API call returns an error — report the exact error message to the user and **STOP**. Do NOT generate fake JSON responses, write simulation documents, echo hardcoded output, or claim success in any form. A simulated success is worse than an explicit failure.
9. **Credential failure = hard stop.** If `aliyun configure list` shows empty or invalid credentials, or any CLI call returns `InvalidAccessKeyId`, `access_key_id must be assigned`, or similar auth errors — **STOP immediately**. Tell the user to configure valid credentials outside this session. Do NOT attempt workarounds (writing config.json manually, using placeholder credentials, proceeding without auth). No subsequent API calls may be attempted until credentials are verified working.
10. **ONLY use APIs listed in this document.** Every API you call must appear in the API Quick Reference table below. If you need an operation that is not listed, check the table again — the operation likely exists under a different name. **NEVER invent API names** (e.g., `CreateDeployment`, `ApproveDeployment`, `DeployNode` do NOT exist). If you cannot find the right API, ask the user.

**If you catch yourself typing ANY of these legacy commands, STOP IMMEDIATELY and re-read the Quick Start below:**
`create-file`, `create-business`, `create-folder`, `--file-type`, `/bizroot`, `/workflowroot`, `deploy-file`, `submit-file`, `list-files`, `get-file`, `list-deployment-packages`, `get-deployment-package`, `create-deployment`, `approve-deployment`, `deploy-node`, `create-flow`, `create-file-depends`, `create-schedule`

### ⚠️ FlowSpec Anti-Patterns

Agents commonly invent wrong FlowSpec fields. The correct format is shown in the Quick Start below.

| ❌ WRONG | ✅ CORRECT | Notes |
|----------|-----------|-------|
| `"apiVersion": "v1"` or `"apiVersion": "dataworks.aliyun.com/v1"` | `"version": "2.0.0"` | FlowSpec uses `version`, not `apiVersion` |
| `"kind": "Flow"` or `"kind": "Workflow"` | `"kind": "CycleWorkflow"` (for workflows) or `"kind": "Node"` (for nodes) | Only `Node`, `CycleWorkflow`, `ManualWorkflow` are valid. `"Workflow"` alone is NOT valid |
| `"metadata": {"name": "..."}` | `"spec": {"workflows": [{"name": "..."}]}` | FlowSpec has no `metadata` field; name goes inside `spec.workflows[0]` or `spec.nodes[0]` |
| `"type": "SHELL"` (at node level) | `"script": {"runtime": {"command": "DIDE_SHELL"}}` | Node type goes in `script.runtime.command` |
| `"schedule": {"cron": "..."}` | `"trigger": {"cron": "...", "type": "Scheduler"}` | Scheduling uses `trigger`, not `schedule` |
| `"script": {"content": "..."}` without `path` | `"script": {"path": "node_name", ...}` | `script.path` is always required |

### 🚀 Quick Start: End-to-End Workflow Creation

Complete working example — create a scheduled workflow with 2 dependent nodes:

```bash
# Step 1: Create the workflow container
aliyun dataworks-public create-workflow-definition \
  --project-id 585549 \
  --spec '{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_etl_workflow","script":{"path":"my_etl_workflow","runtime":{"command":"WORKFLOW"}}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
# → Returns {"Id": "WORKFLOW_ID", ...}

# Step 2: Create upstream node (Shell) inside the workflow
# IMPORTANT: Before creating, verify output name "my_project.check_data" is not already used by another node (list-nodes)
aliyun dataworks-public create-node \
  --project-id 585549 \
  --scene DATAWORKS_PROJECT \
  --container-id WORKFLOW_ID \
  --spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"name":"check_data","id":"check_data","script":{"path":"check_data","runtime":{"command":"DIDE_SHELL"},"content":"#!/bin/bash\necho done"},"outputs":{"nodeOutputs":[{"data":"my_project.check_data","artifactType":"NodeOutput"}]}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
# → Returns {"Id": "NODE_A_ID", ...}

# Step 3: Create downstream node (SQL) with dependency on upstream
# NOTE on dependencies: "nodeId" is the CURRENT node's name (self-reference), "output" is the UPSTREAM node's output
aliyun dataworks-public create-node \
  --project-id 585549 \
  --scene DATAWORKS_PROJECT \
  --container-id WORKFLOW_ID \
  --spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"name":"transform_data","id":"transform_data","script":{"path":"transform_data","runtime":{"command":"ODPS_SQL"},"content":"SELECT 1;"},"outputs":{"nodeOutputs":[{"data":"my_project.transform_data","artifactType":"NodeOutput"}]}}],"dependencies":[{"nodeId":"transform_data","depends":[{"type":"Normal","output":"my_project.check_data"}]}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop

# Step 4: Set workflow schedule (daily at 00:30)
aliyun dataworks-public update-workflow-definition \
  --project-id 585549 \
  --id WORKFLOW_ID \
  --spec '{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_etl_workflow","script":{"path":"my_etl_workflow","runtime":{"command":"WORKFLOW"}},"trigger":{"cron":"00 30 00 * * ?","timezone":"Asia/Shanghai","type":"Scheduler"}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop

# Step 5: Deploy the workflow online (REQUIRED — workflow is not active until deployed)
aliyun dataworks-public create-pipeline-run \
  --project-id 585549 \
  --type Online --object-ids WORKFLOW_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
# → Returns {"Id": "PIPELINE_RUN_ID", ...}
# Then poll get-pipeline-run and advance stages with exec-pipeline-run-stage
# (see "Publishing and Deploying" section below for full polling flow)
```

> **Key pattern**: `create-workflow-definition` → `create-node` (with `--container-id` + outputs.nodeOutputs) → `update-workflow-definition` (add trigger) → **`create-pipeline-run` (deploy)**. Each node within a workflow MUST have `outputs.nodeOutputs`. **The workflow is NOT active until deployed via `create-pipeline-run`.**
>
> **Dependency wiring summary**: In `spec.dependencies`, `nodeId` is the **current node's own name** (self-reference, NOT the upstream node), and `depends[].output` is the **upstream node's output** (`projectIdentifier.upstream_node_name`). The `outputs.nodeOutputs[].data` value of the upstream node and the `depends[].output` value of the downstream node must be **character-for-character identical**, otherwise the dependency silently fails.

## Core Workflow

### Environment Discovery (Required Before Creating)

**Step 0 — Check CLI Credentials (MUST be the very first action):**
Run `aliyun configure list`. The CLI is almost always pre-configured with STS token credentials — **do NOT claim "I have no credentials" or search for credential files before running this command.** If the output shows a `Valid` profile, you have working credentials — proceed immediately. If multiple profiles exist, run `aliyun configure switch --profile <name>` (prefer `dataworks`-named profile, otherwise `default`). **No `aliyun dataworks-public` command may run before this.**

> **If credentials are empty or invalid, STOP HERE.** Do not proceed with any API calls. Report the error to the user and instruct them to configure valid credentials outside this session (via `aliyun configure` or environment variables). Do not attempt workarounds such as writing config files manually or using placeholder values.

Before creating nodes or workflows, understand the project's existing environment. **It is recommended to use a subagent to execute queries**, returning only a summary to the main Agent to avoid raw data consuming too much context.

Subagent tasks:
1. Call `list-workflow-definitions` to get the workflow list
2. Call `list-nodes` to get the existing node list
3. Call `list-data-sources` **AND** `list-compute-resources` to get all available data sources and compute engine bindings (EMR, Hologres, StarRocks, etc.). `list-compute-resources` supplements `list-data-sources` which may not return compute-engine-type resources
4. Return a summary (do not return raw data):
   - Workflow inventory: name + number of contained nodes + type (scheduled/manual)
   - Existing nodes relevant to the current task: name + type + parent workflow
   - Available data sources + compute resources (name, type) — combine both lists
   - Suggested target workflow (if inferable from the task description)

Based on the summary, the main Agent decides: **target workflow** (existing or new, user decides), **node naming** (follow existing conventions), and **dependencies** (infer from SQL references and existing nodes).

**Pre-creation conflict check (required, applies to all object types)**:
1. **Name duplication check**: Before creating any object, use the corresponding list command to check if an object with the same name already exists:
   - Workflow → `list-workflow-definitions`
   - Node → `list-nodes` (node names are globally unique within a project)
   - Resource → `list-resources`
   - Function → `list-functions`
   - Component → `list-components`
2. **Handling existing objects**: Inform the user and ask how to proceed (use existing / rename / update existing). **Direct deletion of existing objects is prohibited**
3. **Output name conflict check (CRITICAL)**: A node's `outputs.nodeOutputs[].data` (format `${projectIdentifier}.NodeName`) must be **globally unique within the project**, even across different workflows. Use `list-nodes --name NodeName` and inspect `Outputs.NodeOutputs[].Data` in the response to verify. If the output name conflicts with an existing node, the conflict **must be resolved before creation** — otherwise deployment will fail with `"can not exported multiple nodes into the same output"` (see troubleshooting.md #11b)

**Certainty level determines interaction approach**:
- Certain information → Use directly, do not ask the user
- Confident inference → Proceed, explain the reasoning in the output
- Uncertain information → Must ask the user

### Creating Nodes

**Unified workflow**: Whether in OpenAPI Mode or Git Mode, generate the same local file structure.

> **⚠️ 必须先创建本地文件，再调用 API**
> 无论使用 OpenAPI Mode 还是 Git Mode，都**必须**先在本地创建完整的节点文件夹（spec.json + 代码文件 + dataworks.properties），经过 build.py 合并和 validate.py 校验后，再调用 `create-node`/`create-workflow-definition` 命令。**禁止跳过本地文件创建直接调用 API 构造 Spec。**

#### Step 1: Create the Node Directory and Three Files

One folder = one node, containing three files:

```
my_node/
├── my_node.spec.json          # FlowSpec node definition
├── my_node.sql                # Code file (extension based on contentFormat)
└── dataworks.properties       # Runtime configuration (actual values)
```

**spec.json** — Copy the minimal Spec from `references/nodetypes/{category}/{TYPE}.md`, modify name and path, and use `${spec.xxx}` placeholders to reference values from properties. If the user specifies trigger, dependencies, rerunTimes, etc., add them to the spec as well.

**Code file** — Determine the format (sql/shell/python/json/empty) based on the `contentFormat` in the node type documentation; determine the extension based on the `extension` field.

**dataworks.properties** — Fill in actual values:
```properties
projectIdentifier=<actual project identifier>
spec.datasource.name=<actual datasource name>
spec.runtimeResource.resourceGroup=<actual resource group identifier>
```
Do not fill in uncertain values — if omitted, the server automatically uses project defaults.

Reference examples: `assets/templates/`

#### Step 2: Submit

**Default is OpenAPI** (unless the user explicitly says "commit to Git"):

1. Use `build.py` to merge the three files into API input:
   ```bash
   python $SKILL/scripts/build.py ./my_node > /tmp/spec.json
   ```
   build.py does three things (no third-party dependencies; if errors occur, refer to the source code to execute manually):
   - Read `dataworks.properties` → replace `${spec.xxx}` and `${projectIdentifier}` placeholders in spec.json
   - Read the code file (including DI `.json` code files) → replace placeholders → embed into `script.content`
   - Output the merged complete JSON
2. Validate the spec before submission:
   ```bash
   python $SKILL/scripts/validate.py ./my_node
   ```
3. **Pre-submission verification (MANDATORY)** — Before calling `create-node`，**必须**通过 API 验证以下信息确实存在且正确：

   **环境验证（首次提交前执行一次）**：
   - [ ] `runtimeResource.resourceGroup` — 调用 `list-resource-groups` 确认资源组存在，使用返回的资源组 ID（如 `Serverless_res_group_...`），**不要使用人类可读名称**（如 `cx_res_4`）。如不确定，省略让服务端使用项目默认值
   - [ ] `datasource` — 计算引擎节点（ODPS_SQL、HOLOGRES_SQL 等）需要数据源。调用 `list-data-sources` 或 `list-compute-resources` 确认数据源名称和类型匹配。如不确定，省略让服务端使用项目默认值
   
   **Spec 内容审查（每个节点提交前）**：
   - [ ] `script.runtime.command` matches the intended node type (check `references/nodetypes/{category}/{TYPE}.md`)
   - [ ] `script.content` — For code nodes, confirm the merged spec contains non-empty code. For `DI` nodes specifically, `script.content` must be a valid DIJob JSON string with **flat top-level keys `type`, `version`, `steps`, `order`, `setting`, `extend`** — it is NOT the legacy DataX shape `{"job":{"content":[{"reader":{"plugin":...}}]}}`. If your generated content has a top-level `"job"` wrapper or `content[].reader.plugin`, you are using the wrong format from training memory; rewrite it to match `references/nodetypes/data_integration/DI.md` and `DATAX.md` before calling `CreateNode`
   - [ ] `trigger` — For workflow nodes: omit to inherit the workflow schedule; only set when the user explicitly specifies a per-node schedule. For standalone nodes: set if the user specified a schedule
   - [ ] `outputs.nodeOutputs` — **Required for workflow nodes**. Format: `{"data":"${projectIdentifier}.NodeName","artifactType":"NodeOutput"}`. Verify the output name is globally unique in the project (`list-nodes --name`)
   - [ ] `dependencies` — `nodeId` must be the **current node's own name** (self-reference). `depends[].output` must **exactly match** the upstream node's `outputs.nodeOutputs[].data`. **Every workflow node MUST have dependencies**: root nodes (no upstream) MUST depend on `${projectIdentifier}_root` (underscore, not dot); downstream nodes depend on upstream outputs. A workflow node with NO dependencies entry will become an orphan
   - [ ] No invented fields — Compare against the FlowSpec Anti-Patterns table above; remove any field not documented in `references/flowspec-guide.md`
4. Call the API to submit (refer to [references/api/CreateNode.md](references/api/CreateNode.md)):
   ```bash
   aliyun dataworks-public create-node \
     --project-id $PROJECT_ID \
     --scene DATAWORKS_PROJECT \
     --spec "$(cat /tmp/spec.json)" \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
   ```
   > **Note**: Requires the dataworks-public plugin (see Aliyun CLI Setup above). If the command is not found, install the plugin first. **Never** use legacy commands (`create-file`/`create-folder`).

   > **Sandbox fallback**: If `$(cat ...)` is blocked, use Python `subprocess.run(['aliyun', 'dataworks-public', 'create-node', '--project-id', str(PID), '--scene', 'DATAWORKS_PROJECT', '--spec', spec_str, '--user-agent', 'AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop'])`.
5. To place within a workflow, add `--container-id $WorkflowId`

**Git Mode** (when the user explicitly requests): `git add ./my_node && git commit`, DataWorks automatically syncs and replaces placeholders

**Minimum required fields** (verified in practice, universal across all 130+ types):
- `name` — Node name
- `id` — **Must be set equal to `name`**. Ensures `spec.dependencies[*].nodeId` can match. Without explicit `id`, the API may silently drop dependencies
- `script.path` — Script path, must end with the node name; the server automatically prepends the workflow prefix
- `script.runtime.command` — Node type (e.g., ODPS_SQL, DIDE_SHELL)

**Copyable minimal node Spec** (Shell node example):
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{
  "name":"my_shell_node","id":"my_shell_node",
  "script":{"path":"my_shell_node","runtime":{"command":"DIDE_SHELL"},"content":"#!/bin/bash\necho hello"}
}]}}
```

Other fields are not required; the server will automatically fill in project defaults:
- **datasource, runtimeResource** — If unsure, do not pass them; the server automatically binds project defaults
- **trigger** — If not passed, inherits the workflow schedule. Only pass when specified by the user
- **dependencies, rerunTimes, etc.** — Only pass when specified by the user
- **outputs.nodeOutputs** — Optional for standalone nodes; **required for nodes within a workflow** (`{"data":"${projectIdentifier}.NodeName","artifactType":"NodeOutput"}`), otherwise downstream dependencies silently fail. ⚠️ The output name (`${projectIdentifier}.NodeName`) must be **globally unique within the project** — if another node (even in a different workflow) already uses the same output name, deployment will fail with "can not exported multiple nodes into the same output". Always check with `list-nodes` before creating

### Creating Workflows

> **⚠️ 工作流创建也必须先创建本地文件。** 先为工作流内每个节点创建本地文件夹（spec.json + 代码文件 + dataworks.properties），验证通过后再依次调用 API。首次提交前，必须通过 `list-resource-groups`、`list-data-sources` 等命令确认资源组、数据源等环境信息存在且正确。目录结构详见 [workflow-guide.md](references/workflow-guide.md)。

1. **Create the workflow definition** (minimal spec):
   ```json
   {"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{
     "name":"workflow_name","script":{"path":"workflow_name","runtime":{"command":"WORKFLOW"}}
   }]}}
   ```
   Call `create-workflow-definition` → returns WorkflowId
2. **Create nodes in dependency order** (each node passes `--container-id WorkflowId`)
   - **Before each node**: Check that `${projectIdentifier}.NodeName` is not already used as an output by any existing node in the project (use `list-nodes` with `--name` and inspect `Outputs.NodeOutputs[].Data`). Duplicate output names cause deployment failure
   - Each node's spec **must include** `outputs.nodeOutputs`: `{"data":"${projectIdentifier}.NodeName","artifactType":"NodeOutput"}`
   - Downstream nodes declare dependencies in `spec.dependencies`: `nodeId` = **current node's own name** (self-reference), `depends[].output` = **upstream node's output** (see workflow-guide.md)
3. **Verify dependencies (MANDATORY after all nodes created)** — For each downstream node, call `list-node-dependencies --id <NodeID>`. If `TotalCount` is `0` but the node should have upstream dependencies, `create-node` silently dropped them. **Fix immediately** with `update-node` using `spec.dependencies` (see "Updating dependencies" below). Do NOT proceed to deploy until all dependencies are confirmed
4. **Set the schedule** — `update-workflow-definition` with `trigger` (if the user specified a schedule)
5. **Deploy online (REQUIRED)** — `create-pipeline-run --type Online --object-ids <WorkflowId>` → poll `get-pipeline-run --id <PipelineRunId>` → advance stages with `exec-pipeline-run-stage --id <PipelineRunId> --code <StageCode>`. **A workflow is NOT active until deployed.** Do not skip this step or tell the user to do it manually.

Detailed guide and copyable complete node Spec examples (including outputs and dependencies): [references/workflow-guide.md](references/workflow-guide.md)

### Updating Existing Nodes

**Must use incremental updates** — only pass the node id + fields to modify:
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{
  "id":"NodeID",
  "script":{"content":"new code"}
}]}}
```

> **⚠️ Critical**: `update-node` **always** uses `"kind":"Node"`, even if the node belongs to a workflow. Do NOT use `"kind":"CycleWorkflow"` — that is only for workflow-level operations (`update-workflow-definition`).

**Do not pass unchanged fields like datasource or runtimeResource** (the server may have corrected values; passing them back can cause errors).

> **⚠️ Updating dependencies**: To fix or change a node's dependencies via `update-node`, use `spec.dependencies`. Example:
> ```json
> {"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"NodeID"}],"dependencies":[{"nodeId":"current_node_name","depends":[{"type":"Normal","output":"project.upstream_node"}]}]}}
> ```

#### Update + Republish Workflow

Complete end-to-end flow for modifying an existing node and deploying the change:

1. **Find the node** — `list-nodes(--name xxx)` → get Node ID
2. **Update the node** — `update-node` with incremental spec (`kind:Node`, only `id` + changed fields)
3. **Publish** — `create-pipeline-run --type Online --object-ids <PublishObjectId>` → poll `get-pipeline-run --id <PipelineRunId>` → advance stages with `exec-pipeline-run-stage --id <PipelineRunId> --code <StageCode>`. ⚠️ **`<PublishObjectId>` selection rule**: if the node sits inside a workflow (its `path` from `get-node` contains a `/`, e.g. `wf_name/node_name`), `<PublishObjectId>` MUST be the **workflow ID**, NOT the node ID — the API rejects intra-workflow node IDs with `未找到发布对象`. Only standalone nodes (root path, no `/`) take their own ID.

```bash
# Step 1: Find the node
aliyun dataworks-public list-nodes --project-id $PID --name "my_node" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
# → Note the node Id from the response

# Step 2: Update (incremental — only id + changed fields)
aliyun dataworks-public update-node --project-id $PID --id $NODE_ID \
  --spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"'$NODE_ID'","script":{"content":"SELECT 1;"}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop

# Step 3: Publish (see "Publishing and Deploying" below)
# IMPORTANT: if $NODE_ID's `path` from get-node contains a "/", it is in a workflow —
# replace $NODE_ID below with the workflow ID. Standalone nodes (root path) take their own ID.
aliyun dataworks-public create-pipeline-run --project-id $PID \
  --type Online --object-ids $NODE_ID \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

> **Common wrong paths after `update-node`** (all prohibited):
> - ❌ `deploy-file` / `submit-file` — legacy APIs, will fail or behave unexpectedly
> - ❌ `import-workflow-definition` — for initial bulk import only, not for updating or publishing
> - ❌ `list-files` / `get-file` — legacy file model, use `list-nodes` / `get-node` instead
> - ✅ `create-pipeline-run` → `get-pipeline-run` → `exec-pipeline-run-stage`

### Publishing and Deploying

> **⚠️ NEVER use `deploy-file`, `submit-file`, `list-deployment-packages`, `get-deployment-package`, `list-files`, or `get-file` for deployment.** These are all legacy APIs. Use ONLY: `create-pipeline-run` → `get-pipeline-run` → `exec-pipeline-run-stage`.

Publishing is an asynchronous multi-stage pipeline:

1. `create-pipeline-run --type Online --object-ids <ID>` → get `PipelineRunId` from `Id` field. ⚠️ **`--object-ids` is space-separated bare IDs**, NOT a JSON array string. Pass the ID literally: `--object-ids 7567482277219412494`. Wrapping it as `'["..."]'` causes the CLI to send the bracketed text as the literal ID, producing `未找到发布对象: [["..."]]`. The API only publishes the first ID and its child entities — for independent objects, run separate `create-pipeline-run` calls. **For nodes inside a workflow**: pass the workflow ID, NOT the node ID (intra-workflow node IDs are rejected with the same `未找到发布对象` error)
2. Poll `get-pipeline-run --id <PipelineRunId>` → check `Pipeline.Status` and `Pipeline.Stages`
3. When a Stage has `Init` status and all preceding Stages are `Success` → call `exec-pipeline-run-stage --id <PipelineRunId> --code <Stage.Code>` (the parameter is `--id`, **NOT** `--pipeline-run-id`) to advance
4. Until the Pipeline overall status becomes `Success` (deploy succeeded) — any other terminal status (`Fail`, `Termination`, `Cancel`) means the deploy did NOT succeed; see Rule #15 above

**Key point**: The Build stage runs automatically, but the Check and Deploy stages must be manually advanced. Detailed CLI examples, the full Status Decision Matrix, and polling scripts are in [references/deploy-guide.md](references/deploy-guide.md).

> **CLI Note**: The `aliyun` CLI returns JSON with the top-level key `Pipeline` (not SDK's `resp.body.pipeline`); Stages are in `Pipeline.Stages`.

## Common Node Types

| Use Case | command | contentFormat | Extension | datasource |
|------|---------|--------------|------|------------|
| Shell script | DIDE_SHELL | shell | .sh | — |
| MaxCompute SQL | ODPS_SQL | sql | .sql | odps |
| Python script | PYTHON | python | .py | — |
| Offline data sync | DI | json | .json | — |
| Hologres SQL | HOLOGRES_SQL | sql | .sql | hologres |
| Flink streaming SQL | FLINK_SQL_STREAM | sql | .json | flink |
| Flink batch SQL | FLINK_SQL_BATCH | sql | .json | flink |
| EMR Hive | EMR_HIVE | sql | .sql | emr |
| EMR Spark SQL | EMR_SPARK_SQL | sql | .sql | emr |
| Serverless Spark SQL | SERVERLESS_SPARK_SQL | sql | .sql | emr |
| StarRocks SQL | StarRocks | sql | .sql | starrocks |
| ClickHouse SQL | CLICK_SQL | sql | .sql | clickhouse |
| Virtual node | VIRTUAL | empty | .vi | — |

Complete list (130+ types): [references/nodetypes/index.md](references/nodetypes/index.md) (searchable by command name, description, and category, with links to detailed documentation for each type)

**When you cannot find a node type**:
1. Check `references/nodetypes/index.md` and match by keyword
2. `Glob("**/{keyword}*.md", path="references/nodetypes")` to locate the documentation directly
3. Use the `get-node` command to get the spec of a similar node from the live environment as a reference
4. If none of the above works → fall back to `DIDE_SHELL` and use command-line tools within the Shell to accomplish the task

## Key Constraints

1. **script.path is required**: Script path, must end with the node name. When creating, you can pass just the node name; the server automatically prepends the workflow prefix
2. **Dependencies are configured via `spec.dependencies`**: In `spec.dependencies`, `nodeId` is a **self-reference** — it must be the **current node's own `name`** (the node being created), NOT the upstream node. `depends[].output` is the **upstream node's output** (`${projectIdentifier}.UpstreamNodeName`). The upstream's `outputs.nodeOutputs[].data` and downstream's `depends[].output` must be **character-for-character identical**. Upstream nodes must declare `outputs.nodeOutputs`. ⚠️ Output names (`${projectIdentifier}.NodeName`) must be **globally unique within the project** — duplicates cause deployment failure
3. **Immutable properties**: A node's `command` (node type) cannot be changed after creation; if incorrect, inform the user and suggest creating a new node with the correct type
4. **Updates must be incremental**: Only pass id + fields to modify; do not pass unchanged fields like datasource/runtimeResource
5. **datasource.type may be corrected by the server**: e.g., `flink` → `flink_serverless`; use the generic type when creating
6. **Nodes can exist independently**: Nodes can be created at the root level (without passing `--container-id`) or belong to a workflow (pass `--container-id WorkflowId`). Whether to place in a workflow is the user's decision
7. **Workflow command is always WORKFLOW**: `script.runtime.command` must be `"WORKFLOW"`
8. **Deletion is not supported by this skill**: This skill does not provide any delete operations. When creation or publishing fails, **never** attempt to "fix" the problem by deleting existing objects. Correct approach: diagnose the failure cause → inform the user of the specific conflict → let the user decide how to handle it (rename / update existing)
9. **Name conflict check is required before creation**: Before calling any Create API, use the corresponding List API to confirm the name is not duplicated (see "Environment Discovery"). Name conflicts will cause creation failure; duplicate node output names (`outputs.nodeOutputs[].data`) will cause dependency errors or publishing failure
10. **Mutating operations require user confirmation**: Except for Create and read-only queries (Get/List), all OpenAPI operations that modify existing objects (Update, Move, Rename, etc.) **must be shown to the user with explicit confirmation obtained before execution**. Confirmation information should include: operation type, target object name/ID, and key changes. These APIs must not be called before user confirmation. **Delete and Abolish operations are not supported by this skill**
11. **Use only 2024-05-18 version APIs**: All APIs in this skill are DataWorks 2024-05-18 version. Legacy APIs (`create-file`, `create-folder`, `create-flow-project`, etc.) are prohibited. If an API call returns an error, first check [troubleshooting.md](references/troubleshooting.md); do not fall back to legacy APIs
12. **Stop on errors instead of brute-force retrying**: If the same error code appears more than 2 consecutive times, the approach is wrong. Stop and analyze the error cause (check [troubleshooting.md](references/troubleshooting.md)) instead of repeatedly retrying the same incorrect API with different parameters. **Never fall back to legacy APIs** (`create-file`, `create-business`, etc.) when a new API fails — review the FlowSpec Anti-Patterns table at the top of this document instead. **#1 failure trap**: If you get `0x5083000000000005` ("Spec JSON parse failed"), do NOT try random FlowSpec structures — go to the Quick Start section and copy the working JSON verbatim. **#2 failure trap**: If a command is not found, ensure the plugin is installed (`aliyun plugin install --names dataworks-public`)
13. **CLI parameter names must be checked in documentation, guessing is prohibited**: Before calling an API, you must first check `references/api/{APIName}.md` to confirm parameter names. Common mistakes: `get-project`'s ID parameter is `--id` (not `--project-id`); `update-node` requires `--id`. When unsure, verify with `aliyun dataworks-public {command} --help`
14. **Idempotency protection for write operations**: Before creating, run the pre-creation conflict check (List API). After a network error/timeout on Create, check via List/Get API whether the resource was already created before retrying. Log `RequestId` from every response
15. **Never claim deployment success unless `Pipeline.Status == 'Success'`**: After `create-pipeline-run`, the only outcome that means "deployed" is a final `Pipeline.Status` of `Success` returned by `get-pipeline-run`. Statuses `Termination`, `Fail`, `Cancel`, or any stage left in `Init`/`Fail` mean **the deploy did NOT succeed** — even if some stages succeeded, the version number changed, or `exec-pipeline-run-stage` returned `Success: true` for an earlier stage. Do NOT write local result files (e.g., `publishing_result.json`) claiming success in those cases, do NOT tell the user "deployed", and do NOT silently swallow `400 流水线不是正在运行` errors. Re-fetch `get-pipeline-run` once before composing the user-facing summary; report the actual stage that ended the pipeline. Decision matrix: [references/deploy-guide.md](references/deploy-guide.md) "Status Decision Matrix" section

## API Quick Reference

> **API Version**: All APIs listed below are DataWorks **2024-05-18** version. **Only use the APIs listed in the table below**; do not search for or use other DataWorks APIs.

**Business call format** (plugin mode, UA flag required on every call): `aliyun dataworks-public {kebab-case-command} --parameter --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop` — for plugin installation and global UA configuration see the "Aliyun CLI Setup" section above.

Detailed parameters and code templates for each API are in `references/api/{APIName}.md`. If a call returns an error, you can get the latest definition from `https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/{APIName}/api.json`.

### Components

| Command | Description |
|-----|------|
| [create-component](references/api/CreateComponent.md) | Create a component |
| [get-component](references/api/GetComponent.md) | Get component details |
| [update-component](references/api/UpdateComponent.md) | Update a component |
| [list-components](references/api/ListComponents.md) | List components |

### Nodes

| Command | Description |
|-----|------|
| [create-node](references/api/CreateNode.md) | Create a data development node. project-id + scene + spec, optional container-id |
| [update-node](references/api/UpdateNode.md) | Update node information. Incremental update, only pass id + fields to change |
| [move-node](references/api/MoveNode.md) | Move a node to a specified path |
| [rename-node](references/api/RenameNode.md) | Rename a node |
| [get-node](references/api/GetNode.md) | Get node details, returns the complete spec |
| [list-nodes](references/api/ListNodes.md) | List nodes, supports filtering by workflow |
| [list-node-dependencies](references/api/ListNodeDependencies.md) | List a node's dependency nodes |

### Workflow Definitions

| Command | Description |
|-----|------|
| [create-workflow-definition](references/api/CreateWorkflowDefinition.md) | Create a workflow. project-id + spec |
| [import-workflow-definition](references/api/ImportWorkflowDefinition.md) | Import a workflow (initial bulk import ONLY — do NOT use for updates or publishing; use `update-node` + `create-pipeline-run` instead) |
| [update-workflow-definition](references/api/UpdateWorkflowDefinition.md) | Update workflow information, incremental update |
| [move-workflow-definition](references/api/MoveWorkflowDefinition.md) | Move a workflow to a target path |
| [rename-workflow-definition](references/api/RenameWorkflowDefinition.md) | Rename a workflow |
| [get-workflow-definition](references/api/GetWorkflowDefinition.md) | Get workflow details |
| [list-workflow-definitions](references/api/ListWorkflowDefinitions.md) | List workflows, filter by type |

### Resources

| Command | Description |
|-----|------|
| [create-resource](references/api/CreateResource.md) | Create a file resource |
| [update-resource](references/api/UpdateResource.md) | Update file resource information, incremental update |
| [move-resource](references/api/MoveResource.md) | Move a file resource to a specified directory |
| [rename-resource](references/api/RenameResource.md) | Rename a file resource |
| [get-resource](references/api/GetResource.md) | Get file resource details |
| [list-resources](references/api/ListResources.md) | List file resources |

### Functions

| Command | Description |
|-----|------|
| [create-function](references/api/CreateFunction.md) | Create a UDF function |
| [update-function](references/api/UpdateFunction.md) | Update UDF function information, incremental update |
| [move-function](references/api/MoveFunction.md) | Move a function to a target path |
| [rename-function](references/api/RenameFunction.md) | Rename a function |
| [get-function](references/api/GetFunction.md) | Get function details |
| [list-functions](references/api/ListFunctions.md) | List functions |

### Publishing Pipeline

| Command | Description |
|-----|------|
| [create-pipeline-run](references/api/CreatePipelineRun.md) | Create a publishing pipeline. type=Online/Offline |
| [exec-pipeline-run-stage](references/api/ExecPipelineRunStage.md) | Execute a specified stage of the publishing pipeline, async requires polling |
| [get-pipeline-run](references/api/GetPipelineRun.md) | Get publishing pipeline details, returns Stages status |
| [list-pipeline-runs](references/api/ListPipelineRuns.md) | List publishing pipelines |
| [list-pipeline-run-items](references/api/ListPipelineRunItems.md) | Get publishing content |

### Auxiliary Queries

| Command | Description |
|-----|------|
| [get-project](references/api/GetProject.md) | Get projectIdentifier by id |
| [list-data-sources](references/api/ListDataSources.md) | List data sources |
| [list-compute-resources](references/api/ListComputeResources.md) | List compute engine bindings (EMR, Hologres, StarRocks, etc.) — supplements `list-data-sources` |
| [list-resource-groups](references/api/ListResourceGroups.md) | List resource groups |

## Reference Documentation

| Scenario | Document |
|------|------|
| Complete list of APIs and CLI commands | [references/related-apis.md](references/related-apis.md) |
| RAM permission policy configuration | [references/ram-policies.md](references/ram-policies.md) |
| Operation verification methods | [references/verification-method.md](references/verification-method.md) |
| Acceptance criteria and test cases | [references/acceptance-criteria.md](references/acceptance-criteria.md) |
| CLI installation and configuration guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) |
| Node type index (130+ types) | [references/nodetypes/index.md](references/nodetypes/index.md) |
| FlowSpec field reference | [references/flowspec-guide.md](references/flowspec-guide.md) |
| Workflow development | [references/workflow-guide.md](references/workflow-guide.md) |
| Scheduling configuration | [references/scheduling-guide.md](references/scheduling-guide.md) |
| Publishing and unpublishing | [references/deploy-guide.md](references/deploy-guide.md) |
| DI data integration | [references/di-guide.md](references/di-guide.md) |
| Troubleshooting | [references/troubleshooting.md](references/troubleshooting.md) |
| Complete examples | [assets/templates/README.md](assets/templates/README.md) |
