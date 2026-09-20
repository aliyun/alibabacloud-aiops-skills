# -*- coding: utf-8 -*-
"""
lhm-common CLI 入口

四个子命令：
  config  — 配置管理（get/set/list/add-ds/remove-ds/show）
  client  — 构建并验证 LHM 客户端（网络层走 aliyun CLI）
  check   — 前置条件检查（按 profile）
  setup   — 引导式配置（分步写入 data_validation_config.yaml）

所有输出为 JSON（stderr 打印进度信息，stdout 输出结构化结果）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# 复用外层 common.py
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(os.path.dirname(_HERE), '..', '..', 'scripts')
sys.path.insert(0, os.path.normpath(_SCRIPTS_DIR))

from common import (
    build_client,
    check_agent_status,
    check_resource_group_status,
    check_resp,
    list_engine_datasources,
    load_config,
    recall_engine_choice,
    save_config,
    CONFIG_PATH,
    ENGINE_REQUIRED_DS_TYPES,
    REGION_ID_MAP,
)
import lhm_models
import aliyun_cli


def _out(obj):
    """JSON 输出到 stdout。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _log(*args):
    print(*args, file=sys.stderr)


# ============================================================================
# Profile 定义
# ============================================================================

PROFILES = {
    'data-validation': {
        'required_checks': [
            'cli_environment',
            'api_credentials',
            'api_connectivity',
            'resource_group',
            'agent',
            'data_sources',
            'engine_binding',
        ],
        'optional_checks': [],
    },
    'sql-convert': {
        'required_checks': ['cli_environment', 'api_credentials', 'api_connectivity'],
        'optional_checks': ['resource_group'],
    },
    'schedule': {
        'required_checks': ['cli_environment', 'api_credentials', 'api_connectivity'],
        'optional_checks': ['resource_group', 'data_sources'],
    },
}


# ============================================================================
# config 子命令
# ============================================================================

def cmd_config_get(args):
    """读取某个配置字段（点分隔路径）。"""
    cfg = load_config()
    keys = args.key.split('.')
    val = cfg
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            val = None
            break
    _out({'key': args.key, 'value': val})


def cmd_config_set(args):
    """设置某个配置字段（点分隔路径）。"""
    cfg = load_config()
    keys = args.key.split('.')
    d = cfg
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    # 尝试智能类型转换
    raw = args.value
    if raw.lower() in ('true', 'yes'):
        raw = True
    elif raw.lower() in ('false', 'no'):
        raw = False
    else:
        try:
            raw = int(raw)
        except ValueError:
            pass
    d[keys[-1]] = raw
    save_config(cfg)
    _out({'ok': True, 'key': args.key, 'value': raw})


def cmd_config_list(args):
    """列出所有配置（AK 脱敏显示）。"""
    cfg = load_config()
    display = json.loads(json.dumps(cfg))  # deep copy

    # 脱敏 api.access_key_secret
    api = display.get('api', {})
    sk = api.get('access_key_secret', '')
    if sk and len(sk) > 4:
        api['access_key_secret'] = sk[:4] + '****'

    _out(display)


def cmd_config_show(args):
    """显示某个数据源详情。"""
    cfg = load_config()
    ds_list = cfg.get('data_sources', [])
    for ds in ds_list:
        if ds.get('alias') == args.alias:
            _out(ds)
            return
    _out({'error': f'未找到别名 {args.alias!r} 的数据源', 'available': [d.get('alias') for d in ds_list]})
    sys.exit(1)


def cmd_config_add_ds(args):
    """添加数据源。"""
    cfg = load_config()
    ds_list = cfg.setdefault('data_sources', [])

    # 检查别名冲突
    for ds in ds_list:
        if ds.get('alias') == args.alias:
            _out({'error': f'别名 {args.alias!r} 已存在，请先 remove-ds 或使用不同别名'})
            sys.exit(1)

    entry = {
        'alias': args.alias,
        'ds_id': args.ds_id,
        'ds_name': args.ds_name,
        'ds_type': args.ds_type,
    }
    # 校验引擎（可选）：MaxCompute/Hive 等类型不绑引擎会导致校验执行期失败
    if getattr(args, 'engine_id', None):
        entry['engine_id'] = args.engine_id
        entry['engine_name'] = args.engine_name or args.engine_id
        entry['engine_type'] = args.engine_type or args.ds_type
    ds_list.append(entry)
    save_config(cfg)
    _out({'ok': True, 'alias': args.alias, 'message': f'数据源 {args.alias} 已添加'})


def cmd_config_remove_ds(args):
    """删除数据源。"""
    cfg = load_config()
    ds_list = cfg.get('data_sources', [])
    new_list = [ds for ds in ds_list if ds.get('alias') != args.alias]
    if len(new_list) == len(ds_list):
        _out({'error': f'未找到别名 {args.alias!r} 的数据源'})
        sys.exit(1)
    cfg['data_sources'] = new_list
    save_config(cfg)
    _out({'ok': True, 'alias': args.alias, 'message': f'数据源 {args.alias} 已删除'})


# ============================================================================
# client 子命令
# ============================================================================

def cmd_client(args):
    """从 data_validation_config.yaml 构建客户端并验证连通性。Credentials resolved via default credential chain."""
    cfg = load_config()
    api_cfg = cfg.get('api', {})

    region = args.region or api_cfg.get('region')

    try:
        client = build_client(
            region=region,
        )
    except RuntimeError as e:
        _out({'ok': False, 'error': str(e)})
        sys.exit(1)

    # 验证连通性
    if not args.skip_verify:
        try:
            resp = client.get_data_check_task_list(
                lhm_models.GetDataCheckTaskListRequest(page_index=1, page_size=1)
            )
            check_resp(resp, 'GetDataCheckTaskList')
        except Exception as e:
            _out({
                'ok': False,
                'error': f'客户端构建成功但连通性验证失败: {e}',
                'region': region,
            })
            sys.exit(1)

    region_key = region.lower()
    region_id = REGION_ID_MAP.get(region_key, 'cn-hangzhou')

    _out({
        'ok': True,
        'region': region,
        'region_id': region_id,
        'verified': not args.skip_verify,
    })


# ============================================================================
# check 子命令
# ============================================================================

def _check_cli_environment(cfg) -> dict:
    """检查 aliyun CLI + aliyun-cli-lhm 插件是否就绪（网络层依赖）。"""
    if aliyun_cli.find_aliyun_binary() is None:
        return {
            'name': 'cli_environment',
            'status': 'fail',
            'message': '未检测到 aliyun CLI',
            'fix_guide': (
                '请先安装 aliyun CLI（版本 >= 3.3.8）：https://help.aliyun.com/cli/'
            ),
            'blocking': True,
        }

    plugin_manifest = os.path.expanduser(
        '~/.aliyun/plugins/aliyun-cli-lhm/manifest.json'
    )
    if not os.path.isfile(plugin_manifest):
        return {
            'name': 'cli_environment',
            'status': 'fail',
            'message': 'aliyun-cli-lhm 插件未安装',
            'fix_guide': (
                '请运行：aliyun plugin install --names lhm '
                '--source-base https://cli.aliyun-inc.com/registry_id/2/env/pre/plugins'
            ),
            'blocking': True,
        }

    return {
        'name': 'cli_environment',
        'status': 'pass',
        'message': 'aliyun CLI + aliyun-cli-lhm 插件已就绪',
    }


def _check_api_credentials(cfg) -> dict:
    """检查 API 凭证是否配置。"""
    api = cfg.get('api', {})
    ak = api.get('access_key_id', '')
    sk = api.get('access_key_secret', '')

    # fallback 到环境变量
    ak = ak or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID', '')
    sk = sk or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')

    if ak and sk:
        return {
            'name': 'api_credentials',
            'status': 'pass',
            'message': 'AK/SK 已配置',
        }
    return {
        'name': 'api_credentials',
        'status': 'fail',
        'message': '未配置 API 凭证',
        'fix_guide': (
            '请在 data_validation_config.yaml 的 api 段配置 access_key_id 和 access_key_secret，'
            '或设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET。'
            '运行 "python run.py setup" 可引导完成配置。'
        ),
        'blocking': True,
    }


def _check_api_connectivity(cfg) -> dict:
    """验证 LHM API 可达。"""
    api = cfg.get('api', {})
    ak = api.get('access_key_id') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    sk = api.get('access_key_secret') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    region = api.get('region')

    if not ak or not sk:
        return {
            'name': 'api_connectivity',
            'status': 'skip',
            'message': 'API 凭证未配置，跳过连通性检查',
        }

    try:
        client = build_client(region=region)
        resp = client.get_data_check_task_list(
            lhm_models.GetDataCheckTaskListRequest(page_index=1, page_size=1)
        )
        check_resp(resp, 'GetDataCheckTaskList')
        return {
            'name': 'api_connectivity',
            'status': 'pass',
            'message': f'LHM endpoint 可达 (region={client._region_id})',
        }
    except Exception as e:
        return {
            'name': 'api_connectivity',
            'status': 'fail',
            'message': f'LHM API 调用失败: {e}',
            'fix_guide': (
                '请检查：1) AK/SK 是否正确 2) RAM 权限是否包含 LHM '
                '3) 网络是否能访问阿里云 API。'
            ),
            'blocking': True,
        }


def _check_resource_group(cfg) -> dict:
    """检查资源组绑定状态。"""
    api = cfg.get('api', {})
    ak = api.get('access_key_id') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    sk = api.get('access_key_secret') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    region = api.get('region')

    if not ak or not sk:
        return {
            'name': 'resource_group',
            'status': 'skip',
            'message': 'API 凭证未配置，跳过资源组检查',
        }

    try:
        client = build_client(region=region)
        region_id = client._region_id
        result = check_resource_group_status(client, region_id)
    except Exception as e:
        return {
            'name': 'resource_group',
            'status': 'fail',
            'message': f'资源组状态查询异常: {e}',
            'fix_guide': '请确认 SDK 版本和 API 权限。',
            'blocking': True,
        }

    if not result['ok']:
        return {
            'name': 'resource_group',
            'status': 'fail',
            'message': f'资源组状态查询失败: {result.get("error", "未知错误")}',
            'fix_guide': '请确认 API 权限和网络连通性。',
            'blocking': True,
        }

    if not result['bound']:
        return {
            'name': 'resource_group',
            'status': 'fail',
            'message': '未绑定 DataWorks 资源组',
            'fix_guide': (
                '请在 LHM 控制台绑定资源组: '
                'https://apds.console.aliyun.com/lake-house/resource-agent\n'
                '操作：点击「绑定资源组」→ 选择已创建的 Serverless 资源组。\n'
                '详见 guides/resource-group-config.md'
            ),
            'blocking': True,
        }

    if result['is_healthy']:
        # 更新 data_validation_config.yaml 中的状态缓存
        rg = cfg.setdefault('resource_group', {})
        rg['lhm_binding_status'] = result['status']
        return {
            'name': 'resource_group',
            'status': 'pass',
            'message': 'DataWorks 资源组状态正常',
            'data': result['status'],
        }

    return {
        'name': 'resource_group',
        'status': 'fail',
        'message': f'资源组状态异常: {result["status"]}',
        'data': result['status'],
        'fix_guide': (
            f'当前状态: {result["status"]}。'
            '请进入 DataWorks 控制台检查资源组：'
            'https://dataworks.console.aliyun.com/resource/list\n'
            '常见状态：Creating/Updating/Starting=等待完成，'
            'CreateFailed/UpdateFailed=检查错误日志，'
            'Stop/Freezed=续费或解冻。'
        ),
        'blocking': True,
    }


def _check_agent(cfg) -> dict:
    """检查服务代理在线状态。"""
    api = cfg.get('api', {})
    ak = api.get('access_key_id') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    sk = api.get('access_key_secret') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    region = api.get('region')

    if not ak or not sk:
        return {
            'name': 'agent',
            'status': 'skip',
            'message': 'API 凭证未配置，跳过服务代理检查',
        }

    try:
        client = build_client(region=region)
        result = check_agent_status(client, agent_type=1)
    except Exception as e:
        return {
            'name': 'agent',
            'status': 'fail',
            'message': f'服务代理状态查询异常: {e}',
            'fix_guide': '请确认 SDK 版本和 API 权限。',
            'blocking': True,
        }

    if not result['ok']:
        return {
            'name': 'agent',
            'status': 'fail',
            'message': f'服务代理状态查询失败: {result.get("error", "未知错误")}',
            'fix_guide': '请确认 API 权限和网络连通性。',
            'blocking': True,
        }

    if not result['configured']:
        return {
            'name': 'agent',
            'status': 'fail',
            'message': '未配置服务代理',
            'fix_guide': (
                '请在 LHM 控制台安装服务代理: '
                'https://apds.console.aliyun.com/lake-house/resource-agent\n'
                '操作：申请 License → 服务代理安装 → 选择 ECS 实例。\n'
                '详见 guides/agent-config.md'
            ),
            'blocking': True,
        }

    if result['is_online']:
        # 更新 data_validation_config.yaml 中的状态缓存
        ag = cfg.setdefault('agent', {})
        ag['agent_status'] = result['status']
        return {
            'name': 'agent',
            'status': 'pass',
            'message': '服务代理在线',
            'data': result['status'],
        }

    agent_name = cfg.get('agent', {}).get('agent_name', '')
    return {
        'name': 'agent',
        'status': 'fail',
        'message': f'服务代理状态为 {result["status"]}',
        'data': result['status'],
        'fix_guide': (
            f'当前状态: {result["status"]}。'
            f'请检查 ECS 上的 Agent 进程'
            f'{"（" + agent_name + "）" if agent_name else ""}：\n'
            f'  客户端路径: /home/agent/meta/{{代理名称}}/\n'
            f'  启动日志: start.log\n'
            f'  查询日志: /var/log/agent/meta/{{代理名称}}/application*.log\n'
            f'详见: https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/service-agent-management'
        ),
        'blocking': True,
    }


def _check_data_sources(cfg) -> dict:
    """检查数据源配置（pending_api 阶段：仅验证配置文件）。"""
    ds_list = cfg.get('data_sources', [])
    if not ds_list:
        return {
            'name': 'data_sources',
            'status': 'pending_api',
            'message': '配置文件中未定义数据源',
            'fix_guide': (
                '请在 LHM 控制台添加数据源：'
                'https://apds.console.aliyun.com/lake-house/datasource-manage\n'
                '然后运行 config add-ds 添加到配置文件。'
            ),
            'config_count': 0,
            'aliases': [],
        }

    aliases = [ds.get('alias', '?') for ds in ds_list]
    return {
        'name': 'data_sources',
        'status': 'pending_api',
        'message': '数据源检查 API 待接入，当前仅验证配置文件中有数据源定义',
        'config_count': len(ds_list),
        'aliases': aliases,
    }


def _check_engine_binding(cfg) -> dict:
    """
    检查需要校验引擎的数据源能否确定引擎。

    API 创建的任务不带引擎，MaxCompute/Hive 等类型缺引擎会在执行期报
    [RuntimeException]No default project specified.，这里提前拦住。
    """
    ds_list = cfg.get('data_sources', [])
    if not ds_list:
        return {
            'name': 'engine_binding',
            'status': 'skip',
            'message': '配置文件中未定义数据源，跳过引擎检查',
        }

    api = cfg.get('api', {})
    ak = api.get('access_key_id') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    sk = api.get('access_key_secret') or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    region = api.get('region')
    if not ak or not sk:
        return {
            'name': 'engine_binding',
            'status': 'skip',
            'message': 'API 凭证未配置，跳过引擎检查',
        }

    try:
        client = build_client(region=region)
    except Exception as e:
        return {
            'name': 'engine_binding',
            'status': 'skip',
            'message': f'客户端构建失败，跳过引擎检查: {e}',
        }

    details = []
    blocking = False
    for ds in ds_list:
        ds_type = str(ds.get('ds_type') or '')
        if ds_type.lower() not in ENGINE_REQUIRED_DS_TYPES:
            continue
        item = {'alias': ds.get('alias'), 'ds_type': ds_type}
        if ds.get('engine_id'):
            item.update(status='configured', engine_id=str(ds.get('engine_id')))
            details.append(item)
            continue
        remembered = recall_engine_choice(ds.get('ds_id'))
        if remembered:
            item.update(status='remembered', engine_id=remembered[0])
            details.append(item)
            continue
        try:
            candidates = list_engine_datasources(client, ds_type)
        except Exception as e:
            item.update(status='unknown', message=str(e))
            details.append(item)
            continue
        if len(candidates) == 1:
            item.update(status='auto', engine_id=candidates[0][0],
                        engine_name=candidates[0][1])
        else:
            blocking = True
            item.update(
                status='ambiguous' if candidates else 'missing',
                candidates=[
                    {'id': c[0], 'name': c[1], 'type': c[2]} for c in candidates
                ],
            )
        details.append(item)

    if not details:
        return {
            'name': 'engine_binding',
            'status': 'pass',
            'message': '没有需要绑定校验引擎的数据源',
        }
    if blocking:
        return {
            'name': 'engine_binding',
            'status': 'fail',
            'message': '存在无法自动确定校验引擎的数据源（缺引擎会导致执行期失败）',
            'details': details,
            'fix_guide': (
                'status=missing：请先在 LHM 控制台注册对应类型的计算引擎；\n'
                'status=ambiguous：候选多于一个，请把选定的引擎写入配置：\n'
                '  python run.py config add-ds --alias <别名> --ds-id <id> '
                '--ds-name <名称> --ds-type <类型> '
                '--engine-id <引擎id> --engine-name <引擎名> --engine-type <引擎类型>\n'
                '也可以在调用校验时用 --src-engine-id/--dst-engine-id 显式指定一次，'
                '之后会自动记忆。'
            ),
            'blocking': True,
        }
    return {
        'name': 'engine_binding',
        'status': 'pass',
        'message': f'{len(details)} 个数据源的校验引擎可确定',
        'details': details,
    }


CHECK_HANDLERS = {
    'cli_environment': _check_cli_environment,
    'api_credentials': _check_api_credentials,
    'api_connectivity': _check_api_connectivity,
    'resource_group': _check_resource_group,
    'agent': _check_agent,
    'data_sources': _check_data_sources,
    'engine_binding': _check_engine_binding,
}


def cmd_check(args):
    """前置条件检查。"""
    cfg = load_config()
    profile_name = args.profile or 'data-validation'

    if profile_name not in PROFILES:
        _out({
            'ok': False,
            'error': f'未知 profile: {profile_name!r}',
            'available': list(PROFILES.keys()),
        })
        sys.exit(1)

    profile = PROFILES[profile_name]
    checks_to_run = profile['required_checks'] + profile['optional_checks']

    if args.all:
        checks_to_run = list(CHECK_HANDLERS.keys())

    results = []
    for check_name in checks_to_run:
        handler = CHECK_HANDLERS.get(check_name)
        if handler:
            result = handler(cfg)
            is_optional = check_name in profile.get('optional_checks', [])
            if is_optional:
                result['optional'] = True
            results.append(result)

    # 保存状态缓存（check 过程中可能更新了 resource_group/agent 状态）
    save_config(cfg)

    # 汇总
    passed = sum(1 for r in results if r['status'] == 'pass')
    failed = sum(1 for r in results if r['status'] == 'fail' and not r.get('optional'))
    blocking_items = [r['name'] for r in results if r['status'] == 'fail' and r.get('blocking') and not r.get('optional')]
    ready = failed == 0 and len(blocking_items) == 0

    total = len(results)
    summary_parts = [f'{passed}/{total} 项通过']
    if failed:
        summary_parts.append(f'{failed} 项未通过（红线项）')
    pending = sum(1 for r in results if r['status'] == 'pending_api')
    if pending:
        summary_parts.append(f'{pending} 项待接入 API')
    skipped = sum(1 for r in results if r['status'] == 'skip')
    if skipped:
        summary_parts.append(f'{skipped} 项跳过')

    _out({
        'ok': ready,
        'profile': profile_name,
        'checks': results,
        'ready': ready,
        'summary': '，'.join(summary_parts),
        'blocking_items': blocking_items,
    })


# ============================================================================
# setup 子命令
# ============================================================================

SETUP_STEPS = [
    {'id': 'api', 'name': 'API 凭证', 'order': 1},
    {'id': 'resource_group', 'name': 'DataWorks 资源组', 'order': 2},
    {'id': 'bind_rg', 'name': '绑定资源组到 LHM', 'order': 3},
    {'id': 'agent', 'name': '服务代理', 'order': 4},
    {'id': 'data_sources', 'name': '数据源', 'order': 5},
    {'id': 'verify', 'name': '验证', 'order': 6},
]

STEP_GUIDES = {
    'api': {
        'description': '配置阿里云 AccessKey 和 Region',
        'guide': 'guides/setup-overview.md#step-1-api-凭证',
        'config_keys': ['api.access_key_id', 'api.access_key_secret', 'api.region'],
        'prompt_fields': [
            {'key': 'api.access_key_id', 'prompt': 'AccessKey ID', 'required': True},
            {'key': 'api.access_key_secret', 'prompt': 'AccessKey Secret', 'required': True},
            {'key': 'api.region', 'prompt': 'Region (hangzhou/singapore)', 'required': False, 'default': 'hangzhou'},
        ],
    },
    'resource_group': {
        'description': '配置 DataWorks Serverless 资源组',
        'guide': 'guides/resource-group-config.md',
        'config_keys': ['resource_group.dataworks_rg_id', 'resource_group.dataworks_rg_name'],
        'prompt_fields': [
            {'key': 'resource_group.dataworks_rg_id', 'prompt': '资源组 ID', 'required': True},
            {'key': 'resource_group.dataworks_rg_name', 'prompt': '资源组名称', 'required': False, 'default': ''},
        ],
    },
    'bind_rg': {
        'description': '在 LHM 控制台绑定资源组',
        'guide': 'guides/setup-overview.md#step-3-绑定资源组到-lhm',
        'console_url': 'https://apds.console.aliyun.com/lake-house/resource-agent',
        'config_keys': [],
        'prompt_fields': [],
    },
    'agent': {
        'description': '配置服务代理（ECS Agent）',
        'guide': 'guides/agent-config.md',
        'console_url': 'https://apds.console.aliyun.com/lake-house/resource-agent',
        'config_keys': ['agent.agent_name', 'agent.ecs_instance_id', 'agent.ecs_region'],
        'prompt_fields': [
            {'key': 'agent.agent_name', 'prompt': 'Agent 名称', 'required': True},
            {'key': 'agent.ecs_instance_id', 'prompt': 'ECS 实例 ID', 'required': False, 'default': ''},
            {'key': 'agent.ecs_region', 'prompt': 'ECS 所在地域', 'required': False, 'default': ''},
        ],
    },
    'data_sources': {
        'description': '配置数据源',
        'guide': 'guides/data-source-config.md',
        'console_url': 'https://apds.console.aliyun.com/lake-house/datasource-manage',
        'config_keys': ['data_sources'],
        'prompt_fields': [],
    },
    'verify': {
        'description': '运行前置检查验证配置',
        'config_keys': [],
        'prompt_fields': [],
    },
}


def cmd_setup(args):
    """引导式配置。"""
    step_filter = args.step

    if step_filter:
        # 按名称或序号筛选
        target = None
        for s in SETUP_STEPS:
            if s['id'] == step_filter or str(s['order']) == step_filter:
                target = s
                break
        if not target:
            _out({
                'ok': False,
                'error': f'未知步骤: {step_filter!r}',
                'available': [{'id': s['id'], 'name': s['name'], 'order': s['order']} for s in SETUP_STEPS],
            })
            sys.exit(1)
        steps = [target]
    else:
        steps = SETUP_STEPS

    result_steps = []
    for step in steps:
        step_id = step['id']
        guide = STEP_GUIDES.get(step_id, {})

        if step_id == 'verify':
            # 验证步骤：运行 check
            _log(f'[Step {step["order"]}] {step["name"]}: 运行前置检查...')
            # 构造 check 结果
            cfg = load_config()
            checks = []
            for check_name in PROFILES['data-validation']['required_checks']:
                handler = CHECK_HANDLERS.get(check_name)
                if handler:
                    checks.append(handler(cfg))
            save_config(cfg)

            passed = sum(1 for c in checks if c['status'] == 'pass')
            total = len(checks)
            result_steps.append({
                'step': step_id,
                'order': step['order'],
                'name': step['name'],
                'status': 'done',
                'check_summary': f'{passed}/{total} 项通过',
                'checks': checks,
            })
            continue

        step_info = {
            'step': step_id,
            'order': step['order'],
            'name': step['name'],
            'description': guide.get('description', ''),
        }

        if 'console_url' in guide:
            step_info['console_url'] = guide['console_url']
        if 'guide' in guide:
            step_info['guide'] = guide['guide']

        # 如果有 prompt_fields，输出提示结构（AI 会据此向用户提问）
        prompt_fields = guide.get('prompt_fields', [])
        if prompt_fields:
            cfg = load_config()
            # 读取当前值
            for field in prompt_fields:
                keys = field['key'].split('.')
                val = cfg
                for k in keys:
                    val = val.get(k, '') if isinstance(val, dict) else ''
                field['current'] = val or field.get('default', '')

            step_info['prompt_fields'] = prompt_fields
            step_info['status'] = 'awaiting_input'
        elif not prompt_fields and step_id != 'verify':
            step_info['status'] = 'manual_step'
            step_info['message'] = f'请在控制台完成操作后，告知我继续下一步'

        result_steps.append(step_info)

    _out({
        'ok': True,
        'config_path': CONFIG_PATH,
        'steps': result_steps,
        'message': '按步骤引导用户完成配置。每个 prompt_fields 中的字段需要向用户询问并写入 data_validation_config.yaml。',
    })


def cmd_setup_write(args):
    """setup 步骤中写入用户提供的配置值。"""
    cfg = load_config()
    updates = json.loads(args.values_json)

    for key, value in updates.items():
        keys = key.split('.')
        d = cfg
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value

    save_config(cfg)
    _out({'ok': True, 'updated_keys': list(updates.keys()), 'config_path': CONFIG_PATH})


# ============================================================================
# argparse
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='lhm-common CLI: LHM 技能共享基座',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest='command')

    # config
    p_config = sub.add_parser('config', help='配置管理')
    p_config_sub = p_config.add_subparsers(dest='config_cmd')

    p_config_get = p_config_sub.add_parser('get', help='读取配置字段')
    p_config_get.add_argument('key', help='点分隔路径，如 api.region')

    p_config_set = p_config_sub.add_parser('set', help='设置配置字段')
    p_config_set.add_argument('key', help='点分隔路径')
    p_config_set.add_argument('value', help='值')

    p_config_sub.add_parser('list', help='列出所有配置（脱敏）')

    p_config_show = p_config_sub.add_parser('show', help='显示数据源详情')
    p_config_show.add_argument('--alias', required=True, help='数据源别名')

    p_add_ds = p_config_sub.add_parser('add-ds', help='添加数据源')
    p_add_ds.add_argument('--alias', required=True, help='别名（好记的名字）')
    p_add_ds.add_argument('--ds-id', required=True, help='LHM 数据源 ID')
    p_add_ds.add_argument('--ds-name', required=True, help='显示名称')
    p_add_ds.add_argument('--ds-type', required=True, help='数据源类型（MaxCompute/Hive/StarRocks 等）')
    p_add_ds.add_argument('--engine-id', default=None, help='校验引擎 ID（MaxCompute/Hive 等建议配置）')
    p_add_ds.add_argument('--engine-name', default=None, help='校验引擎名称（默认同 engine-id）')
    p_add_ds.add_argument('--engine-type', default=None, help='校验引擎类型（默认同 ds-type）')

    p_rm_ds = p_config_sub.add_parser('remove-ds', help='删除数据源')
    p_rm_ds.add_argument('--alias', required=True, help='数据源别名')

    # client
    p_client = sub.add_parser('client', help='构建并验证 LHM 客户端（aliyun CLI）')
    p_client.add_argument('--region', help='覆盖 region')
    p_client.add_argument('--skip-verify', action='store_true', help='跳过连通性验证')

    # check
    p_check = sub.add_parser('check', help='前置条件检查')
    p_check.add_argument('--profile', default='data-validation', help='检查 profile 名称')
    p_check.add_argument('--all', action='store_true', help='检查所有项（忽略 profile 限制）')

    # setup
    p_setup = sub.add_parser('setup', help='引导式配置')
    p_setup.add_argument('--step', help='指定步骤（名称或序号）')

    # setup-write (内部使用，AI 调用写入配置)
    p_sw = sub.add_parser('setup-write', help='写入 setup 步骤的配置值')
    p_sw.add_argument('values_json', help='JSON 格式的 key-value 对')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 路由
    if args.command == 'config':
        if not args.config_cmd:
            p_config.print_help()
            sys.exit(1)
        {
            'get': cmd_config_get,
            'set': cmd_config_set,
            'list': cmd_config_list,
            'show': cmd_config_show,
            'add-ds': cmd_config_add_ds,
            'remove-ds': cmd_config_remove_ds,
        }[args.config_cmd](args)

    elif args.command == 'client':
        cmd_client(args)

    elif args.command == 'check':
        cmd_check(args)

    elif args.command == 'setup':
        cmd_setup(args)

    elif args.command == 'setup-write':
        cmd_setup_write(args)


if __name__ == '__main__':
    main()
