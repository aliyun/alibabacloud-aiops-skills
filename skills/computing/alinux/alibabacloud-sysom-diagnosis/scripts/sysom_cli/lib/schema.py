# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

FORMAT_NAME = "sysom_agent"
# 信封「字段契约」版本：删除/改名已承诺的 data/agent 键，或已承诺的引用串格式（如 data_refs 形）变更时递增。
FORMAT_VERSION = "3.4"


def agent_block(
    status: str,
    summary: str,
    *,
    findings: Optional[List[Dict[str, Any]]] = None,
    next_steps: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "summary": summary,
        "findings": findings or [],
        "next": next_steps or [],
    }


def envelope(
    *,
    action: str,
    ok: bool,
    agent: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    execution: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "ok": ok,
        "action": action,
        "error": error,
        "agent": agent,
        "data": data if data is not None else {},
        "execution": execution if execution is not None else {},
    }


def dumps(obj: Dict[str, Any], *, compact: bool = False) -> str:
    if compact:
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(obj, ensure_ascii=False, indent=2)


def error_envelope(action: str, code: str, message: str) -> Dict[str, Any]:
    return envelope(
        action=action,
        ok=False,
        agent=agent_block("unknown", message, findings=[]),
        error={"code": code, "message": message},
        execution={"mode": "local"},
    )
