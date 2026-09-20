# -*- coding: utf-8 -*-
"""
LHM 校验模板管理 — CRUD 统一入口。

通过 --action 分发操作：list / detail / create / update / delete。

用法：
  python atomic-skills/lhm-template-manage/scripts/run.py \
    --action list [--check-type 1] [--name "MIX"] [--is-builtin 1]

  python atomic-skills/lhm-template-manage/scripts/run.py \
    --action detail --template-id <UUID>

  python atomic-skills/lhm-template-manage/scripts/run.py \
    --action create --name "模板名" --check-type 1 \
    --ds-engine-rels-json '[...]' --metric-rules-json '[...]'

  python atomic-skills/lhm-template-manage/scripts/run.py \
    --action update --template-id <UUID> --metric-rules-json '[...]'

  python atomic-skills/lhm-template-manage/scripts/run.py \
    --action delete --template-ids <UUID1>,<UUID2>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'),
)
from common import (  # noqa: E402
    build_client_from_config,
    list_templates,
    get_template_detail,
    create_template,
    update_template,
    delete_templates,
)


def emit_error(reason: str) -> None:
    sys.stderr.write(json.dumps({'ok': False, 'reason': reason}, ensure_ascii=False) + '\n')
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description='LHM 校验模板管理')
    parser.add_argument('--action', required=True,
                        choices=['list', 'detail', 'create', 'update', 'delete'],
                        help='操作类型')

    # 通用参数
    parser.add_argument('--region', default=None, help='中心节点（hangzhou/singapore）')

    # list 筛选
    parser.add_argument('--check-type', type=int, default=None, help='校验类型 (0/1/2)')
    parser.add_argument('--name', default=None, help='模板名称模糊匹配')
    parser.add_argument('--is-builtin', type=int, default=None, help='0=自定义, 1=内置')

    # detail / update / delete
    parser.add_argument('--template-id', default=None, help='模板 ID')
    parser.add_argument('--template-ids', default=None, help='批量删除的模板 ID（逗号分隔）')

    # create / update 共用
    parser.add_argument('--template-name', default=None, help='模板名称（create/update）')
    parser.add_argument('--template-desc', default=None, help='模板描述')
    parser.add_argument('--ds-engine-rels-json', default=None,
                        help='数据源-引擎映射 JSON，如 \'[{"dsType":"MaxCompute","engineTypes":["MaxCompute"]}\'')

    # create 指标规则
    parser.add_argument('--metric-rules-json', default=None,
                        help='指标规则 JSON 数组')

    # create 弱内容规则
    parser.add_argument('--weak-content-rule-json', default=None,
                        help='弱内容规则 JSON 对象')

    args = parser.parse_args()

    # ── 构建客户端 ──
    try:
        client = build_client_from_config(
            region=args.region,
        )
    except Exception as e:
        emit_error(f'构建客户端失败: {e}')

    # ── 分发 ──
    try:
        if args.action == 'list':
            result = _do_list(client, args)
        elif args.action == 'detail':
            result = _do_detail(client, args)
        elif args.action == 'create':
            result = _do_create(client, args)
        elif args.action == 'update':
            result = _do_update(client, args)
        elif args.action == 'delete':
            result = _do_delete(client, args)
        else:
            emit_error(f'未知 action: {args.action}')
            return 1

        result['ok'] = True
        print(json.dumps(result, ensure_ascii=False))
        return 0

    except Exception as e:
        sys.stderr.write(json.dumps(
            {'ok': False, 'reason': str(e), 'traceback': traceback.format_exc()},
            ensure_ascii=False,
        ) + '\n')
        return 1


# ─────────────────────────────────────────────
# action handlers
# ─────────────────────────────────────────────

def _do_list(client, args) -> dict:
    templates = list_templates(
        client,
        check_type=args.check_type,
        name=args.name,
        is_builtin=args.is_builtin,
    )
    return {'templates': templates}


def _do_detail(client, args) -> dict:
    if not args.template_id:
        emit_error('detail 需要 --template-id')
    detail = get_template_detail(client, args.template_id)
    return {'template': detail}


def _do_create(client, args) -> dict:
    if not args.template_name:
        emit_error('create 需要 --template-name')
    if args.check_type is None:
        emit_error('create 需要 --check-type')

    ds_engine_rels = json.loads(args.ds_engine_rels_json) if args.ds_engine_rels_json else None
    if not ds_engine_rels:
        emit_error('create 需要 --ds-engine-rels-json')

    metric_rules = json.loads(args.metric_rules_json) if args.metric_rules_json else None
    weak_content_rule = json.loads(args.weak_content_rule_json) if args.weak_content_rule_json else None

    template_id = create_template(
        client,
        name=args.template_name,
        check_type=args.check_type,
        ds_engine_rels=ds_engine_rels,
        metric_rules=metric_rules,
        weak_content_rule=weak_content_rule,
        desc=args.template_desc,
    )
    return {'templateId': template_id}


def _do_update(client, args) -> dict:
    if not args.template_id:
        emit_error('update 需要 --template-id')

    ds_engine_rels = json.loads(args.ds_engine_rels_json) if args.ds_engine_rels_json else None
    metric_rules = json.loads(args.metric_rules_json) if args.metric_rules_json else None
    weak_content_rule = json.loads(args.weak_content_rule_json) if args.weak_content_rule_json else None

    update_template(
        client,
        template_id=args.template_id,
        name=args.template_name,
        check_type=args.check_type,
        ds_engine_rels=ds_engine_rels,
        metric_rules=metric_rules,
        weak_content_rule=weak_content_rule,
        desc=args.template_desc,
    )
    return {'updated': True, 'templateId': args.template_id}


def _do_delete(client, args) -> dict:
    if not args.template_ids:
        emit_error('delete 需要 --template-ids')
    ids = [s.strip() for s in args.template_ids.split(',') if s.strip()]
    delete_templates(client, ids)
    return {'deleted': True, 'templateIds': ids}


if __name__ == '__main__':
    sys.exit(main())
