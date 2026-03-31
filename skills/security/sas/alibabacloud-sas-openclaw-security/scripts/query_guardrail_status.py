#!/usr/bin/env python3
"""通过云助手查询阿里云安全护栏插件安装状态。

用法:
  python -m scripts.query_guardrail_status \
      --instance-ids i-abc123,i-def456
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ecs_client import EcsClient  # noqa: E402


PLUGIN_ID = "openclaw-security-assistant"
QUERY_COMMAND = f"openclaw plugins info {PLUGIN_ID}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过云助手查询安全护栏插件安装状态")
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
        default="openclaw-security-guardrail-status",
        help="云助手命令名称",
    )
    parser.add_argument(
        "--description",
        default="Query Aliyun security guardrail plugin status",
        help="云助手命令描述",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="云助手命令超时时间（秒，默认: 120）",
    )
    parser.add_argument(
        "--max-polls",
        type=int,
        default=12,
        help="最大轮询次数（默认: 12）",
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
    ids = [item.strip() for item in raw.split(",")]
    result = [item for item in ids if item]
    if not result:
        raise ValueError("请至少提供一个有效的 --instance-ids")
    return result


def _is_installed(result: dict[str, Any]) -> bool:
    """根据云助手返回判断插件是否已安装。"""
    return (
        result.get("InvocationStatus") == "Success"
        and str(result.get("ExitCode")) == "0"
    )


def _display_status(result: dict[str, Any]) -> str:
    """返回对用户更友好的状态。"""
    return "Installed" if _is_installed(result) else "NotInstalled"


def format_markdown(
    run_result: dict[str, Any],
    execution_results: dict[str, dict[str, Any]],
    instance_ids: list[str],
    command: str,
    region: str,
) -> str:
    """将状态查询结果格式化为 Markdown。"""
    lines = [
        "# 安全护栏状态查询结果",
        "",
        f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"区域: {region}",
        f"实例数量: {len(instance_ids)}",
        "",
        "## 查询参数",
        "",
        f"- 实例 ID: `{', '.join(instance_ids)}`",
        f"- 命令: `{command}`",
        "",
        "## 云助手返回",
        "",
        f"- CommandId: `{run_result.get('CommandId', '-')}`",
        f"- InvokeId: `{run_result.get('InvokeId', '-')}`",
        "",
        "## 查询结果",
        "",
        "| 实例 ID | 插件状态 | InvocationStatus | ExitCode |",
        "|---------|----------|------------------|----------|",
    ]

    for instance_id in instance_ids:
        one = execution_results.get(instance_id, {})
        lines.append(
            f"| {instance_id} | "
            f"{_display_status(one)} | "
            f"{one.get('InvocationStatus', '-')} | "
            f"{one.get('ExitCode', '-')} |"
        )

    for instance_id in instance_ids:
        one = execution_results.get(instance_id, {})
        lines.extend(
            [
                "",
                f"### 输出（{instance_id}）",
                "",
                "```text",
                one.get("Output") or one.get("Error", ""),
                "```",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    instance_ids = _to_instance_ids(args.instance_ids)
    region = args.region or "cn-shanghai"
    client = EcsClient(region=args.region)

    params = f"region={region}, instances={len(instance_ids)}, " f"type={args.type}"
    print(f"[*] 提交云助手状态查询命令 ({params})")
    print(f"[*] 查询命令: {QUERY_COMMAND}")

    run_result = client.run_command(
        instance_ids=instance_ids,
        command_content=QUERY_COMMAND,
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
        "[*] 正在轮询状态查询结果 "
        f"(timeout={args.timeout}s, max_polls={args.max_polls})"
    )
    execution_results: dict[str, dict[str, Any]] = {}
    has_uninstalled = False
    has_error = False

    for instance_id in instance_ids:
        print(f"[*] 等待实例执行完成: {instance_id}")
        try:
            one_result = client.wait_command_result(
                invoke_id=invoke_id,
                instance_id=instance_id,
                timeout=args.timeout,
                max_polls=args.max_polls,
                allow_nonzero_exit=True,
            )
            execution_results[instance_id] = one_result

            if _is_installed(one_result):
                print("[+] 查询完成:" f" instance={instance_id}, status=Installed")
            else:
                has_uninstalled = True
                print(
                    "[!] 查询完成:"
                    f" instance={instance_id}, status=NotInstalled, "
                    f"exit_code={one_result.get('ExitCode', '-')}"
                )
        except Exception as e:
            has_error = True
            execution_results[instance_id] = {
                "InvocationStatus": "Failed",
                "ExitCode": "-",
                "Output": "",
                "Error": str(e),
            }
            print("[!] 查询失败:" f" instance={instance_id}, error={e}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = {
        "submitted_at": datetime.now().isoformat(),
        "region": region,
        "instance_ids": instance_ids,
        "command": QUERY_COMMAND,
        "run_result": run_result,
        "execution_results": execution_results,
    }
    json_path = out_dir / "guardrail_status.json"
    json_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "guardrail_status.md"
    md_path.write_text(
        format_markdown(
            run_result=run_result,
            execution_results=execution_results,
            instance_ids=instance_ids,
            command=QUERY_COMMAND,
            region=region,
        ),
        encoding="utf-8",
    )
    print(f"[+] Markdown → {md_path}")

    if has_error:
        raise SystemExit(1)
    if has_uninstalled:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
