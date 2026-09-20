# -*- coding: utf-8 -*-
"""
重跑 LHM 数据校验批次中的失败任务。

对应外层 scripts/common.py 的 rerun_failed()，输出 JSON 到 stdout。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))
from common import build_client_from_config, rerun_failed


def main() -> None:
    parser = argparse.ArgumentParser(description='重跑 LHM 数据校验批次中的失败任务')
    parser.add_argument('--batch-id', required=True, type=int, help='原批次 ID')
    parser.add_argument(
        '--fail-type',
        type=int,
        default=0,
        choices=[0, 1, 2],
        help='重跑类型：0=仅失败 1=失败+不通过 2=失败+被终止',
    )
    parser.add_argument('--region', default='hangzhou', help='中心节点，如 hangzhou / singapore')
    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=getattr(args, 'region', None),
        )

        # rerun_failed 内部会 print，重定向 stdout 保证只输出 JSON
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            new_batch_id = rerun_failed(client, args.batch_id, fail_type=args.fail_type)
        finally:
            sys.stdout = old_stdout

        print(json.dumps({'ok': True, 'new_batch_id': new_batch_id}, ensure_ascii=False))
    except Exception as e:
        print(
            json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
