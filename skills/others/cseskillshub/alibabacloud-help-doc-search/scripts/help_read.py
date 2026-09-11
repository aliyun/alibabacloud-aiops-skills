#!/usr/bin/env python3
"""Document body reading and the raw per-product index dump.

Only help-center hosts are accepted; the URL is normalised to its .md form and the body
is cleaned through help_render.
"""

from __future__ import annotations

import sys

from help_cache import (
    _get_llms_text,
    _llms_cache_path,
)
from help_core import (
    DOC_MAX_BYTES,
    SITES,
    _resolve_site_lang,
    _url_host,
)
from help_http import (
    _is_err,
    _is_index_corpus,
    _looks_like_html,
    fetch,
)
from help_query import (
    _normalize_product_code,
)
from help_render import (
    _convert_html_tables,
)


# Hosts whose document URLs accept the '.md' raw-Markdown suffix. Derived from SITES so a new
# site can never be forgotten here (the historical check was a bare 'help.aliyun.com' substring
# test, which also matched the host appearing anywhere in the query string).
_DOC_HOSTS = frozenset(cfg["result_host"] for cfg in SITES.values())


def read_doc(args) -> int:
    """Read a document body (auto-append the .md suffix; detect HTML fallback so a whole HTML page is not dumped into context).

    Returns the process exit code: 0 = body rendered, 1 = the endpoint answered HTTP 200 with an
    HTML page or an empty body (a dead or moved slug), 2 = the request itself failed.
    """
    url = args.url
    host = _url_host(url)

    # Ensure .md suffix
    if not url.endswith(".md"):
        # Only the two Help Center hosts serve raw Markdown at '<url>.md'
        if host in _DOC_HOSTS:
            url = url.rstrip("/") + ".md"

    site = (getattr(args, "site", None) or "").strip().lower()
    if site in SITES and host and host != SITES[site]["result_host"]:
        print(f"WARN[site-cross]: --site {site} points at {SITES[site]['result_host']} but the given URL is "
              f"on '{host}'; the URL is read as-is and no cross-site rewriting is performed",
              file=sys.stderr)

    text = fetch(url, max_bytes=DOC_MAX_BYTES)
    if len(text.encode("utf-8", errors="replace")) >= DOC_MAX_BYTES:
        # N4: a document body larger than the cap is clipped rather than buffered whole; the
        # largest legitimate .md measured on 2026-09-08 was 119 KB, so reaching here means the
        # endpoint returned something unexpected.
        print(f"WARN[oversize]: the document body exceeded {DOC_MAX_BYTES // (1024 * 1024)} MB and was "
              f"truncated; the tail of this document is missing from the output", file=sys.stderr)
    if _is_err(text):
        # Fallback: try without .md
        if url.endswith(".md"):
            print(f"[.md fetch failed, trying the original URL]", file=sys.stderr)
            text = fetch(url[:-3], max_bytes=DOC_MAX_BYTES)
        if _is_err(text):
            print(text)
            return 2

    if _looks_like_html(text) and not args.raw:
        print(f"[warning] this URL returned an HTML page instead of Markdown (HTTP 200, but the doc may have moved or the slug is dead).")
        print(f"URL: {url}")
        print("Suggestions:")
        print("  1. Use search/list-docs to find the latest .md link of this doc in the llms.txt index (links in the index are guaranteed valid)")
        print("  2. Or use the WebFetch tool to read the original URL (without .md) and extract the body")
        print("  (append --raw if you really need the raw HTML output)")
        return 1

    if not text.strip():
        print(f"[warning] this URL returned empty content (HTTP 200 empty body); the doc may not exist.")
        print(f"URL: {url}")
        print("Suggestion: use search/list-docs to find the latest .md link of this doc in the llms.txt index.")
        return 1

    if not args.raw:
        # Convert bare HTML tables in the body to Markdown (--raw keeps the original output)
        text = _convert_html_tables(text)

    if args.max_lines > 0:
        lines = text.split("\n")
        if len(lines) > args.max_lines:
            text = "\n".join(lines[:args.max_lines])
            text += f"\n\n... ({len(lines)} lines in total, first {args.max_lines} shown)"

    print(text)
    return 0


def read_product_llms(args) -> int:
    """Read a product's raw llms.txt (via the local cache layer, scoped by site and language).

    Returns the process exit code: 0 = index rendered, 1 = the index does not exist on this
    site+language, 2 = the request itself failed.
    """
    site, lang = _resolve_site_lang(args)
    product = _normalize_product_code(args.product)
    text, from_cache = _get_llms_text(product, site, lang)
    if from_cache:
        print(f"INFO: llms.txt served from local cache {_llms_cache_path(product, site, lang)}", file=sys.stderr)
    if _is_err(text):
        print(text)
        return 2
    if not _is_index_corpus(text):
        # A nonexistent product may return an HTML page, an HTTP 200 empty response body, or the
        # international 'no LLMS content yet' placeholder - none of them is a document index.
        print(f"[warning] the llms.txt of product '{product}' does not exist or is empty; please use list-products to verify the product code.")
        other = "cn" if site == "intl" else "intl"
        print(f"WARN[no-corpus]: product '{product}' has no llms.txt index on the {SITES[site]['label']} "
              f"({SITES[site]['result_host']}, language '{lang}'). It may exist on the "
              f"{SITES[other]['label']}: retry with '--site {other}' if you need it. "
              f"No automatic site fallback is performed.", file=sys.stderr)
        return 1

    if args.max_lines > 0:
        lines = text.split("\n")
        if len(lines) > args.max_lines:
            text = "\n".join(lines[:args.max_lines])
            text += f"\n\n... ({len(lines)} lines in total, first {args.max_lines} shown)"

    print(text)
    return 0
