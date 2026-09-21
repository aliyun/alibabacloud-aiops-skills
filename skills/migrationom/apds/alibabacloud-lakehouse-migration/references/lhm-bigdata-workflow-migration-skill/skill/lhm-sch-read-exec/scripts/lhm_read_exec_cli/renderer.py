"""Result rendering for LHM Scheduler CLI.

Two text rendering paths exist:

1.  Summary mode (preferred): downloads the conversion result zip via
    `download_url`, extracts `metadata/convert_statistics.json`, and renders a
    rich summary following design doc §5.3 algorithm / §5.4 templates.
2.  Fallback mode: when statistics are unavailable, renders the flat fields
    returned directly by the conversion API.

JSON mode always outputs the raw conversion data for machine consumption.
"""

import json
from typing import Any, Dict, List, Optional

from lhm_read_exec_cli.statistics_loader import (
    StatisticsLoadError,
    load_convert_statistics,
)

MAX_NODE_TYPES_IN_SUMMARY = 5
MAX_ERROR_NODES_INLINE = 3


def format_duration(duration_ms: Any) -> str:
    """Format a millisecond duration per design doc §5.5.

    Args:
        duration_ms: Duration in milliseconds (int-like) or unknown.

    Returns:
        Human-readable duration string. Returns "N/A" if not a valid number.
    """
    try:
        total_ms = int(duration_ms)
    except (TypeError, ValueError):
        return "N/A"

    if total_ms < 1000:
        return f"{total_ms}ms"
    if total_ms < 60000:
        return f"{total_ms / 1000:.1f}s"
    if total_ms < 3600000:
        minutes = total_ms // 60000
        seconds = (total_ms % 60000) // 1000
        return f"{minutes}m{seconds}s"
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    return f"{hours}h{minutes}m"


def _build_overview_section(summary: Dict[str, Any]) -> List[str]:
    """Build the overview block (design doc §5.3 step 3)."""
    total_workflows = summary.get("total_workflows", "N/A")
    total_nodes = summary.get("total_nodes", "N/A")
    success_nodes = summary.get("success_nodes", "N/A")
    failed_nodes = summary.get("failed_nodes", "N/A")
    degraded_nodes = summary.get("degraded_nodes", 0)
    skipped_nodes = summary.get("skipped_nodes", 0)
    duration = format_duration(summary.get("duration_ms"))

    counts = f"  成功 {success_nodes} | 失败 {failed_nodes} | 降级 {degraded_nodes}"
    if isinstance(skipped_nodes, int) and skipped_nodes > 0:
        counts += f" | 跳过 {skipped_nodes}"
    counts += f" | 耗时 {duration}"

    return [
        "概览：",
        f"  工作流 {total_workflows} 个 | 节点 {total_nodes} 个",
        counts,
    ]


def _build_node_type_section(node_type_distribution: Dict[str, Any]) -> List[str]:
    """Build the node type distribution block (design doc §5.3 step 4)."""
    if not node_type_distribution:
        return []

    sorted_types = sorted(
        node_type_distribution.items(), key=lambda item: item[1], reverse=True
    )
    top_types = sorted_types[:MAX_NODE_TYPES_IN_SUMMARY]
    distribution_text = "  " + "  ".join(
        f"{type_name}({count})" for type_name, count in top_types
    )
    if len(sorted_types) > MAX_NODE_TYPES_IN_SUMMARY:
        distribution_text += f" ...等 {len(sorted_types)} 种"

    return ["节点类型分布：", distribution_text]


def _build_custom_mapping_section(
    convert_config_applied: Dict[str, Any], 
    degraded_nodes: int,
    node_type_distribution: Optional[Dict[str, Any]] = None,
    source_node_type_distribution: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Build the custom mapping block (design doc §7.2).

    Shown when sqlNodeTypeMapping is non-empty, regardless of degraded_nodes count.
    Supports the actual backend format: [{"rule": "SRC->TGT", "count": N}, ...]
    """
    sql_node_type_mapping = (convert_config_applied or {}).get("sqlNodeTypeMapping")
    if not sql_node_type_mapping:
        return []

    lines = ["应用的自定义映射："]
    total_hit_count = 0
    
    # Handle actual backend format: list of {rule: "SRC->TGT", count: N}
    if isinstance(sql_node_type_mapping, list):
        for item in sql_node_type_mapping:
            if isinstance(item, dict):
                rule_str = item.get("rule", "")
                count = item.get("count", 0)
                
                # Parse "SRC->TGT" format
                if "->" in str(rule_str):
                    parts = str(rule_str).split("->", 1)
                    source_type = parts[0].strip()
                    target_type = parts[1].strip()
                    if isinstance(count, int) and count > 0:
                        lines.append(f"  {source_type} → {target_type}（命中 {count} 个节点）")
                        total_hit_count += count
                    else:
                        lines.append(f"  {source_type} → {target_type}")
                else:
                    if isinstance(count, int) and count > 0:
                        lines.append(f"  {rule_str}（命中 {count} 个节点）")
                        total_hit_count += count
                    else:
                        lines.append(f"  {rule_str}")
            elif isinstance(item, str) and "->" in item:
                # Fallback for simple string rules
                parts = item.split("->", 1)
                lines.append(f"  {parts[0].strip()} → {parts[1].strip()}")
    
    # Fallback for legacy dict format
    elif isinstance(sql_node_type_mapping, dict):
        for source_type, target_type in sql_node_type_mapping.items():
            hit_count = 0
            if source_node_type_distribution and source_type in source_node_type_distribution:
                hit_count = source_node_type_distribution[source_type]
            elif node_type_distribution and target_type in node_type_distribution:
                hit_count = node_type_distribution[target_type]
            elif len(sql_node_type_mapping) == 1:
                hit_count = degraded_nodes
            
            if hit_count > 0:
                lines.append(f"  {source_type} → {target_type}（命中 {hit_count} 个节点）")
                total_hit_count += hit_count
            else:
                lines.append(f"  {source_type} → {target_type}")

    if total_hit_count > 0:
        lines.append(f"  命中自定义转换规则的节点总数：{total_hit_count}")
    elif degraded_nodes > 0:
        lines.append(f"  命中自定义转换规则的节点总数：{degraded_nodes}")
        
    return lines


def _build_issues_section(issues: List[Dict[str, Any]]) -> List[str]:
    """Build the issues summary block (design doc §5.3 step 5)."""
    if not issues:
        return []

    errors = [issue for issue in issues if issue.get("level") == "ERROR"]
    warnings = [issue for issue in issues if issue.get("level") == "WARNING"]
    infos = [issue for issue in issues if issue.get("level") == "INFO"]

    lines = ["问题汇总："]

    if errors:
        error_line = f"  [ERROR] {len(errors)} 个节点转换失败"
        if len(errors) <= MAX_ERROR_NODES_INLINE:
            node_names = [
                str(issue.get("node_id", "N/A"))
                for issue in errors
                if issue.get("node_id")
            ]
            if node_names:
                error_line += f"（{', '.join(node_names)}）"
        lines.append(error_line)

    if warnings:
        category_counts: Dict[str, int] = {}
        for issue in warnings:
            category = issue.get("category", "other")
            category_counts[category] = category_counts.get(category, 0) + 1
        category_text = ", ".join(
            f"{count} 个{category}" for category, count in category_counts.items()
        )
        lines.append(f"  [WARNING] {len(warnings)} 个告警（{category_text}）")

    if infos:
        lines.append(f"  [INFO] {len(infos)} 条信息提示")

    return lines


def render_summary_from_statistics(stats: Dict[str, Any]) -> str:
    """Render result summary from convert_statistics.json (design doc §5.3/§5.4).

    Args:
        stats: Parsed convert_statistics.json content.

    Returns:
        Formatted summary text.
    """
    source = stats.get("source", {}) or {}
    target = stats.get("target", {}) or {}
    summary = stats.get("summary", {}) or {}
    node_type_distribution = stats.get("node_type_distribution", {}) or {}
    issues = stats.get("issues", []) or []
    convert_config_applied = stats.get("convert_config_applied", {}) or {}

    source_name = source.get("datasource_name", "N/A")
    target_name = target.get("datasource_name", "N/A")
    failed_nodes = summary.get("failed_nodes", 0)
    degraded_nodes = summary.get("degraded_nodes", 0)
    has_error = any(issue.get("level") == "ERROR" for issue in issues)

    is_all_success = (failed_nodes == 0) and not has_error
    if is_all_success:
        header = f"✓ 转换完成 — {source_name} → {target_name}"
    else:
        header = f"⚠ 转换完成（有问题需关注）— {source_name} → {target_name}"

    lines = [header, ""]
    lines.extend(_build_overview_section(summary))

    custom_mapping_section = _build_custom_mapping_section(
        convert_config_applied, 
        degraded_nodes,
        node_type_distribution,
        stats.get("source_node_type_distribution")
    )
    if custom_mapping_section:
        lines.append("")
        lines.extend(custom_mapping_section)

    node_type_section = _build_node_type_section(node_type_distribution)
    if node_type_section:
        lines.append("")
        lines.extend(node_type_section)

    issues_section = _build_issues_section(issues)
    if issues_section:
        lines.append("")
        lines.extend(issues_section)

    lines.append("")
    excel_path = (stats.get("output_artifacts", {}) or {}).get(
        "excel_report_path", "LHMPackageOverview.xls"
    )
    lines.append(f"报告：{excel_path}")
    
    # Output the absolute path of the extracted files
    extraction_dir = stats.get("_extraction_dir")
    if extraction_dir:
        lines.append(f"汇总统计信息：{extraction_dir}")
    
    # Output the full export package path if available
    oss_package_path = stats.get("_oss_package_path")
    if oss_package_path:
        lines.append(f"完整导出包：{oss_package_path}")
    
    lines.append("详情：执行 /lhm-sch-read-explain 可深入查看")

    return "\n".join(lines)


def render_result_text_fallback(task_id: str, request_id: str, data: Any) -> str:
    """Render conversion result from flat API fields (fallback mode).

    Used when convert_statistics.json cannot be downloaded or parsed.

    Args:
        task_id: Migration task ID.
        request_id: API request ID for traceability.
        data: Parsed conversion result data (flat fields).

    Returns:
        Formatted text string.
    """
    lines = ["✓ 转换完成", f"- 任务ID: {task_id}", f"- 请求ID: {request_id}"]

    if isinstance(data, dict):
        total_workflows = data.get("total_workflows", "N/A")
        total_nodes = data.get("total_nodes", "N/A")
        success_nodes = data.get("success_nodes", "N/A")
        failed_nodes = data.get("failed_nodes", "N/A")
        download_url = data.get("download_url", "")

        lines.append(f"- 工作流总数: {total_workflows}")
        lines.append(f"- 节点总数: {total_nodes}")
        lines.append(f"- 成功: {success_nodes}")
        lines.append(f"- 失败: {failed_nodes}")
        if download_url:
            lines.append(f"- 结果下载: {download_url}")
    elif isinstance(data, list):
        lines.append(f"- 结果条目数: {len(data)}")
    else:
        lines.append(f"- 转换结果: {data}")

    return "\n".join(lines)


def render_result_text(task_id: str, request_id: str, data: Any) -> str:
    """Render conversion result as human-readable text.

    Prefers the rich summary built from convert_statistics.json (downloaded via
    download_url). Falls back to flat-field rendering when statistics are
    unavailable.

    Args:
        task_id: Migration task ID.
        request_id: API request ID for traceability.
        data: Parsed conversion result data.

    Returns:
        Formatted text string.
    """
    download_url = ""
    oss_download_url = ""
    if isinstance(data, dict):
        download_url = data.get("download_url", "")
        oss_download_url = data.get("oss_download_url", "")

    if download_url:
        try:
            stats = load_convert_statistics(download_url, oss_download_url)
            if stats:
                return render_summary_from_statistics(stats)
        except StatisticsLoadError:
            # Statistics unavailable; degrade to flat-field rendering.
            pass

    return render_result_text_fallback(task_id, request_id, data)


def render_result_json(task_id: str, request_id: str, data: Any) -> str:
    """Render conversion result as JSON.

    Args:
        task_id: Migration task ID.
        request_id: API request ID for traceability.
        data: Parsed conversion result data.

    Returns:
        JSON string with indentation.
    """
    output: Dict[str, Any] = {
        "task_id": task_id,
        "request_id": request_id,
        "data": data,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def render_result(
    task_id: str, request_id: str, data: Any, output_format: str = "text"
) -> str:
    """Render conversion result in specified format.

    Args:
        task_id: Migration task ID.
        request_id: API request ID for traceability.
        data: Parsed conversion result data.
        output_format: 'text' or 'json'.

    Returns:
        Formatted result string.
    """
    if output_format == "json":
        return render_result_json(task_id, request_id, data)
    return render_result_text(task_id, request_id, data)
