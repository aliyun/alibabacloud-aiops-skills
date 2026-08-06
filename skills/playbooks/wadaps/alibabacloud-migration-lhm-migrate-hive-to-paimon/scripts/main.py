#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hive-to-Paimon 存量迁移 - 编排主脚本
串联 Step 1-5，支持断点续跑、步骤跳过、预检查和迁移报告
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

# 将 scripts 目录加入 PYTHONPATH 以便导入 common
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from common import (
    read_config, validate_config_values, SparkThriftExecutor,
    StepResult, MigrationReport, write_migration_report,
)


STEPS = [
    {
        'num': 1,
        'name': '生成 Paimon 内表 DDL',
        'script': 'step1_generate_paimon_ddl.py',
        'outputs': ['paimon_ddl.sql', 'table_manifest.csv'],
    },
    {
        'num': 2,
        'name': '生成 Paimon 外表 DDL',
        'script': 'step2_generate_ext_ddl.py',
        'outputs': ['paimon_ext_ddl.sql', 'text_tables_insert.sql'],
    },
    {
        'num': 3,
        'name': '执行建表 DDL',
        'script': 'step3_execute_ddl.py',
        'outputs': ['ddl_result.csv'],
    },
    {
        'num': 4,
        'name': 'rclone 数据同步',
        'script': 'step4_rclone_sync.py',
        'outputs': ['rclone_result.csv'],
    },
    {
        'num': 5,
        'name': 'INSERT OVERWRITE 数据导入',
        'script': 'step5_insert_overwrite.py',
        'outputs': ['insert_overwrite_all.sql', 'insert_result.csv'],
    },
]


# ---------------------------------------------------------------------------
# 预检查
# ---------------------------------------------------------------------------

def run_preflight_checks(config_path, args):
    """
    执行预检查：配置校验 + Spark 连通性测试。
    返回 (passed: bool, messages: list[str])
    """
    messages = []
    passed = True

    # 1. 配置占位符检测
    config = read_config(config_path)
    sections_to_check = {}

    if config.has_section('spark_thrift'):
        sections_to_check['spark_thrift'] = [
            'host', 'port', 'username', 'password']

    if not args.direct_read and config.has_section('rclone_source_hdfs'):
        sections_to_check['rclone_source_hdfs'] = ['name']
    if not args.direct_read and config.has_section('rclone_target_s3'):
        sections_to_check['rclone_target_s3'] = [
            'name', 'endpoint', 'access_key_id', 'secret_access_key', 'bucket']

    if config.has_section('paimon'):
        sections_to_check['paimon'] = ['warehouse', 'catalog_name']

    if sections_to_check:
        warnings = validate_config_values(config, sections_to_check)
        if warnings:
            passed = False
            messages.append("配置校验失败 - 检测到占位符值:")
            for w in warnings:
                messages.append(f"  ! {w}")
            messages.append("请先修改 config.ini 中的占位符为实际值")

    # 2. Spark 连通性测试（仅当需要 Spark 连接的步骤未跳过时检测）
    skip_steps = set()
    if args.skip_steps:
        skip_steps = set(int(s.strip()) for s in args.skip_steps.split(','))
    if args.direct_read:
        skip_steps.add(4)

    needs_spark = any(s not in skip_steps and s >= args.start_step
                      for s in [3, 5])
    if needs_spark and config.has_section('spark_thrift'):
        messages.append("测试 Spark Thrift Server 连通性...")
        ok, err = SparkThriftExecutor.quick_test(config)
        if ok:
            messages.append("  Spark 连接: 正常")
        else:
            passed = False
            messages.append(f"  Spark 连接: 失败 - {err}")
            messages.append("  请检查 [spark_thrift] 配置或 Spark Thrift Server 状态")

    if passed:
        messages.append("预检查通过")

    return passed, messages


# ---------------------------------------------------------------------------
# 步骤执行
# ---------------------------------------------------------------------------

def run_step(step, cmd_args, dry_run=False):
    """执行单个步骤"""
    script_path = os.path.join(SCRIPT_DIR, step['script'])
    cmd = [sys.executable, script_path] + cmd_args

    # 只有 Step 3/4/5（涉及外部系统）需要 dry-run，Step 1/2 纯本地生成
    if dry_run and step['num'] >= 3:
        cmd.append('--dry-run')

    print(f"\n{'=' * 60}")
    print(f"Step {step['num']}: {step['name']}")
    print(f"脚本: {step['script']}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    start_time = time.time()
    result = subprocess.run(cmd)
    duration = time.time() - start_time

    status = '成功' if result.returncode == 0 else '失败'
    print(f"\nStep {step['num']} {status} (耗时: {duration:.1f}s)")

    return result.returncode, duration


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Hive-to-Paimon 存量迁移编排主脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 使用探查目录执行完整迁移
  python main.py -e /path/to/hive_explore_dir -c config.ini

  # 指定数据库迁移
  python main.py -d ads,dwd -c config.ini

  # 从 Step 3 开始（前置输出已存在）
  python main.py -e /path/to/explore -c config.ini --start-step 3 --output-dir output/20260413

  # 跳过 rclone 同步（手动同步数据）
  python main.py -e /path/to/explore -c config.ini --skip-steps 4

  # dry-run 全流程
  python main.py -e /path/to/explore -c config.ini --dry-run

  # 直读模式（OSS-HDFS/DLS 场景，跳过 rclone，外表直接指向源端路径）
  python main.py -e /path/to/explore -c config.ini --direct-read

  # 自动建库 + 强制重建 + 并行 INSERT + 行数校验
  python main.py -e /path/to/explore -c config.ini \\
      --auto-create-db --force --max-parallel 4 --verify
        '''
    )

    # 输入来源
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-e', '--explore-dir', help='migration-lhm-inspect-hive-metastore 探查输出目录')
    input_group.add_argument('-d', '--databases', help='数据库名列表，逗号分隔')
    input_group.add_argument('-t', '--tables', help='表名列表 (db.table)，逗号分隔')

    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录 (默认: output/<timestamp>)')
    parser.add_argument('--start-step', type=int, default=1, choices=[1, 2, 3, 4, 5],
                        help='从第几步开始执行 (默认: 1)')
    parser.add_argument('--skip-steps', help='跳过的步骤，逗号分隔 (如: 3,4)')
    parser.add_argument('--dry-run', action='store_true', help='所有步骤均 dry-run')
    parser.add_argument('--direct-read', action='store_true',
                        help='直读模式：外表直接指向源端原始路径，自动跳过 rclone（适用于 OSS-HDFS/DLS 场景）')
    parser.add_argument('--filter-db', help='在探查结果上过滤数据库，逗号分隔')
    parser.add_argument('--filter-tables', help='在探查结果上过滤表，逗号分隔')

    # Step 3 新增参数
    parser.add_argument('--auto-create-db', action='store_true',
                        help='Step 3: 自动创建不存在的数据库')
    parser.add_argument('--force', action='store_true',
                        help='Step 3: 强制重建 (DROP TABLE IF EXISTS + CREATE)')

    # Step 5 新增参数
    parser.add_argument('--max-parallel', type=int, default=1,
                        help='Step 5: INSERT 并行数 (默认 1=串行)')
    parser.add_argument('--verify', action='store_true',
                        help='Step 5: INSERT 后对比源/目标表行数')
    parser.add_argument('--partition-info',
                        help='分区信息 CSV 文件路径，用于生成分区感知的 COUNT 校验 SQL')

    # 预检查控制
    parser.add_argument('--skip-preflight', action='store_true',
                        help='跳过预检查（配置校验 + Spark 连通性测试）')

    args = parser.parse_args()

    # 解析跳过步骤
    skip_steps = set()
    if args.skip_steps:
        skip_steps = set(int(s.strip()) for s in args.skip_steps.split(','))

    # 直读模式：自动跳过 Step 4 (rclone)
    if args.direct_read:
        skip_steps.add(4)
        print("直读模式: 外表将指向源端原始路径，自动跳过 Step 4 (rclone 数据同步)")

    # 创建输出目录
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = os.path.join("output", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)

    config_path = os.path.abspath(args.config)

    # ------- 预检查 -------
    if not args.skip_preflight and not args.dry_run:
        print("\n" + "-" * 60)
        print("执行预检查...")
        print("-" * 60)
        passed, messages = run_preflight_checks(config_path, args)
        for msg in messages:
            print(f"  {msg}")
        if not passed:
            print("\n预检查失败，停止执行。使用 --skip-preflight 可跳过预检查。")
            return 1
        print("-" * 60 + "\n")

    # ------- 初始化迁移报告 -------
    report = MigrationReport(
        config_path=config_path,
        output_dir=output_dir,
        direct_read=args.direct_read,
    )
    if args.explore_dir:
        report.input_source = f"探查目录: {args.explore_dir}"
    elif args.databases:
        report.input_source = f"数据库: {args.databases}"
    else:
        report.input_source = f"表: {args.tables}"

    # ------- 打印总览 -------
    print("=" * 60)
    print("Hive-to-Paimon 存量迁移")
    print("=" * 60)
    print(f"输出目录: {output_dir}")
    print(f"配置文件: {config_path}")
    print(f"起始步骤: {args.start_step}")
    print(f"跳过步骤: {skip_steps or '无'}")
    print(f"Dry-run:  {args.dry_run}")
    if args.direct_read:
        print(f"直读模式: 是（外表直接指向源端路径，跳过 rclone）")
    if args.auto_create_db:
        print(f"自动建库: 是")
    if args.force:
        print(f"强制重建: 是 (DROP + CREATE)")
    if args.max_parallel > 1:
        print(f"INSERT 并行: {args.max_parallel}")
    if args.verify:
        print(f"行数校验: 是")

    # 输入参数
    if args.explore_dir:
        print(f"输入来源: 探查目录 {args.explore_dir}")
    elif args.databases:
        print(f"输入来源: 数据库 {args.databases}")
    else:
        print(f"输入来源: 表 {args.tables}")

    # ------- 执行各步骤 -------
    step_results = {}  # {step_num: (returncode, duration)}

    for step in STEPS:
        step_num = step['num']

        if step_num < args.start_step:
            print(f"\n>>> 跳过 Step {step_num} (start-step={args.start_step})")
            report.steps.append(StepResult(
                step_num=step_num, step_name=step['name'], status='skipped'))
            continue
        if step_num in skip_steps:
            print(f"\n>>> 跳过 Step {step_num} (skip-steps)")
            report.steps.append(StepResult(
                step_num=step_num, step_name=step['name'], status='skipped'))
            continue

        # 构建各步骤的命令参数
        cmd_args = []

        if step_num == 1:
            if args.explore_dir:
                cmd_args.extend(['-e', args.explore_dir])
            elif args.databases:
                cmd_args.extend(['-d', args.databases])
            else:
                cmd_args.extend(['-t', args.tables])
            cmd_args.extend(['-c', config_path, '-o', output_dir])
            if args.filter_db:
                cmd_args.extend(['--filter-db', args.filter_db])
            if args.filter_tables:
                cmd_args.extend(['--filter-tables', args.filter_tables])

        elif step_num == 2:
            manifest_path = os.path.join(output_dir, 'table_manifest.csv')
            if not args.dry_run and not os.path.exists(manifest_path):
                print(f"\n错误: Step 2 需要 {manifest_path}，请先执行 Step 1")
                return 1
            cmd_args.extend(['-m', manifest_path, '-c', config_path, '-o', output_dir])
            if args.direct_read:
                cmd_args.append('--direct-read')

        elif step_num == 3:
            inner_ddl = os.path.join(output_dir, 'paimon_ddl.sql')
            ext_ddl = os.path.join(output_dir, 'paimon_ext_ddl.sql')
            if not args.dry_run:
                for f, label in [(inner_ddl, 'paimon_ddl.sql'), (ext_ddl, 'paimon_ext_ddl.sql')]:
                    if not os.path.exists(f):
                        print(f"\n错误: Step 3 需要 {label}，请先执行 Step 1 和 2")
                        return 1
            log_dir = os.path.join(output_dir, 'logs')
            cmd_args.extend(['-c', config_path, '--inner-ddl', inner_ddl,
                             '--ext-ddl', ext_ddl, '--log-dir', log_dir])
            # 透传新参数
            if args.auto_create_db:
                cmd_args.append('--auto-create-db')
            if args.force:
                cmd_args.append('--force')

        elif step_num == 4:
            manifest_path = os.path.join(output_dir, 'table_manifest.csv')
            if not args.dry_run and not os.path.exists(manifest_path):
                print(f"\n错误: Step 4 需要 table_manifest.csv，请先执行 Step 1")
                return 1
            log_dir = os.path.join(output_dir, 'logs')
            cmd_args.extend(['-m', manifest_path, '-c', config_path, '--log-dir', log_dir])

        elif step_num == 5:
            manifest_path = os.path.join(output_dir, 'table_manifest.csv')
            if not args.dry_run and not os.path.exists(manifest_path):
                print(f"\n错误: Step 5 需要 table_manifest.csv，请先执行 Step 1")
                return 1
            log_dir = os.path.join(output_dir, 'logs')
            cmd_args.extend(['-m', manifest_path, '-c', config_path, '--log-dir', log_dir])
            text_insert = os.path.join(output_dir, 'text_tables_insert.sql')
            if os.path.exists(text_insert):
                cmd_args.extend(['--text-insert', text_insert])
            # 透传新参数
            if args.max_parallel > 1:
                cmd_args.extend(['--max-parallel', str(args.max_parallel)])
            if args.verify:
                cmd_args.append('--verify')

        returncode, duration = run_step(step, cmd_args, dry_run=args.dry_run)
        step_results[step_num] = (returncode, duration)

        # 记录到报告
        sr = StepResult(
            step_num=step_num,
            step_name=step['name'],
            status='success' if returncode == 0 else 'failed',
            duration=round(duration, 1),
        )
        report.steps.append(sr)

        if returncode != 0 and not args.dry_run:
            print(f"\nStep {step_num} 失败，停止执行后续步骤")
            break

    # ------- 全流程汇总 -------
    print("\n" + "=" * 60)
    print("迁移流程汇总")
    print("=" * 60)

    for step in STEPS:
        num = step['num']
        if num in step_results:
            rc, dur = step_results[num]
            status = '成功' if rc == 0 else '失败'
            print(f"  Step {num}: {step['name']} - {status} ({dur:.1f}s)")
        elif num < args.start_step:
            print(f"  Step {num}: {step['name']} - 跳过 (start-step)")
        elif num in skip_steps:
            print(f"  Step {num}: {step['name']} - 跳过 (skip-steps)")
        else:
            print(f"  Step {num}: {step['name']} - 未执行")

    print(f"\n输出目录: {output_dir}")

    # 列出输出文件
    print("\n输出文件:")
    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            print(f"  {fname} ({size:,} bytes)")
    logs_dir = os.path.join(output_dir, 'logs')
    if os.path.isdir(logs_dir):
        log_files = os.listdir(logs_dir)
        if log_files:
            print(f"  logs/ ({len(log_files)} 个日志文件)")

    # ------- 生成迁移报告 -------
    report_path = write_migration_report(report, output_dir)
    print(f"\n  迁移报告: {report_path}")

    # ------- 生成 COUNT 校验 SQL（可选） -------
    if args.partition_info:
        try:
            from utils_verification import read_partition_info, generate_count_verification_sql
            partition_info = read_partition_info(args.partition_info)
            # 从 table_manifest.csv 读取表列表
            manifest_path = os.path.join(output_dir, 'table_manifest.csv')
            verify_tables = []
            if os.path.exists(manifest_path):
                import csv
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        db = row.get('db_name', row.get('db', ''))
                        tbl = row.get('table_name', row.get('table', ''))
                        if db and tbl:
                            verify_tables.append(f"{db}.{tbl}")
            if verify_tables:
                count_sql = generate_count_verification_sql(verify_tables, partition_info)
                count_sql_path = os.path.join(output_dir, 'count_verification.sql')
                with open(count_sql_path, 'w', encoding='utf-8') as f:
                    f.write(count_sql)
                print(f"  COUNT 校验 SQL: {count_sql_path}")
        except Exception as e:
            print(f"  [WARN] 生成 COUNT 校验 SQL 失败: {e}")

    print("=" * 60)

    # 任意步骤失败则返回非零
    failed = any(rc != 0 for rc, _ in step_results.values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
