#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3: 连接 Spark Thrift Server 执行建表 DDL
输入: paimon_ddl.sql + paimon_ext_ddl.sql + config.ini
输出: ddl_result.csv + step3_execution.log
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

from common import (
    read_config, SparkThriftExecutor,
    extract_table_name_from_sql, split_sql_file,
    classify_error,
)


def _log_and_print(log_f, msg):
    """同时输出到控制台和日志文件"""
    print(msg)
    if log_f:
        log_f.write(msg + '\n')
        log_f.flush()


def _extract_databases(stmts):
    """从 DDL 语句列表中提取唯一数据库名"""
    dbs = set()
    for sql in stmts:
        tbl = extract_table_name_from_sql(sql)
        if '.' in tbl:
            dbs.add(tbl.split('.')[0])
    return sorted(dbs)


def main():
    parser = argparse.ArgumentParser(
        description='Step 3: 连接 Spark 执行建表 DDL（含详细日志和结果记录）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('--inner-ddl', required=True, help='Paimon 内表 DDL 文件')
    parser.add_argument('--ext-ddl', required=True, help='Paimon 外表 DDL 文件')
    parser.add_argument('--log-dir', help='日志输出目录')
    parser.add_argument('--dry-run', action='store_true', help='仅打印 SQL，不执行')
    parser.add_argument('--auto-create-db', action='store_true',
                        help='自动创建不存在的数据库 (CREATE DATABASE IF NOT EXISTS)')
    parser.add_argument('--force', action='store_true',
                        help='强制重建：在 CREATE TABLE 前执行 DROP TABLE IF EXISTS')
    args = parser.parse_args()

    # 验证文件存在
    for f, label in [(args.inner_ddl, '内表 DDL'), (args.ext_ddl, '外表 DDL')]:
        if not os.path.exists(f):
            print(f"错误：{label}文件不存在: {f}")
            return 1

    # 确定输出路径
    output_dir = os.path.dirname(os.path.abspath(args.inner_ddl))
    log_dir = args.log_dir or os.path.join(output_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    result_csv_path = os.path.join(output_dir, 'ddl_result.csv')
    execution_log_path = os.path.join(log_dir, 'step3_execution.log')

    # 解析 SQL 文件
    inner_stmts = split_sql_file(args.inner_ddl)
    ext_stmts = split_sql_file(args.ext_ddl)
    total = len(inner_stmts) + len(ext_stmts)

    print(f"内表 DDL: {len(inner_stmts)} 条, 外表 DDL: {len(ext_stmts)} 条, 总计: {total} 条")
    if args.auto_create_db:
        print("自动建库模式: 将自动创建不存在的数据库")
    if args.force:
        print("强制重建模式: 将 DROP TABLE IF EXISTS 后重新创建")

    # dry-run 模式
    if args.dry_run:
        print(f"\n=== DRY-RUN 模式 ===\n")
        if args.auto_create_db:
            dbs = _extract_databases(inner_stmts + ext_stmts)
            print(f"将自动创建 {len(dbs)} 个数据库: {', '.join(dbs)}")

        print(f"\n内表 DDL ({len(inner_stmts)} 条):")
        for sql in inner_stmts[:5]:
            tbl = extract_table_name_from_sql(sql)
            prefix = "[DROP+CREATE]" if args.force else ""
            print(f"  - {prefix} {tbl}")
        if len(inner_stmts) > 5:
            print(f"  ... 共 {len(inner_stmts)} 条")

        print(f"\n外表 DDL ({len(ext_stmts)} 条):")
        for sql in ext_stmts[:5]:
            tbl = extract_table_name_from_sql(sql)
            prefix = "[DROP+CREATE]" if args.force else ""
            print(f"  - {prefix} {tbl}")
        if len(ext_stmts) > 5:
            print(f"  ... 共 {len(ext_stmts)} 条")

        print(f"\n结果 CSV 将输出到: {result_csv_path}")
        print(f"执行日志将输出到: {execution_log_path}")
        print(f"\nDRY-RUN 完成，共 {total} 条 DDL")
        return 0

    # 连接 Spark
    config = read_config(args.config, required_sections={
        'spark_thrift': ['host', 'port', 'username', 'password']
    })

    # 用于收集所有结果: [(table_name, ddl_type, status, duration, error_msg)]
    all_results = []

    # 打开日志文件
    log_f = open(execution_log_path, 'w', encoding='utf-8')
    try:
        log_f.write(f"Step 3: DDL 执行日志\n")
        log_f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_f.write(f"内表 DDL: {args.inner_ddl} ({len(inner_stmts)} 条)\n")
        log_f.write(f"外表 DDL: {args.ext_ddl} ({len(ext_stmts)} 条)\n")
        if args.auto_create_db:
            log_f.write("模式: --auto-create-db\n")
        if args.force:
            log_f.write("模式: --force\n")
        log_f.write(f"{'=' * 60}\n\n")
        log_f.flush()

        executor = SparkThriftExecutor(config)
        try:
            # ---- 阶段 0: 自动建库 ----
            if args.auto_create_db:
                dbs = _extract_databases(inner_stmts + ext_stmts)
                if dbs:
                    _log_and_print(log_f, f"\n{'=' * 60}")
                    _log_and_print(log_f, f"阶段 0: 自动创建数据库 ({len(dbs)} 个)")
                    _log_and_print(log_f, f"{'=' * 60}")

                    for db_name in dbs:
                        create_db_sql = f"CREATE DATABASE IF NOT EXISTS {db_name}"
                        start = time.time()
                        ok, err = executor.execute_sql(create_db_sql, log_file=log_f)
                        dur = time.time() - start
                        status = 'success' if ok else 'failed'
                        all_results.append((db_name, 'create_db', status,
                                            round(dur, 2), err if not ok else ''))
                        if not ok:
                            cat, sug = classify_error(err)
                            _log_and_print(log_f, f"    [{cat}] {sug}")

            # ---- 阶段 1: 内表 DDL ----
            _log_and_print(log_f, f"\n{'=' * 60}")
            _log_and_print(log_f, f"阶段 1: 执行 Paimon 内表 DDL ({len(inner_stmts)} 条)")
            _log_and_print(log_f, f"{'=' * 60}")

            for i, sql in enumerate(inner_stmts, 1):
                table_name = extract_table_name_from_sql(sql)

                # --force: 先 DROP
                if args.force:
                    drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                    drop_start = time.time()
                    drop_ok, drop_err = executor.execute_sql(drop_sql, log_file=log_f)
                    drop_dur = time.time() - drop_start
                    all_results.append((table_name, 'drop_inner',
                                        'success' if drop_ok else 'failed',
                                        round(drop_dur, 2),
                                        drop_err if not drop_ok else ''))

                start = time.time()
                ok, err = executor.execute_sql(sql, log_file=log_f)
                dur = time.time() - start
                status = 'success' if ok else 'failed'
                all_results.append((table_name, 'inner', status, round(dur, 2),
                                    err if not ok else ''))

                if not ok:
                    log_f.write(f"    FAILED SQL:\n    {sql[:500]}\n")
                    log_f.flush()
                    cat, sug = classify_error(err)
                    _log_and_print(log_f, f"    [{cat}] {sug}")

            # ---- 阶段 2: 外表 DDL ----
            _log_and_print(log_f, f"\n{'=' * 60}")
            _log_and_print(log_f, f"阶段 2: 执行 Paimon 外表 DDL ({len(ext_stmts)} 条)")
            _log_and_print(log_f, f"{'=' * 60}")

            for i, sql in enumerate(ext_stmts, 1):
                table_name = extract_table_name_from_sql(sql)

                # --force: 先 DROP
                if args.force:
                    drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                    drop_start = time.time()
                    drop_ok, drop_err = executor.execute_sql(drop_sql, log_file=log_f)
                    drop_dur = time.time() - drop_start
                    all_results.append((table_name, 'drop_ext',
                                        'success' if drop_ok else 'failed',
                                        round(drop_dur, 2),
                                        drop_err if not drop_ok else ''))

                start = time.time()
                ok, err = executor.execute_sql(sql, log_file=log_f)
                dur = time.time() - start
                status = 'success' if ok else 'failed'
                all_results.append((table_name, 'ext', status, round(dur, 2),
                                    err if not ok else ''))

                if not ok:
                    log_f.write(f"    FAILED SQL:\n    {sql[:500]}\n")
                    log_f.flush()
                    cat, sug = classify_error(err)
                    _log_and_print(log_f, f"    [{cat}] {sug}")

        finally:
            executor.close()

        # 写入日志汇总
        log_f.write(f"\n{'=' * 60}\n")
        log_f.write(f"执行结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_f.flush()

    finally:
        log_f.close()

    # ---- 写入结果 CSV ----
    with open(result_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['table_name', 'ddl_type', 'status', 'duration_seconds', 'error_msg'])
        for r in all_results:
            writer.writerow(r)

    # ---- 汇总统计 ----
    inner_success = sum(1 for r in all_results if r[1] == 'inner' and r[2] == 'success')
    inner_failed = sum(1 for r in all_results if r[1] == 'inner' and r[2] == 'failed')
    ext_success = sum(1 for r in all_results if r[1] == 'ext' and r[2] == 'success')
    ext_failed = sum(1 for r in all_results if r[1] == 'ext' and r[2] == 'failed')
    db_success = sum(1 for r in all_results if r[1] == 'create_db' and r[2] == 'success')
    total_success = inner_success + ext_success
    total_failed = inner_failed + ext_failed

    print(f"\n{'=' * 60}")
    print(f"DDL 执行汇总:")
    if db_success > 0:
        print(f"  建库: {db_success} 个数据库已创建/已存在")
    print(f"  内表: {inner_success}/{len(inner_stmts)} 成功, {inner_failed} 失败")
    print(f"  外表: {ext_success}/{len(ext_stmts)} 成功, {ext_failed} 失败")
    print(f"  合计: {total_success} 成功, {total_failed} 失败")

    if total_failed > 0:
        print(f"\n  失败明细:")
        for r in all_results:
            if r[2] == 'failed' and r[1] in ('inner', 'ext'):
                cat, sug = classify_error(r[4])
                print(f"    - [{r[1]}] {r[0]}: {r[4][:100]}")
                print(f"      -> [{cat}] {sug}")

    print(f"\n  结果 CSV:  {result_csv_path}")
    print(f"  执行日志:  {execution_log_path}")
    print(f"{'=' * 60}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
