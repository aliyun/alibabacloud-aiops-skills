#!/usr/bin/env python3
"""
A2A Operations Hub — 3 个操作的统一入口

内部调用 references/ 下的通信层、会话管理、格式化模块，
对外暴露统一的 --operation 参数入口。

本脚本与具体 Agent 解耦：endpoint、agent-id 等 Agent 特定配置必须由调用方
（通常是 SKILL.md）通过命令行参数显式传入，脚本本身不持有任何默认值。

用法:
  python3 a2a_operations.py --operation <操作名> --endpoint <URL> --agent-id <ID> [参数...]

操作名:
  get_agent_card          获取 Agent 公开卡片（不需要 token）
  send_message            发送消息（同步，等待完整回复）
  send_streaming_message  发送消息（流式/打字机效果）
  subscribe_task          内部操作：订阅 AUTH_REQUIRED 后的已有任务

Token 获取:
  脚本内部调用同目录下的 get_token.sh 自动获取 BearerToken（带缓存）。
  get_token.sh 从本地 AgentHub profile 读取凭证，并由 Skill 直接签名调用 GenerateAccessToken。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid

# 将本脚本目录加入 Python 路径，使 bundled references 可作为 package 导入
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from .references.common import (
        StreamIdleTimeout,
        rpc_request,
        rpc_stream,
        rest_get,
        _normalize_token,
    )
    from .references.context import save_context_id, load_context_id
    from .references.client_detect import detect_client, detect_qwen_session_id, detect_codex_session_id
    from .references.formatter import (
        format_task_result, format_message_result, format_rpc_error,
        format_agent_card, format_rpc_response, handle_stream_event,
        format_task_list,
    )
    from .references import task_recovery, task_store
    from .references.http_security import (
        agenthub_origin,
        normalize_official_agenthub_endpoint,
        validate_agent_id,
    )
    from .references.observability import ObservabilitySessionError, validate_session_id
except ImportError:  # pragma: no cover - direct script execution
    from references.common import (
        StreamIdleTimeout,
        rpc_request,
        rpc_stream,
        rest_get,
        _normalize_token,
    )
    from references.context import save_context_id, load_context_id
    from references.client_detect import detect_client, detect_qwen_session_id, detect_codex_session_id
    from references.formatter import (
        format_task_result, format_message_result, format_rpc_error,
        format_agent_card, format_rpc_response, handle_stream_event,
        format_task_list,
    )
    from references import task_recovery, task_store
    from references.http_security import (
        agenthub_origin,
        normalize_official_agenthub_endpoint,
        validate_agent_id,
    )
    from references.observability import ObservabilitySessionError, validate_session_id

# 固定配置（仅保留与具体 Agent 无关的路径常量）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GET_TOKEN_SCRIPT = os.path.join(SCRIPT_DIR, "get_token.sh")
AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC = 600
FOLLOW_WINDOW_SEC = 180
FOLLOW_INTERVAL_SEC = 5
STREAM_TASK_ID_ERROR = (
    "InvalidResponse: 远端流式事件的 taskId 与当前任务不一致，已停止处理该流。"
)


class StreamTaskBindingError(ValueError):
    """Raised before state mutation when a stream changes task identity."""


def _bind_stream_task_id(current_task_id: str | None, event_task_id) -> str | None:
    if event_task_id is None or event_task_id == "":
        return current_task_id
    if not isinstance(event_task_id, str):
        raise StreamTaskBindingError(STREAM_TASK_ID_ERROR)
    if current_task_id is not None and event_task_id != current_task_id:
        raise StreamTaskBindingError(STREAM_TASK_ID_ERROR)
    return event_task_id


def _control_writer(control_fd: int | None):
    if control_fd is None:
        return None

    def write(event: dict) -> None:
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(payload) > 64 * 1024:
            raise ValueError("control event exceeds 64 KiB")
        os.write(control_fd, payload + b"\n")

    return write


def _emit_control(control_sink, event: dict) -> None:
    if control_sink is not None:
        control_sink(event)


def _task_control_event(record: dict | None) -> dict | None:
    if not record or record.get("activeState") != task_store.STATE_PENDING:
        return None
    task_id = record.get("taskId")
    hitl_round = record.get("hitlRound")
    if not isinstance(task_id, str) or not task_id or type(hitl_round) is not int or hitl_round <= 0:
        return None
    return {
        "v": 1,
        "type": "task_state",
        "state": "auth_required",
        "taskId": task_id,
        "hitlRound": hitl_round,
    }


def _emit_auth_record(control_sink, record: dict | None) -> None:
    event = _task_control_event(record)
    if event is not None:
        _emit_control(control_sink, event)


def _current_task_record(session_id: str, agent_id: str, task_id: str) -> dict | None:
    try:
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            return tx.normalize()[1]
    except ValueError:
        return None


# ============================================================
# Token 提取与校验
# ============================================================

# 与 get_token.sh 约定的 token 输出标记（强契约，缺失即视为污染）
_TOKEN_MARK_BEGIN = "===A2A_TOKEN_BEGIN==="
_TOKEN_MARK_END = "===A2A_TOKEN_END==="

# JWT / 阿里云 AccessToken 字符集白名单（base64url + JWT 分隔符）
_TOKEN_CHARSET_RE = re.compile(r"^[A-Za-z0-9._\-+/=]+$")

# token 提取/校验失败的统一报错文案（简短模式）
_TOKEN_POLLUTION_MSG = "[错误] token 含非法字符，可能是 get_token.sh 输出被污染，请重试或检查脚本输出"
_TOKEN_AUTH_REQUIRED_EXIT_CODE = 20
_CLIENT_SESSION_PREFIXES = {
    "claudecode": "claudecode-",
    "codex": "codex-",
    "qwencode": "qwencode-",
}


def _prefix_client_session_id(client_name: str, session_id: str | None) -> str | None:
    if not session_id:
        return None
    prefix = _CLIENT_SESSION_PREFIXES.get(client_name)
    if not prefix:
        return session_id
    if session_id.startswith(prefix):
        return session_id
    return f"{prefix}{session_id}"


def _valid_generated_session_id(value: str | None) -> bool:
    try:
        validate_session_id(value)
    except ObservabilitySessionError:
        return False
    return True


def _session_id_from_env() -> str | None:
    value = os.environ.get("SKILL_SESSION_ID", "").strip()
    if not _valid_generated_session_id(value):
        return None
    return value


def _self_managed_session_id(
    value: str | None,
    generated_id: str | None,
    *,
    required_prefix: str | None = None,
) -> str | None:
    """Preserve a client prefix and bind the full ID to SKILL_SESSION_ID."""
    generated = generated_id.strip() if generated_id else None
    if not _valid_generated_session_id(generated):
        return None
    candidate = value.strip() if value else None
    if required_prefix:
        expected = f"{required_prefix}-{generated}"
        if candidate in (None, generated, expected):
            return expected
        return None
    if candidate and candidate != generated and candidate.endswith(f"-{generated}"):
        return candidate
    return None


# ============================================================
# 会话 ID 缺失的统一中断入口
# ============================================================

def _fail_missing_session_id(client_name: str, qwen_fallback_failed: bool,
                             codex_env_missing: bool = False,
                             qoderwork_invalid: bool = False) -> None:
    """
    session-id 无法获得时的统一中断。

    打印结构化、可操作的提示到 stderr，退出码 2
    （区别于 token/网络错误的 exit 1），便于外层按码匹配错误分支。

    Args:
        client_name:            detect_client() 识别出的客户端名
        qwen_fallback_failed:   True 表示是 qwen 软链 fallback 失败；
                                False 表示其他客户端的 --session-id 为空
        codex_env_missing:      True 表示 codex 的 CODEX_THREAD_ID 为空或不存在
        qoderwork_invalid:      True 表示 qoderwork 的 session-id 缺失或格式非法
    """
    lines = ["[错误] 无法确定会话 ID (--session-id)，脚本已中断。"]
    if qwen_fallback_failed:
        lines.append(
            f"  识别到客户端: {client_name}，但 ~/.qwen/debug/latest 软链不存在或不可读。"
        )
        lines.append("  请确保本次 qwen-code 会话正常启动后再重试，")
    elif codex_env_missing:
        lines.append(
            f"  识别到客户端: {client_name}，但 CODEX_THREAD_ID 环境变量不存在或为空。"
        )
        lines.append("  请在当前 Codex 会话中执行 printenv CODEX_THREAD_ID 确认后再重试。")
    elif qoderwork_invalid:
        lines.append(
            f"  识别到客户端: {client_name}，但 session-id 不是 qoderwork-<32 位小写十六进制> 格式，"
        )
        lines.append("  或其后缀与 SKILL_SESSION_ID 不一致。请只生成一次 SKILL_SESSION_ID，")
        lines.append("  并将业务会话固定派生为 qoderwork-${SKILL_SESSION_ID}；不要删除 qoderwork- 前缀。")
        lines.append("  该值只允许首次远程访问前分配一次；后续提问、tool call、任务续接都必须复用。")
    elif client_name == "claudecode":
        lines.append("  请确保 Claude Code 版本已暴露 ${CLAUDE_CODE_SESSION_ID} 或 ${CLAUDE_SESSION_ID}，")
    else:
        # 客户端分配类（未知/未来客户端）没有已知的 session-id 自动获取方式，必须由端侧维护。
        lines.append(
            f"  识别到客户端: {client_name}。此客户端没有已知的 session-id 自动获取方式。"
        )
        lines.append("  请首次生成 SKILL_SESSION_ID=<32-char-lowercase-hex>，")
        lines.append("  并显式传入 <client-name>-${SKILL_SESSION_ID}；保留现有客户端前缀。")
        lines.append("  该值只允许首次远程访问前分配一次；后续提问、tool call、任务续接都必须复用。")
    sys.stderr.write("\n".join(lines) + "\n")
    sys.stderr.flush()
    sys.exit(2)


def acquire_token() -> str:
    """
    调用 get_token.sh 获取 BearerToken。

    get_token.sh 会复用缓存中锁定的凭证来源；首次选择时优先使用 aliyun CLI
    AK/StsToken/RamRoleArn profile，否则使用 AgentHub 私有 AK/OAuth profile。
    内部有 Token 缓存机制（~/.aliyun_agenthub/${SITE}_credential），
    如果 Token 未过期则直接返回，不调用远端 API。

    强契约：get_token.sh 必须用 ===A2A_TOKEN_BEGIN=== / ===A2A_TOKEN_END===
    标记包裹真正的 token 输出。任何形式的污染（无标记、多行、非 ASCII、
    非白名单字符、长度异常）都会立即简短报错并退出，避免被中文/不可见字符
    污染后写入 HTTP Header 触发 latin-1 编码错误。

    Returns:
        BearerToken 字符串

    Raises:
        SystemExit: 获取失败、token 提取失败或校验失败时退出
    """
    if not os.path.exists(GET_TOKEN_SCRIPT):
        print(f"[错误] 找不到 get_token.sh 脚本: {GET_TOKEN_SCRIPT}")
        sys.exit(1)

    # 避免 profile、网络或 ramoauth 服务异常时永久阻塞。
    try:
        result = subprocess.run(
            ["bash", GET_TOKEN_SCRIPT, "login", "CN"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "AGENTHUB_PYTHON": sys.executable},
        )
    except subprocess.TimeoutExpired:
        print("[错误] 获取 Token 超时，请检查 profile 配置、网络或 ramoauth 服务是否正常")
        sys.exit(1)
    if result.returncode != 0:
        if result.returncode == _TOKEN_AUTH_REQUIRED_EXIT_CODE:
            if result.stdout.strip():
                print(result.stdout.strip())
            if result.stderr.strip():
                print(result.stderr.strip())
            sys.exit(_TOKEN_AUTH_REQUIRED_EXIT_CODE)
        print(f"[错误] 获取 Token 失败 (exit code: {result.returncode})")
        print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        sys.exit(1)
    token = _extract_token_from_output(result.stdout)
    # 三重严格校验：ASCII / 字符集白名单 / 长度
    is_valid = (
        token.isascii()
        and _TOKEN_CHARSET_RE.match(token)
        and len(token) >= 20
    )
    if not is_valid:
        print(_TOKEN_POLLUTION_MSG)
        sys.exit(1)
    return token


def _extract_token_from_output(output: str) -> str:
    """
    强制按 ===A2A_TOKEN_BEGIN=== / ===A2A_TOKEN_END=== 标记从 stdout 中提取 token。

    协议：
      - 必须存在恰好一对 BEGIN/END 标记
      - 标记之间必须恰好有 1 行非空内容（即 token 本身）
      - 任何偏离上述约束的都视为脚本输出被污染，立即简短报错并退出

    Returns:
        提取并 normalize 后的 token 字符串
    """
    lines = output.splitlines()
    try:
        start = lines.index(_TOKEN_MARK_BEGIN)
        end = lines.index(_TOKEN_MARK_END, start + 1)
    except ValueError:
        print(_TOKEN_POLLUTION_MSG)
        sys.exit(1)
    candidates = [l.strip() for l in lines[start + 1:end] if l.strip()]
    if len(candidates) != 1:
        print(_TOKEN_POLLUTION_MSG)
        sys.exit(1)
    return _normalize_token(candidates[0])


# ============================================================
# 操作实现
# ============================================================

def _agent_card_control_event(card: dict, endpoint: str) -> dict:
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list):
        raise ValueError("Agent Card has no supported interfaces")
    expected_origin = agenthub_origin(endpoint)
    selected = None
    for interface in interfaces:
        if not isinstance(interface, dict):
            continue
        if interface.get("protocolBinding") != "JSONRPC":
            continue
        url = interface.get("url")
        if not isinstance(url, str):
            continue
        try:
            trusted_url = normalize_official_agenthub_endpoint(url)
        except ValueError:
            continue
        if agenthub_origin(trusted_url) == expected_origin:
            selected = interface
            break
    if selected is None:
        raise ValueError("Agent Card has no trusted JSONRPC interface")
    capabilities = card.get("capabilities")
    streaming = bool(
        isinstance(capabilities, dict)
        and type(capabilities.get("streaming")) is bool
        and capabilities.get("streaming")
    )
    return {
        "v": 1,
        "type": "agent_card",
        "supportsStreaming": streaming,
        "rpcPath": "/rpc",
    }


def do_get_agent_card(endpoint: str, control_sink=None) -> None:
    """GetAgentCard — 获取 Agent 公开卡片（不需要 token）"""
    resp = rest_get(endpoint, "/.well-known/agent-card.json")
    if resp["error"]:
        print(f"请求失败: {resp['error']}")
        if resp["raw"]:
            print(f"响应: {resp['raw'][:500]}")
        sys.exit(1)
    card = resp["body"]
    if not card:
        print("请求成功，但响应体为空。")
        sys.exit(1)
    try:
        event = _agent_card_control_event(card, endpoint)
    except ValueError as exc:
        print(f"Agent Card 无可用可信接口: {exc}")
        sys.exit(1)
    _emit_control(control_sink, event)
    print(format_agent_card(card))


def _task_state(task: dict) -> str:
    return (task.get("status") or {}).get("state", "")


def _task_status_message(task: dict) -> str:
    parts = ((task.get("status") or {}).get("message") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts if part.get("text"))


def _stream_message_text(event: dict) -> str:
    message = ((event.get("result") or {}).get("message") or {})
    parts = message.get("parts") or []
    return "".join(str(part.get("text", "")) for part in parts if part.get("text"))


def _normalize_stream_text(text) -> str:
    return "".join(str(text or "").split())


def _should_suppress_final_message(event: dict, streamed_text: str) -> bool:
    message_text = _stream_message_text(event)
    if not message_text or not streamed_text:
        return False
    return _normalize_stream_text(message_text) == _normalize_stream_text(streamed_text)


def _task_from_stream_state(task_id: str, context_id: str, state: str, message: str = "") -> dict:
    return {
        "id": task_id,
        "contextId": context_id,
        "status": {
            "state": state,
            "message": {"parts": [{"text": message}]} if message else {"parts": []},
        },
        "artifacts": [],
    }


def _record_auth_required_if_possible(
    endpoint: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    context_id: str,
    status_message: str = "",
    original_message: str = None,
) -> dict | None:
    if not task_id:
        print("\n[警告] 收到 TASK_STATE_AUTH_REQUIRED，但未获得 taskId，无法进入本地恢复队列。")
        return None
    try:
        return task_recovery.record_auth_required_task(
            session_id=session_id,
            agent_id=agent_id,
            endpoint=endpoint,
            task_id=task_id,
            context_id=context_id,
            status_message=status_message,
            original_message=original_message,
        )
    except ValueError as e:
        print(f"\n[警告] taskId 无法安全落盘，跳过本地恢复队列: {e}")
        return None


def _record_input_required_if_possible(
    endpoint: str,
    agent_id: str,
    session_id: str,
    task: dict = None,
    task_id: str = None,
    context_id: str = None,
    status_message: str = "",
) -> bool:
    task_id = task_id or (task or {}).get("id") or (task or {}).get("taskId")
    if not task_id:
        print("\n[警告] 收到 TASK_STATE_INPUT_REQUIRED，但未获得 taskId，无法进入本地 input_required 队列。")
        return False
    input_task = task or _task_from_stream_state(
        task_id,
        context_id,
        task_recovery.TASK_STATE_INPUT_REQUIRED,
        status_message,
    )
    if context_id and not input_task.get("contextId"):
        input_task = dict(input_task)
        input_task["contextId"] = context_id
    try:
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            _state, existing = tx.normalize()
            task_recovery.tx_enter_input_required(
                tx,
                endpoint=endpoint,
                task=input_task,
                existing=existing,
            )
    except ValueError as e:
        print(f"\n[警告] taskId 无法安全落盘，跳过本地 input_required 队列: {e}")
        return False
    return True


def _transition_typed_stream_state(
    endpoint: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    context_id: str,
    state: str,
    status_message: str = "",
    task: dict | None = None,
) -> dict | None:
    if not task_id or not session_id or not agent_id:
        return None
    typed_task = task or _task_from_stream_state(task_id, context_id, state, status_message)
    try:
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            _current_state, existing = tx.normalize()
            if existing is None and state not in (
                task_recovery.TASK_STATE_AUTH_REQUIRED,
                task_recovery.TASK_STATE_INPUT_REQUIRED,
            ):
                return None
            updated = task_recovery.transition_from_task(
                tx,
                endpoint=endpoint,
                task=typed_task,
                existing=existing,
                probe_attempt=False,
            )
            if state in task_recovery.TERMINAL_STATES:
                return task_recovery.tx_enter_delivered(
                    tx,
                    record=updated,
                    delivery_mode="send_streaming_foreground",
                )
            return updated
    except ValueError as exc:
        print(f"\n[警告] typed task state 无法安全落盘: {exc}")
        return None


def _sweep_and_print_reminder(endpoint: str, token: str, agent_id: str,
                              session_id: str, max_tasks: int,
                              deadline_ms: int, no_sweep: bool = False,
                              control_sink=None) -> None:
    if not no_sweep and token:
        task_recovery.sweep_recoverable_tasks(
            endpoint=endpoint,
            token=token,
            session_id=session_id,
            agent_id=agent_id,
            max_tasks=max_tasks,
            deadline_ms=deadline_ms,
        )
    ready = []
    input_required = []
    for record in task_store.list_records(session_id, agent_id):
        state = record.get("activeState")
        task_id = record.get("taskId")
        if not isinstance(task_id, str) or not task_id:
            continue
        if state == task_store.STATE_READY and record.get("terminalState") == task_recovery.TASK_STATE_COMPLETED:
            ready.append({"taskId": task_id, "state": task_recovery.TASK_STATE_COMPLETED})
        elif state == task_store.STATE_INPUT_REQUIRED:
            input_required.append({"taskId": task_id, "state": task_recovery.TASK_STATE_INPUT_REQUIRED})
    if ready or input_required:
        _emit_control(
            control_sink,
            {
                "v": 1,
                "type": "task_notifications",
                "readyResults": ready[:3],
                "inputRequired": input_required[:3],
            },
        )


def _combined_approval_text(latest_message: str = "", streamed_text_parts: list = None) -> str:
    streamed_text = "".join(streamed_text_parts or []).strip()
    latest = (latest_message or "").strip()
    parts = []
    if streamed_text:
        parts.append(streamed_text)
    if latest and latest not in streamed_text:
        parts.append(latest)
    return "\n".join(parts)


def _cleanup_task_not_found_if_possible(session_id: str, agent_id: str, task_id: str) -> bool:
    if not (session_id and agent_id and task_id):
        return False
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        removed = task_recovery.tx_remove_task_not_found(tx, record)
    print(removed["message"])
    return True


def _check_task_command(task_id: str) -> str:
    return f"check_task --task-id {task_id}"


def _format_idle_timeout_message(task_id: str, idle_timeout_sec: int) -> str:
    minutes = max(1, int(idle_timeout_sec // 60))
    return (
        f"\n[提示] 本次 subscribe_task 已等待到 {minutes} 分钟无新的服务端事件；"
        "已结束这次一次性订阅并保留本地任务记录。"
        f"后续不要再次执行 subscribe_task，只能使用 {_check_task_command(task_id)} 主动查询任务进展。"
    )


def _subscribed_terminal_task(task_id: str, context_id: str, state: str,
                              message: str = "", streamed_text: str = "",
                              fallback_task: dict = None) -> dict:
    if fallback_task:
        return fallback_task
    task = _task_from_stream_state(task_id, context_id, state, message)
    if streamed_text:
        task["artifacts"] = [{"parts": [{"text": streamed_text}]}]
    return task


def _deliver_subscribed_terminal(
    tx,
    record: dict,
    endpoint: str,
    task_id: str,
    context_id: str,
    state: str,
    message: str = "",
    fallback_task: dict = None,
    streamed_text: str = "",
):
    final_task = _subscribed_terminal_task(
        task_id,
        context_id,
        state,
        message=message,
        streamed_text=streamed_text,
        fallback_task=fallback_task,
    )
    ready = task_recovery.tx_enter_ready(
        tx,
        endpoint=endpoint,
        task=final_task,
        existing=record,
    )
    delivered = task_recovery.tx_enter_delivered(
        tx,
        record=ready,
        delivery_mode="auth_subscribe",
    )
    return delivered, True


def _transition_subscribe_dispatch(
    endpoint: str,
    token: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    context_id: str,
    state: str,
    message: str = "",
    task: dict = None,
    history_length: int = None,
    streamed_text: str = "",
):
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record:
            return None, True
        if state in task_recovery.TERMINAL_STATES:
            return _deliver_subscribed_terminal(
                tx,
                record,
                endpoint,
                task_id,
                context_id,
                state,
                message=message,
                fallback_task=task,
                streamed_text=streamed_text,
            )
        updated = _handle_continue_state(
            tx,
            record,
            endpoint,
            task_id,
            context_id,
            state,
            message,
            task=task,
        )
        return updated, updated and updated.get("activeState") == task_store.STATE_INPUT_REQUIRED


def _mark_subscribe_progress(
    endpoint: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    context_id: str,
) -> None:
    if not task_id:
        return
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record or record.get("activeState") not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
            return
        task_recovery.tx_enter_running(
            tx,
            endpoint=endpoint,
            task_id=task_id,
            context_id=context_id or record.get("contextId"),
            state=task_recovery.TASK_STATE_WORKING,
            existing=record,
            probe_attempt=False,
        )


def _begin_auth_subscribe_once(
    agent_id: str,
    session_id: str,
    task_id: str,
    idle_timeout_sec: int,
) -> int | None:
    try:
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            _state, record = tx.normalize()
            if not record:
                print(f"当前 session 下没有找到任务 {task_id}。")
                return None
            current_round = record.get("hitlRound", 1) or 1
            attempted_round = record.get("authSubscribeAttemptedRound")
            if attempted_round is None and record.get("authSubscribeAttempted"):
                attempted_round = current_round
            if record.get("authSubscribeAttempted") and attempted_round == current_round:
                print(
                    f"[提示] 任务 {task_id} 的第 {current_round} 轮审批已经执行过一次 subscribe_task；"
                    "每个 auth_required 审批轮次只允许一次前台订阅，不能重复订阅以免丢失流数据。"
                    f"后续只能使用 {_check_task_command(task_id)} 主动查询任务进展。"
                )
                return None
            active = record.get("activeState")
            if active not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
                print(task_recovery.format_task_status_record(record))
                return None
            updated = dict(record)
            updated["authSubscribeAttempted"] = True
            updated["authSubscribeAttemptedRound"] = current_round
            updated["authSubscribeStartedAt"] = task_store.now_iso()
            updated.pop("authSubscribeEndedAt", None)
            updated.pop("authSubscribeEndReason", None)
            updated["authSubscribeIdleTimeoutSec"] = idle_timeout_sec
            tx.enter(active, updated)
            return current_round
    except ValueError as e:
        print(f"[警告] taskId 无法安全落盘，跳过订阅: {e}")
        return None


def _end_auth_subscribe_attempt(
    agent_id: str,
    session_id: str,
    task_id: str,
    reason: str,
) -> None:
    if not task_id:
        return
    try:
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            _state, record = tx.normalize()
            if not record:
                return
            active = record.get("activeState")
            if active not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
                return
            updated = dict(record)
            updated["authSubscribeAttempted"] = True
            updated["authSubscribeAttemptedRound"] = record.get("hitlRound", 1) or 1
            updated["authSubscribeEndedAt"] = task_store.now_iso()
            updated["authSubscribeEndReason"] = reason
            tx.enter(active, updated)
    except ValueError:
        return


def _maybe_emit_nested_auth_subscribe(
    endpoint: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    subscribed_round: int,
    updated_record: dict | None,
    approval_text: str,
    control_sink=None,
) -> bool:
    new_round = (updated_record or {}).get("hitlRound", subscribed_round) or subscribed_round
    if new_round <= subscribed_round:
        return False
    print(
        f"\n[提示] 订阅过程中远端任务进入第 {new_round} 轮 TASK_STATE_AUTH_REQUIRED；"
        "这是新的审批轮次，必须展示新审批信息并立即重新订阅本轮审批结果。"
    )
    _emit_auth_record(control_sink, updated_record)
    return True


def _subscribe_auth_required_task(
    endpoint: str,
    token: str,
    agent_id: str,
    session_id: str,
    task_id: str,
    idle_timeout_sec: int = AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
    history_length: int = None,
    control_sink=None,
) -> None:
    if not token or not task_id:
        return
    subscribed_round = _begin_auth_subscribe_once(agent_id, session_id, task_id, idle_timeout_sec)
    if not subscribed_round:
        return
    print(
        "\n[提示] 审批信息已完整输出，原 SSE 连接已结束；"
        f"我主动帮你订阅第 {subscribed_round} 轮审批结果。本轮 SubscribeToTask 是一次性前台订阅；"
        "若本轮订阅结束仍未拿到终态，后续只能使用 check_task。"
    )
    sys.stdout.flush()
    params = {"id": task_id}
    current_task_id = task_id
    current_context_id = None
    streamed_text_parts = []
    terminal_or_waiting_input = False
    auth_waiting_reported = False
    try:
        for event in rpc_stream(
            endpoint,
            token,
            "SubscribeToTask",
            params,
            timeout=idle_timeout_sec,
            idle_timeout=idle_timeout_sec,
        ):
            if task_recovery.is_task_not_found_error(event.get("error")):
                _cleanup_task_not_found_if_possible(session_id, agent_id, current_task_id)
                return
            suppress_message_text = _should_suppress_final_message(
                event,
                "".join(streamed_text_parts),
            )
            dispatch = handle_stream_event(event, suppress_message_text=suppress_message_text)
            if dispatch["type"] == "error":
                with task_store.task_transaction(session_id, agent_id, current_task_id) as tx:
                    _state, record = tx.normalize()
                    if record:
                        task_recovery.tx_update_probe_error(
                            tx,
                            record,
                            error_message=format_rpc_error(dispatch.get("error", {})),
                        )
                _end_auth_subscribe_attempt(agent_id, session_id, current_task_id, "error")
                print(
                    f"\n[提示] 订阅任务 {current_task_id} 失败；本次 subscribe_task 已结束且不可重试，"
                    f"本地记录已保留，后续只能使用 {_check_task_command(current_task_id)} 查看。"
                )
                return
            try:
                current_task_id = _bind_stream_task_id(
                    current_task_id,
                    dispatch.get("task_id"),
                )
            except StreamTaskBindingError:
                with task_store.task_transaction(
                    session_id,
                    agent_id,
                    task_id,
                ) as tx:
                    _state, record = tx.normalize()
                    if record:
                        task_recovery.tx_update_probe_error(
                            tx,
                            record,
                            error_message=STREAM_TASK_ID_ERROR,
                        )
                _end_auth_subscribe_attempt(
                    agent_id,
                    session_id,
                    task_id,
                    "invalid_task_id",
                )
                print(f"\n[错误] {STREAM_TASK_ID_ERROR}")
                return
            if dispatch.get("context_id"):
                current_context_id = dispatch.get("context_id")
            if dispatch["type"] == "artifact":
                text = dispatch.get("text") or ""
                if text:
                    streamed_text_parts.append(text)
                _mark_subscribe_progress(
                    endpoint,
                    agent_id,
                    session_id,
                    current_task_id,
                    current_context_id,
                )
            elif dispatch["type"] == "message":
                text = dispatch.get("text") or ""
                if text:
                    streamed_text_parts.append(text)
                _mark_subscribe_progress(
                    endpoint,
                    agent_id,
                    session_id,
                    current_task_id,
                    current_context_id,
                )
            elif dispatch["type"] == "task":
                task = dispatch["task"]
                state = dispatch.get("state") or _task_state(task)
                _updated, terminal_or_waiting_input = _transition_subscribe_dispatch(
                    endpoint,
                    token,
                    agent_id,
                    session_id,
                    current_task_id,
                    current_context_id,
                    state,
                    _task_status_message(task),
                    task=task,
                    history_length=history_length,
                    streamed_text="".join(streamed_text_parts),
                )
                if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                    if _maybe_emit_nested_auth_subscribe(
                        endpoint,
                        agent_id,
                        session_id,
                        current_task_id,
                        subscribed_round,
                        _updated,
                        _combined_approval_text(
                            _task_status_message(task),
                            streamed_text_parts,
                        ),
                        control_sink=control_sink,
                    ):
                        return
                    if not auth_waiting_reported:
                        print(
                            "\n[提示] 订阅流显示任务仍在等待审批；"
                            "保持当前一次性订阅继续等待后续服务端事件。"
                        )
                        auth_waiting_reported = True
                    continue
                if terminal_or_waiting_input:
                    return
            elif dispatch["type"] == "status":
                state = dispatch.get("state")
                _updated, terminal_or_waiting_input = _transition_subscribe_dispatch(
                    endpoint,
                    token,
                    agent_id,
                    session_id,
                    current_task_id,
                    current_context_id,
                    state,
                    dispatch.get("agent_message") or "",
                    history_length=history_length,
                    streamed_text="".join(streamed_text_parts),
                )
                if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                    if _maybe_emit_nested_auth_subscribe(
                        endpoint,
                        agent_id,
                        session_id,
                        current_task_id,
                        subscribed_round,
                        _updated,
                        _combined_approval_text(
                            dispatch.get("agent_message") or "",
                            streamed_text_parts,
                        ),
                        control_sink=control_sink,
                    ):
                        return
                    if not auth_waiting_reported:
                        print(
                            "\n[提示] 订阅流显示任务仍在等待审批；"
                            "保持当前一次性订阅继续等待后续服务端事件。"
                        )
                        auth_waiting_reported = True
                    continue
                if terminal_or_waiting_input:
                    return
    except StreamIdleTimeout:
        _end_auth_subscribe_attempt(agent_id, session_id, current_task_id, "idle_timeout")
        print(_format_idle_timeout_message(current_task_id, idle_timeout_sec))
        return
    except KeyboardInterrupt:
        _end_auth_subscribe_attempt(agent_id, session_id, current_task_id, "interrupted")
        sys.stdout.write(
            f"\n[中断] 用户主动停止订阅，本次 subscribe_task 已结束且不可重试；"
            f"任务保留为当前状态，后续只能 {_check_task_command(current_task_id)}。\n"
        )
        sys.stdout.flush()
        sys.exit(0)
    if not terminal_or_waiting_input:
        _end_auth_subscribe_attempt(agent_id, session_id, current_task_id, "stream_closed")
        print(
            f"\n[提示] 订阅连接已结束但任务尚未返回终态；本次 subscribe_task 已结束且不可重试，"
            f"本地记录已保留，后续只能使用 {_check_task_command(current_task_id)} 主动查询任务进展。"
        )


def do_send_message(endpoint: str, token: str, message: str,
                    accepted_output_modes: str = None,
                    history_length: int = None, return_immediately: bool = False,
                    agent_id: str = None, session_id: str = None,
                    sweep_max_tasks: int = 2,
                    sweep_deadline_ms: int = task_recovery.GET_TASK_SWEEP_DEADLINE_MS,
                    no_sweep: bool = False,
                    auth_subscribe_idle_timeout_sec: int = AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
                    no_auth_followup: bool = False,
                    control_sink=None) -> None:
    """SendMessage — 同步发送消息"""
    token = _normalize_token(token)
    ctx_id = _resolve_context_id(session_id=session_id, agent_id=agent_id)
    msg = {
        "messageId": uuid.uuid4().hex,
        "role": "ROLE_USER",
        "parts": [{"text": message}],
    }
    if ctx_id:
        msg["contextId"] = ctx_id
    params = {"message": msg}
    configuration = {}
    if accepted_output_modes:
        configuration["acceptedOutputModes"] = [m.strip() for m in accepted_output_modes.split(",")]
    if history_length is not None:
        configuration["historyLength"] = history_length
    if return_immediately:
        configuration["returnImmediately"] = True
    if configuration:
        params["configuration"] = configuration
    response = rpc_request(endpoint, token, "SendMessage", params)
    error = response.get("error")
    if error:
        print(format_rpc_error(error))
        sys.exit(1)
    result = response.get("result", {})
    if task := result.get("task"):
        state = _task_state(task)
        if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
            record = _record_auth_required_if_possible(
                endpoint=endpoint,
                agent_id=agent_id,
                session_id=session_id,
                task_id=task.get("id") or task.get("taskId"),
                context_id=task.get("contextId"),
                status_message=_task_status_message(task),
                original_message=message,
            )
            _emit_auth_record(control_sink, record)
        elif state == task_recovery.TASK_STATE_INPUT_REQUIRED:
            _record_input_required_if_possible(
                endpoint=endpoint,
                agent_id=agent_id,
                session_id=session_id,
                task=task,
                task_id=task.get("id") or task.get("taskId"),
                context_id=task.get("contextId"),
                status_message=_task_status_message(task),
            )
        _handle_task_response(task, endpoint, agent_id=agent_id, session_id=session_id)
    elif message_resp := result.get("message"):
        _handle_message_response(message_resp, endpoint, agent_id=agent_id, session_id=session_id)
    else:
        print(format_rpc_response(response))
    _sweep_and_print_reminder(
        endpoint, token, agent_id, session_id,
        max_tasks=sweep_max_tasks,
        deadline_ms=sweep_deadline_ms,
        no_sweep=no_sweep,
        control_sink=control_sink,
    )


def do_send_streaming_message(endpoint: str, token: str, message: str,
                              accepted_output_modes: str = None,
                              history_length: int = None, agent_id: str = None,
                              session_id: str = None,
                              sweep_max_tasks: int = 2,
                              sweep_deadline_ms: int = task_recovery.GET_TASK_SWEEP_DEADLINE_MS,
                              no_sweep: bool = False,
                              auth_subscribe_idle_timeout_sec: int = AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
                              no_auth_followup: bool = False,
                              control_sink=None) -> None:
    """SendStreamingMessage — 流式发送消息"""
    token = _normalize_token(token)
    ctx_id = _resolve_context_id(session_id=session_id, agent_id=agent_id)
    msg = {
        "messageId": uuid.uuid4().hex,
        "role": "ROLE_USER",
        "parts": [{"text": message}],
    }
    if ctx_id:
        msg["contextId"] = ctx_id
    params = {"message": msg}
    configuration = {}
    if accepted_output_modes:
        configuration["acceptedOutputModes"] = [m.strip() for m in accepted_output_modes.split(",")]
    if history_length is not None:
        configuration["historyLength"] = history_length
    if configuration:
        params["configuration"] = configuration
    context_id_result = None
    current_task_id = None
    auth_recorded = False
    input_required_recorded = False
    streamed_text_parts = []
    auth_message_parts = []
    emitted_auth_rounds = set()
    try:
        for event in rpc_stream(endpoint, token, "SendStreamingMessage", params):
            if task_recovery.is_task_not_found_error(event.get("error")):
                if _cleanup_task_not_found_if_possible(session_id, agent_id, current_task_id):
                    return
                print(format_rpc_error(event.get("error")))
                sys.exit(1)
            suppress_message_text = _should_suppress_final_message(
                event,
                "".join(streamed_text_parts),
            )
            dispatch = handle_stream_event(event, suppress_message_text=suppress_message_text)
            if dispatch["type"] == "error":
                sys.exit(1)
            try:
                current_task_id = _bind_stream_task_id(
                    current_task_id,
                    dispatch.get("task_id"),
                )
            except StreamTaskBindingError:
                print(f"\n[错误] {STREAM_TASK_ID_ERROR}")
                sys.exit(1)
            if dispatch.get("context_id"):
                context_id_result = dispatch.get("context_id")
            if dispatch["type"] == "artifact":
                if dispatch.get("text"):
                    text = dispatch.get("text")
                    streamed_text_parts.append(text)
                    auth_message_parts.append(text)
            elif dispatch["type"] == "task":
                task = dispatch["task"]
                context_id_result = context_id_result or task.get("contextId")
                state = dispatch.get("state") or _task_state(task)
                record = _transition_typed_stream_state(
                    endpoint,
                    agent_id,
                    session_id,
                    current_task_id,
                    context_id_result,
                    state,
                    _task_status_message(task),
                    task=task,
                )
                if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                    auth_recorded = True
                    hitl_round = (record or {}).get("hitlRound")
                    if hitl_round not in emitted_auth_rounds:
                        _emit_auth_record(control_sink, record)
                        emitted_auth_rounds.add(hitl_round)
                elif state == task_recovery.TASK_STATE_INPUT_REQUIRED:
                    input_required_recorded = record is not None
            elif dispatch["type"] == "status":
                state = dispatch.get("state")
                if dispatch.get("agent_message"):
                    auth_message_parts.append(dispatch.get("agent_message"))
                status_task_id = current_task_id or dispatch.get("task_id")
                status_context_id = context_id_result or dispatch.get("context_id")
                record = _transition_typed_stream_state(
                    endpoint,
                    agent_id,
                    session_id,
                    status_task_id,
                    status_context_id,
                    state,
                    dispatch.get("agent_message") or "",
                )
                if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                    auth_recorded = True
                    hitl_round = (record or {}).get("hitlRound")
                    if hitl_round not in emitted_auth_rounds:
                        _emit_auth_record(control_sink, record)
                        emitted_auth_rounds.add(hitl_round)
                elif state == task_recovery.TASK_STATE_INPUT_REQUIRED:
                    input_required_recorded = record is not None
            elif dispatch["type"] == "message":
                context_id_result = dispatch.get("context_id")
                if dispatch.get("text"):
                    auth_message_parts.append(dispatch.get("text"))
    except KeyboardInterrupt:
        sys.stdout.write("\n[中断] 用户主动停止接收。\n")
        sys.stdout.flush()
        sys.exit(0)
    print()
    auth_message = "".join(auth_message_parts)
    if context_id_result:
        save_context_id(
            session_id=session_id,
            agent_id=agent_id,
            context_id=context_id_result,
        )
    _sweep_and_print_reminder(
        endpoint, token, agent_id, session_id,
        max_tasks=sweep_max_tasks,
        deadline_ms=sweep_deadline_ms,
        no_sweep=no_sweep,
        control_sink=control_sink,
    )


def do_list_tasks(agent_id: str, session_id: str, include_delivered: bool = False) -> None:
    records = task_store.list_records(
        session_id=session_id,
        agent_id=agent_id,
        include_delivered=include_delivered,
    )
    print(format_task_list(records))


def do_check_task(endpoint: str, token: str, agent_id: str, session_id: str,
                  task_id: str, history_length: int = None) -> None:
    if not task_id:
        print("错误: check_task 需要 --task-id")
        sys.exit(1)
    print(task_recovery.check_task(
        endpoint=endpoint,
        token=token,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        history_length=history_length,
    ))


def do_subscribe_task(endpoint: str, token: str, agent_id: str, session_id: str,
                      task_id: str,
                      idle_timeout_sec: int = AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
                      history_length: int = None,
                      control_sink=None) -> None:
    if not task_id:
        print("错误: subscribe_task 需要 --task-id")
        sys.exit(1)
    _subscribe_auth_required_task(
        endpoint=endpoint,
        token=token,
        agent_id=agent_id,
        session_id=session_id,
        task_id=task_id,
        idle_timeout_sec=idle_timeout_sec,
        history_length=history_length,
        control_sink=control_sink,
    )


def do_follow_task(endpoint: str, token: str, agent_id: str, session_id: str,
                   task_id: str, window_sec: int = FOLLOW_WINDOW_SEC,
                   interval_sec: int = FOLLOW_INTERVAL_SEC,
                   control_sink=None) -> None:
    if not task_id:
        print("错误: follow_task 需要 --task-id")
        sys.exit(1)
    before = _current_task_record(session_id, agent_id, task_id)
    before_round = (before or {}).get("hitlRound", 0) or 0
    result = task_recovery.follow_auth_required_task_until_ready(
        endpoint=endpoint,
        token=token,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        window_sec=window_sec,
        interval_sec=interval_sec,
    )
    if result:
        print(result)
    after = _current_task_record(session_id, agent_id, task_id)
    after_round = (after or {}).get("hitlRound", 0) or 0
    if after_round > before_round:
        _emit_auth_record(control_sink, after)


def do_cancel_task(endpoint: str, token: str, agent_id: str, session_id: str,
                   task_id: str, history_length: int = None) -> None:
    if not task_id:
        print("错误: cancel_task 需要 --task-id")
        sys.exit(1)
    print(task_recovery.cancel_task(
        endpoint=endpoint,
        token=token,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        history_length=history_length,
    ))


def do_view_task(endpoint: str, token: str, agent_id: str, session_id: str,
                 task_id: str) -> None:
    if not task_id:
        print("错误: view_task 需要 --task-id")
        sys.exit(1)
    task_recovery.view_task(
        endpoint=endpoint,
        token=token,
        session_id=session_id,
        agent_id=agent_id,
        task_id=task_id,
        emit=lambda text: print(text),
    )


def _finish_continue_with_task(tx, record: dict, endpoint: str, task: dict) -> dict:
    ready = task_recovery.tx_enter_ready(tx, endpoint=endpoint, task=task, existing=record)
    return task_recovery.tx_enter_delivered(
        tx,
        record=ready,
        delivery_mode="continue_task_foreground",
    )


def _handle_continue_state(tx, record: dict, endpoint: str, task_id: str,
                           context_id: str, state: str, message: str = "",
                           task: dict = None) -> dict:
    if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
        return task_recovery.tx_enter_pending(
            tx,
            endpoint=endpoint,
            task_id=task_id,
            context_id=context_id,
            status_message=message,
            existing=record,
            probe_attempt=False,
        )
    if state == task_recovery.TASK_STATE_INPUT_REQUIRED:
        return task_recovery.tx_enter_input_required(
            tx,
            endpoint=endpoint,
            task=task or _task_from_stream_state(task_id, context_id, state, message),
            existing=record,
        )
    if state in task_recovery.TERMINAL_STATES:
        return _finish_continue_with_task(
            tx,
            record,
            endpoint,
            task or _task_from_stream_state(task_id, context_id, state, message),
        )
    if state in task_recovery.WORKING_STATES:
        return task_recovery.tx_enter_running(
            tx,
            endpoint=endpoint,
            task_id=task_id,
            context_id=context_id,
            state=state,
            existing=record,
            probe_attempt=False,
        )
    return record


def _close_continue_stream_if_still_running(tx, record: dict, endpoint: str,
                                            token: str, task_id: str,
                                            context_id: str,
                                            history_length: int = None) -> dict:
    if not record or record.get("activeState") != task_store.STATE_RUNNING:
        return record
    try:
        task = task_recovery.get_task(
            endpoint,
            token,
            task_id,
            history_length=0,
        )
        if task_recovery.task_state(task) in task_recovery.TERMINAL_STATES:
            task = task_recovery.get_task(
                endpoint,
                token,
                task_id,
                history_length=history_length,
            )
    except task_recovery.TaskNotFoundError:
        removed = task_recovery.tx_remove_task_not_found(tx, record)
        print(f"\n[提示] {removed['message']}")
        return removed
    except task_recovery.TaskRecoveryError as e:
        print(f"\n[提示] 流结束后确认任务状态失败，任务保留为 running，后续可 check_task: {e}")
        return record

    return _handle_continue_state(
        tx,
        record,
        endpoint,
        task_recovery.task_id_of(task) or task_id,
        task_recovery.context_id_of(task) or context_id,
        task_recovery.task_state(task),
        task_recovery.task_status_message(task),
        task=task,
    )


def do_continue_task(endpoint: str, token: str, agent_id: str, session_id: str,
                     task_id: str, message: str,
                     accepted_output_modes: str = None,
                     history_length: int = None,
                     auth_subscribe_idle_timeout_sec: int = AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
                     no_auth_followup: bool = False,
                     control_sink=None) -> None:
    if not task_id:
        print("错误: continue_task 需要 --task-id")
        sys.exit(1)
    if not message:
        print("错误: continue_task 需要从 stdin 读取非空 message")
        sys.exit(1)

    deferred_auth_events: list[dict] = []
    with task_recovery.continue_task_context(
        session_id=session_id,
        agent_id=agent_id,
        endpoint=endpoint,
        task_id=task_id,
        user_message=message,
    ) as ctx:
        if not ctx.ok:
            print(ctx.error)
            return
        msg = {
            "messageId": uuid.uuid4().hex,
            "taskId": ctx.task_id,
            "contextId": ctx.context_id,
            "role": "ROLE_USER",
            "parts": [{"text": message}],
        }
        params = {"message": msg}
        configuration = {}
        if accepted_output_modes:
            configuration["acceptedOutputModes"] = [m.strip() for m in accepted_output_modes.split(",")]
        if history_length is not None:
            configuration["historyLength"] = history_length
        if configuration:
            params["configuration"] = configuration

        record = ctx.record
        current_task_id = ctx.task_id
        current_context_id = ctx.context_id
        streamed_text_parts = []
        auth_message_parts = []
        emitted_auth_rounds = set()
        try:
            for event in rpc_stream(endpoint, token, "SendStreamingMessage", params):
                if task_recovery.is_task_not_found_error(event.get("error")):
                    task_recovery.tx_remove_task_not_found(ctx.tx, record)
                    print(task_recovery.format_task_not_found_cleanup(current_task_id))
                    return
                suppress_message_text = _should_suppress_final_message(
                    event,
                    "".join(streamed_text_parts),
                )
                dispatch = handle_stream_event(event, suppress_message_text=suppress_message_text)
                if dispatch["type"] == "error":
                    sys.exit(1)
                try:
                    current_task_id = _bind_stream_task_id(
                        current_task_id,
                        dispatch.get("task_id"),
                    )
                except StreamTaskBindingError:
                    print(f"\n[错误] {STREAM_TASK_ID_ERROR}")
                    sys.exit(1)
                if dispatch.get("context_id"):
                    current_context_id = dispatch.get("context_id")
                if dispatch["type"] == "artifact":
                    if dispatch.get("text"):
                        text = dispatch.get("text")
                        streamed_text_parts.append(text)
                        auth_message_parts.append(text)
                elif dispatch["type"] == "task":
                    task = dispatch["task"]
                    state = dispatch.get("state") or _task_state(task)
                    record = _handle_continue_state(
                        ctx.tx,
                        record,
                        endpoint,
                        current_task_id,
                        current_context_id,
                        state,
                        _task_status_message(task),
                        task=task,
                    )
                    if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                        hitl_round = (record or {}).get("hitlRound")
                        if hitl_round not in emitted_auth_rounds:
                            control_event = _task_control_event(record)
                            if control_event is not None:
                                deferred_auth_events.append(control_event)
                            emitted_auth_rounds.add(hitl_round)
                elif dispatch["type"] == "status":
                    state = dispatch.get("state")
                    if dispatch.get("agent_message"):
                        auth_message_parts.append(dispatch.get("agent_message"))
                    record = _handle_continue_state(
                        ctx.tx,
                        record,
                        endpoint,
                        current_task_id,
                        current_context_id,
                        state,
                        dispatch.get("agent_message") or "",
                    )
                    if state == task_recovery.TASK_STATE_AUTH_REQUIRED:
                        hitl_round = (record or {}).get("hitlRound")
                        if hitl_round not in emitted_auth_rounds:
                            control_event = _task_control_event(record)
                            if control_event is not None:
                                deferred_auth_events.append(control_event)
                            emitted_auth_rounds.add(hitl_round)
                elif dispatch["type"] == "message":
                    if dispatch.get("text"):
                        auth_message_parts.append(dispatch.get("text"))
        except KeyboardInterrupt:
            sys.stdout.write("\n[中断] 用户主动停止接收，任务保留为 running，后续可 check_task。\n")
            sys.stdout.flush()
            sys.exit(0)
        auth_message = "".join(auth_message_parts)
        record = _close_continue_stream_if_still_running(
            ctx.tx,
            record,
            endpoint,
            token,
            current_task_id,
            current_context_id,
            history_length=history_length,
        )
        print()
        if current_context_id:
            save_context_id(session_id=session_id, agent_id=agent_id, context_id=current_context_id)
    # continue_task_context owns the task lock for the full stream. Emit only
    # after leaving it so callbacks can independently verify the committed
    # record without trying to re-lock the same task in this process.
    for control_event in deferred_auth_events:
        _emit_control(control_sink, control_event)


# ============================================================
# 辅助函数
# ============================================================

def _resolve_context_id(session_id: str = None, agent_id: str = None) -> str:
    """
    自动从 session 缓存读取 context_id。

    逻辑：
    1. 有 session_id + agent_id → 从 ~/.aliyun_agenthub/{session_id}.json 读取
    2. 找到 → 返回 context_id（续接会话）
    3. 找不到或无 session_id → 返回 None（服务端创建新会话）
    """
    if session_id and agent_id:
        cached = load_context_id(session_id, agent_id)
        if cached:
            return cached
    return None


def _handle_task_response(task: dict, endpoint: str, agent_id: str = None, session_id: str = None):
    """处理 Task 类型响应"""
    context_id = task.get("contextId")
    if context_id:
        save_context_id(
            session_id=session_id,
            agent_id=agent_id,
            context_id=context_id,
        )
    print(format_task_result(task))


def _handle_message_response(message: dict, endpoint: str, agent_id: str = None, session_id: str = None):
    """处理 Message 类型响应"""
    context_id = message.get("contextId")
    if context_id:
        save_context_id(
            session_id=session_id,
            agent_id=agent_id,
            context_id=context_id,
        )
    print(format_message_result(message))


# ============================================================
# 主入口
# ============================================================

def main(argv=None, stdin=None) -> int:
    stdin = stdin or sys.stdin
    parser = argparse.ArgumentParser(
        description="A2A Operations Hub — A2A 操作的统一入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--operation", required=True,
                        choices=[
                            "get_agent_card", "send_message", "send_streaming_message",
                            "list_tasks", "check_task", "subscribe_task", "follow_task",
                            "cancel_task", "view_task", "continue_task",
                        ],
                        help="要执行的 A2A 操作")
    parser.add_argument("--task-id", default=None, help="任务 ID（check_task / subscribe_task / cancel_task / view_task / continue_task 必填）")
    parser.add_argument("--include-delivered", action="store_true", help="list_tasks 时包含 delivered 归档任务")
    parser.add_argument("--sweep-max-tasks", type=int, default=2, help="send 后置 sweep 最多检查的任务数")
    parser.add_argument("--sweep-deadline-ms", type=int, default=task_recovery.GET_TASK_SWEEP_DEADLINE_MS, help="send 后置 sweep 最大耗时（毫秒）")
    parser.add_argument("--no-sweep", action="store_true", help="跳过 send 后置 pending/running sweep")
    parser.add_argument(
        "--auth-subscribe-idle-timeout-sec",
        type=int,
        default=AUTH_SUBSCRIBE_IDLE_TIMEOUT_SEC,
        help="AuthRequired 后自动 SubscribeToTask 订阅的无进展超时秒数",
    )
    parser.add_argument("--no-auth-followup", action="store_true", help="跳过 AuthRequired 后自动 subscribe_task 请求")
    parser.add_argument("--session-id", default=None,
                        help=(
                            "会话 ID，用于按会话隔离 context 缓存（~/.aliyun_agenthub/{session_id}.json）。"
                            "识别为 qwencode 时脚本会自动从 ~/.qwen/debug/latest 解析、加 qwencode- 前缀并覆盖本参数；"
                            "识别为 codex 时脚本会自动读取 CODEX_THREAD_ID、加 codex- 前缀并覆盖本参数；"
                            "识别为 qoderwork 时需生成 32 位小写十六进制 SKILL_SESSION_ID，业务 ID 保持 qoderwork-<生成值>；"
                            "识别为 claudecode 时需由调用方显式传入 ${CLAUDE_CODE_SESSION_ID} 或 ${CLAUDE_SESSION_ID}，脚本会加 claudecode- 前缀；"
                            "未知/未来客户端使用 <client-name>-<生成值> 并保留客户端前缀；"
                            "为空时脚本以退出码 2 中断并给出引导提示。"
                        ))
    parser.add_argument("--accepted-output-modes", default=None, help="接受的输出类型（逗号分隔）")
    parser.add_argument("--history-length", type=int, default=None, help="返回历史消息最大数量")
    parser.add_argument("--return-immediately", action="store_true", help="非阻塞模式")
    parser.add_argument("--control-fd", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--rpc-path", default="/rpc", help=argparse.SUPPRESS)
    parser.add_argument("--follow-window-sec", type=int, default=FOLLOW_WINDOW_SEC, help=argparse.SUPPRESS)
    parser.add_argument("--follow-interval-sec", type=int, default=FOLLOW_INTERVAL_SEC, help=argparse.SUPPRESS)
    parser.add_argument("--endpoint", required=True,
                        help="A2A Server 地址（必填，由 SKILL.md 指定，脚本不持有任何 Agent 特定默认值）")
    parser.add_argument("--agent-id", required=True,
                        help="Skill Agent ID（必填，由 SKILL.md 指定，用于隔离会话缓存文件）")
    args = parser.parse_args(argv)
    if args.rpc_path != "/rpc":
        parser.error("仅支持 /rpc A2A JSON-RPC 路径")
    if not 0 < args.follow_window_sec <= FOLLOW_WINDOW_SEC:
        parser.error("follow window 必须在 1-180 秒之间")
    if not 0 < args.follow_interval_sec <= FOLLOW_INTERVAL_SEC:
        parser.error("follow interval 必须在 1-5 秒之间")
    try:
        args.agent_id = validate_agent_id(args.agent_id)
        endpoint = normalize_official_agenthub_endpoint(
            args.endpoint,
            agent_id=args.agent_id,
        )
    except ValueError as exc:
        sys.stderr.write(f"[错误] 不可信的 AgentHub 路由: {exc}\n")
        return 2
    control_sink = _control_writer(args.control_fd)
    # 预热客户端 Agent 识别缓存：识别结果不输出到 stdout，仅作为 HTTP header
    # (User-Agent) 的信息源，由 references/common.py 在每次构造 header 时读取。
    # 此处显式触发一次，确保识别（含 2s 版本探测）发生在明确的时机，而非首个
    # HTTP 请求构造时的隐式副作用。
    client_name, _client_version = detect_client()
    generated_session_id = _session_id_from_env()
    # ===== 会话 ID 解析（按客户端分发） =====
    # 策略：
    #   - qwencode: 无条件以 ~/.qwen/debug/latest 软链解析结果加 qwencode- 前缀后覆盖 args.session_id
    #              （软链是 qwen-code 运行期唯一真源，用户/SKILL 侧传入的值可能过期）；
    #              软链不可读 → fail-fast exit(2)。
    #   - codex: 无条件以 CODEX_THREAD_ID 解析结果加 codex- 前缀后覆盖 args.session_id
    #             （该环境变量是 Codex 当前 thread 的稳定 ID）；
    #             环境变量缺失或为空 → fail-fast exit(2)。
    #   - qoderwork: 属于客户端分配类，生成部分必须使用 32 位小写十六进制
    #                SKILL_SESSION_ID，完整业务 ID 保持 qoderwork-<生成值>，
    #                同一会话保持不变；
    #                缺失或格式非法 → fail-fast exit(2)。
    #   - claudecode: args.session_id 直接透传并幂等加 claudecode- 前缀；
    #                  为空或纯空白 → fail-fast exit(2)。
    #   - 未知/未来客户端: 属于客户端分配类，完整业务 ID 保留客户端前缀，
    #                    且最后的生成部分必须与 SKILL_SESSION_ID 一致；
    #                    为空或纯空白 → fail-fast exit(2)。
    # fail-fast 的动机：避免"静默接受空 session_id → context 缓存漂移 → 续接失效"。
    if client_name == "qwencode":
        qwen_sid = detect_qwen_session_id()
        if qwen_sid:
            args.session_id = _prefix_client_session_id(client_name, qwen_sid)
        else:
            _fail_missing_session_id(client_name, qwen_fallback_failed=True)
    elif client_name == "codex":
        codex_sid = detect_codex_session_id()
        if codex_sid:
            args.session_id = _prefix_client_session_id(client_name, codex_sid)
        else:
            _fail_missing_session_id(
                client_name,
                qwen_fallback_failed=False,
                codex_env_missing=True,
            )
    elif client_name == "qoderwork":
        args.session_id = _self_managed_session_id(
            args.session_id,
            generated_session_id,
            required_prefix="qoderwork",
        )
        if not args.session_id:
            _fail_missing_session_id(
                client_name,
                qwen_fallback_failed=False,
                qoderwork_invalid=True,
            )
    elif client_name == "claudecode":
        if not args.session_id or not args.session_id.strip():
            _fail_missing_session_id(client_name, qwen_fallback_failed=False)
        args.session_id = _prefix_client_session_id(client_name, args.session_id.strip())
    else:
        args.session_id = _self_managed_session_id(
            args.session_id,
            generated_session_id,
        )
        if not args.session_id:
            _fail_missing_session_id(client_name, qwen_fallback_failed=False)
    if args.operation in ("send_message", "send_streaming_message", "continue_task"):
        args.message = stdin.read()
    if args.operation in ("send_message", "send_streaming_message") and not args.message:
        print(f"错误: {args.operation} 需要从 stdin 读取非空 message")
        sys.exit(1)
    if args.operation in (
        "check_task", "subscribe_task", "follow_task", "cancel_task", "view_task", "continue_task"
    ) and not args.task_id:
        print(f"错误: {args.operation} 需要 --task-id")
        sys.exit(1)
    if args.operation == "continue_task" and not args.message:
        print("错误: continue_task 需要从 stdin 读取非空 message")
        sys.exit(1)
    # 获取 token（get_agent_card 不需要）
    token = None
    if args.operation not in ("get_agent_card", "list_tasks", "view_task"):
        token = acquire_token()
    # 分发到对应操作
    operation_handlers = {
        "get_agent_card": lambda: do_get_agent_card(endpoint, control_sink=control_sink),
        "send_message": lambda: do_send_message(
            endpoint, token, args.message,
            args.accepted_output_modes, args.history_length, args.return_immediately,
            agent_id=args.agent_id, session_id=args.session_id,
            sweep_max_tasks=args.sweep_max_tasks,
            sweep_deadline_ms=args.sweep_deadline_ms,
            no_sweep=args.no_sweep,
            auth_subscribe_idle_timeout_sec=args.auth_subscribe_idle_timeout_sec,
            no_auth_followup=args.no_auth_followup,
            control_sink=control_sink,
        ),
        "send_streaming_message": lambda: do_send_streaming_message(
            endpoint, token, args.message,
            args.accepted_output_modes, args.history_length,
            agent_id=args.agent_id, session_id=args.session_id,
            sweep_max_tasks=args.sweep_max_tasks,
            sweep_deadline_ms=args.sweep_deadline_ms,
            no_sweep=args.no_sweep,
            auth_subscribe_idle_timeout_sec=args.auth_subscribe_idle_timeout_sec,
            no_auth_followup=args.no_auth_followup,
            control_sink=control_sink,
        ),
        "list_tasks": lambda: do_list_tasks(
            agent_id=args.agent_id,
            session_id=args.session_id,
            include_delivered=args.include_delivered,
        ),
        "check_task": lambda: do_check_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
            history_length=args.history_length,
        ),
        "subscribe_task": lambda: do_subscribe_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
            idle_timeout_sec=args.auth_subscribe_idle_timeout_sec,
            history_length=args.history_length,
            control_sink=control_sink,
        ),
        "follow_task": lambda: do_follow_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
            window_sec=args.follow_window_sec,
            interval_sec=args.follow_interval_sec,
            control_sink=control_sink,
        ),
        "cancel_task": lambda: do_cancel_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
            history_length=args.history_length,
        ),
        "view_task": lambda: do_view_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
        ),
        "continue_task": lambda: do_continue_task(
            endpoint, token, args.agent_id, args.session_id,
            task_id=args.task_id,
            message=args.message,
            accepted_output_modes=args.accepted_output_modes,
            history_length=args.history_length,
            auth_subscribe_idle_timeout_sec=args.auth_subscribe_idle_timeout_sec,
            no_auth_followup=args.no_auth_followup,
            control_sink=control_sink,
        ),
    }
    op_func = operation_handlers.get(args.operation)
    if not op_func:
        print(f"错误: 未知操作 {args.operation}")
        sys.exit(1)
    op_func()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
