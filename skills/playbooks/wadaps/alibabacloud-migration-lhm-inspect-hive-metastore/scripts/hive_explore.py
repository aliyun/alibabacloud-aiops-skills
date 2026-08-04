#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hive 数据探查统一入口

整合全量探查、增量探查、连接测试和对比模式，提供：
- CLI 参数 + 交互式配置补全
- 连接预检
- 备用主机回退
- 自动重试
- 配置 Profile 管理
"""

import argparse
import configparser
import csv
import os
import sys
from datetime import datetime

# 将脚本所在目录加入 sys.path 以便导入同目录模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from connection_utils import (
    test_port, classify_error, retry_with_backoff,
    get_db_connection_robust, try_hosts_with_fallback,
    print_connection_report, ConnectionTestResult, ErrorInfo,
)
from config_manager import (
    load_profile, save_profile, list_profiles,
    merge_cli_args_into_config, interactive_fill,
    determine_required_sections, config_to_dict,
    expand_env_vars,
)

# 退出码
EXIT_OK = 0
EXIT_CONNECTION = 1
EXIT_CONFIG = 2
EXIT_MISSING_DEP = 3
EXIT_INVALID_ARGS = 4


# ──────────────────────────────────────────────
# CLI 参数解析
# ──────────────────────────────────────────────

def build_parser():
    parent = argparse.ArgumentParser(add_help=False)

    # 全局参数
    parent.add_argument("-c", "--config", default=None,
                        help="配置文件路径 (默认: config.ini)")
    parent.add_argument("--profile", default=None,
                        help="加载已保存的 profile")
    parent.add_argument("--save-profile", default=None, dest="save_profile",
                        help="保存当前配置为 profile")
    parent.add_argument("--mode", choices=["db", "thrift", "both"], default=None,
                        help="连接模式 (默认: thrift)")
    parent.add_argument("--host", default=None,
                        help="主机地址 (DB 和 Thrift 共用)")
    parent.add_argument("--thrift-host", default=None, dest="thrift_host",
                        help="Thrift 专用主机 (覆盖 --host)")
    parent.add_argument("--port", default=None,
                        help="DB 端口 (默认: 3306)")
    parent.add_argument("--thrift-port", default=None, dest="thrift_port",
                        help="Thrift 端口 (默认: 9083)")
    parent.add_argument("--user", default=None,
                        help="DB 用户名")
    parent.add_argument("--password", default=None,
                        help="DB 密码")
    parent.add_argument("--database", default=None,
                        help="Metastore 数据库名 (留空自动检测)")
    parent.add_argument("--db-type", choices=["mysql", "postgres"], default=None,
                        dest="db_type", help="DB 类型")
    parent.add_argument("--auth", choices=["NOSASL", "KERBEROS"], default=None,
                        help="Thrift 认证方式")
    parent.add_argument("--fallback-host", default=None, dest="fallback_host",
                        help="备用主机")
    parent.add_argument("--no-interactive", action="store_true", dest="no_interactive",
                        help="禁用交互式提示")
    parent.add_argument("-v", "--verbose", action="store_true",
                        help="详细输出")

    # 主解析器
    main_parser = argparse.ArgumentParser(
        prog="hive_explore.py",
        description="Hive 数据探查统一入口 — 全量/增量/测试/对比",
    )
    subparsers = main_parser.add_subparsers(dest="command", help="子命令")

    # full 子命令
    p_full = subparsers.add_parser("full", parents=[parent],
                                   help="全量探查")
    p_full.add_argument("databases", nargs="*",
                        help="要探查的数据库列表 (不指定则全部)")
    p_full.add_argument("--size-source", choices=["params", "hadoop", "skip"],
                        default=None, dest="size_source",
                        help="表大小获取方式 (默认: params)")
    p_full.add_argument("-o", "--output-dir", default=None, dest="output_dir",
                        help="输出目录")

    # incr 子命令
    p_incr = subparsers.add_parser("incr", parents=[parent],
                                   help="增量探查")
    p_incr.add_argument("-s", "--start-time", required=True, dest="start_time",
                        help="开始时间 YYYY-MM-DD HH:MM:SS")
    p_incr.add_argument("-o", "--output", default="metastore_delta.csv",
                        help="输出 CSV 路径")
    p_incr.add_argument("--databases", nargs="*", default=None,
                        help="限制扫描的数据库列表")

    # test 子命令
    p_test = subparsers.add_parser("test", parents=[parent],
                                   help="连接测试")

    # compare 子命令
    p_compare = subparsers.add_parser("compare", parents=[parent],
                                      help="对比模式 (同时运行 DB + Thrift)")
    p_compare.add_argument("-s", "--start-time", required=True, dest="start_time",
                           help="开始时间 YYYY-MM-DD HH:MM:SS")
    p_compare.add_argument("-o", "--output", default="compare_report.md",
                           help="对比报告路径")
    p_compare.add_argument("--databases", nargs="*", default=None,
                           help="限制扫描的数据库列表")

    return main_parser


# ──────────────────────────────────────────────
# 连接预检
# ──────────────────────────────────────────────

def precheck_connections(config, required_sections, verbose=False):
    """
    对所需的连接端口做预检，返回 (results, all_ok)。
    """
    results = []

    if 'metastore_db' in required_sections:
        db_conf = config_to_dict(config, 'metastore_db')
        host = db_conf.get('host', '')
        port = int(db_conf.get('port', 3306))
        if host:
            r = test_port(host, port)
            err_info = None if r.reachable else ErrorInfo('network_timeout', '端口不可达', '检查主机和端口')
            results.append(ConnectionTestResult('DB', host, port, r.reachable, r.latency_ms, err_info))

        fallback = config.get('general', 'fallback_host', fallback='')
        if fallback:
            r = test_port(fallback, port)
            err_info = None if r.reachable else ErrorInfo('network_timeout', '备用端口不可达', '检查备用主机')
            results.append(ConnectionTestResult('DB(备用)', fallback, port, r.reachable, r.latency_ms, err_info))

    if 'thrift' in required_sections:
        th_conf = config_to_dict(config, 'thrift')
        host = th_conf.get('host', '')
        port = int(th_conf.get('port', 9083))
        if host:
            r = test_port(host, port)
            err_info = None if r.reachable else ErrorInfo('network_timeout', '端口不可达', '检查 HMS 服务')
            results.append(ConnectionTestResult('Thrift', host, port, r.reachable, r.latency_ms, err_info))

        fallback = config.get('general', 'fallback_host', fallback='')
        if fallback:
            r = test_port(fallback, port)
            err_info = None if r.reachable else ErrorInfo('network_timeout', '备用端口不可达', '检查备用主机')
            results.append(ConnectionTestResult('Thrift(备用)', fallback, port, r.reachable, r.latency_ms, err_info))

    all_ok = all(r.reachable for r in results) if results else True
    return results, all_ok


def maybe_fallback_to_thrift(config, args, verbose=False):
    """
    DB 模式下连接失败时，检测 Thrift 是否可用并提示切换。

    返回:
        实际使用的 mode 字符串 ('db' 或 'thrift')
    """
    mode = config.get('general', 'connection_mode', fallback='thrift')
    if mode != 'db':
        return mode

    # 检查 Thrift 配置是否存在
    th_conf = config_to_dict(config, 'thrift')
    th_host = th_conf.get('host', '')
    if not th_host:
        return mode

    th_port = int(th_conf.get('port', 9083))
    r = test_port(th_host, th_port)
    if not r.reachable:
        return mode

    # Thrift 可达，提示用户
    is_tty = sys.stdin.isatty() and not getattr(args, 'no_interactive', False)
    if is_tty:
        answer = input(f"\n  DB 连接不可达，但 Thrift ({th_host}:{th_port}) 可用。切换到 Thrift 模式? [Y/n]: ").strip()
        if answer.lower() in ('', 'y', 'yes'):
            config.set('general', 'connection_mode', 'thrift')
            print("  已切换到 Thrift 模式")
            return 'thrift'
    else:
        if verbose:
            print(f"  提示: Thrift ({th_host}:{th_port}) 可达，可通过 --mode thrift 切换")

    return mode


# ──────────────────────────────────────────────
# 子命令实现
# ──────────────────────────────────────────────

def cmd_test(config, args):
    """连接测试子命令"""
    print("\n=== 连接测试 ===\n")

    # 测试所有可能的连接
    sections = []
    if config.has_section('metastore_db') and config_to_dict(config, 'metastore_db').get('host'):
        sections.append('metastore_db')
    if config.has_section('thrift') and config_to_dict(config, 'thrift').get('host'):
        sections.append('thrift')

    if not sections:
        print("  未配置任何连接信息。请通过 --host 或配置文件提供。")
        return EXIT_CONFIG

    results, all_ok = precheck_connections(config, sections, verbose=args.verbose)
    print_connection_report(results)

    # 额外：尝试实际连接
    print("\n  实际连接测试:")

    if 'metastore_db' in sections:
        db_conf = config_to_dict(config, 'metastore_db')
        if db_conf.get('user'):
            try:
                conn, db_type = get_db_connection_robust(db_conf)
                conn.close()
                print(f"    [DB] 连接成功 (类型: {db_type})")
            except Exception as e:
                err = classify_error(e)
                print(f"    [DB] 连接失败: {err.message_zh} -> {err.suggestion_zh}")

    if 'thrift' in sections:
        th_conf = config_to_dict(config, 'thrift')
        try:
            from thrift_client import ThriftHMSConnection
            with ThriftHMSConnection(th_conf) as client:
                dbs = client.get_all_databases()
                print(f"    [Thrift] 连接成功 (发现 {len(dbs)} 个数据库)")
        except ImportError as e:
            err = classify_error(e)
            print(f"    [Thrift] {err.message_zh} -> {err.suggestion_zh}")
        except Exception as e:
            err = classify_error(e)
            print(f"    [Thrift] 连接失败: {err.message_zh} -> {err.suggestion_zh}")

    print()
    return EXIT_OK


def cmd_full(config, args):
    """全量探查子命令"""
    mode = config.get('general', 'connection_mode', fallback='thrift')

    if mode == 'db':
        print("\n提示: DB 直连全量探查需要使用 hive_dive.sh（依赖 hadoop/hive CLI）。")
        print("请在 Hive 集群节点上执行: bash hive_dive.sh [databases...]")
        print("或切换到 Thrift 模式: --mode thrift")
        return EXIT_INVALID_ARGS

    # Thrift 全量探查
    print("\n=== 全量探查 (Thrift 模式) ===\n")

    th_conf = config_to_dict(config, 'thrift')
    size_source = args.size_source or th_conf.get('size_source', 'params')
    target_dbs = args.databases if args.databases else None

    try:
        from hive_dive_thrift import run_full_exploration
        run_full_exploration(th_conf, target_dbs, size_source, args.output_dir)
        return EXIT_OK
    except ImportError as e:
        err = classify_error(e)
        print(f"错误: {err.message_zh}")
        print(f"建议: {err.suggestion_zh}")
        return EXIT_MISSING_DEP
    except Exception as e:
        err = classify_error(e)
        print(f"\n探查失败: {err.message_zh}")
        print(f"建议: {err.suggestion_zh}")
        return EXIT_CONNECTION if err.category.startswith('network_') else EXIT_OK


def _run_incr_db(config, start_ts, output, target_dbs):
    """通过 DB 直连运行增量探查，返回 records 列表"""
    from get_metastore_changes import get_changes as db_get_changes
    db_conf = config_to_dict(config, 'metastore_db')

    # 使用增强连接
    conn, db_type = get_db_connection_robust(db_conf)
    try:
        records = db_get_changes(conn, db_type, start_ts)
    finally:
        conn.close()

    # 如果有 target_dbs 过滤
    if target_dbs:
        target_set = set(target_dbs)
        records = [r for r in records if r['db_name'] in target_set]

    return records


def _run_incr_thrift(config, start_ts, target_dbs):
    """通过 Thrift 运行增量探查，返回 records 列表"""
    from get_metastore_changes_thrift import get_changes as thrift_get_changes
    from thrift_client import ThriftHMSConnection

    th_conf = config_to_dict(config, 'thrift')
    with ThriftHMSConnection(th_conf) as client:
        records = thrift_get_changes(client, start_ts, target_dbs=target_dbs)

    return records


def _write_incr_csv(records, output):
    """将增量记录写入 CSV 文件"""
    from get_metastore_changes_thrift import clean_partition_name

    if not records:
        print("指定时间内无变更。")
        return

    records.sort(key=lambda x: x['change_unix_ts'])
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['type', 'db_name', 'table_name', 'is_partitioned',
                         'partition_keys', 'partition_values', 'location', 'change_time'])
        for r in records:
            change_time = datetime.fromtimestamp(
                int(r['change_unix_ts'])
            ).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([
                r['type'],
                r['db_name'],
                r['table_name'],
                r['is_partitioned'],
                r.get('partition_keys') or '',
                clean_partition_name(r.get('partition_name')),
                r.get('location') or '',
                change_time,
            ])
    print(f"成功导出 {len(records)} 条变更记录至 {output}")


def cmd_incr(config, args):
    """增量探查子命令"""
    mode = config.get('general', 'connection_mode', fallback='thrift')

    try:
        start_ts = int(datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S').timestamp())
    except ValueError:
        print(f"错误: 时间格式不正确，要求 YYYY-MM-DD HH:MM:SS，实际: {args.start_time}")
        return EXIT_INVALID_ARGS

    print(f"\n=== 增量探查 ({mode} 模式) ===")
    print(f"查询起始时间: {args.start_time} (Unix: {start_ts})\n")

    try:
        if mode == 'thrift':
            records = _run_incr_thrift(config, start_ts, args.databases)
        elif mode == 'db':
            records = _run_incr_db(config, start_ts, args.output, args.databases)
        else:
            print(f"错误: 增量探查不支持 mode='{mode}'，请用 'db' 或 'thrift'")
            return EXIT_INVALID_ARGS

        _write_incr_csv(records, args.output)
        return EXIT_OK

    except ImportError as e:
        err = classify_error(e)
        print(f"错误: {err.message_zh}")
        print(f"建议: {err.suggestion_zh}")
        return EXIT_MISSING_DEP
    except ConnectionError as e:
        # 尝试回退
        fallback_mode = maybe_fallback_to_thrift(config, args, verbose=args.verbose)
        if fallback_mode != mode:
            print(f"\n  回退到 {fallback_mode} 模式重试...\n")
            try:
                if fallback_mode == 'thrift':
                    records = _run_incr_thrift(config, start_ts, args.databases)
                else:
                    records = _run_incr_db(config, start_ts, args.output, args.databases)
                _write_incr_csv(records, args.output)
                return EXIT_OK
            except Exception as e2:
                err = classify_error(e2)
                print(f"\n回退也失败: {err.message_zh}")
                print(f"建议: {err.suggestion_zh}")
                return EXIT_CONNECTION
        err = classify_error(e)
        print(f"\n连接失败: {err.message_zh}")
        print(f"建议: {err.suggestion_zh}")
        return EXIT_CONNECTION
    except Exception as e:
        err = classify_error(e)
        print(f"\n探查失败: {err.message_zh}")
        print(f"建议: {err.suggestion_zh}")
        return EXIT_CONNECTION if err.category.startswith('network_') else EXIT_OK


def cmd_compare(config, args):
    """对比模式子命令"""
    try:
        start_ts = int(datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S').timestamp())
    except ValueError:
        print(f"错误: 时间格式不正确，要求 YYYY-MM-DD HH:MM:SS，实际: {args.start_time}")
        return EXIT_INVALID_ARGS

    print(f"\n=== 对比模式 (DB + Thrift) ===")
    print(f"查询起始时间: {args.start_time} (Unix: {start_ts})\n")

    db_records = None
    thrift_records = None
    db_error = None
    thrift_error = None

    # 运行 DB 增量
    print("--- DB 直连增量探查 ---")
    try:
        db_records = _run_incr_db(config, start_ts, None, args.databases)
        print(f"  DB 检测到 {len(db_records)} 条变更\n")
    except Exception as e:
        db_error = classify_error(e)
        print(f"  DB 探查失败: {db_error.message_zh}\n")

    # 运行 Thrift 增量
    print("--- Thrift 增量探查 ---")
    try:
        thrift_records = _run_incr_thrift(config, start_ts, args.databases)
        print(f"  Thrift 检测到 {len(thrift_records)} 条变更\n")
    except Exception as e:
        thrift_error = classify_error(e)
        print(f"  Thrift 探查失败: {thrift_error.message_zh}\n")

    # 生成对比报告
    report = _generate_compare_report(
        db_records, thrift_records, db_error, thrift_error, args.start_time
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"对比报告已保存至: {args.output}")

    # 同时输出各自的 CSV
    if db_records:
        _write_incr_csv(db_records, "compare_db_delta.csv")
    if thrift_records:
        _write_incr_csv(thrift_records, "compare_thrift_delta.csv")

    return EXIT_OK


def _record_key(r):
    """生成记录去重 key"""
    return (
        r.get('type', ''),
        r.get('db_name', ''),
        r.get('table_name', ''),
        r.get('partition_name') or '',
    )


def _generate_compare_report(db_records, thrift_records, db_error, thrift_error, start_time):
    """生成 Markdown 格式的对比报告"""
    lines = []
    lines.append(f"# Hive 增量探查对比报告")
    lines.append(f"")
    lines.append(f"起始时间: {start_time}")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")

    # 总数对比
    lines.append(f"## 总览")
    lines.append(f"")
    lines.append(f"| 方式 | 状态 | 变更数 |")
    lines.append(f"|------|------|--------|")

    if db_error:
        lines.append(f"| DB 直连 | 失败: {db_error.message_zh} | - |")
    elif db_records is not None:
        lines.append(f"| DB 直连 | 成功 | {len(db_records)} |")
    else:
        lines.append(f"| DB 直连 | 未运行 | - |")

    if thrift_error:
        lines.append(f"| Thrift | 失败: {thrift_error.message_zh} | - |")
    elif thrift_records is not None:
        lines.append(f"| Thrift | 成功 | {len(thrift_records)} |")
    else:
        lines.append(f"| Thrift | 未运行 | - |")

    lines.append(f"")

    # 仅当两者都成功时做差异分析
    if db_records is not None and thrift_records is not None:
        db_keys = {_record_key(r) for r in db_records}
        thrift_keys = {_record_key(r) for r in thrift_records}

        both = db_keys & thrift_keys
        only_db = db_keys - thrift_keys
        only_thrift = thrift_keys - db_keys

        lines.append(f"## 差异分析")
        lines.append(f"")
        lines.append(f"- 两者一致: {len(both)} 条")
        lines.append(f"- 仅 DB 检测到: {len(only_db)} 条")
        lines.append(f"- 仅 Thrift 检测到: {len(only_thrift)} 条")
        lines.append(f"")

        if only_db:
            lines.append(f"### 仅 DB 检测到")
            lines.append(f"")
            lines.append(f"| type | db_name | table_name | partition |")
            lines.append(f"|------|---------|------------|-----------|")
            for key in sorted(only_db):
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} |")
            lines.append(f"")

        if only_thrift:
            lines.append(f"### 仅 Thrift 检测到")
            lines.append(f"")
            lines.append(f"| type | db_name | table_name | partition |")
            lines.append(f"|------|---------|------------|-----------|")
            for key in sorted(only_thrift):
                lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {key[3]} |")
            lines.append(f"")

        if not only_db and not only_thrift:
            lines.append(f"两种方式检测结果完全一致。")
            lines.append(f"")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return EXIT_INVALID_ARGS

    # ── 1. 加载配置 ──
    config = configparser.ConfigParser()

    # 确保基础 section 存在
    for section in ('general', 'thrift', 'metastore_db'):
        if not config.has_section(section):
            config.add_section(section)

    if args.profile:
        try:
            config = load_profile(args.profile)
            print(f"已加载 profile: {args.profile}")
        except FileNotFoundError as e:
            print(f"错误: {e}")
            return EXIT_CONFIG
    elif args.config:
        if os.path.exists(args.config):
            config.read(args.config, encoding='utf-8')
        else:
            print(f"警告: 配置文件不存在: {args.config}")
    else:
        # 默认尝试 config.ini
        default_config = os.path.join(SCRIPT_DIR, 'config.ini')
        if os.path.exists(default_config):
            config.read(default_config, encoding='utf-8')

    # ── 2. CLI 参数覆盖 ──
    config = merge_cli_args_into_config(args, config)

    # ── 2.5 环境变量插值（支持 config.ini 中使用 ${ENV_VAR}）──
    expand_env_vars(config)

    # ── 3. 确定连接模式和所需配置段 ──
    mode = config.get('general', 'connection_mode', fallback='thrift')
    required = determine_required_sections(mode, args.command)

    # ── 4. 交互式补全缺失配置 ──
    try:
        interactive_fill(config, required, no_interactive=getattr(args, 'no_interactive', False))
    except ValueError as e:
        print(f"\n配置错误: {e}")
        return EXIT_CONFIG

    # ── 5. 连接预检 ──
    if args.command != 'test':
        results, all_ok = precheck_connections(config, required, verbose=args.verbose)
        if results:
            print_connection_report(results)
        if not all_ok:
            # DB 模式下尝试回退到 Thrift
            actual_mode = maybe_fallback_to_thrift(config, args, verbose=args.verbose)
            if actual_mode == mode and not all_ok:
                # 依然不行，但继续尝试（实际连接可能通过备用主机）
                any_reachable = any(r.reachable for r in results)
                if not any_reachable:
                    print("\n所有连接端口均不可达。")
                    failed = [r for r in results if not r.reachable and r.error_info]
                    for r in failed:
                        print(f"  [{r.method}] {r.error_info.suggestion_zh}")
                    return EXIT_CONNECTION

    # ── 6. 执行子命令 ──
    cmd_map = {
        'test': cmd_test,
        'full': cmd_full,
        'incr': cmd_incr,
        'compare': cmd_compare,
    }
    exit_code = cmd_map[args.command](config, args)

    # ── 7. 保存 profile ──
    if exit_code == EXIT_OK:
        if getattr(args, 'save_profile', None):
            save_profile(args.save_profile, config)
        # 自动保存 _last
        try:
            save_profile('_last', config)
        except Exception:
            pass  # _last 保存失败不影响主流程

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
