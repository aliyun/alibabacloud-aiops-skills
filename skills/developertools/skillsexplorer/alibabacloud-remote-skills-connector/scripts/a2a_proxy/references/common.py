#!/usr/bin/env python3
"""
A2A Client — HTTP 通信层

封装 JSON-RPC 2.0 请求、SSE 流式读取和 REST GET，
上层 Operation 脚本无需关心 HTTP 细节。
"""

import json
import socket
import time
import uuid
import urllib.request
import urllib.error
from typing import Any, Callable, Generator, Optional

from .client_detect import client_header_value
from .http_security import (
    agenthub_origin,
    agenthub_rpc_url,
    normalize_official_agenthub_endpoint,
    secure_urlopen,
)


A2A_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 60
MAX_JSON_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_AGENT_CARD_BYTES = 1024 * 1024
MAX_ERROR_RESPONSE_BYTES = 256 * 1024
MAX_SSE_LINE_BYTES = 1024 * 1024


class StreamIdleTimeout(TimeoutError):
    """Raised when an SSE stream has no data events within the idle window."""


class ResponseTooLarge(ValueError):
    """Raised when a remote response crosses a local memory boundary."""


# ============================================================
# 内部工具
# ============================================================

def _normalize_token(raw: str) -> str:
    """
    规范化 token：去除首尾空白、合并中间所有空白字符。
    应对用户复制粘贴 token 时夹带的换行、空格等不可见字符。
    """
    return "".join(raw.split())


def _build_rpc_body(method: str, params: dict) -> dict:
    """构造 JSON-RPC 2.0 请求信封"""
    return {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex[:8],
        "method": method,
        "params": params,
    }


def _common_headers(token: str, extra: Optional[dict] = None) -> dict:
    """构造通用请求头"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "A2A-Version": A2A_VERSION,
        # User-Agent 形如：
        # AlibabaCloud-Agent-Skills/alibabacloud-remote-skills-connector/<session-id> claudecode/2.1.118
        # 远程服务端据此同时识别"调用工具"与"承载它的客户端 Agent"。
        "User-Agent": client_header_value(),
    }
    if extra:
        headers.update(extra)
    return headers


def _make_error(code: int, message: str, data: Any = None) -> dict:
    """构造标准化错误返回"""
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": None, "error": err}


def _read_limited(stream, max_bytes: int) -> bytes:
    """Read at most ``max_bytes`` and detect any additional response byte."""
    if type(max_bytes) is not int or max_bytes < 0:
        raise ValueError("response byte limit must be a non-negative integer")
    chunks = []
    remaining = max_bytes + 1
    while remaining > 0:
        chunk = stream.read(min(65536, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    payload = b"".join(chunks)
    if len(payload) > max_bytes:
        raise ResponseTooLarge(f"remote response exceeds {max_bytes} byte size limit")
    return payload


def _json_object_from_bytes(payload: bytes) -> dict:
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("remote JSON response is not an object")
    return decoded


def _invalid_response(detail: str) -> dict:
    return _make_error(-1, "InvalidResponse", detail)


# ============================================================
# rpc_request — 同步 JSON-RPC 请求
# ============================================================

def rpc_request(
    endpoint: str,
    token: str,
    method: str,
    params: dict,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    发送一次同步 JSON-RPC 2.0 请求。

    Args:
        endpoint: A2A Server 基础地址（由已验证的 AgentHub agentId 派生）
        token:    Bearer Token
        method:   JSON-RPC 方法名（如 SendMessage, GetTask）
        params:   方法参数
        timeout:  超时秒数

    Returns:
        解析后的 JSON 响应体 dict，包含 result 或 error。
        网络异常时返回合成的 error 对象。
    """
    url = agenthub_rpc_url(endpoint)
    body = _build_rpc_body(method, params)
    headers = _common_headers(_normalize_token(token))
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with secure_urlopen(req, timeout=timeout) as resp:
            payload = _read_limited(resp, MAX_JSON_RESPONSE_BYTES)
            try:
                return _json_object_from_bytes(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                return _invalid_response(str(exc))
    except urllib.error.HTTPError as e:
        try:
            payload = _read_limited(e, MAX_ERROR_RESPONSE_BYTES)
        except ResponseTooLarge as exc:
            return _invalid_response(str(exc))
        try:
            return _json_object_from_bytes(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raw = payload.decode("utf-8", errors="replace")
            return _make_error(e.code, f"HTTP {e.code}", raw)
    except ResponseTooLarge as e:
        return _invalid_response(str(e))
    except Exception as e:
        return _make_error(-1, "NetworkError", str(e))


# ============================================================
# rpc_stream — SSE 流式 JSON-RPC 请求（Generator）
# ============================================================

def _readline_unbuffered(resp, max_bytes: int = MAX_SSE_LINE_BYTES) -> bytes:
    """
    逐字节从 HTTP 响应中读取一行。

    避免 Python BufferedReader 的内部缓冲导致 SSE 事件延迟返回。
    readline() 会等待填满缓冲区后再扫描换行符，而 read(1) 每次只取
    1 字节，服务端 flush 一个事件后客户端立即能读到。

    性能影响可忽略：SSE 是文本协议，每行几十到几百字节。
    """
    buf = bytearray()
    while True:
        byte = resp.read(1)
        if not byte:
            break
        buf.extend(byte)
        if len(buf) > max_bytes:
            raise ResponseTooLarge(f"SSE line exceeds {max_bytes} byte size limit")
        if byte == b"\n":
            break
    return bytes(buf)


def _set_response_timeout(resp, timeout: Optional[float]) -> None:
    if timeout is None:
        return
    try:
        resp.fp.raw._sock.settimeout(timeout)
    except AttributeError:
        try:
            resp.fp.raw._fp.fp.raw._sock.settimeout(timeout)
        except AttributeError:
            return


def rpc_stream(
    endpoint: str,
    token: str,
    method: str,
    params: dict,
    timeout: int = DEFAULT_TIMEOUT,
    idle_timeout: Optional[float] = None,
    clock: Callable[[], float] = time.monotonic,
) -> Generator[dict, None, None]:
    """
    发送 JSON-RPC 请求并以 SSE 流式接收响应。

    逐字节读取 SSE 事件流，解析 data: 行为 JSON 对象并 yield。
    自动忽略：
      - 以 : 开头的心跳包（如 ": keepalive"）
      - 空行（SSE 事件分隔符）

    使用 read(1) 逐字节构建行，绕过 Python IO 缓冲，
    确保服务端每 flush 一个事件客户端就能立即收到，实现打字机效果。

    Args:
        endpoint: A2A Server 基础地址
        token:    Bearer Token
        method:   JSON-RPC 方法名（如 SendStreamingMessage, SubscribeToTask）
        params:   方法参数
        timeout:  超时秒数

    Yields:
        每个 SSE data 事件解析后的 dict（JSON-RPC 响应信封）
    """
    url = agenthub_rpc_url(endpoint)
    body = _build_rpc_body(method, params)
    headers = _common_headers(_normalize_token(token), {
        "Accept": "text/event-stream, application/json, application/problem+json, application/a2a+json",
    })
    data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    request_timeout = min(timeout, idle_timeout) if idle_timeout else timeout

    try:
        resp = secure_urlopen(req, timeout=request_timeout)
    except urllib.error.HTTPError as e:
        try:
            payload = _read_limited(e, MAX_ERROR_RESPONSE_BYTES)
        except ResponseTooLarge as exc:
            yield _invalid_response(str(exc))
            return
        try:
            yield _json_object_from_bytes(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raw = payload.decode("utf-8", errors="replace")
            yield _make_error(e.code, f"HTTP {e.code}", raw)
        return
    except Exception as e:
        yield _make_error(-1, "NetworkError", str(e))
        return

    try:
        # 逐字节读取 SSE 流，确保实时性
        saw_sse_data = False
        last_data_at = clock()
        try:
            while True:
                if idle_timeout is not None:
                    remaining = idle_timeout - (clock() - last_data_at)
                    if remaining <= 0:
                        raise StreamIdleTimeout(f"No SSE data event for {idle_timeout:g} seconds")
                    _set_response_timeout(resp, min(timeout, remaining))
                try:
                    raw_line = _readline_unbuffered(resp)
                except (socket.timeout, TimeoutError) as e:
                    if idle_timeout is not None:
                        raise StreamIdleTimeout(f"No SSE data event for {idle_timeout:g} seconds") from e
                    raise
                if not raw_line:
                    break

                line = raw_line.decode("utf-8").rstrip("\n\r")

                # 兼容网关把 JSON-RPC 错误以 HTTP 200 + application/json 返回的情况。
                # 不依赖 Content-Type：有些代理会错误标注 SSE 响应。
                if not saw_sse_data and line and not line.startswith(("data:", ":")):
                    remaining_limit = MAX_JSON_RESPONSE_BYTES - len(raw_line)
                    if remaining_limit < 0:
                        raise ResponseTooLarge(
                            f"remote response exceeds {MAX_JSON_RESPONSE_BYTES} byte size limit"
                        )
                    payload = raw_line + _read_limited(resp, remaining_limit)
                    try:
                        yield _json_object_from_bytes(payload)
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                        yield _invalid_response(str(exc))
                    return

                # 心跳包：以 : 开头（如 ": keepalive"），静默跳过
                if line.startswith(":"):
                    continue

                # 空行：SSE 事件分隔符，跳过
                if not line:
                    continue

                # data: 行：提取 JSON 载荷
                if line.startswith("data:"):
                    saw_sse_data = True
                    last_data_at = clock()
                    payload_str = line[5:].strip()
                    if not payload_str:
                        continue
                    try:
                        decoded = json.loads(payload_str)
                    except json.JSONDecodeError:
                        # 非 JSON 的 data 行，跳过
                        continue
                    if isinstance(decoded, dict):
                        yield decoded
        except (ResponseTooLarge, UnicodeDecodeError) as exc:
            # The consumer may abort immediately on this yielded protocol
            # error, so close before yielding rather than relying on generator
            # finalization to release the connection.
            resp.close()
            yield _invalid_response(str(exc))
    finally:
        resp.close()


# ============================================================
# rest_get — REST GET 请求（仅供 GetAgentCard 使用）
# ============================================================

def rest_get(
    endpoint: str,
    path: str,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """
    发送 REST GET 请求。

    专为 GetAgentCard 等 REST-only 端点设计。
    始终添加 A2A-Version header，token 可选。

    Args:
        endpoint: A2A Server 基础地址
        path:     请求路径（如 /.well-known/agent-card.json）
        token:    Bearer Token（可选，GetAgentCard 不需要）
        timeout:  超时秒数

    Returns:
        dict 包含:
          - status: HTTP 状态码
          - body:   解析后的 JSON 响应体（或 None）
          - raw:    原始响应文本
          - error:  错误信息（成功时为 None）
    """
    endpoint = normalize_official_agenthub_endpoint(endpoint)
    url = f"{agenthub_origin(endpoint)}{path}"
    headers = {
        "A2A-Version": A2A_VERSION,
        # 与 _common_headers 保持一致的 User-Agent 规范
        "User-Agent": client_header_value(),
    }
    if token:
        headers["Authorization"] = f"Bearer {_normalize_token(token)}"

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with secure_urlopen(req, timeout=timeout) as resp:
            payload = _read_limited(resp, MAX_AGENT_CARD_BYTES)
            raw = payload.decode("utf-8")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = None
            return {"status": resp.status, "body": body, "raw": raw, "error": None}
    except urllib.error.HTTPError as e:
        try:
            payload = _read_limited(e, MAX_ERROR_RESPONSE_BYTES)
        except ResponseTooLarge as exc:
            return {"status": -1, "body": None, "raw": "", "error": str(exc)}
        raw = payload.decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = None
        return {"status": e.code, "body": body, "raw": raw, "error": f"HTTP {e.code}"}
    except ResponseTooLarge as e:
        return {"status": -1, "body": None, "raw": "", "error": str(e)}
    except Exception as e:
        return {"status": -1, "body": None, "raw": "", "error": str(e)}
