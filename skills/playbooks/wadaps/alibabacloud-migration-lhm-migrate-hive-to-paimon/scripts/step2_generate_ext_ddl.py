#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2: 生成 Paimon 外表 DDL + TextFile 表的特殊 INSERT 语句
输入: table_manifest.csv + config.ini
输出: paimon_ext_ddl.sql + text_tables_insert.sql
"""

import argparse
import os
import sys
from datetime import datetime

from common import (
    TableMeta, ColumnDef, read_manifest, read_config,
    hdfs_path_to_oss_path, get_oss_relative_path
)


# string 类型集合（不需要 CAST 的类型）
STRING_TYPES = {'string', 'varchar', 'char', 'binary'}


def _needs_cast(col_type: str) -> bool:
    """判断字段类型是否需要 CAST"""
    base_type = col_type.lower().split('(')[0].strip()
    return base_type not in STRING_TYPES


def generate_standard_ext_ddl(meta: TableMeta, bucket: str,
                             target_path: str = '',
                             direct_read: bool = False) -> str:
    """
    生成标准外表 DDL（orc/parquet/json/csv 格式）。
    表名后缀 _oss，通过 TBLPROPERTIES 指向 OSS 数据。
    direct_read=True 时直接使用源端原始路径（适用于 OSS-HDFS/DLS 场景）。
    """
    if direct_read:
        oss_path = meta.location
    else:
        oss_path = hdfs_path_to_oss_path(meta.location, bucket, target_path)
    ext_name = f"{meta.table_name}_oss"
    lines = []

    # CREATE TABLE
    lines.append(f"CREATE TABLE IF NOT EXISTS {meta.db_name}.{ext_name}(")

    # 字段列表（主字段 + 分区字段合并）
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

    # PARTITIONED BY
    if meta.is_partitioned:
        part_names = ", ".join(f"`{c.name}`" for c in meta.partition_columns)
        lines.append(f"PARTITIONED BY ({part_names})")

    # TBLPROPERTIES
    lines.append("TBLPROPERTIES (")
    props = [
        f"  'path' = '{oss_path}'",
        f"  'type' = 'format-table'",
        f"  'file.format' = '{meta.storage_format}'",
    ]
    lines.append(",\n".join(props))
    lines.append(")")

    return "\n".join(lines) + ";"


def generate_text_ext_ddl(meta: TableMeta, bucket: str,
                          target_path: str = '',
                          direct_read: bool = False) -> str:
    """
    生成 TextFile 格式的特殊外表 DDL。
    数据列只有 raw_line string，分区列（如有）从目录结构推断。
    表名后缀 _oss。
    direct_read=True 时直接使用源端原始路径（适用于 OSS-HDFS/DLS 场景）。
    """
    if direct_read:
        oss_path = meta.location
    else:
        oss_path = hdfs_path_to_oss_path(meta.location, bucket, target_path)
    ext_name = f"{meta.table_name}_oss"
    lines = []

    lines.append(f"CREATE TABLE IF NOT EXISTS {meta.db_name}.{ext_name}(")

    # 数据列 + 分区列
    col_defs = ["  `raw_line` string"]
    if meta.is_partitioned:
        for col in meta.partition_columns:
            col_defs.append(f"  `{col.name}` {col.type}")
    lines.append(",\n".join(col_defs))
    lines.append(")")
    lines.append("USING paimon")

    # PARTITIONED BY（分区列值从目录结构推断）
    if meta.is_partitioned:
        part_names = ", ".join(f"`{c.name}`" for c in meta.partition_columns)
        lines.append(f"PARTITIONED BY ({part_names})")

    lines.append("TBLPROPERTIES (")
    props = [
        f"  'path' = '{oss_path}'",
        f"  'type' = 'format-table'",
        f"  'file.format' = 'text'",
    ]
    lines.append(",\n".join(props))
    lines.append(")")

    return "\n".join(lines) + ";"


def generate_text_insert_sql(meta: TableMeta) -> str:
    """
    生成 TextFile 格式表的 INSERT OVERWRITE 语句。
    使用 split(raw_line, '\\u0001') 拆分非分区字段，CAST 转换类型，处理 \\N 为 NULL。
    分区字段直接从外表的分区列获取（值来自目录结构）。
    """
    # 只有主字段参与 split，分区字段从外表直接获取
    data_cols = meta.columns  # 非分区字段
    ext_name = f"{meta.table_name}_oss"
    total_data_cols = len(data_cols)

    # 构建 SELECT 列表：先是非分区字段（从 split 结果），再是分区字段（直接引用）
    select_items = []
    for i, col in enumerate(data_cols):
        null_expr = f"CASE WHEN fields[{i}] = '\\\\N' THEN NULL ELSE fields[{i}] END"

        if _needs_cast(col.type):
            expr = f"    CAST(\n      {null_expr}\n      AS {col.type}\n    ) AS {col.name}"
        else:
            expr = f"    {null_expr} AS {col.name}"

        select_items.append(expr)

    # 分区字段直接引用（值来自外表的分区推断）
    for col in meta.partition_columns:
        select_items.append(f"    {col.name}")

    select_clause = ",\n".join(select_items)

    # 构建 INSERT 语句
    lines = []
    if meta.is_partitioned:
        part_keys = ", ".join(c.name for c in meta.partition_columns)
        lines.append(f"INSERT OVERWRITE {meta.db_name}.{meta.table_name} PARTITION ({part_keys})")
    else:
        lines.append(f"INSERT OVERWRITE {meta.db_name}.{meta.table_name}")

    lines.append("SELECT")
    lines.append(select_clause)
    lines.append("FROM (")

    # 子查询：split raw_line，同时保留分区字段
    if meta.is_partitioned:
        part_cols_str = ", ".join(col.name for col in meta.partition_columns)
        lines.append(f"    SELECT split(raw_line, '\\u0001') AS fields, {part_cols_str}")
    else:
        lines.append(f"    SELECT split(raw_line, '\\u0001') AS fields")

    lines.append(f"    FROM {meta.db_name}.{ext_name}")
    lines.append(") t")
    lines.append(f"WHERE size(t.fields) = {total_data_cols}")

    return "\n".join(lines) + ";"


def main():
    parser = argparse.ArgumentParser(
        description='Step 2: 生成 Paimon 外表 DDL + TextFile INSERT',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-m', '--manifest', required=True, help='table_manifest.csv 路径')
    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录')
    parser.add_argument('--direct-read', action='store_true',
                        help='直读模式：外表直接指向源端原始路径（适用于 OSS-HDFS/DLS 场景，跳过 rclone）')
    args = parser.parse_args()

    direct_read = args.direct_read

    # 直读模式不需要 rclone_target_s3 配置
    if direct_read:
        config = read_config(args.config)
        bucket = ''
        target_path = ''
        print("直读模式: 外表将指向源端原始路径（跳过 rclone 路径转换）")
    else:
        config = read_config(args.config, required_sections={
            'rclone_target_s3': ['bucket']
        })
        bucket = config.get('rclone_target_s3', 'bucket')
        target_path = config.get('rclone_target_s3', 'target_path', fallback='')
    tables = read_manifest(args.manifest)

    if not tables:
        print("Manifest 为空，退出")
        return 1

    # 输出目录
    output_dir = args.output_dir or os.path.dirname(args.manifest)
    ext_ddl_path = os.path.join(output_dir, "paimon_ext_ddl.sql")
    text_insert_path = os.path.join(output_dir, "text_tables_insert.sql")

    # 生成外表 DDL
    ext_ddl_statements = []
    text_insert_statements = []
    standard_count = 0
    text_count = 0
    skip_count = 0

    for meta in tables:
        if meta.error:
            print(f"  跳过 {meta.full_name}: {meta.error}")
            skip_count += 1
            continue

        if not meta.location:
            print(f"  跳过 {meta.full_name}: 缺少 HDFS location")
            skip_count += 1
            continue

        if meta.storage_format == 'text':
            # TextFile 格式：单列外表 + 特殊 INSERT
            ext_ddl = generate_text_ext_ddl(meta, bucket, target_path, direct_read)
            ext_ddl_statements.append(
                f"-- TextFile 外表: {meta.full_name}\n{ext_ddl}"
            )
            insert_sql = generate_text_insert_sql(meta)
            text_insert_statements.append(
                f"-- TextFile INSERT: {meta.full_name} "
                f"({meta.column_count} columns)\n{insert_sql}"
            )
            text_count += 1
        else:
            # 标准格式外表
            ext_ddl = generate_standard_ext_ddl(meta, bucket, target_path, direct_read)
            ext_ddl_statements.append(
                f"-- 外表: {meta.full_name} (format: {meta.storage_format})\n{ext_ddl}"
            )
            standard_count += 1

    # 写入外表 DDL 文件
    with open(ext_ddl_path, 'w', encoding='utf-8') as f:
        f.write("-- Paimon External Table DDL (format-table)\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Standard tables: {standard_count}, TextFile tables: {text_count}\n\n")
        f.write("\n\n".join(ext_ddl_statements))
        f.write("\n")

    print(f"\n外表 DDL 已写入: {ext_ddl_path}")
    print(f"  标准格式: {standard_count} 张表")
    print(f"  TextFile: {text_count} 张表")
    print(f"  跳过: {skip_count} 张表")

    # 写入 TextFile INSERT 文件
    if text_insert_statements:
        with open(text_insert_path, 'w', encoding='utf-8') as f:
            f.write("-- TextFile Tables INSERT OVERWRITE (split + CAST)\n")
            f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Total: {text_count} tables\n\n")
            f.write("\n\n".join(text_insert_statements))
            f.write("\n")
        print(f"TextFile INSERT 已写入: {text_insert_path}")
    else:
        print("无 TextFile 格式表，跳过生成 text_tables_insert.sql")

    return 0


if __name__ == "__main__":
    sys.exit(main())
