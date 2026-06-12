#!/usr/bin/env python3
"""
Retrieve information from a Bailian knowledge base via HTTPS API.
API Key is automatically retrieved via api_key.py.

Usage:
    python3 retrieve.py <index_id> <query> [top_n]
"""

import json
import os
import re
import secrets
import sys
import urllib.request
import urllib.error
from api_key import get_api_key

API_ENDPOINT = "https://dashscope.aliyuncs.com"
API_PATH = "/api/v1/indices/rag/index/retrieve"
REQUEST_TIMEOUT_S = 15


def _get_user_agent() -> str:
    """Build User-Agent string with session-id from SKILL_SESSION_ID env var."""
    session_id = os.environ.get("SKILL_SESSION_ID", "")
    if not session_id:
        session_id = secrets.token_hex(16)
        os.environ["SKILL_SESSION_ID"] = session_id
    return f"AlibabaCloud-Agent-Skills/alibabacloud-bailian-rag-knowledgebase/{session_id}"


def validate_index_id(arg: str) -> str:
    if not arg or not arg.strip():
        raise ValueError("index_id cannot be empty")
    arg = arg.strip()
    if len(arg) > 64:
        raise ValueError("index_id must not exceed 64 characters")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", arg):
        raise ValueError("index_id contains invalid characters; only letters, digits, hyphens and underscores are allowed")
    return arg


def validate_query(arg: str) -> str:
    if not arg or not arg.strip():
        raise ValueError("query cannot be empty")
    arg = arg.strip()
    if len(arg) > 2000:
        raise ValueError("query must not exceed 2000 characters")
    if re.search(r"[<>\{\}\[\]\$\|`;]", arg):
        raise ValueError("query contains invalid characters")
    return arg


def validate_top_n(arg: str) -> int:
    try:
        num = int(arg)
    except (ValueError, TypeError):
        return 5
    if num < 1:
        return 5
    if num > 20:
        raise ValueError("top_n must not exceed 20")
    return num


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 retrieve.py <index_id> <query> [top_n]", file=sys.stderr)
        sys.exit(1)

    index_id = validate_index_id(sys.argv[1])
    query = validate_query(sys.argv[2])
    top_n = validate_top_n(sys.argv[3]) if len(sys.argv) > 3 else 5

    api_key = get_api_key()

    payload = json.dumps({
        "query": query,
        "rerank_top_n": top_n,
        "dense_similarity_top_k": 100,
        "sparse_similarity_top_k": 100,
        "enable_reranking": True,
        "rerank": [{
            "model_name": "qwen3-rerank-hybrid",
            "rerank_mode": "similar",
        }],
        "index_id": index_id,
        "search_filters": []
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{API_ENDPOINT}{API_PATH}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": _get_user_agent(),
            "_source": "skill"
        },
        data=payload,
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

    # Extract chunks from response
    nodes = (
        body.get("data", {}).get("nodes")
        or body.get("nodes")
        or []
    )
    chunks = [
        {
            "content": n.get("text") or n.get("content", ""),
            "score": n.get("score", 0),
            "doc_name": n.get("metadata", {}).get("doc_name") or n.get("doc_name", ""),
            "title": n.get("metadata", {}).get("title") or n.get("title", ""),
        }
        for n in nodes
    ]

    print(json.dumps({"indexId": index_id, "chunks": chunks}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
