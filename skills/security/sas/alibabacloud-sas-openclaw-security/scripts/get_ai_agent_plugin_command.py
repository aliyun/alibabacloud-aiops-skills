#!/usr/bin/env python3
"""调用 AISC GetAIAgentPluginKey，获取 OpenClaw 安全助手的安装命令。

注意：API 名称为 GetAIAgentPluginKey、字段为 InstallKey，但实际返回的是
一条可直接执行的 shell 安装命令，而非传统意义的密钥。

用法:
  python -m scripts.get_ai_agent_plugin_key
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.aisc_client import AiscClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        # API 名称保持原样（GetAIAgentPluginKey），但实际获取的是安装命令
        description="调用 AISC GetAIAgentPluginKey，获取 OpenClaw 安全助手安装命令"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="输出目录（默认: output）",
    )
    return parser.parse_args()


def format_markdown(result: dict) -> str:
    """将调用结果格式化为 Markdown。"""
    data = result.get("Data", {})
    request_id = result.get("RequestId", "-")
    # API 字段名为 InstallKey，实际含义是安装命令（install command）
    install_command = data.get("InstallKey", "-")  # 字段名 InstallKey 为 API 规定，勿改
    expire_time = data.get("ExpireTime", "-")

    lines = [
        # 标题保留 API 名称，方便源码追溯
        "# AISC GetAIAgentPluginKey 调用结果（获取安装命令）",
        "",
        f"调用时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 响应概览",
        "",
        f"- RequestId: `{request_id}`",
        f"- ExpireTime: `{expire_time}`",
        "",
        "## 安装命令",
        "",
        "```bash",
        install_command,  # 这里输出的是安装命令字符串
        "```",
        "",
        "## 完整响应",
        "",
        "```json",
        json.dumps(result, ensure_ascii=False, indent=2),
        "```",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    client = AiscClient()

    # API 名称为 GetAIAgentPluginKey，返回值为安装命令
    print("[*] 调用 GetAIAgentPluginKey（获取安装命令）")
    result = client.get_ai_agent_plugin_command()  # 方法已改名，底层调用的 API 不变
    print("[+] 调用完成")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 输出文件名使用 plugin_command 以准确语义
    raw_path = out_dir / "ai_agent_plugin_command.json"
    raw_path.write_text(
        json.dumps(
            {
                "called_at": datetime.now().isoformat(),
                "response": result,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[+] JSON → {raw_path}")

    md_path = out_dir / "ai_agent_plugin_command.md"
    md_path.write_text(
        format_markdown(result),
        encoding="utf-8",
    )
    print(f"[+] Markdown → {md_path}")


if __name__ == "__main__":
    main()
