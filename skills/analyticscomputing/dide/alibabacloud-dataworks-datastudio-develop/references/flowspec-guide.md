# FlowSpec Format Reference

FlowSpec is the standardized JSON description format for DataWorks data development nodes and workflows. This document provides detailed descriptions of each field's meaning, type, and constraints.

## Top-Level Structure

Each FlowSpec file contains the following top-level fields:

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {}
}
```

| Field | Type | Required | Description |
|------|------|------|------|
| `version` | string | Yes | FlowSpec version number, format `2.x.x`, currently recommended `"2.0.0"` |
| `kind` | string | Yes | Resource type, see SpecKind enum below |

**SpecKind enum values**:

| kind | Description |
|------|------|
| `Node` | Single node |
| `ManualNode` | Manual single node |
| `CycleWorkflow` | Cycle-scheduled workflow |
| `ManualWorkflow` | Manually triggered workflow |
| `TriggerWorkflow` | Event-triggered workflow |
| `TemporaryWorkflow` | Temporary workflow |
| `Workflow` | Generic workflow |
| `PaiFlow` | PAI workflow |
| `Component` | Component |
| `Resource` | Resource |
| `Function` | Function |
| `Table` | Table |
| `BatchDeployment` | Batch deployment |
| `DataSource` | Data source |
| `DataQuality` | Data quality |
| `DataService` | Data service |
| `DataCatalog` | Data catalog |
| `DataIntegrationJob` | Data integration job |

| Field | Type | Required | Description |
|------|------|------|------|
| `metadata` | object | No | Custom metadata, not used in business logic |
| `spec` | object | Yes | Resource definition body, structure varies by `kind` |

---

## Node Type Details

When `kind` is `"Node"`, `spec` contains the following structure:

```json
{
  "spec": {
    "nodes": [ ... ],
    "dependencies": [ ... ]
  }
}
```

### spec.nodes (Node Definition Array)

`nodes` is an array that typically contains one node object. The complete fields of a node object are as follows:

#### name (Node Name)

| Property | Value |
|------|------|
| Type | string |
| Required | Yes |
| Constraints | Minimum 1 character, recommend using English letters, numbers, and underscores |

Node name, must be unique within the same project. The name is also used for references in `outputs.nodeOutputs` and `dependencies`.

```json
"name": "etl_daily_report"
```

#### recurrence (Scheduling Type)

| Property | Value |
|------|------|
| Type | string |
| Required | No |
| Default | `"Normal"` |
| Options | `"Normal"` / `"Pause"` / `"Skip"` |

- **Normal**: Normal scheduling, runs automatically according to the trigger definition
- **Pause**: Paused scheduling, the node will not execute automatically, but downstream nodes still trigger normally
- **Skip**: Skip scheduling, the node is marked as successful but does not actually execute

```json
"recurrence": "Normal"
```

#### priority

| Property | Value |
|------|------|
| Type | integer |
| Required | No |
| Range | 1 ~ 8 |
| Default | 1 |

Higher values mean higher priority. When resources are insufficient, higher-priority nodes execute first.

```json
"priority": 3
```

#### script (Script Definition)

script is the core configuration of a node, defining the code to execute and the runtime environment.

```json
"script": {
  "language": "odps-sql",
  "runtime": {
    "command": "ODPS_SQL"
  },
  "content": "SELECT * FROM my_table;",
  "path": "business_flow/data_processing/etl_daily",
  "parameters": [...]
}
```

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `language` | string | No | Script language identifier, must match the `language` in the registry |
| `runtime.command` | string | Yes | Node type identifier (e.g., `ODPS_SQL`, `DIDE_SHELL`), determines the runtime environment |
| `runtime.engine` | string | No | Runtime engine identifier (e.g., specific engine version) |
| `runtime.flinkConf` | object | No | Flink job configuration (for Flink-type nodes) |
| `runtime.emrJobConfig` | object | No | EMR job configuration (for EMR-type nodes) |
| `runtime.sparkConf` | object | No | Spark configuration (for Spark-type nodes) |
| `content` | string | No | Script code content. Usually empty during local development (code is in a separate file); must be populated when submitting to the API |
| `path` | string | No | Script file path (inherited from SpecFile parent class), the node's script path in DataWorks |
| `extension` | string | No | Script file extension (e.g., `.sql`, `.sh`, `.py`) |
| `parameters` | array | No | Scheduling parameter list |

`language` and `runtime.command` must match. See the "Common Node Types" table in SKILL.md for common types.

##### parameters (Scheduling Parameters)

`parameters` is an array where each element defines a parameter:

```json
"parameters": [
  {
    "name": "bizdate",
    "scope": "NodeParameter",
    "type": "System",
    "value": "$yyyymmdd"
  },
  {
    "name": "hour",
    "scope": "NodeParameter",
    "type": "System",
    "value": "$[hh24]"
  },
  {
    "name": "env",
    "scope": "NodeParameter",
    "type": "Constant",
    "value": "production"
  }
]
```

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `name` | string | Yes | Parameter name |
| `scope` | string | No | Scope: `"NodeParameter"` (node level) or `"WorkflowParameter"` (workflow level) |
| `type` | string | No | Parameter type: `"System"` (system variable), `"Constant"` (constant), `"NodeOutput"` (upstream output) |
| `value` | string | Yes | Parameter value or system variable expression |

**Common system variables**:

| Variable Expression | Description | Example Value |
|-----------|------|--------|
| `$yyyymmdd` | Business date (T-1), format yyyyMMdd | `20260321` |
| `$bizdate` | Same as `$yyyymmdd` | `20260321` |
| `$yyyy` | Year of the business date | `2026` |
| `$mm` | Month of the business date | `03` |
| `$dd` | Day of the business date | `21` |
| `$[yyyymmdd]` | Run date (T+0), format yyyyMMdd | `20260322` |
| `$[yyyy-mm-dd]` | Run date, format yyyy-MM-dd | `2026-03-22` |
| `$[hh24]` | Hour of the run time (24-hour format) | `14` |
| `$[hh24miss]` | Run time, format HHmmss | `143000` |
| `$[yyyymmdd-1]` | Run date minus 1 day | `20260321` |
| `$[yyyymmdd+7]` | Run date plus 7 days | `20260329` |
| `$[yyyymm-1]` | Run date minus 1 month | `202602` |
| `$gmtdate` | Current timestamp | `20260322143000` |
| `${out_table_name}` | Custom parameter reference | User-assigned value |

**How to reference parameters in code**:

- Shell scripts: Use `$bizdate` or `${bizdate}` directly
- SQL scripts: Use `${bizdate}` format
- Python scripts: Access via `sys.argv` or `os.environ`

#### trigger (Scheduling Trigger)

Defines the node's scheduling trigger method and timing.

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `type` | string | Yes | `Scheduler` (scheduled) / `Manual` / `Streaming` / `Custom` / `None` |
| `cron` | string | Conditionally required | 6-field cron expression (`second minute hour day month weekday`), required when type is `Scheduler` |
| `startTime` | string | No | Scheduling start time, format `yyyy-MM-dd HH:mm:ss` |
| `endTime` | string | No | Scheduling end time, format `yyyy-MM-dd HH:mm:ss` |
| `timezone` | string | No | Timezone, default `"Asia/Shanghai"` |
| `delaySeconds` | integer | No | Delay execution in seconds |
| `calendarId` | string | No | Custom calendar ID |
| `identifier` | string | No | Custom trigger identifier, used when type is `Custom` |
| `cycleType` | string | No | `"Daily"` (daily scheduling) / `"NotDaily"` (hourly/minute-level) |

For detailed cron expression configuration and scheduling cycle type descriptions, see [scheduling-guide.md](scheduling-guide.md).

#### runtimeResource (Runtime Resource)

Specifies the resource group for node execution.

```json
"runtimeResource": {
  "resourceGroup": "${spec.runtimeResource.resourceGroup}"
}
```

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `resourceGroup` | string | Yes | Resource group identifier (e.g., `S_res_group_xxx`). Recommend using the `${spec.runtimeResource.resourceGroup}` placeholder, with the actual value configured in `dataworks.properties` |
| `resourceGroupId` | string | No | Resource group ID, optional |

The resource group identifier can be obtained via the `ListResourceGroups` API.

#### datasource (Data Source)

Node types that require a data source must configure this field. Whether a data source is needed is determined by the `datasourceType` in the registry.

```json
"datasource": {
  "name": "${spec.datasource.name}",
  "type": "odps"
}
```

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `name` | string | Yes | Datasource name. Recommend using the `${spec.datasource.name}` placeholder |
| `type` | string | Yes | Datasource type (e.g., `odps`, `hologres`, `flink`, `emr`, `clickhouse`). Must match the `datasourceType` for the command in the registry |

For whether each node type requires a data source and the corresponding `datasourceType`, see the "Common Node Types" table in SKILL.md.

#### outputs (Output Definition)

Defines the node's output identifier, used for downstream dependency.

```json
"outputs": {
  "nodeOutputs": [
    {
      "data": "${projectIdentifier}.etl_daily_report"
    }
  ]
}
```

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `nodeOutputs` | array | No | Node output array |
| `nodeOutputs[].data` | string | Yes | Output identifier, format `projectIdentifier.nodeName` |

The output identifier is used for `depends[].output` references in `dependencies` of other nodes. `${projectIdentifier}` is defined in `dataworks.properties`.

#### inputs (Input Definition)

Defines the node's input data. **Do not use `inputs.nodeOutputs` to configure dependencies**; dependencies are maintained via the `spec.dependencies` array. However, ensure that `spec.dependencies[*].nodeId` exactly matches the corresponding node's `id`, otherwise dependencies will not be recognized.

```json
"inputs": {
  "nodeOutputs": [
    {
      "data": "${projectIdentifier}.upstream_node"
    }
  ]
}
```

> **Note**: This field is no longer recommended for dependency configuration; use `spec.dependencies` instead. Ensure `dependencies[*].nodeId` exactly matches the node `id`.

#### rerunMode / rerunTimes / rerunInterval (Rerun Configuration)

| Field | Type | Default | Description |
|------|------|--------|------|
| `rerunMode` | string | `"Allowed"` | Rerun mode: `"Allowed"`, `"Denied"`, `"FailureAllowed"` (only allowed on failure) |
| `rerunTimes` | integer | `0` | Auto-retry count (0 means no auto-retry) |
| `rerunInterval` | integer | `180000` | Retry interval (milliseconds), default 180000 (3 minutes) |

```json
"rerunMode": "FailureAllowed",
"rerunTimes": 3,
"rerunInterval": 60000
```

#### timeout / timeoutUnit (Timeout Configuration)

| Field | Type | Default | Description |
|------|------|--------|------|
| `timeout` | number | `4` | Timeout value |
| `timeoutUnit` | string | `"HOURS"` | Timeout unit: `"SECONDS"` / `"MINUTES"` / `"HOURS"` |

```json
"timeout": 4,
"timeoutUnit": "HOURS"
```

The node will be automatically terminated after timeout. Adjust based on actual task duration.

#### instanceMode (Instance Generation Mode)

| Property | Value |
|------|------|
| Type | string |
| Options | `"T+1"` / `"Immediately"` |
| Default | `"T+1"` |

- **T+1**: Instances are generated the next day. A scheduling node configured today will start generating instances tomorrow
- **Immediately**: Instances are generated immediately. Instances can be generated and run on the same day as configuration

```json
"instanceMode": "T+1"
```

#### Other Node Fields

The following are other available fields in the Node model:

| Field | Type | Description |
|------|------|------|
| `autoParse` | boolean | Whether to automatically parse dependencies (extract input/output tables from SQL scripts, etc.) |
| `ignoreBranchConditionSkip` | boolean | Whether to ignore branch condition skip |
| `description` | string | Node description |
| `strategy` | object | Node runtime strategy configuration |
| `fileResources` | array | List of file resources associated with the node |
| `functions` | array | List of functions associated with the node |
| `datasets` | array | List of datasets associated with the node |
| `reference` | object | Node reference configuration |
| `combined` | object | Combined node configuration |
| `paramHub` | object | Parameter hub configuration, used for parameter passing |
| `subflow` | object | Sub-workflow configuration, used for embedded workflows |
| `paiflow` | object | PAI workflow configuration |
| `dqcRule` | object | Data quality rule configuration |

---

#### Control Nodes

The following control nodes have separate detailed documentation; see `references/nodetypes/controller/`:

| Node Type | Command | Description | Documentation |
|----------|------|------|------|
| Branch node | `CONTROLLER_BRANCH` | Routes to different downstream branches based on conditions | [CONTROLLER_BRANCH.md](../nodetypes/controller/CONTROLLER_BRANCH.md) |
| Join node | `CONTROLLER_JOIN` | Merges multiple branches | [CONTROLLER_JOIN.md](../nodetypes/controller/CONTROLLER_JOIN.md) |
| Assignment node | `CONTROLLER_ASSIGNMENT` | Passes script results to downstream | [CONTROLLER_ASSIGNMENT.md](../nodetypes/controller/CONTROLLER_ASSIGNMENT.md) |
| Traverse node | `CONTROLLER_TRAVERSE` | for-each loop | [CONTROLLER_TRAVERSE.md](../nodetypes/controller/CONTROLLER_TRAVERSE.md) |
| Cycle node | `CONTROLLER_CYCLE` | do-while loop | [CONTROLLER_CYCLE.md](../nodetypes/controller/CONTROLLER_CYCLE.md) |

---

### spec.dependencies (Dependencies)

`dependencies` defines the dependency relationships between nodes.

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `nodeId` | string | Yes | Current node's name |
| `depends` | array | No | Dependency list |
| `depends[].type` | string | Yes | `Normal` / `CrossCycleDependsOnSelf` / `CrossCycleDependsOnChildren` / `CrossCycleDependsOnOtherNode` |
| `depends[].output` | string | Yes | Upstream output identifier (format: `projectIdentifier.nodeName`, root node is `projectIdentifier_root`) |
| `depends[].sourceType` | string | No | `"System"` (auto-parsed) / `"Manual"` (manually configured) |
| `variableDepends` | array | No | Variable-level dependencies |

For complete dependency configuration details (usage of `spec.dependencies`, cross-workflow/cross-project/cross-cycle dependencies), see [workflow-guide.md](workflow-guide.md).

---

## Workflow Type

When `kind` is `CycleWorkflow` (cycle-scheduled) or `ManualWorkflow` (manually triggered), the `spec.workflows` array defines the workflow:

| Sub-field | Type | Required | Description |
|--------|------|------|------|
| `name` | string | Yes | Workflow name |
| `script.path` | string | No | Workflow path |
| `script.runtime.command` | string | Yes | Fixed as `"WORKFLOW"` |
| `trigger` | object | No | Scheduling trigger (required for `CycleWorkflow`, not for `ManualWorkflow`) |
| `strategy` | object | No | Workflow-level strategy (priority, timeout, rerunMode, failureStrategy, etc.) |

For the complete workflow development process (creation, node orchestration, dependency configuration, deployment), see [workflow-guide.md](workflow-guide.md).

---

## Placeholder Mechanism

FlowSpec supports two types of placeholders that must be replaced with actual values before API submission (values come from `dataworks.properties`):

### spec Placeholders

Format: `${spec.xxx}`

Used for values in spec.json that need to be replaced per environment:

```json
"datasource": {
  "name": "${spec.datasource.name}",
  "type": "odps"
}
```

Corresponding `dataworks.properties`:
```properties
spec.datasource.name=my_odps_datasource
```

### script Placeholders

Format: `${script.xxx}`

Used for values in code files that need to be replaced per environment:

```sql
-- In the code file
SELECT * FROM ${script.database}.my_table WHERE dt='${script.bizdate}';
```

Corresponding `dataworks.properties`:
```properties
script.database=my_db
script.bizdate=20260101
```

### projectIdentifier Placeholder

Format: `${projectIdentifier}`

A special placeholder used in `outputs` and `dependencies` to reference the project identifier:

```json
"outputs": {
  "nodeOutputs": [{ "data": "${projectIdentifier}.my_node" }]
}
```

Corresponding `dataworks.properties`:
```properties
projectIdentifier=my_project_name
```

---

## Complete Examples

For complete FlowSpec examples of nodes and workflows, see `assets/templates/`.
