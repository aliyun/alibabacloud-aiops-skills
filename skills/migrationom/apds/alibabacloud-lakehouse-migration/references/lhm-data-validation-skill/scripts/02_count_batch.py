# -*- coding: utf-8 -*-
"""
场景 B：同模式批量 — 数据量校验（checkType=0, taskMode=1）

使用 common.run_batch_check 一键执行全流程。

用法：
  1. 设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. 修改下方 [配置区] 的参数
  3. python scripts/02_count_batch.py
"""
from __future__ import annotations

import sys

from common import build_client, check_resp, poll_exec_status, run_batch_check, diagnose_failed
import lhm_models
from report_formatter import format_batch_summary, format_diagnosis_report


# ============================================================================
# [配置区] 按需修改
# ============================================================================

# 数据源: (id, name, type)
SRC_DS = ('ds-src-001', '源端MySQL', 'MySQL')
DST_DS = ('ds-dst-001', '目标端Hive', 'Hive')

# 批量匹配规则（多条用 \n 分隔）
# 格式：源端库名|目标端库名|源表名|目标表名|分区条件|字段映射
# 详见 references/batch_match_rules.md
MATCH_RULE = 'src_db|dst_db|*'

# 校验参数
TOTAL_COUNT_THRESHOLD = 0.0


# ============================================================================
# [主流程]
# ============================================================================

def main() -> int:
    client = build_client()

    # 一键执行：创建任务 → 保存批次（含匹配规则） → 立即执行
    task_id, batch_id = run_batch_check(
        client,
        task_name='全库数据量批量校验',
        src_ds=SRC_DS,
        dst_ds=DST_DS,
        check_type=0,
        match_rule=MATCH_RULE,
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
