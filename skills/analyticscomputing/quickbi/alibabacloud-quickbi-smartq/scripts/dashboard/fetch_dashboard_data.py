#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仪表板数据一站式获取脚本

封装完整流程：
1. 加载配置
2. 解析 URL 获取 pageId（支持仪表板 URL 和数据门户 URL）
3. 调用 OpenAPI 获取仪表板大 JSON
4. 调用 Node.js 脚本解析 JSON 结构
5. 获取数据集名称映射

使用方式：
    from scripts.fetch_dashboard_data import fetch_dashboard_data
    
    result = fetch_dashboard_data(user_input_url)
    if result["success"]:
        dashboardData = result["dashboardData"]
        datasetNameMap = result["datasetNameMap"]
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config_loader import load_config, set_workspace_dir
from dashboard.quickbi_openapi import (
    batch_get_dataset_schema,
    extract_dataportal_ids,
    extract_page_id,
    get_dashboard_json,
    get_dataportal_page_id,
    is_dataportal_url,
    validate_and_prepare_dashboard,
)


def fetch_dashboard_data(url: str, config: dict = None) -> dict:
    """
    一站式获取仪表板数据（包含解析和数据集名称）
    
    Args:
        url: 仪表板 URL 或数据门户 URL
        config: 可选，配置字典。不传则自动加载
    
    Returns:
        {
            "success": True,
            "dashboardData": {...},      # 解析后的仪表板结构
            "datasetNameMap": {...},     # cubeId -> cubeName 映射
            "pageId": "xxx",             # 仪表板 pageId
            "preparedUrl": "xxx",        # 预处理后的 URL
            "error": None
        }
        或
        {
            "success": False,
            "error": "错误信息",
            "error_code": "错误码"
        }
    """
    # 1. 加载配置
    if config is None:
        config = load_config()
    
    if not config:
        return {
            "success": False,
            "error": "配置加载失败，请检查工作目录级配置或全局配置 ~/.qbi/config.yaml",
            "error_code": "CONFIG_LOAD_ERROR"
        }
    
    # 检查必要配置项
    required_keys = ["server_domain", "api_key", "api_secret", "user_token"]
    missing_keys = [k for k in required_keys if not config.get(k)]
    if missing_keys:
        return {
            "success": False,
            "error": f"配置缺失: {', '.join(missing_keys)}",
            "error_code": "CONFIG_INCOMPLETE"
        }
    
    # 2. 解析 URL 获取 pageId
    try:
        if is_dataportal_url(url):
            # 数据门户 URL：需要先获取关联的仪表板 pageId
            portal_ids = extract_dataportal_ids(url)
            portal_result = get_dataportal_page_id(
                host=config["server_domain"],
                access_id=config["api_key"],
                access_key=config["api_secret"],
                dataportal_id=portal_ids["productId"],
                menu_id=portal_ids["menuId"]
            )
            
            if not portal_result["success"]:
                return {
                    "success": False,
                    "error": f"获取数据门户关联仪表板失败: {portal_result['error_message']}",
                    "error_code": portal_result.get("error_code", "PORTAL_ERROR")
                }
            
            page_id = portal_result["page_id"]
        else:
            # 普通仪表板 URL：直接提取 pageId
            page_id = extract_page_id(url)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "URL_PARSE_ERROR"
        }
    
    # 3. 预校验
    validate_result = validate_and_prepare_dashboard(
        host=config["server_domain"],
        access_id=config["api_key"],
        access_key=config["api_secret"],
        page_id=page_id,
        user_id=config["user_token"]
    )
    
    if validate_result.get("success") == False or validate_result.get("success") == "false":
        return {
            "success": False,
            "error": f"预校验失败: {validate_result.get('error_message', '未知错误')}",
            "error_code": validate_result.get("error_code", "VALIDATE_ERROR")
        }
    
    prepared_url = validate_result.get("url", url)
    
    # 4. 获取仪表板大 JSON
    dashboard_result = get_dashboard_json(
        host=config["server_domain"],
        access_id=config["api_key"],
        access_key=config["api_secret"],
        page_id=page_id,
        user_id=config["user_token"]
    )
    
    if not dashboard_result["success"]:
        return {
            "success": False,
            "error": f"获取仪表板数据失败: {dashboard_result.get('error_message', '未知错误')}",
            "error_code": dashboard_result.get("error_code", "DASHBOARD_ERROR")
        }
    
    raw_dashboard_json = dashboard_result["data"]
    
    # 5. 调用 Node.js 脚本解析
    script_dir = Path(__file__).parent
    js_script = script_dir / "get_dashboard_json.js"

    if not js_script.exists():
        return {
            "success": False,
            "error": f"解析脚本不存在: {js_script}",
            "error_code": "SCRIPT_NOT_FOUND"
        }

    # 先获取数据集schema信息，用于字段别名解析
    # 从 dataFromId 字段获取数据集ID
    cube_ids = list(set([
        comp.get("dataFromId")
        for comp in raw_dashboard_json.get("components", [])
        if comp.get("dataFromId")
    ]))

    dataset_schema_map = {}
    if cube_ids:
        dataset_result = batch_get_dataset_schema(
            host=config["server_domain"],
            access_id=config["api_key"],
            access_key=config["api_secret"],
            cube_ids=cube_ids
        )

        if dataset_result["success"]:
            for cube_id, info in dataset_result["data"].items():
                cube_schema = info.get("data", {}).get("cubeSchema", {})
                fields = cube_schema.get("fields", [])
                dataset_schema_map[cube_id] = {
                    "cubeName": cube_schema.get("caption", cube_id),
                    "fields": fields
                }

    # 准备输入数据：包含仪表板JSON和schema信息
    input_data = {
        "dashboardJson": raw_dashboard_json,
        "datasetSchemaMap": dataset_schema_map
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(input_data, f)
        temp_file = f.name

    try:
        # 使用 context manager 确保文件句柄正确关闭，避免 Windows 上文件锁导致后续删除失败
        with open(temp_file, 'r', encoding='utf-8') as stdin_f:
            result = subprocess.run(
                ['node', str(js_script)],
                stdin=stdin_f,
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=str(script_dir.parent)
            )

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"解析脚本执行失败: {result.stderr}",
                "error_code": "SCRIPT_EXEC_ERROR"
            }

        dashboard_data = json.loads(result.stdout)

        if not dashboard_data.get('success'):
            return {
                "success": False,
                "error": f"解析失败: {dashboard_data.get('error', '未知错误')}",
                "error_code": "PARSE_ERROR"
            }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"解析结果格式错误: {str(e)}",
            "error_code": "JSON_DECODE_ERROR"
        }
    finally:
        try:
            os.unlink(temp_file)
        except OSError:
            pass  # Windows 上文件可能仍被锁定，忽略删除失败

    # 6. 从解析结果中提取数据集名称映射
    # datasetSchemaMap 已由 Node.js 脚本在解析过程中使用，并保留在返回结果中
    dataset_name_map = {}
    if dashboard_data.get("datasetSchemaMap"):
        for cube_id, schema_info in dashboard_data["datasetSchemaMap"].items():
            dataset_name_map[cube_id] = schema_info.get("cubeName", cube_id)

    # 构建标准仪表板预览页 URL
    dashboard_url = f"{config['server_domain']}/dashboard/view/pc.htm?pageId={page_id}"

    return {
        "success": True,
        "dashboardData": dashboard_data,
        "datasetNameMap": dataset_name_map,
        "pageId": page_id,
        "dashboardUrl": dashboard_url,  # 标准仪表板预览页地址
        "preparedUrl": prepared_url,    # 原始预处理 URL（保留兼容）
        "error": None
    }


if __name__ == "__main__":
    import argparse as _argparse

    _parser = _argparse.ArgumentParser(description="仪表板数据一站式获取")
    _parser.add_argument("url", help="仪表板 URL 或数据门户 URL")
    _parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    _args = _parser.parse_args()

    if _args.workspace_dir:
        set_workspace_dir(_args.workspace_dir)

    result = fetch_dashboard_data(_args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
