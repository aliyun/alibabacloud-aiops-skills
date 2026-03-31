#!/usr/bin/env python3
"""获取安全护栏安装命令并通过云助手执行安装。

用法:
  python -m scripts.install_security_guardrail \
      --instance-ids i-abc123,i-def456
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.aisc_client import AiscClient  # noqa: E402
from scripts.ecs_client import EcsClient  # noqa: E402

INSTALL_SUCCESS_MARKERS = ("=== 安装配置完成 ===",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="获取安全护栏安装命令并通过云助手执行安装"
    )
    parser.add_argument(
        "--instance-ids",
        required=True,
        help="ECS 实例 ID 列表（逗号分隔）",
    )
    parser.add_argument(
        "--type",
        default="RunShellScript",
        help="云助手命令类型（默认: RunShellScript）",
    )
    parser.add_argument(
        "--name",
        default="openclaw-security-guardrail-install",
        help="云助手命令名称",
    )
    parser.add_argument(
        "--description",
        default="Install Aliyun security guardrail",
        help="云助手命令描述",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="云助手命令超时时间（秒，默认: 600）",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=20,
        help="最大轮询次数（默认: 20）",
    )
    parser.add_argument(
        "--working-dir",
        default=None,
        help="执行目录",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="执行用户",
    )
    parser.add_argument(
        "--keep-command",
        action="store_true",
        help="是否保留命令定义（默认: 否）",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="ECS 区域（默认: cn-hangzhou）",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认: output）",
    )
    return parser.parse_args()


def _to_instance_ids(raw: str) -> list[str]:
    """将逗号分隔的实例 ID 转为列表。"""
    ids = [item.strip() for item in raw.split(",")]
    result = [item for item in ids if item]
    if not result:
        raise ValueError("请至少提供一个有效的 --instance-ids")
    return result


def _extract_install_payload(result: dict[str, Any]) -> tuple[str, int | None]:
    """提取安装命令和过期时间。"""
    # API 直接返回 {"Data": {...}, "RequestId": "...}，无 body 包裹
    data = result.get("Data", {})
    if not isinstance(data, dict):
        # API GetAIAgentPluginKey 返回结构异常，缺少 Data 段
        raise ValueError("GetAIAgentPluginKey 返回缺少 Data（无法提取安装命令）")

    # API 字段名为 InstallKey，实际内容是一条可直接执行的 shell 安装命令
    install_command = data.get("InstallKey")  # 字段名 InstallKey 为 API 规定，勿改
    if not isinstance(install_command, str) or not install_command:
        # InstallKey 字段必须为非空字符串，否则无法下发安装命令
        raise ValueError("GetAIAgentPluginKey 返回缺少有效的 InstallKey（安装命令为空）")

    expire_time = data.get("ExpireTime")
    if isinstance(expire_time, bool):
        expire_time = None
    elif isinstance(expire_time, (int, float)):
        expire_time = int(expire_time)
    else:
        expire_time = None

    return install_command, expire_time


def _format_expire_time(expire_time: int | None) -> str:
    """格式化命令过期时间。"""
    if expire_time is None:
        return "-"
    return datetime.fromtimestamp(expire_time).strftime("%Y-%m-%d %H:%M:%S")


def _wrap_bash_c(command: str) -> str:
    """将安装命令包装为 bash -c 执行。"""
    return f"bash -c {shlex.quote(command)}"


def _is_install_success(result: dict[str, Any]) -> bool:
    """根据云助手结果和安装输出判断是否视为安装成功。"""
    if result.get("InvocationStatus") == "Success":
        return True

    output = result.get("Output", "")
    if not isinstance(output, str):
        return False
    return any(marker in output for marker in INSTALL_SUCCESS_MARKERS)


def _display_status(result: dict[str, Any]) -> str:
    """返回对用户更友好的安装状态。"""
    if _is_install_success(result):
        if result.get("InvocationStatus") == "Success":
            return "Success"
        return "SuccessByMarker"
    return str(result.get("InvocationStatus", "-"))


def format_markdown(
    key_result: dict[str, Any],
    install_command: str,
    remote_command: str,
    expire_time: int | None,
    instance_ids: list[str],
    region: str,
    run_result: dict[str, Any] | None,
    execution_results: dict[str, dict[str, Any]],
) -> str:
    """将安装流程结果格式化为 Markdown。"""
    request_id = key_result.get("RequestId", "-")

    lines = [
        "# 安全护栏安装结果",
        "",
        f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 安装参数",
        "",
        f"- ECS 区域: `{region}`",
        f"- 实例 ID: `{', '.join(instance_ids)}`",
        "",
        "## 安装命令",
        "",
        f"- RequestId: `{request_id}`",
        f"- 过期时间: `{_format_expire_time(expire_time)}`",
        "",
        "原始安装命令:",
        "",
        "```bash",
        install_command,
        "```",
        "",
        "云助手下发命令:",
        "",
        "```bash",
        remote_command,
        "```",
        "",
    ]

    run_result = run_result or {}
    lines.extend(
        [
            "## 云助手返回",
            "",
            f"- CommandId: `{run_result.get('CommandId', '-')}`",
            f"- InvokeId: `{run_result.get('InvokeId', '-')}`",
            "",
            "## 执行结果",
            "",
            "| 实例 ID | 状态 | ExitCode |",
            "|---------|------|----------|",
        ]
    )

    for instance_id in instance_ids:
        one = execution_results.get(instance_id, {})
        lines.append(
            f"| {instance_id} | "
            f"{_display_status(one)} | "
            f"{one.get('ExitCode', '-')} |"
        )

    for instance_id in instance_ids:
        one = execution_results.get(instance_id, {})
        output = one.get("Output", "")
        error = one.get("Error")
        lines.extend(
            [
                "",
                f"### 输出（{instance_id}）",
                "",
                "```text",
                error or output,
                "```",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    instance_ids = _to_instance_ids(args.instance_ids)
    region = args.region or "cn-shanghai"

    # 调用 GetAIAgentPluginKey 获取安装命令（API 字段 InstallKey 实际为 shell 命令）
    print("[*] 调用 API 获取安装命令")
    aisc_client = AiscClient()
    command_result = aisc_client.get_ai_agent_plugin_command()  # 方法已改名，底层 API 不变
    install_command, expire_time = _extract_install_payload(command_result)
    remote_command = _wrap_bash_c(install_command)
    print("[+] 已获取安全护栏安装命令")
    print("")
    print("[*] 将通过云助手执行以下完整命令:")
    print(remote_command)
    print("")
    print("[+] 安装命令过期时间:" f" {_format_expire_time(expire_time)}")

    run_result: dict[str, Any] | None = None
    execution_results: dict[str, dict[str, Any]] = {}
    has_failure = False

    ecs_client = EcsClient(region=args.region)
    params = f"region={region}, instances={len(instance_ids)}, " f"type={args.type}"
    print(f"[*] 提交云助手安装命令 ({params})")
    run_result = ecs_client.run_command(
        instance_ids=instance_ids,
        command_content=remote_command,
        command_type=args.type,
        region=args.region,
        name=args.name,
        description=args.description,
        timeout=args.timeout,
        working_dir=args.working_dir,
        username=args.username,
        keep_command=True if args.keep_command else None,
    )
    print(
        "[+] 提交成功:"
        f" CommandId={run_result.get('CommandId', '-')},"
        f" InvokeId={run_result.get('InvokeId', '-')}"
    )

    invoke_id = run_result.get("InvokeId")
    if not invoke_id:
        raise ValueError("RunCommand 返回缺少 InvokeId，无法查询执行结果")

    print(
        "[*] 正在轮询安装结果 " f"(timeout={args.timeout}s, max_polls={args.max_polls})"
    )
    for instance_id in instance_ids:
        print(f"[*] 等待实例执行完成: {instance_id}")
        try:
            one_result = ecs_client.wait_command_result(
                invoke_id=invoke_id,
                instance_id=instance_id,
                timeout=args.timeout,
                max_polls=args.max_polls,
                allow_nonzero_exit=True,
            )
            one_result["DisplayStatus"] = _display_status(one_result)
            execution_results[instance_id] = one_result
            if _is_install_success(one_result):
                print(
                    "[+] 安装完成:"
                    f" instance={instance_id}, "
                    f"status={one_result.get('DisplayStatus', '-')}, "
                    f"exit_code={one_result.get('ExitCode', '-')}"
                )
            else:
                has_failure = True
                print(
                    "[!] 执行失败:"
                    f" instance={instance_id}, "
                    f"status={one_result.get('DisplayStatus', '-')}, "
                    f"exit_code={one_result.get('ExitCode', '-')}"
                )
        except Exception as e:
            has_failure = True
            execution_results[instance_id] = {
                "InvocationStatus": "Failed",
                "ExitCode": "-",
                "Output": "",
                "Error": str(e),
            }
            print("[!] 执行失败:" f" instance={instance_id}, error={e}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = {
        "called_at": datetime.now().isoformat(),
        "region": region,
        "instance_ids": instance_ids,
        "install_command": install_command,
        "remote_command": remote_command,
        "install_command_expire_time": expire_time,
        "key_result": key_result,
        "run_result": run_result,
        "execution_results": execution_results,
    }
    json_path = out_dir / "security_guardrail_install.json"
    json_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "security_guardrail_install.md"
    md_path.write_text(
        format_markdown(
            key_result=key_result,
            install_command=install_command,
            remote_command=remote_command,
            expire_time=expire_time,
            instance_ids=instance_ids,
            region=region,
            run_result=run_result,
            execution_results=execution_results,
        ),
        encoding="utf-8",
    )
    print(f"[+] Markdown → {md_path}")

    if has_failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
