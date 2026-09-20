# 数据校验接口参考（网络层：aliyun CLI）

## 概述

本文档整理了 LHM 数据校验相关的全部接口，覆盖从任务创建到查看报告的完整生命周期。网络层通过 aliyun CLI（aliyun-cli-lhm 插件）调用，`scripts/common.py` 的 `AliyunCliClient` 将下列 snake_case 方法名自动映射为插件命令（如 `add_data_check_task` → `aliyun lhm add-data-check-task`）。

- **客户端构建**：`from common import build_client`；`client = build_client()`（返回 `AliyunCliClient`）
- **模型导入**：`from alibabacloud_lhm20250116 import models as lhm_models`（request 模型由内置 `sdk/` 目录提供，仅用于参数序列化，不发起网络请求）

## SDK 覆盖状态

| 状态 | 含义 |
|------|------|
| ✅ | SDK 已实现，可直接调用 |

## 通用约定

### 1. 客户端初始化

```python
import sys, os
sys.path.insert(0, os.path.join('<skill-root>', 'scripts'))
from common import build_client

client = build_client()  # endpoint/region 优先取 credentials.json 的 lhm 段，凭证由默认凭证链解析；可传 region='singapore' 显式覆盖 region
```

> 底层等价于：`AliyunCliClient(endpoint, region_id)`，每次方法调用通过 subprocess 执行 `aliyun lhm <command> --api-version 2025-01-16 --endpoint <lhm.endpoint> --region <lhm.region_id> --<flag> <value>`；`--endpoint` / `--region` 为固定参数，优先来源于 credentials.json 的 `lhm` 段（`lhm.endpoint` / `lhm.region_id`），缺失时回退环境变量（`LHM_ENDPOINT` / `REGION_ID`）与内置默认值；凭证由 aliyun CLI 默认凭证链解析，不落 argv。

### 2. 统一响应格式

所有 SDK 方法返回 `*Response` 对象，通过 `.body` 访问核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.success` | bool | 是否成功 |
| `resp.body.err_code` | str \| None | 错误码（成功时为 None） |
| `resp.body.err_message` | str \| None | 错误描述（成功时为 None） |
| `resp.body.request_id` | str | 请求追踪 ID |
| `resp.body.data` | T | 业务数据（类型因接口而异） |

> **字段命名**：Python SDK 统一使用 **snake_case**（如 `err_message` 而非 `errMessage`，`task_id` 而非 `taskId`）。

### 3. 状态枚举速查

| 字段 | 含义 | 取值 |
|------|------|------|
| `check_type` | 校验类型 | 0-数据量比对 / 1-指标比对 / 2-弱内容对比 |
| `task_mode` | 任务创建方式 | 0-逐表精细化 / 1-同模式批量 |
| `execute_type` | 执行类型 | 0-立即执行 / 1-定时执行 |
| `exec_status` | 批次执行状态 | 0-待运行 / 1-运行中 / 2-终止运行 / 3-运行失败 / 4-运行完成 |
| `job_status` / `status` | 作业/Step 状态 | 0-INIT / 1-RUNNING / 2-FINISHED / 3-STOPPED / 4-FAIL / 6-READY / 7-SKIPPED |
| `check_result` | 校验结果 | 0-无记录 / 1-通过 / 2-不通过 |
| `is_consistent` | 是否一致 | 0-不一致 / 1-一致 / 2-人工修复 |
| `report_status` | 报告生成状态 | 0-未生成 / 1-生成中 / 2-已生成 / 3-生成失败 |

---

## 流程图

```
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ Step 1: 创建任务       │────▶│ Step 2: 保存批次       │────▶│ Step 3: 执行校验       │
│ add_data_check_task  │     │exec_data_check_save  │     │ exec_data_check_run  │
│        ✅            │     │      ✅              │     │       ✅             │
└──────────────────────┘     └──────────────────────┘     └────────┬─────────────┘
         │                         │                                │
         │ (可选)                  │ start_immediately=1            │
         ▼                         │ 跳过 Step 3                    │
┌──────────────────────┐           └────────────────────────────────┤
│ Step 1.1 单表配置     │                                           │
│add_data_check_config │                                           │
│       ✅             │                                           │
└──────────────────────┘                                           │
                                                                   │
                                                      ┌────────────▼────────────┐
                                                      │  Step 4: 查询执行状态     │
                                                      │list_data_check_task_    │
                                                      │      history ✅         │
                                                      └───────────┬─────────────┘
                                                                  │
                                                      ┌───────────▼─────────────┐
                                                      │   running? 终止任务?     │
                                                      │ exec_data_check_stop ✅ │
                                                      └───────────┬─────────────┘
                                                                  │ done (exec_status=4)
                                                      ┌───────────▼─────────────┐
                                                      │  Step 5: 报告列表        │
                                                      │list_data_check_report ✅│
                                                      └───────────┬─────────────┘
                                                                  │
   ┌────────────────────────┬─────────────────┬──────────────────┴─────────────────┐
   ▼                        ▼                 ▼                                     ▼
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐               ┌──────────────────┐
│ 5.1 概览     │   │ 5.2 字段      │   │ 5.3 Step概览      │               │ 5.4 Step明细      │
│get_data_    │   │list_data_    │   │get_step_result_  │               │list_data_check_  │
│check_report │   │check_column  │   │   overview       │               │ report_step      │
│_overview ✅ │   │_results ✅   │   │      ✅          │               │      ✅          │
└─────────────┘   └──────────────┘   └──────────────────┘               └──────────────────┘
```

---

## 核心流程接口

### 核心流程（7 个接口）

| 步骤 | SDK 方法 | 状态 | 说明 |
|------|---------|------|------|
| 1 | `add_data_check_task` | ✅ | 创建校验任务 |
| 1.1 | `add_data_check_config` | ✅ | 保存单表校验配置（可选） |
| 2 | `exec_data_check_save_task` | ✅ | 保存批次配置（含表映射） |
| 3 | `exec_data_check_run` | ✅ | 执行校验 |
| 4 | `list_data_check_task_history` | ✅ | 查询执行状态 |
| 4.1 | `exec_data_check_stop` | ✅ | 终止正在执行的任务（可选） |
| 5 | `list_data_check_report` | ✅ | 查看校验报告列表 |

### 报告深度查看（4 个扩展接口，可选）

| 步骤 | SDK 方法 | 状态 | 说明 |
|------|---------|------|------|
| 5.1 | `get_data_check_report_overview` | ✅ | 批次级汇总概览 |
| 5.2 | `list_data_check_column_results` | ✅ | 字段维度明细 |
| 5.3 | `get_step_result_overview` | ✅ | Step 结果概览 |
| 5.4 | `list_data_check_report_step` | ✅ | Step 维度明细列表 |

> **极简模式**：`exec_data_check_save_task` 支持 `start_immediately=1`，可省略 Step 3，此时仅需 **5 个接口**即可完成全流程。

---

## Step 1: 创建校验任务

### `client.add_data_check_task(request)` ✅

创建校验任务外壳，定义源端/目标端数据源和校验类型。

**请求类**：`lhm_models.AddDataCheckTaskRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_name | str | 是 | 任务名称（**仅允许**英文字母、中文字符、数字；`[]`、`-`、`:`、空格等特殊字符**均不允许**，违反则报 E500R103） |
| check_type | int | 是 | 校验类型：0-数据量 1-指标 2-弱内容 |
| task_mode | int | 是 | 创建方式：0-逐表精细化 1-同模式批量 |
| src_ds_id | str | 是 | 源端数据源 ID |
| src_ds_name | str | 否 | 源端数据源名称 |
| src_ds_type | str | 是 | 源端数据源类型（如 MySQL、Hive） |
| dst_ds_id | str | 是 | 目标端数据源 ID |
| dst_ds_name | str | 否 | 目标端数据源名称 |
| dst_ds_type | str | 是 | 目标端数据源类型 |
| check_template_id | str | 否 | 校验模板 ID（指标校验时使用） |

**请求示例：**

```python
request = lhm_models.AddDataCheckTaskRequest(
    task_name='订单表数据量校验',
    check_type=0,
    task_mode=0,
    src_ds_id='ds-001',
    src_ds_name='源端MySQL',
    src_ds_type='MySQL',
    dst_ds_id='ds-002',
    dst_ds_name='目标端Hive',
    dst_ds_type='Hive',
)
resp = client.add_data_check_task(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | int | 任务 ID（task_id） |

**响应示例：**

```python
# resp.body.success   → True
# resp.body.data      → 10001
# resp.body.request_id → '5982CC7C-680B-1511-AA18-40DF21024C1C'
```

> 返回的 `data` 为 task_id，后续步骤引用。

---

## Step 1.1: 保存单表校验配置（可选）

### `client.add_data_check_config(request)` ✅

对单张表进行精细化校验配置（where 条件、分区、字段选择、自定义 SQL 等）。可多次调用逐表添加。

**请求类**：`lhm_models.AddDataCheckConfigRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | int | 是 | 任务 ID（Step 1 返回值） |
| source_table | str | 否 | 源端表名（格式：schema.table） |
| target_table | str | 否 | 目标端表名（格式：schema.table） |
| source_partition | str | 否 | 源端分区条件 |
| target_partition | str | 否 | 目标端分区条件 |
| source_columns | str | 否 | 源端校验字段（逗号分隔，空=全部） |
| target_columns | str | 否 | 目标端校验字段 |
| source_where_clause | str | 否 | 源端 WHERE 条件 |
| target_where_clause | str | 否 | 目标端 WHERE 条件 |
| source_group_clause | str | 否 | 源端 GROUP BY 条件 |
| target_group_clause | str | 否 | 目标端 GROUP BY 条件 |
| source_hint | str | 否 | 源端 Hint |
| target_hint | str | 否 | 目标端 Hint |
| total_count_threshold | float | 否 | 总数据量对比阈值 |
| is_full_table_count | int | 否 | 是否整表校验：0-分区为单位 1-整表。**注意：MaxCompute 分区表设为 1 会触发 ODPS-0130071（full scan 限制），必须设为 0 并指定 source_partition/target_partition，或在 save 时设置 `source_global_params='odps.sql.allow.fullscan=true'`** |
| task_config_info | str | 否 | 批量模式配置（格式：srcSchema\|dstSchema\|tablePattern，多条用 \n 分割） |

**请求示例：**

```python
request = lhm_models.AddDataCheckConfigRequest(
    task_id=10001,
    source_table='source_db.orders',
    target_table='target_db.orders',
    source_partition='date_part=20240305',
    target_partition='date_part=20240305',
    total_count_threshold=100.0,
    is_full_table_count=0,
)
resp = client.add_data_check_config(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | int | 配置 ID（config_id） |

**响应示例：**

```python
# resp.body.success → True
# resp.body.data    → 50001
```

---

## Step 2: 保存批次配置

### `client.exec_data_check_save_task(request)` ✅

保存任务的执行配置，包括容忍度、全局参数等。**核心配置接口。**

> **注意**：批量匹配规则（`task_config_info`）应通过 `add_data_check_config` 接口配置，不在此接口传入。

**请求类**：`lhm_models.ExecDataCheckSaveTaskRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | int | 是 | 任务 ID（Step 1 返回值） |
| full_table_count | int | 否 | 是否整表校验：0-分区为单位（默认） 1-整表 |
| total_count_threshold | float | 否 | 全局对比阈值 |
| start_immediately | int | 否 | 是否立即执行：0-否（默认） 1-是（可省略 Step 3） |
| source_global_params | str | 否 | **源端数据源的 SQL 执行系统参数**（如 `odps.sql.allow.fullscan=true`），多个参数用 `\n` 分割。这些参数在源端执行 SQL 时生效，不是平台规则参数 |
| target_global_params | str | 否 | **目标端数据源的 SQL 执行系统参数**，多个参数用 `\n` 分割。这些参数在目标端执行 SQL 时生效，不是平台规则参数 |
| check_global_params | str | 否 | **平台任务执行规则参数**（非数据源 SQL 参数），多个参数用 `\n` 分割 |

**请求示例：**

```python
# 示例1: 单参数（Hive 源端）
request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=10001,
    total_count_threshold=0.0,
    start_immediately=1,
    source_global_params='hive.compute.query.using.stats=false',
)
resp = client.exec_data_check_save_task(request)

# 示例2: MaxCompute 源端 + 目标端，多个参数用 \n 分割
request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=10002,
    total_count_threshold=0.0,
    start_immediately=1,
    source_global_params='odps.sql.allow.fullscan=true\nodps.sql.mapper.split.size=256',
    target_global_params='odps.sql.allow.fullscan=true',
)
resp = client.exec_data_check_save_task(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | int | 批次 ID（batch_id） |

**响应示例：**

```python
# resp.body.success → True
# resp.body.data    → 20001
```

> 若设置 `start_immediately=1`，可跳过 Step 3 直接执行。

---

## Step 3: 执行校验

### `client.exec_data_check_run(request)` ✅

触发校验任务执行。若 Step 2 设置了 `start_immediately=1` 则无需调用。

**请求类**：`lhm_models.ExecDataCheckRunRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| batch_id | int | **是** | 批次 ID（Step 2 返回值）。**注意：虽然 api.yaml 未标记 required，但后端实现直接调用 `getBatchId()`，不传会报错** |

**请求示例：**

```python
request = lhm_models.ExecDataCheckRunRequest(batch_id=20001)
resp = client.exec_data_check_run(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | None | 无返回数据 |

---

## Step 4: 查询执行状态

### `client.list_data_check_task_history(request)` ✅

轮询查看任务执行状态，直到批次完成（`exec_status=4`）。

**请求类**：`lhm_models.ListDataCheckTaskHistoryRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| batch_id | int | 是 | 批次 ID（精确查询） |
| task_id | int | 否 | 任务 ID |
| exec_status | int | 否 | 执行状态过滤 |
| check_result | int | 否 | 校验结果过滤 |
| create_start_time | str | 否 | 创建时间范围起点（YYYY-MM-DD HH:MM:SS） |
| create_end_time | str | 否 | 创建时间范围终点（YYYY-MM-DD HH:MM:SS） |
| exec_start_time | str | 否 | 执行开始时间范围起点 |
| exec_end_time | str | 否 | 执行开始时间范围终点 |
| finish_start_time | str | 否 | 执行结束时间范围起点 |
| finish_end_time | str | 否 | 执行结束时间范围终点 |
| page_index | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页大小（默认 10） |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | list | 分页列表 |
| `.data[i].batch_id` | int | 批次 ID |
| `.data[i].exec_status` | int | 执行状态：0-待运行 1-运行中 2-终止 3-失败 4-完成 |
| `.data[i].check_result` | int | 校验结果：0-无记录 1-通过 2-不通过 |
| `.data[i].check_table_num` | int | 校验表总数 |
| `.data[i].error_table_num` | int | 异常表数 |
| `.data[i].successful_table_num` | int | 成功表数 |
| `.data[i].skip_table_num` | int | 跳过表数 |
| `.data[i].progress` | float | 执行进度（0-1） |
| `.data[i].pass_process` | float | 通过率（0-100） |
| `.data[i].start_time` | str | 开始时间 |
| `.data[i].end_time` | str | 结束时间 |
| `.data[i].exec_time` | str | 执行耗时 |
| `.data[i].report_title` | str | 报告标题 |

---

## Step 4.1: 终止任务（可选）

### `client.exec_data_check_stop(request)` ✅

终止运行中的批次（`exec_status=1`）。终止后 `exec_status` 变为 `2`。

**请求类**：`lhm_models.ExecDataCheckStopRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| batch_id | int | **是** | 批次 ID。**注意：虽然 api.yaml 未标记 required，但后端实现直接调用 `getBatchId()`，不传会报错** |

**请求示例：**

```python
request = lhm_models.ExecDataCheckStopRequest(batch_id=20001)
resp = client.exec_data_check_stop(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | None | 无返回数据 |

> **仅 `exec_status=1`（运行中）可终止**，其他状态调用会返回错误。

---

## Step 5: 查看校验报告

### `client.list_data_check_report(request)` ✅

查看每张表的校验结果详情，返回 job_id 用于后续明细查询。

**请求类**：`lhm_models.ListDataCheckReportRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| batch_id | int | 是 | 批次 ID |
| job_status | int | 否 | Job 状态过滤 |
| check_result | int | 否 | 校验结果过滤：0-无记录 1-通过 2-不通过 |
| table_name | str | 否 | 表名模糊搜索 |
| page_index | int | 否 | 页码 |
| page_size | int | 否 | 每页大小 |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data` | list | 分页列表 |
| `.data[i].batch_id` | int | 批次 ID |
| `.data[i].job_id` | str | 作业 ID 字符串 |
| `.data[i].result_id` | str | 校验结果 ID |
| `.data[i].job_status` | int | 作业状态 |
| `.data[i].check_result` | int | 校验结果：0-无记录 1-通过 2-不通过 |
| `.data[i].is_skipped` | int | 是否跳过 |
| `.data[i].source_table` | str | 源端表名 |
| `.data[i].target_table` | str | 目标端表名 |
| `.data[i].source_count` | str | 源端行数 |
| `.data[i].target_count` | str | 目标端行数 |
| `.data[i].real_diff_count` | int | 实际差异数 |
| `.data[i].diff_rate` | str | 差异率 |
| `.data[i].source_partition` | str | 源端分区 |
| `.data[i].target_partition` | str | 目标端分区 |
| `.data[i].error_msg` | str | 错误信息 |
| `.data[i].exec_time` | str | 执行时长 |
| `.data[i].finish_time` | str | 完成时间 |
| `.data[i].template_name` | str | 校验模板名称 |

---

## Step 5.1: 报告概览（可选）

### `client.get_data_check_report_overview(request)` ✅

查询批次级别的汇总概览信息（通过率、通过/异常/跳过表数等）。

**请求类**：`lhm_models.GetDataCheckReportOverviewRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| batch_id | int | 是 | 批次 ID |

**请求示例：**

```python
request = lhm_models.GetDataCheckReportOverviewRequest(batch_id=20001)
resp = client.get_data_check_report_overview(request)
```

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `resp.body.data.batch_id` | int | 批次 ID |
| `.data.check_type` | int | 校验类型 |
| `.data.check_result` | int | 校验结果 |
| `.data.report_title` | str | 报告标题 |
| `.data.report_time` | str | 报告生成时间 |
| `.data.report_status` | int | 报告状态：0-未生成 1-生成中 2-已生成 |
| `.data.check_table_num` | int | 校验表总数 |
| `.data.error_table_num` | int | 异常表数 |
| `.data.pass_table_num` | int | 通过表数 |
| `.data.skip_table_num` | int | 跳过表数 |
| `.data.pass_pt_num` | int | 通过分区数 |
| `.data.check_pt_count` | int | 校验分区总数 |
| `.data.check_row_count` | int | 校验总行数 |
| `.data.check_row_pass_count` | int | 通过行数 |
| `.data.pass_process` | float | 通过率（0-100） |
| `.data.pass_process_export` | str | 通过率文本 |
| `.data.task_id` | int | 任务 ID |
| `.data.task_name` | str | 任务名称 |
| `.data.src_ds_name` | str | 源端数据源名称 |
| `.data.src_ds_type` | str | 源端数据源类型 |
| `.data.dst_ds_name` | str | 目标端数据源名称 |
| `.data.dst_ds_type` | str | 目标端数据源类型 |

---

## Step 5.2: 字段维度明细（可选）

### `client.list_data_check_column_results(request)` ✅

查询某个 Job 的字段维度校验明细，适用于指标校验场景。

**请求类**：`lhm_models.ListDataCheckColumnResultsRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | str | 是 | 校验结果 ID（从 Step 5.4 获取） |
| page_index | int | 否 | 页码 |
| page_size | int | 否 | 每页大小 |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `.data[i].src_column_name` | str | 源端字段名 |
| `.data[i].src_column_type` | str | 源端字段类型 |
| `.data[i].dst_column_name` | str | 目标端字段名 |
| `.data[i].dst_column_type` | str | 目标端字段类型 |
| `.data[i].src_alias` | str | **源端指标别名（如 `min_col_bigint`，推荐用这个标识指标类型）** |
| `.data[i].dst_alias` | str | 目标端指标别名 |
| `.data[i].src_metric_column` | str | 源端指标表达式（如 `min(\`col_bigint\`)`） |
| `.data[i].dst_metric_column` | str | 目标端指标表达式 |
| `.data[i].check_rule` | str | 校验规则（如 CUSTOM_METRIC_TEMPLATE） |
| `.data[i].src_result` | str | 源端结果值 |
| `.data[i].dst_result` | str | 目标端结果值 |
| `.data[i].actual_threshold` | str | 实际阈值（如 `96.00%`） |
| `.data[i].expect_threshold` | float | 期望阈值 |
| `.data[i].is_consistent` | int | 一致性：0-不一致 1-一致 2-人工修复 |
| `.data[i].check_result` | int | 校验结果 |

> **注意**：旧文档中的 `compare_type` 字段**不存在**，应使用 `src_alias` 来标识指标类型（如 `min_col_bigint`、`avg_col_int` 等）。

---

## Step 5.3: Step 结果概览（可选）

### `client.get_step_result_overview(request)` ✅

根据 result_id 查询单个 Step 的结果概览。

**请求类**：`lhm_models.GetStepResultOverviewRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| result_id | str | 是 | 校验结果 ID（从 Step 5.4 获取） |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `.data.result_id` | str | 校验结果 ID |
| `.data.status` | int | 状态 |
| `.data.is_consistent` | int | 一致性：0-不一致 1-一致 |
| `.data.source_table` | str | 源端表名 |
| `.data.target_table` | str | 目标端表名 |
| `.data.source_pt_name` | str | 源端分区名 |
| `.data.target_pt_name` | str | 目标端分区名 |
| `.data.src_metric_name` | str | 源端指标名 |
| `.data.dst_metric_name` | str | 目标端指标名 |
| `.data.check_colum_count` | int | 校验字段数 |
| `.data.pass_colum_count` | int | 通过字段数 |

---

## Step 5.4: Step 维度明细（可选）

> **重要**：存在两个不同的 Step 查询 API，入参类型不同：
> - `list_data_check_report_step` — `job_id` 为 **int 数字**（`task_config_id`）
> - `list_data_check_report_step_by_job_id` — `job_id` 为 **str 字符串哈希**（从 `list_data_check_report` 的 `.job_id` 获取）
>
> **推荐用 `list_data_check_report_step_by_job_id`**，因为 `list_data_check_report` 返回的 `job_id` 是字符串哈希。

### `client.list_data_check_report_step_by_job_id(request)` ✅

查询某个 Job（字符串哈希 job_id）下的分区/分片粒度明细。

**请求类**：`lhm_models.ListDataCheckReportStepByJobIdRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| job_id | str | 是 | 作业 ID 字符串哈希（从 `list_data_check_report` 的 `.job_id` 获取） |
| page_index | int | 否 | 页码 |
| page_size | int | 否 | 每页大小 |

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `.data[i].step_id` | str | Step ID |
| `.data[i].result_id` | str | 校验结果 ID（Step 5.3 / 5.2 的入参） |
| `.data[i].source_pt_name` | str | 源端分区名 |
| `.data[i].target_pt_name` | str | 目标端分区名 |
| `.data[i].src_count` | str | 源端行数 |
| `.data[i].dst_count` | str | 目标端行数 |
| `.data[i].src_sql` | str | 源端执行的 SQL |
| `.data[i].dst_sql` | str | 目标端执行的 SQL |
| `.data[i].status` | int | 执行状态 |
| `.data[i].is_consistent` | int | **一致性：0-不一致 1-一致（注意：不是 check_result）** |
| `.data[i].err_message` | str | 错误信息 |
| `.data[i].gmt_start` | str | 开始时间 |
| `.data[i].gmt_end` | str | 结束时间 |

### `client.list_data_check_report_step(request)` ✅

查询某个 Job（数字 config_id）下的分区/分片粒度明细。

**请求类**：`lhm_models.ListDataCheckReportStepRequest`

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| job_id | int | 是 | 作业 ID 数字（`task_config_id`，**不是**字符串哈希） |
| check_result | int | 否 | 校验结果过滤 |
| job_status | int | 否 | Step 状态过滤 |
| page_index | int | 否 | 页码 |
| page_size | int | 否 | 每页大小 |

**响应字段：**（同 `list_data_check_report_step_by_job_id`，见上表）

---

## 补充接口

### 任务管理

| SDK 方法 | 状态 | 请求类 | 说明 |
|---------|------|--------|------|
| `get_data_check_task_list` | ✅ | `GetDataCheckTaskListRequest` | 搜索任务列表（支持 task_name/check_type/exec_status/check_result 等多维度筛选） |
| `get_data_check_task_config` | ✅ | `GetDataCheckTaskConfigRequest` | 查看任务批次级配置 |
| `update_data_check_task` | ✅ | `UpdateDataCheckTaskRequest` | 修改任务（不支持改 check_type/task_mode） |
| `delete_data_check_task` | ✅ | `DeleteDataCheckTaskRequest` | 批量删除任务（入参：task_ids 数组，运行中不可删） |
| `exec_data_check_re_run` | ✅ | `ExecDataCheckReRunRequest` | 全量重跑（入参：batch_id） |
| `exec_data_check_run_failed` | ✅ | `ExecDataCheckRunFailedRequest` | 失败重跑（入参：batch_id, type） |
| `exec_data_check_toggle` | ✅ | `ExecDataCheckToggleRequest` | 开启/关闭定时调度（入参：params 数组，每项含 id/last_batch_id/is_scheduled） |
| `get_cron_exec_time` | ✅ | `GetCronExecTimeRequest` | 预览 Cron 执行时间（入参：cron_rule） |

#### `get_data_check_task_list` 响应字段（重要）

> **注意**：此接口返回的字段名与 `add_data_check_task` 的 task_id 不同，使用 `id` 作为主键。

**入参：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_name | str | 否 | 任务名称（模糊搜索） |
| check_type | int | 否 | 校验类型筛选：0-数据量比对 1-指标比对 2-弱内容对比 |
| exec_status | int | 否 | 执行状态筛选：0-待运行 1-运行中 2-终止运行 3-运行失败 4-运行完成 |
| check_result | int | 否 | 校验结果筛选：0-无记录 1-通过 2-不通过 |
| is_scheduled | int | 否 | 是否启用调度筛选：0-未启用 1-已启用 |
| template_name | str | 否 | 校验模板名称（模糊搜索） |
| create_start_time | str | 否 | 创建时间范围起点（YYYY-MM-DD HH:MM:SS） |
| create_end_time | str | 否 | 创建时间范围终点（YYYY-MM-DD HH:MM:SS） |
| update_start_time | str | 否 | 更新时间范围起点（YYYY-MM-DD HH:MM:SS） |
| update_end_time | str | 否 | 更新时间范围终点（YYYY-MM-DD HH:MM:SS） |
| page_index | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页大小（默认 10） |

**响应字段（`resp.body.data[i]`）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `.id` | int | **任务 ID（注意：是 `id` 不是 `task_id`）** |
| `.task_name` | str | 任务名称 |
| `.check_type` | int | 校验类型 |
| `.task_mode` | int | 任务模式 |
| `.exec_status` | int | **最新执行状态（可直接使用，无需再调 history）** |
| `.check_result` | int | **最新校验结果（可直接使用）** |
| `.last_batch_id` | int | **最新批次 ID（可直接使用）** |
| `.src_ds_id` / `.src_ds_name` / `.src_ds_type` | int/str/str | 源端数据源信息 |
| `.dst_ds_id` / `.dst_ds_name` / `.dst_ds_type` | int/str/str | 目标端数据源信息 |
| `.check_template_id` | str | 校验模板 ID |
| `.template_name` | str | 模板名称 |
| `.pass_process` | float | 通过率 |
| `.process` | float | 进度 |
| `.is_scheduled` | int | 是否定时调度 |
| `.gmt_create` | str | 创建时间 |
| `.gmt_modified` | str | 修改时间 |

> **最佳实践**：遍历任务列表时，直接使用 `task.exec_status`、`task.check_result`、`task.last_batch_id`，**无需**再对每个任务调用 `list_data_check_task_history`（后者需要 `batch_id` 且会额外消耗 API 配额）。

#### `update_data_check_task` 入参

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | int | 是 | 任务 ID（定位要修改的任务） |
| task_name | str | 否 | 任务名称（**仅允许**英文字母、中文字符、数字；特殊字符报 E500R103） |
| task_description | str | 否 | 任务描述信息 |
| src_ds_id / src_ds_name / src_ds_type | str | 否 | 源端数据源信息 |
| dst_ds_id / dst_ds_name / dst_ds_type | str | 否 | 目标端数据源信息 |
| src_engine_id / src_engine_name / src_engine_type | str | 否 | 源端校验引擎信息 |
| dst_engine_id / dst_engine_name / dst_engine_type | str | 否 | 目标端校验引擎信息 |
| check_template_id | str | 否 | 校验模板 ID（不传则保持原值） |

> **注意**：不支持修改 `check_type` 和 `task_mode`，需新建任务。

#### `delete_data_check_task` 入参

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_ids | list[int] | 是 | 任务 ID 列表（支持批量删除） |

> **注意**：运行中的任务不可删除，需先 stop 终止。

#### `exec_data_check_sql_preview` 入参

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | int | 是 | 校验任务 ID |
| data_source_id | str | 是 | 数据源 ID |
| full_table_name | str | 是 | 校验表名（格式：schema.table） |
| engine_id | str | 否 | 校验引擎 ID（Spark 场景使用） |
| partition_condition | str | 否 | 分区条件 |
| where_clause | str | 否 | WHERE 条件 |
| check_column | str | 否 | 校验字段 |

#### `list_data_check_config` 入参

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | int | 是 | 校验任务 ID |
| src_table | str | 否 | 源表名称（模糊搜索） |
| page_index | int | 否 | 页码（默认 1） |
| page_size | int | 否 | 每页大小（默认 10） |

### 配置管理

| SDK 方法 | 状态 | 请求类 | 说明 |
|---------|------|--------|------|
| `get_data_check_config` | ✅ | `GetDataCheckConfigRequest` | 查看表级配置列表（入参：task_id） |
| `delete_data_check_config` | ✅ | `DeleteDataCheckConfigRequest` | 删除表级配置（入参：id） |
| `exec_data_check_sql_preview` | ✅ | `ExecDataCheckSqlPreviewRequest` | SQL 预览（入参：task_id, data_source_id, full_table_name, engine_id, partition_condition, where_clause, check_column） |

### 报告下载

| SDK 方法 | 状态 | 请求类 | 说明 |
|---------|------|--------|------|
| `list_data_check_report_instance` | ✅ | `ListDataCheckReportInstanceRequest` | 报告历史实例（入参：task_id） |
| `exec_data_check_generate_report` | ✅ | `ExecDataCheckGenerateReportRequest` | 触发报告生成（入参：batch_id） |
| `get_data_check_report_status` | ✅ | `GetDataCheckReportStatusRequest` | 报告生成状态（入参：batch_id，返回 0/1/2/3） |
| `exec_data_check_download_report` | ✅ | `ExecDataCheckDownloadReportRequest` | 下载报告（入参：batch_id，返回 OSS 链接） |

---

## ID 传递关系

```
Step 1  (add_data_check_task)        → task_id    → Step 1.1, Step 2, Step 4
Step 2  (exec_data_check_save_task)   → batch_id   → Step 3, 4.1, 5, 5.1
Step 5  (list_data_check_report)      → job_id     → Step 5.4
Step 5.4(list_data_check_report_step) → result_id  → Step 5.2, Step 5.3
```
