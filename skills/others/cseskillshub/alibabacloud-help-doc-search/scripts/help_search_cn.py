#!/usr/bin/env python3
"""China-site full-text backend adapter (t.aliyun.com/abs/search/doSearch).

That endpoint has no language dimension, so it only ever serves the cn+zh corpus. Everything
that is specific to its wire contract lives here and nowhere else: the parameter names it
accepts, the page size it honours, and which item field carries the product name.

Paging note (F1): the only page-size parameter this endpoint honours is "limit"; "pageSize" and
"pageNo" are accepted and silently ignored (measured 2026-09-09: limit=50 returns 49 items,
limit=200 returns 198, totalCount unchanged). One request therefore asks for the whole page the
caller wants, and no accumulation loop exists on top of it.
"""

from __future__ import annotations

# Bounds of the "limit" parameter. The precise (categoryId) path asks for what the caller
# requested, up to the largest page the endpoint honours; the unscoped wide path keeps asking
# for a top-ranked single page only, so a broad query never pulls the whole corpus down.
CN_LIMIT_MIN = 2
CN_LIMIT_MAX = 200
CN_WIDE_LIMIT_MAX = 20
# Page size used when the caller asked for "unlimited" (-n 0).
CN_UNLIMITED_FETCH = CN_LIMIT_MAX


def build_params(keyword: str, *, category_id=None, product=None,
                 include_category_id: bool = False, limit=10,
                 site: str = "cn", lang: str = "zh"):
    """Return (params, page_size) for the single doSearch request, never None.

    'limit' is the caller's requested maximum (None means "no cap"); the value actually sent is
    echoed back as page_size so the caller can report it. A categoryId-filtered request is
    already narrowed server-side, so it takes the requested page; an unscoped request stays at
    one top-ranked page (the historical behaviour a default cn+zh invocation relies on).
    """
    precise = category_id is not None or product or include_category_id
    if limit is None:
        page_size = CN_UNLIMITED_FETCH
    elif precise:
        page_size = min(max(limit, CN_LIMIT_MIN), CN_LIMIT_MAX)
    else:
        page_size = min(max(limit, CN_LIMIT_MIN), CN_WIDE_LIMIT_MAX)
    params = {
        "queryWord": keyword,
        "limit": page_size,
        "bizType": "help",
    }
    return params, page_size


def parse_product(item: dict, *, site: str, lang: str) -> str:
    """Product name of a doSearch entry: the endpoint carries it directly."""
    return item.get("productName") or ""


def requires_content() -> bool:
    """Whether an entry without a content snippet counts as a degraded shell.

    doSearch entries always carry both url and content (measured 197/197), and its historical
    behaviour must not change, so only an entry without a URL is structurally useless here.
    """
    return False


def inspect_envelope(data: dict, page_size: int, page_num: int) -> bool:
    """Legality screen of the response body.

    doSearch has none of the HTTP-200 degradation envelopes that search.json answers with, so
    it is never inspected; the shared caller has already rejected success=false and code!=200.
    """
    return False


def report_totals(total: int, shown: int, site_label: str, lang: str,
                  page_size: int) -> None:
    """Emit the single-page note.

    doSearch answers with the page that was asked for and its own totalCount, so the shared
    flow reports nothing extra here; the trace exists only on the international adapter.
    """
    return None
