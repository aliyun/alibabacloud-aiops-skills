#!/usr/bin/env python3
"""
Script to query resource types by keyword from Alibaba Cloud Resource Center.

This script helps you find resource type codes by searching across ResourceType,
ProductName, and ResourceTypeName fields. Results are printed as JSON on stdout.

Usage:
    python3 scripts/query-resource-types.py [keyword] [--language LANGUAGE]

Examples:
    # Query all resource types
    python3 scripts/query-resource-types.py

    # Query with keyword (case-insensitive)
    python3 scripts/query-resource-types.py ecs
    python3 scripts/query-resource-types.py vpc --language en-US

    # Example success output:
    # {"success":true,"language":"zh-CN","keyword":"ecs","count":1,"resourceTypes":[...]}
    JSON output (stdout, UTF-8):
    success (bool): true on API success; false on fetch/CLI failure (then also ``error``).
    language (str): Same as ``--language`` (only when success).
    keyword (str|null): Search keyword, or null when listing all types (only when success).
    count (int): Length of ``resourceTypes`` (only when success).
    resourceTypes (list[object]): Sorted matches; each object has:
        resourceType (str): Resource type code, e.g. ``ACS::ECS::Instance`` (maps to API ``ResourceType``).
        productName (str): Product display name (maps to API ``ProductName``).
        resourceTypeName (str): Resource type display name (maps to API ``ResourceTypeName``).
    hints (list[str], optional): Present when ``success`` and ``count == 0``; search tips.
    On failure: ``error`` (str) and optional ``checks`` (list[str]) for common fixes.

Note: Run from the skill's root directory.
"""

import sys
import json
import subprocess
import argparse
from typing import Optional, List, Dict, Tuple, Any


def fetch_resource_types(language: str = "zh-CN") -> Tuple[Optional[dict], Optional[str]]:
    """
    Run Aliyun CLI list-resource-types and return parsed JSON.

    Filtering by keyword is done in Python so all three fields
    (ResourceType, ProductName, ResourceTypeName) stay searchable.

    Args:
        language: Language for resource labels (e.g. 'zh-CN', 'en-US').

    Returns:
        (parsed JSON dict, None) on success, or (None, error message) on failure.
    """
    cmd = [
        "aliyun", "resourcecenter", "list-resource-types",
        "--accept-language", language,
        "--user-agent", "AlibabaCloud-Agent-Skills",
        "--query", "ProductName", "ResourceTypeName", "ResourceType",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            msg = result.stderr.strip() or f"aliyun CLI exited with code {result.returncode}"
            return None, f"CLI error: {msg}"

        return json.loads(result.stdout), None

    except FileNotFoundError:
        return None, (
            "'aliyun' CLI not found. Install Alibaba Cloud CLI and ensure it is on PATH."
        )
    except subprocess.TimeoutExpired:
        return None, "Command timed out after 60 seconds"
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e}"
    except Exception as e:
        return None, str(e)


def filter_resource_types(data: dict, keyword: str) -> List[Dict[str, str]]:
    """
    Filter resource types by keyword.

    Args:
        data: The API response containing resource types
        keyword: Search keyword (case-insensitive)

    Returns:
        List of dicts with keys resourceType, productName, resourceTypeName
    """
    keyword_lower = keyword.lower()
    matched: List[Dict[str, str]] = []

    resource_types = data.get("ResourceTypes", [])

    for rt in resource_types:
        resource_type = rt.get("ResourceType", "")
        product_name = rt.get("ProductName", "")
        type_name = rt.get("ResourceTypeName", "")

        if (
            keyword_lower in resource_type.lower()
            or keyword_lower in product_name.lower()
            or keyword_lower in type_name.lower()
        ):
            matched.append(
                {
                    "resourceType": resource_type,
                    "productName": product_name,
                    "resourceTypeName": type_name,
                }
            )

    return matched


def all_resource_types_as_records(data: dict) -> List[Dict[str, str]]:
    """Build resource type records from full API response (no keyword filter)."""
    return [
        {
            "resourceType": rt.get("ResourceType", ""),
            "productName": rt.get("ProductName", ""),
            "resourceTypeName": rt.get("ResourceTypeName", ""),
        }
        for rt in data.get("ResourceTypes", [])
    ]


def empty_result_hints(keyword: Optional[str]) -> List[str]:
    """Human-oriented hints when the result set is empty."""
    if keyword is None:
        return [
            "Retry with a different --language if needed",
        ]
    return [
        "Try different keywords (e.g., product abbreviations like ECS, VPC, OSS)",
        "Use English keywords for better matching",
        "Run with a broader keyword or omit keyword to list all types",
    ]


def emit_json(payload: dict) -> None:
    """Print JSON to stdout with UTF-8 support."""
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main():
    parser = argparse.ArgumentParser(
        description="Query resource types by keyword from Alibaba Cloud Resource Center (JSON output)"
    )
    parser.add_argument(
        "keyword",
        type=str,
        nargs="?",
        default=None,
        help="Search keyword for filtering resource types (optional, omit to query all types)",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="zh-CN",
        choices=["zh-CN", "en-US"],
        help="Language for resource information (default: zh-CN, options: zh-CN, en-US)",
    )

    args = parser.parse_args()

    data, err = fetch_resource_types(args.language)

    if err is not None:
        emit_json(
            {
                "success": False,
                "error": err,
                "checks": [
                    "Aliyun CLI is installed and configured",
                    "Resource Center service is enabled",
                    "Caller has proper permissions",
                ],
            },
        )
        sys.exit(1)

    if args.keyword:
        matched = filter_resource_types(data, args.keyword)
    else:
        matched = all_resource_types_as_records(data)

    matched.sort(key=lambda r: (r["resourceType"], r["productName"], r["resourceTypeName"]))

    payload: Dict[str, Any] = {
        "success": True,
        "language": args.language,
        "keyword": args.keyword,
        "count": len(matched),
        "resourceTypes": matched,
    }

    if not matched:
        payload["hints"] = empty_result_hints(args.keyword)

    emit_json(payload)


if __name__ == "__main__":
    main()
