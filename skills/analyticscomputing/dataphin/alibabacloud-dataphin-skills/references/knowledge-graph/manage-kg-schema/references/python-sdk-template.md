# Python SDK 泛化调用模板（manage-kg-schema，仅旧环境兜底）

> **仅作旧环境兜底**：KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），新环境一律优先 CLI 原生命令（`export-kg-schema` / `import-kg-schema` / `publish-kg-schema` / `get-kg-schema-publish-result`，见 SKILL.md）。本模板仅用于独立部署 < v6.1.1、KG OpenAPI 尚未发布的旧环境，通过 Python Tea SDK `call_api()` 泛化调用。

## 前置安装

```bash
pip3 install alibabacloud-dataphin-public20230630 alibabacloud-tea-openapi alibabacloud-tea-util
```

## 泛化调用模板

```python
import os
from alibabacloud_tea_openapi.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入，与 CLI --user-agent 同一 session-id
# 继承自父 skill alibabacloud-dataphin-skills，未设置时降级为仅 skill 名
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
_ua = 'AlibabaCloud-Agent-Skills/manage-kg-schema' + (f'/{SESSION_ID}' if SESSION_ID else '')

# 初始化客户端
config = open_api_models.Config(
    access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
    access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
    endpoint='<YOUR_DATAPHIN_ENDPOINT>',
    user_agent=_ua,
)
client = Client(config)
runtime = util_models.RuntimeOptions()
runtime.ignore_ssl = True  # 独立部署环境

# 构造泛化请求参数
from alibabacloud_tea_openapi import models as open_api_models

params = open_api_models.Params(
    action='ExportKgSchema',
    version='2023-06-30',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',
    req_body_type='formData',
    body_type='json'
)

# 构造请求（导出整体 Schema，无需请求体）
request = open_api_models.OpenApiRequest(
    query={
        'OpTenantId': '300001413',
        'WorkspaceId': 'workspace_001'
    },
    body={}
)

# 发起调用
result = client.call_api(params, request, runtime)
print(result)
# 响应结构: {'body': {'SchemaInfo': {'Content': '<YAML>', 'OutputFormat': 'yaml'}, ...}, 'statusCode': 200}
```

## 常用 API Action 列表

| Action | method | 说明 |
|--------|--------|------|
| `ExportKgSchema` | POST | 导出整体 Schema（注意是 POST，非 GET） |
| `ImportKgSchema` | POST | 导入整体 Schema（部分环境需 ImportCommand 包装） |
| `PublishKgSchema` | POST | 发布 Schema（部分环境需 PublishCommand 包装） |
| `GetKgSchemaPublishResult` | GET | 查询发布结果 |

> KG Schema OpenAPI 仅提供以上 4 个整体 Schema Action，无实体类型/关系类型的细粒度 CRUD。

## ImportKgSchema 调用示例

部分环境（如 env23）的 ImportKgSchema API 需要将参数包装为 `ImportCommand` JSON 字符串：

```python
import json

yaml_content = open('schema.yaml', 'r').read()

# 包装为 ImportCommand JSON 字符串
import_cmd = json.dumps({
    'Format': 'yaml',
    'Content': yaml_content,
    'MergeStrategy': 'Merge'
})

request = open_api_models.OpenApiRequest(
    query={
        'OpTenantId': '300001414',
        'WorkspaceId': 'd7085c158f6e4c66822c1959c46f0f7c'
    },
    body={'ImportCommand': import_cmd}
)

result = client.call_api(params, request, runtime)
print(result.get('body', {}))
# 成功响应: {'ImportResult': {'EntityTypeCount': 2, 'RelationTypeCount': 1}, 'Success': True}
```

## 注意事项

- 泛化调用通过 `client.call_api(params, request, runtime)` 实现，无需 SDK 预注册方法
- `action` 参数为 API 名称（PascalCase），如 `ImportKgSchema`
- `version` 固定为 `2023-06-30`（Dataphin OpenAPI 版本）
- `style` 使用 `RPC`（Dataphin OpenAPI 均为 RPC 风格）
- 查询类 API 用 `GET` + `query` 传参；写操作类 API 用 `POST` + `body` 传参
