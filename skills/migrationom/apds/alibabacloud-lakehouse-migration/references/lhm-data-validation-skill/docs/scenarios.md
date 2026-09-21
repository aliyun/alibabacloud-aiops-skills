# 标准使用场景

本文档覆盖 `data-validation-skill` 的 4 个核心使用场景，作为测试、推广和外部工作流集成的统一基线。每个场景包含：场景描述、前置条件、操作步骤、涉及能力、预期输出与常见问题。

> 说明：当前版本为单体 Skill，可直接使用 `scripts/common.py` 中的函数。后续会拆分为 `atomic-skills/` 下的内层原子 Skill，届时本文档中的函数名会同步映射到对应原子 Skill。

---

## 场景一：从零发起一次校验任务

### 描述

用户首次或再次需要校验源端到目标端的数据一致性。根据待校验范围，可选择：

- 逐表数据量校验（`run_count_check`）
- 逐表指标校验（`run_metric_check`）
- 批量模式校验（`run_batch_check`）

### 前置条件

1. 已安装 aliyun CLI + aliyun-cli-lhm 插件及 `pyyaml`（见根目录 README「环境准备」）
2. 已配置环境变量 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
3. 已在 LHM 控制台注册源端与目标端数据源
4. 已购买并配置 DataWorks 独享数据集成资源组，且 LHM 数据校验 Agent 已上线
5. 首次使用时，需人工确认上述 3、4 项已就绪（SDK 暂无法自动探测）

### 操作步骤

1. 根据场景选择入口脚本：
   - 逐表数据量：`scripts/01_count_per_table.py`
   - 批量数据量：`scripts/02_count_batch.py`
   - 逐表指标：`scripts/03_metric_per_table.py`
2. 修改脚本顶部 `[配置区]`：数据源三要素、待校验表/匹配规则、阈值等
3. 运行脚本：`python scripts/01_count_per_table.py`
4. 脚本自动完成：创建任务 → 配置 → 保存批次 → 触发执行
5. 记录返回的 `task_id` 与 `batch_id`

### 涉及能力

| 当前函数 | 说明 |
|----------|------|
| `run_count_check()` | 创建并触发逐表数据量校验 |
| `run_metric_check()` | 创建并触发逐表指标校验 |
| `run_batch_check()` | 创建并触发批量模式校验 |

### 预期输出

```text
[一键执行] taskId=12345
  [1/2] src_db.orders → configId=101
  [2/2] src_db.users → configId=102
[一键执行] batchId=20001，已自动触发执行
  [轮询] batchId=20001 execStatus=4(FINISHED) ...

| 项目 | 数值 |
|---|---|
| 任务名称 | 逐表数据量校验 |
| 总表数 | 2 |
| 通过表数 | 1 |
| 失败表数 | 1 |
| 表通过率 | 50.00% |
| 执行状态 | 4(FINISHED) |

完成: task_id=12345  batch_id=20001
```

> 默认执行后**不阻塞轮询**。脚本示例中保留了轮询；若需非阻塞执行，可去掉 `poll_exec_status()`，直接返回 `batch_id`，由调用方后续查询。

### 常见问题

- **任务名报错 E500R103**：`task_name` 仅允许中英文、数字，不能含特殊字符
- **指标校验全部误判 PASSED**：`threshold` 切勿传 `0.0`，应使用 `None` 让系统采用默认值
- **MaxCompute 分区表批量校验报错 ODPS-0130071 或规划为空**：需同时设置 `source_global_params='odps.sql.allow.fullscan=true'` 和 `target_global_params='odps.sql.allow.fullscan=true'`，并在匹配规则中写明源端和目标端分区条件，例如 `dt='2026-01-01';dt='2026-01-01'`

---

## 场景二：查看历史模板或实例并重新运行

### 描述

用户已有历史任务，想查看最近执行状态、下载报告，或对失败/不通过的表进行重跑。

### 前置条件

1. 已知 `task_id` 或 `batch_id`
2. 该任务/批次在目标 LHM 工作空间中真实存在

### 操作步骤

1. 调用 `summarize_batch(client, batch_id)` 查看概览
2. 若存在失败表，调用 `diagnose_failed(client, batch_id)` 定位差异
3. 若需重跑失败表，调用 `rerun_failed(client, batch_id)` 获取新的 `batch_id`
4. 对新 `batch_id` 重复步骤 1~2

### 涉及能力

| 当前函数 | 说明 |
|----------|------|
| `summarize_batch()` | 查看批次概览 |
| `diagnose_failed()` | 诊断不通过原因 |
| `rerun_failed()` | 重跑失败/不通过/被终止的表 |
| `list_failed_tasks()` | 查询所有存在问题的任务 |

### 预期输出

```text
重跑前批次 20001 概览：通过 8/10 张表
新批次 20002 已触发，等待完成后再次查看...
```

### 常见问题

- **用 `task_id` 调 run / stop / rerun / report / download**：这些接口必须使用 `batch_id`
- **重跑后没有新数据**：`rerun_failed()` 只重跑失败/不通过的表，不会重新匹配新表

---

## 场景三：通过外部工作流调用 Skill

### 描述

外部系统（如 Airflow / DataWorks 数据开发 / 内部调度平台）需要以非交互方式触发校验，并将 `batch_id` 纳入自身调度链路。

### 前置条件

1. 外部系统已具备调用 Python 代码的能力
2. 参数可由外部系统完整提供，无需反问用户
3. 同场景一中的环境、数据源、资源组要求

### 操作步骤

1. 将 `data-validation-skill/scripts/` 加入 Python 路径
2. 直接 import 并调用底层函数
3. 函数返回 `task_id` + `batch_id` 后立即退出，不阻塞轮询
4. 外部系统自行决定何时调用 `poll_exec_status()` / `download_report()`

### 示例代码

```python
from common import build_client, run_batch_check

client = build_client()
task_id, batch_id = run_batch_check(
    client,
    task_name='每日全库校验',
    src_ds=('ds-src-001', '源端MySQL', 'MySQL'),
    dst_ds=('ds-dst-001', '目标端Hive', 'Hive'),
    check_type=0,
    match_rule='src_db|dst_db|*',
)

# 返回给外部调度系统
print(f'task_id={task_id} batch_id={batch_id}')
```

### 涉及能力

| 当前函数 | 说明 |
|----------|------|
| `run_count_check()` / `run_metric_check()` / `run_batch_check()` | 创建并触发任务 |
| `poll_exec_status()` | 由外部工作流按需调用 |
| `download_report()` | 由外部工作流在任务完成后调用 |

### 预期输出

```json
{
  "task_id": 12345,
  "batch_id": 20001
}
```

### 常见问题

- **在 Skill 内部轮询导致工作流阻塞**：外部调用时应保持非阻塞，将轮询放到外部调度侧
- **参数不完整导致反问**：外部调用前需确保所有必填参数已准备就绪

---

## 场景四：触发执行与报告下载

### 描述

用户或外部系统已有配置好的任务/批次，需要查看执行结果并下载完整报告。

### 前置条件

1. 已知 `batch_id`
2. 该批次已执行完成（`exec_status=4`）

### 操作步骤

1. 调用 `summarize_batch(client, batch_id)` 获取概览
2. 使用 `format_batch_summary()` 输出 Markdown 表格
3. 若存在失败表，调用 `diagnose_failed()` + `format_diagnosis_report()` 输出诊断摘要
4. 调用 `download_report(client, batch_id)` 获取 OSS 下载链接

### 示例代码

```python
from common import build_client, summarize_batch, diagnose_failed, download_report
from report_formatter import format_batch_summary, format_diagnosis_report

client = build_client()
batch_id = 20001

summary = summarize_batch(client, batch_id)
print(format_batch_summary(summary))

if summary['fail_tables']:
    diagnosis = diagnose_failed(client, batch_id, group_by_field=True)
    print(format_diagnosis_report(diagnosis, max_detail_rows=20))

url = download_report(client, batch_id)
print(f'报告下载链接: {url}')
```

### 涉及能力

| 当前函数 | 说明 |
|----------|------|
| `summarize_batch()` | 查看批次概览 |
| `format_batch_summary()` | 概览 Markdown 表格化 |
| `diagnose_failed()` | 诊断不通过原因 |
| `format_diagnosis_report()` | 诊断报告 Markdown 表格化 |
| `download_report()` | 一键下载报告 |

### 预期输出

```text
| 项目 | 数值 |
|---|---|
| 总表数 | 120 |
| 通过表数 | 115 |
| 失败表数 | 3 |
| 表通过率 | 95.83% |

**共发现 3 张表存在差异/异常**
...

报告下载链接: https://oss-url/xxx.xlsx
```

### 常见问题

- **批次未完成就下载报告**：`download_report()` 会检查 `exec_status=4`，未完成会抛异常
- **报告下载返回空**：`download_report()` 内部会自动触发生成并轮询，无需手动调 `generate_report`
- **报告已生成但想重新下载**：可重复调用 `download_report()`，OSS 链接会刷新
