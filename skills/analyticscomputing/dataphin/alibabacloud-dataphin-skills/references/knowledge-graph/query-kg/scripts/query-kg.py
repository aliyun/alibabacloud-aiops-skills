#!/usr/bin/env python3
"""query-kg.py — 知识图谱只读查询兜底脚本（ExecKgCypher / GetKgNeighbor）。

【仅作旧环境兜底】KG OpenAPI 已正式发布（v6.1.1）并注册到 CLI 插件（>= 0.7.1），
优先使用 CLI 原生命令 exec-kg-cypher / get-kg-neighbor（见 SKILL.md §8）。
本脚本仅用于独立部署 < v6.1.1 未发布 KG OpenAPI 的旧环境，
通过 Python Tea SDK call_api() 泛化调用。纯查询，无任何写操作。

凭证与环境（环境变量，均不打印）：
  ALIBABA_CLOUD_ACCESS_KEY_ID      RAM AccessKey ID
  ALIBABA_CLOUD_ACCESS_KEY_SECRET  RAM AccessKey Secret
  DATAPHIN_ENDPOINT                管理面 endpoint（如 dataphin-openapi.<env>.aliyun.com）
  DATAPHIN_TENANT_ID               OpTenantId
  DATAPHIN_WORKSPACE_ID            WorkspaceId（KG 空间 ID）

用法：
  # Cypher 查询（只读）
  python3 query-kg.py cypher --query "MATCH (n) RETURN count(n) AS cnt" [--limit 100] [--ignore-ssl]
  # 邻居遍历
  python3 query-kg.py neighbor --entity-data-id <DataId> --entity-type <Type> \\
      [--direction Both] [--depth 1] [--relation-types A,B] [--ignore-ssl]

选项：
  --ignore-ssl   独立部署自签证书时忽略 SSL 校验
  --quiet        仅输出结果 JSON（无提示信息，便于管道处理）
"""
import argparse
import json
import os
import sys

try:
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_openapi.client import Client
    from alibabacloud_tea_util import models as util_models
except ImportError:
    sys.stderr.write(
        "缺少依赖，请先安装：\n"
        "  pip3 install alibabacloud_tea_openapi alibabacloud_tea_util\n"
    )
    sys.exit(2)

API_VERSION = '2023-06-30'


def _log(msg, quiet):
    if not quiet:
        sys.stderr.write(msg + "\n")


def _build_client(ignore_ssl):
    ak_id = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
    ak_secret = os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    endpoint = os.environ.get('DATAPHIN_ENDPOINT')
    if not (ak_id and ak_secret and endpoint):
        sys.stderr.write(
            "缺少必要环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID / "
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET / DATAPHIN_ENDPOINT\n"
        )
        sys.exit(2)
    # UA 可观测（Principle 9）：SKILL_SESSION_ID 由 Agent 执行时内联注入，缺失时降级为仅 skill 名
    session_id = os.environ.get('SKILL_SESSION_ID', '')
    ua = 'AlibabaCloud-Agent-Skills/query-kg'
    if session_id:
        ua = f'{ua}/{session_id}'
    config = open_api_models.Config(
        access_key_id=ak_id, access_key_secret=ak_secret, endpoint=endpoint,
        user_agent=ua,
    )
    client = Client(config)
    runtime = util_models.RuntimeOptions()
    if ignore_ssl:
        runtime.ignore_ssl = True
    return client, runtime


def _params(action):
    # KG API 均为 RPC + POST + formData（实测校准）
    return open_api_models.Params(
        action=action, version=API_VERSION, protocol='HTTPS', method='POST',
        auth_type='AK', style='RPC', pathname='/', req_body_type='formData',
        body_type='json',
    )


def _tenant_workspace():
    tenant = os.environ.get('DATAPHIN_TENANT_ID')
    workspace = os.environ.get('DATAPHIN_WORKSPACE_ID')
    if not (tenant and workspace):
        sys.stderr.write(
            "缺少必要环境变量：DATAPHIN_TENANT_ID / DATAPHIN_WORKSPACE_ID\n"
        )
        sys.exit(2)
    return tenant, workspace


def run_cypher(args):
    client, runtime = _build_client(args.ignore_ssl)
    tenant, workspace = _tenant_workspace()
    cypher_body = {'Query': args.query}
    if args.limit is not None:
        cypher_body['Limit'] = args.limit
    _log(f"[cypher] {args.query}", args.quiet)
    request = open_api_models.OpenApiRequest(
        query={'OpTenantId': tenant, 'WorkspaceId': workspace},
        # ★ 请求体参数名是 ExecCommand（非文档中的 ExecKgCypherCommand）
        body={'ExecCommand': json.dumps(cypher_body, ensure_ascii=False)},
    )
    resp = client.call_api(_params('ExecKgCypher'), request, runtime)
    return resp.get('body', resp)


def run_neighbor(args):
    client, runtime = _build_client(args.ignore_ssl)
    tenant, workspace = _tenant_workspace()
    # ★ 参数名 EntityDataId（非 EntityId）；EntityType 必填；POST 方法
    q = {
        'OpTenantId': tenant, 'WorkspaceId': workspace,
        'EntityDataId': args.entity_data_id, 'EntityType': args.entity_type,
        'Direction': args.direction, 'Depth': str(args.depth),
    }
    if args.relation_types:
        q['RelationTypes'] = args.relation_types
    _log(f"[neighbor] {args.entity_type}/{args.entity_data_id} "
         f"dir={args.direction} depth={args.depth}", args.quiet)
    request = open_api_models.OpenApiRequest(query=q)
    resp = client.call_api(_params('GetKgNeighbor'), request, runtime)
    return resp.get('body', resp)


def main():
    parser = argparse.ArgumentParser(description='知识图谱只读查询（ExecKgCypher / GetKgNeighbor）')
    # 公共参数（放到子命令上，允许写在子命令之后：如 `query-kg.py cypher --query .. --ignore-ssl`）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--ignore-ssl', action='store_true', help='忽略 SSL 校验（独立部署自签证书）')
    common.add_argument('--quiet', action='store_true', help='仅输出结果 JSON')
    sub = parser.add_subparsers(dest='command', required=True)

    p_cypher = sub.add_parser('cypher', parents=[common], help='执行 Cypher 查询（只读）')
    p_cypher.add_argument('--query', required=True, help='Cypher 查询语句（仅支持只读）')
    p_cypher.add_argument('--limit', type=int, default=None, help='返回条数上限（默认服务端 100）')
    p_cypher.set_defaults(func=run_cypher)

    p_nb = sub.add_parser('neighbor', parents=[common], help='邻居节点遍历')
    p_nb.add_argument('--entity-data-id', required=True, help='起始实体 DataId（来自 cypher 的 NodeList[].DataId）')
    p_nb.add_argument('--entity-type', required=True, help='起始实体类型（必填）')
    p_nb.add_argument('--direction', default='Both', choices=['In', 'Out', 'Both'], help='遍历方向')
    p_nb.add_argument('--depth', type=int, default=1, help='扩展深度（默认 1）')
    p_nb.add_argument('--relation-types', default=None, help='关系类型编码，逗号分隔（仅遍历指定类型）')
    p_nb.set_defaults(func=run_neighbor)

    args = parser.parse_args()
    body = args.func(args)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    # 业务失败（Success=false / Code!=OK）返回非零退出码
    if isinstance(body, dict) and (body.get('Success') is False or (body.get('Code') not in (None, 'OK'))):
        sys.exit(1)


if __name__ == '__main__':
    main()
