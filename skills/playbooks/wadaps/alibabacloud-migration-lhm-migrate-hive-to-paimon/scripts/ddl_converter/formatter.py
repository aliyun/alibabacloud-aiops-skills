"""输出格式化 - 批量输出和警告注释处理。"""

from typing import List, Tuple


def format_batch_output(
    results: List[Tuple[str, str, str, List[str]]],
    mode: str
) -> Tuple[str, List[str]]:
    """格式化批量输出。

    Args:
        results: [(db, table, ddl_str, warnings), ...]
        mode: "paimon", "ext", "both"

    Returns:
        (formatted_output, all_warnings)
    """
    all_warnings = []
    output_parts = []

    for i, (db, table, ddl, warnings) in enumerate(results, 1):
        all_warnings.extend(warnings)

        part_lines = []
        # 添加警告注释
        for w in warnings:
            part_lines.append(f"-- {w}")

        # 添加表名注释（批量时）
        if len(results) > 1:
            part_lines.append(f"-- {i}. {db}.{table}")

        part_lines.append(ddl)
        output_parts.append("\n".join(part_lines))

    return "\n\n".join(output_parts), all_warnings


def format_both_output(
    paimon_results: List[Tuple[str, str, str, List[str]]],
    ext_results: List[Tuple[str, str, str, List[str]]]
) -> Tuple[str, List[str]]:
    """格式化 both 模式的输出（先 Paimon，再外表）。"""
    all_warnings = []
    sections = []

    # Paimon 部分
    sections.append("-- === Paimon 内表 ===")
    paimon_output, paimon_warnings = format_batch_output(paimon_results, "paimon")
    all_warnings.extend(paimon_warnings)
    sections.append(paimon_output)

    # 外表部分
    sections.append("")
    sections.append("-- === FORMAT 外表 ===")
    ext_output, ext_warnings = format_batch_output(ext_results, "ext")
    all_warnings.extend(ext_warnings)
    sections.append(ext_output)

    return "\n".join(sections), all_warnings
