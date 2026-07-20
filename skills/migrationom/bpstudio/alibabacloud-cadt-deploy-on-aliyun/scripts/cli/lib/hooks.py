"""Dynamic hook loader.

Convention (mirrors hooks/README.md):
  hooks/pre/<OpName>.py   → def pre_hook(args, context) -> dict
  hooks/post/<OpName>.py  → def post_hook(args, result, context) -> dict
  hooks/pre/_global.py    → applies to ALL ops, runs BEFORE per-op hook
  hooks/post/_global.py   → applies to ALL ops, runs AFTER per-op hook

context dict:
  op_name      — canonical Op name
  exec_mode    — "sync" | "async"
  service_type — "qoder" | "ecs" (internal routing, for hook logic)

Raise HookReject(code, message, fix_hint) to abort.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from functools import lru_cache
from types import ModuleType
from typing import Any, Dict, Optional

from .errors import CadtError, HookReject, PostVerifyFailed

# hooks/ sits next to lib/ (i.e. at project root level)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS_DIR = os.path.join(_PROJECT_ROOT, "hooks")


@lru_cache(maxsize=128)
def _load_module(path: str) -> Optional[ModuleType]:
    """Dynamically load a .py file as a module. Returns None if not found."""
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location(
        f"cadt_hook_{os.path.basename(path)}", path
    )
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # Inject lib path so hooks can `from lib.errors import ...`
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _hook_path(phase: str, name: str) -> str:
    """Return absolute path for hooks/<phase>/<name>.py"""
    return os.path.join(HOOKS_DIR, phase, f"{name}.py")


def run_pre_hooks(op_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute global + per-op pre hooks. Returns (possibly modified) args.

    Raises HookReject on rejection.
    """
    # 1. global pre
    args = _call_pre(_hook_path("pre", "_global"), op_name, args, context)
    # 2. per-op pre
    args = _call_pre(_hook_path("pre", op_name), op_name, args, context)
    return args


def run_post_hooks(
    op_name: str,
    original_args: Dict[str, Any],
    result: Any,
    context: Dict[str, Any],
) -> Any:
    """Execute per-op + global post hooks. Returns (possibly modified) result.

    Raises PostVerifyFailed on assertion failure.
    """
    # 1. per-op post
    result = _call_post(_hook_path("post", op_name), op_name, original_args, result, context)
    # 2. global post
    result = _call_post(_hook_path("post", "_global"), op_name, original_args, result, context)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _call_pre(path: str, op_name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    mod = _load_module(path)
    if mod is None:
        return args
    fn = getattr(mod, "pre_hook", None)
    if fn is None:
        return args
    try:
        result = fn(args, context)
        if isinstance(result, dict):
            return result
        return args
    except HookReject:
        raise
    except Exception as exc:
        raise CadtError(
            f"pre-hook exception ({os.path.basename(path)}): {exc}",
            fix_hint=f"Check pre_hook implementation in {path}",
        )


def _call_post(
    path: str,
    op_name: str,
    original_args: Dict[str, Any],
    result: Any,
    context: Dict[str, Any],
) -> Any:
    mod = _load_module(path)
    if mod is None:
        return result
    fn = getattr(mod, "post_hook", None)
    if fn is None:
        return result
    try:
        out = fn(original_args, result, context)
        return out if out is not None else result
    except HookReject as e:
        raise PostVerifyFailed(
            e.message,
            fix_hint=e.fix_hint,
        )
    except Exception as exc:
        raise CadtError(
            f"post-hook exception ({os.path.basename(path)}): {exc}",
            fix_hint=f"Check post_hook implementation in {path}",
        )


def clear_cache() -> None:
    """For testing — clear loaded hook module cache."""
    _load_module.cache_clear()
