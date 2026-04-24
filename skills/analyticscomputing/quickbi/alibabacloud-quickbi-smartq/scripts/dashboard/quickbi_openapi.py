"""
QuickBI OpenAPI HTTP 调用工具函数

使用 HMAC-SHA256 签名方式调用 QuickBI OpenAPI，无需 SDK 依赖。
"""

import base64
import datetime
import hmac
import sys
import time
import uuid
from pathlib import Path
from urllib import parse
import requests
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入配置加载器（四层配置加载，详见 config_loader.py）
from common.config_loader import load_config as _load_config_from_loader


def load_config(config_path: str = None) -> dict:
    """加载配置。

    四层配置加载（高覆盖低）：
    1. default_config.yaml（包内默认值）
    2. ~/.qbi/config.yaml（QBI 全局配置，受 save_global_property 开关控制）
    3. $WORKSPACE_DIR/.qbi/smartq-chat/config.yaml（工作目录级配置）
    4. ACCESS_TOKEN 环境变量（最高优先级）

    委托 config_loader.py 的四层加载器实现。

    Args:
        config_path: 可选，指定配置文件路径（向后兼容，不建议使用）

    Returns:
        配置字典
    """
    if config_path:
        # 向后兼容：从指定路径加载
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    # 使用配置加载器（四层配置加载）
    return _load_config_from_loader()


def hash_hmac(key: str, code: str, algorithm: str = 'sha256') -> str:
    """Base64编码的HMAC-SHA256计算值"""
    hmac_code = hmac.new(key.encode('UTF-8'), code.encode('UTF-8'), algorithm).digest()
    return base64.b64encode(hmac_code).decode()


def build_signature(
    method: str,
    uri: str,
    params: dict,
    access_id: str,
    access_key: str,
    nonce: str,
    timestamp: str
) -> str:
    """
    构造签名
    
    StringToSign = HTTP_METHOD + "\n" + URI + QueryString + 
                   "\nX-Gw-AccessId:" + AccessID + 
                   "\nX-Gw-Nonce:" + UUID + 
                   "\nX-Gw-Timestamp:" + Timestamp
    Signature = Base64(HMAC-SHA256(AccessKey, URL_Encode(StringToSign)))
    """
    # Request参数拼接（按key排序）
    if not params:
        request_query_string = ''
    else:
        sorted_keys = sorted(params.keys())
        query_parts = [f"{key}={params[key]}" for key in sorted_keys if params[key] is not None]
        request_query_string = '\n' + '&'.join(query_parts) if query_parts else ''
    
    # Request Header拼接
    request_headers = f'\nX-Gw-AccessId:{access_id}\nX-Gw-Nonce:{nonce}\nX-Gw-Timestamp:{timestamp}'
    
    # 待签名字符串
    string_to_sign = method.upper() + '\n' + uri + request_query_string + request_headers
    
    # URL编码并计算签名
    encode_string = parse.quote(string_to_sign, '')
    sign = hash_hmac(access_key, encode_string)
    
    return sign


def call_quickbi_api(
    host: str,
    uri: str,
    access_id: str,
    access_key: str,
    method: str = "POST",
    json_param: dict = None,
    form_params: dict = None,
    content_type: str = "application/json"
) -> dict:
    """
    调用 QuickBI OpenAPI
    
    Args:
        host: QuickBI 服务域名
        uri: API 接口路径
        access_id: AccessKey ID
        access_key: AccessKey Secret
        method: HTTP 方法，默认 POST
        json_param: JSON 格式请求体
        form_params: 表单参数（参与签名计算）
        content_type: Content-Type，默认 application/json
    
    Returns:
        JSON 格式的响应数据
    """
    url = host + uri
    nonce = str(uuid.uuid1())
    timestamp = str(round(time.time() * 1000))
    
    signature = build_signature(method, uri, form_params, access_id, access_key, nonce, timestamp)
    
    headers = {
        'X-Gw-AccessId': str(access_id),
        'X-Gw-Nonce': nonce,
        'X-Gw-Timestamp': timestamp,
        'X-Gw-Signature': signature,
        'X-Gw-Debug': 'true',
        'Content-Type': content_type
    }
    
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=form_params,
        json=json_param,
        verify="test" not in url.lower(),
        timeout=300
    )
    return response.json()


def query_openapi(
    endpoint: str,
    access_key_id: str,
    access_key_secret: str,
    question: str,
    user_id: str = None,
    cube_id: str = None
) -> dict:
    """
    调用 QuickBI SmartQ 查询接口
    与 SDK 的 SmartqQueryAbility 接口入参保持一致
    
    Args:
        endpoint: QuickBI endpoint
        access_key_id: AccessKey ID
        access_key_secret: AccessKey Secret
        question: 自然语言问题
        user_id: 用户ID（可选）
        cube_id: 数据集ID（可选，多个用逗号分隔）
    
    Returns:
        查询结果 JSON
    """
    uri = "/openapi/v2/smartq/queryByQuestion"
    
    json_param = {"userQuestion": question}
    
    if user_id:
        json_param["userId"] = user_id
    
    # 处理 cube_id（单表/多表场景）
    if cube_id:
        if ',' in cube_id:
            json_param["multipleCubeIds"] = cube_id  # 多表
        else:
            json_param["cubeId"] = cube_id  # 单表
    
    return call_quickbi_api(
        host=endpoint,
        uri=uri,
        access_id=access_key_id,
        access_key=access_key_secret,
        method="POST",
        json_param=json_param
    )





def is_dataportal_url(url: str) -> bool:
    """
    判断是否为数据门户页面 URL
    
    数据门户 URL 特征:
    - 路径包含 /product/view.htm
    - 包含 productId 和 menuId 参数
    
    Args:
        url: 要检查的 URL
    
    Returns:
        True 如果是数据门户 URL，否则 False
    """
    return '/product/view.htm' in url


def extract_dataportal_ids(url: str) -> dict:
    """
    从数据门户 URL 中提取 productId 和 menuId
    
    支持格式:
    - https://bi.aliyun.com/product/view.htm?module=dashboard&productId=xxx&menuId=yyy
    - https://bi.aliyun.com/product/view.htm?productId=xxx（无 menuId）
    
    Args:
        url: 数据门户 URL
    
    Returns:
        {"productId": "xxx", "menuId": "yyy" 或 None}
    
    Raises:
        ValueError: 如果无法提取 productId
    """
    import re
    
    product_match = re.search(r'productId=([a-zA-Z0-9-]+)', url)
    menu_match = re.search(r'menuId=([a-zA-Z0-9-]+)', url)
    
    if not product_match:
        raise ValueError(f"无法从数据门户 URL 中提取 productId: {url}")
    
    return {
        "productId": product_match.group(1),
        "menuId": menu_match.group(1) if menu_match else None
    }


def get_dataportal_page_id(
    host: str,
    access_id: str,
    access_key: str,
    dataportal_id: str,
    menu_id: str = None
) -> dict:
    """
    通过数据门户接口获取真实的仪表板 pageId
    
    调用 /openapi/v2/dataportal/query 接口获取菜单树，
    根据 menuId 或 homeMenu 逻辑找到对应的仪表板 pageId。
    
    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        dataportal_id: 数据门户 ID（即 URL 中的 productId）
        menu_id: 菜单 ID（可选，不传则自动查找 homeMenu 或第一个有效菜单）
    
    Returns:
        {
            "success": True,
            "page_id": "仪表板 pageId",
            "dashboard_name": "仪表板名称",
            "menu_id": "实际使用的菜单 ID",
            "menu_title": "菜单标题"
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    from .dataportal_resolver import (
        query_dataportal_menus,
        get_selected_menu,
        extract_page_id_from_menu
    )
    
    # 1. 查询菜单树
    query_result = query_dataportal_menus(host, access_id, access_key, dataportal_id)
    
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
    
    # 2. 查找目标菜单
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
    
    # 3. 从菜单中提取 pageId
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


def extract_page_id(url: str) -> str:
    """
    从仪表板 URL 中提取 pageId
    
    支持格式:
    - https://bi.aliyun.com/dashboard/view/pc.htm?pageId=XXXXXXX
    - https://bi.aliyun.com/token3rd/dashboard/view/pc.htm?pageId=XXXXXXX&accessToken=...
    
    注意: 此函数仅支持直接包含 pageId 的仪表板 URL。
    对于数据门户 URL（/product/view.htm），请先使用 is_dataportal_url() 判断，
    然后使用 extract_dataportal_ids() 和 get_dataportal_page_id() 获取 pageId。
    
    Args:
        url: 仪表板 URL
    
    Returns:
        pageId 字符串
    
    Raises:
        ValueError: 如果无法提取 pageId
    """
    import re
    match = re.search(r'pageId=([a-zA-Z0-9-]+)', url)
    if match:
        return match.group(1)
    raise ValueError(f"无法从 URL 中提取 pageId: {url}")


def validate_and_prepare_dashboard(
    host: str,
    access_id: str,
    access_key: str,
    page_id: str,
    user_id: str
) -> dict:
    """
    仪表板转换前的预校验及预处理
    
    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        page_id: 仪表板 pageId
        user_id: 用户 token
    
    Returns:
        {
            "success": True,
            "url": "预处理后的仪表板 URL"
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    uri = "/openapi/v2/skills/dashboard/handle"
    json_param = {
        "id": page_id,
        "userId": user_id,
        "runningBySkill": True,
    }
    
    try:
        result = call_quickbi_api(
            host=host,
            uri=uri,
            access_id=access_id,
            access_key=access_key,
            method="POST",
            json_param=json_param
        )
        
        # success 可能是布尔值或字符串 "true"/"false"
        success_val = result.get("success")
        is_success = success_val == True or success_val == "true"
        
        if is_success:
            # URL 在 data 字段中
            return {
                "success": True,
                "url": result.get("data")
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
            "error_message": f"连接失败: {str(e)}"
        }


def get_dashboard_update_time(
    host: str,
    access_id: str,
    access_key: str,
    page_id: str,
    user_id: str
) -> dict:
    """
    查询仪表板的最后更新时间
    
    通过 /openapi/v2/dashboard/query 接口获取仪表板大 JSON，
    从中提取 gmtModified 字段作为最后更新时间。
    
    用于在生成的查询 skill 启动时校验仪表板是否有更新，
    如果仪表板有更新，则提示用户重新生成 skill。
    
    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        page_id: 仪表板 pageId（即 dashboardId）
        user_id: 用户 token
    
    Returns:
        {
            "success": True,
            "data": {
                "page_id": "xxx",
                "last_modified": xxx,  # 仪表板最后修改时间（gmtModified 原值，用于对比变化）
                "dashboard_name": "仪表板名称"
            }
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    uri = "/openapi/v2/dashboard/query"
    
    # 使用 form_params 作为查询参数
    form_params = {
        "dashboardId": page_id,
        "viewType": "view",
        "queryFavorite": "true"
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
        is_success = success_val == True or success_val == "true"
        
        if is_success:
            data = result.get("data", {})
            # 从仪表板大 JSON 中提取更新时间（gmtModified 原值，用于对比变化）
            gmt_modified = data.get("gmtModified")
            dashboard_name = data.get("name", "")
            
            return {
                "success": True,
                "data": {
                    "page_id": page_id,
                    "last_modified": gmt_modified,
                    "dashboard_name": dashboard_name
                }
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
            "error_message": f"查询仪表板更新时间失败: {str(e)}"
        }


def get_dashboard_json(
    host: str,
    access_id: str,
    access_key: str,
    page_id: str,
    user_id: str
) -> dict:
    """
    获取仪表板完整 JSON 数据
    
    通过 /openapi/v2/dashboard/query 接口获取仪表板大 JSON，
    用于解析仪表板结构。
    
    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        page_id: 仪表板 pageId（即 dashboardId）
        user_id: 用户 token
    
    Returns:
        {
            "success": True,
            "data": { ... 仪表板完整 JSON ... }
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    uri = "/openapi/v2/dashboard/query"
    
    form_params = {
        "dashboardId": page_id,
        "viewType": "view",
        "queryFavorite": "true"
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
        is_success = success_val == True or success_val == "true"
        
        if is_success:
            return {
                "success": True,
                "data": result.get("data", {})
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
            "error_message": f"获取仪表板数据失败: {str(e)}"
        }


def batch_get_dataset_schema(
    host: str,
    access_id: str,
    access_key: str,
    cube_ids: list
) -> dict:
    """
    批量获取数据集详情（包括数据集名称）
    
    通过 /openapi/v2/dataset/batchGetSchema 接口批量获取数据集 schema 信息，
    主要用于获取数据集的名称等元信息，提供更友好的展示。
    
    Args:
        host: QuickBI 服务域名
        access_id: API Key
        access_key: API Secret
        cube_ids: 数据集 ID 列表
    
    Returns:
        {
            "success": True,
            "data": {
                "cube_id_1": {"cubeId": "...", "cubeName": "数据集名称", ...},
                "cube_id_2": {"cubeId": "...", "cubeName": "数据集名称", ...}
            }
        }
        或
        {
            "success": False,
            "error_code": "错误码",
            "error_message": "错误信息"
        }
    """
    if not cube_ids:
        return {
            "success": True,
            "data": {}
        }
    
    uri = "/openapi/v2/dataset/batchGetSchema"
    
    json_param = {
        "cubeIds": cube_ids
    }
    
    try:
        result = call_quickbi_api(
            host=host,
            uri=uri,
            access_id=access_id,
            access_key=access_key,
            method="POST",
            json_param=json_param
        )
        
        success_val = result.get("success")
        is_success = success_val == True or success_val == "true"
        
        if is_success:
            # 将返回数据转换为 cubeId -> schema 的映射
            data_list = result.get("data", [])
            data_map = {}
            
            if isinstance(data_list, list):
                for item in data_list:
                    cube_id = item.get("cubeId")
                    if cube_id:
                        data_map[cube_id] = item
            elif isinstance(data_list, dict):
                # 如果返回的就是 dict，直接使用
                data_map = data_list
            
            return {
                "success": True,
                "data": data_map
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
            "error_message": f"批量获取数据集详情失败: {str(e)}"
        }


def validate_api_credentials(config: dict) -> dict:
    """
    验证 API 凭证有效性
    
    Args:
        config: 配置字典，需包含 server_domain, api_key, api_secret
    
    Returns:
        验证结果 {"success": bool, "error": str, "error_code": str}
    """
    try:
        # 调用一个简单的接口验证凭证
        result = call_quickbi_api(
            host=config.get("server_domain", "https://quickbi-public.cn-hangzhou.aliyuncs.com"),
            uri="/openapi/v2/workspace/list",
            access_id=config["api_key"],
            access_key=config["api_secret"],
            method="GET"
        )
        
        if result.get("success", False) or result.get("code") == 200:
            return {"success": True}
        else:
            return {
                "success": False,
                "error": result.get("message", "API 验证失败"),
                "error_code": str(result.get("code", "UNKNOWN"))
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"连接失败: {str(e)}",
            "error_code": "CONNECTION_ERROR"
        }


# 使用示例
if __name__ == "__main__":
    # 加载配置
    config = load_config()
    
    # 检查必要配置
    _server_domain = config.get("server_domain")
    _api_key = config.get("api_key")
    _api_secret = config.get("api_secret")
    if not _server_domain or not _api_key or not _api_secret:
        print("缺少必要配置项: server_domain / api_key / api_secret，请检查配置文件")
        exit(1)
    
    # 验证凭证
    validation = validate_api_credentials(config)
    if not validation["success"]:
        print(f"验证失败: {validation['error']}")
        exit(1)
    
    # SmartQ 查询
    result = query_openapi(
        endpoint=_server_domain,
        access_key_id=_api_key,
        access_key_secret=_api_secret,
        question="查询销售额排名前五的商品",
        cube_id="your-cube-id"
    )
    print(result)
