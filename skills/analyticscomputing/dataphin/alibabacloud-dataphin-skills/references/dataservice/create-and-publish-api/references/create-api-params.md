# CreateDataServiceApi 完整参数参考

## CreateCommand JSON 结构（实际验证版）

```json
{
  "ProjectId": 22,
  "ApiName": "query_user_info",
  "ApiType": 3,
  "Mode": 0,
  "CallMode": 1,
  "RequestType": 0,
  "BizProtocol": [0],
  "Version": "1.0.0",
  "Timeout": 30000,
  "GroupId": 85,
  "ScriptDetails": {
    "DatasourceID": 7467470269897096832,
    "DatasourceType": 0,
    "SqlMode": 1,
    "Script": "SELECT user_id, user_name FROM user_info WHERE user_id = #{userId}",
    "ScriptRequestParameters": [
      {
        "ParameterName": "userId",
        "ParameterDataType": "STRING"
      }
    ],
    "ScriptResponseParameters": [
      {
        "ParameterName": "user_id",
        "ParameterDataType": "STRING"
      },
      {
        "ParameterName": "user_name",
        "ParameterDataType": "STRING"
      }
    ]
  }
}
```

## 顶层字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ProjectId | int | 是 | 数据服务项目 ID（小整数，如 22） |
| ApiName | string | 是 | API 名称 |
| ApiType | int | 是 | API 类型，**固定为 3**（当前仅支持 3） |
| Mode | int | 是 | API 模式：0=SQL / 1=向导 |
| CallMode | int | 是 | 调用模式：1=同步 / 2=异步 |
| RequestType | int | 是 | 请求类型，**固定为 0** |
| BizProtocol | int[] | 是 | 协议列表：[0]=HTTP |
| Version | string | 是 | 版本号，默认 "1.0.0" |
| Timeout | int | 是 | 超时时间（毫秒），默认 30000 |
| GroupId | int | 否 | API 分组 ID（小整数，如 85） |

## ScriptDetails 字段说明（SQL 模式必填）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| DatasourceID | long | 是 | 数据源 ID（19 位 snowflake，**必须用 Python SDK 传参**） |
| DatasourceType | int | 是 | 0=MySQL / 1=其他关系型 |
| SqlMode | int | 是 | SQL 模式，固定为 1 |
| Script | string | 是 | SQL 语句，使用 #{param} 占位符 |
| IsPaginated | bool | 否 | 是否分页查询 |
| SortPriority | int | 否 | 排序优先级 |
| ScriptRequestParameters | object[] | 是 | 请求参数列表 |
| ScriptResponseParameters | object[] | 是 | 返回参数列表 |

## ScriptRequestParameters / ScriptResponseParameters 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ParameterName | string | 是 | 参数名称 |
| ParameterDataType | string | 是 | 参数数据类型（字符串枚举，见下表） |

## ParameterDataType 枚举值

> **⚠️ SDK Bug**：SDK 中 `ParameterDataType` 定义为 int，但实际应为**字符串枚举**。
> 使用 Python SDK 时需直接传字符串值（如 `'STRING'`），而非数字。

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

## CLI vs SDK 参数名对照

| CLI 参数名（kebab-case） | SDK/JSON 字段名（PascalCase） |
|-------------------------|------------------------------|
| --op-tenant-id | OpTenantId |
| --create-command | CreateCommand |
| --api-id | ApiId |
| --project-id | ProjectId |
| --version-id | VersionId |

## Python SDK 代码示例

```python
import os
import urllib3
urllib3.disable_warnings()

from alibabacloud_dataphin_public20230630.client import Client
from alibabacloud_dataphin_public20230630 import models as datap_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# 1. 配置客户端
# UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入（继承自父 skill）
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
ua = 'AlibabaCloud-Agent-Skills/create-and-publish-api'
if SESSION_ID:
    ua = f'{ua}/{SESSION_ID}'

config = open_api_models.Config(
    access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
    access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
    endpoint='dataphin-openapi.{env}.aliyun.com',  # 替换为实际环境
    user_agent=ua
)
client = Client(config)
runtime = util_models.RuntimeOptions()
runtime.ignore_ssl = True  # 独立部署环境需忽略 SSL

# 2. 构建请求参数
script_details = datap_models.CreateDataServiceApiRequestCreateCommandScriptDetails(
    datasource_id=7467470269897096832,  # 大整数安全
    datasource_type=0,                  # MySQL
    sql_mode=1,
    script='SELECT user_id, user_name FROM user_info WHERE user_id = #{userId}',
    script_request_parameters=[
        datap_models.CreateDataServiceApiRequestCreateCommandScriptDetailsScriptRequestParameters(
            parameter_name='userId',
            parameter_data_type='STRING'  # 字符串枚举
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
    api_type=3,
    mode=0,
    call_mode=1,
    request_type=0,
    biz_protocol=[0],
    version='1.0.0',
    timeout=30000,
    group_id=85,
    script_details=script_details
)

req = datap_models.CreateDataServiceApiRequest(
    op_tenant_id=300001413,
    create_command=create_cmd
)

# 3. 发送请求
resp = client.create_data_service_api_with_options(req, runtime)
result = resp.body.to_map()
print(f"Code: {result.get('Code')}")
print(f"ApiId: {result.get('Data', {}).get('ApiId')}")
```

## SQL 占位符语法

使用 `#{paramName}` 定义请求参数：
```sql
SELECT * FROM users WHERE user_id = #{userId} AND dept_id = #{deptId}
```
系统自动将 `userId`、`deptId` 识别为请求参数。
`ScriptRequestParameters` 中必须显式声明每个参数的名称和类型。

## 注意事项

- **大整数精度丢失**：DatasourceID 是 19 位 snowflake ID，**不可通过 aliyun CLI 传参**（CLI 内部 JSON 解析使用 JavaScript Number，超过 2^53 精度丢失）。必须使用 Python SDK。
- **ProjectId / GroupId / ApiId 是小整数**：不是 snowflake ID，如 22、85、10121。
- **ApiType=3 是唯一支持值**：当前版本只支持类型 3。
- **ScriptResponseParameters 必须提供**：即使 SQL 能自动推断，也必须显式声明返回参数。
- **ParameterDataType 是字符串枚举**：SDK 类型定义为 int 是 bug，需传字符串值如 "STRING"、"INT"。
- **独立部署环境 SSL**：使用 `runtime.ignore_ssl = True` 绕过自签名证书验证。
