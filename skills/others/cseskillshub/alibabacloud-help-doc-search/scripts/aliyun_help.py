#!/usr/bin/env python3
# SECURITY: Read-only tool. It only issues HTTPS GET requests to public Alibaba Cloud
# endpoints (help.aliyun.com, api.aliyun.com, t.aliyun.com); it never sends credentials,
# PII, or any mutating request.
"""Alibaba Cloud Help Center search and OpenAPI metadata verification tool.

Usage:
  # Help Center docs (help.aliyun.com, narrative documentation)
  python3 aliyun_help.py list-products          # List all products
  python3 aliyun_help.py list-docs <product>    # List a product's doc catalog (first 100 by default)
  python3 aliyun_help.py search <keyword> [-p product]  # Search docs (concurrent full scan when no product is given)
  python3 aliyun_help.py read <url>             # Read a document body
  python3 aliyun_help.py read-product <product> # Read a product's raw llms.txt

  # OpenAPI metadata (api.aliyun.com/meta, structured API contracts for precise verification)
  python3 aliyun_help.py api-products [keyword]         # List OpenAPI product codes and versions
  python3 aliyun_help.py api-list <product> [keyword]   # List all APIs of a product
  python3 aliyun_help.py api-info <product> <ApiName>   # Parameters/error codes/RAM permission points of a single API
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

LLMS_BASE = "https://help.aliyun.com/zh"
META_BASE = "https://api.aliyun.com/meta/v1"
SEARCH_API = "https://t.aliyun.com/abs/search/doSearch"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) QoderWork/1.0"
TIMEOUT = 15
SEARCH_TIMEOUT = 8

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

# Product code alias table: only empirically verified entries are included; the single source of truth
# is the "Aliases and non-obvious codes" table in references/product-codes.md — keep that doc in sync when adding aliases.
PRODUCT_CODE_ALIASES = {"fc": "functioncompute"}

# The doSearch backend truly caps each page at 10 items: only the precise categoryId path paginates when limit>10, with a cap of 3 pages
SEARCH_PAGE_CAP = 10
SEARCH_MAX_PAGES = 3

# ---------------- Query construction: alias dictionary / error-code detection / low-result expansion retry ----------------

# Bidirectional query alias/synonym dictionary (high-frequency product aliases, Chinese-English pairs):
# alias-level expansion only, no general translation. When any alias of a group appears in the query,
# the other aliases of the group can drive an expansion retry (see _expand_query).
# Confirm official naming before adding entries, and keep the mechanism notes in references/query-construction.md in sync.
QUERY_SYNONYMS = [
    ("EIP", "弹性公网IP"),
    # Common truncated form (without the IP suffix); works together with the group above: longest match wins, no duplicate expansion
    ("EIP", "弹性公网"),
    ("SLB", "负载均衡"),
    ("OSS", "对象存储"),
    ("ECS", "云服务器"),
    ("CDN", "内容分发网络"),
    ("VPC", "专有网络"),
    ("RDS", "云数据库RDS"),
    ("serverless", "函数计算"),
    ("NAS", "文件存储NAS"),
    ("ACK", "容器服务Kubernetes版"),
    ("SLS", "日志服务"),
    ("RAM", "访问控制"),
    ("KMS", "密钥管理服务"),
    ("WAF", "Web应用防火墙"),
    ("DNS", "域名解析"),
    ("PolarDB", "云原生数据库PolarDB"),
    ("MaxCompute", "ODPS"),
    ("MaxCompute", "大数据计算"),
    # High-frequency concept terms (document titles may use either form)
    ("CORS", "跨域"),
    ("security group", "安全组"),
    ("snapshot", "快照"),
]

# Low-result expansion retry threshold: when the first round returns fewer items than this value and the dictionary can generate a different expanded query, retry once with the expanded term
EXPAND_RETRY_THRESHOLD = 2

# CamelCase error-code shape (e.g. SignatureDoesNotMatch / InvalidAccessKeyId):
# at least two capitalized segments, naturally containing internal capitals
ERROR_CODE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+$")

# Chinese colloquial error wording -> canonical CamelCase error code (hint bridge only):
# users often paste a translated/colloquial description instead of the code; the hint points
# them at the verbatim code form, which is what documentation search actually matches.
ERROR_CODE_CN_HINTS = [
    ("签名不匹配", "SignatureDoesNotMatch"),
    ("签名错误", "SignatureDoesNotMatch"),
    ("访问密钥不存在", "InvalidAccessKeyId.NotFound"),
    ("密钥不存在", "InvalidAccessKeyId.NotFound"),
    ("请求被限流", "Throttling"),
    ("没有权限", "Forbidden.RAM"),
    ("资源不存在", "InvalidParameter.NotFound"),
]


def _build_synonym_lookup(pairs) -> dict:
    """Build a bidirectional dictionary from alias pairs: each alias (lowercased key) maps to all aliases of its group (original casing preserved)."""
    lookup = {}
    for a, b in pairs:
        for alias in (a, b):
            lookup.setdefault(alias.lower(), set()).update((a, b))
    return lookup


_SYNONYM_LOOKUP = _build_synonym_lookup(QUERY_SYNONYMS)
# ASCII alphanumeric boundary check: avoids false matches inside English words ("words" does not match rds),
# while still allowing direct adjacency to CJK text (the alias still matches inside a longer Chinese phrase)
_SYNONYM_PATTERNS = {
    key: re.compile(r"(?<![A-Za-z0-9])" + re.escape(key) + r"(?![A-Za-z0-9])", re.IGNORECASE)
    for key in _SYNONYM_LOOKUP
}


def _expand_query(keyword: str) -> str | None:
    """Alias-level expansion: generate one expanded query different from the original; return None on no dictionary hit.

    Deterministic strategy: take the longest alias matched in the query, then append the first not-yet-present
    alias of the same group (shortest first; sorted to guarantee determinism) to the end of the original query
    (append-only; the original text is never removed; no general translation).
    """
    matched = [key for key, pat in _SYNONYM_PATTERNS.items() if pat.search(keyword)]
    if not matched:
        return None
    best = max(matched, key=len)
    for alias in sorted(_SYNONYM_LOOKUP[best], key=lambda a: (len(a), a)):
        if alias.lower() == best:
            continue
        if _SYNONYM_PATTERNS[alias.lower()].search(keyword):
            continue
        return keyword.strip() + " " + alias
    return None


def _error_code_hint(keyword: str) -> None:
    """CamelCase error-code detection: when the whole query or any token matches the error-code shape, emit an INFO hint on stderr.
    Hint only; the search behavior itself is unchanged (error codes are still searched verbatim).
    All-uppercase abbreviations (e.g. KMS/WAF) are not CamelCase error-code shapes and never trigger the hint.
    Chinese colloquial error wording triggers the hint bridge: it suggests the canonical CamelCase
    code but never rewrites the query (error codes must be searched verbatim)."""
    stripped = keyword.strip()
    tokens = [t for t in re.split(r"\s+", stripped) if t]
    for cand in [stripped] + tokens:
        if ERROR_CODE_RE.match(cand) and not cand.isupper():
            print("INFO: suspected error code detected; it will be searched verbatim as an error code. "
                  "For the contract-level error code list of a specific API, use api-info <product> <ApiName>",
                  file=sys.stderr)
            return
    for phrase, code in ERROR_CODE_CN_HINTS:
        if phrase in stripped:
            print(f"INFO: colloquial error wording detected; if it refers to the '{code}' error, "
                  f"search the code verbatim (e.g. search \"{code}\") for narrative troubleshooting docs",
                  file=sys.stderr)
            return


def _merge_unique(primary: list, extra: list) -> list:
    """Merge two rounds of search results and dedupe by normalized URL (first-round order preserved; new second-round entries appended)."""
    seen = set()
    merged = []
    for rec in list(primary) + list(extra):
        key = _normalize_url(rec["url"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)
    return merged


def _expand_retry(initial: list, keyword: str, run_search) -> list:
    """Low-result expansion retry: when the first round has fewer than EXPAND_RETRY_THRESHOLD results and
    _expand_query can generate a different expanded query, retry once with the expanded term, then merge and
    dedupe with the first-round results; on no dictionary hit or retry failure/empty result, return unchanged.
    The retry inherits the current path semantics (carried by the run_search(kw) closure)."""
    if len(initial) >= EXPAND_RETRY_THRESHOLD:
        return initial
    expanded = _expand_query(keyword)
    if expanded is None:
        return initial
    print(f"INFO: insufficient results for the original query ({len(initial)}); retried with expanded term: {expanded}", file=sys.stderr)
    retry = run_search(expanded.lower())
    return _merge_unique(initial, retry or [])


def fetch(url: str, max_bytes: int = 0) -> str:
    """Fetch URL content as text."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read()
            if max_bytes > 0:
                data = data[:max_bytes]
            return data.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {e.reason}"
    except Exception as e:
        return f"[Error] {e}"


def _is_err(text: str) -> bool:
    """Determine whether a fetch result is an error marker (avoids the legacy startswith('[') falsely matching normal Markdown)."""
    return text.startswith("[HTTP ") or text.startswith("[Error]")


def _looks_like_html(text: str) -> bool:
    """Detect the HTTP 200-but-HTML-page case (help.aliyun.com falls back to an SPA page when a doc moves or a slug is dead)."""
    head = text.lstrip()[:300].lower()
    return head.startswith("<!doctype") or head.startswith("<html") or "<html" in head


def _strip_html(text: str) -> str:
    """Strip HTML tags, unescape entities and collapse consecutive whitespace; used to clean search snippets."""
    s = re.sub(r"<[^>]+>", "", text or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _normalize_product_code(product) -> str:
    """Normalize product code aliases (e.g. fc -> functioncompute).

    The alias table only contains empirically verified entries; the single source of truth is references/product-codes.md.
    When normalization happens, emit an INFO on stderr for traceability.
    """
    if not product:
        return product
    canonical = PRODUCT_CODE_ALIASES.get(product)
    if canonical:
        print(f"INFO: product code {product} normalized to {canonical}", file=sys.stderr)
        return canonical
    return product


def _format_updated(ts) -> str:
    """Convert gmtModifiedOrigin (millisecond timestamp) to YYYY-MM-DD; return '' when the value is missing/invalid."""
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return ""
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
    except (OverflowError, OSError, ValueError):
        return ""


# ---------------- HTML table -> Markdown (read body cleaning) ----------------

class _TableHTMLParser(HTMLParser):
    """Parse a single <table> fragment into rows: list[list[str]].

    Inside cells: <a> becomes [text](href), <li> becomes a "- " line, <p>/<div>/<br> become line breaks,
    all other tags (<b>/<strong>/<code>/<span>, etc.) keep plain text only.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._row = None
        self._cell = None
        self._link_href = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
        elif self._cell is None:
            return
        elif tag == "a":
            self._link_href = dict(attrs).get("href") or ""
        elif tag == "li":
            self._cell.append("\n- ")
        elif tag in ("p", "div"):
            # <li><p> combination: a <p> immediately following the start of a list item does not add a newline, so "- " stays attached to its text
            if not (self._cell and self._cell[-1] == "\n- "):
                self._cell.append("\n")
        elif tag == "br":
            self._cell.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            if self._row is not None and self._cell is not None:
                self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "a":
            self._link_href = None

    def handle_data(self, data):
        if self._cell is None or not data:
            return
        if self._link_href is not None:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self._cell.append(f"[{text}]({self._link_href})")
        else:
            self._cell.append(data)


def _clean_table_cell(raw: str) -> str:
    """Clean cell text: fold by line, collapse whitespace within a line, join lines with <br>;
    escape pipes so the Markdown table structure is not broken."""
    lines = []
    for seg in re.sub(r"[ \t]*\n[ \t]*", "\n", raw).split("\n"):
        seg = re.sub(r"\s+", " ", seg).strip()
        if seg:
            lines.append(seg)
    return "<br>".join(lines).replace("|", "\\|")


def _table_to_markdown(table_html: str) -> str:
    """Convert a single <table> fragment to a Markdown table; on structural anomalies (parse failure or too few rows)
    raise ValueError so the caller can degrade to plain text. The first row becomes the header (actual doc header rows carry <b>)."""
    parser = _TableHTMLParser()
    parser.feed(table_html)
    parser.close()
    rows = parser.rows
    if len(rows) < 2:
        raise ValueError("table rows insufficient")
    width = max(len(r) for r in rows)
    lines = []
    for i, row in enumerate(rows):
        cells = [_clean_table_cell(c) for c in row]
        cells += [""] * (width - len(cells))
        lines.append("| " + " | ".join(cells) + " |")
        if i == 0:
            lines.append("|" + "---|" * width)
    return "\n".join(lines)


_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.DOTALL | re.IGNORECASE)


def _convert_html_tables(text: str) -> str:
    """Convert all <table> fragments in the body to Markdown tables; when a single table fails to convert,
    degrade it to _strip_html plain text without affecting the rest of the content."""
    def _repl(m):
        try:
            return _table_to_markdown(m.group(0))
        except Exception:
            return _strip_html(m.group(0))
    return _TABLE_RE.sub(_repl, text)


def fetch_json(url: str):
    """Fetch and parse JSON; return None on failure and print the reason to stderr."""
    text = fetch(url)
    if _is_err(text):
        print(f"[request failed] {url} -> {text}", file=sys.stderr)
        return None
    if _looks_like_html(text):
        print(f"[request failed] {url} returned an HTML page (the path may not exist)", file=sys.stderr)
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[JSON parse failed] {url}: {e}", file=sys.stderr)
        return None


# ---------------- Help Center (llms.txt / .md) ----------------

def list_products(args):
    """List all available products and their codes."""
    text = fetch(f"{LLMS_BASE}/llms.txt")
    if _is_err(text):
        print(text)
        return

    # Parse product entries: - [name](url): description
    pattern = re.compile(r"^- \[([^\]]+)\]\(([^)]+)\):\s*(.*)", re.MULTILINE)
    matches = pattern.findall(text)

    def extract_code(url: str) -> str:
        """Extract the product code from an llms.txt URL."""
        m = re.search(r"/zh/product/([^/]+)\.html/llms\.txt", url)
        if m:
            return m.group(1)
        m = re.search(r"/zh/([^/]+)/llms\.txt", url)
        return m.group(1) if m else ""

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


def list_docs(args):
    """List the full doc catalog of a product (truncated to the first N entries by default to prevent context bloat)."""
    product = _normalize_product_code(args.product)
    text, from_cache = _get_llms_text(product)
    if from_cache:
        print(f"INFO: llms.txt served from local cache {_llms_cache_path(product)}", file=sys.stderr)
    if _is_err(text):
        print(text)
        return

    # Parse entries
    pattern = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)", re.MULTILINE)
    matches = pattern.findall(text)

    if not matches:
        print(f"No doc index found for product '{product}'; please check whether the product code is correct.")
        print(f"URL: {LLMS_BASE}/{product}/llms.txt")
        return

    total = len(matches)
    limit = args.max_results if args.max_results > 0 else total

    if args.json:
        docs = [{"title": t, "url": u, "desc": d[:100]} for t, u, d in matches[:limit]]
        print(json.dumps(docs, ensure_ascii=False, indent=2))
        if total > limit:
            print(f"... ({total} entries in total, first {limit} shown; use -n 0 to show all, or search -p {product} for a precise search)",
                  file=sys.stderr)
        return

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
            m = re.match(r"- \[([^\]]+)\]\(([^)]+)\):\s*(.*)", line_s)
            if m:
                title, url, desc = m.group(1), m.group(2), m.group(3)
                short_desc = desc[:80] + "..." if len(desc) > 80 else desc
                print(f"  - {title}")
                print(f"    {url}")
                if short_desc:
                    print(f"    {short_desc}")
                printed += 1
    if total > limit:
        print(f"\n... ({total} entries in total, first {limit} shown; use -n 0 to show all, or search -p {product} for a precise search)")


# ---------------- categoryId mapping cache (user directory only; never write into the skill directory) ----------------

def _load_category_cache() -> dict:
    """Load the product_code -> categoryId cache.

    When the file is missing, JSON parsing fails, or the top level is not an object (e.g. `[1,2,3]`, `"abc"`),
    fall back to the built-in seeds (seeds are bare ints; the reader is compatible with them and they are TTL-exempt).
    Valid file entries only accept the {"category_id": int, "written_at": number} shape;
    bare-int entries come only from the built-in seeds and are never written to the file by _save_category_cache.
    """
    cache = {"expires_days": CATEGORY_CACHE_TTL_DAYS, "entries": dict(CATEGORY_SEED)}
    try:
        with open(CATEGORY_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return cache
        entries = data.get("entries")
        if isinstance(entries, dict):
            cache["entries"].update(
                {k: v for k, v in entries.items()
                 if isinstance(v, dict) and isinstance(v.get("category_id"), int)})
    except (OSError, ValueError):
        pass
    return cache


def _get_cached_category_id(cache: dict, product: str):
    """Return a non-expired cached categoryId; return None when there is no entry or the TTL has passed.

    Bare-int entries (the built-in seed shape, e.g. {"oss": 31815}) are compatible: return them directly;
    seeds are TTL-exempt (no written_at, valid forever).
    """
    entry = cache.get("entries", {}).get(product)
    if isinstance(entry, bool):
        return None
    if isinstance(entry, int):
        return entry if entry > 0 else None
    if not isinstance(entry, dict):
        return None
    written = entry.get("written_at")
    if not isinstance(written, (int, float)):
        return None
    ttl = cache.get("expires_days", CATEGORY_CACHE_TTL_DAYS) * 86400
    if time.time() - written > ttl:
        return None
    cid = entry.get("category_id")
    return cid if isinstance(cid, int) else None


def _save_category_cache(cache: dict) -> None:
    """Write the cache file back (create the directory if missing).

    Bare-int seed entries are not written to the file (avoid cache-file shape drift; seeds only take effect in memory).
    Write to a temp file (same directory, pid suffix) then os.replace atomically; on write failure only WARN,
    without affecting the main flow.
    """
    entries = {k: v for k, v in cache.get("entries", {}).items()
               if not isinstance(v, int)}
    payload = {"expires_days": cache.get("expires_days", CATEGORY_CACHE_TTL_DAYS),
               "entries": entries}
    try:
        os.makedirs(os.path.dirname(CATEGORY_CACHE_PATH), exist_ok=True)
        tmp_path = f"{CATEGORY_CACHE_PATH}.tmp.{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, CATEGORY_CACHE_PATH)
    except OSError as e:
        print(f"WARN: failed to write the categoryId cache ({e}); skipping cache this time", file=sys.stderr)


# ---------------- Product llms.txt local cache (user directory only; never write into the skill directory) ----------------

def _llms_cache_path(product: str) -> str:
    """Cache file path for a product llms.txt; path separators in the product code are escaped to underscores."""
    safe = product.replace("/", "_")
    return os.path.join(LLMS_CACHE_DIR, f"{safe}.txt")


def _get_llms_text(product: str) -> tuple:
    """Get the product llms.txt content, preferring a non-expired local cache.

    Returns (text, from_cache). On cache miss/expiry/read failure, silently refetch from origin and atomically
    refresh the cache; when the fetch returns an error marker ([HTTP ...]/[Error]...), the cache is not written;
    Rate-limit/outage local degradation: when the origin fetch fails but an expired local cache exists,
    degrade to the stale cache (non-empty content only) with a WARN, instead of surfacing nothing.
    """
    path = _llms_cache_path(product)
    try:
        st = os.stat(path)
        if time.time() - st.st_mtime <= LLMS_CACHE_TTL_DAYS * 86400:
            with open(path, encoding="utf-8") as f:
                return f.read(), True
    except OSError:
        pass
    text = fetch(f"{LLMS_BASE}/{product}/llms.txt")
    if not _is_err(text):
        try:
            os.makedirs(LLMS_CACHE_DIR, exist_ok=True)
            tmp_path = f"{path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp_path, path)
        except OSError as e:
            print(f"WARN: failed to write the llms.txt cache ({e}); skipping cache this time", file=sys.stderr)
    else:
        # Local degradation on rate limit / outage: serve the expired cache if present
        try:
            with open(path, encoding="utf-8") as f:
                stale = f.read()
            if stale.strip():
                print(f"WARN: llms.txt fetch failed ({text.splitlines()[0] if text else 'unknown'}); "
                      f"degrading to the expired local cache for '{product}' "
                      f"(results may lag the live docs)", file=sys.stderr)
                return stale, True
        except OSError:
            pass
    return text, False


_NUMERIC_TITLE_RE = re.compile(r"^\d{4}-\d{8}$")


def _readable_title(item: dict) -> str:
    """Get a readable title: for purely numeric titles (e.g. 2024-12345678), fall back to
    seoTitle/originTitle/categoryName (take the first non-empty, non-numeric one); if no fallback is usable,
    keep the original title."""
    title = item.get("title") or ""
    if " | " in title:
        title = title.split(" | ")[0]
    # Server-side highlight markers (<em>keyword</em>) are not part of the title itself; always strip them
    title = _strip_html(title)
    if not _NUMERIC_TITLE_RE.match(title):
        return title
    for field in ("seoTitle", "originTitle", "categoryName"):
        cand = (item.get(field) or "").strip()
        if " | " in cand:
            cand = cand.split(" | ")[0]
        if cand and not _NUMERIC_TITLE_RE.match(cand):
            return _strip_html(cand)
    return title


def _search_fetch_page(params: dict):
    """Issue a single-page doSearch request and validate the response; return None on anomalies (caller degrades).

    Network exception/timeout: retry once; HTTP 4xx/5xx: no retry.
    """
    url = SEARCH_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    text = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=SEARCH_TIMEOUT) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as e:
            hint = " (suspected rate limiting)" if e.code == 429 else ""
            print(f"WARN: search API returned HTTP {e.code} {e.reason}{hint}; no retry, "
                  f"degrading to the llms.txt index leg", file=sys.stderr)
            return None
        except Exception as e:
            if attempt == 0:
                print(f"WARN: search API network exception ({e}); retrying once...", file=sys.stderr)
                continue
            print(f"WARN: search API still failed after retry ({e}); degrading to the llms.txt index leg",
                  file=sys.stderr)
            return None

    # HTTP 200 but anomalous content: signals of channel revamp/rate limiting; degrade directly
    if _looks_like_html(text):
        print("WARN: search API returned an HTML page (suspected rate limiting/revamp); degrading to the llms.txt index leg",
              file=sys.stderr)
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        print("WARN: search API returned non-JSON content (suspected rate limiting/revamp); degrading to the llms.txt index leg",
              file=sys.stderr)
        return None

    if not isinstance(data, dict):
        print("WARN: search API returned a malformed structure; degrading to the llms.txt index leg", file=sys.stderr)
        return None
    if data.get("success") is False:
        print("WARN: search API success=false; degrading to the llms.txt index leg", file=sys.stderr)
        return None
    code = data.get("code")
    if code is not None and str(code) != "200":
        print(f"WARN: search API code={code} (not 200); degrading to the llms.txt index leg", file=sys.stderr)
        return None
    return data


def _search_parse_items(info: list, include_category_id: bool) -> list:
    """Convert raw doSearch info entries into output records (including the updated timestamp field)."""
    results = []
    for item in info:
        if not isinstance(item, dict):
            continue
        title = _readable_title(item)
        url = item.get("url") or ""
        desc = _strip_html(item.get("content") or "")[:120]
        prod = item.get("productName") or ""
        if not prod:
            m = re.search(r"/zh/([^/]+)/", url)
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
               include_category_id: bool = False) -> list | None:
    """Call the official doSearch full-text search backend.
    
    On success (including a trustworthy "no results" empty list) return a list; on failure return None, and the
    caller degrades to the llms.txt index leg. All degradations emit a WARN on stderr for traceability.
    
    - category_id: doSearch server-side category filter (pure digits). With this param, pageSize=50
      and the server-side filter is trusted; no URL post-filtering.
    - product only (no category_id): wide search with pageSize=50, then client-side post-filter by URLs containing
      /zh/{product}/ (the fallback path before categoryId discovery).
    - include_category_id=True: result items carry the raw categoryId field (for the discovery mechanism to take the mode);
      the discovery wide search also requests pageSize=50 (not capped by limit).
    - Only pure global unfiltered queries (no category_id, no product, not a discovery wide search) cap pageSize at 20.
    - Multi-page fetching: the backend truly caps each page at 10 items but pageNo paging works. Only enabled on the
      precise categoryId path when limit>10 (or unlimited): paginate ceil(limit/10) times,
      capped at SEARCH_MAX_PAGES (3 pages, i.e. up to 30 items); paths without categoryId keep a single request.
    """
    if category_id is not None or product or include_category_id:
        page_size = 50
    else:
        page_size = min(max(limit, 1), 20)
    params = {
        "queryWord": keyword,
        "pageSize": page_size,
        "pageNo": 1,
        "bizType": "help",
    }
    if category_id is not None:
        params["categoryId"] = category_id

    data = _search_fetch_page(params)
    if data is None:
        return None
    info = ((data.get("data") or {}).get("info")) or []
    results = _search_parse_items(info, include_category_id)

    # Only the precise categoryId path enables pagination: the backend truly caps each page at 10 items; keep pulling later pages when limit>10
    if category_id is not None and (limit is None or limit > SEARCH_PAGE_CAP):
        pages_fetched = 1
        max_pages = SEARCH_MAX_PAGES
        if limit is not None:
            max_pages = min(max_pages, (limit + SEARCH_PAGE_CAP - 1) // SEARCH_PAGE_CAP)
        while len(info) >= SEARCH_PAGE_CAP and pages_fetched < max_pages:
            params["pageNo"] = pages_fetched + 1
            page_data = _search_fetch_page(params)
            if page_data is None:
                print(f"WARN: failed to fetch doSearch page {pages_fetched + 1}; "
                      f"keeping only the results of the first {pages_fetched} pages", file=sys.stderr)
                break
            info = ((page_data.get("data") or {}).get("info")) or []
            results.extend(_search_parse_items(info, include_category_id))
            pages_fetched += 1
        if pages_fetched > 1:
            print(f"INFO: doSearch paginated fetch (precise categoryId path), {pages_fetched} page requests in total, "
                  f"{len(results)} items accumulated", file=sys.stderr)

    # Server-side categoryId filter: trust the server-side results; no URL post-filtering
    if category_id is not None:
        return results if limit is None else results[:limit]
    # Product filtering is client-side post-filtering (wide search with pageSize=50, then filter down to limit items)
    if product:
        results = _post_filter_by_product(results, product)
    # totalCount=0 / empty info is a trustworthy "no results"; return an empty list instead of None
    return results if limit is None else results[:limit]


def _post_filter_by_product(results: list, product: str) -> list:
    """Client-side post-filter: keep only results whose URL contains /zh/{product}/."""
    needle = f"/zh/{product}/"
    return [r for r in results if needle in r["url"]]


def _scan_product_index(product: str, keyword: str) -> list:
    """llms.txt index leg: title+summary substring scan for a single product (via the local cache layer).
    Return None when the index does not exist; return [] when nothing matches."""
    text, _ = _get_llms_text(product)
    if _is_err(text) or _looks_like_html(text) or not text.strip():
        return None
    doc_pattern = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)", re.MULTILINE)
    hits = []
    for title, url, desc in doc_pattern.findall(text):
        if keyword in title.lower() or keyword in desc.lower():
            hits.append({"product": product, "title": title, "url": url,
                         "desc": desc[:120], "source": "index"})
    return hits


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


def _discover_category_id(raw_results: list, product: str):
    """Reverse-look-up the product categoryId from wide-search results: collect the categoryIds of entries whose URL
    contains /zh/{product}/ and take the mode; only trust it when the mode gets >= 2 votes; return None when it
    cannot be discovered."""
    needle = f"/zh/{product}/"
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


def _normalize_url(url: str) -> str:
    """URL normalization: strip the query/fragment, the .md suffix and the trailing slash, and fold case at path level
    (improves cross-leg dedup robustness)."""
    u = url.split("#", 1)[0].split("?", 1)[0].lower()
    if u.endswith(".md"):
        u = u[:-3]
    return u.rstrip("/")


def _fuse_results(fulltext_hits: list, index_hits: list) -> list:
    """Fuse full-text leg and index leg results (deterministic, no randomness).

    Score = full-text leg rank-decaying base score (N-i) + index-leg hit BONUS;
    entries hit by both legs score highest (source=both). Sort by score descending first;
    on ties, by full-text leg original order (index-only hits come after full-text entries, keeping index order).
    """
    bonus = max(len(fulltext_hits), 1)
    scores = {}
    ranks = {}
    records = {}
    for i, h in enumerate(fulltext_hits):
        key = _normalize_url(h["url"])
        scores[key] = scores.get(key, 0) + (len(fulltext_hits) - i)
        ranks.setdefault(key, i)
        records[key] = {"product": h["product"], "title": h["title"],
                        "url": h["url"], "desc": h["desc"], "source": "fulltext"}
        if h.get("updated"):
            records[key]["updated"] = h["updated"]
    for h in index_hits:
        key = _normalize_url(h["url"])
        scores[key] = scores.get(key, 0) + bonus
        ranks.setdefault(key, len(fulltext_hits))
        if key not in records:
            records[key] = {"product": h["product"], "title": h["title"],
                            "url": h["url"], "desc": h["desc"], "source": "index"}
        else:
            records[key]["source"] = "both"
            if not records[key]["desc"]:
                records[key]["desc"] = h["desc"]
    order = sorted(scores.keys(), key=lambda k: (-scores[k], ranks[k]))
    return [records[k] for k in order]


def _render_search_results(found: list, keyword: str, max_results) -> None:
    """Render search results in the existing format (shared by the full-text and index legs); max_results=None means unlimited.
    When a full-text leg entry carries an updated timestamp field, append (updated: YYYY-MM-DD) after the snippet line."""
    shown = len(found) if max_results is None else min(len(found), max_results)
    print(f"Found {len(found)} matching docs (showing first {shown}):\n")
    for i, doc in enumerate(found[:max_results] if max_results is not None else found, 1):
        print(f"{i}. [{doc['product']}] {doc['title']}")
        print(f"   {doc['url']}")
        desc_line = f"   {doc['desc']}" if doc['desc'] else ""
        updated = f" (updated: {doc['updated']})" if doc.get('updated') else ""
        if desc_line or updated:
            print(desc_line + updated)
        print()


def _render_no_result(keyword: str) -> None:
    print(f"No docs found containing '{keyword}'.")
    print("Suggestion: use the WebSearch tool with 'keyword site:help.aliyun.com' for broader results.")
    print("Hint: if this was a query with -p, retry without -p, or use list-products to verify the product code.")


def _product_search_results(args, keyword: str, product: str):
    """Search with -p: full-text leg (categoryId server-side filter) + llms.txt index leg dual-path fusion,
    eliminating false negatives from client-side URL post-filtering and substring matching.

    Returns the fused result list (may be empty); when the product index does not exist and the full-text leg
    also has no results, emit a warning and return None so the caller terminates.
    """
    cache = _load_category_cache()
    category_id = _get_cached_category_id(cache, product)
    # Normalize -n 0 to "unlimited" (consistent with list-docs and other subcommands)
    limit = args.max_results if args.max_results > 0 else None

    # ---- Full-text leg: prefer categoryId server-side filter ----
    fulltext_hits = None
    if category_id is not None:
        print(f"INFO: categoryId cache hit {product}->{category_id}, doSearch server-side filtering", file=sys.stderr)
        precise = search_api(keyword, product=product, limit=limit,
                             category_id=category_id)
        if precise is not None:
            fulltext_hits = precise
        else:
            print(f"WARN: precise query with categoryId={category_id} failed; degrading to wide search + URL post-filter",
                  file=sys.stderr)

    if fulltext_hits is None:
        # Wide search (no categoryId, pageSize=50): serves both as the discovery data source and as the post-filter fallback result
        wide_raw = search_api(keyword, limit=50, include_category_id=True)
        if wide_raw is not None:
            discovered = _discover_category_id(wide_raw, product)
            if discovered is not None:
                precise = search_api(keyword, product=product, limit=limit,
                                     category_id=discovered)
                if precise is not None:
                    fulltext_hits = precise
                    # Only write the cache after a precise query succeeds, so a wrong id is not cached for 30 days
                    print(f"INFO: discovered categoryId {product}->{discovered} (mode votes>=2), "
                          f"written to cache {CATEGORY_CACHE_PATH}", file=sys.stderr)
                    cache["entries"][product] = {"category_id": discovered,
                                                 "written_at": int(time.time())}
                    _save_category_cache(cache)
            if fulltext_hits is None:
                if discovered is None:
                    print(f"WARN: could not discover the categoryId of {product} (insufficient mode votes); "
                          f"falling back to URL post-filter (pageSize=50) this time", file=sys.stderr)
                elif precise is None:
                    print(f"WARN: precise query with categoryId={discovered} failed; "
                          f"falling back to URL post-filter (pageSize=50) this time, not writing to cache", file=sys.stderr)
                filtered = _post_filter_by_product(wide_raw, product)
                fulltext_hits = filtered if limit is None else filtered[:limit]
        else:
            print("WARN: full-text search leg unavailable; degrading to the llms.txt index leg", file=sys.stderr)

    # ---- Index leg + fusion ----
    index_hits = _scan_product_index(product, keyword)
    if index_hits is None:
        if fulltext_hits:
            # Index leg unavailable (the product may not exist, or a transient llms.txt outage),
            # but do not discard the already-successful full-text leg results
            print(f"WARN: llms.txt index leg unavailable; outputting full-text leg results only", file=sys.stderr)
            index_hits = []
        else:
            print(f"[warning] the doc index of product '{product}' does not exist; please use list-products to verify the product code.")
            return None

    if fulltext_hits is not None:
        for h in fulltext_hits:
            h["source"] = "fulltext"
        fused = _fuse_results(fulltext_hits, index_hits)
        print(f"INFO: fused: {len(fulltext_hits)} fulltext + {len(index_hits)} index"
              f" -> {len(fused)} unique", file=sys.stderr)
    else:
        fused = index_hits
    return fused


def _render_found(args, found: list, limit) -> None:
    """Unified output entry for search results: --json / empty-result advice / normal rendering; limit=None means unlimited."""
    if args.json:
        print(json.dumps(found if limit is None else found[:limit],
                         ensure_ascii=False, indent=2))
        return
    if not found:
        _render_no_result(args.keyword)
        return
    _render_search_results(found, args.keyword, limit)


def _scan_full_index(product: str, keyword: str) -> list:
    """Scan a single product's llms.txt index (title+summary substring match); return [] on index anomalies."""
    text = fetch(f"{LLMS_BASE}/{product}/llms.txt")
    if _is_err(text) or _looks_like_html(text):
        return []
    doc_pattern = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\):\s*(.*)", re.MULTILINE)
    hits = []
    for title, url, desc in doc_pattern.findall(text):
        if keyword in title.lower() or keyword in desc.lower():
            hits.append({"product": product, "title": title, "url": url,
                         "desc": desc[:120], "source": "index"})
    return hits


def _index_leg_search(keyword: str, product: str | None):
    """llms.txt index leg: with a product, scan that single product; without one, concurrently scan all product indexes.
    Returns a list; when a single product's index does not exist, emit a warning and return None (caller terminates)."""
    if product:
        products = [product]
    else:
        # Fetch master index to get all product llms.txt URLs
        master = fetch(f"{LLMS_BASE}/llms.txt")
        if _is_err(master):
            print(master)
            return None
        # Match both /zh/{code}/llms.txt and /zh/product/{id}.html/llms.txt
        url_pattern = re.compile(r"\((https://help\.aliyun\.com/zh/[^)]+/llms\.txt)\)")
        products = []
        for url_match in url_pattern.findall(master):
            m = re.search(r"/zh/product/([^/]+)\.html/llms\.txt", url_match)
            if m:
                products.append(f"product/{m.group(1)}.html")
            else:
                m = re.search(r"/zh/([^/]+)/llms\.txt", url_match)
                if m:
                    products.append(m.group(1))
        print(f"INFO: no product specified; concurrently scanning {len(products)} product indexes (~10-20s; "
              f"specifying -p <product> returns in seconds)...", file=sys.stderr)

    if len(products) == 1:
        # Single product: distinguish product-not-exists from no-match to avoid misleading the user
        found = _scan_product_index(products[0], keyword)
        if found is None:
            print(f"[warning] the doc index of product '{products[0]}' does not exist; please use list-products to verify the product code.")
            return None
        return found

    found = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        for hits in pool.map(lambda prod: _scan_full_index(prod, keyword), products):
            found.extend(hits)
    return found


def search_docs(args):
    """Search docs: without -p, full-text leg only (degrade to a full index scan on failure);
    with -p, fuse the full-text leg and the llms.txt index leg; on escape switch / full-text leg failure, index leg only.
    When results are low (<2) and the alias dictionary hits, retry once with the expanded term and merge/dedupe both rounds (traced on stderr);
    the retry inherits the current path semantics; escape switch and degradation leg semantics are unchanged."""
    keyword = args.keyword.lower()
    product = args.product
    if product:
        product = _normalize_product_code(product)
    # Normalize -n 0 to "unlimited" (consistent with list-docs and other subcommands)
    limit = args.max_results if args.max_results > 0 else None

    # CamelCase error-code detection: stderr hint only; does not change the search behavior itself
    _error_code_hint(args.keyword)

    # Full-text search leg (skippable via the ALIYUN_HELP_NO_SEARCH_API=1 escape switch)
    if os.environ.get("ALIYUN_HELP_NO_SEARCH_API") != "1":
        if product:
            results = _product_search_results(args, keyword, product)
            if results is None:
                return
            results = _expand_retry(results, keyword,
                                    lambda kw: _product_search_results(args, kw, product))
            _render_found(args, results, limit)
            return

        def _global_fulltext(kw: str):
            hits = search_api(kw, product=None, limit=limit)
            if hits is None:
                return None
            for h in hits:
                h["source"] = "fulltext"
            return hits

        api_hits = _global_fulltext(keyword)
        if api_hits is not None:
            api_hits = _expand_retry(api_hits, keyword, _global_fulltext)
            _render_found(args, api_hits, limit)
            return

    # ---- Index leg: llms.txt (title+summary substring match, no ranking) ----
    print("INFO: degrading to the llms.txt index leg (title+summary substring match only, no relevance ranking)",
          file=sys.stderr)
    found = _index_leg_search(keyword, product)
    if found is None:
        return
    found = _expand_retry(found, keyword,
                          lambda kw: _index_leg_search(kw, product) or [])
    _render_found(args, found, limit)


def read_doc(args):
    """Read a document body (auto-append the .md suffix; detect HTML fallback so a whole HTML page is not dumped into context)."""
    url = args.url

    # Ensure .md suffix
    if not url.endswith(".md"):
        # If it's a help.aliyun.com URL, append .md
        if "help.aliyun.com" in url:
            url = url.rstrip("/") + ".md"

    text = fetch(url)
    if _is_err(text):
        # Fallback: try without .md
        if url.endswith(".md"):
            print(f"[.md fetch failed, trying the original URL]", file=sys.stderr)
            text = fetch(url[:-3])
        if _is_err(text):
            print(text)
            return

    if _looks_like_html(text) and not args.raw:
        print(f"[warning] this URL returned an HTML page instead of Markdown (HTTP 200, but the doc may have moved or the slug is dead).")
        print(f"URL: {url}")
        print("Suggestions:")
        print("  1. Use search/list-docs to find the latest .md link of this doc in the llms.txt index (links in the index are guaranteed valid)")
        print("  2. Or use the WebFetch tool to read the original URL (without .md) and extract the body")
        print("  (append --raw if you really need the raw HTML output)")
        return

    if not text.strip():
        print(f"[warning] this URL returned empty content (HTTP 200 empty body); the doc may not exist.")
        print(f"URL: {url}")
        print("Suggestion: use search/list-docs to find the latest .md link of this doc in the llms.txt index.")
        return

    if not args.raw:
        # Convert bare HTML tables in the body to Markdown (--raw keeps the original output)
        text = _convert_html_tables(text)

    if args.max_lines > 0:
        lines = text.split("\n")
        if len(lines) > args.max_lines:
            text = "\n".join(lines[:args.max_lines])
            text += f"\n\n... ({len(lines)} lines in total, first {args.max_lines} shown)"

    print(text)


def read_product_llms(args):
    """Read a product's raw llms.txt (via the local cache layer)."""
    product = _normalize_product_code(args.product)
    text, from_cache = _get_llms_text(product)
    if from_cache:
        print(f"INFO: llms.txt served from local cache {_llms_cache_path(product)}", file=sys.stderr)
    if _is_err(text):
        print(text)
        return
    if _looks_like_html(text) or not text.strip():
        # A nonexistent product may return an HTML page, or an HTTP 200 empty response body
        print(f"[warning] the llms.txt of product '{product}' does not exist or is empty; please use list-products to verify the product code.")
        return

    if args.max_lines > 0:
        lines = text.split("\n")
        if len(lines) > args.max_lines:
            text = "\n".join(lines[:args.max_lines])
            text += f"\n\n... ({len(lines)} lines in total, first {args.max_lines} shown)"

    print(text)


# ---------------- OpenAPI metadata (api.aliyun.com/meta) ----------------

def _load_meta_products() -> list:
    data = fetch_json(f"{META_BASE}/products.json")
    return data if isinstance(data, list) else []


def _resolve_meta_product(code: str) -> dict:
    """Match an OpenAPI product code case-insensitively (meta paths require exact casing, e.g. Actiontrail/Ecs)."""
    products = _load_meta_products()
    low = code.lower()
    for p in products:
        if (p.get("code") or "").lower() == low or (p.get("shortName") or "").lower() == low:
            return p
    # Fallback: substring match on name
    hits = [p for p in products if low in (p.get("name") or "").lower()]
    if len(hits) == 1:
        return hits[0]
    if hits:
        print(f"[hint] '{code}' matches multiple products; please use an exact code:", file=sys.stderr)
        for p in hits[:10]:
            print(f"  {p['code']:<24s} {p['name']}", file=sys.stderr)
    return {}


def api_products(args):
    """List OpenAPI metadata products (code/name/version), with optional keyword filtering."""
    products = _load_meta_products()
    if not products:
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return
    kw = (args.keyword or "").lower()
    if kw:
        products = [p for p in products
                    if kw in (p.get("code") or "").lower() or kw in (p.get("name") or "").lower()
                    or kw in (p.get("group") or "").lower()]
    if args.json:
        print(json.dumps(products, ensure_ascii=False, indent=2))
        return
    print(f"{len(products)} products in total:")
    for p in products[:args.max_results]:
        versions = ",".join(p.get("versions") or [])
        print(f"  {p.get('code') or '':<24s} {p.get('name') or '':<20s} default version {p.get('defaultVersion') or '-'}"
              f"  (all: {versions})")
    if len(products) > args.max_results:
        print(f"... ({len(products)} entries in total, first {args.max_results} shown; add a keyword to filter)")


def api_list(args):
    """List all APIs (name/title/read-write type) of a given product version, with optional keyword filtering."""
    prod = _resolve_meta_product(args.product)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return
    version = args.api_version or prod.get("defaultVersion")
    data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/api-docs.json")
    if not data:
        print(f"Failed to fetch the API list of {prod['code']}/{version}; available versions: {prod.get('versions')}")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return
    apis = data.get("apis") or {}
    kw = (args.keyword or "").lower()
    rows = []
    for name, info in apis.items():
        title = info.get("title") or ""
        summary = (info.get("summary") or "").split("\n")[0]
        if kw and kw not in name.lower() and kw not in title.lower() and kw not in summary.lower():
            continue
        rows.append((name, title, info.get("operationType", "-"), bool(info.get("deprecated")), summary))
    rows.sort()

    if args.json:
        print(json.dumps([{"api": n, "title": t, "operationType": o, "deprecated": dep, "summary": s}
                          for n, t, o, dep, s in rows], ensure_ascii=False, indent=2))
        return
    print(f"{prod['code']} / {version}: {len(rows)} matching APIs in total:\n")
    for name, title, op, deprecated, summary in rows[:args.max_results]:
        flag = " (deprecated)" if deprecated else ""
        print(f"  {name:<44s} {title}{flag} [{op}]")
    if len(rows) > args.max_results:
        print(f"\n... ({len(rows)} entries in total, first {args.max_results} shown; add a keyword to filter)")


def _render_schema_type(schema: dict) -> str:
    t = schema.get("type", "-")
    if t == "array":
        item_t = (schema.get("items") or {}).get("type", "?")
        return f"array<{item_t}>"
    return t


def _is_valid_api_meta(data) -> bool:
    """Determine whether single-API metadata is valid (a nonexistent API endpoint returns empty/insubstantial JSON instead of an error)."""
    return isinstance(data, dict) and bool(
        data.get("title") or data.get("methods") or data.get("parameters") or data.get("summary")
    )


# Degradation hint for the api-* failure exits: the meta endpoint is a single dependency (no backup
# backend), so every failure exit points the caller at the narrative fallback path.
_META_FALLBACK_HINT = ("Hint: the OpenAPI metadata endpoint (api.aliyun.com) may be unavailable or rate-limited, "
                       "or the product/API name may be wrong; verify codes with api-products, "
                       "or fall back to help-doc search, e.g. search \"<error-code-or-keyword>\" -p <product>")


def api_info(args):
    """Output the structured contract of a single API: parameters / error codes / RAM permission points / debug link."""
    prod = _resolve_meta_product(args.product)
    if not prod:
        print(f"Product '{args.product}' not found in the OpenAPI metadata; use api-products to see product codes.")
        print(_META_FALLBACK_HINT, file=sys.stderr)
        return
    version = args.api_version or prod.get("defaultVersion")
    api_name = args.api

    data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/apis/{api_name}/api.json")
    if not _is_valid_api_meta(data):
        # API-name casing fallback: find the exact name from api-docs.json and retry
        docs = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/api-docs.json")
        apis = (docs or {}).get("apis") or {}
        match = next((n for n in apis if n.lower() == api_name.lower()), None)
        if match and match != api_name:
            api_name = match
            data = fetch_json(f"{META_BASE}/products/{prod['code']}/versions/{version}/apis/{api_name}/api.json")
        if not _is_valid_api_meta(data):
            print(f"API '{args.api}' not found ({prod['code']}/{version}). "
                  f"Use api-list {prod['code']} to see the API catalog.")
            print(_META_FALLBACK_HINT, file=sys.stderr)
            return

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"# {api_name} ({prod['code']} / {version})")
    if data.get("title"):
        print(f"Title: {data['title']}")
    summary = (data.get("summary") or "").strip()
    if summary:
        print(f"Summary: {summary.splitlines()[0]}")
    print(f"Methods: {','.join(data.get('methods', []))}  |  Read/Write: {data.get('operationType', '-')}"
          f"  |  Deprecated: {'yes' if data.get('deprecated') else 'no'}")

    ram = data.get("ramActions") or []
    acts = []
    for a in ram:
        if not isinstance(a, dict):
            continue
        # Two historical shapes: nested {ramAction:{action}} or flat {action}
        act = ((a.get("ramAction") or {}).get("action")) or a.get("action")
        if act:
            acts.append(act)
    if acts:
        print(f"RAM permission points: {', '.join(acts)}")

    params = data.get("parameters") or []
    if params:
        print(f"\n## Request parameters ({len(params)})\n")
        print("| Parameter | In | Type | Required | Description |")
        print("|---|---|---|---|---|")
        for p in params:
            schema = p.get("schema") or {}
            desc = (schema.get("description") or "").split("\n")[0].strip()
            if len(desc) > 80:
                desc = desc[:80] + "..."
            desc = desc.replace("|", "\\|")
            required = "✅" if schema.get("required") else ""
            print(f"| {p.get('name', '-')} | {p.get('in', '-')} | {_render_schema_type(schema)}"
                  f" | {required} | {desc} |")

    err = data.get("errorCodes") or {}
    entries = []
    if isinstance(err, dict):
        for status, items in err.items():
            for it in items if isinstance(items, list) else []:
                entries.append((status, it.get("errorCode", "-"), (it.get("errorMessage") or "")[:80]))
    if entries:
        print(f"\n## Error codes ({len(entries)})\n")
        print("| HTTP | Error code | Message |")
        print("|---|---|---|")
        for status, code, msg in entries:
            print(f"| {status} | {code} | {msg.replace('|', '·')} |")

    print(f"\nDebug / full schema: https://api.aliyun.com/api/{prod['code']}/{version}/{api_name}"
          f" (append --json to this command to dump the full raw metadata, including response structures and examples)")


# ---------------- CLI ----------------

def main():
    parser = argparse.ArgumentParser(
        description="Alibaba Cloud Help Center search and OpenAPI metadata verification tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list-products
    p_lp = sub.add_parser("list-products", help="List all Help Center products")
    p_lp.add_argument("-v", "--verbose", action="store_true", help="Show product descriptions")
    p_lp.add_argument("--json", action="store_true", help="Output in JSON format")
    p_lp.set_defaults(func=list_products)

    # list-docs
    p_ld = sub.add_parser("list-docs", help="List a product's doc catalog (first 100 by default)")
    p_ld.add_argument("product", help="Product code (e.g. oss, ecs)")
    p_ld.add_argument("-n", "--max-results", type=int, default=100,
                      help="Max entries (default 100, 0=unlimited; large products can reach thousands, use 0 with care)")
    p_ld.add_argument("--json", action="store_true", help="Output in JSON format")
    p_ld.set_defaults(func=list_docs)

    # search
    p_s = sub.add_parser("search", help="Search help documents")
    p_s.add_argument("keyword", help="Search keyword")
    p_s.add_argument("-p", "--product", help="Restrict to a product code (strongly recommended; without it, all indexes are scanned concurrently in ~10-20s)")
    p_s.add_argument("-n", "--max-results", type=int, default=20,
                     help="Max results (default 20, 0=unlimited; the doSearch backend truly caps each page at 10 items; "
                          "without -p, -n 20 returns at most 10 in practice; with -p, only the precise categoryId path "
                          "paginates, up to 30 items)")
    p_s.add_argument("--json", action="store_true",
                     help="Output in JSON format (source field: fulltext=full-text leg, index=index leg, both=hit by both legs)")
    p_s.set_defaults(func=search_docs)

    # read
    p_r = sub.add_parser("read", help="Read a document body")
    p_r.add_argument("url", help="Doc URL (the .md suffix is appended automatically)")
    p_r.add_argument("-l", "--max-lines", type=int, default=0, help="Max lines (0=unlimited)")
    p_r.add_argument("--raw", action="store_true", help="Output as-is even when the response is HTML (by default it is intercepted with advice)")
    p_r.set_defaults(func=read_doc)

    # read-product
    p_rp = sub.add_parser("read-product", help="Read a product's raw llms.txt")
    p_rp.add_argument("product", help="Product code")
    p_rp.add_argument("-l", "--max-lines", type=int, default=0, help="Max lines")
    p_rp.set_defaults(func=read_product_llms)

    # api-products
    p_ap = sub.add_parser("api-products", help="List OpenAPI product codes and versions")
    p_ap.add_argument("keyword", nargs="?", default=None, help="Filter by code/name/group")
    p_ap.add_argument("-n", "--max-results", type=int, default=50, help="Max entries (default 50)")
    p_ap.add_argument("--json", action="store_true", help="Output in JSON format")
    p_ap.set_defaults(func=api_products)

    # api-list
    p_al = sub.add_parser("api-list", help="List all APIs of a product")
    p_al.add_argument("product", help="OpenAPI product code (case-insensitive, e.g. actiontrail/ecs)")
    p_al.add_argument("keyword", nargs="?", default=None, help="Filter by API name/title/summary")
    p_al.add_argument("-v", "--api-version", default=None, help="API version (defaults to the product's defaultVersion)")
    p_al.add_argument("-n", "--max-results", type=int, default=50, help="Max entries (default 50)")
    p_al.add_argument("--json", action="store_true", help="Output in JSON format")
    p_al.set_defaults(func=api_list)

    # api-info
    p_ai = sub.add_parser("api-info", help="Structured contract of a single API (parameters/error codes/RAM permission points)")
    p_ai.add_argument("product", help="OpenAPI product code (case-insensitive)")
    p_ai.add_argument("api", help="API name (case-insensitive, e.g. LookupEvents)")
    p_ai.add_argument("-v", "--api-version", default=None, help="API version (defaults to the product's defaultVersion)")
    p_ai.add_argument("--json", action="store_true", help="Dump the full raw metadata JSON (including response structures/examples)")
    p_ai.set_defaults(func=api_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
