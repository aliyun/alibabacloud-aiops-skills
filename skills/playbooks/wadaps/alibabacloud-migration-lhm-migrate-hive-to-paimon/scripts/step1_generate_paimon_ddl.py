#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1: 将 Hive DDL 转换为 Paimon 内表 DDL
输入: migration-lhm-inspect-hive-metastore 探查目录 或 数据库/表名列表
输出: paimon_ddl.sql + table_manifest.csv
"""

import argparse
import os
import sys

from common import (
    TableMeta, add_common_args, resolve_tables_from_args,
    create_output_dir, write_manifest
)


def generate_paimon_inner_ddl(meta: TableMeta) -> str:
    """
    将 TableMeta 转换为 Paimon 内表 DDL。
    转换规则:
    1. CREATE TABLE IF NOT EXISTS db.table(
    2. 主字段 + 分区字段合并
    3. ) USING paimon
    4. COMMENT（如有，放在 USING paimon 之后）
    5. PARTITIONED BY (只保留字段名)
    6. ;
    """
    lines = []

    # CREATE TABLE 头
    lines.append(f"CREATE TABLE IF NOT EXISTS {meta.db_name}.{meta.table_name}(")

    # 字段列表：主字段 + 分区字段
    all_cols = meta.all_columns
    col_defs = []
    for col in all_cols:
        col_str = f"  `{col.name}` {col.type}"
        if col.comment:
            escaped = col.comment.replace("'", "\\'")
            col_str += f" COMMENT '{escaped}'"
        col_defs.append(col_str)

    lines.append(",\n".join(col_defs))
    lines.append(")")

    # USING paimon
    lines.append("USING paimon")

    # 表注释
    if meta.comment:
        escaped = meta.comment.replace("'", "\\'")
        lines.append(f"COMMENT '{escaped}'")

    # PARTITIONED BY（只有字段名，无类型）
    if meta.is_partitioned:
        part_names = ", ".join(f"`{c.name}`" for c in meta.partition_columns)
        lines.append(f"PARTITIONED BY ({part_names})")

    # 分号
    return "\n".join(lines) + ";"


def main():
    parser = argparse.ArgumentParser(
        description='Step 1: Hive DDL -> Paimon 内表 DDL',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_common_args(parser)
    args = parser.parse_args()

    # 解析表列表
    tables = resolve_tables_from_args(args)
    if not tables:
        print("未找到任何表，退出")
        return 1

    # 创建输出目录
    output_dir = create_output_dir(args.output_dir)
    ddl_path = os.path.join(output_dir, "paimon_ddl.sql")
    manifest_path = os.path.join(output_dir, "table_manifest.csv")

    # 生成 DDL
    success_count = 0
    error_count = 0
    ddl_statements = []

    for meta in tables:
        if meta.error:
            print(f"  跳过 {meta.full_name}: {meta.error}")
            error_count += 1
            continue

        if not meta.columns and not meta.partition_columns:
            meta.error = "无法解析出任何字段"
            print(f"  跳过 {meta.full_name}: {meta.error}")
            error_count += 1
            continue

        ddl = generate_paimon_inner_ddl(meta)
        ddl_statements.append(
            f"-- Table: {meta.full_name} (format: {meta.storage_format}, "
            f"partitioned: {meta.is_partitioned})\n{ddl}"
        )
        success_count += 1

    # 写入 DDL 文件
    with open(ddl_path, 'w', encoding='utf-8') as f:
        f.write("-- Paimon Inner Table DDL\n")
        f.write(f"-- Generated at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Total: {success_count} tables\n\n")
        f.write("\n\n".join(ddl_statements))
        f.write("\n")

    print(f"\nPaimon 内表 DDL 已写入: {ddl_path}")
    print(f"  成功: {success_count} 张表")
    print(f"  失败: {error_count} 张表")

    # 写入 manifest
    write_manifest(tables, manifest_path)

    print(f"\n输出目录: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
