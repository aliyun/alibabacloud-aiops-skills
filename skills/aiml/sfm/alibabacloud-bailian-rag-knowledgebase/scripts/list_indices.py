#!/usr/bin/env python3
"""
Query the list of Bailian knowledge bases via HTTPS API.
API Key is automatically retrieved via api_key.py.

Usage:
    python3 list_indices.py [page_number] [page_size]
"""

import json
import os
import secrets
import sys
import urllib.request
import urllib.error
from api_key import get_api_key

API_ENDPOINT = "https://dashscope.aliyuncs.com"
API_PATH = "/api/v1/indices/rag/index/list"
REQUEST_TIMEOUT_S = 15


def _get_user_agent() -> str:
    """Build User-Agent string with session-id from SKILL_SESSION_ID env var."""
    session_id = os.environ.get("SKILL_SESSION_ID", "")
    if not session_id:
        session_id = secrets.token_hex(16)
        os.environ["SKILL_SESSION_ID"] = session_id
    return f"AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase/{session_id}"


def validate_page_number(arg: str) -> int:
    try:
        num = int(arg)
    except (ValueError, TypeError):
        return 1
    if num < 1:
        return 1
    if num > 10000:
        raise ValueError("page_number must not exceed 10000")
    return num


def validate_page_size(arg: str) -> int:
    try:
        num = int(arg)
    except (ValueError, TypeError):
        return 10
    if num < 1:
        return 10
    if num > 100:
        raise ValueError("page_size must not exceed 100")
    return num


def main():
    page_number = validate_page_number(sys.argv[1]) if len(sys.argv) > 1 else 1
    page_size = validate_page_size(sys.argv[2]) if len(sys.argv) > 2 else 10

    api_key = get_api_key()

    url = f"{API_ENDPOINT}{API_PATH}?pipeline_name&page_number={page_number}&page_size={page_size}"

    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _get_user_agent(),
            "_source": "skill"
        },
        data=b"",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_json = json.loads(error_body)
        except json.JSONDecodeError:
            error_json = error_body
        print(json.dumps({"error": f"HTTP {e.code}", "detail": error_json}, indent=2))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(json.dumps({"error": f"Network request failed: {e.reason}"}, indent=2))
        sys.exit(1)
    except TimeoutError:
        print(json.dumps({"error": f"Request timeout ({REQUEST_TIMEOUT_S}s)"}, indent=2))
        sys.exit(1)

    rows = body.get("data", {}).get("rows", [])
    result = [
        {
            "id": row.get("id", ""),
            "name": row.get("name", ""),
            "description": row.get("description", ""),
        }
        for row in rows
    ]
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
