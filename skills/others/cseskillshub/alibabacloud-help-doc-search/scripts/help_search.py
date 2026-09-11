#!/usr/bin/env python3
"""Full-text search flow shared by both backends.

Request issue, response legality, site-purity guards and the product-scoped orchestration
(fused with the llms.txt index leg) live here; the per-site differences are delegated to
help_search_cn / help_search_intl through the adapter interface defined in those modules.
"""

from __future__ import annotations

import help_search_cn
import help_search_intl
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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
from help_core import (
    CATEGORY_CACHE_PATH,
    DEFAULT_SITE,
    DOC_MAX_BYTES,
    INTL_SEARCH_PAGESIZE_MIN,
    SEARCH_BACKENDS,
    SEARCH_LANG_WHITELIST,
    SEARCH_MAX_BYTES,
    SEARCH_TIMEOUT,
    SITES,
    UA,
    _clamp_query,
    _extract_items,
    _extract_total,
    _has_cjk,
    _needle,
    _parse_category_id,
    _path_prefix,
    _resolve_site_lang,
    _scope_explicit,
    _search_backend,
    _strip_help_prefix,
    _url_host,
    _url_lang_segment,
    result_cache_enabled,
)
from help_http import (
    _is_err,
    _looks_like_html,
    fetch,
    fetch_response,
)
from help_llms_index import (
    _INDEX_FUSION_FULL_SCORE,
    _index_leg_search,
    _scan_product_index_scored,
)
from help_query import (
    _error_code_hint,
    _expand_retry,
    _normalize_product_code,
    is_precision_query,
    translate_query_for_english,
)
from help_render import (
    _format_updated,
    _fuse_results,
    _readable_title,
    _render_found,
    _strip_html,
)
from help_search_intl import (
    _catmap_name_matches,
    _detect_degraded_envelope,
)


def _drop_shell_items(items: list, require_content: bool = True) -> list:
    """Drop empty-shell result entries (guard S8).

    An out-of-range pageNum is not an error on search.json: it answers HTTP 200 with a full
    page whose entries lost categoryId, categoryName and content (measured: pageNum=50 with 40
    valid pages returned 10 items carrying only 7 fields), so a length-based pagination test
    would loop forever and collect shells. require_content=False is used for doSearch, whose
    entries always carry both fields (measured 197/197) and whose historical behaviour must not
    change; there only an entry without a URL is structurally useless.
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
    help.aliyun.com/document_detail/{id}.html shape, measured 2/119 doSearch items) are kept:
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


def _search_fetch_page(params: dict, backend: str = "doSearch", page_size: int = 0, page_num: int = 1):
    """Issue a single-page full-text request and validate the response; return None on anomalies (caller degrades).

    Retry policy (N2): a network failure, an HTTP 429 or a 5xx is retried once with exponential
    backoff and honours an advertised Retry-After; any other 4xx is final because repeating the
    request cannot change the answer. The body is capped at SEARCH_MAX_BYTES (N4).

    The endpoint comes from the backend contract; both are plain GET with no header dependency
    other than the observability User-Agent (search.json was verified header-independent over
    24 control requests, all HTTP 200 with an identical totalCount).
    """
    url = SEARCH_BACKENDS[backend]["endpoint"] + "?" + urllib.parse.urlencode(params)
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
                        backend: str = "doSearch") -> list:
    """Convert raw full-text entries into output records (including the updated timestamp field).

    product: doSearch carries productName and keeps its historical chain untouched so a default
    cn+zh invocation stays byte-for-byte identical. search.json has no productName field at all,
    so the product name is taken from categoryName with the 'help@@' namespace prefix stripped
    (C21/C22). Both fall back to the URL path, and that fallback regex is site-scoped:
    '/{lang}/{product}/' on the China site, '/help/{lang}/{product}/' on the international one.
    updated: only doSearch returns gmtModifiedOrigin; search.json has no timestamp field, so
    international-site results legitimately carry no 'updated' key. It is display-only and takes
    no part in the fusion score, so ranking is unaffected.
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
        prod = (help_search_cn if backend == "doSearch" else help_search_intl) \
            .parse_product(item, site=site, lang=lang)
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


def search_api(keyword: str, product: str | None = None, limit: int = 10,
               category_id: int | None = None,
               include_category_id: bool = False,
               site: str = DEFAULT_SITE, lang: str = "") -> list | None:
    """Call the official full-text search backend of one (site, lang) pair.

    On success (including a trustworthy "no results" empty list) return a list; on failure return None, and the
    caller degrades to the llms.txt index leg. All degradations emit a WARN on stderr for traceability.

    Backend routing: doSearch serves cn+zh only (it has no language dimension); search.json
    serves intl en/zh and cn+en. Any other language has no full-text corpus of its own and the
    leg is skipped by the caller (guard S3), so search_api returns None for it without issuing
    a request.

    - category_id: server-side category filter (pure digits only; search.json answers a prefixed
      or non-numeric value with envelope A code=400). With this param the server-side filter is
      trusted; no URL post-filtering.
    - product only (no category_id): wide search, then client-side post-filter by URLs containing
      the site-scoped product needle (the fallback path before categoryId discovery).
    - include_category_id=True: result items carry the raw categoryId field (for the discovery
      mechanism to take the mode); the discovery wide search is not capped by limit.
    - doSearch paging (F1): the only page-size parameter that endpoint honours is 'limit'
      ('pageSize'/'pageNo' are accepted and ignored), so one request asks for the whole page;
      no accumulation loop and no page-count cap exist any more.
    - search.json paging (C14): 'pageSize' really is honoured and is clamped to 2..200 (S7), and
      a single page is requested - no pagination loop. Termination would have to use
      pageNum * pageSize >= totalCount (S8) because an out-of-range pageNum still answers HTTP
      200 with a full page of degraded shells, so 'len(items) < pageSize' can never be used.
    """
    lang = lang or SITES[site]["default_lang"]
    backend = _search_backend(site, lang)
    if backend is None:
        return None

    # One adapter per portal: the parameter names, the page size that is honoured, the item
    # field carrying the product name and the response envelopes are endpoint knowledge and
    # live in help_search_cn / help_search_intl, never in this flow.
    adapter = help_search_cn if backend == "doSearch" else help_search_intl
    built = adapter.build_params(keyword, category_id=category_id, product=product,
                                 include_category_id=include_category_id, limit=limit,
                                 site=site, lang=lang)
    if built is None:
        # The adapter refused to build a request (an empty query on search.json) and already
        # traced why: that is a trustworthy "no results", not a degradation.
        return []
    params, page_size = built
    if category_id is not None:
        params["categoryId"] = category_id

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
            return cache_hit if limit is None else cache_hit[:limit]

    data = _search_fetch_page(params, backend,
                              page_size=page_size if backend == "search_json" else 0,
                              page_num=1)
    if data is None:
        return None
    info = _extract_items(data, backend)
    info = _validate_site_purity(info, site, lang)
    info = _drop_shell_items(info, require_content=adapter.requires_content())
    results = _search_parse_items(info, include_category_id, site, lang, backend)

    # One request per leg on both portals; only the international adapter has anything to
    # declare about totalCount vs returned items (the cn adapter no-ops).
    adapter.report_totals(_extract_total(data, backend), len(results),
                          SITES[site]["label"], lang, page_size)

    # Server-side categoryId filter: trust the server-side results; no URL post-filtering
    if category_id is not None:
        if result_cache_enabled() and cache_hit is None:
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


def _post_filter_by_product(results: list, product: str,
                            site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Client-side post-filter: keep only results whose URL contains the site-scoped product needle."""
    lang = lang or SITES[site]["default_lang"]
    needle = _needle(site, lang, product)
    return [r for r in results if needle in r["url"]]


def _discover_category_id(raw_results: list, product: str,
                          site: str = DEFAULT_SITE, lang: str = ""):
    """Reverse-look-up the product categoryId from wide-search results: collect the categoryIds of entries whose URL
    contains the site-scoped product needle and take the mode; only trust it when the mode gets >= 2 votes; return
    None when it cannot be discovered."""
    lang = lang or SITES[site]["default_lang"]
    needle = _needle(site, lang, product)
    counts = {}
    for r in raw_results:
        cid = _parse_category_id(r.get("categoryId"))
        if cid is not None and needle in r["url"]:
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
    backend has no facet (doSearch), when the probe fails, or when the gate rejects the name, so
    the caller falls back to the mode-vote discovery.
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

    The page embeds "nodeId": N. Measured 2026-09-09 across the 14 seeded China-site products,
    nodeId equals the categoryId the search endpoint uses for 9 of them and differs for 5
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


def _product_search_results(args, keyword: str, product: str,
                            site: str = DEFAULT_SITE, lang: str = ""):
    """Search with -p: full-text leg (categoryId server-side filter) + llms.txt index leg dual-path fusion,
    eliminating false negatives from client-side URL post-filtering and substring matching.

    Returns the fused result list (may be empty); when the product index does not exist and the full-text leg
    also has no results, emit a warning and return None so the caller terminates.

    Every lookup is scoped to (site, lang): the categoryId cache key, the product needle behind
    the URL post-filter, the mode-vote discovery and the product llms.txt index. cn+zh keeps the
    historical bare-product cache key and the historical 'doSearch' wording, so a default
    invocation stays byte-for-byte identical.
    """
    lang = lang or SITES[site]["default_lang"]
    backend = _search_backend(site, lang)
    backend_label = "doSearch" if backend == "doSearch" else "search.json"
    cache_key = _category_cache_key(site, lang, product)
    cache = _load_category_cache()
    category_id = _get_cached_category_id(cache, cache_key)
    # Normalize -n 0 to "unlimited" (consistent with list-docs and other subcommands)
    limit = args.max_results if args.max_results > 0 else None

    # ---- Full-text leg: prefer categoryId server-side filter ----
    fulltext_hits = None
    if category_id is not None:
        print(f"INFO: categoryId cache hit {product}->{category_id}, {backend_label} server-side filtering", file=sys.stderr)
        precise = search_api(keyword, product=product, limit=limit,
                             category_id=category_id, site=site, lang=lang)
        if precise is not None:
            fulltext_hits = precise
        else:
            print(f"WARN[leg-fallback]: precise query with categoryId={category_id} failed; degrading to wide search + URL post-filter",
                  file=sys.stderr)

    if fulltext_hits is None and backend == "search_json":
        # C25: search.json exposes a categoryMap facet that can name the categoryId directly and
        # so saves the wide-search round trip. doSearch has no facet, hence the backend test:
        # cn+zh skips this block entirely and keeps its historical request sequence.
        facet_cid = _discover_category_id_by_catmap(product, site, lang)
        if facet_cid is not None:
            facet_hits = search_api(keyword, product=product, limit=limit,
                                    category_id=facet_cid, site=site, lang=lang)
            if facet_hits is not None:
                fulltext_hits = facet_hits
                print(f"INFO: discovered categoryId {product}->{facet_cid} (categoryMap facet), "
                      f"written to cache {CATEGORY_CACHE_PATH}", file=sys.stderr)
                cache["entries"][cache_key] = {"category_id": facet_cid,
                                               "written_at": int(time.time())}
                _save_category_cache(cache)
            else:
                print(f"WARN[leg-fallback]: precise query with categoryId={facet_cid} failed; "
                      f"degrading to wide search + URL post-filter", file=sys.stderr)

    if fulltext_hits is None:
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
                if precise is not None:
                    fulltext_hits = precise
                    # Only write the cache after a precise query succeeds, so a wrong id is not cached for 30 days
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
                elif precise is None:
                    print(f"WARN[leg-fallback]: precise query with categoryId={discovered} failed; "
                          f"falling back to URL post-filter (pageSize=50) this time, not writing to cache", file=sys.stderr)
                filtered = _post_filter_by_product(wide_raw, product, site, lang)
                fulltext_hits = filtered if limit is None else filtered[:limit]
        else:
            print("WARN[leg-fallback]: full-text search leg unavailable; degrading to the llms.txt index leg", file=sys.stderr)

    # ---- Index leg + fusion ----
    # The scan keeps its scores: the fusion below weighs an index-leg hit by how well its title
    # and summary actually match the query, instead of treating every hit as equally strong.
    index_scored = _scan_product_index_scored(product, keyword, site, lang)
    if index_scored is None:
        if fulltext_hits:
            # Index leg unavailable (the product may not exist, or a transient llms.txt outage),
            # but do not discard the already-successful full-text leg results
            print(f"WARN[leg-fallback]: llms.txt index leg unavailable; outputting full-text leg results only", file=sys.stderr)
            index_hits, index_scores = [], {}
        else:
            print(f"[warning] the doc index of product '{product}' does not exist; please use list-products to verify the product code.")
            return None
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
        fused = index_hits
    return fused


def search_docs(args) -> int:
    """Search docs: without -p, full-text leg only (degrade to a full index scan on failure);
    with -p, fuse the full-text leg and the llms.txt index leg; on escape switch / full-text leg failure, index leg only.
    When results are low (<2) and the alias dictionary hits, retry once with the expanded term and merge/dedupe both rounds (traced on stderr);
    the retry inherits the current path semantics; escape switch and degradation leg semantics are unchanged.

    Returns the process exit code (0 = at least one document reported, 1 = the scoped corpus
    produced nothing or a leg reported a missing product index, 2 = invalid site/language).
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
    if product:
        product = _normalize_product_code(product)
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
        # S12: the endpoint accepts a CJK query with language=en without any error and answers
        # with unrelated hits (measured) or even a fake whole-corpus match. F6 tries the built-in
        # bilingual vocabulary first; only when nothing can be mapped is the leg dropped, because
        # a Chinese query in an English corpus is never an answer to anything.
        english, mapped = translate_query_for_english(keyword)
        if mapped:
            print(f"INFO[query-translate]: the query is Chinese but the corpus language is "
                  f"'{lang}'; searching the mapped English wording instead: \"{english}\"",
                  file=sys.stderr)
            keyword = english
        else:
            print(f"WARN[query-lang]: the query contains CJK characters but the requested corpus "
                  f"language is '{lang}', and none of its terms are in the built-in vocabulary; "
                  f"the full-text leg is skipped because the endpoint would answer with "
                  f"unrelated hits, and the llms.txt {lang} index leg is used instead",
                  file=sys.stderr)
            backend = None

    # Full-text search leg (skippable via the ALIYUN_HELP_NO_SEARCH_API=1 escape switch, and
    # skipped by guard S3 for a language the endpoint does not really serve)
    if backend is not None and os.environ.get("ALIYUN_HELP_NO_SEARCH_API") != "1":
        if product:
            results = _product_search_results(args, keyword, product, site, lang)
            if results is None:
                if explicit:
                    print(f"WARN[site-cross]: product '{product}' has no documentation on the "
                          f"{SITES[site]['label']} ({SITES[site]['result_host']}, language "
                          f"'{lang}'); no cross-site fallback is performed", file=sys.stderr)
                return 1
            results = _expand_retry(results, keyword,
                                    lambda kw: _product_search_results(args, kw, product, site, lang))
            return _render_found(args, results, limit, site, lang, explicit, precision_query)

        def _global_fulltext(kw: str):
            hits = search_api(kw, product=None, limit=limit, site=site, lang=lang)
            if hits is None:
                return None
            for h in hits:
                h["source"] = "fulltext"
            return hits

        api_hits = _global_fulltext(keyword)
        if api_hits is not None:
            api_hits = _expand_retry(api_hits, keyword, _global_fulltext)
            return _render_found(args, api_hits, limit, site, lang, explicit, precision_query)

    # ---- Index leg: llms.txt (title+summary substring match, no ranking) ----
    print("INFO: degrading to the llms.txt index leg (title+summary substring match only, no relevance ranking)",
          file=sys.stderr)
    found = _index_leg_search(keyword, product, site, lang)
    if found is None:
        if explicit and product:
            print(f"WARN[site-cross]: product '{product}' has no documentation on the "
                  f"{SITES[site]['label']} ({SITES[site]['result_host']}, language '{lang}'); "
                  f"no cross-site fallback is performed", file=sys.stderr)
        return 1
    found = _expand_retry(found, keyword,
                          lambda kw: _index_leg_search(kw, product, site, lang) or [])
    return _render_found(args, found, limit, site, lang, explicit, precision_query)
