#!/usr/bin/env python3
"""Hive DDL 转 DLF DDL - CLI 入口脚本。

用法:
  cat hive_ddl.sql | python hive_to_dlf.py --mode paimon
  cat hive_ddl.sql | python hive_to_dlf.py --mode ext --source-hdfs-nameservice ns1 --oss-bucket bucket --oss-prefix prefix
  cat hive_ddl.sql | python hive_to_dlf.py --mode both --source-hdfs-nameservice ns1 --oss-bucket bucket --oss-prefix prefix
"""

import argparse
import sys
import os

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import parse_ddl
from transformer import to_paimon, to_external, ExtConfig
from formatter import format_batch_output, format_both_output


def main():
    args = parse_args()

    # 读取 stdin
    ddl_text = sys.stdin.read().strip()
    if not ddl_text:
        print("ERROR: No input received from stdin", file=sys.stderr)
        sys.exit(1)

    # 解析 DDL
    tables = parse_ddl(ddl_text)
    if not tables:
        print("ERROR: Failed to parse DDL - no CREATE TABLE statements found", file=sys.stderr)
        sys.exit(2)

    # 模式校验
    if args.mode in ("ext", "both"):
        missing = []
        if not args.source_hdfs_nameservice:
            missing.append("--source-hdfs-nameservice")
        if not args.oss_bucket:
            missing.append("--oss-bucket")
        if not args.oss_prefix:
            missing.append("--oss-prefix")
        if missing:
            print(
                f"ERROR: Missing required arguments for ext mode: {', '.join(missing)}",
                file=sys.stderr
            )
            sys.exit(3)

    # 构建外表配置
    ext_config = None
    if args.mode in ("ext", "both"):
        ext_config = ExtConfig(
            source_hdfs_nameservice=args.source_hdfs_nameservice,
            oss_bucket=args.oss_bucket,
            oss_prefix=args.oss_prefix,
            ext_table_prefix=args.ext_table_prefix,
            default_format=args.default_format,
        )

    # 转换
    all_warnings = []

    if args.mode == "paimon":
        results = []
        for table in tables:
            ddl, warnings = to_paimon(table)
            results.append((table.database, table.table_name, ddl, warnings))
        output, warnings = format_batch_output(results, "paimon")
        all_warnings.extend(warnings)

    elif args.mode == "ext":
        results = []
        for table in tables:
            ddl, warnings = to_external(table, ext_config)
            results.append((table.database, table.table_name, ddl, warnings))
        output, warnings = format_batch_output(results, "ext")
        all_warnings.extend(warnings)

    elif args.mode == "both":
        paimon_results = []
        ext_results = []
        for table in tables:
            p_ddl, p_warnings = to_paimon(table)
            paimon_results.append((table.database, table.table_name, p_ddl, p_warnings))
            e_ddl, e_warnings = to_external(table, ext_config)
            ext_results.append((table.database, table.table_name, e_ddl, e_warnings))
        output, warnings = format_both_output(paimon_results, ext_results)
        all_warnings.extend(warnings)

    # 输出
    print(output)

    # 警告输出到 stderr（去重）
    seen = set()
    for w in all_warnings:
        if w not in seen:
            seen.add(w)
            print(w, file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description="将 Hive DDL 转换为 DLF DDL（Paimon 内表 / FORMAT 外表）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  cat ddl.sql | python hive_to_dlf.py --mode paimon
  cat ddl.sql | python hive_to_dlf.py --mode both \\
    --source-hdfs-nameservice nameservice1 \\
    --oss-bucket my-bucket --oss-prefix temp_upload
"""
    )
    parser.add_argument(
        "--mode", required=True, choices=["paimon", "ext", "both"],
        help="输出模式: paimon(内表), ext(外表), both(两者)"
    )
    parser.add_argument(
        "--source-hdfs-nameservice",
        help="HDFS NameService 名称（ext/both 模式必填）"
    )
    parser.add_argument(
        "--oss-bucket",
        help="目标 OSS Bucket（ext/both 模式必填）"
    )
    parser.add_argument(
        "--oss-prefix",
        help="OSS 路径前缀（ext/both 模式必填）"
    )
    parser.add_argument(
        "--ext-table-prefix", default="ext_",
        help="外表命名前缀（默认 ext_）"
    )
    parser.add_argument(
        "--default-format", default="ORC",
        help="无 SERDE 信息时的默认存储格式（默认 ORC）"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
