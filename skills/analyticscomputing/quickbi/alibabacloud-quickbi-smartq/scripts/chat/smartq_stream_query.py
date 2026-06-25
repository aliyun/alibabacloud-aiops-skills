# -*- coding: utf-8 -*-
"""
Quick BI 小Q问数：流式查询主入口。

负责 SSE 事件流的解析和编排，具体子任务委托给各专职模块：
- cube_resolver  — 数据集解析（智能选表 / 权限查询 / 相关性兜底）
- chart_renderer — 图表渲染 + Markdown 表格 fallback

SSE 流中的 olapResult 事件已直接包含取数结果，无需再调用 OLAP 接口。

用法：
    python3 scripts/smartq_stream_query.py "2023年的总销售额是多少" --cube-id "dcbb0f94-..."
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
    check_known_error_code,
)
from chat.cube_resolver import resolve_cube_id
from chat.chart_renderer import render_chart, chart_data_to_markdown
from common.config_loader import get_skill_output_dir, get_image_output_dir
from common.messages import msg, set_locale

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
# SSE param 事件处理（获取一些必要参数信息供后续链路使用）
# ---------------------------------------------------------------------------

def handle_param_event(event_data: dict) -> Optional[dict]:
    """
    处理 type=param 事件：
    1. 解析 param_data，获取 result 中的 info 信息
    2. 返回包含 question、cubeId、specificDsl、abstractDsl 等信息的字典
    """
    data_str = event_data.get("data", "")
    try:
        param_data = json.loads(data_str) if isinstance(
            data_str, str) else data_str
    except json.JSONDecodeError:
        print(msg("smartq_param_parse_error"), flush=True)
        return None

    result_info = param_data.get("result", {})
    info = result_info.get("info", {})

    # 提取关键信息
    result = {
        "question": info.get("question", ""),
        "cubeId": info.get("cubeId", 0),
        "specificDsl": info.get("specificDsl", ""),
        "abstractDsl": info.get("abstractDsl", ""),
    }

    return result

# ---------------------------------------------------------------------------
# SSE olapResult 事件处理（取数结果已内联在流中，无需再调用 OLAP 接口）
# ---------------------------------------------------------------------------

def _build_field_names_from_dsl(param_info_list: List[dict]) -> Optional[List[str]]:
    """
    从 param 事件的 DSL 中构建字段名列表。

    DSL 的 select 数组包含字段定义，根据 aggregate 和 calculate 生成语义化列名：
    - 只有 name → "销售平台"
    - name + aggregate: "SUM" → "销售额(SUM)"
    - name + aggregate: "SUM" + calculate: "proportion" → "销售额(SUM+proportion)"
    - name + aggregate: "AVG" → "价格(AVG)"
    - name + calculate: "proportion" → "占比(proportion)"

    示例 DSL select:
        [
            {"name": "销售平台", "calculate": "proportion"},
            {"name": "销售额",   "aggregate": "SUM"},
            {"name": "销售额",   "aggregate": "SUM", "calculate": "proportion"}
        ]

    Returns:
        字段名列表，如 ["销售平台", "销售额(SUM)", "销售额(SUM+proportion)"]
        如果无法解析则返回 None
    """
    if not param_info_list:
        return None

    # 从第一个 param_info 中获取 abstractDsl 或 specificDsl
    first_param = param_info_list[0]
    dsl_str = first_param.get("abstractDsl") or first_param.get("specificDsl")
    if not dsl_str:
        return None

    # 解析 DSL（可能是字符串或已经是 dict）
    try:
        dsl = json.loads(dsl_str) if isinstance(dsl_str, str) else dsl_str
    except (json.JSONDecodeError, ValueError):
        return None

    select_list = dsl.get("select")
    if not select_list or not isinstance(select_list, list):
        return None

    field_names = []
    for item in select_list:
        name = item.get("name", "")
        aggregate = item.get("aggregate", "")
        calculate = item.get("calculate", "")

        # 构建字段名：使用 DSL 原始值保持映射关系清晰
        if aggregate and calculate:
            # 既有聚合又有计算：销售额(SUM+proportion)
            field_names.append(f"{name}({aggregate}+{calculate})")
        elif aggregate:
            # 只有聚合：销售额(SUM)
            field_names.append(f"{name}({aggregate})")
        elif calculate:
            # 只有计算：占比(proportion)
            field_names.append(f"{name}({calculate})")
        else:
            # 只有名称：销售平台
            field_names.append(name)

    return field_names if field_names else None


def handle_olap_result_event(
    event_data: dict,
    *,
    question: str = "",
    param_info_list: Optional[List[dict]] = None,
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
        print(msg("smartq_olap_parse_error"), flush=True)
        return None

    values = olap_result.get("values") or []
    meta_type_list = olap_result.get("metaType") or []
    chart_type_raw = olap_result.get("chartType", "")
    logic_sql = olap_result.get("logicSql", "")

    chart_type = OLAP_CHART_TYPE_MAP.get(chart_type_raw, "bar")

    print(f"\n{'=' * 60}", flush=True)
    print(msg("smartq_olap_result", chart_type=chart_type, raw_type=chart_type_raw), flush=True)
    print(msg("smartq_olap_rows", count=len(values)), flush=True)
    print(f"{'=' * 60}", flush=True)

    if logic_sql:
        print(f"\n[SQL] {logic_sql}", flush=True)

    if not values or not meta_type_list:
        print(f"\n**{question or msg('smartq_query_result_default')}**\n\n{msg('smartq_no_data')}", flush=True)
        return None

    # 从 DSL 构建字段名，失败则降级到 metaType.k
    field_names = _build_field_names_from_dsl(param_info_list or [])

    field_info: List[Dict[str, Any]] = []
    for idx, meta in enumerate(meta_type_list):
        meta_v = meta.get("v", "string")
        meta_t = meta.get("t", "")
        meta_type_val = meta.get("type", "")

        if meta_t:
            role = "metric" if meta_t.lower() == "measure" else "dimension"
        else:
            role = "metric" if meta_type_val == "column" else "dimension"

        # 使用 DSL/SQL 提取的字段名，如果超出范围则降级到 metaType.k
        if idx < len(field_names) and field_names[idx]:
            field_name = field_names[idx]
        else:
            field_name = meta.get("k", "")

        field_info.append({
            "fieldName": field_name,
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

    print(msg("smartq_field_row_count", fields=len(field_info), rows=len(data_rows)), flush=True)

    # 统计度量列数量
    metric_count = sum(1 for f in field_info if f.get("role") == "metric")

    if chart_type == "table" and metric_count == 1:
        # table 类型且仅一个度量列：同时输出图表图片和 Markdown 表格
        output_dir = str(get_image_output_dir())
        # 临时将 chartType 改为 bar 以便渲染图片
        chart_data_for_render = {**chart_data, "chartType": "bar"}
        chart_path = render_chart(chart_data_for_render, output_dir=output_dir)
        if chart_path:
            chart_title = chart_data.get("title", msg("smartq_chart_default_title"))
            print(f"\n[{chart_title}]({chart_path})", flush=True)
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
            chart_title = chart_data.get("title", msg("smartq_chart_default_title"))
            print(f"\n[{chart_title}]({chart_path})", flush=True)
        else:
            md_table = chart_data_to_markdown(chart_data)
            print(f"\n{md_table}", flush=True)

    return chart_data


# ---------------------------------------------------------------------------
# 保存query取数结果
# ---------------------------------------------------------------------------

def save_query_result(
    question: str,
    cube_id: str,
    chart_results: List[dict],
    param_info_list: List[dict],
) -> str:
    """
    整合问数结果并保存为 JSON 文件。

    Args:
        question: 用户问题
        cube_id: 数据集 ID
        chart_results: 图表结果列表
        param_info_list: 参数信息列表

    Returns:
        保存的文件路径
    """

    def _parse_string_json(value: Any) -> Any:
        """
        解析 DSL 值：如果是字符串则尝试解析为 JSON，否则原样返回。
        """
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    if not chart_results:
        return ""

    # 构建 charts 数组
    charts = []
    for idx, chart in enumerate(chart_results):
        # 获取对应的 param_info（如果有的话）
        current_param = param_info_list[idx] if idx < len(
            param_info_list) else {}

        chart_entry = {
            "id": chart.get("id", f"olap_{int(time.time())}"),
            "title": chart.get("title", ""),
            "chartType": chart.get("chartType", ""),
            "data": chart.get("data", []),
            "fieldInfo": chart.get("fieldInfo", []),
            "logicBlock": {
                "specificDsl": _parse_string_json(current_param.get("specificDsl", "")),
                "abstractDsl": _parse_string_json(current_param.get("abstractDsl", "")),
            }
        }
        charts.append(chart_entry)

    # 构建最终结果
    result_data = {
        "question": question,
        "cube_id": cube_id,
        "charts": charts
    }

    # 保存 JSON 文件
    if result_data:
        output_dir = get_skill_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"query_result_{int(time.time())}.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            print(msg("smartq_query_saved", path=output_file), flush=True)
        except Exception as e:
            print(msg("smartq_query_save_failed", exc=e), flush=True)

# ---------------------------------------------------------------------------
# 流式问数主流程
# ---------------------------------------------------------------------------

def run_stream_query(
    question: str,
    cube_id: Optional[str] = None,
    *,
    name_hint: Optional[str] = None,
    cube_ids: Optional[List[str]] = None,
    locale: str,
    config: Optional[dict] = None,
):
    """
    执行流式问数的完整流程。

    当 cube_id 未提供时，委托 cube_resolver.resolve_cube_id 自动解析数据集。
    若同时提供了 name_hint，则先尝试名称直查，精确匹配时跳过智能选表。
    """
    config = config or read_config()
    user_id = require_user_id(config)

    if not cube_id:
        cube_id = resolve_cube_id(question, name_hint=name_hint, cube_ids=cube_ids, config=config)
        if not cube_id:
            print(msg("smartq_terminated"), flush=True)
            return []
        print(flush=True)

    payload: Dict[str, Any] = {
        "userQuestion": question,
        "userId": user_id,
        "cubeId": cube_id,
        "llmNameForData": "nvl",
        "llmNameForInference": "nvl",
        "runningBySkill": True,
        "locale": locale,
    }

    print(f"{'=' * 60}", flush=True)
    print(msg("smartq_header", question=question), flush=True)
    print(msg("smartq_dataset", cube_id=cube_id), flush=True)
    print(msg("smartq_locale", locale=locale), flush=True)
    print(f"{'=' * 60}\n", flush=True)

    uri = "/openapi/v2/smartq/queryByQuestionStream"

    related_info_buf: List[str] = []
    reasoning_buf: List[str] = []
    sql_buf: List[str] = []
    summary_buf: List[str] = []
    text_buf: List[str] = []
    conclusion_buf: List[str] = []
    check_buf: List[str] = []
    chart_results: List[dict] = []
    param_info_list: List[dict] = []
    trace_id: Optional[str] = None

    def _flush_buffers():
        """输出已缓冲的流式事件文本。

        采用 buffer-then-flush 模式：SSE 事件是 token-by-token 推送的，
        若每个 token 独占一行会造成超过数十行的终端输出。在调用者需要
        看到完整文本的边界（olapResult / finish）才 flush，将同一类型事件的
        所有 token 合并为一行输出。
        """
        nonlocal related_info_buf, reasoning_buf, sql_buf
        nonlocal text_buf, conclusion_buf, check_buf
        if related_info_buf:
            print(msg("smartq_related_info", data=''.join(related_info_buf)), flush=True)
            related_info_buf.clear()
        if reasoning_buf:
            print(msg("smartq_reasoning", data=''.join(reasoning_buf)), flush=True)
            reasoning_buf.clear()
        if sql_buf:
            print(msg("smartq_sql", data=''.join(sql_buf)), flush=True)
            sql_buf.clear()
        if text_buf:
            print(msg("smartq_text", data=''.join(text_buf)), flush=True)
            text_buf.clear()
        if conclusion_buf:
            print(msg("smartq_conclusion", data=''.join(conclusion_buf)), flush=True)
            conclusion_buf.clear()
        if check_buf:
            print(msg("smartq_check", data=''.join(check_buf)), flush=True)
            check_buf.clear()

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
                text_buf.append(str(data))

            elif event_type == "sql":
                sql_buf.append(str(data))

            elif event_type == "olapResult":
                _flush_buffers()
                chart_data = handle_olap_result_event(
                    event_data, question=question, param_info_list=param_info_list,
                )
                if chart_data:
                    chart_results.append(chart_data)

            elif event_type == "summary":
                summary_buf.append(str(data))

            elif event_type == "conclusion":
                conclusion_buf.append(str(data))

            elif event_type == "check":
                check_buf.append(str(data))

            elif event_type == "error":
                print(msg("smartq_error", data=data), flush=True)
                check_known_error_code(str(data))

            elif event_type == "param":
                saved_param_info = handle_param_event(event_data)
                if saved_param_info:
                    print(msg("smartq_param_info", data=saved_param_info), flush=True)
                    param_info_list.append(saved_param_info)

            elif event_type in ("dsl", "answer", "feedback", "python"):
                pass

            elif event_type == "finish":
                _flush_buffers()
                if summary_buf:
                    print(msg("smartq_summary", data=''.join(summary_buf)), flush=True)
                print(msg("smartq_finish", data=data), flush=True)
                break
    except Exception as e:
        print(msg("smartq_stream_failed", uri=uri, exc=e), flush=True)
        check_known_error_code(str(e))
        return chart_results

    print(f"\n{'=' * 60}", flush=True)
    print(msg("smartq_end", count=len(chart_results)), flush=True)
    if trace_id:
        print(msg("smartq_trace_id", trace_id=trace_id), flush=True)

    # 保存query结果 保存至query_result_XX.json
    if chart_results:
        save_query_result(question, cube_id, chart_results, param_info_list)

    print(f"{'=' * 60}", flush=True)

    return chart_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Quick BI 小Q问数")
    parser.add_argument("question", help="用户问题")
    parser.add_argument("--cube-id", dest="cube_id", default=None, help="数据集 ID（不指定时自动智能选表）")
    parser.add_argument("--cube-name", dest="cube_name", default=None, help="数据集名称提示（用于名称直查，精确匹配时跳过智能选表）")
    parser.add_argument("--cube-ids", dest="cube_ids", default=None, help="候选数据集 ID 列表，逗号分隔（仅智能选表时使用）")
    parser.add_argument("--locale", required=True, choices=["zh_CN", "en_US"], help="语言环境: zh_CN(简体中文) 或 en_US(英文)")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    args = parser.parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    set_locale(args.locale)
    cube_ids = args.cube_ids.split(",") if args.cube_ids else None
    chart_results = run_stream_query(args.question, args.cube_id, name_hint=args.cube_name, cube_ids=cube_ids, locale=args.locale)
    
    # CLI 模式下，返回值已通过文件保存并输出路径到控制台
    # 如需进一步处理，可使用 chart_results 变量


if __name__ == "__main__":
    main()
