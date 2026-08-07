---
name: create-and-publish-api
description: |
  数据服务 API 创建与发布的完整流程。数据开发工程师通过 CLI 完成：查询项目 → 创建 SQL 模式 API → 发布到生产环境 → 验证发布结果。
  触发场景：创建数据服务 API / 发布 API / SQL API / API 开发 / 直连数据源创建 API。
---

# 数据服务 API 创建与发布

## 1. Scenario Description

数据开发工程师通过阿里云 CLI 完成数据服务 API 的全生命周期管理：

**业务流程：**
```
查询项目 → 查询分组 → 创建 API（直连 SQL 模式）→ 发布到生产 → 验证发布
```

**资源拓扑：**
```
数据服务项目
├── API 分组（可选）
└── API
    ├── 请求参数
    ├── 返回参数
    ├── 数据源绑定
    └── 发布状态（开发态 / 已发布）
```

**前置条件：**
- 数据服务项目已存在，当前用户为项目成员
- 目标数据源已注册并授权（[TODO: 数据源管理 Skill，属于 dataplan 模块]）

## 2. Installation

```bash
# 安装 aliyun CLI（>= 3.4.8）：https://github.com/aliyun/aliyun-cli
# 各操作系统一键安装脚本见 ./references/cli-installation-guide.md

# 安装 dataphin-public 插件
aliyun plugin install --names aliyun-cli-dataphin-public

# 验证
aliyun dataphin-public --help
```

详见 [CLI 安装指南](./references/cli-installation-guide.md)。

## 3. Environment Variables

> 凭证与环境变量由父 skill `alibabacloud-dataphin-skills` 统一声明并预检（父 §3 + §4 Authentication + §8 Step 0，先于路由到本 skill 执行）；本 skill 不重复声明。

## 4. Authentication

### Pre-check: Credentials Required

```bash
# 检查凭证配置
aliyun configure list

# 检查 CLI 版本
aliyun version
# 要求 >= 3.4.8

# 检查插件可用
aliyun dataphin-public --help
```

**凭证不可打印**：任何时候不得将 AccessKey ID/Secret 输出到终端或日志。

## 5. RAM Policy

本 Skill 涉及的最小 RAM 权限：

```json
{
  "Effect": "Allow",
  "Action": [
    "dataphin:GetDataServiceMyProjects",
    "dataphin:GetDataServiceApiGroups",
    "dataphin:CreateDataServiceApi",
    "dataphin:PublishDataServiceApi",
    "dataphin:ListDataServicePublishedApis",
    "dataphin:GetDataServiceApiDocument"
  ],
  "Resource": "*"
}
```

### Permission Failure Handling

若遇到权限错误（HTTP 403 或 ErrorCode 含 `Forbidden`/`NoPermission`），请：
1. 确认 RAM 用户已附加上述策略
2. 确认策略中 Resource 范围覆盖目标租户
3. 联系租户管理员授权

详见 [RAM 策略参考](../../ram-policies.md)。

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation**
> 执行前必须确认以下业务参数：

### 顶层参数

| 参数 | 含义 | 获取方式 | 必填 |
|------|------|---------|------|
| OpTenantId | 租户 ID（小整数，如 300001413） | profile 或询问用户 | 是 |
| ProjectId | 数据服务项目 ID（小整数，如 22） | 步骤 1 查询 | 是 |
| ApiName | API 名称 | 用户指定 | 是 |
| GroupId | API 分组 ID（小整数，如 85） | 步骤 2 查询 | 否 |

### CreateCommand 必填参数

| 参数 | 含义 | 合法值 | 必填 |
|------|------|-------|------|
| ProjectId | 项目 ID | 小整数 | 是 |
| ApiName | API 名称 | 字符串 | 是 |
| ApiType | API 类型 | **3**（当前仅支持 3） | 是 |
| Mode | 项目模式 | 0（Basic模式）/ 1（Dev-Prod模式） | 是 |
| CallMode | 调用模式 | 1（同步）/ 2（异步） | 否 |
| RequestType | 请求类型 | 0（GET单条）/ **1**（LIST多条）/ 2（CREATE）/ 3（UPDATE） | 是 |
| BizProtocol | 协议 | **[0]**（HTTP） | 是 |
| Version | 版本号 | **"1.0.0"** | 是 |
| Timeout | 超时（毫秒） | 默认 **30000** | 是 |
| ApiGroupId | 分组 ID（SDK 字段名） | 小整数 | 是 |
| ApiGroupName | 分组名称 | 字符串（如 `默认API分组`） | 是 |

### ScriptDetails 参数（SQL 模式必填）

| 参数 | 含义 | 合法值 | 必填 |
|------|------|-------|------|
| DatasourceID | 数据源 ID | **19 位 snowflake ID，必须用 Python SDK 传参** | 是 |
| DatasourceType | 数据源或数据服务单元类型 | 0（数据服务单元）/ **1**（数据源） | 是 |
| SqlMode | SQL 模式 | **1**（基础模式）/ 2（高级模式） | 是 |
| Script | SQL 语句 | 使用 `${param}` 占位符 | 是 |
| ScriptRequestParameters | 请求参数列表 | 见下方枚举 | 是 |
| ScriptResponseParameters | 返回参数列表 | 见下方枚举 | 是 |

### ScriptRequestParameters 字段

| 字段 | 含义 | 合法值 | 必填 |
|------|------|-------|------|
| ParameterName | 参数名称 | 与 SQL 中 `${param}` 对应 | 是 |
| ParameterDataType | 数据类型 | 见 ParameterDataType 枚举 | 是 |
| ParameterValueType | 参数值类型 | **1**（单值，用于=/>=/<=/>/</!=/between）/ 2（多值，用于 IN/NOT IN） | 是 |
| IsRequiredParameter | 是否必填 | true / false | 否 |
| DefaultValue | 默认值 | 字符串 | 否 |
| ExampleValue | 示例值 | 字符串 | 否 |

### ParameterDataType 枚举值（字符串类型）

| 值 | 含义 |
|----|------|
| STRING | 字符串 |
| INT | 整型 |
| LONG | 长整型 |
| DOUBLE | 双精度浮点 |
| FLOAT | 单精度浮点 |
| SHORT | 短整型 |
| BOOLEAN | 布尔 |
| DATE | 日期（yyyy-MM-dd HH:mm:ss） |
| BIGDECIMAL | 高精度十进制 |
| BINARY | 二进制 |
| BYTE | 字节 |
| ARRAY | 数组 |

### publish-data-service-api 参数

| 参数 | 含义 | 获取方式 | 必填 |
|------|------|---------|------|
| OpTenantId | 租户 ID | 同上 | 是 |
| ApiId | API ID | 步骤 3 返回 | 是 |
| ProjectId | 项目 ID | 同上 | 是 |
| VersionId | 版本 ID | 步骤 3 返回或查询 | 是 |

**数据源获取说明：**
> 数据源需预先创建并授权。当前可通过 Dataphin 控制台 > 数据源管理 获取 DatasourceID。
> [TODO: 数据源管理 Skill（dataplan 模块）后续补充]

**⚠️ 大整数精度警告：**
> DatasourceID 是 19 位 snowflake ID（如 `7467470269897096832`），超过 JavaScript 安全整数范围（2^53）。
> **aliyun CLI 内部 JSON 解析会丢失精度**（`7467470269897096832` → `7467470269897097216`）。
> 因此 `create-data-service-api` **必须使用 Python SDK 而非 CLI**。详见 §8 步骤 3。

## 7. Observability

本子 Skill 的 session-id **继承自父 Skill `alibabacloud-dataphin-skills`**，不重新生成。

所有 CLI 命令携带：
```
--user-agent AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}
```

其中 `{SESSION_ID}` 为父 Skill 生成的 32 字符小写十六进制字符串。

## 8. Core Workflow

### 步骤 1：查询数据服务项目

```bash
aliyun dataphin-public get-data-service-my-projects \
  --op-tenant-id "{OpTenantId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}"
```

**响应处理：**
- 从返回的项目列表中选择目标项目
- 提取 `ProjectId`（小整数，如 22）
- 示例：`"ProjectId": 22`

### 步骤 2：查询 API 分组（可选）

```bash
aliyun dataphin-public get-data-service-api-groups \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}"
```

**响应处理：**
- 列出可用分组，用户选择或使用默认分组
- 提取 `GroupId`（小整数，如 85）

### 步骤 3：创建 API（Python SDK 方式）

> **⚠️ 为什么必须使用 Python SDK？**
> `create-data-service-api` 涉及 `DatasourceID`（19 位 snowflake ID），aliyun CLI 内部 JSON 解析会将超过 2^53 的整数精度丢失。
> 例如：`7467470269897096832` → `7467470269897097216`（差值 384）。
> 必须使用 Python SDK 绕过此问题。

#### HITL 确认（写操作）

执行前确认以下信息：
- API 名称：`{ApiName}`
- SQL 语句：`{Sql}`
- 数据源：`{DatasourceID}`
- 调用模式：同步/异步
- 影响范围：在目标项目中创建新 API
- 可回滚：创建后可删除

**确认后执行：**

```python
import os
from alibabacloud_dataphin_public20230630.client import Client
from alibabacloud_dataphin_public20230630 import models as datap_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入（继承自父 skill）
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
ua = 'AlibabaCloud-Agent-Skills/create-and-publish-api'
if SESSION_ID:
    ua = f'{ua}/{SESSION_ID}'

config = open_api_models.Config(
    access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
    access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
    endpoint='dataphin-openapi.{env}.aliyun.com',
    user_agent=ua
)
client = Client(config)
runtime = util_models.RuntimeOptions()
runtime.ignore_ssl = True  # 独立部署环境需忽略 SSL

# ⚠️ ParameterDataType SDK 定义为 int 是 bug，需 monkey-patch 为字符串
# 参考：https://github.com/aliyun/alibabacloud-sdk/issues

script_details = datap_models.CreateDataServiceApiRequestCreateCommandScriptDetails(
    datasource_id=7467470269897096832,  # ← 大整数在 Python int 中安全
    datasource_type=1,  # 0=数据服务单元, 1=数据源
    sql_mode=1,          # 1=基础模式
    script='SELECT user_id, user_name FROM user_info WHERE user_id = ${userId}',
    script_request_parameters=[
        datap_models.CreateDataServiceApiRequestCreateCommandScriptDetailsScriptRequestParameters(
            parameter_name='userId',
            parameter_data_type='STRING',   # ← 字符串枚举，非 int
            parameter_value_type='1',       # 1=单值（必填）
            is_required_parameter=True
        )
    ],
    script_response_parameters=[
        datap_models.CreateDataServiceApiRequestCreateCommandScriptDetailsScriptResponseParameters(
            parameter_name='user_id',
            parameter_data_type='STRING'
        ),
        datap_models.CreateDataServiceApiRequestCreateCommandScriptDetailsScriptResponseParameters(
            parameter_name='user_name',
            parameter_data_type='STRING'
        )
    ]
)

create_cmd = datap_models.CreateDataServiceApiRequestCreateCommand(
    project_id=22,
    api_name='query_user_info',
    api_type=3,           # 固定为 3（数据源SQL模式）
    mode=0,               # 0=Basic模式, 1=Dev-Prod模式
    call_mode=1,          # 1=同步
    request_type=1,       # 1=LIST（返回多条）
    biz_protocol=[0],     # [0]=HTTP
    version='1.0.0',      # 固定初始版本
    timeout=30000,        # 毫秒
    api_group_id=85,      # API 分组 ID（SDK 字段名）
    api_group_name='默认API分组',  # API 分组名称
    script_details=script_details
)

req = datap_models.CreateDataServiceApiRequest(
    op_tenant_id=300001413,
    create_command=create_cmd
)

resp = client.create_data_service_api_with_options(req, runtime)
print(resp.body.to_map())
# 成功时返回 ApiId
```

完整参数结构见 [CreateDataServiceApi 参数参考](./references/create-api-params.md)。

**SDK 安装：**
```bash
pip3 install alibabacloud-dataphin-public20230630
```

**响应处理：**
- 确认 `Code` 为 `OK`
- 提取 `ApiId`（小整数，如 10121）

### 步骤 4：发布 API

#### HITL 确认（写操作）

执行前确认：
- 要发布的 API：`{ApiName}`（ID: `{ApiId}`）
- 版本 ID：`{VersionId}`
- 影响范围：API 发布到生产环境，可被授权应用调用
- 可回滚：发布后可下线

**确认后执行：**

```bash
aliyun dataphin-public publish-data-service-api \
  --op-tenant-id "{OpTenantId}" \
  --api-id "{ApiId}" \
  --project-id "{ProjectId}" \
  --version-id "{VersionId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}"
```

**VersionId 说明：**
- `VersionId` 即创建 API 时指定的 `Version` 字符串（如 `"1.0.0"`），直接传入即可

### 步骤 5：验证发布结果

```bash
aliyun dataphin-public list-data-service-published-apis \
  --op-tenant-id "{OpTenantId}" \
  --project-id "{ProjectId}" \
  --list-query "PageNo=1 PageSize=50" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}"
```

**验证标准：**
- 在 `PageResult.ApiList` 中找到 `ApiId` 对应的记录
- 确认 `DeployTime` 非空（表示已发布）

## 9. Success Verification

采用三步验证法：

1. **同步返回检查**：`create-data-service-api` 返回 Code 为成功
2. **反查确认**：`list-data-service-published-apis`（需传 `--list-query` 分页参数）能查到已发布 API
3. **文档获取**（可选）：
```bash
aliyun dataphin-public get-data-service-api-document \
  --op-tenant-id "{OpTenantId}" \
  --id "{ApiId}" \
  --version-id "{VersionId}" \
  --endpoint <YOUR_DATAPHIN_ENDPOINT> \
  --user-agent "AlibabaCloud-Agent-Skills/create-and-publish-api/{SESSION_ID}"
```

## 10. Cleanup

如需清理测试创建的 API：

> 注意：当前 OpenAPI 可能不支持直接删除 API。如需清理，请通过 Dataphin 控制台操作。

## 11. Command Tables

| 命令 | 用途 | 类型 |
|------|------|------|
| `get-data-service-my-projects` | 查询我的项目 | 读 |
| `get-data-service-api-groups` | 查询 API 分组 | 读 |
| `create-data-service-api` | 创建 API | 写 |
| `publish-data-service-api` | 发布 API | 写 |
| `list-data-service-published-apis` | 查询已发布 API | 读 |
| `get-data-service-api-document` | 获取 API 文档 | 读 |

详见 [相关命令索引](./references/related-commands.md)。

## 12. Best Practices

- **大整数精度丢失（Critical）**：aliyun CLI 内部 JSON 解析使用 JavaScript Number，超过 2^53 的整数会精度丢失。DatasourceID 等大整数**必须使用 Python SDK** 传参，不可通过 CLI `--create-command` JSON 传入。
- **CLI 参数格式**：CLI 使用 kebab-case（如 `--op-tenant-id`），非 PascalCase（如 `--OpTenantId`）
- **ProjectId / GroupId / ApiId**：数据服务项目的 ID 是小整数（如 22/85/10121），非 snowflake ID
- **SQL 占位符**：使用 `${paramName}` 语法定义请求参数，如 `WHERE user_id = ${userId}`
- **默认分组**：如无特殊需求，可使用项目默认 API 分组
- **SDK ParameterDataType Bug**：SDK 中 `ParameterDataType` 定义为 int，但实际应为字符串枚举（"STRING"/"INT"/"LONG" 等），需 monkey-patch 或直接传字符串
- **独立部署 SSL**：独立部署环境自签名证书需 `runtime.ignore_ssl = True`
- **grant-data-service-api 限制**：APP 类型授权查询类 API 需 `ProdFieldList`（含字段 ID），但 OpenAPI 未提供获取字段 ID 的接口，仅前端 RESTful API `/api/dataService/api/queryApiColumns` 可查。如遇此限制，可改用 USER 类型授权（无需 ProdFieldList）
- **list-data-service-published-apis 需分页**：必须传 `--list-query "PageNo=1 PageSize=50"` 参数，否则返回空列表
- **环境 Endpoint**：
  - 管理面：`dataphin-openapi.<env>.aliyun.com`
  - 数据服务网关：`dataphin-os-gateway.<env>.aliyun.com`
