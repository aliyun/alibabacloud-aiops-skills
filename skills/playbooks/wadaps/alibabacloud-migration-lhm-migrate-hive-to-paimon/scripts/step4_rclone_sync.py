#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 4: 自动执行 rclone 将 HDFS 数据同步到 OSS
输入: table_manifest.csv + config.ini
输出: rclone_result.csv + 各表 rclone 日志 + step4_rclone_master.log

支持 --background 后台执行，关闭终端不影响运行。
"""

import argparse
import csv
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from common import (
    read_manifest, read_config, get_oss_relative_path,
    add_rclone_override_args, apply_rclone_overrides, build_rclone_override_cmd_args,
    ensure_rclone_installed,
)


# ---------------------------------------------------------------------------
# 线程安全的增量 CSV 写入器
# ---------------------------------------------------------------------------

class _ResultWriter:
    """线程安全的 CSV 写入器，每完成一张表就追加写入"""

    def __init__(self, path):
        self._path = path
        self._lock = threading.Lock()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['db_name', 'table_name', 'status', 'duration_seconds', 'error_msg'])

    def append(self, row):
        with self._lock:
            with open(self._path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)


# ---------------------------------------------------------------------------
# 线程安全的日志打印
# ---------------------------------------------------------------------------

_print_lock = threading.Lock()


def safe_print(msg, log_f=None):
    """线程安全的打印，同时写入主日志文件"""
    with _print_lock:
        print(msg)
        if log_f:
            log_f.write(msg + '\n')
            log_f.flush()


# ---------------------------------------------------------------------------
# rclone 操作
# ---------------------------------------------------------------------------

def setup_rclone(config, log_f=None):
    """初始化 rclone 远程配置，支持 HDFS 和 S3/OSS 两种源端类型"""
    src = config['rclone_source_hdfs']
    tgt = config['rclone_target_s3']

    safe_print("正在配置 rclone 远程...", log_f)

    # 配置源端（根据 type 字段区分 HDFS 和 S3）
    src_type = src.get('type', 'hdfs').lower()
    if src_type in ('s3', 'oss'):
        cmd_src = [
            'rclone', 'config', 'create', src['name'], 's3',
            'provider', src.get('provider', 'Alibaba'),
            'endpoint', src['endpoint'],
            'access_key_id', src['access_key_id'],
            'secret_access_key', src['secret_access_key'],
        ]
        safe_print(f"  S3 源: rclone config create {src['name']} s3 provider ... (敏感信息已隐藏)", log_f)
    else:
        cmd_src = [
            'rclone', 'config', 'create', src['name'], 'hdfs',
            'namenode', src['namenode'],
            'username', src['username'],
        ]
        safe_print(f"  HDFS 源: {' '.join(cmd_src)}", log_f)

    result = subprocess.run(cmd_src, capture_output=True, text=True)
    if result.returncode != 0:
        safe_print(f"  错误: {result.stderr}", log_f)
        sys.exit(1)

    # 配置 S3 目标
    cmd_tgt = [
        'rclone', 'config', 'create', tgt['name'], 's3',
        'provider', tgt['provider'],
        'endpoint', tgt['endpoint'],
        'access_key_id', tgt['access_key_id'],
        'secret_access_key', tgt['secret_access_key'],
    ]
    safe_print(f"  S3 目标: rclone config create {tgt['name']} s3 provider ... (敏感信息已隐藏)", log_f)
    result = subprocess.run(cmd_tgt, capture_output=True, text=True)
    if result.returncode != 0:
        safe_print(f"  错误: {result.stderr}", log_f)
        sys.exit(1)

    safe_print("rclone 配置完成", log_f)


def sync_single_table(table_info, config, log_dir, result_writer, log_f=None):
    """
    同步单张表的数据。在线程池中执行。
    完成后增量写入 result CSV。
    返回 (db_name, table_name, status, duration, error_msg)
    """
    db_name = table_info['db_name']
    table_name = table_info['table_name']
    hdfs_path = table_info['hdfs_path']
    oss_path = table_info.get('oss_path', hdfs_path)
    full_name = f"{db_name}.{table_name}"

    src_name = config.get('rclone_source_hdfs', 'name')
    tgt_name = config.get('rclone_target_s3', 'name')
    tgt_bucket = config.get('rclone_target_s3', 'bucket')
    copy_flags = config.get('rclone_options', 'copy_flags')
    bwlimit = config.get('rclone_options', 'bwlimit')

    # 构建源端路径：S3 源需要 bucket/path，HDFS 源直接用 path
    src_type = config.get('rclone_source_hdfs', 'type', fallback='hdfs').lower()
    if src_type in ('s3', 'oss'):
        src_bucket = config.get('rclone_source_hdfs', 'bucket')
        source_spec = f"{src_name}:{src_bucket}{hdfs_path}"
    else:
        source_spec = f"{src_name}:{hdfs_path}"

    # 构建 rclone 命令
    cmd = f'rclone copy {copy_flags} --bwlimit "{bwlimit}" {source_spec} {tgt_name}:{tgt_bucket}{oss_path}'

    table_log_file = os.path.join(log_dir, f"rclone_{db_name}_{table_name}.log")
    start_time = time.time()

    try:
        with open(table_log_file, 'w', encoding='utf-8') as lf:
            lf.write(f"# rclone sync: {full_name}\n")
            lf.write(f"# 命令: {cmd}\n")
            lf.write(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            process = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                lf.write(line)
            process.wait()

            duration = time.time() - start_time
            lf.write(f"\n# 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            lf.write(f"# 耗时: {duration:.1f}s\n")
            lf.write(f"# 返回码: {process.returncode}\n")

        if process.returncode == 0:
            row = (db_name, table_name, 'success', round(duration, 2), '')
        else:
            row = (db_name, table_name, 'failed', round(duration, 2),
                   f'返回码: {process.returncode}, 详见 {table_log_file}')

    except Exception as e:
        duration = time.time() - start_time
        row = (db_name, table_name, 'failed', round(duration, 2), str(e))

    # 增量写入结果 CSV
    result_writer.append(row)
    return row


# ---------------------------------------------------------------------------
# 后台执行
# ---------------------------------------------------------------------------

def _launch_background(args, log_dir):
    """以后台守护进程方式重新启动本脚本（脱离终端会话）"""
    script = os.path.abspath(__file__)

    # 重构命令行参数（去掉 --background）
    cmd = [sys.executable, script]
    cmd.extend(['-m', os.path.abspath(args.manifest)])
    cmd.extend(['-c', os.path.abspath(args.config)])
    cmd.extend(['--log-dir', os.path.abspath(log_dir)])
    if args.max_parallel:
        cmd.extend(['--max-parallel', str(args.max_parallel)])
    if args.tables:
        cmd.extend(['--tables', args.tables])
    if args.dry_run:
        cmd.append('--dry-run')
    # 透传 rclone 覆盖参数
    cmd.extend(build_rclone_override_cmd_args(args))

    master_log = os.path.join(log_dir, 'step4_rclone_master.log')
    pid_file = os.path.join(log_dir, 'step4_rclone.pid')
    result_csv = os.path.join(os.path.dirname(os.path.abspath(args.manifest)),
                              'rclone_result.csv')

    # 写入启动信息
    log_f = open(master_log, 'w', encoding='utf-8')
    log_f.write(f"# rclone 后台同步\n")
    log_f.write(f"# 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_f.write(f"# 命令: {' '.join(cmd)}\n\n")
    log_f.flush()

    # 启动子进程：start_new_session=True 使进程脱离终端会话组
    process = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_f.close()  # 父进程关闭 fd，子进程持有自己的 fd 继续写入

    with open(pid_file, 'w') as f:
        f.write(str(process.pid))

    print(f"rclone 同步已在后台启动!")
    print(f"  PID:       {process.pid}")
    print(f"  PID 文件:  {pid_file}")
    print(f"  主日志:    {master_log}")
    print(f"  结果 CSV:  {result_csv}")
    print(f"  各表日志:  {log_dir}/rclone_<db>_<table>.log")
    print()
    print(f"查看实时进度:  tail -f {master_log}")
    print(f"查看已完成数:  wc -l {result_csv}")
    print(f"检查进程状态:  ps -p {process.pid}")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Step 4: 自动执行 rclone 数据同步',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
后台执行示例:
  python step4_rclone_sync.py -m manifest.csv -c config.ini --background

  启动后可关闭终端，任务继续运行。
  查看进度: tail -f logs/step4_rclone_master.log
  查看结果: cat rclone_result.csv
        '''
    )
    parser.add_argument('-m', '--manifest', required=True, help='table_manifest.csv 路径')
    parser.add_argument('-c', '--config', default='config.ini', help='配置文件路径')
    parser.add_argument('--max-parallel', type=int, help='最大并行同步数，覆盖配置文件')
    parser.add_argument('--tables', help='只同步指定表，逗号分隔 (db.table)')
    parser.add_argument('--log-dir', help='日志输出目录')
    parser.add_argument('--dry-run', action='store_true', help='仅打印 rclone 命令')
    parser.add_argument('--background', action='store_true',
                        help='后台执行，脱离终端会话，关闭窗口不影响运行')
    add_rclone_override_args(parser)
    args = parser.parse_args()

    # 确定日志目录
    log_dir = args.log_dir or os.path.join(os.path.dirname(args.manifest), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 后台模式：以守护进程重新启动
    if args.background:
        _launch_background(args, log_dir)
        return 0

    # ---- 前台模式 ----

    # 读取配置（源端仅要求 name，具体 key 按 type 决定）
    config = read_config(args.config, required_sections={
        'rclone_source_hdfs': ['name'],
        'rclone_target_s3': ['name', 'provider', 'endpoint', 'access_key_id', 'secret_access_key', 'bucket'],
        'rclone_options': ['copy_flags', 'bwlimit'],
    })

    # 应用 CLI 覆盖参数
    apply_rclone_overrides(config, args)

    max_parallel = args.max_parallel or config.getint('rclone_options', 'max_parallel', fallback=4)
    filter_tables = set(t.strip() for t in args.tables.split(',')) if args.tables else None

    # 读取 manifest
    tables = read_manifest(args.manifest)

    # 构建同步任务列表
    sync_tasks = []
    for meta in tables:
        if meta.error or not meta.location:
            continue
        if filter_tables and meta.full_name not in filter_tables:
            continue
        hdfs_path = get_oss_relative_path(meta.location)
        target_path = config.get('rclone_target_s3', 'target_path', fallback='')
        oss_path = get_oss_relative_path(meta.location, target_path)
        sync_tasks.append({
            'db_name': meta.db_name,
            'table_name': meta.table_name,
            'hdfs_path': hdfs_path,
            'oss_path': oss_path,
        })

    if not sync_tasks:
        print("无需同步的表，退出")
        return 0

    print(f"待同步表数: {len(sync_tasks)}, 最大并行数: {max_parallel}")

    # dry-run 模式
    if args.dry_run:
        print("\n=== DRY-RUN 模式：仅打印 rclone 命令 ===\n")
        src_name = config.get('rclone_source_hdfs', 'name')
        tgt_name = config.get('rclone_target_s3', 'name')
        tgt_bucket = config.get('rclone_target_s3', 'bucket')
        copy_flags = config.get('rclone_options', 'copy_flags')
        bwlimit = config.get('rclone_options', 'bwlimit')
        src_type = config.get('rclone_source_hdfs', 'type', fallback='hdfs').lower()

        for task in sync_tasks:
            oss_path = task.get('oss_path', task['hdfs_path'])
            if src_type in ('s3', 'oss'):
                src_bucket = config.get('rclone_source_hdfs', 'bucket')
                source_spec = f'{src_name}:{src_bucket}{task["hdfs_path"]}'
            else:
                source_spec = f'{src_name}:{task["hdfs_path"]}'
            cmd = (f'rclone copy {copy_flags} --bwlimit "{bwlimit}" '
                   f'{source_spec} '
                   f'{tgt_name}:{tgt_bucket}{oss_path}')
            print(cmd)
        print(f"\nDRY-RUN 完成，共 {len(sync_tasks)} 条命令")
        return 0

    # 检查 rclone 安装
    if not ensure_rclone_installed():
        print("错误: rclone 未安装且自动安装失败，无法继续")
        return 1

    # 初始化 rclone 配置
    master_log_path = os.path.join(log_dir, 'step4_rclone_master.log')
    master_log_f = open(master_log_path, 'w', encoding='utf-8')

    try:
        master_log_f.write(f"# rclone 同步主日志\n")
        master_log_f.write(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        master_log_f.write(f"# 待同步: {len(sync_tasks)} 张表, 并行数: {max_parallel}\n")
        master_log_f.write(f"{'=' * 60}\n\n")
        master_log_f.flush()

        setup_rclone(config, log_f=master_log_f)

        # 初始化增量结果写入器
        result_csv_path = os.path.join(os.path.dirname(args.manifest), 'rclone_result.csv')
        result_writer = _ResultWriter(result_csv_path)

        # 并行执行同步
        completed = 0
        failed_count = 0
        all_results = []

        safe_print(f"\n开始同步 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
                     master_log_f)
        safe_print("-" * 60, master_log_f)

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {}
            for task in sync_tasks:
                future = executor.submit(
                    sync_single_table, task, config, log_dir,
                    result_writer, master_log_f
                )
                futures[future] = task

            for future in as_completed(futures):
                task = futures[future]
                full_name = f"{task['db_name']}.{task['table_name']}"
                try:
                    result = future.result()
                    all_results.append(result)
                    completed += 1
                    status = result[2]
                    duration = result[3]

                    if status == 'success':
                        safe_print(
                            f"  [{completed}/{len(sync_tasks)}] {full_name} - "
                            f"成功 ({duration:.1f}s)", master_log_f)
                    else:
                        failed_count += 1
                        safe_print(
                            f"  [{completed}/{len(sync_tasks)}] {full_name} - "
                            f"失败: {result[4][:100]}", master_log_f)
                except Exception as e:
                    completed += 1
                    failed_count += 1
                    err_row = (task['db_name'], task['table_name'],
                               'failed', 0, str(e))
                    all_results.append(err_row)
                    result_writer.append(err_row)
                    safe_print(
                        f"  [{completed}/{len(sync_tasks)}] {full_name} - "
                        f"异常: {e}", master_log_f)

        # 汇总
        success_count = sum(1 for r in all_results if r[2] == 'success')

        summary_lines = [
            f"\n{'=' * 60}",
            f"rclone 同步汇总:",
            f"  总计: {len(sync_tasks)} 张表",
            f"  成功: {success_count}",
            f"  失败: {failed_count}",
        ]
        if failed_count > 0:
            summary_lines.append(f"  失败明细:")
            for r in all_results:
                if r[2] == 'failed':
                    summary_lines.append(f"    - {r[0]}.{r[1]}: {r[4][:100]}")
        summary_lines.extend([
            f"  结果 CSV: {result_csv_path}",
            f"  主日志:   {master_log_path}",
            f"  各表日志: {log_dir}",
            f"{'=' * 60}",
        ])

        for line in summary_lines:
            safe_print(line, master_log_f)

    finally:
        master_log_f.close()

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
