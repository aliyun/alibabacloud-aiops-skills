# 外部工作流集成指南

本文档面向需要将 LHM 数据校验能力嵌入到自身调度系统（Airflow、DataWorks 数据开发、内部调度平台等）的开发人员。集成方式采用**直接调用 Python 函数**，绕过外层 Skill 的交互层，保证工作流不被阻塞。

---

## 集成原则

1. **非阻塞触发**：调用 `run_*` 函数后立即返回 `batch_id`，不在函数内部轮询等待。
2. **外部自治轮询**：外部系统自行决定何时调用 `poll_exec_status()`，并可设置自己的超时、重试、告警策略。
3. **参数完整**：外部调用时所有必填参数必须一次性传入，避免函数内部反问或交互。
4. **幂等可重跑**：失败后可使用原 `batch_id` 调用 `rerun_failed()` 生成新的 `batch_id`。

---

## 前置检查（lhm-common）

在集成前，建议先通过 `lhm-common` 原子 Skill 完成环境连通性验证和 onboarding 状态确认：

```bash
# 验证 AK/SK 和 Region 能连通 LHM
python atomic-skills/lhm-common/scripts/run.py check --profile data-validation --region hangzhou

# 在控制台确认各项前置条件后，记录确认状态
python atomic-skills/lhm-common/scripts/run.py confirm --profile data-validation \
  --resource-group --agent --data-sources --region hangzhou
```

`check` 返回 `env_ready=true` 表示凭证和 Region 可连通 LHM；`confirm` 将手动确认结果写入本地状态文件，供后续审计。详细说明见 [操作手册 §2.3 前置检查](operations-manual.md)。

---

## 最小集成示例

```python
# workflow_validate.py
import os
from common import build_client, run_batch_check, poll_exec_status, download_report

# Credentials are resolved through the default credential chain
# (environment variables / ~/.alibabacloud/credentials / RAM Role); never handle AK/SK explicitly.
# Optionally use lhm-common's data_validation_config.yaml:
# from common import build_client_from_config
# client = build_client_from_config(config_path='data_validation_config.yaml', profile='data-validation')


def trigger_validation() -> dict:
    """触发校验并返回 batch_id，不等待完成。"""
    client = build_client()
    # 推荐：使用 build_client_from_config 从 data_validation_config.yaml 加载凭证，无需手动传入 AK/SK
    # client = build_client_from_config(config_path='data_validation_config.yaml', profile='data-validation')
    task_id, batch_id = run_batch_check(
        client,
        task_name='每日全库校验',
        src_ds=('ds-src-001', '源端MySQL', 'MySQL'),
        dst_ds=('ds-dst-001', '目标端Hive', 'Hive'),
        check_type=0,
        match_rule='src_db|dst_db|*',
        # 数据量校验默认精确匹配，不要传 0.0
        threshold=None,
    )
    return {'task_id': task_id, 'batch_id': batch_id}


def wait_and_download(batch_id: int) -> str:
    """等待完成并下载报告。"""
    client = build_client()
    # 查询历史记录拿到 task_id（轮询需要 task_id + batch_id）
    import lhm_models
    from common import check_resp

    resp = client.list_data_check_task_history(
        lhm_models.ListDataCheckTaskHistoryRequest(batch_id=batch_id, page_index=1, page_size=1)
    )
    check_resp(resp, 'ListDataCheckTaskHistory')
    task_id = resp.body.data[0].task_id

    final_status = poll_exec_status(client, task_id, batch_id)
    if final_status == 3:
        raise RuntimeError(f'校验执行失败: batch_id={batch_id}')

    return download_report(client, batch_id)
```

外部调度系统可以这样编排：

```python
# Step 1: 触发校验
info = trigger_validation()
# Step 2: 将 batch_id 存入 XCom / 状态库，供下游使用
# Step 3: 下游任务等待完成后下载报告
url = wait_and_download(info['batch_id'])
```

---

## 推荐接口映射

| 外部工作流需求 | 当前可直接调用的函数 | 返回 |
|----------------|----------------------|------|
| 触发逐表数据量校验 | `run_count_check()` | `(task_id, batch_id)` |
| 触发逐表指标校验 | `run_metric_check()` | `(task_id, batch_id)` |
| 触发批量模式校验 | `run_batch_check()` | `(task_id, batch_id)` |
| 查询执行状态 | `poll_exec_status()` | `exec_status` |
| 获取概览 | `summarize_batch()` | `dict` |
| 诊断失败 | `diagnose_failed()` | `list` / `dict` |
| 下载报告 | `download_report()` | OSS URL |
| 重跑失败 | `rerun_failed()` | 新 `batch_id` |

后续拆分为内层原子 Skill 后，上表会映射为 `atomic-skills/lhm-*/scripts/run.py`。

---

## 参数约定

### 数据源三要素

```python
src_ds = ('ds-src-001', '源端MySQL', 'MySQL')
dst_ds = ('ds-dst-001', '目标端Hive', 'Hive')
```

- `ds_id`：SDK 核心入参，必须真实存在于 LHM 控制台
- `ds_name` / `ds_type`：仅用于展示与日志，不影响调用

### 批量匹配规则

```python
match_rule = 'src_db|dst_db|*'
```

规则语法详见 `references/batch_match_rules.md`。

### threshold 约定

- 数据量校验默认精确匹配，建议不传或传 `None`。
- 传 `0.0` 表示“一致率 ≥ 0% 即通过”，会导致所有校验被判为 PASSED，通常不是期望行为。

### 校验类型

| `check_type` | 含义 | 推荐入口 |
|--------------|------|----------|
| 0 | 数据量 | `run_count_check()` / `run_batch_check(check_type=0)` |
| 1 | 指标 | `run_metric_check()` / `run_batch_check(check_type=1)` |

---

## 错误处理建议

外部工作流应至少捕获以下异常并做对应处理：

| 异常场景 | 建议处理 |
|----------|----------|
| `RuntimeError`（AK 未配置） | 检查环境变量或密钥管理服务 |
| `RuntimeError`（API 调用失败） | 记录 requestId，按 err_code 重试或告警 |
| `poll_exec_status()` 返回 `-1` | 超时，建议改为异步告警，稍后人工或定时任务再查 |
| `poll_exec_status()` 返回 `3` | 执行失败，调用 `diagnose_failed()` 或查看 LHM 控制台 |
| `download_report()` 报告生成失败 | 检查批次是否完成、报告状态是否为 2 |

---

## 权限与前置条件

外部工作流运行前，请确保：

1. AK/SK 具备 LHM 服务调用权限
2. DataWorks 独享数据集成资源组已购买并绑定
3. LHM 数据校验 Agent 已上线
4. 源端/目标端数据源已在 LHM 控制台注册
5. 运行环境已安装 aliyun CLI（含 aliyun-cli-lhm 插件）与 `pyyaml`（request 模型由本地 `scripts/lhm_models.py` 提供，无需另装 SDK）

> 本 Skill 无法自动校验 2~4 项，首次集成时需要人工确认。可使用 `lhm-common confirm` 将确认结果记录到本地状态文件，便于后续审计和自动化检查。
