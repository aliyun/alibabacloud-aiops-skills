# -*- coding: utf-8 -*-
"""
获取 LHM 数据校验批次概览。

用法：
  python atomic-skills/lhm-report-summary/scripts/run.py \
    --batch-id 67890 --region hangzhou
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
from common import build_client_from_config, summarize_batch  # noqa: E402


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
    parser = argparse.ArgumentParser(description='获取 LHM 数据校验批次概览')
    parser.add_argument('--batch-id', type=int, required=True, help='批次 ID')
    parser.add_argument('--region', required=True, help='中心节点，如 hangzhou / singapore')
    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=getattr(args, 'region', None),
        )
    except Exception as e:
        emit_error(f'构建客户端失败: {e}')

    try:
        summary = capture_stdout(summarize_batch, client, args.batch_id)
    except Exception as e:
        emit_error(f'获取批次概览失败: {e}')

    result = dict(summary)
    result['ok'] = True
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
