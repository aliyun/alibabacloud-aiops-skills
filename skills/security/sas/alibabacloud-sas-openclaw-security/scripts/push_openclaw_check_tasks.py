#!/usr/bin/env python3
"""按 UUID 下发 OpenClaw 漏洞与基线检查任务。

用法:
  python -m scripts.push_openclaw_check_tasks \
      --uuid sas-xxxxxxxx
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.sas_client import SasClient  # noqa: E402


DEFAULT_TASKS = "OVAL_ENTITY,CMS,SYSVUL,SCA,HEALTH_CHECK"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按 UUID 下发漏洞与基线检查任务")
    parser.add_argument(
        "--uuid",
        required=True,
        help="云安全中心实例 UUID",
    )
    parser.add_argument(
        "--tasks",
        default=DEFAULT_TASKS,
        help=("任务列表（默认: " "OVAL_ENTITY,CMS,SYSVUL,SCA,HEALTH_CHECK）"),
    )
    parser.add_argument(
        "--region",
        default=None,
        help="区域（默认: cn-shanghai）",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认: output）",
    )
    return parser.parse_args()


def _extract_push_results(body: dict) -> list[dict]:
    """兼容提取 PushTaskResultList。"""
    if not isinstance(body, dict):
        return []
    push_task_rsp = body.get("PushTaskRsp", {})
    if isinstance(push_task_rsp, dict):
        result_list = push_task_rsp.get("PushTaskResultList")
        if isinstance(result_list, list):
            return result_list
    return []


def format_markdown(
    uuid: str,
    tasks: str,
    result: dict,
) -> str:
    """将下发结果格式化为 Markdown。"""
    push_results = _extract_push_results(result)
    success_count = sum(1 for item in push_results if item.get("Success"))

    lines = [
        "# OpenClaw 检查任务下发结果",
        "",
        f"下发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"UUID: {uuid}",
        f"任务: `{tasks}`",
        "",
        "## 下发结果",
        "",
        f"- 目标实例数: {len(push_results)}",
        f"- 下发成功: {success_count}",
        f"- 下发失败: {len(push_results) - success_count}",
        "",
    ]

    if push_results:
        lines.extend(
            [
                "| 序号 | 实例名 | IP | 区域 | 在线 | 结果 |",
                "|------|--------|----|------|------|------|",
            ]
        )
        for i, item in enumerate(push_results, 1):
            name = item.get("InstanceName", "-")
            ip = item.get("Ip", "-")
            region = item.get("Region", "-")
            online = "是" if item.get("Online") else "否"
            success = "成功" if item.get("Success") else "失败"
            lines.append(
                f"| {i} | {name} | {ip} | {region} | " f"{online} | {success} |"
            )
        lines.append("")
    else:
        lines.append("未返回 PushTaskResultList。")
        lines.append("")

    lines.extend(
        [
            "## 下一步",
            "",
            "- 已触发漏洞与基线检查任务，请等待 **2-3 分钟** 后再查询结果。",
            "- 漏洞查询命令: "
            "`python -m scripts.check_openclaw_vulns --uuids <UUID>`",
            "- 基线查询命令: "
            "`python -m scripts.check_openclaw_baseline --uuid <UUID>`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = SasClient(region=args.region)

    print("[*] 下发检查任务 " f"(uuid={args.uuid}, tasks={args.tasks})")
    result = client.modify_push_all_task(
        uuids=args.uuid,
        tasks=args.tasks,
    )

    push_results = _extract_push_results(result)
    success_count = sum(1 for item in push_results if item.get("Success"))
    print(f"[+] 下发完成: 成功 {success_count}/" f"{len(push_results)}")
    print("[!] 提示: 请等待 2-3 分钟后再查询漏洞和基线结果")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = {
        "triggered_at": datetime.now().isoformat(),
        "uuid": args.uuid,
        "tasks": args.tasks,
        "result": result,
    }
    json_path = out_dir / "openclaw_push_check_tasks.json"
    json_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[+] JSON → {json_path}")

    md_path = out_dir / "openclaw_push_check_tasks.md"
    md_path.write_text(
        format_markdown(
            uuid=args.uuid,
            tasks=args.tasks,
            result=result,
        ),
        encoding="utf-8",
    )
    print(f"[+] Markdown → {md_path}")


if __name__ == "__main__":
    main()
