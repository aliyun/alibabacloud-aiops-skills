from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

try:
    from scripts.a2a_proxy.references.observability import validate_session_id
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.references.observability import validate_session_id


CLAUDE_SESSION_ENV_VARS = (
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "ANTHROPIC_SESSION_ID",
)
GENERATED_SESSION_ENV = "SKILL_SESSION_ID"
CODEX_THREAD_ID_ENV = "CODEX_THREAD_ID"
QWEN_LATEST_LINK = Path.home() / ".qwen" / "debug" / "latest"
CLIENT_SESSION_PREFIXES = {
    "claudecode": "claudecode-",
    "codex": "codex-",
    "qwencode": "qwencode-",
}


def _usable_session_id(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"<empty>", "none", "null", "undefined"}:
        return None
    if value.startswith("${") and value.endswith("}"):
        return None
    if value.startswith("$") and value[1:].replace("_", "").isalnum():
        return None
    return value


def _looks_like_claude_code(env: Mapping[str, str]) -> bool:
    if env.get("CLAUDECODE") == "1":
        return True
    return any(
        env.get(name)
        for name in (
            "CLAUDE_CONFIG_DIR",
            "CLAUDE_PLUGIN_ROOT",
            "CLAUDE_CODE_ENTRYPOINT",
            "CMUX_CLAUDE_HOOK_CMUX_BIN",
        )
    )


def _process_basename(comm: str, args: str = "") -> str:
    candidate = comm.strip() if comm else ""
    if not candidate and args:
        first_token = args.strip().split()[0] if args.strip() else ""
        candidate = Path(first_token).name
    if candidate.lower().endswith(".exe"):
        candidate = candidate[:-4]
    return candidate.lower()


def _client_from_skill_path(file_path: str | Path | None = None) -> str | None:
    path = str(Path(file_path or __file__).resolve()).lower()
    if ".qoderwork/skills" in path:
        return "qoderwork"
    if ".qwen/skills" in path:
        return "qwencode"
    if ".claude/skills" in path:
        return "claudecode"
    if ".codex/skills" in path:
        return "codex"
    return None


def _read_process_info(pid: int) -> tuple[str, str, int] | None:
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=,comm=,args=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=1,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    parts = result.stdout.strip().split(None, 2)
    if len(parts) < 2:
        return None
    try:
        ppid = int(parts[0])
    except ValueError:
        return None
    return parts[1], parts[2] if len(parts) == 3 else "", ppid


def _client_from_parent_process(
    parent_pids: Iterable[int] | None,
    process_info: Mapping[int, tuple[str, str, int]] | None = None,
) -> str | None:
    pids = list(parent_pids) if parent_pids is not None else _parent_process_ids()
    for pid in pids:
        info = process_info.get(pid) if process_info else _read_process_info(pid)
        if not info:
            continue
        comm, args, _ppid = info
        basename = _process_basename(comm, args)
        if basename in {"qoder", "qoderwork", "qodercli"}:
            return "qoderwork"
        if basename == "qwen":
            return "qwencode"
        if basename == "claude":
            return "claudecode"
        if basename == "codex":
            return "codex"
    return None


def _client_from_env_markers(env: Mapping[str, str]) -> str | None:
    if any(
        env.get(name)
        for name in (
            "QODERWORK_SESSION",
            "QODERWORK_CONFIG_DIR",
            "QODERWORK_PLUGIN_ROOT",
            "QODERWORK_CODE_ENTRYPOINT",
        )
    ):
        return "qoderwork"
    if any(env.get(name) for name in ("QWEN_CONFIG_DIR", "QWEN_CODE_ENTRYPOINT")):
        return "qwencode"
    if _looks_like_claude_code(env) or any(env.get(name) for name in CLAUDE_SESSION_ENV_VARS):
        return "claudecode"
    return None


def _detect_client_context(
    env: Mapping[str, str],
    parent_pids: Iterable[int] | None,
    process_info: Mapping[int, tuple[str, str, int]] | None = None,
) -> str | None:
    return (
        _client_from_skill_path()
        or _client_from_parent_process(parent_pids, process_info)
        or _client_from_env_markers(env)
    )


def _looks_like_qwen_code(
    env: Mapping[str, str],
    parent_pids: Iterable[int] | None,
    process_info: Mapping[int, tuple[str, str, int]] | None = None,
) -> bool:
    return _detect_client_context(env, parent_pids, process_info) == "qwencode"


def _looks_like_qoderwork(
    env: Mapping[str, str],
    parent_pids: Iterable[int] | None,
    process_info: Mapping[int, tuple[str, str, int]] | None = None,
) -> bool:
    return _detect_client_context(env, parent_pids, process_info) == "qoderwork"


def _valid_generated_session_id(value: str | None) -> str | None:
    try:
        return validate_session_id(value)
    except RuntimeError:
        return None


def _self_managed_session_id(
    value: str | None,
    generated_id: str | None,
    *,
    required_prefix: str | None = None,
) -> str | None:
    """Keep the client session prefix while binding it to one generated ID."""
    generated = _valid_generated_session_id(generated_id)
    if not generated:
        return None
    candidate = _usable_session_id(value)
    if required_prefix:
        expected = f"{required_prefix}-{generated}"
        if candidate in (None, generated, expected):
            return expected
        return None
    if candidate and candidate != generated and candidate.endswith(f"-{generated}"):
        return candidate
    return None


def _prefix_client_session_id(client_name: str, session_id: str | None) -> str | None:
    if not session_id:
        return None
    prefix = CLIENT_SESSION_PREFIXES.get(client_name)
    if not prefix:
        return session_id
    if session_id.startswith(prefix):
        return session_id
    return f"{prefix}{session_id}"


def _detect_qwen_session_id(latest_link: str | Path | None = None) -> str | None:
    link = Path(latest_link) if latest_link is not None else QWEN_LATEST_LINK
    try:
        if not link.is_symlink():
            return None
        target = Path(os.readlink(link))
        basename = target.name
        stem = basename[:-4] if basename.endswith(".txt") else ""
        return _usable_session_id(stem)
    except OSError:
        return None


def _default_config_dir(env: Mapping[str, str]) -> Path:
    if env.get("CLAUDE_CONFIG_DIR"):
        return Path(env["CLAUDE_CONFIG_DIR"]).expanduser()
    return Path.home() / ".claude"


def _parent_process_ids(start_pid: int | None = None) -> list[int]:
    pid = start_pid or os.getppid()
    seen: set[int] = set()
    pids: list[int] = []
    while pid > 1 and pid not in seen:
        seen.add(pid)
        pids.append(pid)
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception:
            break
        if result.returncode != 0:
            break
        try:
            pid = int(result.stdout.strip())
        except ValueError:
            break
    return pids


def _read_session_record(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _record_session_id(record: Mapping) -> str | None:
    value = record.get("sessionId") or record.get("session_id")
    return _usable_session_id(str(value)) if value is not None else None


def _record_updated_at(record: Mapping, path: Path) -> float:
    value = record.get("updatedAt") or record.get("updated_at") or record.get("startedAt") or 0
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0


def _cwd_score(record: Mapping, cwd: str | Path | None) -> int:
    record_cwd = record.get("cwd")
    if not record_cwd or not cwd:
        return 0
    try:
        record_path = Path(str(record_cwd)).expanduser().resolve()
        cwd_path = Path(cwd).expanduser().resolve()
    except OSError:
        return 0
    if record_path == cwd_path:
        return 3
    if cwd_path.is_relative_to(record_path):
        return 2
    if record_path.is_relative_to(cwd_path):
        return 1
    return 0


def _resolve_from_claude_sessions(
    config_dir: Path,
    parent_pids: Iterable[int] | None,
    cwd: str | Path | None,
) -> str | None:
    sessions_dir = config_dir / "sessions"
    if not sessions_dir.exists():
        return None

    pids = list(parent_pids) if parent_pids is not None else _parent_process_ids()
    for pid in pids:
        record = _read_session_record(sessions_dir / f"{pid}.json")
        if not record:
            continue
        session_id = _record_session_id(record)
        if session_id:
            return session_id

    candidates: list[tuple[int, float, str]] = []
    for path in sessions_dir.glob("*.json"):
        record = _read_session_record(path)
        if not record:
            continue
        session_id = _record_session_id(record)
        if not session_id:
            continue
        candidates.append((_cwd_score(record, cwd), _record_updated_at(record, path), session_id))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def resolve_session_id(
    explicit: str | None,
    *,
    env: Mapping[str, str] | None = None,
    config_dir: str | Path | None = None,
    parent_pids: Iterable[int] | None = None,
    cwd: str | Path | None = None,
    process_info: Mapping[int, tuple[str, str, int]] | None = None,
    qwen_latest_link: str | Path | None = None,
) -> str | None:
    env = os.environ if env is None else env
    explicit_id = _usable_session_id(explicit)
    client_name = _detect_client_context(env, parent_pids, process_info)
    generated_id = _usable_session_id(env.get(GENERATED_SESSION_ENV))

    if client_name == "qoderwork":
        return _self_managed_session_id(
            explicit_id,
            generated_id,
            required_prefix="qoderwork",
        )

    if client_name == "qwencode":
        return _prefix_client_session_id("qwencode", _detect_qwen_session_id(qwen_latest_link))

    if client_name == "claudecode":
        if explicit_id:
            return _prefix_client_session_id("claudecode", explicit_id)
        for env_name in CLAUDE_SESSION_ENV_VARS:
            session_id = _usable_session_id(env.get(env_name))
            if session_id:
                return _prefix_client_session_id("claudecode", session_id)
        return _prefix_client_session_id(
            "claudecode",
            _resolve_from_claude_sessions(
                Path(config_dir) if config_dir is not None else _default_config_dir(env),
                parent_pids,
                cwd or os.getcwd(),
            ),
        )

    if client_name == "codex":
        return _prefix_client_session_id("codex", _usable_session_id(env.get(CODEX_THREAD_ID_ENV)))

    return _self_managed_session_id(explicit_id, generated_id)
