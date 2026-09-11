#!/usr/bin/env python3
"""Shared vocabulary of the skill: constants and (site, language) scope resolution.

Site-neutral by construction: the two portals differ only in the data described here,
never in behaviour, and this module imports nothing from the rest of the package.
"""

from __future__ import annotations

import os
import re
import sys
import uuid
import urllib.error
import urllib.parse
import urllib.request


SKILL_NAME = "alibabacloud-help-doc-search"


# Observability: session-id is a 32-character lowercase hex string, generated once per
# process and appended to every User-Agent header so backend logs can be correlated.
_SESSION_ID = uuid.uuid4().hex


# International-site full-text endpoint. The whole URL is a single hard-coded constant on
# purpose: the site is selected by the explicit "website" query parameter (not by the host),
# and dropping the "/help" path segment returns an HTTP 200 WAF interstitial HTML page
# (~92 KB) instead of JSON, which would silently poison the result set.
SEARCH_JSON_API = "https://www.alibabacloud.com/help/json/search.json"


# Per-site constants (MUST 1.1.2: embedded as constants, never loaded from a data file).
# "llms_base" carries a {lang} placeholder; "path_prefix" is the URL path segment that
# precedes a product slug, used to build product-code extraction regexes and URL needles.
SITES = {
    "cn": {
        "label": "China site",
        "llms_base": "https://help.aliyun.com/{lang}",
        "path_prefix": "/{lang}/",
        "langs": ("zh", "en"),
        "default_lang": "zh",
        "index_timeout": 15,
        "result_host": "help.aliyun.com",
    },
    "intl": {
        "label": "international site",
        "llms_base": "https://www.alibabacloud.com/help/{lang}",
        "path_prefix": "/help/{lang}/",
        "langs": ("en", "zh", "tc", "ja", "id", "pt-br", "fr"),
        "default_lang": "en",
        "index_timeout": 20,
        "result_host": "www.alibabacloud.com",
    },
}


DEFAULT_SITE = "cn"


# Full-text backend contracts. doSearch has no language dimension, so it is used only for
# cn+zh; every other supported (site, lang) pair with a real full-text corpus uses the
# search.json endpoint, including cn+en (its English corpus is unreachable via doSearch).
SEARCH_BACKENDS = {
    "doSearch": {
        "endpoint": "https://t.aliyun.com/abs/search/doSearch",
        "items_path": ("data", "info"),
        "total_path": ("data", "totalCount"),
    },
    "search_json": {
        "endpoint": SEARCH_JSON_API,
        "items_path": ("data", "documents", "data"),
        "total_path": ("data", "documents", "totalCount"),
    },
}


# Languages whose full-text leg returns a real corpus. Any other language silently falls
# back to English server-side (verified: 28/28 combinations returned the English totalCount
# and English URL language segment), so the full-text leg is skipped for them instead.
SEARCH_LANG_WHITELIST = frozenset({"en", "zh"})


# search.json paging bounds (empirically verified on 2026-09-08):
#   pageSize > 200  -> silent degradation, totalCount=0 and the "data" key disappears;
#   pageSize == 1   -> totalCount collapses to 0 when the query hits a product name;
#   pageSize 200    -> 2.5-3.1 s, so the international leg stays at 20-50 items per page.
INTL_SEARCH_PAGESIZE_MIN = 2


INTL_SEARCH_PAGESIZE_MAX = 200


INTL_SEARCH_PAGESIZE_DEFAULT = 50


# Query guard rails for search.json: an empty "keywords" returns the whole-corpus hot list
# (93046 items) and an over-long query silently returns totalCount=0.
MAX_QUERY_LEN = 60


# Language aliases accepted on the command line and normalized before any request.
# "pt" is not a valid code: the real one is "pt-br" ("pt" 302-redirects to an empty body).
LANG_ALIASES = {"pt": "pt-br", "pt_br": "pt-br", "zh-cn": "zh", "en-us": "en"}


# Languages that exist in the front end but have no corpus of their own; their llms.txt is
# byte-identical to English (verified: ko/de master sha256 == en master sha256).
UNSUPPORTED_LANGS = frozenset({"ko", "de", "es", "th", "vi", "tr", "ru", "it"})


# Site-independent OpenAPI metadata endpoint (both sites reference the same contracts).
META_BASE = "https://api.aliyun.com/meta/v1"


# Backwards-compatible aliases for the pre-i18n defaults (cn + zh). They must resolve to the
# exact same strings as before so that a default invocation stays byte-for-byte identical.
LLMS_BASE = SITES[DEFAULT_SITE]["llms_base"].format(lang=SITES[DEFAULT_SITE]["default_lang"])


SEARCH_API = SEARCH_BACKENDS["doSearch"]["endpoint"]


UA_BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QoderWork/1.0"


UA = f"{UA_BROWSER} AlibabaCloud-Agent-Skills/{SKILL_NAME}/{_SESSION_ID}"


TIMEOUT = SITES[DEFAULT_SITE]["index_timeout"]
# Named once so the CLI help text and the request layer cannot drift apart (N3).
DEFAULT_DOC_TIMEOUT = TIMEOUT


SEARCH_TIMEOUT = 8

# Response size caps (N4), each set above the largest legitimate body measured on 2026-09-08
# with at least double headroom: the biggest product index is 1.49 MB (intl/ja/oss, cn/oss
# 0.92 MB), a search.json page at pageSize=200 is 419 KB, and a document body fetched as .md
# peaked at 119 KB. An unexpected response beyond a cap is truncated with a WARN instead of
# being buffered in full.
LLMS_MAX_BYTES = 8 * 1024 * 1024
SEARCH_MAX_BYTES = 2 * 1024 * 1024
DOC_MAX_BYTES = 4 * 1024 * 1024


# categoryId mapping cache: must live in the user directory; never write into the skill directory (platform static checks only allow standard files)
CATEGORY_CACHE_PATH = os.path.expanduser("~/.cache/aliyun-help-search/category_map.json")


CATEGORY_CACHE_TTL_DAYS = 30


# All seeds are empirically verified: oss=31815 (a CORS query narrowed 978 -> 131, all OSS docs);
# functioncompute=2508973 (wide searches with cold-start / Function Compute keywords collected
# /zh/functioncompute/ entries, mode won 8 votes, and precise queries proved the filter effective).
# The remaining entries were verified on 2026-08-28: wide queries collected >=7 /zh/{product}/ votes
# per id, and precise queries with each id returned 10/10 pure product documents.
# When adding seeds, keep references/search-backend.md in sync.
CATEGORY_SEED = {
    "oss": 31815, "functioncompute": 2508973,
    "ecs": 25365, "rds": 26090, "slb": 27537, "vpc": 27706, "cdn": 27099,
    "ack": 85222, "ram": 28625, "sls": 28958, "kms": 28933, "waf": 28515,
    "polardb": 2249963, "maxcompute": 27797,
}


# Local cache for product llms.txt (also user-directory only): every search with -p fetches the full
# product llms.txt (~1MB); cache it for 3 days to avoid repeated downloads; on expiry/read failure,
# silently refetch from origin and refresh.
LLMS_CACHE_DIR = os.path.expanduser("~/.cache/aliyun-help-search/llms")


LLMS_CACHE_TTL_DAYS = 3

# Disk budget of the llms.txt cache (N1). A whole-catalogue walk caches one file per product
# (~78 KB average, 1 MB for the largest), so an unbounded cache grows by ~33 MB per site+language
# scanned; the trim keeps the newest entries and drops the oldest past the budget.
LLMS_CACHE_MAX_BYTES = 300 * 1024 * 1024
LLMS_CACHE_TRIM_TO = 0.8


# Product code alias table: only empirically verified entries are included; the single source of truth
# is the "Aliases and non-obvious codes" table in references/product-codes.md - keep that doc in sync when adding aliases.
# Aliases are NOT split per site: both portals use the same slug for every entry below (verified 2026-09-08).
# fc 301-redirects to functioncompute on both portals. sas -> security-center and alb/nlb/clb -> slb
# are dead-slug repairs: those four slugs answer HTTP 200 with a zero-byte body on both portals, i.e.
# the slug does not exist, so without the alias the user is told "index does not exist" for a product
# that is in fact documented under another slug. 'cs' is deliberately NOT aliased to 'ack': the two are
# distinct live indexes (144461 B vs 90559 B on cn/zh), so collapsing them would discard a working
# corpus and change the historical cn+zh behaviour.
PRODUCT_CODE_ALIASES = {
    "fc": "functioncompute",
    "sas": "security-center",
    "alb": "slb",
    "nlb": "slb",
    "clb": "slb",
}


# Paging is endpoint knowledge and lives with the endpoint: the single-request page size of cn
# doSearch is bounded in help_search_cn (CN_LIMIT_*), the pageSize clamp of the international
# search.json endpoint is _clamp_page_size below (guard S7). Neither leg walks several pages
# any more, so no page-count cap exists. See references/search-backend.md.


# Union of the languages both sites host, in the order used by user-facing error messages.
_ALL_LANGS = ("zh", "en", "tc", "ja", "id", "pt-br", "fr")


# Every language code that can legitimately appear as a URL path segment: the hosted languages
# plus the front-end-only ones the server silently redirects away from. _url_lang_segment uses it
# to tell a language segment from an ordinary first path segment ('document_detail'), which the
# China site puts directly after the host.
_KNOWN_LANG_SEGMENTS = frozenset(_ALL_LANGS) | UNSUPPORTED_LANGS


class _UsageError(Exception):
    """Invalid site/language combination on the command line; main() maps it to exit code 2."""


def _normalize_lang(raw) -> str:
    """Normalize a --lang value: strip, lowercase, apply LANG_ALIASES; return '' when unset.

    Normalization happens before any request so that 'pt' becomes the real code 'pt-br'
    ('pt' would 302-redirect to an empty body) and 'zh-CN'/'EN' collapse to 'zh'/'en'.
    """
    if not raw:
        return ""
    lang = str(raw).strip().lower()
    return LANG_ALIASES.get(lang, lang)


def _infer_site(lang: str) -> str:
    """Infer the site from an explicit --lang when --site was omitted.

    'zh' keeps the historical default (cn) so an unchanged invocation behaves as before;
    'en' selects the international site, whose English corpus is the one with a real
    full-text leg; tc/ja/id/pt-br/fr exist only on the international site.
    """
    if lang == "en":
        return "intl"
    if lang in SITES["cn"]["langs"]:
        return "cn"
    return "intl"


def _resolve_site_lang(args) -> tuple:
    """Resolve and validate the (site, lang) pair from CLI arguments.

    Returns (site, lang). Raises _UsageError for an unknown --site/--lang value or for a
    language the target site does not host (no network request is issued in that case).
    A language that exists in the front end but has no corpus of its own (ko/de/es/th/vi/
    tr/ru/it) is not an error: it WARNs and falls back to the site default language.
    """
    site = (getattr(args, "site", None) or "").strip().lower() or DEFAULT_SITE
    if site not in SITES:
        raise _UsageError(
            f"ERROR: invalid --site value '{site}'. Supported values: {', '.join(SITES)}.")
    raw_lang = getattr(args, "lang", None)
    raw_lower = str(raw_lang).strip().lower() if raw_lang else ""
    lang = _normalize_lang(raw_lang)
    site_explicit = bool((getattr(args, "site", None) or "").strip())
    if not lang:
        return site, SITES[site]["default_lang"]
    if lang != raw_lower:
        # Traced, never an error: 'pt' is the common mistake for the real code 'pt-br' (the bare
        # form 302-redirects to an empty body), and 'zh-CN'/'EN' collapse to 'zh'/'en'.
        print(f"INFO: language '{raw_lower}' normalized to '{lang}'", file=sys.stderr)
    if not site_explicit:
        site = _infer_site(lang)
    supported = SITES[site]["langs"]
    if lang in supported:
        return site, lang
    if lang in UNSUPPORTED_LANGS:
        fallback = SITES[site]["default_lang"]
        print(f"WARN[lang-fallback]: language '{lang}' is not supported (supported: {', '.join(supported)}); "
              f"falling back to '{fallback}'. Results are in {fallback}, not {lang}.",
              file=sys.stderr)
        return site, fallback
    # Name the site only when the user actually passed --site; otherwise the site was inferred
    # from --lang and quoting it would claim a flag the user never wrote.
    scope = f" for --site {site}" if site_explicit else ""
    raise _UsageError(
        f"ERROR: unsupported --lang '{lang}'{scope}. "
        f"Supported languages for cn: {', '.join(SITES['cn']['langs'])}. "
        f"Supported languages for intl: {', '.join(SITES['intl']['langs'])}.")


def _llms_base(site: str, lang: str) -> str:
    """Root URL of a site+language llms.txt tree, e.g. https://help.aliyun.com/zh."""
    return SITES[site]["llms_base"].format(lang=lang)


def _path_prefix(site: str, lang: str) -> str:
    """URL path segment preceding a product slug, e.g. '/zh/' (cn) or '/help/en/' (intl)."""
    return SITES[site]["path_prefix"].format(lang=lang)


def _master_llms_url(site: str, lang: str) -> str:
    """Master (root) llms.txt URL of a site+language pair."""
    return f"{_llms_base(site, lang)}/llms.txt"


def _product_llms_url(site: str, lang: str, product: str) -> str:
    """Product-level llms.txt URL of a site+language pair."""
    return f"{_llms_base(site, lang)}/{product}/llms.txt"


def _needle(site: str, lang: str, product: str) -> str:
    """URL substring that identifies a product on a given site+language, e.g. '/zh/oss/'.

    Site-scoped on purpose: the same slug on the two sites is a different corpus, so a
    needle built for one site must never match the other site's URLs.
    """
    return f"{_path_prefix(site, lang)}{product}/"


def _product_code_regexes(site: str, lang: str) -> tuple:
    """(product-html regex, document_detail-html regex, slug regex) for extracting a product code.

    All three are anchored on the site+language path prefix, which also excludes the master
    preamble section (its links point at '/help/{lang}/llms.txt', i.e. one segment short)
    and any cross-site link (a different host).

    The master indexes list every product under one of three path shapes, measured on
    2026-09-08 over the cn/zh and intl/en masters:
      /{lang}/{slug}/llms.txt                     218 cn/zh, most of intl
      /{lang}/product/{id}.html/llms.txt           64 cn/zh
      /{lang}/document_detail/{id}.html/llms.txt  178 cn/zh (38.7% of the catalog)
    The numeric legacy shape carries no slug, so its product code is the whole two-segment
    tail; that string round-trips through _product_llms_url() unchanged and reaches a
    collision-free cache file through _llms_cache_path() (which escapes '/' to '_').
    """
    prefix = re.escape(_path_prefix(site, lang))
    return (re.compile(prefix + r"product/([^/]+)\.html/llms\.txt"),
            re.compile(prefix + r"(document_detail/[^/]+\.html)/llms\.txt"),
            re.compile(prefix + r"([^/]+)/llms\.txt"))


def _product_code_from_llms_url(url: str, site: str, lang: str) -> str:
    """Normalized product code of a product-level llms.txt URL, or '' when it is not one.

    Covers all three shapes listed by _product_code_regexes(); '' means the URL is the master
    preamble (one segment short) or belongs to the other portal, so a caller must skip it
    instead of scanning a foreign-site index.
    """
    product_html_re, doc_detail_re, slug_re = _product_code_regexes(site, lang)
    m = product_html_re.search(url)
    if m:
        return f"product/{m.group(1)}.html"
    m = doc_detail_re.search(url)
    if m:
        return m.group(1)
    m = slug_re.search(url)
    return m.group(1) if m else ""


def _doc_url_regex(site: str, lang: str):
    """Regex matching a product-level llms.txt URL of this site+language inside master text."""
    base = re.escape(_llms_base(site, lang))
    return re.compile(r"\((" + base + r"/[^)]+/llms\.txt)\)")


# N3: a caller may widen or narrow every request deadline from the command line (0 = keep the
# per-endpoint default). The override is applied only through effective_timeout(), so no call
# site carries its own timeout arithmetic.
_cli_timeout = 0


def set_cli_timeout(seconds) -> None:
    """Record the --timeout override; a non-positive or unparsable value means 'no override'."""
    global _cli_timeout
    try:
        _cli_timeout = int(seconds or 0)
    except (TypeError, ValueError):
        _cli_timeout = 0
    if _cli_timeout < 0:
        _cli_timeout = 0


def effective_timeout(base: int) -> int:
    """Deadline of one request: the CLI override when given, else the endpoint's own value."""
    return _cli_timeout if _cli_timeout > 0 else base


# N8: the short-TTL full-text result cache is on by default and disabled per run by
# --no-result-cache, so a caller can force live endpoint behaviour for one invocation.
_result_cache_off = False


def set_result_cache(enabled) -> None:
    """Record the --no-result-cache choice (anything falsy disables the cache)."""
    global _result_cache_off
    _result_cache_off = not bool(enabled)


def result_cache_enabled() -> bool:
    """Whether a full-text result set may be reused inside the short TTL window."""
    return not _result_cache_off


def _search_backend(site: str, lang: str) -> str | None:
    """Full-text backend id for a (site, lang) pair, or None when the leg must be skipped.

    doSearch serves cn+zh only (it has no language dimension). search.json serves intl en/zh
    and cn+en. Any other language silently falls back to English server-side, so the caller
    skips the full-text leg and relies on the index leg instead (guard S3).
    """
    if lang not in SEARCH_LANG_WHITELIST:
        return None
    if site == "cn" and lang == "zh":
        return "doSearch"
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


def _url_host(url: str) -> str:
    """Lowercase host of a URL ('' when unparsable); used by the site-purity guard S1."""
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _url_lang_segment(url: str, site: str) -> str:
    """Language segment of a result URL on a given site ('' when the shape is unexpected).

    cn shape:   https://help.aliyun.com/{lang}/{product}/...
    intl shape: https://www.alibabacloud.com/help/{lang}/{product}/...
    Used by guard S2 to detect the silent server-side fallback to English.

    The candidate segment is accepted only when it is a known language code: the China site also
    serves the legacy 'https://help.aliyun.com/document_detail/{id}.html' shape (measured 2/119
    doSearch items), whose first path segment is not a language. Such an URL carries no evidence
    of a language fallback, so '' means 'no opinion' and S2 keeps the item.
    """
    head, _, _tail = _path_prefix(site, "{lang}").partition("{lang}")
    path = urllib.parse.urlsplit(url).path
    if not path.startswith(head):
        return ""
    rest = path[len(head):]
    if "/" not in rest:
        return ""
    candidate = rest.split("/")[0]
    return candidate if candidate in _KNOWN_LANG_SEGMENTS else ""


def _strip_help_prefix(value) -> str:
    """Strip the 'help@@' namespace prefix both search backends put on categoryName.

    Returns '' for a missing/non-string value. Without this the customer-facing output
    would read 'help@@Object Storage Service'.
    """
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if "@@" in text:
        text = text.split("@@")[-1].strip()
    return text


# CJK ranges used by guard S12; the check is a plain range test so no segmentation dependency
# is needed (and the ranges are functional retrieval data, not user-facing copy).
_CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def _has_cjk(text: str) -> bool:
    """True when the text contains a Chinese/Japanese/Korean character (guard S12)."""
    return bool(_CJK_RE.search(text or ""))


def _scope_explicit(args) -> bool:
    """True when the user passed --site or --lang explicitly.

    Only an explicitly scoped invocation annotates its output with the site and the language:
    a default invocation must stay byte-for-byte identical to the pre-i18n behaviour, which
    predates any scope annotation.
    """
    return bool((getattr(args, "site", None) or "").strip()
                or (getattr(args, "lang", None) or "").strip())


def _annotate_scope(records: list, site: str, lang: str) -> list:
    """Tag every output record with its (site, lang) so a result set can never be mistaken for
    the other site's corpus (the two sites document different products, regions and prices)."""
    for rec in records:
        if isinstance(rec, dict):
            rec["site"] = site
            rec["lang"] = lang
    return records


# Entry shapes shared by every llms.txt parser in this file (master list, catalog listing and
# the two index-leg scanners) so the three paths can never disagree about what an entry is.
# The ': summary' part is OPTIONAL on purpose: a required summary group hid every entry that
# carries none, which is 492 of 4359 lines (11.3%) in the cn/zh OSS index and 198 of 1568
# (12.6%) in ECS (measured 2026-09-08). Most of them are navigation nodes, but a navigation
# node is still a real catalog entry the caller may want to descend into, and 6 of the 461
# master entries have no summary either. re.findall() yields '' for the absent group, so every
# downstream 'desc[:120]' / 'desc.lower()' stays safe.
_MASTER_ENTRY_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\)(?::\s*(.*))?$", re.MULTILINE)


_DOC_ENTRY_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\)(?::\s*(.*))?$", re.MULTILINE)


def _extract_items(data, backend: str) -> list:
    """Result list of a search response, read through the backend's own path (C16).

    doSearch nests it two levels deep (data.info); search.json three (data.documents.data).
    Reading the wrong path yields an empty list, which the caller would trust as a legitimate
    "no results" answer, so the path belongs to the backend contract and is never hard-coded
    at the call site.
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
