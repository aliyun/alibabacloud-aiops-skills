#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 5: 生成并执行 INSERT OVERWRITE 将外表数据导入 Paimon 内表
输入: table_manifest.csv + text_tables_insert.sql(可选) + config.ini
输出: insert_overwrite_all.sql + insert_result.csv + step5_execution.log

支持 --max-parallel 多线程并行执行（每线程独立 Spark 连接）
支持 --verify 对比源表/目标表行数
"""

import argparse
import os
import re
import sys
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import (
    read_manifest, read_config, SparkThriftExecutor,
    safe_print, ResultWriter, classify_error, verify_row_count,
    ProgressTracker,
)


# ---------------------------------------------------------------------------
# 线程局部存储：每线程一个独立的 SparkThriftExecutor
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def _get_executor(config):
    """获取当前线程的 SparkThriftExecutor（懒初始化）"""
    if not hasattr(_thread_local, 'executor'):
        _thread_local.executor = SparkThriftExecutor(config)
    return _thread_local.executor


def _close_thread_executor():
    """关闭当前线程的 SparkThriftExecutor（如有）"""
    executor = getattr(_thread_local, 'executor', None)
    if executor:
        executor.close()
        _thread_local.executor = None


# ---------------------------------------------------------------------------
# SQL 生成
# ---------------------------------------------------------------------------

def generate_standard_insert(meta) -> str:
    """生成标准格式表的 INSERT OVERWRITE 语句"""
    ext_name = f"{meta.table_name}_oss"
    if meta.is_partitioned:
        part_keys = ", ".join(c.name for c in meta.partition_columns)
        return (f"INSERT OVERWRITE {meta.db_name}.{meta.table_name} "
                f"PARTITION ({part_keys}) "
                f"SELECT * FROM {meta.db_name}.{ext_name}")
    else:
        return (f"INSERT OVERWRITE {meta.db_name}.{meta.table_name} "
                f"SELECT * FROM {meta.db_name}.{ext_name}")


def load_text_inserts(filepath: str) -> dict:
    """
    从 text_tables_insert.sql 加载 TextFile 表的 INSERT 语句。
    返回 {full_table_name: sql_statement}
    """
    if not filepath or not os.path.exists(filepath):
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {}
    pattern = r'--\s*TextFile\s+INSERT:\s+(\S+)\s+\([^)]*\)\s*\n(.*?)(?=\n--\s*TextFile\s+INSERT:|\Z)'
    for match in re.finditer(pattern, content, re.DOTALL):
        table_name = match.group(1).strip()
        sql = match.group(2).strip()
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        result[table_name] = sql

    return result


# ---------------------------------------------------------------------------
# 单表执行（在工作线程中运行）
# ---------------------------------------------------------------------------

def _execute_one(task, config, verify, log_f):
    """
    执行单张表的 INSERT OVERWRITE。
    task = (full_name, sql, storage_format, ext_table_name)
    返回 (full_name, fmt, status, duration, error, verify_result)
    verify_result: None 或 dict {match, source_count, target_count, error}
    """
    full_name, sql, fmt, ext_table = task
    start_time = time.time()

    try:
        executor = _get_executor(config)
        ok, err = executor.execute_sql(sql, log_file=log_f)
        duration = time.time() - start_time

        if not ok:
            cat, suggestion = classify_error(err)
            err_detail = f"[{cat}] {err[:300]}  建议: {suggestion}"
            return (full_name, fmt, 'failed', round(duration, 2), err_detail, None)

        # INSERT 成功 → 可选行数校验
        vr = None
        if verify:
            try:
                match, src_cnt, tgt_cnt, verr = verify_row_count(
                    executor, ext_table, full_name)
                vr = {
                    'table': full_name,
                    'match': match,
                    'source_count': src_cnt,
                    'target_count': tgt_cnt,
                    'error': verr,
                }
            except Exception as ve:
                vr = {
                    'table': full_name,
                    'match': False,
                    'source_count': -1,
                    'target_count': -1,
                    'error': str(ve),
                }

        return (full_name, fmt, 'success', round(duration, 2), '', vr)

    except Exception as e:
        duration = time.time() - start_time
        return (full_name, fmt, 'failed', round(duration, 2), str(e), None)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Step 5: 生成并执行 INSERT OVERWRITE（支持并行 + 行数校验）',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-m', '--manifest', required=True, help='table_manifest.csv 路径')
    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('--text-insert', help='TextFile INSERT SQL 文件路径')
    parser.add_argument('--tables', help='只处理指定表，逗号分隔 (db.table)')
    parser.add_argument('--log-dir', help='日志输出目录')
    parser.add_argument('--dry-run', action='store_true', help='仅生成 SQL，不执行')
    parser.add_argument('--max-parallel', type=int, default=1,
                        help='最大并行 INSERT 数 (默认 1=串行，每线程独立 Spark 连接)')
    parser.add_argument('--verify', action='store_true',
                        help='INSERT 后对比源/目标表行数 (COUNT(*))')
    args = parser.parse_args()

    # 读取 manifest
    tables = read_manifest(args.manifest)
    filter_tables = set(t.strip() for t in args.tables.split(',')) if args.tables else None

    # 加载 TextFile INSERT 语句
    text_inserts = load_text_inserts(args.text_insert)
    if text_inserts:
        print(f"已加载 {len(text_inserts)} 条 TextFile INSERT 语句")

    # 构建所有 INSERT 任务
    # task = (full_name, sql, storage_format, ext_table_name)
    insert_tasks = []
    for meta in tables:
        if meta.error:
            continue
        if filter_tables and meta.full_name not in filter_tables:
            continue

        ext_table = f"{meta.db_name}.{meta.table_name}_oss"

        if meta.storage_format == 'text':
            sql = text_inserts.get(meta.full_name)
            if not sql:
                print(f"  警告: TextFile 表 {meta.full_name} 缺少 INSERT 语句，跳过")
                continue
            insert_tasks.append((meta.full_name, sql, 'text', ext_table))
        else:
            sql = generate_standard_insert(meta)
            insert_tasks.append((meta.full_name, sql, meta.storage_format, ext_table))

    if not insert_tasks:
        print("无需执行的 INSERT 语句，退出")
        return 0

    print(f"待执行 INSERT OVERWRITE: {len(insert_tasks)} 张表")

    # 写入汇总 SQL 文件
    output_dir = os.path.dirname(args.manifest)
    all_sql_path = os.path.join(output_dir, 'insert_overwrite_all.sql')
    with open(all_sql_path, 'w', encoding='utf-8') as f:
        f.write(f"-- INSERT OVERWRITE Statements\n")
        f.write(f"-- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Total: {len(insert_tasks)} tables\n\n")
        for full_name, sql, fmt, _ in insert_tasks:
            f.write(f"-- {full_name} (format: {fmt})\n{sql};\n\n")
    print(f"INSERT SQL 汇总: {all_sql_path}")

    # dry-run 模式
    if args.dry_run:
        print("\n=== DRY-RUN 模式：仅生成 SQL，不执行 ===")
        for full_name, sql, fmt, _ in insert_tasks:
            print(f"\n-- {full_name} ({fmt})")
            print(sql[:200] + ('...' if len(sql) > 200 else '') + ';')
        print(f"\nDRY-RUN 完成，共 {len(insert_tasks)} 条 INSERT")
        return 0

    # ------- 执行模式 -------
    config = read_config(args.config, required_sections={
        'spark_thrift': ['host', 'port', 'username', 'password']
    })
    log_dir = args.log_dir or os.path.join(output_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    max_parallel = max(1, args.max_parallel)
    result_csv_path = os.path.join(output_dir, 'insert_result.csv')
    execution_log_path = os.path.join(log_dir, 'step5_execution.log')

    # 增量 CSV 写入器
    result_writer = ResultWriter(
        result_csv_path,
        ['table_name', 'storage_format', 'status', 'duration_seconds',
         'error_msg', 'verify_match', 'source_count', 'target_count']
    )

    # 进度追踪器
    tracker = ProgressTracker(len(insert_tasks), label="INSERT OVERWRITE")

    # 打开执行日志
    log_f = open(execution_log_path, 'w', encoding='utf-8')
    verify_results = []
    all_results = []

    try:
        log_f.write(f"Step 5: INSERT OVERWRITE 执行日志\n")
        log_f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_f.write(f"待执行: {len(insert_tasks)} 张表, 并行数: {max_parallel}\n")
        log_f.write(f"行数校验: {'是' if args.verify else '否'}\n")
        log_f.write(f"{'=' * 60}\n\n")
        log_f.flush()

        if max_parallel == 1:
            # ---------- 串行模式 ----------
            executor = SparkThriftExecutor(config)
            try:
                for task in insert_tasks:
                    full_name, sql, fmt, ext_table = task
                    progress_prefix = tracker.tick(full_name)
                    safe_print(f"{progress_prefix} INSERT OVERWRITE (format: {fmt})", log_f)

                    start_time = time.time()
                    ok, err = executor.execute_sql(sql, log_file=log_f)
                    duration = time.time() - start_time

                    vr = None
                    if ok:
                        # 可选行数校验
                        if args.verify:
                            try:
                                match, src_cnt, tgt_cnt, verr = verify_row_count(
                                    executor, ext_table, full_name)
                                vr = {
                                    'table': full_name,
                                    'match': match,
                                    'source_count': src_cnt,
                                    'target_count': tgt_cnt,
                                    'error': verr,
                                }
                                verify_results.append(vr)
                                v_msg = f"  校验: {'匹配' if match else '不匹配'} " \
                                        f"(源={src_cnt}, 目标={tgt_cnt})"
                                if verr:
                                    v_msg += f"  错误: {verr}"
                                safe_print(v_msg, log_f)
                            except Exception as ve:
                                vr = {
                                    'table': full_name, 'match': False,
                                    'source_count': -1, 'target_count': -1,
                                    'error': str(ve),
                                }
                                verify_results.append(vr)
                                safe_print(f"  校验异常: {ve}", log_f)

                        row = (full_name, fmt, 'success', round(duration, 2), '',
                               str(vr.get('match', '')) if vr else '',
                               str(vr.get('source_count', '')) if vr else '',
                               str(vr.get('target_count', '')) if vr else '')
                        all_results.append(row)
                        result_writer.append(row)
                        safe_print(f"  成功 ({duration:.1f}s)", log_f)
                    else:
                        cat, suggestion = classify_error(err)
                        err_detail = f"[{cat}] {err[:300]}"
                        row = (full_name, fmt, 'failed', round(duration, 2),
                               err_detail, '', '', '')
                        all_results.append(row)
                        result_writer.append(row)
                        safe_print(f"  失败 ({duration:.1f}s): {err_detail[:150]}", log_f)
                        safe_print(f"  建议: {suggestion}", log_f)
            finally:
                executor.close()

        else:
            # ---------- 并行模式 ----------
            safe_print(f"使用 {max_parallel} 个并行线程执行 INSERT", log_f)
            thread_ids = set()

            with ThreadPoolExecutor(max_workers=max_parallel) as pool:
                futures = {}
                for task in insert_tasks:
                    future = pool.submit(_execute_one, task, config, args.verify, log_f)
                    futures[future] = task

                for future in as_completed(futures):
                    task = futures[future]
                    full_name = task[0]
                    fmt = task[2]
                    try:
                        result = future.result()
                        fn, rf, status, dur, err, vr = result
                    except Exception as e:
                        fn, rf, status, dur, err, vr = (
                            full_name, fmt, 'failed', 0, str(e), None)

                    progress_prefix = tracker.tick(fn)

                    if vr:
                        verify_results.append(vr)

                    row = (fn, rf, status, round(dur, 2),
                           err[:500] if err else '',
                           str(vr.get('match', '')) if vr else '',
                           str(vr.get('source_count', '')) if vr else '',
                           str(vr.get('target_count', '')) if vr else '')
                    all_results.append(row)
                    result_writer.append(row)

                    if status == 'success':
                        msg = f"{progress_prefix} 成功 ({dur:.1f}s)"
                        if vr:
                            match_str = '匹配' if vr.get('match') else '不匹配'
                            msg += f"  校验: {match_str} " \
                                   f"(源={vr.get('source_count')}, " \
                                   f"目标={vr.get('target_count')})"
                        safe_print(msg, log_f)
                    else:
                        safe_print(
                            f"{progress_prefix} 失败 ({dur:.1f}s): {err[:150]}",
                            log_f)

            # 关闭所有线程的 executor
            # ThreadPoolExecutor 线程退出后 thread_local 自动清理

        # 写入日志尾部
        log_f.write(f"\n{'=' * 60}\n")
        log_f.write(f"执行结束: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_f.write(tracker.summary() + '\n')
        log_f.flush()

    finally:
        log_f.close()

    # ------- 写入错误日志 -------
    error_results = [r for r in all_results if r[2] == 'failed']
    if error_results:
        error_log_path = os.path.join(log_dir, 'step5_errors.log')
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"INSERT OVERWRITE 错误日志\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"错误数: {len(error_results)}\n")
            f.write("=" * 60 + "\n\n")
            for r in error_results:
                f.write(f"--- {r[0]} ({r[1]}) ---\n")
                f.write(f"错误: {r[4]}\n\n")

    # ------- 汇总 -------
    success_count = sum(1 for r in all_results if r[2] == 'success')
    failed_count = sum(1 for r in all_results if r[2] == 'failed')
    total_duration = sum(r[3] for r in all_results)

    print(f"\n{'=' * 60}")
    print(f"INSERT OVERWRITE 执行汇总:")
    print(f"  总计: {len(all_results)} 张表")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  总耗时: {total_duration:.1f}s")
    if max_parallel > 1:
        print(f"  并行数: {max_parallel}")
    if failed_count > 0:
        print(f"  失败明细:")
        for r in all_results:
            if r[2] == 'failed':
                cat_match = r[4][:40] if r[4] else ''
                print(f"    - {r[0]}: {cat_match}")

    if verify_results:
        match_count = sum(1 for v in verify_results if v.get('match'))
        mismatch_count = sum(1 for v in verify_results if not v.get('match'))
        print(f"\n  行数校验:")
        print(f"    匹配: {match_count}")
        print(f"    不匹配: {mismatch_count}")
        for v in verify_results:
            if not v.get('match'):
                print(f"    ! {v['table']}: 源={v.get('source_count')} "
                      f"目标={v.get('target_count')} {v.get('error', '')}")

    print(f"\n  结果 CSV:  {result_csv_path}")
    print(f"  执行日志:  {execution_log_path}")
    print(f"{'=' * 60}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
