# Python SDK 泛化调用模板（manage-kg-knowledge，仅旧环境兜底）

> **仅作旧环境兜底**：KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），新环境一律优先 CLI 原生命令（`create-kg-entity` / `exec-kg-cypher` 等，见 SKILL.md）。本模板仅用于独立部署 < v6.1.1、KG OpenAPI 尚未发布的旧环境，通过 Python Tea SDK `call_api()` 泛化调用。

## 前置安装

```bash
pip3 install alibabacloud-dataphin-public20230630 alibabacloud-tea-openapi alibabacloud-tea-util
```

## 泛化调用模板

```python
import json
import os
from alibabacloud_tea_openapi.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入（继承自父 skill）
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
_ua = 'AlibabaCloud-Agent-Skills/manage-kg-knowledge' + (f'/{SESSION_ID}' if SESSION_ID else '')

config = open_api_models.Config(
    access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
    access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
    endpoint='<YOUR_DATAPHIN_ENDPOINT>',
    user_agent=_ua,
)
client = Client(config)
runtime = util_models.RuntimeOptions()
runtime.ignore_ssl = True

# 创建实体
params = open_api_models.Params(
    action='CreateKgEntity',
    version='2023-06-30',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json'
)

request = open_api_models.OpenApiRequest(
    query={'OpTenantId': '<YOUR_OP_TENANT_ID>', 'WorkspaceId': '<YOUR_WORKSPACE_ID>'},
    # ★ 写操作请求体参数名是 CreateCommand（JSON 字符串），不是平铺 body
    body={'CreateCommand': json.dumps({
        'EntityType': 'COMPANY',
        'PropertyList': [
            {'Code': 'name', 'Value': '阿里巴巴集团'},
            {'Code': 'industry', 'Value': '互联网'}
        ]
    }, ensure_ascii=False)}
)

result = client.call_api(params, request, runtime)
print(result)
```

## Cypher 查询模板

```python
params = open_api_models.Params(
    action='ExecKgCypher',
    version='2023-06-30',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json'
)

request = open_api_models.OpenApiRequest(
    query={'OpTenantId': '<YOUR_OP_TENANT_ID>', 'WorkspaceId': '<YOUR_WORKSPACE_ID>'},
    # ★ 请求体参数名是 ExecCommand（JSON 字符串）
    body={'ExecCommand': json.dumps({
        'Query': "MATCH (c:COMPANY)-[r:INVEST]->(t:COMPANY) RETURN c, r, t LIMIT 10",
        'Limit': 100
    }, ensure_ascii=False)}
)

result = client.call_api(params, request, runtime)
# 实测响应字段均在 Data 下：NodeList / EdgeList / RowList
data = result.get('body', {}).get('Data', {})
nodes = data.get('NodeList', [])
edges = data.get('EdgeList', [])
print(f"Nodes: {len(nodes)}, Edges: {len(edges)}")
```

## 常用 API Action 列表

| Action | method | 说明 |
|--------|--------|------|
| `CreateKgEntity` | POST | 创建实体 |
| `ListKgEntity` | POST | 实体列表（含过滤） |
| `BatchCreateKgEntity` | POST | 批量创建实体 |
| `CreateKgRelation` | POST | 创建关系 |
| `ListKgRelation` | GET | 关系列表 |
| `BatchCreateKgRelation` | POST | 批量创建关系 |
| `ExecKgCypher` | POST | Cypher 查询 |
| `GetKgNeighbor` | GET | 邻居遍历 |
