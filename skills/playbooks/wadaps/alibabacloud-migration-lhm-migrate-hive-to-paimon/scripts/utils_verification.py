#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据迁移校验工具集。

从 hive_to_paimon_migration 提取的独有校验功能，提供：
1. read_partition_info - 读取分区信息 CSV
2. generate_count_verification_sql - 生成 COUNT 校验 SQL
3. verify_ddl_field_count - DDL 字段数交叉校验
"""

import re
from typing import Dict, List, Optional, Tuple


def read_partition_info(csv_file: str) -> Dict[str, List[str]]:
    """读取分区信息 CSV 文件，返回表名到分区字段列表的映射。

    CSV 格式（无 header 或首行为"表名"开头）：
        db.table_name, partition_col1, partition_col2, ...

    Args:
        csv_file: CSV 文件路径

    Returns:
        Dict[str, List[str]]: {表名: [分区字段1, 分区字段2, ...]}
    """
    partition_map = {}
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('表名'):
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                table_name = parts[0].strip()
                partitions = []
                for i in range(1, min(4, len(parts))):
                    p = parts[i].strip()
                    if p and p != '':
                        partitions.append(p)
                partition_map[table_name] = partitions
    return partition_map


def generate_count_verification_sql(
    tables: List[str],
    partition_info: Optional[Dict[str, List[str]]] = None,
    result_table: str = "test.table_count_result",
    partition_values: Optional[Dict[str, str]] = None,
) -> str:
    """生成表记录数统计 SQL，用于迁移前后数据校验。

    为每张表生成 INSERT INTO result_table SELECT count(*) 语句，
    支持按分区过滤以加速校验。

    Args:
        tables: 表名列表，格式为 ["db.table", ...]
        partition_info: 分区信息映射 {表名: [分区字段列表]}，为 None 则全表计数
        result_table: 存放结果的目标表名
        partition_values: 分区字段→校验值映射，如 {"dt": "20260316", "dates": "202603"}
                         未指定时使用默认规则

    Returns:
        str: 完整的 SQL 脚本文本
    """
    if partition_info is None:
        partition_info = {}

    # 默认分区值规则
    default_partition_values = {
        "dt": "20260316",
        "data_from": "20260316",
        "dates": "202603",
    }
    if partition_values:
        default_partition_values.update(partition_values)

    lines = []
    lines.append("-- 表记录数统计 SQL（迁移校验用）")
    lines.append(f"-- 结果表: {result_table}")
    lines.append("-- 字段: db (库), tbl (表), part (分区), num (条数)")
    lines.append("")
    lines.append("-- 创建结果表")
    lines.append(f"CREATE TABLE IF NOT EXISTS {result_table}(")
    lines.append("  db string COMMENT '库',")
    lines.append("  tbl string COMMENT '表',")
    lines.append("  part string COMMENT '分区',")
    lines.append("  num bigint COMMENT '条数'")
    lines.append(")")
    lines.append("STORED AS ORC;")
    lines.append("")
    lines.append(f"-- 清空结果表")
    lines.append(f"TRUNCATE TABLE {result_table};")
    lines.append("")
    lines.append("-- 插入各表的记录数")

    for table_name in tables:
        parts = table_name.split('.')
        if len(parts) != 2:
            continue
        db, tbl = parts

        # 获取分区信息
        partitions = partition_info.get(table_name, [])

        if not partitions:
            # 无分区，计算全表
            lines.append(f"INSERT INTO TABLE {result_table}")
            lines.append(
                f"SELECT '{db}' as db, '{tbl}' as tbl, 'all' as part, "
                f"count(*) as num FROM {table_name};"
            )
        else:
            # 有分区，使用第一个分区字段
            part_field = partitions[0]
            partition_val = default_partition_values.get(part_field)

            if partition_val:
                lines.append(f"INSERT INTO TABLE {result_table}")
                lines.append(
                    f"SELECT '{db}' as db, '{tbl}' as tbl, "
                    f"'{part_field}={partition_val}' as part, "
                    f"count(*) as num FROM {table_name} "
                    f"WHERE {part_field} = '{partition_val}';"
                )
            else:
                # 未知分区字段，计算全表
                lines.append(f"INSERT INTO TABLE {result_table}")
                lines.append(
                    f"SELECT '{db}' as db, '{tbl}' as tbl, 'all' as part, "
                    f"count(*) as num FROM {table_name};"
                )

    return "\n".join(lines)


def verify_ddl_field_count(original_ddl: str, generated_ddl: str, table_name: str) -> Tuple[bool, str]:
    """验证生成的 DDL 字段数与原始 DDL 是否一致。

    通过正则提取两份 DDL 中的字段定义，比较字段总数（普通字段 + 分区字段）。

    Args:
        original_ddl: 原始 Hive DDL 文本
        generated_ddl: 生成的 Paimon DDL 文本
        table_name: 表名（用于在生成的 DDL 中定位）

    Returns:
        Tuple[bool, str]: (是否一致, 描述信息)
    """
    try:
        # 解析原始 DDL 中的普通字段
        orig_start = original_ddl.find('CREATE TABLE')
        if orig_start == -1:
            orig_start = original_ddl.find('CREATE EXTERNAL TABLE')
        if orig_start == -1:
            return False, "无法找到 CREATE TABLE 语句"

        orig_brace = original_ddl.find('(', orig_start)
        if orig_brace == -1:
            return False, "无法解析原始 DDL"

        # 找到匹配的右括号
        brace_count = 0
        orig_end = orig_brace
        for i, c in enumerate(original_ddl[orig_brace:], orig_brace):
            if c == '(':
                brace_count += 1
            elif c == ')':
                brace_count -= 1
                if brace_count == 0:
                    orig_end = i
                    break

        orig_pattern = re.compile(r'`(\w+)`\s+(\w+(?:\([^)]*\))?)', re.IGNORECASE)
        orig_fields = orig_pattern.findall(original_ddl[orig_brace + 1:orig_end])

        # 解析原始 DDL 中的分区字段
        orig_part_match = re.search(
            r'PARTITIONED\s+BY\s*\((.*?)\)', original_ddl, re.IGNORECASE | re.DOTALL
        )
        orig_part_fields = []
        if orig_part_match:
            part_pat = re.compile(r'`(\w+)`\s+(\w+)', re.IGNORECASE)
            orig_part_fields = part_pat.findall(orig_part_match.group(1))

        # 解析生成的 DDL 字段
        # 尝试定位特定表的 DDL（支持注释标记格式）
        gen_pattern = re.compile(
            rf'CREATE TABLE.*?{re.escape(table_name)}.*?\((.*?)\)\s*(?:USING|PARTITIONED|TBLPROPERTIES|;)',
            re.DOTALL | re.IGNORECASE
        )
        gen_match = gen_pattern.search(generated_ddl)
        if not gen_match:
            # 退而求其次：直接找 CREATE TABLE 后面的括号内容
            simple_pattern = re.compile(
                r'CREATE TABLE[^(]*\((.*?)\)\s*(?:USING|PARTITIONED|;)',
                re.DOTALL | re.IGNORECASE
            )
            gen_match = simple_pattern.search(generated_ddl)
            if not gen_match:
                return False, "无法匹配生成的 DDL"

        field_pat = re.compile(r'(\w+)\s+(\w+(?:\([^)]*\))?)', re.IGNORECASE)
        gen_fields = field_pat.findall(gen_match.group(1))

        # 验证：Paimon DDL 会将分区字段合并到主字段列表中
        expected = len(orig_fields) + len(orig_part_fields)
        actual = len(gen_fields)

        if expected == actual:
            return True, f"字段数一致: {actual}"
        else:
            return False, (
                f"字段数不一致: 原始 {len(orig_fields)} + {len(orig_part_fields)} 分区 "
                f"= {expected}, 生成 {actual}"
            )

    except Exception as e:
        return False, f"验证错误: {e}"
