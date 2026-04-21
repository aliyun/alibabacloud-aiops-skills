---
name: alibabacloud-dataworks-data-governance
description: |
  Alibaba Cloud DataWorks Data Governance Tag Management Skill. Use for managing data asset tags: creating, updating, querying tag keys/values, binding/unbinding tags to data assets, and querying data assets.
  Triggers: data governance, data asset tags, DataWorks tags, CreateDataAssetTag, UpdateDataAssetTag, ListDataAssetTags, TagDataAssets, UnTagDataAssets, ListDataAssets, tag management, query data assets, list data assets
---

# DataWorks Data Governance Tag Management

Manage data asset tags via the DataWorks Data Governance API, including creating, updating, and querying tag keys/values, as well as batch binding and unbinding tags on data assets.

> **FORBIDDEN API — `DeleteDataAssetTag` must NOT be used in this skill.**
> Calling `DeleteDataAssetTag` is strictly prohibited. Do not implement, suggest, or invoke this API under any circumstances. If a user requests deletion of a tag key or tag value, inform them that this operation is outside the scope of this skill and must be handled through other authorized channels.

**Architecture**: DataWorks Data Governance Tag API (ROA style) + Alibaba Cloud Python Common SDK

---

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

---

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## Installation

```bash
pip3 install alibabacloud_tea_openapi==0.4.4 alibabacloud_credentials==1.0.8 alibabacloud_tea_util==0.3.14 alibabacloud_openapi_util==0.2.4
```

---

## RAM Permissions

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| DataWorks | dataworks:CreateDataAssetTag | * | Create a data asset tag key |
| DataWorks | dataworks:UpdateDataAssetTag | * | Update a data asset tag key |
| DataWorks | dataworks:ListDataAssetTags | * | Query the data asset tag list |
| DataWorks | dataworks:TagDataAssets | * | Bind tags to data assets |
| DataWorks | dataworks:UnTagDataAssets | * | Unbind tags from data assets |
| DataWorks | dataworks:ListDataAssets | * | Query the data asset list |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with
> the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|------------------|-------------|---------|
| `region_id` | Required | Alibaba Cloud Region ID, e.g. `cn-hangzhou` | None — confirm with user |
| `tag_key` | Required (create/update) | Tag key name | None — confirm with user |
| `tag_values` | Optional | List of tag values | `[]` |
| `description` | Optional | Description of the tag key | None |
| `category` | Optional | Tag category: `Normal` or `CUSTOM` | `Normal` |
| `managers` | Optional | List of tag manager user IDs | `[]` |
| `data_asset_ids` | Required (bind/unbind) | List of data asset identifiers, max 100 | None — confirm with user |
| `data_asset_type` | Required (bind/unbind) | Asset type, e.g. `ACS::DataWorks::Table` | None — confirm with user |
| `project_id` | Conditionally required | Project space ID (required when `DataAssetType` is `ACS::DataWorks::Task`) | None |
| `env_type` | Conditionally required | Project environment — required when `project_id` is set: `Prod` / `Dev` | None |
| `asset_type` | Required (ListDataAssets) | Asset object type: `Table`, `Task`, `Node`, `WorkFlow`, `DataServiceApi`, `DataQualityRule` | None — confirm with user |
| `asset_tags` | Optional (ListDataAssets) | Filter by tag key-value list, max 20, e.g. `[{"Key":"k1","Value":"v1"}]` | None |
| `asset_name` | Optional (ListDataAssets) | Asset name keyword for fuzzy search | None |
| `asset_ids` | Optional (ListDataAssets) | List of asset module IDs | None |
| `asset_owner` | Optional (ListDataAssets) | Asset owner user ID | None |
| `sort_by` | Optional (ListDataAssets) | Sort field and direction, e.g. `CreateTime Desc` | `CreateTime Desc` |

---

## Core Workflow

### Initialize SDK Client

```python
import re
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
import json

_VALID_DATA_ASSET_TYPES = {
    'ACS::DataWorks::Table', 'ACS::DataWorks::Task',
    'ACS::DataWorks::Node', 'ACS::DataWorks::WorkFlow',
    'ACS::DataWorks::DataServiceApi', 'ACS::DataWorks::DataQualityRule'
}
_VALID_ASSET_TYPES = {'Table', 'Task', 'Node', 'WorkFlow', 'DataServiceApi', 'DataQualityRule'}
_VALID_CATEGORIES  = {'Normal', 'CUSTOM'}
_VALID_ENV_TYPES   = {'Prod', 'Dev'}

def _validate_region_id(region_id):
    if not isinstance(region_id, str) or not region_id:
        raise ValueError('region_id must be a non-empty string')
    if not re.match(r'^[a-z]{2}-[a-z0-9-]+$', region_id):
        raise ValueError(f'Invalid region_id format: {region_id!r}')

def _validate_tags(tags, max_len=20):
    if not isinstance(tags, list) or len(tags) == 0:
        raise ValueError('tags must be a non-empty list')
    if len(tags) > max_len:
        raise ValueError(f'tags exceeds max length {max_len}, got {len(tags)}')
    for t in tags:
        if not isinstance(t, dict) or 'Key' not in t or 'Value' not in t:
            raise ValueError('Each tag must be a dict with "Key" and "Value"')

def _validate_asset_ids(ids, max_len=100):
    if not isinstance(ids, list) or len(ids) == 0:
        raise ValueError('data_asset_ids must be a non-empty list')
    if len(ids) > max_len:
        raise ValueError(f'data_asset_ids exceeds max length {max_len}, got {len(ids)}')

def _validate_page(page_number, page_size):
    if not isinstance(page_number, int) or page_number < 1:
        raise ValueError(f'page_number must be an integer >= 1, got {page_number!r}')
    if not isinstance(page_size, int) or not (1 <= page_size <= 100):
        raise ValueError(f'page_size must be an integer between 1 and 100, got {page_size!r}')

def create_client(region_id: str) -> OpenApiClient:
    _validate_region_id(region_id)
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = f'dataworks.{region_id}.aliyuncs.com'
    config.user_agent = 'AlibabaCloud-Agent-Skills'
    return OpenApiClient(config)
```

---

### 1. Create Tag Key (CreateDataAssetTag)

```python
def create_data_asset_tag(client, key: str, values=None, description=None,
                           value_policy=None, category='Normal', managers=None):
    if not isinstance(key, str) or not key.strip():
        raise ValueError('key must be a non-empty string')
    if category not in _VALID_CATEGORIES:
        raise ValueError(f'category must be one of {_VALID_CATEGORIES}, got {category!r}')
    if values is not None:
        if not isinstance(values, list):
            raise ValueError('values must be a list')
    if managers is not None:
        if not isinstance(managers, list):
            raise ValueError('managers must be a list')

    params = open_api_models.Params(
        action='CreateDataAssetTag',
        version='2024-05-18',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/tags',
        req_body_type='json',
        body_type='json'
    )
    body = {'Key': key}
    if values is not None:
        body['Values'] = values
    if description is not None:
        body['Description'] = description
    if value_policy is not None:
        body['ValuePolicy'] = value_policy
    if category:
        body['Category'] = category
    if managers is not None:
        body['Managers'] = managers

    request = open_api_models.OpenApiRequest(body=body)
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

### 2. Update Tag Key (UpdateDataAssetTag)

```python
def update_data_asset_tag(client, key: str, values=None, description=None, managers=None):
    if not isinstance(key, str) or not key.strip():
        raise ValueError('key must be a non-empty string')
    if values is not None:
        if not isinstance(values, list):
            raise ValueError('values must be a list')
    if managers is not None:
        if not isinstance(managers, list):
            raise ValueError('managers must be a list')

    params = open_api_models.Params(
        action='UpdateDataAssetTag',
        version='2024-05-18',
        protocol='HTTPS',
        method='PUT',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/tags',
        req_body_type='json',
        body_type='json'
    )
    body = {'Key': key}
    if values is not None:
        body['Values'] = values
    if description is not None:
        body['Description'] = description
    if managers is not None:
        body['Managers'] = managers

    request = open_api_models.OpenApiRequest(body=body)
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

### 3. List Tag Keys (ListDataAssetTags)

```python
def list_data_asset_tags(client, key=None, category=None, page_number=1, page_size=10):
    _validate_page(page_number, page_size)
    if category is not None and category not in _VALID_CATEGORIES:
        raise ValueError(f'category must be one of {_VALID_CATEGORIES}, got {category!r}')

    params = open_api_models.Params(
        action='ListDataAssetTags',
        version='2024-05-18',
        protocol='HTTPS',
        method='GET',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/tags',
        req_body_type='json',
        body_type='json'
    )
    queries = {
        'PageNumber': page_number,
        'PageSize': page_size
    }
    if key:
        queries['Key'] = key
    if category:
        queries['Category'] = category

    request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(queries)
    )
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

### 4. Bind Tags to Data Assets (TagDataAssets)

```python
def tag_data_assets(client, tags: list, data_asset_ids: list, data_asset_type: str,
                    project_id=None, env_type=None, auto_trace_enable=False):
    _validate_tags(tags, max_len=20)
    _validate_asset_ids(data_asset_ids, max_len=100)
    if data_asset_type not in _VALID_DATA_ASSET_TYPES:
        raise ValueError(f'data_asset_type must be one of {_VALID_DATA_ASSET_TYPES}, got {data_asset_type!r}')
    if data_asset_type == 'ACS::DataWorks::Task':
        if project_id is None or env_type is None:
            raise ValueError('project_id and env_type are required when data_asset_type is ACS::DataWorks::Task')
    if env_type is not None and env_type not in _VALID_ENV_TYPES:
        raise ValueError(f'env_type must be one of {_VALID_ENV_TYPES}, got {env_type!r}')

    params = open_api_models.Params(
        action='TagDataAssets',
        version='2024-05-18',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/tags/bind',
        req_body_type='json',
        body_type='json'
    )
    body = {
        'Tags': tags,
        'DataAssetIds': data_asset_ids,
        'DataAssetType': data_asset_type,
        'AutoTraceEnable': auto_trace_enable
    }
    if project_id is not None:
        body['ProjectId'] = project_id
    if env_type is not None:
        body['EnvType'] = env_type

    request = open_api_models.OpenApiRequest(body=body)
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

### 5. List Data Assets (ListDataAssets)

```python
def list_data_assets(client, asset_type: str, tags=None, name=None, ids=None,
                     owner=None, project_id=None, sort_by=None,
                     page_number=1, page_size=10):
    if asset_type not in _VALID_ASSET_TYPES:
        raise ValueError(f'asset_type must be one of {_VALID_ASSET_TYPES}, got {asset_type!r}')
    _validate_page(page_number, page_size)
    if tags is not None:
        _validate_tags(tags, max_len=20)

    params = open_api_models.Params(
        action='ListDataAssets',
        version='2024-05-18',
        protocol='HTTPS',
        method='GET',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/assets',
        req_body_type='json',
        body_type='json'
    )
    queries = {
        'Type': asset_type,
        'PageNumber': page_number,
        'PageSize': page_size
    }
    if tags is not None:
        queries['Tags'] = json.dumps(tags)
    if name is not None:
        queries['Name'] = name
    if ids is not None:
        queries['Ids'] = json.dumps(ids)
    if owner is not None:
        queries['Owner'] = owner
    if project_id is not None:
        queries['ProjectId'] = project_id
    if sort_by is not None:
        queries['SortBy'] = sort_by

    request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(queries)
    )
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

### 6. Unbind Tags from Data Assets (UnTagDataAssets)

```python
def untag_data_assets(client, tags: list, data_asset_ids: list, data_asset_type: str,
                      project_id=None, env_type=None):
    _validate_tags(tags, max_len=20)
    _validate_asset_ids(data_asset_ids, max_len=100)
    if data_asset_type not in _VALID_DATA_ASSET_TYPES:
        raise ValueError(f'data_asset_type must be one of {_VALID_DATA_ASSET_TYPES}, got {data_asset_type!r}')
    if data_asset_type == 'ACS::DataWorks::Task':
        if project_id is None or env_type is None:
            raise ValueError('project_id and env_type are required when data_asset_type is ACS::DataWorks::Task')
    if env_type is not None and env_type not in _VALID_ENV_TYPES:
        raise ValueError(f'env_type must be one of {_VALID_ENV_TYPES}, got {env_type!r}')

    params = open_api_models.Params(
        action='UnTagDataAssets',
        version='2024-05-18',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/data-governance/tags/unbind',
        req_body_type='json',
        body_type='json'
    )
    body = {
        'Tags': tags,
        'DataAssetIds': data_asset_ids,
        'DataAssetType': data_asset_type
    }
    if project_id is not None:
        body['ProjectId'] = project_id
    if env_type is not None:
        body['EnvType'] = env_type

    request = open_api_models.OpenApiRequest(body=body)
    runtime = util_models.RuntimeOptions()
    runtime.connect_timeout = 5000   # ms
    runtime.read_timeout = 30000     # ms
    return client.call_api(params, request, runtime)
```

---

## Response Handling

```python
def handle_response(response):
    status_code = response.get('statusCode')
    body = response.get('body', {})
    if status_code == 200 and body.get('Data'):
        print(f"[SUCCESS] RequestId: {body.get('RequestId')}")
        return body.get('Data')
    else:
        code = body.get('Code')
        message = body.get('Message')
        raise Exception(f"[FAIL] Code={code}, Message={message}, RequestId={body.get('RequestId')}")
```

---

## Success Verification

Operation success criteria:
- HTTP status code `200`
- Response body `Data` field is `true` (create/update/bind/unbind operations)
- Response body `Data` is an object (ListDataAssetTags, ListDataAssets)

For detailed step-by-step verification commands, see `references/verification-method.md`.

---

## Cleanup

```python
client = create_client('cn-hangzhou')  # Replace with actual Region

# Unbind tags from data assets
untag_data_assets(client,
    tags=[{"Key": "k1", "Value": "v1"}],
    data_asset_ids=["maxcompute-table.project.tableName"],
    data_asset_type="ACS::DataWorks::Table"
)
```

> **Note:** Deletion of tag keys or tag values via `DeleteDataAssetTag` is **not supported** in this skill. Do not attempt to call this API.

---

## Best Practices

1. **Batch limits**: `Tags` max 20, `DataAssetIds` max 100 per request — split into batches if needed
2. **Task-type assets**: When `DataAssetType` is `ACS::DataWorks::Task`, both `ProjectId` and `EnvType` are required
3. **Value policy**: Use `ValuePolicy` (e.g. regex `^L[1-7]$`) when creating a tag key to enforce valid value formats
4. **Least privilege**: Create a dedicated RAM role for tag management with only the required permissions
5. **Throttling retry**: Use exponential backoff when encountering `Throttling` errors
6. **Pagination**: `ListDataAssetTags` and `ListDataAssets` default to 10 per page, max 100 — use `TotalCount` to calculate total pages
7. **ListDataAssets serialization**: `Tags` and `Ids` query parameters must be JSON-serialized strings (use `json.dumps()`)
8. **ListDataAssets sort**: Default sort is `CreateTime Desc`; also supports `ModifyTime` and `HealthScore`

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [ram-policies.md](references/ram-policies.md) | RAM permission policies required by this Skill |
| [related-commands.md](references/related-commands.md) | API command reference |
| [verification-method.md](references/verification-method.md) | Step-by-step success verification |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria with correct/incorrect examples |
