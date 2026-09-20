"""LHM CLI 客户端工厂和 API 封装。

职责：
- 封装部署相关 API：start_submit / list_submit_instances /
  get_result_package_url / list_writer_workflows

凭据由 aliyun CLI 默认凭证链在调用时解析（环境变量 / RAM Role /
~/.alibabacloud/credentials），本模块不解析、不校验任何凭证。

网络层使用 aliyun CLI（aliyun-cli-lhm 插件）替代 Python SDK。
"""

from __future__ import annotations

import os
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Tuple

# 网络层模块（与本文件同目录）
try:
    from lhm_deploy_cli import aliyun_cli
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import aliyun_cli

# Bind the names from the already-imported module object. A bare top-level
# `from aliyun_cli import ...` fails under the packaged install because the
# module resolves to lhm_deploy_cli.aliyun_cli and sys.path is not patched in
# the success branch above.
AliyunCliClient = aliyun_cli.AliyunCliClient  # noqa: F401
AliyunCliError = aliyun_cli.AliyunCliError  # noqa: F401

from lhm_deploy_cli import credentials as credential_file

DEFAULT_ENDPOINT = "lhm-pre.cn-hangzhou.aliyuncs.com"


_FALLBACK_SESSION_ID = ""


def build_user_agent() -> str:
    """Observability UA：AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{version}。

    session-id 优先取环境变量 LHM_SESSION_ID（dispatcher 会话开始时生成一次，
    全会话复用）；未设置时每进程兜底生成一次并缓存，保证 UA 始终存在且
    同进程内多次调用一致。
    """
    global _FALLBACK_SESSION_ID
    session_id = os.environ.get("LHM_SESSION_ID", "").strip()
    if not session_id:
        if not _FALLBACK_SESSION_ID:
            _FALLBACK_SESSION_ID = uuid.uuid4().hex
        session_id = _FALLBACK_SESSION_ID
    version = os.environ.get("LHM_SKILL_VERSION", "").strip() or "1.0.0"
    return f"AlibabaCloud-Agent-Skills/lhm-sch-deploy/{session_id} skill-version/{version}"


@lru_cache(maxsize=1)
def resolve_session_endpoint() -> Tuple[str, str]:
    """
    从会话配置读取 endpoint / region；无会话配置时返回空串。

    用于让会话配置的环境信息参与 cli.py 的优先级链，而不用在多处重复读文件。
    """
    session_config = credential_file.load_session_file()
    if session_config is None:
        return "", ""
    return (
        session_config.value("lhm", "endpoint"),
        session_config.value("lhm", "region_id"),
    )


@lru_cache(maxsize=1)
def resolve_session_task_id() -> str:
    """
    从会话配置读取阶段③ 回写的 `convert_task_id`（顶层扁平键，
    兼容旧版 `migration.convert_task_id` 嵌套写法）。

    lhm-sch-read-exec 在 convert-start 成功后会把 task_id 写入会话配置，
    使阶段④ 无需再从 readexec.json 推测或追问用户。

    Returns:
        task_id；无会话配置或未回写时返回空串。
    """
    session_config = credential_file.load_session_file()
    if session_config is None:
        return ""
    return session_config.value("migration", "convert_task_id")


def create_client(endpoint: str = None, region_id: str = None) -> AliyunCliClient:
    """
    创建 LHM CLI 客户端。

    Endpoint 优先级（与 lhm-sch-ds 对齐）：
      1. 参数显式传入
      2. 环境变量 LHM_ENDPOINT
      3. 默认 lhm-pre.cn-hangzhou.aliyuncs.com（预发环境）

    凭据通过 aliyun CLI 的默认凭证链自动解析，无需显式传递 AK/SK。

    Args:
        endpoint: LHM 服务端点（可选）
        region_id: 地域（可选，默认取 REGION_ID 环境变量或 cn-hangzhou）

    Returns:
        AliyunCliClient 实例

    Raises:
        RuntimeError: 凭据缺失（由 aliyun CLI 处理）
    """
    endpoint = endpoint or os.environ.get("LHM_ENDPOINT") or DEFAULT_ENDPOINT
    region_id = region_id or os.environ.get("REGION_ID") or "cn-hangzhou"

    return AliyunCliClient(
        endpoint=endpoint,
        region_id=region_id,
        skill_name="lhm-sch-deploy",
    )


def start_submit(client: AliyunCliClient, task_id: str) -> Dict[str, Any]:
    """
    触发部署提交。

    API: GetBwmMigrationWorkflowSubmitStart
    Request: { task_id: str }
    Response: { data: int, success: bool, err_code: str, err_message: str }

    Args:
        client: LHM CLI Client
        task_id: 迁移任务 ID

    Returns:
        响应体字典
    """
    request = {"taskId": task_id}
    response = client.get_bwm_migration_workflow_submit_start(request)
    body = response.body
    return {
        "data": body.data,
        "success": body.success,
        "err_code": body.err_code,
        "err_message": body.err_message,
        "request_id": body.request_id,
    }


def list_submit_instances(
    client: AliyunCliClient,
    task_id: str,
    page_index: int = 1,
    page_size: int = 10,
) -> Dict[str, Any]:
    """
    查询部署实例列表。

    API: GetBwmMigrationSubmitInstanceList
    Request: { task_id, page_index, page_size, status? }
    Response: 分页列表，每条记录包含 instance_id, instance_name, status, detail 等

    Args:
        client: LHM CLI Client
        task_id: 迁移任务 ID
        page_index: 页码（从 1 开始）
        page_size: 每页大小

    Returns:
        响应体字典
    """
    request = {
        "taskId": task_id,
        "pageIndex": page_index,
        "pageSize": page_size,
    }
    response = client.get_bwm_migration_submit_instance_list(request)
    body = response.body

    # 将 data 列表中的对象转为字典
    instances = []
    if body.data:
        for item in body.data:
            instances.append({
                "instance_id": item.instance_id,
                "instance_name": item.instance_name,
                "status": item.status,
                "detail": item.detail,
                "gmt_convert": item.gmt_convert,
                "src_meta_info": item.src_meta_info,
                "src_meta_gmt_update": item.src_meta_gmt_update,
            })

    return {
        "data": instances,
        "total_count": body.total_count,
        "total_pages": body.total_pages,
        "page_index": body.page_index,
        "page_size": body.page_size,
        "success": body.success,
        "err_code": body.err_code,
        "err_message": body.err_message,
    }


def get_result_package_url(
    client: AliyunCliClient,
    instance_id: str,
) -> Dict[str, Any]:
    """
    获取结果包下载 URL（预签名 OSS 链接）。

    API: GetBwmMigrationTaskWriterResultPackage
    Request: { instance_id: str }
    Response body: { data: str (预签名URL), success: bool, err_code, err_message }

    Args:
        client: LHM CLI Client
        instance_id: 部署实例 ID

    Returns:
        dict: { "success": bool, "url": str, "err_code": str, "err_message": str }
    """
    try:
        request = {"instanceId": instance_id}
        response = client.get_bwm_migration_task_writer_result_package(request)
        body = response.body

        if not body.success:
            return {
                "success": False,
                "url": None,
                "err_code": body.err_code,
                "err_message": body.err_message,
            }

        return {
            "success": True,
            "url": body.data,  # body.data 直接就是预签名 URL 字符串
            "err_code": None,
            "err_message": None,
        }
    except Exception as e:
        return {
            "success": False,
            "url": None,
            "err_code": "API_CALL_FAILED",
            "err_message": str(e),
        }


def list_writer_workflows(
    client: AliyunCliClient,
    instance_id: str,
    page_index: int = 1,
    page_size: int = 100,
    workflow_name: str = None,
) -> Dict[str, Any]:
    """
    查询工作流写入结果列表。

    API: GetBwmMigrationTaskWriterWorkflowList
    Request: { instance_id, page_index, page_size, workflow_name? }
    Response: 分页列表，每条记录包含 workflow_name, submit_status, target_workflow_id 等

    Args:
        client: LHM CLI Client
        instance_id: 部署实例 ID
        page_index: 页码
        page_size: 每页大小
        workflow_name: 可选，按工作流名称过滤

    Returns:
        响应体字典
    """
    request = {
        "instanceId": instance_id,
        "pageIndex": page_index,
        "pageSize": page_size,
    }
    if workflow_name is not None:
        request["workflowName"] = workflow_name
    response = client.get_bwm_migration_task_writer_workflow_list(request)
    body = response.body

    # 将 data 列表中的对象转为字典
    workflows = []
    if body.data:
        for item in body.data:
            workflows.append({
                "workflow_name": item.workflow_name,
                "workflow_id": item.workflow_id,
                "target_workflow_id": item.target_workflow_id,
                "target_workflow_name": item.target_workflow_name,
                "submit_status": item.submit_status,
                "submit_detail": item.submit_detail,
                "task_node_count": item.task_node_count,
                "cron": item.cron,
            })

    return {
        "data": workflows,
        "total_count": body.total_count,
        "total_pages": body.total_pages,
        "page_index": body.page_index,
        "page_size": body.page_size,
        "success": body.success,
        "err_code": body.err_code,
        "err_message": body.err_message,
    }


def fetch_all_workflows(
    client: AliyunCliClient,
    instance_id: str,
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    分页获取所有工作流结果。

    Args:
        client: LHM Client
        instance_id: 部署实例 ID
        page_size: 每页大小

    Returns:
        工作流列表（合并所有页）
    """
    all_workflows = []
    page_index = 1

    while True:
        result = list_writer_workflows(
            client, instance_id, page_index=page_index, page_size=page_size
        )

        if not result["success"]:
            raise RuntimeError(
                f"查询工作流列表失败: {result['err_code']} - {result['err_message']}"
            )

        all_workflows.extend(result["data"])

        # 检查是否还有下一页
        if page_index >= result["total_pages"]:
            break
        page_index += 1

    return all_workflows
