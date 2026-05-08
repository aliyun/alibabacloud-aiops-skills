# Workflow Development Guide

This document describes how to create and manage workflows in DataWorks, including the complete development process for both cycle workflows and manual workflows.

## Workflow Types

DataWorks supports two workflow types:

### CycleWorkflow

Runs automatically according to a preset scheduling cycle, suitable for daily ETL, scheduled reports, and similar scenarios.

- Must configure a `trigger` (scheduling trigger)
- Nodes within the workflow execute in dependency order
- FlowSpec `kind` is `"CycleWorkflow"`

### ManualWorkflow

Runs only when manually triggered, suitable for data repair, one-time tasks, and similar scenarios.

- No `trigger` configuration required
- Must be triggered manually or via API
- FlowSpec `kind` is `"ManualWorkflow"`

---

## Complete Workflow Creation Process

### Step 1: Create the Workflow Definition

First, create the FlowSpec definition file for the workflow.

**Cycle Workflow**:

```bash
mkdir -p ./my_wf
# Build the workflow spec JSON (refer to the workflow creation example in SKILL.md)
```

Edit `my_wf.spec.json`, filling in the workflow name and scheduling trigger:

```json
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "workflows": [
      {
        "name": "my_wf",
        "script": {
          "path": "my_wf",
          "runtime": {
            "command": "WORKFLOW"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 00 * * ?",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        }
      }
    ]
  }
}
```

> **`script.runtime.command: "WORKFLOW"` must be set**, otherwise `create-workflow-definition` will return an error `"script.runtime.command is empty"`.

**Manual Workflow**:

```bash
mkdir -p ./my_manual_wf
# Build the manual workflow spec JSON (kind=ManualWorkflow)
```

Edit `my_manual_wf.spec.json`:

```json
{
  "version": "2.0.0",
  "kind": "ManualWorkflow",
  "spec": {
    "workflows": [
      {
        "name": "my_manual_wf",
        "script": {
          "path": "my_manual_wf",
          "runtime": {
            "command": "WORKFLOW"
          }
        }
      }
    ]
  }
}
```

Build the spec JSON and call the API to create the workflow:

```bash
aliyun dataworks-public create-workflow-definition \
  --project-id {{project_id}} \
  --spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

**Important**: Record the returned `WorkflowId`, as it is needed when creating nodes within the workflow.

### Step 2: Create Nodes Within the Workflow

Each node in the workflow must be created individually. Use the `ContainerId` parameter to associate the node with the workflow.

```bash
# Create node directory
mkdir -p ./my_wf/step1

# Copy node template
# Refer to templates in assets/templates/ and modify accordingly
# [Required] Add outputs.nodeOutputs for each node (not included in minSpec):
#   "outputs":{"nodeOutputs":[{"data":"${projectIdentifier}.node_name","artifactType":"NodeOutput"}]}

# Edit spec.json, write code file, configure properties
# ...(follow the standard node creation process)

# Build spec JSON and submit, note the --container-id parameter
aliyun dataworks-public create-node \
  --project-id {{project_id}} \
  --scene DATAWORKS_PROJECT \
  --container-id {{workflow_id}} \
  --spec "$(cat /tmp/step1.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

Repeat this step for each node in the workflow.

### Complete Example: 3-Node Workflow (extract -> transform -> load)

Below is a complete copy-ready example showing the spec structure of nodes within a workflow. For the full version, see `assets/templates/05-cycle-workflow/`.

**Root node (no upstream dependency) -- extract.spec.json**:
```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "extract",
        "id": "extract",
        "script": {
          "path": "extract",
          "runtime": { "command": "DIDE_SHELL" }
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.extract", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "extract",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

**Middle node (depends on extract) -- transform.spec.json**:
```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "transform",
        "id": "transform",
        "script": {
          "path": "transform",
          "runtime": { "command": "ODPS_SQL" }
        },
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "odps"
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.transform", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "transform",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.extract" }
        ]
      }
    ]
  }
}
```

**Terminal node (depends on transform) -- load.spec.json**:
```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "load",
        "id": "load",
        "script": {
          "path": "load",
          "runtime": { "command": "HOLOGRES_SQL" }
        },
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "hologres"
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.load", "artifactType": "NodeOutput" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "load",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.transform" }
        ]
      }
    ]
  }
}
```

**Key points**:
- Each node **must** declare `outputs.nodeOutputs` (format `${projectIdentifier}.node_name`), otherwise downstream dependencies will silently fail
- The output name (`${projectIdentifier}.node_name`) must be **globally unique within the project**. If another node (even in a different workflow) already uses the same output name, deployment will fail with `"can not exported multiple nodes into the same output"`. Always check with `list-nodes --Name node_name` before creating
- Dependencies are configured via `spec.dependencies` only:
  - `nodeId` = the **current node's own name** (self-reference, NOT the upstream node)
  - `depends[].output` = the **upstream node's output** (`${projectIdentifier}.upstream_node_name`)
  - The upstream's `outputs.nodeOutputs[].data` and downstream's `depends[].output` must be **character-for-character identical**
- Root nodes (no upstream) depend on `${projectIdentifier}_root` (underscore, not dot)
- When `datasource` and `runtimeResource` are uncertain, they can be omitted; the server will automatically use the project defaults
- For additional optional fields (trigger, rerunTimes, parameters, etc.), see `assets/templates/05-cycle-workflow/`

### Step 3: Configure Dependencies

Dependencies between nodes within a workflow are configured via the `spec.dependencies` array only:

> **Dependency configuration rules**:
> 1. **Upstream nodes** declare `outputs.nodeOutputs`: `{"data":"${projectIdentifier}.node_name","artifactType":"NodeOutput"}`
> 2. **Downstream nodes** declare dependencies in `spec.dependencies`, referencing the upstream `outputs.nodeOutputs[].data`
>
> **⚠️ `nodeId` is a SELF-REFERENCE** — it must be the **current node's own `name`** (the node that HAS the dependency), NOT the upstream node's name or API-returned ID. For example, if you are creating node `"step2"` and it depends on `"step1"`, then `nodeId` must be `"step2"` (self), and `depends[].output` must be `"${projectIdentifier}.step1"` (upstream's output).
>
> **`outputs.nodeOutputs[].data` and `dependencies[].depends[].output` must be character-for-character identical** (e.g., `${projectIdentifier}.upstream_node`); any mismatch will cause the dependency to silently fail.
>
> **Output names must be globally unique within the project.** Before creating any node, use `list-nodes --Name node_name` to verify the output name `${projectIdentifier}.node_name` is not already used by another node. Duplicate output names cause deployment failure: `"can not exported multiple nodes into the same output"`.
>
> Note: The minSpec template does not include the outputs field; it must be added manually when creating workflow nodes.

**Single dependency chain** (step1 -> step2 -> step3):

In step2's `spec.json`:
```json
"dependencies": [
  {
    "nodeId": "step2",
    "depends": [
      {
        "type": "Normal",
        "output": "${projectIdentifier}.step1"
      }
    ]
  }
]
```

In step3's `spec.json`:
```json
"dependencies": [
  {
    "nodeId": "step3",
    "depends": [
      {
        "type": "Normal",
        "output": "${projectIdentifier}.step2"
      }
    ]
  }
]
```

**Multiple dependency merge** (step1 + step2 -> step3):

```json
"dependencies": [
  {
    "nodeId": "step3",
    "depends": [
      {
        "type": "Normal",
        "output": "${projectIdentifier}.step1"
      },
      {
        "type": "Normal",
        "output": "${projectIdentifier}.step2"
      }
    ]
  }
]
```

### Step 4: Publish and Deploy

After all nodes are created, publish the workflow:

```bash
aliyun dataworks-public create-pipeline-run \
  --project-id {{project_id}} \
  --type Online \
  --object-ids {{workflow_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

Query the publish status:

```bash
aliyun dataworks-public get-pipeline-run \
  --project-id {{project_id}} \
  --id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Step 5: Verify and Fix Dependencies (MANDATORY)

**The `create-node` API may silently drop `spec.dependencies`.** After creating all nodes but before deploying, you MUST verify dependencies by calling `list-node-dependencies` for each downstream node:

```bash
aliyun dataworks-public list-node-dependencies \
  --project-id {{project_id}} \
  --id {{downstream_node_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

Check the response: if `TotalCount` is `0` but the node should have upstream dependencies, **fix immediately** with `update-node`:

```bash
aliyun dataworks-public update-node --project-id {{project_id}} --id {{node_id}} \
  --spec '{"version":"2.0.0","kind":"Node","spec":{"nodes":[{"id":"{{node_id}}"}],"dependencies":[{"nodeId":"{{node_name}}","depends":[{"type":"Normal","output":"{{projectIdentifier}}.{{upstream_node_name}}"}]}]}}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

> Always use `spec.dependencies` in update-node.

**Do NOT proceed to deploy until all dependencies are confirmed.** Common causes of missing dependencies:
1. `create-node` API silently dropped `spec.dependencies` (known behavior — fix with update-node)
2. `nodeId` was set to the upstream node's name instead of the current node's own name (self-reference)
3. `depends[].output` string does not exactly match the upstream's `outputs.nodeOutputs[].data`
4. Upstream node did not declare `outputs.nodeOutputs`

---

## Dependency Configuration Details

### Intra-Workflow Dependencies

Dependencies between nodes within a workflow are configured via the `spec.dependencies` array only.

**How `spec.dependencies` wiring works** (A → B, where B depends on A):

```
Node A (upstream):                         Node B (downstream):
  name: "node_a"                             name: "node_b"
  outputs.nodeOutputs[0].data:               dependencies[0].nodeId: "node_b"      ← SELF (current node's own name)
    "${projectIdentifier}.node_a"  ←──MUST MATCH──→  dependencies[0].depends[0].output:
                                                       "${projectIdentifier}.node_a"  ← UPSTREAM's output
```

**Upstream node** (must declare outputs):
```json
"outputs": {
  "nodeOutputs": [
    {"data": "${projectIdentifier}.upstream_node", "artifactType": "NodeOutput"}
  ]
}
```

**Downstream node** (references upstream output in `spec.dependencies`):
```json
"dependencies": [
  {
    "nodeId": "current_node",
    "depends": [
      {
        "type": "Normal",
        "output": "${projectIdentifier}.upstream_node"
      }
    ]
  }
]
```

> **Common mistake**: Setting `nodeId` to the upstream node's name or API-returned ID. `nodeId` is always the **current node's own name** — it tells the system which node in the spec this dependency entry applies to.

### Cross-Workflow Dependencies

When a node in the current workflow depends on a node in another workflow, the usage is the same as long as both workflows are in the same project:

```json
{
  "nodeId": "current_node",
  "depends": [
    {
      "type": "Normal",
      "output": "${projectIdentifier}.other_workflow_node"
    }
  ]
}
```

### Cross-Project Dependencies

When depending on a node from another project, use the upstream project's `projectIdentifier` directly (without the placeholder):

```json
{
  "nodeId": "current_node",
  "depends": [
    {
      "type": "Normal",
      "output": "upstream_project_name.upstream_node_name"
    }
  ]
}
```

Note that the output format for cross-project dependencies is `upstream_projectIdentifier.upstream_node_name`.

### No Upstream Dependency (Attach to Project Root Node)

If a node has no upstream dependency, it must be attached to the project root node:

```json
{
  "nodeId": "first_node",
  "depends": [
    {
      "type": "Normal",
      "output": "${projectIdentifier}_root"
    }
  ]
}
```

Note: The root node output format is `projectIdentifier_root` (underscore), not `projectIdentifier.root` (dot).

### Cross-Cycle Dependencies

A node depends on the previous scheduling cycle's result of itself or another node:

**Self-dependency**:
```json
{
  "nodeId": "daily_incremental",
  "depends": [
    {
      "type": "CrossCycleDependsOnSelf",
      "output": "${projectIdentifier}.daily_incremental"
    }
  ]
}
```

**Depends on another node's previous cycle**:
```json
{
  "nodeId": "current_node",
  "depends": [
    {
      "type": "CrossCycleDependsOnOther",
      "output": "${projectIdentifier}.other_node"
    }
  ]
}
```

---

## Workflow Directory Structure

子节点文件夹直接放在工作流根目录下，**禁止嵌套子目录**（即节点文件夹内不能再有节点文件夹）：

```
my_wf/
├── my_wf.spec.json            # Workflow definition (CycleWorkflow or ManualWorkflow)
├── dataworks.properties       # Workflow-level configuration
├── step1/                     # Child node 1 (直接在工作流根目录下)
│   ├── step1.spec.json        # Node FlowSpec
│   ├── step1.sh               # Code file
│   └── dataworks.properties   # Node-level configuration
├── step2/                     # Child node 2 (直接在工作流根目录下)
│   ├── step2.spec.json
│   ├── step2.sql
│   └── dataworks.properties
└── step3/                     # Child node 3 (直接在工作流根目录下)
    ├── step3.spec.json
    ├── step3.py
    └── dataworks.properties
```

Each child node directory follows the standard node file structure (spec.json + code file + dataworks.properties). 节点文件夹内只包含这三个文件，不要再创建子目录。

---

## Workflow Development in Git Mode

In a DataWorks Git project directory, workflow development does not require API calls. Follow these steps:

1. Create the workflow spec.json and node files
2. Configure dependencies
3. `git add` and `git commit` to submit

```bash
# Commit
git add ./my_wf
git commit -m "Add workflow: my_wf with step1, step2, step3"
```

---

## Important Notes

1. **Creation order**: The workflow definition must be created first to obtain the returned WorkflowId before creating nodes within the workflow
2. **`script.runtime.command` is required**: The workflow spec must include `script.runtime.command: "WORKFLOW"`, otherwise `create-workflow-definition` will return an error `"script.runtime.command is empty"`
3. **ContainerId parameter**: Nodes within a workflow are associated to the workflow via the `ContainerId` parameter of the `create-node` API (value is the WorkflowId), rather than embedding node definitions inside the workflow spec
4. **Intra-workflow node dependencies are configured via `spec.dependencies`** only. `spec.dependencies[*].nodeId` is a **self-reference** — it must be the **current node's own `name`**, NOT the upstream node's name or API-returned ID. `depends[].output` is the **upstream node's output identifier** (see the complete example and template `assets/templates/05-cycle-workflow/`)
5. **Node outputs must be declared**: Each node within a workflow **must** declare `${projectIdentifier}.node_name` in `outputs.nodeOutputs` (minSpec does not include this field; it must be added manually). **Output names must be globally unique within the project** — if another node already uses the same output name, deployment will fail
6. **Root node dependency**: Nodes with no upstream dependency must be attached to `${projectIdentifier}_root`
7. **Workflow trigger**: The trigger of a cycle workflow defines the workflow-level scheduling cycle; nodes within the workflow inherit this schedule
8. **Immutable properties**: The workflow type (CycleWorkflow / ManualWorkflow) cannot be changed after creation
9. **Updates must be incremental**: When calling `update-node`, only pass the id + fields to be modified; do not pass unchanged fields like `datasource` or `runtimeResource`. The server may have corrected these field values (e.g., `flink` to `flink_serverless`), and passing back the original values will cause errors
10. **get-node returns the full workflow spec**: When calling `get-node` on a node within a workflow, the response returns a complete `kind: CycleWorkflow` workflow spec; the target node is located at `spec.workflows[0].nodes[]` (not `spec.nodes[]`)
11. **Workflow `strategy` field**: Workflows support a `strategy` configuration (including priority, timeout, rerunMode, failureStrategy, etc.); this field is defined at the workflow level, not the node level
12. **`datasource.type` auto-correction**: The server may automatically correct the value of `datasource.type` (e.g., `flink` is corrected to `flink_serverless`); refer to the actual returned value
