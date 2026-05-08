# Acceptance Criteria: DataWorks Data Development

**Scenario**: DataWorks node and workflow development
**Purpose**: Skill test acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product -- Verify Product Name Exists

```bash
# CORRECT: dataworks-public is the correct product name
aliyun dataworks-public get-node --help

# INCORRECT: dataworks without the -public suffix
aliyun dataworks get-node --help
```

### 2. Command -- Verify Action Exists Under the Product

```bash
# CORRECT: Correct action names
aliyun dataworks-public create-node --help
aliyun dataworks-public list-nodes --help
aliyun dataworks-public get-node --help
aliyun dataworks-public update-node --help

aliyun dataworks-public create-workflow-definition --help
aliyun dataworks-public list-workflow-definitions --help
aliyun dataworks-public get-workflow-definition --help

aliyun dataworks-public create-pipeline-run --help
aliyun dataworks-public get-pipeline-run --help
aliyun dataworks-public exec-pipeline-run-stage --help

# INCORRECT: Wrong action names
aliyun dataworks-public create-task --help  # Should be create-node
aliyun dataworks-public list-task --help    # Should be list-nodes
```

### 3. Parameters -- Verify Each Parameter Name Exists

```bash
# CORRECT: Correct parameter names
aliyun dataworks-public create-node \
  --project-id 123456 \
  --scene DATAWORKS_PROJECT \
  --spec '{"version":"2.0.0",...}'

aliyun dataworks-public create-node \
  --project-id 123456 \
  --scene DATAWORKS_PROJECT \
  --container-id 789012 \
  --spec '{"version":"2.0.0",...}'

# INCORRECT: Wrong parameter names
aliyun dataworks-public create-node \
  --projectid 123456        # Should be --project-id (kebab-case)
  --Scene DATAWORKS_PROJECT  # Should be --scene (lowercase)
```

### 4. user-agent Identifier -- Must Be Included in Every Command

```bash
# CORRECT: Includes user-agent
aliyun dataworks-public get-node \
  --project-id 123456 \
  --id 789012 \
  --user-agent AlibabaCloud-Agent-Skills

# INCORRECT: Missing user-agent
aliyun dataworks-public get-node \
  --project-id 123456 \
  --id 789012
```

---

## Correct FlowSpec Patterns

### 1. Node spec.json Basic Structure

```json
// CORRECT: Correct node spec structure
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [{
      "name": "my_node",
      "script": {
        "path": "my_node",
        "language": "odps-sql",
        "runtime": {
          "command": "ODPS_SQL"
        }
      },
      "trigger": {
        "type": "Scheduler",
        "cron": "00 00 00 * * ?",
        "startTime": "1970-01-01 00:00:00",
        "endTime": "9999-01-01 00:00:00",
        "timezone": "Asia/Shanghai"
      }
    }],
    "dependencies": [{
      "nodeId": "my_node",
      "depends": [{
        "type": "Normal",
        "output": "${projectIdentifier}_root"
      }]
    }]
  }
}

// INCORRECT: Missing required fields
{
  "kind": "Node",  // Missing version
  "spec": {
    "nodes": [{
      "name": "my_node"
      // Missing script
    }]
  }
}
```

### 2. script.path Must Match name

```json
// CORRECT: path matches name
{
  "name": "etl_daily",
  "script": {
    "path": "etl_daily",  // Matches name
    "runtime": { "command": "ODPS_SQL" }
  }
}

// INCORRECT: path does not match name
{
  "name": "etl_daily",
  "script": {
    "path": "other_path",  // API will return "script path not match name"
    "runtime": { "command": "ODPS_SQL" }
  }
}
```

### 3. Dependency Configuration (spec.dependencies)

```json
// CORRECT: Configure dependencies in spec.dependencies, ensure nodeId exactly matches the node id
{
  "spec": {
    "nodes": [{
      "name": "downstream"
    }],
    "dependencies": [{
      "nodeId": "downstream",
      "depends": [{
        "type": "Normal",
        "output": "${projectIdentifier}.upstream"
      }]
    }]
  }
}

// INCORRECT: Using the legacy `flow` field instead of `spec.dependencies`
{
  "spec": {
    "nodes": [{ "name": "downstream" }],
    "flow": [{
      "nodeId": "downstream",
      "depends": [{
        "type": "Normal",
        "output": "${projectIdentifier}.upstream"
      }]
    }]
  }
}
```

### 4. Workflow spec Must Include command: WORKFLOW

```json
// CORRECT: Workflow spec
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "workflows": [{
      "name": "my_workflow",
      "script": {
        "path": "my_workflow",
        "runtime": {
          "command": "WORKFLOW"  // Must be set
        }
      },
      "trigger": {
        "type": "Scheduler",
        "cron": "00 00 00 * * ?"
      }
    }]
  }
}

// INCORRECT: Missing command
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "workflows": [{
      "name": "my_workflow",
      "script": {
        "path": "my_workflow"
        // Missing runtime.command, API will return an error
      }
    }]
  }
}
```

### 5. Datasource Type Matching

```json
// CORRECT: ODPS_SQL uses odps datasource
{
  "script": {
    "runtime": { "command": "ODPS_SQL" },
    "language": "odps-sql"
  },
  "datasource": {
    "name": "${spec.datasource.name}",
    "type": "odps"
  }
}

// CORRECT: HOLOGRES_SQL uses hologres datasource
{
  "script": {
    "runtime": { "command": "HOLOGRES_SQL" },
    "language": "hologres-sql"
  },
  "datasource": {
    "name": "${spec.datasource.name}",
    "type": "hologres"
  }
}

// INCORRECT: Type mismatch
{
  "script": {
    "runtime": { "command": "HOLOGRES_SQL" }
  },
  "datasource": {
    "name": "my_ds",
    "type": "odps"  // Should be hologres
  }
}
```

---

## Correct dataworks.properties Patterns

```properties
# CORRECT: Correct properties format
projectIdentifier=my_project_name
spec.datasource.name=my_odps_datasource
spec.runtimeResource.resourceGroup=S_res_group_xxx
script.bizdate=20260101

# INCORRECT: Wrong key prefix
datasource.name=my_ds              # Should be spec.datasource.name
resource_group=S_res_group_xxx     # Should be spec.runtimeResource.resourceGroup

# INCORRECT: Value contains placeholder
spec.datasource.name=${datasource} # Value must not contain placeholders
```

---

## Correct Python SDK Code Patterns

### 1. Import Patterns

```python
# CORRECT
from alibabacloud_dataworks_public20240518.client import Client
from alibabacloud_dataworks_public20240518.models import CreateNodeRequest
from alibabacloud_tea_openapi.models import Config

# INCORRECT
from alibabacloud_dataworks.client import Client  # Wrong module name
from dataworks.models import CreateNodeRequest    # Wrong module name
```

### 2. Client Initialization

```python
# CORRECT: Use CredentialClient
from alibabacloud_credentials.client import Client as CredentialClient

credential = CredentialClient()
config = Config(credential=credential)
config.endpoint = 'dataworks.cn-hangzhou.aliyuncs.com'
client = Client(config)

# INCORRECT: Hardcoded AK/SK (security risk)
config = Config(
    access_key_id='LTAI5tXXX',        # Do not hardcode
    access_key_secret='8dXXXXXXX'     # Do not hardcode
)
```

### 3. API Calls

```python
# CORRECT
request = CreateNodeRequest(
    project_id=123456,
    scene='DATAWORKS_PROJECT',
    spec=spec_json
)
response = client.create_node(request)
node_id = response.body.id

# INCORRECT: Wrong parameter names
request = CreateNodeRequest(
    projectId=123456,    # Should be project_id
    Scene='xxx'          # Should be scene
)
```

---

## Validation Commands

Each CLI command should be verified with `--help`:

```bash
# Verify product and action exist
aliyun dataworks-public create-node --help
aliyun dataworks-public update-node --help
aliyun dataworks-public get-node --help
aliyun dataworks-public list-nodes --help

aliyun dataworks-public create-workflow-definition --help
aliyun dataworks-public update-workflow-definition --help
aliyun dataworks-public get-workflow-definition --help
aliyun dataworks-public list-workflow-definitions --help

aliyun dataworks-public create-pipeline-run --help
aliyun dataworks-public get-pipeline-run --help
aliyun dataworks-public exec-pipeline-run-stage --help
aliyun dataworks-public list-pipeline-runs --help
aliyun dataworks-public list-pipeline-run-items --help
aliyun dataworks-public abolish-pipeline-run --help

aliyun dataworks-public get-project --help
aliyun dataworks-public list-data-sources --help
aliyun dataworks-public list-resource-groups --help
```

---

## Critical Anti-Patterns to Avoid

1. **Dependencies must only live in `spec.dependencies`**: Do not place dependency declarations anywhere else on the node; `dependencies[*].nodeId` must exactly match the node `id`
2. **Do not hardcode AK/SK**: Use CredentialClient or environment variables
3. **Do not forget user-agent**: Every aliyun command must include `--user-agent AlibabaCloud-Agent-Skills`
4. **Do not assume update-node works for all nodes**: Hologres nodes cannot be updated
5. **Do not skip validation**: Always run validate.py after each modification
6. **Do not echo AK/SK**: Never print credential information
7. **Do not execute write operations without confirmation**: Except for Create and read-only queries (Get/List), all Delete, Update, Move, Rename, Abolish, and other APIs that modify existing objects must be confirmed with the user first
