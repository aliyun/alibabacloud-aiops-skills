# -*- coding: utf-8 -*-
"""
查询可用校验引擎 / 给已有任务绑定校验引擎。

作为内层原子 Skill，本脚本不反问用户，所有参数均通过命令行传入，
结果以 JSON 形式输出到 stdout；异常时输出 JSON 到 stderr 并 exit(1)。

子命令：
  list  — 查询某数据源类型下可用的校验引擎
  bind  — 给已有任务绑定校验引擎（UpdateDataCheckTask，部分更新，安全）
  show  — 回读任务当前绑定的引擎
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
    bind_task_engine,
    build_client_from_config,
    build_engine_arg,
    get_task_engine,
    list_ds_engine_types,
    list_engine_datasources,
    remember_engine_choice,
    resolve_engine_alias,
)


def cmd_list(client, args):
    engine_types = []
    if args.check_type is not None or args.template_id:
        try:
            engine_types = list_ds_engine_types(
                client, args.ds_type, args.check_type, args.template_id
            )
        except Exception as e:
            print(f'[engine] 查询引擎类型失败，不做过滤: {e}', file=sys.stderr)
    candidates = list_engine_datasources(client, args.ds_type, engine_types)
    return {
        'ok': True,
        'ds_type': args.ds_type,
        'allowed_engine_types': engine_types,
        'count': len(candidates),
        'engines': [
            {'id': c[0], 'name': c[1], 'type': c[2]} for c in candidates
        ],
    }


def cmd_bind(client, args):
    src_engine = build_engine_arg(
        engine_alias=args.src_engine_alias,
        engine_id=args.src_engine_id,
        engine_name=args.src_engine_name,
        engine_type=args.src_engine_type,
    )
    dst_engine = build_engine_arg(
        engine_alias=args.dst_engine_alias,
        engine_id=args.dst_engine_id,
        engine_name=args.dst_engine_name,
        engine_type=args.dst_engine_type,
    )
    if src_engine is None and dst_engine is None:
        raise RuntimeError(
            '至少指定一端引擎：--src-engine-id/--src-engine-alias 或 '
            '--dst-engine-id/--dst-engine-alias'
        )
    bind_task_engine(client, args.task_id, src_engine, dst_engine)
    bound = get_task_engine(client, args.task_id)
    if args.remember_ds_id and src_engine:
        remember_engine_choice(args.remember_ds_id, src_engine, args.check_type)
    return {'ok': True, 'task_id': args.task_id, 'engines': bound}


def cmd_show(client, args):
    return {
        'ok': True,
        'task_id': args.task_id,
        'engines': get_task_engine(client, args.task_id),
    }


def main():
    parser = argparse.ArgumentParser(description='校验引擎查询与绑定')
    parser.add_argument('--region', default=None, help='中心节点逻辑名，如 hangzhou / singapore')
    sub = parser.add_subparsers(dest='command', required=True)

    p_list = sub.add_parser('list', help='查询可用校验引擎')
    p_list.add_argument('--ds-type', required=True, help='数据源类型，如 MaxCompute、Hive')
    p_list.add_argument('--check-type', type=int, default=None, help='校验类型：0 数据量 / 1 指标 / 2 弱内容')
    p_list.add_argument('--template-id', default=None, help='校验模板 ID（不传按 check-type 取内置模板）')

    p_bind = sub.add_parser('bind', help='给已有任务绑定校验引擎')
    p_bind.add_argument('--task-id', type=int, required=True, help='任务 ID')
    p_bind.add_argument('--src-engine-alias', default=None, help='源端引擎别名（读配置 engine_* 字段）')
    p_bind.add_argument('--src-engine-id', default=None, help='源端校验引擎 ID')
    p_bind.add_argument('--src-engine-name', default=None, help='源端校验引擎名称')
    p_bind.add_argument('--src-engine-type', default=None, help='源端校验引擎类型')
    p_bind.add_argument('--dst-engine-alias', default=None, help='目标端引擎别名')
    p_bind.add_argument('--dst-engine-id', default=None, help='目标端校验引擎 ID')
    p_bind.add_argument('--dst-engine-name', default=None, help='目标端校验引擎名称')
    p_bind.add_argument('--dst-engine-type', default=None, help='目标端校验引擎类型')
    p_bind.add_argument('--remember-ds-id', default=None, help='把本次源端选择记忆到该数据源 ID 上')
    p_bind.add_argument('--check-type', type=int, default=None, help='记忆时区分校验类型（可选）')

    p_show = sub.add_parser('show', help='回读任务已绑定的引擎')
    p_show.add_argument('--task-id', type=int, required=True, help='任务 ID')

    args = parser.parse_args()

    try:
        client = build_client_from_config(
            region=args.region,
        )
        handler = {'list': cmd_list, 'bind': cmd_bind, 'show': cmd_show}[args.command]
        result = handler(client, args)
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + '\n')
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}
        sys.stderr.write(json.dumps(err, ensure_ascii=False) + '\n')
        sys.exit(1)


if __name__ == '__main__':
    main()
