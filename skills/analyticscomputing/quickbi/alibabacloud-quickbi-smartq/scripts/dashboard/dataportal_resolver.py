# -*- coding: utf-8 -*-
"""
数据门户 URL 到 pageId 解析器

通过 /openapi/v2/dataportal/query 接口获取菜单树，
根据 menuId 或 homeMenu 逻辑找到对应的仪表板 pageId。
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any, List, Tuple

from .quickbi_openapi import call_quickbi_api


# ---------------------------------------------------------------------------
# Menu 类型定义（对应 find_menu.ts）
# ---------------------------------------------------------------------------

# content.type 支持的类型
CONTENT_TYPE_REPORT = 'report'  # 仪表板
CONTENT_TYPE_EXCEL = 'excel'    # 电子表格
CONTENT_TYPE_URL = 'url'        # 外部链接
CONTENT_TYPE_PAGE = 'page'      # 页面
CONTENT_TYPE_FORM = 'form'      # 数据填报
CONTENT_TYPE_DOWNLOAD = 'download'  # 自助取数
CONTENT_TYPE_CUBE = 'Cube'      # 数据集
CONTENT_TYPE_ANALYSIS = 'analysis'  # 即席分析
CONTENT_TYPE_SCREEN = 'screen'  # 数据大屏

# 支持的仪表板类型（只有 report 才能提取 pageId）
SUPPORTED_CONTENT_TYPES = {CONTENT_TYPE_REPORT}

# 内容类型中文描述
CONTENT_TYPE_NAMES = {
    CONTENT_TYPE_REPORT: '仪表板',
    CONTENT_TYPE_EXCEL: '电子表格',
    CONTENT_TYPE_URL: '外部链接',
    CONTENT_TYPE_PAGE: '页面',
    CONTENT_TYPE_FORM: '数据填报',
    CONTENT_TYPE_DOWNLOAD: '自助取数',
    CONTENT_TYPE_CUBE: '数据集',
    CONTENT_TYPE_ANALYSIS: '即席分析',
    CONTENT_TYPE_SCREEN: '数据大屏',
}


# ---------------------------------------------------------------------------
# URL 解析
# ---------------------------------------------------------------------------

def extract_dataportal_info(url: str) -> Dict[str, Optional[str]]:
    """
    从数据门户 URL 中提取 productId 和 menuId

    Args:
        url: 数据门户 URL

    Returns:
        {"productId": "xxx", "menuId": "yyy" 或 None}

    Raises:
        ValueError: 如果无法提取 productId
    """
    product_match = re.search(r'productId=([a-zA-Z0-9-]+)', url)
    menu_match = re.search(r'menuId=([a-zA-Z0-9-]+)', url)

    if not product_match:
        raise ValueError(f"无法从数据门户 URL 中提取 productId: {url}")

    return {
        "productId": product_match.group(1),
        "menuId": menu_match.group(1) if menu_match else None
    }


# ---------------------------------------------------------------------------
# 菜单树遍历（移植自 find_menu.ts）
# ---------------------------------------------------------------------------

def is_hide_menu(menu: Dict[str, Any], template_name: str = 'default') -> bool:
    """判断菜单是否隐藏"""
    config_key = 'mobileConfig' if template_name == 'mobile' else 'pcConfig'
    config = menu.get(config_key, {})
    return config.get('isHide', False) if config else False


def find_first_child(
    menu: Dict[str, Any],
    template_name: str = 'default',
    with_content: bool = True
) -> Optional[Dict[str, Any]]:
    """
    递归查找第一个有效的菜单叶子节点（移植自 find_menu.ts）

    查找条件：
    - 非空节点（isEmpty = False）
    - 非隐藏节点
    - 无子节点（叶子节点）
    - 有内容且内容类型不是 url

    Args:
        menu: 菜单节点
        template_name: 模板名称 'default' 或 'mobile'
        with_content: 是否要求有 content

    Returns:
        找到的菜单节点或 None
    """
    is_hide = is_hide_menu(menu, template_name)
    children = menu.get('children', [])
    content = menu.get('content', [])
    is_empty = menu.get('isEmpty', False)

    # 如果是有效的叶子节点
    if (
        not is_empty
        and not is_hide
        and not children
    ):
        if with_content:
            # 需要有 content 且 type 不是 url
            if content and content[0].get('type') and content[0].get('type') != 'url':
                return menu
        else:
            return menu

    # 如果当前节点被隐藏，不再遍历子节点
    if is_hide or not children:
        return None

    # 递归查找子节点
    for child_menu in children:
        result = find_first_child(child_menu, template_name, with_content)
        if result:
            return result

    return None


def get_menu_by(
    menu_root: List[Dict[str, Any]],
    predicate: callable
) -> Optional[Dict[str, Any]]:
    """
    在菜单树中查找满足条件的菜单节点

    Args:
        menu_root: 菜单根节点列表
        predicate: 判断函数

    Returns:
        找到的菜单节点或 None
    """
    def visit(menus: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for menu in menus:
            if predicate(menu):
                return menu
            children = menu.get('children', [])
            if children:
                result = visit(children)
                if result:
                    return result
        return None

    return visit(menu_root)


def get_selected_menu(
    menus: List[Dict[str, Any]],
    menu_id: Optional[str] = None,
    template_name: str = 'default'
) -> Optional[Dict[str, Any]]:
    """
    获取选中的菜单（移植自 find_menu.ts 的 getSelectedMenuId 逻辑）

    逻辑：
    1. 如果有 menuId，直接查找该菜单
    2. 如果没有 menuId，选中首页（isHome=True）
    3. 如果首页是空节点，选择第一个非空节点

    Args:
        menus: 菜单列表
        menu_id: 可选的菜单 ID
        template_name: 模板名称

    Returns:
        选中的菜单节点或 None
    """
    # 1. 如果有 menuId，直接查找
    if menu_id:
        return get_menu_by(menus, lambda m: m.get('id') == menu_id)

    # 2. 没有 menuId，查找首页
    home_menu = get_menu_by(menus, lambda m: m.get('isHome', False))

    if home_menu:
        # 如果首页是空节点，找第一个非空子节点
        first_child = find_first_child(home_menu, template_name)
        if first_child:
            return first_child

    # 3. 没有首页或首页为空，找整个菜单树的第一个非空节点
    virtual_root = {'isEmpty': True, 'children': menus}
    first_menu = find_first_child(virtual_root, template_name)
    return first_menu


def extract_page_id_from_menu(menu: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """
    从菜单节点中提取 pageId

    Args:
        menu: 菜单节点

    Returns:
        (success, message, page_id)
        - success: 是否成功
        - message: 成功或错误信息
        - page_id: 仪表板 pageId（成功时有值）
    """
    content = menu.get('content', [])

    if not content:
        return False, "菜单没有关联任何内容", None

    first_content = content[0]
    content_type = first_content.get('type')
    content_id = first_content.get('id')
    content_name = first_content.get('name', '未命名')

    if content_type not in SUPPORTED_CONTENT_TYPES:
        type_name = CONTENT_TYPE_NAMES.get(content_type, content_type)
        return (
            False,
            f"该菜单关联的是「{type_name}」类型（{content_name}），"
            f"不是仪表板。请提供指向仪表板的数据门户链接。",
            None
        )

    if not content_id:
        return False, f"菜单「{content_name}」未关联有效的仪表板 ID", None

    return True, f"成功获取仪表板「{content_name}」", content_id


# ---------------------------------------------------------------------------
# OpenAPI 调用
# ---------------------------------------------------------------------------

def query_dataportal_menus(
    host: str,
    access_id: str,
    access_key: str,
    dataportal_id: str
) -> Dict[str, Any]:
    """
    查询数据门户菜单树

    调用 /openapi/v2/dataportal/query 接口获取菜单结构。

    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        dataportal_id: 数据门户 ID（即 URL 中的 productId）

    Returns:
        {
            "success": True,
            "menus": [...菜单树...]
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    uri = "/openapi/v2/dataportal/query"

    form_params = {
        "dataPortalId": dataportal_id
    }

    try:
        result = call_quickbi_api(
            host=host,
            uri=uri,
            access_id=access_id,
            access_key=access_key,
            method="GET",
            form_params=form_params
        )

        success_val = result.get("success")
        is_success = success_val is True or success_val == "true"

        if is_success:
            data = result.get("data", {})
            # 菜单树在 data.menu 或 data.menus 中
            menus = data.get("menu") or data.get("menus") or []
            if isinstance(menus, dict):
                # 如果返回的是单个菜单对象，包装成列表
                menus = [menus]

            return {
                "success": True,
                "menus": menus,
                "dataportal_name": data.get("name", "")
            }
        else:
            return {
                "success": False,
                "error_code": str(result.get("errorCode", result.get("code", "UNKNOWN"))),
                "error_message": result.get("errorMsg", result.get("message", "未知错误"))
            }
    except Exception as e:
        return {
            "success": False,
            "error_code": "CONNECTION_ERROR",
            "error_message": f"查询数据门户失败: {str(e)}"
        }


def resolve_dataportal_page_id(
    host: str,
    access_id: str,
    access_key: str,
    dataportal_url: str
) -> Dict[str, Any]:
    """
    从数据门户 URL 解析出仪表板 pageId

    完整流程：
    1. 从 URL 提取 productId 和 menuId
    2. 调用 /openapi/v2/dataportal/query 获取菜单树
    3. 根据 menuId 或 homeMenu 逻辑找到目标菜单
    4. 验证菜单内容类型为 report，提取 pageId

    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        dataportal_url: 数据门户 URL

    Returns:
        {
            "success": True,
            "page_id": "仪表板 pageId",
            "dashboard_name": "仪表板名称",
            "dataportal_name": "数据门户名称"
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    # 1. 从 URL 提取参数
    try:
        url_info = extract_dataportal_info(dataportal_url)
        product_id = url_info["productId"]
        menu_id = url_info["menuId"]
    except ValueError as e:
        return {
            "success": False,
            "error_code": "INVALID_URL",
            "error_message": str(e)
        }

    # 2. 查询菜单树
    query_result = query_dataportal_menus(host, access_id, access_key, product_id)

    if not query_result["success"]:
        return query_result

    menus = query_result["menus"]
    dataportal_name = query_result.get("dataportal_name", "")

    if not menus:
        return {
            "success": False,
            "error_code": "EMPTY_MENU",
            "error_message": "数据门户没有配置任何菜单"
        }

    # 3. 查找目标菜单
    target_menu = get_selected_menu(menus, menu_id)

    if not target_menu:
        if menu_id:
            return {
                "success": False,
                "error_code": "MENU_NOT_FOUND",
                "error_message": f"在数据门户中找不到 menuId={menu_id} 对应的菜单"
            }
        else:
            return {
                "success": False,
                "error_code": "NO_DEFAULT_MENU",
                "error_message": "数据门户没有可用的默认菜单（首页或第一个非空菜单）"
            }

    # 4. 从菜单中提取 pageId
    success, message, page_id = extract_page_id_from_menu(target_menu)

    if not success:
        return {
            "success": False,
            "error_code": "INVALID_CONTENT_TYPE",
            "error_message": message
        }

    # 获取仪表板名称
    content = target_menu.get('content', [])
    dashboard_name = content[0].get('name', '') if content else ''

    return {
        "success": True,
        "page_id": page_id,
        "dashboard_name": dashboard_name,
        "dataportal_name": dataportal_name,
        "menu_id": target_menu.get('id'),
        "menu_title": target_menu.get('title', '')
    }


# ---------------------------------------------------------------------------
# 测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse as _argparse
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from common.config_loader import load_config, set_workspace_dir

    _parser = _argparse.ArgumentParser(description="数据门户 URL 解析器")
    _parser.add_argument("--url", default="https://bi.aliyun.com/product/view.htm?productId=xxx&menuId=yyy",
                         help="数据门户 URL")
    _parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    _args = _parser.parse_args()

    if _args.workspace_dir:
        set_workspace_dir(_args.workspace_dir)

    config = load_config()

    # 检查必要配置
    _api_key = config.get("api_key")
    _api_secret = config.get("api_secret")
    if not _api_key or not _api_secret:
        print("缺少必要配置项: api_key / api_secret，请检查配置文件")
        sys.exit(1)

    # 测试 URL
    test_url = _args.url

    result = resolve_dataportal_page_id(
        host=config.get("server_domain", "https://quickbi-public.cn-hangzhou.aliyuncs.com"),
        access_id=_api_key,
        access_key=_api_secret,
        dataportal_url=test_url
    )

    print(result)
