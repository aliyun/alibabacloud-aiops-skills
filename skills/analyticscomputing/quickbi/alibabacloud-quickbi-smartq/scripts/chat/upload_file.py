# -*- coding: utf-8 -*-
"""
文件上传脚本（步骤 1）：将 Excel/CSV 文件上传至 Quick BI 并获取 fileId。

用法：
    python scripts/upload_file.py /path/to/data.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

from common.utils import read_config, require_user_id, get_server_domain, build_request_headers, check_trial_expired, _should_skip_ssl

ALLOWED_EXTENSIONS = {"xls", "xlsx", "csv"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

MIME_MAP = {
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
}

UPLOAD_URI = "/openapi/v2/copilot/parse"


def validate_file(file_path: str):
    """校验文件格式和大小。"""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    ext = p.suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式 .{ext}，仅支持: {', '.join(ALLOWED_EXTENSIONS)}")
    size = p.stat().st_size
    if size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小 {size / 1024 / 1024:.1f}MB 超过限制 10MB")


def upload_file(file_path: str, *, config: Optional[dict] = None) -> dict:
    """
    调用 POST /openapi/v2/copilot/parse 上传文件并解析结构。
    返回接口响应 JSON（含 fileId）。
    """
    config = config or read_config()
    validate_file(file_path)

    p = Path(file_path)
    file_name = p.name
    ext = p.suffix.lower()
    content_type = MIME_MAP.get(ext, "application/octet-stream")

    server_domain = get_server_domain(config)
    url = server_domain + UPLOAD_URI

    user_id = require_user_id(config)
    form_data: Dict[str, str] = {
        "fileName": file_name,
        "isSave": "false",
        "fileId": "",
        "oApiUserId": user_id,
        "runningBySkill": "true",
    }

    headers = build_request_headers("POST", UPLOAD_URI, None, config=config)
    headers["origin"] = server_domain

    file_size = p.stat().st_size
    print(f"[文件上传] 请求: POST {url}", flush=True)
    print(f"[文件上传] 表单参数: {json.dumps(form_data, ensure_ascii=False)}", flush=True)
    print(f"[文件上传] 文件: name={file_name}, size={file_size / 1024:.1f}KB, contentType={content_type}", flush=True)

    with open(file_path, "rb") as f:
        files = {"file": (file_name, f, content_type)}
        resp = requests.post(url, headers=headers, data=form_data, files=files, timeout=120,
                              verify=not _should_skip_ssl(url))

    if not resp.ok:
        body = ""
        try:
            body = resp.text[:2000]
        except Exception:
            pass
        raise requests.HTTPError(
            f"HTTP {resp.status_code} {resp.reason} for POST {UPLOAD_URI}\n响应体: {body}",
            response=resp,
        )
    return resp.json()


def _is_success(result: dict) -> bool:
    val = result.get("success")
    if isinstance(val, bool):
        return val
    return str(val).lower() == "true"


def main():
    parser = argparse.ArgumentParser(description="上传 Excel/CSV 文件并获取 fileId")
    parser.add_argument("file", help="要上传的文件路径（支持 xls/xlsx/csv，≤10MB）")
    parser.add_argument("--workspace-dir", default=None, help="用户工作目录路径")
    args = parser.parse_args()

    if args.workspace_dir:
        from common.config_loader import set_workspace_dir
        set_workspace_dir(args.workspace_dir)

    config = read_config()
    user_id = require_user_id(config)
    print(f"[文件上传] userId={user_id}", flush=True)

    print(f"[文件上传] 正在上传: {args.file}", flush=True)
    result = upload_file(args.file, config=config)

    if _is_success(result):
        data = result.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {}
        file_id = data.get("fileId", "") if isinstance(data, dict) else ""
        print(f"[文件上传] 上传成功，fileId={file_id}", flush=True)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    else:
        print(f"[文件上传] 上传失败: {result.get('message', '未知错误')}", flush=True)
        print(f"[文件上传] 错误详情:", flush=True)
        print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
        check_trial_expired(result)
        sys.exit(1)


if __name__ == "__main__":
    main()
