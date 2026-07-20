from __future__ import annotations

import os
from typing import Any, Dict

from lib.errors import ValidationFailed

COMMAND_SIZE_LIMIT = 18000


def _resolve_file_ref(value: str) -> str:
    if value.startswith("@") and len(value) > 1:
        path = value[1:]
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return value


def _read_file(path: str) -> str | None:
    if path == "-":
        import sys
        return sys.stdin.read()
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _check_command_size(cmd: str) -> None:
    if isinstance(cmd, str) and len(cmd) > COMMAND_SIZE_LIMIT:
        raise ValidationFailed(
            f"command exceeds size limit: {len(cmd)} chars (limit: ~{COMMAND_SIZE_LIMIT})",
            fix_hint="Split into multiple EcsRunCommand calls, or upload script to OSS and download via curl/wget",
        )


def pre_hook(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    args.setdefault("type", "RunShellScript")

    command_file = args.pop("commandFile", None)
    if command_file and not args.get("command"):
        content = _read_file(command_file)
        if content is not None:
            args["command"] = content

    cmd = args.get("command")
    if isinstance(cmd, str):
        args["command"] = _resolve_file_ref(cmd)
    elif isinstance(cmd, list):
        resolved = [_resolve_file_ref(c) if isinstance(c, str) else c for c in cmd]
        args["command"] = "\n".join(str(c) for c in resolved)

    _check_command_size(args.get("command", ""))
    return args
