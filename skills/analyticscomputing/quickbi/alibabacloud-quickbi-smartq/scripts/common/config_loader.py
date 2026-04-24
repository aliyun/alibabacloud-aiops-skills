# -*- coding: utf-8 -*-
"""
QBI 小Q问数配置加载器。

实现四层配置分层加载，确保用户配置不受技能包更新影响。

加载优先级（低 → 高）：
1. default_config.yaml — 包内默认值，随技能包发布
2. ~/.qbi/config.yaml — QBI 全局配置，所有 skill 共享
3. $WORKSPACE_DIR/.qbi/smartq-chat/config.yaml — 工作目录级配置（由 --workspace-dir 参数或 WORKSPACE_DIR 环境变量指定，必须显式传入）
4. ACCESS_TOKEN 环境变量 — 最高优先级，适合容器部署
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BASE_DIR.parent.parent / "default_config.yaml"

QBI_HOME = Path.home() / ".qbi"
GLOBAL_CONFIG_PATH = QBI_HOME / "config.yaml"

SKILL_NAME = "smartq-chat"

# 由 CLI --workspace-dir 参数设置，优先级最高
_workspace_dir_override: Optional[str] = None


def set_workspace_dir(path: str):
    """设置工作目录路径（由脚本入口通过 --workspace-dir 参数调用）。"""
    global _workspace_dir_override
    _workspace_dir_override = path


def _resolve_work_dir() -> Path:
    """获取用户实际工作目录。

    优先级：CLI --workspace-dir 参数 > WORKSPACE_DIR 环境变量。
    两者均未设置时直接报错，禁止静默降级到 HOME 目录（会导致配置读取错误）。
    """
    # 1. CLI 参数（最高优先级）
    if _workspace_dir_override:
        work_dir = Path(_workspace_dir_override)
        print(f"[配置] 工作目录: {work_dir} (来源=--workspace-dir 参数)", flush=True)
        return work_dir
    # 2. 环境变量
    env_cwd = os.environ.get("WORKSPACE_DIR")
    if env_cwd:
        work_dir = Path(env_cwd)
        print(f"[配置] 工作目录: {work_dir} (来源=WORKSPACE_DIR 环境变量)", flush=True)
        return work_dir
    # 3. 未设置 → 报错，要求 agent 显式传入
    raise RuntimeError(
        "[配置错误] 工作目录未设置！--workspace-dir 参数和 WORKSPACE_DIR 环境变量均未提供。\n"
        "请通过 --workspace-dir 参数传入用户实际工作目录的绝对路径后重新执行脚本。\n"
        "示例: python3 script.py ... --workspace-dir '/path/to/workspace'"
    )


def get_skill_work_home() -> Path:
    """$WORKSPACE_DIR/.qbi（工作目录级 QBI 根目录）"""
    return _resolve_work_dir() / ".qbi"


def get_skill_config_dir() -> Path:
    """$WORKSPACE_DIR/.qbi/smartq-chat/"""
    return get_skill_work_home() / SKILL_NAME


def get_skill_config_path() -> Path:
    """$WORKSPACE_DIR/.qbi/smartq-chat/config.yaml"""
    return get_skill_config_dir() / "config.yaml"


def get_skill_output_dir() -> Path:
    """$WORKSPACE_DIR/.qbi/smartq-chat/output/"""
    return get_skill_config_dir() / "output"


def get_image_output_dir() -> Path:
    """$WORKSPACE_DIR/output/（仅用于图片产物，便于用户直接查看）"""
    return _resolve_work_dir() / "output"



# ---------------------------------------------------------------------------
# 试用凭证常量与解码器
# ---------------------------------------------------------------------------

# 注意：以下为试用凭证的 base64 编码，仅用于避免明文展示，并非加密措施。
# 任何人可通过 base64 解码还原原始值。正式环境请使用用户自有凭证。
_R0 = "__BI_TRAIL_AK__"
_R1 = "__BI_TRAIL_SK__"


def _rv(v: str) -> str:
    return base64.b64decode(v).decode("utf-8")


# ---------------------------------------------------------------------------
# 试用欢迎提示
# ---------------------------------------------------------------------------

_TRIAL_WELCOME_MSG = """
============================================================
您的超级数据分析师已就位！
只需自然语言提问，即可智能匹配并分析您的 Excel 或 Quick BI 数据集，
将洞察即时呈现。让复杂分析，从未如此简单。

检测到您尚未配置凭证，我们将自动为您注册试用凭证并进入试用期。

试用到期后，请前往 Quick BI 控制台获取正式凭证：
  https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205

如需帮助，请扫码加入交流群获取最新资讯：
  https://at.umtrack.com/r4Tnme
============================================================
""".strip()


def _print_trial_welcome():
    print(f"\n{_TRIAL_WELCOME_MSG}\n", flush=True)


# ---------------------------------------------------------------------------
# 试用到期检测
# ---------------------------------------------------------------------------

TRIAL_EXPIRED_CODE = "AE0579100004"

_TRIAL_EXPIRED_MESSAGE = """
============================================================
小 Q 超级分析助理已陪伴您一周，我们看到您在通过 AI 寻找数据背后的真相，这很了不起。

🕙 试用模式已结束
授权到期后，动态分析将暂告一段落。

💡 其实，您可以更轻松
目前的"文件模式"仍需您手动搬运数据。让 AI 直连企业存量数据资产，实现分析结果自动更新？立即体验完整功能。

🚀 0 元体验，限时加码
现在上阿里云，将额外赠送 30 天全功能体验，解锁企业级安全管控与深度分析引擎，让 AI 洞察更准、更稳。点击下方链接，领取试用：
https://www.aliyun.com/product/quickbi-smart?utm_content=g_1000411205

💬 点击下方链接，进入交流群获取最新资讯：
https://at.umtrack.com/r4Tnme
============================================================
""".strip()


def check_trial_expired(result) -> bool:
    """检查 API 响应是否包含试用到期错误码，如果是则打印提示信息。

    Args:
        result: API 响应 dict 或原始文本 str。

    Returns:
        True 表示检测到试用到期，False 表示非此错误。
    """
    code = None
    if isinstance(result, dict):
        code = str(result.get("code", ""))
    elif isinstance(result, str):
        if TRIAL_EXPIRED_CODE in result:
            code = TRIAL_EXPIRED_CODE

    if code == TRIAL_EXPIRED_CODE:
        print(f"\n{_TRIAL_EXPIRED_MESSAGE}", flush=True)
        return True
    return False


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """安全加载 YAML 文件，文件不存在或解析失败返回空 dict。"""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _merge_config(base: dict, override: dict) -> dict:
    """将 override 中的非空值合并到 base 中。"""
    for key, value in override.items():
        if value is not None and str(value).strip() != "":
            base[key] = value
    return base


def load_config() -> dict:
    """四层配置加载。

    加载优先级（高覆盖低）：
    1. default_config.yaml（包内默认值）
    2. ~/.qbi/config.yaml（QBI 全局配置）
    3. $WORKSPACE_DIR/.qbi/smartq-chat/config.yaml（工作目录级配置）
    4. ACCESS_TOKEN 环境变量（最高优先级）
    """
    # --- 第 1 层：包内默认配置 ---
    print(
        f"[配置] 包内默认配置路径: {DEFAULT_CONFIG_PATH}"
        f" (存在={DEFAULT_CONFIG_PATH.exists()})",
        flush=True,
    )
    config = _load_yaml(DEFAULT_CONFIG_PATH)

    # --- 提前读取工作目录级配置，用于判断 save_global_property 开关 ---
    skill_config_path = get_skill_config_path()
    print(
        f"[配置] 工作目录级配置路径: {skill_config_path}"
        f" (存在={skill_config_path.exists()})",
        flush=True,
    )
    skill_config = _load_yaml(skill_config_path)

    # 判断 save_global_property 开关（仅从工作目录级 > 默认配置两层取值）
    _global_enabled = True
    for _cfg in (skill_config, config):
        _val = _cfg.get("save_global_property")
        if _val is not None:
            _global_enabled = bool(_val)
            break

    # --- 第 2 层：QBI 全局配置（受 save_global_property 开关控制） ---
    if _global_enabled:
        print(
            f"[配置] 全局配置路径: {GLOBAL_CONFIG_PATH}"
            f" (存在={GLOBAL_CONFIG_PATH.exists()})",
            flush=True,
        )
        global_config = _load_yaml(GLOBAL_CONFIG_PATH)
        _merge_config(config, global_config)
    else:
        print(
            f"[配置] save_global_property 为 false，跳过全局配置读取"
            f" (路径={GLOBAL_CONFIG_PATH})",
            flush=True,
        )

    # --- 第 3 层：工作目录级配置（已提前读取，直接合并） ---
    _merge_config(config, skill_config)

    # --- 第 4 层：环境变量覆盖（最高优先级） ---
    if config.get("use_env_property"):
        access_token = os.environ.get("ACCESS_TOKEN")
        if not access_token:
            raise ValueError("use_env_property 为 true 时，必须设置 ACCESS_TOKEN 环境变量")
        try:
            token_data = json.loads(access_token)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ACCESS_TOKEN 解析失败：{exc}") from exc

        env_mapping = {
            "qbi_api_key": "api_key",
            "qbi_api_secret": "api_secret",
            "qbi_server_domain": "server_domain",
            "qbi_user_token": "user_token",
        }
        for env_key, config_key in env_mapping.items():
            env_val = token_data.get(env_key)
            if env_val:
                config[config_key] = env_val

    # --- 试用凭证兜底 ---
    # 先检查全局配置和工作目录级配置原始文件中是否已有 api_key / api_secret
    # （不受 save_global_property 开关影响，避免已配置用户误入试用链路）
    # 注意：仅检查 api_key / api_secret，不检查 user_token。
    # user_token 可能来自试用自动注册（_persist_user_id force=True），
    # 单独存在 user_token 不代表用户已有自有凭证，不应阻止试用凭证填充。
    _raw_global_cfg = global_config if _global_enabled else _load_yaml(GLOBAL_CONFIG_PATH)
    _has_external_api_creds = (
        _raw_global_cfg.get("api_key") or _raw_global_cfg.get("api_secret")
        or skill_config.get("api_key") or skill_config.get("api_secret")
    )

    if _has_external_api_creds:
        # 全局配置或工作目录级配置已有 api_key/api_secret，不进入试用链路
        print("[配置] 检测到全局配置或工作目录级配置已有 API 凭证，跳过试用凭证填充", flush=True)
    else:
        missing_key = not config.get("api_key")
        missing_secret = not config.get("api_secret")
        missing_token = not config.get("user_token")

        if missing_key and missing_secret and missing_token:
            _print_trial_welcome()

        if missing_key:
            config["api_key"] = _rv(_R0)
        if missing_secret:
            config["api_secret"] = _rv(_R1)

    return config


# ---------------------------------------------------------------------------
# 服务域名获取
# ---------------------------------------------------------------------------


def get_server_domain(config: Optional[dict] = None) -> str:
    config = config or load_config()
    return str(config["server_domain"]).rstrip("/")


# ---------------------------------------------------------------------------
# 配置持久化
# ---------------------------------------------------------------------------

def persist_to_skill_config(key: str, value: str):
    """将单个配置项写入工作目录级配置文件。

    写入路径：$WORKSPACE_DIR/.qbi/smartq-chat/config.yaml
    """
    config_dir = get_skill_config_dir()
    config_path = get_skill_config_path()
    _persist_to_yaml(
        config_dir,
        config_path,
        key,
        value,
        header=(
            "# Quick BI 用户配置（此文件不受技能包更新影响）\n"
            "# 配置优先级：此文件 > ~/.qbi/config.yaml > 包内 default_config.yaml\n"
            f"# 路径：{config_path}\n\n"
        ),
    )


def is_global_save_enabled() -> bool:
    """检查 save_global_property 开关是否开启。

    仅从工作目录级配置和包内默认配置中读取，不依赖全局配置本身。
    默认为 True。
    """
    skill_cfg = _load_yaml(get_skill_config_path())
    default_cfg = _load_yaml(DEFAULT_CONFIG_PATH)
    # 按优先级：工作目录级 > 默认
    for cfg in (skill_cfg, default_cfg):
        val = cfg.get("save_global_property")
        if val is not None:
            return bool(val)
    return True


def persist_to_global_config(key: str, value: str, *, force: bool = False):
    """将单个配置项写入 QBI 全局配置文件。

    写入路径：~/.qbi/config.yaml
    当 save_global_property 为 false 且 force=False 时，跳过写入并打印提示。
    试用凭证自动注册场景应使用 force=True 强制写入。
    """
    if not force and not is_global_save_enabled():
        print(
            f"[配置] save_global_property 为 false，跳过全局配置写入: {key}",
            flush=True,
        )
        return
    _persist_to_yaml(
        QBI_HOME,
        GLOBAL_CONFIG_PATH,
        key,
        value,
        header=(
            "# Quick BI 全局配置（所有 skill 共享，不受技能包更新影响）\n"
            "# 所有配置（server_domain、api_key、api_secret、user_token 等）建议放在此文件\n\n"
        ),
    )


def _persist_to_yaml(config_dir: Path, config_path: Path, key: str, value: str, header: str):
    """将单个键值对写入指定 YAML 配置文件。"""
    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = [header]

    found = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"{key}:"):
            lines[i] = f"{key}: {value}\n"
            found = True
            break

    if not found:
        lines.append(f"{key}: {value}\n")

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
