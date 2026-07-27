from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from .config import default_vendor_proxy_script, normalize_agenthub_endpoint


CONTROL_VERSION = 1
MAX_CONTROL_LINE_BYTES = 64 * 1024
_TASK_EVENT_KEYS = {"v", "type", "state", "taskId", "hitlRound"}
_CARD_EVENT_KEYS = {"v", "type", "supportsStreaming", "rpcPath"}
_NOTIFICATION_KEYS = {"v", "type", "readyResults", "inputRequired"}
_NOTIFICATION_ITEM_KEYS = {"taskId", "state"}
_TASK_EVENT_OPERATIONS = {
    "send_message",
    "send_streaming_message",
    "continue_task",
    "subscribe_task",
    "follow_task",
}
_NOTIFICATION_OPERATIONS = set(_TASK_EVENT_OPERATIONS)
_TASK_BOUND_OPERATIONS = {"continue_task", "subscribe_task", "follow_task"}


def _trusted_endpoint(endpoint: str, agent_id: str) -> str:
    return normalize_agenthub_endpoint(endpoint, agent_id=agent_id)


def _is_exact_int(value: object) -> bool:
    return type(value) is int


def _valid_task_event(event: dict, command: "ProxyCommand") -> bool:
    if set(event) != _TASK_EVENT_KEYS:
        return False
    if event.get("v") != CONTROL_VERSION or not _is_exact_int(event.get("v")):
        return False
    if event.get("type") != "task_state" or event.get("state") != "auth_required":
        return False
    task_id = event.get("taskId")
    hitl_round = event.get("hitlRound")
    if not isinstance(task_id, str) or not task_id or not _is_exact_int(hitl_round) or hitl_round <= 0:
        return False
    if command.operation not in _TASK_EVENT_OPERATIONS:
        return False
    if command.operation in _TASK_BOUND_OPERATIONS and task_id != command.task_id:
        return False
    return True


def _valid_notification_item(item: object, expected_state: str) -> bool:
    return (
        isinstance(item, dict)
        and set(item) == _NOTIFICATION_ITEM_KEYS
        and isinstance(item.get("taskId"), str)
        and bool(item.get("taskId"))
        and item.get("state") == expected_state
    )


def _valid_notification_event(event: dict, command: "ProxyCommand") -> bool:
    if set(event) != _NOTIFICATION_KEYS:
        return False
    if event.get("v") != CONTROL_VERSION or not _is_exact_int(event.get("v")):
        return False
    if event.get("type") != "task_notifications" or command.operation not in _NOTIFICATION_OPERATIONS:
        return False
    ready = event.get("readyResults")
    input_required = event.get("inputRequired")
    if not isinstance(ready, list) or not isinstance(input_required, list):
        return False
    return all(
        _valid_notification_item(item, "TASK_STATE_COMPLETED") for item in ready
    ) and all(
        _valid_notification_item(item, "TASK_STATE_INPUT_REQUIRED") for item in input_required
    )


def _valid_agent_card_event(event: dict, command: "ProxyCommand") -> bool:
    return (
        command.operation == "get_agent_card"
        and set(event) == _CARD_EVENT_KEYS
        and event.get("v") == CONTROL_VERSION
        and _is_exact_int(event.get("v"))
        and event.get("type") == "agent_card"
        and type(event.get("supportsStreaming")) is bool
        and event.get("rpcPath") == "/rpc"
    )


def _validated_control_event(raw: bytes, command: "ProxyCommand") -> dict | None:
    try:
        event = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(event, dict):
        return None
    if _valid_task_event(event, command):
        return event
    if _valid_notification_event(event, command):
        return event
    if _valid_agent_card_event(event, command):
        return event
    return None


@dataclass(frozen=True)
class ProxyResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""
    control_events: tuple[dict, ...] = ()


@dataclass(frozen=True)
class ProxyCommand:
    operation: str
    endpoint: str
    agent_id: str
    session_id: str
    message: str | None = None
    task_id: str | None = None
    include_delivered: bool = False
    accepted_output_modes: str | None = None
    history_length: int | None = None
    return_immediately: bool = False
    rpc_path: str = "/rpc"
    follow_window_sec: int = 180
    follow_interval_sec: int = 5

    def to_vendor_argv(
        self,
        vendor_script: str | Path,
        *,
        control_fd: int | None = None,
    ) -> list[str]:
        endpoint = _trusted_endpoint(self.endpoint, self.agent_id)
        if self.rpc_path != "/rpc":
            raise ValueError("unsupported A2A RPC path")
        if self.follow_window_sec <= 0 or self.follow_window_sec > 180:
            raise ValueError("follow window is out of bounds")
        if self.follow_interval_sec <= 0 or self.follow_interval_sec > 5:
            raise ValueError("follow interval is out of bounds")
        argv = [
            sys.executable,
            str(vendor_script),
            "--operation",
            self.operation,
            "--endpoint",
            endpoint,
            "--agent-id",
            self.agent_id,
            "--session-id",
            self.session_id,
            "--rpc-path",
            self.rpc_path,
        ]
        if control_fd is not None:
            argv.extend(["--control-fd", str(control_fd)])
        if self.task_id is not None:
            argv.extend(["--task-id", self.task_id])
        if self.include_delivered:
            argv.append("--include-delivered")
        if self.accepted_output_modes:
            argv.extend(["--accepted-output-modes", self.accepted_output_modes])
        if self.history_length is not None:
            argv.extend(["--history-length", str(self.history_length)])
        if self.return_immediately:
            argv.append("--return-immediately")
        if self.operation == "follow_task":
            argv.extend(["--follow-window-sec", str(self.follow_window_sec)])
            argv.extend(["--follow-interval-sec", str(self.follow_interval_sec)])
        return argv


class ProxyRunner:
    def __init__(self, vendor_script: str | Path | None = None, runner=subprocess.run):
        self.vendor_script = Path(vendor_script) if vendor_script else default_vendor_proxy_script()
        self.runner = runner
        self.last_control_events: tuple[dict, ...] = ()

    @staticmethod
    def _read_control_fd(read_fd: int, command: ProxyCommand, destination: list[dict]) -> None:
        buffer = bytearray()
        dropping = False
        try:
            while True:
                chunk = os.read(read_fd, 8192)
                if not chunk:
                    break
                for byte in chunk:
                    if byte == 0x0A:
                        if not dropping and buffer:
                            event = _validated_control_event(bytes(buffer), command)
                            if event is not None:
                                destination.append(event)
                        buffer.clear()
                        dropping = False
                        continue
                    if dropping:
                        continue
                    if len(buffer) >= MAX_CONTROL_LINE_BYTES:
                        buffer.clear()
                        dropping = True
                        continue
                    buffer.append(byte)
            if buffer and not dropping:
                event = _validated_control_event(bytes(buffer), command)
                if event is not None:
                    destination.append(event)
        finally:
            os.close(read_fd)

    def _execute(self, command: ProxyCommand, *, capture: bool):
        read_fd, write_fd = os.pipe()
        events: list[dict] = []
        thread = threading.Thread(
            target=self._read_control_fd,
            args=(read_fd, command, events),
            daemon=True,
        )
        thread.start()
        try:
            argv = command.to_vendor_argv(self.vendor_script, control_fd=write_fd)
            kwargs = {
                "input": command.message,
                "text": True,
                "pass_fds": (write_fd,),
            }
            if capture:
                kwargs["capture_output"] = True
            result = self.runner(argv, **kwargs)
        finally:
            os.close(write_fd)
            thread.join()
        self.last_control_events = tuple(events)
        return result

    def run(self, command: ProxyCommand) -> int:
        result = self._execute(command, capture=False)
        return int(getattr(result, "returncode", 0) or 0)

    def run_capture(self, command: ProxyCommand) -> ProxyResult:
        result = self._execute(command, capture=True)
        return ProxyResult(
            returncode=int(getattr(result, "returncode", 0) or 0),
            stdout=str(getattr(result, "stdout", "") or ""),
            stderr=str(getattr(result, "stderr", "") or ""),
            control_events=self.last_control_events,
        )
