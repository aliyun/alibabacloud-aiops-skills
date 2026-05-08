# DataWorks Related CLI Commands

This document lists all CLI commands involved in the DataWorks data development SKILL.

## Node Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public create-node` | Create node |
| dataworks-public | `aliyun dataworks-public update-node` | Update node |
| dataworks-public | `aliyun dataworks-public get-node` | Get node details |
| dataworks-public | `aliyun dataworks-public list-nodes` | List nodes |

## Workflow Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public create-workflow-definition` | Create workflow |
| dataworks-public | `aliyun dataworks-public update-workflow-definition` | Update workflow |
| dataworks-public | `aliyun dataworks-public get-workflow-definition` | Get workflow details |
| dataworks-public | `aliyun dataworks-public list-workflow-definitions` | List workflows |

## Deployment Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public create-pipeline-run` | Create deployment process |
| dataworks-public | `aliyun dataworks-public get-pipeline-run` | Get deployment status |
| dataworks-public | `aliyun dataworks-public exec-pipeline-run-stage` | Advance deployment stage |
| dataworks-public | `aliyun dataworks-public list-pipeline-runs` | Query deployment history |
| dataworks-public | `aliyun dataworks-public list-pipeline-run-items` | Query deployment items |
| dataworks-public | `aliyun dataworks-public abolish-pipeline-run` | Cancel deployment |

## Project and Resource Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public get-project` | Get project information |
| dataworks-public | `aliyun dataworks-public list-data-sources` | List data sources |
| dataworks-public | `aliyun dataworks-public list-resource-groups` | List resource groups |

## Resource and Function Operations

| Product | CLI Command | Description |
|---------|-------------|-------------|
| dataworks-public | `aliyun dataworks-public create-resource` | Create resource |
| dataworks-public | `aliyun dataworks-public list-resources` | List resources |
| dataworks-public | `aliyun dataworks-public create-function` | Create function |
| dataworks-public | `aliyun dataworks-public list-functions` | List functions |

## Command Usage Examples

### Create Node

```bash
aliyun dataworks-public create-node \
  --project-id {{project_id}} \
  --scene DATAWORKS_PROJECT \
  --spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Create Node Within a Workflow

```bash
aliyun dataworks-public create-node \
  --project-id {{project_id}} \
  --scene DATAWORKS_PROJECT \
  --container-id {{workflow_id}} \
  --spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Create Workflow

```bash
aliyun dataworks-public create-workflow-definition \
  --project-id {{project_id}} \
  --spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Deploy (Online)

```bash
aliyun dataworks-public create-pipeline-run \
  --project-id {{project_id}} \
  --type Online \
  --object-ids {{object_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Query Deployment Status

```bash
aliyun dataworks-public get-pipeline-run \
  --project-id {{project_id}} \
  --id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

### Advance Deployment Stage

```bash
aliyun dataworks-public exec-pipeline-run-stage \
  --project-id {{project_id}} \
  --id {{pipeline_run_id}} \
  --code {{stage_code}} \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

## Command Help

View command details:

```bash
aliyun dataworks-public create-node --help
aliyun dataworks-public list-nodes --help
aliyun dataworks-public create-workflow-definition --help
```

## Important Notes

1. **All commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop`**
2. API version is `2024-05-18`, using the `dataworks-public` product
3. Parameter names are case-sensitive (e.g., `--project-id` not `--projectid`)
