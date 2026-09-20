# -*- coding: utf-8 -*-
"""
诊断 LHM 数据校验批次的不通过原因。

对应外层 scripts/common.py 的 diagnose_failed()，输出 JSON 到 stdout。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))
from common import build_client_from_config, diagnose_failed


def main() -> None:
    parser = argparse.ArgumentParser(description='诊断 LHM 数据校验批次的不通过原因')
    parser.add_argument('--batch-id', required=True, type=int, help='批次 ID')
    parser.add_argument(
        '--group-by-field',
        action='store_true',
        default=False,
        help='按字段分组输出结构化字典（默认扁平列表）',
    )
    parser.add_argument('--region', default='hangzhou', help='中心节点，如 hangzhou / singapore')
    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=getattr(args, 'region', None),
        )

        # diagnose_failed 内部无 print，但为严格保证 stdout 只有 JSON，重定向 stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            diagnosis = diagnose_failed(
                client, args.batch_id, group_by_field=args.group_by_field
            )
        finally:
            sys.stdout = old_stdout

        print(json.dumps({'ok': True, 'diagnosis': diagnosis}, ensure_ascii=False))
    except Exception as e:
        print(
            json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
