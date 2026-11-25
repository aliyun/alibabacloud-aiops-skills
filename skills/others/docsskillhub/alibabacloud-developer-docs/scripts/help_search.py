#!/usr/bin/env python3
"""The full-text search leg, from the wire contract up to the `search` subcommand.

Four layers sit here in dependency order.

Wire contract (search.json, both sites): the request uses the selected site's host, with
'website' and 'language' parameters selecting the corpus explicitly. Everything specific to
the endpoint's contract lives in this layer and nowhere else: the parameter names it accepts
(keywords/pageNum/pageSize/website/language), the pageSize clamp its degradation envelopes
force, the four HTTP-200 envelope shapes, which item field carries the product name, and the
categoryMap name gate used to resolve a product's categoryId.

Item guards: each guard answers one question about an item the endpoint returned - does it
carry real content, does it belong to the requested site and language, and does it belong to
the requested product. None of them issues a request, so they are pure filters over lists of
dicts, and every drop is traced on stderr instead of happening silently.

One request: a page is fetched, its HTTP-200 legality is established, the surviving items are
turned into records and an identical repeat request is answered from the short-TTL cache.

categoryId discovery: the endpoint filters by a numeric categoryId, which the site menu
(help_menu) publishes as each product node's id. Only a product absent from the menu has its id
inferred, from three independent sources in increasing cost and decreasing confidence: the
categoryMap facet of a single probe request, the mode of the categoryIds a wide search returned
for the product's own URLs, and the nodeId embedded in the product landing page. Each inferred
result is only a candidate; the flow caches it after a filtered query has actually returned
documents, so a wrong guess costs one request and nothing more.

Orchestration: the top layer combines the two retrieval legs - the full-text endpoint and the
llms.txt index. It owns only the decisions - which leg to run for the requested scope, which
categoryId to filter by, when to degrade and what to tell the user about it - while every
score and index scan belongs to the module it is imported from.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse

from help_cache import (
    SEARCH_CACHE_DIR,
    SEARCH_CACHE_TTL_SECONDS,
    _category_cache_key,
    _get_cached_category_id,
    _load_category_cache,
    _save_category_cache,
    read_search_cache,
    search_cache_key,
    write_search_cache,
)
from help_const import (
    CATEGORY_CACHE_PATH,
    DEFAULT_SITE,
    DOC_MAX_BYTES,
    INTL_SEARCH_PAGESIZE_DEFAULT,
    INTL_SEARCH_PAGESIZE_MAX,
    INTL_SEARCH_PAGESIZE_MIN,
    MAX_QUERY_LEN,
    SEARCH_BACKENDS,
    SEARCH_LANG_WHITELIST,
    SEARCH_MAX_BYTES,
    SEARCH_TIMEOUT,
    SITES,
    result_cache_enabled,
)
from help_http import (
    _is_err,
    _looks_like_html,
    fetch,
    fetch_response,
)
from help_llms_index import (
    _IndexUnavailable,
    _index_leg_search,
    _scan_product_index_scored,
    _resolve_menu_product,
)
from help_query import (
    _INDEX_FUSION_FULL_SCORE,
    _SYNONYM_LOOKUP,
    _error_code_hint,
    _expand_retry,
    _fuse_results,
    is_precision_query,
    translate_query_for_english,
)
from help_render import (
    _format_updated,
    _readable_title,
    _render_found,
    _strip_html,
)
from help_scope import (
    _has_cjk,
    _path_prefix,
    _resolve_site_lang,
    _scope_explicit,
    _strip_help_prefix,
    _url_host,
    _url_in_product,
    _url_lang_segment,
)


# ---------------------------------------------------------------------------
# Layer 1 - the search.json wire contract: parameter names, paging bounds, envelope shapes.
# ---------------------------------------------------------------------------

def _search_backend(site: str, lang: str) -> str | None:
    """Full-text backend id for a (site, lang) pair, or None when the leg must be skipped.

    search.json serves every pair that has a real full-text corpus, on both portals: the
    corpus is selected by its 'website' and 'language' parameters. Any language outside the
    whitelist silently falls back to English server-side, so the caller skips the full-text
    leg and relies on the index leg instead (guard S3).
    """
    if lang not in SEARCH_LANG_WHITELIST:
        return None
    return "search_json"


def _clamp_page_size(n) -> int:
    """Clamp a search.json pageSize into 2..200 (guard S7).

    Below 2 the server can collapse totalCount to 0; above 200 it silently degrades to an
    empty envelope with success=true. Non-numeric input falls back to the default.
    """
    try:
        value = int(n)
    except (TypeError, ValueError):
        return INTL_SEARCH_PAGESIZE_DEFAULT
    return max(INTL_SEARCH_PAGESIZE_MIN, min(value, INTL_SEARCH_PAGESIZE_MAX))


def _clamp_query(keyword: str) -> str:
    """Trim a search query to MAX_QUERY_LEN characters (an over-long query returns total=0)."""
    text = (keyword or "").strip()
    if len(text) > MAX_QUERY_LEN:
        print(f"WARN[query-clamp]: query longer than {MAX_QUERY_LEN} characters truncated; "
              f"the search endpoint silently returns zero results for over-long queries",
              file=sys.stderr)
        return text[:MAX_QUERY_LEN]
    return text


def _extract_items(data, backend: str) -> list:
    """Result list of a search response, read through the backend's own path (C16).

    search.json nests it three levels deep (data.documents.data). Reading the wrong path yields
    an empty list, which the caller would trust as a legitimate "no results" answer, so the path
    belongs to the backend contract and is never hard-coded at the call site.
    """
    node = data
    for key in SEARCH_BACKENDS[backend]["items_path"]:
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, list) else []


def _extract_total(data, backend: str) -> int:
    """totalCount of a search response (0 when absent or non-numeric).

    This is the only trustworthy pagination-termination criterion (guard S8): an out-of-range
    page number still answers HTTP 200 with a full page, so a length-based test never fires.
    """
    node = data
    for key in SEARCH_BACKENDS[backend]["total_path"]:
        node = node.get(key) if isinstance(node, dict) else None
    if isinstance(node, bool):
        return 0
    try:
        return max(int(node), 0)
    except (TypeError, ValueError):
        return 0


def _parse_category_id(value) -> int | None:
    """Normalize the categoryId of a result item: compatible with pure digits and prefixed strings (e.g. 'help@@31815')."""
    # isinstance(True, int) is true; bools must be intercepted first
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        m = re.search(r"(\d+)", value)
        if m:
            try:
                n = int(m.group(1))
                return n if n > 0 else None
            except ValueError:
                return None
    return None


def build_params(keyword: str, *, category_id=None, category4_id=None, product=None,
                 include_category_id: bool = False, limit=10,
                 site: str = DEFAULT_SITE, lang: str = "zh",
                 original: bool = False):
    """Return (params, page_size) for one search.json request, or None to skip the request.

    The corpus is selected by the 'website' and 'language' parameters, not by the host.
    Subproducts use the menu's parent categoryId together with category4Id and DOCUMENT,PRODUCT
    topics. An empty query returns a catalogue rather than search results, while over-long queries
    silently return totalCount=0; both are intercepted here.
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
    if category_id is not None:
        params["categoryId"] = category_id
        if category4_id is not None:
            params["category4Id"] = category4_id
            params["topics"] = "DOCUMENT,PRODUCT"
    if original:
        params["original"] = "1"
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
    """Confirm a whole product code, display name, known alias or full-name initials."""
    slug = (product or "").strip().lower()
    text = _strip_help_prefix(name).lower()
    if len(slug) < 2 or not text:
        return False
    if re.search(r"(?<![a-z0-9_])" + re.escape(slug) + r"(?![a-z0-9_])", text):
        return True
    names = {slug, *(str(member).lower() for member in _SYNONYM_LOOKUP.get(slug, ()))}
    normalized = re.sub(r"[\s_-]+", " ", text).strip()
    if normalized in {re.sub(r"[\s_-]+", " ", name).strip() for name in names}:
        return True
    forms = {slug}
    parts = [part for part in slug.split("-") if part]
    if len(parts) >= 2:
        forms.add("".join(part[0] for part in parts))
    initials = "".join(word[0] for word in re.findall(r"[a-z0-9]+", text))
    return len(initials) >= 2 and initials in forms


# ---------------------------------------------------------------------------
# Layer 2 - item guards: pure filters over raw result items, every drop traced on stderr.
# ---------------------------------------------------------------------------

def _drop_shell_items(items: list, require_content: bool = True) -> list:
    """Drop empty-shell result entries (guard S8).

    An out-of-range pageNum is not an error on search.json: it answers HTTP 200 with a full
    page whose entries lost categoryId, categoryName and content (measured: pageNum=50 with 40
    valid pages returned 10 items carrying only 7 fields), so a length-based pagination test
    would loop forever and collect shells, so an entry that lost 'content' is treated as a
    shell alongside one that lost its URL.
    """
    kept = []
    dropped = 0
    for item in items:
        if not isinstance(item, dict) or not str(item.get("url") or "").strip():
            dropped += 1
            continue
        if require_content and not str(item.get("content") or "").strip():
            dropped += 1
            continue
        kept.append(item)
    if dropped:
        print(f"WARN[schema-drift]: dropped {dropped} empty-shell result item(s) carrying no usable url/content "
              f"(the search endpoint returns such degraded shells for an out-of-range page); "
              f"they are never counted as results", file=sys.stderr)
    return kept


def _validate_site_purity(items: list, site: str, lang: str) -> list:
    """Enforce site isolation and language consistency on raw search hits (guards S1 + S2).

    S1 (host): the two documentation sites carry different product portfolios, regional
    availability and billing rules, so a result set must never mix them and no cross-site
    fallback is ever performed; an item whose URL host is not the requested site's host is
    dropped.
    S2 (language segment): the endpoint silently falls back to English for every language
    outside the whitelist (measured 28/28 combinations returned the English totalCount and
    English URLs with HTTP 200 and no error signal), so an item whose URL language segment
    names a different language is dropped. Items with no language segment at all (the legacy
    help.aliyun.com/document_detail/{id}.html shape, measured 2/119 items) are kept:
    they carry no evidence of a fallback and dropping them would lose real results.
    """
    host = SITES[site]["result_host"]
    kept = []
    bad_host = 0
    bad_lang = 0
    for item in items:
        url = str(item.get("url") or "") if isinstance(item, dict) else ""
        item_host = _url_host(url)
        if item_host and item_host != host:
            bad_host += 1
            continue
        segment = _url_lang_segment(url, site)
        if segment and segment != lang:
            bad_lang += 1
            continue
        kept.append(item)
    if bad_host:
        print(f"WARN[site-cross]: dropped {bad_host} result(s) served by a host other than {host}; "
              f"the China site and the international site are never mixed and no cross-site "
              f"fallback is performed", file=sys.stderr)
    if bad_lang:
        print(f"WARN[lang-fallback]: dropped {bad_lang} result(s) whose URL language segment is "
              f"not '{lang}'; the search endpoint silently falls back to English for "
              f"unsupported languages", file=sys.stderr)
    return kept


def _post_filter_by_product(results: list, product: str,
                            site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Keep results within the product's actual URL path, never a query-string occurrence."""
    lang = lang or SITES[site]["default_lang"]
    return [r for r in results if _url_in_product(r["url"], product, site, lang)]


# ---------------------------------------------------------------------------
# Layer 3 - one full-text request, from the wire to output records.
# ---------------------------------------------------------------------------

def _search_fetch_page(params: dict, backend: str = "search_json", page_size: int = 0, page_num: int = 1):
    """Issue a single-page full-text request and validate the response; return None on anomalies (caller degrades).

    Retry policy (N2): a network failure, an HTTP 429 or a 5xx is retried once with exponential
    backoff and honours an advertised Retry-After; any other 4xx is final because repeating the
    request cannot change the answer. The body is capped at SEARCH_MAX_BYTES (N4).

    The endpoint follows the request's website parameter; both sites use plain GET with no
    header dependency other than the observability User-Agent.
    """
    url = SEARCH_BACKENDS[backend]["endpoint"][params["website"]] + "?" + urllib.parse.urlencode(params)
    text, meta = fetch_response(url, timeout=SEARCH_TIMEOUT,
                               max_bytes=SEARCH_MAX_BYTES, attempts=2)
    if _is_err(text):
        status = meta.get("status")
        if status == 429 or (status or 0) >= 500:
            print(f"WARN[rate-limit]: search API returned HTTP {status} after the backoff "
                  f"retry; degrading to the llms.txt index leg", file=sys.stderr)
        elif status:
            print(f"WARN[rate-limit]: search API returned HTTP {status}; no further retry, degrading to the "
                  f"llms.txt index leg", file=sys.stderr)
        else:
            print(f"WARN[unreachable]: search API request failed ({text}); degrading to the llms.txt index leg",
                  file=sys.stderr)
        return None
    if meta.get("truncated"):
        print(f"WARN[oversize]: the search response exceeded "
              f"{SEARCH_MAX_BYTES // (1024 * 1024)} MB and was truncated; degrading to the "
              f"llms.txt index leg", file=sys.stderr)
        return None

    # HTTP 200 but anomalous content: signals of channel revamp/rate limiting; degrade directly.
    # This guard matters more on the international host: dropping the '/help' path segment from
    # the endpoint returns HTTP 200 with a ~92 KB WAF interstitial HTML page instead of JSON.
    if _looks_like_html(text):
        print("WARN[waf-block]: the search endpoint answered HTTP 200 with an HTML page "
              "(rate limiting or a channel revamp); degrading to the llms.txt index leg",
              file=sys.stderr)
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        print("WARN[schema-drift]: the search endpoint returned non-JSON content; degrading to "
              "the llms.txt index leg", file=sys.stderr)
        return None

    if not isinstance(data, dict):
        print("WARN[schema-drift]: the search endpoint returned a malformed structure; degrading "
              "to the llms.txt index leg", file=sys.stderr)
        return None
    # Envelope A (invalid parameter). 'success' is only false for a parameter error, so it is a
    # legality test and never a "has results" test; the 'msg' field can echo a server-side Java
    # stack trace and is therefore never printed - only the numeric code is.
    if data.get("success") is False:
        print("WARN[schema-drift]: search API success=false; degrading to the llms.txt index leg", file=sys.stderr)
        return None
    code = data.get("code")
    if code is not None and str(code) != "200":
        print(f"WARN[schema-drift]: search API code={code} (not 200); degrading to the llms.txt index leg", file=sys.stderr)
        return None
    if _detect_degraded_envelope(data, backend, page_size, page_num):
        return None
    return data


def _search_parse_items(info: list, include_category_id: bool,
                        site: str = DEFAULT_SITE, lang: str = "",
                        backend: str = "search_json") -> list:
    """Convert raw full-text entries into output records.

    product: search.json has no productName field, so the product name is taken from
    categoryName with the 'help@@' namespace prefix stripped (C21/C22), falling back to the URL
    path. That fallback regex is site-scoped: '/{lang}/{product}/' on the China site,
    '/help/{lang}/{product}/' on the international one.
    updated: search.json has no modification-timestamp field, so no result carries an 'updated'
    key. The field is kept in the record shape because it is display-only and takes no part in
    the fusion score, so an index-leg entry that ever gains one is rendered unchanged.
    """
    lang = lang or SITES[site]["default_lang"]
    fallback_re = re.compile(re.escape(_path_prefix(site, lang)) + r"([^/]+)/")
    results = []
    for item in info:
        if not isinstance(item, dict):
            continue
        title = _readable_title(item)
        url = item.get("url") or ""
        desc = _strip_html(item.get("content") or "")[:120]
        prod = parse_product(item, site=site, lang=lang)
        if not prod:
            m = fallback_re.search(url)
            prod = m.group(1) if m else ""
        rec = {"product": prod, "title": title, "url": url, "desc": desc}
        updated = _format_updated(item.get("gmtModifiedOrigin"))
        if updated:
            rec["updated"] = updated
        if include_category_id:
            rec["categoryId"] = item.get("categoryId")
        results.append(rec)
    return results


def _guard_subproduct_hits(results: list, product: str, site: str, lang: str):
    kept = _post_filter_by_product(results, product, site, lang)
    if len(kept) != len(results):
        print(f"WARN[subproduct-scope]: dropped {len(results) - len(kept)} full-text item(s) "
              f"outside '{product}'; the returned page is not exhaustive", file=sys.stderr)
        if not kept:
            return None
    for hit in kept:
        hit["product"] = product
    return kept


def search_api(keyword: str, product: str | None = None, limit: int = 10,
               category_id: int | None = None,
               include_category_id: bool = False, category4_id: int | None = None,
               site: str = DEFAULT_SITE, lang: str = "",
               original: bool = False) -> list | None:
    """Call the official full-text search backend of one (site, lang) pair.

    On success (including a trustworthy "no results" empty list) return a list; on failure return None, and the
    caller degrades to the llms.txt index leg. All degradations emit a WARN on stderr for traceability.

    Backend routing: search.json serves every (site, lang) pair that has a real full-text
    corpus, selecting it through its own 'website' and 'language' parameters. Any other language
    has no full-text corpus of its own and the leg is skipped by the caller (guard S3), so
    search_api returns None for it without issuing a request.

    - category_id selects a main product; category4_id additionally selects its subproduct.
      Subproduct pages are checked against the semantic directory before caching or limiting.
    - product only (no category_id): wide search, then filter by the site's product path.
    - include_category_id=True: result items carry the raw categoryId field (for the discovery
      mechanism to take the mode); the discovery wide search is not capped by limit.
    - search.json paging (C14): 'pageSize' really is honoured and is clamped to 2..200 (S7), and
      a single page is requested - no pagination loop. Termination would have to use
      pageNum * pageSize >= totalCount (S8) because an out-of-range pageNum still answers HTTP
      200 with a full page of degraded shells, so 'len(items) < pageSize' can never be used.
    """
    lang = lang or SITES[site]["default_lang"]
    backend = _search_backend(site, lang)
    if backend is None:
        return None

    # The parameter names, the page size that is honoured, the item field carrying the product
    # name and the response envelopes are endpoint knowledge and belong to layer 1, never to
    # this flow.
    built = build_params(keyword, category_id=category_id, category4_id=category4_id,
                         product=product, include_category_id=include_category_id, limit=limit,
                         site=site, lang=lang, original=original)
    if built is None:
        # Layer 1 refused to build a request (an empty query on search.json) and already
        # traced why: that is a trustworthy "no results", not a degradation.
        return []
    params, page_size = built

    # N8: a repeated identical request is answered from the short-TTL cache. The key is the
    # request (site, language, backend, every parameter), never the response body, so the
    # jittering search.json fields cannot fragment it.
    cache_hit = None
    if result_cache_enabled():
        request_key = search_cache_key(site, lang, backend, params)
        cache_hit = read_search_cache(request_key)
        if cache_hit is not None:
            print(f"INFO[result-cache]: reusing the full-text result of an identical request "
                  f"asked within the last {SEARCH_CACHE_TTL_SECONDS}s "
                  f"({SEARCH_CACHE_DIR}); pass --no-result-cache to force a live query",
                  file=sys.stderr)
            if category4_id is not None and product:
                cache_hit = _guard_subproduct_hits(cache_hit, product, site, lang)
                if cache_hit is None:
                    return None
            return cache_hit if limit is None else cache_hit[:limit]

    data = _search_fetch_page(params, backend,
                              page_size=page_size,
                              page_num=1)
    if data is None:
        return None
    info = _extract_items(data, backend)
    info = _validate_site_purity(info, site, lang)
    info = _drop_shell_items(info, require_content=requires_content())
    results = _search_parse_items(info, include_category_id, site, lang, backend)
    cacheable = category4_id is None or len(results) == len(_extract_items(data, backend))
    if category4_id is not None and _extract_total(data, backend) > 0 and not results:
        print("WARN[subproduct-scope]: the nonempty subproduct page contained no usable "
              "in-scope documents; treating this leg as unavailable, not an empty search",
              file=sys.stderr)
        return None

    # One request per leg: declare how the returned page compares with totalCount.
    report_totals(_extract_total(data, backend), len(results),
                  SITES[site]["label"], lang, page_size)

    if category4_id is not None and product:
        guarded = _guard_subproduct_hits(results, product, site, lang)
        if guarded is None:
            return None
        cacheable = cacheable and len(guarded) == len(results)
        results = guarded
    if category_id is not None:
        if result_cache_enabled() and cache_hit is None and cacheable:
            write_search_cache(request_key, results)
        return results if limit is None else results[:limit]
    # Product filtering is client-side post-filtering (wide search, then filter down to limit items)
    if product:
        results = _post_filter_by_product(results, product, site, lang)
    # totalCount=0 / empty items is a trustworthy "no results"; return an empty list instead of None
    if result_cache_enabled() and cache_hit is None and not product:
        # Only the unfiltered wide request is cached: a post-filtered set depends on client-side
        # needle logic and would freeze a product's share of the corpus for the cache lifetime.
        write_search_cache(request_key, results)
    return results if limit is None else results[:limit]


# ---------------------------------------------------------------------------
# Layer 4 - categoryId discovery for products absent from the menu: three independent sources,
# each result only a candidate.
# ---------------------------------------------------------------------------

def _discover_category_id(raw_results: list, product: str,
                          site: str = DEFAULT_SITE, lang: str = ""):
    """Reverse-look-up the product categoryId from wide-search results: collect the categoryIds of entries whose URL
    contains the site-scoped product needle and take the mode; only trust it when the mode gets >= 2 votes; return
    None when it cannot be discovered."""
    lang = lang or SITES[site]["default_lang"]
    counts = {}
    for r in raw_results:
        cid = _parse_category_id(r.get("categoryId"))
        if cid is not None and _url_in_product(r["url"], product, site, lang):
            counts[cid] = counts.get(cid, 0) + 1
    if not counts:
        return None
    best = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
    if best[1] < 2:
        return None
    return best[0]


def _discover_category_id_by_catmap(product: str, site: str, lang: str):
    """Discover a product's categoryId from the search.json categoryMap facet (C25, P1).

    One probe request (keywords={product}, pageSize=2 - the smallest legal page, S7) returns
    data.categoryMap.category_id as a ranked [{id, name}] list whose length varies with the query
    (measured 9 entries for 'CORS', 1 for 'oss'); only index 0 is used. The id is accepted only
    after the name gate confirms it. Returns None - without issuing any request - when the
    full-text leg is skipped for this language, when the probe fails, or when the gate rejects
    the name, so the caller falls back to the mode-vote discovery.
    """
    if _search_backend(site, lang) != "search_json":
        return None
    params = {"keywords": product, "pageNum": 1, "pageSize": INTL_SEARCH_PAGESIZE_MIN,
              "website": site, "language": lang}
    data = _search_fetch_page(params, "search_json",
                                          page_size=INTL_SEARCH_PAGESIZE_MIN, page_num=1)
    if data is None:
        return None
    payload = data.get("data")
    catmap = (payload.get("categoryMap") or {}) if isinstance(payload, dict) else {}
    facet = catmap.get("category_id") if isinstance(catmap, dict) else None
    if not isinstance(facet, list) or not facet or not isinstance(facet[0], dict):
        return None
    cid = _parse_category_id(facet[0].get("id"))
    name = _strip_help_prefix(facet[0].get("name"))
    if cid is None:
        return None
    if not _catmap_name_matches(product, name):
        print(f"INFO: the categoryMap facet suggested categoryId {cid} ('{name}') for '{product}' "
              f"but the product-name gate did not confirm it; falling back to mode-vote discovery",
              file=sys.stderr)
        return None
    return cid


def _discover_category_id_from_landing(product: str, site: str, lang: str):
    """categoryId candidate read from the product landing page (F4), or None.

    The page embeds "nodeId": N. Measured 2026-09-09 across 14 core China-site products, nodeId
    equals the categoryId the search endpoint uses for 9 of them and differs for 5
    (ack 126295 vs 85222, polardb 58609 vs 2249963, rds 95798 vs 26090, slb 196881 vs 27537,
    waf 2402328 vs 28515). The value is therefore only a candidate, consulted when the wide-search
    mode vote produced nothing - exactly the error-code and parameter queries where catmap fails -
    and a wrong candidate costs nothing: it is cached only after a categoryId-filtered query has
    actually returned results.

    Only the plain slug form is tried; a document_detail/{id}.html product has no landing path of
    its own. One request, capped like any other document body, never retried beyond the shared
    transport policy.
    """
    if not product or "/" in product:
        return None
    url = f"{SITES[site]['result_host']}{_path_prefix(site, lang)}{product}/"
    text = fetch("https://" + url, max_bytes=DOC_MAX_BYTES)
    if _is_err(text):
        return None
    match = re.search(r'"nodeId"\s*:\s*(\d+)', text)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Layer 5 - orchestration of the `search` subcommand: which leg to run, when to degrade.
# ---------------------------------------------------------------------------

def _category_hits_confirm(hits, product: str, site: str, lang: str) -> bool:
    return bool(hits) and all(
        _url_in_product(hit["url"], product, site, lang)
        or _catmap_name_matches(product, hit.get("product", ""))
        for hit in hits
    )


def _product_search_results(args, keyword: str, product: str,
                            site: str = DEFAULT_SITE, lang: str = ""):
    """Search with -p: full-text leg (categoryId server-side filter) + llms.txt index leg dual-path fusion,
    eliminating false negatives from client-side URL post-filtering and substring matching.

    Returns the fused list; raises _IndexUnavailable when retrieval gaps leave no usable matches.

    Every lookup is scoped to (site, lang): the menu, the categoryId cache key, the product needle
    behind the URL post-filter, the mode-vote discovery and the product llms.txt index. The menu id
    is authoritative; the cache only holds ids discovered for products the menu does not list.
    """
    lang = lang or SITES[site]["default_lang"]
    backend = _search_backend(site, lang)
    backend_label = "search.json"
    record, _tree = _resolve_menu_product(product, site, lang)
    if record is not None:
        product = record["code"]
    cache_key = _category_cache_key(site, lang, product)
    cache = _load_category_cache()
    category_id = record["category_id"] if record else None
    category4_id = record["category4_id"] if record else None
    category_source = "product menu"
    if category_id is None:
        category_id = _get_cached_category_id(cache, cache_key)
        category_source = "discovery cache"
    # Normalize -n 0 to "unlimited" (consistent with list-docs and other subcommands)
    limit = args.max_results if args.max_results > 0 else None

    # ---- Full-text leg: prefer categoryId server-side filter ----
    fulltext_hits = None
    if category_id is not None:
        child_filter = f", category4Id={category4_id}" if category4_id is not None else ""
        print(f"INFO: categoryId {product}->{category_id}{child_filter} ({category_source}), "
              f"{backend_label} server-side filtering", file=sys.stderr)
        precise = search_api(keyword, product=product, limit=limit, category_id=category_id,
                             category4_id=category4_id, site=site, lang=lang)
        if precise is not None and (category_source == "product menu"
                                    or _category_hits_confirm(precise, product, site, lang)):
            fulltext_hits = precise
        else:
            fallback = "the scoped llms.txt index" if record else "category discovery and URL-filtered search"
            print(f"WARN[leg-fallback]: categoryId={category_id}{child_filter} query was unavailable "
                  f"or its product identity was not confirmed; degrading to {fallback}", file=sys.stderr)

    if fulltext_hits is None and record is None and backend == "search_json":
        # C25: search.json exposes a categoryMap facet that can name the categoryId directly and
        # so saves the wide-search round trip.
        facet_cid = _discover_category_id_by_catmap(product, site, lang)
        if facet_cid is not None:
            facet_hits = search_api(keyword, product=product, limit=limit,
                                    category_id=facet_cid, site=site, lang=lang)
            if _category_hits_confirm(facet_hits, product, site, lang):
                fulltext_hits = facet_hits
                print(f"INFO: discovered categoryId {product}->{facet_cid} (categoryMap facet), "
                      f"written to cache {CATEGORY_CACHE_PATH}", file=sys.stderr)
                cache["entries"][cache_key] = {"category_id": facet_cid,
                                               "written_at": int(time.time())}
                _save_category_cache(cache)
            else:
                print(f"WARN[category-unverified]: categoryId={facet_cid} returned no "
                      f"identity-confirming documents; not caching it and continuing with "
                      f"wide search + URL post-filter", file=sys.stderr)

    if fulltext_hits is None and record is None:
        # Wide search (no categoryId, pageSize=50): serves both as the discovery data source and as the post-filter fallback result
        wide_raw = search_api(keyword, limit=50, include_category_id=True,
                              site=site, lang=lang)
        if wide_raw is not None:
            discovered = _discover_category_id(wide_raw, product, site, lang)
            discovered_source = "mode votes>=2"
            if discovered is None:
                # F4: the mode vote needs results that carry the product's own categoryId; an
                # error-code query has none, so ask the product page before giving up.
                discovered = _discover_category_id_from_landing(product, site, lang)
                discovered_source = "landing page nodeId"
            if discovered is not None:
                precise = search_api(keyword, product=product, limit=limit,
                                     category_id=discovered, site=site, lang=lang)
                if _category_hits_confirm(precise, product, site, lang):
                    fulltext_hits = precise
                    print(f"INFO: discovered categoryId {product}->{discovered} ({discovered_source}), "
                          f"written to cache {CATEGORY_CACHE_PATH}", file=sys.stderr)
                    cache["entries"][cache_key] = {"category_id": discovered,
                                                 "written_at": int(time.time())}
                    _save_category_cache(cache)
            if fulltext_hits is None:
                if discovered is None:
                    print(f"WARN[leg-fallback]: could not discover the categoryId of {product} (neither mode votes "
                          f"nor the product landing page produced one); "
                          f"falling back to URL post-filter (pageSize=50) this time", file=sys.stderr)
                else:
                    print(f"WARN[category-unverified]: categoryId={discovered} returned no "
                          f"identity-confirming documents; falling back to URL post-filter "
                          f"(pageSize=50) without caching the candidate", file=sys.stderr)
                filtered = _post_filter_by_product(wide_raw, product, site, lang)
                fulltext_hits = filtered if limit is None else filtered[:limit]
        else:
            print("WARN[leg-fallback]: full-text search leg unavailable; degrading to the llms.txt index leg", file=sys.stderr)

    # ---- Index leg + fusion ----
    # The scan keeps its scores: the fusion below weighs an index-leg hit by how well its title
    # and summary actually match the query, instead of treating every hit as equally strong.
    try:
        index_scored = _scan_product_index_scored(product, keyword, site, lang)
    except _IndexUnavailable as exc:
        if not fulltext_hits:
            raise
        print(f"WARN[leg-fallback]: {exc}; outputting full-text results only, "
              f"with incomplete retrieval coverage", file=sys.stderr)
        index_scored = None
    if index_scored is None:
        print(f"WARN[no-index]: no usable llms.txt index was returned for '{product}'; "
              f"this does not establish that its documentation is absent", file=sys.stderr)
        if fulltext_hits is None:
            raise _IndexUnavailable("the full-text leg is unavailable and no usable index "
                                    "was returned; documentation could not be verified")
        index_hits, index_scores = [], {}
    else:
        index_hits = [record for _score, record in index_scored]
        index_scores = {record["url"]: score for score, record in index_scored}

    if fulltext_hits is not None:
        for h in fulltext_hits:
            h["source"] = "fulltext"
        fused = _fuse_results(fulltext_hits, index_hits, index_scores,
                              _INDEX_FUSION_FULL_SCORE)
        print(f"INFO: fused: {len(fulltext_hits)} fulltext + {len(index_hits)} index"
              f" -> {len(fused)} unique", file=sys.stderr)
    else:
        print("WARN[leg-fallback]: full-text search is unavailable; only index titles and "
              "summaries were searched, not document bodies", file=sys.stderr)
        fused = index_hits
        if not fused:
            raise _IndexUnavailable("full-text search was unavailable and the index yielded "
                                    "no matches; the requested knowledge remains unverified")
    return fused


def search_docs(args) -> int:
    """Search docs: without -p, full-text leg only (degrade to a full index scan on failure);
    with -p, fuse the full-text leg and the llms.txt index leg; on escape switch / full-text leg failure, index leg only.
    When results are low (<2) and the alias dictionary hits, retry once with the expanded term and merge/dedupe both rounds (traced on stderr);
    the retry inherits the current path semantics; escape switch and degradation leg semantics are unchanged.

    Returns 0 for usable matches, 1 for no usable match/index, or 2 for request/parameter failure
    or retrieval gaps that leave documentation unverified.
    """
    site, lang = _resolve_site_lang(args)
    explicit = _scope_explicit(args)
    keyword = args.keyword.lower()
    # F9: one query-normalisation gate in front of both legs. An empty, blank or punctuation-only
    # query is not a search - the endpoints either answer with a whole-corpus hot list or with
    # unrelated pages - and an over-long query is silently answered with zero results, so both
    # shapes are handled here instead of being left to the individual backend adapter.
    keyword = _clamp_query(keyword)
    if not re.search(r"\w", keyword):
        print("ERROR: the query carries no searchable characters (empty, blank or punctuation "
              "only); no request was issued. Pass a documentation keyword such as 'presigned "
              "url', or an error code.", file=sys.stderr)
        return 2
    precision_query = is_precision_query(args.keyword)
    product = args.product
    # Normalize -n 0 to "unlimited" (consistent with list-docs and other subcommands)
    limit = args.max_results if args.max_results > 0 else None

    # CamelCase error-code detection: stderr hint only; does not change the search behavior itself
    _error_code_hint(args.keyword)

    # S3: only en/zh have a real full-text corpus. Any other language is answered with English
    # content while still reporting success=true, so the leg is skipped instead of being allowed
    # to return a foreign-language corpus as if it had matched the request.
    backend = _search_backend(site, lang)
    if backend is None:
        print(f"INFO: skipping the full-text leg for language '{lang}': the search endpoint only "
              f"serves {', '.join(sorted(SEARCH_LANG_WHITELIST))} and silently falls back to "
              f"English for any other language. Using the llms.txt index leg of the "
              f"{SITES[site]['label']} ({lang}) only", file=sys.stderr)
    elif backend == "search_json" and lang != "zh" and _has_cjk(keyword):
        # CJK queries silently produce unrelated English hits, even after partial translation.
        english, mapped = translate_query_for_english(keyword)
        if mapped and not _has_cjk(english):
            print(f"INFO[query-translate]: the query is Chinese but the corpus language is "
                  f"'{lang}'; searching the mapped English wording instead: \"{english}\"",
                  file=sys.stderr)
            keyword = english
        else:
            print(f"WARN[query-lang]: the query contains CJK characters but the requested corpus "
                  f"language is '{lang}', and the built-in vocabulary could not translate "
                  f"all CJK terms; the full-text leg is skipped to avoid unrelated hits. "
                  f"Use a corpus-language query; the llms.txt {lang} index alone cannot "
                  f"establish that the requested documentation is absent",
                  file=sys.stderr)
            backend = None

    # Full-text search leg (skippable via the ALIYUN_HELP_NO_SEARCH_API=1 escape switch, and
    # skipped by guard S3 for a language the endpoint does not really serve)
    fulltext_failed = False
    if backend is not None and os.environ.get("ALIYUN_HELP_NO_SEARCH_API") != "1":
        if product:
            failures = []

            def product_results(kw):
                try:
                    return _product_search_results(args, kw, product, site, lang)
                except _IndexUnavailable as exc:
                    failures.append(str(exc))
                    print(f"WARN[index-unavailable]: {exc}", file=sys.stderr)
                    return []

            results = product_results(keyword)
            results = _expand_retry(results, keyword, product_results)
            if not results and failures:
                print("ERROR: no usable matches within incomplete retrieval coverage; "
                      "the requested documentation remains unverified", file=sys.stderr)
                if args.json:
                    print("[]")
                return 2
            return _render_found(args, results, limit, site, lang, explicit, precision_query)

        def _global_fulltext(kw: str):
            hits = search_api(kw, product=None, limit=limit, site=site, lang=lang,
                              original=getattr(args, "original_query", False))
            if hits is None:
                return None
            for h in hits:
                h["source"] = "fulltext"
            return hits

        api_hits = _global_fulltext(keyword)
        if api_hits is not None:
            api_hits = _expand_retry(api_hits, keyword, _global_fulltext)
            return _render_found(args, api_hits, limit, site, lang, explicit, precision_query)
        fulltext_failed = True

    print("INFO: using the relevance-ranked llms.txt index leg; only titles and summaries "
          "are searched, not document bodies", file=sys.stderr)
    failures = []

    def index_results(kw):
        try:
            return _index_leg_search(kw, product, site, lang) or []
        except _IndexUnavailable as exc:
            failures.append(str(exc))
            print(f"WARN[index-unavailable]: {exc}", file=sys.stderr)
            return []

    found = index_results(keyword)
    found = _expand_retry(found, keyword, index_results)
    if not found and (failures or fulltext_failed):
        print("ERROR: no usable matches within incomplete retrieval coverage; documentation "
              "could not be verified", file=sys.stderr)
        if args.json:
            print("[]")
        return 2
    return _render_found(args, found, limit, site, lang, explicit, precision_query)
