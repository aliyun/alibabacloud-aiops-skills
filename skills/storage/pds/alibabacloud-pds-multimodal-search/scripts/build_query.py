#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a PDS SearchFile API query string.

Combines scalar-query JSON and semantic-query JSON into the final SearchFile
API `query` string. Supports recursively parsing nested query conditions and
merging `modality` with `category` constraints.

Usage:
    python build_query.py --scalar-json '<json>' --semantic-json '<json>'
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional, List, Set, Tuple

from get_scalar_query_prompt import field_schema


def _escape_value(value: str) -> str:
    """Escape backslashes and double quotes in query values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_value(field: str, value: str) -> str:
    """
    Format a value according to the field type.

    Args:
        field: Field name.
        value: Field value.

    Returns:
        A formatted value string. String/date fields are quoted, while
        long/boolean fields are not.
    """
    # Unknown fields default to string handling.
    field_info = field_schema.get(field.lower(), {})
    field_type = field_info.get("type", "string")

    # long and boolean values are emitted without quotes.
    if field_type in ("long", "boolean"):
        return str(value)

    # string and date values are quoted and escaped.
    escaped = _escape_value(str(value))
    return f'"{escaped}"'


def _parse_query_recursive(query: Dict[str, Any]) -> Tuple[str, Set[str]]:
    """
    Recursively parse a Query object into a query string.

    Args:
        query: A Query JSON object.

    Returns:
        A tuple of (query_string, extracted_category_values).
    """
    operation = query.get("Operation", "").lower()
    categories_found: Set[str] = set()

    # Operator mapping from JSON schema to SearchFile query syntax.
    op_map = {
        "lt": "<",
        "lte": "<=",
        "eq": "=",
        "gt": ">",
        "gte": ">=",
        "match": "match",
        "prefix": "prefix",
    }

    # Logical operators work on SubQueries.
    if operation in ("and", "or", "not"):
        sub_queries = query.get("SubQueries", [])
        if not sub_queries:
            return "", categories_found

        sub_parts = []
        for sub in sub_queries:
            sub_str, sub_cats = _parse_query_recursive(sub)
            categories_found.update(sub_cats)
            # Filter out empty parts. This happens when category clauses are
            # extracted and removed from the recursive query string.
            if sub_str:
                sub_parts.append(sub_str)

        # Re-check the remaining subqueries after filtering.
        if not sub_parts:
            return "", categories_found

        if operation == "not":
            return f"not ({sub_parts[0]})", categories_found
        if len(sub_parts) == 1:
            return sub_parts[0], categories_found

        joined = f" {operation} ".join(sub_parts)
        return f"({joined})", categories_found

    # Comparison / match operators.
    if operation in op_map:
        field = query.get("Field", "")
        value = query.get("Value", "")
        api_op = op_map[operation]

        # Extract category constraints and rebuild them later in a dedicated
        # merge step instead of leaving them inline.
        if field.lower() == "category":
            categories_found.add(value)
            return "", categories_found

        formatted_value = _format_value(field, value)
        return f"({field} {api_op} {formatted_value})", categories_found

    return "", categories_found


def _modality_to_category(modality: str) -> Optional[str]:
    """
    Map a semantic modality to a scalar category.

    Args:
        modality: A modality value.

    Returns:
        The corresponding category value, or None if the modality is unsupported.
    """
    mapping = {
        "document": "doc",
        "doc": "doc",
        "image": "image",
        "video": "video",
        "audio": "audio",
    }
    return mapping.get(modality.lower())


def _build_category_query(categories: Set[str]) -> str:
    """Build a category query fragment from a set of category values."""
    if not categories:
        return ""

    if len(categories) == 1:
        cat = next(iter(categories))
        return f'category = "{_escape_value(cat)}"'

    escaped_cats = [f'"{_escape_value(cat)}"' for cat in sorted(categories)]
    return f'category in [{", ".join(escaped_cats)}]'


def build_query(
    scalar_json: Optional[str],
    semantic_json: Optional[str]
) -> Dict[str, Any]:
    """
    Build the final query payload.

    Args:
        scalar_json: Scalar-query JSON string.
        semantic_json: Semantic-query JSON string.

    Returns:
        A dictionary containing has_query, query, order_by, and message.
    """
    scalar_data = None
    semantic_data = None

    # Parse scalar query JSON.
    if scalar_json:
        try:
            scalar_data = json.loads(scalar_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse scalar query JSON: {e}", file=sys.stderr)

    # Parse semantic query JSON.
    if semantic_json:
        try:
            semantic_data = json.loads(semantic_json)
        except json.JSONDecodeError as e:
            print(f"[WARN] Failed to parse semantic query JSON: {e}", file=sys.stderr)

    # Check whether at least one side is valid.
    scalar_valid = scalar_data and scalar_data.get("valid", False)
    semantic_valid = semantic_data and semantic_data.get("valid", False)

    if not scalar_valid and not semantic_valid:
        return {
            "has_query": False,
            "query": None,
            "order_by": None,
            "message": (
                "Sorry, I can't understand your search intent yet. "
                "Supported search types currently include:\n"
                "1. File-attribute search, such as filename, type, size, and creation time\n"
                "2. Content-based semantic search, such as file topics or scenes\n\n"
                "Try describing the file more specifically, for example:\n"
                '- "Find last year\'s PDF documents"\n'
                '- "Photos of beach sunsets"\n'
                '- "Video files larger than 10 MB"'
            ),
        }

    query_parts: List[str] = []
    scalar_categories: Set[str] = set()

    # Process scalar query.
    scalar_query_str = ""
    if scalar_valid:
        result = scalar_data.get("result", {})
        query_obj = result.get("Query")

        if query_obj:
            # Parse recursively while extracting category clauses out of the
            # main scalar query string.
            scalar_query_str, cats_from_scalar = _parse_query_recursive(query_obj)
            scalar_categories.update(cats_from_scalar)

    # Process semantic query.
    semantic_query_str = ""
    semantic_category: Optional[str] = None
    if semantic_valid:
        result = semantic_data.get("result", {})
        query_text = result.get("query", "")
        modalities = result.get("modality", [])

        if query_text:
            escaped_text = _escape_value(query_text)
            semantic_query_str = f'semantic_text = "{escaped_text}"'

        # Semantic search only supports a single modality.
        if not isinstance(modalities, list) or len(modalities) != 1:
            return {
                "has_query": False,
                "query": None,
                "order_by": None,
                "message": (
                    "Semantic search currently supports only a single modality. "
                    "Please specify exactly one of document, image, video, or audio."
                ),
            }

        semantic_category = _modality_to_category(str(modalities[0]))
        if not semantic_category:
            return {
                "has_query": False,
                "query": None,
                "order_by": None,
                "message": (
                    "Semantic search currently supports only the four single "
                    "modalities: document, image, video, and audio."
                ),
            }

    # Build the final category condition:
    # 1. Pure scalar retrieval allows multiple categories.
    # 2. Pure semantic retrieval must be single-modality.
    # 3. Mixed retrieval must converge to the semantic modality.
    final_categories: Set[str] = set()
    if semantic_category:
        if scalar_categories and semantic_category not in scalar_categories:
            supported_modalities = ", ".join(sorted(scalar_categories))
            return {
                "has_query": False,
                "query": None,
                "order_by": None,
                "message": (
                    "The semantic modality conflicts with the scalar filters. "
                    f"The semantic modality is {semantic_category}, but the "
                    f"scalar filter only allows {supported_modalities}. "
                    "Please adjust the conditions and try again."
                ),
            }
        final_categories = {semantic_category}
    else:
        final_categories = scalar_categories

    category_str = _build_category_query(final_categories)

    # Assemble the final query string.
    if scalar_query_str:
        query_parts.append(scalar_query_str)
    if semantic_query_str:
        query_parts.append(f"({semantic_query_str})")
    if category_str:
        query_parts.append(f"({category_str})")

    # Remove a redundant outer pair of parentheses for single-part queries.
    if len(query_parts) == 1:
        part = query_parts[0]
        if part.startswith("(") and part.endswith(")"):
            final_query = part[1:-1]
        else:
            final_query = part
    else:
        final_query = " and ".join(query_parts)

    # Build order_by from Sort and Order.
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
        "message": None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Combine scalar-query and semantic-query JSON into a SearchFile API query string.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scalar query only
  python build_query.py --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gte", "Field": "size", "Value": "1000"}}}'

  # Semantic query only
  python build_query.py --semantic-json '{"valid": true, "result": {"query": "beach sunset", "modality": ["image"]}}'

  # Mixed query
  python build_query.py \\
    --scalar-json '{"valid": true, "result": {"Query": {"Operation": "gt", "Field": "size", "Value": "1000"}, "Sort": "size", "Order": "desc"}}' \\
    --semantic-json '{"valid": true, "result": {"query": "landscape photo", "modality": ["image"]}}'

Output:
  {
    "has_query": true,
    "query": "combined query string",
    "order_by": "size DESC",
    "message": null
  }
""",
    )

    parser.add_argument(
        "--scalar-json",
        default=None,
        help="Scalar-query JSON string containing valid and result fields.",
    )
    parser.add_argument(
        "--semantic-json",
        default=None,
        help="Semantic-query JSON string containing valid and result fields.",
    )

    args = parser.parse_args()

    # Input validation.
    if not args.scalar_json and not args.semantic_json:
        print("[INFO] No query parameters were provided.", file=sys.stderr)

    # Build and print the final query result.
    result = build_query(args.scalar_json, args.semantic_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
