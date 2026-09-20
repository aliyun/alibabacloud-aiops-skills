# -*- coding: utf-8 -*-
"""
报告格式化器

将 LHM SDK 返回的原始数据对象转换为 Markdown 表格，便于在对话、文档或
日志中直接阅读。

本模块不依赖网络调用，仅做数据展示格式化；所有输入均为 plain dict 或
SDK 返回的 data model（可用属性访问）。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Union


# ============================================================================
# 轻量常量（避免循环依赖 common.py）
# ============================================================================

EXEC_STATUS_TEXT = {
    0: 'TODO', 1: 'RUNNING', 2: 'STOPPED', 3: 'FAILED', 4: 'FINISHED',
}
CHECK_RESULT_TEXT = {
    0: 'NO_RECORD', 1: 'PASSED', 2: 'FAILED',
}
CHECK_TYPE_TEXT = {
    0: '数据量', 1: '指标', 2: '弱内容',
}


# ============================================================================
# 私有工具
# ============================================================================

def _get(obj: Any, key: str, default: Any = None) -> Any:
    """同时支持 dict 与 object 属性访问。"""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _fmt_number(value: Any) -> str:
    """格式化整数/浮点数；无法识别时返回原字符串或 '-'。"""
    if value is None:
        return '-'
    if isinstance(value, bool):
        return '是' if value else '否'
    if isinstance(value, int):
        return f'{value:,}'
    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            return f'{int(round(value)):,}'
        return f'{value:,.2f}'
    s = str(value).strip()
    return s if s else '-'


def _fmt_percent(value: Any) -> str:
    """格式化百分比。SDK 有时返回 '88.46%' 字符串，有时是 0.8846 浮点数。"""
    if value is None:
        return '-'
    if isinstance(value, str):
        s = value.strip()
        if s.endswith('%'):
            return s
        try:
            v = float(s)
            return f'{v * 100:.2f}%' if v <= 1 else f'{v:.2f}%'
        except ValueError:
            return s if s else '-'
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value <= 1.0:
            return f'{value * 100:.2f}%'
        return f'{value:.2f}%'
    return str(value)


def _text_status(exec_status: Any) -> str:
    if exec_status is None:
        return '-'
    return f"{exec_status}({EXEC_STATUS_TEXT.get(exec_status, '?')})"


def _text_check_result(check_result: Any) -> str:
    if check_result is None:
        return '-'
    return f"{check_result}({CHECK_RESULT_TEXT.get(check_result, '?')})"


def _make_table(headers: list[str], rows: list[list[str]]) -> str:
    """生成标准 Markdown 表格。"""
    if not rows:
        return ''
    lines = [
        '| ' + ' | '.join(headers) + ' |',
        '|' + '|'.join(['---'] * len(headers)) + '|',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(lines)


# ============================================================================
# 公共接口
# ============================================================================

def format_batch_summary(
    batch_summary: Mapping[str, Any],
    report_url: Optional[str] = None,
) -> str:
    """
    将 summarize_batch() 返回的 dict 格式化为 Markdown 概览表格。

    Args:
        batch_summary: 批次概况字典，典型字段：
            task_name, template, total_tables, pass_tables, fail_tables,
            skip_tables, pass_rate, column_pass_rate, diff_rate,
            exec_status, check_result
        report_url: 可选的 OSS 报告下载链接，会追加到表格末尾

    Returns:
        Markdown 字符串
    """
    total = _get(batch_summary, 'total_tables', 0) or 0
    passed = _get(batch_summary, 'pass_tables', 0) or 0
    failed = _get(batch_summary, 'fail_tables', 0) or 0
    skipped = _get(batch_summary, 'skip_tables')
    if skipped is None and total > 0:
        skipped = max(0, total - passed - failed)

    rows = [
        ['任务名称', str(_get(batch_summary, 'task_name', '-'))],
        ['校验模板', str(_get(batch_summary, 'template', '-') or '-')],
        ['总表数', _fmt_number(total)],
        ['通过表数', _fmt_number(passed)],
        ['失败表数', _fmt_number(failed)],
        ['跳过表数', _fmt_number(skipped)],
        ['表通过率', _fmt_percent(_get(batch_summary, 'pass_rate'))],
        ['字段一致率', _fmt_percent(_get(batch_summary, 'column_pass_rate'))],
        ['差异率', _fmt_percent(_get(batch_summary, 'diff_rate'))],
        ['执行状态', _text_status(_get(batch_summary, 'exec_status'))],
        ['校验结果', _text_check_result(_get(batch_summary, 'check_result'))],
    ]
    check_columns = _get(batch_summary, 'check_columns')
    pass_columns = _get(batch_summary, 'pass_columns')
    if check_columns is not None:
        rows.insert(7, ['校验字段数', _fmt_number(check_columns)])
    if pass_columns is not None:
        rows.insert(8, ['通过字段数', _fmt_number(pass_columns)])
    if report_url:
        rows.append(['报告链接', f'[下载报告]({report_url})'])

    return _make_table(['项目', '数值'], rows)


def format_table_list(
    tables: Iterable[Any],
    group_by: str = 'result',
) -> str:
    """
    将 list_data_check_report 返回的表级结果格式化为 Markdown 表格。

    Args:
        tables: 可迭代的表结果对象（或 dict），支持属性/字典访问
        group_by: 分组方式，目前支持 'result'（按通过/失败分组）

    Returns:
        Markdown 字符串
    """
    items = []
    for t in tables or []:
        check_result = _get(t, 'check_result')
        is_consistent = _get(t, 'is_consistent')
        if check_result == 1 or is_consistent == 1:
            result_text = 'PASSED'
        elif check_result == 2 or is_consistent == 0:
            result_text = 'FAILED'
        else:
            result_text = CHECK_RESULT_TEXT.get(check_result, '-')

        src_count = _get(t, 'source_count')
        dst_count = _get(t, 'target_count')
        # 有些接口把行数放在 step 里，表级可能为空
        if src_count is None:
            src_count = _get(t, 'src_count')
        if dst_count is None:
            dst_count = _get(t, 'dst_count')

        diff = '-'
        if isinstance(src_count, (int, float)) and isinstance(dst_count, (int, float)):
            diff = _fmt_number(dst_count - src_count)

        items.append({
            'source_table': _get(t, 'source_table', '-'),
            'target_table': _get(t, 'target_table', '-'),
            'src_count': _fmt_number(src_count),
            'dst_count': _fmt_number(dst_count),
            'diff': diff,
            'diff_rate': _fmt_percent(_get(t, 'diff_rate')),
            'result': result_text,
            'err_message': _get(t, 'err_message', '-'),
        })

    if not items:
        return '暂无表级结果。'

    if group_by == 'result':
        groups = {'PASSED': [], 'FAILED': [], '其他': []}
        for it in items:
            groups.get(it['result'], groups['其他']).append(it)

        parts = []
        for name in ('PASSED', 'FAILED', '其他'):
            group_items = groups[name]
            if not group_items:
                continue
            parts.append(f"**{name}**（{len(group_items)} 张）")
            parts.append(_table_items(group_items))
        return '\n\n'.join(parts)

    return _table_items(items)


def _table_items(items: list[dict]) -> str:
    headers = ['源表', '目标表', '源行数', '目标行数', '差异', '差异率', '结果', '说明']
    rows = [
        [
            it['source_table'],
            it['target_table'],
            it['src_count'],
            it['dst_count'],
            it['diff'],
            it['diff_rate'],
            it['result'],
            it['err_message'],
        ]
        for it in items
    ]
    return _make_table(headers, rows)


def format_diagnosis_report(
    diagnosis: Union[list[dict], dict[str, Any]],
    show_passed: bool = False,
    max_detail_rows: int = 50,
) -> str:
    """
    将 diagnose_failed() 的输出格式化为 Markdown 诊断报告。

    Args:
        diagnosis: diagnose_failed() 返回的扁平列表或按字段分组的字典
        show_passed: 是否展示通过项（默认只展示失败/不一致）
        max_detail_rows: 单个表格最大行数，超出时追加提示

    Returns:
        Markdown 字符串
    """
    if isinstance(diagnosis, Mapping):
        return _format_grouped_diagnosis(diagnosis, show_passed, max_detail_rows)
    return _format_flat_diagnosis(diagnosis or [], show_passed, max_detail_rows)


def _format_flat_diagnosis(
    diagnosis: list[dict],
    show_passed: bool,
    max_detail_rows: int,
) -> str:
    if not diagnosis:
        return '诊断结果为空，暂无失败表或差异明细。'

    # 默认过滤掉通过项
    if not show_passed:
        filtered = []
        for it in diagnosis:
            detail = it.get('detail', {})
            is_consistent = detail.get('is_consistent')
            if is_consistent != 1:
                filtered.append(it)
        diagnosis = filtered

    if not diagnosis:
        return '所有检查项均已通过。'

    # 按表聚合
    tables: dict[str, list[dict]] = {}
    for it in diagnosis:
        tables.setdefault(it.get('table', '-'), []).append(it)

    parts = [f"**共发现 {len(tables)} 张表存在差异/异常**\n"]

    total_rows = 0
    for table, items in tables.items():
        parts.append(f"\n### {table}")

        step_rows = []
        col_rows = []
        for it in items:
            detail = it.get('detail', {})
            if it.get('type') == 'STEP':
                src = _fmt_number(detail.get('src_count'))
                dst = _fmt_number(detail.get('dst_count'))
                diff = '-'
                if detail.get('src_count') is not None and detail.get('dst_count') is not None:
                    diff = _fmt_number(detail['dst_count'] - detail['src_count'])
                step_rows.append([
                    detail.get('source_pt_name', '-'),
                    detail.get('target_pt_name', '-'),
                    src,
                    dst,
                    diff,
                    '一致' if detail.get('is_consistent') == 1 else '不一致',
                    detail.get('err_message', '-'),
                ])
            elif it.get('type') == 'COLUMN':
                col_rows.append([
                    detail.get('column', '-'),
                    detail.get('metric', '-'),
                    str(detail.get('src_result', '-')),
                    str(detail.get('dst_result', '-')),
                    _fmt_percent(detail.get('actual_threshold')),
                    '一致' if detail.get('is_consistent') == 1 else '不一致',
                ])

        if step_rows:
            parts.append("**Step 明细**")
            parts.append(_make_table(
                ['源分区', '目标分区', '源计数', '目标计数', '差异', '结果', '错误信息'],
                step_rows[:max_detail_rows],
            ))
            total_rows += len(step_rows)
            if len(step_rows) > max_detail_rows:
                parts.append(f"\n> 仅展示前 {max_detail_rows} 条 Step 记录，完整数据请下载报告。")

        if col_rows:
            parts.append("**字段指标明细**")
            parts.append(_make_table(
                ['字段', '指标', '源结果', '目标结果', '实际阈值', '结果'],
                col_rows[:max_detail_rows],
            ))
            total_rows += len(col_rows)
            if len(col_rows) > max_detail_rows:
                parts.append(f"\n> 仅展示前 {max_detail_rows} 条字段记录，完整数据请下载报告。")

        parts.append(_advice_for_table(table, items))

    return '\n'.join(parts)


def _format_grouped_diagnosis(
    grouped: Mapping[str, Any],
    show_passed: bool,
    max_detail_rows: int,
) -> str:
    if not grouped:
        return '诊断结果为空。'

    parts = [f"**共发现 {len(grouped)} 张表存在差异**\n"]
    for table, data in grouped.items():
        summary = _get(data, 'summary', {})
        steps = _get(data, 'steps', [])
        columns = _get(data, 'columns', {})

        total = _get(summary, 'total', 0) or 0
        fail = _get(summary, 'fail', 0) or 0
        pass_ = _get(summary, 'pass', 0) or 0

        parts.append(f"\n### {table}")
        parts.append(_make_table(
            ['总字段数', '通过字段数', '失败字段数'],
            [[_fmt_number(total), _fmt_number(pass_), _fmt_number(fail)]],
        ))

        # Step 信息
        if steps:
            step_rows = []
            for s in steps[:max_detail_rows]:
                src = _fmt_number(_get(s, 'src_count'))
                dst = _fmt_number(_get(s, 'dst_count'))
                diff = '-'
                if _get(s, 'src_count') is not None and _get(s, 'dst_count') is not None:
                    diff = _fmt_number(_get(s, 'dst_count') - _get(s, 'src_count'))
                step_rows.append([
                    _get(s, 'source_pt_name', '-'),
                    _get(s, 'target_pt_name', '-'),
                    src,
                    dst,
                    diff,
                    '一致' if _get(s, 'is_consistent') == 1 else '不一致',
                    _get(s, 'err_message', '-'),
                ])
            parts.append("**Step 明细**")
            parts.append(_make_table(
                ['源分区', '目标分区', '源计数', '目标计数', '差异', '结果', '错误信息'],
                step_rows,
            ))
            if len(steps) > max_detail_rows:
                parts.append(f"\n> 仅展示前 {max_detail_rows} 条 Step 记录。")

        # 字段分组
        if columns:
            col_rows = []
            for field, field_info in columns.items():
                metrics = _get(field_info, 'metrics', [])
                pass_n = _get(field_info, 'pass', 0)
                fail_n = _get(field_info, 'fail', 0)
                # 合并显示该字段下的指标
                metric_names = ', '.join(
                    str(_get(m, 'metric', '-')) for m in metrics[:3]
                )
                if len(metrics) > 3:
                    metric_names += ' ...'
                col_rows.append([
                    field,
                    _fmt_number(pass_n),
                    _fmt_number(fail_n),
                    metric_names,
                ])
            parts.append("**字段差异汇总**")
            parts.append(_make_table(
                ['字段', '通过指标数', '失败指标数', '涉及指标'],
                col_rows[:max_detail_rows],
            ))
            if len(col_rows) > max_detail_rows:
                parts.append(f"\n> 仅展示前 {max_detail_rows} 个字段。")

        # 生成建议
        flat_items = []
        for s in steps:
            flat_items.append({'type': 'STEP', 'detail': s})
        for field_info in columns.values():
            for m in _get(field_info, 'metrics', []):
                flat_items.append({'type': 'COLUMN', 'detail': m, 'table': table})
        parts.append(_advice_for_table(table, flat_items))

    return '\n'.join(parts)


def _advice_for_table(table: str, items: list[dict]) -> str:
    """针对单表差异生成简单的下一步建议。"""
    has_count_diff = False
    has_metric_diff = False
    for it in items:
        if it.get('type') == 'STEP':
            d = it.get('detail', {})
            src = d.get('src_count')
            dst = d.get('dst_count')
            if src is not None and dst is not None and src != dst:
                has_count_diff = True
        elif it.get('type') == 'COLUMN':
            has_metric_diff = True

    advice = ["\n**建议操作**："]
    if has_count_diff:
        advice.append(
            f"- `{table}` 源/目标行数不一致，建议检查对应分区的生成时间、"
            "同步链路延迟或增量同步遗漏。"
        )
    if has_metric_diff:
        advice.append(
            f"- `{table}` 存在字段级指标差异，建议逐字段核对聚合结果，"
            "必要时跑弱内容校验或自定义 SQL 二次定位。"
        )
    if not has_count_diff and not has_metric_diff:
        advice.append(
            f"- `{table}` 暂未定位到具体差异，建议查看完整报告或 Step 错误信息。"
        )
    return '\n'.join(advice)
