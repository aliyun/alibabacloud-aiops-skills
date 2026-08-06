#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量迁移执行脚本
输入: migration-lhm-inspect-hive-metastore 增量探查的输出目录（sync_commands.sh + paimon_sync.sql）
输出: incr_ddl_result.csv + incr_rclone_result.csv + incr_insert_result.csv + 日志

三阶段流水线:
  Phase 1: 执行 DDL (CREATE TABLE) — 建外表和内表
  Phase 2: rclone 数据同步 (HDFS → OSS) — 并行执行
  Phase 3: 执行 DML (INSERT OVERWRITE) — 数据导入

支持 --background 后台执行，关闭终端不影响运行。
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from common import (
    read_config, SparkThriftExecutor,
    split_sql_file, extract_table_name_from_sql,
    add_rclone_override_args, apply_rclone_overrides,
    has_rclone_overrides, build_rclone_override_cmd_args,
)


# ---------------------------------------------------------------------------
# 线程安全的增量 CSV 写入器（复用 step4 模式）
# ---------------------------------------------------------------------------

class _ResultWriter:
    """线程安全的 CSV 写入器，每完成一条命令就追加写入"""

    def __init__(self, path, header):
        self._path = path
        self._lock = threading.Lock()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

    def append(self, row):
        with self._lock:
            with open(self._path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)


# ---------------------------------------------------------------------------
# 线程安全的日志打印
# ---------------------------------------------------------------------------

_print_lock = threading.Lock()


def _safe_print(msg, log_f=None):
    """线程安全的打印，同时写入日志文件"""
    with _print_lock:
        print(msg)
        if log_f:
            log_f.write(msg + '\n')
            log_f.flush()


def _log_and_print(log_f, msg):
    """同时输出到控制台和日志文件（非线程安全版，用于单线程阶段）"""
    print(msg)
    if log_f:
        log_f.write(msg + '\n')
        log_f.flush()


# ---------------------------------------------------------------------------
# 解析函数
# ---------------------------------------------------------------------------

def parse_sync_commands(sh_path: str) -> Tuple[List[str], List[str]]:
    """
    解析 sync_commands.sh，分离 rclone config 命令和 rclone copy 命令。
    返回 (config_commands, copy_commands)
    """
    config_cmds = []
    copy_cmds = []

    with open(sh_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('#!/'):
                continue
            if line.startswith('rclone config'):
                config_cmds.append(line)
            elif line.startswith('rclone copy') or line.startswith('rclone sync'):
                copy_cmds.append(line)

    return config_cmds, copy_cmds


def classify_sql_statements(sql_path: str) -> Tuple[List[str], List[str]]:
    """
    解析 paimon_sync.sql，将语句分类为 DDL 和 DML。
    返回 (ddl_statements, dml_statements)
    """
    statements = split_sql_file(sql_path)
    ddl_stmts = []
    dml_stmts = []

    for sql in statements:
        stripped = sql.strip()
        if re.match(r'CREATE\s', stripped, re.IGNORECASE):
            ddl_stmts.append(sql)
        elif re.match(r'INSERT\s', stripped, re.IGNORECASE):
            dml_stmts.append(sql)
        # SET / USE 等其他语句忽略

    return ddl_stmts, dml_stmts


def build_path_to_table_map(delta_csv_path: str) -> Dict[str, Tuple[str, str, str]]:
    """
    从 metastore_delta.csv 构建 HDFS路径 → (db_name, table_name, change_type) 映射。
    路径为 urlparse 后的 path 部分（去掉 hdfs://host:port 前缀）。
    """
    path_map = {}
    if not os.path.exists(delta_csv_path):
        return path_map

    with open(delta_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            location = row.get('location', '')
            if not location:
                continue
            try:
                parsed = urlparse(location)
                path = parsed.path
                if path:
                    path_map[path] = (
                        row.get('db_name', ''),
                        row.get('table_name', ''),
                        row.get('type', ''),
                    )
            except Exception:
                continue

    return path_map


def extract_source_path_from_rclone_cmd(cmd: str, source_remote: str) -> str:
    """
    从 rclone copy 命令中提取 source 路径。
    cmd 格式: rclone copy <flags> source_remote:/path target_remote:bucket/path
    """
    pattern = re.escape(source_remote) + r':(\S+)'
    m = re.search(pattern, cmd)
    if m:
        return m.group(1)
    return ''


def resolve_table_for_rclone(source_path: str,
                              path_map: Dict[str, Tuple[str, str, str]]
                              ) -> Tuple[str, str, str]:
    """
    根据 source 路径在 path_map 中查找对应的表信息。
    先精确匹配，再向上尝试父路径匹配（处理分区路径）。
    返回 (db_name, table_name, change_type)，找不到返回从路径推断的值。
    """
    # 精确匹配
    if source_path in path_map:
        return path_map[source_path]

    # 向上查找父路径（分区路径如 /warehouse/db.db/table/dt=xxx）
    parent = source_path
    for _ in range(3):
        parent = os.path.dirname(parent)
        if parent in path_map:
            return path_map[parent]

    # 从路径推断
    parts = source_path.rstrip('/').split('/')
    if len(parts) >= 2:
        table_name = parts[-1].split('=')[0] if '=' in parts[-1] else parts[-1]
        db_part = parts[-2] if len(parts) >= 2 else 'unknown_db'
        db_name = db_part.replace('.db', '') if db_part.endswith('.db') else db_part
        return (db_name, table_name, 'UNKNOWN')

    return ('unknown', 'unknown', 'UNKNOWN')


def extract_source_remote_name(config_cmds: List[str]) -> str:
    """从 rclone config create 命令中提取 HDFS 源的 remote 名称。"""
    for cmd in config_cmds:
        # rclone config create <name> hdfs ...
        if 'hdfs' in cmd.lower():
            parts = cmd.split()
            if len(parts) >= 4:
                return parts[3]  # rclone config create <name>
    return 'source'  # 默认 fallback


def extract_target_remote_name(config_cmds: List[str]) -> str:
    """从 rclone config create 命令中提取 S3 目标的 remote 名称。"""
    for cmd in config_cmds:
        if 's3' in cmd.lower():
            parts = cmd.split()
            if len(parts) >= 4:
                return parts[3]
    return 'target'


def _generate_config_commands(config) -> List[str]:
    """
    从 config 对象生成 rclone config create 命令列表。
    当用户通过 CLI 覆盖了 rclone 参数时，用此函数的输出替代 sync_commands.sh 中的 config 命令。
    """
    src = config['rclone_source_hdfs']
    tgt = config['rclone_target_s3']

    src_cmd = (f"rclone config create {src['name']} hdfs "
               f"namenode {src['namenode']} username {src['username']}")
    tgt_cmd = (f"rclone config create {tgt['name']} s3 "
               f"provider {tgt['provider']} endpoint {tgt['endpoint']} "
               f"access_key_id {tgt['access_key_id']} "
               f"secret_access_key {tgt['secret_access_key']}")

    return [src_cmd, tgt_cmd]


def _apply_copy_cmd_overrides(copy_cmds: List[str], args,
                               old_bucket: Optional[str] = None,
                               config_cmds: Optional[List[str]] = None) -> List[str]:
    """
    修改已解析的 rclone copy 命令，将 CLI 覆盖参数应用到命令字符串中。
    处理: bwlimit, transfers, checkers, tgt-bucket, tgt-path
    """
    tgt_remote = extract_target_remote_name(config_cmds or [])
    result = []
    for cmd in copy_cmds:
        # bwlimit
        if getattr(args, 'bwlimit', None):
            cmd = re.sub(r'--bwlimit\s+"[^"]*"',
                         f'--bwlimit "{args.bwlimit}"', cmd)
            cmd = re.sub(r"--bwlimit\s+'[^']*'",
                         f'--bwlimit "{args.bwlimit}"', cmd)
        # transfers
        if getattr(args, 'transfers', None):
            cmd = re.sub(r'--transfers\s+\d+',
                         f'--transfers {args.transfers}', cmd)
        # checkers
        if getattr(args, 'checkers', None):
            cmd = re.sub(r'--checkers\s+\d+',
                         f'--checkers {args.checkers}', cmd)
        # bucket 替换
        if getattr(args, 'tgt_bucket', None) and old_bucket:
            cmd = cmd.replace(f':{old_bucket}/', f':{args.tgt_bucket}/')
            cmd = cmd.replace(f':{old_bucket} ', f':{args.tgt_bucket} ')
        # target path 替换：将目标端路径从原始 HDFS 路径改为用户指定路径
        if getattr(args, 'tgt_path', None):
            tgt_path = args.tgt_path.strip('/')
            # 匹配 target_remote:bucket/original_path 格式
            bucket_name = getattr(args, 'tgt_bucket', None) or old_bucket or '[^/\\s]+'
            pattern = re.escape(tgt_remote) + r':(' + re.escape(bucket_name) + r')(/.+)'
            m = re.search(pattern, cmd)
            if m:
                orig_path = m.group(2)
                # 取 HDFS 路径的最后两段（db.db/table）
                parts = orig_path.rstrip('/').split('/')
                if len(parts) >= 2:
                    relative = '/'.join(parts[-2:])
                else:
                    relative = orig_path.lstrip('/')
                new_target = f'{tgt_remote}:{m.group(1)}/{tgt_path}/{relative}'
                cmd = cmd[:m.start()] + new_target + cmd[m.end():]
        result.append(cmd)
    return result


def _extract_bucket_from_copy_cmd(copy_cmds: List[str],
                                   config_cmds: List[str]) -> Optional[str]:
    """从 copy 命令中提取当前 bucket 名称（用于替换）"""
    tgt_remote = extract_target_remote_name(config_cmds)
    for cmd in copy_cmds:
        # 匹配 target_remote:bucket/path
        m = re.search(re.escape(tgt_remote) + r':([^/\s]+)', cmd)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Phase 1: DDL 执行
# ---------------------------------------------------------------------------

def run_ddl_phase(executor: SparkThriftExecutor,
                  ddl_stmts: List[str],
                  log_f, output_dir: str) -> List[tuple]:
    """
    执行 DDL 语句（CREATE TABLE），返回结果列表。
    结果格式: (table_name, ddl_type, status, duration, error_msg)
    """
    results = []
    total = len(ddl_stmts)

    _log_and_print(log_f, f"\n{'=' * 60}")
    _log_and_print(log_f, f"Phase 1: 执行 DDL ({total} 条)")
    _log_and_print(log_f, f"{'=' * 60}")

    for i, sql in enumerate(ddl_stmts, 1):
        table_name = extract_table_name_from_sql(sql)
        # 判断是外表还是内表
        ddl_type = 'ext' if '_lhm_ext' in table_name else 'inner'

        _log_and_print(log_f, f"\n[{i}/{total}] CREATE TABLE {table_name} ({ddl_type})")
        start = time.time()
        ok, err = executor.execute_sql(sql, log_file=log_f)
        dur = time.time() - start
        status = 'success' if ok else 'failed'
        results.append((table_name, ddl_type, status, round(dur, 2),
                         err if not ok else ''))

        if not ok:
            log_f.write(f"    FAILED SQL:\n    {sql[:500]}\n")
            log_f.flush()

    return results


# ---------------------------------------------------------------------------
# Phase 2: rclone 并行执行
# ---------------------------------------------------------------------------

def _run_single_rclone(cmd: str, db_name: str, table_name: str,
                        idx: int, log_dir: str,
                        result_writer: _ResultWriter,
                        master_log_f=None) -> tuple:
    """
    执行单条 rclone copy 命令。
    返回 (db_name, table_name, source_path, status, duration, error_msg)
    """
    # 从命令中提取 source_path（用于日志命名和记录）
    # 简化提取：找到第一个 remote:path 格式的参数
    source_path_match = re.search(r'\S+:(/\S+)', cmd)
    source_path = source_path_match.group(1) if source_path_match else f'cmd_{idx}'

    full_name = f"{db_name}.{table_name}"
    log_file_name = f"rclone_{db_name}_{table_name}_{idx}.log"
    table_log_path = os.path.join(log_dir, log_file_name)

    start_time = time.time()

    try:
        with open(table_log_path, 'w', encoding='utf-8') as lf:
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
            row = (db_name, table_name, source_path, 'success',
                   round(duration, 2), '')
        else:
            row = (db_name, table_name, source_path, 'failed',
                   round(duration, 2),
                   f'返回码: {process.returncode}, 详见 {table_log_path}')

    except Exception as e:
        duration = time.time() - start_time
        row = (db_name, table_name, source_path, 'failed',
               round(duration, 2), str(e))

    result_writer.append(row)
    return row


def run_rclone_phase(config_cmds: List[str], copy_cmds: List[str],
                     path_map: Dict[str, Tuple[str, str, str]],
                     log_dir: str, output_dir: str,
                     max_parallel: int,
                     master_log_f=None) -> List[tuple]:
    """
    执行 rclone 数据同步阶段。
    1. 顺序执行 rclone config create 命令
    2. 并行执行 rclone copy 命令
    返回结果列表。
    """
    _safe_print(f"\n{'=' * 60}", master_log_f)
    _safe_print(f"Phase 2: rclone 数据同步 ({len(copy_cmds)} 条命令)", master_log_f)
    _safe_print(f"{'=' * 60}", master_log_f)

    # Step 1: 执行 rclone config 配置命令
    if config_cmds:
        _safe_print(f"\n配置 rclone 远程 ({len(config_cmds)} 条)...", master_log_f)
        for cmd in config_cmds:
            _safe_print(f"  执行: {cmd[:100]}{'...' if len(cmd) > 100 else ''}",
                        master_log_f)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                _safe_print(f"  错误: {result.stderr[:200]}", master_log_f)
        _safe_print("rclone 配置完成", master_log_f)

    if not copy_cmds:
        _safe_print("无 rclone copy 命令，跳过", master_log_f)
        return []

    # 提取 source remote 名称
    source_remote = extract_source_remote_name(config_cmds)

    # 初始化结果写入器
    result_csv_path = os.path.join(output_dir, 'incr_rclone_result.csv')
    result_writer = _ResultWriter(
        result_csv_path,
        ['db_name', 'table_name', 'source_path', 'status',
         'duration_seconds', 'error_msg']
    )

    # 为每条 copy 命令解析表信息
    tasks = []
    for idx, cmd in enumerate(copy_cmds, 1):
        src_path = extract_source_path_from_rclone_cmd(cmd, source_remote)
        db_name, table_name, _ = resolve_table_for_rclone(src_path, path_map)
        tasks.append((cmd, db_name, table_name, idx))

    _safe_print(f"\n开始同步 {len(tasks)} 条命令, 并行数: {max_parallel}", master_log_f)
    _safe_print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", master_log_f)
    _safe_print("-" * 60, master_log_f)

    # Step 2: 并行执行 copy 命令
    all_results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_parallel) as pool:
        futures = {}
        for cmd, db_name, table_name, idx in tasks:
            future = pool.submit(
                _run_single_rclone, cmd, db_name, table_name,
                idx, log_dir, result_writer, master_log_f
            )
            futures[future] = (db_name, table_name)

        for future in as_completed(futures):
            db_name, table_name = futures[future]
            full_name = f"{db_name}.{table_name}"
            completed += 1
            try:
                result = future.result()
                all_results.append(result)
                status = result[3]
                duration = result[4]
                if status == 'success':
                    _safe_print(
                        f"  [{completed}/{len(tasks)}] {full_name} - "
                        f"成功 ({duration:.1f}s)", master_log_f)
                else:
                    _safe_print(
                        f"  [{completed}/{len(tasks)}] {full_name} - "
                        f"失败: {result[5][:100]}", master_log_f)
            except Exception as e:
                completed_row = (db_name, table_name, '', 'failed', 0, str(e))
                all_results.append(completed_row)
                result_writer.append(completed_row)
                _safe_print(
                    f"  [{completed}/{len(tasks)}] {full_name} - "
                    f"异常: {e}", master_log_f)

    return all_results


# ---------------------------------------------------------------------------
# Phase 3: DML 执行
# ---------------------------------------------------------------------------

def run_dml_phase(executor: SparkThriftExecutor,
                  dml_stmts: List[str],
                  log_f, output_dir: str) -> List[tuple]:
    """
    执行 DML 语句（INSERT OVERWRITE），返回结果列表。
    结果格式: (table_name, sql_type, status, duration, error_msg)
    """
    results = []
    total = len(dml_stmts)

    _log_and_print(log_f, f"\n{'=' * 60}")
    _log_and_print(log_f, f"Phase 3: 执行 INSERT OVERWRITE ({total} 条)")
    _log_and_print(log_f, f"{'=' * 60}")

    for i, sql in enumerate(dml_stmts, 1):
        table_name = extract_table_name_from_sql(sql)
        # 判断 SQL 类型
        if 'PARTITION' in sql.upper():
            sql_type = 'partition_sync'
        else:
            sql_type = 'full_sync'

        _log_and_print(log_f,
                       f"\n[{i}/{total}] INSERT OVERWRITE {table_name} ({sql_type})")
        start = time.time()
        ok, err = executor.execute_sql(sql, log_file=log_f)
        dur = time.time() - start
        status = 'success' if ok else 'failed'
        results.append((table_name, sql_type, status, round(dur, 2),
                         err if not ok else ''))

        if ok:
            _log_and_print(log_f, f"  成功 ({dur:.1f}s)")
        else:
            _log_and_print(log_f, f"  失败 ({dur:.1f}s): {err[:200]}")
            log_f.write(f"    FAILED SQL:\n    {sql[:500]}\n")
            log_f.flush()

    return results


# ---------------------------------------------------------------------------
# 后台执行
# ---------------------------------------------------------------------------

def _launch_background(args, output_dir):
    """以后台进程方式重新启动本脚本"""
    script = os.path.abspath(__file__)
    log_dir = os.path.join(output_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # 重构命令行参数（去掉 --background）
    cmd = [sys.executable, script]
    cmd.extend(['-i', os.path.abspath(args.incr_dir)])
    cmd.extend(['-c', os.path.abspath(args.config)])
    cmd.extend(['-o', os.path.abspath(output_dir)])
    if args.max_parallel:
        cmd.extend(['--max-parallel', str(args.max_parallel)])
    if args.skip_phase:
        cmd.extend(['--skip-phase', args.skip_phase])
    if args.dry_run:
        cmd.append('--dry-run')
    # 透传 rclone 覆盖参数
    cmd.extend(build_rclone_override_cmd_args(args))

    bg_log = os.path.join(log_dir, 'incr_background.log')
    pid_file = os.path.join(log_dir, 'incr_phase2.pid')

    log_f = open(bg_log, 'w', encoding='utf-8')
    log_f.write(f"# 增量迁移后台执行\n")
    log_f.write(f"# 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_f.write(f"# 命令: {' '.join(cmd)}\n\n")
    log_f.flush()

    process = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_f.close()

    with open(pid_file, 'w') as f:
        f.write(str(process.pid))

    print(f"增量迁移已在后台启动!")
    print(f"  PID:       {process.pid}")
    print(f"  PID 文件:  {pid_file}")
    print(f"  主日志:    {bg_log}")
    print(f"  输出目录:  {output_dir}")
    print()
    print(f"查看实时进度:  tail -f {bg_log}")
    print(f"检查进程状态:  ps -p {process.pid}")


# ---------------------------------------------------------------------------
# 汇总报告
# ---------------------------------------------------------------------------

def write_summary(output_dir: str, incr_dir: str,
                  ddl_results: Optional[List[tuple]],
                  rclone_results: Optional[List[tuple]],
                  dml_results: Optional[List[tuple]],
                  skip_phases: set):
    """写入汇总报告"""
    summary_path = os.path.join(output_dir, 'incr_summary.txt')

    lines = [
        "=" * 60,
        "增量迁移执行汇总",
        "=" * 60,
        f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"探查目录: {incr_dir}",
        f"输出目录: {output_dir}",
        "",
    ]

    # Phase 1 汇总
    if 1 in skip_phases:
        lines.append("Phase 1 (DDL): 已跳过")
    elif ddl_results is not None:
        s = sum(1 for r in ddl_results if r[2] == 'success')
        f = sum(1 for r in ddl_results if r[2] == 'failed')
        lines.append(f"Phase 1 (DDL): {s} 成功, {f} 失败 (共 {len(ddl_results)} 条)")
        if f > 0:
            lines.append("  失败明细:")
            for r in ddl_results:
                if r[2] == 'failed':
                    lines.append(f"    - {r[0]} ({r[1]}): {r[4][:120]}")

    lines.append("")

    # Phase 2 汇总
    if 2 in skip_phases:
        lines.append("Phase 2 (rclone): 已跳过")
    elif rclone_results is not None:
        s = sum(1 for r in rclone_results if r[3] == 'success')
        f = sum(1 for r in rclone_results if r[3] == 'failed')
        lines.append(f"Phase 2 (rclone): {s} 成功, {f} 失败 (共 {len(rclone_results)} 条)")
        if f > 0:
            lines.append("  失败明细:")
            for r in rclone_results:
                if r[3] == 'failed':
                    lines.append(f"    - {r[0]}.{r[1]}: {r[5][:120]}")

    lines.append("")

    # Phase 3 汇总
    if 3 in skip_phases:
        lines.append("Phase 3 (INSERT): 已跳过")
    elif dml_results is not None:
        s = sum(1 for r in dml_results if r[2] == 'success')
        f = sum(1 for r in dml_results if r[2] == 'failed')
        lines.append(f"Phase 3 (INSERT): {s} 成功, {f} 失败 (共 {len(dml_results)} 条)")
        if f > 0:
            lines.append("  失败明细:")
            for r in dml_results:
                if r[2] == 'failed':
                    lines.append(f"    - {r[0]} ({r[1]}): {r[4][:120]}")

    lines.extend(["", "=" * 60])

    content = '\n'.join(lines)

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(content + '\n')

    # 同时输出到控制台
    print(content)

    return summary_path


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='增量迁移执行: 执行 migration-lhm-inspect-hive-metastore 增量探查生成的 rclone 和 SQL 命令',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  # 执行增量迁移（指向增量探查输出目录）
  python incremental_migrate.py -i /path/to/incr_output/ -c config.ini

  # dry-run 预览
  python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --dry-run

  # 后台执行
  python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --background

  # 只执行 rclone（跳过 DDL 和 INSERT）
  python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --skip-phase 1,3

  # 只执行 SQL（DDL + INSERT，跳过 rclone）
  python incremental_migrate.py -i /path/to/incr_output/ -c config.ini --skip-phase 2
        '''
    )
    parser.add_argument('-i', '--incr-dir', required=True,
                        help='migration-lhm-inspect-hive-metastore 增量探查输出目录')
    parser.add_argument('-c', '--config', default='config.ini',
                        help='配置文件路径')
    parser.add_argument('-o', '--output-dir',
                        help='结果输出目录 (默认: <incr-dir>/migrate_result/)')
    parser.add_argument('--max-parallel', type=int,
                        help='rclone 最大并行数')
    parser.add_argument('--skip-phase',
                        help='跳过的阶段，逗号分隔 (如: 1,2 或 2)')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅打印，不执行')
    parser.add_argument('--background', action='store_true',
                        help='后台执行，脱离终端会话')
    add_rclone_override_args(parser)
    args = parser.parse_args()

    # ---- 验证输入 ----
    incr_dir = os.path.abspath(args.incr_dir)
    if not os.path.isdir(incr_dir):
        print(f"错误: 增量探查输出目录不存在: {incr_dir}")
        return 1

    sync_sh = os.path.join(incr_dir, 'sync_commands.sh')
    paimon_sql = os.path.join(incr_dir, 'paimon_sync.sql')
    delta_csv = os.path.join(incr_dir, 'metastore_delta.csv')
    schema_txt = os.path.join(incr_dir, 'schema_changes.txt')

    # 至少需要 sync_commands.sh 或 paimon_sync.sql 之一
    has_sh = os.path.exists(sync_sh)
    has_sql = os.path.exists(paimon_sql)
    if not has_sh and not has_sql:
        print(f"错误: 目录中找不到 sync_commands.sh 或 paimon_sync.sql: {incr_dir}")
        return 1

    # ---- 输出目录 ----
    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        output_dir = os.path.join(incr_dir, 'migrate_result')
    os.makedirs(output_dir, exist_ok=True)
    log_dir = os.path.join(output_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # ---- 跳过阶段 ----
    skip_phases = set()
    if args.skip_phase:
        skip_phases = set(int(s.strip()) for s in args.skip_phase.split(','))

    # ---- 后台模式 ----
    if args.background:
        _launch_background(args, output_dir)
        return 0

    # ---- 解析输入文件 ----
    config_cmds, copy_cmds = [], []
    if has_sh:
        config_cmds, copy_cmds = parse_sync_commands(sync_sh)

    ddl_stmts, dml_stmts = [], []
    if has_sql:
        ddl_stmts, dml_stmts = classify_sql_statements(paimon_sql)

    path_map = build_path_to_table_map(delta_csv) if os.path.exists(delta_csv) else {}

    # ---- 打印执行计划 ----
    print("=" * 60)
    print("增量迁移")
    print("=" * 60)
    print(f"探查目录: {incr_dir}")
    print(f"输出目录: {output_dir}")
    print(f"跳过阶段: {skip_phases or '无'}")
    print(f"Dry-run:  {args.dry_run}")
    print()
    print(f"Phase 1 (DDL):    {len(ddl_stmts)} 条{'  [跳过]' if 1 in skip_phases else ''}")
    print(f"Phase 2 (rclone): {len(copy_cmds)} 条命令"
          f" + {len(config_cmds)} 条配置{'  [跳过]' if 2 in skip_phases else ''}")
    print(f"Phase 3 (INSERT): {len(dml_stmts)} 条{'  [跳过]' if 3 in skip_phases else ''}")

    # schema_changes 警告
    if os.path.exists(schema_txt):
        with open(schema_txt, 'r', encoding='utf-8') as f:
            changes = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        if changes:
            print(f"\n!!! 警告: 发现 {len(changes)} 张表有结构变更 (TABLE_MODIFIED)，需手工处理:")
            for t in changes[:10]:
                print(f"    - {t}")
            if len(changes) > 10:
                print(f"    ... 共 {len(changes)} 张")
            print(f"    详见: {schema_txt}")

    print()

    # ---- dry-run 模式 ----
    if args.dry_run:
        print("=== DRY-RUN 模式 ===\n")

        if ddl_stmts and 1 not in skip_phases:
            print(f"Phase 1 - DDL ({len(ddl_stmts)} 条):")
            for sql in ddl_stmts[:5]:
                tbl = extract_table_name_from_sql(sql)
                print(f"  - CREATE TABLE {tbl}")
            if len(ddl_stmts) > 5:
                print(f"  ... 共 {len(ddl_stmts)} 条")
            print()

        if copy_cmds and 2 not in skip_phases:
            # 如果有覆盖参数，展示覆盖后的命令
            dry_config_cmds = config_cmds
            dry_copy_cmds = copy_cmds
            if has_rclone_overrides(args):
                try:
                    rclone_cfg = read_config(args.config, required_sections={
                        'rclone_source_hdfs': ['name', 'namenode', 'username'],
                        'rclone_target_s3': ['name', 'provider', 'endpoint',
                                             'access_key_id', 'secret_access_key', 'bucket'],
                        'rclone_options': ['copy_flags', 'bwlimit'],
                    })
                    apply_rclone_overrides(rclone_cfg, args)
                    dry_config_cmds = _generate_config_commands(rclone_cfg)
                    old_bucket = _extract_bucket_from_copy_cmd(copy_cmds, config_cmds)
                    dry_copy_cmds = _apply_copy_cmd_overrides(
                        copy_cmds, args, old_bucket, config_cmds)
                    print("[rclone 参数已覆盖]")
                except SystemExit:
                    pass

            print(f"Phase 2 - rclone config ({len(dry_config_cmds)} 条):")
            for cmd in dry_config_cmds:
                # 隐藏 AK/SK
                display = re.sub(r'(access_key_id\s+)\S+', r'\1***', cmd)
                display = re.sub(r'(secret_access_key\s+)\S+', r'\1***', display)
                print(f"  - {display[:120]}{'...' if len(display) > 120 else ''}")
            print()

            print(f"Phase 2 - rclone copy ({len(dry_copy_cmds)} 条命令):")
            for cmd in dry_copy_cmds[:5]:
                print(f"  - {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
            if len(dry_copy_cmds) > 5:
                print(f"  ... 共 {len(dry_copy_cmds)} 条")
            print()

        if dml_stmts and 3 not in skip_phases:
            print(f"Phase 3 - INSERT OVERWRITE ({len(dml_stmts)} 条):")
            for sql in dml_stmts[:5]:
                tbl = extract_table_name_from_sql(sql)
                print(f"  - INSERT OVERWRITE {tbl}")
            if len(dml_stmts) > 5:
                print(f"  ... 共 {len(dml_stmts)} 条")
            print()

        print("DRY-RUN 完成")
        return 0

    # ---- 实际执行 ----
    ddl_results = None
    rclone_results = None
    dml_results = None
    executor = None

    need_spark = (1 not in skip_phases and ddl_stmts) or \
                 (3 not in skip_phases and dml_stmts)

    try:
        # 连接 Spark（如果需要）
        if need_spark:
            config = read_config(args.config, required_sections={
                'spark_thrift': ['host', 'port', 'username', 'password']
            })
            executor = SparkThriftExecutor(config)

        # ========== Phase 1: DDL ==========
        if 1 not in skip_phases and ddl_stmts:
            phase1_log_path = os.path.join(log_dir, 'incr_phase1_execution.log')
            phase1_log_f = open(phase1_log_path, 'w', encoding='utf-8')
            try:
                phase1_log_f.write(f"Phase 1: DDL 执行日志\n")
                phase1_log_f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                phase1_log_f.write(f"DDL 语句数: {len(ddl_stmts)}\n")
                phase1_log_f.write(f"{'=' * 60}\n")
                phase1_log_f.flush()

                ddl_results = run_ddl_phase(executor, ddl_stmts,
                                            phase1_log_f, output_dir)

                phase1_log_f.write(f"\n{'=' * 60}\n")
                phase1_log_f.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            finally:
                phase1_log_f.close()

            # 写入 DDL 结果 CSV
            ddl_csv_path = os.path.join(output_dir, 'incr_ddl_result.csv')
            with open(ddl_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['table_name', 'ddl_type', 'status',
                                 'duration_seconds', 'error_msg'])
                for r in ddl_results:
                    writer.writerow(r)

            # Phase 1 阶段汇总
            s1 = sum(1 for r in ddl_results if r[2] == 'success')
            f1 = sum(1 for r in ddl_results if r[2] == 'failed')
            print(f"\nPhase 1 汇总: {s1} 成功, {f1} 失败 (共 {len(ddl_results)} 条)")
            if f1 > 0:
                for r in ddl_results:
                    if r[2] == 'failed':
                        print(f"  - {r[0]}: {r[4][:100]}")

        # ========== Phase 2: rclone ==========
        if 2 not in skip_phases and copy_cmds and not ensure_rclone_installed():
            print("错误: rclone 未安装且自动安装失败，跳过 Phase 2")
            copy_cmds = []

        if 2 not in skip_phases and copy_cmds:
            max_parallel = args.max_parallel or 4
            # 尝试从 config.ini 读取 max_parallel
            if not args.max_parallel:
                try:
                    rclone_cfg = read_config(args.config, required_sections={
                        'rclone_options': ['copy_flags'],
                    })
                    max_parallel = rclone_cfg.getint(
                        'rclone_options', 'max_parallel', fallback=4)
                except SystemExit:
                    pass  # config.ini 中没有 rclone_options 也没关系

            # 如果有 rclone 覆盖参数，重新生成 config 命令并修改 copy 命令
            effective_config_cmds = config_cmds
            effective_copy_cmds = copy_cmds
            if has_rclone_overrides(args):
                try:
                    rclone_cfg = read_config(args.config, required_sections={
                        'rclone_source_hdfs': ['name', 'namenode', 'username'],
                        'rclone_target_s3': ['name', 'provider', 'endpoint',
                                             'access_key_id', 'secret_access_key', 'bucket'],
                        'rclone_options': ['copy_flags', 'bwlimit'],
                    })
                    apply_rclone_overrides(rclone_cfg, args)
                    effective_config_cmds = _generate_config_commands(rclone_cfg)
                    old_bucket = _extract_bucket_from_copy_cmd(copy_cmds, config_cmds)
                    effective_copy_cmds = _apply_copy_cmd_overrides(
                        copy_cmds, args, old_bucket, config_cmds)
                    print("已应用 rclone 参数覆盖")
                except SystemExit:
                    print("警告: 读取 config.ini rclone 配置失败，使用 sync_commands.sh 原始命令")

            phase2_log_path = os.path.join(log_dir, 'incr_phase2_master.log')
            phase2_log_f = open(phase2_log_path, 'w', encoding='utf-8')
            try:
                phase2_log_f.write(f"Phase 2: rclone 同步主日志\n")
                phase2_log_f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                phase2_log_f.write(f"命令数: {len(effective_copy_cmds)}, 并行数: {max_parallel}\n")
                phase2_log_f.write(f"{'=' * 60}\n\n")
                phase2_log_f.flush()

                rclone_results = run_rclone_phase(
                    effective_config_cmds, effective_copy_cmds, path_map,
                    log_dir, output_dir, max_parallel, phase2_log_f
                )

                phase2_log_f.write(f"\n{'=' * 60}\n")
                phase2_log_f.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            finally:
                phase2_log_f.close()

            # Phase 2 阶段汇总
            s2 = sum(1 for r in rclone_results if r[3] == 'success')
            f2 = sum(1 for r in rclone_results if r[3] == 'failed')
            print(f"\nPhase 2 汇总: {s2} 成功, {f2} 失败 (共 {len(rclone_results)} 条)")
            if f2 > 0:
                for r in rclone_results:
                    if r[3] == 'failed':
                        print(f"  - {r[0]}.{r[1]}: {r[5][:100]}")

        # ========== Phase 3: DML ==========
        if 3 not in skip_phases and dml_stmts:
            # 验证 Spark 连接（可能因 Phase 2 耗时太长而断开）
            if executor:
                try:
                    executor.execute_sql("SELECT 1")
                except Exception:
                    print("Spark 连接已断开，正在重连...")
                    try:
                        executor.close()
                    except Exception:
                        pass
                    config = read_config(args.config, required_sections={
                        'spark_thrift': ['host', 'port', 'username', 'password']
                    })
                    executor = SparkThriftExecutor(config)

            phase3_log_path = os.path.join(log_dir, 'incr_phase3_execution.log')
            phase3_log_f = open(phase3_log_path, 'w', encoding='utf-8')
            try:
                phase3_log_f.write(f"Phase 3: INSERT OVERWRITE 执行日志\n")
                phase3_log_f.write(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                phase3_log_f.write(f"DML 语句数: {len(dml_stmts)}\n")
                phase3_log_f.write(f"{'=' * 60}\n")
                phase3_log_f.flush()

                dml_results = run_dml_phase(executor, dml_stmts,
                                            phase3_log_f, output_dir)

                phase3_log_f.write(f"\n{'=' * 60}\n")
                phase3_log_f.write(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            finally:
                phase3_log_f.close()

            # 写入 DML 结果 CSV
            dml_csv_path = os.path.join(output_dir, 'incr_insert_result.csv')
            with open(dml_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['table_name', 'sql_type', 'status',
                                 'duration_seconds', 'error_msg'])
                for r in dml_results:
                    writer.writerow(r)

            # Phase 3 阶段汇总
            s3 = sum(1 for r in dml_results if r[2] == 'success')
            f3 = sum(1 for r in dml_results if r[2] == 'failed')
            print(f"\nPhase 3 汇总: {s3} 成功, {f3} 失败 (共 {len(dml_results)} 条)")
            if f3 > 0:
                for r in dml_results:
                    if r[2] == 'failed':
                        print(f"  - {r[0]}: {r[4][:100]}")

    finally:
        if executor:
            try:
                executor.close()
            except Exception:
                pass

    # ---- 写入汇总报告 ----
    write_summary(output_dir, incr_dir,
                  ddl_results, rclone_results, dml_results, skip_phases)

    # 判断总体是否有失败
    has_failure = False
    if ddl_results:
        has_failure = has_failure or any(r[2] == 'failed' for r in ddl_results)
    if rclone_results:
        has_failure = has_failure or any(r[3] == 'failed' for r in rclone_results)
    if dml_results:
        has_failure = has_failure or any(r[2] == 'failed' for r in dml_results)

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
