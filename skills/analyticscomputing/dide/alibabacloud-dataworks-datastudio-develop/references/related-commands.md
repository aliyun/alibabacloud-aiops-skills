# DataWorks Related CLI Commands

This document lists all CLI commands involved in the DataWorks data development SKILL.

## Node Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public CreateNode` | Create node |
| dataworks-public | `aliyun dataworks-public UpdateNode` | Update node |
| dataworks-public | `aliyun dataworks-public GetNode` | Get node details |
| dataworks-public | `aliyun dataworks-public ListNodes` | List nodes |

## Workflow Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public CreateWorkflowDefinition` | Create workflow |
| dataworks-public | `aliyun dataworks-public UpdateWorkflowDefinition` | Update workflow |
| dataworks-public | `aliyun dataworks-public GetWorkflowDefinition` | Get workflow details |
| dataworks-public | `aliyun dataworks-public ListWorkflowDefinitions` | List workflows |

## Deployment Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public CreatePipelineRun` | Create deployment process |
| dataworks-public | `aliyun dataworks-public GetPipelineRun` | Get deployment status |
| dataworks-public | `aliyun dataworks-public ExecPipelineRunStage` | Advance deployment stage |
| dataworks-public | `aliyun dataworks-public ListPipelineRuns` | Query deployment history |
| dataworks-public | `aliyun dataworks-public ListPipelineRunItems` | Query deployment items |
| dataworks-public | `aliyun dataworks-public AbolishPipelineRun` | Cancel deployment |

## Project and Resource Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public GetProject` | Get project information |
| dataworks-public | `aliyun dataworks-public ListDataSources` | List data sources |
| dataworks-public | `aliyun dataworks-public ListResourceGroups` | List resource groups |

## Resource and Function Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public CreateResource` | Create resource |
| dataworks-public | `aliyun dataworks-public ListResources` | List resources |
| dataworks-public | `aliyun dataworks-public CreateFunction` | Create function |
| dataworks-public | `aliyun dataworks-public ListFunctions` | List functions |

## Command Usage Examples

### Create Node

```bash
aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Node Within a Workflow

```bash
aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --ContainerId {{workflow_id}} \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Workflow

```bash
aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Deploy (Online)

```bash
aliyun dataworks-public CreatePipelineRun \
  --ProjectId {{project_id}} \
  --Type Online \
  --ObjectIds '["{{object_id}}"]' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Deployment Status

```bash
aliyun dataworks-public GetPipelineRun \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

### Advance Deployment Stage

```bash
aliyun dataworks-public ExecPipelineRunStage \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --Code {{stage_code}} \
  --user-agent AlibabaCloud-Agent-Skills
```

## Command Help

View command details:

```bash
aliyun dataworks-public CreateNode --help
aliyun dataworks-public ListNodes --help
aliyun dataworks-public CreateWorkflowDefinition --help
```

## Important Notes

1. **All commands must include `--user-agent AlibabaCloud-Agent-Skills`**
2. API version is `2024-05-18`, using the `dataworks-public` product
3. Parameter names are case-sensitive (e.g., `--ProjectId` not `--projectId`)
