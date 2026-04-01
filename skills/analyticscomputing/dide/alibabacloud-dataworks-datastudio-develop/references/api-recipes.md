# DataWorks Data Development API Call Templates

All APIs are based on the DataWorks OpenAPI **2024-05-18** version. Each operation provides both aliyun CLI and Python SDK methods.

## Node Operations

### Create Node

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_node > /tmp/spec.json

aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_dataworks_public20240518.client import Client
from alibabacloud_dataworks_public20240518.models import CreateNodeRequest
from alibabacloud_tea_openapi.models import Config

credential = CredentialClient()
config = Config(credential=credential)
config.endpoint = 'dataworks.{{region}}.aliyuncs.com'
config.user_agent = 'AlibabaCloud-Agent-Skills'
client = Client(config)

with open('/tmp/spec.json') as f:
    spec = f.read()

request = CreateNodeRequest(
    project_id={{project_id}},
    scene='DATAWORKS_PROJECT',
    spec=spec
)
response = client.create_node(request)
print(f"NodeId: {response.body.id}")
```

### Create Node Within a Workflow

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_wf/step1 > /tmp/spec.json

aliyun dataworks-public CreateNode \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --ContainerId {{workflow_id}} \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
request = CreateNodeRequest(
    project_id=383839,
    scene='DATAWORKS_PROJECT',
    container_id='<workflow_id>',  # Create the node inside a workflow
    spec=spec
)
response = client.create_node(request)
print(f"NodeId: {response.body.id}")
```

### Update Node

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_node > /tmp/spec.json

aliyun dataworks-public UpdateNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --Spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateNodeRequest

request = UpdateNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}',
    spec=spec
)
response = client.update_node(request)
```

### Get Node Details

**aliyun CLI**:
```bash
aliyun dataworks-public GetNode \
  --ProjectId {{project_id}} \
  --Id {{node_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetNodeRequest

request = GetNodeRequest(
    project_id={{project_id}},
    id='{{node_id}}'
)
response = client.get_node(request)
# response.body.spec contains the full FlowSpec JSON
```

### List Nodes

**aliyun CLI**:
```bash
aliyun dataworks-public ListNodes \
  --ProjectId {{project_id}} \
  --Scene DATAWORKS_PROJECT \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListNodesRequest

request = ListNodesRequest(
    project_id={{project_id}},
    scene='DATAWORKS_PROJECT',
    page_number=1,
    page_size=100
)
response = client.list_nodes(request)
for node in response.body.paging_info.nodes:
    print(f"{node.id}: {node.name}")
```

## Workflow Operations

### Create Workflow

The workflow spec must include `script.runtime.command: "WORKFLOW"`, otherwise creation will fail. The correct spec format is as follows:

```json
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "workflows": [{
      "name": "my_workflow",
      "script": {
        "path": "my_workflow",
        "runtime": {"command": "WORKFLOW"}
      },
      "trigger": {
        "type": "Scheduler",
        "cron": "00 00 02 * * ?",
        "startTime": "1970-01-01 00:00:00",
        "endTime": "9999-01-01 00:00:00",
        "timezone": "Asia/Shanghai"
      }
    }]
  }
}
```

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_wf > /tmp/wf.json

aliyun dataworks-public CreateWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateWorkflowDefinitionRequest

with open('/tmp/wf.json') as f:
    spec = f.read()

request = CreateWorkflowDefinitionRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_workflow_definition(request)
print(f"WorkflowId: {response.body.id}")
```

### Update Workflow

**aliyun CLI**:
```bash
aliyun dataworks-public UpdateWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --Spec "$(cat /tmp/wf.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import UpdateWorkflowDefinitionRequest

request = UpdateWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}',
    spec=spec
)
client.update_workflow_definition(request)
```

### Get Workflow Details

**aliyun CLI**:
```bash
aliyun dataworks-public GetWorkflowDefinition \
  --ProjectId {{project_id}} \
  --Id {{workflow_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetWorkflowDefinitionRequest

request = GetWorkflowDefinitionRequest(
    project_id={{project_id}},
    id='{{workflow_id}}'
)
response = client.get_workflow_definition(request)
```

### List Workflows

**aliyun CLI**:
```bash
aliyun dataworks-public ListWorkflowDefinitions \
  --ProjectId {{project_id}} \
  --Type CycleWorkflow \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListWorkflowDefinitionsRequest

request = ListWorkflowDefinitionsRequest(
    project_id={{project_id}},
    type='CycleWorkflow',
    page_number=1,
    page_size=100
)
response = client.list_workflow_definitions(request)
```

## Resource File Operations

### Create Resource

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_resource > /tmp/res.json

aliyun dataworks-public CreateResource \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/res.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateResourceRequest

request = CreateResourceRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_resource(request)
print(f"ResourceId: {response.body.id}")
```

### List Resources

**aliyun CLI**:
```bash
aliyun dataworks-public ListResources \
  --ProjectId {{project_id}} \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

## Function Operations

### Create Function

**aliyun CLI**:
```bash
$PYTHON $SKILL/scripts/build.py ./my_func > /tmp/func.json

aliyun dataworks-public CreateFunction \
  --ProjectId {{project_id}} \
  --Spec "$(cat /tmp/func.json)" \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreateFunctionRequest

request = CreateFunctionRequest(
    project_id={{project_id}},
    spec=spec
)
response = client.create_function(request)
print(f"FunctionId: {response.body.id}")
```

### List Functions

**aliyun CLI**:
```bash
aliyun dataworks-public ListFunctions \
  --ProjectId {{project_id}} \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

## Node Dependency Configuration

### Dependency Configuration

When configuring inter-node dependencies, there is no need to dual-write `inputs.nodeOutputs`; only maintain dependencies in the `spec.dependencies` array:

- Upstream nodes must declare `outputs.nodeOutputs` (`${projectIdentifier}.node_name`)
- Downstream nodes reference upstream outputs in `spec.dependencies`
- `spec.dependencies[*].nodeId` must exactly match the corresponding node's `id`, otherwise dependencies will not be recognized

```json
{
  "spec": {
    "nodes": [{
      "name": "downstream_node"
    }],
    "dependencies": [{
      "nodeId": "downstream_node",
      "depends": [{
        "type": "Normal",
        "output": "upstream_project.upstream_node_output"
      }]
    }]
  }
}
```

## Deployment Process

Deployment is an asynchronous multi-stage pipeline. For the complete process and detailed instructions, see [deploy-guide.md](deploy-guide.md). Below are the API call templates.

### Create Deployment (Online)

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import CreatePipelineRunRequest

# type: Online (deploy) or Offline (take offline)
# object_ids: Only the first entity and its child entities are processed
request = CreatePipelineRunRequest(
    project_id={{project_id}},
    type='Online',
    object_ids=['{{object_id}}']
)
response = client.create_pipeline_run(request)
run_id = response.body.id
print(f"PipelineRunId: {run_id}")
```

### Query Deployment Status

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetPipelineRunRequest

response = client.get_pipeline_run(GetPipelineRunRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}'
))
pipeline = response.body.pipeline.to_map()
print(f"Status: {pipeline['Status']}")
# Status: Init / Running / Success / Fail / Termination / Cancel
for stage in pipeline.get('Stages', []):
    print(f"  {stage['Code']}({stage['Status']}): {stage['Name']}")
```

### Advance Deployment Stage

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ExecPipelineRunStageRequest

# code: Stage code, obtained from Stages[].Code returned by GetPipelineRun
# Must advance in order; stages cannot be skipped
# Async trigger; continue polling to confirm results
client.exec_pipeline_run_stage(ExecPipelineRunStageRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}',
    code='{{stage_code}}'  # e.g., PROD_CHECK, PROD
))
```

### View Deployment Items

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunItemsRequest

response = client.list_pipeline_run_items(ListPipelineRunItemsRequest(
    project_id={{project_id}},
    pipeline_run_id='{{pipeline_run_id}}',
    page_number=1,
    page_size=50
))
for item in response.body.paging_info.pipeline_run_items:
    m = item.to_map()
    print(f"{m['Name']}: {m.get('Status', 'N/A')}")
```

### Query Deployment History

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListPipelineRunsRequest

response = client.list_pipeline_runs(ListPipelineRunsRequest(
    project_id={{project_id}},
    page_number=1,
    page_size=20
))
for run in response.body.paging_info.pipeline_runs:
    m = run.to_map()
    print(f"{m['Id']} [{m['Status']}]")
```

### Cancel Deployment

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import AbolishPipelineRunRequest

client.abolish_pipeline_run(AbolishPipelineRunRequest(
    project_id={{project_id}},
    id='{{pipeline_run_id}}'
))
```

## Helper Queries

### Get Project Information (Convert Between projectId and projectIdentifier)

**aliyun CLI**:
```bash
# Get projectId by projectIdentifier
aliyun dataworks-public GetProject \
  --ProjectIdentifier my_project_name \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import GetProjectRequest

request = GetProjectRequest(
    project_identifier='my_project_name'
)
response = client.get_project(request)
print(f"ProjectId: {response.body.id}")
print(f"ProjectIdentifier: {response.body.project_identifier}")
```

### List Data Sources

**aliyun CLI**:
```bash
aliyun dataworks-public ListDataSources \
  --ProjectId {{project_id}} \
  --Type odps \
  --PageNumber 1 \
  --PageSize 100 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListDataSourcesRequest

request = ListDataSourcesRequest(
    project_id={{project_id}},
    type='odps',
    page_number=1,
    page_size=100
)
response = client.list_data_sources(request)
for ds in response.body.paging_info.data_sources:
    print(f"{ds.name}: {ds.type}")
```

### List Resource Groups

**aliyun CLI**:
```bash
aliyun dataworks-public ListResourceGroups \
  --ProjectId {{project_id}} \
  --user-agent AlibabaCloud-Agent-Skills
```

**Python SDK**:
```python
from alibabacloud_dataworks_public20240518.models import ListResourceGroupsRequest

request = ListResourceGroupsRequest(
    project_id={{project_id}}
)
response = client.list_resource_groups(request)
for rg in response.body.resource_groups:
    print(f"{rg.identifier}: {rg.name}")
```
