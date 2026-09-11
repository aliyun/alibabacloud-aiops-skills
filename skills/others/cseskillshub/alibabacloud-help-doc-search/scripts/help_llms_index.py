#!/usr/bin/env python3
"""llms.txt catalog layer: master/product parsing and the index-leg scanners.

Products are listed under three URL shapes on both masters and all of them resolve
through help_core._product_code_from_llms_url, so enumeration and scanning can never
disagree about what a product is.
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from help_cache import (
    _get_llms_text,
    _llms_cache_path,
)
from help_core import (
    DEFAULT_SITE,
    SITES,
    _DOC_ENTRY_RE,
    _MASTER_ENTRY_RE,
    _doc_url_regex,
    _master_llms_url,
    _product_code_from_llms_url,
    _product_llms_url,
    _resolve_site_lang,
)
from help_http import (
    _fetch_index,
    _is_err,
    _is_index_corpus,
    _non_corpus_reason,
)
from help_query import (
    _normalize_product_code,
)


# Budget of an unscoped index scan (N2): the whole-catalogue walk used 16 parallel connections
# with no backoff, which is the harshest pattern the help endpoints have ever been observed
# under and has no SLA behind it; 8 keeps the cold scan under half a minute while halving the
# instantaneous pressure. Progress cadence is the N7 feedback interval.
INDEX_SCAN_WORKERS = 8
INDEX_SCAN_PROGRESS_EVERY = 100

# F3: lightweight relevance for the index leg, which used to answer in catalogue order. The
# weights are ordinal, not calibrated: an exact full-query hit in a title is worth more than any
# amount of partial coverage, and title coverage is worth more than summary coverage because a
# title is what the documentation author chose to name the page with.
_INDEX_TITLE_EXACT = 4.0
_INDEX_DESC_EXACT = 2.0
_INDEX_TITLE_COVERAGE = 3.0
_INDEX_DESC_COVERAGE = 1.5
_INDEX_HAS_SUMMARY = 0.5
# A partial match must cover at least this share of the query's tokens. Without the floor, a
# single common bigram ("配置", "管理") matches a whole product index: measured 2026-09-09, a
# four-character Chinese query matched 3881 of 4359 OSS entries on the English index.
_INDEX_MIN_COVERAGE = 0.34
# Reference scale for the fusion leg: the index score that earns the full cross-leg bonus. The
# theoretical maximum of `_index_score` is 9.0 (4.0 title-exact + 3.0 full title coverage + 1.5
# full summary coverage + 0.5 has-summary); a title-exact hit with complete title coverage
# measures 7.5, so 8.0 keeps a genuinely on-topic entry at the whole bonus while a weak
# bigram-only match (around 2.0) earns a quarter of it.
_INDEX_FUSION_FULL_SCORE = 8.0
# Tokens of a query that carry no topical meaning; matching on them produces noise.
_INDEX_STOP_TOKENS = {"the", "a", "an", "of", "to", "for", "and", "in", "on", "with", "how",
                     "do", "i", "is", "are", "what", "please", "一下", "如何", "怎么", "什么是"}


def _index_tokens(query: str) -> list:
    """Meaningful matching units of a query: latin words, and CJK character bigrams.

    CJK text is split into overlapping two-character units because Chinese documents have no word
    boundaries and a whole-string substring match misses every query that is phrased differently
    from the title (measured: '什么是传输加速' and '跨域访问怎么配' recalled zero entries before F3,
    while the individual characters appear all over the index). Bigrams keep the match localised
    instead of degrading into single-character noise.
    """
    text = (query or "").strip().lower()
    if not text:
        return []
    tokens = [t for t in re.split(r"[^0-9a-z_\u4e00-\u9fff]+", text) if t]
    out = []
    for token in tokens:
        if token in _INDEX_STOP_TOKENS:
            continue
        if re.search(r"[\u4e00-\u9fff]", token):
            if len(token) == 1:
                out.append(token)
            else:
                out.extend(token[i:i + 2] for i in range(len(token) - 1))
        else:
            out.append(token)
    return out


def _index_score(query: str, title: str, desc: str) -> float:
    """Relevance of one index entry to a query (0.0 means "not a hit", same as before F3)."""
    title_l = (title or "").lower()
    desc_l = (desc or "").lower()
    whole = (query or "").strip().lower()
    score = 0.0
    if whole and whole in title_l:
        score += _INDEX_TITLE_EXACT
    elif whole and whole in desc_l:
        score += _INDEX_DESC_EXACT
    tokens = _index_tokens(whole)
    if tokens:
        uniq = list(dict.fromkeys(tokens))
        title_hits = sum(1 for t in uniq if t in title_l)
        desc_hits = sum(1 for t in uniq if t in desc_l)
        # A pure partial match has to carry enough of the query to be about it at all; an exact
        # hit on the whole query is already scored above and is kept whatever the coverage is.
        best_ratio = max(title_hits, desc_hits) / len(uniq)
        if score == 0.0 and best_ratio < _INDEX_MIN_COVERAGE:
            return 0.0
        score += _INDEX_TITLE_COVERAGE * title_hits / len(uniq)
        score += _INDEX_DESC_COVERAGE * desc_hits / len(uniq)
    if score and (desc or "").strip():
        score += _INDEX_HAS_SUMMARY
    return round(score, 4)


def _index_scored_hits(product: str, text: str, keyword: str) -> list:
    """Collect the matching entries of one index as `[(score, record)]`, best first (F3).

    The score is kept here because two callers need different things from it: the unscoped scan
    has to compare candidates across products, and the fusion leg has to weigh an index-leg hit
    against a full-text rank. Records themselves stay score-free so `--json` keeps its shape.
    The sort is stable, so equally scored entries keep their catalogue order.
    """
    scored = []
    for title, url, desc in _DOC_ENTRY_RE.findall(text):
        score = _index_score(keyword, title, desc)
        if score > 0:
            scored.append((score, {"product": product, "title": title, "url": url,
                                   "desc": desc[:120], "source": "index"}))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored


def _index_hits(product: str, text: str, keyword: str) -> list:
    """The matching entries of one index, ordered by relevance; records only, no score field.

    Records are truncated by the caller after this ordering.
    """
    return [record for _score, record in _index_scored_hits(product, text, keyword)]


def parse_site_matrix(text: str) -> list:
    """The 'available sites and languages' block of a master index, as [{label, url}] (F10).

    Both masters publish their own site x language table, which is the only self-describing
    statement of what the portals claim to host. It is presented as read-only display and is
    never a runtime dependency: the site dictionary in help_core stays the source of truth, so a
    change to that block cannot break any code path, and a master without the block simply
    yields an empty list.
    """
    body = text or ""
    match = re.search(r"^##[^\n]*(?:\u7ad9\u70b9\u4e0e\u8bed\u8a00|Sites and Languages)[^\n]*\n(.*?)(?=\n## |\Z)",
                      body, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    rows = []
    for line in match.group(1).splitlines():
        found = re.search(r"\[([^\]]+)\]\((https://[^)]+/llms\.txt)\)", line)
        if not found:
            continue
        # The masters write the site name before the link ("中国站 (中文) - [llms.txt](...)"), so
        # the leading text is the label and the link text is a constant 'llms.txt'.
        lead = line[: found.start()].strip(" -*\t")
        rows.append({"label": lead or found.group(1).strip(), "url": found.group(2)})
    return rows


def list_products(args) -> int:
    """List all available products and their codes of one (site, language) pair."""
    site, lang = _resolve_site_lang(args)
    text = _fetch_index(_master_llms_url(site, lang), site, lang)
    if _is_err(text):
        print(text)
        return 2
    if not text.strip():
        # A path that does not exist answers HTTP 200 with an empty body; that must never be
        # reported as "this site has no products".
        print(f"WARN[no-corpus]: the master llms.txt of the {SITES[site]['label']} ({lang}) returned an "
              f"empty body (HTTP 200); no product list is available", file=sys.stderr)
        return 1

    # Parse product entries: - [name](url): description
    matches = _MASTER_ENTRY_RE.findall(text)
    if not matches:
        # A master index that parses to zero entries is never a genuine "this portal lists no
        # product": both portals list 200+ of them. It means the body was an interstitial page
        # served under rate limiting, so the degradation is reported instead of printing nothing
        # and exiting 0 as if the empty answer were trustworthy.
        print(f"WARN[no-corpus]: the master llms.txt of the {SITES[site]['label']} ({lang}) returned "
              f"{len(text)} byte(s) but no parsable product entry "
              f"({_non_corpus_reason(text)}); no product list is available", file=sys.stderr)
        return 1
    # All three product-code shapes resolve through one helper so list-products can not report a
    # code the index leg would then refuse to scan.
    def extract_code(url: str) -> str:
        """Extract the product code from an llms.txt URL of this site+language."""
        return _product_code_from_llms_url(url, site, lang)

    if args.json:
        products = []
        for name, url, desc in matches:
            code = extract_code(url)
            products.append({"name": name, "code": code, "url": url, "desc": desc[:80]})
        print(json.dumps(products, ensure_ascii=False, indent=2))
    else:
        for name, url, desc in matches:
            code = extract_code(url) or "(unknown)"
            short_desc = desc[:60] + "..." if len(desc) > 60 else desc
            print(f"  {code:<30s} {name}")
            if args.verbose and short_desc:
                print(f"    {short_desc}")
    if getattr(args, "show_sites", False):
        # F10: display only; the catalogue above stays the authority for what can be queried.
        rows = parse_site_matrix(text)
        if rows:
            print(f"\nSites and languages published by this master index ({len(rows)} entries):")
            for row in rows:
                print(f"  {row['label']:<28s} {row['url']}")
            print("This list is informational: the queryable sites and languages of this tool "
                  "are cn (zh, en) and intl (en, zh, tc, ja, id, pt-br, fr experimental).")
        else:
            print("INFO: this master index publishes no 'available sites and languages' block; "
                  "nothing to show", file=sys.stderr)
    return 0


def list_docs(args) -> int:
    """List the full doc catalog of a product (truncated to the first N entries by default to prevent context bloat)."""
    site, lang = _resolve_site_lang(args)
    product = _normalize_product_code(args.product)
    text, from_cache = _get_llms_text(product, site, lang)
    if from_cache:
        print(f"INFO: llms.txt served from local cache {_llms_cache_path(product, site, lang)}", file=sys.stderr)
    if _is_err(text):
        print(text)
        return 2

    # Parse entries
    matches = _DOC_ENTRY_RE.findall(text) if text.strip() else []

    if not matches:
        print(f"No doc index found for product '{product}'; please check whether the product code is correct.")
        print(f"URL: {_product_llms_url(site, lang, product)}")
        other = "cn" if site == "intl" else "intl"
        print(f"WARN[site-cross]: product '{product}' has no documentation on the {SITES[site]['label']} "
              f"({SITES[site]['result_host']}, language '{lang}'). It may exist on the "
              f"{SITES[other]['label']}: retry with '--site {other}' if you need it. "
              f"No automatic site fallback is performed.", file=sys.stderr)
        return 1

    total = len(matches)
    limit = args.max_results if args.max_results > 0 else total

    if args.json:
        docs = [{"title": t, "url": u, "desc": d[:100]} for t, u, d in matches[:limit]]
        print(json.dumps(docs, ensure_ascii=False, indent=2))
        if total > limit:
            print(f"... ({total} entries in total, first {limit} shown; use -n 0 to show all, or search -p {product} for a precise search)",
                  file=sys.stderr)
        return 0

    # Group by category (terminate early at the truncation cap to avoid dumping tens of thousands of lines)
    print(f"{total} docs in total (showing first {min(limit, total)}):")
    printed = 0
    current_section = ""
    for line in text.split("\n"):
        if printed >= limit:
            break
        line_s = line.strip()
        if line_s.startswith("## "):
            current_section = line_s
            print(f"\n{current_section}")
        elif line_s.startswith("- ["):
            m = _DOC_ENTRY_RE.match(line_s)
            if m:
                title, url = m.group(1), m.group(2)
                # An optional group that did not participate comes back as None from match()
                # (only findall substitutes ''), so an entry without a summary must read as empty.
                desc = m.group(3) or ""
                short_desc = desc[:80] + "..." if len(desc) > 80 else desc
                print(f"  - {title}")
                print(f"    {url}")
                if short_desc:
                    print(f"    {short_desc}")
                printed += 1
    if total > limit:
        print(f"\n... ({total} entries in total, first {limit} shown; use -n 0 to show all, or search -p {product} for a precise search)")
    return 0


def _scan_index_scored(product: str, keyword: str,
                       site: str = DEFAULT_SITE, lang: str = "") -> list:
    """Scored index scan of one product: `[(score, record)]` best first, or None when the product
    index does not exist. Cache-backed (N1) and site+language scoped, never following a redirect
    on the international site (guard S13), so a missing language can not be answered with English.
    """
    text, _from_cache = _get_llms_text(product, site, lang)
    if not _is_index_corpus(text):
        return None
    return _index_scored_hits(product, text, keyword)


def _merge_scored_scans(batches: list) -> list:
    """Merge per-product scored scans of an unscoped search into one relevance-ordered list.

    Before this existed the unscoped index leg concatenated products in master-index order, so a
    weak bigram match inside an early product outranked an exact title hit in a later one (measured
    2026-09-09: an unscoped Chinese query for "server side encryption" ranked an API endpoint-list
    page above the object-storage encryption documents). The sort is stable, so equal scores keep
    the previous catalogue order and a rerun of the same candidates is deterministic.
    """
    pooled = []
    for batch in batches:
        pooled.extend(batch or [])
    pooled.sort(key=lambda pair: pair[0], reverse=True)
    return [record for _score, record in pooled]


def _scan_product_index(product: str, keyword: str,
                        site: str = DEFAULT_SITE, lang: str = "") -> list:
    """llms.txt index leg: title+summary relevance scan for a single product (via the local cache layer).
    Return None when the index does not exist; return [] when nothing matches."""
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
    """Scan a single product's llms.txt index and return its records; [] on index anomalies.

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
    Returns a list; when a single product's index does not exist, emit a warning and return None (caller terminates).

    The master index and both product-code regexes are site+language scoped, so this leg can never
    pull the other site's catalog. For cn+zh the generated URL pattern is character-identical to
    the historical hard-coded one.
    """
    if product:
        products = [product]
    else:
        # Fetch master index to get all product llms.txt URLs
        master = _fetch_index(_master_llms_url(site, lang), site, lang)
        if _is_err(master):
            print(master)
            return None
        if not master.strip():
            print(f"WARN[no-corpus]: the master llms.txt of the {SITES[site]['label']} ({lang}) returned an "
                  f"empty body (HTTP 200); the index leg has no product list to scan",
                  file=sys.stderr)
        # Every product of this site+language, in whichever of the three URL shapes the master lists it.
        # De-duplicated: the master repeats a product across sections (460 links but 412 distinct
        # products on cn/zh, measured 2026-09-08), and a duplicate would be a wasted ~78 KB fetch.
        url_pattern = _doc_url_regex(site, lang)
        products = list(dict.fromkeys(
            code for code in (_product_code_from_llms_url(u, site, lang)
                              for u in url_pattern.findall(master)) if code))
        print(f"INFO: no product specified; scanning {len(products)} product indexes, one request "
              f"each (cold catalogue: the whole China site is ~33 MB); specifying -p <product> "
              f"returns in seconds...", file=sys.stderr)
        if not products:
            # Never let a zero-product scan masquerade as a trustworthy empty result: both master
            # indexes list 200+ products, so an empty scan set means the body was not a real index.
            reason = (_non_corpus_reason(master) if not _is_index_corpus(master)
                      else "no product link matched this site+language URL pattern")
            print(f"WARN[no-corpus]: the master llms.txt of the {SITES[site]['label']} ({lang}) yielded no "
                  f"product index URL to scan ({reason}); the index leg has nothing to walk, so "
                  f"this run reports a degraded empty result rather than a real no-match",
                  file=sys.stderr)

    if len(products) == 1:
        # Single product: distinguish product-not-exists from no-match to avoid misleading the user
        found = _scan_product_index(products[0], keyword, site, lang)
        if found is None:
            print(f"[warning] the doc index of product '{products[0]}' does not exist; please use list-products to verify the product code.")
            return None
        return found

    workers = min(INDEX_SCAN_WORKERS, len(products)) or 1
    started = time.monotonic()
    done = 0
    batches = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for scored in pool.map(lambda prod: _scan_index_scored(prod, keyword, site, lang), products):
            done += 1
            # Scores are collected per product and only compared at the end: an exact title hit in
            # a product scanned late must not lose to a bigram match in one scanned early.
            batches.append(scored or [])
            # N7: a long unscoped scan must be watchable. Progress goes to stderr only, so a
            # --json run keeps stdout parseable, and the closing line reports the real duration
            # instead of the stale "~10-20s" estimate the intro line used to claim.
            if done % INDEX_SCAN_PROGRESS_EVERY == 0 and done < len(products):
                print(f"INFO: index scan progress {done}/{len(products)} product indexes "
                      f"({time.monotonic() - started:.0f}s elapsed, {workers} workers)",
                      file=sys.stderr)
    found = _merge_scored_scans(batches)
    print(f"INFO: index scan finished over {len(products)} product indexes in "
          f"{time.monotonic() - started:.1f}s", file=sys.stderr)
    return found
