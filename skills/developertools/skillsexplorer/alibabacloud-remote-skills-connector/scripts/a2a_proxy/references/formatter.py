#!/usr/bin/env python3
"""
A2A Client — 输出格式化

将 A2A 响应数据转换为自然语言输出。
按 task_state 分类展示，处理 JSON-RPC 错误码映射。
"""

import json
import sys
from typing import Any, Optional


# ============================================================
# JSON-RPC 错误码 → 可读信息
# ============================================================

_RPC_ERROR_MESSAGES = {
    -32700: "JSON 解析失败",
    -32600: "无效请求（协议版本错误或缺少必要字段）",
    -32601: "方法不存在",
    -32602: "参数无效",
    -32603: "内部错误",
    -32001: "任务不存在",
    -32002: "任务不可取消（已完成或已终止）",
    -32003: "推送通知不受支持",
    -32004: "操作不受支持",
    -32005: "内容类型不受支持",
    -32006: "无效的智能体响应",
    -32007: "扩展智能体卡片未配置",
    -32008: "需要扩展支持",
    -32009: "协议版本不受支持",
}


# ============================================================
# Task 状态 → 输出行为
# ============================================================

_STATE_LABELS = {
    "TASK_STATE_UNSPECIFIED":      "未知",
    "TASK_STATE_SUBMITTED":        "已提交",
    "TASK_STATE_WORKING":          "处理中",
    "TASK_STATE_COMPLETED":        "已完成",
    "TASK_STATE_FAILED":           "失败",
    "TASK_STATE_CANCELED":         "已取消",
    "TASK_STATE_INPUT_REQUIRED":   "等待输入",
    "TASK_STATE_REJECTED":         "已拒绝",
    "TASK_STATE_AUTH_REQUIRED":    "需要认证",
}

# 终态：任务生命周期结束
_TERMINAL_STATES = frozenset({
    "TASK_STATE_COMPLETED", "TASK_STATE_FAILED",
    "TASK_STATE_CANCELED", "TASK_STATE_REJECTED",
})

# 中断态：需要用户干预才能继续
_INTERRUPT_STATES = frozenset({
    "TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED",
})


def _is_terminal(state: str) -> bool:
    return state in _TERMINAL_STATES


def _is_interrupt(state: str) -> bool:
    return state in _INTERRUPT_STATES


# ============================================================
# 核心格式化函数
# ============================================================

def format_rpc_error(error: dict) -> str:
    """
    格式化 JSON-RPC 错误对象。

    Args:
        error: {"code": -32001, "message": "...", "data": ...}

    Returns:
        可读的错误信息字符串
    """
    code = error.get("code", 0)
    message = error.get("message", "未知错误")
    readable = _RPC_ERROR_MESSAGES.get(code)
    parts = []
    if readable:
        parts.append(readable)
    else:
        parts.append(message)
    parts.append(f"(错误码: {code})")
    data = error.get("data")
    if data:
        parts.append(f"\n  详情: {data}")
    return " ".join(parts)


def extract_text_from_artifacts(artifacts: list) -> str:
    """
    从 artifacts 列表中提取所有文本内容。

    Args:
        artifacts: task.artifacts 数组

    Returns:
        拼接后的文本
    """
    texts = []
    for artifact in artifacts or []:
        parts = artifact.get("parts", []) or artifact.get("part", {}).get("parts", [])
        for part in parts:
            text = part.get("text")
            if text:
                texts.append(text)
    return "\n".join(texts)


def format_task_result(task: dict, agent_name: Optional[str] = None) -> str:
    """
    格式化一个完整的 task 响应为自然语言。

    根据 task 的状态输出不同的内容，并追加 contextId 续接提示。

    Args:
        task:       task 对象 {"id", "status", "contextId", "artifacts", ...}
        agent_name: Agent 名称（可选，用于续接提示展示）

    Returns:
        格式化后的字符串
    """
    status     = task.get("status", {})
    state      = status.get("state", "UNKNOWN")
    label      = _STATE_LABELS.get(state, state)
    # 从 status.message.parts 拼接文本，供多个分支复用
    msg_text = "".join(
        part.get("text", "")
        for part in status.get("message", {}).get("parts", [])
    )
    if state == "TASK_STATE_COMPLETED":
        artifacts = task.get("artifacts", [])
        text      = extract_text_from_artifacts(artifacts)
        result    = text or f"[{label}] 任务完成，但未返回文本内容。"
    elif state == "TASK_STATE_INPUT_REQUIRED":
        result = (
            f"Agent 需要更多信息: {msg_text}"
            if msg_text else
            "Agent 需要更多信息（未提供具体提示）。"
        )
    elif state == "TASK_STATE_AUTH_REQUIRED":
        result = (
            f"Agent 需要额外的认证才能继续: {msg_text}"
            if msg_text else
            "Agent 需要额外的认证才能继续。"
        )
    elif state == "TASK_STATE_FAILED":
        result = f"[{label}] {msg_text}" if msg_text else f"[{label}] 任务执行失败，未返回错误详情。"
    elif state == "TASK_STATE_CANCELED":
        result = f"[{label}] 任务已取消。"
    elif state == "TASK_STATE_REJECTED":
        result = f"[{label}] {msg_text}" if msg_text else f"[{label}] 智能体拒绝执行该任务。"
    else:
        result = f"[{label}] 任务状态: {state}"
    return result


def format_message_result(message: dict, agent_name: Optional[str] = None) -> str:
    """
    格式化 Message 响应为自然语言。

    用于同步响应中收到 result.message（仅消息流模式）的情况。

    Args:
        message:    Message 对象 {"role", "parts", "contextId", "taskId", ...}
        agent_name: Agent 名称（可选）

    Returns:
        格式化后的字符串
    """
    texts = [
        part.get("text")
        for part in message.get("parts", [])
        if part.get("text")
    ]
    return "\n".join(texts) if texts else "[智能体回复] 未返回文本内容。"


def format_rpc_response(response: dict, agent_name: Optional[str] = None) -> str:
    """
    格式化一个完整的 JSON-RPC 响应。

    自动区分 result（成功）和 error（失败）。
    同步响应中只可能收到 result.task 或 result.message。

    Args:
        response:  JSON-RPC 响应体 {"jsonrpc", "id", "result"|"error"}
        agent_name: Agent 名称（可选，用于续接提示展示）

    Returns:
        格式化后的字符串
    """
    # 错误响应
    error = response.get("error")
    if error:
        return format_rpc_error(error)
    # 成功响应
    result = response.get("result")
    if result is None:
        return "请求成功，但响应为空。"
    if not isinstance(result, dict):
        return json.dumps(result, indent=2, ensure_ascii=False)
    # result 中包含 task 对象
    task = result.get("task")
    if task:
        return format_task_result(task, agent_name=agent_name)
    # result 中包含 message 对象（仅消息流模式）
    message = result.get("message")
    if message:
        return format_message_result(message, agent_name=agent_name)
    # result 是其他结构（如 ListTasks、PushNotificationConfig 等），直接格式化
    return json.dumps(result, indent=2, ensure_ascii=False)


# ============================================================
# 流式输出辅助
# ============================================================

def print_streaming_text(text: str) -> None:
    """
    打字机效果输出文本片段。
    直接写入 stdout 并 flush，不换行。
    """
    sys.stdout.write(text)
    sys.stdout.flush()


def print_streaming_status(state: str) -> None:
    """
    输出流式事件中的状态变化提示。

    设计：流式场景下字符会实时打字机式输出，WORKING 等中间过渡态
    没有信息价值且会在多个 statusUpdate 事件中重复出现，因此完全静默。
    仅在以下情况输出标签：
      - SUBMITTED：请求送达服务端的视觉确认（仅出现一次，独占一行）
      - 终态（COMPLETED/FAILED/CANCELED/REJECTED）：触发后续动作判断
      - 中断态（INPUT_REQUIRED/AUTH_REQUIRED）：触发交互续接
    """
    label = _STATE_LABELS.get(state, state)
    if state == "TASK_STATE_SUBMITTED":
        # 独占一行，避免与后续 artifact 文本粘连
        sys.stdout.write(f"[{label}]\n")
        sys.stdout.flush()
    elif state == "TASK_STATE_WORKING":
        # 中间过渡态完全静默：流式场景下用户能看到字符流出，无需额外标签
        return
    elif state == "TASK_STATE_COMPLETED":
        # 完成时换行
        sys.stdout.write(f"\n[{label}]\n")
        sys.stdout.flush()
    elif state == "TASK_STATE_INPUT_REQUIRED":
        sys.stdout.write(f"\n[{label}] Agent 需要更多信息，请继续输入。\n")
        sys.stdout.flush()
    elif state == "TASK_STATE_AUTH_REQUIRED":
        sys.stdout.write(
            f"\n[{label}] 远端任务需要审批，当前响应流按预期结束。\n"
        )
        sys.stdout.flush()
    else:
        # FAILED / CANCELED / REJECTED 等
        sys.stdout.write(f"\n[{label}]\n")
        sys.stdout.flush()


def _task_id_from_payload(payload: dict) -> Optional[str]:
    """从 A2A 事件载荷中提取 taskId，兼容 task.id 与事件 taskId。"""
    return payload.get("taskId") or payload.get("id")


def _context_id_from_payload(payload: dict) -> Optional[str]:
    """从 A2A 事件载荷中提取 contextId。"""
    return payload.get("contextId")


# ============================================================
# SSE 事件调度
# ============================================================

def handle_stream_event(event: dict, suppress_message_text: bool = False) -> dict:
    """
    处理单个 SSE 流式事件，自动分发到对应的输出逻辑。

    三种事件类型：
      1. artifactUpdate → 提取文本，打字机实时输出
      2. statusUpdate   → 状态变化提示
      3. task           → 首个事件，包含完整 task 对象（含 SUBMITTED 状态）

    心跳包已在 common.rpc_stream 中过滤，不会到达此函数。

    Args:
        event: 单个 SSE data 解析后的 JSON-RPC 响应信封
               {"jsonrpc":"2.0", "id":..., "result":{...}} 或 {"error":{...}}
        suppress_message_text: 为 True 时，message 事件仍返回文本，但不打印文本。

    Returns:
        dict 描述该事件的类型和关键数据：
          type="error"    → {"type","error"}
          type="artifact" → {"type","text","last_chunk","task_id","context_id"}
          type="status"   → {"type","state","agent_message","task_id","context_id"}
          type="task"     → {"type","task","state","task_id","context_id"}
          type="message"  → {"type","text","task_id","context_id"}
          type="unknown"  → {"type"}
    """
    # JSON-RPC 错误
    error = event.get("error")
    if error:
        print(format_rpc_error(error))
        return {"type": "error", "error": error}
    result = event.get("result", {})
    # oneOf 校验：StreamResponse 必须恰好包含 task/message/statusUpdate/artifactUpdate 之一
    oneof_keys = [k for k in ("task", "message", "statusUpdate", "artifactUpdate") if k in result]
    if len(oneof_keys) > 1:
        print(f"\n[警告] StreamResponse 违反 oneOf 约束: 同时包含 {oneof_keys}", file=sys.stderr)
    # artifactUpdate → 打字机输出
    artifact = result.get("artifactUpdate")
    if artifact:
        parts = artifact.get("artifact", {}).get("parts", [])
        text = ""
        for p in parts:
            if t := p.get("text", ""):
                text += t
                print_streaming_text(t)
        return {
            "type":       "artifact",
            "text":       text,
            "last_chunk": artifact.get("lastChunk", False),
            "task_id":    _task_id_from_payload(artifact),
            "context_id": _context_id_from_payload(artifact),
        }
    # statusUpdate → 状态提示
    status_update = result.get("statusUpdate")
    if status_update:
        status = status_update.get("status", {})
        state  = status.get("state", "")
        print_streaming_status(state)
        agent_message = None
        if state in ("TASK_STATE_INPUT_REQUIRED", "TASK_STATE_AUTH_REQUIRED"):
            msg_texts = [
                t for p in status.get("message", {}).get("parts", [])
                if (t := p.get("text"))
            ]
            if msg_texts:
                agent_message = "".join(msg_texts)
                print_streaming_text(f" {agent_message}\n")
        return {
            "type":          "status",
            "state":         state,
            "agent_message": agent_message,
            "task_id":       _task_id_from_payload(status_update),
            "context_id":    _context_id_from_payload(status_update),
        }
    # task 对象（通常是首个事件，包含 SUBMITTED 状态）
    task = result.get("task")
    if task:
        state = task.get("status", {}).get("state", "")
        print_streaming_status(state)
        return {
            "type":       "task",
            "task":       task,
            "state":      state,
            "task_id":    _task_id_from_payload(task),
            "context_id": _context_id_from_payload(task),
        }
    # message 对象（仅消息流模式，单个 Message 后流关闭）
    message = result.get("message")
    if message:
        texts = [
            t for p in message.get("parts", [])
            if (t := p.get("text"))
        ]
        text = "".join(texts)
        if text and not suppress_message_text:
            print(text)
        return {
            "type":       "message",
            "text":       text,
            "task_id":    _task_id_from_payload(message),
            "context_id": message.get("contextId"),
        }
    return {"type": "unknown"}


def format_task_list(records: list) -> str:
    """格式化本地 task 队列列表。"""
    if not records:
        return "当前 session 下没有本地异步任务。"
    lines = []
    for record in records:
        task_id = record.get("taskId", "?")
        state = record.get("activeState") or record.get("archiveState") or "unknown"
        seen = record.get("terminalState") or record.get("lastSeenState") or state
        updated = record.get("updatedAt", "")
        extra = ""
        if state == "input_required" and record.get("prompt"):
            extra = f" - {record.get('prompt')}"
        elif state == "ready" and record.get("displayTitle"):
            extra = f" - {record.get('displayTitle')}"
        updated_suffix = f" {updated}" if updated else ""
        lines.append(f"- {task_id}: {state} ({seen}){updated_suffix}{extra}")
    return "\n".join(lines)


def format_agent_card(card: dict) -> str:
    """
    格式化 Agent Card 为可读文本。

    Args:
        card: Agent Card JSON 对象

    Returns:
        格式化后的字符串
    """
    lines = []
    name = card.get("name", "未知 Agent")
    description = card.get("description", "")
    lines.append(f"Agent: {name}")
    if description:
        lines.append(f"简介: {description}")
    # 能力
    caps = card.get("capabilities", {})
    if caps:
        cap_items = []
        if caps.get("extendedAgentCard"):
            cap_items.append("扩展卡片")
        if caps.get("pushNotifications"):
            cap_items.append("推送通知")
        if caps.get("streaming"):
            cap_items.append("流式响应")
        if cap_items:
            lines.append(f"能力: {', '.join(cap_items)}")
    # 技能
    skills = card.get("skills", [])
    if skills:
        lines.append(f"技能 ({len(skills)}):")
        for skill in skills:
            skill_name = skill.get("name", "?")
            skill_desc = skill.get("description", "")
            if skill_desc:
                lines.append(f"  - {skill_name}: {skill_desc}")
            else:
                lines.append(f"  - {skill_name}")
    # 支持的接口
    interfaces = card.get("supportedInterfaces", [])
    if interfaces:
        iface_descs = []
        for iface in interfaces:
            if isinstance(iface, dict):
                binding_raw = iface.get("protocolBinding", "?")
                url = iface.get("url", "")
                ver = iface.get("protocolVersion", "")
                # protocolBinding="JSONRPC" 是 A2A 规范定义的枚举值，
                # 实际承载的传输协议是 JSON-RPC 2.0（固定，不会随 Agent Card 变化）；
                # 其他 binding 值按原值展示以保留扩展性。
                if binding_raw == "JSONRPC":
                    desc = "JSON-RPC 2.0"
                else:
                    desc = binding_raw
                if ver:
                    # ver 是 A2A 应用层协议版本（protocolVersion 字段），
                    # 与上面的 JSON-RPC 2.0 是不同维度的版本号；
                    # 显式中文标注以避免被客户端 Agent 误读为 JSON-RPC 版本。
                    desc += f" (A2A 协议版本 {ver})"
                if url:
                    desc += f" ({url})"
                iface_descs.append(desc)
            else:
                iface_descs.append(str(iface))
        lines.append(f"接口: {', '.join(iface_descs)}")
    # 输入/输出模式
    input_modes = card.get("defaultInputModes", [])
    if input_modes:
        lines.append(f"输入模式: {', '.join(input_modes)}")
    output_modes = card.get("defaultOutputModes", [])
    if output_modes:
        lines.append(f"输出模式: {', '.join(output_modes)}")
    return "\n".join(lines)
