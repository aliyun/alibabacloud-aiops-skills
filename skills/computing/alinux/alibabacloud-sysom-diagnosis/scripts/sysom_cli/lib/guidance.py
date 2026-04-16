# -*- coding: utf-8 -*-
"""SysOM OpenAPI 权限引导：precheck / diagnosis 用的固定文案与结构化字段。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# 相对于 sysom-diagnosis/（技能根，与 SKILL.md 同级）
DOC_PATHS_REL_SYSOM_DIAGNOSIS = {
    "openapi_permission_guide": "references/openapi-permission-guide.md",
    "authentication": "references/authentication.md",
    "sysom_diagnosis_skill": "SKILL.md",
    "invoke_diagnosis_ref": "references/invoke-diagnosis.md",
}

# 兼容旧名称（模块内引用）
DOC_PATHS_REL_OS_OPS = DOC_PATHS_REL_SYSOM_DIAGNOSIS

# 需在 RAM 控制台完成授权/角色管理时的统一入口（与 permission 文案一致）
RAM_CONSOLE_URL = "https://ram.console.aliyun.com/"

# COSH：无 TTY 时 osops configure 无法交互读密钥时的补救说明
INTERACTIVE_CONFIGURE_PTY_HINT = (
    "若当前执行环境不支持交互式输入（无 PTY）：在 **COSH** 中可通过 **/settings** 开启「**交互式Shell（PTY）**」，"
    "或使用 **/bash** 进入交互式 Bash，再在 sysom-diagnosis（技能根）执行 ./scripts/osops.sh configure。"
)


def precheck_commands() -> List[str]:
    """推荐在 sysom-diagnosis（技能根）执行；次选为在 scripts 目录下已配置 PYTHONPATH 时直接调模块。"""
    return [
        "./scripts/osops.sh precheck",
        "cd scripts && ./osops.sh precheck",
    ]


def base_guidance_block() -> Dict[str, Any]:
    """写入 precheck / diagnosis 的 data.guidance，供 Agent 解析。"""
    return {
        "session_rule": (
            "本机 memory 快速排查（`memory classify` / `oom` / `memgraph` 等，未加 `--deep-diagnosis`）"
            "默认不调 OpenAPI，不要要求用户提供 region/instance。"
            "用户只说「内存高」等泛化症状且未明确要 SysOM 远程时，应先在技能根跑本机 quick，不要一上来只问 ECS 实例 ID。"
            "远程专项（`memory … --deep-diagnosis`）内建与 `osops precheck` 等价的凭证/开通检查，"
            "不要求每次远程前再手动跑一遍 precheck。"
            "一旦进入远程专项路径，必须通过 SysOM InvokeDiagnosis/GetDiagnosisResult 获取结论；"
            "禁止用 ECS 通用诊断或 RunCommand/Cloud Assistant 手工命令采集替代。"
        ),
        "diagnosis_target_rule": (
            "以下二选一仅在要使用远程专项（`memory … --deep-diagnosis`）时适用；本机 memory quick 不适用。"
            "A) 诊断本机 — 不传 --region 与 --instance，由 CLI 从元数据补全。"
            "B) 诊断远程实例 — 须由用户提供目标 region 与 instance-id；Agent 禁止自行 curl 元数据冒充用户目标。"
        ),
        "credential_policy": (
            "禁止在对话中向用户索要、收集或请用户粘贴 AccessKey / Secret。"
            "RAM 用户 AK 路径须通过终端执行 ./scripts/osops.sh configure；"
            "密钥仅出现在用户本机终端输入，不进入聊天记录。"
            + INTERACTIVE_CONFIGURE_PTY_HINT
        ),
        "precheck_command": precheck_commands()[0],
        "configure_command": "./scripts/osops.sh configure",
        "precheck_command_alternate": precheck_commands()[1],
        "read_next": [
            DOC_PATHS_REL_SYSOM_DIAGNOSIS["openapi_permission_guide"],
            DOC_PATHS_REL_SYSOM_DIAGNOSIS["authentication"],
        ],
        "guided_steps": [
            "1) 确认工作区含完整 sysom-diagnosis（含 references/、scripts/）；在技能根执行 ./scripts/init.sh（仅首次或依赖变更后）。",
            "2) 可选：执行 ./scripts/osops.sh precheck 单独验证环境；远程子命令也会在调用 OpenAPI 前自动做同等检查。",
            "3) 若远程返回或 precheck 显示认证失败：请用户二选一——"
            "A) RAM 用户 AK（本机/非 ECS）B) ECS RAM Role（仅在阿里云 ECS 内）。"
            "选 A 则 Agent 用 Bash 执行 ./scripts/osops.sh configure（勿在聊天传密钥），再重试远程命令；"
            "无 PTY 时见 credential_policy 中的交互式 Shell 说明。"
            "选 B 则按 openapi-permission-guide §4.1 完成控制台绑角色 + CLI 的 ECS RAM Role 模式配置。",
            "4) 若 service_not_activated：在 Alinux 控制台开通 SysOM（SLR 通常随开通自动创建）；"
            "子账号开通过程报权限不足时见仓库根 RAM 专文。",
            "5) 每完成一类配置后可再执行 precheck 或直接重试远程专项命令。",
            "6) 内存域：表述已对应专项则用本机 `./scripts/osops.sh memory memgraph`（占用高/大图）"
            "或 `memory oom`（OOM）或 `memory javamem`（Java）；"
            "仍不明时用 `memory classify`（均默认不调云）。选路见 references/memory-routing.md。"
            "深度/远程入口：`./scripts/osops.sh memory <classify|memgraph|oom|javamem> … --deep-diagnosis`；"
            "专有 params 见 references/diagnoses/。",
            "7) 若失败且与实例侧相关（云助手、控制台诊断授权等），见 references/invoke-diagnosis.md。",
        ],
    }


def remediation_service_not_activated() -> List[str]:
    return [
        "场景 A-K3 / E-R4：OpenAPI 已通，但账号侧 SysOM 未开通或未就绪。",
        "步骤 1：用有权限的账号打开 https://alinux.console.aliyun.com/?source=cosh，进入 SysOM 相关入口，按页面完成「开通」。",
        "步骤 2：在 Alinux 控制台按引导完成 SysOM 开通时，通常会**自动**创建服务关联角色 AliyunServiceRoleForSysom，一般无需在控制台外单独创建；若子账号在开通步骤报无 CreateServiceLinkedRole 等权限，按仓库根《如何让RAM子用户拥有创建服务角色的权限》配置后再试。",
        "步骤 3：开通后等待 1～3 分钟，再在运行 CLI 的环境执行: " + precheck_commands()[0],
        "步骤 4：仍报相同错误时，在控制台确认 SysOM 已显示为已开通，并检查当前 AK/RAM 角色所属账号与开通账号一致。",
    ]


def auth_path_choice_block() -> Dict[str, Any]:
    """凭证未配置时：先选路径，再执行对应动作（写入 data.guidance）。"""
    return {
        "step_0": (
            "请先请用户二选一（未配置 AK 且未可用 ECS RAM Role 时）："
            "A) RAM 用户 AccessKey — 适用于本机、非 ECS、CI 等；"
            "B) ECS 实例 RAM Role — 仅当在阿里云 ECS 内运行本 CLI / Agent。"
        ),
        "path_a_ram_user_ak": {
            "label": "A — RAM 用户 AK",
            "when": "用户选择 A",
            "agent_run": (
                "在 sysom-diagnosis（技能根）目录执行 Bash（勿在对话中索要密钥）："
                "./scripts/osops.sh configure。"
                + INTERACTIVE_CONFIGURE_PTY_HINT
            ),
            "then": "配置成功后同一环境执行: " + precheck_commands()[0],
        },
        "path_b_ecs_ram_role": {
            "label": "B — ECS RAM Role",
            "when": "用户选择 B",
            "summary": (
                f"在 RAM 控制台（{RAM_CONSOLE_URL}）创建可信 ECS 的 RAM 角色并附加 AliyunSysomFullAccess；"
                "ECS 控制台将角色绑定到当前实例；"
                "在实例内将 CLI 配置为 ECS RAM Role 模式（ram-role-name 与实例绑定一致）；"
                "验证: curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/ 应返回角色名。"
            ),
            "then": "再执行: " + precheck_commands()[0],
            "read_next": [
                DOC_PATHS_REL_SYSOM_DIAGNOSIS["openapi_permission_guide"] + "（§4.1）",
                DOC_PATHS_REL_SYSOM_DIAGNOSIS["authentication"] + "（方式 1 ECS RAM Role）",
            ],
        },
    }


def remediation_auth_failed() -> List[str]:
    return [
        "场景：尚未形成可用的 SysOM 调用身份（A-K* / E-R*），或 InitialSysom 未通过。",
        "安全：不要在对话中索要或粘贴 AccessKey/Secret。",
        "步骤 0：请先请用户二选一 — A) RAM 用户 AK（本机/非 ECS） B) ECS RAM Role（仅在阿里云 ECS 内）。",
        "若选 A：Agent 应在 sysom-diagnosis（技能根）直接执行 Bash — ./scripts/osops.sh configure（交互式本地输入，不回显）；"
        + INTERACTIVE_CONFIGURE_PTY_HINT
        + " 完成后执行 " + precheck_commands()[0] + "。",
        "若选 B：按 references/openapi-permission-guide.md §4.1 与 references/authentication.md「ECS RAM Role」— "
        f"在 RAM 控制台（{RAM_CONSOLE_URL}）与 ECS 控制台完成角色与绑定 + 完成 CLI 的 ECS RAM Role 模式配置，再 "
        + precheck_commands()[0]
        + "。",
        "若 ~/.aliyun/config.json 解析失败：修复或删除后重试；选 A 可再次 ./scripts/osops.sh configure。",
    ]


def _remediation_ecs_ram_role_lines(
    *,
    role_label: str,
    ram_profile_configured: bool,
    metadata_role_bound: bool,
) -> List[str]:
    """ECS RAM Role 主路径步骤（单源）；元数据已确认绑定时省略 curl 排障行。"""
    lines: List[str] = [
        "主路径：ECS RAM Role（实例角色）。无需再配置 RAM 用户 AccessKey。",
    ]
    if role_label:
        lines.append(
            f"步骤 1：打开 RAM 控制台（{RAM_CONSOLE_URL}）→ 角色「{role_label}」→ 权限管理，"
            "确认已附加 AliyunSysomFullAccess（无则新增授权）。"
        )
    else:
        lines.append(
            f"步骤 1：打开 RAM 控制台（{RAM_CONSOLE_URL}）→ 找到配置文件中的 RAM 角色 → 权限管理，"
            "确认已附加 AliyunSysomFullAccess（无则新增授权）。"
        )
    lines.append("步骤 2：策略变更后等待约 2～5 分钟。")
    if ram_profile_configured:
        lines.append(
            "步骤 3：已配置本地 config.json 的 ECS RAM Role/RAM Role，请核对 ram-role-name 与实例绑定一致、config.json 有效。"
        )
    elif role_label:
        lines.append(
            "步骤 3：实例内将 CLI 配置为 ECS RAM Role，ram-role-name 与实例绑定一致。"
        )
    else:
        lines.append(
            "步骤 3：完成实例 RAM 角色绑定后，在实例内完成 CLI 的 ECS RAM Role 模式配置。"
        )
    if not metadata_role_bound:
        lines.append(
            "（可选排障）curl -s http://100.100.100.200/latest/meta-data/ram/security-credentials/ 应返回角色名一行。"
        )
    lines.append("最后：在技能根执行: " + precheck_commands()[0])
    return lines


def remediation_ecs_role_hint(role_name: str) -> List[str]:
    """兼容旧调用：实例已绑角色场景，与主路径 remediation 共用生成逻辑。"""
    return _remediation_ecs_ram_role_lines(
        role_label=str(role_name).strip(),
        ram_profile_configured=False,
        metadata_role_bound=True,
    )


def precheck_guidance_compact(
    primary_path: str,
    *,
    scenario_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    预检失败且已锁定单一路径时的精简 guidance：不含 session_rule / diagnosis_target_rule / guided_steps。
    """
    bg = base_guidance_block()
    out: Dict[str, Any] = {
        "credential_policy": bg["credential_policy"],
        "precheck_command": bg["precheck_command"],
        "configure_command": bg["configure_command"],
        "read_next": [
            DOC_PATHS_REL_SYSOM_DIAGNOSIS["openapi_permission_guide"],
            DOC_PATHS_REL_SYSOM_DIAGNOSIS["authentication"],
        ],
        "primary_path": primary_path,
    }
    if scenario_hint:
        out["scenario_hint"] = scenario_hint
    return out


def precheck_guidance_success_light() -> Dict[str, Any]:
    """precheck 成功时的轻量 guidance，与失败侧 precheck_compact 对称（不含 session_rule / guided_steps）。"""
    bg = base_guidance_block()
    return {
        "credential_policy": bg["credential_policy"],
        "precheck_command": bg["precheck_command"],
        "configure_command": bg["configure_command"],
        "read_next": list(bg["read_next"]),
    }


def remediation_for_precheck_failure(
    check_result: Dict[str, Any],
    path_summary: Dict[str, Any],
    *,
    needs_sysom_activation: bool,
) -> List[str]:
    """
    按 path_summary.primary_path 与 checked 进度生成 remediation；已完成步骤不重复叙述。
    """
    if needs_sysom_activation:
        return remediation_service_not_activated()

    primary = path_summary.get("primary_path") or "configure_identity"
    prog: Dict[str, Any] = dict(path_summary.get("progress") or {})
    checked: List[Dict[str, Any]] = list(check_result.get("checked") or [])
    ecs_role_name = check_result.get("ecs_role_name")
    ram_rows = [
        r
        for r in checked
        if str(r.get("method", "")).lower().startswith("配置文件 ecsramrole")
        or str(r.get("method", "")).startswith("配置文件 ECS RAM Role")
        or str(r.get("method", "")).startswith("配置文件 RAM Role")
    ]
    if not prog:
        prog = {
            "metadata_role_bound": bool(ecs_role_name)
            or any("✓" in str((r.get("status") or "")) for r in checked if r.get("method") == "ECS元数据"),
            "env_ak_attempted": any(
                r.get("method") == "环境变量 AKSK" and "未配置" not in str(r.get("status") or "")
                for r in checked
            ),
            "file_ak_attempted": any(r.get("method") == "配置文件 AKSK" for r in checked),
            "file_profile_missing_or_invalid": any(
                r.get("method") == "配置文件" and "✗" in str(r.get("status") or "") for r in checked
            ),
            "ram_profile_configured": bool(ram_rows),
        }

    if primary == "ecs_ram_role":
        role_label = str(ecs_role_name).strip() if ecs_role_name else ""
        meta_bound = bool(prog.get("metadata_role_bound"))
        ram_prof = bool(prog.get("ram_profile_configured", bool(ram_rows)))
        return _remediation_ecs_ram_role_lines(
            role_label=role_label,
            ram_profile_configured=ram_prof,
            metadata_role_bound=meta_bound,
        )

    if primary == "access_key":
        env_ok = bool(prog.get("env_ak_attempted"))
        file_ok = bool(prog.get("file_ak_attempted"))
        file_bad = bool(prog.get("file_profile_missing_or_invalid"))
        head = [
            "主路径：RAM 用户 AccessKey（环境变量或本地配置文件 AK）。无需并行配置 ECS RAM Role。",
        ]
        if env_ok and not file_ok:
            return head + [
                f"步骤 1：在 RAM 控制台（{RAM_CONSOLE_URL}）确认 RAM 用户或 AK 对应主体已附加 AliyunSysomFullAccess。",
                "步骤 2：环境变量 AK 须与 precheck 在同一 shell 进程内导出后再执行；否则改用 ./scripts/osops.sh configure 写入 ~/.aliyun。",
                "步骤 3：执行: " + precheck_commands()[0],
            ]
        if file_ok and not env_ok:
            return head + [
                "步骤 1：核对本地配置文件中的 AK 模式配置有效（密钥正确、profile 未损坏）。",
                f"步骤 2：在 RAM 控制台（{RAM_CONSOLE_URL}）确认该 RAM 用户已附加 AliyunSysomFullAccess。",
                "步骤 3：执行: " + precheck_commands()[0],
            ]
        if file_bad and not env_ok:
            return head + [
                "步骤 1：在技能根由 Agent 执行 ./scripts/osops.sh configure 重建有效配置，勿在对话中传输 Secret。",
                f"步骤 2：在 RAM 控制台（{RAM_CONSOLE_URL}）确认 RAM 用户已附加 AliyunSysomFullAccess。",
                "步骤 3：执行: " + precheck_commands()[0],
            ]
        return head + [
            "步骤 1：在技能根由 Agent 执行 ./scripts/osops.sh configure，勿在对话中传输 Secret。",
            f"步骤 2：在 RAM 控制台（{RAM_CONSOLE_URL}）确认 RAM 用户已附加 AliyunSysomFullAccess。",
            "步骤 3：若用环境变量 AK，须与 precheck 在同一 shell 进程；否则优先写入 ~/.aliyun。",
            "步骤 4：执行: " + precheck_commands()[0],
        ]

    return remediation_auth_failed()


def scenario_hint_for_error_code(error_code: Optional[str]) -> Optional[str]:
    if error_code == "service_not_activated":
        return "A-K3_or_E-R4_sysom_not_activated"
    if error_code == "sysom_role_not_exist":
        return "A-K3_or_E-R4_sysom_slr_not_ready"
    return None


def diagnosis_subsystem_minimal_guidance(
    *,
    include_console_authorization_hint: bool = False,
) -> Dict[str, Any]:
    """
    专项命令（`memory … --deep-diagnosis` 等）失败时 data 内唯一引导块：
    不展开 precheck 全量 guided_steps，避免与 error 重复。
    认证/开通类问题仍以 references/openapi-permission-guide.md 为准。
    """
    rem: List[str] = [
        "invoke 参数与「本机/远程」约定见 read_next；precheck 与账号开通见 "
        + DOC_PATHS_REL_SYSOM_DIAGNOSIS["openapi_permission_guide"]
        + "。",
    ]
    if include_console_authorization_hint:
        rem.append(
            "若 error.message 指向未授权：在 SysOM 或 ECS 控制台为目标实例完成诊断授权（勿使用已废弃 OpenAPI 授权）。"
        )
    return {
        "diagnosis_target": (
            "本机不传 --region/--instance（由 CLI 从元数据补全）；"
            "远程须由用户提供 region 与 instance-id。"
        ),
        "read_next": [DOC_PATHS_REL_SYSOM_DIAGNOSIS["invoke_diagnosis_ref"]],
        "remediation": rem,
    }
