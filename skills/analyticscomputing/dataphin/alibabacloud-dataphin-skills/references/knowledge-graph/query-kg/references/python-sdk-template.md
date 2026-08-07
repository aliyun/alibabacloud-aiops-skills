# Python SDK 泛化调用模板（query-kg）——旧版本独立部署兜底

> **仅作兜底**：KG OpenAPI 已正式发布（Online version: v6.1.1）并注册到 CLI 插件（>= 0.7.1），**优先使用 CLI 原生命令** `exec-kg-cypher` / `get-kg-neighbor`（见 SKILL.md §8）。本模板仅用于独立部署 < v6.1.1 的旧环境，使用 `alibabacloud_tea_openapi.client.Client.call_api()` 泛化调用。

> **实测校准**：以下模板基于实测环境验证。

## 前置安装

```bash
pip install alibabacloud-tea-openapi alibabacloud-tea-util
```

## ExecKgCypher 调用模板

```python
import json
import os
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client
from alibabacloud_tea_util import models as util_models

# UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入（继承自父 skill）
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
_ua = 'AlibabaCloud-Agent-Skills/query-kg' + (f'/{SESSION_ID}' if SESSION_ID else '')

# 1. 初始化客户端
config = open_api_models.Config(
    access_key_id='<YOUR_AK>',      # 从环境变量获取
    access_key_secret='<YOUR_SK>',   # 从环境变量获取
    endpoint='dataphin-openapi.<env>.aliyun.com',
    user_agent=_ua,
)
client = Client(config)
runtime = util_models.RuntimeOptions()  # 如需忽略 SSL: RuntimeOptions(ignore_ssl=True)

# 2. 构建请求参数
params = open_api_models.Params(
    action='ExecKgCypher',
    version='2023-06-30',
    protocol='HTTPS',
    method='POST',          # ★ 必须 POST
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json',
)

query_body = {
    'Query': "MATCH (n:Drug) RETURN n.product_name, n.drug_category LIMIT 10",
    'Limit': 100,
}

request = open_api_models.OpenApiRequest(
    query={
        'OpTenantId': '<YOUR_TENANT_ID>',
        'WorkspaceId': '<YOUR_WORKSPACE_ID>',
    },
    body={'ExecCommand': json.dumps(query_body)},  # ★ 参数名是 ExecCommand
)

# 3. 调用
result = client.call_api(params, request, runtime)
body = result.get('body', {})
data = body.get('Data', {})

# 4. 解析结果
# 4a. 标量查询结果（RETURN 返回具体列值）
row_list = data.get('RowList', [])
for row in row_list:
    cols = {c['Code']: c['Value'] for c in row['Columns']}
    print(cols)

# 4b. 节点查询结果（RETURN n 返回整个节点）
node_list = data.get('NodeList', [])
for node in node_list:
    print(f"DataId={node['DataId']}, Type={node['EntityType']}")
    props = {p['Code']: p['Value'] for p in node.get('Properties', [])}
    print(f"  Properties: {props}")

# 4c. 边查询结果（RETURN r 返回关系）
edge_list = data.get('EdgeList', [])
for edge in edge_list:
    print(f"{edge['SourceEntityId']} --[{edge['RelationType']}]--> {edge['TargetEntityId']}")
```

## GetKgNeighbor 调用模板

```python
# 前置：从 ExecKgCypher 获取目标实体的 DataId 和 EntityType
# node_list = cypher_result['body']['Data']['NodeList']
# data_id = node_list[0]['DataId']        # 如 "0a259156-d9f9-4bc1-be44-9b942a0b0e1a"
# entity_type = node_list[0]['EntityType'] # 如 "Drug"

params = open_api_models.Params(
    action='GetKgNeighbor',
    version='2023-06-30',
    protocol='HTTPS',
    method='POST',          # ★ 必须 POST
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json',
)

request = open_api_models.OpenApiRequest(
    query={
        'OpTenantId': '<YOUR_TENANT_ID>',
        'WorkspaceId': '<YOUR_WORKSPACE_ID>',
        'EntityDataId': data_id,       # ★ 参数名是 EntityDataId（不是 EntityId）
        'EntityType': entity_type,     # ★ EntityType 必填
        'Direction': 'Both',           # In / Out / Both
        'Depth': '1',
    },
)
runtime = util_models.RuntimeOptions()

result = client.call_api(params, request, runtime)
body = result.get('body', {})
data = body.get('Data', {})

# 解析邻居节点
node_list = data.get('NodeList', [])
print(f"邻居节点数: {len(node_list)}")
for node in node_list:
    props = {p['Code']: p['Value'] for p in node.get('PropertyList', [])}
    print(f"  {node['EntityType']}: {props}")

# 解析连接关系
edge_list = data.get('EdgeList', [])
print(f"连接关系数: {len(edge_list)}")
for edge in edge_list:
    props = {p['Code']: p['Value'] for p in edge.get('PropertyList', [])}
    print(f"  {edge['SourceEntityId'][:8]}.. --[{edge['RelationType']}]--> {edge['TargetEntityId'][:8]}.. {props}")
```

## 完整示例：益赛拓竞品分析

```python
# 组合查询：先 Cypher 定位益赛拓 → 再邻居遍历获取竞品关系
import json
import os
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client
from alibabacloud_tea_util import models as util_models

# UA 可观测：同上，SKILL_SESSION_ID 由 Agent 内联注入
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
_ua = 'AlibabaCloud-Agent-Skills/query-kg' + (f'/{SESSION_ID}' if SESSION_ID else '')

config = open_api_models.Config(
    access_key_id='<AK>', access_key_secret='<SK>',
    endpoint='<endpoint>',
    user_agent=_ua,
)
client = Client(config)
runtime = util_models.RuntimeOptions()

TENANT = '<租户ID>'
WS = '<空间ID>'

def cypher(query, limit=100):
    params = open_api_models.Params(action='ExecKgCypher', version='2023-06-30',
        protocol='HTTPS', method='POST', auth_type='AK', style='RPC',
        pathname='/', req_body_type='formData', body_type='json')
    request = open_api_models.OpenApiRequest(
        query={'OpTenantId': TENANT, 'WorkspaceId': WS},
        body={'ExecCommand': json.dumps({'Query': query, 'Limit': limit})})
    return client.call_api(params, request, runtime)

def get_neighbor(data_id, entity_type, direction='Both', depth='1'):
    params = open_api_models.Params(action='GetKgNeighbor', version='2023-06-30',
        protocol='HTTPS', method='POST', auth_type='AK', style='RPC',
        pathname='/', req_body_type='formData', body_type='json')
    request = open_api_models.OpenApiRequest(
        query={'OpTenantId': TENANT, 'WorkspaceId': WS,
               'EntityDataId': data_id, 'EntityType': entity_type,
               'Direction': direction, 'Depth': depth})
    return client.call_api(params, request, runtime)

# Step 1: 定位益赛拓
r = cypher("MATCH (n:Drug {drug_code: 'D002'}) RETURN n LIMIT 1")
node = r['body']['Data']['NodeList'][0]
print(f"找到: {node['EntityType']} DataId={node['DataId']}")

# Step 2: 遍历邻居
nr = get_neighbor(node['DataId'], node['EntityType'])
for n in nr['body']['Data']['NodeList']:
    print(f"  邻居: {n['EntityType']} - {n.get('PropertyList',[])}")
for e in nr['body']['Data']['EdgeList']:
    print(f"  关系: {e['RelationType']} ({e['SourceEntityId'][:8]}→{e['TargetEntityId'][:8]})")
```
