# -*- coding: utf-8 -*-
"""
轮询 LHM 数据校验任务执行状态。

用法：
  python atomic-skills/lhm-poll-status/scripts/run.py \
    --task-id 12345 --batch-id 67890 --region hangzhou \
    [--timeout-sec 1800] [--interval-sec 5]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'),
)
from common import (  # noqa: E402
    build_client_from_config,
    poll_exec_status,
    EXEC_STATUS_TEXT,
)


def capture_stdout(fn, *args, **kwargs):
    """调用函数并捕获其 print 输出，避免污染 stdout 的 JSON 输出。"""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        result = fn(*args, **kwargs)
    finally:
        captured = sys.stdout.getvalue()
        sys.stdout = old_stdout
        if captured:
            sys.stderr.write(captured)
    return result


def emit_error(reason: str) -> None:
    sys.stderr.write(json.dumps({'ok': False, 'reason': reason}, ensure_ascii=False) + '\n')
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description='轮询 LHM 数据校验任务执行状态')
    parser.add_argument('--task-id', type=int, required=True, help='任务 ID')
    parser.add_argument('--batch-id', type=int, required=True, help='批次 ID')
    parser.add_argument('--timeout-sec', type=int, default=1800, help='轮询超时时间（秒），默认 1800')
    parser.add_argument('--interval-sec', type=int, default=5, help='轮询间隔（秒），默认 5')
    parser.add_argument('--region', required=True, help='中心节点，如 hangzhou / singapore')
    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=getattr(args, 'region', None),
        )
    except Exception as e:
        emit_error(f'构建客户端失败: {e}')

    try:
        final_status = capture_stdout(
            poll_exec_status,
            client,
            args.task_id,
            args.batch_id,
            timeout_sec=args.timeout_sec,
            interval_sec=args.interval_sec,
        )
    except Exception as e:
        emit_error(f'轮询状态失败: {e}')

    if final_status == -1:
        result = {
            'ok': False,
            'exec_status': -1,
            'reason': 'timeout',
        }
        sys.stderr.write(json.dumps(result, ensure_ascii=False) + '\n')
        return 1

    result = {
        'ok': True,
        'exec_status': final_status,
        'exec_status_text': EXEC_STATUS_TEXT.get(final_status, str(final_status)),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
