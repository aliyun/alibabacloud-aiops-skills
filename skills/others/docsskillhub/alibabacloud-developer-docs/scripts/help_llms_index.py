#!/usr/bin/env python3
"""Cached llms.txt scans and menu-alias, menupath-first document directory listing."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from help_cache import (
    _llms_cache_path,
    _trim_llms_cache,
)
from help_const import (
    DEFAULT_SITE,
    LLMS_CACHE_TTL_DAYS,
    LLMS_MAX_BYTES,
    SITES,
    _DOC_ENTRY_RE,
)
from help_scope import (
    _product_llms_url,
    _resolve_site_lang,
    _path_prefix,
    _semantic_alias,
    _url_host,
    _url_in_product,
    _url_lang_segment,
)
from help_menu import find_product, load_menu, load_product_tree, menu_product_codes, product_tree_docs
from help_http import (
    _fetch_index,
    _index_failure_code,
    _is_index_corpus,
    _non_corpus_reason,
)
from help_query import (
    _index_scored_hits,
    _merge_scored_scans,
)


# Budget of an unscoped index scan (N2): the whole-catalogue walk used 16 parallel connections
# with no backoff, which is the harshest pattern the help endpoints have ever been observed
# under and has no SLA behind it; 8 keeps the cold scan under half a minute while halving the
# instantaneous pressure. Progress cadence is the N7 feedback interval.
INDEX_SCAN_WORKERS = 8
INDEX_SCAN_PROGRESS_EVERY = 100


class _IndexUnavailable(Exception):
    pass


def _resolve_menu_product(product: str, site: str, lang: str):
    record = find_product(load_menu(site, lang), product)
    if record is None or record["alias"]:
        return record, None
    text, _cached = _get_llms_text(record["code"], site, lang)
    if _is_index_corpus(text):
        for _title, url, _desc in _DOC_ENTRY_RE.findall(text):
            if (_url_host(url) != SITES[site]["result_host"]
                    or _url_lang_segment(url, site) != lang):
                continue
            path = urllib.parse.urlsplit(url).path
            prefix = _path_prefix(site, lang)
            candidate = _semantic_alias("/" + path[len(prefix):].removesuffix(".md"))
            if not candidate or not path.startswith(prefix):
                continue
            tree = load_product_tree(record, site, lang, alias=candidate)
            if tree is not None:
                resolved = dict(record, code=tree["alias"].strip("/"), alias=tree["alias"])
                return resolved, tree
            break
    print(f"WARN[product-scope-unverified]: no semantic alias could be verified for "
          f"'{product}'; no product directory is guessed", file=sys.stderr)
    return record, None


def _scoped_index_hits(scored: list, product: str, site: str, lang: str) -> list:
    semantic = bool(_semantic_alias("/" + product))
    kept = [(score, hit) for score, hit in scored
            if (_url_in_product(hit["url"], product, site, lang) if semantic else
                _url_host(hit["url"]) == SITES[site]["result_host"]
                and _url_lang_segment(hit["url"], site) in ("", lang))]
    if len(kept) != len(scored):
        print(f"WARN[index-scope]: dropped {len(scored) - len(kept)} out-of-scope index "
              f"match(es) for '{product}'", file=sys.stderr)
    return kept


def _scan_index_scored(product: str, keyword: str,
                       site: str = DEFAULT_SITE, lang: str = "") -> list | None:
    """Scored index scan: ordered hits, None for a missing index, _IndexUnavailable on retrieval failure.

    Cache-backed (N1) and site+language scoped, never following a redirect
    on the international site (guard S13), so a missing language can not be answered with English.
    """
    lang = lang or SITES[site]["default_lang"]
    record, _tree = _resolve_menu_product(product, site, lang)
    if record is not None:
        if record["category4_id"] is not None and not record["alias"]:
            raise _IndexUnavailable(f"the semantic scope of subproduct '{product}' could not be verified")
        product = record["code"]
    text, _from_cache = _get_llms_text(product, site, lang)
    if not _is_index_corpus(text):
        if _index_failure_code(text) == 2:
            raise _IndexUnavailable(f"llms.txt for '{product}' could not be verified: {_non_corpus_reason(text)}")
        return None
    return _scoped_index_hits(_index_scored_hits(product, text, keyword), product, site, lang)


def _scan_product_index(product: str, keyword: str,
                        site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Index hits, None for no usable index, or _IndexUnavailable for retrieval failure."""
    scored = _scan_index_scored(product, keyword, site, lang)
    if scored is None:
        return None
    return [record for _score, record in scored]


def _scan_product_index_scored(product: str, keyword: str,
                               site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Single-product index scan keeping the scores, for the fusion leg to weigh against ranks."""
    return _scan_index_scored(product, keyword, site, lang)


def _scan_full_index(product: str, keyword: str,
                     site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Scan a product index; [] for no usable index, _IndexUnavailable for retrieval failure.

    Cache-backed since N1: this runs over the whole product list, so without the cache every
    unscoped search re-downloaded the complete catalogue (measured 33 MB across 412 China-site
    indexes) and a second identical run was no faster than the first. Re-reads now cost nothing,
    and the write path enforces the cache size budget in help_cache.
    """
    scored = _scan_index_scored(product, keyword, site, lang)
    if scored is None:
        return []
    return [record for _score, record in scored]


def _index_leg_search(keyword: str, product: str | None,
                      site: str = DEFAULT_SITE, lang: str = ""):
    """llms.txt index leg: with a product, scan that single product; without one, concurrently scan all product indexes.
    Returns hits, None for a product without a usable index, or _IndexUnavailable for retrieval gaps.

    The product set is the site+language menu, so this leg can never pull the other site's catalog.
    """
    if product:
        products = [product]
    else:
        products = menu_product_codes(site, lang)
        if not products:
            raise _IndexUnavailable(f"the product menu of the {SITES[site]['label']} ({lang}) "
                                    f"is unavailable; index coverage could not be verified")
        print(f"INFO: no product specified; scanning {len(products)} product indexes, one request "
              f"each (cold catalogue: the whole China site is ~33 MB); specifying -p <product> "
              f"returns in seconds...", file=sys.stderr)

    if len(products) == 1:
        # Single product: distinguish product-not-exists from no-match to avoid misleading the user
        found = _scan_product_index(products[0], keyword, site, lang)
        if found is None:
            print(f"WARN[no-index]: product '{products[0]}' returned no usable llms.txt index; "
                  f"use list-products to check the documentation scope. This does not prove "
                  f"that the product has no documentation.", file=sys.stderr)
            return None
        return found

    workers = min(INDEX_SCAN_WORKERS, len(products)) or 1
    started = time.monotonic()
    done = 0
    batches = []
    missing = failed = 0

    def scan_product(prod):
        try:
            return _scan_index_scored(prod, keyword, site, lang), False
        except _IndexUnavailable:
            return None, True

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for scored, unavailable in pool.map(scan_product, products):
            done += 1
            failed += int(unavailable)
            missing += int(scored is None and not unavailable)
            batches.append(scored or [])
            # N7: a long unscoped scan must be watchable. Progress goes to stderr only, so a
            # --json run keeps stdout parseable, and the closing line reports the real duration
            # instead of the stale "~10-20s" estimate the intro line used to claim.
            if done % INDEX_SCAN_PROGRESS_EVERY == 0 and done < len(products):
                print(f"INFO: index scan progress {done}/{len(products)} product indexes "
                      f"({time.monotonic() - started:.0f}s elapsed, {workers} workers)",
                      file=sys.stderr)
    found = _merge_scored_scans(batches)
    if missing or failed:
        print(f"WARN[partial-scan]: scanned {len(products) - missing - failed}/{len(products)} "
              f"usable product indexes; {missing} returned no index and {failed} could not be "
              f"verified. Results are not exhaustive.", file=sys.stderr)
    if failed and not found:
        raise _IndexUnavailable("some product indexes could not be verified; no usable matches "
                                "were found within the remaining coverage")
    print(f"INFO: index scan finished over {len(products)} product indexes in "
          f"{time.monotonic() - started:.1f}s", file=sys.stderr)
    return found


def _get_llms_text(product: str, site: str = DEFAULT_SITE, lang: str = "") -> tuple:
    """Get the product llms.txt content of one (site, lang) pair, preferring a non-expired local cache.

    Returns (text, from_cache). On cache miss/expiry/read failure, silently refetch from origin and atomically
    refresh the cache; a body that is not a real index - an error marker ([HTTP ...]/[Error]...), an empty body,
    the international 'no LLMS content yet' placeholder, or a WAF interstitial HTML page - is never cached, so a
    dead slug is not pinned as dead for the whole TTL and a transient WAF answer is not served from cache later.
    Rate-limit/outage local degradation: when the origin fetch fails but an expired local cache exists,
    degrade to the stale cache (non-empty content only) with a WARN, instead of surfacing nothing.
    """
    lang = lang or SITES[site]["default_lang"]
    path = _llms_cache_path(product, site, lang)
    try:
        st = os.stat(path)
        if (st.st_size < LLMS_MAX_BYTES
                and time.time() - st.st_mtime <= LLMS_CACHE_TTL_DAYS * 86400):
            with open(path, encoding="utf-8") as f:
                cached = f.read()
            if _is_index_corpus(cached):
                print(f"INFO[index-cache]: using llms.txt cached on "
                      f"{time.strftime('%Y-%m-%d', time.localtime(st.st_mtime))}; "
                      f"this is an index snapshot, not current document evidence", file=sys.stderr)
                return cached, True
    except OSError:
        pass
    text = _fetch_index(_product_llms_url(site, lang, product), site, lang)
    if _is_index_corpus(text):
        try:
            _trim_llms_cache()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, path)
        except OSError as e:
            print(f"WARN[cache-write]: failed to write the llms.txt cache ({e}); skipping cache this time", file=sys.stderr)
    else:
        # Local degradation on rate limit / outage: serve the expired cache if present
        try:
            with open(path, encoding="utf-8") as f:
                stale = f.read(LLMS_MAX_BYTES)
            if _is_index_corpus(stale) and len(stale.encode("utf-8")) < LLMS_MAX_BYTES:
                print(f"WARN[stale-cache]: llms.txt fetch returned no usable index ({_non_corpus_reason(text)}); "
                      f"degrading to the expired local cache for '{product}' "
                      f"(discovery clues only; current documentation remains unverified)", file=sys.stderr)
                return stale, True
        except OSError:
            pass
    return text, False


# ---------------------------------------------------------------------------
# The `list-docs` subcommand: read a product index and print it, without searching or ranking.
# ---------------------------------------------------------------------------

def list_docs(args) -> int:
    site, lang = _resolve_site_lang(args)
    product = args.product
    record, tree = _resolve_menu_product(product, site, lang)
    docs = None
    tree_failed = False
    if record is not None:
        product = record["code"]
        if record["category4_id"] is not None and not record["alias"]:
            if args.json:
                print("[]")
            return 2
        if record["alias"]:
            tree = tree or load_product_tree(record, site, lang)
            tree_failed = tree is None
            if tree is not None:
                docs = product_tree_docs(tree, product, site, lang)
                tree_failed = docs is None
                print(f"INFO[menu-path]: listing the document tree for '{product}' "
                      f"({site}/{lang}); directory entries are discovery clues, not body evidence",
                      file=sys.stderr)
    if docs is None:
        text, _from_cache = _get_llms_text(product, site, lang)
        if not _is_index_corpus(text):
            code = 2 if tree_failed else _index_failure_code(text)
            print(f"WARN[{'index-unavailable' if code == 2 else 'no-index'}]: product '{product}' "
                  f"returned no usable directory/index ({_non_corpus_reason(text)}); "
                  f"URL: {_product_llms_url(site, lang, product)}. This does not prove missing "
                  f"documentation.", file=sys.stderr)
            if args.json:
                print("[]")
            return code
        scored = [(1, {"title": t, "url": u, "desc": d[:100]})
                  for t, u, d in _DOC_ENTRY_RE.findall(text)]
        docs = [hit for _score, hit in _scoped_index_hits(scored, product, site, lang)]
        print(f"INFO[directory-source]: listing the llms.txt index for '{product}'", file=sys.stderr)
    if not docs:
        print(f"WARN[no-docs]: no usable document entries were returned for '{product}'; "
              "this does not prove missing documentation", file=sys.stderr)
        if args.json:
            print("[]")
        return 2 if tree_failed else 1
    total = len(docs)
    limit = args.max_results if args.max_results > 0 else total
    if args.json:
        print(json.dumps(docs[:limit], ensure_ascii=False, indent=2))
    else:
        print(f"{total} directory entries (showing first {min(limit, total)}):")
        for doc in docs[:limit]:
            print(f"  - {doc['title']}\n    {doc['url']}")
            if doc["desc"]:
                print(f"    {doc['desc'][:80]}")
    if total > limit:
        print(f"... ({total} entries in this directory snapshot, first {limit} shown; "
              f"use -n 0 to show all returned entries, or search -p {product})", file=sys.stderr)
    return 0
