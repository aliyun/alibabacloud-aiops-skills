"""
认证检查器
支持检查 AKSK、STS Token 和 ECS RAM Role 三种认证方式，并调用 SysOM API 验证权限
"""
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from sysom_cli.lib.guidance import RAM_CONSOLE_URL


def check_env_credentials() -> Dict[str, Any]:
    """
    检查环境变量中的 AKSK / STS Token 配置
    
    查找以下环境变量：
    - ALIBABA_CLOUD_ACCESS_KEY_ID: AccessKey ID
    - ALIBABA_CLOUD_ACCESS_KEY_SECRET: AccessKey Secret
    - ALIBABA_CLOUD_SECURITY_TOKEN: STS SecurityToken（可选）
    
    返回格式：
        成功时（AK/SK 都存在且非空，且可选带 STS Token）：
        {
            "available": True,
            "method": "环境变量(AKSK)" 或 "环境变量(STS Token)",
            "credentials": {
                "ak_id": "LTAI...",
                "ak_secret": "...",
                "security_token": "CAES..."  # 仅 STS Token 模式
            }
        }
        失败时：
        {
            "available": False,
            "method": "环境变量"
        }
    """
    # 与阿里云 Python SDK / CLI 常见变量名对齐（多段 Shell 不共享 export 时优先用 configure 写 config.json）
    ak_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or os.getenv("ALICLOUD_ACCESS_KEY_ID")
    ak_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or os.getenv("ALICLOUD_ACCESS_KEY_SECRET")
    security_token = (
        os.getenv("ALIBABA_CLOUD_SECURITY_TOKEN")
        or os.getenv("ALICLOUD_SECURITY_TOKEN")
        or os.getenv("SECURITY_TOKEN")
    )

    if ak_id and ak_secret:
        creds: Dict[str, str] = {
            "ak_id": ak_id,
            "ak_secret": ak_secret,
        }
        method = "环境变量(AKSK)"
        if security_token:
            creds["security_token"] = security_token
            method = "环境变量(STS Token)"
        return {
            "available": True,
            "method": method,
            "credentials": creds,
        }
    return {"available": False, "method": "环境变量(AKSK/STS Token)"}


def _ecs_metadata_on_ecs_instance() -> bool:
    """若能读到 instance-id，说明当前环境可访问 ECS 元数据（多半在 ECS 内网）。"""
    url = "http://100.100.100.200/latest/meta-data/instance-id"
    try:
        r = requests.get(url, timeout=2)
        return r.status_code == 200 and bool((r.text or "").strip())
    except Exception:
        return False


def check_ecs_metadata_role() -> Dict[str, Any]:
    """
    检查 ECS 实例是否绑定了 RAM Role（通过元数据 API）。

    说明：在阿里云 ECS 内，若实例**未附加实例 RAM 角色**，
    ``ram/security-credentials/`` 常返回 **404**，这与「元数据不可达」不同。
    此时会补充探测 ``instance-id``，以区分「在 ECS 上但未绑角色」与「非 ECS / 网络不可达」。
    """
    base = "http://100.100.100.200/latest/meta-data"
    url = f"{base}/ram/security-credentials/"

    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            role_name = response.text.strip()
            if role_name:
                return {
                    "available": True,
                    "role_name": role_name,
                    "method": "ECS元数据服务",
                }
            return {
                "available": False,
                "error": "实例未绑定 RAM 角色（security-credentials 响应体为空）",
            }

        if response.status_code == 404:
            if _ecs_metadata_on_ecs_instance():
                return {
                    "available": False,
                    "error": (
                        "已在 ECS 环境中（可读取 instance-id），但 ram/security-credentials/ 返回 404："
                        "实例可能未附加 RAM 角色。请在 ECS 控制台为实例绑定 RAM 角色，或改用 AK/SK / 配置 aliyun CLI。"
                    ),
                }
            return {
                "available": False,
                "error": (
                    "HTTP 404：未获取到 RAM 临时凭证路径（可能不在阿里云 ECS 内网，或实例未绑定 RAM 角色）"
                ),
            }

        return {
            "available": False,
            "error": f"HTTP {response.status_code}: 无法读取 RAM 凭证路径",
        }
    except requests.exceptions.Timeout:
        return {
            "available": False,
            "error": "连接超时（可能不在阿里云 ECS 内网，或元数据 100.100.100.200 不可达）",
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"访问元数据服务失败: {str(e)}",
        }


def check_aliyun_config() -> Dict[str, Any]:
    """
    检查 ~/.aliyun/config.json 配置文件
    
    支持四种认证模式：
    1. AK 模式：mode=AK，包含 access_key_id 和 access_key_secret
    2. StsToken 模式：mode=StsToken，包含 access_key_id / access_key_secret / sts_token
    3. EcsRamRole 模式：mode=EcsRamRole，SDK 自动从元数据服务获取临时凭证
    4. 兼容旧格式：包含 ram_role_name 字段（不推荐）
    
    返回格式：
        AK 模式成功：
        {
            "available": True,
            "method": "配置文件(AK)",
            "credentials": {
                "ak_id": "LTAI...",
                "ak_secret": "..."
            }
        }
        
        EcsRamRole 模式成功：
        {
            "available": True,
            "method": "配置文件(EcsRamRole)",
            "needs_metadata": True  # 需要调用 check_ecs_metadata_role() 获取角色名
        }
        
        旧格式 RAM Role：
        {
            "available": True,
            "method": "配置文件(RAM Role)",
            "ram_role": "角色名"
        }
        
        失败时：
        {
            "available": False,
            "method": "配置文件",
            "error": "错误描述"
        }
    """
    config_path = Path.home() / ".aliyun" / "config.json"
    
    if not config_path.exists():
        return {"available": False, "method": "配置文件"}
    
    try:
        config = json.loads(config_path.read_text())
        # 支持 current_profile 或 current 字段
        profile_name = config.get("current_profile") or config.get("current") or "default"
        
        for profile in config.get("profiles", []):
            if profile.get("name") == profile_name:
                mode = profile.get("mode", "AK")
                
                mode_norm = str(mode).strip().lower()

                # AK 模式
                if mode_norm == "ak" and "access_key_id" in profile:
                    return {
                        "available": True,
                        "method": "配置文件(AK)",
                        "credentials": {
                            "ak_id": profile["access_key_id"],
                            "ak_secret": profile.get("access_key_secret", "")
                        }
                    }
                # StsToken 模式
                elif mode_norm == "ststoken" and "access_key_id" in profile:
                    sts_token = (
                        profile.get("sts_token")
                        or profile.get("security_token")
                        or profile.get("access_key_sts_token")
                    )
                    if not sts_token:
                        return {
                            "available": False,
                            "method": "配置文件(StsToken)",
                            "error": "StsToken 模式缺少 sts_token/security_token",
                        }
                    return {
                        "available": True,
                        "method": "配置文件(StsToken)",
                        "credentials": {
                            "ak_id": profile["access_key_id"],
                            "ak_secret": profile.get("access_key_secret", ""),
                            "security_token": sts_token,
                        },
                    }
                # EcsRamRole 模式
                elif mode_norm == "ecsramrole":
                    return {
                        "available": True,
                        "method": "配置文件(EcsRamRole)",
                        "needs_metadata": True  # 需要从元数据服务获取角色名
                    }
                # 兼容旧的 RAM Role 配置（有 ram_role_name 字段）
                elif "ram_role_name" in profile:
                    return {
                        "available": True,
                        "method": "配置文件(RAM Role)",
                        "ram_role": profile["ram_role_name"]
                    }
        
        return {"available": False, "method": "配置文件", "error": "未找到有效的 profile"}
    
    except Exception as e:
        return {
            "available": False,
            "method": "配置文件",
            "error": f"解析配置文件失败: {str(e)}"
        }


def get_ecs_ram_credentials(role_name: str) -> Dict[str, Any]:
    """
    从 ECS 元数据服务获取 RAM Role 的 STS 临时凭证
    
    通过访问 ECS 元数据 API (http://100.100.100.200/latest/meta-data/ram/security-credentials/<role_name>)
    获取由 STS (Security Token Service) 签发的临时访问凭证，包含：
    - 临时 AccessKey ID (以 STS. 开头)
    - 临时 AccessKey Secret
    - SecurityToken（用于验证临时凭证的有效性）
    
    这些临时凭证会自动轮换，有效期通常为 6 小时。
    
    Args:
        role_name: RAM 角色名称
    
    Returns:
        dict: 凭证获取结果
            成功时：
            {
                "available": True,
                "credentials": {
                    "ak_id": "STS.xxx",          # 临时 AccessKey ID
                    "ak_secret": "xxx",          # 临时 AccessKey Secret
                    "security_token": "CAES+xxx" # STS SecurityToken
                }
            }
            失败时：
            {
                "available": False,
                "error": "错误描述"
            }
    """
    url = f"http://100.100.100.200/latest/meta-data/ram/security-credentials/{role_name}"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            creds = response.json()
            return {
                "available": True,
                "credentials": {
                    "ak_id": creds["AccessKeyId"],
                    "ak_secret": creds["AccessKeySecret"],
                    "security_token": creds["SecurityToken"]
                }
            }
        else:
            return {
                "available": False,
                "error": f"HTTP {response.status_code}: 无法获取凭证"
            }
    except requests.exceptions.Timeout:
        return {
            "available": False,
            "error": "连接超时（可能不在 ECS 环境中）"
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"获取凭证失败: {str(e)}"
        }


def _extract_initial_sysom_role_exist(data: Any) -> Optional[bool]:
    """
    从 InitialSysom 返回的 data 解析 role_exist。
    返回 True/False 表示布尔值；字段不存在时返回 None（不强制据此判失败，兼容旧响应）。
    """
    if data is None:
        return None
    if isinstance(data, dict):
        if "role_exist" not in data:
            return None
        return bool(data["role_exist"])
    if hasattr(data, "role_exist"):
        v = getattr(data, "role_exist", None)
        return bool(v) if v is not None else None
    if hasattr(data, "to_map"):
        m = data.to_map()
        if isinstance(m, dict):
            raw = m.get("role_exist")
            if raw is None:
                raw = m.get("RoleExist")
            if raw is None:
                return None
            return bool(raw)
    return None


def test_sysom_api(credentials: Dict[str, str]) -> Dict[str, Any]:
    """
    调用 InitialSysom API 测试权限
    
    支持两种认证模式：
    1. AKSK 模式：credentials 包含 ak_id 和 ak_secret
    2. RAM Role 模式（STS 临时凭证）：credentials 包含 ak_id、ak_secret 和 security_token
    
    Args:
        credentials: 认证凭证字典
            - ak_id (str): AccessKey ID（AKSK 模式）或临时 AccessKey ID（STS 模式）
            - ak_secret (str): AccessKey Secret 或临时 AccessKey Secret
            - security_token (str, optional): STS SecurityToken（仅 RAM Role 模式需要）
    
    Returns:
        dict: API 调用结果
            - success (bool): 是否成功
            - response (dict): 成功时的响应数据
            - error (str): 失败时的错误信息
    """
    try:
        from alibabacloud_sysom20231230.client import Client
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_sysom20231230 import models as sysom_models
        
        # 创建配置
        config = open_api_models.Config(
            access_key_id=credentials["ak_id"],
            access_key_secret=credentials["ak_secret"],
            endpoint="sysom.cn-hangzhou.aliyuncs.com",
            user_agent="AlibabaCloud-Agent-Skills/alibabacloud-sysom-diagnosis",
        )
        
        # RAM Role 模式：设置 STS SecurityToken
        if "security_token" in credentials:
            config.security_token = credentials["security_token"]
        
        # 创建客户端
        client = Client(config)
        
        # 构造请求
        request = sysom_models.InitialSysomRequest()
        
        # 调用 API
        response = client.initial_sysom(request)
        
        # 检查响应
        if response and response.body:
            # 检查是否返回了角色信息（判断 SysOM 服务是否已开通）
            # InitialSysom API 成功返回，但如果没有角色信息，说明服务未开通
            data = response.body.data if hasattr(response.body, 'data') else None
            
            # 如果 data 为空或 None，说明 SysOM 服务未开通
            if not data:
                return {
                    "success": False,
                    "error": "SysOM 服务未开通",
                    "error_code": "service_not_activated",
                    "detail": "InitialSysom API 调用成功，但返回的角色信息为空，请先开通 SysOM 服务"
                }

            role_exist = _extract_initial_sysom_role_exist(data)
            if role_exist is False:
                return {
                    "success": False,
                    "error": "SysOM 服务关联角色未创建或未就绪",
                    "error_code": "sysom_role_not_exist",
                    "detail": (
                        "InitialSysom 返回 data.role_exist=false：请在 Alinux 控制台完成 SysOM 开通"
                        "（开通流程通常会**自动**创建 AliyunServiceRoleForSysom）；若刚完成开通，等待 1～3 分钟后再执行 precheck"
                    ),
                }

            # 成功且服务已开通（role_exist 为 True，或未返回该字段时沿用非空 data 判断）
            return {
                "success": True,
                "response": {
                    "RequestId": response.body.request_id if hasattr(response.body, 'request_id') else None,
                    "Data": data
                }
            }
        return {
            "success": False,
            "error": "InitialSysom 返回无效：缺少响应体或 body",
            "error_code": "initial_sysom_invalid_response",
            "detail": "InitialSysom 未返回可用 data，请确认 SysOM 已开通且账号侧正常，或稍后重试",
        }
    
    except Exception as e:
        error_msg = str(e)
        
        # 解析常见错误
        if "InvalidAccessKeyId" in error_msg or "Specified access key is not found" in error_msg:
            return {
                "success": False,
                "error": "AccessKey 无效或不存在",
                "error_code": "invalid_access_key",
                "detail": error_msg
            }
        elif "Forbidden" in error_msg or "Permission" in error_msg or "NoPermission" in error_msg:
            return {
                "success": False,
                "error": "权限不足，需要 AliyunSysomFullAccess 权限",
                "error_code": "insufficient_permissions",
                "detail": error_msg
            }
        elif "InvalidAction.NotFound" in error_msg or "404" in error_msg:
            return {
                "success": False,
                "error": "API 不可用或 endpoint 配置错误",
                "error_code": "api_not_found",
                "detail": error_msg
            }
        else:
            return {
                "success": False,
                "error": f"API 调用失败: {error_msg[:100]}",
                "error_code": "api_call_failed",
                "detail": error_msg
            }


def generate_help_message(
    *,
    include_aksk: bool = True,
    include_ram_role: bool = True,
    include_permission: bool = True,
) -> Dict[str, str]:
    """生成帮助信息；可按场景省略块，避免与信封 remediation 重复堆叠。"""
    aksk = (
        "方式 1: 使用 AccessKey (AKSK)\n"
        "A. 推荐（跨 Shell / Agent）：./scripts/osops.sh configure，写入 ~/.aliyun/config.json\n"
        "B. 如需环境变量方式，请按 references/authentication.md 操作，避免在命令行/日志中明文展示凭证\n"
        "C. 或手工编辑 ~/.aliyun/config.json（mode=AK 或 mode=StsToken）"
    )
    ram_role = (
        "方式 2: 使用 ECS RAM Role（推荐）\n"
        "1. 在 ECS 控制台为实例绑定 RAM 角色\n"
        "2. 配置 ~/.aliyun/config.json 指定 ram_role_name"
    )
    ram_role_compact = (
        "方式 2: ECS RAM Role — 完整步骤见 references/authentication.md（ECS RAM Role）。"
    )
    permission = (
        "重要: 授予权限\n"
        "无论使用哪种方式，都需要授予 AliyunSysomFullAccess 权限\n"
        f"RAM 控制台: {RAM_CONSOLE_URL}"
    )
    out: Dict[str, str] = {}
    if include_aksk:
        out["aksk"] = aksk
    if include_ram_role:
        out["ram_role"] = ram_role if include_aksk else ram_role_compact
    if include_permission:
        out["permission"] = permission
    return out


def resolve_sysom_auth(*, verify_api: bool = True) -> Dict[str, Any]:
    """
    解析 SysOM 访问凭证（供 OpenAPI 客户端等使用）。

    优先级与 ``run_precheck`` 一致：环境变量 AKSK → ~/.aliyun/config.json
    （EcsRamRole / 配置文件 RAM Role / AK）。环境变量存在但校验失败时仍会尝试配置文件。

    Args:
        verify_api: 为 True 时在拿到候选凭证后调用 InitialSysom 校验；为 False 则仅解析配置/元数据。

    Returns:
        成功: ``ok``、``method``、``credentials``、``message``；RAM 场景另有 ``role``。
        失败: ``ok``、``error``、``help``；凭证可用但服务未开通时含 ``error_code``。
    """
    metadata_result = check_ecs_metadata_role()
    service_not_activated_error: Optional[Dict[str, Any]] = None
    last_sysom_api_failure: Optional[Dict[str, Any]] = None

    def _try_accept(
        method: str,
        credentials: Dict[str, str],
        *,
        role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        nonlocal service_not_activated_error, last_sysom_api_failure
        if verify_api:
            api_result = test_sysom_api(credentials)
            if not api_result["success"]:
                if api_result.get("error_code") in (
                    "service_not_activated",
                    "sysom_role_not_exist",
                ):
                    service_not_activated_error = api_result
                else:
                    last_sysom_api_failure = api_result
                return None
        out: Dict[str, Any] = {
            "ok": True,
            "method": method,
            "credentials": credentials,
            "message": (
                "认证验证成功，拥有 SysOM 访问权限"
                if verify_api
                else "已解析凭证（未调用 SysOM API 验证权限）"
            ),
        }
        if role is not None:
            out["role"] = role
        return out

    env_result = check_env_credentials()
    if env_result["available"]:
        env_method = (
            "环境变量 STS Token"
            if env_result.get("credentials", {}).get("security_token")
            else "环境变量 AKSK"
        )
        got = _try_accept(env_method, env_result["credentials"])
        if got:
            return got

    config_result = check_aliyun_config()
    if config_result["available"]:
        if config_result.get("needs_metadata"):
            if metadata_result["available"]:
                ram_role = metadata_result["role_name"]
                ram_creds = get_ecs_ram_credentials(ram_role)
                if ram_creds["available"]:
                    got = _try_accept(
                        f"ECS RAM Role ({ram_role})",
                        ram_creds["credentials"],
                        role=ram_role,
                    )
                    if got:
                        return got
        elif config_result["method"].endswith("(RAM Role)"):
            ram_role = config_result["ram_role"]
            ram_creds = get_ecs_ram_credentials(ram_role)
            if ram_creds["available"]:
                got = _try_accept(
                    f"ECS RAM Role ({ram_role})",
                    ram_creds["credentials"],
                    role=ram_role,
                )
                if got:
                    return got
        else:
            got = _try_accept("配置文件 AKSK", config_result["credentials"])
            if got:
                return got

    if service_not_activated_error:
        return {
            "ok": False,
            "error": service_not_activated_error["error"],
            "error_code": service_not_activated_error.get("error_code"),
            "help": generate_help_message(),
        }

    if last_sysom_api_failure:
        return {
            "ok": False,
            "error": last_sysom_api_failure["error"],
            "error_code": last_sysom_api_failure.get("error_code"),
            "help": generate_help_message(),
        }

    return {
        "ok": False,
        "error": "未找到有效的认证配置",
        "help": generate_help_message(),
    }


def run_precheck() -> Dict[str, Any]:
    """
    执行完整的认证检查流程
    
    Returns:
        dict: 检查结果
            - ok (bool): 是否通过检查
            - method (str): 成功的认证方式
            - message (str): 结果消息
            - checked (list): 已检查的方式列表
            - error (str): 错误信息
            - help (dict): 帮助信息
            - ecs_role_name (str): 如果在 ECS 上检测到绑定的角色名
    """
    check_results = []
    ecs_role_name = None
    service_not_activated_error = None  # 记录"服务未开通"错误
    last_sysom_api_failure: Optional[Dict[str, Any]] = None  # InitialSysom 其他失败（含无效响应）

    # 0. 首先检查是否在 ECS 环境并绑定了 RAM Role
    metadata_result = check_ecs_metadata_role()
    if metadata_result["available"]:
        ecs_role_name = metadata_result["role_name"]
        check_results.append({
            "method": "ECS元数据",
            "status": f"✓ 实例已绑定 RAM 角色: {ecs_role_name}"
        })
    else:
        check_results.append({
            "method": "ECS元数据",
            "status": f"✗ {metadata_result.get('error', '未检测到')}"
        })
    
    # 1. 检查环境变量 AKSK
    env_result = check_env_credentials()
    if env_result["available"]:
        api_result = test_sysom_api(env_result["credentials"])
        if api_result["success"]:
            # 成功时只返回成功的方式，不返回其他检查结果
            env_method = (
                "环境变量 STS Token"
                if env_result.get("credentials", {}).get("security_token")
                else "环境变量 AKSK"
            )
            return {
                "ok": True,
                "method": env_method,
                "message": "认证验证成功，拥有 SysOM 访问权限"
            }
        # 记录"服务未开通"错误（优先级最高）
        if api_result.get("error_code") in (
            "service_not_activated",
            "sysom_role_not_exist",
        ):
            service_not_activated_error = api_result
        else:
            last_sysom_api_failure = api_result
        check_results.append({
            "method": "环境变量 AKSK",
            "status": f"✗ {api_result.get('error', 'API 调用失败')}"
        })
    else:
        check_results.append({
            "method": "环境变量 AKSK",
            "status": "✗ 未配置"
        })
    
    # 2. 检查阿里云配置文件
    config_result = check_aliyun_config()
    if config_result["available"]:
        # 2.1 EcsRamRole 模式（需要从元数据获取角色）
        if config_result.get("needs_metadata"):
            if metadata_result["available"]:
                ram_role = metadata_result["role_name"]
                ram_creds = get_ecs_ram_credentials(ram_role)
                
                if ram_creds["available"]:
                    api_result = test_sysom_api(ram_creds["credentials"])
                    if api_result["success"]:
                        # 成功时只返回成功的方式
                        return {
                            "ok": True,
                            "method": f"ECS RAM Role ({ram_role})",
                            "role": ram_role,
                            "message": "认证验证成功，拥有 SysOM 访问权限"
                        }
                    # 记录"服务未开通"错误
                    if api_result.get("error_code") in (
                        "service_not_activated",
                        "sysom_role_not_exist",
                    ):
                        service_not_activated_error = api_result
                    else:
                        last_sysom_api_failure = api_result
                    check_results.append({
                        "method": f"配置文件 EcsRamRole ({ram_role})",
                        "status": f"✗ {api_result.get('error', 'API 调用失败')}"
                    })
                else:
                    check_results.append({
                        "method": f"配置文件 EcsRamRole ({ram_role})",
                        "status": f"✗ {ram_creds.get('error', '获取临时凭证失败')}"
                    })
            else:
                check_results.append({
                    "method": "配置文件 EcsRamRole",
                    "status": "✗ 配置为 EcsRamRole 模式，但实例未绑定 RAM 角色"
                })
        
        # 2.2 RAM Role 模式（配置文件指定了 ram_role_name）
        elif config_result["method"].endswith("(RAM Role)"):
            ram_role = config_result["ram_role"]
            ram_creds = get_ecs_ram_credentials(ram_role)
            
            if ram_creds["available"]:
                api_result = test_sysom_api(ram_creds["credentials"])
                if api_result["success"]:
                    # 成功时只返回成功的方式
                    return {
                        "ok": True,
                        "method": f"ECS RAM Role ({ram_role})",
                        "role": ram_role,
                        "message": "认证验证成功，拥有 SysOM 访问权限"
                    }
                # 记录"服务未开通"错误
                if api_result.get("error_code") in (
                    "service_not_activated",
                    "sysom_role_not_exist",
                ):
                    service_not_activated_error = api_result
                else:
                    last_sysom_api_failure = api_result
                check_results.append({
                    "method": f"配置文件 RAM Role ({ram_role})",
                    "status": f"✗ {api_result.get('error', 'API 调用失败')}"
                })
            else:
                check_results.append({
                    "method": f"配置文件 RAM Role ({ram_role})",
                    "status": f"✗ {ram_creds.get('error', '获取临时凭证失败')}"
                })
        # 2.3 StsToken 模式
        elif config_result["method"] == "配置文件(StsToken)":
            api_result = test_sysom_api(config_result["credentials"])
            if api_result["success"]:
                return {
                    "ok": True,
                    "method": "配置文件 STS Token",
                    "message": "认证验证成功，拥有 SysOM 访问权限"
                }
            if api_result.get("error_code") in (
                "service_not_activated",
                "sysom_role_not_exist",
            ):
                service_not_activated_error = api_result
            else:
                last_sysom_api_failure = api_result
            check_results.append({
                "method": "配置文件 STS Token",
                "status": f"✗ {api_result.get('error', 'API 调用失败')}"
            })
        
        # 2.4 AK 模式
        else:
            api_result = test_sysom_api(config_result["credentials"])
            if api_result["success"]:
                # 成功时只返回成功的方式
                return {
                    "ok": True,
                    "method": "配置文件 AKSK",
                    "message": "认证验证成功，拥有 SysOM 访问权限"
                }
            # 记录"服务未开通"错误
            if api_result.get("error_code") in (
                "service_not_activated",
                "sysom_role_not_exist",
            ):
                service_not_activated_error = api_result
            else:
                last_sysom_api_failure = api_result
            check_results.append({
                "method": "配置文件 AKSK",
                "status": f"✗ {api_result.get('error', 'API 调用失败')}"
            })
    else:
        check_results.append({
            "method": "配置文件",
            "status": f"✗ {config_result.get('error', '未配置或配置无效')}"
        })
    
    # 所有方式都失败，生成详细的错误信息
    # 优先返回"服务未开通"错误（如果检测到）
    if service_not_activated_error:
        ec = service_not_activated_error.get("error_code")
        if ec == "sysom_role_not_exist":
            sug = (
                "InitialSysom 指示服务关联角色尚未就绪。请在 Alinux/SysOM 控制台完成 SysOM 开通"
                "（开通流程通常会**自动**创建 AliyunServiceRoleForSysom）；若已开通，等待 1～3 分钟再执行 precheck。"
            )
        else:
            sug = (
                "认证配置正确，但需要先开通 SysOM 服务。"
                "请访问 https://alinux.console.aliyun.com/?source=cosh 完成服务开通。"
            )
        return {
            "ok": False,
            "checked": check_results,
            "error": service_not_activated_error["error"],
            "error_code": service_not_activated_error["error_code"],
            "ecs_role_name": ecs_role_name,
            "suggestion": sug,
            "help": generate_help_message()
        }

    if last_sysom_api_failure:
        sug = None
        help_msg = generate_help_message()
        if ecs_role_name:
            sug = (
                "InitialSysom 未通过：请以 JSON 信封中 data.remediation 与 path_summary 为准逐条修复；"
                "勿在对话中传输密钥。"
            )
            help_msg = generate_help_message(
                include_aksk=False,
                include_ram_role=True,
                include_permission=True,
            )
        return {
            "ok": False,
            "checked": check_results,
            "error": last_sysom_api_failure["error"],
            "error_code": last_sysom_api_failure.get("error_code", "api_call_failed"),
            "ecs_role_name": ecs_role_name,
            "detail": last_sysom_api_failure.get("detail"),
            "suggestion": sug,
            "help": help_msg,
        }

    # 其他认证失败情况
    error_msg = "未找到有效的认证配置"

    suggestion = None
    help_msg = generate_help_message()
    if ecs_role_name:
        suggestion = (
            "实例已绑定 RAM 角色：请以 JSON 信封中 data.remediation 与 path_summary 为唯一修复主线；"
            "勿在对话中传输密钥。"
        )
        help_msg = generate_help_message(
            include_aksk=False,
            include_ram_role=True,
            include_permission=True,
        )

    return {
        "ok": False,
        "checked": check_results,
        "error": error_msg,
        "ecs_role_name": ecs_role_name,
        "suggestion": suggestion,
        "help": help_msg,
    }
