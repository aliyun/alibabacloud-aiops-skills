# 数据校验场景示例（网络层：aliyun CLI）

本文档提供执行数据校验的完整场景示例。API 调用统一经 `scripts/aliyun_cli.py`
封装为 `aliyun lhm <命令>` 子进程调用，对外保持与 Python SDK 一致的调用形状。

---

## 0. 初始化客户端

```python
import sys
sys.path.insert(0, 'scripts')

from common import build_client, check_resp
import lhm_models  # request 模型层（本地实现，替代已废弃、不再安装的 alibabacloud_lhm20250116 SDK）

def build():
    """构建 LHM 客户端（底层走 aliyun CLI + aliyun-cli-lhm 插件）。"""
    return build_client(region='hangzhou')  # AK/SK 从环境变量读取

client = build()
```

> 运行前提：已安装 aliyun CLI（>= 3.3.8）与 aliyun-cli-lhm 插件，
> 并设置环境变量 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`。
> `check_resp(resp, action)` 在 `resp.body.success == False` 时抛异常。

---

## 1. 场景分类

| 场景 | 描述 | 推荐模式 |
|------|------|---------|
| A. 已有任务 | 平台上已创建校验任务和校验对象 | 直接执行并查看报告 |
| B. 批量校验 | 知道大概范围（如某个库下所有表） | task_mode=1 同模式批量创建 |
| C. 逐表校验 | 只需校验特定几张表 | task_mode=0 逐表精细化创建 |

---

## 2. 场景 B：同模式批量创建示例

### B1：全库数据量校验

```python
# Step 1: 创建任务
request = lhm_models.AddDataCheckTaskRequest(
    task_name='lhm库全表数据量校验',
    check_type=0,       # 0 = 数据量比对
    task_mode=1,        # 1 = 同模式批量
    src_ds_id='ds-src-001', src_ds_name='源端MySQL', src_ds_type='MySQL',
    dst_ds_id='ds-dst-001', dst_ds_name='目标端Hive', dst_ds_type='Hive',
)
resp = client.add_data_check_task(request)
check_resp(resp, 'AddDataCheckTask')
task_id = resp.body.data
print(f'taskId={task_id}')

# Step 2: 配置批量匹配规则
config_req = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    task_config_info='lhm|lhm_dw|*',
)
resp = client.add_data_check_config(config_req)
check_resp(resp, 'AddDataCheckConfig')

# Step 3: 保存并立即执行
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    total_count_threshold=0.0,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
check_resp(resp, 'ExecDataCheckSaveTask')
batch_id = resp.body.data
print(f'batchId={batch_id}, 已自动触发执行')
```

### B2：正则匹配 + 关键字替换

```python
# Step 2: 配置匹配规则（正则 + 关键字替换）
config_req = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    task_config_info='lhm|lhm_dw|aliyun.*|aliyun.*|||${replace:aliyun:alibaba}',
)
resp = client.add_data_check_config(config_req)
check_resp(resp, 'AddDataCheckConfig')

# Step 3: 保存并立即执行
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
# aliyun_order → alibaba_order, aliyun_user → alibaba_user
```

### B3：带分区筛选 + 字段映射

```python
# Step 2: 配置匹配规则（分区筛选 + 字段映射）
config_req = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    task_config_info='lhm|lhm_dw|order.*|order.*|pt>lastNDate(${bizdate:yyyyMMdd},3)|pt:dt',
)
resp = client.add_data_check_config(config_req)
check_resp(resp, 'AddDataCheckConfig')

# Step 3: 保存并立即执行
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
# 只校验最近 3 天的分区，源端分区字段 pt 映射到目标端 dt
```

> 完整规则语法见 [batch_match_rules.md](batch_match_rules.md)。

---

## 3. 场景 C：逐表精细化示例

```python
# Step 1: 创建任务
request = lhm_models.AddDataCheckTaskRequest(
    task_name='核心表精细校验',
    check_type=0,       # 数据量比对
    task_mode=0,        # 逐表精细化
    src_ds_id='ds-001', src_ds_name='源端MySQL', src_ds_type='MySQL',
    dst_ds_id='ds-002', dst_ds_name='目标端Hive', dst_ds_type='Hive',
)
resp = client.add_data_check_task(request)
check_resp(resp, 'AddDataCheckTask')
task_id = resp.body.data

# Step 1.1: orders 表 — 带 where 条件 + 分区
config_request = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    source_table='lhm.orders',
    target_table='lhm_dw.orders',
    source_partition='dt=20260612',
    target_partition='dt=20260612',
    source_where_clause='status=1',
    target_where_clause='status=1',
    total_count_threshold=0.0,
    is_full_table_count=0,  # 分区为单位
)
resp = client.add_data_check_config(config_request)
check_resp(resp, 'AddDataCheckConfig')

# Step 1.1: users 表 — 全量校验
config_request = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    source_table='lhm.users',
    target_table='lhm_dw.users',
    is_full_table_count=1,  # 整表校验
)
resp = client.add_data_check_config(config_request)
check_resp(resp, 'AddDataCheckConfig')

# Step 2: 保存并执行
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
check_resp(resp, 'ExecDataCheckSaveTask')
batch_id = resp.body.data
```

---

## 4. 指标校验示例

### 4.1 使用 MIX 模板

```python
request = lhm_models.AddDataCheckTaskRequest(
    task_name='订单金额指标校验',
    check_type=1,       # 1 = 指标比对
    task_mode=1,        # 批量模式
    check_template_id='1001',  # MIX 模板（推荐）
    src_ds_id='ds-001', src_ds_name='源端MySQL', src_ds_type='MySQL',
    dst_ds_id='ds-002', dst_ds_name='目标端Hive', dst_ds_type='Hive',
)
resp = client.add_data_check_task(request)
check_resp(resp, 'AddDataCheckTask')
task_id = resp.body.data

# 配置批量匹配规则
config_req = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    task_config_info='lhm|lhm_dw|*',
)
resp = client.add_data_check_config(config_req)
check_resp(resp, 'AddDataCheckConfig')

# 保存并立即执行
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
```

### 4.2 自定义聚合字段（逐表模式）

```python
config_request = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    source_table='lhm.orders',
    target_table='lhm_dw.orders',
    # 自定义聚合表达式（必须有 AS 别名，源端目标端别名一致）
    source_columns='max(ifNull(id,0)) AS max_id,sum(amount) AS total_amount',
    target_columns='max(ifNull(id,0)) AS max_id,sum(amount) AS total_amount',
    total_count_threshold=0.0,
)
resp = client.add_data_check_config(config_request)
```

### 4.3 只校验特定字段

```python
config_request = lhm_models.AddDataCheckConfigRequest(
    task_id=task_id,
    source_table='lhm.orders',
    target_table='lhm_dw.orders',
    source_columns='id',       # 只校验 id 字段
    target_columns='id',
)
resp = client.add_data_check_config(config_request)
```

---

## 5. 轮询执行状态

```python
import time

EXEC_STATUS_TEXT = {0: 'PENDING', 1: 'RUNNING', 2: 'STOPPED', 3: 'FAILED', 4: 'FINISHED'}

history_request = lhm_models.ListDataCheckTaskHistoryRequest(
    task_id=task_id,
    batch_id=batch_id,
    page_index=1,
    page_size=10,
)
timeout_sec = 1800
deadline = time.time() + timeout_sec

while True:
    resp = client.list_data_check_task_history(history_request)
    check_resp(resp, 'ListDataCheckTaskHistory')
    rows = resp.body.data or []
    if rows:
        row = rows[0]
        status = row.exec_status
        print(
            f'batchId={row.batch_id} '
            f'execStatus={status}({EXEC_STATUS_TEXT.get(status, "?")}) '
            f'checkResult={row.check_result} '
            f'progress={row.progress}'
        )
        if status in (2, 3, 4):  # 终止/失败/完成
            break
    if time.time() > deadline:
        stop_request = lhm_models.ExecDataCheckStopRequest(batch_id=batch_id)
        client.exec_data_check_stop(stop_request)
        print(f'Timeout ({timeout_sec}s), attempted to stop batch')
        break
    time.sleep(5)
```

---

## 6. 报告查看

### 6.1 报告概览（已实现）

```python
overview_request = lhm_models.GetDataCheckReportOverviewRequest(batch_id=batch_id)
resp = client.get_data_check_report_overview(overview_request)
check_resp(resp, 'GetDataCheckReportOverview')
overview = resp.body.data
print(
    f'passRate={overview.pass_process_export} '
    f'checkedTables={overview.check_table_num} '
    f'pass={overview.pass_table_num} '
    f'error={overview.error_table_num} '
    f'skip={overview.skip_table_num}'
)
```

### 6.2 报告列表

```python
report_request = lhm_models.ListDataCheckReportRequest(
    batch_id=batch_id,
    check_result=2,  # 筛选不通过的表
    page_index=1, page_size=50,
)
resp = client.list_data_check_report(report_request)
check_resp(resp, 'ListDataCheckReport')
for row in resp.body.data:
    print(f'jobId={row.job_id} sourceTable={row.source_table} targetTable={row.target_table}')
    print(f'  checkResult={row.check_result} diffRate={row.diff_rate}')
```

### 6.3 字段维度明细

```python
column_request = lhm_models.ListDataCheckColumnResultsRequest(
    result_id='result-xxx',
)
resp = client.list_data_check_column_results(column_request)
check_resp(resp, 'ListDataCheckColumnResults')
for row in resp.body.data:
    print(f'{row.src_column_name} {row.src_alias}: src={row.src_result} dst={row.dst_result}')
```

### 6.4 Step 明细

```python
step_request = lhm_models.ListDataCheckReportStepRequest(job_id=30002)
resp = client.list_data_check_report_step(step_request)
check_resp(resp, 'ListDataCheckReportStep')
for row in resp.body.data:
    print(f'resultId={row.result_id} boundary={row.boundary}')
    print(f'  srcCount={row.src_count} dstCount={row.dst_count}')
    print(f'  srcSql={row.src_sql}')
    print(f'  dstSql={row.dst_sql}')
    print(f'  isConsistent={row.is_consistent} errMessage={row.err_message}')
```

---

## 7. 任务管理

### 7.1 搜索任务

```python
find_request = lhm_models.GetDataCheckTaskListRequest(
    task_name='订单校验',
    page_index=1, page_size=10,
)
resp = client.get_data_check_task_list(find_request)
check_resp(resp, 'GetDataCheckTaskList')
for row in resp.body.data:
    print(f'taskId={row.id} taskName={row.task_name} execStatus={row.exec_status}')
```

### 7.2 终止任务（已实现）

```python
# 仅 exec_status=1（运行中）可终止
stop_request = lhm_models.ExecDataCheckStopRequest(batch_id=batch_id)
resp = client.exec_data_check_stop(stop_request)
check_resp(resp, 'ExecDataCheckStop')
print(f'任务已终止')
```

### 7.3 全量重跑

```python
rerun_request = lhm_models.ExecDataCheckReRunRequest(batch_id=batch_id)
resp = client.exec_data_check_re_run(rerun_request)
check_resp(resp, 'ExecDataCheckReRun')
new_batch_id = resp.body.data
```

### 7.4 失败重跑

```python
run_failed_request = lhm_models.ExecDataCheckRunFailedRequest(
    batch_id=batch_id,
    type=0,  # 0=仅失败 1=失败+不通过 2=失败+被终止
)
resp = client.exec_data_check_run_failed(run_failed_request)
check_resp(resp, 'ExecDataCheckRunFailed')
new_batch_id = resp.body.data
```

---

## 8. 报告下载 SOP

```python
# Step 1: 确认校验批次已执行完成（exec_status=4）
history_request = lhm_models.ListDataCheckTaskHistoryRequest(
    task_id=task_id, batch_id=batch_id,
)
resp = client.list_data_check_task_history(history_request)
assert resp.body.data[0].exec_status == 4

# Step 2: 触发生成报告
generate_request = lhm_models.ExecDataCheckGenerateReportRequest(batch_id=batch_id)
resp = client.exec_data_check_generate_report(generate_request)
check_resp(resp, 'ExecDataCheckGenerateReport')

# Step 3: 轮询报告生成状态
while True:
    status_request = lhm_models.GetDataCheckReportStatusRequest(batch_id=batch_id)
    resp = client.get_data_check_report_status(status_request)
    status = resp.body.data
    if status == 2:   # 已完成
        break
    elif status == 3: # 生成失败
        raise RuntimeError('Report generation failed')
    time.sleep(3)

# Step 4: 下载报告
download_request = lhm_models.ExecDataCheckDownloadReportRequest(batch_id=batch_id)
resp = client.exec_data_check_download_report(download_request)
download_url = resp.body.data
print(f'Download URL: {download_url}')
```

---

## 9. 定时调度

```python
# 注意：定时调度通过 toggle 接口管理，不是通过 save_task 设置

# 先执行一次获取 batch_id
save_request = lhm_models.ExecDataCheckSaveTaskRequest(
    task_id=task_id,
    start_immediately=1,
)
resp = client.exec_data_check_save_task(save_request)
batch_id = resp.body.data

# 预览 Cron 执行时间
cron_request = lhm_models.GetCronExecTimeRequest(cron_rule='0+0+2+*+*+?')
resp = client.get_cron_exec_time(cron_request)
print(f'Next executions: {resp.body.data}')

# 开启/关闭定时调度
toggle_request = lhm_models.ExecDataCheckToggleRequest(
    params=[lhm_models.ExecDataCheckToggleRequestParams(
        id=task_id,
        last_batch_id=batch_id,
        is_scheduled=1,  # 0=关闭 1=开启
    )]
)
resp = client.exec_data_check_toggle(toggle_request)
```

---

## 10. common.py 助手函数速查

`scripts/common.py` 把上面 9 个章节的常用动作封装成一组工作流函数。Agent 优先使用助手函数，必要时再用原生 SDK 调用。

### 10.1 一键执行三种场景

```python
import sys
sys.path.insert(0, '<skill-dir>/scripts')
from common import build_client, run_count_check, run_metric_check, run_batch_check

client = build_client()                          # 生产

# 逐表数据量校验
task_id, batch_id = run_count_check(
    client,
    task_name='逐表数据量',
    src_ds=('ds-001', '源端MySQL', 'MySQL'),
    dst_ds=('ds-002', '目标端Hive', 'Hive'),
    tables=[('src_db.orders', 'dst_db.orders', 'dt=20240305', 'dt=20240305')],
    threshold=0.0,
)

# 逐表指标校验
task_id, batch_id = run_metric_check(
    client,
    task_name='逐表指标',
    src_ds=('ds-001', '源端MySQL', 'MySQL'),
    dst_ds=('ds-002', '目标端Hive', 'Hive'),
    tables=[{
        'source_table': 'src_db.orders', 'target_table': 'dst_db.orders',
        'source_partition': '', 'target_partition': '',
        'source_columns': 'sum(amount) AS total_amount',
        'target_columns': 'sum(amount) AS total_amount',
    }],
    check_template_id='1001',
)

# 批量模式（match_rule 可以是字符串或 List[Dict]）
task_id, batch_id = run_batch_check(
    client,
    task_name='全库数据量',
    src_ds=('ds-001', '源端MySQL', 'MySQL'),
    dst_ds=('ds-002', '目标端Hive', 'Hive'),
    check_type=0,
    match_rule='src_db|dst_db|*',
)
```

### 10.2 轮询 / 诊断 / 重跑

```python
from common import poll_exec_status, list_failed_tasks, diagnose_failed, rerun_failed

# 轮询直到终态（exec_status ∈ {2,3,4}）
final_status = poll_exec_status(client, task_id, batch_id, timeout_sec=1200)

# 列出本批次不通过/异常的表
failed = list_failed_tasks(client, batch_id)

# 按字段分组诊断不通过原因
diagnosis = diagnose_failed(client, batch_id, group_by_field=True)

# 重跑失败的表 → 返回新 batch_id
new_batch_id = rerun_failed(client, batch_id, fail_type=0)
# fail_type: 0=仅失败 1=失败+不通过 2=失败+被终止
```

### 10.3 下载报告

```python
from common import download_report

# 内部自动 generate_report → 等 report_status=2 → download
oss_url = download_report(client, batch_id)
print(f'报告下载地址: {oss_url}')
```

### 10.4 端到端 pipeline

```python
from common import full_check_pipeline

# 执行 → 轮询 → 下载 → 诊断 一气呵成
result = full_check_pipeline(
    client,
    task_name='端到端校验',
    src_ds=('ds-001', '源端MySQL', 'MySQL'),
    dst_ds=('ds-002', '目标端Hive', 'Hive'),
    tables=[('src_db.orders', 'dst_db.orders', '', '')],
)
print(result)
# {
#   'task_id': 10001,
#   'batch_id': 20001,
#   'pass_rate': '95.5%',
#   'oss_url': 'https://...',
#   'diagnosis': {...}
# }
```

### 10.5 批次概况

```python
from common import summarize_batch

summary = summarize_batch(client, batch_id)
# 返回通过率、校验表数、字段数、不通过明细等
```

