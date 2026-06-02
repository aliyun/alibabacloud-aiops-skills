#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build PDS SearchFile API query string.

Combines scalar query JSON and semantic query JSON into the SearchFile API query string.
Supports recursive parsing of nested query conditions and merging modality/category conditions.

Usage:
    python build_query.py --scalar-json '<json>' --semantic-json '<json>'
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional, List, Set, Tuple

from get_scalar_query_prompt import field_schema


def _escape_value(value: str) -> str:
    """Escape special characters (backslash and double quotes) in query strings"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_value(field: str, value: str) -> str:
    """
    Format value based on field type.

    Returns quoted string for string/date types, unquoted for long/boolean.
    """
    field_info = field_schema.get(field.lower(), {})
    field_type = field_info.get("type", "string")

    if field_type in ("long", "boolean"):
        return str(value)

    escaped = _escape_value(str(value))
    return f'"{escaped}"'


def _parse_query_recursive(query: Dict[str, Any]) -> Tuple[str, Set[str]]:
    """
    Recursively parse a Query object into a query string.

    Returns:
        Tuple of (query string, set of extracted category values)
    """
    operation = query.get("Operation", "").lower()
    categories_found: Set[str] = set()

    op_map = {
        "lt": "<",
        "lte": "<=",
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "match": "match",
        "prefix": "prefix"
    }
    
    if operation in ("and", "or", "not"):
        sub_queries = query.get("SubQueries", [])
        if not sub_queries:
            return "", categories_found

        sub_parts = []
        for sub in sub_queries:
            sub_str, sub_cats = _parse_query_recursive(sub)
            categories_found.update(sub_cats)
            if sub_str:
                sub_parts.append(sub_str)

        if not sub_parts:
            return "", categories_found
        
        if operation == "not":
            return f"not ({sub_parts[0]})", categories_found
        elif len(sub_parts) == 1:
            return sub_parts[0], categories_found
        else:
            joined = f" {operation} ".join(sub_parts)
            return f"({joined})", categories_found

    if operation in op_map:
        field = query.get("Field", "")
        value = query.get("Value", "")
        api_op = op_map[operation]

        if field.lower() == "category":
            categories_found.add(value)
            return "", categories_found

        formatted_value = _format_value(field, value)
        return f"({field} {api_op} {formatted_value})", categories_found
    
    return "", categories_found



def _modality_to_category(modality: str) -> Optional[str]:
    """Map modality to category. Returns None for 'all'."""
    mapping = {
        "document": "doc",
        "doc": "doc",
        "image": "image",
        "video": "video",
        "audio": "audio"
    }
    return mapping.get(modality.lower())


def build_query(
    scalar_json: Optional[str],
    semantic_json: Optional[str]
) -> Dict[str, Any]:
    """
    Build the final query result.

    Returns:
        Dict with has_query, query, order_by, message fields.
    """
    scalar_data = None
    semantic_data = None

    if scalar_json:
        try:
            scalar_data = json.loads(scalar_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] Scalar query JSON parse failed: {e}", file=sys.stderr)

    if semantic_json:
        try:
            semantic_data = json.loads(semantic_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] Semantic query JSON parse failed: {e}", file=sys.stderr)

    scalar_valid = scalar_data and scalar_data.get("valid", False)
    semantic_valid = semantic_data and semantic_data.get("valid", False)
    
    if not scalar_valid and not semantic_valid:
        return {
            "has_query": False,
            "query": None,
            "order_by": None,
            "message": "Sorry, I cannot understand your search intent. Currently supported search methods:\n1. Search by file attributes: filename, type, size, creation time, etc.\n2. Search by content semantics: describe file content, scenes, etc.\n\nPlease try describing the file you want to find more specifically, for example:\n- \"Find PDF documents from last year\"\n- \"Photos of sunset at the beach\"\n- \"Video files larger than 10MB\""
        }
    
    query_parts: List[str] = []
    all_categories: Set[str] = set()

    scalar_query_str = ""
    if scalar_valid:
        result = scalar_data.get("result", {})
        query_obj = result.get("Query")

        if query_obj:
            scalar_query_str, cats_from_scalar = _parse_query_recursive(query_obj)
            all_categories.update(cats_from_scalar)

    semantic_query_str = ""
    if semantic_valid:
        result = semantic_data.get("result", {})
        query_text = result.get("query", "")
        modalities = result.get("modality", ["all"])

        if query_text:
            escaped_text = _escape_value(query_text)
            semantic_query_str = f'semantic_text = "{escaped_text}"'

        for m in modalities:
            cat = _modality_to_category(m)
            if cat:
                all_categories.add(cat)

    category_str = ""
    if all_categories:
        if len(all_categories) == 1:
            cat = list(all_categories)[0]
            escaped_cat = _escape_value(cat)
            category_str = f'category = "{escaped_cat}"'
        else:
            cats_list = sorted(list(all_categories))
            escaped_cats = [f'"{_escape_value(c)}"' for c in cats_list]
            category_str = f'category in [{", ".join(escaped_cats)}]'

    if scalar_query_str:
        query_parts.append(scalar_query_str)
    if semantic_query_str:
        query_parts.append(f"({semantic_query_str})")
    if category_str:
        query_parts.append(f"({category_str})")

    if len(query_parts) == 1:
        part = query_parts[0]
        # Single parenthesized expression: strip outer parens
        if part.startswith("(") and part.endswith(")"):
            final_query = part[1:-1]
        else:
            final_query = part
    else:
        final_query = " and ".join(query_parts)
    
    order_by = None
    if scalar_valid:
        result = scalar_data.get("result", {})
        sort_field = result.get("Sort")
        order_direction = result.get("Order", "")

        if sort_field:
            sort_fields = [f.strip() for f in sort_field.split(",")]
            order_directions = [d.strip().upper() for d in order_direction.split(",")] if order_direction else []

            order_parts = []
            for i, field in enumerate(sort_fields):
                direction = order_directions[i] if i < len(order_directions) else "ASC"
                if direction not in ("ASC", "DESC"):
                    direction = "ASC"
                order_parts.append(f"{field} {direction}")

            order_by = ",".join(order_parts)
    
    return {
        "has_query": True,
        "query": final_query if final_query else None,
        "order_by": order_by,
        "message": None
    }


def main():
    parser = argparse.ArgumentParser(
        description="Build SearchFile API query string from scalar and semantic query JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scalar query only
  python build_query.py --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gte", "Field": "size", "Value": "1000"}}}'

  # Semantic query only
  python build_query.py --semantic-json '{"valid": true, "result": {"query": "sunset", "modality": ["image"]}}'

  # Mixed query
  python build_query.py \\
    --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gt", "Field": "size", "Value": "1000"}, "Sort": "size", "Order": "desc"}}' \\
    --semantic-json '{"valid": true, "result": {"query": "landscape", "modality": ["image"]}}'

Output format:
  {
    "has_query": true,
    "query": "combined query string",
    "order_by": "size DESC",
    "message": null
  }
"""
    )

    parser.add_argument(
        "--scalar-json",
        default=None,
        help="Scalar query JSON string with valid and result fields"
    )
    parser.add_argument(
        "--semantic-json",
        default=None,
        help="Semantic query JSON string with valid and result fields"
    )

    args = parser.parse_args()

    if not args.scalar_json and not args.semantic_json:
        print("[INFO] No query parameters provided", file=sys.stderr)

    result = build_query(args.scalar_json, args.semantic_json)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
