# -*- coding: utf-8 -*-
"""
QBI 小Q问数公共工具（统一版）。

提供配置读取、OpenAPI 签名、HTTP 请求（含 SSE 流式）、SSE 事件解析、
用户自动注册、试用提示以及 multipart 文件上传能力。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import random
import re
import string
import time
import uuid
from html import unescape
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Tuple
from urllib import parse

import requests

from .config_loader import (
    load_config as read_config,    # 向后兼容：其他脚本 from utils import read_config
    persist_to_skill_config,
    persist_to_global_config,
    is_global_save_enabled,
    set_workspace_dir,
    get_server_domain,
    get_skill_config_path,
    get_skill_output_dir,
    check_trial_expired,
    TRIAL_EXPIRED_CODE,
    DEFAULT_CONFIG_PATH,
    GLOBAL_CONFIG_PATH,
)

BASE_DIR = Path(__file__).resolve().parent


def _should_skip_ssl(url: str) -> bool:
    """当请求域名包含 'test' 时跳过 SSL 证书验证。"""
    return "test" in url.lower()


def require_user_id(config: dict) -> str:
    """获取 userId，按优先级：外部config → 自动注册。"""
    user_id = config.get("user_token")
    if user_id is None or str(user_id).strip() == "":
        user_id = _auto_provision_user(config)
        config["user_token"] = user_id
    else:
        user_id = str(user_id).strip()
        config["user_token"] = user_id
        # 已有 user_token（来自全局/skill/环境变量），无需再持久化
    return user_id


# ---------------------------------------------------------------------------
# 用户自动注册
# ---------------------------------------------------------------------------

from .device_id import get_device_account_id as _get_device_account_id  # noqa: E402
from .device_id import get_device_hostname as _get_device_hostname  # noqa: E402

_ALREADY_IN_ORG_CODE = "AE0150100022"
_NICK_EXISTS_CODE = "AE0150100010"
_last_add_user_code: Optional[str] = None


def _add_user_to_org(account_id: str, hostname: str, config: dict) -> Optional[str]:
    """
    调用 POST /openapi/v2/organization/user/addSuer 添加用户到默认组织。
    返回系统分配的 userId，失败返回 None。
    """
    uri = "/openapi/v2/organization/user/addSuer"
    body: Dict[str, Any] = {
        "accountId": account_id,
        "accountName": hostname,
        "nickName": hostname
    }
    print(f"[用户注册][添加用户] 请求: POST {uri}", flush=True)
    print(f"[用户注册][添加用户] 入参: {json.dumps(body, ensure_ascii=False)}", flush=True)
    global _last_add_user_code
    try:
        resp = request_openapi(
            "POST",
            uri,
            json_body=body,
            config=config,
        )
        result = resp.json()
        print(f"[用户注册][添加用户] 响应: {json.dumps(result, ensure_ascii=False)}", flush=True)
        _last_add_user_code = str(result.get("code", ""))
        if result.get("success") is True and isinstance(result.get("data"), dict):
            user_id = result["data"].get("userId")
            if user_id:
                return user_id
    except Exception as e:
        print(f"[用户注册][添加用户] 异常: {e}", flush=True)
    return None


def _query_user_by_account(account_name: str, config: dict) -> Optional[str]:
    """
    通过 GET /openapi/v2/organization/user/queryByAccount 查询已存在用户的 userId。
    """
    uri = "/openapi/v2/organization/user/queryByAccount"
    params = {"account": account_name}
    print(f"[用户注册][查询用户] 请求: GET {uri}?account={account_name}", flush=True)
    try:
        resp = request_openapi("GET", uri, params=params, config=config)
        result = resp.json()
        print(f"[用户注册][查询用户] 响应: {json.dumps(result, ensure_ascii=False)}", flush=True)
        if result.get("success") and isinstance(result.get("data"), dict):
            return result["data"].get("userId")
    except Exception as e:
        print(f"[用户注册][查询用户] 异常: {e}", flush=True)
    return None


def _persist_user_id(user_id: str):
    """将自动注册产生的 user_token 持久化到全局配置 ~/.qbi/config.yaml。

    写入全局配置而非包内 default_config.yaml，因为后者随技能包更新覆盖。
    试用凭证自动注册产生的 user_token 使用 force=True 强制写入，
    不受 save_global_property 开关限制。
    """
    try:
        persist_to_global_config("user_token", user_id, force=True)
        print(f"[用户注册] user_token 已写入 {GLOBAL_CONFIG_PATH}", flush=True)
    except Exception as e:
        print(f"[用户注册] 警告：无法将 user_token 写入 {GLOBAL_CONFIG_PATH}: {e}", flush=True)


def _auto_provision_user(config: dict) -> str:
    """
    未配置 user_token 时的自动注册流程：
    1. 生成 accountId（设备 ID 的 MD5）和 accountName（主机名）
    2. 先通过 accountName 查询用户是否已在组织中，已存在则直接复用 userId（兼容历史用户）
    3. 不存在则调用 addUser 添加到组织
    4. 将 userId 写入全局配置 ~/.qbi/config.yaml（不受技能包更新影响）
    """
    account_id = _get_device_account_id()
    hostname = _get_device_hostname()
    print(f"[用户注册] 未配置 user_token，开始自动注册 (accountId={account_id}, accountName={hostname})", flush=True)

    existing_uid = _query_user_by_account(hostname, config)
    if existing_uid:
        print(f"[用户注册] 通过 accountName 查询到已有用户，userId={existing_uid}", flush=True)
        _persist_user_id(existing_uid)
        return existing_uid

    print(f"[用户注册] 未查询到已有用户，正在添加 (accountName={hostname}) ...", flush=True)
    uid = _add_user_to_org(account_id, hostname, config)
    if uid:
        print(f"[用户注册] 添加成功，userId={uid}", flush=True)
        _persist_user_id(uid)
        return uid

    if _last_add_user_code in (_ALREADY_IN_ORG_CODE, _NICK_EXISTS_CODE):
        print(f"[用户注册] 添加返回已存在（错误码={_last_add_user_code}），重新查询 userId ...", flush=True)
        queried_uid = _query_user_by_account(hostname, config)
        if queried_uid:
            print(f"[用户注册] 查询成功，userId={queried_uid}", flush=True)
            _persist_user_id(queried_uid)
            return queried_uid

    suffixed_name = f"{hostname}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=5))}"
    print(f"[用户注册] 使用带后缀名称重试 (accountName={suffixed_name}) ...", flush=True)
    uid = _add_user_to_org(account_id, suffixed_name, config)
    if uid:
        print(f"[用户注册] 重试添加成功，userId={uid}", flush=True)
        _persist_user_id(uid)
        return uid

    raise ValueError(
        "自动注册用户失败，请手动在 ~/.qbi/config.yaml 中配置 user_token。"
        "可通过 Quick BI 管理控制台获取用户 ID。"
    )


# ---------------------------------------------------------------------------
# OpenAPI 签名
# ---------------------------------------------------------------------------

def build_signature(
    method: str,
    uri: str,
    params: Optional[Dict[str, Any]],
    access_id: str,
    access_key: str,
    nonce: str,
    timestamp: str,
) -> str:
    if not params:
        request_query_string = ""
    else:
        parts: List[str] = []
        for key in sorted(params):
            value = params[key]
            if value is None or value == "":
                continue
            parts.append(f"{key}={value}")
        request_query_string = "\n" + "&".join(parts) if parts else ""

    request_headers = (
        "\nX-Gw-AccessId:" + access_id
        + "\nX-Gw-Nonce:" + nonce
        + "\nX-Gw-Timestamp:" + timestamp
    )
    string_to_sign = method.upper() + "\n" + uri + request_query_string + request_headers
    encoded_string = parse.quote(string_to_sign, "")
    digest = hmac.new(
        access_key.encode("utf-8"),
        encoded_string.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_request_headers(
    method: str,
    uri: str,
    params: Optional[Dict[str, Any]],
    *,
    content_type: Optional[str] = None,
    config: Optional[dict] = None,
) -> Dict[str, str]:
    config = config or read_config()
    access_id = str(config["api_key"])
    access_key = str(config["api_secret"])
    nonce = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))

    signature = build_signature(method, uri, params, access_id, access_key, nonce, timestamp)

    headers = {
        "X-Gw-AccessId": access_id,
        "X-Gw-Nonce": nonce,
        "X-Gw-Timestamp": timestamp,
        "X-Gw-Signature": signature,
        "X-Gw-Debug": "true",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


# ---------------------------------------------------------------------------
# HTTP 请求
# ---------------------------------------------------------------------------

def request_openapi(
    method: str,
    uri: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    sign_params: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    config: Optional[dict] = None,
    quiet: bool = False,
) -> requests.Response:
    """调用 Quick BI OpenAPI（非流式）。

    Args:
        files: multipart 文件上传字典（与 requests 的 files 参数一致）。
        quiet: 为 True 时仅打印请求方法和状态码，不打印详细请求体与响应体（用于高频轮询场景）。
    """
    config = config or read_config()
    server_domain = get_server_domain(config)
    method = method.upper()
    url = server_domain + uri

    if sign_params is None and method == "GET":
        sign_params = params
    if sign_params is None and form_data is not None:
        sign_params = form_data

    content_type: Optional[str] = None
    if json_body is not None:
        content_type = "application/json"
    elif files is not None:
        content_type = None  # requests 自动设置 multipart boundary
    elif form_data is not None:
        content_type = "application/x-www-form-urlencoded"

    headers = build_request_headers(method, uri, sign_params, content_type=content_type, config=config)
    headers["origin"] = server_domain

    kwargs: Dict[str, Any] = {"method": method, "url": url, "headers": headers, "timeout": timeout}

    if method == "GET":
        kwargs["params"] = params
    elif files is not None:
        kwargs["data"] = params
        kwargs["files"] = files
    elif json_body is not None:
        kwargs["json"] = json_body
    elif form_data is not None:
        kwargs["data"] = form_data
    else:
        kwargs["params"] = params

    if not quiet:
        print(f"\n>>> API Request: {method} {uri}", flush=True)

    if _should_skip_ssl(url):
        kwargs["verify"] = False

    resp = requests.request(**kwargs)

    if not quiet and not resp.ok:
        body = ""
        try:
            body = resp.text[:2000]
        except Exception:
            pass
        print(f"\n<<< API Response: {resp.status_code}", flush=True)

    if not resp.ok:
        body = ""
        try:
            body = resp.text[:2000]
        except Exception:
            pass
        check_trial_expired(body)
        raise requests.HTTPError(
            f"HTTP {resp.status_code} {resp.reason} for {method} {uri}\n响应体: {body}",
            response=resp,
        )
    return resp


def request_openapi_stream(
    uri: str,
    *,
    json_body: Dict[str, Any],
    config: Optional[dict] = None,
    timeout: int = 600,
) -> Generator[str, None, None]:
    """
    POST 流式请求，返回 SSE 事件文本块的生成器。
    每次 yield 一个完整的 SSE 事件块（以 ``\\n\\n`` 分隔）。
    """
    config = config or read_config()
    server_domain = get_server_domain(config)
    url = server_domain + uri

    headers = build_request_headers("POST", uri, None, content_type="application/json", config=config)
    headers["origin"] = server_domain
    headers["Accept"] = "text/event-stream"
    headers["Accept-Encoding"] = "identity"
    headers["Cache-Control"] = "no-cache"

    verify = not _should_skip_ssl(url)
    with requests.post(url, json=json_body, headers=headers, stream=True, timeout=timeout, verify=verify) as resp:
        if not resp.ok:
            body = ""
            try:
                body = resp.text[:2000]
            except Exception:
                pass
            check_trial_expired(body)
            raise requests.HTTPError(
                f"HTTP {resp.status_code} {resp.reason} for POST {uri}\n响应体: {body}",
                response=resp,
            )
        resp.encoding = "utf-8"
        buffer = ""
        for line in resp.iter_lines(decode_unicode=True):
            if line is None:
                continue
            buffer += line + "\n"
            # SSE 事件以空行分隔（即连续两个换行）
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)
                event_block = event_block.strip()
                if event_block:
                    yield event_block
        if buffer.strip():
            yield buffer.strip()


# ---------------------------------------------------------------------------
# SSE 事件解析
# ---------------------------------------------------------------------------

def parse_sse_event(raw_event: str) -> Dict[str, Any]:
    """
    解析单个 SSE 事件块，返回 data 中的 JSON 字典。

    事件格式示例::

        event:message
        data:{"data":"xxx","type":"reasoning"}
    """
    lines = raw_event.strip().split("\n")
    data_content = ""
    for line in lines:
        if line.startswith("data:"):
            data_content = line[len("data:"):]
            break

    if not data_content:
        return {}

    try:
        return json.loads(data_content)
    except json.JSONDecodeError:
        try:
            repaired = data_content.replace('\\"', '"').replace('\\\\', '\\')
            return json.loads(repaired)
        except json.JSONDecodeError:
           return {"raw": data_content}


# ---------------------------------------------------------------------------
# 报告模块公共工具（从 quickbi-smartq-data-report 迁移）
# ---------------------------------------------------------------------------

REPORT_URL_PATH_TEMPLATE = "/copilot/qreportReplay?caseId={chat_id}"
UPLOAD_CHAT_TYPE = "manus"
DEFAULT_POLL_INTERVAL_SECONDS = 10.0
DEFAULT_MAX_POLL_SECONDS = 30 * 60
SUPPORTED_UPLOAD_SUFFIXES = {".doc", ".docx", ".xls", ".xlsx", ".csv"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024


def validate_upload_file(file_path: str) -> Path:
    """校验上传文件类型与大小。"""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"不是有效文件：{path}")
    if path.suffix.lower() not in SUPPORTED_UPLOAD_SUFFIXES:
        raise ValueError(
            f"不支持的文件类型：{path.suffix}，仅支持 doc/docx/xls/xlsx/csv"
        )
    file_size = path.stat().st_size
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            f"文件超过 10MB：{path.name}，当前大小 {file_size} 字节"
        )
    return path


def upload_reference_file(
    file_path: str,
    *,
    config: Optional[dict] = None,
) -> Dict[str, Any]:
    """上传单个文件并返回原始文件元数据。"""
    config = config or read_config()
    path = validate_upload_file(file_path)
    user_id = require_user_id(config)

    params = {"chatType": UPLOAD_CHAT_TYPE, "userId": user_id}
    with path.open("rb") as file_handle:
        upload_files_dict = {"file": (path.name, file_handle)}
        response = request_openapi(
            "POST",
            "/openapi/v2/qreport/uploadReferenceFile",
            params=params,
            files=upload_files_dict,
            sign_params=None,
            timeout=60,
            config=config,
        )

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError(f"上传文件接口返回了非 JSON 响应：{response.text}") from exc

    if not isinstance(result, dict):
        raise ValueError(f"上传文件接口返回结构异常：{result}")

    data = result.get("data", result)
    if isinstance(data, dict) and data.get("fileId"):
        result = data

    if not result.get("fileId") or not result.get("fileName") or not result.get("fileType"):
        raise ValueError(f"上传文件接口未返回完整文件信息：{result}")

    return result


def resource_from_reference_file(reference_file: Dict[str, Any]) -> Dict[str, str]:
    """将上传结果映射为会话所需的 resources 结构。"""
    return {
        "id": str(reference_file.get("fileId", "")),
        "title": str(reference_file.get("fileName", "")),
        "type": str(reference_file.get("fileType", "")),
    }


def build_resources(reference_files: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """批量把上传结果映射为 resources 列表。"""
    return [resource_from_reference_file(item) for item in reference_files]


def normalize_resources(resources: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """兼容上传结果和已映射 resources 两种输入。"""
    normalized: List[Dict[str, str]] = []
    for item in resources or []:
        if {"id", "title", "type"}.issubset(item.keys()):
            normalized.append(
                {
                    "id": str(item["id"]),
                    "title": str(item["title"]),
                    "type": str(item["type"]),
                }
            )
        elif {"fileId", "fileName", "fileType"}.issubset(item.keys()):
            normalized.append(resource_from_reference_file(item))
        else:
            raise ValueError(f"资源格式不正确：{item}")
    return normalized


def _parse_running_task_response(text: str) -> Optional[Dict[str, str]]:
    """解析"运行中任务"的返回格式。"""
    pattern = r"当前用户已有运行中的任务.*问题[：:]\s*(.+?)[，,]\s*chatId[：:]\s*([a-zA-Z0-9\-]+)"
    match = re.search(pattern, text)
    if match:
        return {
            "question": match.group(1).strip(),
            "chatId": match.group(2).strip(),
            "message": text,
        }
    return None


def normalize_string_response(response_text: str, fallback: str) -> str:
    """把接口返回值规范为纯字符串；非字符串结果回退到 fallback。"""
    text = response_text.strip()
    if not text:
        return fallback
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        normalized = text.strip('"').strip("'")
        return normalized if normalized else fallback
    if isinstance(parsed, str):
        normalized = parsed.strip()
        return normalized if normalized else fallback
    return fallback


_FILE_TYPE_ICON_MAP = {
    "doc": "word",
    "docx": "word",
    "xls": "excel",
    "xlsx": "excel",
    "csv": "excel",
    "pdf": "pdf",
}


def _build_attachment(
    resources: List[Dict[str, str]],
    upload_results: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """根据上传结果构建 attachment JSON 字符串。"""
    files_list: List[Dict[str, Any]] = []
    if upload_results:
        for item in upload_results:
            file_id = str(item.get("fileId", ""))
            file_type = str(item.get("fileType", ""))
            file_name = str(item.get("fileName", ""))
            icon_type = _FILE_TYPE_ICON_MAP.get(file_type, file_type)
            ext = f".{file_type}" if file_type else ""
            files_list.append({
                "fileId": file_id,
                "fileType": file_type,
                "iconType": icon_type,
                "file": {"name": f"{file_name}{ext}"},
                "fileName": file_name,
            })
    elif resources:
        for res in resources:
            file_id = res.get("id", "")
            file_type = res.get("type", "")
            file_name = res.get("title", "")
            icon_type = _FILE_TYPE_ICON_MAP.get(file_type, file_type)
            ext = f".{file_type}" if file_type else ""
            files_list.append({
                "fileId": file_id,
                "fileType": file_type,
                "iconType": icon_type,
                "file": {"name": f"{file_name}{ext}"},
                "fileName": file_name,
            })

    attachment_obj = {
        "resource": {
            "files": files_list,
            "pages": [],
            "cubes": [],
            "dashboardFiles": [],
        },
        "useOnlineSearch": True,
    }
    return json.dumps(attachment_obj, ensure_ascii=False)


def format_report_url(chat_id: str, config: Optional[dict] = None) -> str:
    """拼出最终回放链接，域名从 config.server_domain 动态获取。"""
    config = config or read_config()
    server_domain = get_server_domain(config)
    return server_domain + REPORT_URL_PATH_TEMPLATE.format(chat_id=chat_id)


def create_report_chat(
    question: str,
    *,
    resources: Optional[Sequence[Dict[str, Any]]] = None,
    upload_results: Optional[Sequence[Dict[str, Any]]] = None,
    chat_id: Optional[str] = None,
    message_id: Optional[str] = None,
    config: Optional[dict] = None,
) -> Dict[str, Any]:
    """创建小Q报告会话。

    当接口返回"当前用户已有运行中的任务"时，自动切换至该任务并返回对应 chatId。
    """
    config = config or read_config()
    chat_id = chat_id or str(uuid.uuid4())
    message_id = message_id or str(uuid.uuid4())
    oapi_user_id = require_user_id(config)
    server_domain = get_server_domain(config)

    normalized_resources = normalize_resources(resources)

    payload: Dict[str, Any] = {
        "async": True,
        "chatId": chat_id,
        "messageId": message_id,
        "oapiUserId": oapi_user_id,
        "reGenerate": True,
        "needReplay": True,
        "userQuestion": question,
        "needWebSearch": True,
        "autoAcceptedPlan": True,
        "runningBySkill": True,
        "resources": normalized_resources if normalized_resources else [],
        "interruptFeedback": "",
        "messages": [
            {
                "role": "user",
                "content": question,
            }
        ],
        "attachment": _build_attachment(normalized_resources, upload_results),
        "bizArgs": {
            "qbiHost": server_domain,
        },
    }

    response = request_openapi(
        "POST",
        "/openapi/v2/smartq/createQreportChat",
        json_body=payload,
        sign_params=None,
        timeout=60,
        config=config,
    )

    response_text = response.text.strip()

    running_task = _parse_running_task_response(response_text)
    if running_task:
        existing_chat_id = running_task["chatId"]
        existing_question = running_task["question"]
        print(f"\n{'=' * 60}", flush=True)
        print(f"[运行中任务] 检测到当前用户已有运行中的任务", flush=True)
        print(f"[运行中任务] 已有任务问题：{existing_question}", flush=True)
        print(f"[运行中任务] 已有任务chatId：{existing_chat_id}", flush=True)
        print(f"[运行中任务] 将使用上述 chatId 进行后续轮询", flush=True)
        print(f"{'=' * 60}\n", flush=True)
        return {
            "chatId": existing_chat_id,
            "messageId": message_id,
            "reportUrl": format_report_url(existing_chat_id, config),
            "request": payload,
            "response": response_text,
            "statusCode": response.status_code,
            "runningTask": True,
            "runningTaskInfo": running_task,
        }

    final_chat_id = normalize_string_response(response_text, chat_id)

    return {
        "chatId": final_chat_id,
        "messageId": message_id,
        "reportUrl": format_report_url(final_chat_id, config),
        "request": payload,
        "response": final_chat_id,
        "statusCode": response.status_code,
    }


def fetch_report_result(chat_id: str, *, config: Optional[dict] = None) -> str:
    """获取当前 chatId 的累积结果（轮询场景静默）。"""
    config = config or read_config()
    user_id = require_user_id(config)
    query_params = {"chatId": chat_id, "userId": user_id}
    response = request_openapi(
        "GET",
        "/openapi/v2/smartq/qreportChatData",
        params=query_params,
        sign_params=query_params,
        timeout=60,
        config=config,
        quiet=True,
    )
    return response.text


def _decode_data_field(item: Dict[str, Any]) -> Dict[str, Any]:
    """对单个事件的 data 字段做二次 JSON 解析，填充 parsedData。"""
    event = dict(item)
    data_val = event.get("data")
    if isinstance(data_val, str) and data_val.strip():
        try:
            event["parsedData"] = json.loads(data_val)
        except json.JSONDecodeError:
            event["parsedData"] = data_val
    else:
        event["parsedData"] = data_val
    return event


def _parse_json_array_events(arr: list) -> List[Dict[str, Any]]:
    """将 JSON 数组中的每个元素解码为事件。"""
    return [_decode_data_field(item) for item in arr if isinstance(item, dict)]


def parse_report_events(raw_text: str) -> List[Dict[str, Any]]:
    """解析 qreportChatData 返回结果。"""
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    try:
        parsed = json.loads(text)

        if isinstance(parsed, dict):
            inner = parsed.get("data")
            if isinstance(inner, str) and inner.strip():
                try:
                    inner_parsed = json.loads(inner)
                    if isinstance(inner_parsed, list):
                        return _parse_json_array_events(inner_parsed)
                except json.JSONDecodeError:
                    pass
            elif isinstance(inner, list):
                return _parse_json_array_events(inner)

        if isinstance(parsed, list):
            return _parse_json_array_events(parsed)
    except json.JSONDecodeError:
        pass

    events: List[Dict[str, Any]] = []
    blocks = re.split(r"\r?\n\r?\n", text)
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        data_lines: List[str] = []
        for line in lines:
            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())

        if not data_lines:
            continue

        raw_data = "\n".join(data_lines)
        try:
            outer = json.loads(raw_data)
        except json.JSONDecodeError:
            events.append({"data": raw_data, "type": "unknown", "parsedData": raw_data})
            continue

        if isinstance(outer, dict):
            events.append(_decode_data_field(outer))

    return events


def clean_text_fragment(text: str) -> str:
    """把 HTML 片段转成便于终端阅读的纯文本。"""
    if not text:
        return ""
    cleaned = unescape(text)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</p\s*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<p[^>]*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<li[^>]*>", "- ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</li>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def truncate_text(text: str, limit: int = 800) -> str:
    """截断长文本，避免终端输出过长。"""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


_FUNCTION_LABEL = {
    "thinking": "思考中...",
    "learn": "文件学习",
    "refuse": "拒识",
    "mainText": "规划步骤",
    "interrupt": "等待确认",
}

_SKIP_TYPES = {"heartbeat", "locale", "check", "time"}


def _normalize_streaming_text(text: str) -> str:
    """修复 SSE 流式传输造成的文本断行。"""
    if not text:
        return text
    text = re.sub(r'\*\n\*', '**', text)
    text = re.sub(
        r'(?<=[^。.！!？?\n:：;；\)）\]】])\n(?=[^\n\s*#\-\d（(【\[])',
        '',
        text,
    )
    return text


def _streaming_content(events: List[Dict[str, Any]]) -> str:
    """从事件中提取流式文本内容并修复 SSE 断行。"""
    return _normalize_streaming_text(clean_text_fragment(_collect_content(events)))


def _event_group_key(event: Dict[str, Any]) -> Tuple[str, str]:
    """返回 (type, function) 用于分组。"""
    etype = event.get("type", "")
    pd = event.get("parsedData")
    func = pd.get("function", "") if isinstance(pd, dict) else ""
    return (etype, func)


def _collect_content(events: List[Dict[str, Any]]) -> str:
    """从一组事件中提取并拼接 content 字段。"""
    parts: List[str] = []
    for e in events:
        pd = e.get("parsedData")
        if isinstance(pd, dict):
            c = pd.get("content", "")
            if c:
                parts.append(c)
        elif isinstance(pd, str) and pd:
            parts.append(pd)
        else:
            raw = e.get("data", "")
            if isinstance(raw, str) and raw:
                parts.append(raw)
    return "".join(parts)


def group_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将连续同 (type, function) 的事件合并为分组。"""
    if not events:
        return []

    groups: List[Dict[str, Any]] = []
    cur_key = _event_group_key(events[0])
    cur_events: List[Dict[str, Any]] = [events[0]]

    for event in events[1:]:
        key = _event_group_key(event)
        if key == cur_key:
            cur_events.append(event)
        else:
            groups.append({
                "type": cur_key[0],
                "function": cur_key[1],
                "events": cur_events,
            })
            cur_key = key
            cur_events = [event]

    groups.append({
        "type": cur_key[0],
        "function": cur_key[1],
        "events": cur_events,
    })
    return groups


def summarize_structured_chart(parsed_payload: Dict[str, Any]) -> List[str]:
    """生成结构化图表的终端摘要。"""
    chart = parsed_payload.get("chart") or {}
    if isinstance(chart, list):
        data_list = chart
    elif isinstance(chart, dict):
        data_list = chart.get("dataList") or []
    else:
        data_list = []
    if not data_list:
        return ["[structuredChart] 空结果"]

    lines: List[str] = []
    for index, item in enumerate(data_list, start=1):
        title = item.get("title") or item.get("chartType") or item.get("id") or f"chart-{index}"
        rows = item.get("data") or []
        lines.append(f"[structuredChart] {index}. {title} | rows={len(rows)}")
        if rows:
            sample = json.dumps(rows[0], ensure_ascii=False)
            lines.append(f"  sample: {truncate_text(sample, 500)}")
    return lines


def summarize_unstructured_chart(parsed_payload: Dict[str, Any]) -> List[str]:
    """生成非结构化图表/大纲的终端摘要。"""
    chart = parsed_payload.get("chart") or []
    if not chart:
        return ["[unStructuredChart] 空结果"]

    lines: List[str] = []
    for index, item in enumerate(chart, start=1):
        content = item.get("data") or item.get("content") or ""
        title = item.get("title") or item.get("purpose") or item.get("id") or f"chunk-{index}"
        lines.append(f"[unStructuredChart] {index}. {title}")
        if content:
            lines.append(truncate_text(clean_text_fragment(str(content)), 800))
    return lines


def _render_token_info(parsed_data: Dict[str, Any], label: str) -> Tuple[List[str], Dict[str, Any]]:
    """提取 token 用量并格式化输出。"""
    info = {
        "promptTokens": parsed_data.get("promptTokens"),
        "totalTokens": parsed_data.get("totalTokens"),
        "completionTokens": parsed_data.get("completionTokens"),
    }
    line = (
        f"[{label}] "
        f"prompt={info['promptTokens']} total={info['totalTokens']} "
        f"completion={info['completionTokens']}"
    )
    return [line], info


_SUBSTEP_LABEL = {
    "onlineSearchResult": "联网搜索结果",
    "knowledgeBaseResult": "知识库结果",
}


def _render_substep(parsed_data: Dict[str, Any]) -> List[str]:
    """渲染 subStep 事件。"""
    if not isinstance(parsed_data, dict):
        return [f"  [subStep] {truncate_text(str(parsed_data), 1000)}"]

    function_name = parsed_data.get("function", "subStep")
    label = _SUBSTEP_LABEL.get(function_name, function_name)
    prefix = f"[subStep:{label}]" if label else "[subStep]"
    raw_lines: List[str] = []

    if function_name == "onlineSearchResult":
        web_items = parsed_data.get("webItems") or []
        raw_lines.append(f"{prefix} {len(web_items)} 条网页结果")
        for idx, item in enumerate(web_items[:3], 1):
            title = item.get("title", "")
            link = item.get("link", "")
            host = item.get("hostName", "")
            display_title = truncate_text(title, 100)
            if link:
                raw_lines.append(f"  {idx}. [{display_title}]({link}) — {host}")
            elif host:
                raw_lines.append(f"  {idx}. {display_title} — {host}")
            else:
                raw_lines.append(f"  {idx}. {display_title}")
    elif function_name == "knowledgeBaseResult":
        kb_items = parsed_data.get("knowledgeItems") or []
        raw_lines.append(f"{prefix} {len(kb_items)} 条知识库结果")
        for idx, item in enumerate(kb_items[:3], 1):
            name = item.get("resourceName", "")
            raw_lines.append(f"  {idx}. {truncate_text(name, 120)}")
    elif function_name == "structuredChart":
        raw_lines.extend(summarize_structured_chart(parsed_data))
    elif function_name == "unStructuredChart":
        raw_lines.extend(summarize_unstructured_chart(parsed_data))
    elif function_name == "usedToken":
        return []
    elif function_name == "text":
        content = parsed_data.get("content", "")
        if content:
            cleaned = truncate_text(_normalize_streaming_text(clean_text_fragment(str(content))), 1500)
            raw_lines.append(f"{prefix} {cleaned}")
        else:
            raw_lines.append(prefix)
    else:
        content = parsed_data.get("content", "")
        if content:
            raw_lines.append(prefix)
            raw_lines.append(truncate_text(clean_text_fragment(str(content)), 1500))
        else:
            raw_lines.append(prefix)

    return [f"  {line}" for line in raw_lines]


def render_event_group(
    group: Dict[str, Any],
    continuation: bool = False,
) -> Tuple[List[str], bool, Optional[Dict[str, Any]], Optional[str]]:
    """将一个事件分组渲染为终端输出。

    Returns: (lines, finished, token_info, error_msg)
    """
    etype = group["type"]
    func = group["function"]
    events = group["events"]
    lines: List[str] = []
    finished = False
    token_info: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None

    if etype in _SKIP_TYPES:
        return lines, finished, token_info, error_msg

    if etype == "trace":
        text = str(_collect_content(events)).strip()
        if text and not continuation:
            lines.append(f"[trace] {text}")
        return lines, finished, token_info, error_msg

    if etype == "error":
        error_msg = clean_text_fragment(_collect_content(events))
        if not error_msg:
            error_msg = "未知错误"
        lines.append(f"[error] {error_msg}")
        finished = True
        return lines, finished, token_info, error_msg

    if etype == "plan":
        if func == "usedToken":
            return lines, finished, token_info, error_msg
        label = _FUNCTION_LABEL.get(func, func or "plan")
        content = _streaming_content(events)
        if content:
            if not continuation:
                lines.append(label)
            lines.append(content)
        return lines, finished, token_info, error_msg

    if etype == "schedule":
        if func == "usedToken":
            pass
        else:
            content = _streaming_content(events)
            if content:
                lines.append(f"[schedule] {truncate_text(content, 1500)}")
        return lines, finished, token_info, error_msg

    if etype == "step":
        for e in events:
            pd = e.get("parsedData")
            if not isinstance(pd, dict):
                continue
            f = pd.get("function", "")
            if f == "usedToken":
                continue
            else:
                title = pd.get("title", "")
                desc = pd.get("desc", "")
                lines.append(f"Step: {title}" if title else "Step")
                if desc and desc != title:
                    lines.append(f"  {desc}")
        return lines, finished, token_info, error_msg

    if etype == "actionThinking":
        content = _streaming_content(events)
        if content:
            if not continuation:
                lines.append("思考中...")
            lines.append(content)
        return lines, finished, token_info, error_msg

    if etype == "subStep":
        for e in events:
            pd = e.get("parsedData")
            if isinstance(pd, dict):
                lines.extend(_render_substep(pd))
        return lines, finished, token_info, error_msg

    if etype == "qreport":
        if func in ("qreportUsedToken", "usedToken"):
            pd = events[-1].get("parsedData", {})
            if isinstance(pd, dict):
                _, token_info = _render_token_info(pd, func)
            if func == "qreportUsedToken":
                finished = True
            return lines, finished, token_info, error_msg

        if func == "onlineSearchResult":
            for e in events:
                pd = e.get("parsedData")
                if isinstance(pd, dict):
                    web_items = pd.get("webItems") or []
                    lines.append(f"[qreport:联网搜索结果] {len(web_items)} 条网页结果")
                    for idx, item in enumerate(web_items[:3], 1):
                        title = item.get("title", "")
                        link = item.get("link", "")
                        host = item.get("hostName", "")
                        display_title = truncate_text(title, 100)
                        if link:
                            lines.append(f"  {idx}. [{display_title}]({link}) — {host}")
                        elif host:
                            lines.append(f"  {idx}. {display_title} — {host}")
                        else:
                            lines.append(f"  {idx}. {display_title}")
            return lines, finished, token_info, error_msg

        if func == "structuredChart":
            for e in events:
                pd = e.get("parsedData")
                if isinstance(pd, dict):
                    lines.extend(summarize_structured_chart(pd))
            return lines, finished, token_info, error_msg

        if func == "unStructuredChart":
            for e in events:
                pd = e.get("parsedData")
                if isinstance(pd, dict):
                    lines.extend(summarize_unstructured_chart(pd))
            return lines, finished, token_info, error_msg

        content = _streaming_content(events)
        if content and not continuation:
            label = func or "qreport"
            lines.append(f"[qreport:{label}] {truncate_text(content, 2000)}")
        return lines, finished, token_info, error_msg

    if etype == "finish":
        return lines, finished, token_info, error_msg

    content = _streaming_content(events)
    if content:
        lines.append(f"[{etype or 'message'}] {truncate_text(content, 1000)}")
    return lines, finished, token_info, error_msg


def poll_report_result(
    chat_id: str,
    *,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    max_wait_seconds: int = DEFAULT_MAX_POLL_SECONDS,
    show_progress: bool = True,
    config: Optional[dict] = None,
) -> Dict[str, Any]:
    """轮询小Q报告结果，直到 qreportUsedToken 或 error 出现。"""
    config = config or read_config()
    start_time = time.time()
    processed_events = 0

    result: Dict[str, Any] = {
        "chatId": chat_id,
        "reportUrl": None,
        "finished": False,
        "error": None,
        "eventCount": 0,
        "tokenInfo": None,
    }

    prev_group_key: Tuple[str, str] = ("", "")
    prev_output_key: Tuple[str, str] = ("", "")
    last_new_event_time = time.time()
    idle_hint_printed = False
    _IDLE_HINT_SECONDS = 9.0

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            raise TimeoutError(f"轮询超时：已等待 {max_wait_seconds // 60} 分钟")

        raw_text = fetch_report_result(chat_id, config=config)
        events = parse_report_events(raw_text)

        if processed_events > len(events):
            processed_events = 0

        new_events = events[processed_events:]
        if not new_events:
            if (
                show_progress
                and not idle_hint_printed
                and time.time() - last_new_event_time >= _IDLE_HINT_SECONDS
            ):
                print(flush=True)
                print("结果生成中，请耐心等待", flush=True)
                print(flush=True)
                idle_hint_printed = True
            time.sleep(poll_interval)
            continue

        last_new_event_time = time.time()
        idle_hint_printed = False

        groups = group_events(new_events)
        batch_finished = False
        saw_qreport_used_token = False

        for idx, grp in enumerate(groups):
            grp_key = (grp["type"], grp["function"])
            is_continuation = (idx == 0 and grp_key == prev_group_key)
            lines, finished, token_info, error_msg = render_event_group(grp, continuation=is_continuation)

            if show_progress and lines:
                curr_key = (grp["type"], grp["function"])
                if prev_output_key[0] and curr_key != prev_output_key:
                    if not (prev_output_key[0] == "step" and curr_key[0] == "subStep"):
                        if not (prev_output_key[0] == "subStep" and curr_key[0] == "subStep"):
                            print(flush=True)
                for line in lines:
                    print(line, flush=True)
                prev_output_key = curr_key

            result["eventCount"] += len(grp["events"])
            if token_info:
                result["tokenInfo"] = token_info
            if error_msg:
                result["error"] = error_msg
            if finished:
                batch_finished = True
                if (
                    not error_msg
                    and grp["type"] == "qreport"
                    and grp["function"] == "qreportUsedToken"
                ):
                    saw_qreport_used_token = True

        if groups:
            prev_group_key = (groups[-1]["type"], groups[-1]["function"])
        processed_events = len(events)

        if batch_finished:
            result["finished"] = True
            success_with_url = saw_qreport_used_token and result.get("error") is None
            if success_with_url:
                result["reportUrl"] = format_report_url(chat_id, config)
            else:
                result["reportUrl"] = None
            if show_progress:
                print(flush=True)
                if result.get("error"):
                    print(f"报告生成失败：{result['error']}", flush=True)
                elif success_with_url and result.get("reportUrl"):
                    url = result["reportUrl"]
                    print("📊 报告链接", flush=True)
                    print(f"在线数据报告：[点击查看完整报告]({url})", flush=True)
            return result

        time.sleep(poll_interval)


def upload_files(
    file_paths: Sequence[str],
    *,
    config: Optional[dict] = None,
) -> Dict[str, Any]:
    """批量上传文件并返回上传结果和 resources 列表。"""
    config = config or read_config()
    upload_results = [upload_reference_file(path, config=config) for path in file_paths]
    resources = build_resources(upload_results)
    return {
        "uploadResults": upload_results,
        "resources": resources,
    }
