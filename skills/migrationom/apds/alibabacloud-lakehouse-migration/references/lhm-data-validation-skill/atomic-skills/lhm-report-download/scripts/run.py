# -*- coding: utf-8 -*-
"""
下载 LHM 数据校验报告。

用法：
  python atomic-skills/lhm-report-download/scripts/run.py \
    --batch-id 67890 --region hangzhou \
    [--timeout-sec 300] [--interval-sec 3]
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
from common import build_client_from_config, download_report  # noqa: E402


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
    parser = argparse.ArgumentParser(description='下载 LHM 数据校验报告')
    parser.add_argument('--batch-id', type=int, required=True, help='批次 ID')
    parser.add_argument('--timeout-sec', type=int, default=300, help='报告生成超时时间（秒），默认 300')
    parser.add_argument('--interval-sec', type=int, default=3, help='报告生成轮询间隔（秒），默认 3')
    parser.add_argument('--region', required=True, help='中心节点，如 hangzhou / singapore')
    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=getattr(args, 'region', None),
        )
    except Exception as e:
        emit_error(f'构建客户端失败: {e}')

    try:
        oss_url = capture_stdout(
            download_report,
            client,
            args.batch_id,
            timeout_sec=args.timeout_sec,
            interval_sec=args.interval_sec,
        )
    except Exception as e:
        emit_error(f'下载报告失败: {e}')

    result = {
        'ok': True,
        'oss_url': oss_url,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
