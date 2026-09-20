# -*- coding: utf-8 -*-
"""
创建并触发 LHM 逐表指标校验任务。

作为内层原子 Skill，本脚本不反问用户，所有参数均通过命令行传入，
结果以 JSON 形式输出到 stdout；异常时输出 JSON 到 stderr 并 exit(1)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

# 复用外层 scripts/common.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))
from common import (  # noqa: E402
    build_client_from_config,
    build_engine_arg,
    resolve_data_source,
    resolve_engine_alias,
    run_metric_check,
)


def parse_threshold(value):
    """解析 threshold 参数：'none' 或省略表示 None，否则转为 float。"""
    if value is None or str(value).lower() == 'none':
        return None
    return float(value)


def main():
    parser = argparse.ArgumentParser(description='创建并触发逐表指标校验')
    parser.add_argument('--task-name', required=True, help='任务名称')
    parser.add_argument('--src-alias', default=None, help='源端数据源别名（从 data_validation_config.yaml 解析，与 --src-ds-* 互斥）')
    parser.add_argument('--src-ds-id', required=False, default=None, help='源端数据源 ID')
    parser.add_argument('--src-ds-name', required=False, default=None, help='源端数据源名称')
    parser.add_argument('--src-ds-type', required=False, default=None, help='源端数据源类型，如 MySQL、MaxCompute')
    parser.add_argument('--dst-alias', default=None, help='目标端数据源别名（从 data_validation_config.yaml 解析，与 --dst-ds-* 互斥）')
    parser.add_argument('--dst-ds-id', required=False, default=None, help='目标端数据源 ID')
    parser.add_argument('--dst-ds-name', required=False, default=None, help='目标端数据源名称')
    parser.add_argument('--dst-ds-type', required=False, default=None, help='目标端数据源类型，如 Hive、MaxCompute')
    parser.add_argument('--src-engine-alias', default=None, help='源端引擎别名（取 data_sources 中该别名的 engine_* 字段）')
    parser.add_argument('--src-engine-id', default=None, help='源端校验引擎 ID（显式指定，优先级最高）')
    parser.add_argument('--src-engine-name', default=None, help='源端校验引擎名称')
    parser.add_argument('--src-engine-type', default=None, help='源端校验引擎类型，如 MaxCompute')
    parser.add_argument('--dst-engine-alias', default=None, help='目标端引擎别名')
    parser.add_argument('--dst-engine-id', default=None, help='目标端校验引擎 ID')
    parser.add_argument('--dst-engine-name', default=None, help='目标端校验引擎名称')
    parser.add_argument('--dst-engine-type', default=None, help='目标端校验引擎类型')
    parser.add_argument('--no-auto-engine', action='store_true', help='禁用引擎自动解析（沿用旧行为：引擎留空）')
    parser.add_argument(
        '--tables-json',
        required=True,
        help=(
            'JSON 数组，元素为 dict：'
            '{"source_table": "...", "target_table": "...", '
            '"source_partition": "...", "target_partition": "...", '
            '"source_columns": "...", "target_columns": "..."}'
        ),
    )
    parser.add_argument(
        '--check-template-id',
        default='1001',
        help='校验模板 ID，默认 1001（MIX）',
    )
    parser.add_argument(
        '--threshold',
        type=parse_threshold,
        default=None,
        help='指标阈值，默认 None 表示不传；传 0.0 时明确传给 SDK',
    )
    parser.add_argument('--source-global-params', default=None, help='源端全局参数（可选）')
    parser.add_argument('--target-global-params', default=None, help='目标端全局参数（可选）')
    parser.add_argument('--region', required=False, default=None, help='中心节点逻辑名，如 hangzhou / singapore')

    args = parser.parse_args()

    try:
        tables = json.loads(args.tables_json)
        if not isinstance(tables, list):
            raise ValueError('tables-json 必须是 JSON 数组')
        for i, item in enumerate(tables):
            if not isinstance(item, dict):
                raise ValueError(f'tables-json 第 {i + 1} 个元素必须是 dict')
            for key in ('source_table', 'target_table'):
                if key not in item:
                    raise ValueError(f'tables-json 第 {i + 1} 个元素缺少必填字段 {key}')

        client = build_client_from_config(
            region=args.region,
        )

        # 解析数据源：别名优先，其次用 CLI 参数
        if args.src_alias:
            src_ds = resolve_data_source(args.src_alias)
        elif args.src_ds_id and args.src_ds_name and args.src_ds_type:
            src_ds = (args.src_ds_id, args.src_ds_name, args.src_ds_type)
        else:
            raise RuntimeError('源端数据源：必须提供 --src-alias 或 --src-ds-id/name/type')

        if args.dst_alias:
            dst_ds = resolve_data_source(args.dst_alias)
        elif args.dst_ds_id and args.dst_ds_name and args.dst_ds_type:
            dst_ds = (args.dst_ds_id, args.dst_ds_name, args.dst_ds_type)
        else:
            raise RuntimeError('目标端数据源：必须提供 --dst-alias 或 --dst-ds-id/name/type')

        # 解析校验引擎：显式参数 > 数据源别名条目里的 engine_* > 自动解析（在 common 内完成）
        src_engine = build_engine_arg(
            engine_alias=args.src_engine_alias,
            engine_id=args.src_engine_id,
            engine_name=args.src_engine_name,
            engine_type=args.src_engine_type,
        )
        if src_engine is None and args.src_alias:
            src_engine = resolve_engine_alias(args.src_alias)
        dst_engine = build_engine_arg(
            engine_alias=args.dst_engine_alias,
            engine_id=args.dst_engine_id,
            engine_name=args.dst_engine_name,
            engine_type=args.dst_engine_type,
        )
        if dst_engine is None and args.dst_alias:
            dst_engine = resolve_engine_alias(args.dst_alias)
        engines: dict = {}

        task_id, batch_id = run_metric_check(
            client,
            args.task_name,
            src_ds,
            dst_ds,
            tables,
            check_template_id=args.check_template_id,
            threshold=args.threshold,
            source_global_params=args.source_global_params,
            target_global_params=args.target_global_params,
            src_engine=src_engine,
            dst_engine=dst_engine,
            auto_bind_engine=not args.no_auto_engine,
            engines_out=engines,
        )

        result = {
            'ok': True,
            'task_id': task_id,
            'batch_id': batch_id,
            'engines': engines.get('bound', {}),
            'engine_warnings': engines.get('warnings', []),
        }
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + '\n')
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}
        sys.stderr.write(json.dumps(err, ensure_ascii=False) + '\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
