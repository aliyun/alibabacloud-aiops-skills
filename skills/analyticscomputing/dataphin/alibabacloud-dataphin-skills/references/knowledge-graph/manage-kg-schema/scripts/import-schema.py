#!/usr/bin/env python3
"""
知识图谱 Schema 导入与发布工具 — Python SDK 泛化调用（仅旧环境兜底）

【仅作旧环境兜底】KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），
新环境优先使用 CLI 原生命令 import-kg-schema / publish-kg-schema（见 SKILL.md）。
本脚本仅用于独立部署 < v6.1.1 未发布 KG OpenAPI 的旧环境。

完成 Schema 导入的端到端流程：本地预校验 → 导出基线 → 导入 → 验证 → 发布 → 轮询结果。

用法:
  python3 import-schema.py <yaml_file> [选项]

选项:
  --skip-export       跳过导入前的 Schema 导出
  --skip-publish      导入后不自动发布
  --ignore-ssl        跳过 SSL 证书验证（独立部署环境常用）
  --merge-strategy S  合并策略：Replace（替换，默认）或 Merge（合并）
  --help              显示此帮助信息

环境变量（必须）:
  ALIBABA_CLOUD_ACCESS_KEY_ID       RAM AccessKey ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET   RAM AccessKey Secret
  DATAPHIN_ENDPOINT                 OpenAPI 端点（如 dataphin-openapi.cn-hangzhou.aliyuncs.com）
  DATAPHIN_TENANT_ID                租户 ID（OpTenantId）
  DATAPHIN_WORKSPACE_ID             知识图谱空间 ID（WorkspaceId）
"""

import json
import time
import sys
import os

try:
    import yaml
except ImportError:
    print("错误: 需要安装 PyYAML\n  pip3 install pyyaml")
    sys.exit(1)

try:
    from alibabacloud_tea_openapi.client import Client
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models
except ImportError:
    print("错误: 需要安装 Tea SDK\n  pip3 install alibabacloud-tea-openapi alibabacloud-tea-util")
    sys.exit(1)


# ══════════════════════════════════════════
# 参数解析
# ══════════════════════════════════════════
def parse_args():
    """解析命令行参数"""
    args = sys.argv[1:]
    if not args or '--help' in args or '-h' in args:
        print(__doc__.strip())
        sys.exit(0)

    yaml_path = None
    skip_export = False
    skip_publish = False
    ignore_ssl = False
    merge_strategy = 'Replace'

    i = 0
    while i < len(args):
        a = args[i]
        if a == '--skip-export':
            skip_export = True
        elif a == '--skip-publish':
            skip_publish = True
        elif a == '--ignore-ssl':
            ignore_ssl = True
        elif a == '--merge-strategy' and i + 1 < len(args):
            i += 1
            merge_strategy = args[i]
            if merge_strategy not in ('Replace', 'Merge'):
                print(f"错误: --merge-strategy 仅支持 Replace 或 Merge，当前值: {merge_strategy}")
                sys.exit(1)
        elif not a.startswith('--') and (a.endswith('.yaml') or a.endswith('.yml')):
            yaml_path = a
        else:
            print(f"未知参数: {a}")
            print("运行 python3 import-schema.py --help 查看帮助")
            sys.exit(1)
        i += 1

    if not yaml_path:
        print("错误: 请指定 Schema YAML 文件路径")
        print("用法: python3 import-schema.py <yaml_file> [选项]")
        sys.exit(1)

    return yaml_path, skip_export, skip_publish, ignore_ssl, merge_strategy


def require_env(name, hint=''):
    """获取必须的环境变量，缺失时给出明确提示"""
    val = os.environ.get(name, '')
    if not val:
        msg = f"错误: 环境变量 {name} 未设置"
        if hint:
            msg += f"（{hint}）"
        print(msg)
        sys.exit(1)
    return val


# ══════════════════════════════════════════
# 客户端初始化
# ══════════════════════════════════════════
def create_client(ignore_ssl):
    """根据环境变量创建 Tea SDK 客户端"""
    ak_id = require_env('ALIBABA_CLOUD_ACCESS_KEY_ID', 'RAM AccessKey ID')
    ak_secret = require_env('ALIBABA_CLOUD_ACCESS_KEY_SECRET', 'RAM AccessKey Secret')
    endpoint = require_env('DATAPHIN_ENDPOINT', '如 dataphin-openapi.cn-hangzhou.aliyuncs.com')

    # UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入，缺失时降级为仅 skill 名
    session_id = os.environ.get('SKILL_SESSION_ID', '')
    ua = 'AlibabaCloud-Agent-Skills/manage-kg-schema'
    if session_id:
        ua = f'{ua}/{session_id}'

    config = open_api_models.Config(
        access_key_id=ak_id,
        access_key_secret=ak_secret,
        endpoint=endpoint,
        user_agent=ua,
    )
    client = Client(config)
    runtime = util_models.RuntimeOptions()
    if ignore_ssl:
        runtime.ignore_ssl = True
    return client, runtime


def call_api(client, runtime, tenant_id, action, workspace_id,
             method='POST', body=None, extra_query=None):
    """泛化调用 Dataphin OpenAPI"""
    params = open_api_models.Params(
        action=action,
        version='2023-06-30',
        protocol='HTTPS',
        method=method,
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json',
    )
    query = {'OpTenantId': tenant_id, 'WorkspaceId': workspace_id}
    if extra_query:
        query.update(extra_query)
    request = open_api_models.OpenApiRequest(query=query, body=body)
    return client.call_api(params, request, runtime)


def pp(result):
    """Pretty print API 响应"""
    body = result.get('body', {})
    print(json.dumps(body, ensure_ascii=False, indent=2))
    return body


# ══════════════════════════════════════════
# 步骤函数
# ══════════════════════════════════════════
def step_local_validate(yaml_path):
    """Step 0: 本地预校验 YAML Schema"""
    print("=" * 60)
    print("Step 0: 本地预校验 YAML Schema")
    print("=" * 60)

    validator_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validate-schema.py')
    if not os.path.exists(validator_path):
        print(f"  校验脚本未找到，跳过: {validator_path}")
        return True

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("validate_schema", validator_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        validator = mod.SchemaValidator(data, yaml_path)
        if validator.validate():
            et_count = len(data.get('entityTypes') or [])
            rt_count = len(data.get('relationTypes') or [])
            print(f"  校验通过: {et_count} 个实体类型，{rt_count} 个关系类型")
            return True
        else:
            for w in validator.warnings:
                print(f"  {w}")
            for e in validator.errors:
                print(f"  {e}")
            print(f"\n  校验失败 ({len(validator.errors)} 个错误)，请修复后重试")
            return False
    except Exception as e:
        print(f"  本地校验异常（不阻塞导入）: {e}")
        return True  # 不阻塞


def step_export(client, runtime, tenant_id, workspace_id):
    """Step 1: 导出当前 Schema（基线）"""
    print("\n" + "=" * 60)
    print("Step 1: 导出当前 Schema (ExportKgSchema)")
    print("=" * 60)
    try:
        result = call_api(client, runtime, tenant_id, 'ExportKgSchema', workspace_id)
        resp = pp(result)
        if resp.get('Success'):
            content = resp.get('SchemaInfo', {}).get('Content', '')
            print(f"\n  当前 Schema YAML ({len(content)} 字符)")
            if content:
                print(f"---\n{content}---\n")
        else:
            print(f"  导出失败: {resp.get('Code')} - {resp.get('Message')}")
    except Exception as e:
        print(f"  ExportKgSchema 异常: {e}")


def step_import(client, runtime, tenant_id, workspace_id, yaml_path, merge_strategy):
    """Step 2: 导入 Schema"""
    print(f"\n  读取 Schema YAML: {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    print(f"  YAML 内容 ({len(yaml_content)} 字符):\n---\n{yaml_content}---\n")

    print("=" * 60)
    print(f"Step 2: 导入 Schema (ImportKgSchema, 策略: {merge_strategy})")
    print("=" * 60)

    import_cmd = json.dumps({
        'Format': 'yaml',
        'Content': yaml_content,
        'MergeStrategy': merge_strategy,
    })

    try:
        result = call_api(
            client, runtime, tenant_id, 'ImportKgSchema', workspace_id,
            body={'ImportCommand': import_cmd},
        )
        resp = pp(result)
        if resp.get('Success'):
            print("\n  Schema 导入成功!")
            return True
        else:
            print(f"\n  Schema 导入失败: {resp.get('Code', '')} - {resp.get('Message', '')}")
            return False
    except Exception as e:
        print(f"  ImportKgSchema 异常: {e}")
        return False


def step_verify(client, runtime, tenant_id, workspace_id):
    """Step 3: 导入后导出确认"""
    print("\n" + "=" * 60)
    print("Step 3: 导入后导出确认 (ExportKgSchema)")
    print("=" * 60)
    try:
        result = call_api(client, runtime, tenant_id, 'ExportKgSchema', workspace_id)
        resp = pp(result)
        if resp.get('Success'):
            content = resp.get('SchemaInfo', {}).get('Content', '')
            if content:
                print(f"\n  导入后 Schema YAML:\n---\n{content}---\n")
    except Exception as e:
        print(f"  ExportKgSchema 异常: {e}")


def step_publish(client, runtime, tenant_id, workspace_id, yaml_path):
    """Step 4: 发布 Schema + Step 5: 轮询结果"""
    print("=" * 60)
    print("Step 4: 发布 Schema (PublishKgSchema)")
    print("=" * 60)

    publish_cmd = json.dumps({
        'Description': f'Schema import from {os.path.basename(yaml_path)}',
        'DataAdjustmentPolicies': [],
    })

    try:
        result = call_api(
            client, runtime, tenant_id, 'PublishKgSchema', workspace_id,
            body={'PublishCommand': publish_cmd},
        )
        resp = pp(result)

        # 提取 TaskId（尝试多种响应路径）
        task_id = None
        for key_path in [
            ('Data', 'TaskId'),
            ('PublishKgSchemaResult', 'TaskId'),
            ('Result', 'TaskId'),
        ]:
            obj = resp
            for k in key_path:
                obj = obj.get(k, {}) if isinstance(obj, dict) else {}
            if obj and isinstance(obj, str):
                task_id = obj
                break

        if not task_id:
            print("  未获取到 TaskId，请检查响应")
            return

        print(f"\n  发布 TaskId: {task_id}")

        # 轮询发布结果
        print("\n" + "=" * 60)
        print("Step 5: 轮询发布结果")
        print("=" * 60)

        for i in range(12):
            time.sleep(5)
            try:
                r = call_api(
                    client, runtime, tenant_id,
                    'GetKgSchemaPublishResult', workspace_id,
                    extra_query={'TaskId': task_id},
                )
                r_resp = r.get('body', {})
                status = ''
                for key in ['Data', 'PublishResult', 'Result']:
                    r_data = r_resp.get(key, {})
                    if isinstance(r_data, dict):
                        status = r_data.get('Status', '')
                        if status:
                            break
                if not status:
                    status = r_resp.get('Status', '')

                print(f"  [{i+1}/12] 状态: {status}")
                if status in ('Published', 'Partial', 'Failed'):
                    pp(r)
                    break
            except Exception as e:
                print(f"  轮询异常: {e}")

    except Exception as e:
        print(f"  PublishKgSchema 异常: {e}")


# ══════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════
def main():
    yaml_path, skip_export, skip_publish, ignore_ssl, merge_strategy = parse_args()

    # 校验文件存在
    if not os.path.exists(yaml_path):
        print(f"错误: 文件不存在: {yaml_path}")
        sys.exit(1)

    # 环境变量
    tenant_id = require_env('DATAPHIN_TENANT_ID', 'OpTenantId')
    workspace_id = require_env('DATAPHIN_WORKSPACE_ID', 'WorkspaceId')

    client, runtime = create_client(ignore_ssl)

    print(f"  Endpoint: {client._endpoint}")
    print(f"  TenantId: {tenant_id}")
    print(f"  WorkspaceId: {workspace_id}")
    print(f"  YAML: {yaml_path}")
    print(f"  MergeStrategy: {merge_strategy}")
    print(f"  IgnoreSSL: {ignore_ssl}")
    print()

    # Step 0: 本地预校验
    if not step_local_validate(yaml_path):
        sys.exit(1)

    # Step 1: 导出基线
    if not skip_export:
        step_export(client, runtime, tenant_id, workspace_id)
    else:
        print("\nStep 1: 跳过导出（--skip-export）")

    # Step 2: 导入
    if not step_import(client, runtime, tenant_id, workspace_id, yaml_path, merge_strategy):
        sys.exit(1)

    # Step 3: 验证
    step_verify(client, runtime, tenant_id, workspace_id)

    # Step 4+5: 发布 + 轮询
    if not skip_publish:
        step_publish(client, runtime, tenant_id, workspace_id, yaml_path)
    else:
        print("\nStep 4: 跳过发布（--skip-publish）")

    print("\n" + "=" * 60)
    print("执行完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
