# LHM 数据校验 API 参考

> 本文档告诉模型"用户想做什么 → 调哪个 SDK 方法"。
> 场景脚本（get_report.py / get_task_info.py / submit_check.py）覆盖了常见场景。
> 当场景脚本不覆盖时，使用 `api_call.py` 直接调用 SDK 方法。

## 意图 → API 映射表

### 1. 任务管理

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 查看所有任务 | `get_data_check_task_list` | `get_task_info.py --list-tasks` | 分页查询 |
| 查看任务历史批次 | `list_data_check_task_history` | `get_task_info.py --list-batches` | 按 taskId |
| 查看任务配置 | `get_data_check_task_config` | `get_task_info.py --task-config` | 按 taskId |
| 创建任务 | `add_data_check_task` | `submit_check.py --create-task` | 返回 taskId |
| 更新任务 | `update_data_check_task` | ❌ 未覆盖 | 用 `api_call.py` |
| 删除任务 | `delete_data_check_task` | ❌ 未覆盖 | 用 `api_call.py` |
| 立即执行 | `exec_data_check_run` | `submit_check.py --run` | 按 batchId |
| 重新执行 | `exec_data_check_re_run` | ❌ 未覆盖 | 用 `api_call.py` |
| 停止执行 | `exec_data_check_stop` | ❌ 未覆盖 | 用 `api_call.py` |
| 重跑失败 | `exec_data_check_run_failed` | `submit_check.py --rerun-failed` | type: 0=失败 1=失败+不通过 2=失败+停止 |
| 开关定时 | `exec_data_check_toggle` | ❌ 未覆盖 | 用 `api_call.py` |
| 保存配置并执行 | `exec_data_check_save_task` | `submit_check.py --save` | 返回 batchId |

### 2. 报告查询（4 层下钻）

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 批次概览 | `get_data_check_report_overview` | `get_report.py --overview` | 通过率、表数、行数 |
| 表级详情 | `list_data_check_report` | `get_report.py --detail` | 每张表的校验结果 |
| 字段级记录 | `list_data_check_column_results` | `get_report.py --column` | 每个字段的源端/目标端值 |
| 分片级记录 | `list_data_check_report_step_by_job_id` | `get_report.py --step` | 每个分片的 SQL + 错误信息 |
| 全文比对概览 | — | `get_report.py --fulltext` | 当前不支持 |
| 步骤结果概览 | `get_step_result_overview` | ❌ 未覆盖 | 用 `api_call.py` |
| 报告历史列表 | `list_data_check_report_instance` | ❌ 未覆盖 | 用 `api_call.py` |
| 报告状态 | `get_data_check_report_status` | ❌ 未覆盖 | 0=无 1=生成中 2=完成 3=失败 |
| 生成报告 | `exec_data_check_generate_report` | ❌ 未覆盖 | 校验完成后触发 |
| 下载报告 | `exec_data_check_download_report` | ❌ 未覆盖 | 返回 OSS 链接 |
| 清除报告 | — | ❌ 未覆盖 | 通过 API 调用 |

### 3. 任务配置

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 添加表配置 | `add_data_check_config` | `submit_check.py --add-config` | 逐表配置 |
| 查看配置列表 | `list_data_check_config` | ❌ 未覆盖 | 分页查询 |
| 删除表配置 | `delete_data_check_config` | ❌ 未覆盖 | 用 `api_call.py` |
| SQL 预览 | `exec_data_check_sql_preview` | `submit_check.py --preview` | 预览生成的 SQL |

### 4. 模板管理

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 列出模板 | `list_check_templates` | `get_task_info.py --list-templates` | 分页查询 |
| 查看模板详情 | `get_check_template` | ❌ 未覆盖 | 按 templateId |
| 创建模板 | `create_check_template` | ❌ 未覆盖 | 用 `api_call.py` |
| 更新模板 | `update_check_template` | ❌ 未覆盖 | 用 `api_call.py` |
| 删除模板 | `delete_check_templates` | ❌ 未覆盖 | 用 `api_call.py` |

### 5. 统计与趋势

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 统计概览 | — | ❌ 未覆盖 | 通过 REST API 调用 |
| 通过率趋势 | — | ❌ 未覆盖 | 通过 REST API 调用 |
| 最近通过率 | — | ❌ 未覆盖 | 通过 REST API 调用 |

> 统计类 API 当前未在 SDK 中暴露方法，需通过 REST API 直接调用。

### 6. 签核与审核

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 人工审核 | — | ❌ 未覆盖 | 通过 REST API: POST /report/v3/review |
| 阈值修正 | — | ❌ 未覆盖 | 通过 REST API: POST /report/v3/correctionThreshold |

> 签核/审核 API 当前未在 SDK 中暴露方法。

### 7. 辅助功能

| 用户意图 | SDK 方法 | 场景脚本 | 说明 |
|---------|---------|---------|------|
| 轮询执行状态 | `list_data_check_task_history` | `submit_check.py --poll` | 自适应间隔 |
| 获取 cron 执行时间 | `get_cron_exec_time` | ❌ 未覆盖 | 预览下次执行时间 |

---

## 不可用的 API（当前版本不支持）

以下 API 调用会返回 `NOT_SUPPORT` 或为空实现，**不要调用**：

| API | 原因 |
|-----|------|
| 全文比对概览 | 后端未实现 |
| 全文比对详情分页 | 后端未实现 |
| 分组概览 | 后端未实现 |
| 分组详情分页 | 后端未实现 |
| 导出子任务结果 | 已废弃 |
| 批量重跑/停止 | 已废弃 |

---

## 使用 `api_call.py` 调用未覆盖的 API

当场景脚本不覆盖某个操作时，使用通用调用器：

```bash
python3 api_call.py <sdk_method_name> '<json_params>'
```

### 示例

```bash
# 删除任务
python3 api_call.py delete_data_check_task '{"task_ids": [123, 456]}'

# 停止执行
python3 api_call.py exec_data_check_stop '{"batch_id": 789}'

# 查看模板详情
python3 api_call.py get_check_template '{"template_id": "1001"}'

# 开关定时任务
python3 api_call.py exec_data_check_toggle '{"task_ids": [123], "params": []}'

# 查看报告状态
python3 api_call.py get_data_check_report_status '{"batch_id": 789}'

# 生成报告
python3 api_call.py exec_data_check_generate_report '{"batch_id": 789}'

# 下载报告
python3 api_call.py exec_data_check_download_report '{"batch_id": 789}'
```

### 参数格式

- JSON 参数使用 **snake_case**（与 SDK Request 类的字段名一致）
- 数字类型直接写，不要加引号
- 列表用 JSON 数组
- 可选参数不传即可

---

## 枚举值速查

### checkType — 校验类型

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | ByCount | 数据量比对（对比行数） |
| 1 | ByMetric | 指标比对（SUM/AVG/MIN/MAX/COUNT） |
| 2 | ByQuantity | 弱内容比对（MD5/CRC32 校验和） |

### checkResult — 校验结果

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | NO_RECORD | 无记录 |
| 1 | PASSED | 通过 |
| 2 | FAILED | 不通过 |

### execStatus — 批次执行状态

| 值 | 名称 | 终态 | 状态流转 |
|----|------|------|---------|
| 0 | TODO | ✗ | 已创建未触发 |
| 1 | RUNNING | ✗ | 可调用 stop 终止 |
| 2 | STOPPED | ✓ | 用户主动终止 |
| 3 | FAILED | ✓ | 可查看 errMessage |
| 4 | FINISHED | ✓ | 可查看报告 |

```
TODO(0) ──run──▶ RUNNING(1) ──完成──▶ FINISHED(4)
                   │
                   ├──stop──▶ STOPPED(2)
                   └──异常──▶ FAILED(3) ──重跑──▶ TODO(0)
```

### jobStatus — 作业/Step 状态

| 值 | 名称 | 终态 |
|----|------|------|
| 0 | INIT | ✗ |
| 1 | RUNNING | ✗ |
| 2 | FINISHED | ✓ |
| 3 | STOPPED | ✓ |
| 4 | FAIL | ✓ |
| 6 | READY | ✗ |
| 7 | SKIPPED | ✓ |

### reportStatus — 报告生成状态

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | NO_RECORD | 无记录 |
| 1 | GENERATING | 生成中 |
| 2 | DONE | 已完成 |
| 3 | FAIL | 生成失败 |

---

## 内置校验模板

| templateId | 模板名 | 说明 | 状态 |
|-----------|--------|------|------|
| 1001 | MIX | NUM + LEN 组合，覆盖最全 | **推荐** |
| 1002 | NUM | 行数 + 数值字段 avg/max/min | 可用 |
| 1003 | LEN | String/Map/Array 字段长度之和 | 可用 |
| ~~1004~~ | ~~XXHASH64~~ | ~~基础数据类型 hash 分位数~~ | **已废弃** |

---

## ID 传递链路

```
Step 1: add_data_check_task → task_id → 用于 config, save, query, update, delete
Step 2: exec_data_check_save_task → batch_id → 用于 run, stop, rerun, report, overview, download
Step 3: list_data_check_report → job_id (字符串) → 用于 step 详情
Step 4: list_data_check_report_step → result_id → 用于 column 详情
```

**关键规则**：
- `run`/`stop`/`rerun`/`report`/`download` 必须用 **batch_id**，不是 task_id
- `exec_data_check_run` 如果传 task_id 而非 batch_id，后端会抛 NPE
- `poll_exec_status` 需要同时传 task_id 和 batch_id

---

## 跨层级字段名对照

不同 API 层级对同一概念使用不同字段名：

| 概念 | 报告层 (list_data_check_report) | Step 层 (report_step) | 字段层 (column_results) |
|------|------|------|------|
| 源端行数 | `source_count` | `src_count` | — |
| 目标端行数 | `target_count` | `dst_count` | — |
| 一致性判定 | `check_result` (0/1/2) | `is_consistent` (0/1) | `is_consistent` (0/1) |
| 总表数 | `check_table_num` (overview) | — | — |
| 差异率 | `diff_rate` | — | `actual_threshold` |

**注意**：
- 判断一致性用 `is_consistent`（0=不一致，1=一致），不是 `check_result`
- 字段层用 `src_alias` 标识指标类型（如 `min_col_bigint`），不存在 `compare_type` 字段
