# -*- coding: utf-8 -*-
"""
场景 C：逐表精细化 — 指标校验（checkType=1, taskMode=0）

使用 common.run_metric_check 一键执行全流程。

指标校验与数据量校验的关键区别：
  - 需要 check_template_id（推荐 MIX 1001）
  - 可通过 source_columns / target_columns 指定自定义聚合表达式
  - 报告阶段可深入字段维度查看每个指标的对比结果

用法：
  1. 设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. 修改下方 [配置区] 的参数
  3. python scripts/03_metric_per_table.py
"""
from __future__ import annotations

import sys

from common import build_client, check_resp, poll_exec_status, run_metric_check, diagnose_failed
import lhm_models
from report_formatter import format_batch_summary, format_diagnosis_report


# ============================================================================
# [配置区] 按需修改
# ============================================================================

# 数据源: (id, name, type)
SRC_DS = ('ds-src-001', '源端MySQL', 'MySQL')
DST_DS = ('ds-dst-001', '目标端Hive', 'Hive')

# 校验模板
CHECK_TEMPLATE_ID = '1001'    # MIX（NUM + LEN，覆盖最全）

# 待校验的表
# source_columns / target_columns 可为空字符串，表示使用模板默认指标
# 自定义聚合必须有 AS 别名，源端目标端别名一致
TABLES = [
    {
        'source_table': 'src_db.orders',
        'target_table': 'dst_db.orders',
        'source_partition': 'dt=20240305',
        'target_partition': 'dt=20240305',
        'source_columns': 'sum(amount) AS total_amount,max(id) AS max_id',
        'target_columns': 'sum(amount) AS total_amount,max(id) AS max_id',
    },
    {
        'source_table': 'src_db.users',
        'target_table': 'dst_db.users',
        'source_partition': '',
        'target_partition': '',
        'source_columns': '',   # 使用模板默认指标
        'target_columns': '',
    },
]

# 校验参数
TOTAL_COUNT_THRESHOLD = 0.0


# ============================================================================
# [主流程]
# ============================================================================

def main() -> int:
    client = build_client()

    # 一键执行：创建任务（指定模板） → 逐表配置指标字段 → 保存批次 → 立即执行
    task_id, batch_id = run_metric_check(
        client,
        task_name='逐表指标校验',
        src_ds=SRC_DS,
        dst_ds=DST_DS,
        tables=TABLES,
        check_template_id=CHECK_TEMPLATE_ID,
        threshold=TOTAL_COUNT_THRESHOLD,
    )

    # 轮询执行状态
    final_status = poll_exec_status(client, task_id, batch_id)
    if final_status == 3:
        print('执行失败')
        return 2

    # 报告概览
    resp = client.get_data_check_report_overview(
        lhm_models.GetDataCheckReportOverviewRequest(batch_id=batch_id))
    check_resp(resp, 'GetDataCheckReportOverview')
    ov = resp.body.data
    if ov:
        summary = {
            'task_name': ov.task_name,
            'template': getattr(ov, 'check_template_name', None),
            'total_tables': ov.check_table_num,
            'pass_tables': ov.pass_table_num,
            'fail_tables': ov.error_table_num,
            'skip_tables': getattr(ov, 'skip_table_num', None),
            'pass_rate': ov.pass_process_export,
            'column_pass_rate': getattr(ov, 'pass_column_rate', None),
            'diff_rate': '-',
            'exec_status': 4,
            'check_result': ov.check_result,
        }
        # 指标校验额外追加字段级统计
        check_column_count = getattr(ov, 'check_colum_count', None)
        pass_column_count = getattr(ov, 'pass_colum_count', None)
        if check_column_count:
            summary['check_columns'] = check_column_count
        if pass_column_count is not None:
            summary['pass_columns'] = pass_column_count

        print(format_batch_summary(summary))

        # 指标校验按字段分组诊断，便于定位差异列
        if ov.error_table_num:
            print()
            print(format_diagnosis_report(
                diagnose_failed(client, batch_id, group_by_field=True),
                max_detail_rows=20,
            ))

    print(f'\n完成: task_id={task_id}  batch_id={batch_id}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
