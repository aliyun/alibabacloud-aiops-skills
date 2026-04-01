# CreateNode

> Latest API definition: https://api.aliyun.com/meta/v1/products/dataworks-public/versions/2024-05-18/apis/CreateNode/api.json
> If the call returns an error, you can obtain the latest parameter definitions from the URL above.

### Idempotency Note

This API does not support `ClientToken`. If the call times out or returns a network error, **do not blindly retry**. First check whether the node was created by calling `ListNodes --Name <node_name>`. Only retry if the node does not exist. Always record the `RequestId` from the response for traceability.

### Create Node

**Prerequisite**: Use build.py to merge the three files (spec.json + code file + properties) into the API input:
```bash
python $SKILL/scripts/build.py ./my_node > /tmp/spec.json
```

**aliyun CLI**:
```bash
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

### Create Node Inside a Workflow

Same as above, after merging with build.py, add `--ContainerId`:

**aliyun CLI**:
```bash
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
    project_id={{project_id}},
    scene='DATAWORKS_PROJECT',
    container_id='{{workflow_id}}',
    spec=spec
)
response = client.create_node(request)
print(f"NodeId: {response.body.id}")
```
