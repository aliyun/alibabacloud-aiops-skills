#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 dashboardData 中的纯机械型大表渲染为 Markdown 片段。

渲染三块内容：
1. 数据集列表（按 sourceId groupby chartComponents，统计关联图表数，自动推断主要用途）
2. 字段映射（从 dashboardData.fieldMapping 直接遍历，按数据集分章节）
3. 图表组件完整列表（12 列表格，全部由脚本推断填充，含分析主题和分析层级）

不渲染：
- 意图路由矩阵（涉及关键词归纳，仍由 LLM 生成）

调用方式：
    # 作为模块
    from render_skill_sections import render_dataset_list, render_field_mapping, render_chart_components_table
    md_dataset = render_dataset_list(dashboardData, datasetNameMap=datasetNameMap)
    md_field   = render_field_mapping(dashboardData, datasetNameMap)
    md_charts  = render_chart_components_table(dashboardData)

    # 作为 CLI（stdin JSON → stdout JSON）
    cat input.json | python3 render_skill_sections.py
    # input.json = {"dashboardData": {...}, "datasetNameMap": {...}, "lang": "zh"|"en"}
    # 输出     = {"dataset_list_md": "...", "field_mapping_md": "...", "chart_components_md": "..."}
"""

import json
import sys
from collections import Counter
from typing import Any, Optional


# ---------- 数据集列表渲染 ----------

def render_dataset_list(
    dashboard_data: dict,
    dataset_name_map: Optional[dict] = None,
    lang: str = "zh",
) -> str:
    """渲染"数据集列表"小节（不含 ### 标题，仅返回表格 + 引用块）。

    输出格式（zh）：
        > 汇总所有图表关联的数据集 ID...

        | 数据集 ID | 关联图表数 | 主要用途 |
        |----------|-----------|----------|
        | `{sourceId}` | {N} | {推断的用途} |

    "主要用途"列由 _infer_usage 从数据集名称自动推断，不再需要 LLM 后处理。
    """
    dataset_name_map = dataset_name_map or {}
    chart_components = dashboard_data.get("chartComponents") or []

    # 构建 sourceId → 关联图表列表的映射（用于推断用途）
    source_id_charts: dict = {}
    source_id_counter: Counter = Counter()
    for chart in chart_components:
        source_id = chart.get("sourceId")
        if source_id:
            source_id_counter[source_id] += 1
            source_id_charts.setdefault(source_id, []).append(chart)

    if not source_id_counter:
        return _empty_hint(lang, "dataset")

    header = _intro_dataset_list(lang)
    if lang == "zh":
        table_head = (
            "| 数据集 ID | 关联图表数 | 主要用途 |\n"
            "|----------|-----------|----------|"
        )
    else:
        table_head = (
            "| Dataset ID | Linked Charts | Main Usage |\n"
            "|-----------|--------------|-----------|"
        )

    rows = []
    for source_id, count in sorted(
        source_id_counter.items(), key=lambda kv: (-kv[1], kv[0])
    ):
        usage = _infer_usage(source_id, source_id_charts.get(source_id, []), dataset_name_map, lang)
        rows.append(f"| `{source_id}` | {count} | {usage} |")

    return f"{header}\n\n{table_head}\n" + "\n".join(rows)


def _intro_dataset_list(lang: str) -> str:
    if lang == "zh":
        return "> 汇总所有图表关联的数据集 ID。这些是 `query_openapi` 的核心输入参数。"
    return "> Aggregates all dataset IDs linked from charts. These are the core inputs for `query_openapi`."


# ---------- 字段映射渲染 ----------

def render_field_mapping(
    dashboard_data: dict,
    dataset_name_map: Optional[dict] = None,
    lang: str = "zh",
) -> str:
    """
    渲染"字段映射"小节（不含 ## 标题，仅返回每数据集子章节）。

    JS 端 (get_dashboard_json.js) 已完成两步过滤：
    1. caption == originalCaption 的字段已被过滤
    2. 空 fields 的数据集已被删除

    所以本函数只需直接遍历 dashboardData.fieldMapping。
    若整个 fieldMapping 为空 → 返回"所有数据集的字段名一致，无需映射"提示。
    """
    field_mapping = dashboard_data.get("fieldMapping") or {}
    dataset_name_map = dataset_name_map or {}

    if not field_mapping:
        return _empty_hint(lang, "field_mapping")

    parts = [_intro_field_mapping(lang)]

    for source_id, mapping_info in field_mapping.items():
        fields = mapping_info.get("fields") or []
        if not fields:  # 防御性：理论上 JS 已删除空数据集
            continue

        dataset_name = (
            mapping_info.get("datasetName")
            or dataset_name_map.get(source_id)
            or source_id
        )

        parts.append(_render_one_dataset_block(dataset_name, source_id, fields, lang))

    if len(parts) == 1:  # 全部 fields 都是空，等价于无映射
        return _empty_hint(lang, "field_mapping")

    return "\n\n".join(parts)


def _render_one_dataset_block(
    dataset_name: str, source_id: str, fields: list, lang: str
) -> str:
    """渲染单个数据集的 #### 子标题 + 5 列映射表。

    charts 数组展开规则：同一字段在 N 个图表使用同一别名 → 输出 N 行。
    """
    if lang == "zh":
        sub_header = f"#### 数据集：{dataset_name}（`{source_id}`）"
        table_head = (
            "| 图表展示名 | 数据集原名 | 类型 | 图表 ID | 图表名称 |\n"
            "|-----------|-----------|------|---------|----------|"
        )
    else:
        sub_header = f"#### Dataset: {dataset_name} (`{source_id}`)"
        table_head = (
            "| Chart Display Name | Dataset Original Name | Type | Chart ID | Chart Name |\n"
            "|-------------------|----------------------|------|----------|------------|"
        )

    rows = []
    for field in fields:
        caption = _md_escape(field.get("caption") or "")
        original = _md_escape(field.get("originalCaption") or "")
        item_type = field.get("itemType") or "-"
        # 兜底：若 charts 缺失/为空，仍输出一行（component_id/name 为 -），避免该字段整行被吞
        charts = field.get("charts") or []
        if not charts:
            charts = [{"componentId": "-", "componentName": "-"}]
        for chart in charts:
            component_id = chart.get("componentId") or "-"
            component_name = _md_escape(chart.get("componentName") or "-")
            id_cell = "-" if component_id == "-" else f"`{component_id}`"
            rows.append(
                f"| {caption} | {original} | {item_type} | {id_cell} | {component_name} |"
            )

    return f"{sub_header}\n\n{table_head}\n" + "\n".join(rows)


def _intro_field_mapping(lang: str) -> str:
    if lang == "zh":
        return "> 建立图表展示名称与数据集原始字段名的映射关系。仅展示两者不一致的字段。"
    return "> Maps chart display names to original dataset field names. Only shows fields where the two differ."


# ---------- 图表组件表渲染 ----------

# 分析层级启发式映射：组件类型 → 层级
_L1_TYPES = {"indicator-card", "kpi", "gauge", "indicator"}
_L2_TYPES = {"line", "area", "indicator-trend"}
_L3_TYPES = {"bar", "pie", "ranking-list", "scatter", "radar", "funnel", "cross-table"}
_L4_TYPES = {"common-table", "table", "detail"}


def render_chart_components_table(dashboard_data: dict, lang: str = "zh") -> str:
    """渲染"图表组件完整列表"小节（不含 ### 标题，返回引用块 + 12 列表）。

    全部 12 列由脚本推断填充，包括分析主题（_infer_analysis_theme）和分析层级（_infer_analysis_level）。
    Filter 列输出占位符 __FILTER_{i}__，由 LLM 在 Phase 2 中替换。
    """
    chart_components = dashboard_data.get("chartComponents") or []

    if not chart_components:
        return _empty_hint(lang, "chart_components")

    parts = [_intro_chart_components(lang)]

    # 表头
    if lang == "zh":
        table_head = (
            "| 图表名 | 组件类型 | 数据集ID | 维度字段 | 度量字段 | 过滤条件 | 下钻字段 | 关联筛选器 | 分析主题 | 分析层级 | 位置 | 所属Tab |\n"
            "|--------|---------|---------|---------|---------|---------|---------|---------|---------|---------|------|--------|"
        )
    else:
        table_head = (
            "| Chart Name | Type | Dataset ID | Dimensions | Measures | Filters | Drill Fields | Related Filters | Analysis Theme | Level | Position | Tab |\n"
            "|--------|---------|---------|---------|---------|---------|---------|---------|---------|---------|------|--------|"
        )

    rows = []
    for chart_index, chart in enumerate(chart_components):
        rows.append(_render_chart_row(chart, lang, chart_index))

    parts.append(table_head)
    parts.append("\n".join(rows))
    # intro / table之间用 \n\n 分隔；表头与数据行必须紧挨（无空行）
    return f"{parts[0]}\n\n{parts[1]}\n{parts[2]}"


def _render_chart_row(chart: dict, lang: str, chart_index: int = 0) -> str:
    """渲染单行图表组件记录。"""
    # 1. 图表名
    name = _md_escape(chart.get("componentName") or "")

    # 2. 组件类型
    comp_type = chart.get("componentType") or ""

    # 3. 数据集ID
    source_id = chart.get("sourceId")
    source_id_cell = f"`{source_id}`" if source_id else "-"

    # 4. 维度字段
    dims = ", ".join(
        _md_escape(d.get("caption") or "")
        for d in (chart.get("dimensions") or [])
    )

    # 5. 度量字段（含聚合方式）
    measures_list = []
    for m in (chart.get("measures") or []):
        caption = _md_escape(m.get("caption") or "")
        agg = m.get("aggregateType")
        measures_list.append(f"{caption}({agg})" if agg else caption)
    measures = ", ".join(measures_list)

    # 6. 过滤条件（输出占位符，由 LLM 在 Phase 2 替换）
    filters = _render_filters(chart.get("defaultFilters") or [], lang, chart_index)

    # 7. 下钻字段
    drill_fields = chart.get("drillFields") or []
    drill = ", ".join(_md_escape(d.get("caption") or "") for d in drill_fields) if drill_fields else ("无" if lang == "zh" else "none")

    # 8. 关联筛选器
    related_qcs = chart.get("relatedQueryControls") or []
    qc_fields = []
    for qc in related_qcs:
        qc_fields.extend(qc.get("fields") or [])
    related_qc_str = ", ".join(_md_escape(f) for f in qc_fields) if qc_fields else ("无" if lang == "zh" else "none")

    # 9. 分析主题（脚本推断）
    analysis_theme = _infer_analysis_theme(chart, lang)

    # 10. 分析层级（脚本推断）
    analysis_level = _infer_analysis_level(chart)

    # 11. 位置
    pos = chart.get("position") or {}
    position = f"({pos.get('x', 0)},{pos.get('y', 0)})"

    # 12. 所属Tab
    tab_info = chart.get("tabInfo")
    tab = _md_escape(tab_info.get("tabItemTitle", "")) if tab_info else "-"

    return f"| {name} | {comp_type} | {source_id_cell} | {dims} | {measures} | {filters} | {drill} | {related_qc_str} | {analysis_theme} | {analysis_level} | {position} | {tab} |"


def _infer_analysis_theme(chart: dict, lang: str) -> str:
    """基于组件类型、维度/度量字段启发式推断分析主题。

    策略：图表类型 → 主题模板，度量关键词 → 前缀修饰。
    """
    comp_type = (chart.get("componentType") or "").lower()
    dimensions = chart.get("dimensions") or []
    measures = chart.get("measures") or []
    has_datetime = any(d.get("itemType") == "datetime" for d in dimensions)

    # 图表类型 → 主题词
    if comp_type in _L1_TYPES:
        type_theme_zh = "指标监控"
        type_theme_en = "Metric monitoring"
    elif comp_type in _L2_TYPES:
        type_theme_zh = "趋势分析"
        type_theme_en = "Trend analysis"
    elif comp_type in _L4_TYPES:
        type_theme_zh = "明细查询"
        type_theme_en = "Detail query"
    elif comp_type == "pie":
        type_theme_zh = "构成分析"
        type_theme_en = "Composition analysis"
    elif comp_type == "ranking-list":
        type_theme_zh = "排行分析"
        type_theme_en = "Ranking analysis"
    elif comp_type == "cross-table":
        type_theme_zh = "分布分析"
        type_theme_en = "Distribution analysis"
    elif comp_type in _L3_TYPES:
        # bar / scatter / radar / funnel
        type_theme_zh = "对比分析"
        type_theme_en = "Comparative analysis"
    elif has_datetime:
        type_theme_zh = "趋势分析"
        type_theme_en = "Trend analysis"
    else:
        type_theme_zh = "数据分析"
        type_theme_en = "Data analysis"

    # 度量关键词 → 前缀修饰
    measure_keyword_zh, measure_keyword_en = _extract_measure_keyword(measures)

    if lang == "zh":
        return f"{measure_keyword_zh}{type_theme_zh}" if measure_keyword_zh else type_theme_zh
    return f"{measure_keyword_en} {type_theme_en}" if measure_keyword_en else type_theme_en


def _extract_measure_keyword(measures: list) -> tuple:
    """从度量列表中提取一个最具业务辨识度的关键词，用于修饰分析主题。

    返回 (zh_keyword, en_keyword)；无法提取时返回 ("", "")。
    """
    if not measures:
        return "", ""

    # 度量 caption → 中文关键词映射
    _KEYWORD_MAP_ZH = {
        "销售额": "销售", "销售金额": "销售", "营收": "营收",
        "利润": "利润", "毛利": "毛利", "净利润": "净利润",
        "成本": "成本", "费用": "费用",
        "订单数": "订单", "订单量": "订单",
        "客户数": "客户", "客户量": "客户",
        "库存": "库存", "库存量": "库存",
        "转化率": "转化", "完成率": "完成",
        "金额": "金额", "数量": "数量",
        "利润率": "利润率", "毛利率": "毛利率",
        "退货": "退货", "退款": "退款",
        "均价": "均价", "客单价": "客单价",
        "增长率": "增长", "同比": "同比", "环比": "环比",
    }

    _KEYWORD_MAP_EN = {
        "sales": "Sales", "revenue": "Revenue", "amount": "Amount",
        "profit": "Profit", "margin": "Margin",
        "cost": "Cost", "expense": "Expense",
        "order": "Order", "quantity": "Quantity", "count": "Count",
        "customer": "Customer", "client": "Client",
        "inventory": "Inventory", "stock": "Stock",
        "conversion": "Conversion", "rate": "Rate",
        "return": "Return", "refund": "Refund",
        "price": "Price", "avg": "Average",
        "growth": "Growth",
    }

    for m in measures:
        caption = (m.get("caption") or "").lower()
        for key_zh, keyword_zh in _KEYWORD_MAP_ZH.items():
            if key_zh in caption:
                # 对应英文关键词：取第一个匹配
                keyword_en = ""
                for key_en, kw_en in _KEYWORD_MAP_EN.items():
                    if key_en in caption:
                        keyword_en = kw_en
                        break
                return keyword_zh, keyword_en

    # 英文度量名匹配
    for m in measures:
        caption = (m.get("caption") or "").lower()
        for key_en, keyword_en in _KEYWORD_MAP_EN.items():
            if key_en in caption:
                return "", keyword_en

    return "", ""


def _extract_measure_keyword_from_charts(charts: list) -> tuple:
    """从一组图表的度量字段中提取业务关键词，用于推断数据集用途。

    返回 (zh_keyword, en_keyword)；无法提取时返回 ("", "")。
    """
    for chart in charts:
        measures = chart.get("measures") or []
        kw_zh, kw_en = _extract_measure_keyword(measures)
        if kw_zh or kw_en:
            return kw_zh, kw_en
    return "", ""


def _infer_usage(
    source_id: str,
    linked_charts: list,
    dataset_name_map: dict,
    lang: str,
) -> str:
    """从数据集名称和关联图表推断主要用途。

    策略：
    1. 从 datasetNameMap 取数据集名称，关键词匹配 → 用途词
    2. 回退：取数据集名称前 4-8 字
    3. 最终回退：source_id
    """
    dataset_name = dataset_name_map.get(source_id, "")

    # 关键词 → 用途映射
    _USAGE_MAP_ZH = {
        "销售": "销售分析", "订单": "订单分析", "营收": "营收分析",
        "利润": "利润分析", "成本": "成本分析", "费用": "费用分析",
        "库存": "库存管理", "客户": "客户分析", "用户": "用户分析",
        "商品": "商品分析", "产品": "产品分析", "供应链": "供应链分析",
        "财务": "财务分析", "采购": "采购分析", "物流": "物流分析",
        "售后": "售后服务", "退货": "退货分析", "退款": "退款分析",
        "营销": "营销分析", "推广": "推广分析", "广告": "广告分析",
        "人力资源": "人力资源", "员工": "员工分析", "薪资": "薪酬分析",
    }

    _USAGE_MAP_EN = {
        "sales": "Sales analysis", "order": "Order analysis", "revenue": "Revenue analysis",
        "profit": "Profit analysis", "cost": "Cost analysis", "expense": "Expense analysis",
        "inventory": "Inventory mgmt", "customer": "Customer analysis", "user": "User analysis",
        "product": "Product analysis", "supply": "Supply chain", "finance": "Financial analysis",
        "purchase": "Procurement", "logistics": "Logistics analysis",
        "marketing": "Marketing analysis", "hr": "HR analysis", "employee": "Employee analysis",
    }

    name_lower = dataset_name.lower()

    if lang == "zh":
        for key, usage in _USAGE_MAP_ZH.items():
            if key in name_lower or key in dataset_name:
                return usage
        # 回退：从关联图表的度量字段中提取用途关键词
        measure_keyword_zh, _ = _extract_measure_keyword_from_charts(linked_charts)
        if measure_keyword_zh:
            return f"{measure_keyword_zh}分析"
        # 回退：取数据集名称前 6 字 + "分析"
        if dataset_name:
            short_name = dataset_name[:6]
            return f"{short_name}分析" if not short_name.endswith("分析") else short_name
        return source_id[:8]
    else:
        for key, usage in _USAGE_MAP_EN.items():
            if key in name_lower:
                return usage
        # 回退：从关联图表的度量字段中提取用途关键词
        _, measure_keyword_en = _extract_measure_keyword_from_charts(linked_charts)
        if measure_keyword_en:
            return f"{measure_keyword_en} analysis"
        if dataset_name:
            words = dataset_name.split()
            return " ".join(words[:3]) if len(words) > 3 else dataset_name
        return source_id[:8]


def _infer_analysis_level(chart: dict) -> str:
    """基于组件类型和位置启发式推断分析层级。

    优先级：组件类型 > 位置
    - L1: indicator-card / kpi / gauge（整体监控）
    - L2: line / area / indicator-trend（趋势分析）
    - L3: bar / pie / ranking-list / scatter / radar / funnel（维度分解）
    - L4: common-table / table / detail（明细追踪）
    - 回退: y<=20→L1, y>50→L4, 含 datetime 维度→L2, 否则→L3
    """
    comp_type = (chart.get("componentType") or "").lower()

    if comp_type in _L1_TYPES:
        return "L1"
    if comp_type in _L2_TYPES:
        return "L2"
    if comp_type in _L3_TYPES:
        return "L3"
    if comp_type in _L4_TYPES:
        return "L4"

    # 回退：基于位置推断
    y = (chart.get("position") or {}).get("y", 0)
    dimensions = chart.get("dimensions") or []
    has_datetime = any(d.get("itemType") == "datetime" for d in dimensions)

    if y <= 20:
        return "L1"
    if y > 50:
        return "L4" if not has_datetime else "L2"
    if has_datetime:
        return "L2"
    return "L3"


def _render_filters(filters: list, lang: str, chart_index: int = 0) -> str:
    """渲染过滤条件列：有过滤条件时输出占位符，由 LLM 在 Phase 2 生成可读描述并替换。"""
    if not filters:
        return "无" if lang == "zh" else "none"

    return f"__FILTER_{chart_index}__"


def _extract_filter_logic(complex_filter: Any) -> str:
    """尝试从 complexFilter 提取简单过滤条件伪代码。

    支持常见结构：
    - {"filterConditions": [{"operate": "eq", "values": ["华东"]}]}
    - {"logicalOperator": "AND", "filterConditions": [...]}
    - {"filterConditions": [{"operate": "in", "values": [...]}]}

    提取失败返回空字符串。
    """
    if not complex_filter or not isinstance(complex_filter, dict):
        return ""

    filter_conditions = complex_filter.get("filterConditions")
    if not filter_conditions or not isinstance(filter_conditions, list):
        return ""

    parts = []
    for fc in filter_conditions:
        if not isinstance(fc, dict):
            continue
        operate = fc.get("operate", "")
        values = fc.get("values")
        if not values or not isinstance(values, list):
            continue

        # 格式化值列表
        formatted_values = ", ".join(str(v) for v in values if v is not None)
        if not formatted_values:
            continue

        if operate in ("eq", "="):
            if len(values) == 1:
                parts.append(f"= {formatted_values}")
            else:
                parts.append(f"in ({formatted_values})")
        elif operate in ("ne", "!="):
            parts.append(f"!= {formatted_values}")
        elif operate in ("gt", ">"):
            parts.append(f"> {formatted_values}")
        elif operate in ("lt", "<"):
            parts.append(f"< {formatted_values}")
        elif operate in ("ge", ">="):
            parts.append(f">= {formatted_values}")
        elif operate in ("le", "<="):
            parts.append(f"<= {formatted_values}")
        elif operate == "in":
            parts.append(f"in ({formatted_values})")
        elif operate == "notNull":
            parts.append("is not null")
        elif operate == "null":
            parts.append("is null")
        elif operate in ("not_in", "notIn"):
            parts.append(f"not in ({formatted_values})")
        else:
            # 未知操作符：尝试展示
            parts.append(f"{operate} {formatted_values}")

    logical_op = complex_filter.get("logicalOperator", "")
    if len(parts) > 1 and logical_op:
        return f" {logical_op} ".join(parts)
    return parts[0] if parts else ""


def _intro_chart_components(lang: str) -> str:
    if lang == "zh":
        return "> 必须列出所有图表组件；每个图表的数据集 ID 对 SmartQ 查询至关重要。"
    return "> All chart components MUST be listed; each chart's dataset ID is critical for SmartQ queries."


# ---------- 公共 helpers ----------

def _empty_hint(lang: str, kind: str) -> str:
    if kind == "field_mapping":
        return (
            "**所有数据集的字段名一致，无需映射。**"
            if lang == "zh"
            else "**All dataset field names are consistent across charts; no mapping required.**"
        )
    if kind == "dataset":
        return (
            "**未发现关联数据集。**"
            if lang == "zh"
            else "**No linked datasets found.**"
        )
    if kind == "chart_components":
        return (
            "**未发现图表组件。**"
            if lang == "zh"
            else "**No chart components found.**"
        )
    return ""


def _md_escape(text: Any) -> str:
    """转义 Markdown 表格单元中会破坏表格结构的字符。

    主要处理管道符 `|`（拆表格）和换行符（多行单元）。
    """
    if text is None:
        return ""
    s = str(text)
    return s.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


# ---------- CLI ----------

def _main_cli() -> int:
    """从 stdin 读 JSON，渲染后从 stdout 输出 JSON。

    输入：
        {
            "dashboardData": {...},      # 必填
            "datasetNameMap": {...},     # 可选
            "lang": "zh" | "en"          # 可选，默认 zh
        }
    输出：
        {
            "success": true,
            "dataset_list_md": "...",
            "field_mapping_md": "...",
            "chart_components_md": "..."
        }
    """
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        json.dump(
            {"success": False, "error": f"stdin JSON decode error: {e}"},
            sys.stdout,
            ensure_ascii=False,
        )
        return 1

    dashboard_data = payload.get("dashboardData") or {}
    dataset_name_map = payload.get("datasetNameMap") or {}
    lang = (payload.get("lang") or "zh").lower()
    if lang not in ("zh", "en"):
        lang = "zh"

    result = {
        "success": True,
        "dataset_list_md": render_dataset_list(dashboard_data, dataset_name_map=dataset_name_map, lang=lang),
        "field_mapping_md": render_field_mapping(
            dashboard_data, dataset_name_map, lang=lang
        ),
        "chart_components_md": render_chart_components_table(dashboard_data, lang=lang),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
