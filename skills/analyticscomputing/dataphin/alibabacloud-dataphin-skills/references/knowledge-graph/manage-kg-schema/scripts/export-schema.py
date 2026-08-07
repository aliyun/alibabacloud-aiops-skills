#!/usr/bin/env python3
"""
知识图谱 Schema 只读导出工具 — Python SDK 泛化调用（仅旧环境兜底）

【仅作旧环境兜底】KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），
新环境优先使用 CLI 原生命令 export-kg-schema（见 SKILL.md）。
本脚本仅用于独立部署 < v6.1.1 未发布 KG OpenAPI 的旧环境。

调用 ExportKgSchema 导出当前空间的 Schema YAML（草稿态），**只读、不写远端**。
用于：删除/修改类型前的侦察与取基线、编辑前保存本地基线、变更后复验。

用法:
  python3 export-schema.py [选项]

选项:
  --output FILE   将导出的 Schema YAML 写入本地文件（不指定则仅打印到 stdout）
  --quiet         仅输出 YAML 内容本身（便于管道/重定向），不打印元信息
  --ignore-ssl    跳过 SSL 证书验证（独立部署环境常用）
  --help          显示此帮助信息

环境变量（必须）:
  ALIBABA_CLOUD_ACCESS_KEY_ID       RAM AccessKey ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET   RAM AccessKey Secret
  DATAPHIN_ENDPOINT                 OpenAPI 端点（如 dataphin-openapi.cn-hangzhou.aliyuncs.com）
  DATAPHIN_TENANT_ID                租户 ID（OpTenantId）
  DATAPHIN_WORKSPACE_ID             知识图谱空间 ID（WorkspaceId）
"""

import json
import sys
import os

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
    if '--help' in args or '-h' in args:
        print(__doc__.strip())
        sys.exit(0)

    output = None
    quiet = False
    ignore_ssl = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == '--output' and i + 1 < len(args):
            i += 1
            output = args[i]
        elif a == '--quiet':
            quiet = True
        elif a == '--ignore-ssl':
            ignore_ssl = True
        else:
            print(f"未知参数: {a}")
            print("运行 python3 export-schema.py --help 查看帮助")
            sys.exit(1)
        i += 1

    return output, quiet, ignore_ssl


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


# ══════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════
def main():
    output, quiet, ignore_ssl = parse_args()

    tenant_id = require_env('DATAPHIN_TENANT_ID', 'OpTenantId')
    workspace_id = require_env('DATAPHIN_WORKSPACE_ID', 'WorkspaceId')

    client, runtime = create_client(ignore_ssl)

    if not quiet:
        print(f"  Endpoint: {client._endpoint}")
        print(f"  TenantId: {tenant_id}")
        print(f"  WorkspaceId: {workspace_id}")
        print()

    try:
        result = call_api(client, runtime, tenant_id, 'ExportKgSchema', workspace_id, body={})
    except Exception as e:
        print(f"错误: ExportKgSchema 异常: {e}")
        sys.exit(1)

    resp = result.get('body', {})
    if not resp.get('Success'):
        print(f"错误: 导出失败: {resp.get('Code')} - {resp.get('Message')}")
        sys.exit(1)

    # 实测响应结构（v6.1.1）：YAML 在 SchemaInfo.Content，做 Data.SchemaContent 兼容兜底
    content = resp.get('SchemaInfo', {}).get('Content') or resp.get('Data', {}).get('SchemaContent', '')

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        if not quiet:
            print(f"  已导出 Schema YAML ({len(content)} 字符) -> {output}")
    elif quiet:
        # 仅打印 YAML，便于 > file 或管道
        sys.stdout.write(content)
    else:
        print(f"  当前 Schema YAML ({len(content)} 字符):")
        print(f"---\n{content}---")


if __name__ == '__main__':
    main()
