#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
连接工具库

提供端口连通性测试、错误分类、数据库名自动检测、备用主机回退、重试机制等通用能力。
"""

import socket
import time
from collections import namedtuple

PortTestResult = namedtuple('PortTestResult', ['reachable', 'latency_ms', 'error'])
ErrorInfo = namedtuple('ErrorInfo', ['category', 'message_zh', 'suggestion_zh'])
ConnectionTestResult = namedtuple('ConnectionTestResult', ['method', 'host', 'port', 'reachable', 'latency_ms', 'error_info'])


def test_port(host, port, timeout=5):
    """
    快速检测端口连通性。

    返回:
        PortTestResult(reachable, latency_ms, error)
    """
    try:
        start = time.monotonic()
        sock = socket.create_connection((host, int(port)), timeout=timeout)
        latency = (time.monotonic() - start) * 1000
        sock.close()
        return PortTestResult(reachable=True, latency_ms=round(latency, 1), error=None)
    except socket.gaierror as e:
        return PortTestResult(reachable=False, latency_ms=0, error=f"dns_resolution_failed: {e}")
    except socket.timeout:
        return PortTestResult(reachable=False, latency_ms=0, error="timeout")
    except ConnectionRefusedError:
        return PortTestResult(reachable=False, latency_ms=0, error="refused")
    except OSError as e:
        return PortTestResult(reachable=False, latency_ms=0, error=str(e))


def classify_error(exception):
    """
    将异常分类为友好的错误信息。

    返回:
        ErrorInfo(category, message_zh, suggestion_zh)
    """
    exc_type = type(exception).__name__
    exc_module = type(exception).__module__ or ''
    exc_str = str(exception).lower()

    # DNS 解析失败
    if isinstance(exception, socket.gaierror) or 'gaierror' in exc_type.lower():
        return ErrorInfo('network_dns', 'DNS 解析失败', '检查主机名拼写，确认 DNS 可用')

    # 连接超时
    if isinstance(exception, socket.timeout) or 'timeout' in exc_str:
        return ErrorInfo('network_timeout', '连接超时', '确认主机/端口正确，检查防火墙规则')

    # 连接被拒绝
    if isinstance(exception, ConnectionRefusedError) or 'refused' in exc_str:
        return ErrorInfo('network_refused', '连接被拒绝', '服务可能未启动，或端口不正确')

    # MySQL/PostgreSQL 认证失败
    if '1045' in exc_str or 'access denied' in exc_str:
        return ErrorInfo('auth_denied', '认证失败', '检查用户名和密码是否正确')

    # 数据库不存在
    if '1049' in exc_str or 'unknown database' in exc_str or 'does not exist' in exc_str:
        return ErrorInfo('db_not_found', '数据库不存在', '检查数据库名，或留空使用自动检测')

    # Kerberos 相关
    if 'gssapi' in exc_str or 'kinit' in exc_str or 'kerberos' in exc_str:
        return ErrorInfo('auth_kerberos', 'Kerberos 票据无效', "请先执行 'kinit' 获取票据")

    # Thrift 传输层错误
    if 'ttransportexception' in exc_type.lower() or 'thrift' in exc_module.lower():
        return ErrorInfo('network_transport', 'Thrift 传输层错误', 'HMS Thrift 服务可能未运行')

    # 缺少依赖
    if isinstance(exception, ImportError):
        module_name = str(exception).replace('No module named ', '').strip("'\"")
        install_hint = {
            'pymysql': 'pip install PyMySQL',
            'psycopg2': 'pip install psycopg2-binary',
            'hmsclient': 'pip install hmsclient',
            'thrift_sasl': 'pip install thrift_sasl gssapi',
            'thrift': 'pip install thrift',
        }
        suggestion = install_hint.get(module_name, f'pip install {module_name}')
        return ErrorInfo('missing_dep', f'缺少依赖: {module_name}', suggestion)

    # 未知错误
    return ErrorInfo('unknown', f'未知错误: {exc_type}', str(exception))


def retry_with_backoff(fn, max_retries=3, base_delay=1):
    """
    带指数退避的重试机制。

    仅重试 network 类错误，auth/config 类错误立即抛出。
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_error = e
            error_info = classify_error(e)
            # 非 network 类错误不重试
            if not error_info.category.startswith('network_'):
                raise
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"  连接失败 (尝试 {attempt + 1}/{max_retries})，{delay}s 后重试... "
                      f"错误: {error_info.message_zh}")
                time.sleep(delay)
    raise last_error


def auto_detect_database(host, port, user, password, db_type='mysql'):
    """
    自动检测 Hive Metastore 数据库名。

    依次尝试常见名称，通过查询 TBLS 表确认是 Metastore 库。

    返回:
        str: 检测到的数据库名，或 None
    """
    candidates = ['hive', 'hivemeta', 'metastore', 'hive_metastore', 'hivemetastore']

    for name in candidates:
        try:
            if db_type == 'mysql':
                import pymysql
                conn = pymysql.connect(
                    host=host, port=int(port), user=user, password=password,
                    database=name, connect_timeout=5
                )
            elif db_type == 'postgres':
                import psycopg2
                conn = psycopg2.connect(
                    host=host, port=int(port), user=user, password=password,
                    dbname=name, connect_timeout=5
                )
            else:
                return None

            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM TBLS LIMIT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                print(f"  自动检测到 Metastore 数据库: '{name}'")
                return name
            except Exception:
                conn.close()
                continue
        except Exception as e:
            exc_str = str(e).lower()
            # 数据库不存在，继续尝试下一个
            if '1049' in exc_str or 'unknown database' in exc_str or 'does not exist' in exc_str:
                continue
            # 认证失败等其他错误，停止尝试
            if '1045' in exc_str or 'access denied' in exc_str:
                return None
            continue

    return None


def try_hosts_with_fallback(hosts, port, connect_fn):
    """
    依次尝试多个主机，返回首个成功的连接。

    参数:
        hosts: 主机列表，如 ["internal.domain", "1.2.3.4"]
        port: 端口号
        connect_fn: 接受 host 参数的连接函数，返回连接对象

    返回:
        (result, used_host) 元组
    """
    errors = []
    for host in hosts:
        if not host:
            continue
        port_result = test_port(host, port)
        if not port_result.reachable:
            errors.append((host, port_result.error))
            print(f"  主机 {host}:{port} 不可达 ({port_result.error})，尝试下一个...")
            continue
        try:
            result = connect_fn(host)
            return result, host
        except Exception as e:
            errors.append((host, str(e)))
            print(f"  主机 {host} 连接失败: {classify_error(e).message_zh}，尝试下一个...")
            continue

    error_details = '; '.join([f"{h}: {e}" for h, e in errors])
    raise ConnectionError(f"所有主机均不可达: {error_details}")


def get_db_connection_robust(config_dict):
    """
    增强版数据库连接，整合自动检测、备用主机回退和重试。

    参数:
        config_dict: 包含 host, port, user, password, database, db_type 等键的字典
                     可选 fallback_host 键

    返回:
        (connection, db_type) 元组

    异常:
        连接失败时抛出异常（不调用 sys.exit）
    """
    db_type = config_dict.get('db_type', 'mysql').lower()
    port = int(config_dict.get('port', 3306 if db_type == 'mysql' else 5432))
    user = config_dict.get('user', '')
    password = config_dict.get('password', '')
    database = config_dict.get('database', '')

    # 构建主机列表
    hosts = [config_dict.get('host', '')]
    fallback = config_dict.get('fallback_host', '')
    if fallback:
        hosts.append(fallback)

    # 自动检测数据库名
    placeholder_markers = ('$', 'your_', '')
    need_detect = not database or any(database.startswith(m) for m in placeholder_markers if m)

    def connect_to_host(host):
        nonlocal database

        if need_detect:
            detected = auto_detect_database(host, port, user, password, db_type)
            if detected:
                database = detected
            else:
                raise ConnectionError("无法自动检测数据库名，请通过 --database 指定")

        def do_connect():
            if db_type == 'mysql':
                import pymysql
                return pymysql.connect(
                    host=host, port=port, user=user, password=password,
                    database=database, cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=10
                )
            elif db_type == 'postgres':
                import psycopg2
                return psycopg2.connect(
                    host=host, port=port, user=user, password=password,
                    dbname=database, connect_timeout=10
                )
            else:
                raise ValueError(f"不支持的数据库类型: {db_type}")

        conn = retry_with_backoff(do_connect)
        return conn

    conn, used_host = try_hosts_with_fallback(hosts, port, connect_to_host)
    if used_host != hosts[0]:
        print(f"  使用备用主机: {used_host}")
    return conn, db_type


def print_connection_report(results):
    """
    格式化输出连接测试报告。

    参数:
        results: ConnectionTestResult 列表
    """
    if not results:
        print("  无测试结果")
        return

    # 表头
    print(f"\n  {'方式':<12} {'主机':<24} {'端口':<8} {'状态':<6} {'延迟':<10}")
    print(f"  {'-'*12} {'-'*24} {'-'*8} {'-'*6} {'-'*10}")

    for r in results:
        status = 'OK' if r.reachable else 'FAIL'
        if r.reachable:
            latency = f"{r.latency_ms}ms"
        elif r.error_info:
            latency = r.error_info.category
        else:
            latency = '-'
        print(f"  {r.method:<12} {r.host:<24} {str(r.port):<8} {status:<6} {latency:<10}")

    # 失败项的详细建议
    failed = [r for r in results if not r.reachable and r.error_info]
    if failed:
        print(f"\n  问题排查:")
        for r in failed:
            print(f"    [{r.method}] {r.error_info.message_zh} -> {r.error_info.suggestion_zh}")
