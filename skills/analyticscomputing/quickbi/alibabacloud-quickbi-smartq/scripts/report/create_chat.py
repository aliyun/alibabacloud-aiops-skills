# -*- coding: utf-8 -*-
"""
创建小Q报告会话。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import create_report_chat, read_config
from common.messages import msg, set_locale


def load_resources_from_args(resources_json: Optional[str], resources_file: Optional[str]) -> Optional[List[dict]]:
    """从命令行参数读取 resources。"""
    if resources_file:
        with open(resources_file, "r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
            if isinstance(loaded, dict):
                if "resources" in loaded:
                    return loaded["resources"]
                raise ValueError(msg('report_resources_file_error'))
            return loaded
    if resources_json:
        loaded = json.loads(resources_json)
        if isinstance(loaded, dict):
            if "resources" in loaded:
                return loaded["resources"]
            raise ValueError(msg('report_resources_json_error'))
        return loaded
    return None


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="创建小Q报告会话")
    parser.add_argument("question", help="用户输入的问题")
    parser.add_argument("--resources-json", default=None, help="resources 的 JSON 字符串")
    parser.add_argument("--resources-file", default=None, help="包含 resources 的 JSON 文件")
    parser.add_argument("--chat-id", default=None, help="自定义 chatId，不传则自动生成")
    parser.add_argument("--message-id", default=None, help="自定义 messageId，不传则自动生成")
    parser.add_argument("--locale", required=True, choices=["zh_CN", "en_US"], help="语言环境: zh_CN(简体中文) 或 en_US(英文)")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""
    args = parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    set_locale(args.locale)

    config = read_config()
    resources = load_resources_from_args(args.resources_json, args.resources_file)

    result = create_report_chat(
        args.question,
        resources=resources,
        chat_id=args.chat_id,
        message_id=args.message_id,
        locale=args.locale,
        config=config,
    )

    print(f"chatId: {result['chatId']}")
    print(f"messageId: {result['messageId']}")
    print(
        json.dumps(
            {
                "chatId": result["chatId"],
                "messageId": result["messageId"],
                "statusCode": result["statusCode"],
                "response": result["response"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - 终端脚本直接输出错误
        print(msg('report_create_failed', exc=exc), file=sys.stderr)
        raise SystemExit(1)
