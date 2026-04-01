# Related APIs

Complete API reference for MaxCompute Project Management operations.

## API Overview

| Product | API Version | CLI Command | API Action | Description |
|---------|-------------|-------------|------------|-------------|
| MaxCompute | 2022-01-04 | `aliyun maxcompute create-project` | CreateProject | Create a MaxCompute project |
| MaxCompute | 2022-01-04 | `aliyun maxcompute get-project` | GetProject | Get project details |
| MaxCompute | 2022-01-04 | `aliyun maxcompute list-projects` | ListProjects | List all projects |
| MaxCompute | 2022-01-04 | `aliyun maxcompute delete-project` | DeleteProject | Delete a project |

---

## CreateProject

**API Endpoint:** `https://maxcompute.{regionId}.aliyuncs.com`

**API Documentation:** [CreateProject](https://api.aliyun.com/api/MaxCompute/2022-01-04/CreateProject)

### CLI Command

```bash
aliyun maxcompute create-project \
  --body '{"name":"<project-name>","defaultQuota":"os_PayAsYouGoQuota","productType":"payasyougo"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Request Body Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `name` | string | Yes | Project name (3-28 characters, lowercase letters, numbers, underscores) | `test_project` |
| `defaultQuota` | string | No | Quota alias | `os_PayAsYouGoQuota` |
| `productType` | string | No | Product type: `payasyougo` or `subscription` | `payasyougo` |
| `properties.typeSystem` | string | No | Type system: `1` (Hive) or `2` (MaxCompute) | `2` |
| `properties.autoMvQuotaGb` | integer | No | Auto MV quota in GB | `100` |

### Response

```json
{
  "requestId": "0bc1ec92-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": "project_name"
}
```

---

## GetProject

**API Documentation:** [GetProject](https://api.aliyun.com/api/MaxCompute/2022-01-04/GetProject)

### CLI Command

```bash
aliyun maxcompute get-project \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--project-name` | string | Yes | Project name to query |
| `--verbose` | boolean | No | Return detailed information |

### Response

```json
{
  "requestId": "0bc1ec92-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": {
    "name": "project_name",
    "owner": "ALIYUN$account@aliyun.com",
    "status": "AVAILABLE",
    "type": "managed",
    "defaultQuota": "os_PayAsYouGoQuota",
    "productType": "payasyougo",
    "regionId": "cn-hangzhou",
    "createdTime": 1234567890000,
    "properties": {
      "typeSystem": "2"
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `data.name` | string | Project name |
| `data.owner` | string | Project owner account |
| `data.status` | string | Status: `AVAILABLE`, `READONLY`, `DELETING`, `FROZEN` |
| `data.type` | string | Project type |
| `data.defaultQuota` | string | Associated quota alias |
| `data.productType` | string | Product type |
| `data.regionId` | string | Region ID |
| `data.createdTime` | long | Creation timestamp (milliseconds) |
| `data.properties.typeSystem` | string | Type system setting |

---

## ListProjects

**API Documentation:** [ListProjects](https://api.aliyun.com/api/MaxCompute/2022-01-04/ListProjects)

### CLI Command

```bash
# List all projects
aliyun maxcompute list-projects \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills

# Filter by quota
aliyun maxcompute list-projects \
  --quota-nick-name <quota-name> \
  --max-item 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Request Parameters

| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `--quota-nick-name` | string | No | Filter by quota alias | - |
| `--quota-name` | string | No | Filter by quota name | - |
| `--prefix` | string | No | Project name prefix filter | - |
| `--max-item` | integer | No | Maximum items per page | 10 |
| `--marker` | string | No | Pagination marker from previous response | - |
| `--type` | string | No | Project type filter | - |

### Response

```json
{
  "requestId": "0bc1ec92-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": {
    "projects": [
      {
        "name": "project1",
        "owner": "ALIYUN$account@aliyun.com",
        "status": "AVAILABLE",
        "defaultQuota": "os_PayAsYouGoQuota"
      },
      {
        "name": "project2",
        "owner": "ALIYUN$account@aliyun.com",
        "status": "AVAILABLE",
        "defaultQuota": "my_quota"
      }
    ],
    "nextToken": "next_page_marker"
  }
}
```

---

## DeleteProject

**API Documentation:** [DeleteProject](https://api.aliyun.com/api/MaxCompute/2022-01-04/DeleteProject)

> ⚠️ **Warning:** This operation is irreversible. All data in the project will be permanently deleted.

### CLI Command

```bash
aliyun maxcompute delete-project \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--project-name` | string | Yes | Project name to delete |

### Prerequisites

1. Project must be in `AVAILABLE` status
2. All tables and resources in the project should be deleted first
3. User must have `odps:DeleteProject` permission

### Response

```json
{
  "requestId": "0bc1ec92-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "data": "project_name"
}
```

---

## Error Codes

| Error Code | HTTP Status | Description | Solution |
|------------|-------------|-------------|----------|
| `InvalidParameter` | 400 | Invalid parameter value | Check parameter format and constraints |
| `ProjectAlreadyExist` | 409 | Project name already exists | Choose a different project name |
| `ProjectNotFound` | 404 | Project does not exist | Verify project name |
| `NoPermission` | 403 | Insufficient permissions | Check RAM policy |
| `QuotaNotFound` | 404 | Specified quota does not exist | Verify quota alias |
| `InvalidProjectName` | 400 | Project name format invalid | Use 3-28 chars: lowercase, numbers, underscores |

---

## SDK Code Example (Python)

If CLI is not suitable for your use case, use the Python Common SDK:

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
import json

# User-Agent identifier for Alibaba Cloud Agent Skills
USER_AGENT = 'AlibabaCloud-Agent-Skills'

def create_maxcompute_project(project_name, quota_nickname, product_type="payasyougo"):
    """Create a MaxCompute project using Python Common SDK."""
    
    # Initialize credentials
    credential = CredentialClient()
    config = open_api_models.Config(credential=credential)
    config.endpoint = 'maxcompute.cn-hangzhou.aliyuncs.com'
    # [MUST] Set User-Agent for tracking
    config.user_agent = USER_AGENT
    client = OpenApiClient(config)
    
    # Configure API parameters
    params = open_api_models.Params(
        action='CreateProject',
        version='2022-01-04',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='ROA',
        pathname='/api/v1/projects',
        req_body_type='json',
        body_type='json'
    )
    
    # Build request body
    body = {
        'name': project_name,
        'defaultQuota': quota_nickname,
        'productType': product_type
    }
    
    request = open_api_models.OpenApiRequest(
        body=OpenApiUtilClient.parse_to_map(body)
    )
    
    # Execute request with timeout settings
    runtime = util_models.RuntimeOptions(
        connect_timeout=10000,  # 10 seconds connection timeout
        read_timeout=30000      # 30 seconds read timeout
    )
    return client.call_api(params, request, runtime)
```

**Required Dependencies:**

```bash
pip install alibabacloud_credentials alibabacloud_tea_openapi alibabacloud_tea_util alibabacloud_openapi_util
```
