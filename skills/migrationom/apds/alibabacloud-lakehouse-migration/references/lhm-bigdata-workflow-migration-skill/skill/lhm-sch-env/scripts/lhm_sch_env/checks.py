"""环境检查项实现：api_connectivity / resource_group / agent。

配置来源：本模块只从会话/用户配置文件解析 endpoint 与 region；
凭证由 aliyun CLI 默认凭证链在调用时解析（环境变量 / RAM Role /
~/.alibabacloud/credentials），本模块不读取、不校验任何凭证；若凭证
缺失或错误，会在探针调用中以真实报错暴露。

网络层：通过 aliyun CLI（aliyun-cli-lhm 插件）调用 LHM API。
"""

from __future__ import annotations

import json
import os
import stat
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 配置解析（仅 endpoint/region；凭证由 aliyun CLI 默认凭证链处理）
# ---------------------------------------------------------------------------

_CREDENTIALS_FILE_ENV_VAR = "LHM_CREDENTIALS_FILE"
_WORKSPACE_CREDENTIALS_PATH = Path("config") / "lhm_credentials.json"
_USER_CREDENTIALS_PATH = Path.home() / ".lhm" / "credentials.json"

_SESSION_ROOT = Path("/tmp")
_SESSION_DIR_NAME = "lhm-sch-session-%d" % getattr(os, "getuid", lambda: 0)()
_SESSION_FILE_NAME = "session.json"
_SESSION_POINTER_NAME = "current"
_SESSION_FILE_ENV_VAR = "LHM_SESSION_FILE"

_PLACEHOLDER_PREFIX = "<"


def _read_pointer() -> Optional[Path]:
    """读会话指针文件；目标不存在或指针损坏时返回 None。"""
    pointer = _SESSION_ROOT / _SESSION_DIR_NAME / _SESSION_POINTER_NAME
    if not pointer.is_file():
        return None
    try:
        target = Path(pointer.read_text(encoding="utf-8").strip())
    except OSError:
        return None
    return target if target.is_file() else None


def _session_file_path() -> Path:
    """会话配置文件路径（解析顺序与 session_writer.py 完全一致）。"""
    override = os.environ.get(_SESSION_FILE_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    pointed = _read_pointer()
    if pointed is not None:
        return pointed
    return _SESSION_ROOT / _SESSION_DIR_NAME / _SESSION_FILE_NAME


def _resolve_value(data: Dict[str, Any], key: str) -> str:
    """从配置字典中读取值，支持嵌套（credentials.key / lhm.key）和扁平写法。

    占位符 `<YOUR_...>` 视为未填写，返回空字符串。
    """
    # 尝试嵌套写法：credentials.key / lhm.key
    for section in ("credentials", "lhm"):
        nested = data.get(section)
        if isinstance(nested, dict):
            candidate = nested.get(key)
            if isinstance(candidate, str) and candidate.strip():
                val = candidate.strip()
                if not val.startswith(_PLACEHOLDER_PREFIX):
                    return val

    # 回退到顶层 key
    candidate = data.get(key)
    if isinstance(candidate, str) and candidate.strip():
        val = candidate.strip()
        if not val.startswith(_PLACEHOLDER_PREFIX):
            return val

    return ""


def _read_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """安全读取 JSON 文件，失败时向 stderr 告警并返回 None。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as err:
        print(f"⚠️  凭证文件读取失败，已跳过 {path}: {err}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"⚠️  凭证文件格式应为 JSON 对象，已跳过 {path}", file=sys.stderr)
        return None
    _warn_if_permissive(path)
    return data


def _warn_if_permissive(path: Path) -> None:
    """凭证文件权限过宽时告警。"""
    try:
        mode = path.stat().st_mode
    except OSError:
        return
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(
            f"⚠️  凭证文件权限过宽: {path} —— 建议执行 chmod 600 {path}",
            file=sys.stderr,
        )


def load_config(explicit_session_file: Optional[str] = None) -> Dict[str, Any]:
    """加载 endpoint/region 配置（不含凭证），返回含 endpoint/region_id 的字典。

    凭证由 aliyun CLI 默认凭证链在调用时解析，本函数只负责 endpoint/region。

    配置文件优先级：
    1. 显式指定的 session 文件路径
    2. 会话配置文件（$LHM_SESSION_FILE > 指针 current > 旧版固定路径）
    3. 用户配置文件 $LHM_CREDENTIALS_FILE > ./config/lhm_credentials.json
       > ~/.lhm/credentials.json

    endpoint/region 按“配置文件 > 环境变量 LHM_ENDPOINT/REGION_ID > 默认值”解析。
    """
    sources: List[Path] = []
    if explicit_session_file:
        sources.append(Path(explicit_session_file))
    sources.append(_session_file_path())
    explicit_cred = os.environ.get(_CREDENTIALS_FILE_ENV_VAR, "").strip()
    if explicit_cred:
        sources.append(Path(explicit_cred).expanduser())
    sources.append(_WORKSPACE_CREDENTIALS_PATH)
    sources.append(_USER_CREDENTIALS_PATH)

    data: Dict[str, Any] = {}
    for path in sources:
        if not path.is_file():
            continue
        loaded = _read_json_file(path)
        if loaded is None:
            continue
        data = loaded
        if _resolve_value(data, "endpoint") or _resolve_value(data, "region_id"):
            break

    endpoint = (
        _resolve_value(data, "endpoint")
        or os.environ.get("LHM_ENDPOINT", "").strip()
        or "lhm-pre.cn-hangzhou.aliyuncs.com"
    )
    region_id = (
        _resolve_value(data, "region_id")
        or os.environ.get("REGION_ID", "").strip()
        or "cn-hangzhou"
    )
    return {"endpoint": endpoint, "region_id": region_id}


# ---------------------------------------------------------------------------
# SDK Client 构建
# ---------------------------------------------------------------------------

_FALLBACK_SESSION_ID = ""


def _build_user_agent() -> str:
    """Observability UA：AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{version}。

    session-id 优先取环境变量 LHM_SESSION_ID（dispatcher 会话开始时生成一次，
    全会话复用）；未设置时每进程兜底生成一次并缓存，保证 UA 始终存在且
    同进程内多次调用一致。
    """
    global _FALLBACK_SESSION_ID
    session_id = os.environ.get("LHM_SESSION_ID", "").strip()
    if not session_id:
        if not _FALLBACK_SESSION_ID:
            _FALLBACK_SESSION_ID = uuid.uuid4().hex
        session_id = _FALLBACK_SESSION_ID
    version = os.environ.get("LHM_SKILL_VERSION", "").strip() or "1.0.0"
    return f"AlibabaCloud-Agent-Skills/lhm-sch-env/{session_id} skill-version/{version}"


def _build_client(config: Dict[str, Any]):
    """根据 session.json 配置构建 LHM CLI Client。"""
    from .aliyun_cli import AliyunCliClient

    endpoint = config.get("endpoint", "")
    region_id = config.get("region_id", "cn-hangzhou")

    if not endpoint:
        return None

    return AliyunCliClient(
        endpoint=endpoint,
        region_id=region_id,
        skill_name="lhm-sch-env",
    )


# ---------------------------------------------------------------------------
# 检查项实现
# ---------------------------------------------------------------------------

def _check_api_connectivity(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证 LHM API 可达性。

    使用 GetDataCheckTaskList(page_index=1, page_size=1) 作为连通性探针，
    与 lhm-common 保持一致。凭证由 aliyun CLI 默认凭证链解析；若缺失或错误，
    会在探针调用中以真实报错暴露（status=fail），而非提前 skip。
    """
    region_id = config.get("region_id", "cn-hangzhou")

    client = _build_client(config)
    if client is None:
        return {
            "name": "api_connectivity",
            "status": "fail",
            "message": "无法构建 LHM Client，请检查 endpoint 配置",
            "fix_guide": "确认 session.json 中 endpoint 字段正确且网络可达。",
            "blocking": True,
        }

    try:
        # 使用 dict 作为请求参数，避免依赖 SDK models
        # 注意：invoke() 对键做 camelCase->kebab-case 转换，这里必须用 camelCase，
        # 否则会生成 --page_index 这类插件不认的下划线 flag。
        request = {"pageIndex": 1, "pageSize": 1}
        response = client.get_data_check_task_list(request)
        body = response.body

        if getattr(body, "success", False):
            return {
                "name": "api_connectivity",
                "status": "pass",
                "message": f"LHM endpoint 可达 (region={region_id})",
            }

        err_code = getattr(body, "err_code", "UNKNOWN")
        err_msg = getattr(body, "err_message", "未知错误")
        return {
            "name": "api_connectivity",
            "status": "fail",
            "message": f"LHM API 调用失败: [{err_code}] {err_msg}",
            "fix_guide": "请检查：1) aliyun CLI 凭证是否已配置（aliyun configure / 环境变量 / RAM Role） 2) RAM 权限是否包含 LHM 3) 网络是否能访问阿里云 API。",
            "blocking": True,
        }

    except Exception as exc:
        return {
            "name": "api_connectivity",
            "status": "fail",
            "message": f"LHM API 调用异常: {exc}",
            "fix_guide": "请检查：1) aliyun CLI 凭证是否已配置（aliyun configure / 环境变量 / RAM Role） 2) RAM 权限是否包含 LHM 3) 网络是否能访问阿里云 API。",
            "blocking": True,
        }


# ---------------------------------------------------------------------------
# 资源组状态常量
# ---------------------------------------------------------------------------

_RG_STATUS_HEALTHY = "Normal"


def _check_resource_group(config: Dict[str, Any]) -> Dict[str, Any]:
    """检查 DataWorks 资源组绑定状态。

    调用 GetLhmDWResourceGroupStatus(region_id) API。
    response.body.data 为纯字符串（资源组状态），仅 "Normal" 视为健康。
    凭证由 aliyun CLI 默认凭证链解析，缺失/错误在调用中以真实报错暴露。
    """
    region_id = config.get("region_id", "cn-hangzhou")

    client = _build_client(config)
    if client is None:
        return {
            "name": "resource_group",
            "status": "fail",
            "message": "无法构建 LHM Client，请检查 endpoint 配置",
            "fix_guide": "确认 session.json 中 endpoint 字段正确且网络可达。",
            "blocking": True,
        }

    try:
        # 使用 dict 作为请求参数，避免依赖 SDK models
        # 插件命令 get-lhm-dw-resource-group-status 必填参数为 --biz-region-id，
        # 故键用 camelCase bizRegionId；方法名须逐词下划线以映射到正确命令名。
        request = {"bizRegionId": region_id}
        response = client.get_lhm_dw_resource_group_status(request)
        body = response.body

        if not getattr(body, "success", False):
            err_code = getattr(body, "err_code", "UNKNOWN")
            err_msg = getattr(body, "err_message", "未知错误")
            return {
                "name": "resource_group",
                "status": "fail",
                "message": f"资源组状态查询失败: [{err_code}] {err_msg}",
                "fix_guide": "请确认 API 权限和网络连通性。",
                "blocking": True,
            }

        status = getattr(body, "data", "") or ""

        if not status:
            return {
                "name": "resource_group",
                "status": "fail",
                "message": "未绑定 DataWorks 资源组",
                "fix_guide": (
                    "请在 LHM 控制台绑定资源组: "
                    "https://apds.console.aliyun.com/lake-house/resource-agent\n"
                    "操作：点击「绑定资源组」→ 选择已创建的 Serverless 资源组。"
                ),
                "blocking": True,
            }

        if status == _RG_STATUS_HEALTHY:
            return {
                "name": "resource_group",
                "status": "pass",
                "message": "DataWorks 资源组状态正常",
                "data": status,
            }

        return {
            "name": "resource_group",
            "status": "fail",
            "message": f"资源组状态异常: {status}",
            "data": status,
            "fix_guide": (
                f"当前状态: {status}。"
                "请进入 DataWorks 控制台检查资源组："
                "https://dataworks.console.aliyun.com/resource/list\n"
                "常见状态：Creating/Updating/Starting=等待完成，"
                "CreateFailed/UpdateFailed=检查错误日志，"
                "Stop/Freezed=续费或解冻。"
            ),
            "blocking": True,
        }

    except Exception as exc:
        return {
            "name": "resource_group",
            "status": "fail",
            "message": f"资源组状态查询异常: {exc}",
            "fix_guide": "请确认 SDK 版本和 API 权限。",
            "blocking": True,
        }


# ---------------------------------------------------------------------------
# Agent 状态常量
# ---------------------------------------------------------------------------

_AGENT_STATUS_ONLINE = "Online"
# 当前技能名称（与 pyproject.toml 中 [project.scripts] 暴露的命令名一致），
# 透传给 GetLhmAgentStatusRequest.skill_name，用于服务端识别调用方。
_SKILL_NAME = "lhm-sch-workflowmigration"


def _check_agent(config: Dict[str, Any]) -> Dict[str, Any]:
    """检查服务代理在线状态。

    调用 GetLhmAgentStatus(agent_type=1, skill_name="lhm-sch-env") API，
    其中 skill_name 为 SDK 2.0.1 新增的可选参数。
    response.body.data 为纯字符串（Agent 状态），仅 "Online" 视为可用。
    凭证由 aliyun CLI 默认凭证链解析，缺失/错误在调用中以真实报错暴露。
    """
    client = _build_client(config)
    if client is None:
        return {
            "name": "agent",
            "status": "fail",
            "message": "无法构建 LHM Client，请检查 endpoint 配置",
            "fix_guide": "确认 session.json 中 endpoint 字段正确且网络可达。",
            "blocking": True,
        }

    try:
        # 使用 dict 作为请求参数，避免依赖 SDK models
        # 必须用 camelCase：invoke() 只识别 camelCase->kebab-case，
        # 插件期望 --agent-type / --skill-name。
        request = {
            "agentType": 1,
            "skillName": _SKILL_NAME,
        }
        response = client.get_lhm_agent_status(request)
        body = response.body

        if not getattr(body, "success", False):
            err_code = getattr(body, "err_code", "UNKNOWN")
            err_msg = getattr(body, "err_message", "未知错误")
            return {
                "name": "agent",
                "status": "fail",
                "message": f"服务代理状态查询失败: [{err_code}] {err_msg}",
                "fix_guide": "请确认 API 权限和网络连通性。",
                "blocking": True,
            }

        status = getattr(body, "data", "") or ""

        if not status:
            return {
                "name": "agent",
                "status": "fail",
                "message": "未配置服务代理",
                "fix_guide": (
                    "请在 LHM 控制台安装服务代理: "
                    "https://apds.console.aliyun.com/lake-house/resource-agent\n"
                    "操作：申请 License → 服务代理安装 → 选择 ECS 实例。"
                ),
                "blocking": True,
            }

        if status == _AGENT_STATUS_ONLINE:
            return {
                "name": "agent",
                "status": "pass",
                "message": "服务代理在线",
                "data": status,
            }

        return {
            "name": "agent",
            "status": "fail",
            "message": f"服务代理状态为 {status}",
            "data": status,
            "fix_guide": (
                f"当前状态: {status}。"
                "请检查 ECS 上的 Agent 进程：\n"
                "  客户端路径: /home/agent/meta/{{代理名称}}/\n"
                "  启动日志: start.log\n"
                "  查询日志: /var/log/agent/meta/{{代理名称}}/application*.log\n"
                "详见: https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/service-agent-management"
            ),
            "blocking": True,
        }

    except Exception as exc:
        return {
            "name": "agent",
            "status": "fail",
            "message": f"服务代理状态查询异常: {exc}",
            "fix_guide": "请确认 SDK 版本和 API 权限。",
            "blocking": True,
        }


# ---------------------------------------------------------------------------
# 检查项注册表
# ---------------------------------------------------------------------------

_CHECK_REGISTRY: Dict[str, Any] = {
    "api_connectivity": _check_api_connectivity,
    "resource_group": _check_resource_group,
    "agent": _check_agent,
}


# ---------------------------------------------------------------------------
# Profile 定义（与 cli.py 保持一致）
# ---------------------------------------------------------------------------

_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "schedule": {
        "required": ["api_connectivity"],
        "optional": ["resource_group", "agent"],
    },
    "data-validation": {
        "required": ["api_connectivity", "resource_group", "agent"],
        "optional": [],
    },
    "full": {
        "required": ["api_connectivity", "resource_group", "agent"],
        "optional": [],
    },
}


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def run_checks(
    profile: str = "schedule",
    session_file: Optional[str] = None,
) -> Dict[str, Any]:
    """执行指定 profile 的所有检查项。

    Args:
        profile: 检查配置集名称。
        session_file: 显式指定 session.json 路径。

    Returns:
        包含 checks 列表、ready 标志和 summary 的结果字典。
    """
    config = load_config(session_file)
    profile_def = _PROFILES.get(profile, _PROFILES["schedule"])

    check_names: List[str] = []
    for name in profile_def["required"]:
        if name not in check_names:
            check_names.append(name)
    for name in profile_def.get("optional", []):
        if name not in check_names:
            check_names.append(name)

    results: List[Dict[str, Any]] = []
    for name in check_names:
        checker = _CHECK_REGISTRY.get(name)
        if checker is None:
            results.append({
                "name": name,
                "status": "skip",
                "message": f"未知检查项: {name}",
            })
            continue
        results.append(checker(config))

    # 判定就绪状态：所有 required 项必须 pass 或 skip（非 fail）
    required_names = set(profile_def["required"])
    has_blocking_failure = any(
        item["name"] in required_names
        and item["status"] == "fail"
        and item.get("blocking", False)
        for item in results
    )
    ready = not has_blocking_failure

    passed = sum(1 for r in results if r["status"] == "pass")
    total = len(results)
    summary = f"{passed}/{total} 项通过"

    blocking_items = [
        r["name"] for r in results
        if r.get("blocking") and r["status"] == "fail"
    ]

    return {
        "ok": ready,
        "profile": profile,
        "checks": results,
        "ready": ready,
        "summary": summary,
        "blocking_items": blocking_items,
    }
