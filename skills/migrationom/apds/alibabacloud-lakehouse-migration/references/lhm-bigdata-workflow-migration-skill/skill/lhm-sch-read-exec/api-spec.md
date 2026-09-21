# LHM Inner API 接口规范

> 本文档基于 SDK `alibabacloud_lhm20250116_inner-1.2.501a0` 的 `models.py` 提取，字段定义与 SDK 完全一致。

## 1. PostInnerReader - 开始调度探查

### 请求 (PostInnerReaderRequest)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `data_source_name` | String | ✅ | 数据源名称（LHM 平台中已注册的源端数据源） | `"ds_dolphin_prod"` |
| `data_source_descriptor` | Object | ❌ | 数据源描述符（可选） | - |
| `data_source_descriptor.ds_name` | String | ❌ | 数据源描述符中的名称 | `"ds_dolphin_prod"` |

### 响应 (PostInnerReaderResponseBody)

```python
class PostInnerReaderResponseBody:
    data: str         # 响应数据（JSON 字符串，需 json.loads 解析）
    err_code: str     # 错误码（失败时非空）
    err_message: str  # 错误信息（失败时非空）
    request_id: str   # 请求唯一标识
    success: str      # "true" / "false"（字符串类型，非 bool）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | String | JSON 字符串，解析后包含探查任务启动结果。当 `errCode=E610R1002` 时，返回所有匹配的数据源列表 |
| `err_code` | String | 业务错误码，详见文末 **通用业务错误码** |
| `err_message` | String | 人类可读的错误描述 |
| `request_id` | String | 请求 ID |
| `success` | String | `"true"` 表示 API 调用成功，`"false"` 表示失败。**注意是字符串类型** |

---

## 2. GetInnerReadAsyncResult - 获取调度探查结果

### 请求 (GetInnerReadAsyncResultRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `data_source_name` | String | ✅ | 数据源名称（必须与 PostInnerReader 传入的一致） |

### 响应 (GetInnerReadAsyncResultResponseBody)

```python
class GetInnerReadAsyncResultResponseBody:
    data: str         # 探查结果或状态信息（JSON 字符串，需 json.loads 解析）
    err_code: str     # 错误码（失败时非空）
    err_message: str  # 错误信息（失败时非空）
    request_id: str   # 请求唯一标识
    success: str      # "true" / "false"（字符串类型，非 bool）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | String | JSON 字符串，解析后包含状态和结果内容。内部字段结构需根据实际返回值确认 |
| `err_code` | String | 业务错误码，详见文末 **通用业务错误码** |
| `err_message` | String | 人类可读的错误描述 |
| `request_id` | String | 请求 ID |
| `success` | String | `"true"` 表示 API 调用成功，`"false"` 表示失败。**注意是字符串类型** |

---

## 3. PostInnerConvert - 调度转换

### 请求 (PostInnerConvertRequest)

| 字段 | 类型 | 必填 | 说明 | 示例值 |
|------|------|------|------|--------|
| `src_data_source_name` | String | ✅ | 源数据源名称（与 PostInnerReader 的 dataSourceName 一致） | `"ds_dolphin_prod"` |
| `tgt_data_source_name` | String | ✅ | 目标数据源名称（LHM 平台中已注册的目标端数据源） | `"ds_dataworks_prod"` |
| `sql_convert_map` | Map<String, String> | ❌ | SQL 方言转换映射，key 为源 SQL 类型，value 为目标 SQL 类型 | `{"dolphin_sql": "dataworks_sql"}` |

### 响应 (PostInnerConvertResponseBody)

```python
class PostInnerConvertResponseBody:
    data: str         # 转换结果（JSON 字符串，需 json.loads 解析）
    err_code: str     # 错误码（失败时非空）
    err_message: str  # 错误信息（失败时非空）
    request_id: str   # 请求唯一标识
    success: str      # "true" / "false"（字符串类型，非 bool）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | String | JSON 字符串，解析后包含转换结果 |
| `err_code` | String | 业务错误码，详见文末 **通用业务错误码** |
| `err_message` | String | 人类可读的错误描述 |
| `request_id` | String | 请求 ID |
| `success` | String | `"true"` 表示成功，`"false"` 表示失败。**注意是字符串类型** |

---

## 4. GetInnerConvertAsyncResult - 获取调度转换结果

### 请求 (GetInnerConvertAsyncResultRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | String | ✅ | 转换任务 ID（由 PostInnerConvert 返回或业务方指定） |

### 响应 (GetInnerConvertAsyncResultResponseBody)

```python
class GetInnerConvertAsyncResultResponseBody:
    data: str         # 转换结果或状态信息（JSON 字符串，需 json.loads 解析）
    err_code: str     # 错误码（失败时非空）
    err_message: str  # 错误信息（失败时非空）
    request_id: str   # 请求唯一标识
    success: str      # "true" / "false"（字符串类型，非 bool）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | String | JSON 字符串，解析后包含转换任务的状态和结果内容 |
| `err_code` | String | 业务错误码，详见文末 **通用业务错误码** |
| `err_message` | String | 人类可读的错误描述 |
| `request_id` | String | 请求 ID |
| `success` | String | `"true"` 表示 API 调用成功，`"false"` 表示失败。**注意是字符串类型** |

---

## 通用注意事项

1.  **success 字段类型为 str**：所有响应的 `success` 均为字符串 `"true"`/`"false"`，判断时必须使用 `body.success == "true"`，不可直接用 `if body.success`。
2.  **data 字段为 JSON 字符串**：所有接口的 `data` 均为 str 类型，需 `json.loads(body.data)` 解析后使用。
3.  **request_id 字段**：所有响应均包含 `request_id` 字段，用于链路追踪和问题排查。
4.  **任务标识差异**：
    -   探查任务以 `dataSourceName` 为维度标识（PostInnerReader / GetInnerReadAsyncResult）
    -   转换任务以 `taskId` 为维度标识（GetInnerConvertAsyncResult），PostInnerConvert 通过 src/tgt dataSourceName 触发

## 通用业务错误码

以下错误码适用于所有四个接口（PostInnerReader / GetInnerReadAsyncResult / PostInnerConvert / GetInnerConvertAsyncResult）：

| errCode | 说明 | 备注 |
|---------|------|------|
| `200` | 成功 | 接口调用及业务处理均成功 |
| `E610R1001` | 数据源不存在 | 指定的 `dataSourceName` 在 LHM 平台中未注册 |
| `E610R1002` | 检索到多个数据源 | `data` 字段会返回所有匹配的数据源列表，需用户确认具体使用哪一个 |
| `E610R1003` | 未找到探查任务 | 下发指令前检索探查任务失败 |
| `E610R1004` | 探查任务正在进行中 | 当前数据源已有正在执行的探查任务，需等待完成或取消后重试 |
| `E610R1005` | 探查任务出现异常 | 探查任务执行过程中发生内部异常 |
| `E610R1006` | 创建探查任务失败 | 服务端创建任务记录失败 |
| `E610R1007` | 探查指令下发失败 | 向源端调度系统下发探查指令失败 |
| `E610R1008` | 探查完成结果是失败的 | 探查任务已完成但结果为失败状态 |
| `E610R1009` | 未执行过探查 | 该数据源尚未执行过探查操作 |
| `E610R1010` | 获取迁移源端调度的项目空间异常 | 无法获取源端调度系统的项目空间信息 |
| `E610R1011` | 调度迁移任务失败 | 调度迁移整体任务执行失败 |
| `E610R1012` | 下发节点转换指令失败 | 向目标端下发节点转换指令时失败 |
| `E610R1013` | 调度任务不存在 | 指定的调度任务在源端系统中不存在 |
| `E610R1014` | 查询探查记录失败或者从未执行过节点转换 | 无法获取探查记录或节点转换历史 |
| `E610R1015` | 节点转换异常中断 | 节点转换过程被异常中断 |
| `E610R1016` | 节点转换任务还在进行中 | 当前有正在执行的节点转换任务 |
| `E610R1017` | 获取工作流信息或者节点信息失败 | 无法从源端获取工作流或节点的详细信息 |
| `E610R1018` | 数据源联通测试失败 | 数据源连通性验证未通过，请检查网络、凭证或配置 |

## 通用错误响应

当 `success == "false"` 时，通过 `err_code` 和 `err_message` 获取错误详情。除上述业务错误码外，还可能返回以下系统级错误码：

- `INVALID_PARAM`：参数缺失或格式错误
- `AUTH_FAILED`：凭据无效
- `SOURCE_UNREACHABLE`：源端网络不通
- `INTERNAL_ERROR`：服务端异常
