# -*- coding: utf-8 -*-
"""将 run_precheck 结果组装为与 precheck 子命令一致的 JSON 信封（供 precheck 命令与远程门禁复用）。"""
from __future__ import annotations

from typing import Any, Dict

from sysom_cli.lib.guidance import (
    auth_path_choice_block,
    base_guidance_block,
    precheck_guidance_compact,
    precheck_guidance_success_light,
    remediation_for_precheck_failure,
    remediation_service_not_activated,
    scenario_hint_for_error_code,
)
from sysom_cli.lib.invoke_envelope_finalize import ensure_findings_finding_type
from sysom_cli.lib.precheck_summary import summarize_precheck_for_agent
from sysom_cli.lib.schema import agent_block, envelope


def envelope_from_precheck_result(check_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    check_result: run_precheck() 返回值。
    与 PrecheckCommand.execute_local 输出一致。
    """
    guidance_base = base_guidance_block()

    if check_result["ok"]:
        findings_ok = [
            {
                "severity": "info",
                "title": "认证验证通过",
                "detail": check_result["message"],
            },
            {
                "severity": "info",
                "title": "下一步",
                "detail": (
                    "precheck 已通过。可在 memory 子命令加 --deep-diagnosis 发起深度诊断。"
                    "失败时检查云助手与控制台诊断授权；见 references/openapi-permission-guide.md。"
                ),
            },
        ]
        ensure_findings_finding_type(findings_ok)
        return envelope(
            action="precheck",
            ok=True,
            agent=agent_block(
                status="normal",
                summary=f"认证方式：{check_result['method']}，验证成功",
                findings=findings_ok,
            ),
            data={
                "auth_method": check_result["method"],
                "role": check_result.get("role"),
                "api_accessible": True,
                "guidance": precheck_guidance_success_light(),
            },
            execution={"subsystem": "precheck", "mode": "local"},
        )

    err_code_pre = check_result.get("error_code")
    is_service_not_activated = err_code_pre == "service_not_activated"
    is_sysom_role_not_exist = err_code_pre == "sysom_role_not_exist"
    needs_sysom_activation = is_service_not_activated or is_sysom_role_not_exist

    err_title = "认证失败"
    if is_service_not_activated:
        err_title = "SysOM 服务未开通"
    elif is_sysom_role_not_exist:
        err_title = "SysOM 服务关联角色未就绪"

    path_summary = summarize_precheck_for_agent(check_result)
    primary_path = path_summary.get("primary_path", "configure_identity")

    error_finding = {
        "severity": "error",
        "title": err_title,
        "detail": check_result["error"],
    }

    findings: list = []

    if needs_sysom_activation:
        findings = [
            error_finding,
            {
                "severity": "info",
                "title": "处理说明",
                "detail": "具体步骤见 data.remediation。",
            },
        ]
    else:
        if primary_path in ("ecs_ram_role", "access_key"):
            findings = [
                error_finding,
                {
                    "severity": "info",
                    "title": "修复引导",
                    "detail": "请按 data.remediation 顺序执行；详细文档见 data.guidance.read_next。",
                },
            ]
        else:
            findings = [
                error_finding,
                {
                    "severity": "info",
                    "title": "选择凭证路径",
                    "detail": "见 data.guidance.auth_path_choice；步骤见 data.remediation。",
                },
            ]

    err_code = check_result.get("error_code", "auth_failed")
    scenario = scenario_hint_for_error_code(err_code)
    if needs_sysom_activation:
        scenario = scenario or "A-K3_or_E-R4_sysom_not_activated"

    if needs_sysom_activation:
        if is_sysom_role_not_exist:
            summary = (
                "SysOM 服务关联角色未就绪（InitialSysom role_exist=false）。"
                "请在 Alinux 控制台完成开通（SLR 通常随开通自动创建），等待后再 precheck"
            )
        else:
            summary = (
                "SysOM 服务未开通。请访问 https://alinux.console.aliyun.com/?source=cosh 完成服务开通"
            )
        next_steps = [
            {
                "tool": "Read",
                "args": "references/openapi-permission-guide.md",
                "reason": "场景 A-K3 / E-R4：开通与 SLR 相关引导",
            },
        ]
        remediation = remediation_service_not_activated()
        data_out = {
            "path_summary": path_summary,
            "service_activated": False,
            "activation_url": "https://alinux.console.aliyun.com/?source=cosh",
            "guidance": {
                "precheck_command": guidance_base["precheck_command"],
                "read_next": list(guidance_base["read_next"]),
            },
            "remediation": remediation,
        }
    elif primary_path == "ecs_ram_role":
        summary = f"认证失败，请按 data.remediation 完成配置。{path_summary['recommended_focus']}"
        next_steps = [
            {
                "tool": "Read",
                "args": "references/authentication.md（ECS RAM Role）",
                "reason": "角色授权与 CLI 配置细节",
            },
            {
                "tool": "Bash",
                "args": "cd <sysom-diagnosis 技能根> && ./scripts/osops.sh precheck",
                "reason": "修复后复验",
            },
        ]
        remediation = remediation_for_precheck_failure(
            check_result, path_summary, needs_sysom_activation=False
        )
        guidance_merged = precheck_guidance_compact("ecs_ram_role", scenario_hint=scenario)
        data_out: Dict[str, Any] = {
            "path_summary": path_summary,
            "guidance": guidance_merged,
            "remediation": remediation,
        }
        if check_result.get("ecs_role_name"):
            data_out["ecs_role_name"] = check_result["ecs_role_name"]
    elif primary_path == "access_key":
        summary = f"认证失败，请按 data.remediation 完成配置。{path_summary['recommended_focus']}"
        next_steps = [
            {
                "tool": "Read",
                "args": "references/authentication.md（AccessKey）",
                "reason": "AK 配置与权限",
            },
            {
                "tool": "Bash",
                "args": "cd <sysom-diagnosis 技能根> && ./scripts/osops.sh configure",
                "reason": "由 Agent 执行交互式配置（勿在对话输入密钥）",
            },
            {
                "tool": "Bash",
                "args": "cd <sysom-diagnosis 技能根> && ./scripts/osops.sh precheck",
                "reason": "配置完成后复验",
            },
        ]
        remediation = remediation_for_precheck_failure(
            check_result, path_summary, needs_sysom_activation=False
        )
        guidance_merged = precheck_guidance_compact("access_key", scenario_hint=scenario)
        data_out = {
            "path_summary": path_summary,
            "guidance": guidance_merged,
            "remediation": remediation,
        }
    else:
        summary = f"认证失败，请按 data.remediation 完成凭证配置。{path_summary['recommended_focus']}"
        next_steps = [
            {
                "tool": "AskUser",
                "args": (
                    "请选择凭证方式：A) RAM 用户 AccessKey（本机/非 ECS） "
                    "B) ECS 实例 RAM Role（仅在阿里云 ECS 内运行本 CLI）"
                ),
                "reason": "未配置凭证时必须先选路径，再执行对应配置步骤",
            },
            {
                "tool": "Bash",
                "args": "cd <sysom-diagnosis 技能根> && ./scripts/osops.sh configure",
                "reason": "仅当用户选择 A：由 Agent 直接执行交互式配置（勿在对话输入密钥）",
            },
            {
                "tool": "Bash",
                "args": "cd <sysom-diagnosis 技能根> && ./scripts/osops.sh precheck",
                "reason": "A 路径 configure 完成后，或 B 路径完成控制台+EcsRamRole 配置后复验",
            },
            {
                "tool": "Read",
                "args": "references/openapi-permission-guide.md（§4.1 ECS RAM Role）",
                "reason": "仅当用户选择 B：绑定角色与 EcsRamRole 分步说明",
            },
            {
                "tool": "Read",
                "args": "references/authentication.md",
                "reason": "AK 与 ECS RAM Role 详细步骤（控制台操作）",
            },
        ]
        remediation = remediation_for_precheck_failure(
            check_result, path_summary, needs_sysom_activation=False
        )
        guidance_merged = {
            "credential_policy": guidance_base["credential_policy"],
            "precheck_command": guidance_base["precheck_command"],
            "configure_command": guidance_base["configure_command"],
            "read_next": list(guidance_base["read_next"]),
            "auth_path_choice": auth_path_choice_block(),
        }
        data_out = {
            "path_summary": path_summary,
            "guidance": guidance_merged,
            "remediation": remediation,
        }

    ensure_findings_finding_type(findings)
    return envelope(
        action="precheck",
        ok=False,
        agent=agent_block(
            status="error",
            summary=summary,
            findings=findings,
            next_steps=next_steps,
        ),
        data=data_out,
        error={
            "code": check_result.get("error_code", "auth_failed"),
            "message": check_result["error"],
        },
        execution={"subsystem": "precheck", "mode": "local"},
    )
