#!/usr/bin/env python3
"""
Client Agent Detection — 识别"当前加载本 skill 的客户端 Agent"及其版本号

面向多客户端 Agent 场景的统一识别模块。**当前支持 claudecode、qwencode、codex 与 qoderwork**，
其他客户端待后续逐个适配，未命中时统一归为 ``unknown`` 由兜底分支处理。

识别链路（按优先级）：
    1. skill 安装路径判定（primary）— 基于 __file__ 反推本 skill 被加载的目录，
       匹配已知路径模式（``~/.claude/skills`` / ``~/.qwen/skills`` /
       ``~/.codex/skills`` / ``~/.qoderwork/skills``）
    2. 客户端专属环境标记判定 — 仅使用不会被其他客户端通用继承的专属标记
    3. 父进程链扫描（fallback）— 从当前 python 进程向上遍历 PPID 链，
       用 `ps` 读取可执行文件 basename 与已知客户端（claude / qwen / codex / qoderwork）匹配
    4. 兜底 — 均失败则 name = "unknown"

版本探测：
    对已识别出的 claudecode/qwencode/codex，调用对应的 `<cli> --version` 命令；
    对已识别出的 qoderwork，读取 macOS app bundle Info.plist。任何异常 → "unknown"。

缓存：
    模块级 _CACHED_RESULT，首次调用探测，后续直接返回，避免重复 subprocess/ps。

调试：
    设置环境变量 A2A_CLIENT_DETECT_DEBUG=1 可把识别过程打印到 stderr。
    （注意：此环境变量只影响**日志输出**，不参与身份判定。）

对外 API：
    detect_client()        -> (name: str, version: str)
    client_header_value()  -> "AlibabaCloud-Agent-Skills/alibabacloud-remote-skills-connector/<session-id> <name>/<version>"
                              # 供 HTTP User-Agent header 使用
"""

import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from .observability import build_user_agent
except ImportError:  # pragma: no cover - direct script execution
    from observability import build_user_agent

# ============================================================
# 常量定义
# ============================================================

# 路径 → agent_name 映射（按路径片段匹配，大小写不敏感）
# project 局部目录 / user 全局目录统一归一到相同 name
# 注：当前支持 claudecode、qwencode、codex、qoderwork；其他客户端待后续逐个适配，未命中则归为 unknown。
_PATH_PATTERNS = [
    (re.compile(r"(^|/)\.claude/skills(/|$)", re.IGNORECASE), "claudecode"),
    (re.compile(r"(^|/)\.qwen/skills(/|$)", re.IGNORECASE), "qwencode"),
    (re.compile(r"(^|/)\.codex/skills(/|$)", re.IGNORECASE), "codex"),
    (re.compile(r"(^|/)\.qoderwork/skills(/|$)", re.IGNORECASE), "qoderwork"),
]

# 父进程可执行文件 basename → agent_name 映射
# 注：当前支持 claudecode、qwencode、codex、qoderwork；其他客户端待后续逐个适配，未命中则归为 unknown。
_PROC_PATTERNS = [
    ("claude", "claudecode"),
    ("qwen", "qwencode"),
    ("codex", "codex"),
    ("qoder", "qoderwork"),
    ("qoderwork", "qoderwork"),
    ("qodercli", "qoderwork"),
]

# 客户端专属环境标记。不能把 CODEX_THREAD_ID 这类可能跨进程继承的 session 变量
# 当作客户端身份依据；这里只放客户端运行期自己的专属标记。
_ENV_MARKERS = [
    (
        "qoderwork",
        (
            "QODERWORK_SESSION",
            "QODERWORK_CONFIG_DIR",
            "QODERWORK_PLUGIN_ROOT",
            "QODERWORK_CODE_ENTRYPOINT",
        ),
    ),
    ("qwencode", ("QWEN_CONFIG_DIR", "QWEN_CODE_ENTRYPOINT")),
    (
        "claudecode",
        (
            "CLAUDECODE",
            "CLAUDE_CONFIG_DIR",
            "CLAUDE_PLUGIN_ROOT",
            "CLAUDE_CODE_ENTRYPOINT",
        ),
    ),
]

# agent_name → version 探测命令
# 注：claudecode、qwencode、codex 走 CLI；qoderwork 只在已识别为 qoderwork 后读取 app bundle。
_VERSION_COMMANDS = {
    "claudecode": ["claude", "--version"],
    "qwencode": ["qwen", "--version"],
    "codex": ["codex", "--version"],
}

# 版本号正则：匹配 x.y 或 x.y.z
_VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?)")

# 父进程追溯最大层数（防御无限循环）
_MAX_PPID_HOPS = 10

# version 探测超时（秒）
_VERSION_PROBE_TIMEOUT = 5.0

# QoderWork macOS app bundle 标识。只在已识别为 qoderwork 时用于版本探测。
_QODERWORK_BUNDLE_ID = "com.qoder.work"
_QODERWORK_APP_FALLBACKS = (
    Path("/Applications/QoderWork.app"),
    Path.home() / "Applications" / "QoderWork.app",
)

# qwen-code 的当前会话软链路径
# qwen-code 为每个会话在 ~/.qwen/debug/ 下创建一个以 session-id 命名的 .txt 文件，
# 并维护一个 `latest` 软链指向当前/最近的会话。这是 qwen-code 运行期唯一
# 官方暴露的当前会话 ID 通路（qwen-code 自身没有内置环境变量）。
_QWEN_LATEST_LINK = os.path.expanduser("~/.qwen/debug/latest")

# Codex CLI 当前 thread id 环境变量。Codex 会把该值透传给子进程。
_CODEX_THREAD_ID_ENV = "CODEX_THREAD_ID"

# 模块级缓存（首次 detect_client 后填充）
_CACHED_RESULT: Optional[Tuple[str, str]] = None

# 调试开关（读环境变量 A2A_CLIENT_DETECT_DEBUG，仅控制日志，不参与判定）
_DEBUG = os.environ.get("A2A_CLIENT_DETECT_DEBUG", "").strip() in ("1", "true", "True", "yes")


# ============================================================
# 对外API1: 客户端Agent检测
# ============================================================
def detect_client() -> Tuple[str, str]:
    """
    识别当前加载本 skill 的客户端 Agent。
    执行路径判定 → 父进程链 → unknown 兜底；对识别出的 name 探测 version。
    结果缓存在模块级变量，后续调用直接返回。

    Returns:
        (name, version) 二元组。永不抛异常。
        未知时返回 ("unknown", "unknown")。
    """
    global _CACHED_RESULT
    if _CACHED_RESULT is not None:
        return _CACHED_RESULT
    # 依次尝试各检测策略，取第一个成功的结果
    detectors = [
        ("detect_by_path", lambda: _detect_by_path(__file__)),
        ("detect_by_env_marker", lambda: _detect_by_env_marker()),
        ("detect_by_parent_process", lambda: _detect_by_parent_process()),
    ]
    name = "unknown"
    for detector_name, detector in detectors:
        try:
            if result := detector():
                name = result
                break
        except Exception as e:
            _debug(f"{detector_name} raised: {e!r}")
    # 根据 name 探测版本
    version = "unknown"
    if name != "unknown":
        try:
            version = _probe_version(name)
        except Exception as e:
            _debug(f"probe_version raised: {e!r}")
    _CACHED_RESULT = (name, version)
    _debug(f"detect_client: final result = {_CACHED_RESULT}")
    return _CACHED_RESULT


# ============================================================
# 步骤 1：skill 安装路径判定
# ============================================================
def _detect_by_path(file_path: str) -> Optional[str]:
    """
    基于 __file__ 的绝对路径，上溯各级父目录匹配 _PATH_PATTERNS。

    Args:
        file_path: 通常传入本模块的 __file__

    Returns:
        命中的 agent_name；未命中返回 None
    """
    abs_path = os.path.abspath(file_path)
    _debug(f"detect_by_path: abs_path={abs_path}")
    # 直接对整条绝对路径做正则匹配（_PATH_PATTERNS 本身带 ^|/ 前缀约束）
    for pattern, name in _PATH_PATTERNS:
        if pattern.search(abs_path):
            _debug(f"detect_by_path: matched pattern={pattern.pattern!r} -> {name}")
            return name
    _debug("detect_by_path: no pattern matched")
    return None


# ============================================================
# 步骤 2：客户端专属环境标记判定
# ============================================================
def _detect_by_env_marker() -> Optional[str]:
    """
    只使用客户端专属运行期标记判断身份。

    不使用 CODEX_THREAD_ID、AGENTHUB_SESSION_ID 或 Claude session id 这类可能被
    子进程继承的会话变量，避免把从其他客户端启动的进程误判成对应客户端。
    """
    for name, env_names in _ENV_MARKERS:
        if any(os.environ.get(env_name) for env_name in env_names):
            _debug(f"detect_by_env_marker: matched {name}")
            return name
    _debug("detect_by_env_marker: no marker matched")
    return None


# ============================================================
# 步骤 3：父进程链扫描
# ============================================================
def _detect_by_parent_process() -> Optional[str]:
    """
    从当前 python 进程向上遍历 PPID 链，匹配 _PROC_PATTERNS。
    最多追溯 _MAX_PPID_HOPS 层；PPID=1（init/launchd）或读取失败即停止。
    Returns:
        命中的 agent_name；未命中返回 None
    """
    pid = os.getppid()
    _debug(f"detect_by_parent_process: start ppid={pid}")
    for hop in range(_MAX_PPID_HOPS):
        if pid <= 1:
            _debug(f"detect_by_parent_process: reached pid={pid}, stop")
            break
        info = _read_proc_info(pid)
        if info is None:
            _debug(f"detect_by_parent_process: pid={pid} unreadable, stop")
            break
        comm, args, ppid = info
        basename = _extract_basename(comm, args)
        _debug(f"detect_by_parent_process: hop={hop} pid={pid} comm={comm!r} basename={basename!r} ppid={ppid}")
        for needle, name in _PROC_PATTERNS:
            if basename == needle:
                _debug(f"detect_by_parent_process: matched basename={basename!r} -> {name}")
                return name
        if ppid == pid:  # 理论不会发生，防御死循环
            break
        pid = ppid
    _debug("detect_by_parent_process: no match")
    return None


def _detect_by_codex_env() -> Optional[str]:
    """
    不再使用 Codex thread 环境变量作为客户端身份兜底。

    ``CODEX_THREAD_ID`` 只能在已经通过路径或父进程识别为 Codex 后作为
    session ID 使用；其他客户端可能继承该环境变量，不能据此判定当前
    客户端就是 Codex。
    """
    _debug("detect_by_codex_env: disabled")
    return None


def _read_proc_info(pid: int) -> Optional[Tuple[str, str, int]]:
    """
    读取指定 PID 的 (comm, args, ppid)。

    使用 `ps -o ppid=,comm=,args= -p <pid>`：
      - comm  是可执行文件的 basename（macOS/Linux 一致）
      - args  是完整命令行
      - ppid  是父进程 PID

    Returns:
        (comm, args, ppid)；读取失败返回 None。
    """
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=,comm=,args=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        _debug(f"read_proc_info({pid}): ps failed: {e!r}")
        return None
    if result.returncode != 0:
        return None
    # ps 输出格式："  PPID COMM        ARGS..."，首列为 ppid，其后是 comm，再是 args
    # 用 split(None, 2) 最多切 3 段
    parts = result.stdout.strip().split(None, 2)
    if len(parts) < 2:
        return None
    try:
        ppid = int(parts[0])
    except ValueError:
        return None
    comm = parts[1]
    args = parts[2] if len(parts) == 3 else ""
    return comm, args, ppid


def _extract_basename(comm: str, args: str) -> str:
    """
    从 ps 的 comm/args 字段提取可执行文件 basename。

    优先用 comm（已是 basename）；若 comm 为空则从 args 首 token 的路径尾部提取。
    进一步去除常见后缀（.exe）以便跨平台匹配。
    """
    candidate = comm.strip() if comm else ""
    if not candidate and args:
        first_token = args.strip().split()[0] if args.strip() else ""
        candidate = os.path.basename(first_token)
    # 去 .exe 后缀
    if candidate.lower().endswith(".exe"):
        candidate = candidate[:-4]
    return candidate.lower()


# ============================================================
# 版本探测
# ============================================================
def _probe_version(name: str) -> str:
    """
    执行 `<cli> --version` 获取版本号。

    - 5s 硬超时
    - 任何异常（超时/不存在/解析失败）→ "unknown"
    - 成功时返回匹配到的第一个 x.y(.z) 串
    """
    if name == "qoderwork":
        return _probe_qoderwork_version()
    cmd = _VERSION_COMMANDS.get(name)
    if not cmd:
        _debug(f"probe_version({name}): no command registered -> unknown")
        return "unknown"
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_VERSION_PROBE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        _debug(f"probe_version({name}): timeout after {_VERSION_PROBE_TIMEOUT}s -> unknown")
        return "unknown"
    except Exception as e:
        _debug(f"probe_version({name}): failed to run command: {e!r} -> unknown")
        return "unknown"
    # 合并 stdout/stderr，部分 CLI 把 --version 输出写到 stderr
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    match = _VERSION_RE.search(output)
    if not match:
        _debug(f"probe_version({name}): no version regex match in output={output!r} -> unknown")
        return "unknown"
    version = match.group(1)
    _debug(f"probe_version({name}): parsed version={version}")
    return version


def _probe_qoderwork_version(app_paths=None) -> str:
    """
    从 QoderWork macOS app bundle 的 Info.plist 读取桌面端版本。

    本函数只应在调用方已经确认客户端是 qoderwork 后使用；不能作为其他
    客户端的版本兜底。优先使用传入的 app_paths，未传时通过 bundle id
    定位已安装应用，再回退到常见安装路径。
    """
    candidates = app_paths if app_paths is not None else _qoderwork_app_candidates()
    for app_path in candidates:
        version = _read_qoderwork_bundle_version(Path(app_path))
        if version:
            return version
    return "unknown"


def _qoderwork_app_candidates() -> list[Path]:
    candidates: list[Path] = []
    try:
        result = subprocess.run(
            ["mdfind", f'kMDItemCFBundleIdentifier == "{_QODERWORK_BUNDLE_ID}"'],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if result.returncode == 0:
            candidates.extend(Path(line.strip()) for line in result.stdout.splitlines() if line.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        _debug(f"qoderwork_app_candidates: mdfind failed: {e!r}")
    candidates.extend(_QODERWORK_APP_FALLBACKS)
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def _read_qoderwork_bundle_version(app_path: Path) -> str:
    info_plist = app_path / "Contents" / "Info.plist"
    try:
        data = plistlib.loads(info_plist.read_bytes())
    except (OSError, plistlib.InvalidFileException, ValueError) as e:
        _debug(f"read_qoderwork_bundle_version({app_path}): failed: {e!r}")
        return "unknown"
    if data.get("CFBundleIdentifier") != _QODERWORK_BUNDLE_ID:
        _debug(f"read_qoderwork_bundle_version({app_path}): bundle id mismatch")
        return "unknown"
    raw_version = str(data.get("CFBundleShortVersionString") or data.get("CFBundleVersion") or "")
    match = _VERSION_RE.search(raw_version)
    if not match:
        _debug(f"read_qoderwork_bundle_version({app_path}): no version in {raw_version!r}")
        return "unknown"
    return match.group(1)


# ============================================================
# # 对外API2: 客户端qwen-code 专用 session-id 探测
# ============================================================
def detect_qwen_session_id() -> Optional[str]:
    """
    从 qwen-code 的会话软链 ~/.qwen/debug/latest 解析当前 session-id。

    实现语义（与 qwen-code 官方定位当前会话的方式一致）::

        basename $(readlink ~/.qwen/debug/latest) | sed 's/\\.txt$//'

    Returns:
        session-id 字符串（如 ``"a57f9d77-2bae-46ea-85bd-892a3cc4b18f"``）；
        任何异常或不满足格式（软链不存在、不是软链、target basename 非 ``*.txt``、
        去后缀后为空）→ 返回 ``None``。

    设计约束：
      - **不抛异常**：调用方按 None 分支走统一中断策略，避免在识别层决定流程。
      - **不做缓存**：`~/.qwen/debug/latest` 会在 qwen-code 运行期内随会话切换实时更新，
        每次调用都走一次 readlink 以拿到最新值（与 `detect_client()` 的模块级缓存
        语义故意不同：client_name/version 在单进程内是恒定的，session-id 不是）。
      - **只负责解析**，不做归属校验（不关心当前进程是否真的由 qwen 启动）。
        是否调用本函数由上层按 `detect_client()` 结果决定。
    """
    try:
        if not os.path.islink(_QWEN_LATEST_LINK):
            _debug(f"detect_qwen_session_id: {_QWEN_LATEST_LINK} is not a symlink")
            return None
        target = os.readlink(_QWEN_LATEST_LINK)
        basename = os.path.basename(target)
        stem, suffix = os.path.splitext(basename)
        if suffix != ".txt" or not stem:
            _debug(f"detect_qwen_session_id: unexpected symlink target {target!r}")
            return None
        _debug(f"detect_qwen_session_id: resolved session_id={stem}")
        return stem
    except (OSError, ValueError) as e:
        _debug(f"detect_qwen_session_id: error {e!r}")
        return None


# ============================================================
# # 对外API3: 客户端 codex 专用 session-id 探测
# ============================================================
def detect_codex_session_id() -> Optional[str]:
    """
    从 Codex CLI 暴露的 CODEX_THREAD_ID 环境变量读取当前 thread id。

    Returns:
        当前 Codex thread id；环境变量不存在或为空时返回 ``None``。

    设计约束：
      - **不抛异常**：调用方按 None 分支走统一中断策略。
      - **不做缓存**：每次读取当前进程环境，保持和调用时环境一致。
      - **不校验 UUID 格式**：只要求非空，路径安全由存储层统一处理。
    """
    value = os.environ.get(_CODEX_THREAD_ID_ENV, "").strip()
    if not value:
        _debug(f"detect_codex_session_id: {_CODEX_THREAD_ID_ENV} is empty")
        return None
    _debug(f"detect_codex_session_id: resolved session_id={value}")
    return value


# ============================================================
# # 对外API4: 客户端Agent UA标识构造
# ============================================================
def client_header_value() -> str:
    """
    返回 HTTP User-Agent header 用的完整字符串。

    形如：``AlibabaCloud-Agent-Skills/alibabacloud-remote-skills-connector/<session-id>
    <name>/<version>``。

    遵循 RFC 9110 User-Agent 语法：以产品标识 + 空格 + 组件标识 的形式组合，
    远程服务端可据此同时识别调用 skill
    与"承载它的客户端 Agent（name/version）"。

    结果由 detect_client() 的缓存支撑，重复调用无额外开销。
    """
    name, version = detect_client()
    return build_user_agent(f"{name}/{version}")


# ============================================================
# 内部工具
# ============================================================
def _debug(msg: str) -> None:
    """debug 日志打印到 stderr（不污染 stdout，避免破坏脚本主输出）"""
    if _DEBUG:
        sys.stderr.write(f"[client_detect] {msg}\n")
        sys.stderr.flush()
