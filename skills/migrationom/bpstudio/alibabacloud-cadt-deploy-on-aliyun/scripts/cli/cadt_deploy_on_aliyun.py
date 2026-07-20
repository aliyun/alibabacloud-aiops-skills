#!/usr/bin/env python3
"""cadt_deploy_on_aliyun — qoder Operation dispatcher.

Agent contract:
    cadt_deploy_on_aliyun -l [--category=...] [--exec-mode=...] [--search=...]
    cadt_deploy_on_aliyun -d <Op>
    cadt_deploy_on_aliyun -run <Op> <json|@file> [--timeout=N] [--command-file=<path>]
    cadt_deploy_on_aliyun -poll <operationId> [--wait=once|done] [--timeout=N]
    cadt_deploy_on_aliyun -version
    cadt_deploy_on_aliyun -doctor
    cadt_deploy_on_aliyun -whoami

All output is single-line JSON envelope. Exit codes:
    0   success
    1   business failure (envelope.ok=false)
    2   cadt-deploy-on-aliyun itself broken (usage / IO / uncaught)
    124 timeout
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from typing import Any, Dict, List

from lib import envelope as env
from lib import errors as E
from lib import manifest as mf
from lib.envelope import emit, err, ok, stopwatch
from lib.runner import run_op
from lib import poller


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_version(_args: List[str]) -> int:
    sw = stopwatch()
    try:
        meta = mf.manifest_meta()
    except E.CadtError as e:
        meta = {"version": "unknown", "ops_count": 0, "load_error": e.message}
    data = {
        "cadt-deploy-on-aliyun": env.CADT_VERSION,
        "ops_manifest_version": meta.get("version"),
        "ops_count": meta.get("ops_count"),
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }
    emit(ok(data, meta={"elapsedMs": sw.elapsed_ms}))
    return 0


def cmd_list(args: List[str]) -> int:
    sw = stopwatch()
    flags = _parse_flags(args, allowed={"category", "exec-mode", "search", "source"})
    try:
        items = mf.list_ops(
            category=flags.get("category", ""),
            exec_mode=flags.get("exec-mode", ""),
            search=flags.get("search", ""),
            source=flags.get("source", ""),
        )
        meta = mf.manifest_meta()
    except E.CadtError as e:
        emit(_envelope_from_error(e))
        return 1
    emit(ok(
        {
            "version": meta["version"],
            "total": len(items),
            "operations": items,
        },
        meta={"elapsedMs": sw.elapsed_ms},
    ))
    return 0


def cmd_describe(args: List[str]) -> int:
    sw = stopwatch()
    if not args:
        emit(err("CADT_INTERNAL", "Missing Op name", fix_hint="Usage: cadt_deploy_on_aliyun -d <Op>"))
        return 2
    op_name = args[0]
    try:
        spec = mf.load_op(op_name)
    except E.CadtError as e:
        emit(_envelope_from_error(e, op=op_name))
        return 1
    emit(ok(spec, meta={"operation": op_name, "elapsedMs": sw.elapsed_ms}))
    return 0


def cmd_run(args: List[str]) -> int:
    if len(args) < 2:
        emit(err("CADT_INTERNAL", "Missing arguments",
                 fix_hint="Usage: cadt_deploy_on_aliyun -run <Op> '<json>' or cadt_deploy_on_aliyun -run <Op> @input.json"))
        return 2
    _inject_session_id(args)
    op_name, payload_arg, *rest = args
    flags = _parse_flags(rest, allowed={"timeout", "command-file"})

    payload_str = _load_payload(payload_arg)
    if payload_str is None:
        emit(err("CADT_INTERNAL", f"Unable to read input: {payload_arg}",
                 fix_hint="Check that the file path exists, or ensure the JSON string is correct"))
        return 2
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        if payload_str.strip().startswith("--"):
            emit(err("VALIDATION_FAILED",
                     f"CLI does not support --key value format; use JSON instead",
                     fix_hint=f"Usage: -run {op_name} '{{\"key\":\"value\"}}' or -run {op_name} @input.json"))
        else:
            emit(err("VALIDATION_FAILED", f"Input JSON parse failed: {e}",
                     fix_hint="Ensure JSON is valid, e.g., '{\"key\":\"value\"}'"))
        return 1
    if not isinstance(payload, dict):
        emit(err("VALIDATION_FAILED", "Input must be a JSON object",
                  fix_hint="Top level must be {} not an array or scalar"))
        return 1

    command_file = flags.get("command-file")
    if command_file:
        cmd_content = _load_command_file(command_file)
        if cmd_content is None:
            emit(err("CADT_INTERNAL", f"Unable to read command file: {command_file}",
                     fix_hint="Check that the file path exists and is readable"))
            return 2
        payload["command"] = cmd_content

    try:
        timeout = int(flags.get("timeout", 300))
    except (ValueError, TypeError):
        emit(err("CADT_INTERNAL", "--timeout must be an integer"))
        return 2
    try:
        envelope = run_op(op_name, payload, timeout=timeout)
        if envelope.get("data", {}).get("status") == "submitted":
            inv_id = envelope["data"].get("invocationId", "")
            print(f"WARNING: Async operation submitted. You MUST now run: cadt-deploy-on-aliyun -poll {inv_id}", file=sys.stderr)
        emit(envelope)
        return 0
    except E.CadtTimeout as e:
        emit(_envelope_from_error(e, op=op_name,
                                  extra_meta={"operationId": e.invocation_id}))
        return 124
    except E.CadtError as e:
        emit(_envelope_from_error(e, op=op_name))
        return 1


def cmd_poll(args: List[str]) -> int:
    if not args:
        emit(err("CADT_INTERNAL", "Missing operationId",
                 fix_hint="Usage: cadt_deploy_on_aliyun -poll <operationId>"))
        return 2
    _inject_session_id(args)
    invocation_id, *rest = args
    flags = _parse_flags(rest, allowed={"wait", "timeout"})
    wait_mode = flags.get("wait", "done")
    try:
        timeout = int(flags.get("timeout", poller.DEFAULT_TIMEOUT_S))
    except (ValueError, TypeError):
        emit(err("CADT_INTERNAL", "--timeout must be an integer"))
        return 2

    sw = stopwatch()
    try:
        if wait_mode == "once":
            data = poller.poll_once(invocation_id)
        else:
            data = poller.poll_until_done(invocation_id, timeout=timeout)
            data = {"operationId": invocation_id, "status": "success", "data": data}
    except E.CadtTimeout as e:
        emit(_envelope_from_error(e, extra_meta={"operationId": invocation_id}))
        return 124
    except E.CadtError as e:
        emit(_envelope_from_error(e))
        return 1
    emit(ok(data, meta={"elapsedMs": sw.elapsed_ms}))
    return 0


def cmd_doctor(_args: List[str]) -> int:
    sw = stopwatch()
    checks: List[Dict[str, Any]] = []

    # 1. python version
    py_ok = sys.version_info >= (3, 9)
    checks.append({"name": "python>=3.9", "ok": py_ok,
                   "actual": sys.version.split()[0]})

    # 2. jsonschema
    try:
        import jsonschema  # noqa: F401
        checks.append({"name": "jsonschema installed", "ok": True})
    except ImportError:
        checks.append({"name": "jsonschema installed", "ok": False,
                       "fix": "pip install 'jsonschema>=4.0'"})

    # 3. aliyun CLI
    aliyun = shutil.which("aliyun")
    checks.append({"name": "aliyun CLI on PATH", "ok": bool(aliyun),
                   "actual": aliyun or "(not found)"})

    # 4. aliyun bpstudio plugin
    if aliyun:
        import subprocess as _sp
        try:
            _proc = _sp.run(
                [aliyun, "plugin", "list"],
                capture_output=True, text=True, timeout=10,
                stdin=_sp.DEVNULL,
            )
            _has_bpstudio = "bpstudio" in (_proc.stdout or "")
            checks.append({"name": "aliyun bpstudio plugin", "ok": _has_bpstudio,
                           "actual": "installed" if _has_bpstudio else "(not found)"})
            if not _has_bpstudio:
                checks[-1]["fix"] = "Run: aliyun plugin install --name bpstudio"
        except (OSError, _sp.TimeoutExpired):
            checks.append({"name": "aliyun bpstudio plugin", "ok": False,
                           "fix": "Unable to query plugin list; run: aliyun plugin install --name bpstudio"})

    # 5. ops/_manifest.json loadable
    try:
        meta = mf.manifest_meta()
        checks.append({"name": "ops/_manifest.json", "ok": True,
                       "actual": f"{meta['ops_count']} ops"})
    except E.CadtError as e:
        checks.append({"name": "ops/_manifest.json", "ok": False, "fix": e.message})

# 6. ops source info (informational, not pass/fail)
    try:
        src = mf.ops_source_info()
        checks.append({"name": "ops_source", "ok": True, "info": True,
                       "actual": f"{src['ops_dir']} (manifest={src['manifest_version']}, skill={src['skill_version']})"})
    except Exception as e:
        checks.append({"name": "ops_source", "ok": True, "info": True,
                       "actual": f"unable to resolve: {e}"})

    all_ok = all(c["ok"] for c in checks)
    emit(ok({"all_ok": all_ok, "checks": checks},
            meta={"elapsedMs": sw.elapsed_ms}))
    return 0 if all_ok else 1


def cmd_whoami(_args: List[str]) -> int:
    sw = stopwatch()
    try:
        from lib.identity import get_uid
        uid = get_uid()
    except E.CadtError as e:
        emit(_envelope_from_error(e))
        return 1
    emit(ok({"uid": uid}, meta={"elapsedMs": sw.elapsed_ms}))
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _inject_session_id(args: List[str]) -> None:
    """Extract session-id from --user-agent flag and set SKILL_SESSION_ID env var.

    Supports both ``--user-agent=value`` and ``--user-agent value`` forms.
    Only sets the env var if it is not already set (env var takes precedence).
    """
    if os.environ.get("SKILL_SESSION_ID"):
        return
    for i, tok in enumerate(args):
        if tok == "--user-agent" and i + 1 < len(args):
            ua_value = args[i + 1]
        elif tok.startswith("--user-agent="):
            ua_value = tok.split("=", 1)[1]
        else:
            continue
        parts = ua_value.rsplit("/", 1)
        if len(parts) == 2 and parts[1]:
            os.environ["SKILL_SESSION_ID"] = parts[1]
        return


def _parse_flags(rest: List[str], *, allowed: set) -> Dict[str, str]:
    """Parse ``--key=value`` or ``--key value`` style flags from the tail of argv."""
    out: Dict[str, str] = {}
    i = 0
    while i < len(rest):
        tok = rest[i]
        if not tok.startswith("--"):
            i += 1
            continue
        body = tok[2:]
        if "=" in body:
            k, v = body.split("=", 1)
        else:
            k = body
            nxt = rest[i + 1] if i + 1 < len(rest) else None
            if nxt is not None and not nxt.startswith("--"):
                v = nxt
                i += 1
            else:
                v = "true"
        if k in allowed:
            out[k] = v
        i += 1
    return out


def _load_payload(arg: str) -> str | None:
    """Load JSON either from inline string or @file path."""
    if arg.startswith("@"):
        path = arg[1:]
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None
    return arg


def _load_command_file(path: str) -> str | None:
    """Read script content from a local file or stdin (``-``)."""
    if path == "-":
        return sys.stdin.read()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _envelope_from_error(e: E.CadtError, *, op: str = "",
                         extra_meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if op:
        meta["operation"] = op
    if extra_meta:
        meta.update(extra_meta)
    # Propagate diagnostic data (e.g. instanceResults) from BusinessFailure
    error_data = getattr(e, "details", None)
    return err(
        e.code,
        e.message,
        fix_hint=e.fix_hint,
        fields=e.fields,
        docs_ref=e.docs_ref,
        data=error_data,
        meta=meta,
    )


def _print_usage() -> None:
    print(__doc__, file=sys.stderr)


def _suggest_fix(unknown_cmd: str) -> tuple[str, str]:
    """Detect if the user probably meant an Op name and suggest -run usage.

    Returns (error_message, fix_hint).
    """
    import difflib
    looks_like_op = unknown_cmd[:1].isupper() and not unknown_cmd.startswith("-")
    if looks_like_op:
        try:
            from lib.manifest import load_manifest
            names = [x.get("name", "") for x in load_manifest().get("operations", [])]
            suggestions = difflib.get_close_matches(unknown_cmd, names, n=3, cutoff=0.6)
            if suggestions:
                best = suggestions[0]
                msg = (
                    f"Unknown subcommand: {unknown_cmd}. "
                    f"To run an Op use the -run prefix, e.g.: cadt_deploy_on_aliyun -run {best} @input.json"
                )
                hint = f"Did you mean: {', '.join(suggestions)}"
                return msg, hint
            msg = (
                f"Unknown subcommand: {unknown_cmd}. "
                f"To run an Op use the -run prefix, e.g.: cadt_deploy_on_aliyun -run {unknown_cmd} @input.json"
            )
            hint = "Run cadt_deploy_on_aliyun -l to list all available Ops"
            return msg, hint
        except Exception:
            msg = (
                f"Unknown subcommand: {unknown_cmd}. "
                f"To run an Op use the -run prefix, e.g.: cadt_deploy_on_aliyun -run {unknown_cmd} @input.json"
            )
            return msg, ""
    return (
        f"Unknown subcommand: {unknown_cmd}",
        "Supported: -version / -l / -d / -run / -poll / -doctor / -whoami",
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
_ROUTES = {
    "-version": cmd_version,
    "--version": cmd_version,
    "-l": cmd_list,
    "--list": cmd_list,
    "-d": cmd_describe,
    "--describe": cmd_describe,
    "-run": cmd_run,
    "--run": cmd_run,
    "-poll": cmd_poll,
    "--poll": cmd_poll,
    "-doctor": cmd_doctor,
    "--doctor": cmd_doctor,
    "-whoami": cmd_whoami,
    "--whoami": cmd_whoami,
}


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        _print_usage()
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    handler = _ROUTES.get(cmd)
    if handler is None:
        msg, hint = _suggest_fix(cmd)
        emit(err("CADT_INTERNAL", msg, fix_hint=hint or None))
        return 2
    try:
        return handler(rest)
    except KeyboardInterrupt:
        emit(err("CADT_INTERNAL", "interrupted"))
        return 130
    except Exception as exc:  # pragma: no cover - safety net
        import traceback
        traceback.print_exc(file=sys.stderr)
        emit(err("CADT_INTERNAL", f"unhandled: {exc.__class__.__name__}: {exc}",
                 fix_hint="Please submit an issue with stderr traceback"))
        return 2


if __name__ == "__main__":
    sys.exit(main())
