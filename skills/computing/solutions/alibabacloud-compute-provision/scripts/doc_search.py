#!/usr/bin/env python3
"""Alibaba Cloud documentation search.

Search help.aliyun.com for product documentation.
Returns titles, summaries, and links.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from common import USER_AGENT

SEARCH_URL = "https://help.aliyun.com/help/json/search.json"
PAGE_SIZE = 10
TIMEOUT = 15

PRODUCT_CATEGORY_IDS = {
    "ecs": 25365,
    "vpc": 27706,
    "fc": 2508973,
    "ack": 85222,
    "pai": 30347,
    "ros": 28850,
    "oss": 31815,
    "rds": 26090,
    "slb": 27537,
}


def search(
    keywords: str,
    product: str | None = None,
    category_id: int | None = None,
    page_size: int = PAGE_SIZE,
    page_num: int = 1,
) -> list[dict[str, str]]:
    """Search Alibaba Cloud documentation.

    Args:
        keywords: Search keywords.
        product: Product shortname (ecs, vpc, fc, ack, pai, etc.) for scoped search.
        category_id: Explicit category ID. Overrides product if both given.
        page_size: Results per page.
        page_num: Page number.

    Returns:
        List of dicts with 'title', 'content', 'url' keys.
    """
    if not keywords.strip():
        raise ValueError("keywords cannot be empty")

    cid = category_id
    if cid is None and product:
        cid = PRODUCT_CATEGORY_IDS.get(product.lower())

    params: dict[str, Any] = {
        "keywords": keywords,
        "topics": "DOCUMENT,PRODUCT",
        "language": "zh",
        "website": "cn",
        "pageSize": page_size,
        "pageNum": page_num,
    }
    if cid is not None:
        params["categoryId"] = cid

    query_string = urllib.parse.urlencode(params)
    url = f"{SEARCH_URL}?{query_string}"

    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", USER_AGENT)

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Search request failed: {e}")
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("Failed to parse search response")
        return []

    if not data.get("success"):
        print("Search API returned failure")
        return []

    documents = data.get("data", {}).get("documents", {})
    items = documents.get("data", [])
    total = documents.get("totalCount", 0)

    results = []
    for item in items:
        results.append({
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "url": item.get("url", ""),
        })

    print(f"Found {len(results)} documents (total {total}) for: {keywords}")
    return results


def search_and_format(
    keywords: str,
    product: str | None = None,
    category_id: int | None = None,
) -> str:
    """Search and return a formatted string for display."""
    results = search(keywords, product, category_id)
    if not results:
        return f"No documents found for: {keywords}"

    lines = []
    for i, item in enumerate(results, 1):
        lines.append(f"{i}. {item['title']}")
        if item["content"]:
            lines.append(f"   {item['content']}")
        if item["url"]:
            lines.append(f"   Link: {item['url']}")
        lines.append("")

    lines.append(f"Use web_fetch tool to read full document content if needed.")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: doc_search.py <keywords> [product]")
        print("  product: ecs, vpc, fc, ack, pai, ros, oss, rds, slb")
        print()
        print("Examples:")
        print("  doc_search.py 'RunInstances' ecs")
        print("  doc_search.py 'CreateFunction' fc")
        sys.exit(1)

    kw = sys.argv[1]
    prod = sys.argv[2] if len(sys.argv) > 2 else None
    output = search_and_format(kw, prod)
    print(output)
