#!/usr/bin/env python3
"""Search the generated WUYING command catalog without hard-coded intent mappings."""

#
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
#
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(value.lower().replace("-", " "))


def score_command(query: str, product: dict[str, Any], command: dict[str, Any]) -> tuple[int, list[str]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0, []

    query_phrase = " ".join(query_tokens)
    command_phrase = " ".join(tokenize(str(command.get("name") or "")))
    description = str(command.get("description") or "").lower()
    description_phrase = " ".join(tokenize(description))
    product_phrase = " ".join(
        tokenize(f"{product.get('product', '')} {product.get('product_name', '')}")
    )
    command_tokens = set(tokenize(command_phrase))
    description_tokens = set(tokenize(description_phrase))
    product_tokens = set(tokenize(product_phrase))

    score = 0
    matched: set[str] = set()
    if query_phrase == command_phrase:
        score += 100
    elif query_phrase in command_phrase:
        score += 60
    if query_phrase in description_phrase:
        score += 45

    for token in query_tokens:
        if token in command_tokens:
            score += 10
            matched.add(token)
        if token in description_tokens:
            score += 4
            matched.add(token)
        if token in product_tokens:
            score += 2
            matched.add(token)

    coverage = len(matched) / len(set(query_tokens))
    if coverage < 1:
        return 0, sorted(matched)
    score += round(coverage * 20)
    return score, sorted(matched)


def search_catalog(
    catalog: dict[str, Any],
    query: str,
    product_filter: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    if catalog.get("schema_version") != 2:
        raise RuntimeError(
            f"unsupported command catalog schema: {catalog.get('schema_version')!r}"
        )

    candidates: list[dict[str, Any]] = []
    for product in catalog.get("products") or []:
        product_code = str(product.get("product") or "")
        if product_filter and product_code != product_filter:
            continue
        for command in product.get("commands") or []:
            score, matched_terms = score_command(query, product, command)
            if score <= 0:
                continue
            candidates.append(
                {
                    "product": product_code,
                    "product_name": product.get("product_name"),
                    "command": command.get("name"),
                    "description": command.get("description"),
                    "api_versions": command.get("api_versions"),
                    "preferred_api_version": command.get("preferred_api_version"),
                    "risk": command.get("risk"),
                    "score": score,
                    "matched_terms": matched_terms,
                }
            )

    candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["product"]),
            str(item["command"]),
        )
    )
    return candidates[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "query",
        help="Short English business phrase, for example: authorized users",
    )
    parser.add_argument("--product", help="Optional exact product-code filter")
    parser.add_argument("--limit", type=int, default=10, help="Maximum candidates to return")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "references" / "command-catalog.json",
        help="Generated command catalog path",
    )
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    candidates = search_catalog(
        catalog,
        args.query,
        product_filter=args.product,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "query": args.query,
                "product_filter": args.product,
                "catalog_complete": catalog.get("catalog_complete", True),
                "configured_products": catalog.get("configured_products", []),
                "missing_products": catalog.get("missing_products", []),
                "candidate_count": len(candidates),
                "candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
