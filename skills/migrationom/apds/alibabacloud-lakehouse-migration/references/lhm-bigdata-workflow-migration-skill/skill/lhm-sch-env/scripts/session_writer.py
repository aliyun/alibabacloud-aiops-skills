#!/usr/bin/env python3
"""将用户填写的配置转写为本次会话的临时配置文件。

职责：
1. 定位用户填写的配置文件（`--from` > $LHM_CREDENTIALS_FILE > ./config/lhm_credentials.json
   > ~/.lhm/credentials.json）
2. 以用户配置为权威来源，按字段区分取值与校验规则：
   - 源/目标数据源名称：必须写在配置文件中，不接受环境变量或默认值兜底
     （仅迁移阶段必填；`--stage ds` 为纯数据源管理场景，不校验这两个字段）
   - endpoint/region：按“配置文件 > 环境变量 > 默认值”解析，不做必填校验
     （lhm 插件调用时已在环境变量中配好这两个值，无需本脚本拦截）
   - 凭证：本脚本不解析、不校验、不写入，由 aliyun CLI 默认凭证链在调用时解析
     （环境变量 / RAM Role / ~/.alibabacloud/credentials）
3. 校验必填项，占位符 `<YOUR_...>` 与模板示例值视为未填写
4. 写入系统临时目录下的会话配置文件（目录 0700 / 文件 0600），供本次会话的子 agent 加载

会话文件采用与 `lhm_credentials.template.json` 一致的**扁平结构**（endpoint、region、
源/目标数据源名称均为顶层键），各 CLI 按同名顶层键读取；凭证不写入会话文件，
由 aliyun CLI 默认凭证链解析。

安全：
- 会话文件仅落在当前用户的临时目录，权限 0600
- 本脚本不解析、不写入、不输出任何凭证
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PLACEHOLDER_PREFIX = "<"

# 模板（lhm_credentials.template.json）中的示例值不带 `<` 前缀，
# 但同样不是用户真实填写的内容 —— 直接复制模板不应通过校验。
TEMPLATE_PLACEHOLDER_VALUES = {
    "需要被迁移的数据源名称",
    "迁移到目标数据源名称",
}

# 会话根目录固定在 /tmp 下并携带 uid，**不使用 $TMPDIR**：
# tempfile.gettempdir() 的结果随 $TMPDIR 变化（终端/sandbox/CI/cron 各不相同），
# 一旦写入方与读取方的 $TMPDIR 不一致，子 agent 就会静默回退到环境变量，
# 造成“配置改了却不生效”的隐蔽故障。uid 后缀用于多用户机器上的隔离。
#
# 每次会话准备在根目录下新建独立子目录 s-<时间戳>-<随机串>/，
# 并把绝对路径写入指针文件 current，供读取方无环境变量时定位；
# 并行会话用 $LHM_SESSION_FILE 显式指定各自的会话文件，互不干扰。
SESSION_ROOT = Path("/tmp")
SESSION_DIR_NAME = "lhm-sch-session-%d" % getattr(os, "getuid", lambda: 0)()
SESSION_FILE_NAME = "session.json"
SESSION_POINTER_NAME = "current"
SESSION_FILE_ENV_VAR = "LHM_SESSION_FILE"

DEFAULT_ENDPOINT = "lhm-pre.cn-hangzhou.aliyuncs.com"
DEFAULT_REGION_ID = "cn-hangzhou"

# 用户配置文件候选路径（按就近优先）
USER_CONFIG_ENV_VAR = "LHM_CREDENTIALS_FILE"
USER_CONFIG_CANDIDATES = (
    Path("config") / "lhm_credentials.json",
    Path.home() / ".lhm" / "credentials.json",
)


# ---------------------------------------------------------------------------
# 会话文件路径
# ---------------------------------------------------------------------------

def session_root() -> Path:
    """会话根目录 /tmp/lhm-sch-session-<uid>/。"""
    return SESSION_ROOT / SESSION_DIR_NAME


def pointer_path() -> Path:
    """指针文件路径：记录当前会话 session.json 的绝对路径。"""
    return session_root() / SESSION_POINTER_NAME


def read_pointer() -> Optional[Path]:
    """读指针文件；目标不存在或指针损坏时返回 None。"""
    pointer = pointer_path()
    if not pointer.is_file():
        return None
    try:
        target = Path(pointer.read_text(encoding="utf-8").strip())
    except OSError:
        return None
    return target if target.is_file() else None


def session_file_path() -> Path:
    """解析当前会话配置文件路径（读取视角）。

    优先级：$LHM_SESSION_FILE > 指针文件 current > 旧版固定路径
    /tmp/lhm-sch-session-<uid>/session.json（兼容历史会话）。
    路径可被子 agent 直接推导（Agent 每次 Bash 调用都是独立 shell），
    重启后自然失效。目录 0700 + 文件 0600。
    """
    override = os.environ.get(SESSION_FILE_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    pointed = read_pointer()
    if pointed is not None:
        return pointed
    return session_root() / SESSION_FILE_NAME


def new_session_file_path() -> Path:
    """为本次会话生成独立的 session.json 路径（不创建文件）。

    目录形如 /tmp/lhm-sch-session-<uid>/s-<YYYYmmddHHMMSS>-<随机串>/，
    避免多个 QoderWork 会话共用同一目录导致配置互相覆盖、产物混杂。
    """
    session_id = "s-%s-%s" % (
        datetime.now().strftime("%Y%m%d%H%M%S"),
        secrets.token_hex(2),
    )
    return session_root() / session_id / SESSION_FILE_NAME


def write_pointer(target: Path) -> None:
    """把当前会话路径写入指针文件（文件 0600）。"""
    pointer = pointer_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(pointer.parent, 0o700)
    fd = os.open(str(pointer), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(str(target) + "\n")


# ---------------------------------------------------------------------------
# 读取与取值
# ---------------------------------------------------------------------------

def clean(value: Any) -> str:
    """规整取值：非字符串、空串、`<YOUR_...>` 占位符、模板示例值均视为未填写。"""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or value.startswith(PLACEHOLDER_PREFIX):
        return ""
    if value in TEMPLATE_PLACEHOLDER_VALUES:
        return ""
    return value


def pick(data: Dict[str, Any], section: str, key: str) -> str:
    """读取 `section.key`，回退到顶层同名 key（兼容扁平写法）。"""
    node = data.get(section)
    nested = node.get(key) if isinstance(node, dict) else None
    return clean(nested) or clean(data.get(key))


def locate_user_config(explicit: Optional[str]) -> Tuple[Optional[Path], List[str]]:
    """定位用户配置文件，返回 (路径, 告警列表)。"""
    warnings: List[str] = []
    candidates: List[Path] = []

    if explicit:
        candidates.append(Path(explicit).expanduser())
    else:
        env_path = os.environ.get(USER_CONFIG_ENV_VAR, "").strip()
        if env_path:
            candidates.append(Path(env_path).expanduser())
        candidates.extend(USER_CONFIG_CANDIDATES)

    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                json.load(handle)
        except (OSError, json.JSONDecodeError) as read_error:
            warnings.append(f"配置文件无法解析，已跳过 {candidate}：{read_error}")
            continue
        return candidate, warnings

    if explicit:
        warnings.append(f"指定的配置文件不存在或无法解析：{explicit}")
    return None, warnings


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# 合并
# ---------------------------------------------------------------------------

def resolve(
    user_config: Dict[str, Any],
    existing_session: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, str], List[str]]:
    """合并用户配置与环境变量（仅 endpoint/region 与业务字段，不含凭证）。

    优先级：用户配置文件 > 环境变量 > 默认值。
    用户配置是权威来源，环境变量只用于补齐缺失字段 —— 这样可以避免
    shell 中残留的旧值悄悄覆盖用户刚填好的配置。

    Args:
        user_config: 用户填写的配置内容。
        existing_session: 已存在的会话配置，用于保留运行时回写的字段
            （如 convert_task_id），避免重跑本脚本时把它们清空。

    Returns:
        (会话配置字典, 各字段来源标记, 告警列表)
    """
    origins: Dict[str, str] = {}
    warnings: List[str] = []

    def resolve_field(name: str, from_file: str, env_names: List[str], default: str = "") -> str:
        if from_file:
            origins[name] = "file"
            return from_file
        for env_name in env_names:
            env_value = clean(os.environ.get(env_name))
            if env_value:
                origins[name] = f"env:{env_name}"
                return env_value
        if default:
            origins[name] = "default"
            return default
        origins[name] = "missing"
        return ""

    endpoint = resolve_field(
        "endpoint",
        pick(user_config, "lhm", "endpoint"),
        ["LHM_ENDPOINT"],
        DEFAULT_ENDPOINT,
    )
    region_id = resolve_field(
        "region_id",
        pick(user_config, "lhm", "region_id"),
        ["REGION_ID"],
        DEFAULT_REGION_ID,
    )
    source_ds = resolve_field(
        "source_data_source_name",
        pick(user_config, "migration", "source_data_source_name"),
        [],
    )
    target_ds = resolve_field(
        "target_data_source_name",
        pick(user_config, "migration", "target_data_source_name"),
        [],
    )

    # 用户配置与环境变量不一致时给出提示：以配置文件为准，避免用户误以为环境变量生效
    for name, value, env_names in (
        ("endpoint", endpoint, ["LHM_ENDPOINT"]),
        ("region_id", region_id, ["REGION_ID"]),
    ):
        if origins.get(name) != "file":
            continue
        for env_name in env_names:
            env_value = clean(os.environ.get(env_name))
            if env_value and env_value != value:
                warnings.append(
                    f"{name}：配置文件与环境变量 {env_name} 不一致，已采用配置文件的值"
                )
                break

    session = {
        "endpoint": endpoint,
        "region_id": region_id,
        "source_data_source_name": source_ds,
        "target_data_source_name": target_ds,
    }

    # 保留运行时已回写的阶段产物（如 lhm-sch-read-exec 写入的 convert_task_id）：
    # 用户中途重跑本脚本（改了 endpoint 等）不应丢失已发起的转换任务，
    # 否则阶段④ 会因为取不到 task_id 而需要重新追问用户。
    # 但当源/目标数据源发生变更时，旧 task_id 已不再匹配，不能继续沿用。
    if isinstance(existing_session, dict):
        # 兼容旧版分节结构：顶层取不到时回退到 migration 段
        prev_migration = existing_session.get("migration")
        prev_migration = prev_migration if isinstance(prev_migration, dict) else {}

        def prev_value(key: str) -> str:
            return clean(existing_session.get(key)) or clean(prev_migration.get(key))

        same_source = prev_value("source_data_source_name") == source_ds
        same_target = prev_value("target_data_source_name") == target_ds
        for key in ("convert_task_id", "convert_task_created_at"):
            carried = prev_value(key)
            if not carried:
                continue
            if same_source and same_target:
                session[key] = carried
                origins[key] = "session"
            elif key == "convert_task_id":
                warnings.append(
                    "数据源已变更，上一次转换任务的 convert_task_id 已丢弃"
                )

    return session, origins, warnings


def validate(origins: Dict[str, str], stage: str = "all") -> List[str]:
    """校验必填项，返回阻塞项列表。

    仅校验业务字段：
    - 源/目标数据源名称：必须来自配置文件（无环境变量/默认值兜底），
      origin 非 file 即阻塞。

    阶段豁免：
    - `stage == "ds"` 表示本次会话只服务于数据源管理（建数据源 / 校验名称 /
      上传元数据 / 连通性测试），迁移链路根本不会执行，因此源/目标数据源名称
      不是必填项 —— 强行拦截会把“纯建数据源”误报成“卡在迁移参数上”，
      进而诱导上层去追问用户与本请求无关的迁移参数。

    注意：
    - endpoint / region_id 不在此校验 —— lhm 插件调用时已在环境变量中配置好，
      无需本脚本拦截。
    - 凭证不在此校验 —— 由 aliyun CLI 默认凭证链在调用时解析；缺失或错误会在
      环境检测（api_connectivity 探针）中以真实报错暴露，而非在此拦截或追问。
    """
    blockers: List[str] = []

    if stage == "ds":
        return blockers

    ds_labels = {
        "source_data_source_name": "source_data_source_name（源数据源名称）",
        "target_data_source_name": "target_data_source_name（目标数据源名称）",
    }
    for name, label in ds_labels.items():
        if origins.get(name) != "file":
            blockers.append(f"配置文件缺少 {label}")

    return blockers


# ---------------------------------------------------------------------------
# 写入 / 清理
# ---------------------------------------------------------------------------

def write_session(session: Dict[str, Any], source: Optional[Path], target: Path) -> None:
    """写入会话配置文件，目录 0700 / 文件 0600。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)

    payload = {
        "_generated_by": "lhm-sch-env/scripts/setup_session.sh",
        "_generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "_source": str(source) if source else "environment",
        "_warning": (
            "本文件由工具生成，不含任何凭证（凭证由 aliyun CLI 默认凭证链解析）。"
            "会话结束后执行 setup_session.sh --cleanup 删除。"
        ),
    }
    payload.update(session)

    # 先以 0600 创建再写入，避免默认 umask 造成的短暂宽权限窗口
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(target, 0o600)


def cleanup(target: Path) -> bool:
    """删除会话配置文件及其指针；返回是否实际删除。"""
    removed = False
    if target.exists():
        target.unlink()
        removed = True

    # 指针指向被删目标时一并清除，避免后续命令读到悬空指针
    pointer = pointer_path()
    if pointer.is_file():
        try:
            if pointer.read_text(encoding="utf-8").strip() == str(target):
                pointer.unlink()
        except OSError:
            pass

    # 自底向上清理空目录：会话子目录 s-*/ → 会话根目录
    parent = target.parent
    for candidate in (parent, parent.parent):
        if (
            candidate.name.startswith(("s-", "lhm-sch-session"))
            and candidate.is_dir()
            and not any(candidate.iterdir())
        ):
            candidate.rmdir()
    return removed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="session_writer.py",
        description="将用户配置转写为本次会话的临时配置文件",
    )
    parser.add_argument("--from", dest="from_path", help="显式指定用户配置文件路径")
    parser.add_argument(
        "--stage",
        default="all",
        choices=("ds", "read-exec", "deploy", "all"),
        help="本次会话服务的阶段；ds 表示仅数据源管理，不校验迁移源/目标数据源名称",
    )
    parser.add_argument("--check-only", action="store_true", help="只校验，不写会话文件")
    parser.add_argument("--cleanup", action="store_true", help="删除会话文件后退出")
    parser.add_argument("--print-path", action="store_true", help="输出会话文件路径后退出")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    # 读取视角的当前会话路径（env > 指针 > 旧版固定路径）
    current = session_file_path()

    if args.print_path:
        print(current)
        return 0

    if args.cleanup:
        removed = cleanup(current)
        print(json.dumps({
            "action": "cleanup",
            "removed": removed,
            "session_file": str(current),
        }, ensure_ascii=False, indent=2))
        return 0

    # 写入目标：显式指定（$LHM_SESSION_FILE）时复用该路径；
    # 否则每次准备都新建独立会话目录，避免多会话互相覆盖。
    # --check-only 不写文件，沿用当前路径仅作报告。
    explicit_target = os.environ.get(SESSION_FILE_ENV_VAR, "").strip()
    if explicit_target or args.check_only:
        target = current
    else:
        target = new_session_file_path()

    source, warnings = locate_user_config(args.from_path)
    user_config = load_json(source) if source else {}

    # 读取上一次会话配置（可能位于旧目录），以保留 convert_task_id 等回写字段
    existing_session: Optional[Dict[str, Any]] = None
    if current.is_file():
        try:
            existing_session = load_json(current)
        except (OSError, json.JSONDecodeError):
            existing_session = None

    session, origins, merge_warnings = resolve(user_config, existing_session)
    warnings.extend(merge_warnings)
    blockers = validate(origins, args.stage)

    # 数据源管理阶段不要求迁移业务字段：显式记一笔，避免上层把空值误读成“用户漏填”
    if args.stage == "ds" and not (
        session["source_data_source_name"] or session["target_data_source_name"]
    ):
        warnings.append(
            "数据源管理阶段（--stage ds）：未校验 source_data_source_name / "
            "target_data_source_name，迁移链路不在本次会话范围内"
        )

    written = False
    if not blockers and not args.check_only:
        try:
            write_session(session, source, target)
            # 未显式指定路径时更新指针，供后续无环境变量的命令定位本会话
            if not explicit_target:
                write_pointer(target)
            written = True
        except OSError as write_error:
            blockers.append(f"会话文件写入失败：{write_error}")

    result = {
        "ready": not blockers,
        "stage": args.stage,
        "session_file": str(target),
        "session_dir": str(target.parent),
        "session_written": written,
        "user_config": str(source) if source else "",
        "endpoint": session["endpoint"],
        "region_id": session["region_id"],
        "source_data_source_name": session["source_data_source_name"],
        "target_data_source_name": session["target_data_source_name"],
        "convert_task_id": session.get("convert_task_id", ""),
        "field_origins": origins,
        "blockers": blockers,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not blockers else 1


if __name__ == "__main__":
    sys.exit(main())
