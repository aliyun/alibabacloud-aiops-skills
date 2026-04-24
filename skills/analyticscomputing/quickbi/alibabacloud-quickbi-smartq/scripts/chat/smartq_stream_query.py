# -*- coding: utf-8 -*-
"""
Quick BI 小Q问数：流式查询主入口。

负责 SSE 事件流的解析和编排，具体子任务委托给各专职模块：
- cube_resolver  — 数据集解析（智能选表 / 权限查询 / 相关性兜底）
- chart_renderer — 图表渲染 + Markdown 表格 fallback

SSE 流中的 olapResult 事件已直接包含取数结果，无需再调用 OLAP 接口。

用法：
    python scripts/smartq_stream_query.py "2023年的总销售额是多少" --cube-id "dcbb0f94-..."
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import (
    read_config,
    require_user_id,
    request_openapi_stream,
    parse_sse_event,
    check_trial_expired,
)
from chat.cube_resolver import resolve_cube_id
from chat.chart_renderer import render_chart, chart_data_to_markdown
from common.config_loader import get_skill_output_dir, get_image_output_dir

# olapResult 事件中的 chartType 枚举 → chart_renderer 可识别的图表类型
OLAP_CHART_TYPE_MAP = {
    "NEW_TABLE": "table",
    "BAR": "bar",
    "LINE": "line",
    "PIE": "pie",
    "SCATTER_NEW": "scatter",
    "INDICATOR_CARD": "indicator-card",
    "RANKING_LIST": "ranking-list",
    "DETAIL_TABLE": "table",
    "MAP_COLOR_NEW": "bar",
    "PROGRESS_NEW": "horizontal_bar",
    "FUNNEL_NEW": "funnel",
}

# olapResult metaType 中的数据类型 → fieldInfo 标准类型
DATA_TYPE_MAP = {
    "number": "numerical",
    "string": "string",
    "date": "time",
    "datetime": "time",
    "boolean": "string",
}


# ---------------------------------------------------------------------------
# SSE olapResult 事件处理（取数结果已内联在流中，无需再调用 OLAP 接口）
# ---------------------------------------------------------------------------

def handle_olap_result_event(
    event_data: dict,
    *,
    question: str = "",
) -> Optional[dict]:
    """
    处理 type=olapResult 事件：SSE 流已直接返回取数结果，
    将其转换为 chart_renderer 所需的 chart_data 格式并渲染图表。

    olapResult 数据格式::

        {
            "values": [{"row": ["val1", "val2"]}, ...],
            "chartType": "RANKING_LIST",
            "metaType": [{"v": "string", "k": "字段名", "type": "row", "t": "dimension"}, ...],
            "logicSql": "SELECT ...",
            "conclusionText": "..."
        }
    """
    data_str = event_data.get("data", "")
    try:
        olap_result = json.loads(data_str) if isinstance(data_str, str) else data_str
    except json.JSONDecodeError:
        print("  [olapResult] 无法解析 data JSON", flush=True)
        return None

    values = olap_result.get("values") or []
    meta_type_list = olap_result.get("metaType") or []
    chart_type_raw = olap_result.get("chartType", "")
    logic_sql = olap_result.get("logicSql", "")

    chart_type = OLAP_CHART_TYPE_MAP.get(chart_type_raw, "bar")

    print(f"\n{'=' * 60}", flush=True)
    print(f"[取数结果] 图表类型: {chart_type} ({chart_type_raw})", flush=True)
    print(f"[取数结果] 数据行数: {len(values)}", flush=True)
    print(f"{'=' * 60}", flush=True)

    if logic_sql:
        print(f"\n[SQL] {logic_sql}", flush=True)

    if not values or not meta_type_list:
        print(f"\n**{question or '查询结果'}**\n\n（无数据）", flush=True)
        return None

    field_info: List[Dict[str, Any]] = []
    for meta in meta_type_list:
        meta_v = meta.get("v", "string")
        meta_t = meta.get("t", "")
        meta_type_val = meta.get("type", "")

        if meta_t:
            role = "metric" if meta_t.lower() == "measure" else "dimension"
        else:
            role = "metric" if meta_type_val == "column" else "dimension"

        field_info.append({
            "fieldName": meta.get("k", ""),
            "type": DATA_TYPE_MAP.get(meta_v, "string"),
            "role": role,
        })

    data_rows: List[Dict[str, Any]] = []
    for val_item in values:
        row_values = val_item.get("row") or []
        row_dict: Dict[str, Any] = {}
        for i, field in enumerate(field_info):
            if i < len(row_values):
                raw_val = row_values[i]
                if field["type"] == "numerical" and raw_val is not None:
                    try:
                        row_dict[field["fieldName"]] = float(raw_val)
                    except (ValueError, TypeError):
                        row_dict[field["fieldName"]] = raw_val
                else:
                    row_dict[field["fieldName"]] = raw_val
            else:
                row_dict[field["fieldName"]] = ""
        data_rows.append(row_dict)

    chart_data: Dict[str, Any] = {
        "data": data_rows,
        "fieldInfo": field_info,
        "chartType": chart_type,
        "title": question,
        "id": f"olap_{int(time.time())}",
    }

    print(f"  字段数: {len(field_info)}, 数据行数: {len(data_rows)}", flush=True)

    # 统计度量列数量
    metric_count = sum(1 for f in field_info if f.get("role") == "metric")

    if chart_type == "table" and metric_count == 1:
        # table 类型且仅一个度量列：同时输出图表图片和 Markdown 表格
        output_dir = str(get_image_output_dir())
        # 临时将 chartType 改为 bar 以便渲染图片
        chart_data_for_render = {**chart_data, "chartType": "bar"}
        chart_path = render_chart(chart_data_for_render, output_dir=output_dir)
        if chart_path:
            chart_title = chart_data.get("title", "图表")
            print(f"\n![{chart_title}]({chart_path})", flush=True)
        md_table = chart_data_to_markdown(chart_data)
        print(f"\n{md_table}", flush=True)
    elif chart_type == "table":
        # table 类型且多个度量列：仅输出 Markdown 表格
        md_table = chart_data_to_markdown(chart_data)
        print(f"\n{md_table}", flush=True)
    else:
        output_dir = str(get_image_output_dir())
        chart_path = render_chart(chart_data, output_dir=output_dir)
        if chart_path:
            chart_title = chart_data.get("title", "图表")
            print(f"\n![{chart_title}]({chart_path})", flush=True)
        else:
            md_table = chart_data_to_markdown(chart_data)
            print(f"\n{md_table}", flush=True)

    return chart_data


# ---------------------------------------------------------------------------
# 流式问数主流程
# ---------------------------------------------------------------------------

def run_stream_query(
    question: str,
    cube_id: Optional[str] = None,
    *,
    cube_ids: Optional[List[str]] = None,
    config: Optional[dict] = None,
):
    """
    执行流式问数的完整流程。

    当 cube_id 未提供时，委托 cube_resolver.resolve_cube_id 自动解析数据集。
    """
    config = config or read_config()
    user_id = require_user_id(config)

    if not cube_id:
        cube_id = resolve_cube_id(question, cube_ids=cube_ids, config=config)
        if not cube_id:
            print("\n[数据集问数终止] 未能匹配到可用数据集，请参考上方提示选择其他方式。", flush=True)
            return []
        print(flush=True)

    payload: Dict[str, Any] = {
        "userQuestion": question,
        "userId": user_id,
        "cubeId": cube_id,
        "llmNameForData": "nvl",
        "llmNameForInference": "nvl",
        "runningBySkill": True,
    }

    print(f"{'=' * 60}", flush=True)
    print(f"[小Q问数] 问题: {question}", flush=True)
    print(f"[小Q问数] 数据集: {cube_id}", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    uri = "/openapi/v2/smartq/queryByQuestionStream"

    related_info_buf: List[str] = []
    reasoning_buf: List[str] = []
    sql_buf: List[str] = []
    summary_buf: List[str] = []
    chart_results: List[dict] = []
    trace_id: Optional[str] = None

    def _flush_buffers():
        """输出已缓冲的关联知识、推理过程和 SQL。"""
        nonlocal related_info_buf, reasoning_buf, sql_buf
        if related_info_buf:
            print(f"\n[关联知识] {''.join(related_info_buf)}", flush=True)
            related_info_buf.clear()
        if reasoning_buf:
            print(f"\n[推理过程] {''.join(reasoning_buf)}", flush=True)
            reasoning_buf.clear()
        if sql_buf:
            print(f"\n[SQL] {''.join(sql_buf)}", flush=True)
            sql_buf.clear()

    try:
        for raw_event in request_openapi_stream(uri, json_body=payload, config=config, timeout=600):
            event_data = parse_sse_event(raw_event)
            if not event_data:
                continue

            event_type = event_data.get("type", "")
            data = event_data.get("data", "")

            if event_type in ("heartbeat", "locale", "message"):
                continue

            elif event_type == "trace":
                trace_id = str(data)
                print(f"[Trace] {trace_id}", flush=True)

            elif event_type == "relatedInfo":
                related_info_buf.append(str(data))

            elif event_type == "reasoning":
                reasoning_buf.append(str(data))

            elif event_type == "text":
                print(f"[文本] {data}", flush=True)

            elif event_type == "sql":
                sql_buf.append(str(data))

            elif event_type == "olapResult":
                _flush_buffers()
                chart_data = handle_olap_result_event(
                    event_data, question=question,
                )
                if chart_data:
                    chart_results.append(chart_data)

            elif event_type == "summary":
                summary_buf.append(str(data))

            elif event_type == "conclusion":
                print(f"\n[结论] {data}", flush=True)

            elif event_type == "check":
                print(f"\n[校验] {data}", flush=True)

            elif event_type == "error":
                print(f"\n[错误] {data}", flush=True)
                check_trial_expired(str(data))

            elif event_type in ("dsl", "answer", "param", "feedback", "python"):
                pass

            elif event_type == "finish":
                _flush_buffers()
                if summary_buf:
                    print(f"\n[数据解读] {''.join(summary_buf)}", flush=True)
                print(f"\n[完成] {data}", flush=True)
                break
    except Exception as e:
        print(f"\n[问数流式请求失败] POST {uri} 调用异常:\n  {e}", flush=True)
        check_trial_expired(str(e))
        return chart_results

    print(f"\n{'=' * 60}", flush=True)
    print(f"[问数结束] 共生成 {len(chart_results)} 个图表", flush=True)
    if trace_id:
        print(f"[Trace ID] {trace_id}（问题反馈时请提供此 ID）", flush=True)
    
    # 将图表数据保存到 JSON 文件
    if chart_results:
        output_dir = get_skill_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        chart_data_file = output_dir / f"chart_results_{int(time.time())}.json"
        try:
            with open(chart_data_file, 'w', encoding='utf-8') as f:
                json.dump(chart_results, f, ensure_ascii=False, indent=2)
            print(f"[图表数据] 已保存到: {chart_data_file}", flush=True)
        except Exception as e:
            print(f"[警告] 图表数据保存失败: {e}", flush=True)
    
    print(f"{'=' * 60}", flush=True)

    return chart_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Quick BI 小Q问数")
    parser.add_argument("question", help="用户问题")
    parser.add_argument("--cube-id", dest="cube_id", default=None, help="数据集 ID（不指定时自动智能选表）")
    parser.add_argument("--cube-ids", dest="cube_ids", default=None, help="候选数据集 ID 列表，逗号分隔（仅智能选表时使用）")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    args = parser.parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    cube_ids = args.cube_ids.split(",") if args.cube_ids else None
    chart_results = run_stream_query(args.question, args.cube_id, cube_ids=cube_ids)
    
    # CLI 模式下，返回值已通过文件保存并输出路径到控制台
    # 如需进一步处理，可使用 chart_results 变量


if __name__ == "__main__":
    main()
