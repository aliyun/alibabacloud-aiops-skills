# -*- coding: utf-8 -*-
"""
场景 A：逐表精细化 — 数据量校验（checkType=0, taskMode=0）

使用 common.run_count_check 一键执行全流程。

用法：
  1. 设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. 修改下方 [配置区] 的参数
  3. python scripts/01_count_per_table.py
"""
from __future__ import annotations

import sys

from common import build_client, check_resp, poll_exec_status, run_count_check, diagnose_failed
import lhm_models
from report_formatter import format_batch_summary, format_diagnosis_report


# ============================================================================
# [配置区] 按需修改
# ============================================================================

# 数据源: (id, name, type)
SRC_DS = ('ds-src-001', '源端MySQL', 'MySQL')
DST_DS = ('ds-dst-001', '目标端Hive', 'Hive')

# 待校验的表: [(source_table, target_table, source_partition, target_partition)]
# 分区为空字符串表示整表校验
TABLES = [
    ('src_db.orders', 'dst_db.orders', 'dt=20240305', 'dt=20240305'),
    ('src_db.users',  'dst_db.users',  '',            ''),
]

# 校验参数
# 切勿传 0.0：表示"一致率 >= 0% 即通过"，会把所有表误判为 PASSED。
# None = 不传阈值，使用系统默认精确匹配；需要容忍差异时传 100 以内的百分比数值。
TOTAL_COUNT_THRESHOLD = None   # 数据量阈值（None = 系统默认精确匹配）


# ============================================================================
# [主流程]
# ============================================================================

def main() -> int:
    client = build_client()

    # 一键执行：创建任务 → 逐表配置 → 保存批次 → 立即执行
    task_id, batch_id = run_count_check(
        client,
        task_name='逐表数据量校验',
        src_ds=SRC_DS,
        dst_ds=DST_DS,
        tables=TABLES,
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
        print(format_batch_summary(summary))

        # 若存在失败表，自动输出诊断摘要
        if ov.error_table_num:
            print()
            print(format_diagnosis_report(
                diagnose_failed(client, batch_id),
                max_detail_rows=20,
            ))

    print(f'\n完成: task_id={task_id}  batch_id={batch_id}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
