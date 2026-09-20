# LHM 调度数据源 CLI API 文档

> 本文档定义了 `lhm-sch-ds-cli` 工具所依赖的后端 API 接口规范，供开发者和 Agent 参考。

---

## 1. ListMetaDataComponentPage - 分页查询元数据组件（数据源）列表

### 接口说明
分页查询指定类型和名称的调度数据源元数据组件列表，用于获取已注册数据源的详细信息（包括配置、状态、版本等）。

### 请求参数 (Request)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `categoryType` | String | ✅ | 数据源分类类型，如 `"WORKFLOW"` | `"WORKFLOW"` |
| `dsName` | String | ✅ | 数据源名称（支持精确匹配或模糊匹配） | `"test_ds318_hangzhou_0428"` |
| `dsType` | String | ✅ | 数据源技术类型，如 `"DolphinScheduler"`, `"Airflow"` | `"DolphinScheduler"` |

### 响应参数 (Response)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | Boolean | 接口调用是否成功 |
| `totalCount` | Integer | 符合条件的总记录数 |
| `pageSize` | Integer | 每页返回的记录数 |
| `pageIndex` | Integer | 当前页码（从 1 开始） |
| `data` | Array\<Object\> | 数据源列表，每个元素为一个数据源对象 |
| `empty` | Boolean | 结果集是否为空 |
| `notEmpty` | Boolean | 结果集是否非空 |
| `totalPages` | Integer | 总页数 |

#### data 数组元素结构

| 字段 | 类型 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | 数据库主键 ID | `290` |
| `dsName` | String | 数据源名称 | `"test_ds318_hangzhou_0428"` |
| `dsType` | String | 数据源技术类型 | `"DolphinScheduler"` |
| `dsVersion` | String | 数据源版本号 | `"3.2.0"` |
| `dsConfig` | String | 数据源配置（**JSON 字符串**，需 `json.loads()` 解析） | `"{\"endpoint\":\"...\",\"token\":\"******\"}"` |
| `dsStatus` | Integer | 数据源状态码（`2`=正常, `-1`=待初始化） | `2` |
| `endType` | Integer | 端点类型标识 | `0` |
| `createTime` | String | 创建时间（格式：`YYYY-MM-DD HH:mm:ss`） | `"2026-04-28 14:26:47"` |
| `expired` | Boolean | 凭证/Token 是否已过期 | `false` |
| `dsId` | String | 数据源业务 ID（可能与 `id` 相同） | `"290"` |

### 使用注意

1.  **dsConfig 为 JSON 字符串**：与模板文件中的对象化结构不同，API 返回的 `dsConfig` 是序列化后的字符串，使用时需先 `json.loads(ds_info.ds_config)` 解析。
2.  **敏感信息脱敏**：`token` 等敏感字段在响应中会被脱敏（显示为 `******`），如需完整值需通过专用解密接口获取。
3.  **状态码含义**：`dsStatus=2` 表示数据源已激活且可用；`-1` 表示待初始化；其他值请参考平台文档。

### 调用示例（Python）

```python
import json
from alibabacloud_lhm20250116_inner.client import Client
from alibabacloud_lhm20250116_inner import models as lhm_models

request = lhm_models.ListMetaDataComponentPageRequest(
    category_type="WORKFLOW",
    ds_name="test_ds318_hangzhou_0428",
    ds_type="DolphinScheduler"
)
response = client.list_meta_data_component_page(request)
body = response.body

if body.success and body.not_empty:
    ds_info = body.data[0]
    config = json.loads(ds_info.ds_config)
    print(f"Endpoint: {config['endpoint']}")
    print(f"Project: {config['project']}")
    print(f"Status: {ds_info.ds_status}")
```

---

## 2. ExecMetaDataComponentName - 校验数据源名称可用性

### 接口说明
校验指定的数据源名称是否已被占用或符合命名规范，通常在创建新数据源前调用。

### 请求参数 (Request)

| 字段 | 类型 | 必填 | 传参方式 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dsName` | String | ✅ | Query Param | 待校验的数据源名称 | `"test_ds318_hangzhou_0428"` |

**请求示例**:
```
GET /api/meta/component/name?dsName=test_ds318_hangzhou_0428
```

### 响应参数 (Response)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | Boolean | 接口调用是否成功 |
| `requestId` | String | 请求唯一标识，用于链路追踪 |
| `data` | Boolean | 校验结果：`true` 表示名称已存在或不合法，`false` 表示名称可用/合法 |

### 使用注意

1.  **返回值语义**：`data=true` 仅表示名称通过校验（未被占用且格式合法），不代表数据源已创建成功。
2.  **调用时机**：建议在调用创建数据源接口前执行此校验，避免重复创建导致的错误。
3.  **无副作用**：该接口为只读查询，不会修改任何数据源状态。

### 调用示例（Python）

```python
from alibabacloud_lhm20250116_inner.client import Client
from alibabacloud_lhm20250116_inner import models as lhm_models

request = lhm_models.ExecMetaDataComponentNameRequest(ds_name="test_ds318_hangzhou_0428")
response = client.exec_meta_data_component_name(request)
body = response.body

if body.success and not body.data:
    print("✓ 数据源名称可用")
else:
    print("✗ 数据源名称不可用或已被占用")
```

---

## 3. AddMetaDataComponent - 创建调度数据源

### 接口说明
创建一个新的调度数据源元数据组件，支持 Airflow、DolphinScheduler 等多种调度系统类型。

### 请求参数 (Request)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `dsName` | String | ✅ | 数据源唯一标识名称 | `"21313"` |
| `categoryType` | String | ✅ | 数据源分类类型，如 `"WORKFLOW"` | `"WORKFLOW"` |
| `dsType` | String | ✅ | 数据源技术类型，如 `"DolphinScheduler"`, `"Airflow"` | `"DolphinScheduler"` |
| `dsConfig` | String | ✅ | 数据源配置（**JSON 字符串**，需将对象序列化后传入） | `"{\"dsVersion\":\"3.2.0\",\"operator\":\"auto\",...}"` |
| `dsStatus` | Integer | ❌ | 初始状态码，通常设为 `0` 或 `-1` | `0` |

#### dsConfig 子字段（以 DolphinScheduler 为例）

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `dsVersion` | String | ✅ | 调度系统版本号 | `"3.2.0"` |
| `operator` | String | ✅ | 操作模式：`"auto"` 或 `"manual"` | `"auto"` |
| `endpoint` | String | ✅ (auto模式) | 调度系统 API 地址 | `"https://..."` |
| `token` | String | ✅ (auto模式) | 认证 Token | `"token123"` |
| `source-file-path` | String | ❌ | 调度包文件路径（manual 模式使用） | `null` |

> **注意**：`dsConfig` 的具体字段因 `dsType` 而异，请参考对应类型的模板文件。

### 响应参数 (Response)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | Boolean | 接口调用是否成功 |
| `requestId` | String | 请求唯一标识，用于链路追踪 |
| `data` | Integer | 新创建的数据源 ID |

### 使用注意

1.  **前置校验**：建议先调用 `ExecMetaDataComponentName` 确认 `dsName` 可用后再创建。
2.  **dsConfig 结构**：必须与 `dsType` 匹配，错误结构会导致创建失败。
3.  **返回值**：`data` 返回的是新创建记录的主键 ID，可用于后续更新或删除操作。
4.  **幂等性**：该接口非幂等，重复调用相同 `dsName` 会报错（除非后端做了去重处理）。

### 调用示例（Python）

```python
import json
from alibabacloud_lhm20250116_inner.client import Client
from alibabacloud_lhm20250116_inner import models as lhm_models

# dsConfig 需序列化为 JSON 字符串
ds_config_obj = {
    "dsVersion": "3.2.0",
    "operator": "auto",
    "endpoint": "https://...",
    "token": "token123",
    "source-file-path": None
}

request = lhm_models.AddMetaDataComponentRequest(
    ds_name="21313",
    category_type="WORKFLOW",
    ds_type="DolphinScheduler",
    ds_config=json.dumps(ds_config_obj),  # 序列化为 JSON 字符串
    ds_status=0
)
response = client.add_meta_data_component(request)
body = response.body

if body.success:
    print(f"✓ 数据源创建成功，ID: {body.data}")
else:
    print(f"✗ 创建失败: {body.err_message}")
```

---

## 4. 数据源模板文件说明

本目录下提供以下数据源模板文件，用于 CLI 创建/更新操作：

| 文件名 | 适用类型 | 说明 |
| :--- | :--- | :--- |
| `airflow-datasource-template.json` | Airflow | Airflow 调度数据源入参模板，`dsConfig` 已对象化 |
| `dolphinscheduler-datasource-template.json` | DolphinScheduler | DolphinScheduler 调度数据源入参模板，`dsConfig` 已对象化 |

### 模板使用注意

-   模板文件中 `dsConfig` 为**原生对象结构**，便于阅读和编辑。
-   实际调用 API 时，SDK 会自动将 `dsConfig` 对象序列化为 JSON 字符串。
-   模板中的占位符（如 `"数据源名称"`、`"文件路径"`）需替换为实际值后使用。
-   详细字段说明请参考各模板同目录下的 README 文档。

---

## 3. 相关文档

-   [LHM Scheduler Inner API SKILL.md](../migration-sdm-lhm-scheduler-inner/SKILL.md)
-   [Inner API 接口规范](../migration-sdm-lhm-scheduler-inner/api-spec.md)
-   [Airflow 模板说明](./README-airflow-template.md)

---

## 5. ExecWorkflowConnectivity - 校验调度数据源连通性

### 接口说明
校验指定调度数据源的连通性，验证配置的 endpoint、token 等信息是否有效且可访问。通常在创建或更新数据源后调用，确保配置正确。

### 请求参数 (Request)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `dsName` | String | ✅ | 数据源名称 | `"12313"` |
| `dsConfig` | String | ✅ | 数据源配置（**JSON 字符串**） | `"{\"dsVersion\":\"2.0.0\",\"endpoint\":\"123\",...}"` |
| `dsType` | String | ✅ | 数据源技术类型 | `"DolphinScheduler"` |
| `dsVersion` | String | ✅ | 数据源版本号 | `"2.0.0"` |
| `id` | Integer | ❌ | 数据源 ID（可选，用于关联已有记录） | `310` |

#### dsConfig 子字段（以 DolphinScheduler 为例）

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| `dsVersion` | String | ✅ | 调度系统版本号 | `"2.0.0"` |
| `endpoint` | String | ✅ | 调度系统 API 地址 | `"https://..."` |
| `encryptIv` | String | ❌ | 加密向量（如使用加密 token） | `"M3gAeZqnR55pNQk2tXfzG3OKOKhH3bgqRzNY62OR3cs="` |
| `operator` | String | ✅ | 操作模式：`"auto"` 或 `"manual"` | `"auto"` |
| `token` | String | ✅ | 认证 Token（可能脱敏显示为 `******`） | `"******"` |

### 响应参数 (Response)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | Boolean | **连通性校验结果**：`true` 表示连通成功，`false` 表示失败 |
| `errCode` | String | 错误码（仅当 `success=false` 时返回） |
| `errMessage` | String | 错误信息（仅当 `success=false` 时返回） |
| `requestId` | String | 请求唯一标识，用于链路追踪 |

### 使用注意

1.  **返回值语义**：`success=true` 明确表示数据源连通性校验通过；`success=false` 表示连接失败，需检查 `errCode` 和 `errMessage` 定位问题。
2.  **常见错误**：`Target host is not specified` 通常表示 `endpoint` 配置为空或格式不正确。
3.  **敏感信息**：`token` 在请求中可能需要完整值，但响应中不会返回敏感信息。
4.  **调用时机**：建议在 `AddMetaDataComponent` 创建数据源后，或修改 `dsConfig` 后调用此接口验证配置有效性。

### 调用示例（Python）

```python
import json
from alibabacloud_lhm20250116_inner.client import Client
from alibabacloud_lhm20250116_inner import models as lhm_models

# dsConfig 需序列化为 JSON 字符串
ds_config_obj = {
    "dsVersion": "2.0.0",
    "endpoint": "https://example.com/api",
    "encryptIv": "M3gAeZqnR55pNQk2tXfzG3OKOKhH3bgqRzNY62OR3cs=",
    "operator": "auto",
    "token": "your_actual_token"
}

request = lhm_models.ExecWorkflowConnectivityRequest(
    ds_name="12313",
    ds_config=json.dumps(ds_config_obj),
    ds_type="DolphinScheduler",
    ds_version="2.0.0",
    id=310
)
response = client.exec_workflow_connectivity(request)
body = response.body

if body.success:
    print("✓ 数据源连通性校验成功")
else:
    print(f"✗ 连通性校验失败: [{body.err_code}] {body.err_message}")
```

---

## 6. GetMetaOssTempKey - 获取元数据 OSS 临时访问凭证

### 接口说明
获取用于上传/下载元数据文件的 OSS 临时访问凭证（STS Token），包括 AccessKey、SecurityToken、签名策略等信息。该凭证具有时效性和目录级权限控制，适用于向指定 OSS 路径上传调度元数据文件。

### 请求参数 (Request)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- | :--- |
| （无显式入参） | - | - | 接口通常基于当前用户上下文自动关联租户/项目信息 | - |

> **注意**：具体入参可能因后端实现而异，建议参考 SDK 定义或实际调用日志确认。

### 响应参数 (Response)

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `success` | Boolean | 接口调用是否成功 |
| `data` | Object | OSS 临时凭证对象 |

#### data 对象结构

| 字段 | 类型 | 说明 | 示例值 |
| :--- | :--- | :--- | :--- |
| `ak` | String | 临时 AccessKey ID（STS Token） | `"STS.NY6bbCNqNPpt5GcSTEzB6Lahn"` |
| `endpoint` | String | OSS Bucket 所在区域的 Endpoint | `"oss-cn-hangzhou.aliyuncs.com"` |
| `bucket` | String | OSS Bucket 名称 | `"lhm-pre-cn-hangzhou"` |
| `policy` | String | Base64 编码的上传策略（限定文件大小、路径前缀等） | `"eyJleH..."` |
| `signature` | String | 基于 policy 计算的签名，用于服务端验证请求合法性 | `"ydDYrWUzfKNM6slVhjPhUx83qUo="` |
| `expire` | Integer | 凭证过期时间戳（Unix 秒级） | `1779966540` |
| `dir` | String | 允许上传的 OSS 目录前缀（必须以 `/` 结尾） | `"teleport/meta/1063934947625635/"` |
| `securityToken` | String | STS SecurityToken，与 ak 配合使用进行身份认证 | `"CAIS3QJ1q6Ft5B2yfSjIr5qDKdj3o65v..."` |

### 使用注意

1.  **凭证时效性**：`expire` 字段表示凭证的绝对过期时间（Unix 时间戳），使用前应检查当前时间是否已过期，过期需重新获取。
2.  **目录限制**：`dir` 字段限定了可上传的路径前缀，上传时 Key 必须以此前缀开头，否则会被 OSS 拒绝。
3.  **Policy 解码**：`policy` 为 Base64 编码的 JSON 字符串，解码后可查看具体的上传约束（如文件大小上限、允许的 Key 前缀等）。
4.  **安全存储**：`securityToken` 和 `ak` 属于敏感凭证，禁止硬编码或打印到日志中，建议使用环境变量或密钥管理服务暂存。
5.  **OSS 客户端初始化**：使用阿里云 OSS SDK 时，需同时传入 `ak`、`securityToken` 和 `endpoint` 初始化 StsAuth 或 CredentialsProvider。

### 调用示例（Python）

```python
import base64
import json
import time
from alibabacloud_lhm20250116_inner.client import Client
from alibabacloud_lhm20250116_inner import models as lhm_models

request = lhm_models.GetMetaOssTempKeyRequest()
response = client.get_meta_oss_temp_key(request)
body = response.body

if body.success and body.data:
    oss_cred = body.data
    
    # 检查凭证是否过期
    if time.time() > oss_cred.expire:
        print("✗ OSS 临时凭证已过期，请重新获取")
    else:
        print(f"✓ 获取 OSS 临时凭证成功")
        print(f"  Bucket: {oss_cred.bucket}")
        print(f"  Endpoint: {oss_cred.endpoint}")
        print(f"  Dir Prefix: {oss_cred.dir}")
        print(f"  Expire At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oss_cred.expire))}")
        
        # 解码 policy 查看上传约束
        policy_json = json.loads(base64.b64decode(oss_cred.policy).decode('utf-8'))
        print(f"  Policy Conditions: {json.dumps(policy_json['conditions'], indent=2)}")
        
        # 使用凭证初始化 OSS 客户端（示例）
        # from oss2 import StsAuth, Bucket
        # auth = StsAuth(oss_cred.ak, oss_cred.security_token, oss_cred.security_token)
        # bucket = Bucket(auth, oss_cred.endpoint, oss_cred.bucket)
else:
    print(f"✗ 获取 OSS 临时凭证失败")
```

### OSS File Upload Example (curl)

获取临时凭证后，可使用以下 curl 命令向 OSS 上传元数据文件。该请求使用 `multipart/form-data` 格式，包含凭证字段和文件内容：

```bash
curl 'https://lhm-pre-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/' \
  --connect-timeout 10 --max-time 600 \
  -H 'Accept: */*' \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundary06GXcPBjixLoLBNc' \
  --data-raw $'------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="key"\r\n\r\nteleport/meta/1063934947625635/20260528190758_legao.zip\r\n------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="policy"\r\n\r\neyJleHBpcmF0aW9uIjoiMjAyNi0wNS0yOFQxMToxMjo1OC43MzZaIiwiY29uZGl0aW9ucyI6W1siY29udGVudC1sZW5ndGgtcmFuZ2UiLDAsMTA0ODU3NjAwXSxbInN0YXJ0cy13aXRoIiwiJGtleSIsInRlbGVwb3J0L21ldGEvMTA2MzkzNDk0NzYyNTYzNS8iXV19\r\n------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="OSSAccessKeyId"\r\n\r\nSTS.NYYKRZmx9BHNK5pqaPhRy25Qa\r\n------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="signature"\r\n\r\n9ZhL7nFcwnvbc4DK3/cxBVCms44=\r\n------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="x-oss-security-token"\r\n\r\nCAIS3QJ1q6Ft5B2yfSjIr5rsAOjugKcY9YqlSRPBlWEFZN1V3fD6gzz2IHhMfHFvA+kYv/k2nGBQ6/YYlrtXa7p/QkjJVsZr9ZVQ9yWoZoeZVV8sejJf2vOfAmG2J0PR/q27OpfULr70fvOqdCq39Etayqf7cjOPRkGsNYbz57dsctUQWHvTD1MEfqA0QDFvs8gHL3DcGO+wOxrx+ArqAVFvpxB3hBEUi8394LXFsEKD3Qajlr9J+9+teMX1VaQ2YscjCeXS9fdta6/M3BRX7xV376pshMRGg2yf5onFXAMIvUTbarKEqoA/dhUOYqg/HLVfpuX3lvBkoOvXmpztxlNGO6RVWiLQVoCn3dt/7ggvwifDH1ySGQMusrjnXvGd22uvYYFPubgRcJOnpivF7bD41vM+vpXmmTbEK06oIMPO+9pNiuFe9Hbz1oGhRGPiLfjnl0hRVPAyB8cEGPhItQSJGoABGEvINQNhWU1XoGIG3mkVicQG1rbqfFN5mcxYbS0b2HyOvhzlj7VtT1XgZ7CRs3iKtVIl+q7Xv5IV2da9dyhOrZzKFdr/+GsrVfokEi//qDXnhD62DcnSzKRdxZ4I8XxyC/Six9wP95OKuEGWTZlKZriHNIwlhd+Lqcb7ac8ydXUgAA==\r\n------WebKitFormBoundary06GXcPBjixLoLBNc\r\nContent-Disposition: form-data; name="file"; filename="legao.zip"\r\nContent-Type: application/zip\r\n\r\n\r\n------WebKitFormBoundary06GXcPBjixLoLBNc--\r\n'
```

#### 表单字段说明

| 字段名 | 值来源 | 说明 |
| :--- | :--- | :--- |
| `key` | 拼接 `dir` + 文件名 | OSS 对象完整路径，必须以 `GetMetaOssTempKey` 返回的 `dir` 为前缀 |
| `policy` | `GetMetaOssTempKey.data.policy` | Base64 编码的上传策略，服务端校验用 |
| `OSSAccessKeyId` | `GetMetaOssTempKey.data.ak` | 临时 AccessKey ID |
| `signature` | `GetMetaOssTempKey.data.signature` | 基于 policy 计算的签名 |
| `x-oss-security-token` | `GetMetaOssTempKey.data.securityToken` | STS SecurityToken |
| `file` | 本地文件 | 待上传的元数据文件（如 `.zip`、`.json`） |

> **注意**：实际使用时需将示例中的凭证值替换为 `GetMetaOssTempKey` 接口返回的最新值，并确保 `key` 字段以返回的 `dir` 为前缀。
