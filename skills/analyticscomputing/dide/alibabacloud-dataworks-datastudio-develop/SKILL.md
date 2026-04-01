---
name: alibabacloud-dataworks-datastudio-develop
description: |
  DataWorks data development Skill. Create, configure, validate, deploy, update, delete, move, rename, and abolish nodes and workflows.
  Manage components, file resources, and UDF functions. Covers 150+ node types: Shell, SQL, Python, DI, Flink, EMR, etc.
  Supports scheduled and manual workflow orchestration via aliyun CLI or Python SDK.
  WARNING: Supports destructive operations (Delete, Move, Rename, Abolish) requiring explicit user confirmation.
  Triggers: DataWorks, data development nodes, workflows, FlowSpec, scheduling tasks, data integration, ETL pipelines, .spec.json.
  Also triggers for Alibaba Cloud data development, scheduling node configuration, FlowSpec format, or DI task orchestration.
---

# DataWorks Data Development

## ⚡ MANDATORY: Read Before Any API Call

**Three absolute rules — violating ANY ONE means the task WILL FAIL:**

1. **NEVER install plugins.** If `aliyun help` shows "Plugin available but not installed" for dataworks-public → **IGNORE IT**. Do NOT run `aliyun plugin install`. PascalCase RPC works without plugins (requires CLI >= 3.3.1).
2. **ONLY use PascalCase RPC.** Every DataWorks API call must look like: `aliyun dataworks-public CreateNode --ProjectId ... --Spec '...'`. Never use kebab-case (`create-file`, `create-node`, `create-business`).
3. **ONLY use these APIs for create:** `CreateWorkflowDefinition` → `CreateNode` (per node, with `--ContainerId`) → `CreatePipelineRun` (to deploy).
4. **ONLY use these APIs for update:** `UpdateNode` (incremental, `kind:Node`) → `CreatePipelineRun` (to deploy). Never use `ImportWorkflowDefinition`, `DeployFile`, or `SubmitFile` for updates or publishing.
4a. **ONLY use these APIs for deploy/publish:** `CreatePipelineRun` (Type=Online, ObjectIds=[ID]) → `GetPipelineRun` (poll) → `ExecPipelineRunStage` (advance). **NEVER use** `DeployFile`, `SubmitFile`, `ListDeploymentPackages`, or `GetDeploymentPackage` — these are all legacy APIs that will fail.

5. **If `CreateWorkflowDefinition` or `CreateNode` returns an error, FIX THE SPEC — do NOT fall back to legacy APIs.** Error 58014884415 means your FlowSpec JSON format is wrong (e.g., used `"kind":"Workflow"` instead of `"kind":"CycleWorkflow"`, or `"apiVersion"` instead of `"version"`). Copy the exact Spec from the Quick Start below.
6. **Run CLI commands directly — do NOT create wrapper scripts.** Never create `.sh` scripts to batch API calls. Run each `aliyun` command directly in the shell. Wrapper scripts add complexity and obscure errors.
7. **Saving files locally is NOT completion.** The task is only done when the API returns a success response (e.g., `{"Id": "..."}` from `CreateWorkflowDefinition`/`CreateNode`). Writing JSON files to disk without calling the API means the workflow/node was NOT created. Never claim success without a real API response.

**If you catch yourself typing ANY of these, STOP IMMEDIATELY and re-read the Quick Start below:**
`create-file`, `create-business`, `create-folder`, `CreateFolder`, `CreateFile`, `UpdateFile`, `plugin install`, `--file-type`, `/bizroot`, `/workflowroot`, `DeployFile`, `SubmitFile`, `ListFiles`, `GetFile`, `ListDeploymentPackages`, `GetDeploymentPackage`

## ⛔ Prohibited Legacy APIs

This skill uses DataWorks OpenAPI version **2024-05-18**. The following legacy APIs and patterns are **strictly prohibited**:

| Prohibited Legacy Operation | Correct Replacement |
|----------------|----------|
| `create-file` / `CreateFile` (with `--file-type` numeric type code) | `CreateNode` + FlowSpec JSON |
| `create-folder` / `CreateFolder` | No folder needed, use `CreateNode` directly |
| `create-business` / `CreateBusiness` / `CreateFlowProject` | `CreateWorkflowDefinition` + FlowSpec |
| `list-folders` / `ListFolders` | `ListNodes` / `ListWorkflowDefinitions` |
| `import-workflow-definition` / `ImportWorkflowDefinition` (for create or update) | `CreateWorkflowDefinition` + individual `CreateNode` calls (for create); `UpdateNode` per node (for update) |
| Any operation based on folder paths (`/bizroot`, `/workflowroot`, `/Business Flow`) | Specify path via `script.path` in FlowSpec |
| `SubmitFile` / `DeployFile` / `GetDeploymentPackage` / `ListDeploymentPackages` | `CreatePipelineRun` + `ExecPipelineRunStage` |
| `UpdateFile` (legacy file update) | `UpdateNode` + FlowSpec JSON (`kind:Node`, incremental) |
| `ListFiles` / `GetFile` (legacy file model) | `ListNodes` / `GetNode` |
| `aliyun plugin install --names dataworks-public` (legacy plugin) | No plugin installation needed, use PascalCase RPC direct invocation |

**How to tell — STOP if any of these are true**:
- You are typing `create-file`, `create-business`, `create-folder`, or any kebab-case DataWorks command → **WRONG**. Use PascalCase RPC: `CreateNode`, `CreateWorkflowDefinition`
- You are running `aliyun plugin install` → **WRONG**. No plugin needed; PascalCase RPC direct invocation works out of the box (requires CLI >= 3.3.1)
- You are constructing folder paths (`/bizroot`, `/workflowroot`) → **WRONG**. Use `script.path` in FlowSpec
- Your FlowSpec contains `apiVersion`, `type` (at node level), or `schedule` → **WRONG**. See the correct format below

> **CLI Format**: ALL DataWorks 2024-05-18 API calls use **PascalCase RPC direct invocation**:
> `aliyun dataworks-public CreateNode --ProjectId ... --Spec '...' --user-agent AlibabaCloud-Agent-Skills`
> This requires `aliyun` CLI >= 3.3.1. No plugin installation is needed.

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
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId 585549 \
  --Spec '{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_etl_workflow","script":{"path":"my_etl_workflow","runtime":{"command":"WORKFLOW"}}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills
# → Returns {"Id": "WORKFLOW_ID", ...}

# Step 2: Create upstream node (Shell) inside the workflow
aliyun dataworks-public CreateNode \
  --ProjectId 585549 \
  --Scene DATAWORKS_PROJECT \
  --ContainerId WORKFLOW_ID \
  --Spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"name":"check_data","script":{"path":"check_data","runtime":{"command":"DIDE_SHELL"},"content":"#!/bin/bash\necho done"},"outputs":{"nodeOutputs":[{"data":"my_project.check_data","artifactType":"NodeOutput"}]}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills
# → Returns {"Id": "NODE_A_ID", ...}

# Step 3: Create downstream node (SQL) with dependency on upstream
aliyun dataworks-public CreateNode \
  --ProjectId 585549 \
  --Scene DATAWORKS_PROJECT \
  --ContainerId WORKFLOW_ID \
  --Spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"name":"transform_data","script":{"path":"transform_data","runtime":{"command":"ODPS_SQL"},"content":"SELECT 1;"},"outputs":{"nodeOutputs":[{"data":"my_project.transform_data","artifactType":"NodeOutput"}]}}],"dependencies":[{"nodeId":"transform_data","depends":[{"type":"Normal","output":"my_project.check_data"}]}]}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Step 4: Set workflow schedule (daily at 00:30)
aliyun dataworks-public UpdateWorkflowDefinition \
  --ProjectId 585549 \
  --Id WORKFLOW_ID \
  --Spec '{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_etl_workflow","script":{"path":"my_etl_workflow","runtime":{"command":"WORKFLOW"}},"trigger":{"cron":"00 30 00 * * ?","timezone":"Asia/Shanghai","type":"Scheduler"}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Step 5: Deploy the workflow online (REQUIRED — workflow is not active until deployed)
aliyun dataworks-public CreatePipelineRun \
  --ProjectId 585549 \
  --Type Online --ObjectIds '["WORKFLOW_ID"]' \
  --user-agent AlibabaCloud-Agent-Skills
# → Returns {"Id": "PIPELINE_RUN_ID", ...}
# Then poll GetPipelineRun and advance stages with ExecPipelineRunStage
# (see "Publishing and Deploying" section below for full polling flow)
```

> **Key pattern**: CreateWorkflowDefinition → CreateNode (with ContainerId + outputs.nodeOutputs) → UpdateWorkflowDefinition (add trigger) → **CreatePipelineRun (deploy)**. Each node within a workflow MUST have `outputs.nodeOutputs`. **The workflow is NOT active until deployed via CreatePipelineRun.**

## Core Workflow

### Environment Discovery (Required Before Creating)

Before creating nodes or workflows, understand the project's existing environment. **It is recommended to use a subagent to execute queries**, returning only a summary to the main Agent to avoid raw data consuming too much context.

Subagent tasks:
1. Call `ListWorkflowDefinitions` to get the workflow list
2. Call `ListNodes` to get the existing node list
3. Return a summary (do not return raw data):
   - Workflow inventory: name + number of contained nodes + type (scheduled/manual)
   - Existing nodes relevant to the current task: name + type + parent workflow
   - Suggested target workflow (if inferable from the task description)

Based on the summary, the main Agent decides:
- **Target workflow**: Place into an existing workflow or create a new one, or create standalone (user decides)
- **Node naming**: Reference existing naming conventions for consistency
- **Dependencies**: Infer upstream/downstream relationships from SQL references and existing nodes

**Pre-creation conflict check (required, applies to all object types)**:
1. **Name duplication check**: Before creating any object, use the corresponding List API to check if an object with the same name already exists:
   - Workflow → `ListWorkflowDefinitions`
   - Node → `ListNodes` (node names are globally unique within a project)
   - Resource → `ListResources`
   - Function → `ListFunctions`
   - Component → `ListComponents`
2. **Handling existing objects**: Inform the user and ask how to proceed (use existing / rename / update existing). **Direct deletion of existing objects is prohibited**
3. **Output name conflict check**: A node's `outputs.nodeOutputs[].data` (format `${projectIdentifier}.NodeName`) must be unique within the project. If the output name of the node to be created conflicts with an existing node, the conflict must be resolved before creation

**Certainty level determines interaction approach**:
- Certain information → Use directly, do not ask the user
- Confident inference → Proceed, explain the reasoning in the output
- Uncertain information → Must ask the user

### Creating Nodes

**Unified workflow**: Whether in OpenAPI Mode or Git Mode, generate the same local file structure.

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
   - Read the code file → embed into `script.content`
   - Output the merged complete JSON
2. Validate the spec before submission:
   ```bash
   python $SKILL/scripts/validate.py ./my_node
   ```
3. Call the API to submit (refer to [references/api/CreateNode.md](references/api/CreateNode.md)):
   ```bash
   # DataWorks 2024-05-18 API does not yet have plugin mode (kebab-case), use RPC direct invocation format (PascalCase)
   aliyun dataworks-public CreateNode \
     --ProjectId $PROJECT_ID \
     --Scene DATAWORKS_PROJECT \
     --Spec "$(cat /tmp/spec.json)" \
     --user-agent AlibabaCloud-Agent-Skills
   ```
   > **Note**: `aliyun dataworks-public CreateNode` is in RPC direct invocation format and **does not require any plugin installation**. If the command is not found, check the aliyun CLI version (requires >= 3.3.1). **Never** downgrade to legacy kebab-case commands (`create-file`/`create-folder`).

   > **Sandbox fallback**: If `$(cat ...)` command substitution is blocked by the execution environment, use Python to pass the spec:
   > ```python
   > import subprocess, json
   > with open('/tmp/spec.json') as f: spec = f.read()
   > subprocess.run(['aliyun', 'dataworks-public', 'CreateNode',
   >   '--ProjectId', str(PROJECT_ID), '--Scene', 'DATAWORKS_PROJECT',
   >   '--Spec', spec, '--user-agent', 'AlibabaCloud-Agent-Skills'],
   >   capture_output=True, text=True)
   > ```
4. To place within a workflow, add `--ContainerId $WorkflowId`

**Git Mode** (when the user explicitly requests): `git add ./my_node && git commit`, DataWorks automatically syncs and replaces placeholders

**Minimum required fields** (verified in practice, universal across all 130+ types):
- `name` — Node name
- `script.path` — Script path, must end with the node name; the server automatically prepends the workflow prefix
- `script.runtime.command` — Node type (e.g., ODPS_SQL, DIDE_SHELL)

**Copyable minimal node Spec** (Shell node example):
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{
  "name":"my_shell_node",
  "script":{"path":"my_shell_node","runtime":{"command":"DIDE_SHELL"},"content":"#!/bin/bash\necho hello"}
}]}}
```

Other fields are not required; the server will automatically fill in project defaults:
- **datasource, runtimeResource** — If unsure, do not pass them; the server automatically binds project defaults
- **trigger** — If not passed, inherits the workflow schedule. Only pass when specified by the user
- **dependencies, rerunTimes, etc.** — Only pass when specified by the user
- **outputs.nodeOutputs** — Optional for standalone nodes; **required for nodes within a workflow** (`{"data":"${projectIdentifier}.NodeName","artifactType":"NodeOutput"}`), otherwise downstream dependencies silently fail

### Workflow and Node Relationship

```
Project
└── Workflow              ← Container, unified scheduling management
    ├── Node A            ← Minimum execution unit
    ├── Node B (depends A)
    └── Node C (depends B)
```

- A **workflow** is the container and scheduling unit for nodes, with its own trigger and strategy
- **Nodes** can exist independently at the root level or belong to a workflow (user decides)
- The workflow's `script.runtime.command` is always `"WORKFLOW"`
- Dependency configuration for nodes within a workflow: no need to dual-write in both `spec.dependencies` and `inputs.nodeOutputs`; only maintain dependencies in the `spec.dependencies` array. ⚠️ However, `spec.dependencies[*].nodeId` MUST exactly match the corresponding node's `id`, otherwise dependencies will not be recognized. Upstream nodes must declare `outputs.nodeOutputs` (`${projectIdentifier}.NodeName`)

### Creating Workflows

1. **Create the workflow definition** (minimal spec):
   ```json
   {"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{
     "name":"workflow_name","script":{"path":"workflow_name","runtime":{"command":"WORKFLOW"}}
   }]}}
   ```
   Call `CreateWorkflowDefinition` → returns WorkflowId
2. **Create nodes in dependency order** (each node passes `ContainerId=WorkflowId`)
   - Each node's spec **must include** `outputs.nodeOutputs`: `{"data":"${projectIdentifier}.NodeName","artifactType":"NodeOutput"}`
   - Nodes with upstream dependencies declare them in `spec.dependencies`, ensuring `dependencies[*].nodeId` exactly matches the node `id` (see workflow-guide.md)
3. **Set the schedule** — `UpdateWorkflowDefinition` with `trigger` (if the user specified a schedule)
4. **Deploy online (REQUIRED)** — `CreatePipelineRun(Type=Online, ObjectIds=[WorkflowId])` → poll `GetPipelineRun` → advance stages with `ExecPipelineRunStage`. **A workflow is NOT active until deployed.** Do not skip this step or tell the user to do it manually.

Detailed guide and copyable complete node Spec examples (including outputs and dependencies): [references/workflow-guide.md](references/workflow-guide.md)

### Updating Existing Nodes

**Must use incremental updates** — only pass the node id + fields to modify:
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{
  "id":"NodeID",
  "script":{"content":"new code"}
}]}}
```

> **⚠️ Critical**: UpdateNode **always** uses `"kind":"Node"`, even if the node belongs to a workflow. Do NOT use `"kind":"CycleWorkflow"` — that is only for workflow-level operations (`UpdateWorkflowDefinition`).

**Do not pass unchanged fields like datasource or runtimeResource** (the server may have corrected values; passing them back can cause errors).

#### Update + Republish Workflow

Complete end-to-end flow for modifying an existing node and deploying the change:

1. **Find the node** — `ListNodes(Name=xxx)` → get Node ID
2. **Update the node** — `UpdateNode` with incremental spec (`kind:Node`, only `id` + changed fields)
3. **Publish** — `CreatePipelineRun(type=Online, object_ids=[NodeID])` → poll `GetPipelineRun` → advance stages with `ExecPipelineRunStage`

```bash
# Step 1: Find the node
aliyun dataworks-public ListNodes --ProjectId $PID --Name "my_node" --user-agent AlibabaCloud-Agent-Skills
# → Note the node Id from the response

# Step 2: Update (incremental — only id + changed fields)
aliyun dataworks-public UpdateNode --ProjectId $PID --Id $NODE_ID \
  --Spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"'$NODE_ID'","script":{"content":"SELECT 1;"}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills

# Step 3: Publish (see "Publishing and Deploying" below)
aliyun dataworks-public CreatePipelineRun --ProjectId $PID \
  --PipelineRunParam '{"type":"Online","objectIds":["'$NODE_ID'"]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Common wrong paths after UpdateNode** (all prohibited):
> - ❌ `DeployFile` / `SubmitFile` — legacy APIs, will fail or behave unexpectedly
> - ❌ `ImportWorkflowDefinition` — for initial bulk import only, not for updating or publishing
> - ❌ `ListFiles` / `GetFile` — legacy file model, use `ListNodes` / `GetNode` instead
> - ✅ `CreatePipelineRun` → `GetPipelineRun` → `ExecPipelineRunStage`

### Publishing and Deploying

> **⚠️ NEVER use `DeployFile`, `SubmitFile`, `ListDeploymentPackages`, `GetDeploymentPackage`, `ListFiles`, or `GetFile` for deployment.** These are all legacy APIs. Use ONLY: `CreatePipelineRun` → `GetPipelineRun` → `ExecPipelineRunStage`.

Publishing is an asynchronous multi-stage pipeline:

1. `CreatePipelineRun(Type=Online, ObjectIds=[ID])` → get PipelineRunId
2. Poll `GetPipelineRun` → check `Pipeline.Status` and `Pipeline.Stages`
3. When a Stage has `Init` status and all preceding Stages are `Success` → call `ExecPipelineRunStage(Code=Stage.Code)` to advance
4. Until the Pipeline overall status becomes `Success` / `Fail`

**Key point**: The Build stage runs automatically, but the Check and Deploy stages must be manually advanced. Detailed CLI examples and polling scripts are in [references/deploy-guide.md](references/deploy-guide.md).

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
3. Use the `GetNode` API to get the spec of a similar node from the live environment as a reference
4. If none of the above works → fall back to `DIDE_SHELL` and use command-line tools within the Shell to accomplish the task

## Key Constraints

1. **script.path is required**: Script path, must end with the node name. When creating, you can pass just the node name; the server automatically prepends the workflow prefix
2. **Dependencies are configured via `spec.dependencies`**: No need to dual-write in both `spec.dependencies` and `inputs.nodeOutputs`; only maintain dependencies in the `spec.dependencies` array. ⚠️ However, `spec.dependencies[*].nodeId` MUST exactly match the corresponding node's `id`, otherwise dependencies will not be recognized. Upstream nodes must declare `outputs.nodeOutputs` (`${projectIdentifier}.NodeName`)
3. **Immutable properties**: A node's `command` (node type) cannot be changed after creation; incorrect configuration requires deletion and recreation (user must be informed and must confirm before deletion)
4. **Updates must be incremental**: Only pass id + fields to modify; do not pass unchanged fields like datasource/runtimeResource
5. **datasource.type may be corrected by the server**: e.g., `flink` → `flink_serverless`; use the generic type when creating
6. **Nodes can exist independently**: Nodes can be created at the root level (without passing ContainerId) or belong to a workflow (pass ContainerId=WorkflowId). Whether to place in a workflow is the user's decision
7. **Workflow command is always WORKFLOW**: `script.runtime.command` must be `"WORKFLOW"`
8. **Automatic deletion of existing objects is prohibited**: When creation or publishing fails, **never** attempt to "fix" the problem by deleting existing objects with the same name (nodes, workflows, resources, functions, components). Existing objects may contain important user configurations and data; deletion is an irreversible dangerous operation. Correct approach: diagnose the failure cause → inform the user of the specific conflict → let the user decide how to handle it (rename / update existing / user manually deletes)
9. **Name conflict check is required before creation**: Before calling any Create API, use the corresponding List API to confirm the name is not duplicated (see "Environment Discovery"). Name conflicts will cause creation failure; duplicate node output names (`outputs.nodeOutputs[].data`) will cause dependency errors or publishing failure
10. **Mutating operations require user confirmation**: Except for Create and read-only queries (Get/List), all OpenAPI operations that modify or delete existing objects (Delete, Update, Move, Rename, Abolish, etc.) **must be shown to the user with explicit confirmation obtained before execution**. Confirmation information should include: operation type, target object name/ID, and key changes. These APIs must not be called before user confirmation
11. **Use only 2024-05-18 version APIs**: All APIs in this skill are DataWorks 2024-05-18 version. Legacy APIs (`create-file`, `create-folder`, `CreateFlowProject`, etc.) are prohibited. If an API call returns an error, first check [troubleshooting.md](references/troubleshooting.md); do not fall back to legacy APIs
12. **Stop on errors instead of brute-force retrying**: If the same error code appears more than 2 consecutive times, the approach is wrong. Stop and analyze the error cause (check [troubleshooting.md](references/troubleshooting.md)) instead of repeatedly retrying the same incorrect API with different parameters. **Never fall back to legacy APIs** (`create-file`, `create-business`, etc.) when a new API fails — review the FlowSpec Anti-Patterns table at the top of this document instead. **Specific trap**: If `aliyun help` output mentions "Plugin available but not installed" for dataworks-public, do NOT install the plugin — this leads to using deprecated kebab-case APIs. Instead, use PascalCase RPC directly (e.g., `aliyun dataworks-public CreateNode`)
13. **CLI parameter names must be checked in documentation, guessing is prohibited**: Before calling an API, you must first check `references/api/{APIName}.md` to confirm parameter names. Common mistakes: `GetProject`'s ID parameter is `--Id` (not `--ProjectId`); `UpdateNode` requires `--Id`. When unsure, verify with `aliyun dataworks-public {APIName} --help`
14. **PascalCase RPC only, no kebab-case**: CLI commands must use `aliyun dataworks-public CreateNode` (PascalCase), never `aliyun dataworks-public create-node` (kebab-case). No plugin installation is needed. If the command is not found, upgrade `aliyun` CLI to >= 3.3.1
15. **No wrapper scripts**: Run each `aliyun` CLI command directly in the shell. Never create `.sh`/`.py` wrapper scripts to batch multiple API calls — this obscures errors and makes debugging impossible. Execute one API call at a time, check the response, then proceed
16. **API response = success, not file output**: Writing JSON spec files to disk is a preparation step, not completion. The task is complete only when the `aliyun` CLI returns a success response with a valid `Id`. If the API call fails, fix the spec and retry — do not declare the task done by saving local files
17. **On error: re-read the Quick Start, do not invent new approaches**: When an API call fails, compare your spec against the exact Quick Start example at the top of this document field by field. The most common cause is an invented FlowSpec field that does not exist. Copy the working example and modify only the values you need to change
18. **Idempotency protection for write operations**: DataWorks 2024-05-18 Create APIs (`CreateNode`, `CreateWorkflowDefinition`, `CreatePipelineRun`, etc.) do not support a `ClientToken` parameter. To prevent duplicate resource creation on network retries or timeouts:
    - **Before creating**: Always run the pre-creation conflict check (List API) as described in "Environment Discovery" — this is the primary idempotency gate
    - **After a network error or timeout on Create**: Do NOT blindly retry. First call the corresponding List/Get API to check whether the resource was actually created (the server may have processed the request despite the client-side error). Only retry if the resource does not exist
    - **Record RequestId**: Every API response includes a `RequestId` field. Log it so that duplicate-creation incidents can be traced and resolved via Alibaba Cloud support

## API Quick Reference

> **API Version**: All APIs listed below are DataWorks **2024-05-18** version. CLI invocation format: `aliyun dataworks-public {APIName} --Parameter --user-agent AlibabaCloud-Agent-Skills` (PascalCase RPC direct invocation; DataWorks 2024-05-18 does not yet have plugin mode). **Only use the APIs listed in the table below**; do not search for or use other DataWorks APIs.

Detailed parameters and code templates for each API are in `references/api/{APIName}.md`. If a call returns an error, you can get the latest definition from `https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/{APIName}/api.json`.

### Components

| API | Description |
|-----|------|
| [CreateComponent](references/api/CreateComponent.md) | Create a component |
| [DeleteComponent](references/api/DeleteComponent.md) | Delete a component |
| [GetComponent](references/api/GetComponent.md) | Get component details |
| [UpdateComponent](references/api/UpdateComponent.md) | Update a component |
| [ListComponents](references/api/ListComponents.md) | List components |

### Nodes

| API | Description |
|-----|------|
| [CreateNode](references/api/CreateNode.md) | Create a data development node. project_id + scene + spec, optional container_id |
| [DeleteNode](references/api/DeleteNode.md) | Delete a data development node |
| [UpdateNode](references/api/UpdateNode.md) | Update node information. Incremental update, only pass id + fields to change |
| [MoveNode](references/api/MoveNode.md) | Move a node to a specified path |
| [RenameNode](references/api/RenameNode.md) | Rename a node |
| [GetNode](references/api/GetNode.md) | Get node details, returns the complete spec |
| [ListNodes](references/api/ListNodes.md) | List nodes, supports filtering by workflow |
| [ListNodeDependencies](references/api/ListNodeDependencies.md) | List a node's dependency nodes |

### Workflow Definitions

| API | Description |
|-----|------|
| [CreateWorkflowDefinition](references/api/CreateWorkflowDefinition.md) | Create a workflow. project_id + spec |
| [ImportWorkflowDefinition](references/api/ImportWorkflowDefinition.md) | Import a workflow (initial bulk import ONLY — do NOT use for updates or publishing; use `UpdateNode` + `CreatePipelineRun` instead) |
| [DeleteWorkflowDefinition](references/api/DeleteWorkflowDefinition.md) | Delete a workflow |
| [UpdateWorkflowDefinition](references/api/UpdateWorkflowDefinition.md) | Update workflow information, incremental update |
| [MoveWorkflowDefinition](references/api/MoveWorkflowDefinition.md) | Move a workflow to a target path |
| [RenameWorkflowDefinition](references/api/RenameWorkflowDefinition.md) | Rename a workflow |
| [GetWorkflowDefinition](references/api/GetWorkflowDefinition.md) | Get workflow details |
| [ListWorkflowDefinitions](references/api/ListWorkflowDefinitions.md) | List workflows, filter by type |

### Resources

| API | Description |
|-----|------|
| [CreateResource](references/api/CreateResource.md) | Create a file resource |
| [DeleteResource](references/api/DeleteResource.md) | Delete a file resource |
| [UpdateResource](references/api/UpdateResource.md) | Update file resource information, incremental update |
| [MoveResource](references/api/MoveResource.md) | Move a file resource to a specified directory |
| [RenameResource](references/api/RenameResource.md) | Rename a file resource |
| [GetResource](references/api/GetResource.md) | Get file resource details |
| [ListResources](references/api/ListResources.md) | List file resources |

### Functions

| API | Description |
|-----|------|
| [CreateFunction](references/api/CreateFunction.md) | Create a UDF function |
| [DeleteFunction](references/api/DeleteFunction.md) | Delete a UDF function |
| [UpdateFunction](references/api/UpdateFunction.md) | Update UDF function information, incremental update |
| [MoveFunction](references/api/MoveFunction.md) | Move a function to a target path |
| [RenameFunction](references/api/RenameFunction.md) | Rename a function |
| [GetFunction](references/api/GetFunction.md) | Get function details |
| [ListFunctions](references/api/ListFunctions.md) | List functions |

### Publishing Pipeline

| API | Description |
|-----|------|
| [CreatePipelineRun](references/api/CreatePipelineRun.md) | Create a publishing pipeline. type=Online/Offline |
| [AbolishPipelineRun](references/api/AbolishPipelineRun.md) | Abort a publishing pipeline |
| [ExecPipelineRunStage](references/api/ExecPipelineRunStage.md) | Execute a specified stage of the publishing pipeline, async requires polling |
| [GetPipelineRun](references/api/GetPipelineRun.md) | Get publishing pipeline details, returns Stages status |
| [ListPipelineRuns](references/api/ListPipelineRuns.md) | List publishing pipelines |
| [ListPipelineRunItems](references/api/ListPipelineRunItems.md) | Get publishing content |

### Auxiliary Queries

| API | Description |
|-----|------|
| [GetProject](references/api/GetProject.md) | Get projectIdentifier by id |
| [ListDataSources](references/api/ListDataSources.md) | List data sources |
| [ListResourceGroups](references/api/ListResourceGroups.md) | List resource groups |

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
