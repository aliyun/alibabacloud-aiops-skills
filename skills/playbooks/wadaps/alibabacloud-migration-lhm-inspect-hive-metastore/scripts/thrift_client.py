#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Hive Metastore Thrift 连接工厂

支持 NOSASL（无认证）和 KERBEROS（GSSAPI）两种认证方式。
提供上下文管理器 ThriftHMSConnection 用于安全的连接管理。
"""

import time
import sys

from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from hmsclient import hive_metastore
ThriftHiveMetastore = hive_metastore.ThriftHiveMetastore


def _build_nosasl_transport(host, port, timeout_ms):
    """构建无认证 Thrift 传输层"""
    socket = TSocket.TSocket(host, port)
    socket.setTimeout(timeout_ms)
    transport = TTransport.TBufferedTransport(socket)
    return transport


def _build_kerberos_transport(host, port, timeout_ms, kerberos_principal):
    """构建 Kerberos 认证 Thrift 传输层"""
    try:
        import thrift_sasl
    except ImportError:
        print("错误：Kerberos 认证需要安装 thrift_sasl 和 gssapi。")
        print("请执行: pip install thrift_sasl gssapi")
        sys.exit(1)

    # 解析 principal: hive/_HOST@REALM → service=hive, host 替换 _HOST
    service = kerberos_principal.split('/')[0] if '/' in kerberos_principal else 'hive'
    resolved_principal = kerberos_principal.replace('_HOST', host)

    socket = TSocket.TSocket(host, port)
    socket.setTimeout(timeout_ms)

    transport = thrift_sasl.TSaslClientTransport(
        lambda: socket,
        host=host,
        service=service,
        mechanism='GSSAPI',
        principal=resolved_principal
    )
    return transport


def create_hms_client(config):
    """
    根据配置创建 Hive Metastore Thrift 客户端。

    参数:
        config: 字典或 ConfigParser section，包含以下键：
            - host: HMS 主机地址
            - port: Thrift 端口（默认 9083）
            - auth: 认证方式 NOSASL 或 KERBEROS（默认 NOSASL）
            - kerberos_principal: Kerberos 主体（仅 KERBEROS 模式）
            - timeout: 连接超时秒数（默认 60）

    返回:
        (client, transport) 元组
    """
    host = config.get('host', 'localhost')
    port = int(config.get('port', 9083))
    auth = config.get('auth', 'NOSASL').upper()
    timeout = int(config.get('timeout', 60))
    timeout_ms = timeout * 1000

    if auth == 'KERBEROS':
        kerberos_principal = config.get('kerberos_principal', 'hive/_HOST@EXAMPLE.COM')
        transport = _build_kerberos_transport(host, port, timeout_ms, kerberos_principal)
    else:
        transport = _build_nosasl_transport(host, port, timeout_ms)

    # 重试连接，指数退避
    max_retries = 3
    last_error = None
    for attempt in range(max_retries):
        try:
            transport.open()
            protocol = TBinaryProtocol.TBinaryProtocol(transport)
            client = ThriftHiveMetastore.Client(protocol)
            return client, transport
        except TTransport.TTransportException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"连接 Hive Metastore {host}:{port} 失败 (尝试 {attempt + 1}/{max_retries})，"
                      f"{wait}s 后重试... 错误: {e}")
                time.sleep(wait)
            else:
                break
        except Exception as e:
            if auth == 'KERBEROS' and 'GSSAPI' in str(type(e).__name__).upper() or 'gss' in str(e).lower():
                print(f"Kerberos 认证失败。请先执行 'kinit' 获取票据。错误: {e}")
                sys.exit(1)
            raise

    print(f"错误：无法连接到 Hive Metastore {host}:{port}，已重试 {max_retries} 次。")
    print(f"最后一次错误: {last_error}")
    sys.exit(1)


def close_hms_client(transport):
    """安全关闭 Thrift 传输"""
    try:
        if transport and transport.isOpen():
            transport.close()
    except Exception:
        pass


class ThriftHMSConnection:
    """
    Hive Metastore Thrift 连接上下文管理器。

    用法:
        with ThriftHMSConnection(config) as client:
            databases = client.get_all_databases()
    """

    def __init__(self, config):
        self._config = config
        self._client = None
        self._transport = None

    def __enter__(self):
        self._client, self._transport = create_hms_client(self._config)
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        close_hms_client(self._transport)
        return False
