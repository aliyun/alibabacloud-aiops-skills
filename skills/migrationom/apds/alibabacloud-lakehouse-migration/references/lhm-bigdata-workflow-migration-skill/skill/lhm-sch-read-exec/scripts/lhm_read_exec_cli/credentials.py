"""共享配置文件解析（会话配置 / 用户配置）。

本模块只负责定位并读取配置文件，供上层解析 endpoint / region 与业务字段
（数据源名称、convert_task_id 等）。凭证不在此处理：由 aliyun CLI 默认凭证链
在调用时解析（环境变量 / RAM Role / ~/.alibabacloud/credentials）。

配置文件查找优先级（从高到低）：
1. **会话配置文件**（由 lhm-sch-env 转写，位于临时目录）
2. 用户配置文件：$LHM_CREDENTIALS_FILE > ./config/lhm_credentials.json
   > ~/.lhm/credentials.json

会话配置排在最前是有意的：它是 lhm-sch-env 已经合并好的权威结果，
若让 shell 中残留的旧环境变量反过来覆盖它，会产生“配置改了却不生效”的故障。

会话配置文件路径：$LHM_SESSION_FILE，默认 /tmp/lhm-sch-session-<uid>/session.json

配置文件为 JSON，扁平或嵌套写法均可：

    {
      "endpoint": "lhm-pre.cn-hangzhou.aliyuncs.com",
      "region_id": "cn-hangzhou"
    }

嵌套写法（会话配置与 deploy_config.json 均采用）同样被识别：
`lhm.endpoint` / `lhm.region_id`。
"""

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

CREDENTIALS_FILE_ENV_VAR = "LHM_CREDENTIALS_FILE"
WORKSPACE_CREDENTIALS_PATH = Path("config") / "lhm_credentials.json"
USER_CREDENTIALS_PATH = Path.home() / ".lhm" / "credentials.json"

# 会话根目录固定在 /tmp 下并携带 uid，**不使用 $TMPDIR**：
# $TMPDIR 在终端/sandbox/CI/cron 下取值不同，若以它为基准，写入方（lhm-sch-env）
# 与读取方（本 CLI）可能算出不同路径，导致会话配置被静默忽略。
# 本常量与解析顺序必须与 lhm-sch-env/scripts/session_writer.py 保持一致：
# 每次会话准备会新建独立子目录 s-<时间戳>-<随机串>/，指针文件 current 指向当前会话。
SESSION_ROOT = Path("/tmp")
SESSION_DIR_NAME = "lhm-sch-session-%d" % getattr(os, "getuid", lambda: 0)()
SESSION_FILE_NAME = "session.json"
SESSION_POINTER_NAME = "current"
SESSION_FILE_ENV_VAR = "LHM_SESSION_FILE"

PLACEHOLDER_PREFIX = "<"


def _read_pointer() -> Optional[Path]:
    """读会话指针文件；目标不存在或指针损坏时返回 None。"""
    pointer = SESSION_ROOT / SESSION_DIR_NAME / SESSION_POINTER_NAME
    if not pointer.is_file():
        return None
    try:
        target = Path(pointer.read_text(encoding="utf-8").strip())
    except OSError:
        return None
    return target if target.is_file() else None


def session_file_path() -> Path:
    """会话配置文件路径（解析顺序必须与 session_writer.py 完全一致）。

    优先级：$LHM_SESSION_FILE > 指针文件 current > 旧版固定路径。
    """
    override = os.environ.get(SESSION_FILE_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    pointed = _read_pointer()
    if pointed is not None:
        return pointed
    return SESSION_ROOT / SESSION_DIR_NAME / SESSION_FILE_NAME


def session_dir_path() -> Path:
    """会话临时目录（会话配置与结果产物的共同根目录，随会话文件所在目录）。"""
    return session_file_path().parent


@dataclass(frozen=True)
class CredentialFile:
    """已解析的凭证文件内容及其来源路径。"""

    path: Path
    data: Dict[str, Any]

    def value(self, section: str, key: str) -> str:
        """读取 `section.key`，回退到顶层同名 key；占位符视为未填写。"""
        raw = self.data.get(section, {})
        nested = raw.get(key) if isinstance(raw, dict) else None
        candidate = nested if nested else self.data.get(key)
        if not isinstance(candidate, str):
            return ""
        candidate = candidate.strip()
        if not candidate or candidate.startswith(PLACEHOLDER_PREFIX):
            return ""
        return candidate


def search_paths() -> list:
    """返回凭证文件候选路径，会话配置优先，其余按就近优先排序。"""
    paths = [session_file_path()]
    explicit = os.environ.get(CREDENTIALS_FILE_ENV_VAR, "").strip()
    if explicit:
        paths.append(Path(explicit).expanduser())
    paths.append(WORKSPACE_CREDENTIALS_PATH)
    paths.append(USER_CREDENTIALS_PATH)
    return paths


def load_session_file() -> Optional["CredentialFile"]:
    """仅加载会话配置文件（若存在且可解析）。

    用于让会话配置的优先级高于用户配置文件：会话配置是 lhm-sch-env 已合并好的
    权威结果。凭证不由本模块解析，故不再以 AK/SK 是否存在作为加载门控。
    """
    path = session_file_path()
    if not path.is_file():
        return None
    return _read_credential_file(path)


def _read_credential_file(path: Path) -> Optional[CredentialFile]:
    """读取单个凭证文件；无法读取或格式不对时告警并返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as read_error:
        print(f"⚠️  凭证文件读取失败，已跳过 {path}: {read_error}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"⚠️  凭证文件格式应为 JSON 对象，已跳过 {path}", file=sys.stderr)
        return None
    _warn_if_permissive(path)
    return CredentialFile(path=path, data=data)


def load_credential_file() -> Optional[CredentialFile]:
    """加载第一个存在且可解析的凭证文件；全部缺失时返回 None。

    解析失败（JSON 非法、权限不足）时向 stderr 告警并继续尝试下一候选，
    避免因为一个损坏的文件导致整条链路失败。
    """
    for path in search_paths():
        if not path.is_file():
            continue
        loaded = _read_credential_file(path)
        if loaded is not None:
            return loaded
    return None


def _warn_if_permissive(path: Path) -> None:
    """凭证文件对同组/其他用户可读时告警，提示收紧为 600。"""
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(
            f"⚠️  配置文件权限过宽: {path} —— 建议执行 chmod 600 {path}",
            file=sys.stderr,
        )
