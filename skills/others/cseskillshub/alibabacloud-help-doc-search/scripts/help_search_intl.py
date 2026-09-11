#!/usr/bin/env python3
"""International-site full-text backend adapter (www.alibabacloud.com/help/json/search.json).

Everything specific to that endpoint's wire contract lives here and nowhere else: the
parameter names it accepts (keywords/pageNum/pageSize/website/language), the pageSize
clamp its degradation envelopes force, the four HTTP-200 envelope shapes, which item
field carries the product name, and the categoryMap name gate used to resolve a
product's categoryId.
"""

from __future__ import annotations

import re
import sys

from help_core import (
    INTL_SEARCH_PAGESIZE_DEFAULT,
    INTL_SEARCH_PAGESIZE_MAX,
    PRODUCT_CODE_ALIASES,
    _clamp_page_size,
    _clamp_query,
    _strip_help_prefix,
)
from help_query import (
    _SYNONYM_LOOKUP,
)


def build_params(keyword: str, *, category_id=None, product=None,
                 include_category_id: bool = False, limit=10,
                 site: str = "intl", lang: str = "en"):
    """Return (params, page_size) for one search.json request, or None to skip the request.

    Parameter mapping relative to doSearch: queryWord -> keywords, pageNo -> pageNum,
    bizType dropped (a doSearch-only parameter), website + language added. 'topics' and
    'category4Id' are accepted by the endpoint but have no measurable effect, so they are
    not sent. An empty query would return the whole-corpus hot list (93046 items) and an
    over-long query silently returns totalCount=0, so both are intercepted here.
    """
    keyword = _clamp_query(keyword)
    if not keyword:
        print("WARN[query-clamp]: an empty query is rejected for this search endpoint (it would return the "
              "whole-corpus hot list instead of a search result); no request was issued",
              file=sys.stderr)
        return None
    if limit is None:
        page_size = INTL_SEARCH_PAGESIZE_MAX
    else:
        page_size = min(_clamp_page_size(limit), INTL_SEARCH_PAGESIZE_DEFAULT)
    params = {
        "keywords": keyword,
        "pageNum": 1,
        "pageSize": page_size,
        "website": site,
        "language": lang,
    }
    return params, page_size


def parse_product(item: dict, *, site: str, lang: str) -> str:
    """Product name of a search.json entry: it has no productName field at all (C21/C22)."""
    return _strip_help_prefix(item.get("categoryName"))


def requires_content() -> bool:
    """Out-of-range pages on this endpoint answer with shells that lost 'content' (guard S8)."""
    return True


def inspect_envelope(data: dict, page_size: int, page_num: int) -> bool:
    """Screen the HTTP-200 degradation envelopes of this endpoint (guard S9 / C26)."""
    return _detect_degraded_envelope(data, "search_json", page_size, page_num)


def report_totals(total: int, shown: int, site_label: str, lang: str,
                  page_size: int) -> None:
    """Declare that only the top-ranked single page is returned for a larger totalCount."""
    if total > shown:
        print(f"INFO: the full-text leg matched {total} document(s) on the "
              f"{site_label} ({lang}); the {shown} returned item(s) are the "
              f"top-ranked single page (pageSize={page_size})", file=sys.stderr)


def _detect_degraded_envelope(data: dict, backend: str, page_size: int = 0, page_num: int = 1) -> bool:
    """Detect the HTTP-200 silent-degradation envelopes of search.json (guard S9 / C26).

    All known envelopes answer HTTP 200:
      A invalid parameter -> success=false; already rejected by the caller, and its 'msg' field
                             can echo a server-side Java stack trace, so it is never surfaced;
      B normal            -> accepted;
      C silent degradation-> success stays true, 'documents' loses its 'data' key and
                             totalCount collapses to 0 (pageSize>200, an over-long keywords
                             value, or an out-of-range pageNum);
      D case-sensitive     -> 'website=INTL' returns a different payload carrying a top-level
        website value         'code' plus a 'products' key and no 'categoryMap'.
    Envelope C is field-for-field indistinguishable from a genuine zero-result answer (both
    measured as categoryMap={} and no documents.data key), so the echoed paging fields are
    compared against the request: a mismatch means the server ignored the parameters and
    degraded, while a match means the empty result set is real and is returned as such.
    Because pageSize is clamped to 2..200 (S7), the query length is clamped to 60 characters
    and the page number stays inside totalCount (S8), envelope C is unreachable from this
    client; the check is kept as insurance against endpoint drift.
    doSearch has none of these shapes and is never inspected here.
    """
    if backend != "search_json":
        return False
    payload = data.get("data")
    if not isinstance(payload, dict):
        print("WARN[schema-drift]: search API returned no data object; degrading to the llms.txt index leg",
              file=sys.stderr)
        return True
    if "products" in payload or "categoryMap" not in payload:
        print("WARN[schema-drift]: search API returned the case-sensitive-website degradation envelope (a "
              "'products' key and/or no 'categoryMap'); the 'website' value is case-sensitive. "
              "Degrading to the llms.txt index leg", file=sys.stderr)
        return True
    documents = payload.get("documents")
    if not isinstance(documents, dict):
        print("WARN[schema-drift]: search API returned no documents object; degrading to the llms.txt index leg",
              file=sys.stderr)
        return True
    if page_size and documents.get("pageSize") != page_size:
        print(f"WARN[schema-drift]: search API ignored pageSize={page_size} and echoed "
              f"'{documents.get('pageSize')}'; this is the silent degradation envelope, so "
              f"totalCount=0 is not a real empty result. Degrading to the llms.txt index leg",
              file=sys.stderr)
        return True
    if documents.get("pageNum") != page_num:
        print(f"WARN[schema-drift]: search API ignored pageNum={page_num} and echoed "
              f"'{documents.get('pageNum')}'; degrading to the llms.txt index leg", file=sys.stderr)
        return True
    return False


def _catmap_name_matches(product: str, name: str) -> bool:
    """Name gate for the categoryMap facet: accept the suggested category only when it really is
    the requested product.

    The facet ranks categories by query relevance, not by identity, so it must never be trusted
    blindly (measured: the probe for the generic phrase 'storage fee' returns 'ApsaraDB RDS' at
    index 0). Accepted evidence, in order: the slug itself or any alias that maps to it as a
    word-boundary token; any hyphen-separated part of the slug of 3+ characters ('security-center'
    confirms 'Security Center'); any synonym of the slug from QUERY_SYNONYMS as a plain substring
    (needed for the Chinese display names); and the initials of the ASCII words of the display
    name ('Object Storage Service' confirms 'oss', 'Elastic Compute Service' confirms 'ecs').
    The gate is deliberately conservative: a false negative only falls back to the existing
    mode-vote discovery, while a false positive would pin the wrong corpus for 30 days.
    """
    slug = (product or "").strip().lower()
    text = _strip_help_prefix(name).lower()
    if len(slug) < 2 or not text:
        return False
    candidates = {slug}
    for alias, canonical in PRODUCT_CODE_ALIASES.items():
        if canonical == slug:
            candidates.add(alias)
        if alias == slug:
            candidates.add(canonical)
    for part in slug.split("-"):
        if len(part) >= 3:
            candidates.add(part)
    for token in candidates:
        if re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", text):
            return True
    for member in _SYNONYM_LOOKUP.get(slug, ()):
        alias = str(member).lower()
        if alias and alias != slug and alias in text:
            return True
    # Initials of the display name, compared against the slug, its aliases and the initials of
    # every hyphenated form: 'Object Storage Service' confirms 'oss', 'Elastic Compute Service'
    # confirms 'ecs', 'Server Load Balancer' confirms the 'slb' canonical of the 'alb' alias and
    # 'Security Center' confirms 'sas' through its 'security-center' canonical.
    forms = set(candidates)
    for token in candidates:
        parts = [p for p in token.split("-") if p]
        if len(parts) >= 2:
            forms.add("".join(p[0] for p in parts))
    initials = "".join(word[0] for word in re.findall(r"[a-z0-9]+", text))
    if len(initials) >= 2 and initials in forms:
        return True
    return False
