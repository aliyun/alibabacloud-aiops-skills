# -*- coding: utf-8 -*-
"""
轮询小Q报告 SSE 结果并输出增量解析内容。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import DEFAULT_MAX_POLL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS, poll_report_result


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="轮询小Q报告 SSE 结果")
    parser.add_argument("chat_id", help="创建会话时生成的 chatId")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="轮询间隔（秒）",
    )
    parser.add_argument(
        "--max-wait",
        type=int,
        default=DEFAULT_MAX_POLL_SECONDS,
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

    result = poll_report_result(
        args.chat_id,
        poll_interval=args.poll_interval,
        max_wait_seconds=args.max_wait,
        show_progress=True,
    )

    if result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - 终端脚本直接输出错误
        print(f"轮询失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
