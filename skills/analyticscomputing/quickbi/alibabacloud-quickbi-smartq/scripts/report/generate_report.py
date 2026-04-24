# -*- coding: utf-8 -*-
"""
一键生成小Q报告：上传文件 -> 创建会话 -> 轮询结果。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import (
    UPLOAD_CHAT_TYPE,
    create_report_chat,
    poll_report_result,
    read_config,
    upload_files,
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="一键生成小Q报告")
    parser.add_argument("question", help="用户输入的问题")
    parser.add_argument("files", nargs="*", help="可选的本地文件路径")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="轮询间隔（秒）",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=30 * 60,
        help="最大等待时间（秒）",
    )
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""
    args = parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    config = read_config()
    resources: List[Dict[str, Any]] = []
    upload_result: Dict[str, Any] = {}

    if args.files:
        upload_result = upload_files(args.files, config=config)
        resources = upload_result["resources"]
        print(
            json.dumps(
                {
                    "chatType": UPLOAD_CHAT_TYPE,
                    "fileCount": len(args.files),
                    "resources": resources,
                    "summary": f"已上传 {len(args.files)} 个文件",
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )

    create_result = create_report_chat(
        args.question,
        resources=resources,
        config=config,
    )

    print(f"chatId: {create_result['chatId']}", flush=True)
    print(f"messageId: {create_result['messageId']}", flush=True)

    poll_result = poll_report_result(
        create_result["chatId"],
        poll_interval=args.poll_interval,
        max_wait_seconds=args.max_wait,
        show_progress=True,
        config=config,
    )

    final_output = {
        "chatId": create_result["chatId"],
        "messageId": create_result["messageId"],
        # 与 poll_report_result 一致：仅轮询正常完成时才有回放地址
        "reportUrl": poll_result.get("reportUrl"),
        "finished": poll_result["finished"],
        "error": poll_result.get("error"),
        "eventCount": poll_result["eventCount"],
        "tokenInfo": poll_result["tokenInfo"],
        "resources": resources,
        "uploadResults": upload_result.get("uploadResults", []),
        "createResponse": create_result["response"],
    }
    print(
        json.dumps(
            final_output,
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - 终端脚本直接输出错误
        print(f"生成报告失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
