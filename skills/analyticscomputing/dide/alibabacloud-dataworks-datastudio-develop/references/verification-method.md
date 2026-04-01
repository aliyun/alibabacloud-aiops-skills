# DataWorks Data Development Verification Methods

This document describes how to verify whether DataWorks data development operations were successful.

## Node Verification

### Verify Node Creation Success

```bash
# Query by node ID
aliyun dataworks-public GetNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- Returns HTTP 200
- `body.name` matches the name specified during creation
- `body.script.runtime.command` matches the specified node type

### Verify Node List

```bash
aliyun dataworks-public ListNodes \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- The returned node list includes the newly created node
- `pagingInfo.nodes[].name` matches the target node

### Verify Node Dependency Configuration

```bash
# Get node details, check dependency configuration
aliyun dataworks-public GetNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators** (parsed from the returned spec JSON):
- `spec.dependencies[0].depends` contains upstream dependency relationships
- The upstream node's `outputs.nodeOutputs` contains the corresponding output declaration

## Workflow Verification

### Verify Workflow Creation Success

```bash
aliyun dataworks-public GetWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- Returns HTTP 200
- `body.name` matches the name specified during creation
- `body.type` is `CycleWorkflow` or `ManualWorkflow`

### Verify Workflow List

```bash
aliyun dataworks-public ListWorkflowDefinitions \
  --ProjectId {{project_id}} \
  --Type CycleWorkflow \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- The returned list includes the newly created workflow

### Verify Nodes Within a Workflow

```bash
# Query the node list within a workflow
aliyun dataworks-public ListNodes \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --ContainerId {{workflow_id}} \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- The returned node list includes all nodes created within the workflow
- The node count matches expectations

## Deployment Verification

### Verify Deployment Process Creation Success

```bash
aliyun dataworks-public GetPipelineRun \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- `body.pipeline.Status` is not empty
- `body.pipeline.Stages` contains the deployment stage list

### Verify Final Deployment Status

```bash
# Poll until deployment completes
aliyun dataworks-public GetPipelineRun \
  --ProjectId {{project_id}} \
  --Id {{pipeline_run_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- `body.pipeline.Status` is `Success`

**Failure indicators**:
- `body.pipeline.Status` is `Fail`, `Termination`, or `Cancel`
- Check `body.pipeline.Message` for error details

### Verify Deployment Items

```bash
aliyun dataworks-public ListPipelineRunItems \
  --ProjectId {{project_id}} \
  --PipelineRunId {{pipeline_run_id}} \
  --PageNumber 1 \
  --PageSize 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- All `pipelineRunItems[].Status` values indicate success
- All deployed nodes/workflows are in the list

## Data Source and Resource Group Verification

### Verify Data Source Availability

```bash
aliyun dataworks-public ListDataSources \
  --ProjectId {{project_id}} \
  --Type odps \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- The returned data source list includes the data source name referenced in spec.json

### Verify Resource Group Availability

```bash
aliyun dataworks-public ListResourceGroups \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success indicators**:
- The returned resource group list includes the resource group identifier referenced in spec.json

## Local Verification

### Verify spec.json Format

```bash
$PYTHON $SKILL/scripts/validate.py ./my_node
```

**Success indicators**:
- Output "Result: 0 errors, 0 warnings"
- Exit code is 0

### Verify Build Output

```bash
$PYTHON $SKILL/scripts/build.py ./my_node > /tmp/spec.json
python -m json.tool /tmp/spec.json > /dev/null && echo "JSON valid"
```

**Success indicators**:
- Build succeeds without errors
- Output JSON format is valid

## Common Verification Failure Handling

| Verification Failure Scenario | Possible Cause | Solution |
|-------------|---------|---------|
| Node not found | Create API call failed | Check API response and error message |
| Dependencies not effective | spec.dependencies not correctly configured or upstream missing outputs | Configure dependencies in spec.dependencies, ensure upstream declares outputs.nodeOutputs |
| Deployment failed | Code errors or insufficient permissions | Check Stage.Message for details |
| Data source not found | Name misspelled | Confirm with ListDataSources |
| Resource group invalid | Identifier is wrong | Confirm with ListResourceGroups |
