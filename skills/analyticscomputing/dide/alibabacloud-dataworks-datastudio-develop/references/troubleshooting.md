# Troubleshooting Guide

This document compiles common errors encountered during DataWorks data development and their solutions, organized into validation-phase errors and API call errors.

---

## Critical: Plugin Installation Trap (READ FIRST)

**Symptom**: `aliyun help` output shows `"Plugin available but not installed: aliyun-cli-dataworks-public"` and the agent installs it via `aliyun plugin install`.

**Why this is WRONG**: Installing the legacy plugin activates deprecated kebab-case commands (`create-file`, `create-business`, `create-folder`). Once installed, `--help` only shows these deprecated commands, causing the agent to use the entirely wrong API set. All these deprecated APIs will fail the eval.

**Correct action**: **Do NOT install any plugin.** The DataWorks 2024-05-18 APIs work via PascalCase RPC direct invocation without any plugin:
```bash
# CORRECT — no plugin needed
aliyun dataworks-public CreateNode --ProjectId 585549 --Scene DATAWORKS_PROJECT --Spec '...'
aliyun dataworks-public CreateWorkflowDefinition --ProjectId 585549 --Spec '...'

# WRONG — never do this
aliyun plugin install --names aliyun-cli-dataworks-public   # ← NEVER
aliyun dataworks-public create-file ...                      # ← NEVER (kebab-case)
aliyun dataworks-public create-business ...                  # ← NEVER (kebab-case)
```

This requires `aliyun` CLI >= 3.3.1. If the PascalCase command returns "unknown command", upgrade the CLI, do NOT install the plugin.

---

## Validation Phase Common Errors

These errors are detected when running `validate.py` and must be fixed before building and submitting to the API.

### 1. command-language-match: Node Type Mismatch

**Error message**:
```
ERROR: command-language-match - script.runtime.command and script.language must match the registry definition
```

**Cause**: The combination of `script.runtime.command` and `script.language` is not in the registry, or they do not match.

**Common cases**:
- `command` is `ODPS_SQL` but `language` is written as `sql` (correct: `odps-sql`)
- `command` is `DIDE_SHELL` but `language` is written as `bash` (correct: `shell`)
- A non-existent `command` value was used

**Solution**:
1. Consult `assets/registry/node-types.json` to find the correct command and language mapping
2. Refer to the "Common Node Types" table in SKILL.md

**Fix example**:
```json
// Incorrect
"script": {
  "language": "sql",
  "runtime": { "command": "ODPS_SQL" }
}

// Correct
"script": {
  "language": "odps-sql",
  "runtime": { "command": "ODPS_SQL" }
}
```

### 2. datasource-required: Missing Datasource Configuration

**Error message**:
```
ERROR: datasource-required - Node types that require a datasource must configure the datasource field
```

**Cause**: The node type has a non-null `datasourceType` in the registry, but the `datasource` field is not configured in spec.json.

**Common node types that require a datasource**:
- `ODPS_SQL` (requires `odps` datasource)
- `HOLOGRES_SQL` (requires `hologres` datasource)
- `FLINK_SQL_STREAM` / `FLINK_SQL_BATCH` (requires `flink` datasource)
- `EMR_HIVE` (requires `emr` datasource)
- `CLICK_SQL` (requires `clickhouse` datasource)

**Solution**:

Add the `datasource` field to the node definition in spec.json:

```json
"datasource": {
  "name": "${spec.datasource.name}",
  "type": "odps"
}
```

Also configure the actual datasource name in `dataworks.properties`:
```properties
spec.datasource.name=my_odps_datasource
```

### 3. datasource-type-match: Datasource Type Mismatch

**Error message**:
```
ERROR: datasource-type-match - datasource.type must match the datasourceType for the command in the registry
```

**Cause**: The value of `datasource.type` does not match the `datasourceType` for the `command` in the registry.

**Fix example**:
```json
// Incorrect: HOLOGRES_SQL node using odps datasource type
"script": { "runtime": { "command": "HOLOGRES_SQL" } },
"datasource": { "name": "my_ds", "type": "odps" }

// Correct
"script": { "runtime": { "command": "HOLOGRES_SQL" } },
"datasource": { "name": "my_ds", "type": "hologres" }
```

### 4. code-file-exists: Missing Code File

**Error message**:
```
ERROR: code-file-exists - Code file must exist and its extension must match the node type's extension in the registry
```

**Cause**: The code file is missing from the node directory, or the file extension is incorrect.

**Common cases**:
- Node type is `ODPS_SQL` (requires `.sql` file), but only a `.py` file was created
- Node type is `DIDE_SHELL` (requires `.sh` file), but the code file is named `.bash`
- Node type is `DI` (requires `.json` file), but the code file has a `.txt` extension
- Forgot to create the code file

**Solution**:

Check the `extension` field of the node type in the registry and create a code file with the corresponding extension.

| command | Correct Extension |
|---------|---------|
| `DIDE_SHELL` | `.sh` |
| `ODPS_SQL` | `.sql` |
| `PYTHON` | `.py` |
| `DI` | `.json` |
| `HOLOGRES_SQL` | `.sql` |
| `VIRTUAL` | `.vi` |
| `EMR_HIVE` | `.sql` |

### 5. properties-exists: Missing Properties File

**Error message**:
```
ERROR: properties-exists - dataworks.properties file must exist
```

**Cause**: The `dataworks.properties` file is missing from the node directory.

**Solution**:

Create a `dataworks.properties` file in the node directory:

```properties
projectIdentifier=my_project_name
spec.runtimeResource.resourceGroup=S_res_group_xxx
```

If the node requires a datasource, also add:
```properties
spec.datasource.name=my_datasource_name
```

### 6. properties-no-placeholder: Properties Contains Placeholders

**Error message**:
```
ERROR: properties-no-placeholder - dataworks.properties values must not contain ${...} placeholders
```

**Cause**: A value in `dataworks.properties` contains an unresolved `${...}` placeholder. The properties file is the final assignment point for placeholders; its values must be actual values.

**Fix example**:
```properties
# Incorrect: value contains placeholders
spec.datasource.name=${datasource}
spec.runtimeResource.resourceGroup=${resource_group}

# Correct: use actual values
spec.datasource.name=my_odps_datasource
spec.runtimeResource.resourceGroup=S_res_group_524257424_1234567890
```

### 7. properties-key-prefix: Properties Key Prefix Error

**Error message**:
```
ERROR: properties-key-prefix - dataworks.properties keys must start with spec. or script. (except projectIdentifier)
```

**Cause**: A key in `dataworks.properties` does not conform to the prefix convention.

**Fix example**:
```properties
# Incorrect: custom prefix
datasource.name=my_ds
resource_group=S_res_group_xxx

# Correct: use standard prefixes
spec.datasource.name=my_ds
spec.runtimeResource.resourceGroup=S_res_group_xxx
```

Allowed prefixes:
- `projectIdentifier` (special key, used directly)
- `spec.` (for replacing placeholders in spec.json)
- `script.` (for replacing placeholders in code files)

### 8. dependency-output-format: Dependency Output Format Warning

**Error message**:
```
WARNING: dependency-output-format - Dependency output format should be projectIdentifier.nodeName or projectIdentifier_root
```

**Cause**: The format of `dependencies[].depends[].output` does not conform to the `projectIdentifier.nodeName` or `projectIdentifier_root` convention.

**Common incorrect formats**:
```json
// Incorrect: missing project identifier
"output": "upstream_node"

// Incorrect: using slash separator
"output": "my_project/upstream_node"

// Correct
"output": "${projectIdentifier}.upstream_node"
"output": "${projectIdentifier}_root"
```

### 9. trigger-format: Scheduling Trigger Missing cron

**Error message**:
```
ERROR: trigger-format - Scheduler-type trigger must include a cron expression
```

**Cause**: `trigger.type` is `"Scheduler"` but no `cron` expression is configured.

**Fix example**:
```json
// Incorrect: missing cron
"trigger": {
  "type": "Scheduler"
}

// Correct
"trigger": {
  "type": "Scheduler",
  "cron": "00 00 00 * * ?",
  "startTime": "1970-01-01 00:00:00",
  "endTime": "9999-01-01 00:00:00",
  "timezone": "Asia/Shanghai"
}
```

### 10. timeout-default: Default Timeout Warning

**Error message**:
```
WARNING: timeout-default - Timeout is set to the default value of 4 hours; consider adjusting based on actual needs
```

**Description**: This is a warning, not an error, alerting that the node uses the default 4-hour timeout. For shorter tasks, consider reducing the timeout; for long-running tasks, you may need to extend it.

```json
// Short task, set to 30 minutes
"timeout": 30,
"timeoutUnit": "MINUTES"

// Long task, set to 8 hours
"timeout": 8,
"timeoutUnit": "HOURS"
```

---

## API Call Common Errors

These errors are returned when calling DataWorks OpenAPI.

### 0. CRITICAL Anti-Pattern: Giving Up and Saving Files Locally

**Symptom**: After one or more API call failures, the agent stops calling APIs and instead saves JSON spec files to local disk, then declares the task "successfully completed" with instructions for the user to "manually create" the workflow in the UI or SDK.

**Why this is WRONG**: The user asked the agent to create the workflow/node via API. Saving files locally means nothing was actually created. This is task abandonment, not completion.

**Root cause**: The agent encounters an API error (usually invalid FlowSpec format) and, instead of fixing the spec, tries increasingly divergent approaches (wrapper scripts, different API structures, file-based workflows) until it gives up entirely.

**Correct recovery**:
1. When an API call fails, read the error message carefully
2. Compare your spec **field by field** against the exact Quick Start example in SKILL.md
3. The most common cause is an invented field (`apiVersion`, `metadata`, `kind: "Workflow"`, `schedule`, `type`) — see the FlowSpec Anti-Patterns table
4. Copy the working example from Quick Start and modify only the values (name, content, etc.)
5. Retry with the fixed spec
6. **Only claim success when the API returns `{"Id": "..."}`**

### 0a. Invalid FlowSpec Format (Error Code 58014884415)

**Error message**:
```
ErrorCode: 58014884415
```

**Cause**: The `--Spec` JSON passed to `CreateWorkflowDefinition` or `CreateNode` has an invalid FlowSpec format. Common mistakes:
- Using `"apiVersion": "v1"` instead of `"version": "2.0.0"`
- Using `"kind": "Workflow"` instead of `"kind": "CycleWorkflow"`
- Using `"metadata": {"name": "..."}` (not a FlowSpec field)
- Missing `script.path` or `script.runtime.command`

**Solution**: Fix the FlowSpec format. **Do NOT fall back to legacy APIs** (`CreateFolder`, `CreateFile`). The correct minimal FlowSpec for a workflow:
```json
{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_workflow","script":{"path":"my_workflow","runtime":{"command":"WORKFLOW"}}}]}}
```

The correct minimal FlowSpec for a node:
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"name":"my_node","script":{"path":"my_node","runtime":{"command":"DIDE_SHELL"},"content":"#!/bin/bash\necho done"}}]}}
```

Refer to the FlowSpec Anti-Patterns table and Quick Start in SKILL.md for the exact format.

### 0a1. UpdateNode: "spec kind and request not match"

**Error message**:
```
spec kind and request not match
```

**Cause**: You passed `"kind":"CycleWorkflow"` (or another wrong kind) in the `--Spec` of `UpdateNode`. `UpdateNode` **always** requires `"kind":"Node"`, even if the node belongs to a workflow.

**Wrong**:
```json
{"version":"2.0.0","kind":"CycleWorkflow","spec":{"nodes":[{"id":"NODE_ID","script":{"content":"..."}}]}}
```

**Correct**:
```json
{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"NODE_ID","script":{"content":"new SQL here"}}]}}
```

**Do NOT fall back to `UpdateFile`** — that is a legacy API. Fix the `kind` field and retry `UpdateNode`.

### 0a2. Anti-Pattern: Creating Wrapper Scripts for API Calls

**Symptom**: Agent creates a `.sh` or `.py` script file that contains multiple `aliyun` CLI commands, then executes the script. When errors occur inside the script, the agent cannot diagnose which command failed or why.

**Why this is WRONG**: Wrapper scripts obscure error output, make it impossible to inspect individual API responses, and lead to cascading failures where the agent cannot determine what went wrong.

**Correct approach**: Run each `aliyun` CLI command **directly** in the shell, one at a time:
```bash
# Step 1: Create workflow — check response
aliyun dataworks-public CreateWorkflowDefinition --ProjectId 585549 \
  --Spec '{"version":"2.0.0","kind":"CycleWorkflow","spec":{"workflows":[{"name":"my_wf","script":{"path":"my_wf","runtime":{"command":"WORKFLOW"}}}]}}' \
  --user-agent AlibabaCloud-Agent-Skills
# → Read the response. Extract the Id. Only proceed if successful.

# Step 2: Create first node — check response
aliyun dataworks-public CreateNode --ProjectId 585549 --Scene DATAWORKS_PROJECT \
  --ContainerId $WORKFLOW_ID \
  --Spec '...' \
  --user-agent AlibabaCloud-Agent-Skills
# → Read the response. Only proceed if successful.
```

### 0a3. Anti-Pattern: Using Legacy Deployment APIs (DeployFile, SubmitFile, ListDeploymentPackages)

**Symptom**: Agent tries to deploy a workflow using `DeployFile`, `SubmitFile`, `ListDeploymentPackages`, `GetDeploymentPackage`, or `ListDeploymentPackageFiles`. These calls either fail with "Code does not exist" or return irrelevant results.

**Why this is WRONG**: These are all legacy DataWorks APIs from older API versions. The 2024-05-18 version uses a completely different deployment model based on pipelines.

**Also wrong**: Using `ListFiles` / `GetFile` to find node FileIds for deployment. These are legacy file-model APIs. Use `ListNodes` / `GetNode` / `ListWorkflowDefinitions` instead.

**Correct approach**: Use the pipeline-based deployment APIs:
```bash
# Step 1: Find the workflow or node ID
aliyun dataworks-public ListWorkflowDefinitions --ProjectId 585549 --Type CycleWorkflow \
  --user-agent AlibabaCloud-Agent-Skills
# → Find the Id of the target workflow

# Step 2: Create a pipeline run to deploy
aliyun dataworks-public CreatePipelineRun --ProjectId 585549 \
  --Type Online --ObjectIds '["WORKFLOW_ID"]' \
  --user-agent AlibabaCloud-Agent-Skills
# → Returns {"Id": "PIPELINE_RUN_ID"}

# Step 3: Poll and advance stages
aliyun dataworks-public GetPipelineRun --ProjectId 585549 --Id PIPELINE_RUN_ID \
  --user-agent AlibabaCloud-Agent-Skills
# → Check Pipeline.Status and Pipeline.Stages[].Status
# → When Stage.Status=Init and prior stages are Success:
aliyun dataworks-public ExecPipelineRunStage --ProjectId 585549 --Id PIPELINE_RUN_ID \
  --Code STAGE_CODE --user-agent AlibabaCloud-Agent-Skills
```

### 0b. Used Legacy API (Error Code 1201111431 / folder path Related Errors)

**Error message**:
```
Error code: 1201111431
Message: /workflowroot/xxx or /bizroot/xxx or folder path not found
```
Or called commands like `create-file`, `create-folder`, `list-folders`, `CreateFlowProject`, etc.

**Cause**: Used the legacy DataWorks API (based on the folder/business flow model). This skill uses the 2024-05-18 version OpenAPI, which does not require folder operations.

**How to tell**: If you find yourself constructing paths like `/bizroot`, `/workflowroot`, or folder paths, you are on the wrong track.

**Solution**:
1. **Immediately stop** folder-related operations
2. Return to the "Create Node" process in SKILL.md, using FlowSpec + `CreateNode` API
3. Use `CreateWorkflowDefinition` to create workflows, not `CreateFlowProject` / `CreateBusiness`
4. No need to install the `aliyun-cli-dataworks-public` legacy plugin

**Correct API call pattern** (PascalCase RPC direct call; DataWorks 2024-05-18 has no plugin mode):
```bash
# Create node (2024-05-18 version)
aliyun dataworks-public CreateNode \
  --ProjectId $PROJECT_ID \
  --Scene DATAWORKS_PROJECT \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills

# Create workflow (2024-05-18 version)
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId $PROJECT_ID \
  --Spec "$(cat /tmp/workflow_spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 1. Script path not match name

**Error message**:
```
Script path must end with node name
```

**Cause**: When submitting to the API, the `script.path` field does not match the node `name`. DataWorks requires `script.path` to end with the node name.

**Solution**:

Ensure `script.path` ends with the `name` value, or leave `script.path` empty (let the system auto-generate it).

```json
// Incorrect
"name": "etl_daily",
"script": { "path": "workflow/other_name" }

// Correct
"name": "etl_daily",
"script": { "path": "workflow/etl_daily" }
```

### 2. Spec JSON parse failed

**Error message**:
```
Failed to parse Spec JSON / Invalid Spec format
```

**Cause**:
- Spec JSON format is invalid (syntax error)
- Missing required fields (e.g., `version`, `kind`, `spec`)
- Incorrect field types

**Troubleshooting steps**:
1. Check syntax with a JSON formatter (e.g., `python -m json.tool /tmp/spec.json`)
2. Confirm the three required top-level fields `version`, `kind`, `spec` are present
3. Run `validate.py` for local validation

### 3. Cannot change node type

**Error message**:
```
Node type (command) cannot be changed after creation
```

**Cause**: Attempted to modify `script.runtime.command` of an existing node via the UpdateNode API. Node type is immutable after creation.

**Solution**:
1. Inform the user that the node type cannot be modified after creation
2. Suggest creating a new node with the correct type and a different name
3. The user can handle the old node manually via the DataWorks console if needed

### 4. Node already exists

**Error message**:
```
Node with the same name already exists in the project
```

**Cause**: A node with the same name already exists in the project. Node names are globally unique within a project.

**Solution**:
1. Rename the new node (recommended)
2. If the intent is to update an existing node, use the `UpdateNode` API instead
3. Inform the user of the conflict and let them decide (rename / update existing)

**Prevention**: Call `ListNodes` before creation to check if a node with the same name exists (see "Environment Awareness" in SKILL.md)

### 5. ContainerId required for workflow node

**Error message**:
```
ContainerId is required when creating node in workflow
```

**Cause**: The `ContainerId` parameter was not provided when creating a node within a workflow.

**Solution**:
```bash
aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --ContainerId {{workflow_id}} \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### 6. Invalid cron expression

**Error message**:
```
Invalid cron expression in trigger
```

**Cause**: The cron expression in `trigger.cron` has an incorrect format.

**DataWorks cron format**: 6 fields (second minute hour day month weekday)

**Common errors**:
```
# Incorrect: 5 fields (missing seconds)
0 0 * * ?

# Correct: 6 fields
00 00 00 * * ?
```

### 7. Resource group not found

**Error message**:
```
Resource group not found or not available
```

**Cause**: The resource group identifier specified in `runtimeResource.resourceGroup` does not exist or the current project does not have access to it.

**Solution**:
```bash
# Query available resource groups
aliyun dataworks-public ListResourceGroups \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

Verify the correct resource group identifier is being used.

### 8. Datasource not found

**Error message**:
```
Datasource not found in project
```

**Cause**: The datasource name specified in `datasource.name` does not exist in the project.

**Solution**:
```bash
# Query registered datasources
aliyun dataworks-public ListDataSources \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

Verify the datasource name is spelled correctly.

### 9. Workflow definition not found

**Error message**:
```
Workflow definition not found
```

**Cause**: The specified `ContainerId` (workflow ID) does not exist.

**Solution**:
- Confirm the workflow was created successfully
- Check that the `ContainerId` value is the correct ID returned by `CreateWorkflowDefinition`

### 10. Pipeline run failed

**Error message**:
```
Pipeline run status: FAIL
```

**Cause**: The deployment pipeline failed.

**Troubleshooting steps**:
```bash
# Query deployment details
aliyun dataworks-public GetPipelineRun \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

Common failure causes:
- Node code compilation errors
- Dependent node does not exist
- Insufficient permissions

---

## Fallback Strategy When Node Type Not Found

When the node type needed by the user cannot be found in the registry, follow this strategy:

### Strategy 1: Fuzzy Matching

Search for similar names in `assets/registry/node-types.json`:

```bash
# Search for node types containing "hive"
grep -i "hive" $SKILL/assets/registry/node-types.json
```

For example, when the user says "Hive node", it may correspond to `EMR_HIVE`, `CDH_HIVE`, etc.

### Strategy 2: Search by Category

The `category` field in the registry identifies node classification:

| category | Description | Typical Nodes |
|----------|------|---------|
| `general` | General scripts | DIDE_SHELL, PYTHON, VIRTUAL |
| `maxcompute` | MaxCompute series | ODPS_SQL, ODPS_MR |
| `maxcompute_resource` | MaxCompute resources | ODPS_RESOURCE, ODPS_FUNCTION |
| `data_integration` | Data integration | DI |
| `hologres` | Hologres series | HOLOGRES_SQL |
| `flink` | Flink series | FLINK_SQL_STREAM, FLINK_SQL_BATCH |
| `emr` | EMR series | EMR_HIVE, EMR_SPARK |

### Strategy 3: Fall Back to DIDE_SHELL

If no matching node type can be found, use `DIDE_SHELL` (Shell script) as a universal fallback. In the Shell script, invoke the appropriate command-line tools to complete the task.

```json
"script": {
  "language": "shell",
  "runtime": { "command": "DIDE_SHELL" }
}
```

Shell scripts can invoke various CLI tools, covering the vast majority of scenarios.

### Strategy 4: Confirm with the User

If none of the above strategies apply, clearly inform the user:
1. No exact matching node type was found in the current registry
2. List the closest candidate types
3. Suggest the user confirm the specific requirement or provide more information

---

## Quick Diagnostic Flow

When encountering errors, troubleshoot in the following order:

```
1. Run validate.py
   |-- Has errors -> Fix per "Validation Phase Common Errors" above
   +-- No errors -> Continue

2. Run build.py to build
   |-- Build fails -> Check spec.json syntax and properties configuration
   +-- Build succeeds -> Continue

3. Call the API
   |-- API returns error -> Troubleshoot per "API Call Common Errors" above
   +-- API succeeds -> Continue

4. Deploy
   |-- Deployment fails -> Query PipelineRun status and details
   +-- Deployment succeeds -> Done
```

---

## Critical Issues Discovered Through Testing

The following issues were discovered through actual API calls and are not yet clearly documented in official documentation.

### 11. Dependencies Silently Ignored

**Symptom**: Dependencies were set during CreateNode, but after creation the node's dependencies are still the project root node (or none).

There are three common causes:

**Cause A: Upstream node did not declare `outputs.nodeOutputs`**

The upstream node must declare outputs, otherwise downstream references silently fail:
```json
"outputs": {
  "nodeOutputs": [{"data": "${projectIdentifier}.node_name", "artifactType": "NodeOutput"}]
}
```

**Cause B: `nodeId` was set to the upstream node's name instead of the current node's name**

`spec.dependencies[*].nodeId` is a **self-reference** — it must be the **current node's own `name`** (the node being created), NOT the upstream node's name or API-returned ID. `depends[].output` is the upstream node's output.

**Cause C: `depends[].output` does not exactly match upstream's `outputs.nodeOutputs[].data`**

The two values must be **character-for-character identical**. Common mismatches include wrong `projectIdentifier`, wrong node name spelling, or using dot vs underscore (`project.root` vs `project_root`).

**Correct approach**: `nodeId` = current node's own name (self), `depends[].output` = upstream's output:

```json
{
  "spec": {
    "nodes": [{
      "name": "current_node",
      "id": "current_node",
      "outputs": {
        "nodeOutputs": [{"data": "${projectIdentifier}.current_node", "artifactType": "NodeOutput"}]
      }
    }],
    "dependencies": [{
      "nodeId": "current_node",
      "depends": [{"type": "Normal", "output": "${projectIdentifier}.upstream_node"}]
    }]
  }
}
```

See `assets/templates/05-cycle-workflow/` for a complete example.

### 11b. Deployment Fails with "can not exported multiple nodes into the same output"

**Symptom**: `CreatePipelineRun` deployment fails at the PROD stage with error: `"the output name of current workspace:XXX node:YYY and that of workspace:XXX node:YYY are the same one:XXX.YYY, can not exported multiple nodes into the same output"`

**Cause**: Two nodes in the same project have the same `outputs.nodeOutputs[].data` value. Output names must be **globally unique within the project**, even across different workflows. This commonly happens when recreating nodes that already exist in a different workflow.

**Prevention**: Before creating any node, check for existing nodes with the same name and verify their output names:
```bash
aliyun dataworks-public ListNodes --ProjectId $PID --Name "node_name" \
  --user-agent AlibabaCloud-Agent-Skills
```
If a node with the same output name already exists, either:
1. Use a different node name (e.g., add a suffix)
2. Update the existing node instead of creating a new one

**Recovery**: If the node was already created with a conflicting output, inform the user of the conflict and let them decide how to resolve it (rename or update existing).

### 11c. CreateNode Silently Drops spec.dependencies

**Symptom**: `CreateNode` returns success, but `ListNodeDependencies` for the created node shows `TotalCount: 0` — no dependencies were persisted, despite `spec.dependencies` being correctly formatted in the request.

**Cause**: The `CreateNode` API may silently discard `spec.dependencies` in certain conditions. This is a known API behavior, not a spec formatting issue.

**Fix**: After creating all nodes, verify each downstream node's dependencies with `ListNodeDependencies`. If `TotalCount` is `0`, re-apply dependencies via `UpdateNode` using `spec.dependencies`:
```bash
aliyun dataworks-public UpdateNode --ProjectId $PID --Id $NODE_ID \
  --Spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"'$NODE_ID'"}],"dependencies":[{"nodeId":"node_name","depends":[{"type":"Normal","output":"project.upstream_node"}]}]}}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**NEVER use `inputs.nodeOutputs` to fix dependencies** — always use `spec.dependencies` in the UpdateNode call.

**Prevention**: Always run the "Verify and Fix Dependencies" step (see workflow-guide.md Step 5) before deploying.

### 12. datasource.type Auto-Corrected by Server

**Symptom**: Submitted `datasource.type` as `flink`, but the server returned `flink_serverless`.

**Explanation**: The server automatically corrects `datasource.type` based on the actual datasource type. Known corrections:
- `flink` -> `flink_serverless` (Serverless Flink datasource)
- Other types may have similar corrections

**Handling**: Use the generic type when submitting (e.g., `flink`); no need to worry about the server-corrected actual value.

### 13. Flink Node Spec Missing dependencies Field

**Symptom**: When retrieving a Flink node's spec via GetNode, the returned JSON does not contain a `dependencies` field.

**Explanation**: Scheduling dependencies for Flink streaming nodes are configured via `spec.dependencies`. The spec returned by GetNode may not include the `dependencies` field; use the `ListNodeDependencies` API to query instead.

### 14. Duplicate Resource Created by Network Retry

**Symptom**: A Create API call (e.g., `CreateNode`, `CreateWorkflowDefinition`) timed out or returned a network error, so the agent retried the same call. The retry succeeded, but now two identical resources exist (e.g., two nodes with the same name, or creation fails with "Node with the same name already exists").

**Cause**: The original request was actually processed by the server, but the response was lost due to a network issue. The DataWorks 2024-05-18 Create APIs do not support `ClientToken` for idempotent retries, so a blind retry creates a duplicate.

**Correct recovery**:
1. **Before retrying any Create call that failed with a network/timeout error**, use the corresponding List API to check whether the resource was already created:
   ```bash
   # Example: check if node was created despite the error
   aliyun dataworks-public ListNodes --ProjectId $PID --Name "my_node" \
     --user-agent AlibabaCloud-Agent-Skills
   ```
2. If the resource exists → do NOT retry; use the existing resource's ID and continue
3. If the resource does not exist → safe to retry the Create call
4. Always record the `RequestId` from every API response for traceability

**Prevention**: Always perform the pre-creation conflict check (see "Environment Discovery" in SKILL.md) before calling any Create API. This catches both pre-existing resources and resources created by prior failed attempts.

### 15. API Throttling (Throttling.User)

**Error message**:
```
Code: 9990020002
Message: Throttling.User
```

**Explanation**: API call frequency exceeded the rate limit within a short period. Batch operations (such as looping GetNode to retrieve node details) are prone to triggering this.

**Solution**: Add intervals between batch operations (e.g., 500ms between each call), or reduce unnecessary GetNode calls.
