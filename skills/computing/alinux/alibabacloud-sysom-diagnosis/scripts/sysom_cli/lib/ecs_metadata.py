# -*- coding: utf-8 -*-
"""
阿里云 ECS 实例元数据服务访问工具。

仅能在 ECS 实例内网访问：``http://100.100.100.200/latest/meta-data/...``

常用 ``path`` 示例（相对 ``/latest/meta-data/``）::

    instance-id, hostname, region-id, zone-id, image-id
    private-ipv4, vpc-id, vswitch-id, mac, network-type
    owner-account-id, serial-number, source-address
    disks/, network/, instance/   # 目录列表（返回多行文本）
    ram/security-credentials/<RoleName>  # JSON，请用 ``get_ecs_metadata_json``

参考：在实例内执行 ``curl http://100.100.100.200/latest/meta-data`` 可查看根下列表。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Union

import requests

__all__ = [
    "ECS_METADATA_HOST",
    "ECS_METADATA_ROOT",
    "build_ecs_metadata_url",
    "get_ecs_metadata",
    "get_ecs_metadata_json",
]

# 固定链路本地地址（阿里云 ECS）
ECS_METADATA_HOST = "100.100.100.200"
ECS_METADATA_ROOT = f"http://{ECS_METADATA_HOST}/latest/meta-data"


def build_ecs_metadata_url(path: str = "") -> str:
    """
    构造元数据 URL。

    Args:
        path: 相对 ``/latest/meta-data/`` 的路径，如 ``instance-id``、``region-id``、``disks/``；
            空字符串表示根路径（列出顶层条目）。
    """
    p = (path or "").strip().lstrip("/")
    if not p:
        return ECS_METADATA_ROOT
    return f"{ECS_METADATA_ROOT}/{p}"


def get_ecs_metadata(
    path: str = "",
    *,
    timeout: float = 3.0,
    strip: bool = True,
) -> Dict[str, Any]:
    """
    GET 文本类元数据（含目录列表的多行文本）。

    Returns:
        成功: ``{"ok": True, "text": str, "status_code": 200}``
        失败: ``{"ok": False, "error": str, "status_code": int|None}``
    """
    url = build_ecs_metadata_url(path)
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "连接超时（可能不在 ECS 环境或元数据服务不可达）",
            "status_code": None,
        }
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"请求失败: {e}", "status_code": None}

    if resp.status_code != 200:
        return {
            "ok": False,
            "error": f"HTTP {resp.status_code}: 无法读取元数据",
            "status_code": resp.status_code,
        }

    text = resp.text
    if strip:
        text = text.strip()
    return {"ok": True, "text": text, "status_code": resp.status_code}


def get_ecs_metadata_json(
    path: str,
    *,
    timeout: float = 3.0,
) -> Dict[str, Any]:
    """
    GET 并解析为 JSON（如 ``ram/security-credentials/<角色名>``）。

    Returns:
        成功: ``{"ok": True, "data": dict|list}``
        失败: ``{"ok": False, "error": str, "status_code": int|None, "text": str|None}``
    """
    url = build_ecs_metadata_url(path)
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "连接超时（可能不在 ECS 环境或元数据服务不可达）",
            "status_code": None,
            "text": None,
        }
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "error": f"请求失败: {e}",
            "status_code": None,
            "text": None,
        }

    if resp.status_code != 200:
        return {
            "ok": False,
            "error": f"HTTP {resp.status_code}: 无法读取元数据",
            "status_code": resp.status_code,
            "text": resp.text[:500] if resp.text else None,
        }

    try:
        data: Union[dict, list] = resp.json()
    except json.JSONDecodeError as e:
        return {
            "ok": False,
            "error": f"响应不是合法 JSON: {e}",
            "status_code": resp.status_code,
            "text": resp.text[:500] if resp.text else None,
        }

    return {"ok": True, "data": data, "status_code": resp.status_code}
