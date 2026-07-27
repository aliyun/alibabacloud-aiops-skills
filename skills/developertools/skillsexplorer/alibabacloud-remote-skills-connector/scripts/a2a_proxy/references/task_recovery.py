#!/usr/bin/env python3
"""
A2A HITL task recovery orchestration.

Only tasks that have observed TASK_STATE_AUTH_REQUIRED enter this recovery flow.
"""

import contextlib
import shlex
import time
from typing import Callable, Iterator, Optional

from .common import rpc_request
from .formatter import extract_text_from_artifacts, format_rpc_error, format_task_result
from .http_security import normalize_official_agenthub_endpoint
from . import task_store


TASK_STATE_SUBMITTED = "TASK_STATE_SUBMITTED"
TASK_STATE_WORKING = "TASK_STATE_WORKING"
TASK_STATE_COMPLETED = "TASK_STATE_COMPLETED"
TASK_STATE_FAILED = "TASK_STATE_FAILED"
TASK_STATE_CANCELED = "TASK_STATE_CANCELED"
TASK_STATE_REJECTED = "TASK_STATE_REJECTED"
TASK_STATE_INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
TASK_STATE_AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED"

TERMINAL_STATES = frozenset({
    TASK_STATE_COMPLETED,
    TASK_STATE_FAILED,
    TASK_STATE_CANCELED,
    TASK_STATE_REJECTED,
})
WORKING_STATES = frozenset({TASK_STATE_SUBMITTED, TASK_STATE_WORKING})
RECOVERY_ORIGIN_AUTH = "auth_required"
TASK_LOST_OR_EXPIRED = "TASK_LOST_OR_EXPIRED"
TASK_NOT_FOUND_REASON = "TASK_NOT_FOUND"

AUTH_BACKOFF = (3, 6, 12, 24, 48, 96, 192, 300, 600, 1200, 2400, 3600)
RUNNING_BACKOFF = (30, 60, 300, 600)
NETWORK_BACKOFF = (30, 60, 300, 600)
CANCEL_TASK_TIMEOUT = 10
GET_TASK_TIMEOUT = 30.0
GET_TASK_SWEEP_DEADLINE_MS = 30000
AUTH_SUBSCRIBE_RECORD_FIELDS = (
    "authSubscribeAttempted",
    "authSubscribeAttemptedRound",
    "authSubscribeStartedAt",
    "authSubscribeEndedAt",
    "authSubscribeEndReason",
    "authSubscribeIdleTimeoutSec",
)


class TaskRecoveryError(Exception):
    pass


class TaskNotFoundError(TaskRecoveryError):
    pass


def _delay(sequence, attempts: int) -> int:
    if attempts < 0:
        attempts = 0
    return sequence[min(attempts, len(sequence) - 1)]


def task_state(task: dict) -> str:
    return (task.get("status") or {}).get("state", "")


def task_status_message(task: dict) -> str:
    parts = ((task.get("status") or {}).get("message") or {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts if part.get("text"))


def task_id_of(task: dict) -> Optional[str]:
    return task.get("id") or task.get("taskId")


def context_id_of(task: dict) -> Optional[str]:
    return task.get("contextId")


def extract_input_required_prompt(task: dict) -> str:
    return task_status_message(task) or "该任务需要补充输入。"


def is_task_not_found_error(error: object) -> bool:
    if not isinstance(error, dict):
        return False
    if error.get("code") == -32001:
        return True
    data = error.get("data")
    entries = data if isinstance(data, list) else [data]
    return any(
        isinstance(item, dict) and item.get("reason") == TASK_NOT_FOUND_REASON
        for item in entries
    )


def get_task(endpoint: str, token: str, task_id: str,
             history_length: Optional[int] = 0, timeout: float = GET_TASK_TIMEOUT) -> dict:
    params = {"id": task_id}
    if history_length is not None:
        params["historyLength"] = history_length
    response = rpc_request(
        endpoint,
        token,
        "GetTask",
        params,
        timeout=timeout,
    )
    error = response.get("error")
    if error:
        if is_task_not_found_error(error):
            raise TaskNotFoundError(error.get("message", "Task not found"))
        raise TaskRecoveryError(error.get("message", "GetTask failed"))
    result = response.get("result")
    if isinstance(result, dict) and "task" in result:
        result = result["task"]
    if not isinstance(result, dict) or not (result.get("id") or result.get("taskId")):
        raise TaskRecoveryError("GetTask 响应中未包含 Task")
    if task_id_of(result) != task_id:
        raise TaskRecoveryError("GetTask 响应 taskId 与请求 taskId 不匹配")
    return result


def _common_record(existing: Optional[dict], *, endpoint: str, task_id: str,
                   context_id: Optional[str], original_message: Optional[str] = None) -> dict:
    now = task_store.now_iso()
    existing = existing or {}
    record = {
        "schemaVersion": 1,
        "recoveryOrigin": RECOVERY_ORIGIN_AUTH,
        "taskId": task_id,
        "contextId": context_id or existing.get("contextId"),
        "endpoint": endpoint or existing.get("endpoint", ""),
        "createdAt": existing.get("createdAt") or now,
        "updatedAt": now,
        "hitlRound": existing.get("hitlRound", 0) or 0,
    }
    if existing.get("lastStatusMessage"):
        record["lastStatusMessage"] = existing.get("lastStatusMessage")
    for field in AUTH_SUBSCRIBE_RECORD_FIELDS:
        if field in existing:
            record[field] = existing.get(field)
    return record


def _next_auth_round(existing: Optional[dict], probe_attempt: bool) -> int:
    if not existing:
        return 1
    # Repeated GetTask probes that still see AUTH_REQUIRED are the same approval round;
    # only leaving pending and later re-entering AUTH_REQUIRED starts a new HITL round.
    if probe_attempt and existing.get("activeState") == task_store.STATE_PENDING:
        return existing.get("hitlRound", 1) or 1
    if existing.get("lastSeenState") == TASK_STATE_AUTH_REQUIRED and existing.get("activeState") == task_store.STATE_PENDING:
        return existing.get("hitlRound", 1) or 1
    return (existing.get("hitlRound", 0) or 0) + 1


def tx_enter_pending(tx: task_store.TaskTransaction, *, endpoint: str,
                     task_id: str, context_id: Optional[str],
                     status_message: str = "", original_message: Optional[str] = None,
                     existing: Optional[dict] = None, probe_attempt: bool = False) -> dict:
    existing = existing if existing is not None else tx.normalize()[1]
    new_round = _next_auth_round(existing, probe_attempt)
    same_round = existing and new_round == (existing.get("hitlRound") or 0)
    attempts = (existing.get("attempts", 0) + 1) if (probe_attempt and same_round) else 0
    interval = _delay(AUTH_BACKOFF, attempts)
    record = _common_record(
        existing,
        endpoint=endpoint,
        task_id=task_id,
        context_id=context_id,
        original_message=original_message,
    )
    record.update({
        "hitlRound": new_round,
        "lastSeenState": TASK_STATE_AUTH_REQUIRED,
        "lastStatusMessage": status_message or (existing or {}).get("lastStatusMessage", ""),
        "approvalState": "pending",
        "lastProbeAt": task_store.now_iso() if probe_attempt else (existing or {}).get("lastProbeAt"),
        "nextProbeAt": task_store.add_seconds_iso(interval),
        "probeIntervalSec": interval,
        "attempts": attempts,
    })
    if not same_round:
        for field in AUTH_SUBSCRIBE_RECORD_FIELDS:
            record.pop(field, None)
    return tx.enter(task_store.STATE_PENDING, record)


def tx_enter_running(tx: task_store.TaskTransaction, *, endpoint: str,
                     task_id: str, context_id: Optional[str],
                     state: str = TASK_STATE_WORKING,
                     original_message: Optional[str] = None,
                     submitted_message: Optional[str] = None,
                     existing: Optional[dict] = None, probe_attempt: bool = False) -> dict:
    existing = existing if existing is not None else tx.normalize()[1]
    attempts = (existing.get("attempts", 0) + 1) if (probe_attempt and existing) else 0
    interval = _delay(RUNNING_BACKOFF, attempts)
    record = _common_record(
        existing,
        endpoint=endpoint,
        task_id=task_id,
        context_id=context_id,
        original_message=original_message,
    )
    record.update({
        "hitlRound": record.get("hitlRound") or 1,
        "lastSeenState": state,
        "startedAt": (existing or {}).get("startedAt") or task_store.now_iso(),
        "lastProbeAt": task_store.now_iso() if probe_attempt else (existing or {}).get("lastProbeAt"),
        "nextProbeAt": task_store.add_seconds_iso(interval),
        "probeIntervalSec": interval,
        "attempts": attempts,
    })
    return tx.enter(task_store.STATE_RUNNING, record)


def tx_enter_input_required(tx: task_store.TaskTransaction, *, endpoint: str,
                            task: dict, existing: Optional[dict] = None) -> dict:
    existing = existing if existing is not None else tx.normalize()[1]
    task_id = task_id_of(task) or tx.task_id
    record = _common_record(
        existing,
        endpoint=endpoint,
        task_id=task_id,
        context_id=context_id_of(task),
    )
    record.update({
        "hitlRound": record.get("hitlRound") or 1,
        "lastSeenState": TASK_STATE_INPUT_REQUIRED,
        "prompt": extract_input_required_prompt(task),
        "task": task,
    })
    return tx.enter(task_store.STATE_INPUT_REQUIRED, record)


def tx_enter_ready(tx: task_store.TaskTransaction, *, endpoint: str, task: dict,
                   existing: Optional[dict] = None,
                   terminal_state: Optional[str] = None) -> dict:
    existing = existing if existing is not None else tx.normalize()[1]
    state = terminal_state or task_state(task) or TASK_LOST_OR_EXPIRED
    task_id = task_id_of(task) or tx.task_id
    record = _common_record(
        existing,
        endpoint=endpoint,
        task_id=task_id,
        context_id=context_id_of(task),
    )
    record.update({
        "hitlRound": record.get("hitlRound") or 1,
        "lastSeenState": state,
        "terminalState": state,
        "readyAt": task_store.now_iso(),
        "displayTitle": "此前审批任务已完成" if state == TASK_STATE_COMPLETED else "此前审批任务已结束",
        "task": task,
    })
    return tx.enter(task_store.STATE_READY, record)


def tx_enter_delivered(tx: task_store.TaskTransaction, *, record: dict,
                       delivery_mode: str = "view_task") -> dict:
    delivered = dict(record)
    delivered["deliveryMode"] = delivery_mode
    delivered["deliveredAt"] = task_store.now_iso()
    return tx.enter(task_store.STATE_DELIVERED, delivered)


def record_auth_required_task(session_id: str, agent_id: str, endpoint: str,
                              task_id: str, context_id: Optional[str],
                              status_message: str = "",
                              original_message: Optional[str] = None) -> dict:
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, existing = tx.normalize()
        return tx_enter_pending(
            tx,
            endpoint=endpoint,
            task_id=task_id,
            context_id=context_id,
            status_message=status_message,
            original_message=original_message,
            existing=existing,
            probe_attempt=False,
        )


def tx_update_probe_error(tx: task_store.TaskTransaction, record: dict, error_message: str = "") -> dict:
    state = record.get("activeState")
    attempts = record.get("attempts", 0) + 1
    interval = _delay(NETWORK_BACKOFF, attempts)
    updated = dict(record)
    updated.update({
        "attempts": attempts,
        "probeIntervalSec": interval,
        "lastProbeAt": task_store.now_iso(),
        "nextProbeAt": task_store.add_seconds_iso(interval),
    })
    if error_message:
        updated["lastProbeError"] = error_message
    return tx.enter(state, updated)


def format_task_not_found_cleanup(task_id: str) -> str:
    return f"任务 {task_id} 在远端不存在，可能已过期或提供了错误的 taskId；已清理本地记录。"


def tx_remove_task_not_found(tx: task_store.TaskTransaction, record: Optional[dict] = None) -> dict:
    existing = record or {}
    message = format_task_not_found_cleanup(tx.task_id)
    tx.remove_all()
    return {
        "schemaVersion": 1,
        "taskId": tx.task_id,
        "contextId": existing.get("contextId"),
        "endpoint": existing.get("endpoint", ""),
        "terminalState": TASK_LOST_OR_EXPIRED,
        "reason": TASK_NOT_FOUND_REASON,
        "removed": True,
        "message": message,
        "updatedAt": task_store.now_iso(),
    }


def _task_from_cancel_response(response: dict) -> Optional[dict]:
    result = response.get("result")
    if isinstance(result, dict):
        task = result.get("task")
        if isinstance(task, dict):
            return task
        if result.get("status") and (result.get("id") or result.get("taskId")):
            return result
    return None


def _cancel_success_message(task_id: str) -> str:
    return f"任务 {task_id} 已取消；已清理本地记录。"


def _cancel_failed_keep_local_message(task_id: str, error: dict) -> str:
    return f"取消任务 {task_id} 失败: {format_rpc_error(error)}；本地记录已保留，可继续使用 check_task 查看进展。"


def _cancel_keep_local_message(task_id: str, reason: str) -> str:
    return f"取消任务 {task_id} 未清理本地记录: {reason}；本地记录已保留，可继续使用 check_task 查看进展。"


def _normalize_endpoint(endpoint: Optional[str]) -> str:
    return normalize_official_agenthub_endpoint(endpoint or "").rstrip("/")


def _endpoint_matches(record: dict, endpoint: str) -> bool:
    recorded = record.get("endpoint")
    if not recorded or not endpoint:
        return True
    return _normalize_endpoint(recorded) == _normalize_endpoint(endpoint)


def _validate_cancel_task_id(task: dict, expected_task_id: str) -> Optional[str]:
    returned_task_id = task_id_of(task)
    if not returned_task_id:
        return "远端响应未包含 taskId"
    if returned_task_id != expected_task_id:
        return f"远端返回 taskId 不匹配，期望 {expected_task_id}，实际 {returned_task_id}"
    return None


def _enter_ready_from_cancel_terminal(
    tx: task_store.TaskTransaction,
    *,
    endpoint: str,
    token: str,
    task: dict,
    existing: dict,
    history_length: Optional[int],
) -> tuple[Optional[dict], Optional[str]]:
    try:
        final_task = get_task(endpoint, token, tx.task_id, history_length=history_length)
    except TaskRecoveryError as e:
        return None, f"远端任务已结束，但获取完整结果失败: {e}"
    mismatch = _validate_cancel_task_id(final_task, tx.task_id)
    if mismatch:
        return None, mismatch
    updated = transition_from_task(
        tx,
        endpoint=endpoint,
        task=task,
        final_task=final_task,
        existing=existing,
        probe_attempt=True,
    )
    return updated, None


def transition_from_task(tx: task_store.TaskTransaction, *, endpoint: str,
                         task: dict, existing: Optional[dict],
                         final_task: Optional[dict] = None,
                         probe_attempt: bool = True) -> dict:
    state = task_state(task)
    context_id = context_id_of(task) or (existing or {}).get("contextId")
    if state == TASK_STATE_AUTH_REQUIRED:
        return tx_enter_pending(
            tx,
            endpoint=endpoint,
            task_id=task_id_of(task) or tx.task_id,
            context_id=context_id,
            status_message=task_status_message(task),
            existing=existing,
            probe_attempt=probe_attempt,
        )
    if state == TASK_STATE_INPUT_REQUIRED:
        return tx_enter_input_required(tx, endpoint=endpoint, task=task, existing=existing)
    if state in WORKING_STATES:
        return tx_enter_running(
            tx,
            endpoint=endpoint,
            task_id=task_id_of(task) or tx.task_id,
            context_id=context_id,
            state=state,
            existing=existing,
            probe_attempt=probe_attempt,
        )
    if state in TERMINAL_STATES:
        return tx_enter_ready(tx, endpoint=endpoint, task=final_task or task, existing=existing)
    return tx_enter_running(
        tx,
        endpoint=endpoint,
        task_id=task_id_of(task) or tx.task_id,
        context_id=context_id,
        state=state or TASK_STATE_WORKING,
        existing=existing,
        probe_attempt=probe_attempt,
    )


def sweep_recoverable_tasks(
    endpoint: str,
    token: str,
    session_id: str,
    agent_id: str,
    max_tasks: int = 2,
    deadline_ms: int = GET_TASK_SWEEP_DEADLINE_MS,
    final_history_length: Optional[int] = None,
) -> list:
    changed = []
    with task_store.scan_lock(session_id, agent_id) as acquired:
        if not acquired:
            return changed
        start = time.monotonic()
        due = task_store.due_records(
            session_id,
            agent_id,
            states=(task_store.STATE_PENDING, task_store.STATE_RUNNING),
        )
        for record in due[:max_tasks]:
            if (time.monotonic() - start) * 1000 >= deadline_ms:
                break
            task_id = record.get("taskId")
            if not task_id:
                continue
            with task_store.task_transaction(session_id, agent_id, task_id) as tx:
                _current_state, current = tx.normalize()
                if not current or current.get("activeState") not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
                    continue
                remaining = max(0.2, (deadline_ms - ((time.monotonic() - start) * 1000)) / 1000)
                try:
                    task = get_task(endpoint, token, task_id, history_length=0, timeout=remaining)
                    final_task = None
                    if task_state(task) in TERMINAL_STATES:
                        remaining = max(0.2, (deadline_ms - ((time.monotonic() - start) * 1000)) / 1000)
                        final_task = get_task(
                            endpoint,
                            token,
                            task_id,
                            history_length=final_history_length,
                            timeout=max(0.2, remaining),
                        )
                    changed.append(transition_from_task(
                        tx,
                        endpoint=endpoint,
                        task=task,
                        final_task=final_task,
                        existing=current,
                        probe_attempt=True,
                    ))
                except TaskNotFoundError:
                    changed.append(tx_remove_task_not_found(tx, current))
                except TaskRecoveryError:
                    changed.append(tx_update_probe_error(tx, current))
    return changed


def _command(name: str, task_id: str) -> str:
    quoted = shlex.quote(task_id)
    return f"{name} --task-id {quoted}"


def format_ready_task_result(record: dict) -> str:
    state = record.get("terminalState")
    if state == TASK_LOST_OR_EXPIRED:
        return format_task_not_found_cleanup(record.get("taskId", ""))
    task = record.get("task") or {}
    if state == TASK_STATE_COMPLETED:
        text = extract_text_from_artifacts(task.get("artifacts", []))
        return text or "[已完成] 任务完成，但未返回文本内容。"
    return format_task_result(task) if task else f"[{state}] 任务已结束。"


def format_task_status_record(record: dict) -> str:
    active = record.get("activeState") or record.get("archiveState")
    task_id = record.get("taskId", "")
    if active == task_store.STATE_PENDING:
        suffix = " 最近一次探测失败，后续会继续重试。" if record.get("lastProbeError") else ""
        return f"任务 {task_id} 正在等待审批或处理中。{suffix}"
    if active == task_store.STATE_INPUT_REQUIRED:
        prompt = record.get("prompt") or "该任务需要补充输入。"
        return f"任务 {task_id} 需要补充输入: {prompt}"
    if active == task_store.STATE_RUNNING:
        suffix = " 最近一次探测失败，后续会继续重试。" if record.get("lastProbeError") else ""
        return f"任务 {task_id} 已继续提交，正在处理中。{suffix}"
    if active == task_store.STATE_READY:
        if record.get("terminalState") == TASK_LOST_OR_EXPIRED:
            return format_task_not_found_cleanup(task_id)
        return f"任务 {task_id} 已有结果可查看，请使用 view_task。"
    if active == task_store.STATE_DELIVERED:
        if record.get("terminalState") == TASK_LOST_OR_EXPIRED:
            return format_task_not_found_cleanup(task_id)
        return f"任务 {task_id} 的结果已经查看过。"
    return f"当前 session 下没有找到任务 {task_id}。"


def _auth_followup_timeout_message(task_id: str, window_sec: int) -> str:
    return (
        f"任务 {task_id} 在 {window_sec} 秒内仍未结束；"
        f"后续可使用 {_command('check_task', task_id)} 主动查询任务进展。"
    )


def follow_auth_required_task_until_ready(
    endpoint: str,
    token: str,
    session_id: str,
    agent_id: str,
    task_id: str,
    window_sec: int = 180,
    interval_sec: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[str]:
    if not task_id:
        return None
    if window_sec <= 0 or interval_sec <= 0:
        return _auth_followup_timeout_message(task_id, max(0, window_sec))

    attempts = max(1, (window_sec + interval_sec - 1) // interval_sec)
    deadline = time.monotonic() + window_sec
    remaining_window = window_sec
    for _ in range(attempts):
        delay = min(interval_sec, remaining_window)
        if delay <= 0:
            break
        sleep(delay)
        remaining_window -= delay
        timeout = max(0.2, min(GET_TASK_TIMEOUT, deadline - time.monotonic()))
        with task_store.task_transaction(session_id, agent_id, task_id) as tx:
            _state, record = tx.normalize()
            if not record:
                return f"当前 session 下没有找到任务 {task_id}。"
            if record.get("terminalState") == TASK_LOST_OR_EXPIRED:
                return tx_remove_task_not_found(tx, record)["message"]

            active = record.get("activeState")
            if active == task_store.STATE_READY:
                result = format_ready_task_result(record)
                tx_enter_delivered(tx, record=record, delivery_mode="auth_followup")
                return result
            if active in (task_store.STATE_INPUT_REQUIRED, task_store.STATE_DELIVERED):
                return format_task_status_record(record)
            if active not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
                return format_task_status_record(record)

            try:
                task = get_task(endpoint, token, task_id, history_length=0, timeout=timeout)
                final_task = None
                if task_state(task) in TERMINAL_STATES:
                    final_timeout = max(0.2, min(GET_TASK_TIMEOUT, deadline - time.monotonic()))
                    final_task = get_task(
                        endpoint,
                        token,
                        task_id,
                        history_length=None,
                        timeout=final_timeout,
                    )
                updated = transition_from_task(
                    tx,
                    endpoint=endpoint,
                    task=task,
                    final_task=final_task,
                    existing=record,
                    probe_attempt=True,
                )
            except TaskNotFoundError:
                return tx_remove_task_not_found(tx, record)["message"]
            except TaskRecoveryError as e:
                tx_update_probe_error(tx, record, error_message=str(e))
                continue

            if updated.get("activeState") == task_store.STATE_READY:
                result = format_ready_task_result(updated)
                tx_enter_delivered(tx, record=updated, delivery_mode="auth_followup")
                return result
            if updated.get("activeState") == task_store.STATE_INPUT_REQUIRED:
                return format_task_status_record(updated)

    return _auth_followup_timeout_message(task_id, window_sec)


def check_task(endpoint: str, token: str, session_id: str, agent_id: str,
               task_id: str, history_length: Optional[int] = None) -> str:
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record:
            return f"当前 session 下没有找到任务 {task_id}。"
        active = record.get("activeState")
        if record.get("terminalState") == TASK_LOST_OR_EXPIRED:
            return tx_remove_task_not_found(tx, record)["message"]
        if active not in (task_store.STATE_PENDING, task_store.STATE_RUNNING):
            return format_task_status_record(record)
        try:
            task = get_task(endpoint, token, task_id, history_length=0)
            final_task = None
            if task_state(task) in TERMINAL_STATES:
                final_task = get_task(endpoint, token, task_id, history_length=history_length)
            updated = transition_from_task(
                tx,
                endpoint=endpoint,
                task=task,
                final_task=final_task,
                existing=record,
                probe_attempt=True,
            )
            if updated.get("activeState") == task_store.STATE_READY:
                return f"任务 {task_id} 已结束并进入 ready，可使用 view_task 查看结果。"
            return format_task_status_record(updated)
        except TaskNotFoundError:
            return tx_remove_task_not_found(tx, record)["message"]
        except TaskRecoveryError as e:
            error_message = str(e)
            tx_update_probe_error(tx, record, error_message=error_message)
            return (
                f"检查任务 {task_id} 失败: {error_message}。"
                "这通常不代表任务失败，本地任务记录已保留，"
                "请稍后再次使用 check_task。"
            )


def cancel_task(endpoint: str, token: str, session_id: str, agent_id: str,
                task_id: str, history_length: Optional[int] = None) -> str:
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record:
            return f"当前 session 下没有找到任务 {task_id}。"

        active = record.get("activeState")
        if active not in (
            task_store.STATE_PENDING,
            task_store.STATE_RUNNING,
            task_store.STATE_INPUT_REQUIRED,
        ):
            return format_task_status_record(record)

        if not _endpoint_matches(record, endpoint):
            return _cancel_keep_local_message(
                task_id,
                f"endpoint 不匹配，任务记录为 {record.get('endpoint')}，当前为 {endpoint}",
            )

        response = rpc_request(
            endpoint,
            token,
            "CancelTask",
            {"id": task_id},
            timeout=CANCEL_TASK_TIMEOUT,
        )
        error = response.get("error")
        if error:
            if is_task_not_found_error(error):
                return tx_remove_task_not_found(tx, record)["message"]
            return _cancel_failed_keep_local_message(task_id, error)

        task = _task_from_cancel_response(response)
        if task:
            mismatch = _validate_cancel_task_id(task, task_id)
            if mismatch:
                return _cancel_keep_local_message(task_id, mismatch)
            state = task_state(task)
            if state == TASK_STATE_CANCELED:
                tx.remove_all()
                return _cancel_success_message(task_id)
            if state in TERMINAL_STATES:
                updated, reason = _enter_ready_from_cancel_terminal(
                    tx,
                    endpoint=endpoint,
                    token=token,
                    task=task,
                    existing=record,
                    history_length=history_length,
                )
                if reason:
                    return _cancel_keep_local_message(task_id, reason)
                if updated and updated.get("activeState") == task_store.STATE_READY:
                    return f"任务 {task_id} 已结束并进入 ready，可使用 view_task 查看结果。"
                return format_task_status_record(updated or record)
            updated = transition_from_task(
                tx,
                endpoint=endpoint,
                task=task,
                existing=record,
                probe_attempt=True,
            )
            return format_task_status_record(updated)

        try:
            task = get_task(endpoint, token, task_id, history_length=0)
        except TaskNotFoundError:
            return tx_remove_task_not_found(tx, record)["message"]
        except TaskRecoveryError as e:
            return _cancel_keep_local_message(task_id, f"取消请求已返回但无法确认远端状态: {e}")

        mismatch = _validate_cancel_task_id(task, task_id)
        if mismatch:
            return _cancel_keep_local_message(task_id, mismatch)
        state = task_state(task)
        if state == TASK_STATE_CANCELED:
            tx.remove_all()
            return _cancel_success_message(task_id)
        if state in TERMINAL_STATES:
            updated, reason = _enter_ready_from_cancel_terminal(
                tx,
                endpoint=endpoint,
                token=token,
                task=task,
                existing=record,
                history_length=history_length,
            )
            if reason:
                return _cancel_keep_local_message(task_id, reason)
            if updated and updated.get("activeState") == task_store.STATE_READY:
                return f"任务 {task_id} 已结束并进入 ready，可使用 view_task 查看结果。"
            return format_task_status_record(updated or record)
        updated = transition_from_task(
            tx,
            endpoint=endpoint,
            task=task,
            existing=record,
            probe_attempt=True,
        )
        return format_task_status_record(updated)


def view_task(endpoint: str, token: str, session_id: str, agent_id: str,
              task_id: str, emit: Callable[[str], None]) -> None:
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record:
            emit(f"当前 session 下没有找到任务 {task_id}。")
            return
        if record.get("terminalState") == TASK_LOST_OR_EXPIRED:
            emit(tx_remove_task_not_found(tx, record)["message"])
            return
        active = record.get("activeState")
        if active == task_store.STATE_READY:
            emit(format_ready_task_result(record))
            tx_enter_delivered(tx, record=record, delivery_mode="view_task")
            return
        emit(format_task_status_record(record))


class ContinueContext:
    def __init__(self, tx: task_store.TaskTransaction, record: Optional[dict], error: Optional[str] = None):
        self.tx = tx
        self.record = record
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None and self.record is not None

    @property
    def task_id(self) -> str:
        return self.record.get("taskId", "") if self.record else ""

    @property
    def context_id(self) -> Optional[str]:
        return self.record.get("contextId") if self.record else None


@contextlib.contextmanager
def continue_task_context(session_id: str, agent_id: str, endpoint: str,
                          task_id: str, user_message: str) -> Iterator[ContinueContext]:
    with task_store.task_transaction(session_id, agent_id, task_id) as tx:
        _state, record = tx.normalize()
        if not record:
            yield ContinueContext(tx, None, f"当前 session 下没有找到任务 {task_id}。")
            return
        if record.get("activeState") != task_store.STATE_INPUT_REQUIRED:
            yield ContinueContext(tx, None, format_task_status_record(record))
            return
        running = tx_enter_running(
            tx,
            endpoint=endpoint,
            task_id=task_id,
            context_id=record.get("contextId"),
            existing=record,
            submitted_message=user_message,
            probe_attempt=False,
        )
        yield ContinueContext(tx, running)
