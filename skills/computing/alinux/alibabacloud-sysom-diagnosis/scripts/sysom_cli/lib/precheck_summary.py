# -*- coding: utf-8 -*-
"""precheck 结果压缩与路径推荐：合并 AK 来源、对比 AK 与 ECS RAM Role 路径完成度。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _find_row(checked: List[Dict[str, Any]], method: str) -> Optional[Dict[str, Any]]:
    for row in checked:
        if row.get("method") == method:
            return row
    return None


def _find_rows_prefix(checked: List[Dict[str, Any]], prefix: str) -> List[Dict[str, Any]]:
    return [r for r in checked if str(r.get("method", "")).startswith(prefix)]


def _status_text(status: str) -> str:
    s = (status or "").strip()
    if s.startswith("✗"):
        return s[1:].strip()
    if s.startswith("✓"):
        return s[1:].strip()
    return s


def summarize_precheck_for_agent(check_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    供 Agent 展示：合并「环境变量 AK」与「配置文件 AK」为一条；汇总 RAM Role 相关行；
    根据完成度推荐优先跟进 AK 路径、RAM Role 路径或仅控制台开通。
    """
    checked: List[Dict[str, Any]] = list(check_result.get("checked") or [])
    err_code = check_result.get("error_code")
    ecs_role_name = check_result.get("ecs_role_name")

    ecs_row = _find_row(checked, "ECS元数据")
    env_row = _find_row(checked, "环境变量 AKSK")
    file_ak_row = _find_row(checked, "配置文件 AKSK")
    file_generic = _find_row(checked, "配置文件")

    env_unconfigured = env_row is not None and "未配置" in (env_row.get("status") or "")
    env_attempted = env_row is not None and not env_unconfigured
    file_ak_attempted = file_ak_row is not None

    # AK 合并行
    ak_parts: List[str] = []
    if env_attempted:
        ak_parts.append(f"环境变量：{_status_text(env_row.get('status', ''))}")
    elif env_row is not None:
        ak_parts.append("环境变量：未配置")
    if file_ak_attempted:
        ak_parts.append(f"配置文件 AK：{_status_text(file_ak_row.get('status', ''))}")
    if not ak_parts:
        if file_generic is not None:
            ak_parts.append(f"配置文件：{_status_text(file_generic.get('status', ''))}")
        else:
            ak_parts.append("未检测到环境变量 AK 与配置文件 AK 模式")

    merged_ak = "AccessKey（环境变量与本地配置文件 AK 模式，任选其一即可）"
    if env_attempted or file_ak_attempted:
        merged_ak_status = "；".join(ak_parts)
    else:
        merged_ak_status = "；".join(ak_parts) if ak_parts else "未配置有效 AK"

    ram_rows = [
        r
        for r in checked
        if str(r.get("method", "")).lower().startswith("配置文件 ecsramrole")
        or str(r.get("method", "")).startswith("配置文件 ECS RAM Role")
        or str(r.get("method", "")).startswith("配置文件 RAM Role")
    ]
    if ram_rows:
        ram_status = " | ".join(
            f"{r.get('method')}: {_status_text(r.get('status', ''))}" for r in ram_rows
        )
    else:
        ram_status = "未使用配置文件中的 ECS RAM Role 模式或未配置"

    merged_rows = [
        {"label": "ECS 元数据（实例是否绑定 RAM 角色）", "status": ecs_row.get("status", "") if ecs_row else "—"},
        {"label": "AccessKey（环境变量或配置文件，二选一即可）", "status": merged_ak_status},
        {"label": "ECS RAM Role（配置文件 ECS RAM Role / RAM Role）", "status": ram_status},
    ]

    ecs_status = (ecs_row.get("status") or "") if ecs_row else ""
    metadata_role_bound = bool(ecs_role_name) or ("✓" in ecs_status)
    file_profile_missing_or_invalid = file_generic is not None and "✗" in (file_generic.get("status") or "")

    progress: Dict[str, Any] = {
        "activation_needed": err_code in ("service_not_activated", "sysom_role_not_exist"),
        "metadata_role_bound": metadata_role_bound,
        "env_ak_unconfigured": env_unconfigured and env_row is not None,
        "env_ak_attempted": env_attempted,
        "file_ak_attempted": file_ak_attempted,
        "file_profile_missing_or_invalid": file_profile_missing_or_invalid,
        "ram_profile_configured": bool(ram_rows),
        "ecs_role_name": ecs_role_name,
    }

    activation_needed = bool(progress["activation_needed"])

    # 完成度：AK 路径（越高越接近「只剩控制台」）
    ak_score = 0
    if env_attempted:
        ak_score += 2
    if file_ak_attempted:
        ak_score += 2
    if activation_needed and (env_attempted or file_ak_attempted):
        ak_score += 3

    # 完成度：RAM 路径
    ram_score = 0
    if ecs_role_name:
        ram_score += 2
    if ram_rows:
        ram_score += 2
    if activation_needed and ram_rows:
        ram_score += 2

    focus: str
    primary_path: str

    if activation_needed:
        # 仅一侧 AK 已生效、另一侧未配：不要引导再去配「第二套」AK
        if file_ak_attempted and env_unconfigured and not env_attempted:
            primary_path = "console_only"
            focus = (
                "AccessKey 已从配置文件生效（InitialSysom 已调用）；账号侧未开通或 SLR 未就绪。"
                "请优先在 Alinux/SysOM 控制台完成开通，无需再配置环境变量 AK。"
            )
        elif env_attempted and not file_ak_attempted:
            primary_path = "console_only"
            focus = (
                "AccessKey 已从环境变量生效；账号侧未开通或 SLR 未就绪。"
                "请优先在控制台完成开通；若希望改用配置文件 AK，再单独切换即可，不必两套同时配置。"
            )
        elif ak_score > ram_score and (env_attempted or file_ak_attempted):
            primary_path = "access_key_then_console"
            focus = (
                "当前 AccessKey 路径完成度更高：InitialSysom 已返回需账号侧开通 SysOM（SLR 通常随 Alinux 控制台开通自动创建）。"
                "请优先 Alinux/SysOM 控制台；环境变量 AK 与配置文件 AK 只需其一有效即可。"
            )
        elif ram_score > ak_score and (ecs_role_name or ram_rows):
            primary_path = "ecs_ram_role"
            focus = (
                "当前 ECS RAM Role 路径完成度更高：请优先完成 RAM 策略、实例绑定与 CLI 的 ECS RAM Role 模式配置，"
                "再处理 SysOM 控制台开通。"
            )
        else:
            primary_path = "configure_identity"
            focus = (
                "请先建立一种可用身份：环境变量 AK、本地配置文件 AK，或（在 ECS 上）RAM 角色 + ECS RAM Role；"
                "三条路线满足其一即可，不必并行配置多种。"
            )
    else:
        # 非开通类失败：单路径优先（完成度高的路径独占引导，不并列 AK + RAM）
        if ram_score > ak_score and (ecs_role_name or ram_rows):
            primary_path = "ecs_ram_role"
            if ram_rows and ecs_role_name:
                focus = (
                    "实例已绑定 RAM 角色且本地配置文件为 ECS RAM Role/RAM Role：请优先确认该角色具备 AliyunSysomFullAccess、"
                    "等待策略生效后重试 precheck；勿再并行配置 AccessKey。"
                )
            elif ecs_role_name:
                focus = (
                    f"实例已绑定 RAM 角色「{ecs_role_name}」：请授予 AliyunSysomFullAccess，"
                    "并在实例内将 CLI 配置为 ECS RAM Role（或核对现有 ECS RAM Role 配置）后重试 precheck；勿并行配置 AccessKey。"
                )
            else:
                focus = (
                    "配置文件已指向 ECS RAM Role：请确认角色具备 AliyunSysomFullAccess、实例绑定与 STS 拉取正常，"
                    "勿并行配置 AccessKey。"
                )
        elif ak_score > ram_score and (env_attempted or file_ak_attempted):
            primary_path = "access_key"
            focus = (
                "AccessKey 路径已尝试：请仅沿该路径修复（密钥有效性、AliyunSysomFullAccess、环境变量与 precheck 同进程等），"
                "勿同时引入 ECS RAM Role 排查。"
            )
        elif ram_score == ak_score:
            # 平局：实例已绑角色则优先 RAM 路径，避免「已绑角色却仍像未选路径」
            if ecs_role_name or ram_rows:
                primary_path = "ecs_ram_role"
                if ram_rows and ecs_role_name:
                    focus = (
                        "实例已绑定 RAM 角色且本地配置文件为 ECS RAM Role/RAM Role：请优先确认该角色具备 AliyunSysomFullAccess、"
                        "等待策略生效后重试 precheck；勿再并行配置 AccessKey。"
                    )
                elif ecs_role_name:
                    focus = (
                        f"实例已绑定 RAM 角色「{ecs_role_name}」：请授予 AliyunSysomFullAccess，"
                        "并在实例内将 CLI 配置为 ECS RAM Role（或核对现有 ECS RAM Role 配置）后重试 precheck；勿并行配置 AccessKey。"
                    )
                else:
                    focus = (
                        "配置文件已指向 ECS RAM Role：请确认角色具备 AliyunSysomFullAccess、实例绑定与 STS 拉取正常，"
                        "勿并行配置 AccessKey。"
                    )
            elif env_attempted or file_ak_attempted:
                primary_path = "access_key"
                focus = (
                    "AccessKey 路径已尝试：请仅沿该路径修复（密钥有效性、AliyunSysomFullAccess、环境变量与 precheck 同进程等），"
                    "勿同时引入 ECS RAM Role 排查。"
                )
            else:
                primary_path = "configure_identity"
                focus = (
                    "尚未形成明确领先路径：请先建立一种可用身份——环境变量 AK、本地配置文件 AK，"
                    "或（在 ECS 上）实例 RAM 角色 + ECS RAM Role；满足其一即可。"
                )
        else:
            primary_path = "configure_identity"
            focus = (
                "尚未形成明确领先路径：请先建立一种可用身份——环境变量 AK、本地配置文件 AK，"
                "或（在 ECS 上）实例 RAM 角色 + ECS RAM Role；满足其一即可。"
            )

    return {
        "merged_rows": merged_rows,
        "scores": {"ak_path": ak_score, "ram_role_path": ram_score},
        "primary_path": primary_path,
        "recommended_focus": focus,
        "progress": progress,
    }
